"""Parse and serialize vmess, vless, trojan, ss, socks, and wireguard URIs."""
from __future__ import annotations

import base64
import json
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def safe_b64decode(s: str) -> bytes:
    """Safely decode base64 string, handling URL-safe variants and missing padding."""
    s = s.strip()
    # Normalize urlsafe characters
    s = s.replace("-", "+").replace("_", "/")
    missing = len(s) % 4
    if missing:
        s += "=" * (4 - missing)
    return base64.b64decode(s)


def safe_b64encode(b: bytes) -> str:
    """Encode bytes to UTF-8 base64 string without trailing newlines."""
    return base64.b64encode(b).decode("utf-8")


@dataclass
class ParsedNode:
    """Canonical representation of an Xray proxy node."""
    raw_uri: str
    protocol: str
    address: str
    port: int
    uuid_or_password: str = ""
    method: str = ""  # For Shadowsocks cipher
    security: str = "none"  # none, tls, reality
    transport_network: str = "tcp"  # tcp, ws, grpc, http, httpupgrade, xhttp
    sni: str = ""
    host: str = ""
    path_or_service_name: str = ""
    reality_pbk: str = ""
    reality_sid: str = ""
    reality_fp: str = ""
    reality_spx: str = ""
    flow: str = ""
    header_type: str = "none"
    alpn: str = ""
    remark: str = ""
    extra_params: Dict[str, str] = field(default_factory=dict)
    vmess_json_format: bool = False
    node_id: str = ""

    def __post_init__(self) -> None:
        if not self.node_id:
            from src.parser.fingerprint import generate_node_id
            self.node_id = generate_node_id(self)


def parse_uri(uri: str) -> Optional[ParsedNode]:
    """
    Parse a proxy URI string into a canonical ParsedNode.
    Supports vmess://, vless://, trojan://, ss://, socks://, wireguard://.
    Returns None if URI format is invalid or unsupported.
    """
    uri = uri.strip()
    if not uri or uri.startswith("#"):
        return None

    if uri.startswith("vmess://"):
        return _parse_vmess(uri)
    elif uri.startswith("vless://"):
        return _parse_vless(uri)
    elif uri.startswith("trojan://"):
        return _parse_trojan(uri)
    elif uri.startswith("ss://"):
        return _parse_ss(uri)
    elif uri.startswith("socks://"):
        return _parse_socks(uri)
    elif uri.startswith("wireguard://"):
        return _parse_wireguard(uri)
    return None


def _parse_vmess(uri: str) -> Optional[ParsedNode]:
    """Parse vmess:// URI (Base64 JSON format or standard URL format)."""
    raw_payload = uri[8:]
    # Check if payload is Base64 JSON
    if "@" not in raw_payload and "?" not in raw_payload:
        try:
            decoded = safe_b64decode(raw_payload).decode("utf-8")
            data = json.loads(decoded)
            address = str(data.get("add", "")).strip()
            port = int(data.get("port", 0))
            uuid = str(data.get("id", "")).strip()
            remark = str(data.get("ps", "")).strip()
            net = str(data.get("net", "tcp")).strip()
            type_hdr = str(data.get("type", "none")).strip()
            host = str(data.get("host", "")).strip()
            path = str(data.get("path", "")).strip()
            tls_val = str(data.get("tls", "")).strip().lower()
            security = "tls" if tls_val in ("tls", "true") else "none"
            sni = str(data.get("sni", "")).strip() or host
            alpn = str(data.get("alpn", "")).strip()
            fp = str(data.get("fp", "")).strip()

            node = ParsedNode(
                raw_uri=uri,
                protocol="vmess",
                address=address,
                port=port,
                uuid_or_password=uuid,
                security=security,
                transport_network=net,
                sni=sni,
                host=host,
                path_or_service_name=path,
                header_type=type_hdr,
                alpn=alpn,
                reality_fp=fp,
                remark=remark,
                vmess_json_format=True,
            )
            return node
        except Exception:
            pass

    # Fallback to URL-style vmess
    try:
        parsed = urllib.parse.urlparse(uri)
        remark = urllib.parse.unquote(parsed.fragment)
        query = urllib.parse.parse_qs(parsed.query)

        address = parsed.hostname or ""
        port = parsed.port or 0
        uuid = parsed.username or ""
        net = query.get("type", ["tcp"])[0]
        security = query.get("security", ["none"])[0]
        sni = query.get("sni", [""])[0]
        host = query.get("host", [""])[0]
        path = query.get("path", [""])[0]
        alpn = query.get("alpn", [""])[0]
        fp = query.get("fp", [""])[0]
        header_type = query.get("headerType", ["none"])[0]

        return ParsedNode(
            raw_uri=uri,
            protocol="vmess",
            address=address,
            port=port,
            uuid_or_password=uuid,
            security=security,
            transport_network=net,
            sni=sni or host,
            host=host,
            path_or_service_name=path,
            header_type=header_type,
            alpn=alpn,
            reality_fp=fp,
            remark=remark,
            vmess_json_format=False,
        )
    except Exception:
        return None


