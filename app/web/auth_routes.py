"""Auth endpoints: Telegram Login Widget, dev-login (local), and /me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import User
from app.security import create_access_token, verify_telegram_login
from app.services.users import get_or_create_user
from app.web.auth import get_current_user

router = APIRouter(prefix="/api/auth")


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "telegram_user_id": user.telegram_user_id,
    }


@router.post("/telegram")
async def telegram_login(
    payload: dict,
    session: AsyncSession = Depends(get_session),
):
    """Verify the Telegram Login Widget payload and return a JWT."""
    if not verify_telegram_login(payload):
        raise HTTPException(status_code=401, detail="Telegram tasdiqlash muvaffaqiyatsiz")
    try:
        tg_id = int(payload["id"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="id yo'q")

    name = payload.get("first_name") or payload.get("username")
    user = await get_or_create_user(session, tg_id, name)
    await session.commit()
    return {"access_token": create_access_token(user.id, tg_id), "user": _user_dict(user)}


class DevLogin(BaseModel):
    telegram_user_id: int
    name: str | None = None


@router.post("/dev-login")
async def dev_login(
    payload: DevLogin,
    session: AsyncSession = Depends(get_session),
):
    """Local-only shortcut to get a token without the Telegram widget.

    Handy for testing the dashboard on localhost (the widget needs a public
    domain). Disabled unless APP_ENV=development.
    """
    if settings.app_env != "development":
        raise HTTPException(status_code=403, detail="dev-login o'chirilgan")
    user = await get_or_create_user(session, payload.telegram_user_id, payload.name)
    await session.commit()
    return {
        "access_token": create_access_token(user.id, user.telegram_user_id),
        "user": _user_dict(user),
    }


@router.post("/demo-login")
async def demo_login(
    payload: DevLogin,
    x_demo_key: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Secret-gated login for demoing the deployed dashboard.

    Requires DEMO_ACCESS_KEY to be set on the server AND matched by the
    X-Demo-Key header — unlike dev-login, this works in production too, but
    only for whoever holds the secret key. Meant to be temporary, until the
    Telegram Login Widget flow is confirmed working end-to-end.
    """
    if not settings.demo_access_key or x_demo_key != settings.demo_access_key:
        raise HTTPException(status_code=403, detail="demo-login o'chirilgan")
    user = await get_or_create_user(session, payload.telegram_user_id, payload.name)
    await session.commit()
    return {
        "access_token": create_access_token(user.id, user.telegram_user_id),
        "user": _user_dict(user),
    }


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return _user_dict(user)
