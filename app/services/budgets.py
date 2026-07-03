"""Monthly budget tracking — the chosen extra feature.

`budget_status` compares each budget's limit against actual spend and flags
those at/over an alert threshold (default 90%).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Budget, Category, Transaction, TxType

ALERT_THRESHOLD = 0.9


def _month_bounds(month: str) -> tuple[date, date]:
    year, mon = (int(x) for x in month.split("-"))
    start = date(year, mon, 1)
    end = date(year + (mon == 12), (mon % 12) + 1, 1)
    return start, end


async def budget_status(
    session: AsyncSession, user_id: int, month: str | None = None
) -> list[dict]:
    month = month or date.today().strftime("%Y-%m")
    start, end = _month_bounds(month)

    budgets = list(
        (
            await session.scalars(
                select(Budget).where(
                    Budget.user_id == user_id, Budget.month == month
                )
            )
        ).all()
    )
    result: list[dict] = []
    for b in budgets:
        stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.type == TxType.expense,
            Transaction.occurred_at >= start,
            Transaction.occurred_at < end,
        )
        cat_name = None
        if b.category_id:
            stmt = stmt.where(Transaction.category_id == b.category_id)
            cat = await session.get(Category, b.category_id)
            cat_name = cat.name if cat else None
        spent = float(await session.scalar(stmt) or 0)
        limit = float(b.limit_amount)
        pct = (spent / limit) if limit else 0.0
        result.append(
            {
                "budget_id": b.id,
                "category_id": b.category_id,
                "category": cat_name or "Umumiy",
                "limit": limit,
                "spent": spent,
                "pct": round(pct * 100, 1),
                "over": spent > limit,
                "alert": pct >= ALERT_THRESHOLD,
            }
        )
    return result


async def upsert_budget(
    session: AsyncSession,
    user_id: int,
    *,
    month: str,
    limit_amount: float,
    category_id: int | None = None,
) -> Budget:
    stmt = select(Budget).where(
        Budget.user_id == user_id,
        Budget.month == month,
        Budget.category_id.is_(category_id)
        if category_id is None
        else Budget.category_id == category_id,
    )
    budget = await session.scalar(stmt)
    if budget:
        budget.limit_amount = limit_amount
    else:
        budget = Budget(
            user_id=user_id,
            month=month,
            limit_amount=limit_amount,
            category_id=category_id,
        )
        session.add(budget)
    await session.flush()
    return budget