def _parse_vless(uri: str) -> Optional[ParsedNode]:
    """Parse vless:// URI."""
    try:
        parsed = urllib.parse.urlparse(uri)
        remark = urllib.parse.unquote(parsed.fragment)
        query = urllib.parse.parse_qs(parsed.query)

        address = parsed.hostname or ""
        port = parsed.port or 0
        uuid = parsed.username or ""

        net = query.get("type", ["tcp"])[0]
        security = query.get("security", ["none"])[0]
        sni = query.get("sni", [""])[0]
        host = query.get("host", [""])[0]
        path = query.get("path", [""])[0]
        service_name = query.get("serviceName", [""])[0]
        path_or_svc = path or service_name
        pbk = query.get("pbk", [""])[0]
        sid = query.get("sid", [""])[0]
        fp = query.get("fp", [""])[0]
        spx = query.get("spx", [""])[0]
        flow = query.get("flow", [""])[0]
        alpn = query.get("alpn", [""])[0]
        header_type = query.get("headerType", ["none"])[0]

        return ParsedNode(
            raw_uri=uri,
            protocol="vless",
            address=address,
            port=port,
            uuid_or_password=uuid,
            security=security,
            transport_network=net,
            sni=sni or host,
            host=host,
            path_or_service_name=path_or_svc,
            reality_pbk=pbk,
            reality_sid=sid,
            reality_fp=fp,
            reality_spx=spx,
            flow=flow,
            header_type=header_type,
            alpn=alpn,
            remark=remark,
        )
    except Exception:
        return None


def _parse_trojan(uri: str) -> Optional[ParsedNode]:
    """Parse trojan:// URI."""
    try:
        parsed = urllib.parse.urlparse(uri)
        remark = urllib.parse.unquote(parsed.fragment)
        query = urllib.parse.parse_qs(parsed.query)

        address = parsed.hostname or ""
        port = parsed.port or 0
        password = parsed.username or ""

        net = query.get("type", ["tcp"])[0]
        security = query.get("security", ["tls"])[0]
        sni = query.get("sni", [""])[0]
        host = query.get("host", [""])[0]
        path = query.get("path", [""])[0]
        service_name = query.get("serviceName", [""])[0]
        path_or_svc = path or service_name
        alpn = query.get("alpn", [""])[0]
        fp = query.get("fp", [""])[0]
        header_type = query.get("headerType", ["none"])[0]

        return ParsedNode(
            raw_uri=uri,
            protocol="trojan",
            address=address,
            port=port,
            uuid_or_password=password,
            security=security,
            transport_network=net,
            sni=sni or host,
            host=host,
            path_or_service_name=path_or_svc,
            header_type=header_type,
            alpn=alpn,
            reality_fp=fp,
            remark=remark,
        )
    except Exception:
        return None


