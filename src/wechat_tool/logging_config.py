"""简单的日志配置。"""
from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

from .settings import DATA_DIR, ensure_directories


def configure_logging(level: int = logging.INFO) -> None:
    """初始化日志系统，按日滚动写入 data/logs/app.log。"""
    ensure_directories()
    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"

    logger = logging.getLogger()
    if any(isinstance(h, TimedRotatingFileHandler) for h in logger.handlers):
        return

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = TimedRotatingFileHandler(
        log_path,
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
