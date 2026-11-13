"""L'encodage d'un profil doit être stable : c'est le contrat entre l'entraînement et l'application."""

import numpy as np
import pandas as pd
import pytest

from utils import preprocessing


def test_colonnes_du_modele_sont_figees():
    colonnes = preprocessing.colonnes_modele()
    assert len(colonnes) == 31
    assert colonnes[:7] == preprocessing.NUMERIQUES
    assert len(set(colonnes)) == len(colonnes)


def test_encodage_d_un_profil():
    X = preprocessing.encoder(pd.DataFrame([preprocessing.profil_par_defaut()]))
    assert list(X.columns) == preprocessing.colonnes_modele()
    assert X.loc[0, "AGE"] == 40
    assert X.loc[0, "STATUT_MARITAL=M"] == 1 and X.loc[0, "STATUT_MARITAL=C"] == 0
    # exactement une indicatrice active par variable catégorielle
    for variable in preprocessing.CATEGORIELLES:
        assert X.filter(like=f"{variable}=").sum(axis=1).iloc[0] == 1


def test_valeur_manquante_conservee():
    X = preprocessing.encoder(pd.DataFrame([preprocessing.profil_par_defaut()]))
    assert np.isnan(X.loc[0, "SALAIRE"])          # revenu non déclaré : reste manquant


def test_modalite_inconnue_rangee_dans_la_derniere():
    profil = preprocessing.profil_par_defaut() | {"NATURE_CLIENT": "TRPP", "STATUT_MARITAL": None}
    X = preprocessing.encoder(pd.DataFrame([profil]))
    assert X.loc[0, "NATURE_CLIENT=AUTRE"] == 1
    assert X.loc[0, "STATUT_MARITAL=NR"] == 1


def test_variable_absente_refusee():
    profil = preprocessing.profil_par_defaut()
    del profil["AGE"]
    with pytest.raises(ValueError, match="AGE"):
        preprocessing.encoder(pd.DataFrame([profil]))


def test_chaque_variable_a_un_libelle():
    for variable in list(preprocessing.NUMERIQUES) + list(preprocessing.CATEGORIELLES):
        assert variable in preprocessing.LIBELLES


def test_cycle_de_revue_selon_le_score_kyc():
    assert preprocessing.mois_avant_prochaine_revue("LR", 12) == 36      # cycle de 48 mois
    assert preprocessing.mois_avant_prochaine_revue("MR", 12) == 24      # cycle de 36 mois
    assert preprocessing.mois_avant_prochaine_revue("H2", 30) == -6      # cycle de 24 mois : revue en retard
    defaut = preprocessing.profil_par_defaut()
    assert defaut["MOIS_AVANT_PROCHAINE_REVUE"] == preprocessing.mois_avant_prochaine_revue(
        defaut["SCORE_KYC"], defaut["MOIS_DEPUIS_REVUE"])
