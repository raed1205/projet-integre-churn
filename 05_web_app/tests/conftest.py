"""Configuration commune des tests : rend `utils` importable comme le fait Streamlit."""

import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
RACINE = APP.parent
sys.path.insert(0, str(APP))
