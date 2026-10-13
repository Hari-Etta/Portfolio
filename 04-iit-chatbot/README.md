# IIT International Student Policy Chatbot

Answers F-1 immigration and compliance questions for Illinois Tech international students. Answers are grounded in official IIT policy pages and include source citations. Eligibility decisions come from a deterministic rule engine, not the LLM.

- `CB_Backend/`: FastAPI orchestrator, rule engine, hybrid retrieval on Neon Postgres (pgvector + full-text), Claude for answer writing
- `CB_Frontend/`: Next.js / TypeScript chat UI with server-side API proxy routes
- [`DEPLOY.md`](DEPLOY.md): free-tier deployment (Netlify + Render + Neon + Gemini embeddings; Anthropic is the only paid service)

> Not legal advice. For official determinations, contact the IIT Office of Global Services.
