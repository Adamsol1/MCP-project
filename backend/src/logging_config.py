"""Logging configuration for the application.

Sets up a rotating file handler for the 'app' logger.
"""

import logging
import sys
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
    logger.propagate = False

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

    if not any(getattr(handler, "name", "") == "dev-console" for handler in logger.handlers):
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.name = "dev-console"
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(
            logging.Formatter("%(levelname)s [%(name)s] %(message)s")
        )
        logger.addHandler(console_handler)

    # Keep migration chatter out of the dev console unless something is wrong.
    logging.getLogger("alembic").setLevel(logging.WARNING)
    logging.getLogger("alembic.runtime.migration").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return logger
