#!/usr/bin/env python3
"""提交申诉信息；功能与 submit_plea.js 等价，改写为 Python 版本。"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from dotenv import load_dotenv

# AES 参数需与前端保持一致
KEY = b"ebupt_1234567890"
IV = b"1234567890123456"
SIGN_SUFFIX = "91Bmzn$0$#brkNYX"


def _aes_cbc_pkcs7_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def encrypt_phone(plain_phone: str) -> str:
    payload = f"{plain_phone}${int(time.time() * 1000)}"
    cipher_bytes = _aes_cbc_pkcs7_encrypt(payload.encode("utf-8"), KEY, IV)
    enc = base64.b64encode(cipher_bytes).decode("ascii")
    return enc.replace("/", "_").replace("+", "-")


def encrypt_sign(payload: str) -> str:
    data = (payload + SIGN_SUFFIX).encode("utf-8")
    cipher_bytes = _aes_cbc_pkcs7_encrypt(data, KEY, IV)
    return base64.b64encode(cipher_bytes).decode("ascii")


def infer_ext(path_obj: Path) -> str:
    suffix = path_obj.suffix.lower().lstrip(".")
    if not suffix:
        return "jpg"
    if suffix in {"jpg", "jpeg", "png"}:
        return "jpg" if suffix == "jpg" else suffix
    return suffix


def build_filename(user_phone: str, file_path: Path, now: Optional[dt.datetime] = None) -> str:
    now = now or dt.datetime.now()
    ymd = now.strftime("%Y%m%d")
    ymd_hms = now.strftime("%Y%m%d%H%M%S")
    ms = f"{now.microsecond // 1000:03d}"
    digits = ''.join(ch for ch in (user_phone or "") if ch.isdigit())
    last4 = digits[-4:] if digits else "0000"
    ext = infer_ext(file_path)
    return f"{ymd}/{last4}_{ymd_hms}{ms}.{ext}"


class ShensuClient:
    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.cfg = cfg
        self.base = (cfg.get("base") or "https://www.securityeb.com/ktfsr").rstrip("/")
        self.file_path = Path(cfg.get("file_path", ""))
        self.ua_add = cfg.get("ua_add_plea") or (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_3 like Mac OS X) "
            "AppleWebKit/536.26 (KHTML, like Gecko) Mobile/10B329 MicroMessenger/5.0.1"
        )
        self.ua_upload = cfg.get("ua_upload") or (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 19_0 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.54(0x1800363a) NetType/WIFI Language/zh_CN"
        )

    def validate(self) -> None:
        required = [
            "openid",
            "complaint_phone",
            "user_phone",
            "company_id",
            "company_name",
            "plea_reason",
            "file_path",
            "base",
        ]
        missing = [key for key in required if not self.cfg.get(key)]
        if missing:
            raise ValueError(f"缺少必填参数: {', '.join(missing)}")
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {self.file_path}")

    def add_plea(self, client: httpx.Client) -> Dict[str, Any]:
        cfg = self.cfg
        filename = build_filename(cfg["user_phone"], self.file_path)
        plea_phone = encrypt_phone(cfg["complaint_phone"])
        plea_type = "2"
        sign_payload = (
            f"{cfg['openid']}{plea_type}{plea_phone}{cfg['company_id']}"
            f"{cfg['company_name']}{cfg['plea_reason']}{filename}"
        )
        sign = encrypt_sign(sign_payload)

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

        body = {
            "openid": cfg["openid"],
            "plea_type": plea_type,
            "plea_phone": plea_phone,
            "company_id": cfg["company_id"],
            "company_name": cfg["company_name"],
            "plea_reason": cfg["plea_reason"],
            "filename": filename,
            "sign": sign,
        }

        print("[debug] filename =", filename)
        print("[debug] plea_phone =", plea_phone)
        print("[debug] sign =", sign)

        resp = client.post(add_url, json=body, headers=headers, timeout=20.0)
        resp.raise_for_status()
        data = resp.json()
        print("[addPlea] 响应:", data)
        if isinstance(data, dict) and data.get("code") not in (None, 200):
            raise RuntimeError("[addPlea] 非成功 code，终止上传。")
        cfg["_last_filename"] = filename
        return data

    def upload(self, client: httpx.Client) -> Any:
        filename = self.cfg.get("_last_filename")
        if not filename:
            raise RuntimeError("未获取到 filename，无法上传。")
        upload_url = f"{self.base}/pleaphone/upload"
        headers = {
            "User-Agent": self.ua_upload,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "Origin": "https://www.securityeb.com",
            "Referer": "https://www.securityeb.com/?state=ebupt",
        }
        mime_type, _ = mimetypes.guess_type(str(self.file_path))
        mime_type = mime_type or "application/octet-stream"

        with self.file_path.open("rb") as fh:
            files = {"file": (self.file_path.name, fh, mime_type)}
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
            payload = resp.json()
        except ValueError:
            payload = resp.text
        print("[upload] 响应:", payload)
        return payload

    def run(self) -> None:
        self.validate()
        with httpx.Client() as client:
            self.add_plea(client)
            self.upload(client)


def read_config(argv: Optional[list[str]] = None) -> Dict[str, Any]:
    load_dotenv()
    parser = argparse.ArgumentParser(description="提交申诉信息")
    parser.add_argument("--openid")
    parser.add_argument("--complaint-phone", dest="complaint_phone")
    parser.add_argument("--user-phone", dest="user_phone")
    parser.add_argument("--company-id", dest="company_id")
    parser.add_argument("--company-name", dest="company_name")
    parser.add_argument("--plea-reason", dest="plea_reason")
    parser.add_argument("--file")
    parser.add_argument("--base")
    parser.add_argument("--ua-add-plea", dest="ua_add_plea")
    parser.add_argument("--ua-upload", dest="ua_upload")
    args = parser.parse_args(argv)
    env = os.environ

    cfg = {
        "openid": args.openid or env.get("OPENID"),
        "complaint_phone": args.complaint_phone or env.get("COMPLAINT_PHONE"),
        "user_phone": args.user_phone or env.get("USER_PHONE"),
        "company_id": args.company_id or env.get("COMPANY_ID"),
        "company_name": args.company_name or env.get("COMPANY_NAME"),
        "plea_reason": args.plea_reason or env.get("PLEA_REASON"),
        "file_path": args.file or env.get("FILE"),
        "base": args.base or env.get("BASE_URL") or "https://www.securityeb.com/ktfsr",
        "ua_add_plea": args.ua_add_plea or env.get("UA_ADD_PLEA"),
        "ua_upload": args.ua_upload or env.get("UA_UPLOAD"),
    }
    return cfg


def main() -> None:
    try:
        cfg = read_config()
        client = ShensuClient(cfg)
        client.run()
    except Exception as exc:  # noqa: BLE001
        print("执行失败:", exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
