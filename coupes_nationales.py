import streamlit as st
import pandas as pd

def show(tables):
    st.title("🏆 Coupes Nationales")
    
    # Récupération du DataFrame correspondant
    df_all = tables["all_matchs_football"]  

    # ----- Colonne pour sélection de la saison -----
    col1, col2 = st.columns([1.1, 1.1])

    with col1:
        saisons = df_all[
            df_all["competition"].isin([
                'Coupe de France', 'Coupe de la Ligue', 'Community Shield', 
                "Supercoupe d'Allemagne", "Supercoupe d'Espagne", "Supercoupe d'Europe", 
                "Supercoupe d'Italie", 'Trophée des Champions'
            ])
        ]["saison"].dropna().unique()

        saisons = sorted(saisons, reverse=True)
        if len(saisons) == 0:
            st.warning("Aucune saison disponible pour les Coupes Nationales.")
            return

        saison_sel = st.selectbox("Sélectionner une saison :", saisons)

    # ----- Colonne pour sélection de la compétition -----
    with col2:
        competitions = df_all[
            (df_all["saison"] == saison_sel) &
            (df_all["competition"].isin([
                'Coupe de France', 'Coupe de la Ligue', 'Community Shield', 
                "Supercoupe d'Allemagne", "Supercoupe d'Espagne", "Supercoupe d'Europe", 
                "Supercoupe d'Italie", 'Trophée des Champions'
            ]))
        ]["competition"].dropna().unique()

        if len(competitions) == 0:
            st.warning("Aucune Coupe Nationale disponible pour cette saison.")
            return

        competition_sel = st.selectbox("Sélectionner une compétition :", competitions)

    # Fonction pour sécuriser la conversion des NaN en entier
    def safe_int(val):
        return int(val) if pd.notna(val) else 0

    # ----- Filtrage des matchs -----
    df = df_all[
        (df_all["saison"] == saison_sel) & 
        (df_all["competition"] == competition_sel)
    ].copy()

    if df.empty:
        st.info("Aucun match enregistré pour cette compétition et cette saison.")
        return

    # ----- Affichage par phases -----
    phases = ["1/128 de finale", "1/64 de finale", "1/32 de finale", "Premier tour",
                "Deuxième tour", "Seizièmes", "Huitièmes", "Quarts", "Demies", "Finale"]
    hauteur_phase = {"1/128 de finale":1000, "1/64 de finale":600, "1/32 de finale":400,
                    "Premier tour":250, "Deuxième tour":250, "Seizièmes":600,
                    "Huitièmes":310, "Quarts":180, "Demies":120, "Finale":80}

    for phase in phases:
        df_phase = df[df['phase'] == phase]
        if df_phase.empty:
            continue

        st.subheader(f"{phase}")
        rows = []
        qualifiés = []

        for match_id, g in df_phase.groupby("match_id"):
            match = g.iloc[0]
            dom = match['equipe_domicile_nom']
            ext = match['equipe_exterieure_nom']

            # Score régulier
            score_dom = safe_int(match['score_domicile'])
            score_ext = safe_int(match['score_exterieur'])
            score = f"{score_dom}-{score_ext}"

            # Prolongation
            if pd.notna(match.get('prolongation_score_domicile')):
                score += f" (Prol: {safe_int(match['prolongation_score_domicile'])}-{safe_int(match['prolongation_score_exterieur'])})"

            # Tirs au but
            if pd.notna(match.get('tab_score_domicile')):
                score += f" (TAB: {safe_int(match['tab_score_domicile'])}-{safe_int(match['tab_score_exterieur'])})"

            # Détermination du vainqueur
            if score_dom > score_ext:
                vainqueur = dom
            elif score_ext > score_dom:
                vainqueur = ext
            else:
                vainqueur = None

            rows.append({"Domicile": dom, "Score": score, "Extérieur": ext})
            if vainqueur:
                qualifiés.append(vainqueur)

        # ----- Style des vainqueurs -----
        def highlight_winner(row):
            styles = []
            for col in row.index:
                if col == 'Domicile' and row[col] in qualifiés:
                    styles.append('background-color: #0EC557FF; font-weight:bold;')
                elif col == 'Extérieur' and row[col] in qualifiés:
                    styles.append('background-color: #0EC557FF; font-weight:bold;')
                else:
                    styles.append('')
            return styles

        df_display = pd.DataFrame(rows)
        styled_df = (
            df_display.style
            .apply(highlight_winner, axis=1)
            .set_properties(**{'text-align': 'center', 'white-space':'nowrap', 'padding':'4px 6px', 'font-size':'14px'})
        )

        col_match, col_qualifie = st.columns([2, 1.4])

        with col_match:
            st.dataframe(
                styled_df,
                use_container_width=True,
                height=hauteur_phase.get(phase,150),
                hide_index=True
            )

        with col_qualifie:
            if phase == "Finale":
                if vainqueur:
                    st.markdown(
                        f"<div style='text-align:center'>"
                        f"<span style='display:inline-block;background-color:#FFD700;color:#000;padding:10px 20px;border-radius:12px;font-weight:bold;font-size:18px'>🏆 {vainqueur}</span>"
                        f"<br><span style='font-size:16px;margin-top:8px'>Score : {score}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown("### Match nul au score régulier (prolongations/TAB déterminent le vainqueur)")
            else:
                if qualifiés:
                    colors = ["#64c7ba", "#6664c7", "#ae76b3", "#5da78d", "#f79fc8", "#f48282"]
                    qualifies_html = " ".join([
                        f"<span style='display:inline-block;background-color:{colors[i%len(colors)]};color:#000;padding:4px 10px;border-radius:12px;margin:2px;font-weight:bold'>⚡ {team}</span>"
                        for i, team in enumerate(qualifiés)
                    ])
                    st.markdown(f"<h4>Équipes qualifiées pour le tour suivant :</h4>{qualifies_html}", unsafe_allow_html=True)

        st.markdown("---")
