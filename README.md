# J's Cleaners AI Receptionist

A voice AI receptionist ("Jenny") for J's Cleaners that answers calls in the browser, quotes exact prices from the owner's facts, takes callbacks when it can't help, and an owner dashboard to review calls and edit facts live.

## Live demo

| | |
|---|---|
| Call Jenny | https://js-receptionist.onrender.com |
| Owner dashboard | https://js-receptionist.onrender.com/owner |

Dashboard login is shared separately. Use made-up names and phone numbers when calling.

Hosted on Render's free tier (auto-deploys on every push to `main`).

## What it does

- **Voice call in the browser**: no phone number needed. Jenny says she's an AI and that the call is transcribed; callers can opt out.
- **Answers only from the facts**: prices, hours, rush, alterations, pickup and delivery. Totals come from a deterministic quote calculator, never from the LLM.
- **Callbacks**: collects first name, phone (read back digit by digit) and reason, and confirms only after it's saved.
- **Owner dashboard**: every call with time, length, transcript and outcome; callback queue; questions Jenny couldn't answer.
- **Editable facts, no redeploy**: edit prices, hours or rules, or answer an unanswered question, and the next call uses it. Every save is versioned and can be restored.

## Stack

| Layer | Choice |
|---|---|
| Voice pipeline | [Pipecat](https://github.com/pipecat-ai/pipecat) over WebSocket |
| Speech-to-text / text-to-speech | Deepgram Flux (turn detection server-side) / Aura-2 |
| LLM | Claude Haiku 5.5 via OpenRouter, with tool calls |
| Backend | Python, FastAPI, SQLAlchemy, Alembic |
| Database | Postgres |
| Frontend | React, TypeScript, Vite, Tailwind |
| Hosting | Render (Docker) |

## Run locally

```bash
cp .env.example .env        # add DEEPGRAM_API_KEY, OPENROUTER_API_KEY, OWNER_PASSWORD
docker compose up -d        # Postgres, backend (:8000), frontend (:5173)
```

Open http://localhost:5173 to call, http://localhost:5173/owner for the dashboard.

## Tests

```bash
cd backend
uv run --group dev pytest                # unit + API tests (API tests need the local Postgres)
uv run python -m tests.evals.run_evals   # scripted conversations against the real LLM (costs ~1 cent)
```

## Deploy

`render.yaml` is a Render Blueprint that creates the web service and its Postgres database. Secrets (`DEEPGRAM_API_KEY`, `OPENROUTER_API_KEY`, `OWNER_PASSWORD`) are entered once in Render. To add fictional demo calls to an empty database: `python -m app.seed_demo`.

## More

- [PLAN.md](PLAN.md): design decisions, schedule and backlog
- [ASSUMPTIONS.md](ASSUMPTIONS.md): decisions made where the spec was silent
