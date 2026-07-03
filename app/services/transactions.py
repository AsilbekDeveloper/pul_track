"""Transaction CRUD + filtered listing.

All reads eager-load the category so templates/JSON never trigger lazy IO.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import delete as sa_delete
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Category, Transaction, TxSource, TxType


async def create_transaction(
    session: AsyncSession,
    *,
    user_id: int,
    type: TxType,
    amount: float,
    occurred_at: date,
    category_id: int | None = None,
    note: str | None = None,
    source: TxSource = TxSource.telegram_text,
) -> Transaction:
    tx = Transaction(
        user_id=user_id,
        type=type,
        amount=amount,
        occurred_at=occurred_at,
        category_id=category_id,
        note=note,
        source=source,
    )
    session.add(tx)
    await session.flush()
    return tx


async def list_transactions(
    session: AsyncSession,
    user_id: int,
    *,
    type: TxType | None = None,
    category_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Transaction]:
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .options(selectinload(Transaction.category))
        .order_by(desc(Transaction.occurred_at), desc(Transaction.id))
    )
    if type is not None:
        stmt = stmt.where(Transaction.type == type)
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    if start is not None:
        stmt = stmt.where(Transaction.occurred_at >= start)
    if end is not None:
        stmt = stmt.where(Transaction.occurred_at <= end)
    if search:
        like = f"%{search.lower()}%"
        stmt = (
            stmt.outerjoin(Category, Transaction.category_id == Category.id)
            .where(
                (Transaction.note.ilike(like)) | (Category.name.ilike(like))
            )
        )
    stmt = stmt.limit(limit).offset(offset)
    return list((await session.scalars(stmt)).all())


async def get_recent(
    session: AsyncSession, user_id: int, limit: int = 1
) -> list[Transaction]:
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .options(selectinload(Transaction.category))
        .order_by(desc(Transaction.created_at))
        .limit(limit)
    )
    return list((await session.scalars(stmt)).all())


async def update_transaction(
    session: AsyncSession, user_id: int, tx_id: int, **fields
) -> Transaction | None:
    tx = await session.get(Transaction, tx_id)
    if not tx or tx.user_id != user_id:
        return None
    for key, value in fields.items():
        if value is not None and hasattr(tx, key):
            setattr(tx, key, value)
    await session.flush()
    return tx


async def delete_transaction(
    session: AsyncSession, user_id: int, tx_id: int
) -> bool:
    result = await session.execute(
        sa_delete(Transaction).where(
            Transaction.id == tx_id, Transaction.user_id == user_id
        )
    )
    return result.rowcount > 0
