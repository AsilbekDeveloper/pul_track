"""Async database engine + session factory.

A pooled asyncpg engine is created once. `get_session` is a FastAPI
dependency; `session_scope` is an async context manager for the bot side.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=10,          # keep warm connections ready
    max_overflow=20,       # burst capacity under load
    pool_pre_ping=True,    # drop dead connections transparently
    pool_recycle=1800,     # recycle every 30 min (cloud PG idle timeouts)
    echo=False,
)

SessionFactory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session, always closed afterwards."""
    async with SessionFactory() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Standalone session (used by the Telegram bot handlers)."""
    async with SessionFactory() as session:
        yield session
