
# app/cryptog2.py
from __future__ import annotations
import os, base64, hashlib
from typing import Optional, Union
from cryptography.fernet import Fernet, InvalidToken

def generate_key() -> bytes:
    return Fernet.generate_key()

def encrypt_message(message: Union[str, bytes], key: bytes) -> Optional[bytes]:
    try:
        f = Fernet(key)
        return f.encrypt(message if isinstance(message, bytes) else message.encode('utf-8'))
    except Exception as e:
        print(f"[Erro] Criptografia: {e}"); return None

def decrypt_message(encrypted_message: bytes, key: bytes, as_text: bool = True) -> Union[str, bytes]:
    try:
        f = Fernet(key); data = f.decrypt(encrypted_message)
        return data.decode('utf-8') if as_text else data
    except (InvalidToken, Exception) as e:
        print(f"[Erro] Descriptografia: {e}")
        return b"" if not as_text else "[ERRO: token inválido]"

def generate_salt(length: int = 16) -> bytes:
    return os.urandom(length)

def derive_key_from_password(password: str, salt: bytes, iterations: int = 200_000) -> bytes:
    if not isinstance(password, str): password = str(password)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations, dklen=32)
    return base64.urlsafe_b64encode(dk)
