"""Extraction dispatcher.

Priority:
  1. Groq LLM (free, robust to messy voice) if GROQ_API_KEY is set
  2. OpenAI structured output if ai_provider="openai"
  3. free rule-based parser (offline fallback)
"""
from __future__ import annotations

import logging
from datetime import date

from app.config import settings
from app.schemas import ExtractionResult

logger = logging.getLogger("pultrack.extract")


async def extract(
    text: str,
    categories: list[str] | None = None,
    today: date | None = None,
) -> ExtractionResult:
    if settings.groq_api_key:
        try:
            from app.ai.groq_extract import extract_groq

            return await extract_groq(text, categories, today)
        except Exception as exc:  # network / bad JSON -> fall back
            logger.warning("Groq extract failed, using rules: %s", exc)

    if settings.ai_provider == "openai" and settings.openai_api_key:
        from app.ai.openai_extract import extract_openai

        return await extract_openai(text, today)

    from app.ai.rule_extract import extract_rule

    return extract_rule(text, categories=categories, today=today)
