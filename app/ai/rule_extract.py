"""Free, offline rule-based extractor (the default — no API, no cost).

Parses Uzbek/Russian finance messages into the same ExtractionResult schema
the OpenAI path returns, so the rest of the pipeline is provider-agnostic.
Handles amount normalization ("500 ming" -> 500000, "2 mln" -> 2000000),
income/expense detection, category & date matching, reports, delete,
correction and add-category — and always asks a follow-up when unsure.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from app.schemas import ExtractionResult, Intent, ReportPeriod
from app.models import TxType

# --- keyword banks (all lowercase) ---
_EXPENSE = [
    "xarajat", "harajat", "sarf", "ketdi", "ketti", "kitti", "chiqim", "chiqdi",
    "to'la", "tuladim", "to'ladim", "berdim", "xarj", "sotib oldim", "oldim",
    "расход", "потрат", "ушло", "заплат", "оплат", "отдал", "минус",
]
_INCOME = [
    "daromad", "keldi", "kirdi", "tushdi", "tushti", "sotdim", "sotildi", "sotdik",
    "foyda", "kirim", "tushum", "ishladim",
    "приход", "доход", "продал", "поступ", "получил", "заработал", "выручка", "плюс",
]
_DELETE = ["o'chir", "ochir", "o‘chir", "удали", "убери", "delete", "o'chrib"]
_CORRECTION = ["tuzat", "aslida", "noto'g'ri", "notogri", "xato",
               "должно быть", "исправ", "поправ", "не так"]
_REPORT = ["qancha", "qcha", "necha", "nechta", "сколько", "hisobot",
           "отчет", "отчёт", "report", "balans", "баланс", "итого"]

# Multiplier stems. Only distinctive multi-letter stems here — a bare "k"/"min"
# would wrongly match ordinary words like "ketdi"/"keldi" and inflate amounts.
_UNITS = {
    "milliard": 1e9, "mlrd": 1e9, "миллиард": 1e9, "млрд": 1e9,
    "million": 1e6, "milyon": 1e6, "mln": 1e6, "миллион": 1e6, "млн": 1e6,
    "ming": 1e3, "минг": 1e3, "тысяч": 1e3, "тыс": 1e3,
}

_DEFAULT_CATS = [
    "sotuv", "xizmat", "logistika", "ijara", "maosh", "marketing",
    "xomashyo", "kommunal", "soliq",
]

# Everyday words mapped to a canonical category name.
_SYNONYMS = {
    "oylik": "Maosh", "oyliklar": "Maosh", "maosh": "Maosh", "ish haqi": "Maosh",
    "zarplat": "Maosh", "зарплат": "Maosh",
    "savdo": "Sotuv", "sotuv": "Sotuv", "sotdi": "Sotuv", "sotil": "Sotuv", "продаж": "Sotuv",
    "reklama": "Marketing", "marketing": "Marketing", "реклам": "Marketing", "маркетинг": "Marketing",
    "ijara": "Ijara", "arenda": "Ijara", "аренд": "Ijara",
    "logistik": "Logistika", "yetkaz": "Logistika", "dostavka": "Logistika", "доставк": "Logistika", "логистик": "Logistika",
    "xomashyo": "Xomashyo", "material": "Xomashyo", "сырь": "Xomashyo",
    "kommunal": "Kommunal", "komunal": "Kommunal", "коммунал": "Kommunal",
    "soliq": "Soliq", "nalog": "Soliq", "налог": "Soliq",
    "xizmat": "Xizmat", "услуг": "Xizmat",
}


def _is_ru(text: str) -> bool:
    return bool(re.search(r"[а-яё]", text.lower()))


def _has(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def _parse_amount(t: str) -> float | None:
    merged = re.sub(r"(?<=\d)[  ]+(?=\d)", "", t)  # join "1 000 000"
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*([a-zа-яё]*)", merged):
        num = float(m.group(1).replace(",", "."))
        word = m.group(2)
        mult = next((v for k, v in _UNITS.items() if word and word.startswith(k)), None)
        if mult:
            return num * mult
        if 1900 <= num <= 2100 and not word:  # looks like a year, skip
            continue
        if num >= 1000:
            return num
    # glued thousands suffix: "500k"
    km = re.search(r"(\d+(?:[.,]\d+)?)k(?![a-zа-яё])", merged)
    if km:
        return float(km.group(1).replace(",", ".")) * 1000
    return None


def _parse_date(t: str, today: date) -> date | None:
    if "kecha" in t or "вчера" in t:
        return today - timedelta(days=1)
    if "bugun" in t or "сегодня" in t:
        return today
    if "ertaga" in t or "завтра" in t:
        return today + timedelta(days=1)
    m = re.search(r"\b(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?\b", t)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        y = int(m.group(3)) if m.group(3) else today.year
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    return None


def _parse_period(t: str) -> ReportPeriod:
    if "o'tgan oy" in t or "utgan oy" in t or "прошл" in t:
        return ReportPeriod.last_month
    if "hafta" in t or "недел" in t:
        return ReportPeriod.this_week
    if "yil" in t or "год" in t:
        return ReportPeriod.this_year
    if "umumiy" in t or "jami" in t or "hammasi" in t or "barcha" in t or "всего" in t or "итого" in t:
        return ReportPeriod.all
    if "bugun" in t or "сегодня" in t:
        return ReportPeriod.today
    return ReportPeriod.this_month  # sensible default


def _match_category(t: str, categories: list[str]) -> str | None:
    # 1) direct match against the user's own category names (longest first)
    for name in sorted(categories, key=len, reverse=True):
        if name and name.lower() in t:
            return name
    # 2) everyday synonyms -> canonical category, if that category exists
    by_lower = {c.lower(): c for c in categories}
    for kw in sorted(_SYNONYMS, key=len, reverse=True):
        if kw in t:
            canon = _SYNONYMS[kw].lower()
            if canon in by_lower:
                return by_lower[canon]
    return None


def extract_rule(
    text: str,
    categories: list[str] | None = None,
    today: date | None = None,
) -> ExtractionResult:
    today = today or date.today()
    cats = categories or _DEFAULT_CATS
    t = text.lower().replace("`", "'").replace("‘", "'").replace("’", "'")
    lang = "ru" if _is_ru(text) else "uz"

    amount = _parse_amount(t)
    category = _match_category(t, cats)
    when = _parse_date(t, today)

    # ---- add category ----
    if ("kategor" in t or "категор" in t) and (
        "qo'sh" in t or "qosh" in t or "добав" in t or "yangi" in t or "new" in t
    ):
        name = None
        m = re.search(r"([a-zа-яё'’]+)\s+kategor", t) or re.search(
            r"категори\w*\s+([a-zа-яё'’]+)", t
        )
        if m:
            name = m.group(1).strip().capitalize()
        new_type = TxType.income if _has(t, _INCOME) else TxType.expense
        if not name:
            return ExtractionResult(
                intent=Intent.unknown,
                confidence=0.3,
                reply_language=lang,
                clarification="Qaysi nomdagi kategoriya? Masalan: «Reklama kategoriyasini qo'sh».",
            )
        return ExtractionResult(
            intent=Intent.add_category,
            new_category_name=name,
            new_category_type=new_type,
            confidence=0.85,
            reply_language=lang,
        )

    # ---- delete last ----
    if _has(t, _DELETE):
        return ExtractionResult(intent=Intent.delete, confidence=0.8, reply_language=lang)

    # ---- report / question ----
    if _has(t, _REPORT):
        rtype = None
        if _has(t, _EXPENSE) and not _has(t, _INCOME):
            rtype = TxType.expense
        elif _has(t, _INCOME) and not _has(t, _EXPENSE):
            rtype = TxType.income
        return ExtractionResult(
            intent=Intent.report,
            report_period=_parse_period(t),
            report_category=category,
            report_type=rtype,
            confidence=0.8,
            reply_language=lang,
        )

    # ---- correction of last transaction ----
    if _has(t, _CORRECTION) or (re.search(r"\byo'?q\b", t) and amount):
        return ExtractionResult(
            intent=Intent.correction,
            amount=amount,
            category=category,
            occurred_at=when,
            confidence=0.7,
            reply_language=lang,
        )

    # ---- income / expense ----
    is_exp = _has(t, _EXPENSE)
    is_inc = _has(t, _INCOME)
    tx_type = None
    if is_exp and not is_inc:
        tx_type = TxType.expense
    elif is_inc and not is_exp:
        tx_type = TxType.income

    if tx_type and amount:
        return ExtractionResult(
            intent=Intent.income if tx_type == TxType.income else Intent.expense,
            tx_type=tx_type,
            amount=amount,
            category=category,
            occurred_at=when or today,
            confidence=0.9,
            reply_language=lang,
        )

    # ---- not enough info: ask, never fail silently ----
    if amount and not tx_type:
        msg = ("Это доход или расход? 🤔 Например: «расход 500 000»."
               if lang == "ru" else
               "Bu daromadmi yoki xarajat? 🤔 Masalan: «xarajat 500 ming».")
        return ExtractionResult(intent=Intent.unknown, amount=amount,
                                confidence=0.3, reply_language=lang, clarification=msg)
    if tx_type and not amount:
        msg = ("Укажите сумму. Например «500 тысяч» или «2 млн»."
               if lang == "ru" else
               "Summasini ayting. Masalan «500 ming» yoki «2 mln».")
        return ExtractionResult(intent=Intent.unknown, tx_type=tx_type,
                                confidence=0.3, reply_language=lang, clarification=msg)

    msg = ("Не понял 🤔 Напишите, например: «Сегодня с продаж пришло 2 млн»."
           if lang == "ru" else
           "Tushunolmadim 🤔 Masalan: «Bugun sotuvdan 2 mln keldi» deb yozing.")
    return ExtractionResult(intent=Intent.unknown, confidence=0.1,
                            reply_language=lang, clarification=msg)
