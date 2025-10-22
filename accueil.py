import streamlit as st
import pandas as pd
import os

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
    st.title("⚽ Football DB – Tableau de bord (mode CSV)")
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
    if saisons:
        saison_sel = st.selectbox("Sélectionner une saison :", saisons)

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

        col1, col2, col3 = st.columns(3, gap="large")
        with col1:
            kpi_card(f"🏟️ Matchs ({saison_sel})", f"{nb_matchs_saison:,}".replace(",", " "), "#3b82f6")
        with col2:
            kpi_card(f"📋 Pronostics ({saison_sel})", f"{nb_pronos_saison:,}".replace(",", " "), "#22c55e")
        with col3:
            kpi_card(f"👥 Participants ({saison_sel})", f"{nb_participants_saison:,}".replace(",", " "), "#f59e0b")

        if noms_participants:
            st.markdown(f"### 👤 Liste des participants actifs ({saison_sel})")
            df_participants_actifs = pd.DataFrame({"Pseudo": noms_participants})
            st.dataframe(
                df_participants_actifs.style.set_properties(**{
                    'text-align': 'center',
                    'white-space': 'nowrap'
                }),
                use_container_width=True,
                hide_index=True,
                height=min(40 * len(df_participants_actifs), 400)
            )
        else:
            st.info("Aucun participant n’a de pronostics pour cette saison.")
    else:
        st.info("Aucune saison trouvée dans les fichiers CSV.")

    st.markdown("<hr style='border:1px solid #444444; margin: 2rem 0;'>", unsafe_allow_html=True)

    # =======================
    # Aperçu du fichier matchs
    # =======================
    st.subheader("📋 Aperçu des matchs")
    st.dataframe(df_matchs.head(10), use_container_width=True, hide_index=True)
