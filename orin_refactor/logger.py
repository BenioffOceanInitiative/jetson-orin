import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger(log_file=None, level=logging.INFO, max_bytes=64*1024, backup_count=1):
    logger = logging.getLogger("app")
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

Path("logs").mkdir(exist_ok=True)

logger = setup_logger(log_file="logs/app.log", max_bytes=64*1024, backup_count=1)