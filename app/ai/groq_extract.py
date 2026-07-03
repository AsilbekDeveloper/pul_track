"""FREE Groq LLM extractor — robust against messy voice transcription.

Uses Groq's OpenAI-compatible chat API in JSON mode, then validates into
ExtractionResult. Falls back (raises) to the rule parser on any failure.
"""
from __future__ import annotations

import json
import re
from datetime import date

from openai import AsyncOpenAI

from app.ai.prompts import build_extract_groq_prompt
from app.config import settings
from app.models import TxType
from app.schemas import ExtractionResult, Intent, ReportPeriod

_VALID_TYPES = {"income", "expense"}
_VALID_PERIODS = {p.value for p in ReportPeriod}
_VALID_INTENTS = {i.value for i in Intent}


def _clean(data: dict) -> dict:
    """Coerce/validate loose LLM output before Pydantic validation."""
    # amount -> number
    a = data.get("amount")
    if isinstance(a, str):
        digits = re.sub(r"[^\d.]", "", a)
        data["amount"] = float(digits) if digits else None
    # enums -> valid value or None
    for k, allowed in (
        ("tx_type", _VALID_TYPES),
        ("new_category_type", _VALID_TYPES),
        ("report_type", _VALID_TYPES),
        ("report_period", _VALID_PERIODS),
    ):
        if data.get(k) not in allowed:
            data[k] = None
    if data.get("intent") not in _VALID_INTENTS:
        data["intent"] = "unknown"
    # occurred_at must look like a date
    d = data.get("occurred_at")
    if not (isinstance(d, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", d)):
        data["occurred_at"] = None
    # blank strings -> None
    for k in ("category", "note", "new_category_name", "report_category", "clarification"):
        if isinstance(data.get(k), str) and not data[k].strip():
            data[k] = None
    return data


async def extract_groq(
    text: str,
    categories: list[str] | None = None,
    today: date | None = None,
) -> ExtractionResult:
    today = today or date.today()
    client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )
    resp = await client.chat.completions.create(
        model=settings.groq_model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": build_extract_groq_prompt(today, categories)},
            {"role": "user", "content": text},
        ],
    )
    data = json.loads(resp.choices[0].message.content or "{}")
    return ExtractionResult.model_validate(_clean(data))
