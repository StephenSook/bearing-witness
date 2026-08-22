import json

import pytest

from bearing_witness import contract, review


def _red():
    r = contract.ResultContract.model_validate(contract.EMPTY)
    return r.model_copy(update={
        "analysis_id": "Bearing1_3-0155-abcdef01", "asset_id": "XJTU-SY/35Hz12kN/Bearing1_3",
        "status": "ANALYST_REVIEW_REQUIRED", "suspected_location": "outer",
        "inspection_draft": review.draft_task("INSPECTION_WORK_ORDER", "XJTU-SY/35Hz12kN/Bearing1_3", "outer", ["loc1"]),
        "human_review": contract.HumanReview(required=True),
    })


def test_draft_task_shapes():
    d = review.draft_task("INSPECTION_WORK_ORDER", "A", "outer", ["x|w1|aa|envelope|107.03Hz|h1"])
    assert d.task_type == "INSPECTION_WORK_ORDER" and d.suspected_element == "outer"
    assert "replace" not in d.recommended_action.lower()
    assert any("RUL" in n for n in d.not_claimed)
    g = review.draft_task("VERIFY_BEARING_GEOMETRY", "A", None, [])
    assert g.suspected_element is None and "geometry" in g.recommended_action.lower()


def test_approve_and_reject_both_persist_and_retain_evidence(tmp_path):
    store = review.JsonDecisionStore(tmp_path / "decisions.json")
    ok = review.apply_decision(_red(), "APPROVE", "pattern matches; schedule visual", store)
    no = review.apply_decision(_red(), "REJECT", "sensor was bumped", store)
    assert ok.status == "INSPECTION_APPROVED" and no.status == "INSPECTION_REJECTED"
    assert ok.inspection_draft is not None and no.inspection_draft is not None      # evidence retained
    assert ok.human_review.decision == "APPROVE" and no.human_review.reason == "sensor was bumped"
    rows = json.loads((tmp_path / "decisions.json").read_text())
    assert [r["decision"] for r in rows] == ["APPROVE", "REJECT"]
    assert set(rows[0]) == {"analysis_id", "decision", "reason", "timestamp"}


def test_defer_keeps_status(tmp_path):
    store = review.JsonDecisionStore(tmp_path / "d.json")
    r = review.apply_decision(_red(), "DEFER", "waiting on second channel", store)
    assert r.status == "ANALYST_REVIEW_REQUIRED" and r.human_review.decision == "DEFER"


def test_apply_decision_rejects_non_red_cases(tmp_path):
    nonred = _red().model_copy(update={"status": "WATCH_EARLY"})
    store = review.JsonDecisionStore(tmp_path / "decisions.json")
    for decision in ("APPROVE", "REJECT", "DEFER"):
        with pytest.raises(ValueError):
            review.apply_decision(nonred, decision, "x", store)
    assert not (tmp_path / "decisions.json").exists()
