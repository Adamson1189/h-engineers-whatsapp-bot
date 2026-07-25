"""
logging_config.py

WHY THIS FILE EXISTS:
When a customer's WhatsApp message fails to process at 2 AM, `print()` statements
won't help you. You need logs that show:
- WHEN something happened (timestamp)
- WHERE it happened (module name)
- HOW SEVERE it was (INFO, WARNING, ERROR)
- WHAT happened (the message)

We log to both the console (so you see it live during development) and to a
rotating log file (so production history is kept without eating your disk).
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(debug: bool = True) -> None:
    level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter(LOG_FORMAT)

    # Console handler — what you see while developing
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Rotating file handler — keeps last 5 files of 5MB each, so disk never fills up
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
