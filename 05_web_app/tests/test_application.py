"""Test de bout en bout : l'application démarre et chaque page s'exécute sans erreur."""

import pytest
from streamlit.testing.v1 import AppTest

from conftest import APP

PAGES = ["pages/0_Vue_d_ensemble.py", "pages/1_Prediction_du_churn.py", "pages/2_Prevision_du_KPI.py",
         "pages/3_Segments_et_profils.py", "pages/4_Methode_et_equipe.py"]


def ouvrir(page: str | None = None) -> AppTest:
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=60).run()
    if page:
        at.switch_page(page).run()
    return at


def test_l_application_demarre(monkeypatch):
    monkeypatch.chdir(APP)
    at = ouvrir()
    assert not at.exception, [e.value for e in at.exception]
    assert any("vue d'ensemble" in m.value for m in at.markdown)


@pytest.mark.parametrize("page", PAGES)
def test_la_page_s_execute_sans_erreur(page, monkeypatch):
    monkeypatch.chdir(APP)
    at = ouvrir(page)
    assert not at.exception, [e.value for e in at.exception]


def test_le_formulaire_de_prediction_reagit(monkeypatch):
    """Scénario principal : on modifie le profil, le score change dans le bon sens."""
    monkeypatch.chdir(APP)
    at = ouvrir("pages/1_Prediction_du_churn.py")

    def score(app) -> float:
        texte = next(m.value for m in app.markdown if "Probabilité de départ estimée" in m.value)
        return float(texte.split("estimée : ")[1].split(" %")[0].replace(",", "."))

    avant = score(at)
    curseur = next(s for s in at.slider if "dernière revue" in s.label)
    curseur.set_value(120)                         # dossier non revu depuis 10 ans : la revue est en retard
    next(b for b in at.button if b.label == "Calculer le score").click().run()
    assert not at.exception
    assert score(at) > avant
