"""Structured (JSON-ish) logging for the brain.

Every line is a single JSON object so logs are greppable and machine-parseable
while a human can still read them. The whole point of the brain's resilience is
that you can see what it decided and why, after the fact.
"""

from __future__ import annotations

import json
import logging
import sys
import time


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Attach any structured extras passed via logger.x(..., extra={"fields": {...}}).
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLineFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # The claude CLI subprocess can be chatty; keep our own logs clean.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def log_event(logger: logging.Logger, msg: str, **fields) -> None:
    """Log ``msg`` with structured ``fields`` attached to the JSON line."""
    logger.info(msg, extra={"fields": fields})
