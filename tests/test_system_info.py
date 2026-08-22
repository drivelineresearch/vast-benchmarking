from vast_benchmarking import system_info
from vast_benchmarking.system_info import _parse_cpu_max


def test_parse_cgroup_v2_cpu_quota() -> None:
    assert _parse_cpu_max("400000 100000\n") == 4.0
    assert _parse_cpu_max("20480000 100000\n") == 204.8
    assert _parse_cpu_max("max 100000\n") is None


def test_effective_worker_count_uses_fractional_capacity(monkeypatch) -> None:
    monkeypatch.setattr(system_info, "effective_cpu_capacity", lambda: 3.84)
    assert system_info.effective_cpu_count() == 4
