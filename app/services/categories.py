"""Category management + default seeding."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, TxType

# Sensible defaults for a small Uzbek business. Seeded on first contact.
DEFAULT_CATEGORIES: list[tuple[str, TxType]] = [
    ("Sotuv", TxType.income),
    ("Xizmat", TxType.income),
    ("Boshqa daromad", TxType.income),
    ("Logistika", TxType.expense),
    ("Ijara", TxType.expense),
    ("Maosh", TxType.expense),
    ("Marketing", TxType.expense),
    ("Xomashyo", TxType.expense),
    ("Kommunal", TxType.expense),
    ("Soliq", TxType.expense),
    ("Boshqa xarajat", TxType.expense),
]


async def seed_default_categories(session: AsyncSession, user_id: int) -> None:
    session.add_all(
        Category(user_id=user_id, name=name, type=t, is_custom=False)
        for name, t in DEFAULT_CATEGORIES
    )
    await session.flush()


async def list_categories(
    session: AsyncSession, user_id: int, type: TxType | None = None
) -> list[Category]:
    stmt = select(Category).where(Category.user_id == user_id)
    if type is not None:
        stmt = stmt.where(Category.type == type)
    stmt = stmt.order_by(Category.type, Category.name)
    return list((await session.scalars(stmt)).all())


async def get_or_create_category(
    session: AsyncSession, user_id: int, name: str, type: TxType
) -> Category:
    """Case-insensitive match; creates a custom category if none matches."""
    name = name.strip()
    stmt = select(Category).where(
        Category.user_id == user_id,
        Category.type == type,
        func.lower(Category.name) == name.lower(),
    )
    existing = await session.scalar(stmt)
    if existing:
        return existing
    category = Category(user_id=user_id, name=name, type=type, is_custom=True)
    session.add(category)
    await session.flush()
    return category


async def create_category(
    session: AsyncSession, user_id: int, name: str, type: TxType
) -> Category:
    category = Category(
        user_id=user_id, name=name.strip(), type=type, is_custom=True
    )
    session.add(category)
    await session.flush()
    return category


async def delete_category(session: AsyncSession, user_id: int, category_id: int) -> bool:
    category = await session.get(Category, category_id)
    if not category or category.user_id != user_id:
        return False
    await session.delete(category)
    return True
