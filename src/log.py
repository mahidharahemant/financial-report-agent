from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "app.log"
_configured = False


def configure_logging() -> Path:
    global _configured
    if _configured:
        return LOG_PATH
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger = logging.getLogger("src")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    _configured = True
    return LOG_PATH


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
