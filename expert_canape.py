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

def afficher_classement_visuel(classement, saison_sel, championnat_sel=None, classement_prec=None, inclure_bonus=None):
    # --- Sécurité / copie pour ne pas muter l'input ---
    if classement is None or not isinstance(classement, pd.DataFrame):
        st.info("Aucun classement à afficher.")
        return

    df = classement.copy()

    # --- Garantir colonnes de base ---
    for col in ["points", "bonus", "correction"]:
        if col not in df.columns:
            df[col] = 0
    df[["points", "bonus", "correction"]] = df[["points", "bonus", "correction"]].fillna(0)

    # --- Calcul / vérification de points_final (source de vérité) ---
    if "points_final" not in df.columns:
        # Si inclure_bonus est explicitement fourni on l'applique, sinon on considère bonus inclus par défaut
        use_bonus = True if inclure_bonus is None else bool(inclure_bonus)
        df["points_final"] = df["points"] + df["correction"] + (df["bonus"] if use_bonus else 0)
    else:
        # garantir pas de NaN
        df["points_final"] = df["points_final"].fillna(df["points"] + df["correction"] + df["bonus"])

    # --- points_affiches : valeur à afficher (permet d'afficher points sans bonus quand décoché) ---
    if inclure_bonus is None:
        # si on n'a pas de choix explicite, afficher points_final
        df["points_affiches"] = df["points_final"]
    else:
        if inclure_bonus:
            df["points_affiches"] = df["points_final"]
        else:
            # si points_final contenait bonus, on retire le bonus affiché
            # préférer une calcul fiable plutôt que df["points_final"] - df["bonus"] (préserve correction)
            df["points_affiches"] = df["points"] + df["correction"]

    # --- Tri et rangs basés sur points_final (référence unique) ---
    df = df.sort_values(by="points_final", ascending=False).reset_index(drop=True)
    df["Rang"] = df.index + 1

    # --- max pour les barres de progression (utiliser points_affiches pour cohérence d'affichage) ---
    max_points = df["points_affiches"].max() if not df.empty else 1
    if max_points == 0:
        max_points = 1  # éviter division par zero

    # --- Calcul du classement précédent (si fourni) ---
    if classement_prec is not None and isinstance(classement_prec, pd.DataFrame) and not classement_prec.empty:
        # On construit un df minimal avec participant_nom et Rang_prec
        prec = classement_prec.copy()
        # Si la colonne s'appelle points_cumul on la prend, sinon points
        if "points_cumul" in prec.columns:
            prec["points_for_rank"] = pd.to_numeric(prec["points_cumul"], errors="coerce").fillna(0)
        elif "points" in prec.columns:
            prec["points_for_rank"] = pd.to_numeric(prec["points"], errors="coerce").fillna(0)
        else:
            prec["points_for_rank"] = 0

        prec = prec.groupby("participant_nom", as_index=False)["points_for_rank"].max()
        prec = prec.sort_values(by="points_for_rank", ascending=False).reset_index(drop=True)
        prec["Rang_prec"] = prec.index + 1
        prec = prec[["participant_nom", "Rang_prec"]]

        # Merge sans écraser les colonnes existantes
        df = df.merge(prec, on="participant_nom", how="left")
        df["Rang_prec"] = df["Rang_prec"].fillna(0).astype(int)
        df["Δrang"] = df["Rang_prec"] - df["Rang"]
    else:
        df["Rang_prec"] = 0
        df["Δrang"] = 0

    # === 🌈 CSS global ===
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
            max-width: 500px;
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
        .ranking-card h5, .podium-card h4 {
            margin: 0;
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
        .podium-1 { background: linear-gradient(135deg, #facc15 10%, #92400e 120%); }
        .podium-2 { background: linear-gradient(135deg, #a1a1aa 10%, #52525b 120%); }
        .podium-3 { background: linear-gradient(135deg, #f97316 10%, #78350f 120%); }
        .podium-1 h4 { font-size: 20px; }
        .podium-2 h4 { font-size: 18px; }
        .podium-3 h4 { font-size: 16px; }
        .podium-card div.emoji {
            margin-right: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

    # === 🥇 Podium ===
    top3 = df.head(3)
    podium = {1: "🥇", 2: "🥈", 3: "🥉"}

    for place in [1, 2, 3]:
        if len(top3) >= place:
            row = top3.iloc[place - 1]
            progress = (row["points_affiches"] / max_points) if max_points else 0
            delta = int(row.get("Δrang", 0))
            bonus_html = ""
            if inclure_bonus and row.get("bonus", 0) > 0:
                bonus_html = f"<span class='bonus-tag'> &nbsp(dont {row['bonus']:.2f} bonus)</span>"

            if delta > 0:
                delta_html = f"<span style='color:#147E3BFF; font-weight:600;'>🔺+{delta}</span>"
            elif delta < 0:
                delta_html = f"<span style='color:#ef4444;'>🔻{abs(delta)}</span>"
            else:
                delta_html = ""

            st.markdown(f"""
                <div class="podium-card podium-{place}">
                    <div style="display:flex; align-items:center; justify-content:flex-start;">
                        <div class="emoji">{podium[place]}</div>
                        <h4>{row['participant_nom']} - {row['points_affiches']:.2f} pts {bonus_html} {delta_html}</h4>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width:{progress*100:.1f}%;
                            background: linear-gradient(90deg, #3b82f6, rgba(255,255,255,0.3));">
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # === 🏅 Les autres participants ===
    others = df.iloc[3:]
    for _, row in others.iterrows():
        rang = int(row["Rang"])
        nom = row["participant_nom"]
        pts = float(row["points_affiches"])
        progress = (pts / max_points) if max_points else 0
        delta = int(row.get("Δrang", 0))
        bonus_html = f"<span class='bonus-tag'> &nbsp(dont {row['bonus']:.2f} bonus)</span>" if inclure_bonus and row.get("bonus", 0) > 0 else ""

        if delta > 0:
            delta_html = f"<span style='color:#075A25FF;'>🔺+{delta}</span>"
        elif delta < 0:
            delta_html = f"<span style='color:#ef4444;'>🔻{abs(delta)}</span>"
        else:
            delta_html = ""

        st.markdown(f"""
            <div class="ranking-card">
                <h6>⚽ {rang}. {nom} - {pts:.2f} pts {bonus_html} {delta_html}</h6>
                <div class="progress-bar">
                    <div class="progress-fill" style="width:{progress*100:.1f}%;
                        background: linear-gradient(90deg, #3b82f6, rgba(255,255,255,0.3));">
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
        if n < 10:
            # Barème original
            if bons_pronos == n - 2:
                multiplicateur = 1.33
            elif bons_pronos == n - 1:
                multiplicateur = 1.66
            elif bons_pronos == n:
                multiplicateur = 2
        else:
            # Nouveau barème pour n >= 10
            if bons_pronos == n - 3:
                multiplicateur = 1.25
            elif bons_pronos == n - 2:
                multiplicateur = 1.5
            elif bons_pronos == n - 1:
                multiplicateur = 1.75
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
            saisons = sorted(df_matchs["saison"].unique(), reverse=True)
            saison_sel = st.selectbox("Sélectionner une saison", saisons)

        # --- Sélection du championnat --- #
        with col_select_championnat:
            championnats = df_matchs[df_matchs["saison"] == saison_sel]["competition"].dropna().unique().tolist()
            championnats = ["Toutes"] + sorted(championnats)
        #   default_champ = "Ligue 1" if "Ligue 1" in championnats else "Toutes"
            default_champ = "Coupe du Monde" if "Coupe du Monde" in championnats else "Toutes"
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
            df_journees["match_joue"] = df_journees["score_domicile"].notna() & df_journees["score_exterieur"].notna()
            df_statut = df_journees.groupby("journee").apply(lambda x: x["match_joue"].all()).reset_index(name="complete")

            journees_jouees = df_statut[df_statut["complete"]]["journee"].tolist()
            derniere_journee = max(journees_jouees) if journees_jouees else min(df_journees["journee"])
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
                top_n = st.slider(
                    "Afficher les meilleurs participants",
                    min_value=1,
                    max_value=nb_participants,
                    value=min(10, nb_participants),
                    step=1,
                    help=f"Sur un total de {nb_participants} participants pour {saison_sel} ({championnat_sel})"
                )
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

        st.markdown("---")

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
        df["bon_score"] = (
            (df["prono_dom"] == df["match_dom"]) &
            (df["prono_ext"] == df["match_ext"])
        )

        # Convertir les journées en int
        df["journee_match"] = pd.to_numeric(df["journee_match"], errors="coerce")
        df = df.dropna(subset=["journee_match"])
        df["journee_match"] = df["journee_match"].astype(int)

        # --- Calcul des points individuels --- #
        df["points"] = df.apply(calcul_points, axis=1)

        # --- Calcul des points par journée et cumul --- #
        df_progress_all = (df.groupby(["participant_nom", "journee_match"]).apply(calcul_points_journee).reset_index())
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
        with kpi_cols[0]: kpi_card("🏟️ Matchs", nb_matchs, color="#3b82f6")
        with kpi_cols[1]: kpi_card("🧾 Pronostics", nb_pronos, color="#22c55e")
        with kpi_cols[2]: kpi_card("👥 Participants", nb_participants, color="#f59e0b")
        with kpi_cols[3]: kpi_card("🎯 Moy. pts/joueur", f"{moyenne_points_joueur:.2f}", color="#2563eb")

        st.markdown("---")

        # --- Affichage classement et progression ---
        #GROUPES_CLASSEMENT = {
        #    "Classement global": None,
        #    "Les experts du Canapé": ["Matthieu", "Kévin", "Olivier", "Cédric", "Sébastien", "Pierre"],
        #    "Les hasards de dingue": ["Matthieu", "Merguez", "Meemway", "Bebou", "Goustine", "Thif Thif"]
        #}
        
        st.subheader(f"Classement {'global' if journee_sel == 'Toutes' else f'jusqu’à la journée {journee_sel}'} – "
            f"{'toutes compétitions' if championnat_sel == 'Toutes' else championnat_sel} – {saison_sel}")

        col_classement, col_evolution = st.columns([1, 2])
        with col_classement:
            #groupe_sel = st.selectbox(
            #    "🎯 Groupe de classement",
            #    list(GROUPES_CLASSEMENT.keys())
            #)
            
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
                
            #participants_groupe = GROUPES_CLASSEMENT[groupe_sel]

            #if participants_groupe is not None:
            #    df_progress_filtered = df_progress_filtered[
            #        df_progress_filtered["participant_nom"].isin(participants_groupe)
            #    ]

            #    df_progress_all = df_progress_all[
            #        df_progress_all["participant_nom"].isin(participants_groupe)
            #    ]    
                
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

            inclure_bonus = st.checkbox("Prendre en compte les bonus", value=True)

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

            afficher_classement_visuel(classement, saison_sel, championnat_sel if championnat_sel != "Toutes" else None, classement_prec=classement_prec, inclure_bonus=inclure_bonus)

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
        
        # === 📍 SECTION 2 ===        
        col_participants, col_resultats = st.columns([1,3])
        with col_participants:
            st.markdown("### 🎮 Sélection du joueur")
            # --- Sélection du participant ---
            participants = classement["participant_nom"].tolist()
            participant_sel = participants[0]

            # Création de 4 colonnes
            cols = st.columns(4)

            # On parcourt les participants et on les place dans les colonnes alternativement
            for idx, participant in enumerate(participants):
                col = cols[idx % 2]  # alterne entre les colonnes
                card_class = "participant-card"
                if participant == participant_sel:
                    card_class += " selected"
                
                # Bouton caché pour détecter le clic
                if col.button(participant, key=participant):
                    participant_sel = participant
    
        # --- Filtrer les données du joueur sélectionné ---
        df_participant = df[df["participant_nom"] == participant_sel].copy()

        if journee_sel != "Toutes":
            df_participant = df_participant[df_participant["journee_match"] == int(journee_sel)]

        if df_participant.empty:
            st.warning("Aucun pronostic trouvé pour ce joueur sur cette journée.")
        else:
            # --- Recalcul des points de chaque match ---
            df["points"] = df.apply(calcul_points, axis=1)

            journee_courante = df_participant["journee_match"].iloc[0]
            df_journee = df[df["journee_match"] == journee_courante].copy()

            # --- Points sans bonus ---
            points_sans_bonus = (
                df_journee.groupby("participant_nom")["points"]
                .sum()
                .reset_index()
                .rename(columns={"points": "points_bruts"})
            )

            # --- Points totaux (avec bonus) ---
            df_journee_bonus = (
                df_journee.groupby("participant_nom")
                .apply(calcul_points_journee)
                .reset_index()
                .rename(columns={"points": "points_total"})
            )

            # --- Nombre de bons scores (score exact) ---
            bons_scores = (
                df_journee[df_journee["bon_score"] == True]
                .groupby("participant_nom")
                .size()
                .reset_index(name="bons_scores")
            )

            # --- Fusion ---
            classement_journee = pd.merge(points_sans_bonus, df_journee_bonus, on="participant_nom", how="left")
            
            # --- Fusion des bons scores ---
            classement_journee = classement_journee.merge(bons_scores, on="participant_nom", how="left")

            # --- Calcul du bonus réel ---
            classement_journee["points_bonus"] = classement_journee["points_total"] - classement_journee["points_bruts"]
            classement_journee["points_bonus"] = classement_journee["points_bonus"].round(4)
            classement_journee["bons_scores"] = classement_journee["bons_scores"].fillna(0).astype(int)

            # --- Tri ---
            classement_journee = (
                classement_journee.sort_values("points_total", ascending=False)
                .reset_index(drop=True)
            )
            classement_journee["Rang"] = classement_journee.index + 1

            # --- Performance ---
            max_points = classement_journee["points_total"].max()
            classement_journee["Performance (%)"] = (
                classement_journee["points_total"] / max_points * 100).round(1)
            
            # --- Renommage des colonnes ---
            classement_journee = classement_journee.rename(columns={
                "participant_nom": "Participant",
                "points_total": "Total Points",
                "points_bonus": "Dont Bonus",
                "bons_pronos": "Nombre de bons pronos",
                "bons_scores": "Nombre de bons scores"
            })

            # --- Classement du joueur sélectionné ---
            joueur_stats = classement_journee[classement_journee["Participant"] == participant_sel]
            
            # On supprime la colonne points_bruts
            classement_journee = classement_journee.drop(columns=["points_bruts"])

        with col_resultats:
            st.markdown(f"### 🏅 Classement - Journée {journee_courante}")
            st.dataframe(
                classement_journee[
                    [
                        "Rang", "Participant",
                        "Total Points", "Dont Bonus",
                        "Nombre de bons pronos", "multiplicateur",
                        "Performance (%)"
                    ]
                ],
                hide_index=True,
                use_container_width=False
            )
            
        # --- Résumé personnel ---
        if not joueur_stats.empty:
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

            with kpi_cols[0]: kpi_card("🏆 Rang", rang, color="#3b82f6")  
            with kpi_cols[1]: kpi_card("💯 Points bruts", f"{points_bruts:.2f}", color="#22c55e")  
            with kpi_cols[2]: kpi_card("🎯 Bons pronos", f"{bons_pronos} / {len(df_participant)}", color="#f59e0b")  
            with kpi_cols[3]: kpi_card("🎯 Bons scores", f"{bons_scores}", color="#ef4444")
            with kpi_cols[4]: kpi_card("✨ Points avec bonus", f"{points_bonus:.2f}", color="#9333ea")  
            with kpi_cols[5]: kpi_card("⚡ Multiplicateur", f"x{multiplicateur}", color="#9333ea")  

            # Sécuriser la valeur de la barre de progression
            perf_safe = 0 if pd.isna(perf) else perf
            
            # S'assurer que la valeur est entre 0 et 100
            perf_safe = max(0, min(100, perf_safe))

            # --- Barre de performance visuelle ---
            st.progress(perf_safe / 100)
            st.caption(f"Performance de {perf_safe:.1f}% par rapport au meilleur score de la journée.")
                
        # --- 🔍 Statistiques complémentaires ---
        st.markdown(f"### 📊 Statistiques avancées de {participant_sel}")

        # Filtrer les matchs du joueur sélectionné
        df_joueur = df[df["participant_nom"] == participant_sel].copy()
        df_joueur_participant = df_progress_all[df_progress_all["participant_nom"] == participant_sel].copy()

        # --- Calculs de points par match avec bonus ---
        df_joueur["points"] = df_joueur.apply(calcul_points, axis=1)

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
        df_joueur["bonus"] = df_joueur.apply(lambda r: float(calcul_points_journee(pd.DataFrame([r]))["multiplicateur"]), axis=1)

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
        df_bons["cote_correcte"] = df_bons.apply(cote_prono_correct, axis=1)
        # --- Moyenne des cotes exactes des pronos gagnés ---
        cote_moyenne = df_bons["cote_correcte"].mean()

        df_joueur["roi_match"] = df_joueur.apply(gain_match, axis=1)
        roi_total = df_joueur["roi_match"].sum()
        
        # --- Affichage final ---
        # --- Ligne 1 : Performances générales ---
        kpi_cols = st.columns([1, 1, 1, 1, 1, 1])

        with kpi_cols[0]: kpi_card("🎯 Total bons pronos", f"{nb_bons_pronos}/{total_pronos}", f"{pourcentage_bons_pronos}%", color="#f59e0b") 
        with kpi_cols[1]: kpi_card("🎯 Total bons scores", f"{nb_bons_scores}/{total_pronos}", f"{pourcentage_bons_scores}%", color="#ef4444")
        with kpi_cols[2]: kpi_card("🏅 Journées gagnées", int(journees_gagnees), color="#3b82f6")  
        with kpi_cols[3]: kpi_card("Meilleur score / journée", round(meilleur_score_journee, 2), color="#22c55e")  
        with kpi_cols[4]: kpi_card("Moyenne points / match", round(moyenne_points, 2), color="#22c55e")  
        with kpi_cols[5]: kpi_card("💥 Max points sur un match", round(max_points_match, 2), color="#22c55e")  

        st.text("")
        
        # --- Ligne 2 : Bonus et scores spécifiques ---
        kpi_cols2 = st.columns([1, 1, 1, 1, 1])

        with kpi_cols2[0]: kpi_card("⭐ Bonus x1.33", int(bonus_133), color="#9333ea")  
        with kpi_cols2[1]: kpi_card("🔥 Bonus x1.66", int(bonus_166), color="#9333ea")  
        with kpi_cols2[2]: kpi_card("💎 Bonus x2", int(bonus_200), color="#9333ea")  
        with kpi_cols2[3]: kpi_card("📈 Cote moyenne bons pronos", round(cote_moyenne, 2), color="#12eccf")  
        with kpi_cols2[4]: kpi_card("💰 ROI théorique", round(roi_total, 2), color="#12eccf")  

        st.markdown("---")
            
        # === 📍 SECTION 3 ===       
        col_pronos, col_evolution_pts = st.columns([1.3, 2])
        with col_pronos:
            st.markdown(f"### 📝 Pronostics de {participant_sel}")
            
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
            table_display.columns = ["Journée", "Match", "Prono", "Score Réel", "Points"]
            table_display = table_display.sort_values("Match").reset_index(drop=True)

            # --- Affichage ---
            st.dataframe(table_display, hide_index=True, use_container_width=True)

        with col_evolution_pts:
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
        # --- Comparaison progression joueur vs moyenne générale ---
        col_comparaison_moyenne, col_top5 = st.columns([2.2, 1])
        with col_comparaison_moyenne:
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
            if not df_comparatif.empty:
                diff_points = (
                    df_comparatif["points_cumul_joueur"].iloc[-1]
                    - df_comparatif["points_cumul_moyenne"].iloc[-1]
                )

                tendance = "au-dessus" if diff_points > 0 else "en dessous"

                st.markdown(
                    f"💡 **{participant_sel}** est actuellement **{abs(diff_points):.2f} points {tendance}** de la moyenne des participants."
                )
            else:
                st.warning("Pas assez de données pour calculer la comparaison.")

        with col_top5:
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
                
                # --- Top 5 des pires journées du joueur ---
                st.markdown("### 💀 Top 5 des pires journées")

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
                    df_joueur_pires_display["Points"] = (
                        df_joueur_pires_display["Points"].round(2)
                    )
                    df_joueur_pires_display["Multiplicateur"] = (
                        df_joueur_pires_display["Multiplicateur"].round(2)
                    )

                    st.dataframe(
                        df_joueur_pires_display,
                        hide_index=True,
                        use_container_width=True
                    )    

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
        
        # === 📍 SECTION 5 ===
        # --- 📈 Comparaison des points cumulés avec le top 3 ---
        st.markdown(f"### 🏆 Points cumulés de {participant_sel} vs Top 3")

        # Calcul des points cumulés par joueur et par journée
        points_cumules = df_progress_all.groupby(["participant_nom", "journee_match"], as_index=False)["points"].sum()
        points_cumules = points_cumules.sort_values(["participant_nom", "journee_match"])
        points_cumules["points_cumulés"] = points_cumules.groupby("participant_nom")["points"].cumsum()

        # Retirer les journées où il n'y a pas eu de progression de points (match non joué)
        # points_cumules = points_cumules.groupby("participant_nom").apply(lambda df: df[df["points_cumulés"].diff().fillna(df["points_cumulés"]) != 0]).reset_index(drop=True)

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
        # styled_table = joueur_evolution_transpose.style.applymap(lambda val: color_cells(val, joueur_evolution_transpose.index[joueur_evolution_transpose.index.get_loc(val.name)] if hasattr(val, 'name') else ""),)

        # Affichage dans Streamlit
        #st.dataframe(styled_table, use_container_width=True)
        
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
        # --- Récupération de l'historique complet du joueur depuis les CSV ---
        # Filtrage sur le participant
        # data_historique = df_pronos[df_pronos["participant_nom"] == participant_sel].merge(
        #     df_matchs,
        #    on="match_id",
        #     suffixes=("_prono", "_match")
        # )

        # --- Filtrage selon la compétition sélectionnée ---
        # if championnat_sel != "Toutes":
        #     data_historique = data_historique[data_historique["competition"] == championnat_sel]

        # --- Sélection des colonnes et renommage pour correspondre à l'ancien SQL ---
        # data_historique = data_historique[[
        #     "participant_id",
        #     "participant_nom",
        #     "score_domicile_prono", 
        #     "score_exterieur_prono",
        #     "score_domicile_match", 
        #     "score_exterieur_match",
        #     "equipe_domicile_nom",
        #     "equipe_exterieure_nom",
        #     "cote_domicile",
        #     "cote_exterieur",
        #     "cote_nul",
        #     "journee_match",
        #     "saison_match",
        #     "competition",
        #     "match_id"
        # ]].rename(columns={
        #     "score_domicile_prono": "prono_dom",
        #     "score_exterieur_prono": "prono_ext",
        #     "score_domicile_match": "match_dom",
        #     "score_exterieur_match": "match_ext"
        # })

        # --- Suppression des doublons éventuels ---
        # df_historique = data_historique.drop_duplicates(subset=["participant_id", "match_id"], keep="last")

        # --- Préparer le DataFrame historique ---
        # df_historique["journee_match"] = df_historique["journee_match"].astype(int)
        # df_historique = df_historique.sort_values(by=["saison_match", "journee_match"]).reset_index(drop=True)

        # Vérification des résultats
        # if df_historique.empty:
        #     st.info(f"Aucun pronostic historique trouvé pour {participant_sel}.")
        # else:
        #     # Calcul des points pour toutes les saisons
        #    df_historique["points"] = df_historique.apply(calcul_points, axis=1)
        #     df_historique = df_historique.sort_values(["saison_match", "journee_match"]).reset_index(drop=True)

        # --- Comparaison progression joueur par saison ---
        # st.markdown(f"### 📊 Comparaison des saisons de {participant_sel}")

        # saisons_disponibles = sorted(df_historique["saison_match"].unique(), reverse=True)
        # default_saisons = [saison_sel] if saison_sel in saisons_disponibles else []

        # saisons_sel = st.multiselect(
        #     "Sélectionnez les saisons à comparer",
        #     options=saisons_disponibles,
        #    default=default_saisons,
        #     key=f"saisons_compare_{participant_sel}"
        # )

        # if not saisons_sel:
        #     st.warning("Veuillez sélectionner au moins une saison pour l'affichage.")
        # else:
        #     fig = go.Figure()
        #     couleurs_prev = px.colors.qualitative.Pastel
        #     idx_couleur = 0

        #     for saison in saisons_sel:
        #         df_saison = df_historique[df_historique["saison_match"] == saison].copy()
        #         if df_saison.empty:
        #             continue

                # Tri et conversion en int pour les journées
        #         df_saison["journee_match"] = df_saison["journee_match"].astype(int)
        #         df_saison = df_saison.sort_values("journee_match").reset_index(drop=True)

                # --- Calcul cumulatif par journée ---
        #         df_saison = df_saison.groupby("journee_match", as_index=False)["points"].sum()
        #         df_saison["points_cumul"] = df_saison["points"].cumsum()

                # Traces
        #         if saison == saison_sel:
        #             fig.add_trace(go.Scatter(
        #                 x=df_saison["journee_match"],
        #                 y=df_saison["points_cumul"],
        #                 mode="lines+markers",
        #                 name=f"Saison {saison} (actuelle)",
        #                 line=dict(color="limegreen", width=4),
        #                 marker=dict(size=10, symbol="circle"),
        #                 hovertemplate="Journée: %{x}<br>Points cumulés: %{y:.2f}<br>Points journée: %{customdata[0]:.2f}<extra></extra>",
        #                 customdata=df_saison[["points"]].values
        #              ))
        #         else:
        #            couleur = couleurs_prev[idx_couleur % len(couleurs_prev)]
        #             idx_couleur += 1
        #             fig.add_trace(go.Scatter(
        #                 x=df_saison["journee_match"],
        #                 y=df_saison["points_cumul"],
        #                 mode="lines+markers",
        #                 name=f"Saison {saison} (précédente)",
        #                 line=dict(color=couleur, width=2, dash="dash"),
        #                 marker=dict(size=7, symbol="circle"),
        #                 opacity=0.6,
        #                 hovertemplate="Journée: %{x}<br>Points cumulés: %{y:.2f}<br>Points journée: %{customdata[0]:.2f}<extra></extra>",
        #                 customdata=df_saison[["points"]].values
        #             ))

        #     fig.update_layout(
        #        title=f"Progression cumulée de {participant_sel} par saison",
        #         xaxis_title="Journée",
        #         yaxis_title="Points cumulés",
        #         xaxis=dict(range=[0, df_historique["journee_match"].max() + 1]),  # X commence à 0 et va jusqu'à max +1
        #         hovermode="x unified",
        #         template="plotly_white",
        #         height=450,
        #         legend=dict(title="Saisons", x=0.01, y=0.99),
        #         margin=dict(l=50, r=50, t=60, b=50)
        #     )

        #     st.plotly_chart(fig, use_container_width=True)

        # st.markdown("---") 
        
        # === 📍 SECTION 8 ===
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
            st.markdown("### 🏅 Classement – Journées gagnées")
            st.dataframe(classement_journees_gagnees[["Rang", "Participant", "Journees gagnées"]], hide_index=True, use_container_width=True)
        with classements_cols[1] :
            st.markdown("### 🎯 Classement – Bons scores (score exact)")
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
            df_pronos = tables["all_pronostics"]

            pseudos_pronos = df_pronos[
                (df_pronos["saison"] == saison_sel) &
                (df_pronos["competition_nom"] == competition_sel)
            ]["participant_nom"].dropna().unique().tolist()

            # --- Fusion des pseudos sans doublons ---
            pseudos_dispo = sorted(list(set(pseudos_pronos)))

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
                    use_container_width=True,
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