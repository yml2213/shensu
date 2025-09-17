"""加密相关工具函数，封装 AES-CBC 与业务字段加密逻辑。"""
from __future__ import annotations

import base64
import time
from typing import Final

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY: Final[bytes] = b"ebupt_1234567890"
IV: Final[bytes] = b"1234567890123456"
SIGN_SUFFIX: Final[str] = "91Bmzn$0$#brkNYX"


def _aes_cbc_pkcs7_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def encrypt_phone(plain_phone: str) -> str:
    """对手机号进行 AES-CBC 加密，返回 URL 安全的 Base64。"""
    payload = f"{plain_phone}${int(time.time() * 1000)}"
    cipher_bytes = _aes_cbc_pkcs7_encrypt(payload.encode("utf-8"), KEY, IV)
    enc = base64.b64encode(cipher_bytes).decode("ascii")
    return enc.replace("/", "_").replace("+", "-")


def encrypt_sign(payload: str) -> str:
    """签名加密，拼接后缀再进行 AES-CBC，返回 Base64。"""
    data = (payload + SIGN_SUFFIX).encode("utf-8")
    cipher_bytes = _aes_cbc_pkcs7_encrypt(data, KEY, IV)
    return base64.b64encode(cipher_bytes).decode("ascii")
