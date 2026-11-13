"""Project identity and settings — single source of truth.

Editing this file is enough to change a name, a colour or a path in every
generated deliverable (figures, application, report, slides).
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------
PROJECT_NAME = "VIGIE"          # French for "lookout": the watch posted to spot trouble early
SUBTITLE = "Customer churn analysis and prediction"
TAGLINE = "See churn coming. Act before the account closes."

SCHOOL = "ESPRIT School of Business"
PROGRAMME = "Bachelor Year 3 — Business Computing (BI)"
MODULE = "Integrated Project"
GROUP = "Group BI 5"
YEAR = "2026"

TEAM = [
    {"name": "Raed Meddeb", "role": "Project lead · Churn modelling (Machine Learning)",
     "email": "raed.meddeb@esprit.tn"},
    {"name": "Ibrahim Grira", "role": "Web application, UML & DevOps (tests, CI)",
     "email": "ibrahim.grira@esprit.tn"},
    {"name": "Salsabil Ben Elhadj", "role": "Data Warehouse & ETL (Talend, PostgreSQL)",
     "email": "BenElhadj.Salsabil@esprit.tn"},
    {"name": "Salah Chebbi", "role": "Time series & Deep Learning (LSTM)",
     "email": "salah.chebbi@esprit.tn"},
    {"name": "Ines Ayed", "role": "Power BI reporting, DAX & data quality",
     "email": "ines.ayed@esprit.tn"},
]
SUPERVISORS = ["Aymen Ben Brik", "Hela Hammami"]
TEAM_LINE = " · ".join(m["name"] for m in TEAM)

# --------------------------------------------------------------------------
# Visual identity (shared by Power BI, Streamlit, the report and the slides)
# --------------------------------------------------------------------------
COLORS = {
    "ink": "#14213D",        # titles, axes, strong text
    "churn": "#D62839",      # anything that denotes churn / risk
    "retention": "#2A9D8F",  # anything that denotes retained customers
    "amber": "#F4A261",      # intermediate alert, highlight
    "sky": "#457B9D",        # secondary series
    "mist": "#E9ECEF",       # grids, card backgrounds
    "paper": "#FAFAF7",      # page background
    "text": "#1F2937",
    "grey": "#6B7280",
}
PALETTE = [COLORS["ink"], COLORS["churn"], COLORS["retention"], COLORS["amber"], COLORS["sky"], COLORS["grey"]]

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]

# The data is NEVER in the repository. By default it is read from data/
# (git-ignored); the VIGIE_DATA_DIR variable can point elsewhere.
DATA_DIR = Path(os.environ.get("VIGIE_DATA_DIR", ROOT / "data"))

FIGURES = ROOT / "06_rapport" / "figures"
ML_RESULTS = ROOT / "04_machine_learning" / "results"
MODELS = ROOT / "04_machine_learning" / "models"      # outside the repository (.gitignore)
APP_ARTIFACTS = ROOT / "05_web_app" / "artifacts"     # aggregates + model parameters

# --------------------------------------------------------------------------
# Shared business rules
# --------------------------------------------------------------------------
SEED = 42            # reproducibility (splits, models)
MIN_CELL_SIZE = 20   # no aggregate is published below this headcount
MASS_SHARE = 0.50    # mass operations: the weeks that add up to 50% of closures
