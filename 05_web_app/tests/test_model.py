"""Le modèle se charge, renvoie des probabilités cohérentes et s'explique."""

import numpy as np
import pandas as pd
import pytest

from utils import preprocessing
from utils.model import GenerateurFictif, ModeleChurn, niveau_de_risque


@pytest.fixture(scope="module")
def modele() -> ModeleChurn:
    return ModeleChurn()


def test_score_est_une_probabilite(modele):
    p = modele.predire(preprocessing.profil_par_defaut())
    assert 0.0 <= p.score <= 1.0
    assert p.niveau in {"Faible", "Modéré", "Élevé"}


def test_explication_coherente_avec_le_score(modele):
    """Valeur de base + somme des contributions = score (en log-odds) : l'explication est exacte."""
    p = modele.predire(preprocessing.profil_par_defaut())
    logit = modele.meta["valeur_de_base_shap"] + p.contributions.sum()
    assert 1 / (1 + np.exp(-logit)) == pytest.approx(p.score, abs=1e-3)
    assert set(p.contributions.index) == set(preprocessing.LIBELLES)


def test_revue_en_retard_augmente_le_risque(modele):
    base = preprocessing.profil_par_defaut()
    a_jour = modele.predire(base | {"MOIS_DEPUIS_REVUE": 6, "MOIS_AVANT_PROCHAINE_REVUE": 42}).score
    en_retard = modele.predire(base | {"MOIS_DEPUIS_REVUE": 84, "MOIS_AVANT_PROCHAINE_REVUE": -36}).score
    assert en_retard > a_jour + 0.10


def test_multi_equipement_reduit_le_risque_en_moyenne(modele):
    """L'effet du nombre de comptes dépend du profil : on le vérifie en moyenne sur un portefeuille fictif."""
    profils = GenerateurFictif(modele.meta["marginales"], graine=1).generer(2000)
    un_compte = modele.scores(profils.assign(NB_COMPTES=1)).mean()
    trois_comptes = modele.scores(profils.assign(NB_COMPTES=3)).mean()
    assert trois_comptes < un_compte


def test_niveaux_de_risque():
    assert niveau_de_risque(0.10)[0] == "Faible"
    assert niveau_de_risque(0.30)[0] == "Modéré"
    assert niveau_de_risque(0.75)[0] == "Élevé"


def test_taux_observe_croit_avec_le_score(modele):
    taux = [t["taux_observe"] for t in modele.meta["score_vers_taux_observe"]]
    assert taux == sorted(taux)          # un score plus élevé correspond à plus de départs réels


def test_portefeuille_fictif(modele):
    profils = GenerateurFictif(modele.meta["marginales"], graine=1).generer(200)
    assert len(profils) == 200
    assert all(i.startswith("Profil fictif") for i in profils.index)
    scores = modele.scores(profils)
    assert ((scores >= 0) & (scores <= 1)).all()
    assert 0.20 < scores.mean() < 0.55   # proche du taux de base, sans le reproduire exactement
    cycle = profils["SCORE_KYC"].map(preprocessing.CYCLE_REVUE_MOIS)
    assert ((profils["MOIS_DEPUIS_REVUE"] + profils["MOIS_AVANT_PROCHAINE_REVUE"] - cycle).abs() < 1e-6).all()
    # reproductible : même graine, même portefeuille
    pd.testing.assert_frame_equal(profils, GenerateurFictif(modele.meta["marginales"], graine=1).generer(200))
