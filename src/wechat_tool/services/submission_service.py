"""申诉提交服务，将业务逻辑与接口调用解耦。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ..api.client import DEFAULT_BASE, SubmissionApiClient
from ..utils.crypto import encrypt_phone, encrypt_sign
from ..utils.files import build_filename


class SubmissionError(RuntimeError):
    """申诉流程中出现的业务异常。"""


@dataclass
class SubmissionConfig:
    openid: str
    complaint_phone: str
    user_phone: str
    company_id: str
    company_name: str
    plea_reason: str
    file_path: Path
    base: str = DEFAULT_BASE
    ua_add_plea: Optional[str] = None
    ua_upload: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubmissionConfig":
        raw_path = data.get("file_path")
        if not raw_path:
            raise SubmissionError("缺少 file_path 配置")
        file_path = Path(raw_path)
        return cls(
            openid=data["openid"],
            complaint_phone=data["complaint_phone"],
            user_phone=data["user_phone"],
            company_id=data["company_id"],
            company_name=data["company_name"],
            plea_reason=data["plea_reason"],
            file_path=file_path,
            base=data.get("base", DEFAULT_BASE),
            ua_add_plea=data.get("ua_add_plea"),
            ua_upload=data.get("ua_upload"),
        )


class SubmissionService:
    """封装申诉提交的完整流程。"""

    def __init__(self, config: SubmissionConfig) -> None:
        self.config = config

    def validate(self) -> None:
        cfg = self.config
        missing = [
            field
            for field in (
                "openid",
                "complaint_phone",
                "user_phone",
                "company_id",
                "company_name",
                "plea_reason",
                "file_path",
            )
            if not getattr(cfg, field)
        ]
        if missing:
            raise SubmissionError(f"缺少必填参数: {', '.join(missing)}")
        if not cfg.file_path.exists():
            raise SubmissionError(f"文件不存在: {cfg.file_path}")

    def _build_payload(self, filename: str) -> Dict[str, Any]:
        cfg = self.config
        plea_phone = encrypt_phone(cfg.complaint_phone)
        plea_type = "2"
        sign_payload = (
            f"{cfg.openid}{plea_type}{plea_phone}{cfg.company_id}"
            f"{cfg.company_name}{cfg.plea_reason}{filename}"
        )
        sign = encrypt_sign(sign_payload)
        return {
            "openid": cfg.openid,
            "plea_type": plea_type,
            "plea_phone": plea_phone,
            "company_id": cfg.company_id,
            "company_name": cfg.company_name,
            "plea_reason": cfg.plea_reason,
            "filename": filename,
            "sign": sign,
        }

    def submit(self, api_client: Optional[SubmissionApiClient] = None) -> Dict[str, Any]:
        """执行提交流程，返回 addPlea 与 upload 的响应。"""
        self.validate()
        cfg = self.config
        filename = build_filename(cfg.user_phone, cfg.file_path)
        body = self._build_payload(filename)

        should_close = False
        client = api_client
        if client is None:
            client = SubmissionApiClient(
                base_url=cfg.base,
                ua_add=cfg.ua_add_plea,
                ua_upload=cfg.ua_upload,
            )
            should_close = True

        try:
            add_resp = client.add_plea(body)
            code = add_resp.get("code") if isinstance(add_resp, dict) else None
            if code not in (None, 200):
                msg = add_resp.get("msg") if isinstance(add_resp, dict) else str(add_resp)
                raise SubmissionError(f"addPlea 返回异常: code={code}, msg={msg}")
            upload_resp = client.upload(filename, cfg.file_path)
            return {"add": add_resp, "upload": upload_resp, "filename": filename}
        finally:
            if should_close:
                client.close()
