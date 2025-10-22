import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from graphviz import Digraph
import unicodedata

def normalize_str(s):
    """Supprime accents, met en minuscule et retire espaces."""
    if pd.isna(s):
        return ''
    s = str(s)
    s = ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )

def draw_bracket(df_phase):
    """
    Bracket horizontal pour phases à élimination directe
    """
    # Ordre des phases
    phases_order = ["Seizieme", "Huitieme", "Quart", "Demie", "Finale"]
    
    # X positions pour chaque phase
    x_positions = {phase: i*2 for i, phase in enumerate(phases_order)}
    y_offsets = {}  # pour empiler les matchs
    
    # Créer les nodes
    nodes = []
    edges = []
    node_id = 0
    match_to_node = {}
    
    for phase in phases_order:
        df_p = df_phase[df_phase['phase']==phase]
        if df_p.empty:
            continue
        
        matchs = df_p.groupby("match_id")
        y_base = 0
        for match_id, g in matchs:
            # Gestion match aller/retour
            aller = g[g['aller_retour']=="aller"]
            retour = g[g['aller_retour']=="retour"]
            
            if not aller.empty and not retour.empty:
                dom, ext = aller['equipe_domicile_nom'].values[0], aller['equipe_exterieure_nom'].values[0]
                score_dom = aller['score_domicile'].values[0] + retour['score_exterieur'].values[0]
                score_ext = aller['score_exterieure'].values[0] + retour['score_domicile'].values[0]
                vainqueur = dom if score_dom > score_ext else ext
                hover_text = f"Match {dom} vs {ext}<br>Aller: {aller['score_domicile'].values[0]}-{aller['score_exterieur'].values[0]}<br>Retour: {retour['score_domicile'].values[0]}-{retour['score_exterieur'].values[0]}<br>Vainqueur: {vainqueur}"
            else:
                match_finale = g.iloc[0]
                dom, ext = match_finale['equipe_domicile_nom'], match_finale['equipe_exterieure_nom']
                score_dom, score_ext = match_finale['score_domicile'], match_finale['score_exterieur']
                vainqueur = dom if score_dom > score_ext else ext
                hover_text = f"Finale {dom} vs {ext}<br>Score: {score_dom}-{score_ext}<br>Vainqueur: {vainqueur}"
            
            y = y_base
            nodes.append(dict(
                id=node_id,
                x=x_positions[phase],
                y=y,
                label=f"{dom} ({score_dom})\nvs\n{ext} ({score_ext})",
                color='gold' if phase=="Finale" else 'rgba(46,139,87,0.7)',
                hover=hover_text
            ))
            match_to_node[match_id] = node_id
            node_id += 1
            y_base += 2  # espacement vertical
    
    # Création des edges (vainqueurs vers le prochain tour)
    for i, phase in enumerate(phases_order[:-1]):  # pas la finale
        df_curr = df_phase[df_phase['phase']==phase]
        df_next = df_phase[df_phase['phase']==phases_order[i+1]]
        if df_curr.empty or df_next.empty:
            continue
        for match_id_next, g_next in df_next.groupby("match_id"):
            aller_next = g_next[g_next['aller_retour']=="aller"]
            retour_next = g_next[g_next['aller_retour']=="retour"]
            equipes_next = []
            if not aller_next.empty and not retour_next.empty:
                equipes_next = [aller_next['equipe_domicile_nom'].values[0], aller_next['equipe_exterieure_nom'].values[0]]
            elif not g_next.empty:
                equipes_next = [g_next.iloc[0]['equipe_domicile_nom'], g_next.iloc[0]['equipe_exterieure_nom']]
            for m_id, n in match_to_node.items():
                node_label = nodes[n]['label']
                for eq in equipes_next:
                    if eq in node_label:
                        edges.append((n, match_to_node[match_id_next]))
    
    # --- Dessin Plotly ---
    fig = go.Figure()
    # Nodes
    for node in nodes:
        fig.add_trace(go.Scatter(
            x=[node['x']], y=[node['y']],
            mode='markers+text',
            marker=dict(size=80, color=node['color'], line=dict(width=2, color='black')),
            text=[node['label']],
            textposition="middle center",
            hovertext=[node['hover']],
            hoverinfo='text'
        ))
    # Edges
    for e in edges:
        fig.add_trace(go.Scatter(
            x=[nodes[e[0]]['x'], nodes[e[1]]['x']],
            y=[nodes[e[0]]['y'], nodes[e[1]]['y']],
            mode='lines',
            line=dict(color='gray', width=2),
            hoverinfo='none'
        ))
    
    fig.update_layout(
        title="Organigramme des phases à élimination directe",
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",
        font=dict(color="white"),
        height=900,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

def show(tables):
    st.title("🏆 Compétitions Européennes")
    
    # Lire le CSV complet des matchs
    df = tables["all_matchs_football"]  # chemin vers ton CSV

    # Définir les compétitions européennes d'intérêt
    competitions_europe = ['Ligue des Champions', 'Europa League', 'Ligue Conference', 'Ligue Europa']

    # Filtrer le DataFrame pour ne garder que ces compétitions
    df_europe = df[df['competition'].isin(competitions_europe)]

    
    # --- Sélection des saisons disponibles uniquement pour ces compétitions ---
    saisons = sorted(df_europe['saison'].dropna().unique(), reverse=True)
    if len(saisons) == 0:
        st.warning("Aucune saison disponible pour les compétitions européennes.")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        # Sélecteur de saison
        saison_sel = st.selectbox("Sélectionner une saison :", saisons)

        # --- Filtrer le DataFrame pour la saison choisie ---
        df_saison = df_europe[df_europe['saison'] == saison_sel]

    with col2:
        # Sélection des compétitions disponibles pour cette saison
        competitions = sorted(df_saison['competition'].dropna().unique())
        if len(competitions) == 0:
            st.warning("Aucune compétition européenne disponible pour cette saison.")
            return

        # Définir la compétition par défaut
        default_index = competitions.index("Ligue des Champions") if "Ligue des Champions" in competitions else 0
        competition_sel = st.selectbox("Sélectionner une compétition :", competitions, index=default_index)

        # --- Filtrer le DataFrame final pour la compétition choisie ---
        df = df_saison[df_saison['competition'] == competition_sel]
        if df.empty:
            st.info("Aucun match enregistré pour cette compétition et cette saison.")
            return

    # --- Onglets ---
    tabs = st.tabs(["Groupes", "Élimination directe"])

    # --- Onglet Groupes ---
    with tabs[0]:
        groupes = df['groupe'].dropna().unique()
        
        if int(saison_sel.split("-")[0]) >= 2024:
            st.subheader("Phase de Ligue unique")

            # Filtrer les matchs pour la phase "Ligue" ou prendre tous si pas défini
            df_groupe = df[df['phase'].str.contains("Ligue", case=False, na=False)].copy()
            if df_groupe.empty:
                df_groupe = df.copy()

            # --- Calcul du classement général ---
            equipes = pd.unique(df_groupe[['equipe_domicile_nom','equipe_exterieure_nom']].values.ravel('K'))
            classement = pd.DataFrame(index=equipes, columns=['Pts','J','V','N','D','BP','BC','Diff'])
            classement.fillna(0, inplace=True)

            # --- Calcul du classement évolutif par journée ---
            journees = sorted(df_groupe['journee'].dropna().unique())

            # DataFrame pour stocker le classement cumulatif par journée
            classement_par_journee = pd.DataFrame()
            rang_precedent = {}

            for j in journees:
                df_j = df_groupe[df_groupe['journee'] <= j].copy()
                equipes = pd.unique(df_j[['equipe_domicile_nom','equipe_exterieure_nom']].values.ravel('K'))
                classement = pd.DataFrame(index=equipes, columns=['Pts','J','V','N','D','BP','BC','Diff'])
                classement.fillna(0, inplace=True)

                # Calcul des stats cumulées jusqu'à la journée j
                for _, match in df_j.iterrows():
                    dom = match['equipe_domicile_nom']
                    ext = match['equipe_exterieure_nom']
                    score_dom = match['score_domicile']
                    score_ext = match['score_exterieur']
                    if pd.isna(score_dom) or pd.isna(score_ext):
                        continue

                    classement.at[dom,'J'] += 1
                    classement.at[ext,'J'] += 1
                    classement.at[dom,'BP'] += score_dom
                    classement.at[dom,'BC'] += score_ext
                    classement.at[ext,'BP'] += score_ext
                    classement.at[ext,'BC'] += score_dom

                    if score_dom > score_ext:
                        classement.at[dom,'V'] += 1
                        classement.at[dom,'Pts'] += 3
                        classement.at[ext,'D'] += 1
                    elif score_dom < score_ext:
                        classement.at[ext,'V'] += 1
                        classement.at[ext,'Pts'] += 3
                        classement.at[dom,'D'] += 1
                    else:
                        classement.at[dom,'N'] += 1
                        classement.at[ext,'N'] += 1
                        classement.at[dom,'Pts'] += 1
                        classement.at[ext,'Pts'] += 1

                    classement.at[dom,'Diff'] = classement.at[dom,'BP'] - classement.at[dom,'BC']
                    classement.at[ext,'Diff'] = classement.at[ext,'BP'] - classement.at[ext,'BC']

                classement = classement.sort_values(by=['Pts','Diff','BP'], ascending=[False,False,False])
                classement.reset_index(inplace=True)
                classement.rename(columns={'index':'Equipe'}, inplace=True)
                classement.insert(0, 'Rang', range(1, len(classement)+1))

                # Calcul de l'évolution avec nombre de places
                evolution = []
                for _, row in classement.iterrows():
                    equipe = row['Equipe']
                    rang_actuel = row['Rang']
                    if equipe in rang_precedent:
                        diff = rang_precedent[equipe] - rang_actuel
                        if diff > 0:
                            evolution.append(f'▲{diff}')
                        elif diff < 0:
                            evolution.append(f'▼{abs(diff)}')
                        else:
                            evolution.append('—')
                    else:
                        evolution.append('—')  # première journée
                    rang_precedent[equipe] = rang_actuel
                classement['Évolution'] = evolution

                classement['Journée'] = j
                classement_par_journee = pd.concat([classement_par_journee, classement], ignore_index=True)

            # --- Sélecteur de journée ---
            journee_sel = st.selectbox("Sélectionner une journée :", journees, index=len(journees)-1)
            df_journee_sel = df_groupe[df_groupe['journee'] == journee_sel].copy()
            df_classement_sel = classement_par_journee[classement_par_journee['Journée'] == journee_sel].copy()

            # --- Colonnes pour affichage ---
            col1, col2 = st.columns([3, 1.5])

            with col1:
                st.markdown(f"**Classement – Journée {journee_sel}**")
                styled_classement = (
                    df_classement_sel[['Rang','Évolution','Equipe','Pts','J','V','N','D','BP','BC','Diff']]
                    .style
                    .format({'Pts':'{:.0f}', 'Diff':'{:+d}'})
                    .background_gradient(subset=['Pts'], cmap='Greens')
                    .background_gradient(subset=['Diff'], cmap='RdYlGn')
                    .applymap(
                        lambda v: 'color: green;' if isinstance(v, str) and v.startswith('▲') 
                                else ('color: red;' if isinstance(v, str) and v.startswith('▼') else ''),
                        subset=['Évolution']
                    )
                    .set_properties(**{
                        'text-align': 'center',
                        'justify-content': 'center',
                        'white-space': 'nowrap',
                        'font-size': '14px',
                        'padding': '4px 8px'
                    })
                    .set_properties(subset=['Equipe'], **{'text-align': 'left', 'font-weight':'bold'})
                )

                st.dataframe(styled_classement, use_container_width=True, height=36*len(df_classement_sel), hide_index=True)

            with col2:
                st.markdown(f"**Résultats – Journée {journee_sel}**")
                if not df_journee_sel.empty:
                    df_resultats = df_journee_sel[['equipe_domicile_nom','score_domicile','score_exterieur','equipe_exterieure_nom']].copy()
                    df_resultats['Score'] = df_resultats.apply(
                        lambda row: (str(int(row['score_domicile'])) if pd.notna(row['score_domicile']) else '-') 
                                    + '-' + 
                                    (str(int(row['score_exterieur'])) if pd.notna(row['score_exterieur']) else '-'),
                        axis=1
                    )
                    df_resultats.rename(columns={
                        'equipe_domicile_nom': 'Domicile',
                        'equipe_exterieure_nom': 'Extérieur'
                    }, inplace=True)
                    df_resultats = df_resultats[['Domicile','Score','Extérieur']]

                    # Coloration et centrage
                    def color_score_row(row):
                        try:
                            d, e = row['Score'].split('-')
                            d = int(d) if d != '-' else None
                            e = int(e) if e != '-' else None
                        except:
                            d, e = None, None
                        styles = []
                        styles.append('background-color: #089173FF; font-weight: bold;' if d is not None and e is not None and d > e else '')
                        styles.append('text-align: center; font-weight: bold;' if d is not None and e is not None else 'text-align: center;')
                        styles.append('background-color: #089173FF; font-weight: bold;' if d is not None and e is not None and e > d else '')
                        return styles

                    styled_resultats = (
                        df_resultats.style
                        .apply(color_score_row, axis=1)
                        .set_properties(**{
                            'text-align': 'center',
                            'justify-content': 'center',
                            'white-space': 'nowrap',
                            'font-size': '13px',
                            'padding': '4px 6px'
                        })
                    )
                    st.dataframe(styled_resultats, use_container_width=True, height=37*len(df_resultats), hide_index=True)
                else:
                    st.info("Aucun match enregistré pour cette journée.")

        for g in groupes:
            st.subheader(f"Groupe {g}")
            df_groupe = df[df['groupe']==g].copy()

            # Calculer le classement du groupe
            equipes = pd.unique(df_groupe[['equipe_domicile_nom','equipe_exterieure_nom']].values.ravel('K'))
            classement = pd.DataFrame(index=equipes, columns=['Pts','J','V','N','D','BP','BC','Diff'])
            classement.fillna(0, inplace=True)

            for _, match in df_groupe.iterrows():
                dom = match['equipe_domicile_nom']
                ext = match['equipe_exterieure_nom']
                score_dom = match['score_domicile']
                score_ext = match['score_exterieur']
                if pd.isna(score_dom) or pd.isna(score_ext):
                    continue
                # Matches joués
                classement.at[dom,'J'] += 1
                classement.at[ext,'J'] += 1
                # Buts
                classement.at[dom,'BP'] += score_dom
                classement.at[dom,'BC'] += score_ext
                classement.at[ext,'BP'] += score_ext
                classement.at[ext,'BC'] += score_dom
                # Résultats
                if score_dom > score_ext:
                    classement.at[dom,'V'] += 1
                    classement.at[dom,'Pts'] += 3
                    classement.at[ext,'D'] += 1
                elif score_dom < score_ext:
                    classement.at[ext,'V'] += 1
                    classement.at[ext,'Pts'] += 3
                    classement.at[dom,'D'] += 1
                else:
                    classement.at[dom,'N'] += 1
                    classement.at[ext,'N'] += 1
                    classement.at[dom,'Pts'] += 1
                    classement.at[ext,'Pts'] += 1
                # Différence de buts
                classement.at[dom,'Diff'] = classement.at[dom,'BP'] - classement.at[dom,'BC']
                classement.at[ext,'Diff'] = classement.at[ext,'BP'] - classement.at[ext,'BC']

            # Trier le classement
            classement = classement.sort_values(by=['Pts','Diff','BP'], ascending=[False,False,False])
            classement.reset_index(inplace=True)
            classement.rename(columns={'index':'Equipe'}, inplace=True)
            classement.insert(0, 'Rang', range(1, len(classement)+1))

            # Construire la matrice des matchs complète avec aller-retour
            matrice = pd.DataFrame(index=equipes, columns=equipes)

            for _, match in df_groupe.iterrows():
                dom = match['equipe_domicile_nom']
                ext = match['equipe_exterieure_nom']
                score_dom = match['score_domicile']
                score_ext = match['score_exterieur']

                if pd.isna(score_dom) or pd.isna(score_ext):
                    matrice.at[dom, ext] = ''
                    matrice.at[ext, dom] = ''
                else:
                    # 🔹 Conversion en entier
                    score_dom = int(score_dom)
                    score_ext = int(score_ext)

                    # Initialiser si vide
                    if matrice.at[dom, ext] is None or matrice.at[dom, ext] == '' or pd.isna(matrice.at[dom, ext]):
                        matrice.at[dom, ext] = f"{score_dom}-{score_ext}"
                        matrice.at[ext, dom] = f"{score_ext}-{score_dom}"
                    else:
                        matrice.at[dom, ext] += f" / {score_dom}-{score_ext}"
                        matrice.at[ext, dom] += f" / {score_ext}-{score_dom}"


            # Fonction de coloration
            def color_match(val):
                if val == '':
                    return ''
                try:
                    dom, ext = map(int, val.split('-'))
                    if dom > ext:
                        return 'background-color: #A8ABD5FF;'  # vert
                    elif dom < ext:
                        return 'background-color: #f7a8a8;'  # rouge
                    else:
                        return 'background-color: #f9f49c;'  # jaune
                except:
                    return ''

            col1, col2 = st.columns([1.5, 1.5])

            with col1:
                # Tableau classement
                styled_classement = (
                    classement[['Rang','Equipe','Pts','J','V','N','D','BP','BC','Diff']]
                    .style.format({'Pts':'{:.0f}', 'Diff':'{:+d}'})
                    .background_gradient(subset=['Pts'], cmap='Greens')
                    .background_gradient(subset=['Diff'], cmap='RdYlGn')
                    .set_properties(**{
                        'text-align': 'center',
                        'justify-content': 'center',
                        'white-space': 'nowrap',
                        'font-size': '14px',
                        'padding': '4px 8px'
                    })
                    .set_properties(subset=['Equipe'], **{'text-align': 'left'})  # 👈 lisibilité améliorée pour les noms d'équipes
                )   

                st.dataframe(
                    styled_classement,
                    use_container_width=False,  # ✅ permet d’ajuster la largeur au texte
                    height=45 * len(classement),
                    hide_index=True
                )
                    
            with col2:
                st.markdown("**Résultats entre équipes (aller / retour)**")
                    
                # Style de la matrice : couleurs + alignement
                styled_matrice = (
                    matrice.style
                    .applymap(color_match)
                    .set_properties(**{
                        'text-align': 'center',
                        'justify-content': 'center',
                        'white-space': 'nowrap',
                        'font-size': '13px',
                        'padding': '4px 6px'
                    })
                )

                st.dataframe(
                    styled_matrice,
                    use_container_width=False,  # ✅ largeur adaptée au contenu
                    height=45 * len(equipes)
                )

    with tabs[1]:
        phases = ["Seizièmes", "Huitièmes", "Quarts", "Demies", "Finale"]

        hauteur_phase = {
            "Seizièmes": 600,
            "Huitièmes": 320,
            "Quarts": 180,
            "Demies": 110,
            "Finale": 80
        }

        # Couleurs
        win_color = "#07bb4f"
        header_color = "#f0f2f6"
        finale_color = "#FFD700"

        # Normaliser aller/retour
        df['aller_retour'] = df['aller_retour'].astype(str).str.strip().str.capitalize()

        # Créer une clé pour associer Aller et Retour
        df['match_pair'] = df.apply(lambda x: '-'.join(sorted([x['equipe_domicile_nom'], x['equipe_exterieure_nom']])), axis=1)

        def color_score(val, col):
            if val == "" or '-' not in val:
                return ""
            try:
                d_str, e_str = val.split('-')
                d = int(float(d_str))
                e = int(float(e_str))
            except:
                return ""
            if d > e and col == 'Domicile':
                return f'background-color: {win_color}; font-weight: bold;'
            elif e > d and col == 'Extérieur':
                return f'background-color: {win_color}; font-weight: bold;'
            return ''

        for phase in phases:
            df_phase = df[df['phase'] == phase]
            if df_phase.empty:
                continue

            st.markdown(f"## {phase}")

            if phase != "Finale":
                rows_aller, rows_retour, qualifiés = [], [], []

                for match_pair, g in df_phase.groupby('match_pair'):
                    df_aller = g[g['aller_retour'] == "Aller"]
                    df_retour = g[g['aller_retour'] == "Retour"]

                    if df_aller.empty or df_retour.empty:
                        continue

                    match_aller = df_aller.iloc[0]
                    match_retour = df_retour.iloc[0]

                    dom = match_aller['equipe_domicile_nom']
                    ext = match_aller['equipe_exterieure_nom']

                    # --- Fonction pour sécuriser les NaN ---
                    def safe_int(val):
                        return int(val) if pd.notna(val) else 0

                    # Scores Aller et Retour
                    score_dom_aller = safe_int(match_aller['score_domicile'])
                    score_ext_aller = safe_int(match_aller['score_exterieur'])
                    score_dom_retour = safe_int(match_retour['score_domicile'])
                    score_ext_retour = safe_int(match_retour['score_exterieur'])

                    # Score Aller affichage
                    score_aller = f"{score_dom_aller}-{score_ext_aller}"
                    if pd.notna(match_aller.get('prolongation_score_domicile')):
                        score_aller += f" (Prol: {safe_int(match_aller['prolongation_score_domicile'])}-{safe_int(match_aller['prolongation_score_exterieur'])})"
                    if pd.notna(match_aller.get('tab_score_domicile')):
                        score_aller += f" (TAB: {safe_int(match_aller['tab_score_domicile'])}-{safe_int(match_aller['tab_score_exterieur'])})"

                    # Score Retour affichage
                    score_retour = f"{score_dom_retour}-{score_ext_retour}"
                    if pd.notna(match_retour.get('prolongation_score_domicile')):
                        score_retour += f" (Prol: {safe_int(match_retour['prolongation_score_domicile'])}-{safe_int(match_retour['prolongation_score_exterieur'])})"
                    if pd.notna(match_retour.get('tab_score_domicile')):
                        score_retour += f" (TAB: {safe_int(match_retour['tab_score_domicile'])}-{safe_int(match_retour['tab_score_exterieur'])})"

                    # Ajouter aux tableaux
                    rows_aller.append({"Domicile": dom, "Score": score_aller, "Extérieur": ext})
                    rows_retour.append({"Domicile": match_retour['equipe_domicile_nom'], "Score": score_retour, "Extérieur": match_retour['equipe_exterieure_nom']})

                    # Calcul du vainqueur cumulatif
                    total_dom = score_dom_aller + score_ext_retour + safe_int(match_aller.get('prolongation_score_domicile')) + safe_int(match_retour.get('prolongation_score_exterieur'))
                    total_ext = score_ext_aller + score_dom_retour + safe_int(match_aller.get('prolongation_score_exterieur')) + safe_int(match_retour.get('prolongation_score_domicile'))

                    if total_dom > total_ext:
                        qualifiés.append(dom)
                    elif total_ext > total_dom:
                        qualifiés.append(ext)
                    else:
                        # Egalité après prolongation, vérifier TAB
                        tab_dom = safe_int(match_aller.get('tab_score_domicile')) + safe_int(match_retour.get('tab_score_domicile'))
                        tab_ext = safe_int(match_aller.get('tab_score_exterieur')) + safe_int(match_retour.get('tab_score_exterieur'))
                        if tab_dom > tab_ext:
                            qualifiés.append(dom)
                        else:
                            qualifiés.append(ext)

                # Affichage DataFrames
                df_aller_disp = pd.DataFrame(rows_aller)
                df_retour_disp = pd.DataFrame(rows_retour)

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### Matchs Aller")
                    st.dataframe(
                        df_aller_disp.style.apply(lambda x: [color_score(x['Score'], c) for c in x.index], axis=1)
                        .set_properties(**{'text-align': 'center', 'font-size': '14px', 'padding': '6px 8px'}),
                        use_container_width=True,
                        height=hauteur_phase.get(phase),
                        hide_index=True
                    )
                with col2:
                    st.markdown("### Matchs Retour")
                    st.dataframe(
                        df_retour_disp.style.apply(lambda x: [color_score(x['Score'], c) for c in x.index], axis=1)
                        .set_properties(**{'text-align': 'center', 'font-size': '14px', 'padding': '6px 8px'}),
                        use_container_width=True,
                        height=hauteur_phase.get(phase),
                        hide_index=True
                    )

                # Affichage des qualifiés en badges
                colors = ["#a8d5ba", "#8fc1a9", "#76b39b", "#5da78d"]
                qualifies_html = " ".join([
                    f"<span style='display:inline-block;background-color:{colors[i%len(colors)]};color:#000;padding:4px 10px;border-radius:12px;margin:2px;font-weight:bold'>{team}</span>"
                    for i, team in enumerate(qualifiés)
                ])
                st.markdown(f"<h4>Équipes qualifiées pour la phase suivante :</h4>{qualifies_html}", unsafe_allow_html=True)

            else:
                # Finale
                match_finale = df_phase.iloc[0]
                dom = match_finale['equipe_domicile_nom']
                ext = match_finale['equipe_exterieure_nom']

                # Scores sécurisés
                score_dom = safe_int(match_finale['score_domicile'])
                score_ext = safe_int(match_finale['score_exterieur'])
                prol_dom = safe_int(match_finale.get('prolongation_score_domicile'))
                prol_ext = safe_int(match_finale.get('prolongation_score_exterieur'))
                tab_dom = safe_int(match_finale.get('tab_score_domicile'))
                tab_ext = safe_int(match_finale.get('tab_score_exterieur'))

                total_dom = score_dom + prol_dom
                total_ext = score_ext + prol_ext

                if total_dom > total_ext:
                    vainqueur = dom
                elif total_ext > total_dom:
                    vainqueur = ext
                else:
                    vainqueur = dom if tab_dom > tab_ext else ext

                score = f"{score_dom}-{score_ext}"
                if prol_dom or prol_ext:
                    score += f" (Prol: {prol_dom}-{prol_ext})"
                if tab_dom or tab_ext:
                    score += f" (TAB: {tab_dom}-{tab_ext})"

                df_finale_disp = pd.DataFrame([{"Domicile": dom, "Score": score, "Extérieur": ext}])
                st.markdown("### Finale")
                st.dataframe(
                    df_finale_disp.style.apply(lambda x: [color_score(x['Score'], c) for c in x.index], axis=1)
                    .set_properties(**{'text-align': 'center', 'font-size': '14px', 'padding': '6px 8px'}),
                    use_container_width=True,
                    height=hauteur_phase.get(phase),
                    hide_index=True
                )

                # Badge doré pour le vainqueur
                st.markdown(
                    f"<span style='display:inline-block;background-color:{finale_color};color:#000;padding:6px 12px;border-radius:12px;font-weight:bold;font-size:16px'>🏆 {vainqueur}</span>",
                    unsafe_allow_html=True
                )