def _parse_ss(uri: str) -> Optional[ParsedNode]:
    """Parse ss:// URI (SIP002 and legacy Base64 formats)."""
    try:
        payload = uri[5:]
        remark = ""
        if "#" in payload:
            payload, remark_part = payload.split("#", 1)
            remark = urllib.parse.unquote(remark_part)

        method = ""
        password = ""
        address = ""
        port = 0

        # Check for SIP002 format: base64(method:password)@address:port
        if "@" in payload:
            userinfo_part, hostport_part = payload.split("@", 1)
            if "/" in hostport_part:
                hostport_part, _ = hostport_part.split("/", 1)
            if "?" in hostport_part:
                hostport_part, _ = hostport_part.split("?", 1)

            # Try decoding userinfo
            try:
                decoded = safe_b64decode(userinfo_part).decode("utf-8")
                if ":" in decoded:
                    method, password = decoded.split(":", 1)
                else:
                    method = decoded
            except Exception:
                if ":" in userinfo_part:
                    method, password = userinfo_part.split(":", 1)

            if ":" in hostport_part:
                address, port_str = hostport_part.rsplit(":", 1)
                port = int(port_str)
            else:
                address = hostport_part
        else:
            # Legacy format: base64(method:password@address:port)
            # Remove any trailing query params if present
            clean_payload = payload.split("?")[0].split("/")[0]
            decoded = safe_b64decode(clean_payload).decode("utf-8")
            if "@" in decoded and ":" in decoded:
                userinfo, hostport = decoded.split("@", 1)
                if ":" in userinfo:
                    method, password = userinfo.split(":", 1)
                if ":" in hostport:
                    address, port_str = hostport.rsplit(":", 1)
                    port = int(port_str)
                else:
                    address = hostport

        if not address or port <= 0:
            return None

        return ParsedNode(
            raw_uri=uri,
            protocol="ss",
            address=address,
            port=port,
            uuid_or_password=password,
            method=method,
            security="none",
            transport_network="tcp",
            remark=remark,
        )
    except Exception:
        return None


def _parse_socks(uri: str) -> Optional[ParsedNode]:
    """Parse socks:// URI."""
    try:
        parsed = urllib.parse.urlparse(uri)
        remark = urllib.parse.unquote(parsed.fragment)
        address = parsed.hostname or ""
        port = parsed.port or 0
        username = parsed.username or ""
        password = parsed.password or ""

        # Check if username is base64 encoded user:pass
        if username and not password:
            try:
                dec = safe_b64decode(username).decode("utf-8")
                if ":" in dec:
                    username, password = dec.split(":", 1)
            except Exception:
                pass

        cred = f"{username}:{password}" if username else ""
        return ParsedNode(
            raw_uri=uri,
            protocol="socks",
            address=address,
            port=port,
            uuid_or_password=cred,
            remark=remark,
        )
    except Exception:
        return None


def _parse_wireguard(uri: str) -> Optional[ParsedNode]:
    """Parse wireguard:// URI."""
    try:
        parsed = urllib.parse.urlparse(uri)
        remark = urllib.parse.unquote(parsed.fragment)
        query = urllib.parse.parse_qs(parsed.query)

        address = parsed.hostname or ""
        port = parsed.port or 0
        private_key = parsed.username or ""
        public_key = query.get("publickey", [""])[0]

        return ParsedNode(
            raw_uri=uri,
            protocol="wireguard",
            address=address,
            port=port,
            uuid_or_password=private_key,
            reality_pbk=public_key,
            remark=remark,
            extra_params={k: v[0] for k, v in query.items()},
        )
    except Exception:
        return None


