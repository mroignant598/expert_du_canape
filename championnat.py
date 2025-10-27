import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def show(tables):
    st.title("🏆 Classement d'un championnat")

    # --- Charger les données depuis le CSV --- #
    df = tables["archives"]

    # Normaliser les noms de colonnes si nécessaire
    df.rename(columns={
        'equipe_domicile': 'equipe_domicile_nom',
        'equipe_exterieure': 'equipe_exterieure_nom',
        'score_domicile_final': 'score_domicile',
        'score_exterieur_final': 'score_exterieur'
    }, inplace=True)

    # --- Sélection saison / championnat / journée --- #
    col1, col2 = st.columns([1.1, 3])

    # 1️⃣ Sélection de la saison
    with col1:
        saisons = sorted(df['saison'].dropna().unique(), reverse=True)
        if not saisons:
            st.warning("Aucune saison disponible.")
            return
        saison_sel = st.selectbox("Sélectionner une saison :", saisons)
        
    competitions_possibles = [
        'Ligue 1', 'Premier League', 'Serie A', 'Bundesliga', '2. Bundesliga',
        'LaLiga2', 'Championship', 'League One', 'League Two', 'National League',
        'Serie B', 'LaLiga', 'Ligue 2', 'Eredivisie', 'National',
        'Jupiler League', 'Liga Portugal', 'Premiership'
    ]

    with col2:
        competitions_sel = st.multiselect(
            "🏆 Sélectionner les compétitions à inclure dans les stats globales :",
            options=competitions_possibles,
            default=['Ligue 1', 'Premier League', 'Serie A', 'Bundesliga', 'LaLiga']
        )

        if not competitions_sel:
            st.warning("Veuillez sélectionner au moins une compétition.")
            st.stop()

    # === Filtrage des données === #
    df_saison = df[
        (df["saison"] == saison_sel) &
        (df["competition"].isin(competitions_sel))
    ].copy()

    # Conversion des scores en numérique (au cas où)
    df_saison["score_domicile"] = pd.to_numeric(df_saison["score_domicile"], errors="coerce")
    df_saison["score_exterieur"] = pd.to_numeric(df_saison["score_exterieur"], errors="coerce")

    df_saison = df_saison.dropna(subset=["score_domicile", "score_exterieur"])
    if df_saison.empty:
        st.info("Aucune donnée de match disponible pour ces compétitions cette saison.")
        st.stop()

    # === Calcul des stats globales === #
    stats = []
    for _, row in df_saison.iterrows():
        stats.append({
            "équipe": row["equipe_domicile_nom"],
            "buts_pour": row["score_domicile"],
            "buts_contre": row["score_exterieur"]
        })
        stats.append({
            "équipe": row["equipe_exterieure_nom"],
            "buts_pour": row["score_exterieur"],
            "buts_contre": row["score_domicile"]
        })

    df_stats = pd.DataFrame(stats)
    classement = df_stats.groupby("équipe").sum().reset_index()
    classement["diff"] = classement["buts_pour"] - classement["buts_contre"]

    # Meilleure/pire attaque et défense
    meilleure_attaque = classement.loc[classement["buts_pour"].idxmax()]
    pire_attaque = classement.loc[classement["buts_pour"].idxmin()]
    meilleure_defense = classement.loc[classement["buts_contre"].idxmin()]
    pire_defense = classement.loc[classement["buts_contre"].idxmax()]

    # === Affichage des KPI === #
    st.subheader("📊 Statistiques globales sur la saison")

    def kpi_card(title, value, subtitle, color, emoji):
        st.markdown(f"""
            <div style="
                background: {color};
                border-radius: 16px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                color: white;
            ">
                <div style="font-size: 32px;">{emoji}</div>
                <div style="font-size: 20px; font-weight: bold; margin-top: 5px;">{title}</div>
                <div style="font-size: 28px; font-weight: 800; margin-top: 10px;">{value}</div>
                <div style="font-size: 16px; opacity: 0.9; margin-top: 5px;">{subtitle}</div>
            </div>
        """, unsafe_allow_html=True)

    colA, colB, colC, colD = st.columns(4)

    with colA: kpi_card("Meilleure attaque", meilleure_attaque["équipe"], f"{meilleure_attaque['buts_pour']} buts marqués", "#FF8C00", "🔥")

    with colB: kpi_card("Pire attaque", pire_attaque["équipe"], f"{pire_attaque['buts_pour']} buts marqués", "#708090", "🥶")

    with colC: kpi_card("Meilleure défense", meilleure_defense["équipe"], f"{meilleure_defense['buts_contre']} buts encaissés", "#2E8B57", "🛡️")

    with colD: kpi_card("Pire défense", pire_defense["équipe"], f"{pire_defense['buts_contre']} buts encaissés", "#B22222", "💣")

    st.markdown("---")
    
