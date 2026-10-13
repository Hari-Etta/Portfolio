from __future__ import annotations
"""Hybrid retrieval on Neon Postgres: full-text (keyword) + pgvector (semantic), fused with RRF, then topic reranking."""

from typing import List, Dict, Any, Optional
import logging
import re
from .config import SETTINGS
from .db import connection
from .embedding_service import embed_query

log = logging.getLogger("retrieval")

# Columns returned as the hit "_source" (same field names the Elasticsearch index used,
# so fuse_rrf / _rerank_hits / answer code are unchanged).
_SOURCE_COLS = [
    "text", "heading", "category", "policy_topic", "doc_title", "section_title",
    "section_path", "heading_level", "source_file", "source_url", "policy_version",
]

# OR-semantics keyword query, like Elasticsearch multi_match: plainto_tsquery ANDs
# every term, so we rewrite its operators to OR. ts_rank normalization 1 divides by
# 1 + log(doc length), a rough stand-in for BM25 length normalization.
_TSQ = "to_tsquery('english', replace(plainto_tsquery('english', %(q)s)::text, ' & ', ' | '))"
# Case-insensitive topic match: topic.py emits "f1_status_Travel" while the page's Doc_ID is
# "f1_status_travel"; the old case-sensitive Elasticsearch term filter silently matched nothing.
_FILTER = "(%(category)s::text IS NULL OR category = %(category)s) AND (%(topic)s::text IS NULL OR lower(policy_topic) = lower(%(topic)s))"


def _bm25_sql(k_name: str = "k") -> str:
    return (
        f"SELECT chunk_id, ts_rank(fts, {_TSQ}, 1)::float8 AS score, 'bm25' AS src "
        f"FROM {SETTINGS.chunks_table} WHERE fts @@ {_TSQ} AND {_FILTER} "
        f"ORDER BY score DESC, chunk_id LIMIT %({k_name})s"
    )


def _vec_sql(k_name: str = "k") -> str:
    return (
        f"SELECT chunk_id, (1 - (embedding <=> %(vec)s::vector))::float8 AS score, 'vec' AS src "
        f"FROM {SETTINGS.chunks_table} WHERE embedding IS NOT NULL AND {_FILTER} "
        f"ORDER BY embedding <=> %(vec)s::vector, chunk_id LIMIT %({k_name})s"
    )


