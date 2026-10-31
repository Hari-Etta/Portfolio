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
st.navigation(pages).run()
