"""Identité et paramètres du projet — source unique de vérité.

Modifier ce fichier suffit pour changer un nom, une couleur ou un chemin
dans tous les livrables générés (figures, application, rapport, slides).
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Identité
# --------------------------------------------------------------------------
NOM_PROJET = "VIGIE"
SOUS_TITRE = "Analyse et prédiction du churn client"
SIGNATURE = "Voir le churn venir, agir avant la clôture."

ECOLE = "ESPRIT School of Business"
PROGRAMME = "Licence 3 — Business Computing BI"
MODULE = "Projet Intégré"
GROUPE = "Groupe BI 5"
ANNEE = "2026"

EQUIPE = [
    {"nom": "Raed Meddeb", "role": "Chef de projet · Machine Learning & application web"},
    {"nom": "Salsabil Ben Elhadj", "role": "Data Warehouse & ETL (Talend, PostgreSQL)"},
    {"nom": "Salah Chebbi", "role": "Séries temporelles & Deep Learning (LSTM)"},
    {"nom": "Ines Ayed", "role": "Reporting Power BI, DAX & qualité des données"},
]
TUTEURS = ["Aymen Ben Brik", "Hela Hammami"]

# --------------------------------------------------------------------------
# Charte graphique (reprise dans Power BI, Streamlit, rapport et slides)
# --------------------------------------------------------------------------
COULEURS = {
    "encre": "#14213D",      # titres, axes, texte fort
    "churn": "#D62839",      # tout ce qui désigne le churn / le risque
    "retention": "#2A9D8F",  # tout ce qui désigne les clients conservés
    "ambre": "#F4A261",      # alerte intermédiaire, mise en avant
    "ciel": "#457B9D",       # séries secondaires
    "brume": "#E9ECEF",      # grilles, fonds de cartes
    "papier": "#FAFAF7",     # fond de page
    "texte": "#1F2937",
    "gris": "#6B7280",
}
PALETTE = [
    COULEURS["encre"], COULEURS["churn"], COULEURS["retention"],
    COULEURS["ambre"], COULEURS["ciel"], COULEURS["gris"],
]

# --------------------------------------------------------------------------
# Chemins
# --------------------------------------------------------------------------
RACINE = Path(__file__).resolve().parents[1]

# Les données ne sont JAMAIS dans le dépôt. Par défaut on les lit dans data/
# (ignoré par git) ; la variable VIGIE_DATA_DIR permet de pointer ailleurs.
DOSSIER_DONNEES = Path(os.environ.get("VIGIE_DATA_DIR", RACINE / "data"))

FIGURES = RACINE / "06_rapport" / "figures"
RESULTATS_ML = RACINE / "04_machine_learning" / "resultats"
MODELES = RACINE / "04_machine_learning" / "models"      # hors dépôt (.gitignore)
ARTEFACTS_APP = RACINE / "05_web_app" / "artifacts"      # agrégats + paramètres

# --------------------------------------------------------------------------
# Règles métier partagées
# --------------------------------------------------------------------------
GRAINE = 42                 # reproductibilité (découpages, modèles)
SEUIL_PETIT_EFFECTIF = 20   # aucun agrégat publié en dessous de cet effectif
PART_MASSE = 0.50           # opérations de masse : semaines cumulant 50 % des clôtures
