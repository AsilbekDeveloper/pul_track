"""JSON API for the dashboard: reads + chart data + inline create/edit/delete."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Transaction, TxSource, TxType, User
from app.schemas import (
    BudgetUpsert,
    CategoryCreate,
    ReportPeriod,
    TransactionCreate,
    TransactionUpdate,
)
from app.services import analytics, budgets
from app.services import categories as cat_service
from app.services import transactions as tx_service
from app.web.auth import get_current_user

router = APIRouter(prefix="/api")


def _tx_dict(t: Transaction) -> dict:
    return {
        "id": t.id,
        "type": t.type.value,
        "amount": float(t.amount),
        "occurred_at": t.occurred_at.isoformat(),
        "note": t.note,
        "category_id": t.category_id,
        "category": t.category.name if t.category else None,
    }


# ---- Reads ----

@router.get("/overview")
async def overview(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    ov = await analytics.overview(session, user.id)
    recent = await tx_service.get_recent(session, user.id, limit=5)
    alerts = [b for b in await budgets.budget_status(session, user.id) if b["alert"]]
    return {"totals": ov, "recent": [_tx_dict(t) for t in recent], "alerts": alerts}


@router.get("/transactions")
async def list_tx(
    type: TxType | None = None,
    category_id: int | None = None,
    search: str | None = None,
    start: date | None = None,
    end: date | None = None,
    limit: int = 200,
    offset: int = 0,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    txs = await tx_service.list_transactions(
        session, user.id, type=type, category_id=category_id,
        search=search, start=start, end=end, limit=limit, offset=offset,
    )
    return [_tx_dict(t) for t in txs]


@router.get("/categories")
async def list_cats(
    type: TxType | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    cats = await cat_service.list_categories(session, user.id, type)
    return [
        {"id": c.id, "name": c.name, "type": c.type.value, "is_custom": c.is_custom}
        for c in cats
    ]


# ---- Transactions ----

@router.post("/transactions", status_code=201)
async def create_tx(
    payload: TransactionCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tx = await tx_service.create_transaction(
        session,
        user_id=user.id,
        type=payload.type,
        amount=payload.amount,
        occurred_at=payload.occurred_at,
        category_id=payload.category_id,
        note=payload.note,
        source=TxSource.web,
    )
    await session.commit()
    return {"id": tx.id}


@router.patch("/transactions/{tx_id}")
async def update_tx(
    tx_id: int,
    payload: TransactionUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tx = await tx_service.update_transaction(
        session, user.id, tx_id, **payload.model_dump(exclude_none=True)
    )
    if not tx:
        raise HTTPException(404, "Topilmadi")
    await session.commit()
    return {"ok": True}


@router.delete("/transactions/{tx_id}")
async def delete_tx(
    tx_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    ok = await tx_service.delete_transaction(session, user.id, tx_id)
    if not ok:
        raise HTTPException(404, "Topilmadi")
    await session.commit()
    return {"ok": True}


# ---- Categories ----

@router.post("/categories", status_code=201)
async def create_category(
    payload: CategoryCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    cat = await cat_service.create_category(
        session, user.id, payload.name, payload.type
    )
    await session.commit()
    return {"id": cat.id, "name": cat.name, "type": cat.type.value}


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    ok = await cat_service.delete_category(session, user.id, category_id)
    if not ok:
        raise HTTPException(404, "Topilmadi")
    await session.commit()
    return {"ok": True}


# ---- Budgets (extra feature) ----

@router.post("/budgets", status_code=201)
async def upsert_budget(
    payload: BudgetUpsert,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    b = await budgets.upsert_budget(
        session,
        user.id,
        month=payload.month,
        limit_amount=payload.limit_amount,
        category_id=payload.category_id,
    )
    await session.commit()
    return {"id": b.id}


@router.get("/budgets")
async def list_budgets(
    month: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await budgets.budget_status(session, user.id, month)


# ---- Analytics (chart feeds) ----

@router.get("/analytics/trend")
async def trend(
    months: int = 6,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await analytics.monthly_trend(session, user.id, months)


@router.get("/analytics/by-category")
async def by_category(
    type: TxType = TxType.expense,
    period: ReportPeriod = ReportPeriod.this_month,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    start, end = analytics.period_bounds(period)
    return await analytics.by_category(session, user.id, type, start, end)
