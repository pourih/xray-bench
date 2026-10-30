"""Unit tests for Xray multi-inbound/outbound batch JSON configuration builder."""
from src.parser.uri_parser import parse_uri
from src.xray.config_builder import allocate_free_ports, build_batch_config, build_outbound


def test_allocate_free_ports():
    ports = allocate_free_ports(5, host="127.0.0.1")
    assert len(ports) == 5
    assert len(set(ports)) == 5
    for p in ports:
        assert 1024 <= p <= 65535


def test_build_batch_config():
    nodes = [
        parse_uri("vless://uuid1@server1.com:443?security=reality&pbk=key1#Node1"),
        parse_uri("vmess://eyJhZGQiOiAic2VydmVyMi5jb20iLCAicG9ydCI6IDQ0MywgImlkIjogInV1aWQyIiwgIm5ldCI6ICJ3cyJ9"),
        parse_uri("trojan://pass3@server3.com:443#Node3"),
    ]

    config, port_map = build_batch_config(nodes, listen_host="127.0.0.1")

    # Inbounds check
    inbounds = config["inbounds"]
    assert len(inbounds) == 3
    for i, inb in enumerate(inbounds):
        assert inb["tag"] == f"in_{i}"
        assert inb["protocol"] == "socks"
        assert inb["listen"] == "127.0.0.1"
        assert inb["port"] == port_map[nodes[i].node_id]

    # Outbounds check
    outbounds = config["outbounds"]
    # 3 node outbounds + 1 direct fallback
    assert len(outbounds) == 4
    assert outbounds[0]["tag"] == "out_0"
    assert outbounds[0]["protocol"] == "vless"
    assert outbounds[0]["streamSettings"]["security"] == "reality"
    assert outbounds[0]["streamSettings"]["realitySettings"]["publicKey"] == "key1"

    assert outbounds[1]["tag"] == "out_1"
    assert outbounds[1]["protocol"] == "vmess"
    assert outbounds[1]["streamSettings"]["network"] == "ws"

    assert outbounds[2]["tag"] == "out_2"
    assert outbounds[2]["protocol"] == "trojan"

    # Routing rules 1-to-1 check
    rules = config["routing"]["rules"]
    assert len(rules) == 3
    for i, rule in enumerate(rules):
        assert rule["inboundTag"] == [f"in_{i}"]
        assert rule["outboundTag"] == f"out_{i}"
