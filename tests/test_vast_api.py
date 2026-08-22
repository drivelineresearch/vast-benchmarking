from __future__ import annotations

import io
import urllib.error

import pytest

from vast_benchmarking.vast_api import VastAPIError, VastClient


def test_request_retries_rate_limit(monkeypatch) -> None:
    client = VastClient("unused")
    attempts = 0

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self) -> bytes:
            return b'{"success": true}'

    def urlopen(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise urllib.error.HTTPError(
                "https://example.invalid",
                429,
                "Too Many Requests",
                {"Retry-After": "0"},
                io.BytesIO(b"rate limited"),
            )
        return Response()

    monkeypatch.setattr("vast_benchmarking.vast_api.urllib.request.urlopen", urlopen)
    monkeypatch.setattr("vast_benchmarking.vast_api.time.sleep", lambda _seconds: None)

    assert client.request("GET", "test") == {"success": True}
    assert attempts == 3


def test_request_does_not_replay_rate_limited_instance_creation(monkeypatch) -> None:
    client = VastClient("unused")
    attempts = 0

    def urlopen(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        raise urllib.error.HTTPError(
            "https://example.invalid",
            429,
            "Too Many Requests",
            {},
            io.BytesIO(b"rate limited"),
        )

    monkeypatch.setattr("vast_benchmarking.vast_api.urllib.request.urlopen", urlopen)

    with pytest.raises(VastAPIError, match="returned 429"):
        client.request("PUT", "asks/123/", {"image": "example"})
    assert attempts == 1
