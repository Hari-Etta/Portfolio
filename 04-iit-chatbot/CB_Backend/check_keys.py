"""Quick check that the API keys in .env work. Never prints the keys themselves."""
from dotenv import dotenv_values

env = dotenv_values(".env")

# Anthropic (one tiny call, costs a fraction of a cent)
key = env.get("ANTHROPIC_API_KEY", "")
print("Anthropic key starts with:", key[:13])
try:
    import anthropic
    r = anthropic.Anthropic(api_key=key).messages.create(
        model="claude-haiku-5-5",
        max_tokens=200,
        system="Reply with one word.",
        messages=[{"role": "user", "content": "Say OK"}],
        output_config={"effort": "low"},
    )
    print("Anthropic OK ->", "".join(b.text for b in r.content if b.type == "text"))
except Exception as e:
    print("Anthropic FAILED ->", type(e).__name__, str(e)[:200])

# Gemini embeddings (free tier)
try:
    from google import genai
    from google.genai import types
    g = genai.Client(api_key=env.get("GEMINI_API_KEY", ""))
    r = g.models.embed_content(
        model="gemini-embedding-2",
        contents="task: search result | query: How do I apply for CPT?",
        config=types.EmbedContentConfig(output_dimensionality=768),
    )
    print("Gemini OK -> embedding size", len(r.embeddings[0].values))
except Exception as e:
    print("Gemini FAILED ->", type(e).__name__, str(e)[:200])