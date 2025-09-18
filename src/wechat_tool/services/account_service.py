"""账号管理服务，实现账号 CRUD 与持久化。"""
from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import List, Optional

from ..settings import DATA_DIR, ensure_directories
from ..storage.json_store import JSONStore
from ..storage.models import Account

ACCOUNTS_FILE = DATA_DIR / "accounts.json"
SUBMISSIONS_FILE = DATA_DIR / "submissions.json"


def _now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


class AccountExistsError(RuntimeError):
    """重复创建账号时抛出。"""


class AccountNotFoundError(RuntimeError):
    """找不到账号记录时抛出。"""


class AccountService:
    """封装账号的增删改查操作。"""

    def __init__(self) -> None:
        ensure_directories()
        self.store = JSONStore(ACCOUNTS_FILE, default_factory=lambda: {"accounts": []})
        self.submission_store = JSONStore(SUBMISSIONS_FILE, default_factory=lambda: {"submissions": []})

    def list_accounts(self) -> List[Account]:
        data = self.store.load()
        rows = data.get("accounts", [])
        return [Account.from_dict(row) for row in rows]

    def create_account(
        self,
        wechat_id: str,
        display_name: str = "",
        phone: str = "",
    ) -> Account:
        wechat_id = wechat_id.strip()
        if not wechat_id:
            raise ValueError("wechat_id 不能为空")
        accounts = self.list_accounts()
        if any(acc.wechat_id == wechat_id for acc in accounts):
            raise AccountExistsError(f"账号 {wechat_id} 已存在")
        now = _now_str()
        account = Account(
            wechat_id=wechat_id,
            display_name=display_name.strip(),
            phone=phone.strip(),
            quota_date="",
            quota_count=0,
            created_at=now,
            updated_at=now,
        )
        accounts.append(account)
        self._save(accounts)
        return account

    def update_account(
        self,
        wechat_id: str,
        display_name: Optional[str] = None,
        phone: Optional[str] = None,
        *,
        reset_quota: bool = False,
    ) -> Account:
        accounts = self.list_accounts()
        display_val = display_name.strip() if isinstance(display_name, str) else None
        phone_val = phone.strip() if isinstance(phone, str) else None
        for idx, acc in enumerate(accounts):
            if acc.wechat_id == wechat_id:
                quota_date = "" if reset_quota else acc.quota_date
                quota_count = 0 if reset_quota else acc.quota_count
                updated = replace(
                    acc,
                    display_name=display_val if display_val is not None else acc.display_name,
                    phone=phone_val if phone_val is not None else acc.phone,
                    quota_date=quota_date,
                    quota_count=quota_count,
                    updated_at=_now_str(),
                )
                accounts[idx] = updated
                self._save(accounts)
                return updated
        raise AccountNotFoundError(f"账号 {wechat_id} 不存在")

    def delete_account(self, wechat_id: str) -> None:
        accounts = self.list_accounts()
        filtered = [acc for acc in accounts if acc.wechat_id != wechat_id]
        if len(filtered) == len(accounts):
            raise AccountNotFoundError(f"账号 {wechat_id} 不存在")
        self._save(filtered)

    def record_submission(self, wechat_id: str) -> Account:
        """在提交完成后，按天累加账号的提交次数。"""
        today = dt.datetime.now().strftime("%Y-%m-%d")
        accounts = self.list_accounts()
        for idx, acc in enumerate(accounts):
            if acc.wechat_id == wechat_id:
                count = acc.quota_count + 1 if acc.quota_date == today else 1
                updated = replace(
                    acc,
                    quota_date=today,
                    quota_count=count,
                    updated_at=_now_str(),
                )
                accounts[idx] = updated
                self._save(accounts)
                return updated
        raise AccountNotFoundError(f"账号 {wechat_id} 不存在")

    def append_event(self, wechat_id: str, event: dict) -> Account:
        """为账号追加一条事件记录（例如提交成功）。"""
        accounts = self.list_accounts()
        for idx, acc in enumerate(accounts):
            if acc.wechat_id == wechat_id:
                events = list(acc.events)
                ev = dict(event)
                ev.setdefault("wechat_id", wechat_id)
                events.append(ev)
                updated = replace(
                    acc,
                    events=events,
                    updated_at=_now_str(),
                )
                accounts[idx] = updated
                self._save(accounts)
                # 追加到全局 submissions.json 文件，便于外部查阅
                try:
                    def mutator(data):
                        items = list(data.get("submissions", []))
                        items.append(ev)
                        data["submissions"] = items
                        return data
                    self.submission_store.update(mutator)
                except Exception:
                    pass
                return updated
        raise AccountNotFoundError(f"账号 {wechat_id} 不存在")

    def _save(self, accounts: List[Account]) -> None:
        payload = {"accounts": [acc.to_dict() for acc in accounts]}
        self.store.save(payload)
