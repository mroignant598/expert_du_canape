import streamlit as st
import pandas as pd
import accueil as page0
import expert_canape as page1
import championnat as page2
import competitions_europeennes as page3
import coupes_nationales as page4
import os

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

st.sidebar.button("🏠 Accueil", on_click=navigate_to, args=("Accueil",))
st.sidebar.button("🏅 Les Experts du Canapé", on_click=navigate_to, args=("Expert Canapé",))
st.sidebar.button("⚽ Classements Nationaux", on_click=navigate_to, args=("Championnat",))
st.sidebar.button("🌍 Compétitions Européennes", on_click=navigate_to, args=("Compétitions Européennes",))
st.sidebar.button("🏆 Coupes Nationales", on_click=navigate_to, args=("Coupes Nationales",))

# ---------------- Affichage des pages ---------------- #
if st.session_state.page == "Accueil":
    page0.show(tables)
elif st.session_state.page == "Expert Canapé":
    page1.show(tables)
elif st.session_state.page == "Championnat":
    page2.show(tables)
elif st.session_state.page == "Compétitions Européennes":
    page3.show(tables)
elif st.session_state.page == "Coupes Nationales":
    page4.show(tables)  

