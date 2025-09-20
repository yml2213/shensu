"""微信登录/绑定流程服务。"""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..settings import (
    DATA_DIR,
    ensure_directories,
    load_app_config,
    save_app_config,
)
from ..storage.json_store import JSONStore
from ..storage.models import Session
from ..utils.crypto import encrypt_phone
from .account_service import AccountService
from ..api.login_client import LoginApiClient, LoginApiError
from .sms_providers import AutoSmsManager, SmsProviderError, SmsSession

logger = logging.getLogger(__name__)

SESSIONS_FILE = DATA_DIR / "sessions.json"


class LoginError(RuntimeError):
    """登录流程中的业务异常。"""


@dataclass
class LoginContext:
    """记录一次登录流程的临时上下文。"""

    wechat_id: str
    wxid: str
    phone: str
    phone_cipher: str
    authorize_code: str
    openid: str
    auto_session: Optional[SmsSession] = None


class LoginService:
    """串联授权、发送验证码、绑定手机号。"""

    def __init__(self, account_service: Optional[AccountService] = None) -> None:
        ensure_directories()
        self.config = load_app_config()
        login_cfg = self.config.get("login", {})
        auto_cfg = login_cfg.get("auto_sms")
        self.cookie = login_cfg.get("cookie")
        self.authorize_endpoint = login_cfg.get("authorize_endpoint") or "http://gee.myds.me:8005/api/OfficialAccounts/OauthAuthorize"
        self.auto_sms: Optional[AutoSmsManager] = None
        self.auto_sms_enabled = False
        if auto_cfg and auto_cfg.get("enabled"):
            self._reinitialize_auto(auto_cfg)
        self.account_service = account_service or AccountService()
        self.session_store = JSONStore(SESSIONS_FILE, default_factory=lambda: {"sessions": []})

    # 自动接码配置 -----------------------------------------------------
    def _reinitialize_auto(self, auto_cfg: Dict[str, Any]) -> None:
        try:
            self.auto_sms = AutoSmsManager(auto_cfg)
            self.auto_sms_enabled = bool(self.auto_sms.is_enabled())
        except SmsProviderError as exc:
            logger.error("初始化接码失败: %s", exc)
            self.auto_sms = None
            self.auto_sms_enabled = False
            auto_cfg["enabled"] = False
            save_app_config(self.config)

    def auto_mode_enabled(self) -> bool:
        return bool(self.auto_sms_enabled and self.auto_sms and self.auto_sms.is_enabled())

    def enable_auto_mode(self) -> bool:
        login_cfg = self.config.setdefault("login", {})
        auto_cfg = login_cfg.setdefault("auto_sms", {})
        auto_cfg["enabled"] = True
        save_app_config(self.config)
        self._reinitialize_auto(auto_cfg)
        return self.auto_mode_enabled()

    def disable_auto_mode(self) -> None:
        self.auto_sms_enabled = False
        login_cfg = self.config.setdefault("login", {})
        auto_cfg = login_cfg.setdefault("auto_sms", {})
        auto_cfg["enabled"] = False
        save_app_config(self.config)
        self.auto_sms = None

    def get_auto_config(self) -> Dict[str, Any]:
        return self.config.get("login", {}).get("auto_sms", {}).copy()

    def update_auto_config(self, *, token: str, username: str, password: str, project_id: str, operator: str, phone_num: str, scope: str, address: str) -> None:
        login_cfg = self.config.setdefault("login", {})
        auto_cfg = login_cfg.setdefault("auto_sms", {})
        auto_cfg.update(
            {
                "token": token.strip(),
                "username": username.strip(),
                "password": password.strip(),
                "project_id": project_id.strip(),
                "operator": operator.strip(),
                "phone_num": phone_num.strip(),
                "scope": scope.strip(),
                "address": address.strip(),
            }
        )
        auto_cfg["enabled"] = bool(
            auto_cfg["project_id"]
            and (auto_cfg["token"] or (auto_cfg["username"] and auto_cfg["password"]))
        )
        save_app_config(self.config)
        if auto_cfg["enabled"]:
            self._reinitialize_auto(auto_cfg)
        else:
            self.auto_sms = None
            self.auto_sms_enabled = False

    def get_project_id(self) -> str:
        auto_cfg = self.config.get("login", {}).get("auto_sms", {})
        return auto_cfg.get("project_id", "")

    # 登录流程 ---------------------------------------------------------
    def start_login(self, *, wechat_id: str, wxid: str, phone: Optional[str], mode: str) -> LoginContext:
        if not wxid.strip():
            raise LoginError("Wxid 不能为空")
        auto_session: Optional[SmsSession] = None
        real_phone = (phone or "").strip()
        if mode == "auto":
            if not self.auto_mode_enabled():
                raise LoginError("当前未配置自动接码 API")
            try:
                auto_session = self.auto_sms.acquire() if self.auto_sms else None
            except SmsProviderError as exc:
                raise LoginError(f"自动获取手机号失败: {exc}") from exc
            if not auto_session:
                raise LoginError("未能获取手机号，请检查接码配置")
            real_phone = auto_session.phone
        if not real_phone:
            raise LoginError("手机号不能为空")
        phone_cipher = encrypt_phone(real_phone)

        with LoginApiClient(cookie=self.cookie, authorize_endpoint=self.authorize_endpoint) as client:
            try:
                authorize_resp = client.authorize(wxid)
                code = client.extract_code(authorize_resp)
                openid_resp = client.fetch_openid(code)
                openid = openid_resp.get("data", {}).get("openid")
                if not openid:
                    raise LoginError("接口未返回 openid")
                client.send_sms(phone_cipher)
            except LoginApiError as exc:
                logger.exception("登录流程接口错误")
                if auto_session and self.auto_sms:
                    self.auto_sms.release(auto_session, success=False)
                raise LoginError(str(exc)) from exc

        context = LoginContext(
            wechat_id=wechat_id,
            wxid=wxid,
            phone=real_phone,
            phone_cipher=phone_cipher,
            authorize_code=code,
            openid=openid,
            auto_session=auto_session,
        )
        self._save_session(context)
        logger.info("已向 %s 发送验证码", real_phone)
        return context

    def obtain_auto_code(self, context: LoginContext) -> str:
        if not context.auto_session or not self.auto_sms:
            raise LoginError("当前未启用自动接码")
        try:
            code = self.auto_sms.wait_for_code(context.auto_session)
            logger.info("获取验证码成功: %s", code)
            return code
        except SmsProviderError as exc:
            self.auto_sms.release(context.auto_session, success=False)
            context.auto_session = None
            raise LoginError(f"自动获取验证码失败: {exc}") from exc

    def complete_login(self, context: LoginContext, sms_code: str) -> Dict[str, Any]:
        sms_code = (sms_code or "").strip()
        if not sms_code:
            raise LoginError("验证码不能为空")
        sms_cipher = encrypt_phone(sms_code)
        with LoginApiClient(cookie=self.cookie, authorize_endpoint=self.authorize_endpoint) as client:
            try:
                bind_resp = client.bind_user(context.phone_cipher, sms_cipher, context.openid)
            except LoginApiError as exc:
                logger.exception("绑定失败")
                if context.auto_session and self.auto_sms:
                    self.auto_sms.release(context.auto_session, success=False)
                    context.auto_session = None
                raise LoginError(str(exc)) from exc

        self.account_service.update_account(
            context.wechat_id,
            phone=context.phone,
            phone_bound=True,
            reset_quota=True,
        )
        self._update_session_after_bind(context)
        if context.auto_session and self.auto_sms:
            self.auto_sms.release(context.auto_session, success=True)
            context.auto_session = None
        logger.info("账号 %s 绑定成功", context.wechat_id)
        return bind_resp

    def abort_auto(self, context: LoginContext) -> None:
        if context.auto_session and self.auto_sms:
            self.auto_sms.release(context.auto_session, success=False)
            context.auto_session = None

    # session 记录 ----------------------------------------------------
    def _save_session(self, context: LoginContext) -> None:
        expires = (dt.datetime.now() + dt.timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S")
        payload = {
            "wechat_id": context.wechat_id,
            "login_code": context.authorize_code,
            "expired_at": expires,
            "last_fetch_at": dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "openid": context.openid,
        }

        def mutator(data: Dict[str, Any]) -> Dict[str, Any]:
            sessions = [Session.from_dict(item) for item in data.get("sessions", [])]
            for idx, sess in enumerate(sessions):
                if sess.wechat_id == context.wechat_id:
                    sessions[idx] = Session(**payload)
                    break
            else:
                sessions.append(Session(**payload))
            data["sessions"] = [sess.to_dict() for sess in sessions]
            return data

        self.session_store.update(mutator)

    def fetch_balance(self) -> str:
        auto_cfg = self.config.get("login", {}).get("auto_sms") or {}
        if not auto_cfg or not auto_cfg.get("enabled"):
            raise LoginError("请先配置并启用自动接码")
        try:
            if self.auto_sms and self.auto_sms.is_enabled():
                return self.auto_sms.get_balance()
            temp = AutoSmsManager(auto_cfg)
            return temp.get_balance()
        except SmsProviderError as exc:
            raise LoginError(f"查询余额失败: {exc}") from exc
        except Exception as exc:  # 兜底保护，防止意外异常导致 UI 崩溃
            raise LoginError(f"查询余额失败: {exc}") from exc

    def _update_session_after_bind(self, context: LoginContext) -> None:
        def mutator(data: Dict[str, Any]) -> Dict[str, Any]:
            sessions = [Session.from_dict(item) for item in data.get("sessions", [])]
            for idx, sess in enumerate(sessions):
                if sess.wechat_id == context.wechat_id:
                    sessions[idx] = Session(
                        wechat_id=sess.wechat_id,
                        login_code=sess.login_code,
                        expired_at=sess.expired_at,
                        last_fetch_at=dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        openid=context.openid,
                    )
                    break
            data["sessions"] = [sess.to_dict() for sess in sessions]
            return data

        self.session_store.update(mutator)
