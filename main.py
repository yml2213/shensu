#!/usr/bin/env python3
"""命令行入口：提交申诉信息。"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_PATH = ROOT / 'src'
if SRC_PATH.exists() and str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from typing import Any, Dict

from wechat_tool.config import read_submission_config
from wechat_tool.logging_config import configure_logging
from wechat_tool.services.submission_service import SubmissionError, SubmissionService
from wechat_tool.ui.app import run_app


logger = logging.getLogger(__name__)


def _format_output(result: Dict[str, Any]) -> str:
    try:
        return json.dumps(result, ensure_ascii=False, indent=2)
    except TypeError:
        return str(result)


def main() -> None:
    try:
        configure_logging()
        logger.info("开始提交申诉")
        cfg = read_submission_config()
        service = SubmissionService(cfg)
        result = service.submit()
        logger.info("提交流程完成: %s", result.get("add", {}))
        print(_format_output(result))
    except SubmissionError as exc:
        logger.error("业务异常: %s", exc)
        print(f"业务异常: {exc}", file=sys.stderr)
        sys.exit(2)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("执行失败")
        print(f"执行失败: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

def main_gui() -> None:
    """图形界面入口。"""
    run_app()

