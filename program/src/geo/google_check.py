"""Detect what country Google associates with a proxy node's exit IP."""
from __future__ import annotations

import asyncio
import re
from typing import List, Optional, Tuple
import httpx


# ISO 3166-1 alpha-2 country code pattern
COUNTRY_CODE_RE = re.compile(r'^[A-Z]{2}$')

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
HTML_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

LANG_RE = re.compile(r'<html[^>]*\blang\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

# Observed signals for Iran and Russia on Google homepage
IR_LANGS = frozenset({"en-ir", "fa", "fa-ir"})
RU_LANGS = frozenset({"ru", "ru-ru", "en-ru"})

EXPLICIT_LANG_TO_CC = {
    "fa": "IR",
    "fa-ir": "IR",
    "en-ir": "IR",
    "ru": "RU",
    "ru-ru": "RU",
    "en-ru": "RU",
}

BARE_LANG_TO_CC = {
    "en": "US",
    "fa": "IR",
    "ru": "RU",
    "ja": "JP",
    "zh": "CN",
    "zh-cn": "CN",
    "zh-tw": "TW",
    "ko": "KR",
    "ar": "SA",
    "he": "IL",
    "hi": "IN",
    "uk": "UA",
    "tr": "TR",
    "th": "TH",
    "vi": "VN",
    "id": "ID",
    "ms": "MY",
    "pl": "PL",
    "nl": "NL",
    "de": "DE",
    "fr": "FR",
    "it": "IT",
    "es": "ES",
    "pt": "PT",
    "sv": "SE",
    "no": "NO",
    "da": "DK",
    "fi": "FI",
    "el": "GR",
    "hu": "HU",
    "ro": "RO",
    "cs": "CZ",
    "sk": "SK",
    "bg": "BG",
    "hr": "HR",
    "sr": "RS",
}


def extract_html_lang(body_prefix: str) -> str:
    """Extract <html lang="..."> attribute from HTML prefix."""
    m = LANG_RE.search(body_prefix)
    return m.group(1).strip().lower() if m else ""


def google_lang_to_cc(lang: Optional[str]) -> Optional[str]:
    """Map Google <html lang> to ISO 2-letter country code."""
    if not lang:
        return None
    clean = lang.strip().lower().replace("_", "-")
    if not clean:
        return None
    if clean in EXPLICIT_LANG_TO_CC:
        return EXPLICIT_LANG_TO_CC[clean]
    if clean in BARE_LANG_TO_CC:
        return BARE_LANG_TO_CC[clean]
    if "-" in clean:
        parts = [p for p in clean.split("-") if p]
        for part in reversed(parts):
            if len(part) == 2 and part.isalpha():
                return part.upper()
    if len(clean) == 2 and clean.isalpha():
        return clean.upper()
    return None


def parse_google_country_from_html(html: str) -> Optional[str]:
    """Parse country from Google homepage HTML attributes."""
    if not html:
        return None

    # 1. Primary: Extract from <html lang="...">
    lang = extract_html_lang(html[:8192])
    if lang:
        cc = google_lang_to_cc(lang)
        if cc:
            return cc

    # 2. Secondary: Match <input type="hidden" name="gl" value="US">
    m = re.search(r'name=["\']gl["\']\s+value=["\']([A-Z]{2})["\']', html, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    # 3. Match data-country="US" or data-region="US"
    m = re.search(r'data-(?:country|region)=["\']([A-Z]{2})["\']', html, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    # 4. Match "current_country":"US" or "countryCode":"US"
    m = re.search(r'["\'](?:current_country|countryCode|region)["\']\s*:\s*["\']([A-Z]{2})["\']', html, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    return None


async def detect_google_country(
    proxy_url: Optional[str] = None,
    primary_url: str = "https://www.google.com/",
    fallback_url: str = "https://www.google.com/preferences?hl=en",
    timeout_sec: float = 4.0,
) -> Optional[str]:
    """
    Route an HTTPS request through proxy_url to detect Google-assigned country code.
    Tries primary_url (https://www.google.com/) first, then fallback_url.
    """
    client_kwargs = {
        "timeout": httpx.Timeout(timeout_sec, connect=timeout_sec, read=timeout_sec),
        "follow_redirects": True,
        "verify": False,
        "headers": HTML_HEADERS,
    }
    if proxy_url:
        client_kwargs["proxy"] = proxy_url

    async def _do_detect() -> Optional[str]:
        try:
            async with httpx.AsyncClient(**client_kwargs) as client:
                # 1. Primary: Google homepage <html lang>
                try:
                    resp = await client.get(primary_url)
                    if resp.status_code == 200:
                        country = parse_google_country_from_html(resp.text)
                        if country:
                            return country
                except Exception:
                    pass

                # 2. Fallback: Google preferences
                try:
                    resp = await client.get(fallback_url)
                    if resp.status_code == 200:
                        country = parse_google_country_from_html(resp.text)
                        if country:
                            return country
                except Exception:
                    pass
        except Exception:
            pass
        return None

    try:
        return await asyncio.wait_for(_do_detect(), timeout=timeout_sec + 0.5)
    except Exception:
        return None


def check_google_country(
    detected_country: Optional[str],
    blocked_countries: List[str],
) -> Tuple[str, bool]:
    """
    Evaluate if detected country is blocked.
    Returns: (normalized_country_code, is_google_bad)
    """
    if not detected_country:
        return "", False

    code = detected_country.strip().upper()
    blocked_set = {c.strip().upper() for c in blocked_countries}
    is_bad = code in blocked_set
    return code, is_bad
