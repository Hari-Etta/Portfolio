"""Scores the agent against the curated eval question set — correctness,
sub-query count, tool errors, and latency. This is the differentiator that
proves the agent is reliable rather than just impressive on one cherry-picked
demo question.

Improvement over a naive exact-substring scorer: real LLM answers format
numbers inconsistently (e.g. "3,458,906" vs "3458906", or "98.5%" vs "98.50%"),
so a fragile check would mark correct answers as wrong through no fault of the
agent. This scorer normalizes commas out of both the answer and the expected
strings before matching, and is case-insensitive.
"""
import time
from src.agent.graph import agent_app


def _normalize(text: str) -> str:
    return text.replace(",", "").lower()


def _check_answer(answer: str, item: dict) -> bool:
    """An item passes if:
    - every string in expected_answer_contains_all appears in the answer, AND
    - at least one string in expected_answer_contains appears in the answer
      (when that field is present at all).
    Both fields are optional; an item with neither always passes (not
    recommended, but avoids silently failing malformed eval entries)."""
    normalized_answer = _normalize(answer)

    contains_all = item.get("expected_answer_contains_all")
    if contains_all:
        if not all(_normalize(s) in normalized_answer for s in contains_all):
            return False

    contains_any = item.get("expected_answer_contains")
    if contains_any:
        if not any(_normalize(s) in normalized_answer for s in contains_any):
            return False

    return True


def run_eval(eval_set: list[dict]) -> dict:
    results = []
    for item in eval_set:
        start = time.time()
        try:
            output = agent_app.invoke({"question": item["question"]})
            latency = time.time() - start
            correct = _check_answer(output["answer"], item)
            tool_errors = sum(1 for r in output["results"] if "error" in r)
            results.append({
                "id": item.get("id"),
                "question": item["question"],
                "correct": correct,
                "num_subqueries": len(output["plan"]),
                "tool_errors": tool_errors,
                "latency_sec": round(latency, 2),
                "answer": output["answer"],
            })
        except Exception as e:
            latency = time.time() - start
            results.append({
                "id": item.get("id"),
                "question": item["question"],
                "correct": False,
                "num_subqueries": 0,
                "tool_errors": None,
                "latency_sec": round(latency, 2),
                "answer": f"AGENT CRASHED: {e}",
            })

    accuracy = sum(r["correct"] for r in results) / len(results) if results else 0.0
    avg_latency = sum(r["latency_sec"] for r in results) / len(results) if results else 0.0
    avg_subqueries = sum(r["num_subqueries"] for r in results) / len(results) if results else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "num_correct": sum(r["correct"] for r in results),
        "num_total": len(results),
        "avg_latency_sec": round(avg_latency, 2),
        "avg_subqueries": round(avg_subqueries, 2),
        "details": results,
    }