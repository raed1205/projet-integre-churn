"""Access to the application artefacts.

The application reads **only** the ``artifacts/`` folder: aggregates, weekly forecasts
and the model parameters. It holds and reads no customer row.
"""

from __future__ import annotations

import json
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[1] / "artifacts"


class ArtifactStore:
    """Single access point to the JSON files published with the application."""

    def __init__(self, folder: Path | str = FOLDER):
        self.folder = Path(folder)

    def _read(self, name: str) -> dict:
        path = self.folder / name
        if not path.exists():
            raise FileNotFoundError(
                f"Missing artefact: {path.name}. Run the notebooks of 04_machine_learning/ to regenerate it.")
        return json.loads(path.read_text(encoding="utf-8"))

    def kpi_summary(self) -> dict:
        """Aggregated indicators (overview and segmentation)."""
        return self._read("kpi_summary.json")

    def kpi_forecast(self) -> dict:
        """Weekly series, LSTM forecast and model comparison."""
        return self._read("kpi_forecast.json")

    def model_meta(self) -> dict:
        """Threshold, metrics, feature importance, marginal distributions."""
        return self._read("churn_model_meta.json")

    @property
    def model_path(self) -> Path:
        """File of the XGBoost trees (split thresholds and leaf values)."""
        return self.folder / "churn_model.json"
