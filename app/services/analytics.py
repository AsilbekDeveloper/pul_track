"""Reporting/aggregation — pushed down to SQL (SUM / GROUP BY / date_trunc).

The dashboard and the bot's "how much did we spend on X?" both call these.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from sqlalchemy import Numeric, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Transaction, TxType
from app.schemas import ReportPeriod


def period_bounds(period: ReportPeriod, today: date | None = None) -> tuple[date | None, date | None]:
    """Return (start, end) inclusive dates for a named period."""
    today = today or date.today()
    if period == ReportPeriod.today:
        return today, today
    if period == ReportPeriod.this_week:
        start = today - timedelta(days=today.weekday())
        return start, today
    if period == ReportPeriod.this_month:
        return today.replace(day=1), today
    if period == ReportPeriod.last_month:
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    if period == ReportPeriod.this_year:
        return today.replace(month=1, day=1), today
    return None, None  # all time


async def totals(
    session: AsyncSession, user_id: int, start: date | None, end: date | None
) -> dict[str, float]:
    """Income / expense / net over a range."""
    stmt = select(
        Transaction.type,
        func.coalesce(func.sum(Transaction.amount), 0),
    ).where(Transaction.user_id == user_id)
    if start:
        stmt = stmt.where(Transaction.occurred_at >= start)
    if end:
        stmt = stmt.where(Transaction.occurred_at <= end)
    stmt = stmt.group_by(Transaction.type)

    income = expense = 0.0
    for tx_type, total in (await session.execute(stmt)).all():
        if tx_type == TxType.income:
            income = float(total)
        else:
            expense = float(total)
    return {"income": income, "expense": expense, "net": income - expense}


async def by_category(
    session: AsyncSession,
    user_id: int,
    type: TxType,
    start: date | None,
    end: date | None,
) -> list[dict]:
    stmt = (
        select(
            func.coalesce(Category.name, "Kategoriyasiz").label("name"),
            func.sum(Transaction.amount).label("total"),
        )
        .select_from(Transaction)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(Transaction.user_id == user_id, Transaction.type == type)
    )
    if start:
        stmt = stmt.where(Transaction.occurred_at >= start)
    if end:
        stmt = stmt.where(Transaction.occurred_at <= end)
    stmt = stmt.group_by("name").order_by(func.sum(Transaction.amount).desc())
    return [
        {"name": name, "total": float(total)}
        for name, total in (await session.execute(stmt)).all()
    ]


async def monthly_trend(
    session: AsyncSession, user_id: int, months: int = 6
) -> list[dict]:
    """Income vs expense per month for the last `months` months."""
    today = date.today()
    start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    for _ in range(months - 1):
        start = (start - timedelta(days=1)).replace(day=1)

    month_col = func.to_char(Transaction.occurred_at, "YYYY-MM").label("month")
    stmt = (
        select(
            month_col,
            Transaction.type,
            func.sum(Transaction.amount),
        )
        .where(Transaction.user_id == user_id, Transaction.occurred_at >= start)
        .group_by(month_col, Transaction.type)
        .order_by(month_col)
    )
    buckets: dict[str, dict[str, float]] = {}
    for month, tx_type, total in (await session.execute(stmt)).all():
        b = buckets.setdefault(month, {"income": 0.0, "expense": 0.0})
        b[tx_type.value] = float(total)

    # ensure continuous months even when empty
    result: list[dict] = []
    cursor = start
    while cursor <= today:
        key = cursor.strftime("%Y-%m")
        b = buckets.get(key, {"income": 0.0, "expense": 0.0})
        result.append({"month": key, **b})
        # jump to first of next month
        days_in = calendar.monthrange(cursor.year, cursor.month)[1]
        cursor = cursor + timedelta(days=days_in - cursor.day + 1)
    return result


async def overview(session: AsyncSession, user_id: int) -> dict:
    """Everything the Overview page needs in one call."""
    this_start, this_end = period_bounds(ReportPeriod.this_month)
    last_start, last_end = period_bounds(ReportPeriod.last_month)
    this_month = await totals(session, user_id, this_start, this_end)
    last_month = await totals(session, user_id, last_start, last_end)
    all_time = await totals(session, user_id, None, None)
    return {
        "this_month": this_month,
        "last_month": last_month,
        "all_time": all_time,
    }
