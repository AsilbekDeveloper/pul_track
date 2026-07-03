# PulTrack — Business Finance Manager 💼

Finance management for small/medium businesses in Uzbekistan. Log income and
expenses by simply **texting or sending a voice message to a Telegram bot**,
then track everything on a **multi-page web dashboard**.

> Built for the data365 agency assessment (Task 01).

- **Telegram bot** — text + voice, automatic transcription, intent detection,
  natural confirmations, follow-up questions, reports, corrections, custom
  categories. Never fails silently.
- **Web dashboard** — Overview, Transactions, Analytics, Categories,
  Onboarding + Telegram login, and monthly **Budget Alerts** (extra feature).
- **100% free to run** — local rule-based parser + local `faster-whisper` for
  voice. No OpenAI key required (OpenAI is optional).

---

## Architecture (split)

Three independently deployable pieces sharing one database, so a message sent
to the bot appears on the dashboard immediately:

```
        Frontend (static HTML/CSS/JS)          Backend (FastAPI, async)
        Vercel                                 Render
        ┌─────────────────────┐   JWT / REST   ┌──────────────────────────┐
        │ login (Telegram)    │ ─────────────► │ /api/*  (per-user, JWT)  │
        │ overview / tx /     │ ◄───────────── │ /api/auth/telegram       │
        │ analytics / cats    │                │ Telegram bot (webhook)   │
        └─────────────────────┘                └───────────┬──────────────┘
                                                            │
Telegram (text/voice) ──► faster-whisper ─► rule parser ─► │
                                                            ▼
                                              PostgreSQL (Supabase)
```

**Why it's fast:** fully async (FastAPI + `asyncpg` pool), Telegram webhook
ACKs immediately and processes in the background, all reports aggregate in SQL
(`SUM`/`GROUP BY`) over composite indexes, optional Redis for bot state.

## Tech stack

| Layer | Tech | Deploy |
|-------|------|--------|
| Frontend | Static HTML + Tailwind (CDN) + Chart.js + vanilla JS | **Vercel** |
| Backend | FastAPI, aiogram 3, SQLAlchemy 2 (async), PyJWT | **Render** |
| Database | PostgreSQL | **Supabase** |
| AI (free) | rule-based extractor + `faster-whisper` (local) | in backend |
| AI (optional) | OpenAI Whisper + GPT structured output | set `AI_PROVIDER=openai` |

## Project layout

```
app/                     BACKEND (FastAPI)
  main.py                app: API + auth + Telegram webhook
  config.py  db.py  models.py  schemas.py  security.py
  services/              transactions, categories, analytics, budgets, users
  ai/                    extract (dispatcher), rule_extract (free), transcribe, openai_*
  bot/                   pipeline (intent logic), handlers, instance
  web/                   api.py (JSON), auth.py, auth_routes.py
frontend/                FRONTEND (static, deploy to Vercel)
  index.html             login (Telegram widget + dev-login)
  overview/transactions/analytics/categories.html
  app.js  config.js  styles.css
scripts/seed_demo.py     demo data (no keys needed)
render.yaml  runtime.txt docker-compose.yml
```

---

## Run locally

### 0. Prerequisites
Python 3.11+, Docker (for local Postgres + Redis).

### 1. Backend
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # defaults already match docker-compose
docker compose up -d          # Postgres on host port 55432, Redis on 6379
python -m scripts.seed_demo   # optional: demo data (telegram id = 1)
uvicorn app.main:app --port 8000
```
Backend is now on http://localhost:8000 (`/docs` for the API).

### 2. Frontend
```bash
cd frontend
python -m http.server 5500
```
Open http://localhost:5500 → use **dev-login** (id = 1) to see the demo data.
(The Telegram widget needs a public domain, so local dev uses dev-login.)

### 3. Enable the Telegram bot (free)
1. Create a bot with [@BotFather](https://t.me/BotFather) → copy the token.
2. In `.env` set `TELEGRAM_BOT_TOKEN=...` (leave `AI_PROVIDER=local` — free).
3. Restart the backend. The bot starts in **long-polling** mode (no public
   URL needed). Message it: “Bugun sotuvdan 2 mln keldi”, or send a voice note.

> First voice message downloads the `faster-whisper` model once (a few seconds).

---

## Deploy (all free tiers)

**1. Database — Supabase**
Create a project → copy the connection string → convert to async form:
`postgresql+asyncpg://USER:PASS@HOST:5432/postgres`.

**2. Backend — Render** (Blueprint from `render.yaml`)
Set env vars: `DATABASE_URL` (Supabase), `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_WEBHOOK_SECRET` (random), `WEBHOOK_BASE_URL` (this service's URL),
`CORS_ORIGINS` (your Vercel URL). On startup the app auto-registers the
Telegram webhook. `AI_PROVIDER=local`, `WHISPER_MODEL=tiny` (fits free RAM).

**3. Frontend — Vercel**
Set project root to `frontend/`. Edit `frontend/config.js`:
`PULTRACK_API` = your Render URL, `PULTRACK_BOT_USERNAME` = your bot's username.

**4. Telegram Login Widget**
In @BotFather: `/setdomain` → your Vercel domain, so “Log in with Telegram”
works on the deployed dashboard. Reviewers can then log in and see only their
own data.

---

## Bot cheat-sheet

| You say | Bot does |
|---------|----------|
| "Bugun sotuvdan 2 mln keldi" | logs income 2,000,000 · Sotuv |
| "Logistikaga 500 ming xarajat" | logs expense 500,000 · Logistika |
| 🎤 voice note | transcribes (faster-whisper), then logs |
| "Bu oy logistikaga qancha ketdi?" | reports the total |
| "500 ming" (ambiguous) | asks: income or expense? |
| "oxirgisini o'chir" | deletes the last transaction |
| "yo'q, 300 ming edi" | corrects the last transaction |
| "Reklama kategoriyasini qo'sh" | creates a custom category |
| /categories, /help | utility commands |

---

## Product brief

PulTrack lets a busy Uzbek business owner record every som of income and
expense the fastest way possible — by texting or speaking to a Telegram bot in
Uzbek or Russian. Voice is transcribed locally, intent and amounts are parsed
("2 mln" → 2,000,000), and every entry is confirmed, with a follow-up whenever
something is unclear so nothing is lost. A separate web dashboard, secured by
Telegram login, turns that stream into a live picture per business: income vs
expense, category breakdowns, monthly trends, and budget alerts. It runs
entirely on free tiers, replacing messy Excel/paper bookkeeping with a
two-minute daily habit.

## What I'd add in 3 more days

Team workspaces (invite staff to one business with roles), richer reports
(natural-language summaries like "logistics up 32% vs last month", CSV/PDF
export, recurring-transaction detection), a large-amount confirmation step and
an edit audit log for the bot, proactive push notifications (weekly digest,
budget warnings), Redis-cached dashboard aggregates for instant loads, and a
labeled test set to measure and improve extraction accuracy.
