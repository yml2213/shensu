"""应用级别的基础设置。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

# 运行根目录：
# - 普通环境：以源代码仓库根为准（当前文件向上两级）
# - PyInstaller 打包：以可执行文件所在目录为准，避免写入临时目录
try:
    import sys
    if getattr(sys, 'frozen', False):  # PyInstaller 打包运行
        ROOT_DIR = Path(sys.executable).resolve().parent
    else:
        ROOT_DIR = Path(__file__).resolve().parents[2]
except Exception:
    ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
MEDIA_DIR = ROOT_DIR / "media"
CONFIG_FILE = ROOT_DIR / "config.json"


def ensure_directories() -> None:
    """确保数据目录存在。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    # 若缺少配置文件，写入一份安全的默认模板
    if not CONFIG_FILE.exists():
        default = {
            "login": {
                "authorize_endpoint": "http://gee.myds.me:8005/api/OfficialAccounts/OauthAuthorize",
                "cookie": "",
                "auto_sms": {
                    "enabled": False,
                    "provider": "yzy",
                    "base_url": "http://api.sqhyw.net:90",
                    "backup_base_url": "http://api.nnanx.com:90",
                    "token": "",
                    "username": "",
                    "password": "",
                    "project_id": "",
                    "operator": "0",
                    "phone_num": "",
                    "scope": "",
                    "address": "",
                    "poll_interval": 5,
                    "max_wait_seconds": 120,
                    "min_remaining": 10,
                    "release_on_success": True,
                    "release_on_failure": True,
                    "blacklist_on_failure": False,
                },
            }
        }
        try:
            CONFIG_FILE.write_text(
                json.dumps(default, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            # 忽略写入失败，保持后续流程可继续
            pass


def save_app_config(data: Dict[str, Any]) -> None:
    data = data or {}
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_app_config() -> Dict[str, Any]:
    """加载可选的全局配置，文件不存在则返回空字典。"""
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - 日志记录后回落默认
        logging.getLogger(__name__).warning("配置文件解析失败: %s", exc)
        return {}
