"""aiogram message handlers: greet, help, login, categories, text, voice."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.ai.transcribe import transcribe
from app.bot.pipeline import handle_message
from app.config import settings
from app.db import session_scope
from app.models import TxSource, TxType
from app.security import create_access_token
from app.services import categories as cat_service
from app.services.users import get_or_create_user

router = Router()
logger = logging.getLogger("pultrack.bot")

WELCOME = (
    "👋 Assalomu alaykum! PulTrack'ga xush kelibsiz!\n\n"
    "📌 PulTrack — biznesingiz uchun moliya yordamchisi. Daromad va "
    "xarajatlaringizni bir necha soniyada qayd qilib, veb-dashboard'da "
    "kuzatib borasiz.\n\n"
    "💬 Yozib yoki 🎤 gapirib qayd qiling:\n"
    "• «Bugun sotuvdan 2 mln keldi»\n"
    "• «Logistikaga 500 ming xarajat»\n\n"
    "📊 Hisobot so'rang:\n"
    "• «Bu oy marketingga qancha ketdi?»\n\n"
    "✏️ Tuzating yoki o'chiring:\n"
    "• «Yo'q, 300 ming edi» yoki «oxirgisini o'chir»\n\n"
    "🏷 Yangi kategoriya qo'shing:\n"
    "• «Reklama kategoriyasini qo'sh»\n\n"
    "🖥 To'liq grafik, jadval va tahlillar uchun — pastdagi "
    "«Dashboard'ga kirish» tugmasini bosing yoki istalgan vaqtda "
    "/login deb yozing.\n\n"
    "Quyidagi tugmalardan foydalaning 👇"
)


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Dashboard'ga kirish", callback_data="act:login")],
            [
                InlineKeyboardButton(text="🏷 Kategoriyalarim", callback_data="act:categories"),
                InlineKeyboardButton(text="❓ Yordam", callback_data="act:help"),
            ],
        ]
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


async def _send_login_link(chat_id: int, telegram_user_id: int, full_name: str, bot) -> None:
    """Shared by /login command and the inline button."""
    async with session_scope() as session:
        user = await get_or_create_user(session, telegram_user_id, full_name)
        await session.commit()
    token = create_access_token(user.id, user.telegram_user_id)
    link = f"{settings.dashboard_url.rstrip('/')}/index.html?bot_token={token}"
    await bot.send_message(
        chat_id,
        "🔐 Dashboard'ga kirish uchun havola (faqat sizga tegishli):\n"
        f"{link}\n\n"
        "Havola 7 kun amal qiladi.",
    )


async def _send_categories(chat_id: int, telegram_user_id: int, full_name: str, bot) -> None:
    async with session_scope() as session:
        user = await get_or_create_user(session, telegram_user_id, full_name)
        await session.commit()
        income = await cat_service.list_categories(session, user.id, TxType.income)
        expense = await cat_service.list_categories(session, user.id, TxType.expense)
    lines = ["🟢 Daromad kategoriyalari:"]
    lines += [f"  • {c.name}" for c in income] or ["  —"]
    lines += ["", "🔴 Xarajat kategoriyalari:"]
    lines += [f"  • {c.name}" for c in expense] or ["  —"]
    lines += ["", "Yangi qo'shish: «Reklama kategoriyasini qo'sh»."]
    await bot.send_message(chat_id, "\n".join(lines))


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    async with session_scope() as session:
        await get_or_create_user(
            session, message.from_user.id, message.from_user.full_name
        )
        await session.commit()
    await message.answer(WELCOME, reply_markup=main_menu_kb())


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(WELCOME, reply_markup=main_menu_kb())


@router.message(Command("login"))
async def on_login(message: Message) -> None:
    """Send a direct, one-click dashboard sign-in link for this user.

    Bypasses the Telegram Login Widget's oauth.telegram.org confirmation
    flow entirely — it goes through our own bot (proven reliable) instead.
    """
    await _send_login_link(
        message.chat.id, message.from_user.id, message.from_user.full_name, message.bot
    )


@router.message(Command("categories"))
async def on_categories(message: Message) -> None:
    await _send_categories(
        message.chat.id, message.from_user.id, message.from_user.full_name, message.bot
    )


@router.callback_query(F.data == "act:login")
async def on_cb_login(cb: CallbackQuery) -> None:
    await _send_login_link(cb.message.chat.id, cb.from_user.id, cb.from_user.full_name, cb.bot)
    await cb.answer()


@router.callback_query(F.data == "act:categories")
async def on_cb_categories(cb: CallbackQuery) -> None:
    await _send_categories(cb.message.chat.id, cb.from_user.id, cb.from_user.full_name, cb.bot)
    await cb.answer()


@router.callback_query(F.data == "act:help")
async def on_cb_help(cb: CallbackQuery) -> None:
    await cb.message.answer(WELCOME, reply_markup=main_menu_kb())
    await cb.answer()


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
