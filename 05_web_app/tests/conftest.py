"""Shared test setup: makes `utils` importable the way Streamlit does."""

import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
sys.path.insert(0, str(APP))
