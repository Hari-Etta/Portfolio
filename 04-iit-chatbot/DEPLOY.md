# Deploying from scratch (free tier)

Anthropic is the only paid service in this setup. Everything else runs on a free plan.

| Piece | Service | Plan | What it does |
|---|---|---|---|
| Frontend | Netlify | Free (300 credits/mo) | Next.js UI plus the `/api/*` proxy routes |
| Backend | Render | Free web service | FastAPI orchestrator, rule engine, retrieval |
| Search and data | Neon Postgres | Free (1 GB, 100 CU-hrs/mo) | Policy chunks, pgvector embeddings, full-text index, feedback |
| Embeddings | Google Gemini API | Free tier | `gemini-embedding-2`, 768 dims |
| LLM | Anthropic | Pay-as-you-go | `claude-haiku-5-5` for routing, slot extraction and answer writing |

**Expected Anthropic cost.** Roughly $0.001 per message at Haiku 5.5 rates ($0.10 in / $0.50 out per million tokens). `DAILY_MESSAGE_CAP=300` puts a hard ceiling of about $0.30/day on it. Normal portfolio traffic should cost well under $1/month. Also set a monthly spend limit in the Anthropic Console (step 1).

---

## 0. Push the code to GitHub

This project lives inside the **Portfolio** repo (`C:\Users\harip\Documents\Portfolio`). Don't run `git init` in `04-iit-chatbot`; commit from the Portfolio root:

```powershell
cd C:\Users\harip\Documents\Portfolio
git status                      # should NOT list .env, .venv, node_modules, _to_delete or *.tgz
git add 04-iit-chatbot
git commit -m "iit-chatbot: free-tier stack (Neon pgvector, Gemini embeddings, Claude Haiku)"
git push
```

All paths below are relative to the Portfolio repo root.

## 1. Anthropic API key

1. Go to console.anthropic.com → **API Keys** → create a key and copy it (`sk-ant-...`).
2. Go to **Settings → Limits** and set a monthly spend limit, for example $5.

## 2. Gemini API key (free, no card)

1. Go to aistudio.google.com → **Get API key** → create a key.
2. Leave billing off so the key stays on the free tier.

Note: on Google's free tier, request content may be used to improve Google's products. Here that content is public IIT policy text plus the questions users type.

## 3. Neon database

1. Go to neon.com → **New project**.
   - Region: **AWS US East 2 (Ohio)**. It has to match Render's region in `render.yaml`.
   - Use the latest Postgres version.
2. Open **Connect**, turn on **Connection pooling**, and copy the connection string. It looks like `postgresql://...-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require`.
3. That's all. The backend creates the `vector` extension and all tables on first start.

## 4. Render backend

Render's one-click Blueprint looks for `render.yaml` at the repo root, and here it sits inside `04-iit-chatbot/`. So create the service by hand, using `04-iit-chatbot/render.yaml` as the reference for every value.

