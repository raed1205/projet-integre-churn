"""Data-protection safeguards: they must stay green before any deployment."""

import json
import re
import subprocess

from conftest import APP, ROOT

ARTIFACTS = APP / "artifacts"
IDENTIFIER = re.compile(r"\b[KX]\d{7}\b")      # shape of the customer (K…) and account (X…) codes
FORBIDDEN = (".csv", ".xlsx", ".xls", ".parquet", ".pkl", ".joblib", ".h5", ".keras", ".onnx", ".pbix")


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return out.stdout.splitlines()


def test_no_data_file_or_serialised_model_in_the_repository():
    assert [f for f in tracked_files() if f.lower().endswith(FORBIDDEN)] == []


def test_no_identifier_in_the_published_files():
    for f in tracked_files():
        if f.endswith((".json", ".md", ".ipynb", ".py", ".sql", ".html", ".js")):
            text = (ROOT / f).read_text(encoding="utf-8", errors="ignore")
            assert not IDENTIFIER.search(text), f"identifier found in {f}"


def test_no_aggregate_below_the_confidentiality_threshold():
    kpi = json.loads((ARTIFACTS / "kpi_summary.json").read_text(encoding="utf-8"))
    threshold = kpi["source"]["min_cell_size"]
    assert threshold >= 20
    for group in ("customer_axes", "account_axes"):
        for axis, categories in kpi[group].items():
            assert all(c["count"] >= threshold for c in categories), axis
    assert all(s["customers"] >= threshold for s in kpi["segments"])
    assert all(r["accounts"] >= threshold for r in kpi["closure_reasons"])


def test_published_model_only_holds_trees():
    model = json.loads((ARTIFACTS / "churn_model.json").read_text(encoding="utf-8"))
    assert set(model) == {"learner", "version"}
    assert not IDENTIFIER.search(json.dumps(model["learner"]["feature_names"]))


def test_volumes_are_consistent_across_artifacts():
    kpi = json.loads((ARTIFACTS / "kpi_summary.json").read_text(encoding="utf-8"))
    forecast = json.loads((ARTIFACTS / "kpi_forecast.json").read_text(encoding="utf-8"))
    g = kpi["overall"]
    assert g["active_accounts"] + g["closed_accounts"] == g["accounts"]
    assert sum(forecast["history"]["raw"]) == g["closed_accounts"]
    assert sum(y["accounts"] for y in kpi["closures_per_year"]) == g["closed_accounts"]
    meta = json.loads((ARTIFACTS / "churn_model_meta.json").read_text(encoding="utf-8"))
    assert kpi["source"]["sha256"] == meta["source_sha256"]
