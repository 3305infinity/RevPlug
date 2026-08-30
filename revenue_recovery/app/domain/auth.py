from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    password_hash: str
    full_name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, "isoformat") else str(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class UserSession:
    session_token: str
    user_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def hash_password(password: str) -> str:
    """Hash a plain text password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if not password:
        raise ValueError("Password cannot be empty")
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"pbkdf2_sha256$100000${salt.hex()}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a PBKDF2-HMAC-SHA256 hash string."""
    if not password or not hashed or not hashed.startswith("pbkdf2_sha256$"):
        return False
    try:
        parts = hashed.split("$")
        if len(parts) != 4:
            return False
        _, iterations_str, salt_hex, key_hex = parts
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(derived_key, expected_key)
    except Exception:
        return False
