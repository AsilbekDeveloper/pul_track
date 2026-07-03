"""Bot + Dispatcher singletons.

FSM/state storage uses Redis when REDIS_URL is set (survives restarts &
scales across workers), otherwise falls back to in-memory.
"""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings

_bot: Bot | None = None
_dp: Dispatcher | None = None


def _build_storage():
    if settings.redis_url:
        try:
            from aiogram.fsm.storage.redis import RedisStorage

            return RedisStorage.from_url(settings.redis_url)
        except Exception:
            pass
    return MemoryStorage()


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.telegram_bot_token)
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        _dp = Dispatcher(storage=_build_storage())
        from app.bot.handlers import router

        _dp.include_router(router)
    return _dp
