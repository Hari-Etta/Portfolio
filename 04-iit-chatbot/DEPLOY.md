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

From the project folder:

```bash
git init
git add .
git commit -m "Free-tier stack: Neon pgvector, Gemini embeddings, Claude Haiku"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Check that no `.env` file got committed. `.gitignore` already excludes it.

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

1. In the Render dashboard, go to **New → Blueprint** and pick your repo. Render reads `render.yaml`.
2. Fill in the secret values when prompted:
   - `ANTHROPIC_API_KEY` from step 1
   - `GEMINI_API_KEY` from step 2
   - `DATABASE_URL`: the Neon pooled string from step 3
   - `ALLOWED_ORIGINS`: put `http://localhost:3000` for now. You'll update it in step 6.

   `PROXY_SECRET` and `ADMIN_TOKEN` are generated automatically.
3. Deploy. On first boot the server indexes the 20 policy pages into Neon in the background. The logs show `Indexed N chunks from ...`, and it takes a few minutes. Chat replies "still loading" until indexing finishes.
4. Open `https://<your-service>.onrender.com/api/health`. You should see `"status": "ok"`, a `document_count` of a few hundred, and `"ingest": {"status": "done"}`.
5. Go to **Environment** and copy the value of `PROXY_SECRET`. You need it for Netlify.

If Blueprints aren't available on your account, create the service with **New → Web Service** instead and use the same settings:
- Root dir `CB_Backend`
- Build `pip install -r requirements.txt`
- Start `uvicorn api_server:app --host 0.0.0.0 --port $PORT`
- Health check `/api/ping`
- Instance type **Free**
- The env vars from `render.yaml`. Generate your own `PROXY_SECRET` and `ADMIN_TOKEN`, for example with `python -c "import secrets;print(secrets.token_urlsafe(32))"`.

The server pings its own `/api/ping` every 14 minutes, so Render's free instance stays awake and recruiters don't hit a one-minute cold start. One always-on service uses about 744 of Render's 750 free hours a month. Don't run a second Render service in the same workspace. The ping never touches the database, so Neon can still scale to zero.

## 5. Netlify frontend

1. Go to **Add new site → Import from GitHub** and pick the repo.
   - Base directory: `CB_Frontend`
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

## Local development

```bash
cd CB_Backend
docker compose up -d                     # Postgres + pgvector on :5432
cp .env.example .env                     # add your ANTHROPIC_API_KEY and GEMINI_API_KEY
pip install -r requirements-dev.txt
python -m ingest.ingest                  # or let the server do it on startup
uvicorn api_server:app --reload --port 8000

cd ../CB_Frontend
cp .env.example .env.local               # BACKEND_URL=http://localhost:8000
npm install && npm run dev
```

Tests run offline with fake embeddings and no LLM:

```bash
cd CB_Backend
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/iit_chatbot pytest -q
```

## Changing the embedding model or dimension

The `embedding` column is created as `vector(EMBED_DIM)`. If you change `EMBED_DIM`, drop the table first:

```sql
DROP TABLE policy_chunks; DROP TABLE ingest_manifest;
```

Then restart, or run `python -m ingest.ingest --force`. Changing only `GEMINI_EMBED_MODEL` re-embeds automatically.
