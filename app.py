import streamlit as st
import pandas as pd
import accueil as page0
import expert_canape as page1
import championnat as page2
import os
from streamlit_extras.stylable_container import stylable_container

st.set_page_config(page_title="Football DB", page_icon="⚽", layout="wide")

# ---------------- Chargement CSV ---------------- #
def load_csv_tables(folder="csv"):
    tables = {}
    for file in os.listdir(folder):
        if file.endswith(".csv"):
            table_name = file.replace(".csv", "")
            tables[table_name] = pd.read_csv(os.path.join(folder, file))
    return tables

tables = load_csv_tables()

# ---------------- Navigation ---------------- #
if "page" not in st.session_state:
    st.session_state.page = "Accueil"
    
def navigate_to(page):
    st.session_state.page = page

# === MENU HORIZONTAL ===
menu_items = [
    {"label": "🏠 Accueil", "page": "Accueil", "color": ("#2196F3", "#022B5A")},
    {"label": "🏅 Les Experts du Canapé", "page": "Expert Canapé", "color": ("#4CAF50", "#035707")},
#    {"label": "⚽ Classements", "page": "Championnat", "color": ("#FF9800", "#8D4803")},
]

# === Navbar horizontale avec stylable_container ===
cols = st.columns(len(menu_items), gap="small")

for i, item in enumerate(menu_items):
    is_active = st.session_state.page == item["page"]
    gradient = f"linear-gradient(135deg, {item['color'][0]}, {item['color'][1]})"
    border = "3px solid white" if is_active else "1px solid rgba(255,255,255,0.3)"
    font_weight = "bold" if is_active else "normal"

    with cols[i]:
        with stylable_container(
            key=f"container_{item['page']}",
            css_styles=f"""
            button {{
                width: 100%;
                border-radius: 0px;
                border: {border};
                background: {gradient};
                color: white;
                font-weight: {font_weight};
                padding: 12px 0;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            button:hover {{
                transform: scale(1.03);
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }}
            """
        ):
            clicked = st.button(item["label"], key=f"btn_{item['page']}")
            if clicked:
                navigate_to(item["page"])

# ---------------- Affichage des pages ---------------- #
if st.session_state.page == "Accueil":
    page0.show(tables)
elif st.session_state.page == "Expert Canapé":
    page1.show(tables)
#elif st.session_state.page == "Championnat":
#    page2.show(tables)

