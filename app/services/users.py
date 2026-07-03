"""User lookup / creation and dashboard-user resolution."""
from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Transaction, User
from app.services.categories import seed_default_categories


async def get_or_create_user(
    session: AsyncSession, telegram_user_id: int, name: str | None = None
) -> User:
    user = await session.scalar(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    if user:
        return user
    user = User(telegram_user_id=telegram_user_id, name=name)
    session.add(user)
    await session.flush()  # assigns user.id
    await seed_default_categories(session, user.id)
    return user


async def resolve_dashboard_user(session: AsyncSession) -> User | None:
    """Which user's data the single-tenant dashboard shows.

    If DASHBOARD_USER_ID is set, use that Telegram id; otherwise fall back to
    the most recently active user (latest transaction, else newest user).
    """
    if settings.dashboard_user_id:
        user = await session.scalar(
            select(User).where(User.telegram_user_id == settings.dashboard_user_id)
        )
        if user:
            return user

    # most recent transaction's owner
    recent_owner = await session.scalar(
        select(User)
        .join(Transaction, Transaction.user_id == User.id)
        .order_by(desc(Transaction.created_at))
        .limit(1)
    )
    if recent_owner:
        return recent_owner

    return await session.scalar(select(User).order_by(desc(User.created_at)).limit(1))
