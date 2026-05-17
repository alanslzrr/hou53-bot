"""Structured logging setup.

We use ``structlog`` because every production drain (Datadog, Honeycomb,
Loki, …) consumes JSON better than printf strings, and the moment we
move past local dev we want one stable schema across every log line.

Two profiles, picked by :class:`app.config.Settings.log_format`:

- ``json`` — every record is a single-line JSON object. Default for
  containerised runs.
- ``console`` — pretty-printed key/value pairs with ANSI colour. Default
  when ``HOU53_API_LOG_FORMAT=console`` is set locally.

The ``request_id`` middleware in :mod:`app.main` injects a per-request
correlation ID via ``structlog.contextvars`` so every log line in a
request handler carries it without any glue code at the call sites.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, cast

import structlog


def configure_logging(*, level: str = "INFO", as_json: bool = True) -> None:
    """Wire stdlib ``logging`` into structlog and pick a renderer.

    Idempotent — safe to call multiple times (the second call rebinds
    handlers cleanly).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # stdlib root: send to stdout, no format (structlog renders).
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if as_json:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger. Preferred entry point for handlers."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
