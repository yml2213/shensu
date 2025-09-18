#!/usr/bin/env python3
"""应用入口：启动图形界面。"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_PATH = ROOT / "src"
if SRC_PATH.exists() and str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from wechat_tool.ui.app import run_app  # noqa: E402

logger = logging.getLogger(__name__)


def main_gui() -> None:
    run_app()


if __name__ == "__main__":
    main_gui()
