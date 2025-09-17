"""微信登录相关接口封装。"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

import httpx

from .client import KTFSR_BASE, WECHAT_BASE

logger = logging.getLogger(__name__)

APP_ID = "wxe4a8657e84049860"
AUTH_URL = "https://www.securityeb.com"
AUTHORIZE_ENDPOINT = "http://gee.myds.me:8055/api/OfficialAccounts/OauthAuthorize"
DEFAULT_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 19_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.54(0x1800363a) NetType/WIFI Language/zh_CN"
)


class LoginApiError(RuntimeError):
    """封装接口调用异常。"""


class LoginApiClient:
    """对接授权、获取 openid、短信发送与绑定接口。"""

    def __init__(self, cookie: Optional[str] = None, timeout: float = 20.0) -> None:
        self.cookie = cookie
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def authorize(self, wxid: str) -> Dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie
        payload = {"Appid": APP_ID, "Url": AUTH_URL, "Wxid": wxid}
        resp = self._client.post(AUTHORIZE_ENDPOINT, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("Success"):
            raise LoginApiError(f"authorize 失败: {data}")
        return data

    def extract_code(self, authorize_response: Dict[str, Any]) -> str:
        redirect = authorize_response.get("Data", {}).get("redirectUrl")
        if not redirect:
            raise LoginApiError("authorize 响应缺少 redirectUrl")
        parsed = urlparse(redirect)
        params = parse_qs(parsed.query)
        code = params.get("code", [""])[0]
        if not code:
            raise LoginApiError("redirectUrl 未包含 code 参数")
        return code

    def fetch_openid(self, code: str) -> Dict[str, Any]:
        url = f"{WECHAT_BASE}/wechatService/wechatServ/getUserInfo"
        headers = {
            "User-Agent": DEFAULT_UA,
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{AUTH_URL}/?code={code}&state=ebupt",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        }
        resp = self._client.get(url, params={"code": code}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 200:
            raise LoginApiError(f"获取 openid 失败: {data}")
        return data

    def send_sms(self, phone_cipher: str) -> Dict[str, Any]:
        url = f"{KTFSR_BASE}/sms/send/sendCode"
        headers = {
            "User-Agent": DEFAULT_UA,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "Origin": AUTH_URL,
            "Referer": f"{AUTH_URL}/?state=ebupt",
        }
        resp = self._client.post(url, json={"userphone": phone_cipher}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 200:
            raise LoginApiError(f"发送验证码失败: {data}")
        return data

    def bind_user(self, phone_cipher: str, sms_code_cipher: str, openid: str) -> Dict[str, Any]:
        url = f"{KTFSR_BASE}/user/bind/{phone_cipher}"
        headers = {
            "User-Agent": DEFAULT_UA,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "Origin": AUTH_URL,
            "Referer": f"{AUTH_URL}/?state=ebupt",
        }
        payload = {"op_type": "1", "code": sms_code_cipher, "openid": openid, "seq": ""}
        resp = self._client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 200:
            raise LoginApiError(f"绑定失败: {data}")
        return data

    def __enter__(self) -> "LoginApiClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        self.close()
