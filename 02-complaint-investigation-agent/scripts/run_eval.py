"""Runs the full evaluation harness against eval/eval_questions.json and prints
a summary plus per-question detail. Also writes the full results to
eval/eval_results.json so the real numbers can be pulled into the README."""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from src.evaluation.scorer import run_eval


def main():
    eval_path = os.path.join(os.path.dirname(__file__), "..", "eval", "eval_questions.json")
    with open(eval_path) as f:
        eval_set = json.load(f)

    print(f"Running {len(eval_set)} eval questions against the agent...\n")
    results = run_eval(eval_set)

    for r in results["details"]:
        status = "PASS" if r["correct"] else "FAIL"
        print(f"[{status}] #{r['id']} ({r['latency_sec']}s, {r['num_subqueries']} sub-quer{'y' if r['num_subqueries']==1 else 'ies'}) {r['question']}")
        if not r["correct"]:
            print(f"       -> {r['answer'][:300]}")

    print("\n=== Summary ===")
    print(f"Accuracy: {results['num_correct']}/{results['num_total']} ({results['accuracy']*100:.1f}%)")
    print(f"Avg latency: {results['avg_latency_sec']}s")
    print(f"Avg sub-queries per question: {results['avg_subqueries']}")

    out_path = os.path.join(os.path.dirname(__file__), "..", "eval", "eval_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results written to {out_path}")


if __name__ == "__main__":
    main()