# --- Sélection championnat / journée --- #
    col1, col2, col3 = st.columns(3)
    with col1:
        championnats = sorted(
            df[(df['saison'] == saison_sel) & (df['competition'].isin(competitions_possibles))]['competition']
            .dropna().unique()
        )

        if not championnats:
            st.warning("Aucun championnat à afficher pour cette saison.")
            return

        championnat_defaut = "Ligue 1"
        index_defaut = championnats.index(championnat_defaut) if championnat_defaut in championnats else 0
        championnat_sel = st.selectbox("Sélectionner un championnat :", championnats, index=index_defaut)

    with col2:
        # 3️⃣ Sélection de la journée
        journees_res = sorted(df[(df['saison'] == saison_sel) & (df['competition'] == championnat_sel)]['journee'].dropna().unique())
        
        # --- Convertir les journées en entiers valides ---
        journees_entieres = sorted([int(j) for j in journees_res if pd.notna(j)])

        # Ajouter l'option "Toutes" en début de liste
        options_journee = ["Toutes"] + journees_entieres

        # Index par défaut : dernière journée
        default_index = len(options_journee) - 1 if len(journees_entieres) > 0 else 0

        # --- Sélecteur Streamlit ---
        journee_sel = st.selectbox(
            "📅 Sélectionner la journée à afficher :",
            options_journee,
            index=default_index
        )

        # --- Utilisation ---
        if journee_sel == "Toutes":
            df_filtre = df.copy()  # toutes les journées
        else:
            df_filtre = df[df["journee"] == int(journee_sel)]  # journée sélectionnée

    # --- Filtrer les matchs à afficher --- #
    df_matchs = df[(df['saison'] == saison_sel) & (df['competition'] == championnat_sel)]

    if df_matchs.empty:
        st.info("Aucun match pour ce championnat et cette saison.")
        return

    # --- Gestion du filtre sur la journée --- #
    if journee_sel != "Toutes":
        # Inclure toutes les journées jusqu’à celle sélectionnée
        df_matchs_journee = df_matchs[df_matchs["journee"] <= journee_sel]
    else:
        df_matchs_journee = df_matchs.copy()

    if df_matchs_journee.empty:
        st.info("Aucun match pour ce championnat et cette saison / journée.")
        return

    # --- Fonction de calcul du barème de points --- #
    def points_victoire(championnat, saison):
        try:
            annee = int(str(saison).split("-")[0])
        except:
            annee = int(saison)

        barèmes_2pts = {
            "Premier League": 1981,
            "Championship": 1981,
            "League One": 1981,
            "League Two": 1981,
            "National League": 1981,
            "Ligue 1": 1994,
            "Ligue 2": 1994,
            "Serie A": 1994,
            "Serie B": 1994,
            "Jupiler League": 1995,
            "Bundesliga": 1995,
            "2. Bundesliga": 1995,
            "Eredivisie": 1995,
            "Liga Portugal": 1995,
            "LaLiga": 1995,
            "LaLiga2": 1995,
            "Premiership": 1995
        }

        if championnat in barèmes_2pts and annee < barèmes_2pts[championnat]:
            return 2
        else:
            return 3

    # --- Fonction calcul classement --- #
    def calcul_classement(df):
        pts_victoire = points_victoire(championnat_sel, saison_sel)
        equipes = pd.unique(df[['equipe_domicile_nom', 'equipe_exterieure_nom']].values.ravel('K'))
        classement = pd.DataFrame(index=equipes, columns=['Pts','J','V','N','D','BP','BC','Diff'])
        classement.fillna(0, inplace=True)

        for _, match in df.iterrows():
            dom, ext = match['equipe_domicile_nom'], match['equipe_exterieure_nom']
            sd, se = match['score_domicile'], match['score_exterieur']
            if pd.isna(sd) or pd.isna(se):
                continue

            classement.at[dom,'J'] += 1
            classement.at[ext,'J'] += 1
            classement.at[dom,'BP'] += sd
            classement.at[dom,'BC'] += se
            classement.at[ext,'BP'] += se
            classement.at[ext,'BC'] += sd

            if sd > se:
                classement.at[dom,'V'] += 1
                classement.at[dom,'Pts'] += pts_victoire
                classement.at[ext,'D'] += 1
            elif sd < se:
                classement.at[ext,'V'] += 1
                classement.at[ext,'Pts'] += pts_victoire
                classement.at[dom,'D'] += 1
            else:
                classement.at[dom,'N'] += 1
                classement.at[ext,'N'] += 1
                classement.at[dom,'Pts'] += 1
                classement.at[ext,'Pts'] += 1

        classement['Diff'] = classement['BP'] - classement['BC']
        classement = classement.sort_values(by=['Pts','Diff','BP'], ascending=[False,False,False])
        classement.reset_index(inplace=True)
        classement.rename(columns={'index':'Equipe'}, inplace=True)
        classement.insert(0, 'Rang', range(1, len(classement) + 1))
        return classement

    # --- Calcul des classements --- #
    classement_actuel = calcul_classement(df_matchs_journee)
    classement_final = calcul_classement(df_matchs)

    # --- Évolution du classement --- #
    if journee_sel != "Toutes" and journee_sel > min(journees_res):
        df_matchs_prec = df_matchs[df_matchs["journee"] <= journee_sel - 1]
        classement_prec = calcul_classement(df_matchs_prec)

        def evolution(equipe):
            if equipe not in classement_prec["Equipe"].values:
                return "🆕"
            rang_prec = classement_prec.loc[classement_prec["Equipe"] == equipe, "Rang"].values[0]
            rang_actu = classement_actuel.loc[classement_actuel["Equipe"] == equipe, "Rang"].values[0]
            diff = rang_prec - rang_actu
            if diff > 0:
                return f"🟢 +{diff}"
            elif diff < 0:
                return f"🔴 {diff}"
            else:
                return "⚪ ="
        classement_actuel["Évolution"] = classement_actuel["Equipe"].apply(evolution)
    else:
        classement_actuel["Évolution"] = "—"

    # --- Style des tableaux --- #
    def highlight_top_bottom(row, total_teams):
        color = ''
        if row.Rang <= 3:
            color = 'background-color: #124D12FF; font-weight: bold;'
        elif row.Rang > total_teams - 3:
            color = 'background-color: #F75555FF; font-weight: bold;'
        return [color]*len(row)

    def style_table(df):
        total = len(df)
        colonnes = ['Rang','Equipe','Pts','J','V','N','D','BP','BC','Diff']
        if 'Évolution' in df.columns:
            colonnes.append('Évolution')
        return (
            df[colonnes]
            .style
            .apply(highlight_top_bottom, total_teams=total, axis=1)
            .format({'Pts':'{:.0f}','Diff': '{:+d}'})
            .background_gradient(subset=['Pts'], cmap='Greens', low=0.2, high=0.9)
            .background_gradient(subset=['Diff'], cmap='RdYlGn', low=0.2, high=0.9)
        )

    # --- Affichage --- #
    st.subheader(f"🏁 Classements – {championnat_sel} – {saison_sel}")
    col_dyn, col_resultat = st.columns([1.7, 1.2])

    with col_dyn:
        st.markdown(f"**Classement après la journée {journee_sel}**")
        styled_classement = style_table(classement_actuel).set_properties(
            **{'text-align':'center','justify-content':'center','white-space':'nowrap','font-size':'14px','padding':'4px 8px'}
        )
        st.dataframe(styled_classement, use_container_width=False, height=38*len(classement_actuel), hide_index=True)

    with col_resultat:
        st.subheader(f"⚽️ Résultats de la journée {journee_sel}")
        if journee_sel != "Toutes":
            df_journee = df_matchs[df_matchs["journee"] == journee_sel]
        else:
            df_journee = df_matchs.copy()

        if df_journee.empty:
            st.info("Aucun match pour cette journée.")
        else:
            df_journee_display = df_journee.copy()
            df_journee_display["Score"] = df_journee_display.apply(
                lambda row: f"{int(row['score_domicile'])}-{int(row['score_exterieur'])}" 
                if pd.notna(row['score_domicile']) and pd.notna(row['score_exterieur']) else "-", axis=1
            )
            df_journee_display = df_journee_display[["equipe_domicile_nom","Score","equipe_exterieure_nom"]].rename(
                columns={"equipe_domicile_nom":"Équipe domicile","equipe_exterieure_nom":"Équipe extérieure"}
            )
            st.dataframe(
                df_journee_display.style.set_properties(**{'text-align':'center','font-size':'14px','width':'auto','white-space':'nowrap'}),
                use_container_width=False,
                height=390,
                hide_index=True
            )

    st.subheader("📈 Évolution du classement par journée")
    classement_evolution = []
    for j in journees_res:
        if j == "Toutes": 
            st.text("Pas d'évolution à afficher")
            continue
        classement_j = calcul_classement(df_matchs[df_matchs["journee"] <= j])
        classement_j["Journee"] = j
        classement_evolution.append(classement_j[["Journee","Equipe","Rang"]])
    if classement_evolution:
        df_evolution = pd.concat(classement_evolution)
        fig_evo = go.Figure()
        for equipe in df_evolution["Equipe"].unique():
            team_data = df_evolution[df_evolution["Equipe"] == equipe]
            fig_evo.add_trace(go.Scatter(x=team_data["Journee"], y=team_data["Rang"], mode='lines+markers', name=equipe))
        fig_evo.update_layout(
            yaxis=dict(autorange="reversed", title="Rang"),
            xaxis=dict(title="Journée"),
            height=600,
            plot_bgcolor="#0E1117",
            paper_bgcolor="#0E1117",
            font=dict(color="white"),
            legend=dict(orientation="h", y=-0.25)
        )
        st.plotly_chart(fig_evo, use_container_width=True)
            
    # ---------- 🌍 Statistiques globales ----------
    all_matches = df[
        df["competition"] == championnat_sel][["saison", "competition", "equipe_domicile_nom", "equipe_exterieure_nom", "score_domicile", "score_exterieur"]].sort_values(by="saison")

    if all_matches.empty:
        st.info("ℹ️ Pas encore de données globales pour ce championnat.")
    else:
        df_all = pd.DataFrame(all_matches)
        df_all.rename(columns={
            "equipe_domicile": "equipe_domicile_nom",
            "equipe_exterieure": "equipe_exterieure_nom",
            "score_domicile_final": "score_domicile",
            "score_exterieur_final": "score_exterieur"
        }, inplace=True)

        champions = []
        saisons_all = df_all["saison"].unique()
        for s in saisons_all:
            df_saison = df_all[df_all["saison"] == s]
            classement_s = calcul_classement(df_saison)
            if not classement_s.empty:
                champions.append(classement_s.iloc[0]["Equipe"])

        if champions:
            club_plus_titres = pd.Series(champions).value_counts().idxmax()
            nb_titres = pd.Series(champions).value_counts().max()
        else:
            club_plus_titres, nb_titres = "—", 0

        equipes_participations = []
        for s in saisons_all:
            df_saison = df_all[df_all["saison"] == s]
            equipes_s = pd.unique(df_saison[['equipe_domicile_nom','equipe_exterieure_nom']].values.ravel('K'))
            equipes_participations.extend(equipes_s)

        club_plus_present = pd.Series(equipes_participations).value_counts().idxmax()
        nb_saisons = pd.Series(equipes_participations).value_counts().max()

        # --- Cartes KPI globales ---
        st.markdown("### 🏅 Palmarès global")

        st.markdown("""
        <style>
        .kpi-card {
            background: linear-gradient(135deg, #1E90FF, #0D47A1);
            padding: 20px;
            border-radius: 18px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: 0.3s;
        }
        .kpi-card:hover {
            transform: scale(1.03);
        }
        .kpi-value {
            font-size: 26px;
            font-weight: 700;
            margin-top: 10px;
        }
        .kpi-label {
            font-size: 16px;
            opacity: 0.8;
        }
        </style>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class='kpi-card'>
                <div style='font-size:35px;'>🏆</div>
                <div class='kpi-value'>{club_plus_titres}</div>
                <div class='kpi-label'>{nb_titres} titres</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class='kpi-card' style='background: linear-gradient(135deg, #43A047, #1B5E20);'>
                <div style='font-size:35px;'>🏟️</div>
                <div class='kpi-value'>{club_plus_present}</div>
                <div class='kpi-label'>{nb_saisons} saisons</div>
            </div>
            """, unsafe_allow_html=True)

    # ---------- 📆 Statistiques saisonnières ----------
    st.markdown("---")

    # ---------- Vérification des données ----------
    if df_matchs.empty:
        st.info(f"Pas de statistiques disponibles pour la saison {saison_sel}.")
        # On définit des placeholders pour éviter les erreurs
        total_buts = 0
        journee_max = journee_min = None
        buts_max = buts_min = 0
        meilleure_attaque = pire_attaque = {"Equipe": "—", "BP": 0}
        meilleure_defense = pire_defense = {"Equipe": "—", "BC": 0}
        plus_victoires = plus_nuls = plus_defaites = {"Equipe": "—", "V": 0, "N": 0, "D": 0}
    else:
        # Total de buts
        total_buts = df_matchs["score_domicile"].sum() + df_matchs["score_exterieur"].sum()

        # Classement de la saison
        stats_saison = calcul_classement(df_matchs)

        # Buts par journée
        if "journee" in df_matchs.columns and not df_matchs["journee"].isna().all():
            buts_par_journee = df_matchs.groupby("journee").apply(
                lambda x: x["score_domicile"].sum() + x["score_exterieur"].sum()
            )
            if not buts_par_journee.empty:
                journee_max = buts_par_journee.idxmax()
                buts_max = buts_par_journee.max()
                journee_min = buts_par_journee.idxmin()
                buts_min = buts_par_journee.min()
            else:
                journee_max = journee_min = None
                buts_max = buts_min = 0
        else:
            journee_max = journee_min = None
            buts_max = buts_min = 0

        # Meilleure/pire attaque et défense
        meilleure_attaque = stats_saison.loc[stats_saison["BP"].idxmax()] if not stats_saison.empty else {"Equipe": "—", "BP": 0}
        pire_attaque = stats_saison.loc[stats_saison["BP"].idxmin()] if not stats_saison.empty else {"Equipe": "—", "BP": 0}
        meilleure_defense = stats_saison.loc[stats_saison["BC"].idxmin()] if not stats_saison.empty else {"Equipe": "—", "BC": 0}
        pire_defense = stats_saison.loc[stats_saison["BC"].idxmax()] if not stats_saison.empty else {"Equipe": "—", "BC": 0}

        # Victoires, nuls, défaites
        plus_victoires = stats_saison.loc[stats_saison["V"].idxmax()] if not stats_saison.empty else {"Equipe": "—", "V": 0}
        plus_nuls = stats_saison.loc[stats_saison["N"].idxmax()] if not stats_saison.empty else {"Equipe": "—", "N": 0}
        plus_defaites = stats_saison.loc[stats_saison["D"].idxmax()] if not stats_saison.empty else {"Equipe": "—", "D": 0}

    # ---------- TITRE PRINCIPAL ----------
    st.markdown(f"### ⚽ Indicateurs de la saison **{saison_sel}**")

    # ---------- STYLE KPI ----------
    st.markdown("""
    <style>
    .kpi-card {
        background: linear-gradient(135deg, #1E90FF, #0D47A1);
        padding: 20px;
        border-radius: 18px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        height: 200px;
        transition: 0.3s;
        margin-bottom: 12px;
    }
    .kpi-card:hover {
        transform: scale(1.03);
    }
    .kpi-value {
        font-size: 26px;
    font-weight: 700;
            margin-top: 10px;
    }
    .kpi-label {
        font-size: 15px;
        opacity: 0.85;
    }
    </style>
    """, unsafe_allow_html=True)

    # ---------- LIGNE 1 ----------
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class='kpi-card' style='background: linear-gradient(135deg, #FF9800, #F57C00);'>
            <div style='font-size:35px;'>🔥</div>
            <div class='kpi-value'>{meilleure_attaque['Equipe']}</div>
            <div class='kpi-label'>Meilleure attaque — Saison {saison_sel}</div>
            <div class='kpi-label'><b>{int(meilleure_attaque['BP'])} buts marqués</b></div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='kpi-card' style='background: linear-gradient(135deg, #4CAF50, #2E7D32);'>
            <div style='font-size:35px;'>🧱</div>
            <div class='kpi-value'>{meilleure_defense['Equipe']}</div>
            <div class='kpi-label'>Meilleure défense — Saison {saison_sel}</div>
            <div class='kpi-label'><b>{int(meilleure_defense['BC'])} buts encaissés</b></div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class='kpi-card' style='background: linear-gradient(135deg, #9C27B0, #6A1B9A);'>
            <div style='font-size:35px;'>✅</div>
            <div class='kpi-value'>{plus_victoires['Equipe']}</div>
            <div class='kpi-label'>Plus de victoires — Saison {saison_sel}</div>
            <div class='kpi-label'><b>{int(plus_victoires['V'])} victoires</b></div>
        </div>
        """, unsafe_allow_html=True)

    # ---------- LIGNE 2 ----------
    col4, col5, col6 = st.columns(3)

    with col4:
        st.markdown(f"""
        <div class='kpi-card' style='background: linear-gradient(135deg, #9E9E9E, #616161);'>
            <div style='font-size:35px;'>💤</div>
            <div class='kpi-value'>{pire_attaque['Equipe']}</div>
            <div class='kpi-label'>Pire attaque — Saison {saison_sel}</div>
            <div class='kpi-label'><b>{int(pire_attaque['BP'])} buts marqués</b></div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class='kpi-card' style='background: linear-gradient(135deg, #E53935, #B71C1C);'>
            <div style='font-size:35px;'>🚪</div>
            <div class='kpi-value'>{pire_defense['Equipe']}</div>
            <div class='kpi-label'>Pire défense — Saison {saison_sel}</div>
            <div class='kpi-label'><b>{int(pire_defense['BC'])} buts encaissés</b></div>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
        <div class='kpi-card' style='background: linear-gradient(135deg, #C2185B, #880E4F);'>
            <div style='font-size:35px;'>💢</div>
            <div class='kpi-value'>{plus_defaites['Equipe']}</div>
            <div class='kpi-label'>Plus de défaites — Saison {saison_sel}</div>
            <div class='kpi-label'><b>{int(plus_defaites['D'])} défaites</b></div>
        </div>
        """, unsafe_allow_html=True)

    # ---------- TOTAL BUTS + MATCHS NULS ----------
    col_buts, col_jmax, col_jmin, col_nul = st.columns(4)
    with col_buts:
        st.markdown(f"""
        <div class='kpi-card' style='background: linear-gradient(135deg, #2196F3, #1565C0); margin-top:20px;'>
            <div style='font-size:35px;'>⚽</div>
            <div class='kpi-value'>{int(total_buts)} buts</div>
            <div class='kpi-label'>Total de buts marqués — Saison {saison_sel}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_jmax:
            st.markdown(f"""
            <div class='kpi-card' style='background: linear-gradient(135deg, #FF9800, #F57C00); margin-top:20px;'>
                <div style='font-size:35px;'>🔥</div>
                <div class='kpi-value'>Journée {"Journée " + str(journee_max) if journee_max is not None else "—"}</div>
                <div class='kpi-label'>Journée la plus prolifique</div>
                <div class='kpi-label'><b>{int(buts_max)} buts marqués</b></div>
            </div>
            """, unsafe_allow_html=True)

    with col_jmin:
        st.markdown(f"""
        <div class='kpi-card' style='background: linear-gradient(135deg, #2196F3, #1565C0); margin-top:20px;'>
            <div style='font-size:35px;'>❄️</div>
            <div class='kpi-value'>Journée {"Journée " + str(journee_min) if journee_min is not None else "—"}</div>
            <div class='kpi-label'>Journée la moins prolifique</div>
            <div class='kpi-label'><b>{int(buts_min)} buts marqués</b></div>
        </div>
        """, unsafe_allow_html=True)
            
    with col_nul:
        st.markdown(f"""
        <div class='kpi-card' style='background: linear-gradient(135deg, #00BCD4, #00838F); margin-top:15px;'>
            <div style='font-size:35px;'>🤝</div>
            <div class='kpi-value'>{plus_nuls['Equipe']}</div>
            <div class='kpi-label'>Plus de matchs nuls — Saison {saison_sel}</div>
            <div class='kpi-label'><b>{int(plus_nuls['N'])} matchs nuls</b></div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
            
        # ---------- ⚔️ Statistiques de jeu par équipe ---------- #
    st.markdown(f"### ⚔️ Statistiques de jeu par équipe - {saison_sel}")

        # --- Agrégation des stats de jeu ---
    stats_jeu = []

    for equipe in pd.unique(df_matchs[['equipe_domicile_nom', 'equipe_exterieure_nom']].values.ravel('K')):
        dom = df_matchs[df_matchs['equipe_domicile_nom'] == equipe]
        ext = df_matchs[df_matchs['equipe_exterieure_nom'] == equipe]

        total_matchs = len(dom) + len(ext)
        if total_matchs == 0:
            continue

        tirs = dom["tirs_domicile"].sum() + ext["tirs_exterieur"].sum()
        tirs_cadres = dom["tirs_cadres_domicile"].sum() + ext["tirs_cadres_exterieur"].sum()

        stats_jeu.append({
            "Equipe": equipe,
            "Tirs": tirs,
            "Tirs cadrés": tirs_cadres,
            "% tirs cadrés": round((tirs_cadres / tirs * 100), 2) if tirs > 0 else 0,
            "Corners": dom["corners_domicile"].sum() + ext["corners_exterieur"].sum(),
            "Fautes": dom["fautes_domicile"].sum() + ext["fautes_exterieur"].sum(),
            "Cartons jaunes": dom["cartons_jaune_domicile"].sum() + ext["cartons_jaune_exterieur"].sum(),
            "Cartons rouges": dom["cartons_rouges_domicile"].sum() + ext["cartons_rouges_exterieur"].sum(),
            "Matchs": total_matchs
        })

    df_stats_jeu = pd.DataFrame(stats_jeu)

    if df_stats_jeu.empty:
        st.info(f"Pas encore de statistiques détaillées disponibles pour la saison {saison_sel}.")
    else:
        # --- Colonnes principales ---
        cols_stats = ["Tirs", "Tirs cadrés", "Corners", "Fautes", "Cartons jaunes", "Cartons rouges"]

        # --- Moyennes par match ---
        for col in cols_stats:
            df_stats_jeu[f"{col} / match"] = (df_stats_jeu[col] / df_stats_jeu["Matchs"]).round(2)

        # --- Renommer les colonnes pour plus de clarté ---
        rename_map = {
            "Equipe": "Équipe",
            "Tirs": "Tirs totaux",
            "Tirs cadrés": "Tirs cadrés totaux",
            "Corners": "Corners totaux",
            "Fautes": "Fautes totales",
            "Cartons jaunes": "Jaunes",
            "Cartons rouges": "Rouges"
        }
        df_stats_jeu.rename(columns=rename_map, inplace=True)

        # 🔄 Met à jour la liste après renommage
        renamed_cols = list(rename_map.values())

        # --- Tri par les équipes les plus offensives ---
        df_stats_jeu = df_stats_jeu.sort_values("Tirs totaux", ascending=False).reset_index(drop=True)

        # --- Ajout de la moyenne du championnat ---
        # 🔧 Ne garder que les colonnes numériques
        numeric_cols = [c for c in renamed_cols if df_stats_jeu[c].dtype in ['int64', 'float64']]

        moyenne = df_stats_jeu[numeric_cols].mean().round(2)

        moyenne_row = pd.DataFrame({"Équipe": ["📊 Moyenne championnat"]})
        for col in numeric_cols:
            moyenne_row[col] = moyenne[col]
            moyenne_row[f"{col} / match"] = round(moyenne[col] / df_stats_jeu["Matchs"].mean(), 2)
        df_stats_jeu = pd.concat([df_stats_jeu, moyenne_row], ignore_index=True)

        # --- 💅 Style visuel amélioré ---
        styled_df = df_stats_jeu.style

        # Dégradés pour certaines colonnes
        styled_df = (
            styled_df
            .background_gradient(subset=["Tirs totaux", "Tirs cadrés totaux"], cmap="Greens")
            .background_gradient(subset=["Corners totaux"], cmap="Blues")
            .background_gradient(subset=["Fautes totales"], cmap="Oranges")
            .background_gradient(subset=["Jaunes"], cmap="YlOrBr")
            .background_gradient(subset=["Rouges"], cmap="Reds")
        )

        # Colonnes à 2 décimales : pourcentage et colonnes / match
        cols_2dec = [c for c in df_stats_jeu.columns if c.endswith("/ match") or c == "% tirs cadrés"]

        # Colonnes entières : toutes les autres colonnes numériques sauf celles à 2 décimales
        cols_int = [c for c in df_stats_jeu.select_dtypes(include=["number"]).columns if c not in cols_2dec]

        # Formater les colonnes
        styled_df = styled_df.format({
            **{c: "{:.2f}" for c in cols_2dec},
            **{c: "{:,.0f}" for c in cols_int}  # entier sans décimale
        })

        # Styles supplémentaires
        styled_df = styled_df.set_table_styles([
            {"selector": "thead th", "props": [("background-color", "#0D47A1"), ("color", "white"), ("font-weight", "bold")]},
            {"selector": "tbody tr:hover", "props": [("background-color", "#e3f2fd !important")]}
        ]).hide(axis="index")


        # --- Affichage Streamlit ---
        st.markdown(f"""
        <div style='margin-top:10px;'>
            <p style='color:gray;'>Comparatif global des équipes sur leurs performances offensives, défensives et disciplinaires.</p>
        </div>
        """, unsafe_allow_html=True)

        st.dataframe(styled_df, use_container_width=True, hide_index=True, height=620)

        st.markdown("---")

    # ---------- 🏅 Meilleures équipes par catégorie ----------
    st.markdown(f"#### 🏅 Meilleures équipes par catégorie – Saison {saison_sel}")
    
    st.markdown("""
        <style>
        .kpi-card2 {
            background: linear-gradient(135deg, #1E90FF, #0D47A1);
            padding: 20px;
            border-radius: 18px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: 0.3s;
        }
        .kpi-card2:hover {
            transform: scale(1.03);
        }
        .kpi-value2 {
            font-size: 26px;
            font-weight: 380;
            margin-top: 20px;
        }
        .kpi-label2 {
            font-size: 20px;
            opacity: 0.8;
        }
        </style>
        """, unsafe_allow_html=True)

    def best(col, ascending=False):
        if col not in df_stats_jeu.columns:
            return "—", 0
        best_row = df_stats_jeu.loc[df_stats_jeu[col].idxmax()] if not ascending else df_stats_jeu.loc[df_stats_jeu[col].idxmin()]
        return best_row["Équipe"], best_row[col]

    col1, col2, col3 = st.columns(3)

    with col1:
        equipe_tirs, val_tirs = best("Tirs totaux")
        st.markdown(f"""
        <div class='kpi-card2' style='background: linear-gradient(135deg, #FF9800, #F57C00);'>
            🎯 {equipe_tirs}
            <div class='kpi-value2'>{int(val_tirs)} tirs</div>
            <div class='kpi-label2'>Total tirs</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        equipe_corners, val_corners = best("Corners totaux")
        st.markdown(f"""
        <div class='kpi-card2' style='background: linear-gradient(135deg, #4CAF50, #2E7D32);'>
            🥅 {equipe_corners}
            <div class='kpi-value2'>{int(val_corners)}</div>
            <div class='kpi-label2'>Corners</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        equipe_jaunes, val_jaunes = best("Jaunes")
        
        st.markdown(f"""
        <div class='kpi-card2' style='background: linear-gradient(135deg, #FFEB3B, #FBC02D); color:black;'>
            🟨 {equipe_jaunes}
            <div class='kpi-value2'>{int(val_jaunes)}</div>
            <div class='kpi-label2'>Cartons jaunes</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown('')
        
    col1, col2, col3 = st.columns(3)

    with col1:
        equipe_eff, val_eff = best("% tirs cadrés")
        st.markdown(f"""
        <div class='kpi-card2' style='background: linear-gradient(135deg, #FFA726, #FB8C00);'>
            🔥 {equipe_eff}
            <div class='kpi-value2'>{val_eff:.1f}%</div>
            <div class='kpi-label2'>Tirs cadrés</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        equipe_fautes, val_fautes = best("Fautes totales")
        st.markdown(f"""
        <div class='kpi-card2' style='background: linear-gradient(135deg, #FFEB3B, #FBC02D); color:black;'>
            🚫 {equipe_fautes}
            <div class='kpi-value2'>{int(val_fautes)}</div>
            <div class='kpi-label2'>Fautes</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        equipe_rouges, val_rouges = best("Rouges")
        st.markdown(f"""
        <div class='kpi-card2' style='background: linear-gradient(135deg, #F44336, #D32F2F);'>
            🟥 {equipe_rouges}
            <div class='kpi-value2'>{int(val_rouges)}</div>
            <div class='kpi-label2'>Cartons rouges</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ---------- 🚨 Discipline globale sur la saison ----------
    st.markdown(f"#### 🚨 Discipline – Statistiques globales sur la saison – Saison {saison_sel}")

    total_cartons_jaunes = (
        df_matchs["cartons_jaune_domicile"].fillna(0).sum() +
        df_matchs["cartons_jaune_exterieur"].fillna(0).sum()
    )
    total_cartons_rouges = (
        df_matchs["cartons_rouges_domicile"].fillna(0).sum() +
        df_matchs["cartons_rouges_exterieur"].fillna(0).sum()
    )
    total_matchs_saison = df_matchs.shape[0]
    jaunes_par_match = round(total_cartons_jaunes / total_matchs_saison, 2) if total_matchs_saison > 0 else 0
    rouges_par_match = round(total_cartons_rouges / total_matchs_saison, 2) if total_matchs_saison > 0 else 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class='kpi-card2' style='background: linear-gradient(135deg, #FFEB3B, #FBC02D); color:black;'>
            🟨 Total jaunes
            <div class='kpi-value2'>{int(total_cartons_jaunes)}</div>
            <div class='kpi-label2'>{jaunes_par_match} / match</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='kpi-card2' style='background: linear-gradient(135deg, #F44336, #D32F2F);'>
            🟥 Total rouges
            <div class='kpi-value2'>{int(total_cartons_rouges)}</div>
            <div class='kpi-label2'>{rouges_par_match} / match</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class='kpi-card2' style='background: linear-gradient(135deg, #2196F3, #1565C0);'>
            📊 Matchs joués
            <div class='kpi-value2'>{total_matchs_saison}</div>
            <div class='kpi-label2'></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ---------- 🏠 Classements domicile / extérieur ---------- #
    st.markdown("### 🏠 Classements domicile / extérieur")
    
    # --- Filtrer sur la saison entière (et le championnat sélectionné) --- #
    df_matchs_saison = df[(df['saison'] == saison_sel) & (df['competition'] == championnat_sel)].copy()

    # Classement domicile
    df_dom = df_matchs_saison.copy()
    # Ne garder que les équipes à domicile
    df_dom = df_dom[['equipe_domicile_nom', 'score_domicile', 'score_exterieur']].rename(
        columns={
            'equipe_domicile_nom': 'Equipe',
            'score_domicile': 'BP',
            'score_exterieur': 'BC'
        }
    )

    def calcul_classement_domicile(df):
        classement = pd.DataFrame(index=df['Equipe'].unique(), columns=['Pts','J','V','N','D','BP','BC','Diff'])
        classement.fillna(0, inplace=True)
        
        for _, row in df.iterrows():
            equipe = row['Equipe']
            bp, bc = row['BP'], row['BC']
            if pd.isna(bp) or pd.isna(bc):
                continue
            classement.at[equipe,'J'] += 1
            classement.at[equipe,'BP'] += bp
            classement.at[equipe,'BC'] += bc
            if bp > bc:
                classement.at[equipe,'V'] += 1
                classement.at[equipe,'Pts'] += 3
            elif bp < bc:
                classement.at[equipe,'D'] += 1
            else:
                classement.at[equipe,'N'] += 1
                classement.at[equipe,'Pts'] += 1
        
        classement['Diff'] = classement['BP'] - classement['BC']
        classement = classement.sort_values(by=['Pts','Diff','BP'], ascending=[False,False,False])
        classement.reset_index(inplace=True)
        classement.rename(columns={'index':'Equipe'}, inplace=True)
        classement.insert(0, 'Rang', range(1, len(classement)+1))
        return classement

    classement_dom = calcul_classement_domicile(df_dom)

    # Classement extérieur
    df_ext = df_matchs_saison.copy()
    df_ext = df_ext[['equipe_exterieure_nom', 'score_exterieur', 'score_domicile']].rename(
        columns={
            'equipe_exterieure_nom': 'Equipe',
            'score_exterieur': 'BP',
            'score_domicile': 'BC'
        }
    )

    def calcul_classement_exterieur(df):
        classement = pd.DataFrame(index=df['Equipe'].unique(), columns=['Pts','J','V','N','D','BP','BC','Diff'])
        classement.fillna(0, inplace=True)
        
        for _, row in df.iterrows():
            equipe = row['Equipe']
            bp, bc = row['BP'], row['BC']
            if pd.isna(bp) or pd.isna(bc):
                continue
            classement.at[equipe,'J'] += 1
            classement.at[equipe,'BP'] += bp
            classement.at[equipe,'BC'] += bc
            if bp > bc:
                classement.at[equipe,'V'] += 1
                classement.at[equipe,'Pts'] += 3
            elif bp < bc:
                classement.at[equipe,'D'] += 1
            else:
                classement.at[equipe,'N'] += 1
                classement.at[equipe,'Pts'] += 1
        
        classement['Diff'] = classement['BP'] - classement['BC']
        classement = classement.sort_values(by=['Pts','Diff','BP'], ascending=[False,False,False])
        classement.reset_index(inplace=True)
        classement.rename(columns={'index':'Equipe'}, inplace=True)
        classement.insert(0, 'Rang', range(1, len(classement)+1))
        return classement

    classement_ext = calcul_classement_exterieur(df_ext)

    # Affichage côte à côte
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🏡 Domicile")
        st.dataframe(
            style_table(classement_dom),
            use_container_width=True,
            hide_index=True,
            height=35 * len(classement_dom)
        )
    with col2:
        st.markdown("#### 🚗 Extérieur")
        st.dataframe(
            style_table(classement_ext),
            use_container_width=True,
            hide_index=True,
            height=35 * len(classement_ext)
        )

    # --- Statistiques globales sur la saison --- #
    st.markdown(f"#### 📊 Statistiques de la saison {saison_sel}")

    meilleure_dom = classement_dom.iloc[0]["Equipe"]
    pire_dom = classement_dom.iloc[-1]["Equipe"]
    meilleure_ext = classement_ext.iloc[0]["Equipe"]
    pire_ext = classement_ext.iloc[-1]["Equipe"]

    pts_dom = classement_dom.iloc[0]["Pts"]
    pts_dom_min = classement_dom.iloc[-1]["Pts"]
    pts_ext = classement_ext.iloc[0]["Pts"]
    pts_ext_min = classement_ext.iloc[-1]["Pts"]

    # Calcul du classement général sur la saison complète
    classement_saison = calcul_classement(df_matchs_saison)

    meilleure_attaque = classement_saison.loc[classement_saison['BP'].idxmax()]['Equipe']
    bp_max = classement_saison['BP'].max()
    meilleure_defense = classement_saison.loc[classement_saison['BC'].idxmin()]['Equipe']
    bc_min = classement_saison['BC'].min()

    max_victoires = classement_saison.loc[classement_saison['V'].idxmax()]
    max_nuls = classement_saison.loc[classement_saison['N'].idxmax()]
    max_defaites = classement_saison.loc[classement_saison['D'].idxmax()]

    # --- Collecte des stats --- #
    stats_saison = [
        {"label": "🏡 Meilleure équipe à domicile", "equipe": meilleure_dom, "valeur": pts_dom, "unit": "pts", "color": "linear-gradient(135deg, #4CAF50, #2E7D32)"},
        {"label": "🚗 Meilleure équipe à l'extérieur", "equipe": meilleure_ext, "valeur": pts_ext, "unit": "pts", "color": "linear-gradient(135deg, #1E88E5, #0D47A1)"},
        {"label": "⚽ Meilleure attaque", "equipe": meilleure_attaque, "valeur": bp_max, "unit": "buts marqués", "color": "linear-gradient(135deg, #FF9800, #F57C00)"},
        {"label": "🏠 Pire équipe à domicile", "equipe": pire_dom, "valeur": pts_dom_min, "unit": "pts", "color": "linear-gradient(135deg, #FFEB3B, #FBC02D); color:black;"},
        {"label": "🚙 Pire équipe à l'extérieur", "equipe": pire_ext, "valeur": pts_ext_min, "unit": "pts", "color": "linear-gradient(135deg, #F44336, #D32F2F)"},
        {"label": "🛡 Meilleure défense", "equipe": meilleure_defense, "valeur": bc_min, "unit": "buts encaissés", "color": "linear-gradient(135deg, #00BCD4, #00838F)"},
        {"label": "🏆 Plus de victoires", "equipe": max_victoires['Equipe'], "valeur": max_victoires['V'], "unit": "victoires", "color": "linear-gradient(135deg, #9C27B0, #6A1B9A)"},
        {"label": "🤝 Plus de nuls", "equipe": max_nuls['Equipe'], "valeur": max_nuls['N'], "unit": "matchs nuls", "color": "linear-gradient(135deg, #795548, #3E2723)"},
        {"label": "❌ Plus de défaites", "equipe": max_defaites['Equipe'], "valeur": max_defaites['D'], "unit": "défaites", "color": "linear-gradient(135deg, #607D8B, #263238)"},
    ]

    # --- Affichage en grille 3x3 --- #
    for i in range(0, len(stats_saison), 3):
        cols = st.columns(3)
        for j, stat in enumerate(stats_saison[i:i+3]):
            cols[j].markdown(f"""
            <div class='kpi-card' style='background: {stat['color']}; height:160px;'>
                <div style='font-size:16px; font-weight:500; margin-bottom:6px;'>{stat['label']}</div>
                <div style='font-size:22px; font-weight:700; margin-bottom:2px;'>{stat['equipe']}</div>
                <div style='font-size:18px; opacity:0.9;'>{stat['valeur']} {stat['unit']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ---------- ⚔️ Confrontations entre deux clubs ---------- #
    st.markdown(f"### ⚔️ Confrontations entre deux clubs – Saison {saison_sel}")

    # Filtrer les matchs pour la saison sélectionnée
    df_saison = df_all[df_all["saison"] == saison_sel].copy()

    # Liste des équipes présentes dans la saison
    equipes_dispo = sorted(pd.unique(df_saison[['equipe_domicile_nom', 'equipe_exterieure_nom']].values.ravel('K')))

    col1, col2 = st.columns(2)
    with col1:
        club1 = st.selectbox("Choisir le premier club :", equipes_dispo)
    with col2:
        club2 = st.selectbox("Choisir le second club :", equipes_dispo)

    valider = st.button("Afficher les confrontations")

    if valider:
        if club1 and club2 and club1 != club2:
            # --- Filtrer toutes les confrontations entre les deux clubs (toutes saisons) ---
            df_confrontations = df_all[
                ((df_all["equipe_domicile_nom"] == club1) & (df_all["equipe_exterieure_nom"] == club2)) |
                ((df_all["equipe_domicile_nom"] == club2) & (df_all["equipe_exterieure_nom"] == club1))
            ].copy()

            if df_confrontations.empty:
                st.info(f"Aucune confrontation enregistrée entre {club1} et {club2}.")
            else:
                # Calcul du score
                df_confrontations["Score"] = df_confrontations.apply(
                    lambda r: f"{int(r['score_domicile'])} - {int(r['score_exterieur'])}"
                    if pd.notna(r['score_domicile']) and pd.notna(r['score_exterieur']) else "-", axis=1
                )
            
            df_display = df_confrontations[["saison", "equipe_domicile_nom", "Score", "equipe_exterieure_nom"]].rename(columns={
                "saison": "Saison",
                "equipe_domicile_nom": "Équipe domicile",
                "equipe_exterieure_nom": "Équipe extérieure"
            })

            col1, col2 = st.columns([2,1])
            with col1 :
                st.dataframe(
                    df_display.style.set_properties(**{
                        'text-align': 'center',
                        'font-size': '14px',
                        'white-space': 'nowrap',
                    }).set_table_styles([
                        {"selector": "thead th", "props": [("background-color", "#0D47A1"), ("color", "white"), ("font-weight", "bold")]},
                        {"selector": "tbody tr:hover", "props": [("background-color", "#e3f2fd !important")]}
                    ]),
                    use_container_width=True,
                    height=500,
                    hide_index=True
                )

            # Statistiques globales sur toutes les saisons
            victoires_club1 = ((df_confrontations["equipe_domicile_nom"] == club1) & (df_confrontations["score_domicile"] > df_confrontations["score_exterieur"])).sum() + \
                                ((df_confrontations["equipe_exterieure_nom"] == club1) & (df_confrontations["score_exterieur"] > df_confrontations["score_domicile"])).sum()
            victoires_club2 = ((df_confrontations["equipe_domicile_nom"] == club2) & (df_confrontations["score_domicile"] > df_confrontations["score_exterieur"])).sum() + \
                                ((df_confrontations["equipe_exterieure_nom"] == club2) & (df_confrontations["score_exterieur"] > df_confrontations["score_domicile"])).sum()
            nuls = (df_confrontations["score_domicile"] == df_confrontations["score_exterieur"]).sum()

            with col2:
                # Styles individuels pour chaque KPI
                kpi_style1 = "background: linear-gradient(135deg, #FF1EC7FF, #951899FF); padding:15px; border-radius:15px; text-align:center; color:white; box-shadow:0 4px 12px rgba(0,0,0,0.2); margin-bottom:10px;"
                kpi_style2 = "background: linear-gradient(135deg, #00C6D4FF, #036C75FF); padding:15px; border-radius:15px; text-align:center; color:white; box-shadow:0 4px 12px rgba(0,0,0,0.2); margin-bottom:10px;"
                kpi_style3 = "background: linear-gradient(135deg, #00FF37FF, #028109FF); padding:15px; border-radius:15px; text-align:center; color:white; box-shadow:0 4px 12px rgba(0,0,0,0.2); margin-bottom:10px;"

                # Victoires club1
                st.markdown(f"""
                <div style="{kpi_style1}">
                    🏆<br>{club1}<br><b>{victoires_club1} victoires</b>
                </div>
                """, unsafe_allow_html=True)

                # Matchs nuls
                st.markdown(f"""
                <div style="{kpi_style2}">
                    🤝<br>Matchs nuls<br><b>{nuls}</b>
                </div>
                """, unsafe_allow_html=True)

                # Victoires club2
                st.markdown(f"""
                <div style="{kpi_style3}">
                    🏆<br>{club2}<br><b>{victoires_club2} victoires</b>
                </div>
                """, unsafe_allow_html=True)
        
        else:
            st.info("Veuillez choisir deux clubs différents pour voir les confrontations.")
