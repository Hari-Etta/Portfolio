"""Checks the Neon connection and pgvector. Never prints the password."""
from dotenv import dotenv_values
import psycopg

url = dotenv_values(".env").get("DATABASE_URL", "")
print("Host:", url.split("@")[-1].split("/")[0] if "@" in url else "(DATABASE_URL not set)")
try:
    with psycopg.connect(url, prepare_threshold=None, connect_timeout=15) as conn:
        print("Connected ->", conn.execute("select version()").fetchone()[0][:40])
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("pgvector OK ->", conn.execute("select extversion from pg_extension where extname='vector'").fetchone()[0])
except Exception as e:
    print("FAILED ->", type(e).__name__, str(e)[:200])