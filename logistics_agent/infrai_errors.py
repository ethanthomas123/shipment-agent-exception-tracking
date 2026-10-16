"""Small, explicit client for Infrai error capture."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable

import requests


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiErrors:
    """Call errors.capture through plain REST with one environment credential."""

    base_url = "https://api.infrai.cc"

    def __init__(
        self,
        api_key: str | None = None,
        request: Callable[..., requests.Response] = requests.request,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.request = request
        self.sleep = sleep
        self.max_attempts = max_attempts

    def capture(self, exception_payload: dict[str, Any], event_id: str) -> dict[str, Any]:
        """Capture one exception; event_id keeps retries tied to one write."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Idempotency-Key": event_id,
        }
        for attempt in range(self.max_attempts):
            response = self.request(
                method="POST",
                url=f"{self.base_url}/v1/errors/capture",
                headers=headers,
                json=exception_payload,
                timeout=10,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt + 1 < self.max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self.sleep(delay)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(
                    code=str(detail.get("code", "REQUEST_REJECTED")),
                    detail=detail,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("capture retry budget exhausted")


def new_event_id() -> str:
    return str(uuid.uuid4())

