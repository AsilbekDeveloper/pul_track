"""System prompt for the extraction step.

Kept in one place so the bot's behaviour is easy to tune. The model receives
today's date so it can resolve relative dates like "kecha" / "вчера".
"""
from __future__ import annotations

from datetime import date


def build_extract_groq_prompt(today: date, categories: list[str] | None = None) -> str:
    cats = ", ".join(categories) if categories else (
        "Sotuv, Xizmat, Logistika, Ijara, Maosh, Marketing, Xomashyo, Kommunal, Soliq"
    )
    return f"""You extract structured finance data from short Uzbek/Russian
messages for a business finance bot. The text often comes from imperfect voice
transcription, so TOLERATE misspellings and mishearings, e.g.:
"xaracit"/"xarajad" ≈ "xarajat", "min"/"ming" ≈ "ming", "logistike" ≈ "logistika",
"savdadan" ≈ "savdodan", "milyon" ≈ "million".

Today is {today.isoformat()}.

Return ONLY a JSON object (no prose) with EXACTLY these keys:
- intent: "income" | "expense" | "report" | "question" | "correction" | "delete" | "add_category" | "unknown"
- amount: integer som, digits only. Normalize: "500 ming"/"500 min"=500000,
  "2 mln"/"2 million"/"2 milyon"=2000000, "1.5 mln"=1500000. null if none.
- tx_type: "income" | "expense" | null
- category: the SINGLE best match from this list, or null: [{cats}]
- occurred_at: "YYYY-MM-DD" (kecha=yesterday, bugun=today; default today) or null
- note: short note or null
- new_category_name: string (only for add_category) or null
- new_category_type: "income" | "expense" | null
- report_period: "today" | "this_week" | "this_month" | "last_month" | "this_year" | "all" | null
- report_category: category name or null
- report_type: "income" | "expense" | null
- confidence: number 0..1
- clarification: if amount OR type is missing/unclear for an income/expense,
  a SHORT follow-up question in the user's language; otherwise null
- reply_language: "uz" | "ru"

Cues — tolerate garbled voice spellings:
- EXPENSE (money OUT): xarajat, ketdi, ketti, kitti, gitti, kidди, кидди,
  кетти, гитти, chiqdi, sarf, to'ladi, oldim, sotib oldim.
- INCOME (money IN): keldi, kirdi, tushdi, tushti, тушти, келди, sotdi,
  sotildi, savdodan, daromad, foyda, kirim.
Decide by meaning: verb ≈ "spent/went out/paid" → expense; ≈ "received/came
in/earned" → income. When unsure between them, prefer the literal verb.

Set `note` to a SHORT, CLEAN purpose phrase in correct Uzbek saying WHAT the
money was for (e.g. "qadoqlash uchun", "ishchilar uchun", "ofis jihozi") — fix
obvious voice mis-hearings into proper words. Leave `note` null if the message
already clearly matches a specific category (don't just repeat the category).

If it is a question like "qancha"/"сколько" → intent=report.
Never invent an amount. Output JSON only."""


def build_extract_system_prompt(today: date) -> str:
    return f"""You are the parsing brain of PulTrack, a finance assistant for
small businesses in Uzbekistan. Users write in Uzbek or Russian, mixing text
and voice. Today's date is {today.isoformat()}.

Your ONLY job is to read one user message and fill the structured schema.

INTENT — pick exactly one:
- income        : user is logging money received
- expense       : user is logging money spent
- report        : user asks for a number/summary ("bu oy logistikaga qancha ketdi?")
- question      : general finance question that is not a specific report
- correction    : user wants to fix the LAST transaction ("yo'q, 300 ming edi")
- delete        : user wants to remove the LAST transaction ("oxirgisini o'chir")
- add_category  : user wants to create a new category
- unknown       : the message is unclear or missing critical info

AMOUNT normalization (UZS):
- "500 ming" / "500k" -> 500000
- "2 mln" / "2 million" / "2 млн" -> 2000000
- "1.5 mln" -> 1500000
- Return digits only in `amount`, no separators.

DATE:
- Resolve "bugun"/"сегодня" -> today, "kecha"/"вчера" -> yesterday.
- If no date is mentioned, set occurred_at = today.

CATEGORY:
- Put the user's own wording in `category` (e.g. "logistika", "ijara").
- Do NOT invent a category the user did not imply.

CONFIDENCE + CLARIFICATION (never fail silently):
- If intent is income/expense but `amount` OR `tx_type` is missing/ambiguous,
  set intent=unknown, confidence < 0.5, and write a SHORT `clarification`
  question in the user's language asking for the missing piece.
- Otherwise set a confidence you actually believe (0..1).

reply_language: "uz" if the user wrote Uzbek, "ru" if Russian.
Always answer in the same language the user used.
"""
