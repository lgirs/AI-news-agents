"""Compatibility layer that falls back to a lightweight Pydantic stub.

The real project depends on `pydantic`, but the execution environment used
for scaffolding may not ship with external dependencies. This module allows
basic type containers for tests while still importing the official package
when available.
"""
from __future__ import annotations

import json
from typing import Any, Dict

try:  # pragma: no cover - prefer the real dependency when available
    from pydantic import BaseModel, Field, HttpUrl  # type: ignore
except Exception:  # pragma: no cover
    class HttpUrl(str):
        """Very small stand-in for HttpUrl."""

    class BaseModel:
        """Tiny subset of the Pydantic interface used in this project."""

        def __init__(self, **data: Any) -> None:
            for key, value in data.items():
                setattr(self, key, value)
            self.__dict__.setdefault("__fields__", list(data.keys()))

        def dict(self) -> Dict[str, Any]:
            return {key: getattr(self, key) for key in self.__dict__ if not key.startswith("_")}

        def json(self, **_: Any) -> str:
            return json.dumps(self.dict(), default=str)

    def Field(*_, **__):  # type: ignore
        return None

__all__ = ["BaseModel", "Field", "HttpUrl"]
