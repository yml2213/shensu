"""JSON 文件存储封装，提供原子读写与文件锁。"""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Generator, Optional

if os.name == "nt":  # pragma: no cover - Windows 特定
    import msvcrt  # type: ignore[attr-defined]
else:  # pragma: no cover - 非 Windows
    import fcntl  # type: ignore[attr-defined]

LOCK_SUFFIX = ".lock"


@contextmanager
def _file_lock(lock_path: Path) -> Generator[None, None, None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if os.name == "nt":  # pragma: no cover - Windows
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:  # pragma: no branch - Unix
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":  # pragma: no cover - Windows
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no branch - Unix
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class JSONStore:
    """封装 JSON 数据文件的读写，与锁配合保障原子性。"""

    def __init__(
        self,
        path: Path,
        default_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.path = path
        self.default_factory = default_factory or (lambda: {})
        self.lock_path = path.with_suffix(path.suffix + LOCK_SUFFIX)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Any:
        with _file_lock(self.lock_path):
            return self._read_without_lock()

    def save(self, data: Any) -> None:
        with _file_lock(self.lock_path):
            self._atomic_write(data)

    def update(self, mutator: Callable[[Any], Any]) -> Any:
        with _file_lock(self.lock_path):
            current = self._read_without_lock()
            updated = mutator(current)
            if updated is None:
                updated = current
            self._atomic_write(updated)
            return updated

    # 内部实现
    def _read_without_lock(self) -> Any:
        if not self.path.exists():
            data = self.default_factory()
            self._write_without_lock(data)
            return data
        text = self.path.read_text(encoding="utf-8")
        if not text.strip():
            data = self.default_factory()
            self._write_without_lock(data)
            return data
        return json.loads(text)

    def _atomic_write(self, data: Any) -> None:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.path.parent), prefix=self.path.name, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp_file:
                json.dump(data, tmp_file, ensure_ascii=False, indent=2)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            Path(tmp_path).replace(self.path)
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink(missing_ok=True)

    def _write_without_lock(self, data: Any) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