def serialize_uri(node: ParsedNode, new_remark: Optional[str] = None) -> str:
    """
    Serialize a ParsedNode back into its canonical URI format.
    Optionally updates the node remark if new_remark is provided.
    Remarks are properly URL-encoded.
    """
    remark = new_remark if new_remark is not None else node.remark
    encoded_remark = urllib.parse.quote(remark)

    if node.protocol == "vmess":
        # Always output standard V2RayN Base64 JSON for maximum compatibility
        vmess_dict = {
            "v": "2",
            "ps": remark,
            "add": node.address,
            "port": node.port,
            "id": node.uuid_or_password,
            "aid": "0",
            "scy": "auto",
            "net": node.transport_network or "tcp",
            "type": node.header_type or "none",
            "host": node.host or "",
            "path": node.path_or_service_name or "",
            "tls": "tls" if node.security == "tls" else "",
            "sni": node.sni or node.host or "",
            "alpn": node.alpn or "",
            "fp": node.reality_fp or "",
        }
        json_str = json.dumps(vmess_dict, separators=(",", ":"))
        return f"vmess://{safe_b64encode(json_str.encode('utf-8'))}"

    elif node.protocol == "vless":
        query_params = {}
        if node.transport_network and node.transport_network != "tcp":
            query_params["type"] = node.transport_network
        else:
            query_params["type"] = "tcp"

        if node.security:
            query_params["security"] = node.security

        if node.sni:
            query_params["sni"] = node.sni
        if node.host and node.host != node.sni:
            query_params["host"] = node.host

        if node.transport_network == "grpc" and node.path_or_service_name:
            query_params["serviceName"] = node.path_or_service_name
        elif node.path_or_service_name:
            query_params["path"] = node.path_or_service_name

        if node.reality_pbk:
            query_params["pbk"] = node.reality_pbk
        if node.reality_sid:
            query_params["sid"] = node.reality_sid
        if node.reality_fp:
            query_params["fp"] = node.reality_fp
        if node.reality_spx:
            query_params["spx"] = node.reality_spx
        if node.flow:
            query_params["flow"] = node.flow
        if node.alpn:
            query_params["alpn"] = node.alpn
        if node.header_type and node.header_type != "none":
            query_params["headerType"] = node.header_type

        query_str = urllib.parse.urlencode(query_params)
        return f"vless://{node.uuid_or_password}@{node.address}:{node.port}?{query_str}#{encoded_remark}"

    elif node.protocol == "trojan":
        query_params = {
            "security": node.security or "tls",
            "type": node.transport_network or "tcp",
        }
        if node.sni:
            query_params["sni"] = node.sni
        if node.host:
            query_params["host"] = node.host
        if node.transport_network == "grpc" and node.path_or_service_name:
            query_params["serviceName"] = node.path_or_service_name
        elif node.path_or_service_name:
            query_params["path"] = node.path_or_service_name
        if node.alpn:
            query_params["alpn"] = node.alpn
        if node.reality_fp:
            query_params["fp"] = node.reality_fp

        query_str = urllib.parse.urlencode(query_params)
        return f"trojan://{node.uuid_or_password}@{node.address}:{node.port}?{query_str}#{encoded_remark}"

    elif node.protocol == "ss":
        userinfo = f"{node.method}:{node.uuid_or_password}"
        encoded_userinfo = safe_b64encode(userinfo.encode("utf-8"))
        return f"ss://{encoded_userinfo}@{node.address}:{node.port}#{encoded_remark}"

    elif node.protocol == "socks":
        if node.uuid_or_password:
            return f"socks://{node.uuid_or_password}@{node.address}:{node.port}#{encoded_remark}"
        return f"socks://{node.address}:{node.port}#{encoded_remark}"

    elif node.protocol == "wireguard":
        params = dict(node.extra_params)
        if node.reality_pbk:
            params["publickey"] = node.reality_pbk
        q_str = urllib.parse.urlencode(params)
        return f"wireguard://{node.uuid_or_password}@{node.address}:{node.port}?{q_str}#{encoded_remark}"

    return node.raw_uri
