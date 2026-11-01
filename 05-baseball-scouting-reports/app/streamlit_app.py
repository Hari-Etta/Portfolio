"""Advance Scouting Reports: Streamlit entry point (page setup and navigation)."""
import streamlit as st

st.set_page_config(page_title="Advance Scouting Reports", page_icon="⚾", layout="wide")

pages = [
    st.Page("pages/home.py", title="Home", icon="🏠", default=True),
    st.Page("pages/pitcher.py", title="Pitcher report", icon="🎯"),
    st.Page("pages/hitter.py", title="Hitter report", icon="🏏"),
    st.Page("pages/running_defense.py", title="Running game & defense", icon="🏃"),
    st.Page("pages/planner.py", title="Pitch planner", icon="🧠"),
    st.Page("pages/methods.py", title="Methods & data", icon="📘"),
]
with st.sidebar:
    st.toggle(
        "Count reached-on-error as hits",
        key="errors_as_hits",
        help="Off (default): reaching on an error counts as an out, since the fielder should have made the play. "
             "On: Statcast's convention, so wOBA can be checked against Baseball Savant.",
    )

st.navigation(pages).run()

