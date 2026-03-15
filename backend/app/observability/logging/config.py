"""Application logging configuration."""

import json
import logging
import sys
from datetime import datetime, timezone

from app.observability.config import ObservabilityConfig


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Human-readable log formatter for development."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s %(levelname)-8s %(name)-30s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def configure_logging(config: ObservabilityConfig) -> None:
    """Configure Python logging for the application.

    - JSON format for production (LOG_FORMAT=json)
    - Human-readable for development (LOG_FORMAT=text)
    - Level from LOG_LEVEL setting
    - Output to stdout (container-friendly)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create stdout handler
    handler = logging.StreamHandler(sys.stdout)

    if config.log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter())

    root_logger.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
