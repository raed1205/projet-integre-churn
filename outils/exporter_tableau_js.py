"""Alimente l'interface JavaScript (bonus phase 3) à partir des artefacts de l'application.

    python outils/exporter_tableau_js.py

Écrit 03_power_bi/bonus_javascript/donnees.js : les mêmes agrégats que l'application Streamlit,
dans une variable JavaScript, pour que index.html s'ouvre par un simple double-clic.
"""

import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
ARTEFACTS = RACINE / "05_web_app" / "artifacts"
SORTIE = RACINE / "03_power_bi" / "bonus_javascript" / "donnees.js"

kpi = json.loads((ARTEFACTS / "kpi_synthese.json").read_text(encoding="utf-8"))
prevision = json.loads((ARTEFACTS / "prevision_kpi.json").read_text(encoding="utf-8"))
donnees = {"kpi": kpi, "prevision": {"historique": prevision["historique"]}}
SORTIE.write_text(
    "// Fichier généré par outils/exporter_tableau_js.py — agrégats uniquement, aucune ligne client.\n"
    "window.VIGIE_DONNEES = " + json.dumps(donnees, ensure_ascii=False, separators=(",", ":")) + ";\n",
    encoding="utf-8")
print(f"écrit : {SORTIE.relative_to(RACINE)} ({SORTIE.stat().st_size / 1024:.0f} ko)")
