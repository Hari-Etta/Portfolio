"""Streamlit chat UI for the Complaint Investigation Agent.

Shows the question, the agent's answer, and — critically — the full reasoning
trail (every SQL sub-query it ran, in order, with row counts or errors) so a
non-technical stakeholder can verify the answer rather than take it on faith.
This transparency is one of the project's three core differentiators.
"""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.agent.graph import agent_app

st.set_page_config(page_title="Complaint Investigation Agent", page_icon="🔎", layout="wide")

st.title("🔎 Complaint Investigation Agent")
st.caption(
    "Self-serve agentic assistant over the real, public CFPB Consumer Complaint Database "
    "(2011–2023, 3.4M+ complaints). Ask a business question in plain English — the exact "
    "SQL sub-queries the agent ran are shown below every answer, not just a final number."
)

with st.expander("What can I ask?", expanded=False):
    st.markdown(
        """
        Try questions like:
        - *Which product had the most complaints last year?*
        - *What percentage of mortgage complaints got a timely response?*
        - *Compare complaint volume between California and Texas.*
        - *Which company has the most complaints, and what's the top issue for them?*

        Every query is validated by a guardrail before it ever runs against BigQuery —
        only read-only SELECT queries are permitted, and destructive keywords
        (DELETE, DROP, UPDATE, etc.) are blocked outright.
        """
    )

if "history" not in st.session_state:
    st.session_state.history = []  # list of (question, agent_output) tuples

question = st.chat_input("Ask a question about consumer complaint patterns...")

if question:
    with st.spinner("Investigating..."):
        try:
            output = agent_app.invoke({"question": question})
            st.session_state.history.append((question, output, None))
        except Exception as e:
            st.session_state.history.append((question, None, str(e)))

for question, output, error in reversed(st.session_state.history):
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        if error:
            st.error(f"The agent hit an unexpected error: {error}")
            continue

        st.write(output["answer"])

        with st.expander(f"🧠 Reasoning trail ({len(output['plan'])} sub-quer{'y' if len(output['plan']) == 1 else 'ies'})"):
            for i, (sql, result) in enumerate(zip(output["plan"], output["results"]), start=1):
                st.markdown(f"**Sub-query {i}:**")
                st.code(sql, language="sql")
                if "error" in result:
                    st.warning(f"Blocked or failed: {result['error']}")
                else:
                    st.caption(
                        f"{result['row_count']} row(s) returned"
                        + (" (truncated to first 1000)" if result.get("truncated") else "")
                    )
                    if result["result"]:
                        st.dataframe(result["result"], use_container_width=True)

st.divider()
st.caption(
    "Data: the real, public CFPB Consumer Complaint Database via Google BigQuery. "
    "Not a fabricated company's private data — genuine regulatory complaint records."
)