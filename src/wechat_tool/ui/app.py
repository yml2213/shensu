"""Tkinter 应用界面。"""
from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional
from pathlib import Path

import ttkbootstrap as tb

from ..logging_config import configure_logging
from ..services.account_service import AccountExistsError, AccountNotFoundError, AccountService
from ..services.login_service import LoginContext, LoginError, LoginService
from ..services.submission_service import (
    SubmissionConfig,
    SubmissionError,
    SubmissionService,
    check_sysphone_allowed,
)
from ..settings import ensure_directories, save_app_config
from .logger import attach_ui_logger
from .tk_helpers import ensure_tk_env

logger = logging.getLogger(__name__)


class AccountDialog(tb.Toplevel):
    """用于新增/编辑账号的表单对话框。"""

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        initial: Optional[dict[str, str]] = None,
        disable_wechat: bool = False,
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result: Optional[dict[str, str]] = None

        self._wechat_var = tk.StringVar(value=(initial or {}).get("wechat_id", ""))
        self._name_var = tk.StringVar(value=(initial or {}).get("display_name", ""))
        self._phone_var = tk.StringVar(value=(initial or {}).get("phone", ""))

        body = tb.Frame(self, padding=15)
        body.grid(row=0, column=0, sticky="nsew")

        tb.Label(body, text="微信号").grid(row=0, column=0, sticky="w")
        wechat_entry = tb.Entry(body, textvariable=self._wechat_var, width=28)
        wechat_entry.grid(row=0, column=1, padx=(10, 0), pady=5)
        if disable_wechat:
            wechat_entry.configure(state="disabled")

        tb.Label(body, text="备注 / 昵称").grid(row=1, column=0, sticky="w")
        tb.Entry(body, textvariable=self._name_var, width=28).grid(row=1, column=1, padx=(10, 0), pady=5)

        tb.Label(body, text="手机号").grid(row=2, column=0, sticky="w")
        tb.Entry(body, textvariable=self._phone_var, width=28).grid(row=2, column=1, padx=(10, 0), pady=5)

        btn_frame = tb.Frame(self)
        btn_frame.grid(row=1, column=0, pady=(0, 10))
        tb.Button(btn_frame, text="取消", command=self._on_cancel).grid(row=0, column=0, padx=5)
        tb.Button(btn_frame, text="保存", bootstyle="primary", command=self._on_save).grid(row=0, column=1, padx=5)

        self.bind("<Return>", lambda _e: self._on_save())
        self.bind("<Escape>", lambda _e: self._on_cancel())

        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_visibility()
        if not disable_wechat:
            wechat_entry.focus_set()
        else:
            body.focus_set()
        self.wait_window(self)

    def _on_save(self) -> None:
        wechat_id = self._wechat_var.get().strip()
        if not wechat_id:
            messagebox.showwarning("提示", "微信号不能为空", parent=self)
            return
        self.result = {
            "wechat_id": wechat_id,
            "display_name": self._name_var.get().strip(),
            "phone": self._phone_var.get().strip(),
        }
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()


class LoginDialog(tb.Toplevel):
    """登录/绑定流程参数采集。"""

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        default_wxid: str,
        default_phone: str,
        auto_enabled: bool,
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result: Optional[dict[str, str]] = None
        self._auto_enabled = auto_enabled

        self._wxid_var = tk.StringVar(value=default_wxid)
        self._phone_var = tk.StringVar(value=default_phone)
        self._mode_var = tk.StringVar(value="auto" if auto_enabled else "manual")

        body = tb.Frame(self, padding=15)
        body.grid(row=0, column=0, sticky="nsew")

        tb.Label(body, text="Wxid").grid(row=0, column=0, sticky="w")
        tb.Entry(body, textvariable=self._wxid_var, width=28).grid(row=0, column=1, padx=(10, 0), pady=5)

        tb.Label(body, text="手机号（自动模式可留空）").grid(row=1, column=0, sticky="w")
        tb.Entry(body, textvariable=self._phone_var, width=28).grid(row=1, column=1, padx=(10, 0), pady=5)

        mode_frame = tb.LabelFrame(body, text="验证码获取方式", padding=10)
        mode_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        auto_state = tk.NORMAL if auto_enabled else tk.DISABLED
        tb.Radiobutton(mode_frame, text="自动接码", variable=self._mode_var, value="auto", state=auto_state).grid(row=0, column=0, sticky="w")
        tb.Radiobutton(mode_frame, text="手动输入", variable=self._mode_var, value="manual").grid(row=0, column=1, sticky="w", padx=(10, 0))
        if not auto_enabled:
            tb.Label(mode_frame, text="未启用自动接码", bootstyle="danger").grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

        btn_frame = tb.Frame(self)
        btn_frame.grid(row=1, column=0, pady=(0, 10))
        tb.Button(btn_frame, text="取消", command=self._on_cancel).grid(row=0, column=0, padx=5)
        tb.Button(btn_frame, text="继续", bootstyle="primary", command=self._on_confirm).grid(row=0, column=1, padx=5)

        self.bind("<Return>", lambda _e: self._on_confirm())
        self.bind("<Escape>", lambda _e: self._on_cancel())

        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_visibility()
        body.focus_set()
        self.wait_window(self)

    def _on_confirm(self) -> None:
        wxid = self._wxid_var.get().strip()
        phone = self._phone_var.get().strip()
        mode = self._mode_var.get()
        if not wxid:
            messagebox.showwarning("提示", "Wxid 不能为空", parent=self)
            return
        if mode != "auto" and not phone:
            messagebox.showwarning("提示", "手机号不能为空", parent=self)
            return
        if mode == "auto" and not self._auto_enabled:
            messagebox.showwarning("提示", "当前未启用自动接码", parent=self)
            return
        self.result = {"wxid": wxid, "phone": phone, "mode": mode}
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()


