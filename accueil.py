import streamlit as st
import pandas as pd
import os
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder

# =======================
# Fonction KPI
# =======================
def kpi_card(title, value, color):
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {color} 0%, #ffffff20 100%);
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            text-align: center;
            color: white;
            transition: transform 0.2s, box-shadow 0.2s;
        " onmouseover="this.style.transform='scale(1.05)';this.style.boxShadow='0 8px 25px rgba(0,0,0,0.25)';" 
          onmouseout="this.style.transform='scale(1)';this.style.boxShadow='0 4px 20px rgba(0,0,0,0.15)';">
            <div style="font-size: 18px; font-weight: 500; margin-bottom: 5px;">{title}</div>
            <div style="font-size: 32px; font-weight: bold;">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# =======================
# Fonction principale
# =======================
def show(tables):
    st.title("⚽ Football DB – Tableau de bord")
    st.markdown("Bienvenue dans ton application de gestion et d’analyse des matchs à partir de fichiers CSV 🏟️")

    df_matchs = tables["all_matchs_football"]
    df_pronos = tables["all_pronostics"]
    df_participants = tables["participants"]
    df_archives = tables["archives"]

    # =======================
    # KPI GLOBAUX
    # =======================
    st.subheader("🌍 Statistiques globales")

    nb_matchs = len(df_matchs)
    nb_pronos = len(df_pronos)
    nb_participants = df_participants["id"].nunique() if "id" in df_participants.columns else len(df_participants)
    nb_archives = len(df_archives)

    col1, col2, col3, col4 = st.columns(4, gap="large")
    with col1:
        kpi_card("🏟️ Matchs enregistrés", f"{nb_matchs:,}".replace(",", " "), "#3b82f6")
    with col2:
        kpi_card("📋 Pronostics saisis", f"{nb_pronos:,}".replace(",", " "), "#22c55e")
    with col3:
        kpi_card("👥 Participants inscrits", f"{nb_participants:,}".replace(",", " "), "#f59e0b")
    with col4:
        kpi_card("🏆 Matchs archivés", f"{nb_archives:,}".replace(",", " "), "#9333ea")

    st.markdown("<hr style='border:1px solid #444444; margin: 2rem 0;'>", unsafe_allow_html=True)

    # =======================
    # KPI PAR SAISON
    # =======================
    st.subheader("📆 Statistiques par saison")

    if "saison" not in df_matchs.columns:
        st.error("❌ La colonne 'saison' est manquante dans all_matchs_football.csv.")
        return

    saisons = sorted(df_matchs["saison"].dropna().unique(), reverse=True)

    if not saisons:
        st.info("Aucune saison trouvée dans les fichiers CSV.")
        return

    # Créer les colonnes
    col1, col2 = st.columns(2, gap="small")

    with col1:
        # Sélection de la saison
        saison_sel = st.selectbox("Sélectionner une saison :", saisons)

        # Filtrer les données selon la saison
        df_matchs_saison = df_matchs[df_matchs["saison"] == saison_sel]
        df_pronos_saison = df_pronos[df_pronos["saison"] == saison_sel]

        nb_matchs_saison = len(df_matchs_saison)
        nb_pronos_saison = len(df_pronos_saison)

        # Participants actifs
        if "participant_id" in df_pronos.columns and "pseudo" in df_participants.columns:
            participants_saison = df_pronos_saison["participant_id"].unique()
            noms_participants = df_participants[df_participants["id"].isin(participants_saison)]["pseudo"].sort_values().tolist()
        else:
            noms_participants = []

        nb_participants_saison = len(noms_participants)

    with col2:
        st.markdown("### 📊 Stats")
        kpi_card(f"🏟️ Matchs", f"{nb_matchs_saison:,}".replace(",", " "), "#3b82f6")
        st.text('')
        kpi_card(f"📋 Pronostics", f"{nb_pronos_saison:,}".replace(",", " "), "#22c55e")
        st.text('')
        kpi_card(f"👥 Participants", f"{nb_participants_saison:,}".replace(",", " "), "#f59e0b")

    with col1:
        if noms_participants:
            st.markdown("### 👤 Liste des participants")

            # CSS pour les cartes stylées avec avatar initiale
            st.markdown("""
                <style>
                .participant-grid {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    justify-content: flex-start;
                    margin-top: 15px;
                }
                .participant-card {
                    background-color: #1f2937; /* gris foncé */
                    color: white;
                    padding: 10px 16px;
                    border-radius: 14px;
                    font-weight: 500;
                    text-align: left;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.25);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    transition: all 0.25s ease-in-out;
                    min-width: 160px;
                }
                .participant-card:hover {
                    transform: translateY(-4px);
                    background-color: #374151;
                }
                .avatar {
                    width: 38px;
                    height: 38px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 1.1em;
                    flex-shrink: 0;
                }
                </style>
            """, unsafe_allow_html=True)

            # Palette de couleurs agréables pour les avatars
            couleurs = [
                "#ef4444", "#f97316", "#f59e0b", "#10b981", "#3b82f6",
                "#8b5cf6", "#ec4899", "#14b8a6", "#84cc16", "#0ea5e9"
            ]

            # Construire chaque carte
            cards = []
            for i, pseudo in enumerate(noms_participants):
                initiale = pseudo.strip()[0].upper() if pseudo.strip() else "?"
                couleur = couleurs[i % len(couleurs)]
                card_html = (
                    f"<div class='participant-card'>"
                    f"<div class='avatar' style='background-color:{couleur};'>{initiale}</div>"
                    f"<div>{pseudo}</div>"
                    f"</div>"
                )
                cards.append(card_html)

            # Assembler toutes les cartes dans une grille
            grid_html = "<div class='participant-grid'>" + "".join(cards) + "</div>"
            st.markdown(grid_html, unsafe_allow_html=True)

        else:
            st.info("Aucun participant n’a de pronostics pour cette saison.")

    st.markdown("<hr style='border:1px solid #444444; margin: 2rem 0;'>", unsafe_allow_html=True)

    # =======================
    # Aperçu du fichier matchs
    # =======================
    st.subheader("📋 Aperçu des matchs")
    st.dataframe(df_matchs.tail(10), use_container_width=True, hide_index=True)