1. In Render, go to **New → Web Service**, connect GitHub and pick the Portfolio repo.
2. Settings:
   - **Root Directory:** `04-iit-chatbot/CB_Backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api_server:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
   - **Region:** Ohio (same as Neon)
   - **Advanced → Health Check Path:** `/api/ping`
   - **Advanced → Build Filters → Included Paths:** `04-iit-chatbot/CB_Backend/**`. Without it, pushes to your other portfolio projects would redeploy this backend.
3. Under **Environment**, add every key listed under `envVars` in `render.yaml`:
   - Plain values: copy them exactly as written, e.g. `PYTHON_VERSION=3.13.5`, `LLM_PROVIDER=anthropic`, `ANTHROPIC_MODEL=claude-haiku-5-5`, `GEMINI_EMBED_MODEL=gemini-embedding-2`, `EMBED_DIM=768`, `AUTO_INGEST=true`, the four `USE_LLM_*=true` flags, `RATE_LIMIT_PER_HOUR=30`, `DAILY_MESSAGE_CAP=300`.
   - `ANTHROPIC_API_KEY` from step 1.
   - `GEMINI_API_KEY` from step 2.
   - `DATABASE_URL`: the Neon pooled string from step 3.
   - `ALLOWED_ORIGINS`: `http://localhost:3000` for now. You'll update it in step 6.
   - `PROXY_SECRET` and `ADMIN_TOKEN`: generate two different random values with `python -c "import secrets;print(secrets.token_urlsafe(32))"`. Keep `PROXY_SECRET` for Netlify.
4. Click **Deploy**. On first boot the server indexes the 20 policy pages into Neon in the background. The logs show `Indexed N chunks from ...`, and it takes a few minutes. Chat replies "still loading" until indexing finishes.
5. Open `https://<your-service>.onrender.com/api/health`. You should see `"status": "ok"`, a `document_count` of a few hundred, and `"ingest": {"status": "done"}`.

The server pings its own `/api/ping` every 14 minutes, so Render's free instance stays awake and recruiters don't hit a one-minute cold start. One always-on service uses about 744 of Render's 750 free hours a month. Don't run a second Render service in the same workspace. The ping never touches the database, so Neon can still scale to zero.

## 5. Netlify frontend

1. Go to **Add new site → Import from GitHub** and pick the repo.
   - Base directory: `04-iit-chatbot/CB_Frontend`
   - The build command and publish dir come from `netlify.toml`.
2. Under **Environment variables**, set:
   - `BACKEND_URL` = `https://<your-service>.onrender.com`
   - `PROXY_SECRET` = the value copied from Render
3. Deploy. `netlify.toml` skips builds when nothing in `CB_Frontend/` changed, so backend-only commits don't spend Netlify credits. Each production deploy costs 15 of the 300 monthly credits.

## 6. Connect the two

In Render, set `ALLOWED_ORIGINS` to your Netlify URL, for example `https://iit-policy-bot.netlify.app`, and save. Render redeploys.

## 7. Smoke test

Ask the Netlify site:
- "How do I apply for CPT?" should give a retrieval answer with Sources.
- "Am I eligible for CPT?" should show the eligibility form (rule engine).
- "Can I work 40 hours?" should ask a clarifying question.
- "Write my SOP" should be refused as out of scope.

Read feedback (admin only):

```bash
curl -H "Authorization: Bearer <ADMIN_TOKEN>" https://<your-service>.onrender.com/api/feedback
```

---

## Local development (Windows / PowerShell)

Backend: one virtual environment per project, inside `CB_Backend` (already git-ignored).

```powershell
cd C:\Users\harip\Documents\Portfolio\04-iit-chatbot\CB_Backend
py -3.13 -m venv .venv                   # same Python version as Render
.\.venv\Scripts\Activate.ps1             # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
copy .env.example .env                   # then fill in ANTHROPIC_API_KEY, GEMINI_API_KEY, DATABASE_URL
uvicorn api_server:app --reload --port 8000
```

For `DATABASE_URL` locally, use either:
- **Docker:** `docker compose up -d`, then `postgresql://postgres:postgres@localhost:5432/iit_chatbot`.
- **A Neon dev branch:** in Neon, go to Branches → New branch `dev` (free) and use that branch's connection string. Never point local work at the production branch.

Frontend:

```powershell
cd ..\CB_Frontend
copy .env.example .env.local             # BACKEND_URL=http://localhost:8000
npm install
npm run dev
```

Tests run offline, with fake embeddings and no LLM. They **drop and rebuild tables**, so only ever point them at Docker or a throwaway Neon branch, never production:

```powershell
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/iit_chatbot"
pytest -q
```

## Changing the embedding model or dimension

The `embedding` column is created as `vector(EMBED_DIM)`. If you change `EMBED_DIM`, drop the table first:

```sql
DROP TABLE policy_chunks; DROP TABLE ingest_manifest;
```

Then restart, or run `python -m ingest.ingest --force`. Changing only `GEMINI_EMBED_MODEL` re-embeds automatically.
