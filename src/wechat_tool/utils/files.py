"""文件与路径相关的辅助函数。"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional


ALLOWED_IMAGE_SUFFIXES = {"jpg", "jpeg", "png"}


def infer_ext(path_obj: Path) -> str:
    """推断文件扩展名，不存在时默认 jpg。"""
    suffix = path_obj.suffix.lower().lstrip(".")
    if not suffix:
        return "jpg"
    if suffix in ALLOWED_IMAGE_SUFFIXES:
        return "jpg" if suffix == "jpg" else suffix
    return suffix


def build_filename(user_phone: str, file_path: Path, now: Optional[dt.datetime] = None) -> str:
    """根据手机号与当前时间生成远程存储所需的文件名。"""
    now = now or dt.datetime.now()
    ymd = now.strftime("%Y%m%d")
    ymd_hms = now.strftime("%Y%m%d%H%M%S")
    ms = f"{now.microsecond // 1000:03d}"
    digits = ''.join(ch for ch in (user_phone or "") if ch.isdigit())
    last4 = digits[-4:] if digits else "0000"
    ext = infer_ext(file_path)
    return f"{ymd}/{last4}_{ymd_hms}{ms}.{ext}"
