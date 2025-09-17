"""微信登录/绑定流程服务。"""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..settings import DATA_DIR, ensure_directories, load_app_config
from ..storage.json_store import JSONStore
from ..storage.models import Session
from ..utils.crypto import encrypt_phone
from .account_service import AccountService
from ..api.login_client import LoginApiClient, LoginApiError

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


class AutoCodeFetcher:
    """接码 API 的简单封装。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    def is_enabled(self) -> bool:
        return bool(self.config.get("enabled")) and bool(self.config.get("url"))

    def fetch(self, phone: str) -> str:
        import httpx

        if not self.is_enabled():
            raise LoginError("未配置接码 API，无法自动获取验证码")
        url = self.config["url"].format(phone=phone)
        method = self.config.get("method", "GET").upper()
        headers = self.config.get("headers", {})
        body_template = self.config.get("body_template")
        response_key = self.config.get("response_key", "code")

        with httpx.Client(timeout=15.0) as client:
            if method == "POST":
                body = None
                if body_template:
                    body = body_template.format(phone=phone)
                    content_type = headers.get("Content-Type", "application/json")
                    if content_type == "application/json" and isinstance(body, str):
                        import json

                        try:
                            body = json.loads(body)
                        except json.JSONDecodeError as exc:  # noqa: PERF203
                            raise LoginError("接码 API body_template 不是合法 JSON") from exc
                resp = client.post(url, json=body if isinstance(body, dict) else None, data=body if isinstance(body, str) else None, headers=headers)
            else:
                resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        value = data
        for part in response_key.split('.'):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                raise LoginError(f"接码 API 响应不包含 {response_key}")
        if not isinstance(value, str):
            raise LoginError("接码 API 返回的验证码格式不正确")
        return value.strip()


class LoginService:
    """串联授权、发送验证码、绑定手机号。"""

    def __init__(self, account_service: Optional[AccountService] = None) -> None:
        ensure_directories()
        config = load_app_config().get("login", {})
        self.cookie = config.get("cookie")
        self.auto_fetcher = AutoCodeFetcher(config.get("auto_sms"))
        self.account_service = account_service or AccountService()
        self.session_store = JSONStore(SESSIONS_FILE, default_factory=lambda: {"sessions": []})

    def start_login(self, *, wechat_id: str, wxid: str, phone: str) -> LoginContext:
        phone = phone.strip()
        if not phone:
            raise LoginError("手机号不能为空")
        if not wxid.strip():
            raise LoginError("Wxid 不能为空")
        phone_cipher = encrypt_phone(phone)

        with LoginApiClient(cookie=self.cookie) as client:
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
                raise LoginError(str(exc)) from exc

        context = LoginContext(
            wechat_id=wechat_id,
            wxid=wxid,
            phone=phone,
            phone_cipher=phone_cipher,
            authorize_code=code,
            openid=openid,
        )
        self._save_session(context)
        return context

    def fetch_auto_code(self, phone: str) -> str:
        return self.auto_fetcher.fetch(phone)

    def complete_login(self, context: LoginContext, sms_code: str) -> Dict[str, Any]:
        sms_code = sms_code.strip()
        if not sms_code:
            raise LoginError("验证码不能为空")
        sms_cipher = encrypt_phone(sms_code)
        with LoginApiClient(cookie=self.cookie) as client:
            try:
                bind_resp = client.bind_user(context.phone_cipher, sms_cipher, context.openid)
            except LoginApiError as exc:
                logger.exception("绑定失败")
                raise LoginError(str(exc)) from exc

        self.account_service.update_account(
            context.wechat_id,
            phone=context.phone,
            reset_quota=True,
        )
        self._update_session_after_bind(context)
        return bind_resp

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
            updated = False
            for idx, sess in enumerate(sessions):
                if sess.wechat_id == context.wechat_id:
                    sessions[idx] = Session(**payload)
                    updated = True
                    break
            if not updated:
                sessions.append(Session(**payload))
            data["sessions"] = [sess.to_dict() for sess in sessions]
            return data

        self.session_store.update(mutator)

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
