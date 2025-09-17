"""配置读取与解析模块。"""
from __future__ import annotations

import argparse
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from .services.submission_service import SubmissionConfig


def _build_arg_parser() -> argparse.ArgumentParser:
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
    return parser


def read_submission_config(argv: Optional[list[str]] = None) -> SubmissionConfig:
    """读取命令行和环境变量，生成 SubmissionConfig。"""
    load_dotenv()
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    env = os.environ

    cfg_dict: Dict[str, Any] = {
        "openid": args.openid or env.get("OPENID"),
        "complaint_phone": args.complaint_phone or env.get("COMPLAINT_PHONE"),
        "user_phone": args.user_phone or env.get("USER_PHONE"),
        "company_id": args.company_id or env.get("COMPANY_ID"),
        "company_name": args.company_name or env.get("COMPANY_NAME"),
        "plea_reason": args.plea_reason or env.get("PLEA_REASON"),
        "file_path": args.file or env.get("FILE"),
        "base": args.base or env.get("BASE_URL"),
        "ua_add_plea": args.ua_add_plea or env.get("UA_ADD_PLEA"),
        "ua_upload": args.ua_upload or env.get("UA_UPLOAD"),
    }
    return SubmissionConfig.from_dict(cfg_dict)