class SubmissionDialog(tb.Toplevel):
    """提交申诉参数采集对话框。"""

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        default_openid: str,
        default_user_phone: str,
        *,
        default_complaint_phone: str = "",
        default_company_id: str = "",
        default_company_name: str = "",
        default_plea_reason: str = "",
        default_file_path: str = "",
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result: Optional[dict[str, str]] = None

        self._openid_var = tk.StringVar(value=default_openid)
        self._complaint_phone_var = tk.StringVar(value=default_complaint_phone)
        self._user_phone_var = tk.StringVar(value=default_user_phone)
        self._company_id_var = tk.StringVar(value=default_company_id)
        self._company_name_var = tk.StringVar(value=default_company_name)
        self._plea_reason_var = tk.StringVar(value=default_plea_reason)
        self._file_path_var = tk.StringVar(value=default_file_path)

        body = tb.Frame(self, padding=15)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)

        def add_row(r: int, text: str, widget: tk.Widget) -> None:
            tb.Label(body, text=text).grid(row=r, column=0, sticky="w", padx=(0, 8), pady=4)
            widget.grid(row=r, column=1, sticky="ew", pady=4)

        # OpenID 只读，浅灰显示
        add_row(0, "OpenID", tb.Entry(body, textvariable=self._openid_var, state="readonly", bootstyle="secondary"))
        # 用户手机号只读，浅灰显示（置于顶部）
        add_row(1, "用户手机号", tb.Entry(body, textvariable=self._user_phone_var, state="readonly", bootstyle="secondary"))
        # 申诉手机号 + 检测结果（放在用户手机号之后）
        self._phone_check_var = tk.StringVar(value="待检测")
        phone_row = tb.Frame(body)
        phone_row.columnconfigure(0, weight=1)
        phone_entry = tb.Entry(phone_row, textvariable=self._complaint_phone_var)
        phone_entry.grid(row=0, column=0, sticky="ew")
        self._phone_check_label = tb.Label(phone_row, textvariable=self._phone_check_var, bootstyle="secondary")
        self._phone_check_label.grid(row=0, column=1, padx=(8, 0))
        # 失去焦点时自动检测
        phone_entry.bind("<FocusOut>", lambda _e: self._check_phone_async())
        add_row(2, "申诉手机号", phone_row)
        add_row(3, "公司ID", tb.Entry(body, textvariable=self._company_id_var))
        add_row(4, "公司名称", tb.Entry(body, textvariable=self._company_name_var))
        add_row(5, "申诉理由", tb.Entry(body, textvariable=self._plea_reason_var))

        file_row = tb.Frame(body)
        file_row.columnconfigure(0, weight=1)
        tb.Entry(file_row, textvariable=self._file_path_var).grid(row=0, column=0, sticky="ew")
        tb.Button(file_row, text="选择文件", command=self._on_choose_file).grid(row=0, column=1, padx=(8, 0))
        add_row(6, "证明文件", file_row)

        btns = tb.Frame(self)
        btns.grid(row=1, column=0, pady=(0, 10))
        tb.Button(btns, text="取消", command=self._on_cancel).grid(row=0, column=0, padx=5)
        tb.Button(btns, text="提交", bootstyle="primary", command=self._on_confirm).grid(row=0, column=1, padx=5)

        self.bind("<Return>", lambda _e: self._on_confirm())
        self.bind("<Escape>", lambda _e: self._on_cancel())

        self._last_checked_phone: Optional[str] = None
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_visibility()
        self._place_center_lower()
        body.focus_set()
        self.wait_window(self)

    def _on_choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择证明文件",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png"), ("所有文件", "*.*")],
        )
        if path:
            self._file_path_var.set(path)

    def _place_center_lower(self) -> None:
        """在父窗口中心偏下位置显示对话框。"""
        try:
            self.update_idletasks()
            mw = self.master.winfo_width() if self.master else self.winfo_screenwidth()
            mh = self.master.winfo_height() if self.master else self.winfo_screenheight()
            mx = self.master.winfo_rootx() if self.master else 0
            my = self.master.winfo_rooty() if self.master else 0
            w = self.winfo_reqwidth()
            h = self.winfo_reqheight()
            x = mx + max(0, (mw - w) // 2)
            y = my + max(0, int((mh - h) * 0.6))  # 居中偏下
            self.geometry(f"+{x}+{y}")
        except Exception:  # noqa: BLE001
            pass

    def _check_phone_async(self) -> None:
        phone = self._complaint_phone_var.get().strip()
        if not phone:
            self._phone_check_var.set("待检测")
            try:
                self._phone_check_label.configure(bootstyle="secondary")
            except Exception:
                pass
            return
        if getattr(self, "_last_checked_phone", None) == phone:
            return
        self._phone_check_var.set("检测中...")
        try:
            self._phone_check_label.configure(bootstyle="info")
        except Exception:
            pass
        import threading

        def worker(p: str) -> None:
            allowed = check_sysphone_allowed(p)
            def update():
                self._last_checked_phone = p
                self._phone_check_var.set("可提交" if allowed else "不可提交")
                try:
                    self._phone_check_label.configure(bootstyle=("success" if allowed else "danger"))
                except Exception:
                    pass
            self.after(0, update)

        threading.Thread(target=worker, args=(phone,), daemon=True).start()

    def _on_confirm(self) -> None:
        vals = {
            "openid": self._openid_var.get().strip(),
            "complaint_phone": self._complaint_phone_var.get().strip(),
            "user_phone": self._user_phone_var.get().strip(),
            "company_id": self._company_id_var.get().strip(),
            "company_name": self._company_name_var.get().strip(),
            "plea_reason": self._plea_reason_var.get().strip(),
            "file_path": self._file_path_var.get().strip(),
        }
        missing = [k for k, v in vals.items() if not v]
        if missing:
            messagebox.showwarning("提示", f"请填写完整: {', '.join(missing)}", parent=self)
            return
        try:
            if not Path(vals["file_path"]).exists():
                messagebox.showwarning("提示", "选择的文件不存在", parent=self)
                return
        except Exception:
            messagebox.showwarning("提示", "文件路径无效", parent=self)
            return
        self.result = vals
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()

    


class WechatToolApp(tb.Window):
    """主应用窗口。"""

    OPERATOR_CHOICES = [
        ("默认", "0"),
        ("移动", "1"),
        ("联通", "2"),
        ("电信", "3"),
        ("实卡", "4"),
        ("虚卡", "5"),
    ]

    def __init__(self) -> None:
        super().__init__(title="微信申诉工具", themename="cosmo")
        self.geometry("1080x680")
        self.resizable(True, True)

        self.account_service = AccountService()
        self.login_service = LoginService(self.account_service)
        self.status_var = tk.StringVar(value="准备就绪")
        self.tree: Optional[ttk.Treeview] = None
        self.log_text: Optional[tk.Text] = None
        self.login_button: Optional[tb.Button] = None
        self.config_frame: Optional[tk.Misc] = None
        self.save_cfg_btn: Optional[tb.Button] = None
        self.show_auto_config_var = tk.BooleanVar(value=False)
        # 日志级别控制变量，默认取当前根 logger 的级别
        current_level_name = logging.getLevelName(logging.getLogger().getEffectiveLevel())
        if not isinstance(current_level_name, str):
            current_level_name = "INFO"
        self.log_level_var = tk.StringVar(value=current_level_name)

        auto_cfg = self.login_service.get_auto_config()
        self.use_auto_var = tk.BooleanVar(value=self.login_service.auto_mode_enabled())
        self.yzy_token_var = tk.StringVar(value=auto_cfg.get("token", ""))
        self.yzy_user_var = tk.StringVar(value=auto_cfg.get("username", ""))
        self.yzy_pass_var = tk.StringVar(value=auto_cfg.get("password", ""))
        self.yzy_project_var = tk.StringVar(value=auto_cfg.get("project_id", ""))
        operator_code = auto_cfg.get("operator", "0")
        self.yzy_operator_var = tk.StringVar(value=self._operator_code_to_label(operator_code))
        self.yzy_phone_num_var = tk.StringVar(value=auto_cfg.get("phone_num", ""))
        self.yzy_scope_var = tk.StringVar(value=auto_cfg.get("scope", ""))
        self.yzy_address_var = tk.StringVar(value=auto_cfg.get("address", ""))
        self.balance_var = tk.StringVar(value="余额：--")

        self._build_widgets()
        attach_ui_logger(self._append_log)
        self.refresh_accounts()
        self._refresh_balance()
        # 启动后自动置顶并聚焦
        self.after(80, self._bring_to_front)
        self.after(120, self._set_initial_focus)

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main_frame = tb.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        sidebar = tb.Frame(main_frame, padding=14)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.columnconfigure(0, weight=1)

        tb.Label(sidebar, text="账号管理", font=("Helvetica", 14, "bold"), anchor="center").grid(row=0, column=0, sticky="ew", pady=(0, 10))
        button_opts = {"sticky": "ew", "pady": 6}
        tb.Button(sidebar, text="添加账号", bootstyle="primary", command=self._on_add_account).grid(row=1, column=0, **button_opts)
        tb.Button(sidebar, text="编辑账号", bootstyle="info", command=self._on_edit_account).grid(row=2, column=0, **button_opts)
        tb.Button(sidebar, text="删除账号", bootstyle="danger", command=self._on_delete_account).grid(row=3, column=0, **button_opts)
        self.login_button = tb.Button(sidebar, text="微信登录/绑定", bootstyle="success", command=self._on_login_account)
        self.login_button.grid(row=4, column=0, **button_opts)
        tb.Button(sidebar, text="刷新列表", bootstyle="secondary", command=self.refresh_accounts).grid(row=5, column=0, **button_opts)

        tb.Separator(sidebar, orient="horizontal").grid(row=6, column=0, sticky="ew", pady=(12, 6))
        cfg_header = tb.Frame(sidebar)
        cfg_header.grid(row=7, column=0, sticky="ew")
        cfg_header.columnconfigure(0, weight=1)
        tb.Label(cfg_header, text="椰子云配置", font=("Helvetica", 12, "bold"), anchor="w").grid(row=0, column=0, sticky="w")
        tb.Checkbutton(
            cfg_header,
            text="显示配置",
            variable=self.show_auto_config_var,
            bootstyle="round-toggle",
            command=self._on_toggle_config_panel,
        ).grid(row=0, column=1, sticky="e")
        tb.Checkbutton(sidebar, text="启用自动取卡", variable=self.use_auto_var, bootstyle="round-toggle", command=self._on_toggle_auto).grid(row=8, column=0, sticky="w", pady=(4, 4))
        tb.Label(sidebar, textvariable=self.balance_var, bootstyle="info", anchor="w").grid(row=9, column=0, sticky="w", pady=(0, 8))

        config_frame = tb.Frame(sidebar)
        config_frame.grid(row=10, column=0, sticky="ew")
        config_frame.columnconfigure(0, weight=1)
        fields = [
            ("Token", self.yzy_token_var, "entry"),
            ("用户名", self.yzy_user_var, "entry"),
            ("密码", self.yzy_pass_var, "entry"),
            ("项目对接码", self.yzy_project_var, "entry"),
            ("运营商", self.yzy_operator_var, "combo"),
            ("指定号码", self.yzy_phone_num_var, "entry"),
            ("指定号段", self.yzy_scope_var, "entry"),
            ("归属地", self.yzy_address_var, "entry"),
        ]
        operator_labels = [label for label, _ in self.OPERATOR_CHOICES]
        for idx, (label_text, var, mode) in enumerate(fields):
            tb.Label(config_frame, text=label_text).grid(row=idx * 2, column=0, sticky="w", pady=(0, 2))
            if mode == "combo":
                combo = ttk.Combobox(config_frame, textvariable=var, values=operator_labels, state="readonly")
                combo.grid(row=idx * 2 + 1, column=0, sticky="ew", pady=(0, 6))
            else:
                # 椰子云密码使用掩码显示
                show_char = "*" if label_text == "密码" else None
                tb.Entry(config_frame, textvariable=var, width=22, show=show_char).grid(
                    row=idx * 2 + 1, column=0, sticky="ew", pady=(0, 6)
                )
        self.config_frame = config_frame
        self.save_cfg_btn = tb.Button(sidebar, text="保存配置", bootstyle="secondary", command=self._on_save_yzy_config)
        self.save_cfg_btn.grid(row=11, column=0, **button_opts)
        # 默认隐藏配置详情
        self._apply_config_panel_visibility()
        sidebar.rowconfigure(12, weight=1)

        # 主内容区域
        content = tb.Frame(main_frame, padding=14)
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=3)
        content.rowconfigure(2, weight=2)

        header = tb.Frame(content)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)
        tb.Label(header, text="账号列表", font=("Helvetica", 14, "bold")).grid(row=0, column=0, sticky="w")
        tb.Button(header, text="提交申诉", bootstyle="warning", command=self._on_submit_appeal).grid(row=0, column=1, sticky="e")

        style = ttk.Style(self)
        style.configure("Account.Treeview", rowheight=28, padding=0)
        # 不强制表头居中，由每列自行设置以匹配列内容
        style.configure("Account.Treeview.Heading")

        columns = ("wechat", "display_name", "phone", "quota", "status", "last_submit")
        tree = ttk.Treeview(content, columns=columns, show="headings", height=18, style="Account.Treeview")
        headings = {
            "wechat": ("微信号", 180, tk.W),
            "display_name": ("备注", 160, tk.W),
            "phone": ("手机号", 150, tk.CENTER),
            "quota": ("今日提交/上限", 170, tk.CENTER),
            "status": ("状态", 120, tk.CENTER),
            "last_submit": ("最近申诉手机号", 180, tk.CENTER),
        }
        for cid, (title, width, anchor) in headings.items():
            tree.heading(cid, text=title, anchor=anchor)
            tree.column(cid, width=width, anchor=anchor, stretch=False)
        tree.grid(row=1, column=0, sticky="nsew")
        tree.bind("<Double-1>", lambda _e: self._on_edit_account())
        self.tree = tree

        scrollbar = ttk.Scrollbar(content, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns")

        log_frame = tb.LabelFrame(content, text="运行日志", padding=8)
        log_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        log_frame.columnconfigure(0, weight=1)
        # 日志工具条（级别切换）
        toolbar = tb.Frame(log_frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        tb.Label(toolbar, text="日志级别:").grid(row=0, column=0, padx=(0, 6))
        level_box = ttk.Combobox(
            toolbar,
            textvariable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            state="readonly",
            width=10,
        )
        level_box.grid(row=0, column=1, sticky="w")
        level_box.bind(
            "<<ComboboxSelected>>",
            lambda _e: self._on_change_log_level(),
        )
        # 日志正文
        log_frame.rowconfigure(1, weight=1)
        self.log_text = tk.Text(log_frame, height=8, wrap="word", state="disabled")
        self.log_text.grid(row=1, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.grid(row=1, column=1, sticky="ns")

        status_bar = tb.Label(self, textvariable=self.status_var, anchor="w", bootstyle="secondary")
        status_bar.grid(row=1, column=0, sticky="ew")

    # 账号操作 ---------------------------------------------------------
    def refresh_accounts(self) -> None:
        if self.tree is None:
            return
        try:
            accounts = self.account_service.list_accounts()
        except Exception as exc:  # noqa: BLE001
            logger.exception("加载账号失败")
            messagebox.showerror("错误", f"加载账号失败: {exc}")
            return

        self.tree.delete(*self.tree.get_children())
        today = dt_today_string()
        from datetime import datetime
        for acc in accounts:
            quota = acc.quota_count if acc.quota_date == today else 0
            quota_text = f"{quota}/3"
            status = "已绑定手机号" if acc.phone else "未绑定手机号"
            # 最近提交信息（仅展示申诉手机号）
            last_text = "-"
            if acc.events:
                # 找到最后一条提交事件
                for ev in reversed(acc.events):
                    if isinstance(ev, dict) and ev.get("type") == "submission":
                        cphone = ev.get("complaint_phone") or "-"
                        last_text = cphone
                        break
            self.tree.insert(
                "",
                tk.END,
                values=(
                    acc.wechat_id,
                    acc.display_name or "-",
                    acc.phone or "-",
                    quota_text,
                    status,
                    last_text,
                ),
            )
        self._set_status(f"当前共 {len(accounts)} 个账号")

    def _on_add_account(self) -> None:
        dialog = AccountDialog(self, "添加账号")
        if not dialog.result:
            return
        try:
            account = self.account_service.create_account(
                dialog.result["wechat_id"],
                dialog.result.get("display_name", ""),
                dialog.result.get("phone", ""),
            )
        except AccountExistsError as exc:
            messagebox.showwarning("提示", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("创建账号失败")
            messagebox.showerror("错误", f"创建账号失败: {exc}")
            return
        self.refresh_accounts()
        messagebox.showinfo("成功", f"已添加账号 {account.wechat_id}")

    def _on_edit_account(self) -> None:
        wechat_id = self._get_selected_wechat()
        if not wechat_id:
            return
        accounts = {acc.wechat_id: acc for acc in self.account_service.list_accounts()}
        account = accounts.get(wechat_id)
        if account is None:
            messagebox.showerror("错误", "选中的账号不存在，请刷新")
            return
        dialog = AccountDialog(
            self,
            "编辑账号",
            initial={
                "wechat_id": account.wechat_id,
                "display_name": account.display_name,
                "phone": account.phone,
            },
            disable_wechat=True,
        )
        if not dialog.result:
            return
        try:
            updated = self.account_service.update_account(
                wechat_id,
                display_name=dialog.result.get("display_name"),
                phone=dialog.result.get("phone"),
            )
        except AccountNotFoundError as exc:
            messagebox.showerror("错误", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("更新账号失败")
            messagebox.showerror("错误", f"更新账号失败: {exc}")
            return
        self.refresh_accounts()
        messagebox.showinfo("成功", f"已更新账号 {updated.wechat_id}")

    def _on_delete_account(self) -> None:
        wechat_id = self._get_selected_wechat()
        if not wechat_id:
            return
        if not messagebox.askyesno("确认", f"确定要删除账号 {wechat_id} 吗？"):
            return
        try:
            self.account_service.delete_account(wechat_id)
        except AccountNotFoundError as exc:
            messagebox.showerror("错误", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("删除账号失败")
            messagebox.showerror("错误", f"删除账号失败: {exc}")
            return
        self.refresh_accounts()
        messagebox.showinfo("成功", f"账号 {wechat_id} 已删除")

    # 登录流程 ---------------------------------------------------------
    def _on_login_account(self) -> None:
        wechat_id = self._get_selected_wechat()
        if not wechat_id:
            return
        accounts = {acc.wechat_id: acc for acc in self.account_service.list_accounts()}
        account = accounts.get(wechat_id)
        if account is None:
            messagebox.showerror("错误", "选中的账号不存在，请刷新")
            return
        dialog = LoginDialog(
            self,
            title="微信登录/绑定",
            default_wxid=account.wechat_id,
            default_phone=account.phone,
            auto_enabled=self.login_service.auto_mode_enabled(),
        )
        if not dialog.result:
            return
        wxid = dialog.result["wxid"]
        phone = dialog.result["phone"]
        mode = dialog.result["mode"]

        self._set_login_button_enabled(False)
        try:
            context = self.login_service.start_login(
                wechat_id=wechat_id,
                wxid=wxid,
                phone=phone,
                mode=mode,
            )
        except LoginError as exc:
            self._set_login_button_enabled(True)
            messagebox.showerror("错误", str(exc))
            return

        self._append_log(f"账号 {wechat_id} 已发送验证码至 {context.phone}")
        if mode == "auto":
            self._append_log("正在等待验证码...")
            self._set_status("正在等待验证码...")
            thread = threading.Thread(
                target=self._auto_login_worker,
                args=(context, wechat_id),
                daemon=True,
            )
            thread.start()
            return

        sms_code = simpledialog.askstring("验证码", "请输入短信验证码", parent=self)
        if not sms_code:
            self.login_service.abort_auto(context)
            self._append_log("已取消绑定流程")
            self._set_login_button_enabled(True)
            self._set_status("准备就绪")
            return
        try:
            self.login_service.complete_login(context, sms_code)
        except LoginError as exc:
            messagebox.showerror("错误", str(exc))
            self._set_login_button_enabled(True)
            self._set_status("准备就绪")
            return

        self._set_login_button_enabled(True)
        self.refresh_accounts()
        self._refresh_balance()
        self._set_status("准备就绪")
        messagebox.showinfo("成功", f"账号 {wechat_id} 已完成绑定并重置额度")

    def _auto_login_worker(self, context: LoginContext, wechat_id: str) -> None:
        try:
            code = self.login_service.obtain_auto_code(context)
            self._log_async(f"已获取验证码 {code}")
            self.login_service.complete_login(context, code)
        except LoginError as exc:
            message = str(exc)
            self.after(0, lambda: self._handle_auto_failure(context, message))
            return
        self.after(0, lambda: self._handle_auto_success(wechat_id))

    def _handle_auto_failure(self, context: LoginContext, message: str) -> None:
        self.login_service.abort_auto(context)
        self._set_login_button_enabled(True)
        self._refresh_balance()
        self._set_status("准备就绪")
        self._append_log(message)
        messagebox.showerror("错误", message)

    def _handle_auto_success(self, wechat_id: str) -> None:
        self._set_login_button_enabled(True)
        self.refresh_accounts()
        self._refresh_balance()
        self._set_status("准备就绪")
        self._append_log(f"账号 {wechat_id} 自动绑定完成")
        messagebox.showinfo("成功", f"账号 {wechat_id} 已完成绑定并重置额度")

    # 自动接码配置 -----------------------------------------------------
    def _on_toggle_auto(self) -> None:
        enabled = self.use_auto_var.get()
        if enabled:
            if not self.login_service.enable_auto_mode():
                messagebox.showinfo("提示", "请先填写椰子云配置并保存")
                self.use_auto_var.set(False)
                self.balance_var.set("余额：--")
            else:
                self._refresh_balance()
        else:
            self.login_service.disable_auto_mode()
            self.balance_var.set("余额：--")

    def _on_save_yzy_config(self) -> None:
        operator_code = self._operator_label_to_code(self.yzy_operator_var.get())
        self.login_service.update_auto_config(
            token=self.yzy_token_var.get(),
            username=self.yzy_user_var.get(),
            password=self.yzy_pass_var.get(),
            project_id=self.yzy_project_var.get(),
            operator=operator_code,
            phone_num=self.yzy_phone_num_var.get(),
            scope=self.yzy_scope_var.get(),
            address=self.yzy_address_var.get(),
        )
        self.use_auto_var.set(self.login_service.auto_mode_enabled())
        self._refresh_balance()
        messagebox.showinfo("提示", "椰子云配置已保存")

    def _refresh_balance(self) -> None:
        auto_cfg = self.login_service.get_auto_config() or {}
        if not auto_cfg.get("enabled"):
            self.balance_var.set("余额：--")
            return
        try:
            balance = self.login_service.fetch_balance()
            self.balance_var.set(f"余额：{balance}")
        except LoginError as exc:
            logger.warning("查询余额失败: %s", exc)
            self.balance_var.set("余额：--")

    def _operator_code_to_label(self, code: str) -> str:
        for label, mapped in self.OPERATOR_CHOICES:
            if mapped == code:
                return label
        return self.OPERATOR_CHOICES[0][0]

    def _operator_label_to_code(self, label: str) -> str:
        for lbl, mapped in self.OPERATOR_CHOICES:
            if lbl == label:
                return mapped
        return self.OPERATOR_CHOICES[0][1]

    def _set_login_button_enabled(self, enabled: bool) -> None:
        if self.login_button is None:
            return
        state = tk.NORMAL if enabled else tk.DISABLED
        self.login_button.configure(state=state)

    def _log_async(self, message: str) -> None:
        self.after(0, lambda: self._append_log(message))

    # 工具方法 ---------------------------------------------------------
    def _get_selected_wechat(self) -> Optional[str]:
        if self.tree is None:
            return None
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一个账号")
            return None
        item_id = selection[0]
        values = self.tree.item(item_id, "values")
        return values[0] if values else None

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _append_log(self, message: str) -> None:
        if self.log_text is None:
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    

    def _bring_to_front(self) -> None:
        try:
            self.update_idletasks()
            self.deiconify()
            self.lift()
            self.focus_force()
            # 置顶一小段时间确保到前台，再恢复
            self.attributes("-topmost", True)
            self.after(300, lambda: self.attributes("-topmost", False))
        except Exception:  # noqa: BLE001
            pass

    def _on_toggle_config_panel(self) -> None:
        self._apply_config_panel_visibility()

    def _apply_config_panel_visibility(self) -> None:
        visible = bool(self.show_auto_config_var.get())
        if self.config_frame is None or self.save_cfg_btn is None:
            return
        if visible:
            self.config_frame.grid()
            self.save_cfg_btn.grid()
        else:
            self.config_frame.grid_remove()
            self.save_cfg_btn.grid_remove()

    def _get_openid_for(self, wechat_id: str) -> Optional[str]:
        try:
            data = self.login_service.session_store.load()  # type: ignore[attr-defined]
            sessions = data.get("sessions", [])
            for item in sessions:
                if item.get("wechat_id") == wechat_id:
                    return item.get("openid") or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("读取 openid 失败: %s", exc)
        return None

    def _on_submit_appeal(self) -> None:
        wechat_id = self._get_selected_wechat()
        if not wechat_id:
            return
        accounts = {acc.wechat_id: acc for acc in self.account_service.list_accounts()}
        account = accounts.get(wechat_id)
        if account is None:
            messagebox.showerror("错误", "选中的账号不存在，请刷新")
            return
        openid = self._get_openid_for(wechat_id) or ""
        if not openid:
            messagebox.showinfo("提示", "未找到 openid，请先完成登录/绑定流程")
            return
        # 载入上次的提交默认值
        sub_cfg = self.login_service.config.setdefault("submission", {})
        dialog = SubmissionDialog(
            self,
            title="提交申诉",
            default_openid=openid,
            default_user_phone=account.phone or sub_cfg.get("last_user_phone", ""),
            default_complaint_phone=sub_cfg.get("last_complaint_phone", ""),
            default_company_id=sub_cfg.get("default_company_id", ""),
            default_company_name=sub_cfg.get("default_company_name", ""),
            default_plea_reason=sub_cfg.get("default_plea_reason", ""),
            default_file_path=sub_cfg.get("last_file_path", ""),
        )
        if not dialog.result:
            return
        cfg = SubmissionConfig(
            openid=dialog.result["openid"],
            complaint_phone=dialog.result["complaint_phone"],
            user_phone=dialog.result["user_phone"],
            company_id=dialog.result["company_id"],
            company_name=dialog.result["company_name"],
            plea_reason=dialog.result["plea_reason"],
            file_path=Path(dialog.result["file_path"]),
        )
        try:
            service = SubmissionService(cfg)
            resp = service.submit()
        except SubmissionError as exc:
            logger.exception("提交申诉失败")
            messagebox.showerror("错误", f"提交失败: {exc}")
            self._append_log(f"提交失败: {exc}")
            return
        # 保存提交默认值，便于下次预填
        sub_cfg.update(
            {
                "last_complaint_phone": cfg.complaint_phone,
                "last_user_phone": cfg.user_phone,
                "default_company_id": cfg.company_id,
                "default_company_name": cfg.company_name,
                "default_plea_reason": cfg.plea_reason,
                "last_file_path": str(cfg.file_path),
            }
        )
        save_app_config(self.login_service.config)
        # 记录提交次数并刷新列表
        try:
            self.account_service.record_submission(wechat_id)
            # 追加事件明细
            from datetime import datetime
            event = {
                "type": "submission",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "wechat_id": wechat_id,
                "filename": resp.get("filename"),
                "complaint_phone": cfg.complaint_phone,
                "user_phone": cfg.user_phone,
                "company_id": cfg.company_id,
                "company_name": cfg.company_name,
                "plea_reason": cfg.plea_reason,
            }
            self.account_service.append_event(wechat_id, event)
            self.refresh_accounts()
        except Exception as exc:  # noqa: BLE001
            logger.warning("更新提交计数失败: %s", exc)
        self._append_log(
            f"提交成功: 文件 {resp.get('filename')}\nadd: {resp.get('add')}\nupload: {resp.get('upload')}"
        )
        messagebox.showinfo("成功", "申诉已提交")

    def _on_change_log_level(self) -> None:
        level_name = (self.log_level_var.get() or "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        logging.getLogger().setLevel(level)
        # 记录一条提示，方便确认
        self._append_log(f"已切换日志级别为 {level_name}")

    def _set_initial_focus(self) -> None:
        try:
            if self.tree is not None:
                self.tree.focus_set()
                return
            if self.login_button is not None:
                self.login_button.focus_set()
                return
            self.focus_force()
        except Exception:  # noqa: BLE001
            pass


def dt_today_string() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d")


def run_app() -> None:
    configure_logging()
    ensure_directories()
    ensure_tk_env()
    logger.info("启动 Tkinter 应用")
    app = WechatToolApp()
    app.mainloop()
