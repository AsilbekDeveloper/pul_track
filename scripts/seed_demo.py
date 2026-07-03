"""Populate the DB with a demo business so the dashboard has data to show
WITHOUT needing OpenAI/Telegram keys.

Run:  python -m scripts.seed_demo
Then: DASHBOARD_USER_ID=1  (or leave empty — it's the only/most-recent user)
"""
import asyncio
import random
from datetime import date, timedelta

from app.db import SessionFactory, engine
from app.models import Base, TxSource, TxType
from app.services import budgets
from app.services import categories as cat_service
from app.services import transactions as tx_service
from app.services.users import get_or_create_user

DEMO_TELEGRAM_ID = 1

EXPENSE_MIX = [
    ("Logistika", (200_000, 900_000)),
    ("Ijara", (2_000_000, 2_000_000)),
    ("Maosh", (1_500_000, 4_000_000)),
    ("Marketing", (300_000, 1_200_000)),
    ("Xomashyo", (500_000, 2_500_000)),
    ("Kommunal", (150_000, 600_000)),
]
INCOME_MIX = [
    ("Sotuv", (1_000_000, 6_000_000)),
    ("Xizmat", (500_000, 3_000_000)),
]


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionFactory() as session:
        user = await get_or_create_user(session, DEMO_TELEGRAM_ID, "Demo Biznes")
        await session.commit()

        cats = {c.name: c for c in await cat_service.list_categories(session, user.id)}
        today = date.today()

        # 90 days of activity
        for day_offset in range(0, 90):
            d = today - timedelta(days=day_offset)
            # income most days
            if random.random() < 0.6:
                name, (lo, hi) = random.choice(INCOME_MIX)
                await tx_service.create_transaction(
                    session, user_id=user.id, type=TxType.income,
                    amount=round(random.uniform(lo, hi), -3),
                    occurred_at=d, category_id=cats[name].id, source=TxSource.web,
                )
            # a few expenses
            for _ in range(random.randint(0, 2)):
                name, (lo, hi) = random.choice(EXPENSE_MIX)
                await tx_service.create_transaction(
                    session, user_id=user.id, type=TxType.expense,
                    amount=round(random.uniform(lo, hi), -3),
                    occurred_at=d, category_id=cats[name].id, source=TxSource.web,
                )

        # A tight marketing budget this month -> triggers an alert on the dashboard
        await budgets.upsert_budget(
            session, user.id,
            month=today.strftime("%Y-%m"),
            limit_amount=1_500_000,
            category_id=cats["Marketing"].id,
        )
        await session.commit()

    await engine.dispose()
    print("Seed complete. Demo user telegram_id =", DEMO_TELEGRAM_ID)


if __name__ == "__main__":
    asyncio.run(main())
