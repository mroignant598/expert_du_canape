import streamlit as st
import pandas as pd
import os
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
import Fonctions

# =======================
# Fonction principale
# =======================
def show(tables):
    # Charger Font Awesome dans Streamlit
    st.markdown("""
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" 
            integrity="sha512-K..." crossorigin="anonymous" referrerpolicy="no-referrer" />
    """, unsafe_allow_html=True)
    st.markdown("---")
    col_consigne, col_calendrier = st.columns([3,1], gap="large")
    with col_consigne:
        st.markdown("## 🛋️ Bienvenue sur **Expert du Canapé - Saison 2026-2027** !")
        st.markdown("""
        **_Pour une meilleure expérience, je te conseille de passer l'application en mode sombre. Tu as 3 points verticaux en haut à droite, clique dessus et passe l'application en mode dark !_** 
        
        Prêt à montrer qui est le véritable boss du terrain ? 😏⚽
        
        Voici comment fonctionne l’application : c’est très simple. Clique sur le rectangle vert « Les Experts du canapé » pour accéder à une première page regroupant les résultats de tous les participants.
        
        Ensuite, rends-toi dans l’onglet « Insertion Pronos » pour saisir tes pronostics. Pour la première journée, commence par entrer un pseudo, puis complète les scores dans le tableau en dessous et valide en cliquant sur « Soumettre mes pronostics ».
        Attend d'avoir le message de validation avant de fermer la page 😏
        
        Pour les journées suivantes, il te suffira simplement de sélectionner ton pseudo dans la liste déroulante.
        
        
        **🧮 Calcul des points** : Les points attribués à chaque match sont calculés à partir des cotes réelles, auxquelles s’applique un multiplicateur en fonction de tes pronostics.
        Ce multiplicateur dépend de la précision de tes choix : bon score exact, bon vainqueur, bon écart et match prolifique (4 buts et plus). Attention, ici, un match dure 90 min ! Si il y a des prolongations, elles ne sont pas prises en compte dans les calculs.
        
        
        """)
        #Les fichiers Excel, c’était bien… mais avoir **toutes nos données au même endroit**, c’est encore mieux ! 📊  
        #Ici, tu retrouveras **nos pronos depuis le début**, des **stats aux petits oignons**, et même les **classements des championnats** (mis à jour régulièrement). 🔥  
        
    with col_calendrier:
        st.markdown("## 📆 **Calendrier** ")
        st.markdown("""
        - Reprise de la Ligue 1 : 21 aout
        - Reprise de la Ligue 2 : 8 aout
        - Reprise de la Ligue 3 : 7 aout
        - Reprise de la Ligue des champions : 8 septembre
        - Reprise de la Ligue Europa : 16 septembre
        - Reprise de la Ligue Europa Conference : 15 octobre
        """)        

    st.markdown("---")

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

    col_kpi_matchs, col_kpi_pronos, col_kpi_participants, col_kpi_archives = st.columns(4, gap="large")
    with col_kpi_matchs: Fonctions.kpi_card_accueil("🏟️ Matchs enregistrés", f"{nb_matchs:,}".replace(",", " "), "#3b82f6")
    with col_kpi_pronos: Fonctions.kpi_card_accueil("📋 Pronostics saisis", f"{nb_pronos:,}".replace(",", " "), "#22c55e")
    with col_kpi_participants: Fonctions.kpi_card_accueil("👥 Participants inscrits", f"{nb_participants:,}".replace(",", " "), "#f59e0b")
    with col_kpi_archives: Fonctions.kpi_card_accueil("🏆 Matchs archivés", f"{nb_archives:,}".replace(",", " "), "#9333ea")

    st.markdown('')
    st.markdown("""
    - 🏟️ **Matchs enregistrés** : nombre total de matchs pronostiqués depuis le début des pronos (saison 2015-2016).  
    - 📋 **Pronostics saisis** : nombre total de pronos insérés dans la base de données.  
    - 👥 **Participants inscrits** : nombre de joueurs ayant participé aux pronos.  
    - 🏆 **Matchs archivés** : de 1888 à nos jours, des débuts des championnats à aujourd’hui - une grande majorité des matchs joués depuis plus d’un siècle !  
    """)
    st.markdown("---")

    # =======================
    # KPI PAR SAISON
    # =======================
    col_stats_saison, col_noms_participants = st.columns(2)
    with col_stats_saison:
        st.subheader("📆 Statistiques par saison")

        if "saison" not in df_matchs.columns:
            st.error("❌ La colonne 'saison' est manquante dans all_matchs_football.csv.")
            return
        
        saisons = sorted(df_matchs["saison"].dropna().unique(), reverse=True)

        if not saisons:
            st.info("Aucune saison trouvée dans les fichiers CSV.")
            return
        
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
    
    with col_noms_participants:
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
            couleurs = [ "#ef4444", "#f97316", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6", "#84cc16", "#0ea5e9"]

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
    
    st.text('')
    col_kpi_nb_matchs, col_kpi_nb_pronos, col_kpi_nb_participants = st.columns(3)
    with col_kpi_nb_matchs: Fonctions.kpi_card_accueil(f"🏟️ Nombre de matchs", f"{nb_matchs_saison:,}".replace(",", " "), "#3b82f6")
    with col_kpi_nb_pronos: Fonctions.kpi_card_accueil(f"📋 Nombre de pronostics", f"{nb_pronos_saison:,}".replace(",", " "), "#22c55e")
    with col_kpi_nb_participants: Fonctions.kpi_card_accueil(f"👥 Nombre de participants", f"{nb_participants_saison:,}".replace(",", " "), "#f59e0b")

    st.markdown("<hr style='border:1px solid #444444; margin: 2rem 0;'>", unsafe_allow_html=True)


    col_historique, col_news = st.columns(2)
    with col_historique:
        st.markdown("### 🧮 Historique du calcul des points")

        st.markdown("""
        **2015-2016** et **2016-2017** : Un bon prono valait **1 point**, un bon score **3 points**, et un mauvais prono **-1 point**.  
        **2018-2019** : Introduction du système de points basé sur les **côtes des matchs**.  
        **2022-2023** : Ajout du **bonus pronostiqueur**.  
        """)


    with col_news:
        st.markdown("### 🚀 Prochainement sur **Expert du Canapé** ...")

        # Afficher la liste avec icône FA
        st.markdown("""
            - 🔹 **Ajout des bonus** sur les différentes saisons  <i class="fa-regular fa-circle-check" style="color:green;"></i>
            - 🏆 Accès aux **archives de la Ligue des Champions**   
            - 🌍 Accès aux **matchs internationaux**  
            - ✍️ **Insertion directe des pronos** sur l’appli  <i class="fa-regular fa-circle-check" style="color:green;"></i>
        """, unsafe_allow_html=True)
        
    # =======================
    # Aperçu du fichier matchs
    # =======================
    #st.subheader("📋 Aperçu des matchs")
    #st.dataframe(df_matchs.sample(10), use_container_width=True, hide_index=True)
