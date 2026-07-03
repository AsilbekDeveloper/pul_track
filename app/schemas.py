"""Pydantic v2 schemas.

`ExtractionResult` doubles as the JSON schema handed to OpenAI structured
output, so the model returns exactly the shape we need — no fragile parsing.
"""
from __future__ import annotations

import enum
from datetime import date

from pydantic import BaseModel, Field

from app.models import TxType


class Intent(str, enum.Enum):
    income = "income"          # log money in
    expense = "expense"        # log money out
    report = "report"          # "how much did we spend on X this month?"
    question = "question"      # general finance question
    correction = "correction"  # fix the last transaction
    delete = "delete"          # delete the last transaction
    add_category = "add_category"
    unknown = "unknown"        # unclear -> must ask a follow-up


class ReportPeriod(str, enum.Enum):
    today = "today"
    this_week = "this_week"
    this_month = "this_month"
    last_month = "last_month"
    this_year = "this_year"
    all = "all"


class ExtractionResult(BaseModel):
    """Everything the LLM must return for one incoming message."""

    intent: Intent
    # For income/expense:
    amount: float | None = Field(None, description="Amount in UZS, digits only")
    tx_type: TxType | None = Field(None, description="income or expense")
    category: str | None = Field(None, description="Category name in the user's words")
    occurred_at: date | None = Field(None, description="ISO date; resolve 'kecha'/'bugun'")
    note: str | None = None
    # For add_category:
    new_category_name: str | None = None
    new_category_type: TxType | None = None
    # For report/question:
    report_period: ReportPeriod | None = None
    report_category: str | None = None
    report_type: TxType | None = None
    # Meta:
    # No ge/le here: OpenAI strict structured output rejects minimum/maximum.
    confidence: float = Field(0.0, description="0..1 self-assessed confidence")
    clarification: str | None = Field(
        None, description="If unclear, the question to ask the user (their language)"
    )
    reply_language: str = Field("uz", description="uz or ru — answer in this language")


# ---- Web dashboard API ----

class TransactionCreate(BaseModel):
    type: TxType
    amount: float = Field(gt=0)
    category_id: int | None = None
    occurred_at: date
    note: str | None = None


class TransactionUpdate(BaseModel):
    type: TxType | None = None
    amount: float | None = Field(None, gt=0)
    category_id: int | None = None
    occurred_at: date | None = None
    note: str | None = None


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: TxType


class BudgetUpsert(BaseModel):
    category_id: int | None = None
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    limit_amount: float = Field(gt=0)
