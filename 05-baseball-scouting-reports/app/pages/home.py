"""Home page. Step 5.1: data-layer smoke test (opponent picker and "What changed" come in 5.2)."""
import streamlit as st

from lib.data import backend, load

st.title("⚾ Advance Scouting Reports")
st.caption(f"2026 MLB regular season · data backend: {backend()}")

players = load("players")
tx = load("transactions")
c1, c2, c3 = st.columns(3)
c1.metric("Players", f"{len(players):,}")
c2.metric("Teams", players["last_team"].nunique())
c3.metric("Transactions", f"{len(tx):,}")
st.success("Data layer working: gold tables loaded from S3 with the read-only key.")
