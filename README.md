# PulTrack — Business Finance Manager 💼

Finance management for small/medium businesses in Uzbekistan. Log income and
expenses by simply **texting or sending a voice message to a Telegram bot**,
then track everything on a **multi-page web dashboard**.

> Built for the data365 agency assessment (Task 01).

## 🔴 Live demo

| | |
|---|---|
| **Telegram bot** | [@pul_track_finance_bot](https://t.me/pul_track_finance_bot) |
| **Dashboard** | https://pul-track.vercel.app |
| **Backend API** | https://pultrack-api.onrender.com (`/docs` for OpenAPI) |

> ⚠️ Backend runs on Render's **free tier**: it spins down after 15 minutes of
> inactivity, so the *first* request after a while can take 30–50s to wake up.
> Message the bot once first to warm it up before opening the dashboard.

- **Telegram bot** — text + voice, automatic transcription, intent detection,
  natural confirmations, follow-up questions, reports, corrections, custom
  categories. Never fails silently, even with garbled voice transcription.
- **Web dashboard** — Overview, Transactions, Analytics, Categories,
  Onboarding + Telegram login (each user sees only their own data), and
  monthly **Budget Alerts** (extra feature).
- **Free-tier AI** — Groq (free API) runs both voice transcription
  (Whisper large-v3) and message understanding (Llama 3.3 70B), so parsing is
  robust even against messy transcriptions. Falls back to a fully offline
  rule-based parser + local `faster-whisper` if no Groq key is set — so the
  whole project can run with **zero API costs**.

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
Telegram (text/voice) ──► Groq Whisper large-v3 ─► Groq Llama 3.3 ─► │
                          (or local faster-whisper + rule parser)   │
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
| AI (primary, free) | Groq — Whisper large-v3 (voice) + Llama 3.3 70B (parsing) | set `GROQ_API_KEY` |
| AI (offline fallback) | rule-based extractor + `faster-whisper` (local) | no keys needed |
| AI (optional, paid) | OpenAI Whisper + GPT structured output | set `AI_PROVIDER=openai` |

## Project layout

```
app/                     BACKEND (FastAPI)
  main.py                app: API + auth + Telegram webhook
  config.py  db.py  models.py  schemas.py  security.py
  services/              transactions, categories, analytics, budgets, users
  ai/                    extract (dispatcher), groq_extract (primary), rule_extract (offline
                         fallback), transcribe (Groq/local), openai_* (optional)
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
2. In `.env` set `TELEGRAM_BOT_TOKEN=...`.
3. (Recommended) Get a **free** Groq key at
   [console.groq.com/keys](https://console.groq.com/keys) (no card) and set
   `GROQ_API_KEY=...` — this gives much better accuracy on messy/accented
   Uzbek voice than the offline fallback. Without it, the bot still works
   fully offline via the rule-based parser + local `faster-whisper`.
4. Restart the backend. The bot starts in **long-polling** mode (no public
   URL needed). Message it: “Bugun sotuvdan 2 mln keldi”, or send a voice note.

> Without `GROQ_API_KEY`, the first voice message downloads the local
> `faster-whisper` model once (a few seconds).

---

## Deploy (all free tiers — this is exactly how the live demo above is deployed)

**1. Database — Supabase**
Create a project → Connect → **Transaction pooler** → copy the URI → convert
to async form: `postgresql+asyncpg://postgres.PROJECT:PASSWORD@HOST:6543/postgres`.
`app/db.py` already disables asyncpg's statement cache for pgbouncer compatibility.

**2. Backend — Render** (Web Service, Python; `render.yaml` documents the env vars)
Root: repo root. Build: `pip install -r requirements.txt`. Start:
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add a `PYTHON_VERSION=3.11.9`
env var (Render defaults to a newer Python that breaks `pydantic-core`'s build).
Set: `DATABASE_URL` (Supabase, above), `TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`
(free, from [console.groq.com](https://console.groq.com/keys)),
`TELEGRAM_WEBHOOK_SECRET` (random string), `WEBHOOK_BASE_URL` (this service's
own URL, e.g. `https://pultrack-api.onrender.com`), `CORS_ORIGINS` (your Vercel
URL, comma-separated if you have both the custom and auto-generated domain).
On startup the app auto-registers the Telegram webhook at `WEBHOOK_BASE_URL`.

**3. Frontend — Vercel**
Import the repo → set **Root Directory** to `frontend` → no build command
needed (static files) → Deploy. Then edit `frontend/config.js`:
`PULTRACK_API` = your Render URL, `PULTRACK_BOT_USERNAME` = your bot's
username → commit + push (Vercel redeploys automatically).

**4. Telegram Login Widget**
In @BotFather: `/mybots` → your bot → **Bot Settings** → **Domain** →
**Set domain** → type your Vercel domain (e.g. `pul-track.vercel.app`) as a
plain chat message. Reviewers can then log in with their own Telegram account
and see only their own data.

---

## Bot cheat-sheet

| You say | Bot does |
|---------|----------|
| "Bugun sotuvdan 2 mln keldi" | logs income 2,000,000 · Sotuv |
| "Logistikaga 500 ming xarajat" | logs expense 500,000 · Logistika |
| 🎤 voice note | transcribes (Groq Whisper large-v3, or local fallback), then logs |
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
Uzbek or Russian. Voice is transcribed and understood by free AI (Groq), intent
and amounts are parsed ("2 mln" → 2,000,000), and every entry is confirmed, with a follow-up whenever
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
