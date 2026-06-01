"""
main.py — Streamlit hoofdapp voor AP06 Planner.

Navigatie:
  📋 Planning  → xlsx uploaden en verwerken
  👥 Beheer    → monsternemer database beheren

Start met: streamlit run src/ap06_planner/main.py
"""

import streamlit as st

# Laad .env
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="AP06 Planner",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("🧪 AP06 Planner")
st.sidebar.caption("Monster ophaalplanning")
st.sidebar.divider()

pagina = st.sidebar.radio(
    "Navigatie",
    options=["📋 Planning", "👥 Monsternemer beheer"],
    label_visibility="collapsed",
)

if pagina == "📋 Planning":
    from ap06_planner.pages import planning
    planning.render()
elif pagina == "👥 Monsternemer beheer":
    from ap06_planner.pages import beheer
    beheer.render()
