from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_API_BASE = "https://console.vast.ai/api/v0"


class VastAPIError(RuntimeError):
    pass


def read_api_key(env_file: str | None = None) -> str:
    import os

    value = os.environ.get("VAST_API_KEY", "").strip()
    if value:
        return value
    if env_file:
        for line in Path(env_file).read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, raw_value = stripped.split("=", 1)
            if key.strip() == "VAST_API_KEY":
                value = raw_value.strip().strip("\"'")
                if value:
                    return value
    raise VastAPIError("VAST_API_KEY is not set and was not found in the environment file")


class VastClient:
    def __init__(self, api_key: str, api_base: str = DEFAULT_API_BASE) -> None:
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        timeout: float = 60,
        *,
        allow_list: bool = False,
    ) -> Any:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"{self.api_base}/{path.lstrip('/')}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")[:1000]
            raise VastAPIError(f"Vast API {method} {path} returned {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise VastAPIError(f"Vast API {method} {path} failed: {exc}") from exc
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise VastAPIError(f"Vast API {method} {path} returned invalid JSON") from exc
        if isinstance(value, list) and allow_list:
            return value
        if not isinstance(value, dict):
            raise VastAPIError(f"Vast API {method} {path} returned an unexpected payload")
        return value

    def account(self) -> dict[str, Any]:
        return self.request("GET", "users/current/")

    def ssh_keys(self) -> list[dict[str, Any]]:
        payload = self.request("GET", "ssh/", allow_list=True)
        if isinstance(payload, list):
            keys = payload
        else:
            keys = payload.get("ssh_keys", payload.get("keys", []))
        if not isinstance(keys, list):
            raise VastAPIError("Vast SSH key response did not contain a list")
        return keys

    def create_ssh_key(self, public_key: str) -> dict[str, Any]:
        key = public_key.strip()
        if not key.startswith(("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")):
            raise VastAPIError("SSH public key is not in OpenSSH format")
        return self.request("POST", "ssh/", {"ssh_key": key}, timeout=90)

    def instances(self) -> list[dict[str, Any]]:
        payload = self.request("GET", "instances/")
        instances = payload.get("instances", [])
        return instances if isinstance(instances, list) else [instances]

    def instance(self, instance_id: int) -> dict[str, Any]:
        payload = self.request("GET", f"instances/{instance_id}/")
        instance = payload.get("instances", payload)
        if isinstance(instance, list):
            return instance[0] if instance else {}
        return instance

    def search_offers(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        payload = self.request("POST", "bundles/", filters, timeout=90)
        offers = payload.get("offers", [])
        if not isinstance(offers, list):
            raise VastAPIError("Vast offers response did not contain a list")
        return offers

    def offer(self, offer_id: int) -> dict[str, Any]:
        offers = self.search_offers(
            {
                "limit": 25,
                "type": "ondemand",
                "ask_contract_id": {"eq": offer_id},
            }
        )
        matches = [offer for offer in offers if int(offer.get("id", -1)) == offer_id]
        if not matches:
            raise VastAPIError(f"offer {offer_id} is no longer available")
        return matches[0]

    def create_instance(
        self,
        offer_id: int,
        *,
        image: str,
        disk_gb: int,
        label: str,
    ) -> int:
        payload = self.request(
            "PUT",
            f"asks/{offer_id}/",
            {
                "image": image,
                "disk": disk_gb,
                "label": label,
                "runtype": "ssh_direct",
                "target_state": "running",
                "env": "-e TZ=America/Los_Angeles",
            },
            timeout=90,
        )
        instance_id = payload.get("new_contract")
        if not payload.get("success") or instance_id is None:
            raise VastAPIError(f"instance creation failed: {payload.get('msg') or payload}")
        return int(instance_id)

    def destroy_instance(self, instance_id: int) -> dict[str, Any]:
        return self.request("DELETE", f"instances/{instance_id}/", timeout=90)

    def attach_ssh_key(self, instance_id: int, public_key: str) -> dict[str, Any]:
        key = public_key.strip()
        if not key.startswith(("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")):
            raise VastAPIError("SSH public key is not in OpenSSH format")
        return self.request(
            "POST",
            f"instances/{instance_id}/ssh/",
            {"ssh_key": key},
            timeout=90,
        )
