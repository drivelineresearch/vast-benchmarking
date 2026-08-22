import pytest

from vast_benchmarking.vast_runner import _bounded_timeout, _ssh_endpoints


def test_bounded_timeout_respects_instance_deadline(monkeypatch) -> None:
    monkeypatch.setattr("vast_benchmarking.vast_runner.time.monotonic", lambda: 100.0)
    assert _bounded_timeout(130.0, 90) == 30
    with pytest.raises(RuntimeError, match="maximum rental duration"):
        _bounded_timeout(100.0, 90)


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
