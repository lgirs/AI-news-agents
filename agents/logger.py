"""Provides a loguru-compatible logger fallback."""
from __future__ import annotations

import logging

try:  # pragma: no cover
    from loguru import logger  # type: ignore
except Exception:  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("ai-news-agents")
    if not hasattr(logger, "success"):
        logger.success = lambda msg, *args, **kwargs: logger.log(logging.INFO, msg, *args, **kwargs)  # type: ignore[attr-defined]

__all__ = ["logger"]
