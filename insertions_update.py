import os
import time
import csv
from datetime import date
import pandas as pd
import mysql.connector
from mysql.connector import Error
from sqlalchemy import create_engine, text
import requests

# ---------------- CONFIGURATION ---------------- #
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "football_db",
    "charset": "utf8mb4",
    "collation": "utf8mb4_general_ci"
}

API_TOKEN = "fb93f11fcda4428593dcd6bd32860a21"
HEADERS = {"X-Auth-Token": API_TOKEN}

# ---------------- CHEMINS FICHIERS ---------------- #
matchs_excel = r"D:\Docs\Foot\Fichiers Excel\2025-2026\MatchsL1_2025_2026.xlsx"
pronos_excel = matchs_excel  # si les pronos sont dans le même fichier
bonus_excel = r"D:\Docs\Foot\Fichiers Excel\table_bonus.xlsx"
output_csv_folder = r"D:\Docs\Foot\expert_du_canape\csv"

# ---------------- SAISON ---------------- #
saison_id = 59  # à adapter 

# ---------------- FONCTIONS ---------------- #

def connect_db():
    return mysql.connector.connect(**db_config)

def get_team_id(cursor, team_name):
    cursor.execute("SELECT id FROM clubs WHERE nom = %s", (team_name,))
    res = cursor.fetchone()
    return res[0] if res else None

def get_participant_id(cursor, pseudo):
    cursor.execute("SELECT id FROM participants WHERE pseudo = %s", (pseudo,))
    res = cursor.fetchone()
    return res[0] if res else None

def get_saison_info(cursor, saison_id):
    cursor.execute("""
        SELECT s.id, s.saison, s.code, c.nom AS competition
        FROM saisons s
        LEFT JOIN competitions c ON s.competition_id = c.id
        WHERE s.id=%s
    """, (saison_id,))
    return cursor.fetchone()

def get_match_id(cursor, saison_id, journee, equipe_dom_id, equipe_ext_id):
    cursor.execute("""
        SELECT match_id FROM all_matchs_football
        WHERE saison_id=%s AND journee=%s
        AND equipe_domicile_id=%s AND equipe_exterieure_id=%s
    """, (saison_id, journee, equipe_dom_id, equipe_ext_id))
    res = cursor.fetchone()
    return res[0] if res else None

def get_match_info(cursor, match_id):
    """Récupère les infos journee, saison, code_saison pour un match"""
    cursor.execute("""
        SELECT journee, saison, code_saison FROM all_matchs_football
        WHERE match_id = %s
    """, (match_id,))
    return cursor.fetchone()

