"""Garde-fous de protection des données : ils doivent rester verts avant tout déploiement."""

import json
import re
import subprocess

from conftest import APP, RACINE

ARTEFACTS = APP / "artifacts"
IDENTIFIANT = re.compile(r"\b[KX]\d{7}\b")      # forme des codes client (K…) et compte (X…)
EXTENSIONS_INTERDITES = (".csv", ".xlsx", ".xls", ".parquet", ".pkl", ".joblib", ".h5", ".keras", ".onnx", ".pbix")


def fichiers_suivis() -> list[str]:
    sortie = subprocess.run(["git", "ls-files"], cwd=RACINE, capture_output=True, text=True, check=True)
    return sortie.stdout.splitlines()


def test_aucun_fichier_de_donnees_ni_modele_serialise_dans_le_depot():
    interdits = [f for f in fichiers_suivis() if f.lower().endswith(EXTENSIONS_INTERDITES)]
    assert interdits == []


def test_aucun_identifiant_dans_les_fichiers_publies():
    for fichier in fichiers_suivis():
        if fichier.endswith((".json", ".md", ".ipynb", ".py", ".sql", ".html", ".js")):
            texte = (RACINE / fichier).read_text(encoding="utf-8", errors="ignore")
            assert not IDENTIFIANT.search(texte), f"identifiant trouvé dans {fichier}"


def test_aucun_agregat_sous_le_seuil_de_confidentialite():
    kpi = json.loads((ARTEFACTS / "kpi_synthese.json").read_text(encoding="utf-8"))
    seuil = kpi["source"]["seuil_petit_effectif"]
    assert seuil >= 20
    for groupe in ("axes_client", "axes_compte"):
        for axe, modalites in kpi[groupe].items():
            assert all(m["effectif"] >= seuil for m in modalites), axe
    assert all(s["clients"] >= seuil for s in kpi["segments"])
    assert all(m["comptes"] >= seuil for m in kpi["motifs_cloture"])


def test_le_modele_publie_ne_contient_que_des_arbres():
    modele = json.loads((ARTEFACTS / "modele_churn.json").read_text(encoding="utf-8"))
    assert set(modele) == {"learner", "version"}
    assert not IDENTIFIANT.search(json.dumps(modele["learner"]["feature_names"]))


def test_volumes_coherents_entre_artefacts():
    kpi = json.loads((ARTEFACTS / "kpi_synthese.json").read_text(encoding="utf-8"))
    prevision = json.loads((ARTEFACTS / "prevision_kpi.json").read_text(encoding="utf-8"))
    g = kpi["global"]
    assert g["comptes_actifs"] + g["comptes_clos"] == g["comptes"]
    assert sum(prevision["historique"]["brute"]) == g["comptes_clos"]        # série hebdo = comptes clos
    assert sum(a["comptes"] for a in kpi["clotures_par_annee"]) == g["comptes_clos"]
    assert kpi["source"]["sha256"] == json.loads((ARTEFACTS / "modele_churn_meta.json").read_text())["source_sha256"]
