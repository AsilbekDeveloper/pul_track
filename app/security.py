"""Auth primitives: JWT issue/verify + Telegram Login Widget verification."""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

ALGORITHM = "HS256"


def create_access_token(user_id: int, telegram_user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tg": telegram_user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


def verify_telegram_login(data: dict) -> bool:
    """Validate the payload from Telegram's Login Widget.

    Algorithm (per Telegram docs): the check string is every field except
    `hash`, sorted and joined as "k=v" with newlines; HMAC-SHA256 keyed by
    SHA256(bot_token) must equal the received hash.
    """
    received_hash = data.get("hash")
    if not received_hash or not settings.telegram_bot_token:
        return False

    fields = {k: v for k, v in data.items() if k != "hash" and v is not None}
    check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
    computed = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, str(received_hash)):
        return False

    # Reject logins older than 24h.
    try:
        if time.time() - int(data.get("auth_date", 0)) > 86400:
            return False
    except (TypeError, ValueError):
        return False
    return True
