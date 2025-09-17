"""数据模型定义。"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"


def _now_str() -> str:
    return dt.datetime.now().strftime(ISO_FORMAT)


@dataclass
class Account:
    wechat_id: str
    display_name: str = ""
    phone: str = ""
    quota_date: str = ""
    quota_count: int = 0
    person_id: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now_str)
    updated_at: str = field(default_factory=_now_str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Account":
        return cls(
            wechat_id=data["wechat_id"],
            display_name=data.get("display_name", ""),
            phone=data.get("phone", ""),
            quota_date=data.get("quota_date", ""),
            quota_count=int(data.get("quota_count", 0)),
            person_id=data.get("person_id"),
            events=list(data.get("events", [])),
            created_at=data.get("created_at", _now_str()),
            updated_at=data.get("updated_at", _now_str()),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PhoneQuota:
    phone: str
    date: str
    submit_count: int = 0
    last_account_ids: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhoneQuota":
        return cls(
            phone=data["phone"],
            date=data.get("date", ""),
            submit_count=int(data.get("submit_count", 0)),
            last_account_ids=list(data.get("last_account_ids", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Session:
    wechat_id: str
    login_code: str
    expired_at: str
    last_fetch_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        return cls(
            wechat_id=data["wechat_id"],
            login_code=data.get("login_code", ""),
            expired_at=data.get("expired_at", ""),
            last_fetch_at=data.get("last_fetch_at", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PersonProfile:
    person_id: str
    name: str
    phone: str
    reason: str = ""
    photo_paths: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_str)
    updated_at: str = field(default_factory=_now_str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonProfile":
        return cls(
            person_id=data["person_id"],
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            reason=data.get("reason", ""),
            photo_paths=list(data.get("photo_paths", [])),
            meta=dict(data.get("meta", {})),
            created_at=data.get("created_at", _now_str()),
            updated_at=data.get("updated_at", _now_str()),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MediaAsset:
    path: str
    checksum: Optional[str] = None
    uploaded: bool = False
    created_at: str = field(default_factory=_now_str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaAsset":
        return cls(
            path=data["path"],
            checksum=data.get("checksum"),
            uploaded=bool(data.get("uploaded", False)),
            created_at=data.get("created_at", _now_str()),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
