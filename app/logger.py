"""
SafetyVision AI — Structured Logging Module
Thread-safe rotating file and console logging with audit-trail support.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from app.config import get_config


_logger: Optional[logging.Logger] = None


def setup_logger(name: str = "safetyvision") -> logging.Logger:
    """Configures and returns the central logger instance."""
    global _logger
    if _logger is not None:
        return _logger

    cfg = get_config()
    logs_dir = cfg.logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_level_name = cfg.system_config.get("logging", {}).get("level", "INFO").upper()
    level = getattr(logging, log_level_name, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Avoid duplicate handlers if re-initialized
    if not logger.handlers:
        # Standard formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console Stream Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Rotating File Handler
        log_file = logs_dir / "safetyvision.log"
        max_bytes = cfg.system_config.get("logging", {}).get("max_bytes", 10 * 1024 * 1024)
        backup_count = cfg.system_config.get("logging", {}).get("backup_count", 5)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _logger = logger
    _logger.info("SafetyVision AI Logger initialized successfully.")
    return _logger


def get_logger() -> logging.Logger:
    """Convenience accessor for current logger."""
    global _logger
    if _logger is None:
        return setup_logger()
    return _logger
