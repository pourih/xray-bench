"""Build multi-inbound/multi-outbound batch JSON configurations for xray-core."""
from __future__ import annotations

import ipaddress
import socket
from typing import Any, Dict, List, Optional, Tuple
from src.parser.uri_parser import ParsedNode

VALID_NETWORKS = {"tcp", "kcp", "ws", "grpc", "httpupgrade", "xhttp", "splithttp", "domainsocket", "quic"}
VALID_FINGERPRINTS = {"chrome", "firefox", "safari", "ios", "android", "edge", "360", "qq", "random", "randomized"}
VALID_SS_METHODS = {
    "aes-128-gcm", "aes-256-gcm",
    "chacha20-ietf-poly1305", "chacha20-poly1305",
    "xchacha20-ietf-poly1305", "none", ""
}


def is_private_address(addr: str) -> bool:
    """Check if address is a local or private network address."""
    if not addr or addr in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        return ipaddress.ip_address(addr).is_private
    except ValueError:
        return False


def clean_node_for_xray(node: ParsedNode) -> ParsedNode:
    """Normalize node transport and security settings to prevent Xray startup failures."""
    # Clean transport network
    raw_net = (node.transport_network or "tcp").lower().strip()
    for sep in ("?", "#", "%"):
        if sep in raw_net:
            raw_net = raw_net.split(sep)[0]
    node.transport_network = raw_net if raw_net in VALID_NETWORKS else "tcp"

    # Clean uTLS fingerprint
    if node.reality_fp:
        clean_fp = node.reality_fp.lower().strip()
        node.reality_fp = clean_fp if clean_fp in VALID_FINGERPRINTS else ""

    sec = (node.security or "none").lower().strip()

    # Trojan protocol is ALWAYS TLS by specification
    if node.protocol.lower() == "trojan" and sec not in ("tls", "reality"):
        node.security = "tls"

    # Reality only supports raw tcp, xhttp, and grpc in Xray core
    if sec == "reality" and node.transport_network not in ("tcp", "xhttp", "grpc"):
        node.security = "tls"

    return node


def is_node_valid_for_xray(node: ParsedNode) -> Tuple[bool, str]:
    """Verify if a node can be successfully parsed and launched by Xray-core."""
    if not node.address or not node.port or node.port < 1 or node.port > 65535:
        return False, "Invalid address or port"

    proto = node.protocol.lower()
    sec = (node.security or "none").lower()

    if proto == "vless":
        if not node.uuid_or_password:
            return False, "VLESS missing UUID"
        if sec in ("none", "", "false") and not is_private_address(node.address):
            return False, "VLESS without encryption on public IP is prohibited by Xray"
        if sec == "reality" and not node.reality_pbk:
            return False, "Reality without publicKey"

    elif proto == "vmess":
        if not node.uuid_or_password:
            return False, "VMess missing UUID"

    elif proto == "trojan":
        if not node.uuid_or_password:
            return False, "Trojan missing password"

    elif proto == "ss":
        m = (node.method or "").lower()
        if m not in VALID_SS_METHODS:
            return False, f"Unsupported SS cipher: {m}"
        if not node.uuid_or_password:
            return False, "SS missing password"

    elif proto not in ("socks", "wireguard"):
        return False, f"Unsupported protocol: {proto}"

    return True, ""


def allocate_free_ports(count: int, host: str = "127.0.0.1") -> List[int]:
    """Dynamically allocate `count` distinct free TCP ports on the given host."""
    sockets: List[socket.socket] = []
    ports: List[int] = []
    try:
        for _ in range(count):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((host, 0))
            s.listen(1)
            port = s.getsockname()[1]
            ports.append(port)
            sockets.append(s)
    finally:
        for s in sockets:
            s.close()
    return ports


