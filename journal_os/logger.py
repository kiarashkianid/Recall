"""
logger.py
─────────
Centralised logging for Journal OS.

Usage in any module:
    from logger import get_logger
    log = get_logger(__name__)
    log.info("Entry saved", extra={"entry_id": 42})
    log.error("DB connection failed", exc_info=True)

Log files are written to ./logs/ and rotated daily (kept for 14 days).
Console output mirrors the file at WARNING level or above in production,
and at DEBUG level when LOG_LEVEL=DEBUG is set in the environment.
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler

_LOG_DIR = os.getenv("LOG_DIR", "./logs")
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

_CONSOLE_FMT = "%(levelname)s  %(name)s  %(message)s"
_FILE_FMT    = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
_DATE_FMT    = "%Y-%m-%d %H:%M:%S"

_initialised = False


def _setup() -> None:
    global _initialised
    if _initialised:
        return

    os.makedirs(_LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)          # handlers filter individually

    # ── File handler: DEBUG+, rotates daily, keeps 14 days ──
    fh = TimedRotatingFileHandler(
        filename=os.path.join(_LOG_DIR, "journal_os.log"),
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(_FILE_FMT, _DATE_FMT))
    root.addHandler(fh)

    # ── Console handler: WARNING+ by default ──
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, _LOG_LEVEL, logging.WARNING))
    ch.setFormatter(logging.Formatter(_CONSOLE_FMT))
    root.addHandler(ch)

    # Silence noisy third-party loggers
    for lib in ("httpx", "httpcore", "openai", "chromadb", "crewai"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    _initialised = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, initialising the logging system on first call."""
    _setup()
    return logging.getLogger(name)
