"""Accès aux artefacts de l'application.

L'application ne lit **que** le dossier ``artifacts/`` : des agrégats, des prévisions
hebdomadaires et les paramètres du modèle. Elle ne contient et ne lit aucune ligne client.
"""

from __future__ import annotations

import json
from pathlib import Path

DOSSIER = Path(__file__).resolve().parents[1] / "artifacts"


class DepotArtefacts:
    """Point d'accès unique aux fichiers JSON publiés avec l'application."""

    def __init__(self, dossier: Path | str = DOSSIER):
        self.dossier = Path(dossier)

    def _lire(self, nom: str) -> dict:
        chemin = self.dossier / nom
        if not chemin.exists():
            raise FileNotFoundError(
                f"Artefact manquant : {chemin.name}. Exécutez les notebooks de 04_machine_learning/ "
                "pour le régénérer.")
        return json.loads(chemin.read_text(encoding="utf-8"))

    def kpi_synthese(self) -> dict:
        """Indicateurs agrégés (page d'accueil et segmentation)."""
        return self._lire("kpi_synthese.json")

    def prevision_kpi(self) -> dict:
        """Série hebdomadaire, prévision LSTM et comparaison des modèles."""
        return self._lire("prevision_kpi.json")

    def meta_modele(self) -> dict:
        """Seuil, métriques, importance des variables, distributions marginales."""
        return self._lire("modele_churn_meta.json")

    @property
    def chemin_modele(self) -> Path:
        """Fichier des arbres XGBoost (seuils de coupure et valeurs de feuilles)."""
        return self.dossier / "modele_churn.json"
