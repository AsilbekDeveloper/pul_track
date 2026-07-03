"""FastAPI backend entrypoint (API-only; the frontend is a separate static app).

One process serves:
  1. the JSON API (JWT-protected, per-user),
  2. the auth endpoints (Telegram Login Widget + dev-login),
  3. the Telegram webhook (in production) — bot logic lives in app/bot.

In local dev (no WEBHOOK_BASE_URL) the bot runs in long-polling mode inside
a background task, so you don't need a public URL to test it.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.bot.instance import get_bot, get_dispatcher
from app.config import settings
from app.db import engine
from app.models import Base
from app.web.api import router as api_router
from app.web.auth_routes import router as auth_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pultrack")

# keep references so background tasks aren't garbage-collected
_bg_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: ensure tables exist. Production uses Alembic migrations.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    polling_task: asyncio.Task | None = None
    if settings.telegram_bot_token:
        # A bad/placeholder token must not take down the dashboard.
        try:
            bot = get_bot()
            dp = get_dispatcher()
            if settings.use_webhook:
                url = settings.webhook_base_url.rstrip("/") + settings.telegram_webhook_path
                await bot.set_webhook(
                    url,
                    secret_token=settings.telegram_webhook_secret,
                    drop_pending_updates=True,
                    allowed_updates=dp.resolve_used_update_types(),
                )
                logger.info("Telegram webhook set: %s", url)
            else:
                await bot.delete_webhook(drop_pending_updates=True)
                polling_task = asyncio.create_task(dp.start_polling(bot))
                logger.info("Telegram bot started in long-polling mode")
        except Exception as exc:
            logger.warning("Telegram bot disabled (startup failed): %s", exc)
            polling_task = None
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")

    yield

    if polling_task:
        polling_task.cancel()
    if settings.telegram_bot_token:
        await get_bot().session.close()
    await engine.dispose()


app = FastAPI(title="PulTrack API", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(api_router)


@app.get("/")
async def root():
    return {"service": "PulTrack API", "docs": "/docs", "health": "/healthz"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post(settings.telegram_webhook_path, include_in_schema=False)
async def telegram_webhook(request: Request):
    if (
        request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        != settings.telegram_webhook_secret
    ):
        raise HTTPException(status_code=403, detail="bad secret")

    bot = get_bot()
    dp = get_dispatcher()
    update = Update.model_validate(await request.json(), context={"bot": bot})

    # Process in the background so we ACK Telegram immediately (low latency).
    task = asyncio.create_task(dp.feed_update(bot, update))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    return JSONResponse({"ok": True})
