"""
src/utils/logger.py
Centralized rotating file logger + rich console output.
"""
import logging
import logging.handlers
from pathlib import Path
from rich.logging import RichHandler


def get_logger(name: str, config: dict) -> logging.Logger:
    log_cfg = config["logging"]
    log_dir = Path(log_cfg["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_cfg["level"].upper(), logging.INFO))

    if logger.handlers:
        return logger  # Already configured

    # Rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "app.log",
        maxBytes=log_cfg["max_bytes"],
        backupCount=log_cfg["backup_count"],
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )

    # Rich console handler
    console_handler = RichHandler(rich_tracebacks=True, markup=True)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
