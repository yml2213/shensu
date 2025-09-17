"""UI 日志输出工具。"""
from __future__ import annotations

import logging
from logging import Handler, LogRecord
from typing import Callable

Callback = Callable[[str], None]


class TkTextHandler(Handler):
    """将日志写入 Tk 文本组件回调。"""

    def __init__(self, callback: Callback) -> None:
        super().__init__()
        self.callback = callback

    def emit(self, record: LogRecord) -> None:  # noqa: D401
        try:
            msg = self.format(record)
            self.callback(msg)
        except Exception:  # noqa: BLE001
            self.handleError(record)


def attach_ui_logger(callback: Callback) -> logging.Logger:
    """将回调附加到根日志，返回 logger。"""
    handler = TkTextHandler(callback)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S"))
    logger = logging.getLogger()
    logger.addHandler(handler)
    return logger
