"""Primary and backup GeoIP/ISP lookup with SQLite caching and remark formatting."""
from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple
import httpx

from src.database import Database, GeoCacheRecord
from src.events import EventBus, NodeGeoUpdated
from src.geo.google_check import check_google_country, detect_google_country


@dataclass
class GeoInfo:
    exit_ip: str = ""
    country_code: str = ""
    isp: str = ""
    google_country: str = ""
    is_google_bad: bool = False


def clean_isp_name(isp: str) -> str:
    """Clean ISP name by removing common legal suffixes and extraneous details."""
    if not isp:
        return "Unknown"
    cleaned = re.sub(
        r"\b(Inc\.?|LLC|Ltd\.?|Corp\.?|Corporation|GmbH|B\.?V\.?|S\.?A\.?|S\.?R\.?L\.?|Co\.?|Limited)\b",
        "",
        isp,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^AS\d+\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[,/.-]+$", "", cleaned).strip()
    return cleaned or isp[:20]


def cc_to_flag(cc: Optional[str]) -> str:
    """ISO-3166-1 alpha-2 -> regional-indicator flag emoji. Returns empty string when invalid."""
    if not cc:
        return ""
    clean = cc.strip().upper()
    if len(clean) != 2 or not clean.isalpha() or clean == "XX":
        return ""
    try:
        return chr(0x1F1E6 + ord(clean[0]) - ord("A")) + chr(0x1F1E6 + ord(clean[1]) - ord("A"))
    except Exception:
        return ""


def format_country_with_flag(cc: str) -> str:
    """Format country code with flag emoji, e.g. '🇩🇪 DE' or 'XX'."""
    clean = (cc or "XX").strip().upper()
    flag = cc_to_flag(clean)
    return f"{flag} {clean}".strip() if flag else clean


def format_remark(
    prefix: str = "xBench",
    geo_country: str = "XX",
    google_country: str = "",
    isp: str = "Unknown",
    seq_id: int = 0,
    score: int = 0,
) -> str:
    """
    Format node remark using the upgraded specification:
    xBench-xxxx | 🇩🇪 DE (or 🇳🇱 NL) | Hetzner | 5pts
    or xBench-xxxx | 🇩🇪 DE | Hetzner | 0pts when countries match.
    """
    # 1. Clean prefix and format tag (e.g. xBench-0001)
    pfx = prefix.strip().strip("[]").strip() or "xBench"
    tag = f"{pfx}-{seq_id:04d}" if seq_id > 0 else f"{pfx}-0000"

    # 2. Location slot: 🇩🇪 DE (or 🇳🇱 NL) or 🇩🇪 DE
    geo_up = (geo_country or "XX").strip().upper()
    g_up = (google_country or "").strip().upper()
    geo_slot = format_country_with_flag(geo_up)
    if g_up and g_up != geo_up:
        goo_slot = format_country_with_flag(g_up)
        loc_str = f"{geo_slot} (or {goo_slot})"
    else:
        loc_str = geo_slot

    # 3. Clean ISP
    clean_isp = clean_isp_name(isp) or "Unknown"

    # 4. Points slot: {score}pts
    pts_str = f"{score}pts"

    return f"{tag} | {loc_str} | {clean_isp} | {pts_str}"


class GeoLookupService:
    """Service to discover node exit IP, resolve GeoIP/ISP, and check Google country."""

    def __init__(
        self,
        db: Database,
        cache_ttl_days: int = 14,
        blocked_google_countries: Optional[List[str]] = None,
        check_google: bool = True,
        primary_api_url: str = "http://ip-api.com/json/{ip}?fields=status,countryCode,isp,query",
        backup_api_urls: Optional[List[str]] = None,
        google_check_url: str = "https://www.youtube.com/sw.js_data",
        google_fallback_url: str = "https://www.google.com/preferences?hl=en",
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.db = db
        self.cache_ttl_days = cache_ttl_days
        self.blocked_google_countries = blocked_google_countries or ["IR", "RU"]
        self.check_google = check_google
        self.primary_api_url = primary_api_url
        self.backup_api_urls = backup_api_urls or [
            "https://get.geojs.io/v1/ip/geo/{ip}.json",
            "https://ipwhois.app/json/{ip}",
            "https://ipwho.is/{ip}",
            "https://ipinfo.io/{ip}/json",
        ]
        self.google_check_url = google_check_url
        self.google_fallback_url = google_fallback_url
        self.event_bus = event_bus

    async def _single_shot_proxy_lookup(self, proxy_url: str, timeout_sec: float = 2.5) -> Optional[Tuple[str, str, str]]:
        """
        Fast path: Query get.geojs.io, then ip-api.com through proxy in 1 single request
        returning (exit_ip, country_code, isp).
        """
        # 1. Try GeoJS first (unlimited rate limit)
        try:
            geojs_url = "https://get.geojs.io/v1/ip/geo.json"
            async def _req_geojs():
                async with httpx.AsyncClient(
                    proxy=proxy_url,
                    timeout=httpx.Timeout(timeout_sec, connect=timeout_sec, read=timeout_sec),
                    verify=False,
                ) as client:
                    resp = await client.get(geojs_url)
                    if resp.status_code == 200:
                        data = resp.json()
                        ip = str(data.get("ip", "")).strip()
                        cc = str(data.get("country_code", "")).upper()
                        isp = str(data.get("organization_name") or data.get("organization") or "").strip()
                        if ip and cc and cc != "XX":
                            return ip, cc, clean_isp_name(isp)
                return None
            res = await asyncio.wait_for(_req_geojs(), timeout=timeout_sec + 0.3)
            if res:
                return res
        except Exception:
            pass

        # 2. Try ip-api.com
        try:
            url = "http://ip-api.com/json/?fields=status,countryCode,isp,query"
            async def _req():
                async with httpx.AsyncClient(
                    proxy=proxy_url,
                    timeout=httpx.Timeout(timeout_sec, connect=timeout_sec, read=timeout_sec),
                    verify=False,
                ) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        ip = str(data.get("query", "")).strip()
                        cc = str(data.get("countryCode", "")).upper()
                        isp = str(data.get("isp", "")).strip()
                        if ip and cc and cc != "XX":
                            return ip, cc, clean_isp_name(isp)
                    return None
            res = await asyncio.wait_for(_req(), timeout=timeout_sec + 0.3)
            if res:
                return res
        except Exception:
            pass

        return None

    async def discover_exit_ip(self, proxy_url: str, timeout_sec: float = 2.5) -> Optional[str]:
        """Discover exit IP through fast plaintext fallback endpoints."""
        ip_endpoints = [
            "https://get.geojs.io/v1/ip.json",
            "http://api.ipify.org",
            "http://icanhazip.com",
        ]
        for url in ip_endpoints:
            try:
                async def _req():
                    async with httpx.AsyncClient(
                        proxy=proxy_url,
                        timeout=httpx.Timeout(timeout_sec, connect=timeout_sec, read=timeout_sec),
                        verify=False,
                    ) as client:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            if "json" in url:
                                try:
                                    return str(resp.json().get("ip", "")).strip()
                                except Exception:
                                    pass
                            ip = resp.text.strip()
                            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                                return ip
                    return None
                found = await asyncio.wait_for(_req(), timeout=timeout_sec + 0.3)
                if found:
                    return found
            except Exception:
                continue
        return None

    async def lookup_ip_details(self, ip: str) -> Tuple[str, str]:
        """Query primary/backup GeoIP services for country_code and ISP."""
        urls = []
        if self.primary_api_url:
            urls.append(self.primary_api_url)
        if self.backup_api_urls:
            urls.extend(self.backup_api_urls)

        for url_template in urls:
            url = url_template.replace("{ip}", ip if ip else "")
            try:
                async def _req():
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            data = resp.json()
                            country = (
                                data.get("country_code")
                                or data.get("countryCode")
                                or data.get("country")
                                or ""
                            ).upper()
                            isp = (
                                data.get("organization_name")
                                or data.get("organization")
                                or data.get("isp")
                                or (data.get("connection", {}) if isinstance(data.get("connection"), dict) else {}).get("isp")
                                or data.get("org")
                                or ""
                            )
                            if country and len(country) == 2 and country != "XX":
                                return country, clean_isp_name(str(isp))
                    return None
                res = await asyncio.wait_for(_req(), timeout=3.2)
                if res:
                    return res
            except Exception:
                continue

        return "XX", "Unknown"

    async def resolve_node_geo(
        self,
        node_id: str,
        proxy_url: str,
        server_address: str = "",
        timeout_sec: float = 2.5,
    ) -> GeoInfo:
        """
        Resolve GeoIP, ISP, and Google country for a node running on proxy_url.
        Uses SQLite cache when valid, with fast direct server_address fallback.
        """
        exit_ip = ""
        country_code = ""
        isp = ""

        # Check SQLite cache if server_address is known
        cached = None
        if server_address:
            cached = self.db.get_geo_cache(server_address, ttl_days=self.cache_ttl_days)
        if cached and cached.country_code == "XX":
            cached = None

        google_country = ""
        is_google_bad = False

        if cached:
            country_code = cached.country_code or country_code
            isp = cached.isp or isp
            google_country = cached.google_country or country_code
            exit_ip = server_address
            blocked_set = {c.strip().upper() for c in self.blocked_google_countries}
            is_google_bad = (
                cached.is_google_bad
                or (country_code.upper() in blocked_set)
                or (google_country.upper() in blocked_set)
            )
        else:
            # 1. Fast path: single-shot query through proxy to GeoJS
            single = await self._single_shot_proxy_lookup(proxy_url, timeout_sec=timeout_sec)
            if single:
                exit_ip, country_code, isp = single
            else:
                # 2. Try exit IP plaintext discovery through proxy
                exit_ip = await self.discover_exit_ip(proxy_url, timeout_sec=timeout_sec) or ""
                if exit_ip:
                    country_code, isp = await self.lookup_ip_details(exit_ip)

            # 3. Direct server_address fallback (when proxy blocks external IP checks or times out)
            if (not country_code or country_code == "XX") and server_address:
                srv_cc, srv_isp = await self.lookup_ip_details(server_address)
                if srv_cc and srv_cc != "XX":
                    country_code = srv_cc
                    isp = srv_isp
                    if not exit_ip:
                        exit_ip = server_address

            country_code = country_code or "XX"
            isp = isp or "Unknown"

            blocked_set = {c.strip().upper() for c in self.blocked_google_countries}
            is_geo_blocked = country_code.upper() in blocked_set

            # Check Google country if enabled
            if self.check_google:
                raw_g_country = await detect_google_country(
                    proxy_url=proxy_url,
                    primary_url=self.google_check_url,
                    fallback_url=self.google_fallback_url,
                    timeout_sec=max(timeout_sec, 4.0),
                )
                if raw_g_country:
                    google_country = raw_g_country.upper()
                else:
                    google_country = country_code
            else:
                google_country = country_code

            is_google_bad = (
                is_geo_blocked
                or (google_country in blocked_set)
            )

            cache_target = exit_ip or server_address
            if cache_target and country_code and country_code != "XX":
                new_record = GeoCacheRecord(
                    ip=cache_target,
                    country_code=country_code,
                    isp=isp,
                    google_country=google_country,
                    is_google_bad=is_google_bad,
                    updated_at=time.time(),
                )
                self.db.save_geo_cache(new_record)

        self.db.update_node_geo(
            node_id=node_id,
            exit_ip=exit_ip,
            geo_country=country_code,
            isp=isp,
            google_country=google_country,
            is_google_bad=is_google_bad,
        )

        geo_info = GeoInfo(
            exit_ip=exit_ip,
            country_code=country_code,
            isp=isp,
            google_country=google_country,
            is_google_bad=is_google_bad,
        )

        if self.event_bus:
            self.event_bus.emit(
                NodeGeoUpdated(
                    node_id=node_id,
                    country_code=country_code,
                    isp=isp,
                    google_country=google_country,
                    is_google_bad=is_google_bad,
                )
            )

        return geo_info
