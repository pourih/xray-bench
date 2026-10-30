"""Unit tests for proxy URI parsing, normalization, and remark rewriting."""
import json
import urllib.parse
import pytest

from src.parser.uri_parser import (
    ParsedNode,
    parse_uri,
    safe_b64decode,
    safe_b64encode,
    serialize_uri,
)


def test_vmess_base64_json_parsing_and_rewriting():
    vmess_payload = {
        "v": "2",
        "ps": "OldRemark",
        "add": "1.2.3.4",
        "port": 443,
        "id": "b831381d-6324-4d53-ad4f-8cda48b30811",
        "aid": "0",
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "myhost.com",
        "path": "/websocket",
        "tls": "tls",
        "sni": "myhost.com",
    }
    raw_uri = f"vmess://{safe_b64encode(json.dumps(vmess_payload).encode())}"

    node = parse_uri(raw_uri)
    assert node is not None
    assert node.protocol == "vmess"
    assert node.address == "1.2.3.4"
    assert node.port == 443
    assert node.uuid_or_password == "b831381d-6324-4d53-ad4f-8cda48b30811"
    assert node.transport_network == "ws"
    assert node.security == "tls"
    assert node.sni == "myhost.com"
    assert node.path_or_service_name == "/websocket"
    assert node.remark == "OldRemark"

    # Rewrite remark
    new_remark = "[xBench] DE - Cloudflare"
    new_uri = serialize_uri(node, new_remark=new_remark)
    assert new_uri.startswith("vmess://")

    # Re-parse to verify rewritten remark and intact parameters
    reparsed = parse_uri(new_uri)
    assert reparsed is not None
    assert reparsed.remark == new_remark
    assert reparsed.address == "1.2.3.4"
    assert reparsed.port == 443
    assert reparsed.uuid_or_password == "b831381d-6324-4d53-ad4f-8cda48b30811"


def test_vless_reality_parsing_and_rewriting():
    raw_uri = (
        "vless://9d26e4f3-2d2d-4b9b-9c6a-4d22bb48c7f9@example.com:443?"
        "security=reality&type=grpc&serviceName=mygrpc&sni=yahoo.com&"
        "pbk=xyz789publickey&sid=1234abcd&fp=chrome&spx=%2F&flow=xtls-rprx-vision#Original%20VLESS"
    )

    node = parse_uri(raw_uri)
    assert node is not None
    assert node.protocol == "vless"
    assert node.address == "example.com"
    assert node.port == 443
    assert node.uuid_or_password == "9d26e4f3-2d2d-4b9b-9c6a-4d22bb48c7f9"
    assert node.security == "reality"
    assert node.transport_network == "grpc"
    assert node.path_or_service_name == "mygrpc"
    assert node.sni == "yahoo.com"
    assert node.reality_pbk == "xyz789publickey"
    assert node.reality_sid == "1234abcd"
    assert node.reality_fp == "chrome"
    assert node.flow == "xtls-rprx-vision"
    assert node.remark == "Original VLESS"

    # Rewrite remark
    new_remark = "[xBench] US (G:US) - DigitalOcean"
    new_uri = serialize_uri(node, new_remark=new_remark)
    assert new_uri.startswith("vless://")

    reparsed = parse_uri(new_uri)
    assert reparsed is not None
    assert reparsed.remark == new_remark
    assert reparsed.reality_pbk == "xyz789publickey"
    assert reparsed.flow == "xtls-rprx-vision"


def test_trojan_parsing_and_rewriting():
    raw_uri = (
        "trojan://mypassword123@trojan.server.org:443?"
        "security=tls&type=ws&path=%2Ftrojan-ws&sni=trojan.server.org#MyTrojan"
    )

    node = parse_uri(raw_uri)
    assert node is not None
    assert node.protocol == "trojan"
    assert node.address == "trojan.server.org"
    assert node.port == 443
    assert node.uuid_or_password == "mypassword123"
    assert node.security == "tls"
    assert node.transport_network == "ws"
    assert node.path_or_service_name == "/trojan-ws"
    assert node.remark == "MyTrojan"

    new_remark = "[xBench] NL - Leaseweb"
    new_uri = serialize_uri(node, new_remark=new_remark)
    reparsed = parse_uri(new_uri)
    assert reparsed is not None
    assert reparsed.remark == new_remark
    assert reparsed.uuid_or_password == "mypassword123"


def test_shadowsocks_sip002_and_legacy_parsing():
    # SIP002 format
    userinfo = safe_b64encode(b"chacha20-ietf-poly1305:mySecretPass")
    sip002_uri = f"ss://{userinfo}@ss.example.com:8388#SipNode"
    node1 = parse_uri(sip002_uri)
    assert node1 is not None
    assert node1.protocol == "ss"
    assert node1.method == "chacha20-ietf-poly1305"
    assert node1.uuid_or_password == "mySecretPass"
    assert node1.address == "ss.example.com"
    assert node1.port == 8388
    assert node1.remark == "SipNode"

    # Legacy format
    legacy_body = safe_b64encode(b"aes-256-gcm:anotherPass@legacy.server.com:9000")
    legacy_uri = f"ss://{legacy_body}#LegacyNode"
    node2 = parse_uri(legacy_uri)
    assert node2 is not None
    assert node2.protocol == "ss"
    assert node2.method == "aes-256-gcm"
    assert node2.uuid_or_password == "anotherPass"
    assert node2.address == "legacy.server.com"
    assert node2.port == 9000
    assert node2.remark == "LegacyNode"


def test_socks_and_wireguard_parsing():
    socks_uri = "socks://admin:pass123@10.0.0.1:1080#InternalSocks"
    node_socks = parse_uri(socks_uri)
    assert node_socks is not None
    assert node_socks.protocol == "socks"
    assert node_socks.address == "10.0.0.1"
    assert node_socks.port == 1080

    wg_uri = "wireguard://aGVsbG8=@198.51.100.1:51820?publickey=d29ybGQ=#WGNode"
    node_wg = parse_uri(wg_uri)
    assert node_wg is not None
    assert node_wg.protocol == "wireguard"
    assert node_wg.address == "198.51.100.1"
    assert node_wg.port == 51820
    assert node_wg.reality_pbk == "d29ybGQ="
