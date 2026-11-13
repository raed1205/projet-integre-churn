"""Génère les schémas du projet aux couleurs VIGIE (aucune donnée n'est lue).

    python outils/diagrammes.py

Produit :
    02_data_warehouse/schema/star_schema.png   modèle en étoile
    01_etl/schema_flux.png                     flux ETL de bout en bout
    06_rapport/figures/architecture.png        architecture de la solution
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from vigie import config, style  # noqa: E402

C = config.COULEURS
HAUTEUR_LIGNE = 0.27
HAUTEUR_TITRE = 0.42


def table(ax, x, y, largeur, titre, colonnes, couleur, sous_titre=None):
    """Dessine une table (titre + colonnes). (x, y) = coin haut-gauche. Renvoie sa boîte."""
    h = HAUTEUR_TITRE + HAUTEUR_LIGNE * len(colonnes) + 0.12
    ax.add_patch(FancyBboxPatch((x, y - h), largeur, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc="white", ec=couleur, lw=1.6, zorder=2))
    ax.add_patch(FancyBboxPatch((x, y - HAUTEUR_TITRE), largeur, HAUTEUR_TITRE,
                                boxstyle="round,pad=0.02,rounding_size=0.08", fc=couleur, ec=couleur, lw=1.6, zorder=3))
    ax.text(x + largeur / 2, y - HAUTEUR_TITRE / 2, titre, ha="center", va="center", color="white",
            fontweight="bold", fontsize=9.5, zorder=4)
    for i, col in enumerate(colonnes):
        cle = col.startswith(("PK ", "FK "))
        ax.text(x + 0.12, y - HAUTEUR_TITRE - 0.06 - HAUTEUR_LIGNE * (i + 0.5), col, ha="left", va="center",
                fontsize=7.6, color=C["encre"] if cle else C["texte"], fontweight="bold" if cle else "normal",
                family="DejaVu Sans Mono", zorder=4)
    if sous_titre:
        ax.text(x + largeur / 2, y - h - 0.14, sous_titre, ha="center", va="top", fontsize=7.4, color=C["gris"],
                style="italic")
    return (x, y - h, largeur, h)


def lien(ax, a, b, couleur=None):
    """Trait entre les centres de deux boîtes, arrêté à leurs bords."""
    ax_, ay = a[0] + a[2] / 2, a[1] + a[3] / 2
    bx, by = b[0] + b[2] / 2, b[1] + b[3] / 2
    ax.add_patch(FancyArrowPatch((ax_, ay), (bx, by), arrowstyle="-", lw=1.3, color=couleur or C["gris"],
                                 zorder=1, shrinkA=0, shrinkB=0))


def schema_etoile():
    style.appliquer()
    fig, ax = plt.subplots(figsize=(15, 10.2))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 10.2)
    ax.axis("off")

    fait = table(ax, 5.55, 7.75, 3.9, "fait_compte", [
        "PK compte_id", "   code_compte", "FK client_id", "FK agence_id", "FK secteur_id", "FK categorie_id",
        "FK devise_id", "FK motif_id", "FK produit_id", "FK date_ouverture_id", "FK date_cloture_id",
        "   est_clos            (cible)", "   solde · est_debiteur", "   montant_produit · taux_fixe",
        "   anciennete_compte_jours", "   ouverture_apres_cloture", "   statut_produit", "   nb_lignes_source",
    ], C["churn"], "Grain : 1 ligne = 1 compte · 410 309 lignes")

    dims = [
        table(ax, 0.35, 9.75, 3.7, "dim_client", [
            "PK client_id", "   code_client", "   zone_nationalite · zone_residence", "   statut_marital",
            "   age · tranche_age", "   nature_client · segment", "   ligne_metier",
            "   anciennete_annees · tranche", "   revenu_declare · nb_comptes", "   score_kyc · dossier_complet",
            "   dates de revue · revue_en_retard", "   est_churn"], C["encre"], "363 024 clients"),
        table(ax, 0.35, 4.55, 3.7, "dim_date", [
            "PK date_id (AAAAMMJJ)", "   date_complete", "   annee · trimestre · mois", "   nom_mois · annee_mois",
            "   semaine_iso · lundi_semaine", "   jour_semaine · nom_jour"], C["encre"],
            "Calendrier construit (1978–2031)\njoue 2 rôles : ouverture et clôture"),
        table(ax, 0.35, 1.45, 3.7, "dim_agence", [
            "PK agence_id", "   code_groupe · libelle", "   est_masque"], C["encre"], None),
        table(ax, 10.95, 9.75, 3.7, "dim_categorie_compte", [
            "PK categorie_id", "   code_categorie · libelle", "   famille"], C["encre"],
            "ACCOUNT_CATEGORY.xlsx"),
        table(ax, 10.95, 7.6, 3.7, "dim_produit", [
            "PK produit_id", "   groupe_produit", "   ligne_produit"], C["encre"], None),
        table(ax, 10.95, 5.6, 3.7, "dim_devise", [
            "PK devise_id", "   code_devise · libelle"], C["encre"], "CURRENCY.xlsx"),
        table(ax, 10.95, 3.75, 3.7, "dim_motif_cloture", [
            "PK motif_id", "   code_motif · libelle"], C["encre"], "CLOSURE_REASON.xlsx"),
        table(ax, 10.95, 1.9, 3.7, "dim_secteur", [
            "PK secteur_id", "   code_secteur · libelle"], C["encre"], "INDUSTRY.xlsx"),
    ]
    for d in dims:
        gauche = d[0] < 5
        depart = (fait[0] if gauche else fait[0] + fait[2], fait[1] + fait[3] / 2 + (d[1] + d[3] / 2 - 5) * 0.55)
        arrivee = (d[0] + d[2] if gauche else d[0], d[1] + d[3] / 2)
        ax.add_patch(FancyArrowPatch(depart, arrivee, arrowstyle="-", lw=1.3, color=C["gris"], zorder=1))
        ax.text(arrivee[0] + (0.12 if gauche else -0.12), arrivee[1] + 0.13, "1", fontsize=8, color=C["gris"],
                ha="left" if gauche else "right")
        ax.text(depart[0] + (-0.12 if gauche else 0.12), depart[1] + 0.13, "n", fontsize=8, color=C["gris"],
                ha="right" if gauche else "left")

    ax.text(0.35, 10.05, "Modèle en étoile de l'entrepôt — schéma dwh", fontsize=15, fontweight="bold",
            color=C["encre"], va="bottom")
    ax.text(14.65, 0.12, f"{config.NOM_PROJET} · {config.GROUPE} · clé 0 de chaque dimension = « Non renseigné »",
            fontsize=8, color=C["gris"], ha="right")
    chemin = RACINE / "02_data_warehouse" / "schema" / "star_schema.png"
    fig.savefig(chemin, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return chemin


def boite(ax, x, y, w, h, titre, lignes, couleur, fond="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1", fc=fond, ec=couleur,
                                lw=1.6, zorder=2))
    ax.text(x + w / 2, y + h - 0.26, titre, ha="center", va="center", fontweight="bold", fontsize=9.5,
            color=couleur if fond == "white" else "white", zorder=3)
    for i, l in enumerate(lignes):
        ax.text(x + w / 2, y + h - 0.6 - 0.27 * i, l, ha="center", va="center", fontsize=7.8,
                color=C["texte"] if fond == "white" else "white", zorder=3)
    return (x, y, w, h)


def fleche(ax, a, b, texte=None, vertical=False):
    if vertical:
        p1, p2 = (a[0] + a[2] / 2, a[1]), (b[0] + b[2] / 2, b[1] + b[3])
    else:
        p1, p2 = (a[0] + a[2], a[1] + a[3] / 2), (b[0], b[1] + b[3] / 2)
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=14, lw=1.6, color=C["encre"], zorder=1))
    if texte:
        ax.text((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + 0.16, texte, ha="center", fontsize=7.5, color=C["gris"])


def schema_flux():
    style.appliquer()
    fig, ax = plt.subplots(figsize=(15, 6.6))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 6.6)
    ax.axis("off")
    ax.text(0.3, 6.25, "Flux ETL — des fichiers source à l'entrepôt", fontsize=15, fontweight="bold", color=C["encre"])

    src = boite(ax, 0.3, 2.2, 2.4, 3.3, "Sources", [
        "data_churn.csv", "483 536 lignes · 32 col.", "", "5 référentiels Excel", "catégorie · motif · devise",
        "secteur · ligne métier"], C["gris"])
    stg = boite(ax, 3.5, 2.2, 2.4, 3.3, "STAGING", [
        "schéma staging", "stg_churn", "stg_* (référentiels)", "", "copie brute, tout en texte",
        "aucune transformation"], C["ciel"])
    trf = boite(ax, 6.7, 2.2, 3.1, 3.3, "TRANSFORMATION", [
        "1. dates AAAAMMJJ → date", "2. doublons exacts écartés", "3. grain compte : 1re clôture",
        "4. grain client : nb comptes, churn", "5. jointure des 5 référentiels", "6. vides → membre « 0 »",
        "7. variables dérivées", "   (âge, ancienneté, revue)", "8. anomalies de dates signalées"], C["ambre"])
    dwh = boite(ax, 10.6, 2.2, 2.0, 3.3, "ENTREPÔT", [
        "schéma dwh", "8 dimensions", "puis fait_compte", "", "410 309 comptes", "363 024 clients"], C["churn"])
    use = boite(ax, 13.2, 2.2, 1.55, 3.3, "Usages", ["Power BI", "(DAX)", "", "Modèles", "ML / LSTM", "App web"],
                C["retention"])
    fleche(ax, src, stg, "Extract")
    fleche(ax, stg, trf, "Transform")
    fleche(ax, trf, dwh, "Load")
    fleche(ax, dwh, use)

    jobs = [
        ("J01_Staging", "tFileInputDelimited\ntFileInputExcel → tDBOutput", 0.3),
        ("J02_Dim_Referentiels", "tDBInput → tMap\n→ tDBOutput (5 dim.)", 3.25),
        ("J03_Dim_Client", "tDBInput → tUniqRow\n→ tMap → tDBOutput", 6.2),
        ("J04_Fait_Compte", "tAggregateRow → tMap\n(8 lookups) → tDBOutput", 9.15),
        ("J05_Controles", "tDBRow (controles.sql)\n→ tLogRow / tDie", 12.1),
    ]
    for nom, detail, x in jobs:
        ax.add_patch(FancyBboxPatch((x, 0.45), 2.65, 1.15, boxstyle="round,pad=0.02,rounding_size=0.1",
                                    fc=C["encre"], ec=C["encre"], zorder=2))
        ax.text(x + 1.325, 1.3, nom, ha="center", va="center", color="white", fontweight="bold", fontsize=9, zorder=3)
        ax.text(x + 1.325, 0.82, detail, ha="center", va="center", color="white", fontsize=7.3, zorder=3)
    for x in [2.95, 5.9, 8.85, 11.8]:
        ax.add_patch(FancyArrowPatch((x, 1.02), (x + 0.3, 1.02), arrowstyle="-|>", mutation_scale=12, lw=1.4,
                                     color=C["encre"]))
    ax.text(0.3, 1.85, "Jobs Talend, enchaînés par J00_Orchestration (tRunJob) — équivalent Python : 01_etl/pipeline_python/etl.py",
            fontsize=8.6, color=C["encre"], fontweight="bold")
    ax.text(14.75, 0.08, f"{config.NOM_PROJET} · {config.GROUPE}", fontsize=8, color=C["gris"], ha="right")
    chemin = RACINE / "01_etl" / "schema_flux.png"
    fig.savefig(chemin, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return chemin


def architecture():
    style.appliquer()
    fig, ax = plt.subplots(figsize=(15, 6.2))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 6.2)
    ax.axis("off")
    ax.text(0.3, 5.85, "Architecture de la solution VIGIE", fontsize=15, fontweight="bold", color=C["encre"])
    etapes = [
        ("1 · Données", ["CSV + 5 Excel", "anonymisés", "", "Python · pandas", "analyse univariée", "manquants · outliers"], C["gris"]),
        ("2 · ETL", ["Talend", "extraction", "nettoyage", "jointures", "", "(+ pipeline Python)"], C["ciel"]),
        ("3 · Entrepôt", ["PostgreSQL", "pgAdmin", "", "modèle en étoile", "1 fait · 8 dimensions", "19 contrôles"], C["encre"]),
        ("4 · Reporting", ["Power BI", "mesures DAX", "", "vue d'ensemble", "analyse du churn", "segmentation"], C["ambre"]),
        ("5 · Prédiction", ["LSTM (Keras)", "clôtures hebdo", "", "XGBoost", "score de churn", "SHAP"], C["churn"]),
        ("6 · Application", ["Streamlit", "", "KPI de synthèse", "prédiction individuelle", "prévision du KPI", "tests · CI"], C["retention"]),
    ]
    boites = []
    for i, (titre, lignes, couleur) in enumerate(etapes):
        boites.append(boite(ax, 0.3 + i * 2.45, 2.2, 2.1, 2.9, titre, lignes, couleur))
    for a, b in zip(boites, boites[1:]):
        fleche(ax, a, b)
    ax.add_patch(FancyBboxPatch((0.3, 0.55), 14.35, 1.05, boxstyle="round,pad=0.02,rounding_size=0.1",
                                fc=C["papier"], ec=C["brume"], lw=1.2))
    ax.text(7.5, 1.28, "Socle transverse", ha="center", fontweight="bold", fontsize=9.5, color=C["encre"])
    ax.text(7.5, 0.86, "Git / GitHub · bibliothèque commune vigie/ (un seul code pour tous les chiffres) · "
                       "aucune donnée dans le dépôt · agrégats et profils fictifs uniquement dans l'application",
            ha="center", fontsize=8.4, color=C["texte"])
    ax.text(14.75, 0.12, f"{config.NOM_PROJET} · {config.GROUPE}", fontsize=8, color=C["gris"], ha="right")
    chemin = config.FIGURES / "architecture.png"
    fig.savefig(chemin, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return chemin


if __name__ == "__main__":
    for f in (schema_etoile, schema_flux, architecture):
        print("écrit :", f().relative_to(RACINE))
