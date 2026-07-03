"""OpenAI structured-output extractor (OPTIONAL, only if ai_provider=openai).

The free default is app/ai/rule_extract.py; this is here for users who have
an OpenAI key and want smarter parsing.
"""
from __future__ import annotations

from datetime import date

from app.ai.client import get_client
from app.ai.prompts import build_extract_system_prompt
from app.config import settings
from app.schemas import ExtractionResult, Intent


async def extract_openai(text: str, today: date | None = None) -> ExtractionResult:
    today = today or date.today()
    client = get_client()
    try:
        completion = await client.beta.chat.completions.parse(
            model=settings.openai_model,
            temperature=0,
            messages=[
                {"role": "system", "content": build_extract_system_prompt(today)},
                {"role": "user", "content": text},
            ],
            response_format=ExtractionResult,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("empty parse")
        return parsed
    except Exception:
        return ExtractionResult(
            intent=Intent.unknown,
            confidence=0.0,
            clarification=(
                "Kechirasiz, xabaringizni tushunolmadim. Masalan: "
                "«Logistikaga 500 ming xarajat» deb yozib ko'ring."
            ),
        )