def _vec_literal(vec: List[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in vec) + "]"


def _run(parts: List[str], params: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Run one or more ranked sub-queries in a single round trip; returns hits grouped by src."""
    union = " UNION ALL ".join(f"({p})" for p in parts)
    cols = ", ".join(f"c.{c}" for c in _SOURCE_COLS)
    sql = (
        f"SELECT x.src, x.score, c.chunk_id, {cols} FROM ({union}) x "
        f"JOIN {SETTINGS.chunks_table} c USING (chunk_id) ORDER BY x.src, x.score DESC, c.chunk_id"
    )
    out: Dict[str, List[Dict[str, Any]]] = {"bm25": [], "vec": []}
    with connection() as conn:
        for row in conn.execute(sql, params).fetchall():
            src, score, chunk_id, *vals = row
            out[src].append({"_id": chunk_id, "_score": float(score), "_source": dict(zip(_SOURCE_COLS, vals))})
    return out


def _params(query: str, category: Optional[str], topic: Optional[str], k: int) -> Dict[str, Any]:
    return {"q": query or "", "category": category, "topic": topic, "k": int(k)}


def bm25_search(query: str, *, category: Optional[str] = None, topic: Optional[str] = None, k: int = 8) -> List[Dict[str, Any]]:
    return _run([_bm25_sql()], _params(query, category, topic, k))["bm25"]


def vector_search(query: str, *, category: Optional[str] = None, topic: Optional[str] = None, k: int = 8) -> List[Dict[str, Any]]:
    p = _params(query, category, topic, k)
    p["vec"] = _vec_literal(embed_query(query))
    return _run([_vec_sql()], p)["vec"]


def _hybrid_lists(query: str, *, category: Optional[str], topic: Optional[str], k: int):
    """BM25 + vector lists in one database round trip. Degrades to BM25-only if embeddings fail."""
    p = _params(query, category, topic, k)
    try:
        p["vec"] = _vec_literal(embed_query(query))
    except Exception as exc:
        log.warning("query embedding failed, using keyword-only retrieval: %s", exc)
        return _run([_bm25_sql()], p)["bm25"], []
    res = _run([_bm25_sql(), _vec_sql()], p)
    return res["bm25"], res["vec"]



def fuse_rrf(bm25_hits: List[Dict[str, Any]], vec_hits: List[Dict[str, Any]], k: int = 8, rrf_k: int = 60) -> List[Dict[str, Any]]:
    scores = {}
    docs = {}

    def add(hits):
        for rank, h in enumerate(hits, start=1):
            doc_id = h.get("_id")
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (rrf_k + rank))
            docs[doc_id] = h

    add(bm25_hits)
    add(vec_hits)

    merged = []
    for doc_id, sc in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        h = docs[doc_id]
        h["rrf_score"] = sc
        merged.append(h)
    return merged[:k]


def _hit_text(h: Dict[str, Any]) -> str:
    s = h.get("_source") or {}
    return " ".join(
        str(x or "")
        for x in [
            s.get("policy_topic"),
            s.get("heading"),
            s.get("section_title"),
            s.get("section_path"),
            s.get("doc_title"),
            s.get("source_url") or s.get("url"),
            s.get("text"),
        ]
    ).lower()



def _hit_topic(h: Dict[str, Any]) -> str:
    s = h.get("_source") or {}
    return str(s.get("policy_topic") or "").lower()



def _hit_url(h: Dict[str, Any]) -> str:
    s = h.get("_source") or {}
    return str(s.get("source_url") or s.get("url") or "").lower()



def _rerank_hits(hits: List[Dict[str, Any]], query: str, intent: Optional[str], topic: Optional[str]) -> List[Dict[str, Any]]:
    if not hits:
        return hits

    q = (query or "").lower()
    intent = (intent or "").lower()

    boost_terms: List[str] = []
    penalize_terms: List[str] = []
    topic_boosts: Dict[str, float] = {}
    topic_penalties: Dict[str, float] = {}
    url_boosts: Dict[str, float] = {}

    if intent == "work_hours":
        boost_terms += ["20", "hours", "per week", "full-time", "full time", "official", "break", "vacation", "semester", "at least 20 hours"]
        if "j-1" not in q and "j1" not in q:
            penalize_terms += ["j-1", "j1", "ds-2019", "ds2019"]

    if any(x in q for x in ["report", "reporting", "employer", "address", "unemployment", "validation", "20 hours", "e-verify", "i-983"]):
        boost_terms += [
            "reporting requirements", "employment reporting", "change of employer", "address change",
            "unemployment", "validation report", "at least 20 hours", "e-verify", "form i-983",
            "material changes", "sevp portal", "isss portal"
        ]
        penalize_terms += ["initial opt request", "$100 opt administrative fee", "academic advisor details"]

    if any(x in q for x in ["stem opt", "uscis", "i-765", "60 days", "stem opt i-20", "before receiving the stem opt i-20"]):
        boost_terms += ["stem opt extension", "form i-765", "uscis", "within 60 days", "stem opt i-20", "completed form i-983", "$200 stem opt administrative fee"]
        penalize_terms += ["initial opt request", "$100 opt administrative fee"]

    if any(x in q for x in ["i-983", "training plan", "naics", "cip code", "requested period"]):
        boost_terms += ["form i-983", "training plan", "naics", "cip code", "requested period", "dso name", "sevis school code"]

    if (topic or "").lower().endswith("travel") or "travel" in q or "re-enter" in q or "reentry" in q:
        boost_terms += ["travel signature", "re-enter", "reentry", "visa", "i-20", "ds-2019", "passport"]

    if intent in {"contact_info", "portal_link"}:
        boost_terms += ["email", "phone", "contact", "office", "hours", "walk-in", "address", "portal", "forms", "form", "request", "link", "isss", "ogs"]

    if "check-in" in q or "check in" in q:
        boost_terms += ["24 hours", "within 24 hours", "two business days", "isss portal", "check-in after arrival"]
        topic_boosts["f1_status_new_student_check_in"] = max(topic_boosts.get("f1_status_new_student_check_in", 0.0), 1.1)

    if any(x in q for x in ["processing time", "how long does ogs", "program deadline", "submit immigration-related requests", "typically take to process"]):
        boost_terms += ["apply as early as possible", "late or rushed requests", "7 business days", "seven 7 business days", "students should plan ahead"]
        topic_boosts["f1_status_processing_times"] = max(topic_boosts.get("f1_status_processing_times", 0.0), 1.15)
        topic_penalties["f1_status_forms_and_requests"] = max(topic_penalties.get("f1_status_forms_and_requests", 0.0), 0.25)

    if any(x in q for x in ["fewer credits", "required credits", "without informing ogs", "below full-time", "full-time enrollment"]):
        boost_terms += ["negatively impact immigration status", "full-time enrollment", "add/drop deadline", "reduced course load", "violation of status"]
        topic_boosts["f1_status_enrollment_requirements"] = max(topic_boosts.get("f1_status_enrollment_requirements", 0.0), 1.1)
        topic_boosts["f1_status_reduced_course_load"] = max(topic_boosts.get("f1_status_reduced_course_load", 0.0), 0.5)

    if any(x in q for x in ["acceptable reasons", "reasons for rcl", "reasons for reduced course load", "grounds for rcl"]):
        boost_terms += ["completion of program", "qualifying/comprehensive exam", "academic difficulties", "medical condition"]
        topic_boosts["f1_status_reduced_course_load"] = max(topic_boosts.get("f1_status_reduced_course_load", 0.0), 1.15)

    if any(x in q for x in ["change of status", "change to f-1"]) and any(x in q for x in ["documents", "must submit", "required", "application materials"]):
        boost_terms += ["prepare application materials", "completed form i-539", "completed form g-1145", "sevis fee receipt", "cover letter", "original financial documents", "original i-94"]
        topic_boosts["f1_status_change_to_f1_j1"] = max(topic_boosts.get("f1_status_change_to_f1_j1", 0.0), 1.15)

    if "grace period" in q:
        boost_terms += ["grace", "period", "days", "after graduation"]

    if "unauthorized" in q or "consequence" in q or "violation" in q:
        boost_terms += ["unauthorized", "violation", "status", "terminate", "termination", "sevis"]
        if "j-1" not in q and "j1" not in q:
            penalize_terms += ["j-1", "j1"]


    # Health insurance + SHWC + SSN family reranking
    fee_cues = [
        "health insurance fee", "student health insurance fee", "mandatory fee", "mandatory and other fees",
        "student accounting", "tuition and fees", "charge on their bill", "charged by illinois tech",
        "health insurance charge", "bill", "billed"
    ]
    ship_cues = [
        "health insurance plan", "automatically enrolled", "mandatory for international", "required to purchase",
        "waiver", "waive", "comparable coverage", "aetna", "one academic credit hour", "one billable hour",
        "health insurance mandatory", "insurance obligation", "enrolled in the illinois tech health insurance plan"
    ]
    shwc_cues = [
        "student health and wellness center", "shwc", "appointment", "medical assistance", "medical care",
        "care hub", "counseling", "wellness", "health support"
    ]
    ssn_cues = [
        "ssn", "social security", "social security number", "ssa", "ss-5", "ssn support letter", "seo"
    ]

    if any(x in q for x in fee_cues):
        boost_terms += ["student health insurance", "mandatory and other fees", "student accounting", "billable hour", "health insurance is assessed"]
        topic_boosts["health_insurance_student_fees"] = 1.25
        topic_penalties["employment_on_campus"] = 0.6
        url_boosts["student-accounting/tuition-and-fees/mandatory-and-other-fees"] = 0.8

    if any(x in q for x in ship_cues) or ("health insurance" in q and ("international student" in q or "international students" in q)):
        boost_terms += ["illinois tech student health insurance plan", "all students will be added", "required to purchase", "waiver", "comparable coverage", "one academic credit hour", "one billable hour", "does not affect services"]
        topic_boosts["health_insurance_ship_waiver"] = max(topic_boosts.get("health_insurance_ship_waiver", 0.0), 1.2)
        url_boosts["/shwc/insurance/students"] = 0.75

    if any(x in q for x in shwc_cues):
        boost_terms += ["student health and wellness center", "care hub", "call shwc", "email", "counseling", "medical care", "appointment"]
        topic_boosts["health_insurance_shwc_services"] = max(topic_boosts.get("health_insurance_shwc_services", 0.0), 1.15)
        topic_penalties["employment_on_campus"] = max(topic_penalties.get("employment_on_campus", 0.0), 0.9)
        url_boosts["/shwc"] = max(url_boosts.get("/shwc", 0.0), 0.55)

    if any(x in q for x in ssn_cues):
        boost_terms += ["social security number", "ssn", "ssa", "ss-5", "support letter", "job offer", "isss portal"]
        topic_boosts["health_insurance_ssn"] = max(topic_boosts.get("health_insurance_ssn", 0.0), 1.2)
        topic_penalties["employment_on_campus"] = max(topic_penalties.get("employment_on_campus", 0.0), 0.7)
        url_boosts["social-security-number"] = 0.8

    if "off-campus" in q and "shwc" in q:
        boost_terms += ["health insurance choice does not affect services"]
        topic_boosts["health_insurance_ship_waiver"] = max(topic_boosts.get("health_insurance_ship_waiver", 0.0), 1.3)
        topic_penalties["health_insurance_shwc_services"] = max(topic_penalties.get("health_insurance_shwc_services", 0.0), 0.3)

    if ("medical" in q or "health" in q or "shwc" in q) and not any(x in q for x in ["job", "employment", "work", "hours"]):
        topic_penalties["employment_on_campus"] = max(topic_penalties.get("employment_on_campus", 0.0), 1.0)

    def score(h: Dict[str, Any]) -> float:
        t = _hit_text(h)
        hit_topic = _hit_topic(h)
        hit_url = _hit_url(h)
        sc = float(h.get("rrf_score") or 0.0)

        for term in boost_terms:
            if term in t:
                sc += 0.25
        for term in penalize_terms:
            if term in t:
                sc -= 0.40

        for tname, bonus in topic_boosts.items():
            if hit_topic == tname:
                sc += bonus
        for tname, penalty in topic_penalties.items():
            if hit_topic == tname:
                sc -= penalty
        for frag, bonus in url_boosts.items():
            if frag in hit_url:
                sc += bonus

        if "f-1" in q or "f1" in q:
            if "f-1" in t or "f1" in t:
                sc += 0.2
            if "j-1" in t or "j1" in t:
                sc -= 0.2
        return sc

    return sorted(hits, key=score, reverse=True)



def hybrid_retrieve(
    query: str,
    *,
    category: Optional[str] = None,
    topic: Optional[str] = None,
    intent: Optional[str] = None,
    k: int = 8,
) -> List[Dict[str, Any]]:
    bm, ve = _hybrid_lists(query, category=category, topic=topic, k=k)
    fused = fuse_rrf(bm, ve, k=k)

    if topic and not fused:
        bm2, ve2 = _hybrid_lists(query, category=category, topic=None, k=k)
        fused = fuse_rrf(bm2, ve2, k=k)

    fused = _rerank_hits(fused, query=query, intent=intent, topic=topic)
    return fused[:k]
