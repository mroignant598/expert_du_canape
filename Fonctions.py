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
import datetime

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

    # === 🏅 Les autres participants dans un tableau ===
    others = df.iloc[3:].copy()

    if not others.empty:

        def evolution(delta):
            if delta > 0:
                return f"🔺 +{delta}"
            elif delta < 0:
                return f"🔻 {delta}"
            elif delta == 0:
                return ""
            return "➖"

        others["Évolution"] = others["Δrang"].apply(evolution)

        if inclure_bonus:
            others["Bonus"] = others["bonus"].round(2)

        tableau = pd.DataFrame({
            "Rang": others["Rang"],
            "Participant": others["participant_nom"],
            "Points": others["points_affiches"].round(2),
            "Évolution": others["Évolution"]
        })

        if inclure_bonus:
            tableau["Bonus"] = others["Bonus"]

        nb_lignes = len(tableau)

        st.dataframe(
            tableau,
            hide_index=True,
            use_container_width=False,
            height=min(36 * (nb_lignes + 1), 1000),
            column_config={
                "Rang": st.column_config.NumberColumn("Rang", width=50),
                "Participant": st.column_config.TextColumn("Participant", width=100),
                "Points": st.column_config.NumberColumn("Points", width=80),
                "Évolution": st.column_config.TextColumn("Évolution", width=80),
                "Bonus": st.column_config.NumberColumn("Bonus", width=80),
            }
        )

def kpi_card(title, value, delta=None, color="#2563eb", width="100%", height="120px"):
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {color} 0%, #ffffff20 100%);
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
        transition: transform 0.2s, box-shadow 0.2s;
    " onmouseover="this.style.transform='scale(1.05)';this.style.boxShadow='0 8px 25px rgba(0,0,0,0.25)';" 
            onmouseout="this.style.transform='scale(1)';this.style.boxShadow='0 4px 20px rgba(0,0,0,0.15)';">
        <div style="font-size: 16px; font-weight: 500; margin-bottom: 5px;">{title}</div>
        <div style="font-size: 28px; font-weight: bold;">{value}</div>
        {"<div style='font-size:14px; opacity:0.8; margin-top:2px;'>{}</div>".format(delta) if delta else ""}
    </div>
    """, unsafe_allow_html=True)

def kpi_card_accueil(title, value, color):
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
    prolifique_prono = 4 <= buts_prono < 7
    prolifique_reel = 4 <= buts_reel < 7
    super_prolifique_prono = buts_prono >=7
    super_prolifique_reel = buts_reel >=7

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
    if prolifique_prono and (prolifique_reel or super_prolifique_reel): multiplicateur += 1.25
    if prolifique_prono and not prolifique_reel: multiplicateur -= 0.5
    if super_prolifique_prono and super_prolifique_reel: multiplicateur += 2.75
    if super_prolifique_prono and not super_prolifique_reel: multiplicateur -= 0.75

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
 
def color_pronos(df):

            styles = pd.DataFrame("", index=df.index, columns=df.columns)

            for idx in df.index:

                score_reel = str(df.loc[idx, "Score Réel"])
                
                for col in df.columns:
                    if col in ["Match", "Score Réel"]:
                        continue

                    val = df.loc[idx, col]

                    if pd.isna(val):
                        continue

                    try:
                        text = str(val)

                        # extraction points
                        points = float(text.split("(")[1].replace(")", ""))

                        # extraction prono (avant parenthèse)
                        prono = text.split("(")[0].strip()

                        # extraction score réel
                        if score_reel != "nan":
                            real = score_reel.strip()

                            # 1) rouge si négatif
                            if points < 0:
                                styles.loc[idx, col] = "background-color:#dc3545;color:white;font-weight:bold;"
                                continue

                            # 2) score exact (comparaison réelle)
                            if prono == real:
                                styles.loc[idx, col] = "background-color:#28a745;color:white;font-weight:bold;"
                                continue

                            # 3) bon prono (positif mais pas exact)
                            if points > 0:
                                styles.loc[idx, col] = "background-color:#ffc107;color:black;font-weight:bold;"

                    except Exception:
                        continue

            return styles
        
def get_cote_gagnante(row):

    if row["match_dom"] > row["match_ext"]:
        return row["cote_domicile"]

    elif row["match_dom"] < row["match_ext"]:
        return row["cote_exterieur"]

    else:
        return row["cote_nul"]

def color_cotes(row):

    styles = [""] * len(row)

    gagnante = row["Cote gagnante"]

    for col in ["1", "N", "2"]:

        if row[col] == gagnante:

            idx = row.index.get_loc(col)

            styles[idx] = (
                "background-color:#16a34a;"
                "color:white;"
                "font-weight:bold;"
            )

    return styles

def format_score(row):
    if pd.isna(row["match_dom"]) or pd.isna(row["match_ext"]):
        return "-"
    return f"{int(row['match_dom'])}-{int(row['match_ext'])}"

def format_score_reel(row):
    if pd.isna(row["match_dom"]) or pd.isna(row["match_ext"]):
        return ""
    return f"{int(row['match_dom'])}-{int(row['match_ext'])}"