# ---------------- Import / Update Matchs ---------------- #
def import_matches_from_excel(matchs_excel, saison_id):
    print("\n📥 Import des matchs...")
    df = pd.read_excel(matchs_excel)
    
    # Normalisation des noms de colonnes
    df.columns = [
        c.strip().lower()
        .replace('é','e')
        .replace(' ','_')
        .replace('/','_')
        .replace('-','_')
        for c in df.columns
    ]
    
    # print("Colonnes détectées :", df.columns)

    # Colonnes obligatoires
    mandatory_cols = ['journee','equipe_domicile','equipe_exterieure']
    df = df.dropna(subset=mandatory_cols)

    conn = connect_db()
    cursor = conn.cursor(buffered=True)

    saison_info = get_saison_info(cursor, saison_id)
    if not saison_info:
        print(f"⚠️ Saison {saison_id} introuvable")
        return
    _, saison_nom, code_saison, competition_nom = saison_info

    inserted, updated = 0, 0

    for _, row in df.iterrows():
        try:
            journee = int(row['journee'])
        except:
            continue

        equipe_dom_id = get_team_id(cursor, row['equipe_domicile'])
        equipe_ext_id = get_team_id(cursor, row['equipe_exterieure'])
        if not equipe_dom_id or not equipe_ext_id:
            continue

        date_match = pd.to_datetime(row['date']).date() if 'date' in row and pd.notna(row['date']) else None
        score_dom = row.get('score_domicile', None)
        score_ext = row.get('score_exterieur', None)
        cote_dom = row.get('cote_domicile', None)
        cote_nul = row.get('cote_nul', None)
        cote_ext = row.get('cote_exterieur', None)
        groupe = row.get('groupe', None)
        phase = row.get('phase', None)
        aller_retour = row.get('aller_retour', None)
        prolongation_score_domicile = row.get('prolongation_score_domicile', None)
        prolongation_score_exterieur = row.get('prolongation_score_exterieur', None)
        tab_score_domicile = row.get('tab_score_domicile', None)
        tab_score_exterieur = row.get('tab_score_exterieur', None)

        match_id = get_match_id(cursor, saison_id, journee, equipe_dom_id, equipe_ext_id)
        if match_id:
            # UPDATE
            cursor.execute("""
                UPDATE all_matchs_football
                SET date=%s, score_domicile=%s, score_exterieur=%s,
                    cote_domicile=%s, cote_nul=%s, cote_exterieur=%s,
                    groupe=%s, phase=%s, aller_retour=%s,
                    prolongation_score_domicile=%s, prolongation_score_exterieur=%s,
                    tab_score_domicile=%s, tab_score_exterieur=%s,
                    competition=%s
                WHERE match_id=%s
            """, (
                date_match, score_dom, score_ext,
                cote_dom, cote_nul, cote_ext,
                groupe, phase, aller_retour,
                prolongation_score_domicile, prolongation_score_exterieur,
                tab_score_domicile, tab_score_exterieur,
                competition_nom, match_id
            ))
            updated += 1
        else:
            # INSERT
            cursor.execute("""
                INSERT INTO all_matchs_football
                (saison_id, saison, code_saison, competition, date, journee,
                equipe_domicile_id, equipe_domicile_nom,
                equipe_exterieure_id, equipe_exterieure_nom,
                score_domicile, score_exterieur,
                cote_domicile, cote_nul, cote_exterieur,
                groupe, phase, aller_retour,
                prolongation_score_domicile, prolongation_score_exterieur,
                tab_score_domicile, tab_score_exterieur)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                saison_id, saison_nom, code_saison, competition_nom, date_match, journee,
                equipe_dom_id, row['equipe_domicile'],
                equipe_ext_id, row['equipe_exterieure'],
                score_dom, score_ext, cote_dom, cote_nul, cote_ext,
                groupe, phase, aller_retour,
                prolongation_score_domicile, prolongation_score_exterieur,
                tab_score_domicile, tab_score_exterieur
            ))
            inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ Matchs importés/mis à jour : {inserted} insérés, {updated} mis à jour.")

# ---------------- Import / Update Pronostics ---------------- #
def import_pronos_from_excel(pronos_excel, saison_id):
    print("\n📥 Import des pronostics...")
    df = pd.read_excel(pronos_excel)
    fixed_cols = ['date','journée','equipe_domicile','equipe_exterieure','score_domicile','score_exterieur','cote_domicile','cote_nul','cote_exterieur']
    dynamic_cols = [c for c in df.columns if c not in fixed_cols]
    pseudos = list({col.rsplit('_',1)[0] for col in dynamic_cols})

    conn = connect_db()
    cursor = conn.cursor(buffered=True)

    inserted, updated = 0, 0

    for _, row in df.iterrows():
        try:
            journee = int(row['journée'])
        except:
            continue
        equipe_dom_id = get_team_id(cursor, row['equipe_domicile'])
        equipe_ext_id = get_team_id(cursor, row['equipe_exterieure'])
        if not equipe_dom_id or not equipe_ext_id:
            continue

        match_id = get_match_id(cursor, saison_id, journee, equipe_dom_id, equipe_ext_id)
        if not match_id:
            continue

        # 🔍 Récupération des infos du match pour compléter le pronostic
        match_info = get_match_info(cursor, match_id)
        if not match_info:
            continue
        match_journee, match_saison, match_code_saison = match_info
        
        # 🔍 Récupérer la compétition depuis la table saisons
        cursor.execute("SELECT c.nom FROM saisons s LEFT JOIN competitions c ON s.competition_id = c.id WHERE s.code=%s", (match_code_saison,))
        res = cursor.fetchone()
        competition = res[0] if res else None

        for pseudo in pseudos:
            participant_id = get_participant_id(cursor, pseudo)
            if not participant_id:
                continue

            col_dom = f"{pseudo}_dom"
            col_ext = f"{pseudo}_ext"
            if col_dom not in df.columns or col_ext not in df.columns:
                continue

            score_dom = row[col_dom]
            score_ext = row[col_ext]
            if pd.isna(score_dom) or pd.isna(score_ext):
                continue

            cursor.execute("""
                SELECT id FROM all_pronostics
                WHERE participant_id=%s AND match_id=%s
            """, (participant_id, match_id))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                    UPDATE all_pronostics
                    SET score_domicile=%s, score_exterieur=%s,
                        journee=%s, saison=%s, code_saison=%s, competition_nom=%s
                    WHERE id=%s
                """, (score_dom, score_ext, match_journee, match_saison, match_code_saison, competition, existing[0]))
                updated += 1
            else:
                cursor.execute("""
                    INSERT INTO all_pronostics
                    (participant_id, participant_nom,
                    equipe_domicile, equipe_exterieure,
                    score_domicile, score_exterieur,
                    match_id, journee, saison, code_saison, competition_nom)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (participant_id, pseudo, row['equipe_domicile'], row['equipe_exterieure'],
                    score_dom, score_ext, match_id, match_journee, match_saison, match_code_saison, competition))
                inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ Pronostics importés/mis à jour : {inserted} insérés, {updated} mis à jour.")

# ---------- FONCTION PRINCIPALE ----------
def import_bonus_from_excel(bonus_excel):
    print("\n📥 Import des bonus...")
    try:
        # Lecture du fichier Excel
        df = pd.read_excel(bonus_excel)
        print(f"\n{len(df)} lignes trouvées dans le fichier Excel.")

        # Nettoyage des noms de colonnes
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        
        # Connexion à la base MySQL
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Parcours des lignes du fichier
        for _, row in df.iterrows():
            participant = str(row['participant']).strip()
            saison = str(row['saison']).strip()
            competition = str(row['compétition']).strip()
            bonus_mid = float(row.get('bonus_mid', 0) or 0)
            bonus_end = float(row.get('bonus_end', 0) or 0)
            regularite = float(row.get('régularité', 0) or 0)
            extra_question = float(row.get('extra_question', 0) or 0)
            correction = float(row.get('correction', 0) or 0)

            # Récupération des ID depuis les tables de référence
            cursor.execute("SELECT id FROM participants WHERE pseudo = %s", (participant,))
            result = cursor.fetchone()
            id_participant = result[0] if result else None

            cursor.execute("SELECT id, code FROM saisons WHERE competition = %s AND saison = %s", (competition, saison))
            result = cursor.fetchone()
            saison_id, code_saison = result if result else (None, None)

            cursor.execute("SELECT id FROM competitions WHERE nom = %s", (competition,))
            result = cursor.fetchone()
            competition_id = result[0] if result else None

            if not (id_participant and saison_id and competition_id):
                print(f"⚠️ Données incomplètes pour {participant} / {saison} / {competition} — ligne ignorée.")
                continue

            # Vérification si l’entrée existe déjà
            cursor.execute("""
                SELECT bonus_id FROM bonus 
                WHERE id_participant = %s AND saison_id = %s AND competition_id = %s
            """, (id_participant, saison_id, competition_id))
            existing = cursor.fetchone()

            if existing:
                # Mise à jour
                cursor.execute("""
                    UPDATE bonus
                    SET bonus_mi_saison = %s,
                        bonus_fin_saison = %s,
                        regularite = %s,
                        extra_questions = %s,
                        correction = %s
                    WHERE bonus_id = %s
                """, (bonus_mid, bonus_end, regularite, extra_question, correction, existing[0]))
                # print(f"🔄 Mise à jour : {participant} / {saison} / {competition}")
            else:
                # Insertion
                cursor.execute("""
                    INSERT INTO bonus (participant, id_participant, saison, saison_id, code_saison,
                                        competition, competition_id, bonus_mi_saison, bonus_fin_saison,
                                        regularite, extra_questions, correction)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (participant, id_participant, saison, saison_id, code_saison,
                        competition, competition_id, bonus_mid, bonus_end,
                        regularite, extra_question, correction))
                print(f"✅ Insertion : {participant} / {saison} / {competition}")

        conn.commit()
        conn.close()
        print("✅ Import bonus terminé.")
    except Exception as e:
        print(f"❌ Erreur import bonus : {e}")
                
# ---------------- EXPORT CSV ---------------- #
def export_tables_to_csv(output_csv_folder):
    print("\n💾 Export des tables MySQL vers CSV...")
    os.makedirs(output_csv_folder, exist_ok=True)
    engine = create_engine(
        f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}/{db_config['database']}?charset={db_config['charset']}"
    )
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result.fetchall()]

    for table in tables:
        df = pd.read_sql_table(table, engine)
        csv_path = os.path.join(output_csv_folder, f"{table}.csv")
        df.to_csv(csv_path, index=False)
        print(f"Table '{table}' exportée en CSV : {csv_path}")

    print("✅ Toutes les tables exportées.")
    
# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    import_matches_from_excel(matchs_excel, saison_id)
    import_pronos_from_excel(pronos_excel, saison_id)
    import_bonus_from_excel(bonus_excel)
    export_tables_to_csv(output_csv_folder)
    print("\n🎉 Toutes les opérations sont terminées !")