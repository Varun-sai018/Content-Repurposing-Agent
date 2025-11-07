"""User authentication helpers."""

from __future__ import annotations

import hashlib
import secrets
from typing import Optional

from . import db


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_password(stored_hash: str, password: str) -> bool:
    if "$" not in stored_hash:
        return False
    salt, _hash = stored_hash.split("$", 1)
    return _hash_password(password, salt) == stored_hash


def register_user(name: str, email: str, password: str) -> dict:
    existing = db.get_user_by_email(email)
    if existing:
        raise ValueError("An account with this email already exists.")

    password_hash = _hash_password(password)
    user_id = db.insert_user(name=name, email=email, password_hash=password_hash)
    user = db.get_user_by_id(user_id)
    if user:
        user_dict = dict(user)
        user_dict.pop("password_hash", None)
        return user_dict
    return {"id": user_id, "name": name, "email": email}


def authenticate_user(email: str, password: str) -> Optional[dict]:
    user = db.get_user_by_email(email)
    if not user:
        return None
    if not verify_password(user["password_hash"], password):
        return None
    user_dict = dict(user)
    user_dict.pop("password_hash", None)
    return user_dict


__all__ = ["register_user", "authenticate_user", "verify_password"]

