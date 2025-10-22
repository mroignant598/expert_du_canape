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


def afficher_classement_visuel(classement, saison_sel, championnat_sel=None):
    # Tri et rang
    classement = classement.sort_values(by="points", ascending=False).reset_index(drop=True)
    classement["Rang"] = classement.index + 1
    max_points = classement["points"].max()

    # === 🌈 CSS global podium + ranking homogène ===
    st.markdown("""
        <style>
        .ranking-card, .podium-card {
            background: linear-gradient(135deg, rgba(31,41,55,0.95), rgba(55,65,81,0.9));
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 14px;
            padding: 10px 16px;
            margin-bottom: 8px;
            transition: all 0.25s ease-in-out;
            width: 95%;
            max-width: 400px;
            text-align: left;
            display: flex;
            flex-direction: column;
            gap: 6px;
            color: white;
        }
        .ranking-card:hover, .podium-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 0 14px rgba(255,255,255,0.08);
        }

        .ranking-card h5 {
            margin: 0;
            font-size: 15px;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .progress-bar {
            height: 10px;
            border-radius: 8px;
            overflow: hidden;
            background-color: rgba(255,255,255,0.08);
            margin-top: 4px;
        }
        .progress-fill {
            height: 100%;
            border-radius: 8px;
            transition: width 0.8s ease;
        }

        .podium-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin: 20px 0 30px 0;
        }

        /* Couleurs des marches du podium */
        .podium-1 { background: linear-gradient(135deg, #facc15 20%, #92400e 120%); }
        .podium-2 { background: linear-gradient(135deg, #a1a1aa 20%, #52525b 120%); }
        .podium-3 { background: linear-gradient(135deg, #f97316 20%, #78350f 120%); }

        /* Tailles différentes selon le rang */
        .podium-1 h4 { font-size: 20px; font-weight: 700; }
        .podium-2 h4 { font-size: 18px; font-weight: 600; }
        .podium-3 h4 { font-size: 16px; font-weight: 600; }
        .podium-card div.emoji {
            margin-right: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

    # === 🥇 Podium vertical sobre + barre de progression ===
    top3 = classement.head(3)
    max_points = classement["points"].max() if not classement.empty else 1
    podium = {1:"🥇", 2:"🥈", 3:"🥉"}

    st.markdown('<div class="podium-container">', unsafe_allow_html=True)

    for i in [1,2,3]:
        if len(top3) >= i:
            row = top3.iloc[i-1]
            progress = row["points"] / max_points if max_points else 0
            st.markdown(f"""
                <div class="podium-card podium-{i}">
                    <div style="display:flex; align-items:center; justify-content:flex-start;">
                        <div class="emoji">{podium[i]}</div>
                        <h4>{row['participant_nom']} - {row['points']:.2f} pts</h4>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width:{progress*100:.1f}%;
                            background: linear-gradient(90deg, #3b82f6, rgba(255,255,255,0.3));">
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    others = classement.iloc[3:]
    for i, row in others.iterrows():
        rang = int(row["Rang"])
        nom = row["participant_nom"]
        pts = row["points"]
        progress = pts / max_points if max_points else 0
        color = "#3b82f6"

        st.markdown(f"""
            <div class="ranking-card">
                <h5>⚽ {rang}. {nom} - {pts:.2f} pts</h5>
                <div class="progress-bar">
                    <div class="progress-fill" style="width:{progress*100:.1f}% ;
                        background: linear-gradient(90deg, {color}, rgba(255,255,255,0.3));">
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
def kpi_card(title, value, delta=None, color="#2563eb", width="100%", height="120px"):
    st.markdown(f"""
    <div style="
        background: {color};
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        text-align: center;
        color: white;
        width: {width};
        height: {height};       /* Hauteur fixe */
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        transition: transform 0.2s;
    " onmouseover="this.style.transform='scale(1.05)';" 
        onmouseout="this.style.transform='scale(1)';">
        <div style="font-size: 16px; font-weight: 500; margin-bottom: 5px;">{title}</div>
        <div style="font-size: 28px; font-weight: bold;">{value}</div>
        {"<div style='font-size:14px; opacity:0.8; margin-top:2px;'>{}</div>".format(delta) if delta else ""}
    </div>
    """, unsafe_allow_html=True)

def normalize_text(s):
            if not s or pd.isna(s):
                return ""
            s = str(s).lower()
            s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
            return s.strip()
        
def calcul_points(r):
    if pd.isna(r.match_dom) or pd.isna(r.match_ext):
        return 0
        
    score_exact = (r.prono_dom == r.match_dom) and (r.prono_ext == r.match_ext)
    resultat_correct = (
        (r.prono_dom > r.prono_ext and r.match_dom > r.match_ext) or
        (r.prono_dom < r.prono_ext and r.match_dom < r.match_ext) or
        (r.prono_dom == r.prono_ext and r.match_dom == r.match_ext)
    )
    # -> On ignore l'ecart_correct si le match réel est un nul
    ecart_correct = False
    if r.match_dom != r.match_ext:
        ecart_correct = ((r.prono_dom - r.prono_ext) == (r.match_dom - r.match_ext)) and not score_exact

    cotes_absentes = pd.isna(r.cote_domicile) and pd.isna(r.cote_exterieur) and pd.isna(r.cote_nul)
    if cotes_absentes:
        points = 0
        if score_exact: points += 3
        if resultat_correct: points += 1
        if not resultat_correct: points -= 1
        return points

    buts_prono = r.prono_dom + r.prono_ext
    buts_reel = r.match_dom + r.match_ext
    prolifique_prono = buts_prono >= 4
    prolifique_reel = buts_reel >= 4

    if r.match_dom > r.match_ext:
        cote_match = r.cote_domicile
    elif r.match_dom < r.match_ext:
        cote_match = r.cote_exterieur
    else:
        cote_match = r.cote_nul

    cote_min = min(r.cote_domicile, r.cote_exterieur, r.cote_nul)
    cote_finale = cote_match if resultat_correct else cote_min

    multiplicateur = 0
    if resultat_correct: multiplicateur += 3
    if score_exact and resultat_correct: multiplicateur += 2
    if ecart_correct and resultat_correct: multiplicateur += 1.33
    if prolifique_prono and prolifique_reel: multiplicateur += 1.25
    if prolifique_prono and not prolifique_reel: multiplicateur -= 0.5

    return cote_finale * multiplicateur

def calcul_points_journee(df_journee):
    """Calcule le score total d'une journée avec bonus si les matchs ont des cotes."""
    n = len(df_journee)

    # Vérifie s’il y a au moins un match sans cote
    cotes_presentes = not (
        df_journee["cote_domicile"].isna().all() and
        df_journee["cote_exterieur"].isna().all() and
        df_journee["cote_nul"].isna().all()
    )

    # Nombre de bons pronostics
    bons_pronos = (
        ((df_journee["prono_dom"] > df_journee["prono_ext"]) & (df_journee["match_dom"] > df_journee["match_ext"])) |
        ((df_journee["prono_dom"] < df_journee["prono_ext"]) & (df_journee["match_dom"] < df_journee["match_ext"])) |
        ((df_journee["prono_dom"] == df_journee["prono_ext"]) & (df_journee["match_dom"] == df_journee["match_ext"]))
    ).sum()

    # Score total de la journée
    score_total = df_journee["points"].sum()

    # Bonus appliqué uniquement si les cotes sont présentes
    multiplicateur = 1
    if cotes_presentes:
        if bons_pronos == n - 2:
            multiplicateur = 1.33
        elif bons_pronos == n - 1:
            multiplicateur = 1.66
        elif bons_pronos == n:
            multiplicateur = 2

    score_final = score_total * multiplicateur

    return pd.Series({
        "points": score_final,
        "bons_pronos": bons_pronos,
        "multiplicateur": multiplicateur,
        "cotes_presentes": cotes_presentes
    })

def gain_match(r):
    """
    Calcul du ROI pour un match :
    - On mise 1€ sur le pronostic choisi
    - Si le pronostic est correct, le gain net = cote - 1
    - Si incorrect, perte = 1€
    """
    # Si le score réel n'est pas disponible
    if pd.isna(r.match_dom) or pd.isna(r.match_ext):
        return 0.0

    # Déterminer le résultat réel et le résultat pronostiqué
    resultat_reel = 'D' if r.match_dom > r.match_ext else ('E' if r.match_dom < r.match_ext else 'N')
    resultat_prono = 'D' if r.prono_dom > r.prono_ext else ('E' if r.prono_dom < r.prono_ext else 'N')

    # Déterminer la cote correspondante au pronostic
    if resultat_prono == 'D':
        cote = r.cote_domicile
    elif resultat_prono == 'E':
        cote = r.cote_exterieur
    else:
        cote = r.cote_nul

    # Si la cote est manquante, considérer une mise perdue
    if pd.isna(cote):
        return -1.0

    # Gain net : cote - 1 si gagné, sinon perte 1€
    if resultat_prono == resultat_reel:
        return cote - 1.0
    else:
        return -1.0

def gain_match_detail(r):
    """
    Retourne le détail du ROI pour chaque match :
    - résultat réel et pronostiqué
    - cote utilisée
    - gain ou perte net
    """
    if pd.isna(r.match_dom) or pd.isna(r.match_ext):
        return pd.Series({
            "résultat_prono": None,
            "résultat_reel": None,
            "cote_utilisée": None,
            "gain_perte": 0.0
        })

    # Déterminer le résultat réel et le résultat pronostiqué
    resultat_reel = 'D' if r.match_dom > r.match_ext else ('E' if r.match_dom < r.match_ext else 'N')
    resultat_prono = 'D' if r.prono_dom > r.prono_ext else ('E' if r.prono_dom < r.prono_ext else 'N')

    # Déterminer la cote correspondant au pronostic
    if resultat_prono == 'D':
        cote = r.cote_domicile
    elif resultat_prono == 'E':
        cote = r.cote_exterieur
    else:
        cote = r.cote_nul

    if pd.isna(cote):
        cote = 1.0  # mise par défaut si cote manquante

    # Calcul du gain net : seulement le bénéfice ou la perte
    if resultat_prono == resultat_reel:
        gain_net = cote - 1  # on retire l'euro misé
    else:
        gain_net = -1  # perte de 1€

    return pd.Series({
        "résultat_prono": resultat_prono,
        "résultat_reel": resultat_reel,
        "cote_utilisée": cote,
        "gain_perte": gain_net
    })

def cote_prono_correct(r):
    # Déterminer le résultat pronostiqué
    if r.prono_dom > r.prono_ext:
        return r.cote_domicile
    elif r.prono_dom < r.prono_ext:
        return r.cote_exterieur
    else:
        return r.cote_nul

def color_cells(val, row_name):
    if row_name == "Classement":
        # Vert si top 1, jaune si top 3, rouge sinon
        if val == 1:
            color = 'background-color: #b2f2bb'  # vert clair
        elif val <= 3:
            color = 'background-color: #fff3bf'  # jaune clair
        else:
            color = 'background-color: #ffa8a8'  # rouge clair
    elif row_name == "Écart avec Leader":
        # Dégradé vert-rouge selon l'écart
        if val <= 1:
            color = 'background-color: #b2f2bb'
        elif val <= 3:
            color = 'background-color: #fff3bf'
        else:
            color = 'background-color: #ffa8a8'
    else:
        color = ''
    return color
    
def show(tables):
    st.title("📊 Les Experts du Canapé")
    tabs_1, tabs_2 = st.tabs(["Classement/Visualisation", "Export Excel"])
    
    # ---------------------- ONGLET 1 : PAR COMPÉTITION ----------------------
    with tabs_1:
        
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


        # --- Nettoyage rapide --- #
        for col in ["saison", "competition", "journee"]:
            if col in df_matchs.columns:
                df_matchs[col] = df_matchs[col].astype(str)

        # --- ONGLET 1 --- #
        with tabs_1:

            # --- CSS (inchangé) --- #
            st.markdown("""<style> ... ton style CSS complet ici ... </style>""", unsafe_allow_html=True)

            # === 🎛️ Sélecteurs === #
            col1, col2, col3, col4 = st.columns(4)

            # --- Sélection de la saison --- #
            with col1:
                saisons = sorted(df_matchs["saison"].unique(), reverse=True)
                saison_sel = st.selectbox("Sélectionner une saison", saisons)

            # --- Sélection du championnat --- #
            with col2:
                championnats = df_matchs[df_matchs["saison"] == saison_sel]["competition"].dropna().unique().tolist()
                championnats = ["Toutes"] + sorted(championnats)
                default_champ = "Ligue 1" if "Ligue 1" in championnats else "Toutes"
                championnat_sel = st.selectbox("Sélectionner un championnat", championnats, index=championnats.index(default_champ))

            # --- Sélection de la journée --- #
            with col3:
                if championnat_sel == "Toutes":
                    journees = df_matchs[df_matchs["saison"] == saison_sel]["journee"].dropna().unique()
                else:
                    journees = df_matchs[
                        (df_matchs["saison"] == saison_sel) &
                        (df_matchs["competition"] == championnat_sel)
                    ]["journee"].dropna().unique()

                # Convertir en int et trier
                try:
                    journees = sorted(map(int, journees))
                except ValueError:
                    journees = sorted(journees)  # Si ce sont des strings
                journee_sel = st.selectbox("Sélectionner une journée", ["Toutes"] + [str(j) for j in journees])

            with col4:
                top_n = st.slider("Afficher les meilleurs participants", 1, 20, 10)

            st.markdown("---")

            # --- Filtrage des matchs ---
            df_filtre = df_matchs[df_matchs["saison"] == saison_sel].copy()

            if championnat_sel != "Toutes":
                df_filtre = df_filtre[df_filtre["competition"] == championnat_sel]

            # Vérifier que la colonne 'journee' existe
            if "journee" in df_filtre.columns and journee_sel != "Toutes":
                # Convertir en int si nécessaire
                df_filtre["journee"] = df_filtre["journee"].astype(int)
                df_filtre = df_filtre[df_filtre["journee"] == int(journee_sel)]
                

            # --- Jointure avec les pronostics ---
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

        # --- Préparer le DataFrame final ---
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

        # --- Calcul des points ---
        df["points"] = df.apply(calcul_points, axis=1)

        # --- Points cumulés par journée ---
        df_progress_all = df.groupby(["participant_nom", "journee_match"]).apply(calcul_points_journee).reset_index()
        df_progress_all["points_cumul"] = df_progress_all.groupby("participant_nom")["points"].cumsum()

        # --- Classement final sur la saison ---
        classement = df_progress_all.groupby("participant_nom", as_index=False)["points"].sum()
        classement = classement.sort_values(by="points", ascending=False).reset_index(drop=True)
        classement["Rang"] = classement.index + 1

        # --- KPI ---
        nb_matchs = df_filtre["match_id"].nunique()
        nb_pronos = len(df)
        nb_participants = df["participant_nom"].nunique()
        total_points = df_progress_all["points"].sum()
        moyenne_points_joueur = total_points / nb_participants if nb_participants else 0
        moyenne_points_joueur_journee = total_points / (nb_participants * nb_matchs) if nb_matchs and nb_participants else 0

        kpi_cols = st.columns([1.2, 1, 1, 1, 1])
        with kpi_cols[0]: kpi_card("🏟️ Matchs", nb_matchs, color="#3b82f6")
        with kpi_cols[1]: kpi_card("🧾 Pronostics", nb_pronos, color="#22c55e")
        with kpi_cols[2]: kpi_card("👥 Participants", nb_participants, color="#f59e0b")
        with kpi_cols[3]: kpi_card("🎯 Moy. pts/joueur", f"{moyenne_points_joueur:.2f}", color="#2563eb")
        with kpi_cols[4]: kpi_card("👤 Moy. pts/joueur/journée", f"{moyenne_points_joueur_journee:.2f}", color="#9333ea")

        st.markdown("---")

        # --- Affichage classement et progression ---
        st.subheader(
            f"{'Classement global par saison' if championnat_sel == 'Toutes' else f'Classement – {championnat_sel} – {saison_sel}'}"
        )

        col1, col2 = st.columns([1, 2])
        with col1:
            afficher_classement_visuel(classement, saison_sel, championnat_sel if championnat_sel != "Toutes" else None)

        with col2:
            st.markdown('')
            st.markdown('')
            df_cumul = classement[["participant_nom", "Rang", "points"]].merge(
                df_progress_all.groupby("participant_nom")["points_cumul"].apply(list).reset_index(),
                on="participant_nom"
            )
            
            # Conversion en int pour trier correctement
            df_progress_all["journee_match"] = df_progress_all["journee_match"].astype(int)

            # Tri par journée ascendant
            df_progress_all = df_progress_all.sort_values(["journee_match", "participant_nom"]).reset_index(drop=True)

            # Calcul de la moyenne cumulée
            df_moyenne = (
                df_progress_all.groupby("journee_match")["points"]
                .mean()
                .cumsum()
                .reset_index()
            )
            df_moyenne = df_moyenne.rename(columns={"points": "points_cumul_moyenne"})

            fig = go.Figure()
            colors = px.colors.qualitative.Safe

            for i, (_, row) in enumerate(df_cumul.head(top_n).iterrows()):
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(row["points_cumul"])+1)),
                    y=row["points_cumul"],
                    mode='lines+markers',
                    name=row["participant_nom"],
                    line=dict(color=colors[i % len(colors)], width=3),
                    marker=dict(size=8)
                ))
                
            x_moy = [0] + df_moyenne["journee_match"].tolist()
            y_moy = [0] + df_moyenne["points_cumul_moyenne"].tolist()
            max_journee = max(df_moyenne["journee_match"]) + 1

            fig.add_trace(go.Scatter(
                x=df_moyenne["journee_match"],
                y=df_moyenne["points_cumul_moyenne"],
                mode='lines+markers',
                name="Moyenne championnat",
                line=dict(color="dodgerblue", width=3, dash="dot"),
                marker=dict(size=7)
            ))

            fig.update_layout(
                xaxis=dict(title="Journée", tickmode="linear", range=[0, max_journee]),
                yaxis=dict(title="Points cumulés"),
                plot_bgcolor="black",
                hovermode="x unified",
                height=450,
                margin=dict(l=40, r=40, t=50, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        
        # === 📍 SECTION 2 ===        
        col1, col2 = st.columns([1,3])
        with col1:
            # --- Sélection du participant ---
            st.markdown("   ")
            st.markdown("   ")
            participants = classement["participant_nom"].tolist()
            participant_sel = st.selectbox("Sélectionner un participant :", participants)

            # --- Sélection de la journée via CSV / DataFrame ---
            if championnat_sel == "Toutes":
                journees = df_matchs[df_matchs["saison"] == saison_sel]["journee_match"].dropna().unique()
            else:
                journees = df_matchs[
                    (df_matchs["saison"] == saison_sel) &
                    (df_matchs["competition"] == championnat_sel)
                ]["journee"].dropna().unique()

            # Tri croissant
            journees = sorted([int(j) for j in journees])
            
            # Conversion en chaîne pour la selectbox
            journee_filtre = st.selectbox("Filtrer par journée :", [str(j) for j in journees])

            # --- Filtrer les données du joueur sélectionné ---
        df_participant = df[df["participant_nom"] == participant_sel].copy()

        if journee_filtre != "Toutes":
            df_participant = df_participant[df_participant["journee_match"].astype(str) == journee_filtre]

        if journee_sel != "Toutes":
            df_participant = df_participant[df_participant["journee_match"] == int(journee_sel)]

        if df_participant.empty:
            st.warning("Aucun pronostic trouvé pour ce joueur sur cette journée.")
        else:
            # --- Recalcul des points de chaque match ---
            df["points"] = df.apply(calcul_points, axis=1)

            journee_courante = df_participant["journee_match"].iloc[0]
            df_journee = df[df["journee_match"] == journee_courante].copy()

            # --- Points sans bonus (somme brute) ---
            points_sans_bonus = (df_journee.groupby("participant_nom")["points"].sum().reset_index().rename(columns={"points": "points_bruts"}))

            # --- Application du bonus avec calcul_points_journee ---
            df_journee_bonus = (df_journee.groupby("participant_nom").apply(calcul_points_journee).reset_index())
            df_journee_bonus = df_journee_bonus.rename(columns={"points": "points_bonus"})

            # --- Fusion des deux jeux de points ---
            classement_journee = pd.merge(points_sans_bonus, df_journee_bonus, on="participant_nom", how="left")

            # --- Tri et ajout du rang ---
            classement_journee = classement_journee.sort_values(by="points_bonus", ascending=False).reset_index(drop=True)
            classement_journee["Rang"] = classement_journee.index + 1

            # --- Calcul du ratio par rapport au meilleur joueur pour la barre de progression ---
            max_points = classement_journee["points_bonus"].max()
            classement_journee["Performance (%)"] = (classement_journee["points_bonus"] / max_points * 100).round(1)

            # --- Classement du joueur sélectionné ---
            joueur_stats = classement_journee[classement_journee["participant_nom"] == participant_sel]

            with col2:
                st.markdown(f"### 🏅 Classement - Journée {journee_courante}")
                st.dataframe(classement_journee[["Rang", "participant_nom", "points_bruts", "points_bonus", "bons_pronos", "multiplicateur", "Performance (%)"]], hide_index=True, use_container_width=True)

            # --- Résumé personnel ---
            if not joueur_stats.empty:
                points_bruts = joueur_stats["points_bruts"].values[0]
                points_bonus = joueur_stats["points_bonus"].values[0]
                bons_pronos = joueur_stats["bons_pronos"].values[0]
                multiplicateur = joueur_stats["multiplicateur"].values[0]
                rang = joueur_stats["Rang"].values[0]
                perf = joueur_stats["Performance (%)"].values[0]

                st.markdown(f"### 👤 Statistiques de {participant_sel} - Journée {journee_courante}")

                # Colonnes KPI améliorées
                kpi_cols = st.columns([1, 1, 1, 1, 1])

                with kpi_cols[0]: kpi_card("🏆 Rang", rang, color="#3b82f6")  # bleu pour le rang
                with kpi_cols[1]: kpi_card("💯 Points bruts", f"{points_bruts:.2f}", color="#22c55e")  # vert pour points
                with kpi_cols[2]: kpi_card("✨ Points avec bonus", f"{points_bonus:.2f}", color="#9333ea")  # violet pour bonus
                with kpi_cols[3]: kpi_card("🎯 Bons pronos", f"{bons_pronos} / {len(df_participant)}", color="#f59e0b")  # orange pour ratio
                with kpi_cols[4]: kpi_card("⚡ Multiplicateur", f"x{multiplicateur}", color="#2563eb")  # bleu foncé pour multiplicateur

                # Sécuriser la valeur de la barre de progression
                perf_safe = 0 if pd.isna(perf) else perf

                # --- Barre de performance visuelle ---
                st.progress(perf_safe / 100)
                st.caption(f"Performance de {perf_safe:.1f}% par rapport au meilleur score de la journée.")
        
        st.markdown("---")
        
        # --- 🔍 Statistiques complémentaires ---
        st.markdown("### 📊 Statistiques avancées")

        # Filtrer les matchs du joueur sélectionné
        df_joueur = df[df["participant_nom"] == participant_sel].copy()
        df_joueur_participant = df_progress_all[df_progress_all["participant_nom"] == participant_sel].copy()

        # --- Calculs de points par match avec bonus ---
        df_joueur["points"] = df_joueur.apply(calcul_points, axis=1)

        # --- Bons pronos ---
        df_joueur["bon_prono"] = (
            ((df_joueur["prono_dom"] > df_joueur["prono_ext"]) & (df_joueur["match_dom"] > df_joueur["match_ext"])) |
            ((df_joueur["prono_dom"] < df_joueur["prono_ext"]) & (df_joueur["match_dom"] < df_joueur["match_ext"])) |
            ((df_joueur["prono_dom"] == df_joueur["prono_ext"]) & (df_joueur["match_dom"] == df_joueur["match_ext"]))
        )

        # --- Bonus multiplicateurs par match ---
        df_joueur["bonus"] = df_joueur.apply(lambda r: float(calcul_points_journee(pd.DataFrame([r]))["multiplicateur"]), axis=1)

        # --- Stats globales ---
        total_points = df_joueur["points"].sum().round(2)
        moyenne_points = df_joueur["points"].mean().round(2)
        max_points_match = df_joueur["points"].max().round(2)
        min_points_match = df_joueur["points"].min().round(2)
        
        # Somme des points par journée
        points_par_journee = df_joueur_participant.groupby("journee_match")["points"].sum()

        # Meilleur score sur une journée
        meilleur_score_journee = points_par_journee.max().round(2)
        
        nb_bons_pronos = df_joueur["bon_prono"].sum()
        total_pronos = len(df_joueur)
        pourcentage_bons_pronos = round(100 * nb_bons_pronos / total_pronos, 1) if total_pronos > 0 else 0

        bonus_133 = (df_joueur_participant["multiplicateur"] == 1.33).sum() if "multiplicateur" in df_joueur_participant else 0
        bonus_166 = (df_joueur_participant["multiplicateur"] == 1.66).sum() if "multiplicateur" in df_joueur_participant else 0
        bonus_200 = (df_joueur_participant["multiplicateur"] == 2).sum() if "multiplicateur" in df_joueur_participant else 0

        # --- Journées gagnées ---
        df_points_journee = df.groupby(["journee_match","participant_nom"])["points"].sum().unstack(fill_value=0)
        journees_gagnees = (df_points_journee.idxmax(axis=1) == participant_sel).sum()

        # --- Sélection des bons pronostics ---
        df_bons = df_joueur[df_joueur["bon_prono"]].copy()
        # --- Appliquer la fonction ---
        df_bons["cote_correcte"] = df_bons.apply(cote_prono_correct, axis=1)
        # --- Moyenne des cotes exactes des pronos gagnés ---
        cote_moyenne = df_bons["cote_correcte"].mean()

        df_joueur["roi_match"] = df_joueur.apply(gain_match, axis=1)
        roi_total = df_joueur["roi_match"].sum()
        
        # --- Affichage final ---
        # --- Ligne 1 : Performances générales ---
        kpi_cols = st.columns([1, 1, 1, 1, 1])

        with kpi_cols[0]: kpi_card("🎯 Bons pronos", f"{nb_bons_pronos}/{total_pronos}", f"{pourcentage_bons_pronos}%", color="#3b82f6")  # orange
        with kpi_cols[1]: kpi_card("🏅 Journées gagnées", int(journees_gagnees), color="#12eccf")  # bleu
        with kpi_cols[2]: kpi_card("Meilleur score / journée", round(meilleur_score_journee, 2), color="#22c55e")  # vert
        with kpi_cols[3]: kpi_card("Moyenne points / match", round(moyenne_points, 2), color="#2563eb")  # bleu foncé
        with kpi_cols[4]: kpi_card("💥 Max points / match", round(max_points_match, 2), color="#9333ea")  # violet

        st.text("")
        
        # --- Ligne 2 : Bonus et scores spécifiques ---
        kpi_cols2 = st.columns([1, 1, 1, 1, 1])

        with kpi_cols2[0]: kpi_card("⭐ Bonus x1.33", int(bonus_133), color="#f59e0b")  # orange
        with kpi_cols2[1]: kpi_card("🔥 Bonus x1.66", int(bonus_166), color="#f97316")  # orange foncé
        with kpi_cols2[2]: kpi_card("💎 Bonus x2", int(bonus_200), color="#9333ea")  # violet
        with kpi_cols2[3]: kpi_card("📈 Cote moyenne bons pronos", round(cote_moyenne, 2), color="#22c55e")  # vert
        with kpi_cols2[4]: kpi_card("💰 ROI théorique", round(roi_total, 2), color="#3b82f6")  # bleu

        st.markdown("---")
            
        # === 📍 SECTION 3 ===       
        col1, col2 = st.columns([1.3, 2])
        with col1:
            st.markdown("### 📝 Pronostics du joueur")
            
            table_display = df_participant.copy()    
            # --- Créer colonne Match avec noms des équipes ---
            table_display["Match"] = table_display["equipe_domicile_nom"] + " - " + table_display["equipe_exterieure_nom"]

            # --- Conversion en int et création des colonnes simplifiées ---
            table_display["Prono"] = table_display["prono_dom"].fillna(0).astype(int).astype(str) + " - " + \
                                    table_display["prono_ext"].fillna(0).astype(int).astype(str)
            table_display["Score Réel"] = table_display["match_dom"].fillna(0).astype(int).astype(str) + " - " + \
                                        table_display["match_ext"].fillna(0).astype(int).astype(str)

            # --- Colonnes à afficher ---
            table_display = table_display[["journee_match", "Match", "Prono", "Score Réel", "points"]]
            table_display.columns = ["Journée_match", "Match", "Prono", "Score Réel", "Points"]

            # --- Affichage ---
            st.dataframe(table_display, hide_index=True, use_container_width=True)

        with col2:
            # --- Préparer les données ---
            df["journee_match"] = df["journee_match"].astype(int)  # Conversion en entier
            df_progress = df.groupby(["participant_nom", "journee_match"]).apply(calcul_points_journee).reset_index()

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

            # --- Affichage dans Streamlit ---
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
            
        # === 📍 SECTION 4 ===
        # --- Récupération de l'historique complet du joueur depuis les CSV ---
        data_historique = df_pronos[df_pronos["participant_nom"] == participant_sel].merge(
            df_matchs,
            on="match_id",
            suffixes=("_prono", "_match")
        )

        # --- Sélection des colonnes et renommage pour correspondre à l'ancien SQL ---
        data_historique = data_historique[[
            "participant_id",
            "participant_nom",
            "score_domicile_prono", 
            "score_exterieur_prono",
            "score_domicile_match", 
            "score_exterieur_match",
            "equipe_domicile_nom",
            "equipe_exterieure_nom",
            "cote_domicile",
            "cote_exterieur",
            "cote_nul",
            "journee_match",
            "saison_match",
            "competition"
        ]].rename(columns={
            "score_domicile_prono": "prono_dom",
            "score_exterieur_prono": "prono_ext",
            "score_domicile_match": "match_dom",
            "score_exterieur_match": "match_ext"
        })

        # --- Préparer le DataFrame historique ---
        df_historique = data_historique.copy()  # <-- créer df_historique
        df_historique["journee_match"] = df_historique["journee_match"].astype(int)  # Conversion en int
        df_historique = df_historique.sort_values(by=["saison_match", "journee_match"]).reset_index(drop=True)

        # Vérification des résultats
        if df_historique.empty:
            st.info(f"Aucun pronostic historique trouvé pour {participant_sel}.")
        else:
            # Calcul des points pour toutes les saisons
            df_historique["points"] = df_historique.apply(calcul_points, axis=1)
            df_historique = df_historique.sort_values(["saison_match", "journee_match"]).reset_index(drop=True)

        # --- Comparaison progression joueur par saison ---
        st.markdown("### 📊 Comparaison des saisons du joueur")

        saisons_disponibles = sorted(
            df_historique[df_historique["participant_nom"] == participant_sel]["saison_match"].unique(),
            reverse=True  # Tri descendant
        )

        default_saisons = [saison_sel] if saison_sel in saisons_disponibles else []

        saisons_sel = st.multiselect(
            "Sélectionnez les saisons à comparer",
            options=saisons_disponibles,
            default=default_saisons,
            key=f"saisons_compare_{participant_sel}"
        )

        if not saisons_sel:
            st.warning("Veuillez sélectionner au moins une saison pour l'affichage.")
        else:
            fig = go.Figure()
            couleurs_prev = px.colors.qualitative.Pastel
            idx_couleur = 0

            for saison in saisons_sel:
                df_saison = df_historique[
                    (df_historique["participant_nom"] == participant_sel) & 
                    (df_historique["saison_match"] == saison)
                ].copy()

                if df_saison.empty:
                    continue

                # Assurer que les journées sont triées et numériques
                df_saison["journee_match"] = df_saison["journee_match"].astype(int)
                df_saison = df_saison.sort_values("journee_match").reset_index(drop=True)

                # Calcul cumulatif
                df_saison = df_saison.groupby("journee_match")["points"].sum().reset_index()
                df_saison["points_cumul"] = df_saison["points"].cumsum()

                # Traces
                if saison == saison_sel:
                    fig.add_trace(go.Scatter(
                        x=df_saison["journee_match"],
                        y=df_saison["points_cumul"],
                        mode="lines+markers",
                        name=f"Saison {saison} (actuelle)",
                        line=dict(color="limegreen", width=4),
                        marker=dict(size=10, symbol="circle"),
                        hovertemplate="Journée: %{x}<br>Points cumulés: %{y:.2f}<br>Points journée: %{customdata[0]:.2f}<extra></extra>",
                        customdata=df_saison[["points"]].values
                    ))
                else:
                    couleur = couleurs_prev[idx_couleur % len(couleurs_prev)]
                    idx_couleur += 1
                    fig.add_trace(go.Scatter(
                        x=df_saison["journee_match"],
                        y=df_saison["points_cumul"],
                        mode="lines+markers",
                        name=f"Saison {saison} (précédente)",
                        line=dict(color=couleur, width=2, dash="dash"),
                        marker=dict(size=7, symbol="circle"),
                        opacity=0.6,
                        hovertemplate="Journée: %{x}<br>Points cumulés: %{y:.2f}<br>Points journée: %{customdata[0]:.2f}<extra></extra>",
                        customdata=df_saison[["points"]].values
                    ))

            fig.update_layout(
                title=f"Progression cumulée de {participant_sel} par saison",
                xaxis_title="Journée",
                yaxis_title="Points cumulés",
                xaxis=dict(range=[0, df_historique["journee_match"].max() + 1]),  # X commence à 0 et va jusqu'à max +1
                hovermode="x unified",
                template="plotly_white",
                height=450,
                legend=dict(title="Saisons", x=0.01, y=0.99),
                margin=dict(l=50, r=50, t=60, b=50)
            )

            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")          
        
        # === 📍 SECTION 5 ===
        # --- Comparaison progression joueur vs moyenne générale ---
        col1, col2 = st.columns([2.2, 1])
        with col1:
            st.markdown("### 📊 Comparaison avec la moyenne du championnat")

            # Points cumulés du joueur sélectionné
            df_joueur = df_progress_all[df_progress_all["participant_nom"] == participant_sel].copy()
            df_joueur["points_cumul_joueur"] = df_joueur["points"].cumsum()

            # Moyenne des points cumulés
            df_moyenne = df_progress_all.groupby("journee_match")["points"].mean().reset_index()
            df_moyenne["points_cumul_moyenne"] = df_moyenne["points"].cumsum()

            # Filtrer les journées où la moyenne a changé
            df_moyenne = df_moyenne[df_moyenne["points_cumul_moyenne"].diff().fillna(df_moyenne["points_cumul_moyenne"]) != 0]

            # Merge pour aligner les axes
            df_comparatif = pd.merge(df_joueur, df_moyenne, on="journee_match", how="inner")  # on utilise inner pour ne garder que les journées jouées

            # --- Graphique comparatif ---
            fig = go.Figure()

            # Courbe du joueur
            fig.add_trace(go.Scatter(
                x=df_comparatif["journee_match"],
                y=df_comparatif["points_cumul_joueur"],
                mode="lines+markers",
                name=participant_sel,
                line=dict(color="limegreen", width=3),
                marker=dict(size=8),
                hovertemplate="Journée : %{x}<br>Points cumulés : %{y:.2f}<extra></extra>"
            ))

            # Courbe de la moyenne
            fig.add_trace(go.Scatter(
                x=df_comparatif["journee_match"],
                y=df_comparatif["points_cumul_moyenne"],
                mode="lines+markers",
                name="Moyenne championnat",
                line=dict(color="dodgerblue", width=3, dash="dash"),
                marker=dict(symbol="square", size=7),
                hovertemplate="Journée: %{x}<br>Moyenne: %{y:.2f}<extra></extra>"
            ))

            # Mise en page esthétique avec légende en bas
            fig.update_layout(
                title=dict(
                    text=f"Comparaison des performances : {participant_sel} vs Moyenne ({championnat_sel})",
                    font=dict(size=18)
                ),
                xaxis=dict(
                    title=dict(text="Journée", font=dict(size=14)),
                    tickfont=dict(size=12),
                    showgrid=True,
                    gridcolor="lightgray"
                ),
                yaxis=dict(
                    title=dict(text="Points cumulés", font=dict(size=14)),
                    tickfont=dict(size=12),
                    showgrid=True,
                    gridcolor="lightgray"
                ),
                template="plotly_white",
                hovermode="x unified",
                legend=dict(
                    title="Légende",
                    orientation="h",   # horizontale
                    yanchor="bottom",
                    y=-0.25,           # sous le graphique
                    xanchor="left",
                    x=0,
                    font=dict(size=12)
                ),
                height=400,
                margin=dict(l=50, r=50, t=60, b=80)  # plus de marge en bas pour la légende
            )

            st.plotly_chart(fig, use_container_width=True)

            # --- Statistiques comparatives ---
            diff_points = df_comparatif["points_cumul_joueur"].iloc[-1] - df_comparatif["points_cumul_moyenne"].iloc[-1]
            tendance = "au-dessus" if diff_points > 0 else "en dessous"
            st.markdown(f"💡 **{participant_sel}** est actuellement **{abs(diff_points):.2f} points {tendance}** de la moyenne des participants.")

        with col2:
            # --- Top 5 des meilleures journées du joueur ---
            st.markdown("### 🏅 Top 5 des meilleures journées")

            # On récupère les scores du joueur par journée
            df_joueur_journees = (df_progress_all[df_progress_all["participant_nom"] == participant_sel].sort_values(by="points", ascending=False).head(5))

            if df_joueur_journees.empty:
                st.info("Aucune journée jouée pour ce participant.")
            else:
                df_joueur_journees_display = df_joueur_journees[["journee_match", "points", "bons_pronos", "multiplicateur"]]
                df_joueur_journees_display.rename(columns={
                    "journee": "Journée",
                    "points": "Points",
                    "bons_pronos": "Bons pronostics",
                    "multiplicateur": "Multiplicateur"
                }, inplace=True)

                # Formatage visuel
                df_joueur_journees_display["Points"] = df_joueur_journees_display["Points"].round(2)
                df_joueur_journees_display["Multiplicateur"] = df_joueur_journees_display["Multiplicateur"].round(2)

                st.dataframe(df_joueur_journees_display, hide_index=True, use_container_width=True)

            # --- Petit résumé dynamique ---
            moyenne_points = df_joueur_journees["points"].mean() if not df_joueur_journees.empty else 0
            max_points = df_joueur_journees["points"].max() if not df_joueur_journees.empty else 0
            journee_max = (df_joueur_journees.loc[df_joueur_journees["points"].idxmax(), "journee_match"]
                    if not df_joueur_journees.empty else None)

            st.markdown("### 📋 Résumé des performances")
            if journee_max:
                st.markdown(
                    f"🔥 **Meilleure journée :** journée **{journee_max}** avec **{max_points:.2f} pts** "
                    f"(moyenne sur top 5 : {moyenne_points:.2f} pts)."
                )
            else:
                st.markdown("Aucune performance enregistrée pour le moment.")
        
        st.markdown("---")
            
        # === 📍 SECTION 6 ===
        # --- 📈 Évolution du classement du joueur par journée ---
        st.markdown("### 📊 Évolution du classement par journée")

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
            
        # Appliquer le style avec pandas
        styled_table = joueur_evolution_transpose.style.applymap(lambda val: color_cells(val, joueur_evolution_transpose.index[joueur_evolution_transpose.index.get_loc(val.name)] if hasattr(val, 'name') else ""),)

        # Affichage dans Streamlit
        st.dataframe(styled_table, use_container_width=True)
        
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
            
        # --- On récupère les journées effectivement jouées ---
        journees_jouees = classements_journees.groupby("journee_match")["points"].sum()
        journees_jouees = journees_jouees[journees_jouees > 0].index.tolist()

        # Filtrer seulement les journées jouées
        classements_effectifs = classements_journees[classements_journees["journee_match"].isin(journees_jouees)].copy()

        # Palette de couleurs
        colors = px.colors.qualitative.Set2

        # Figure
        fig = go.Figure()

        for i, (nom, data_part) in enumerate(classements_effectifs.groupby("participant_nom")):
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
                    hovertemplate="Journée %{x}<br>%{fullData.name} : %{y}ᵉ<extra></extra>"
                )
            )

        # Layout
        fig.update_layout(
            xaxis=dict(title="Journée", tickfont=dict(size=10)),
            yaxis=dict(title="Classement par journée", autorange="reversed", tickfont=dict(size=10)),
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
            title=f"📊 Évolution du classement par journée - {participant_sel}"
        )

        st.plotly_chart(fig, use_container_width=True)
            
        st.markdown("---")
            
        # === 📍 SECTION 7 ===
        # --- 📈 Comparaison des points cumulés avec le top 3 ---
        st.markdown("### 🏆 Points cumulés du joueur vs Top 3")

        # Calcul des points cumulés par joueur et par journée
        points_cumules = df_progress_all.groupby(["participant_nom", "journee_match"], as_index=False)["points"].sum()
        points_cumules = points_cumules.sort_values(["participant_nom", "journee_match"])
        points_cumules["points_cumulés"] = points_cumules.groupby("participant_nom")["points"].cumsum()

        # Retirer les journées où il n'y a pas eu de progression de points (match non joué)
        points_cumules = points_cumules.groupby("participant_nom").apply(lambda df: df[df["points_cumulés"].diff().fillna(df["points_cumulés"]) != 0]).reset_index(drop=True)

        # Identification du Top 3 global
        top3 = classement.head(3)["participant_nom"].tolist() if "participant_nom" in classement.columns else []

        # Joueurs à afficher : joueur sélectionné + top3 (éviter doublons)
        joueurs_affiches = list(set(top3 + [participant_sel]))
        df_plot = points_cumules[points_cumules["participant_nom"].isin(joueurs_affiches)]

        # Palette de couleurs Plotly pour les participants (sauf joueur sélectionné)
        palette = px.colors.qualitative.Plotly
        autres_joueurs = [j for j in joueurs_affiches if j != participant_sel]
        couleurs = {j: palette[i % len(palette)] for i, j in enumerate(autres_joueurs)}
        couleurs[participant_sel] = "limegreen"  # joueur sélectionné

        fig = go.Figure()

        for joueur, data_joueur in df_plot.groupby("participant_nom"):
            if joueur == participant_sel:
                fig.add_trace(go.Scatter(
                    x=data_joueur["journee_match"],
                    y=data_joueur["points_cumulés"],
                    mode="lines+markers",
                    name=joueur,
                    line=dict(color=couleurs[joueur], width=3),
                    marker=dict(size=8)
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=data_joueur["journee_match"],
                    y=data_joueur["points_cumulés"],
                    mode="lines+markers",
                    name=joueur,
                    line=dict(color=couleurs[joueur], width=2, dash="dash"),
                    marker=dict(size=6),
                    opacity=0.9
                ))

        # Layout esthétique
        fig.update_layout(
            title=dict(text="Évolution des points cumulés - Comparaison avec le Top 3", font=dict(size=16)),
            xaxis=dict(title="Journée", tickfont=dict(size=10)),
            yaxis=dict(title="Points cumulés", tickfont=dict(size=10)),
            height=450,
            template="plotly_white",
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.25,  # sous le graphique
                xanchor="left",
                x=0,
                title="Participants"
            )
        )

        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
            
    # ---------------------- ONGLET 2 : Export Excel ----------------------
    with tabs_2:
        # --- 1️⃣ Sélection Saison / Compétition / Journée ---
        col1, col2, col3 = st.columns(3)

        # Assurer que les colonnes sont bien au bon type
        df_matchs["saison"] = df_matchs["saison"].astype(str)
        df_matchs["journee"] = df_matchs["journee"].astype(int)
        df_matchs["competition"] = df_matchs["competition"].astype(str)

        # Saison
        with col1:
            saisons = sorted(df_matchs["saison"].unique(), reverse=True)  # tri descendant
            saison_sel = st.selectbox("Saison :", saisons, key="export_saison")

        # Compétition
        with col2:
            competitions = sorted(df_matchs[df_matchs["saison"] == saison_sel]["competition"].unique())
            competition_sel = st.selectbox("Compétition :", competitions, key=f"export_comp_{saison_sel}")

        # Journée
        with col3:
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