def build_outbound(node: ParsedNode, tag: str) -> Dict[str, Any]:
    """Generate an Xray outbound object corresponding to a ParsedNode."""
    clean_node_for_xray(node)
    protocol = node.protocol.lower()
    outbound: Dict[str, Any] = {
        "tag": tag,
        "protocol": protocol,
    }

    stream_settings: Dict[str, Any] = {}
    net = (node.transport_network or "tcp").lower()
    security = (node.security or "none").lower()

    # Network configuration
    stream_settings["network"] = net

    # TLS / Reality configuration
    clean_fp = node.reality_fp if (node.reality_fp and node.reality_fp in VALID_FINGERPRINTS) else None

    if security == "tls":
        stream_settings["security"] = "tls"
        tls_settings: Dict[str, Any] = {
            "allowInsecure": False,
            "serverName": node.sni or node.host or node.address,
        }
        if node.alpn:
            tls_settings["alpn"] = [a.strip() for a in node.alpn.split(",") if a.strip()]
        if clean_fp:
            tls_settings["fingerprint"] = clean_fp
        stream_settings["tlsSettings"] = tls_settings

    elif security == "reality":
        stream_settings["security"] = "reality"
        reality_settings: Dict[str, Any] = {
            "serverName": node.sni or node.host or node.address,
            "publicKey": node.reality_pbk or "",
            "shortId": node.reality_sid or "",
            "spiderX": node.reality_spx or "/",
            "fingerprint": clean_fp or "chrome",
        }
        stream_settings["realitySettings"] = reality_settings
    else:
        stream_settings["security"] = "none"

    # Transport-specific streamSettings
    if net == "ws":
        ws_settings: Dict[str, Any] = {
            "path": node.path_or_service_name or "/",
        }
        headers: Dict[str, str] = {}
        if node.host or node.sni or node.address:
            headers["Host"] = node.host or node.sni or node.address
        if headers:
            ws_settings["headers"] = headers
        stream_settings["wsSettings"] = ws_settings

    elif net == "grpc":
        stream_settings["grpcSettings"] = {
            "serviceName": node.path_or_service_name or "",
            "multiMode": False,
        }

    elif net == "httpupgrade":
        stream_settings["httpupgradeSettings"] = {
            "path": node.path_or_service_name or "/",
            "host": node.host or node.sni or node.address,
        }

    elif net == "xhttp":
        stream_settings["xhttpSettings"] = {
            "path": node.path_or_service_name or "/",
            "host": node.host or node.sni or node.address,
        }

    elif net == "tcp" and node.header_type == "http":
        stream_settings["tcpSettings"] = {
            "header": {
                "type": "http",
                "request": {
                    "version": "1.1",
                    "method": "GET",
                    "path": [node.path_or_service_name or "/"],
                    "headers": {
                        "Host": [node.host or node.sni or node.address],
                        "User-Agent": [
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        ],
                    },
                },
            }
        }

    # Protocol-specific outbound settings
    if protocol == "vmess":
        outbound["settings"] = {
            "vnext": [
                {
                    "address": node.address,
                    "port": int(node.port),
                    "users": [
                        {
                            "id": node.uuid_or_password,
                            "alterId": 0,
                            "security": "auto",
                        }
                    ],
                }
            ]
        }
        outbound["streamSettings"] = stream_settings

    elif protocol == "vless":
        user_obj: Dict[str, Any] = {
            "id": node.uuid_or_password,
            "encryption": "none",
        }
        if node.flow:
            user_obj["flow"] = node.flow
        outbound["settings"] = {
            "vnext": [
                {
                    "address": node.address,
                    "port": int(node.port),
                    "users": [user_obj],
                }
            ]
        }
        outbound["streamSettings"] = stream_settings

    elif protocol == "trojan":
        outbound["settings"] = {
            "servers": [
                {
                    "address": node.address,
                    "port": int(node.port),
                    "password": node.uuid_or_password,
                }
            ]
        }
        outbound["streamSettings"] = stream_settings

    elif protocol == "ss":
        outbound["protocol"] = "shadowsocks"
        outbound["settings"] = {
            "servers": [
                {
                    "address": node.address,
                    "port": int(node.port),
                    "method": node.method or "aes-256-gcm",
                    "password": node.uuid_or_password,
                }
            ]
        }
        # Shadowsocks usually tcp, but can support simple streamSettings if needed
        if stream_settings.get("security") != "none":
            outbound["streamSettings"] = stream_settings

    elif protocol == "socks":
        server_obj: Dict[str, Any] = {
            "address": node.address,
            "port": int(node.port),
        }
        if node.uuid_or_password and ":" in node.uuid_or_password:
            u, p = node.uuid_or_password.split(":", 1)
            server_obj["users"] = [{"user": u, "pass": p}]
        outbound["settings"] = {"servers": [server_obj]}

    elif protocol == "wireguard":
        outbound["settings"] = {
            "secretKey": node.uuid_or_password,
            "peers": [
                {
                    "publicKey": node.reality_pbk,
                    "endpoint": f"{node.address}:{node.port}",
                }
            ],
        }

    return outbound


def build_batch_config(
    nodes: List[ParsedNode],
    listen_host: str = "127.0.0.1",
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """
    Build a multi-inbound/multi-outbound Xray configuration for a batch of nodes.
    Pre-cleans and filters out incompatible nodes to guarantee successful Xray launch.
    Returns:
      (xray_config_dict, mapping_from_node_id_to_local_port)
    """
    valid_nodes = [
        clean_node_for_xray(n)
        for n in nodes
        if is_node_valid_for_xray(clean_node_for_xray(n))[0]
    ]

    n = len(valid_nodes)
    ports = allocate_free_ports(n, host=listen_host)

    inbounds: List[Dict[str, Any]] = []
    outbounds: List[Dict[str, Any]] = []
    routing_rules: List[Dict[str, Any]] = []
    port_map: Dict[str, int] = {}

    for idx, (node, port) in enumerate(zip(valid_nodes, ports)):
        in_tag = f"in_{idx}"
        out_tag = f"out_{idx}"
        port_map[node.node_id] = port

        inbounds.append(
            {
                "tag": in_tag,
                "port": port,
                "listen": listen_host,
                "protocol": "socks",
                "settings": {
                    "auth": "noauth",
                    "udp": True,
                },
            }
        )

        outbounds.append(build_outbound(node, tag=out_tag))

        routing_rules.append(
            {
                "type": "field",
                "inboundTag": [in_tag],
                "outboundTag": out_tag,
            }
        )

    # Fallback direct outbound
    outbounds.append({"tag": "direct", "protocol": "freedom"})

    config = {
        "log": {"loglevel": "none"},
        "dns": {
            "servers": [
                "1.1.1.1",
                "8.8.8.8",
                "localhost"
            ]
        },
        "inbounds": inbounds,
        "outbounds": outbounds,
        "routing": {
            "domainStrategy": "AsIs",
            "rules": routing_rules,
        },
    }

    return config, port_map
