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
        self.operator = (config.get("operator") or "").strip()
        self.phone_num = (config.get("phone_num") or "").strip()
        self.scope = (config.get("scope") or "").strip()
        self.address = (config.get("address") or "").strip()
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
        if self.operator and self.operator != "0":
            params["operator"] = self.operator
        if self.phone_num:
            params["phone_num"] = self.phone_num
        if self.scope:
            params["scope"] = self.scope
        if self.address:
            params["address"] = self.address
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
            # 输出原始返回与解析后的 JSON（DEBUG 级别，通过 UI 控制显示）
            try:
                raw_text = resp.text
            except Exception:  # pragma: no cover - 保护性
                raw_text = "<unavailable>"
            logger.debug("椰子云 get_message 原始返回: %s", raw_text)
            data = resp.json()
            logger.debug("椰子云 get_message 解析数据: %s", data)
            message = data.get("message", "")
            if message == "ok":
                # 1) 先尝试顶层 code 字段
                from re import compile as _re_compile
                _pat = _re_compile(r"\b(\d{4,6})\b")
                top_code = data.get("code")
                if isinstance(top_code, str):
                    m = _pat.search(top_code)
                    if m:
                        code = m.group(1)
                        logger.info("椰子云获取验证码(顶层 code) %s", code)
                        return code
                # 2) 再尝试 data 列表/字典中的文本字段
                code = self._extract_code(data.get("data"))
                if code:
                    logger.info("椰子云获取验证码 %s", code)
                    return code
                last_error = "未获取到验证码"
            elif message in ("not_receive", "retry", "短信还未到达,请继续获取", "短信还未到达，请继续获取"):
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

    def get_balance(self) -> str:
        token = self._ensure_token()
        resp = self._request("/api/get_myinfo", params={"token": token})
        data = resp.json()
        if data.get("message") != "ok":
            raise SmsProviderError(f"获取余额失败: {data}")
        entries = data.get("data") or []
        if entries and isinstance(entries, list):
            money = entries[0].get("money")
        else:
            money = None
        if money is None:
            raise SmsProviderError("余额数据缺失")
        return str(money)

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
        """发起 GET 请求，内置主/备域名切换与异常封装。

        - 任何 httpx 异常（网络错误/超时/4xx/5xx）统一封装为 SmsProviderError，
          以避免异常冒泡导致上层 UI 崩溃。
        - 主域名失败后自动尝试备用域名（如已配置）。
        """
        url = f"{self.base_url}{path}"
        # Debug 输出请求（脱敏参数）
        masked = dict(params)
        if "token" in masked and masked["token"]:
            masked["token"] = masked["token"][:4] + "***"  # 仅保留前缀
        if "phone_num" in masked and masked["phone_num"]:
            p = str(masked["phone_num"])  # 只显示后 4 位
            masked["phone_num"] = ("*" * max(0, len(p) - 4)) + p[-4:]
        if "password" in masked and masked["password"]:
            masked["password"] = "***"
        logger.debug("HTTP GET %s params=%s", url, masked)

        try:
            resp = self._client.get(url, params=params)
            logger.debug("HTTP %s -> %s", url, resp.status_code)
            resp.raise_for_status()
            return resp
        except httpx.HTTPError as first_exc:  # 包含请求错误与状态码错误
            # 主域名失败后尝试备用域名
            if self.backup_url:
                backup_url = f"{self.backup_url}{path}"
                logger.warning("主域名请求失败，尝试备用域名 %s", backup_url)
                try:
                    resp2 = self._client.get(backup_url, params=params)
                    logger.debug("HTTP %s -> %s", backup_url, resp2.status_code)
                    resp2.raise_for_status()
                    return resp2
                except httpx.HTTPError as backup_exc:
                    logger.debug("备用域名也失败: %s", backup_exc)
                    raise SmsProviderError(f"椰子云请求失败: {backup_exc}") from backup_exc
            raise SmsProviderError(f"椰子云请求失败: {first_exc}") from first_exc

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
                    for key in ("sms", "message", "content", "sms_message", "modle"):
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

    def get_balance(self) -> str:
        if not self.provider:
            raise SmsProviderError("未配置自动接码提供商")
        if hasattr(self.provider, "get_balance"):
            return self.provider.get_balance()
        raise SmsProviderError("当前提供商不支持查询余额")
