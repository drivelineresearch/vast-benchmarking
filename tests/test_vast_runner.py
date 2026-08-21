from vast_benchmarking.vast_runner import _ssh_endpoints


def test_ssh_endpoints_prefers_direct_and_keeps_proxy_fallback():
    instance = {
        "public_ipaddr": "203.0.113.10",
        "ports": {"22/tcp": [{"HostIp": "0.0.0.0", "HostPort": "22123"}]},
        "ssh_host": "ssh4.vast.ai",
        "ssh_port": 12000,
    }

    assert _ssh_endpoints(instance) == [
        ("203.0.113.10", 22123, "direct"),
        ("ssh4.vast.ai", 12000, "proxy"),
    ]
