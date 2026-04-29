"""
services/api/logger.py
========================
Structured JSON logging for production.
In development: human-readable colored output.
In production: JSON lines (compatible with Datadog, CloudWatch, GCP Logging).
"""

import logging
import sys
import json
from datetime import datetime, timezone
from services.api.config import get_settings

settings = get_settings()


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON — ideal for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
            "module":    record.module,
            "function":  record.funcName,
            "line":      record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger by name.

    Usage:
        from services.api.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Server started", extra={"port": 8000})
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)

    if settings.is_production:
        handler.setFormatter(JSONFormatter())
    else:
        fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
        handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))

    logger.addHandler(handler)
    logger.propagate = False
    return logger
