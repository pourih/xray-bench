"""Unit tests for deterministic node fingerprinting and blacklist filtering."""
import json
import tempfile
from pathlib import Path
import pytest

from src.parser.fingerprint import generate_node_id, is_blacklisted, load_blacklist
from src.parser.uri_parser import parse_uri, safe_b64encode


def test_identical_node_id_across_remark_changes():
    # VLESS node with original remark
    vless_original = (
        "vless://9d26e4f3-2d2d-4b9b-9c6a-4d22bb48c7f9@myserver.com:443?"
        "security=reality&type=grpc&serviceName=mygrpc&sni=myserver.com&"
        "pbk=xyz789publickey#RemarkOne"
    )
    node1 = parse_uri(vless_original)
    assert node1 is not None
    id1 = generate_node_id(node1)

    # Same VLESS node with completely different remark
    vless_renamed = (
        "vless://9d26e4f3-2d2d-4b9b-9c6a-4d22bb48c7f9@myserver.com:443?"
        "security=reality&type=grpc&serviceName=mygrpc&sni=myserver.com&"
        "pbk=xyz789publickey#[xBench]%20DE%20-%20Hetzner"
    )
    node2 = parse_uri(vless_renamed)
    assert node2 is not None
    id2 = generate_node_id(node2)

    assert id1 == id2, "node_id must be completely invariant to remark changes"
    assert node1.node_id == node2.node_id


def test_vmess_node_id_invariance_to_remark():
    vmess_payload1 = {
        "v": "2",
        "ps": "FirstRemark",
        "add": "v.server.io",
        "port": 443,
        "id": "11111111-2222-3333-4444-555555555555",
        "aid": "0",
        "net": "ws",
        "tls": "tls",
    }
    vmess_payload2 = dict(vmess_payload1)
    vmess_payload2["ps"] = "[xBench] US - Google LLC"

    u1 = f"vmess://{safe_b64encode(json.dumps(vmess_payload1).encode())}"
    u2 = f"vmess://{safe_b64encode(json.dumps(vmess_payload2).encode())}"

    n1 = parse_uri(u1)
    n2 = parse_uri(u2)

    assert n1 is not None and n2 is not None
    assert n1.node_id == n2.node_id


def test_blacklist_matching():
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as f:
        # 1. Full URI
        f.write("trojan://secret@badhost.com:443#BadNode\n")
        # 2. Hostname / IP
        f.write("192.0.2.1\n")
        f.write("blocked-domain.com\n")
        # 3. Explicit 64-char hash
        f.write("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\n")
        temp_path = f.name

    try:
        bl = load_blacklist(temp_path)
        assert len(bl) >= 4

        # Test node matching IP
        n_ip = parse_uri("vless://uuid@192.0.2.1:443?type=tcp#Node")
        assert n_ip is not None
        assert is_blacklisted(n_ip, bl) is True

        # Test node matching domain
        n_dom = parse_uri("ss://YWVzLTEyOC1nY206cGFzcw==@blocked-domain.com:8388#Node")
        assert n_dom is not None
        assert is_blacklisted(n_dom, bl) is True

        # Test node matching full URI (via node_id)
        n_uri = parse_uri("trojan://secret@badhost.com:443#DifferentRemark")
        assert n_uri is not None
        assert is_blacklisted(n_uri, bl) is True

        # Test good node that is not blacklisted
        n_good = parse_uri("vless://uuid@goodhost.com:443?type=tcp#GoodNode")
        assert n_good is not None
        assert is_blacklisted(n_good, bl) is False

    finally:
        Path(temp_path).unlink(missing_ok=True)
