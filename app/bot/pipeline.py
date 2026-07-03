"""Core message pipeline — pure logic, framework-agnostic and testable.

Given a user and a text message, decides the intent and returns a natural
reply. The same pipeline serves text and (already transcribed) voice.
Never returns None — every path produces a reply.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.extract import extract
from app.models import Category, Transaction, TxSource, TxType, User
from app.schemas import ExtractionResult, Intent, ReportPeriod
from app.services import analytics, categories, transactions

logger = logging.getLogger("pultrack.pipeline")

CONFIDENCE_FLOOR = 0.45


def fmt_money(amount: float) -> str:
    return f"{int(round(amount)):,}".replace(",", " ") + " so'm"


async def handle_message(
    session: AsyncSession,
    user: User,
    text: str,
    source: TxSource = TxSource.telegram_text,
) -> str:
    known = [c.name for c in await categories.list_categories(session, user.id)]
    result = await extract(text, categories=known)
    logger.info(
        "IN=%r -> intent=%s type=%s amount=%s cat=%s period=%s conf=%.2f",
        text, result.intent.value, result.tx_type, result.amount,
        result.category, result.report_period, result.confidence,
    )

    if result.intent in (Intent.income, Intent.expense):
        return await _log_transaction(session, user, result, source)
    if result.intent == Intent.add_category:
        return await _add_category(session, user, result)
    if result.intent in (Intent.report, Intent.question):
        return await _report(session, user, result)
    if result.intent == Intent.correction:
        return await _correct(session, user, result)
    if result.intent == Intent.delete:
        return await _delete_last(session, user)

    # unknown / low confidence -> always ask, never fail silently
    return result.clarification or (
        "Tushunolmadim 🤔 Daromadmi yoki xarajat? Summani ham yozib yuboring. "
        "Masalan: «Bugun sotuvdan 2 mln keldi»."
    )


async def _log_transaction(
    session: AsyncSession,
    user: User,
    result: ExtractionResult,
    source: TxSource,
) -> str:
    tx_type = result.tx_type or (
        TxType.income if result.intent == Intent.income else TxType.expense
    )
    if not result.amount or result.confidence < CONFIDENCE_FLOOR:
        return result.clarification or (
            "Summani aniq ayta olasizmi? Masalan «450 ming» yoki «2 mln»."
        )

    category = None
    if result.category:
        category = await categories.get_or_create_category(
            session, user.id, result.category, tx_type
        )

    tx = await transactions.create_transaction(
        session,
        user_id=user.id,
        type=tx_type,
        amount=result.amount,
        occurred_at=result.occurred_at or date.today(),
        category_id=category.id if category else None,
        note=result.note,
        source=source,
    )
    await session.commit()

    kind = "Daromad" if tx_type == TxType.income else "Xarajat"
    when = (result.occurred_at or date.today()).strftime("%d.%m.%Y")

    # One "what for" line — avoid repeating the same thing twice.
    generic = {"boshqa xarajat", "boshqa daromad"}
    if category and category.name.lower() not in generic:
        label, what = "Kategoriya", category.name
    elif result.note:
        label, what = "Izoh", result.note
    elif category:
        label, what = "Kategoriya", category.name
    else:
        label, what = "Kategoriya", "kiritilmagan"

    return (
        f"✅ {kind} qayd etildi\n\n"
        f"💵 Summa: {fmt_money(float(tx.amount))}\n"
        f"🏷 {label}: {what}\n"
        f"🗓 Sana: {when}"
    )


async def _add_category(
    session: AsyncSession, user: User, result: ExtractionResult
) -> str:
    name = (result.new_category_name or result.category or "").strip()
    if not name:
        return "Yangi kategoriya nomini yozing. Masalan: «Reklama kategoriyasini qo'sh»."
    tx_type = result.new_category_type or TxType.expense
    cat = await categories.get_or_create_category(session, user.id, name, tx_type)
    await session.commit()
    kind = "daromad" if tx_type == TxType.income else "xarajat"
    return f"➕ «{cat.name}» ({kind}) kategoriyasi qo'shildi."


async def _report(
    session: AsyncSession, user: User, result: ExtractionResult
) -> str:
    period = result.report_period or ReportPeriod.this_month
    start, end = analytics.period_bounds(period)
    label = _period_label(period)

    if result.report_category:
        cat = await session.scalar(
            select(Category).where(
                Category.user_id == user.id,
                func.lower(Category.name) == result.report_category.lower(),
            )
        )
        if not cat:
            return (
                f"«{result.report_category}» kategoriyasi topilmadi. "
                f"Mavjud kategoriyalarni ko'rish uchun /categories deb yozing."
            )
        stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user.id,
            Transaction.category_id == cat.id,
        )
        if start:
            stmt = stmt.where(Transaction.occurred_at >= start)
        if end:
            stmt = stmt.where(Transaction.occurred_at <= end)
        total = float(await session.scalar(stmt) or 0)
        return f"📊 {label} «{cat.name}» bo'yicha: {fmt_money(total)}."

    t = await analytics.totals(session, user.id, start, end)
    return (
        f"📊 {label}:\n"
        f"🟢 Daromad: {fmt_money(t['income'])}\n"
        f"🔴 Xarajat: {fmt_money(t['expense'])}\n"
        f"💰 Sof: {fmt_money(t['net'])}"
    )


async def _correct(
    session: AsyncSession, user: User, result: ExtractionResult
) -> str:
    recent = await transactions.get_recent(session, user.id, limit=1)
    if not recent:
        return "Tuzatish uchun so'nggi yozuv topilmadi."
    tx = recent[0]
    changes: dict = {}
    if result.amount:
        changes["amount"] = result.amount
    if result.tx_type:
        changes["type"] = result.tx_type
    if result.occurred_at:
        changes["occurred_at"] = result.occurred_at
    if result.note:
        changes["note"] = result.note
    if result.category:
        cat = await categories.get_or_create_category(
            session, user.id, result.category, tx.type
        )
        changes["category_id"] = cat.id
    if not changes:
        return "Nimani tuzatay? Masalan: «summa 300 ming edi»."
    await transactions.update_transaction(session, user.id, tx.id, **changes)
    await session.commit()
    return f"✏️ So'nggi yozuv yangilandi: {fmt_money(float(result.amount or tx.amount))}."


async def _delete_last(session: AsyncSession, user: User) -> str:
    recent = await transactions.get_recent(session, user.id, limit=1)
    if not recent:
        return "O'chirish uchun yozuv yo'q."
    tx = recent[0]
    await transactions.delete_transaction(session, user.id, tx.id)
    await session.commit()
    return f"🗑 So'nggi yozuv o'chirildi ({fmt_money(float(tx.amount))})."


def _period_label(period: ReportPeriod) -> str:
    return {
        ReportPeriod.today: "Bugun",
        ReportPeriod.this_week: "Bu hafta",
        ReportPeriod.this_month: "Bu oy",
        ReportPeriod.last_month: "O'tgan oy",
        ReportPeriod.this_year: "Bu yil",
        ReportPeriod.all: "Umumiy",
    }[period]
