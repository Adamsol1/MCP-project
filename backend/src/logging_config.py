"""Logging configuration for the application.

Sets up a rotating file handler for the 'app' logger.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging() -> logging.Logger:
    """Configure and return the application logger.

    Creates the log directory if it does not exist.
    Sets up a RotatingFileHandler writing to data/logs/app.log.
    Rotates at 5 MB, keeping up to 3 backup files.
    Log format: timestamp level name — message

    Returns:
        The configured 'app' logger.
    """
    log_dir = Path(__file__).resolve().parents[1] / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("app")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s")
        )
        logger.addHandler(handler)

    return logger
