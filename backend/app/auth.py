from __future__ import annotations

import hashlib
import hmac
import os
import uuid


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, hashed: str) -> bool:
    salt, digest = hashed.split("$", 1)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return hmac.compare_digest(candidate, digest)


def new_session_token() -> str:
    return str(uuid.uuid4())
