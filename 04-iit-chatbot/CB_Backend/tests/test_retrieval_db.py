from conftest import requires_db

pytestmark = requires_db


def _fresh_ingest():
    from backend.config import SETTINGS
    from backend.db import connection
    from ingest.ingest import ingest

    with connection() as conn:
        conn.execute(f"DROP TABLE IF EXISTS {SETTINGS.chunks_table}")
        conn.execute("DROP TABLE IF EXISTS ingest_manifest")
    return ingest()


def test_ingest_is_idempotent_and_complete():
    from backend.db import chunk_count
    from ingest.ingest import ingest, iter_md_files

    n = _fresh_ingest()
    assert n > 0
    assert chunk_count() > 0
    assert len(iter_md_files()) == 20
    assert ingest() == 0  # second run: nothing changed


def test_bm25_vector_and_hybrid_return_es_shaped_hits():
    from backend.retrieval import bm25_search, hybrid_retrieve, vector_search

    _fresh_ingest()
    q = "How do I apply for CPT curricular practical training?"
    for hits in (bm25_search(q, k=5), vector_search(q, k=5), hybrid_retrieve(q, k=5)):
        assert 0 < len(hits) <= 5
        h = hits[0]
        assert set(h) >= {"_id", "_source"}
        assert h["_source"]["text"] and h["_source"]["policy_topic"]
    assert hybrid_retrieve(q, k=5)[0]["_source"]["policy_topic"] == "employment_cpt"


def test_topic_filter_and_or_semantics():
    from backend.retrieval import bm25_search

    _fresh_ingest()
    hits = bm25_search("travel signature passport visa", topic="f1_status_Travel", k=8)
    assert hits and all(h["_source"]["policy_topic"].lower() == "f1_status_travel" for h in hits)
    # OR semantics: a nonsense word must not make the whole keyword query return nothing
    assert bm25_search("CPT zzzqqqxx", k=3)


def test_falls_back_to_keyword_only_when_embedding_fails(monkeypatch):
    import backend.retrieval as r

    _fresh_ingest()

    def boom(_):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(r, "embed_query", boom)
    assert r.hybrid_retrieve("OPT unemployment days", k=5)


def test_orchestrator_end_to_end_without_llm():
    from backend.orchestrator import chat_turn

    _fresh_ingest()
    out = chat_turn("What documents do I need to travel outside the US and re-enter?")
    assert out["mode"] in {"retrieval", "clarify", "clarify_topic"}
    assert out["answer_markdown"]
    out = chat_turn("Am I eligible for CPT?")
    assert out["mode"] == "rules"
