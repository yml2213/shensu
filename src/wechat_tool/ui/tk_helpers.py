"""Tkinter 环境辅助方法。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable


def _candidates(name: str) -> Iterable[Path]:
    version = "8.6"
    prefixes = [Path(sys.prefix), Path(sys.base_prefix)]
    for prefix in prefixes:
        yield prefix / "lib" / f"{name}{version}"
    # 常见的 pyenv 目录
    pyenv_prefix = Path.home() / ".pyenv"
    if pyenv_prefix.exists():
        yield pyenv_prefix / "versions" / f"{sys.version_info.major}.{sys.version_info.minor}" / "lib" / f"{name}{version}"
    # macOS 系统框架路径
    framework_base = {
        "tcl": Path("/System/Library/Frameworks/Tcl.framework/Versions") / version / "Resources" / "Scripts",
        "tk": Path("/System/Library/Frameworks/Tk.framework/Versions") / version / "Resources" / "Scripts",
    }
    if name == "tcl":
        yield framework_base["tcl"]
    else:
        yield framework_base["tk"]
    # /Library 框架（部分机器）
    alt_framework = {
        "tcl": Path("/Library/Frameworks/Tcl.framework/Versions") / version / "Resources" / "Scripts",
        "tk": Path("/Library/Frameworks/Tk.framework/Versions") / version / "Resources" / "Scripts",
    }
    if name == "tcl":
        yield alt_framework["tcl"]
    else:
        yield alt_framework["tk"]


def ensure_tk_env() -> None:
    """若环境变量未设置，尝试自动查找 Tcl/Tk 库路径。"""
    if not os.environ.get("TCL_LIBRARY"):
        for path in _candidates("tcl"):
            if path.exists():
                os.environ["TCL_LIBRARY"] = str(path)
                break
    if not os.environ.get("TK_LIBRARY"):
        for path in _candidates("tk"):
            if path.exists():
                os.environ["TK_LIBRARY"] = str(path)
                break
