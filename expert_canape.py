import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from datetime import date
import xlsxwriter 
from io import BytesIO
import plotly.io as pio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
from google.oauth2.service_account import Credentials
import Fonctions

def show(tables):
    st.title("📊 Les Experts du Canapé")
    tabs_expert, tabs_insertion, tabs_excel = st.tabs(["Classement/Visualisation", "Insertion Pronos", "Export Excel"])
    
    # ---------------------- ONGLET 1 : PAR COMPÉTITION ----------------------
    with tabs_expert:
        
        # --- ⚡ CSS Glow Reactive Edition : Selectbox + Slider + Animation dynamique ---
        st.markdown("""
            <style>
            /* === Animations === */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-8px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes glowPulse {
                0%,100% { box-shadow: 0 0 0px var(--glow-color, transparent); }
                50% { box-shadow: 0 0 16px var(--glow-color, transparent); }
            }

            /* === Icônes colorées avant les labels === */
            label[data-testid="stWidgetLabel"] {
                font-weight: 600;
                font-size: 15px !important;
                margin-bottom: 6px !important;
                display: flex;
                align-items: center;
                gap: 6px;
                color: #e5e7eb !important;
            }

            label[data-testid="stWidgetLabel"]:has(span:contains('Saison'))::before {
                content: "📅"; color: #f59e0b;
            }
            label[data-testid="stWidgetLabel"]:has(span:contains('championnat'))::before {
                content: "🏆"; color: #3b82f6;
            }
            label[data-testid="stWidgetLabel"]:has(span:contains('journée'))::before {
                content: "📖"; color: #8b5cf6;
            }
            label[data-testid="stWidgetLabel"]:has(span:contains('participants'))::before {
                content: "👑"; color: #facc15;
            }

            label[data-testid="stWidgetLabel"]::before {
                font-size: 18px;
                transition: transform 0.3s ease, filter 0.3s ease;
            }
            label[data-testid="stWidgetLabel"]:hover::before {
                transform: scale(1.25) rotate(10deg);
                filter: brightness(1.3);
            }

            /* === Selectbox base === */
            div[data-baseweb="select"] > div {
                background-color: #1f2937 !important;
                border: 1px solid #374151 !important;
                border-radius: 10px !important;
                color: white !important;
                height: 42px !important;
                transition: all 0.25s ease-in-out;
            }

            /* === Hover (lueur douce) === */
            div[data-baseweb="select"] > div:hover {
                border-color: var(--glow-color, #3b82f6) !important;
                box-shadow: 0 0 10px var(--glow-color, #3b82f688);
            }

            /* === Animation pulsante au focus === */
            div[data-baseweb="select"]:focus-within > div {
                animation: glowPulse 1s ease-in-out;
                border-color: var(--glow-color, #3b82f6) !important;
            }

            /* === Couleurs personnalisées par type === */
            div[data-testid="stSelectbox"]:has(label:has(span:contains('Saison'))) div[data-baseweb="select"] { --glow-color: #f59e0b; }
            div[data-testid="stSelectbox"]:has(label:has(span:contains('championnat'))) div[data-baseweb="select"] { --glow-color: #3b82f6; }
            div[data-testid="stSelectbox"]:has(label:has(span:contains('journée'))) div[data-baseweb="select"] { --glow-color: #8b5cf6; }
            div[data-testid="stSelectbox"]:has(label:has(span:contains('participants'))) div[data-baseweb="select"] { --glow-color: #facc15; }

            /* === Menu déroulant (fade-in + style propre) === */
            ul[role="listbox"] {
                background-color: #111827 !important;
                border: 1px solid #374151 !important;
                border-radius: 10px !important;
                padding: 4px;
                animation: fadeIn 0.3s ease-in-out;
            }
            li[role="option"] {
                color: #f3f4f6 !important;
                font-size: 14px;
                padding: 8px 12px !important;
                border-radius: 6px;
                transition: background 0.15s, transform 0.1s;
            }
            li[role="option"]:hover {
                background-color: #2563eb !important;
                color: white !important;
                transform: scale(1.02);
            }

            /* === Slider === */
            div[data-baseweb="slider"] div[role="slider"] {
                background-color: #facc15 !important;
                box-shadow: 0 0 8px rgba(250,204,21,0.6);
                transition: all 0.3s ease;
            }
            div[data-baseweb="slider"] div[role="slider"]:hover {
                background-color: #fde047 !important;
                box-shadow: 0 0 12px rgba(250,204,21,0.8);
            }
            </style>
        """, unsafe_allow_html=True)

        # --- Charger les CSV une seule fois --- #
        df_matchs = tables["all_matchs_football"]
        df_pronos = tables["all_pronostics"]
        df_bonus = tables["bonus"]

        # --- Nettoyage rapide --- #
        for col in ["saison", "competition", "journee"]:
            if col in df_matchs.columns:
                df_matchs[col] = df_matchs[col].astype(str)

        # === 🎛️ Sélecteurs === #
        col_select_saison, col_select_championnat, col_select_journee, col_select_best = st.columns(4)

        # --- Sélection de la saison --- #
        with col_select_saison:

            # Toutes les saisons disponibles dans les matchs
            saisons = sorted(df_matchs["saison"].dropna().unique(), reverse=True)

            # Garder uniquement les saisons ayant au moins 1 participant
            if "participant_nom" in df_pronos.columns:
                saisons_avec_participants = (
                    df_pronos
                    .dropna(subset=["participant_nom"])
                    .groupby("saison")["participant_nom"]
                    .nunique()
                )

                saisons = [
                    saison for saison in saisons
                    if saisons_avec_participants.get(saison, 0) > 0
                ]

            # Sécurité : aucune saison avec participant
            if not saisons:
                st.warning("⚠️ Aucun participant trouvé dans aucune saison.")
                st.stop()

            # La première est automatiquement la saison la plus récente
            saison_sel = st.selectbox(
                "Sélectionner une saison",
                saisons,
                index=0
            )

        # --- Sélection du championnat --- #
        with col_select_championnat:
            championnats = df_matchs[df_matchs["saison"] == saison_sel]["competition"].dropna().unique().tolist()
        #   championnats = ["Toutes"] + sorted(championnats)
            championnats = sorted(championnats)
            default_champ = "Ligue 1" if "Ligue 1" in championnats else "Ligue 2"
        #   default_champ = "Coupe du Monde" if "Coupe du Monde" in championnats else "Toutes"
            championnat_sel = st.selectbox("Sélectionner un championnat", championnats, index=championnats.index(default_champ))

        # --- Sélection de la journée --- #
        with col_select_journee:
            # --- Récupération des journées disponibles --- #
            if championnat_sel == "Toutes":
                df_journees = df_matchs[df_matchs["saison"] == saison_sel].copy()
            else:
                df_journees = df_matchs[
                    (df_matchs["saison"] == saison_sel) &
                    (df_matchs["competition"] == championnat_sel)
                ].copy()

            # Nettoyage et conversion en int
            df_journees = df_journees.dropna(subset=["journee"])
            df_journees["journee"] = pd.to_numeric(df_journees["journee"], errors="coerce")
            df_journees["date"] = pd.to_datetime(df_journees["date"], errors="coerce")
            journees = sorted(df_journees["journee"].dropna().unique())
            
            # --- 📅 Détermination de la dernière journée jouée --- #
            # Une journée est "jouée" si elle a au moins un score renseigné
            # Une journée est considérée jouée si AU MOINS UN match a un score
            df_journees["match_joue"] = (df_journees["score_domicile"].notna() & df_journees["score_exterieur"].notna())

            journees_jouees = (df_journees.groupby("journee")["match_joue"].any())
            journees_jouees = (journees_jouees[journees_jouees].index.tolist())

            derniere_journee = (max(journees_jouees) if journees_jouees else min(df_journees["journee"]))
            prochaine_journee = derniere_journee + 1 if derniere_journee is not None else min(df_journees["journee"])

            # --- Prochains matchs ---
            if championnat_sel == "Toutes":
                df_prochaine = df_journees[df_journees["journee"] == prochaine_journee].sort_values("date")
            else:
                df_prochaine = df_journees[
                    (df_journees["journee"] == prochaine_journee) &
                    (df_journees["competition"] == championnat_sel)
                ].sort_values("date")
            date_prochain_match = df_prochaine["date"].min().strftime("%d %B %Y à 19 h") if not df_prochaine.empty else "à venir"
            matchs_prochaine = " | ".join(f"{r['equipe_domicile_nom']} vs {r['equipe_exterieure_nom']}" for _, r in df_prochaine.iterrows()) or "Aucun match programmé."

            # --- Résultats dernière journée ---
            df_derniere = df_journees[df_journees["journee"] == derniere_journee].sort_values("date")
            resultats_derniere = " | ".join(
                f"{r['equipe_domicile_nom']} {int(r['score_domicile'])}-{int(r['score_exterieur'])} {r['equipe_exterieure_nom']}"
                for _, r in df_derniere.iterrows()
                if pd.notna(r["score_domicile"]) and pd.notna(r["score_exterieur"])
            ) or "Aucun résultat disponible."

            # --- Sélecteur Streamlit --- #
            options_journees = ["Toutes"] + [str(j) for j in journees]
            default_index = options_journees.index(str(derniere_journee))

            journee_sel = st.selectbox(
                "Sélectionner une journée",
                options_journees,
                index=default_index
            )

            # Convertir en int et trier
            try:
                journees = sorted(map(int, journees))
            except ValueError:
                journees = sorted(journees)  # Si ce sont des strings

        with col_select_best:
            # 🔍 Filtrer les pronostics pour la saison sélectionnée
            if championnat_sel == "Toutes":
                df_saison_pronos = df_pronos[df_pronos["saison"] == saison_sel].copy()
            else:
                df_saison_pronos = df_pronos.loc[
                    (df_pronos["saison"] == saison_sel) &
                    (df_pronos["competition_nom"] == championnat_sel)
                ].copy()

            # 🧮 Calcul du nombre de participants uniques
            if not df_saison_pronos.empty and "participant_nom" in df_saison_pronos.columns:
                nb_participants = df_saison_pronos["participant_nom"].nunique()
            else:
                nb_participants = 0

            # ⚙️ Slider dynamique selon le nombre réel de participants
            if nb_participants > 0:
                top_n = nb_participants
                #st.slider(
                #    "Afficher les meilleurs participants",
                #    min_value=1,
                #    max_value=nb_participants,
                #    value=min(10, nb_participants),
                #    step=1,
                #    help=f"Sur un total de {nb_participants} participants pour {saison_sel} ({championnat_sel})"
                #)
            else:
                st.warning("⚠️ Aucun participant trouvé pour cette saison / championnat.")
                top_n = 0

        # --- Vérifier l'état des pronostics pour la prochaine journée ---
        etat_pronos = []

        # Filtrer les participants actifs pour cette saison/championnat
        if championnat_sel == "Toutes":
            participants_saison = df_pronos[df_pronos["saison"] == saison_sel]["participant_nom"].dropna().unique()
        else:
            participants_saison = (
                df_pronos.merge(df_matchs[["match_id", "competition"]], on="match_id", how="left")
                        .query("saison == @saison_sel and competition == @championnat_sel")
                        ["participant_nom"]
                        .dropna()
                        .unique()
            )

        # Boucle pour vérifier si chaque participant a fait ses pronos pour la prochaine journée
        for p in participants_saison:
            if championnat_sel == "Toutes":
                df_check = df_pronos[
                    (df_pronos["saison"] == saison_sel) &
                    (df_pronos["participant_nom"] == p) &
                    (df_pronos["journee"] == prochaine_journee)
                ]
            else:
                df_check = df_pronos.merge(df_matchs[["match_id", "competition"]], on="match_id", how="left").query(
                    "saison == @saison_sel and competition == @championnat_sel and participant_nom == @p and journee == @prochaine_journee"
                )

            # ✅ si pronostic existant pour cette journée, ❌ sinon
            if not df_check.empty:
                etat_pronos.append(f"<span style='color:#FFFFFFFF;font-weight:600;'>{p} ✅</span>")
            else:
                etat_pronos.append(f"<span style='color:#F75E5EFF;font-weight:600;'>{p} ❌</span>")

        # --- Concaténer pour l'affichage ---
        etat_html = " • ".join(etat_pronos) if etat_pronos else "Aucun participant"

        # === 💫 Ruban animé Streamlit avec défilement continu === #
        texte_pronos = etat_html  # ton texte participants avec ✅/❌

        st.markdown(f"""
        <style>
        @keyframes scrollInfinite {{
            0% {{ transform: translateX(0); }}
            100% {{ transform: translateX(-100%); }}
        }}
        .ribbon {{
            overflow: hidden;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.25);
            margin-bottom: 15px;
            text-align: center;
        }}
        .ribbon-prochaine {{
            background: linear-gradient(90deg, #2563eb, #3b82f6, #60a5fa);
            color: white;
            padding: 10px 0;
            position: relative;
        }}
        .ribbon-text-wrapper {{
            display: inline-block;
            white-space: nowrap;
        }}
        .ribbon-text-track {{
            display: inline-block;
            white-space: nowrap;
            animation: scrollInfinite 300s linear infinite;
        }}
        .ribbon-text {{
            display: inline-block;
            padding-right: 3rem; /* espace entre deux passages */
            font-weight: 600;
            font-size: 16px;
        }}
        .ribbon-resultats {{
            background: linear-gradient(90deg, #6b7280, #9ca3af, #d1d5db);
            color: black;
            padding: 10px 0;
        }}
        </style>

        <!-- Bandeau Prochaine Journée avec participants défilants -->
        <div class="ribbon ribbon-prochaine">
            <div class="ribbon-text-track">
                <div class="ribbon-text-wrapper">
                    <span class="ribbon-text">⚽ <strong>Prochaine journée : {prochaine_journee}</strong> • Préparez vos pronostics avant le <strong>{date_prochain_match}</strong> ⏰ ➜ {matchs_prochaine} • 📊 État des pronostics : {texte_pronos}</span>
                    <span class="ribbon-text">⚽ <strong>Prochaine journée : {prochaine_journee}</strong> • Préparez vos pronostics avant le <strong>{date_prochain_match}</strong> ⏰ ➜ {matchs_prochaine} • 📊 État des pronostics : {texte_pronos}</span>
                    <span class="ribbon-text">⚽ <strong>Prochaine journée : {prochaine_journee}</strong> • Préparez vos pronostics avant le <strong>{date_prochain_match}</strong> ⏰ ➜ {matchs_prochaine} • 📊 État des pronostics : {texte_pronos}</span>
                    <span class="ribbon-text">⚽ <strong>Prochaine journée : {prochaine_journee}</strong> • Préparez vos pronostics avant le <strong>{date_prochain_match}</strong> ⏰ ➜ {matchs_prochaine} • 📊 État des pronostics : {texte_pronos}</span>
                    <span class="ribbon-text">⚽ <strong>Prochaine journée : {prochaine_journee}</strong> • Préparez vos pronostics avant le <strong>{date_prochain_match}</strong> ⏰ ➜ {matchs_prochaine} • 📊 État des pronostics : {texte_pronos}</span>
                    <span class="ribbon-text">⚽ <strong>Prochaine journée : {prochaine_journee}</strong> • Préparez vos pronostics avant le <strong>{date_prochain_match}</strong> ⏰ ➜ {matchs_prochaine} • 📊 État des pronostics : {texte_pronos}</span>
                    <span class="ribbon-text">⚽ <strong>Prochaine journée : {prochaine_journee}</strong> • Préparez vos pronostics avant le <strong>{date_prochain_match}</strong> ⏰ ➜ {matchs_prochaine} • 📊 État des pronostics : {texte_pronos}</span>
                    <span class="ribbon-text">⚽ <strong>Prochaine journée : {prochaine_journee}</strong> • Préparez vos pronostics avant le <strong>{date_prochain_match}</strong> ⏰ ➜ {matchs_prochaine} • 📊 État des pronostics : {texte_pronos}</span>
                </div>
            </div>
        </div>

        <!-- Ruban résultats dernière journée -->
        <div class="ribbon ribbon-resultats">
            <div class="ribbon-text-track">
                <span class="ribbon-text"> 🏁 <strong>Résultats de la journée {derniere_journee}</strong> ➜ {resultats_derniere}</span>
                <span class="ribbon-text"> 🏁 <strong>Résultats de la journée {derniere_journee}</strong> ➜ {resultats_derniere}</span>
                <span class="ribbon-text"> 🏁 <strong>Résultats de la journée {derniere_journee}</strong> ➜ {resultats_derniere}</span>
                <span class="ribbon-text"> 🏁 <strong>Résultats de la journée {derniere_journee}</strong> ➜ {resultats_derniere}</span>
                <span class="ribbon-text"> 🏁 <strong>Résultats de la journée {derniere_journee}</strong> ➜ {resultats_derniere}</span>
                <span class="ribbon-text"> 🏁 <strong>Résultats de la journée {derniere_journee}</strong> ➜ {resultats_derniere}</span>
                <span class="ribbon-text"> 🏁 <strong>Résultats de la journée {derniere_journee}</strong> ➜ {resultats_derniere}</span>
                <span class="ribbon-text"> 🏁 <strong>Résultats de la journée {derniere_journee}</strong> ➜ {resultats_derniere}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- 🔍 Filtrer la saison et le championnat, mais PAS la journée (pour permettre le cumul) --- #
        df_filtre = df_matchs[df_matchs["saison"] == saison_sel].copy()
        if championnat_sel != "Toutes":
            df_filtre = df_filtre[df_filtre["competition"] == championnat_sel]

        # --- Fusion avec les pronostics (on garde tous les matchs de la saison filtrée) --- #
        if "match_id" not in df_filtre.columns or "match_id" not in df_pronos.columns:
            st.warning("Impossible de faire le merge : la colonne 'match_id' est manquante")
            return

        df_merge = df_pronos.merge(
            df_filtre,
            on="match_id",
            suffixes=("_prono", "_match"),
            how="inner"
        )

        if df_merge.empty:
            st.info("Aucun pronostic enregistré pour cette sélection.")
            return

        # --- Préparation du DataFrame final --- #
        df = df_merge[[
            "participant_id", "participant_nom",
            "score_domicile_prono", "score_exterieur_prono",
            "score_domicile_match", "score_exterieur_match",
            "equipe_domicile_nom", "equipe_exterieure_nom",
            "cote_domicile", "cote_exterieur", "cote_nul",
            "journee_match", "saison_match", "competition"
        ]].rename(columns={
            "score_domicile_prono": "prono_dom",
            "score_exterieur_prono": "prono_ext",
            "score_domicile_match": "match_dom",
            "score_exterieur_match": "match_ext"
        })
        
        # --- Détection des scores exacts ---
        df["bon_score"] = ((df["prono_dom"] == df["match_dom"]) & (df["prono_ext"] == df["match_ext"]))

        # Convertir les journées en int
        df["journee_match"] = pd.to_numeric(df["journee_match"], errors="coerce")
        df = df.dropna(subset=["journee_match"])
        df["journee_match"] = df["journee_match"].astype(int)

        # --- Calcul des points individuels --- #
        df["points"] = df.apply(Fonctions.calcul_points, axis=1)

        # --- Calcul des points par journée et cumul --- #
        df_progress_all = (df.groupby(["participant_nom", "journee_match"]).apply(Fonctions.calcul_points_journee).reset_index())
        df_progress_all["points_cumul"] = df_progress_all.groupby("participant_nom")["points"].cumsum()

        # --- 🧮 Filtrage jusqu’à la journée sélectionnée --- #
        if journee_sel != "Toutes":
            try:
                journee_num = int(journee_sel)
                df_progress_filtered = df_progress_all[df_progress_all["journee_match"] <= journee_num]
            except ValueError:
                df_progress_filtered = df_progress_all.copy()
        else:
            df_progress_filtered = df_progress_all.copy()

        # --- KPI ---
        nb_matchs = df_filtre["match_id"].nunique()
        nb_pronos = len(df)
        nb_participants = df["participant_nom"].nunique()
        total_points = df_progress_all["points"].sum()
        moyenne_points_joueur = total_points / nb_participants if nb_participants else 0

        kpi_cols = st.columns([1.2, 1, 1, 1])
        with kpi_cols[0]: Fonctions.kpi_card("🏟️ Matchs", nb_matchs, color="#3b82f6", width="100%", height="80px")
        with kpi_cols[1]: Fonctions.kpi_card("🧾 Pronostics", nb_pronos, color="#22c55e", width="100%", height="80px")
        with kpi_cols[2]: Fonctions.kpi_card("👥 Participants", nb_participants, color="#f59e0b", width="100%", height="80px")
        with kpi_cols[3]: Fonctions.kpi_card("🎯 Moy. pts/joueur", f"{moyenne_points_joueur:.2f}", color="#2563eb", width="100%", height="80px")

        st.markdown("---")

        # --- Affichage classement et progression ---
        st.subheader(f"Classement {'global' if journee_sel == 'Toutes' else f'jusqu’à la journée {journee_sel}'} – "
            f"{'toutes compétitions' if championnat_sel == 'Toutes' else championnat_sel} – {saison_sel}")

        col_classement, col_evolution = st.columns([1, 2])
        with col_classement:
            journee_num = None
            # === 🕓 Classement précédent (pour visualiser les places gagnées/perdues) === #
            if journee_sel != "Toutes":
                try:
                    journee_num = int(journee_sel)
                    if journee_num > 1:
                        # Classement cumulé jusqu’à la journée précédente
                        df_progress_prev = df_progress_all[df_progress_all["journee_match"] <= journee_num - 1]

                        classement_prec = (
                            df_progress_prev.groupby("participant_nom", as_index=False)["points_cumul"]
                            .max()
                            .sort_values(by="points_cumul", ascending=False)
                            .reset_index(drop=True)
                        )
                        classement_prec.rename(columns={"points_cumul": "points"}, inplace=True)
                        classement_prec["Rang"] = classement_prec.index + 1
                    else:
                        classement_prec = None  # pas de classement précédent pour la 1re journée
                except ValueError:
                    classement_prec = None
            else:
                classement_prec = None
            
            # --- 🎯 CALCUL FINAL DU CLASSEMENT (cumul + bonus) --- #
            # Calcul du cumul actuel
            classement = (
                df_progress_filtered
                    .groupby("participant_nom", as_index=False)["points_cumul"]
                    .max()
                    .rename(columns={"points_cumul": "points"})
            )

            # Calcul du classement précédent
            classement_prec = None

            if journee_num and journee_num > 1:
                df_prev = df_progress_all[df_progress_all["journee_match"] <= journee_num - 1]

                classement_prec = (
                    df_prev
                        .groupby("participant_nom", as_index=False)["points_cumul"]
                        .max()
                        .rename(columns={"points_cumul": "points"})
                        .sort_values("points", ascending=False)
                        .reset_index(drop=True)
                )
                classement_prec["Rang"] = classement_prec.index + 1

            # Intégration des bonus
            classement["bonus"] = 0
            classement["correction"] = 0

            inclure_bonus = st.checkbox("Prendre en compte les bonus", value=False)

            # --- Fusion bonus uniquement si table OK --- #
            if isinstance(df_bonus, pd.DataFrame) and "participant" in df_bonus.columns:

                if championnat_sel == "Toutes":
                    df_bonus_filtered = (
                        df_bonus[df_bonus["saison"] == saison_sel]
                        .groupby("participant", as_index=False)[["total_bonus", "correction"]]
                        .sum()
                    )
                else:
                    df_bonus_filtered = (
                        df_bonus[
                            (df_bonus["saison"] == saison_sel) &
                            (df_bonus["competition"] == championnat_sel)
                        ]
                        .groupby("participant", as_index=False)[["total_bonus", "correction"]]
                        .sum()
                    )

                df_bonus_filtered = df_bonus_filtered.fillna(0)

                # merge sans risque
                classement = classement.merge(
                    df_bonus_filtered,
                    left_on="participant_nom",
                    right_on="participant",
                    how="left"
                )

                # Sécurisation totale : si colonnes manquantes → 0
                if "total_bonus" not in classement.columns:
                    classement["total_bonus"] = 0

                if "correction_y" in classement.columns:
                    classement["correction"] = classement["correction_y"]
                elif "correction" in classement.columns:
                    # déjà bon
                    pass
                else:
                    classement["correction"] = 0

                classement["bonus"] = classement["total_bonus"]

            # --- Sécurisation finale : toujours 2 colonnes existantes --- #
            for col in ["bonus", "correction"]:
                if col not in classement.columns:
                    classement[col] = 0
                classement[col] = classement[col].fillna(0)

            # --- Calcul final --- #
            classement["points_final"] = (
                classement["points"]
                + classement["correction"]
                + (classement["bonus"] if inclure_bonus else 0)
            )

            classement = classement.sort_values(by="points_final", ascending=False).reset_index(drop=True)
            classement["Rang"] = classement.index + 1

            Fonctions.afficher_classement_visuel(classement, saison_sel, championnat_sel if championnat_sel != "Toutes" else None, classement_prec=classement_prec, inclure_bonus=inclure_bonus)

        with col_evolution:
            st.markdown('')
            st.markdown('')

            # --- Préparer df_cumul avec points cumulés ---
            df_cumul = classement[["participant_nom", "Rang", "points", "bonus"]].merge(
                df_progress_all.groupby("participant_nom")["points_cumul"].apply(list).reset_index(),
                on="participant_nom"
            )

            # Conversion en int pour trier correctement
            df_progress_all["journee_match"] = df_progress_all["journee_match"].astype(int)
            df_progress_all = df_progress_all.sort_values(["journee_match", "participant_nom"]).reset_index(drop=True)

            # Calcul de la moyenne cumulée (hors bonus)
            df_moyenne = (
                df_progress_all.groupby("journee_match")["points"]
                .mean()
                .cumsum()
                .reset_index()
            )
            df_moyenne = df_moyenne.rename(columns={"points": "points_cumul_moyenne"})

            # --- Ajouter le bonus comme "journée" supplémentaire si activé ---
            if inclure_bonus:
                max_journee = df_progress_all["journee_match"].max()
                points_cumul_final = []
                for _, row in df_cumul.iterrows():
                    cumul = row["points_cumul"].copy()
                    cumul.append(cumul[-1] + row["bonus"])  # ajouter bonus
                    points_cumul_final.append(cumul)
                df_cumul["points_cumul_affiche"] = points_cumul_final
            else:
                df_cumul["points_cumul_affiche"] = df_cumul["points_cumul"]

            # --- Graphique ---
            fig = go.Figure()
            colors = px.colors.qualitative.Safe

            for i, (_, row) in enumerate(df_cumul.head(top_n).iterrows()):
                x_vals = list(range(1, len(row["points_cumul_affiche"]) + 1))
                fig.add_trace(go.Scatter(
                    x=x_vals,
                    y=row["points_cumul_affiche"],
                    mode='lines+markers',
                    name=row["participant_nom"],
                    line=dict(color=colors[i % len(colors)], width=3),
                    marker=dict(size=8)
                ))

            # Ajouter moyenne championnat (sans bonus)
            fig.add_trace(go.Scatter(
                x=df_moyenne["journee_match"],
                y=df_moyenne["points_cumul_moyenne"],
                mode='lines+markers',
                name="Moyenne championnat",
                line=dict(color="dodgerblue", width=3, dash="dot"),
                marker=dict(size=7)
            ))

            # Ajuster l'axe x si bonus inclus
            x_max = df_progress_all["journee_match"].max() + (1 if inclure_bonus else 0) + 1

            fig.update_layout(
                xaxis=dict(title="Journée", tickmode="linear", range=[0, x_max]),
                yaxis=dict(title="Points cumulés"),
                plot_bgcolor="black",
                hovermode="x unified",
                height=450,
                margin=dict(l=40, r=40, t=50, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        
        # =====================================================
        # CALCULS JOURNÉE
        # =====================================================

        # Recalcul des points de chaque pronostic
        df["points"] = df.apply(Fonctions.calcul_points, axis=1)

        # Filtre sur la journée choisie
        if journee_sel != "Toutes":
            df_journee = df[df["journee_match"] == int(journee_sel)].copy()
        else:
            df_journee = df.copy()

        if df_journee.empty:
            st.warning("Aucune donnée disponible.")
            st.stop()

        journee_courante = df_journee["journee_match"].iloc[0]

        # =====================================================
        # CLASSEMENT DE LA JOURNÉE
        # =====================================================

        # Points bruts (sans bonus)
        points_sans_bonus = (df_journee.groupby("participant_nom")["points"].sum().reset_index().rename(columns={"points": "points_bruts"}))

        # Points totaux (avec bonus)
        df_journee_bonus = (df_journee.groupby("participant_nom").apply(Fonctions.calcul_points_journee).reset_index().rename(columns={"points": "points_total"}))

        # Nombre de scores exacts
        bons_scores = (df_journee[df_journee["bon_score"] == True].groupby("participant_nom").size().reset_index(name="bons_scores"))

        # Fusion des résultats
        classement_journee = (points_sans_bonus.merge(df_journee_bonus, on="participant_nom", how="left").merge(bons_scores, on="participant_nom", how="left"))

        classement_journee["bons_scores"] = (classement_journee["bons_scores"].fillna(0).astype(int))

        # Bonus obtenu
        classement_journee["points_bonus"] = (classement_journee["points_total"] - classement_journee["points_bruts"]).round(2)

        # Tri classement
        classement_journee = (classement_journee.sort_values("points_total", ascending=False).reset_index(drop=True))

        classement_journee["Rang"] = classement_journee.index + 1

        # Performance relative au meilleur joueur
        max_points = classement_journee["points_total"].max()

        classement_journee["Performance (%)"] = (classement_journee["points_total"] / max_points * 100).round(1)

        # Renommage
        classement_journee = classement_journee.rename(
            columns={
                "participant_nom": "Participant",
                "points_total": "Total Points",
                "points_bonus": "Dont Bonus",
                "bons_pronos": "Nombre de bons pronos",
                "bons_scores": "Nombre de bons scores"
            }
        )

        # =====================================================
        # TABLEAU GLOBAL DES PRONOSTICS
        # =====================================================

        df_journee["Match"] = (df_journee["equipe_domicile_nom"] + " - " + df_journee["equipe_exterieure_nom"])

        df_journee["Score Réel"] = df_journee.apply(Fonctions.format_score_reel, axis=1)

        df_journee["points_txt"] = (df_journee["points"].fillna(0).astype(float).map(lambda x: f"{x:.2f}"))

        df_journee["Prono Points"] = (df_journee["prono_dom"].fillna(0).astype(int).astype(str) + "-" + df_journee["prono_ext"].fillna(0).astype(int).astype(str) + " (" + df_journee["points_txt"] + ")")

        table_globale = (
            df_journee
            .pivot_table(
                index=["Match", "Score Réel"],
                columns="participant_nom",
                values="Prono Points",
                aggfunc="first"
            )
            .reset_index()
        )
        
        # =====================================================
        # VUE GLOBALE
        # =====================================================

        st.markdown(f"### 📝 Tous les pronostics - Journée {journee_sel}")

        st.dataframe(
            table_globale.style.apply(Fonctions.color_pronos, axis=None),
            hide_index=True,
            use_container_width=True
        )

        details_cotes = (
            df_journee[
                [
                    "Match",
                    "match_dom",
                    "match_ext",
                    "cote_domicile",
                    "cote_nul",
                    "cote_exterieur"
                ]
            ]
            .drop_duplicates()
            .copy()
        )

        details_cotes["cote_gagnante"] = details_cotes.apply(Fonctions.get_cote_gagnante, axis=1)

        # Score affiché sans décimales
        details_cotes["Score"] = details_cotes.apply(Fonctions.format_score, axis=1)

        details_cotes = details_cotes.rename(
            columns={
                "cote_domicile": "1",
                "cote_nul": "N",
                "cote_exterieur": "2",
                "cote_gagnante": "Cote gagnante"
            }
        )

        details_cotes = details_cotes[
            [
                "Match",
                "Score",
                "1",
                "N",
                "2",
                "Cote gagnante"
            ]
        ]

        col_detail_pronos, col_classement_journee = st.columns(2)
        
        with col_detail_pronos:
            st.markdown("### 💰 Cotes des matchs")

            st.dataframe(details_cotes.style.apply(Fonctions.color_cotes, axis=1).format({"1": "{:.2f}", "N": "{:.2f}", "2": "{:.2f}", "Cote gagnante": "{:.2f}"}),
                    hide_index=True,
                    use_container_width=False
            )
        
        with col_classement_journee:
            st.markdown(f"### 🏅 Détails du classement de la journée {journee_courante}")

            st.dataframe(
                classement_journee[
                    [
                    "Rang",
                    "Participant",
                    "Total Points",
                    "Nombre de bons pronos",
                    "multiplicateur",
                    "Performance (%)"
                ]
            ].style.format({
                "Rang": "{:.0f}",
                "Total Points": "{:.2f}",
                "Nombre de bons pronos": "{:.0f}",
                "multiplicateur": "{:.2f}",
                "Performance (%)": "{:.1f}"
            }),
                hide_index=True,
                use_container_width=False
            )

        # =====================================================
        # SÉLECTION JOUEUR
        # =====================================================

        st.divider()
        st.markdown("### 🎮 Analyse d'un joueur")

        participants = classement["participant_nom"].tolist()

        if "participant_sel" not in st.session_state:
            st.session_state.participant_sel = participants[0]

        cols = st.columns(10)

        for idx, participant in enumerate(participants):
            col = cols[idx % 10]

            if col.button(participant, key=f"joueur_{participant}", use_container_width=True):
                st.session_state.participant_sel = participant

        participant_sel = st.session_state.participant_sel

        # =====================================================
        # DÉTAILS DU JOUEUR
        # =====================================================

        df_participant = df[df["participant_nom"] == participant_sel].copy()
        joueur_stats = classement_journee[classement_journee["Participant"] == participant_sel]
        
        nb_matchs_journee = df_journee["Match"].nunique()
                    
        # --- Résumé personnel ---
        points_bruts = 0
        points_bonus = 0
        bons_pronos = 0
        multiplicateur = 1
        rang = "-"
        perf = 0
        bons_scores = 0

        if joueur_stats.empty:
            st.warning(f"Aucune statistique disponible pour {participant_sel} pour la journée {journee_sel}")
        else:
            points_bruts = joueur_stats["points_bruts"].values[0]
            points_bonus = joueur_stats["Dont Bonus"].values[0]
            bons_pronos = joueur_stats["Nombre de bons pronos"].values[0]
            multiplicateur = joueur_stats["multiplicateur"].values[0]
            rang = joueur_stats["Rang"].values[0]
            perf = joueur_stats["Performance (%)"].values[0]
            bons_scores = joueur_stats["Nombre de bons scores"].values[0]

        st.markdown(f"### 👤 Statistiques de {participant_sel} - Journée {journee_courante}")

        # Colonnes KPI améliorées
        kpi_cols = st.columns([1, 1, 1, 1, 1, 1])

        with kpi_cols[0]: Fonctions.kpi_card("🏆 Rang", rang, color="#3b82f6", width="100%", height="80px")  
        with kpi_cols[1]: Fonctions.kpi_card("💯 Points bruts", f"{points_bruts:.2f}", color="#22c55e", width="100%", height="80px")  
        with kpi_cols[2]: Fonctions.kpi_card("🎯 Bons pronos", f"{bons_pronos} / {nb_matchs_journee}", color="#f59e0b", width="100%", height="80px")  
        with kpi_cols[3]: Fonctions.kpi_card("🎯 Bons scores", f"{bons_scores}", color="#ef4444", width="100%", height="80px")
        with kpi_cols[4]: Fonctions.kpi_card("✨ Points avec bonus", f"{points_bonus:.2f}", color="#9333ea", width="100%", height="80px")  
        with kpi_cols[5]: Fonctions.kpi_card("⚡ Multiplicateur", f"x{multiplicateur}", color="#9333ea", width="100%", height="80px")  

        # Sécuriser la valeur de la barre de progression
        perf_safe = 0 if pd.isna(perf) else perf
        
        # S'assurer que la valeur est entre 0 et 100
        perf_safe = max(0, min(100, perf_safe))

        # --- Barre de performance visuelle ---
        st.progress(perf_safe / 100)
        st.caption(f"Performance de {perf_safe:.1f}% par rapport au meilleur score de la journée.")
                
        # Filtrer les matchs du joueur sélectionné
        df_joueur = df[df["participant_nom"] == participant_sel].copy()
        df_joueur_participant = df_progress_all[df_progress_all["participant_nom"] == participant_sel].copy()

        # --- Calculs de points par match avec bonus ---
        df_joueur["points"] = df_joueur.apply(Fonctions.calcul_points, axis=1)

        # --- Bons pronos ---
        df_joueur["bon_prono"] = (
            ((df_joueur["prono_dom"] > df_joueur["prono_ext"]) & (df_joueur["match_dom"] > df_joueur["match_ext"])) |
            ((df_joueur["prono_dom"] < df_joueur["prono_ext"]) & (df_joueur["match_dom"] < df_joueur["match_ext"])) |
            ((df_joueur["prono_dom"] == df_joueur["prono_ext"]) & (df_joueur["match_dom"] == df_joueur["match_ext"])))
        
        # --- Bons scores (score exact) ---
        df_joueur["bon_score"] = (
            (df_joueur["prono_dom"] == df_joueur["match_dom"]) &
            (df_joueur["prono_ext"] == df_joueur["match_ext"]))

        # --- Bonus multiplicateurs par match ---
        df_joueur["bonus"] = df_joueur.apply(lambda r: float(Fonctions.calcul_points_journee(pd.DataFrame([r]))["multiplicateur"]), axis=1)

        # --- Stats globales ---
        total_points = df_joueur["points"].sum().round(2)
        moyenne_points = df_joueur["points"].mean().round(2)
        max_points_match = df_joueur["points"].max().round(2)
        min_points_match = df_joueur["points"].min().round(2)
        nb_bons_scores = df_joueur["bon_score"].sum()
        
        # Somme des points par journée
        points_par_journee = df_joueur_participant.groupby("journee_match")["points"].sum()

        # Meilleur score sur une journée
        meilleur_score_journee = points_par_journee.max().round(2)
        
        nb_bons_pronos = df_joueur["bon_prono"].sum()
        total_pronos = len(df_joueur)
        pourcentage_bons_pronos = round(100 * nb_bons_pronos / total_pronos, 1) if total_pronos > 0 else 0
        pourcentage_bons_scores = round(100 * nb_bons_scores / total_pronos, 1) if total_pronos > 0 else 0

        bonus_133 = (df_joueur_participant["multiplicateur"] == 1.33).sum() if "multiplicateur" in df_joueur_participant else 0
        bonus_166 = (df_joueur_participant["multiplicateur"] == 1.66).sum() if "multiplicateur" in df_joueur_participant else 0
        bonus_200 = (df_joueur_participant["multiplicateur"] == 2).sum() if "multiplicateur" in df_joueur_participant else 0

        # --- Journées gagnées ---
        df_points_journee = df.groupby(["journee_match","participant_nom"])["points"].sum().unstack(fill_value=0)
        journees_gagnees = (df_points_journee.idxmax(axis=1) == participant_sel).sum()

        # --- Sélection des bons pronostics ---
        df_bons = df_joueur[df_joueur["bon_prono"]].copy()
        # --- Appliquer la fonction ---
        df_bons["cote_correcte"] = df_bons.apply(Fonctions.cote_prono_correct, axis=1)
        # --- Moyenne des cotes exactes des pronos gagnés ---
        cote_moyenne = df_bons["cote_correcte"].mean()

        df_joueur["roi_match"] = df_joueur.apply(Fonctions.gain_match, axis=1)
        roi_total = df_joueur["roi_match"].sum()
        
        # --- Affichage final ---
        st.markdown(f"###### Statistiques globales de la saison")
        # --- Ligne 1 : Performances générales ---
        kpi_cols = st.columns([1, 1, 1, 1, 1, 1])

        with kpi_cols[0]: Fonctions.kpi_card("🎯 Total bons pronos", f"{nb_bons_pronos}/{total_pronos}", f"{pourcentage_bons_pronos}%", color="#f59e0b", width="100%", height="100px") 
        with kpi_cols[1]: Fonctions.kpi_card("🎯 Total bons scores", f"{nb_bons_scores}/{total_pronos}", f"{pourcentage_bons_scores}%", color="#ef4444", width="100%", height="100px")
        with kpi_cols[2]: Fonctions.kpi_card("🏅 Journées gagnées", int(journees_gagnees), color="#3b82f6", width="100%", height="100px")  
        with kpi_cols[3]: Fonctions.kpi_card("Meilleur score / journée", round(meilleur_score_journee, 2), color="#22c55e", width="100%", height="100px")  
        with kpi_cols[4]: Fonctions.kpi_card("Moyenne points / match", round(moyenne_points, 2), color="#22c55e", width="100%", height="100px")  
        with kpi_cols[5]: Fonctions.kpi_card("💥 Max points sur un match", round(max_points_match, 2), color="#22c55e", width="100%", height="100px")  

        st.text("")
        
        # --- Ligne 2 : Bonus et scores spécifiques ---
        kpi_cols2 = st.columns([1, 1, 1, 1, 1])

        with kpi_cols2[0]: Fonctions.kpi_card("⭐ Bonus x1.33", int(bonus_133), color="#9333ea", width="100%", height="80px")  
        with kpi_cols2[1]: Fonctions.kpi_card("🔥 Bonus x1.66", int(bonus_166), color="#9333ea", width="100%", height="80px")  
        with kpi_cols2[2]: Fonctions.kpi_card("💎 Bonus x2", int(bonus_200), color="#9333ea", width="100%", height="80px")  
        with kpi_cols2[3]: Fonctions.kpi_card("📈 Cote moyenne bons pronos", round(cote_moyenne, 2), color="#12eccf", width="100%", height="80px")  
        with kpi_cols2[4]: Fonctions.kpi_card("💰 ROI théorique", round(roi_total, 2), color="#12eccf", width="100%", height="80px")  

        st.markdown("")
                
        # --- Préparer les données ---
        df["journee_match"] = df["journee_match"].astype(int)  # Conversion en entier
        df_progress = df.groupby(["participant_nom", "journee_match"]).apply(Fonctions.calcul_points_journee).reset_index()

        df_joueur = df_progress[df_progress["participant_nom"] == participant_sel].copy()

        # Trier les journées de façon ascendante
        df_joueur = df_joueur.sort_values("journee_match").reset_index(drop=True)

        # Points cumulés
        df_joueur["points_cumulés"] = df_joueur["points"].cumsum()

        # --- Création de la figure ---
        fig = go.Figure()

        # Ligne points cumulés (axe Y gauche)
        fig.add_trace(go.Scatter(
            x=df_joueur["journee_match"],
            y=df_joueur["points_cumulés"],
            mode="lines+markers",
            name="Points cumulés",
            line=dict(color="limegreen", width=2),
            marker=dict(size=8),
            hovertemplate=(
                "Journée : %{x}<br>"
                "Points cumulés : %{y:.2f}<br>"
                "Points journée : %{customdata[0]:.2f}<br>"
                "Bons pronos : %{customdata[1]}<br>"
                "Multiplicateur : %{customdata[2]}<extra></extra>"
            ),
            customdata=df_joueur[["points", "bons_pronos", "multiplicateur"]].values
        ))

        # Barres points par journée (axe Y droit)
        fig.add_trace(go.Bar(
            x=df_joueur["journee_match"],
            y=df_joueur["points"],
            name="Points par journée",
            marker_color="skyblue",
            opacity=0.6,
            yaxis="y2",
            hovertemplate=(
                "Journée : %{x}<br>"
                "Points journée : %{y:.2f}<br>"
                "Bons pronos : %{customdata[0]}<br>"
                "Multiplicateur : %{customdata[1]}<extra></extra>"
            ),
            customdata=df_joueur[["bons_pronos", "multiplicateur"]].values
        ))

        # --- Layout avec deux axes Y ---
        fig.update_layout(
            title=f"Évolution des points - {participant_sel}",
            xaxis_title="Journée",
            yaxis=dict(
                title=dict(text="Points cumulés", font=dict(color="limegreen")),
                tickfont=dict(color="limegreen")
            ),
            yaxis2=dict(
                title=dict(text="Points par journée", font=dict(color="skyblue")),
                tickfont=dict(color="skyblue"),
                overlaying="y",
                side="right"
            ),
            legend=dict(x=0.01, y=0.99),
            template="plotly_white",
            margin=dict(l=50, r=50, t=50, b=50),
            hovermode="x unified"
        )

        col_evolution, col_top_flop = st.columns(2)
            # --- Affichage dans Streamlit ---
        with col_evolution:
            st.plotly_chart(fig, use_container_width=True)

        with col_top_flop:
            # --- Top 5 des meilleures journées du joueur ---
            st.markdown("")
            st.markdown("###### 🏅 Top 5 des meilleures journées")

            # On récupère les scores du joueur par journée
            df_joueur_journees = (df_progress_all[df_progress_all["participant_nom"] == participant_sel].sort_values(by="points", ascending=False).head(5))

            if df_joueur_journees.empty:
                st.info("Aucune journée jouée pour ce participant.")
            else:
                df_joueur_journees_display = df_joueur_journees[["journee_match", "points", "bons_pronos", "multiplicateur"]]
                df_joueur_journees_display.rename(columns={
                    "journee_match": "Journée",
                    "points": "Points",
                    "bons_pronos": "Bons pronostics",
                    "multiplicateur": "Multiplicateur"
                }, inplace=True)

                # Formatage visuel
                df_joueur_journees_display["Points"] = df_joueur_journees_display["Points"].round(2)
                df_joueur_journees_display["Multiplicateur"] = df_joueur_journees_display["Multiplicateur"].round(2)

                st.dataframe(df_joueur_journees_display, hide_index=True, use_container_width=False)
                    
            # --- Top 5 des pires journées du joueur ---
            st.markdown("###### 💀 Top 5 des pires journées")

            # On récupère les scores du joueur par journée
            df_joueur_pires = (
                df_progress_all[df_progress_all["participant_nom"] == participant_sel]
                .sort_values(by="points", ascending=True)
                .head(5)
            )

            if df_joueur_pires.empty:
                st.info("Aucune journée jouée pour ce participant.")
            else:
                df_joueur_pires_display = df_joueur_pires[
                    ["journee_match", "points", "bons_pronos", "multiplicateur"]
                ].copy()

                df_joueur_pires_display.rename(columns={
                    "journee_match": "Journée",
                    "points": "Points",
                    "bons_pronos": "Bons pronostics",
                    "multiplicateur": "Multiplicateur"
                }, inplace=True)

                # Formatage visuel
                df_joueur_pires_display["Points"] = (df_joueur_pires_display["Points"].round(2))
                df_joueur_pires_display["Multiplicateur"] = (df_joueur_pires_display["Multiplicateur"].round(2))

                st.dataframe(df_joueur_pires_display, hide_index=True, use_container_width=False)    
                
        # --- 📈 Évolution du classement du joueur par journée ---
        # On recalcule les classements par journée
        classements_journees = (df_progress_all.groupby(["journee_match", "participant_nom"], as_index=False)["points"].sum())

        # Pour chaque journée, on classe les participants
        classements_journees["Rang"] = classements_journees.groupby("journee_match")["points"] \
                .rank(method="min", ascending=False).astype(int)

        # Récupération du classement du joueur sélectionné
        joueur_evolution = classements_journees[classements_journees["participant_nom"] == participant_sel].copy()

        # Récupération du leader de chaque journée pour comparaison
        leaders = classements_journees.loc[classements_journees.groupby("journee_match")["points"].idxmax(), ["journee_match", "participant_nom", "points"]].rename(columns={"participant_nom": "leader", "points": "points_leader"})

        joueur_evolution = joueur_evolution.merge(leaders, on="journee_match", how="left")

        # Calcul des écarts de points
        joueur_evolution["écart_avec_leader"] = joueur_evolution["points_leader"] - joueur_evolution["points"]

        # Formatage visuel
        joueur_evolution = joueur_evolution.sort_values("journee_match")
        joueur_evolution_display = joueur_evolution[["journee_match", "points", "Rang", "écart_avec_leader", "leader"]]
        joueur_evolution_display.rename(columns={
                "journee_match": "Journée",
                "points": "Points",
                "Rang": "Classement",
                "écart_avec_leader": "Écart avec Leader",
                "leader": "Leader"
        }, inplace=True)

        joueur_evolution_display["Écart avec Leader"] = joueur_evolution_display["Écart avec Leader"].round(2)
        joueur_evolution_display["Points"] = joueur_evolution_display["Points"].round(2)

        # Transposition du tableau
        joueur_evolution_transpose = joueur_evolution[["journee_match", "points", "Rang", "écart_avec_leader", "leader"]].copy()
        joueur_evolution_transpose.set_index("journee_match", inplace=True)
        joueur_evolution_transpose = joueur_evolution_transpose.T
        joueur_evolution_transpose.index = ["Points", "Classement", "Écart avec Leader", "Leader"]

        # Formater Points et Écart avec Leader avec 2 décimales (conversion en float d'abord)
        joueur_evolution_transpose.loc["Points"] = joueur_evolution_transpose.loc["Points"].apply(lambda x: f"{x:.2f}")
        joueur_evolution_transpose.loc["Écart avec Leader"] = joueur_evolution_transpose.loc["Écart avec Leader"].apply(lambda x: f"{x:.2f}")
                    
        # Journées où au moins un participant a des points > 0
        journees_jouees = df_progress_all.groupby("journee_match")["points"].sum()
        journees_jouees = journees_jouees[journees_jouees > 0].index.tolist()

        # Filtrage des données
        classements_cumul = df_progress_all[df_progress_all["journee_match"].isin(journees_jouees)].copy()

        # Calcul cumulatif des points par participant
        classements_cumul = (classements_cumul.groupby(["journee_match", "participant_nom"], as_index=False)["points"].sum().sort_values(["participant_nom", "journee_match"])
        )
        classements_cumul["points_cumulés"] = classements_cumul.groupby("participant_nom")["points"].cumsum()

        # Classement général cumulatif par journée
        classements_cumul["Rang"] = classements_cumul.groupby("journee_match")["points_cumulés"] \
            .rank(method="min", ascending=False).astype(int)

        # Palette de couleurs
        colors = px.colors.qualitative.Set2

        # Figure
        fig = go.Figure()

        for i, (nom, data_part) in enumerate(classements_cumul.groupby("participant_nom")):
            is_selected = nom == participant_sel
            fig.add_trace(
                go.Scatter(
                    x=data_part["journee_match"],
                    y=data_part["Rang"],
                    mode="lines+markers",
                    name=nom,
                    line=dict(
                        color=colors[i % len(colors)],
                        width=4 if is_selected else 1.5
                    ),
                    marker=dict(size=6 if is_selected else 4),
                    opacity=1.0 if is_selected else 0.3,
                    hovertemplate="Journée %{x}<br>%{fullData.name}: %{y}ᵉ<extra></extra>"
                )
            )

        # Layout
        fig.update_layout(
            xaxis=dict(title="Journée", tickfont=dict(size=10)),
            yaxis=dict(title="Classement général", autorange="reversed", tickfont=dict(size=10)),
            template="plotly_white",
            height=500,
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            title=f"📊 Évolution du classement général - {participant_sel}"
        )

        st.plotly_chart(fig, use_container_width=True)
            
        st.markdown("---")

        # --- Points par journée et participant ---
        df_points_journee = (df.groupby(["journee_match", "participant_nom"])["points"].sum().reset_index())

        # --- Gagnant de chaque journée ---
        gagnants_journee = (df_points_journee.sort_values(["journee_match", "points"], ascending=[True, False]).groupby("journee_match").first().reset_index())

        # --- Nombre de journées gagnées par participant ---
        classement_journees_gagnees = (gagnants_journee.groupby("participant_nom").size().reset_index(name="Journees gagnées").sort_values("Journees gagnées", ascending=False).reset_index(drop=True))
        classement_journees_gagnees = classement_journees_gagnees.rename(columns={"participant_nom": "Participant"})
        classement_journees_gagnees["Rang"] = classement_journees_gagnees.index + 1
        
        # --- Détection des scores exacts ---
        df["bon_score"] = ((df["prono_dom"] == df["match_dom"]) & (df["prono_ext"] == df["match_ext"]))

        # --- Nombre total de bons scores par participant ---
        classement_bons_scores = (df[df["bon_score"]].groupby("participant_nom").size().reset_index(name="Bons scores").sort_values("Bons scores", ascending=False).reset_index(drop=True))
        classement_bons_scores = classement_bons_scores.rename(columns={"participant_nom": "Participant"})
        classement_bons_scores["Rang"] = classement_bons_scores.index + 1

        classements_cols = st.columns([1, 1])
        with classements_cols[0] :
            st.markdown("#### 🏅 Classement – Journées gagnées")
            st.dataframe(classement_journees_gagnees[["Rang", "Participant", "Journees gagnées"]], hide_index=True, use_container_width=True)
        with classements_cols[1] :
            st.markdown("#### 🎯 Classement – Bons scores (score exact)")
            st.dataframe(classement_bons_scores[["Rang", "Participant", "Bons scores"]], hide_index=True, use_container_width=True)

    # ---------------------- ONGLET 2 : Insertion Pronos ----------------------
    with tabs_insertion:
        # Assurer les bons types
        df_matchs["saison"] = df_matchs["saison"].astype(str)
        df_matchs["journee"] = df_matchs["journee"].astype(int)
        df_matchs["competition"] = df_matchs["competition"].astype(str)

        # Sélection Saison / Compétition / Journée
        col_select_saison, col_select_championnat, col_select_journee, col_4 = st.columns(4)
        with col_select_saison:
            saisons = sorted(df_matchs["saison"].unique(), reverse=True)
            saison_sel = st.selectbox("Saison :", saisons)

        with col_select_championnat:
            competitions = sorted(df_matchs[df_matchs["saison"] == saison_sel]["competition"].unique())
            competition_sel = st.selectbox("Compétition :", competitions)

        with col_select_journee:
            # Filtrer les journées pour la saison et la compétition sélectionnées
            df_journees = df_matchs[
                (df_matchs["saison"] == saison_sel) &
                (df_matchs["competition"] == competition_sel)
            ].copy()

            # Nettoyage
            df_journees = df_journees.dropna(subset=["journee"])
            df_journees["journee"] = pd.to_numeric(df_journees["journee"], errors="coerce")
            df_journees["date"] = pd.to_datetime(df_journees["date"], errors="coerce")

            # Déterminer la dernière journée complète
            df_journees["match_joue"] = df_journees["score_domicile"].notna() & df_journees["score_exterieur"].notna()
            df_statut = df_journees.groupby("journee")["match_joue"].all().reset_index(name="complete")
            journees_jouees = df_statut[df_statut["complete"]]["journee"].tolist()
            derniere_journee = max(journees_jouees) if journees_jouees else df_journees["journee"].min()

            # Déterminer la prochaine journée à jouer
            prochaine_journee = derniere_journee + 1

            # Sélecteur Streamlit directement sur la prochaine journée
            journees_dispo = sorted(df_journees["journee"].dropna().unique())
            default_index = journees_dispo.index(prochaine_journee) if prochaine_journee in journees_dispo else 0
            journee_sel = st.selectbox("Journée :", journees_dispo, index=default_index)
            
        col_select_pseudo, col_2, col_3, col_4 = st.columns(4)
        with col_select_pseudo:
            st.markdown("### Sélection du participant")

            # --- Source 1 : pseudos déjà présents dans les pronostics ---
            df_repartition = tables["repartition_saison_participant"]

            pseudos_dispo = sorted(
                df_repartition[
                    (df_repartition["saison"] == saison_sel) &
                    (df_repartition["competition"] == competition_sel)
                ]["pseudo"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )
            
            if not pseudos_dispo:
                st.warning(
                    f"Aucun participant enregistré pour {competition_sel} - {saison_sel}"
                )
                st.stop()

            # --- Option d'ajout manuel ---
            option_ajout = "➕ Ajouter un nouveau pseudo"

            if len(pseudos_dispo) == 0:
                st.warning(
                    "Aucun pseudo existant pour cette saison/compétition."
                )
                nom_participant = st.text_input("Nom / Pseudo")
            else:
                choix_pseudo = st.selectbox(
                    "🚀 Pseudo :",
                    [option_ajout] + pseudos_dispo
                )

                # Si l'utilisateur veut créer un nouveau pseudo
                if choix_pseudo == option_ajout:
                    nom_participant = st.text_input(
                        "Nouveau pseudo :"
                    )
                else:
                    nom_participant = choix_pseudo
                    
        # Filtrer les matchs
        matchs = df_matchs[
            (df_matchs["saison"] == saison_sel) &
            (df_matchs["competition"] == competition_sel) &
            (df_matchs["journee"] == journee_sel)
        ].sort_values(["equipe_domicile_nom", "equipe_exterieure_nom"])

        if matchs.empty:
            st.warning("⚠️ Aucun match trouvé pour cette sélection.")
        else:
            st.markdown("### 📋 Saisir vos pronostics")

            # Récupérer les pronostics existants pour le participant
            pseudo = nom_participant  # pseudo sélectionné ou saisi
            df_existing = tables["all_pronostics"]
            df_existing = df_existing[
                (df_existing["saison"] == saison_sel) &
                (df_existing["competition_nom"] == competition_sel) &
                (df_existing["participant_nom"] == pseudo)
            ][["match_id", "score_domicile", "score_exterieur"]]

            # Préparer le DataFrame pour l'édition
            df_table = matchs[["match_id", "equipe_domicile_nom", "equipe_exterieure_nom"]].copy()

            # Ajouter les colonnes de scores, pré-remplis si existants
            df_table = df_table.merge(df_existing, on="match_id", how="left")
            df_table["score_domicile"] = df_table["score_domicile"].fillna(0).astype(int)
            df_table["score_exterieur"] = df_table["score_exterieur"].fillna(0).astype(int)

            # Renommer et réorganiser les colonnes
            df_table = df_table.rename(columns={
                "equipe_domicile_nom": "Équipe domicile",
                "equipe_exterieure_nom": "Équipe extérieure",
                "score_domicile": "Score domicile",
                "score_exterieur": "Score extérieur"
            })[
                ["match_id", "Équipe domicile", "Score domicile", "Score extérieur", "Équipe extérieure"]
            ]
            
            df_table = df_table.sort_values("match_id").reset_index(drop=True)

            col_pronos, col_boutons = st.columns([1.1,1])
            with col_pronos:
                # --- Tableau éditable ---
                df_edit = st.data_editor(
                    df_table,
                    num_rows="fixed",
                    use_container_width=False,
                    column_config={
                        "match_id": st.column_config.NumberColumn(disabled=True),
                        "Équipe domicile": st.column_config.TextColumn(disabled=True),
                        "Équipe extérieure": st.column_config.TextColumn(disabled=True),
                        "Score domicile": st.column_config.NumberColumn(disabled=False),
                        "Score extérieur": st.column_config.NumberColumn(disabled=False),
                    }
                )

                # --- Extraction des pronostics après édition ---
                pronostics = []
                for _, row in df_edit.iterrows():
                    pronostics.append((
                        row["match_id"],
                        # ids récupérés depuis df_matchs
                        matchs.loc[matchs["match_id"]==row["match_id"], "equipe_domicile_id"].values[0],
                        row["Équipe domicile"],
                        int(row["Score domicile"]),
                        matchs.loc[matchs["match_id"]==row["match_id"], "equipe_exterieure_id"].values[0],
                        row["Équipe extérieure"],
                        int(row["Score extérieur"])
                    ))
        
            with col_boutons:
                # Formulaire participant
                sa_info = st.secrets["google_service_account"]
                if st.button("Soumettre mes pronostics"):
                    if not nom_participant :
                        st.warning("Merci de renseigner votre nom")
                    else:
                        # Connexion Google Sheets
                        scope = [
                            "https://www.googleapis.com/auth/spreadsheets",  
                            "https://www.googleapis.com/auth/drive"
                        ]
                        creds = Credentials.from_service_account_info(sa_info, scopes=scope)
                        client = gspread.authorize(creds)
                        sheet = client.open("Pronos Expert").sheet1

                        # Ajouter chaque pronostic
                        for match in pronostics:
                            sheet.append_row([
                                str(nom_participant),
                                str(saison_sel),
                                str(competition_sel),
                                int(journee_sel),
                                int(match[0]),  # match_id
                                int(match[1]),  # équipe domicile id
                                str(match[2]),  # équipe domicile nom
                                int(match[3]),  # score domicile
                                int(match[4]),  # équipe extérieure id
                                str(match[5]),  # équipe extérieure nom
                                int(match[6]),  # score extérieure
                                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ])

                        st.success(f"✅ Vos pronostics pour la Journée {journee_sel} ont été enregistrés !")

                # Télécharger les matchs 
                df_export = pd.DataFrame(pronostics, columns=[
                    "Match ID", "Equipe Domicile ID", "Equipe Domicile", "Score Domicile",
                    "Equipe Extérieure ID", "Equipe Extérieure", "Score Extérieur"
                ])
                
                # Réorganiser les colonnes selon l'ordre souhaité
                df_export = df_export[[
                    "Equipe Domicile", "Score Domicile",
                    "Score Extérieur", "Equipe Extérieure"
                ]]

                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_export.to_excel(writer, sheet_name="Pronostics", index=False, startrow=2)
                    workbook  = writer.book
                    worksheet = writer.sheets["Pronostics"]

                    # === Styles ===
                    title_format = workbook.add_format({
                        "bold": True, "font_size": 16, "align": "center", "valign": "vcenter",
                        "bg_color": "#004c91", "font_color": "white"
                    })
                    header_format = workbook.add_format({
                        "bold": True, "bg_color": "#4f81bd", "font_color": "white", "border": 1,
                        "align": "center", "valign": "vcenter"
                    })
                    cell_center = workbook.add_format({"align": "center", "valign": "vcenter", "border": 1})
                    cell_left   = workbook.add_format({"align": "left",   "valign": "vcenter", "border": 1})
                    cell_right  = workbook.add_format({"align": "right",  "valign": "vcenter", "border": 1})
                    cell_center_alt = workbook.add_format({"align": "center", "valign": "vcenter", "border": 1, "bg_color": "#e6f0fa"})
                    cell_left_alt   = workbook.add_format({"align": "left",   "valign": "vcenter", "border": 1, "bg_color": "#e6f0fa"})
                    cell_right_alt  = workbook.add_format({"align": "right",  "valign": "vcenter", "border": 1, "bg_color": "#e6f0fa"})

                    # === Titre fusionné sur toutes les colonnes ===
                    worksheet.merge_range(0, 0, 0, len(df_export.columns)-1, 
                                        f"{competition_sel} - Saison {saison_sel} - Journée {journee_sel}", 
                                        title_format)

                    # === En-têtes ===
                    for col_num, col_name in enumerate(df_export.columns):
                        worksheet.write(2, col_num, col_name, header_format)

                    # === Largeur automatique des colonnes ===
                    for i, col in enumerate(df_export.columns):
                        max_len = max(df_export[col].astype(str).map(len).max(), len(col)) + 2
                        worksheet.set_column(i, i, max_len)

                    # === Contours et zébrage pour les données ===
                        for row_num in range(len(df_export)):
                            alt = (row_num % 2 == 1)
                            for col_num, col_name in enumerate(df_export.columns):
                                value = df_export.iloc[row_num, col_num]
                                if col_num == 0:
                                    fmt = cell_left_alt if alt else cell_left
                                elif col_num in [1,2]:  # scores ou valeurs centrales
                                    fmt = cell_center_alt if alt else cell_center
                                else:
                                    fmt = cell_right_alt if alt else cell_right
                                worksheet.write(row_num + 3, col_num, value, fmt)

                st.download_button(
                    label="📥 Télécharger mes pronostics en Excel",
                    data=output.getvalue(),
                    file_name=f"{competition_sel}_J{journee_sel}_{saison_sel}_pronostics.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
    # ---------------------- ONGLET 3 : Export Excel ----------------------
    with tabs_excel:
        # --- 1️⃣ Sélection Saison / Compétition / Journée ---
        col_select_saison, col_select_championnat, col_select_journee = st.columns(3)

        # Assurer que les colonnes sont bien au bon type
        df_matchs["saison"] = df_matchs["saison"].astype(str)
        df_matchs["journee"] = df_matchs["journee"].astype(int)
        df_matchs["competition"] = df_matchs["competition"].astype(str)

        # Saison
        with col_select_saison:
            saisons = sorted(df_matchs["saison"].unique(), reverse=True)  # tri descendant
            saison_sel = st.selectbox("Saison :", saisons, key="export_saison")

        # Compétition
        with col_select_championnat:
            competitions = sorted(df_matchs[df_matchs["saison"] == saison_sel]["competition"].unique())
            competition_sel = st.selectbox("Compétition :", competitions, key=f"export_comp_{saison_sel}")

        # Journée
        with col_select_journee:
            journees = sorted(
                df_matchs[
                    (df_matchs["saison"] == saison_sel) & 
                    (df_matchs["competition"] == competition_sel)
                ]["journee"].unique()
            )
            journee_sel = st.selectbox("Journée :", journees, key=f"export_journee_{saison_sel}_{competition_sel}")

        # --- 2️⃣ Récupérer les matchs ---
        matchs = df_matchs[
            (df_matchs["saison"] == saison_sel) &
            (df_matchs["competition"] == competition_sel) &
            (df_matchs["journee"] == journee_sel)
        ].sort_values(["equipe_domicile_nom", "equipe_exterieure_nom"])

        if matchs.empty:
            st.warning("⚠️ Aucun match trouvé pour cette sélection.")
        else:
            # Préparer le DataFrame pour export
            df_export = matchs[[
                "equipe_domicile_nom",
                "score_domicile",
                "score_exterieur",
                "equipe_exterieure_nom"
            ]].copy()

            df_export.columns = ["Equipe domicile", "Score domicile", "Score extérieur", "Equipe extérieure"]

            # Remplacer les NaN par des chaînes vides pour éviter les erreurs Excel
            df_export = df_export.fillna("").astype(str)

            # --- Prévisualisation ---
            st.markdown("### Prévisualisation des matchs")
            st.dataframe(df_export, hide_index=True)

            # --- Générer le fichier Excel en mémoire ---
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_export.to_excel(writer, sheet_name="Pronostics", index=False, startrow=2)
                workbook  = writer.book
                worksheet = writer.sheets["Pronostics"]

                # === Styles ===
                title_format = workbook.add_format({
                    "bold": True, "font_size": 14, "align": "center", "valign": "vcenter",
                    "bg_color": "#004c91", "font_color": "white"
                })
                header_format = workbook.add_format({
                    "bold": True, "bg_color": "#6fa8dc", "border": 1,
                    "align": "center", "valign": "vcenter"
                })
                cell_center = workbook.add_format({"align": "center", "valign": "vcenter", "border": 1})
                cell_left   = workbook.add_format({"align": "left",   "valign": "vcenter", "border": 1})
                cell_right  = workbook.add_format({"align": "right",  "valign": "vcenter", "border": 1})
                cell_center_alt = workbook.add_format({"align": "center", "valign": "vcenter", "border": 1, "bg_color": "#dce6f1"})
                cell_left_alt   = workbook.add_format({"align": "left",   "valign": "vcenter", "border": 1, "bg_color": "#dce6f1"})
                cell_right_alt  = workbook.add_format({"align": "right",  "valign": "vcenter", "border": 1, "bg_color": "#dce6f1"})

                # === Titre fusionné ===
                titre = f"{competition_sel} - Saison {saison_sel} - Journée {journee_sel}"
                worksheet.merge_range("A1:D1", titre, title_format)

                # === En-têtes ===
                for col_num, col_name in enumerate(df_export.columns):
                    worksheet.write(2, col_num, col_name, header_format)

                # === Largeur automatique ===
                for i, col in enumerate(df_export.columns):
                    max_len = max(df_export[col].map(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, max_len)

                # === Alignement + zébrage ===
                for row_num in range(len(df_export)):
                    alt = (row_num % 2 == 1)
                    fmt_right  = cell_right_alt if alt else cell_right
                    fmt_center = cell_center_alt if alt else cell_center
                    fmt_left   = cell_left_alt if alt else cell_left

                    worksheet.write(row_num + 3, 0, df_export.iloc[row_num, 0], fmt_right)
                    worksheet.write(row_num + 3, 1, df_export.iloc[row_num, 1], fmt_center)
                    worksheet.write(row_num + 3, 2, df_export.iloc[row_num, 2], fmt_center)
                    worksheet.write(row_num + 3, 3, df_export.iloc[row_num, 3], fmt_left)

            # === Téléchargement ===
            st.download_button(
                label="📥 Télécharger le fichier Excel",
                data=output.getvalue(),
                file_name=f"{competition_sel}_J{journee_sel}_{saison_sel}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )