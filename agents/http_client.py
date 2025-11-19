"""HTTP helper that prefers `requests` but falls back to urllib."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import request as urllib_request


@dataclass
class SimpleResponse:
    text: str
    status_code: int
    headers: dict[str, str] | None = None

    def json(self) -> Any:
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if not (200 <= self.status_code < 400):
            raise RuntimeError(f"HTTP {self.status_code}")


def http_get(url: str, timeout: int = 20) -> SimpleResponse:
    try:  # pragma: no cover
        import requests

        response = requests.get(url, timeout=timeout)
        return SimpleResponse(text=response.text, status_code=response.status_code, headers=dict(response.headers))
    except Exception:
        with urllib_request.urlopen(url, timeout=timeout) as resp:  # type: ignore[arg-type]
            body = resp.read().decode("utf-8")
            return SimpleResponse(text=body, status_code=resp.getcode() or 200)
