"""End-to-end test: the application starts and every page runs without error."""

import pytest
from streamlit.testing.v1 import AppTest

from conftest import APP

PAGES = ["pages/0_Overview.py", "pages/1_Churn_Prediction.py", "pages/2_KPI_Forecast.py",
         "pages/3_Segments.py", "pages/4_Method_and_Team.py"]


def open_app(page: str | None = None) -> AppTest:
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=60).run()
    if page:
        at.switch_page(page).run()
    return at


def test_the_application_starts(monkeypatch):
    monkeypatch.chdir(APP)
    at = open_app()
    assert not at.exception, [e.value for e in at.exception]
    assert any("churn overview" in m.value for m in at.markdown)


@pytest.mark.parametrize("page", PAGES)
def test_the_page_runs_without_error(page, monkeypatch):
    monkeypatch.chdir(APP)
    at = open_app(page)
    assert not at.exception, [e.value for e in at.exception]


def test_the_prediction_form_reacts(monkeypatch):
    """Main scenario: the profile is changed, the score moves in the right direction."""
    monkeypatch.chdir(APP)
    at = open_app("pages/1_Churn_Prediction.py")

    def score(app) -> float:
        text = next(m.value for m in app.markdown if "Estimated probability of leaving" in m.value)
        return float(text.split("leaving: ")[1].split("%")[0])

    before = score(at)
    slider = next(s for s in at.slider if "last review" in s.label)
    slider.set_value(120)                       # file not reviewed for 10 years: the review is overdue
    next(b for b in at.button if b.label == "Compute the score").click().run()
    assert not at.exception
    assert score(at) > before
