"""应用级别的基础设置。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
MEDIA_DIR = ROOT_DIR / "media"
CONFIG_FILE = ROOT_DIR / "config.json"


def ensure_directories() -> None:
    """确保数据目录存在。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def load_app_config() -> Dict[str, Any]:
    """加载可选的全局配置，文件不存在则返回空字典。"""
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - 日志记录后回落默认
        logging.getLogger(__name__).warning("配置文件解析失败: %s", exc)
        return {}
