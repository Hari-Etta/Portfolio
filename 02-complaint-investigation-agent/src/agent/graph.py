"""LangGraph state machine: the agent plans concrete SQL sub-queries from a
plain-English question, executes them through the guardrailed SQL tool, and
synthesizes a grounded answer. The full plan/results trail is kept visible in
state rather than hidden inside a single opaque LLM call — this is what lets a
non-technical stakeholder actually trust the answer.
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict
from langchain_anthropic import ChatAnthropic
import json
import re

from src.tools.sql_tool import execute_sql_tool
from src.data.schema_reference import SCHEMA_DESCRIPTION
from src.agent.prompts import PLAN_SYSTEM_PROMPT, SYNTHESIZE_SYSTEM_PROMPT

# claude-haiku-4-5 confirmed working against this account during setup; cheap
# enough that the full eval harness costs well under $1 to run repeatedly.
MODEL_NAME = "claude-haiku-4-5"

# How many result rows (per sub-query) get sent back into the synthesis prompt.
# Keeps token usage bounded even if a sub-query legitimately returns hundreds of rows.
MAX_ROWS_IN_SYNTHESIS_CONTEXT = 20


class AgentState(TypedDict):
    question: str
    plan: list[str]           # sub-queries the agent decided to run
    results: list[dict]        # tool outputs, one per sub-query (same order as plan)
    answer: str


def _get_llm() -> ChatAnthropic:
    # Lazily constructed so importing this module doesn't require ANTHROPIC_API_KEY
    # to already be set (useful for tests that only exercise the tools).
    return ChatAnthropic(model=MODEL_NAME)


def _extract_json_array(text: str) -> list[str]:
    """The model is asked to return only a JSON array, but strip markdown code
    fences defensively in case it adds them anyway."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    parsed = json.loads(cleaned)
    if not isinstance(parsed, list):
        raise ValueError(f"Expected a JSON array of SQL strings, got: {type(parsed)}")
    return [str(q) for q in parsed]


def plan_step(state: AgentState) -> AgentState:
    """Breaks the question into concrete SQL sub-queries, grounded in the real schema."""
    llm = _get_llm()
    prompt = PLAN_SYSTEM_PROMPT.format(schema=SCHEMA_DESCRIPTION)
    response = llm.invoke([
        {"role": "system", "content": prompt},
        {"role": "user", "content": state["question"]},
    ])
    try:
        state["plan"] = _extract_json_array(response.content)
    except (json.JSONDecodeError, ValueError):
        # Fall back to treating the whole response as a single query attempt rather
        # than crashing the graph — the guardrail will reject it if it's not valid SQL,
        # and the failure is still visible in the reasoning trail.
        state["plan"] = [response.content.strip()]
    return state


def execute_step(state: AgentState) -> AgentState:
    """Executes each planned sub-query through the guardrailed tool and records the
    results — including errors, so a blocked/failed query is still visible in the trail."""
    state["results"] = [execute_sql_tool(sql) for sql in state["plan"]]
    return state


def _trim_result_for_context(result: dict) -> dict:
    """Caps how many rows of a tool result get sent into the synthesis prompt."""
    if "result" not in result:
        return result
    rows = result["result"]
    if len(rows) <= MAX_ROWS_IN_SYNTHESIS_CONTEXT:
        return result
    return {
        **result,
        "result": rows[:MAX_ROWS_IN_SYNTHESIS_CONTEXT],
        "note": f"showing first {MAX_ROWS_IN_SYNTHESIS_CONTEXT} of {len(rows)} rows",
    }


def synthesize_step(state: AgentState) -> AgentState:
    """Synthesizes a final grounded answer from the tool results, citing the
    reasoning trail rather than hallucinating a number."""
    llm = _get_llm()
    context_parts = []
    for q, r in zip(state["plan"], state["results"]):
        trimmed = _trim_result_for_context(r)
        context_parts.append(f"Query: {q}\nResult: {json.dumps(trimmed)}")
    context = "\n\n".join(context_parts)

    user_prompt = f"Question: {state['question']}\n\nQuery results:\n{context}"
    response = llm.invoke([
        {"role": "system", "content": SYNTHESIZE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])
    state["answer"] = response.content
    return state


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("plan", plan_step)
    graph.add_node("execute", execute_step)
    graph.add_node("synthesize", synthesize_step)
    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


# Compiled once at import time — LangGraph graphs are cheap to build and this
# keeps every caller (Streamlit app, eval harness, scripts) using one instance.
agent_app = build_graph()