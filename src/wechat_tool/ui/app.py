"""Tkinter 应用骨架。"""
from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk

import ttkbootstrap as tb

from ..logging_config import configure_logging
from ..settings import ensure_directories
from .tk_helpers import ensure_tk_env

logger = logging.getLogger(__name__)


class WechatToolApp(tb.Window):
    """主应用窗口，负责搭建基础布局。"""

    def __init__(self) -> None:
        super().__init__(title="微信申诉工具", themename="cosmo")
        self.geometry("960x600")
        self.resizable(True, True)
        self._build_widgets()

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main_frame = tb.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        sidebar = tb.Frame(main_frame, padding=10)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.columnconfigure(0, weight=1)

        tb.Label(sidebar, text="账号管理", font=("Helvetica", 14, "bold")).grid(row=0, column=0, pady=(0, 10))
        tb.Button(sidebar, text="添加账号", bootstyle="primary-outline").grid(row=1, column=0, sticky="ew", pady=5)
        tb.Button(sidebar, text="导入资料", bootstyle="info-outline").grid(row=2, column=0, sticky="ew", pady=5)
        tb.Button(sidebar, text="换绑手机号", bootstyle="warning-outline").grid(row=3, column=0, sticky="ew", pady=5)

        content = tb.Frame(main_frame, padding=10)
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        tb.Label(content, text="账号列表", font=("Helvetica", 14, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))

        tree = ttk.Treeview(content, columns=("wechat", "phone", "quota", "status"), show="headings", height=15)
        tree.heading("wechat", text="微信号")
        tree.heading("phone", text="手机号")
        tree.heading("quota", text="今日提交/上限")
        tree.heading("status", text="状态")
        tree.column("wechat", width=180)
        tree.column("phone", width=140)
        tree.column("quota", width=160)
        tree.column("status", width=200)
        tree.grid(row=1, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(content, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns")

        placeholder = [
            ("wx_demo1", "13800001111", "1/3", "可提交"),
            ("wx_demo2", "13800002222", "3/3", "今日额度用尽"),
        ]
        for item in placeholder:
            tree.insert("", tk.END, values=item)

        status_bar = tb.Label(self, text="准备就绪", anchor="w", bootstyle="secondary")
        status_bar.grid(row=1, column=0, sticky="ew")


def run_app() -> None:
    configure_logging()
    ensure_directories()
    ensure_tk_env()
    logger.info("启动 Tkinter 应用")
    app = WechatToolApp()
    app.mainloop()
