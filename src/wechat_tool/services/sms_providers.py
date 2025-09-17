"""短信自动获取提供商实现。"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SmsSession:
    phone: str
    project_id: str
    token: str
    provider_data: Dict[str, Any] = field(default_factory=dict)


class SmsProviderError(RuntimeError):
    """短信提供商异常。"""


class BaseSmsProvider:
    def acquire_phone(self) -> SmsSession:  # pragma: no cover - 接口定义
        raise NotImplementedError

    def wait_for_code(self, session: SmsSession) -> str:  # pragma: no cover - 接口定义
        raise NotImplementedError

    def release_phone(self, session: SmsSession, blacklist: bool = False) -> None:  # pragma: no cover - 接口定义
        raise NotImplementedError


class YzySmsProvider(BaseSmsProvider):
    """椰子云短信平台集成。"""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.base_url = config.get("base_url", "http://api.sqhyw.net:90").rstrip("/")
        self.backup_url = config.get("backup_base_url", "http://api.nnanx.com:90").rstrip("/")
        self.username = config.get("username")
        self.password = config.get("password")
        self._token = config.get("token")
        self.project_id = config.get("project_id")
        self.poll_interval = float(config.get("poll_interval", 5))
        self.max_wait_seconds = float(config.get("max_wait_seconds", 120))
        self.min_remaining = int(config.get("min_remaining", 10))
        self.release_on_success = bool(config.get("release_on_success", True))
        self.release_on_failure = bool(config.get("release_on_failure", True))
        self.blacklist_on_failure = bool(config.get("blacklist_on_failure", False))
        if not self.project_id:
            raise SmsProviderError("请在 config.json 的 login.auto_sms.project_id 配置项目 ID 或专属对接码")
        self._client = httpx.Client(timeout=20.0)

    # 公共方法
    def acquire_phone(self) -> SmsSession:
        token = self._ensure_token()
        params = {"token": token, "project_id": self.project_id}
        resp = self._request("/api/get_mobile", params=params)
        data = resp.json()
        if data.get("message") != "ok":
            raise SmsProviderError(f"取号失败: {data}")
        phone = data.get("mobile")
        remaining = self._parse_remaining(data.get("1 分钟内剩余取卡数"))
        if remaining is not None and remaining < self.min_remaining:
            raise SmsProviderError("椰子云剩余取卡数过低，请稍后再试")
        if not phone:
            raise SmsProviderError("椰子云未返回手机号")
        logger.info("椰子云获取手机号 %s", phone)
        return SmsSession(phone=phone, project_id=self.project_id, token=token, provider_data={"base": self.base_url})

    def wait_for_code(self, session: SmsSession) -> str:
        deadline = time.time() + self.max_wait_seconds
        last_error: Optional[str] = None
        while time.time() < deadline:
            params = {
                "token": session.token,
                "project_id": session.project_id,
                "phone_num": session.phone,
            }
            resp = self._request("/api/get_message", params=params)
            data = resp.json()
            message = data.get("message", "")
            if message == "ok":
                code = self._extract_code(data.get("data"))
                if code:
                    logger.info("椰子云获取验证码 %s", code)
                    return code
                last_error = "未获取到验证码"
            elif message == "not_receive" or message == "retry":
                last_error = "短信尚未到达"
            else:
                last_error = f"拉取短信失败: {data}"
            time.sleep(self.poll_interval)
        raise SmsProviderError(last_error or "获取验证码超时")

    def release_phone(self, session: SmsSession, blacklist: bool = False) -> None:
        action = "/api/add_blacklist" if blacklist else "/api/free_mobile"
        params = {
            "token": session.token,
            "phone_num": session.phone,
        }
        if action.endswith("add_blacklist"):
            params["project_id"] = session.project_id
        else:
            params["project_id"] = session.project_id
        try:
            self._request(action, params=params)
        except Exception as exc:  # noqa: BLE001
            logger.warning("释放/拉黑手机号失败: %s", exc)

    # 帮助方法
    def _ensure_token(self) -> str:
        if self._token:
            return self._token
        if not self.username or not self.password:
            raise SmsProviderError("请提供椰子云 token 或用户名/密码")
        params = {"username": self.username, "password": self.password}
        resp = self._request("/api/logins", params=params)
        data = resp.json()
        token = data.get("token")
        if not token:
            raise SmsProviderError(f"椰子云登录失败: {data}")
        self._token = token
        logger.info("椰子云登录成功，获取 token")
        return token

    def _request(self, path: str, params: Dict[str, Any]) -> httpx.Response:
        url = f"{self.base_url}{path}"
        resp = self._client.get(url, params=params)
        if resp.status_code >= 500 and self.backup_url:
            backup_url = f"{self.backup_url}{path}"
            logger.warning("主域名请求失败，尝试备用域名 %s", backup_url)
            resp = self._client.get(backup_url, params=params)
        resp.raise_for_status()
        return resp

    @staticmethod
    def _parse_remaining(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(str(value))
        except ValueError:
            return None

    @staticmethod
    def _extract_code(data: Any) -> Optional[str]:
        if not data:
            return None
        texts: list[str] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    texts.append(item)
                elif isinstance(item, dict):
                    for key in ("sms", "message", "content", "sms_message"):
                        val = item.get(key)
                        if isinstance(val, str):
                            texts.append(val)
        elif isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, str):
                    texts.append(val)
        pattern = re.compile(r"\b(\d{4,6})\b")
        for text in texts:
            match = pattern.search(text)
            if match:
                return match.group(1)
        return None


class AutoSmsManager:
    """自动接码管理器。"""

    def __init__(self, config: Optional[Dict[str, Any]]) -> None:
        self.provider: Optional[BaseSmsProvider] = None
        if config and config.get("enabled"):
            provider_name = (config.get("provider") or "yzy").lower()
            if provider_name == "yzy":
                try:
                    self.provider = YzySmsProvider(config)
                except SmsProviderError as exc:
                    logger.error("初始化椰子云提供商失败: %s", exc)
                    raise
            else:
                raise SmsProviderError(f"暂不支持的接码提供商: {provider_name}")

    def is_enabled(self) -> bool:
        return self.provider is not None

    def acquire(self) -> SmsSession:
        if not self.provider:
            raise SmsProviderError("未配置自动接码提供商")
        return self.provider.acquire_phone()

    def wait_for_code(self, session: SmsSession) -> str:
        if not self.provider:
            raise SmsProviderError("未配置自动接码提供商")
        return self.provider.wait_for_code(session)

    def release(self, session: SmsSession, *, success: bool) -> None:
        if not self.provider:
            return
        provider = self.provider
        blacklist = getattr(provider, "blacklist_on_failure", False)
        if success:
            if getattr(provider, "release_on_success", True):
                provider.release_phone(session, blacklist=False)
        else:
            release_required = getattr(provider, "release_on_failure", True)
            if release_required:
                provider.release_phone(session, blacklist=blacklist)
