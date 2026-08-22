import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures_data"

pytestmark = pytest.mark.skipif(
    not (FIXTURE_DIR / "fixture_red.json").exists(),
    reason="fixtures not generated")


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    from bw_product.report import build
    return build(tmp_path_factory.mktemp("report") / "report.html").read_text()


def test_report_is_self_contained(report):
    # no external fetches: check the MARKUP only (inline plotly.js source contains
    # href strings in its own code, which the browser never fetches)
    import re
    markup = re.sub(r"<script[^>]*>.*?</script>", "", report, flags=re.S)
    assert 'src="http' not in markup and "src='http" not in markup
    assert 'href="http' not in markup and "href='http" not in markup
    assert "data:audio/wav;base64," in report or not (FIXTURE_DIR / "beat_early.wav").exists()
    assert "plotly" in report.lower()


def test_report_ends_on_decision_not_a_lone_spectrum(report):
    assert "ANALYST_REVIEW_REQUIRED" in report
    assert "INSPECTION_WORK_ORDER" in report
    assert "HUMAN REVIEW REQUIRED" in report
    low = report.lower()
    assert low.index("inspection_work_order") > low.index("envelope spectrum")


def test_report_never_says_replace_in_the_action(report):
    r = json.loads((FIXTURE_DIR / "fixture_red.json").read_text())["result"]
    assert "replace" not in r["inspection_draft"]["recommended_action"].lower()
    assert "INSPECT, NEVER REPLACE" in report


def test_report_carries_locators_and_refusal(report):
    assert "|w155|" in report and "|envelope|" in report
    assert "VERIFY_BEARING_GEOMETRY" in report


def test_audio_loudness_record_matches_gate():
    rec = FIXTURE_DIR / "audio_loudness.json"
    if not rec.exists():
        pytest.skip("audio not generated")
    vals = list(json.loads(rec.read_text()).values())
    assert all(-18.0 <= v <= -14.0 for v in vals)
    assert abs(vals[0] - vals[1]) <= 1.0
