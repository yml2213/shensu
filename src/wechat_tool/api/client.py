"""对外接口调用封装。"""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

DEFAULT_BASE = "https://www.securityeb.com/ktfsr"
DEFAULT_UA_ADD = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_3 like Mac OS X) "
    "AppleWebKit/536.26 (KHTML, like Gecko) Mobile/10B329 MicroMessenger/5.0.1"
)
DEFAULT_UA_UPLOAD = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 19_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.54(0x1800363a) NetType/WIFI Language/zh_CN"
)


class SubmissionApiClient:
    """封装申诉提交流程涉及的接口调用。"""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE,
        ua_add: Optional[str] = None,
        ua_upload: Optional[str] = None,
        timeout: float = 20.0,
    ) -> None:
        self.base = (base_url or DEFAULT_BASE).rstrip("/")
        self.ua_add = ua_add or DEFAULT_UA_ADD
        self.ua_upload = ua_upload or DEFAULT_UA_UPLOAD
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    def _ensure_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client()
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "SubmissionApiClient":
        self._ensure_client()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def add_plea(self, body: Dict[str, Any]) -> Dict[str, Any]:
        client = self._ensure_client()
        add_url = f"{self.base}/pleaphone/addPlea"
        headers = {
            "User-Agent": self.ua_add,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,fr;q=0.8,de;q=0.7,en;q=0.6",
            "Cache-Control": "no-cache",
            "Origin": "https://www.securityeb.com",
            "Pragma": "no-cache",
            "Referer": "https://www.securityeb.com/?state=ebupt",
        }
        resp = client.post(add_url, json=body, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def upload(self, filename: str, file_path: Path) -> Any:
        client = self._ensure_client()
        upload_url = f"{self.base}/pleaphone/upload"
        headers = {
            "User-Agent": self.ua_upload,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "Origin": "https://www.securityeb.com",
            "Referer": "https://www.securityeb.com/?state=ebupt",
        }
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"
        with file_path.open("rb") as fh:
            files = {"file": (file_path.name, fh, mime_type)}
            data = {"filename": filename}
            resp = client.post(
                upload_url,
                headers=headers,
                data=data,
                files=files,
                timeout=httpx.Timeout(30.0),
            )
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return resp.text
