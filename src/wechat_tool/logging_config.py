"""简单的日志配置。"""
from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from typing import Optional
import os

from .settings import DATA_DIR, ensure_directories


def configure_logging(level: Optional[int] = None) -> None:
    """初始化日志系统，按日滚动写入 data/logs/app.log。

    若未显式传入 level，则从环境变量 APP_LOG_LEVEL 读取，
    支持的值例如：DEBUG/INFO/WARNING/ERROR/CRITICAL，默认 INFO。
    """
    ensure_directories()
    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"

    logger = logging.getLogger()
    if any(isinstance(h, TimedRotatingFileHandler) for h in logger.handlers):
        return

    if level is None:
        level_name = os.getenv("APP_LOG_LEVEL", "INFO").upper().strip()
        level = getattr(logging, level_name, logging.INFO)

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
