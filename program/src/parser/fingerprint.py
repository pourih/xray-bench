"""Deterministic SHA-256 node fingerprinting and blacklist filtering."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, List, Set

if TYPE_CHECKING:
    from src.parser.uri_parser import ParsedNode


def generate_node_id(node: ParsedNode) -> str:
    """
    Generate a canonical deterministic SHA-256 hex digest for a node.
    Normalized tuple:
      (protocol, lower(address), port, uuid_or_password, transport_network, tls_or_reality, sni, path_or_service_name, reality_pbk)
    The URI remark/fragment is completely excluded, ensuring renamed nodes
    consistently produce the exact same node_id.
    """
    protocol = (node.protocol or "").strip().lower()
    address = (node.address or "").strip().lower()
    port = int(node.port or 0)

    # For UUIDs or passwords, normalize whitespace and lowercase UUIDs
    uuid_or_pw = (node.uuid_or_password or "").strip()
    if protocol in ("vmess", "vless"):
        uuid_or_pw = uuid_or_pw.lower()

    transport = (node.transport_network or "").strip().lower()
    tls_sec = (node.security or "").strip().lower()
    sni = (node.sni or "").strip().lower()
    path = (node.path_or_service_name or "").strip()
    pbk = (node.reality_pbk or "").strip()

    fingerprint_elements = [
        protocol,
        address,
        str(port),
        uuid_or_pw,
        transport,
        tls_sec,
        sni,
        path,
        pbk,
    ]
    raw_key = "|".join(fingerprint_elements)
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def load_blacklist(blacklist_path: Path | str = "data/blacklist.txt") -> Set[str]:
    """
    Load blacklist items from file.
    Supports:
    - 64-character SHA-256 hex digests
    - IP addresses or server hostnames
    - Full URIs (converts to node_id on load)
    """
    from src.parser.uri_parser import parse_uri

    path = Path(blacklist_path)
    blacklist: Set[str] = set()

    if not path.is_file():
        return blacklist

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            item = line.strip()
            if not item or item.startswith("#"):
                continue

            # Check if line is a full URI
            if "://" in item:
                parsed = parse_uri(item)
                if parsed:
                    blacklist.add(parsed.node_id)
                    blacklist.add(parsed.address.lower())
                else:
                    blacklist.add(item.lower())
            elif len(item) == 64 and all(c in "0123456789abcdefABCDEF" for c in item):
                # Node ID hash
                blacklist.add(item.lower())
            else:
                # Hostname or IP
                blacklist.add(item.lower())

    return blacklist


def is_blacklisted(node: ParsedNode, blacklist: Set[str]) -> bool:
    """
    Check if a ParsedNode matches any blacklist criterion.
    Checks node_id, hostname/IP, and raw URI.
    """
    if not blacklist:
        return False

    if node.node_id.lower() in blacklist:
        return True

    if node.address.strip().lower() in blacklist:
        return True

    if node.raw_uri.strip().lower() in blacklist:
        return True

    return False
