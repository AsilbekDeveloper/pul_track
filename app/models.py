"""SQLAlchemy 2.0 ORM models.

Indexes are chosen for the hot query paths: per-user lookups filtered by
date and category (dashboard + bot reports).
"""
from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TxType(str, enum.Enum):
    income = "income"
    expense = "expense"


class TxSource(str, enum.Enum):
    telegram_text = "telegram_text"
    telegram_voice = "telegram_voice"
    web = "web"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True
    )
    name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    categories: Mapped[list[Category]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    type: Mapped[TxType] = mapped_column(Enum(TxType, name="tx_type"))
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="categories")
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="category"
    )

    __table_args__ = (
        Index("ix_categories_user_type", "user_id", "type"),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    type: Mapped[TxType] = mapped_column(Enum(TxType, name="tx_type"))
    # Amounts stored in UZS. Numeric avoids float rounding on money.
    amount: Mapped[float] = mapped_column(Numeric(16, 2))
    occurred_at: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[TxSource] = mapped_column(
        Enum(TxSource, name="tx_source"), default=TxSource.telegram_text
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="transactions")
    category: Mapped[Category | None] = relationship(
        back_populates="transactions"
    )

    __table_args__ = (
        # Covers the dashboard/report filters: user + date range + type.
        Index("ix_tx_user_date", "user_id", "occurred_at"),
        Index("ix_tx_user_type_date", "user_id", "type", "occurred_at"),
    )


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Null category => overall monthly spending budget.
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE")
    )
    month: Mapped[str] = mapped_column(String(7))  # "YYYY-MM"
    limit_amount: Mapped[float] = mapped_column(Numeric(16, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_budget_user_month", "user_id", "month"),
    )
