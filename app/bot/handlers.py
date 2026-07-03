"""aiogram message handlers: greet, help, list categories, text, voice."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.ai.transcribe import transcribe
from app.bot.pipeline import handle_message
from app.db import session_scope
from app.models import TxSource, TxType
from app.services import categories as cat_service
from app.services.users import get_or_create_user

router = Router()
logger = logging.getLogger("pultrack.bot")

WELCOME = (
    "Assalomu alaykum! Men PulTrack — biznesingiz pulini kuzataman. 💼\n\n"
    "Shunchaki yozing yoki gapiring:\n"
    "• «Bugun sotuvdan 2 mln keldi»\n"
    "• «Logistikaga 500 ming xarajat»\n"
    "• «Bu oy marketingga qancha ketdi?»\n\n"
    "Tuzatish: «oxirgisini o'chir» yoki to'g'ri summani yozing.\n"
    "Buyruqlar: /categories, /help"
)


async def _process(message: Message, text: str, source: TxSource) -> None:
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    async with session_scope() as session:
        user = await get_or_create_user(
            session, message.from_user.id, message.from_user.full_name
        )
        await session.commit()  # persist user + seeded categories
        reply = await handle_message(session, user, text, source)
    await message.answer(reply)


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    async with session_scope() as session:
        await get_or_create_user(
            session, message.from_user.id, message.from_user.full_name
        )
        await session.commit()
    await message.answer(WELCOME)


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(WELCOME)


@router.message(Command("categories"))
async def on_categories(message: Message) -> None:
    async with session_scope() as session:
        user = await get_or_create_user(
            session, message.from_user.id, message.from_user.full_name
        )
        await session.commit()
        income = await cat_service.list_categories(session, user.id, TxType.income)
        expense = await cat_service.list_categories(session, user.id, TxType.expense)
    lines = ["🟢 Daromad kategoriyalari:"]
    lines += [f"  • {c.name}" for c in income] or ["  —"]
    lines += ["", "🔴 Xarajat kategoriyalari:"]
    lines += [f"  • {c.name}" for c in expense] or ["  —"]
    lines += ["", "Yangi qo'shish: «Reklama kategoriyasini qo'sh»."]
    await message.answer("\n".join(lines))


@router.message(F.voice | F.audio)
async def on_voice(message: Message) -> None:
    voice = message.voice or message.audio
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    file = await message.bot.get_file(voice.file_id)
    buffer = await message.bot.download_file(file.file_path)
    text = await transcribe(buffer.read())
    logger.info("VOICE transcript=%r", text)
    if not text:
        await message.answer(
            "Ovozni tushunolmadim 🎤 Iltimos, qayta urinib ko'ring yoki yozib yuboring."
        )
        return
    # We intentionally do NOT echo the raw transcript (it can be imperfect);
    # the confirmation below shows exactly what was recorded.
    await _process(message, text, TxSource.telegram_voice)


@router.message(F.text)
async def on_text(message: Message) -> None:
    await _process(message, message.text, TxSource.telegram_text)
