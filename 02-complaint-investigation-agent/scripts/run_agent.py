"""Quick CLI to run the agent against a single question and print its full
reasoning trail — useful for manual testing without spinning up Streamlit."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from src.agent.graph import agent_app


def main():
    question = " ".join(sys.argv[1:]) or input("Question: ")

    result = agent_app.invoke({"question": question})

    print("\n=== Reasoning trail ===")
    for i, (q, r) in enumerate(zip(result["plan"], result["results"]), 1):
        print(f"\n[{i}] SQL:\n{q}")
        if "error" in r:
            print(f"    ERROR: {r['error']}")
        else:
            print(f"    -> {r['row_count']} row(s){' (truncated)' if r.get('truncated') else ''}")

    print("\n=== Answer ===")
    print(result["answer"])


if __name__ == "__main__":
    main()