import pytest

from bw_product import contract_shape as cs
from bw_product import store as st
from bw_product.tests.conftest import needs_mongod
from bw_product.tests.test_store_validators import _red

pytestmark = needs_mongod


def test_conditional_update_refuses_task_without_gate_state(db):
    st.init_db(db)
    watch = cs.empty_contract()
    watch.update({"analysis_id": "B13-0059-aa", "asset_id": "A", "status": "WATCH_EARLY"})
    st.insert_case(db, watch)
    # No work order without its evidence record: gate state must be present.
    assert st.attach_inspection_task(db, "B13-0059-aa", _red()["inspection_draft"]) is None
    doc = db.diagnostic_cases.find_one({"analysis_id": "B13-0059-aa"})
    assert doc["inspection_draft"] is None


def test_approve_and_reject_both_persist_and_retain_evidence(db):
    st.init_db(db)
    store = st.MongoDecisionStore(db)
    a, b = _red(), _red()
    b["analysis_id"] = "Bearing1_3-0155-second"
    st.insert_case(db, a)
    st.insert_case(db, b)

    ok = store.record(a["analysis_id"], "APPROVE", "pattern matches; schedule visual")
    no = store.record(b["analysis_id"], "REJECT", "sensor was bumped")
    assert ok.decision == "APPROVE" and no.reason == "sensor was bumped"
    assert ok.timestamp and no.timestamp

    da = db.diagnostic_cases.find_one({"analysis_id": a["analysis_id"]})
    dbb = db.diagnostic_cases.find_one({"analysis_id": b["analysis_id"]})
    assert da["status"] == "INSPECTION_APPROVED" and dbb["status"] == "INSPECTION_REJECTED"
    # evidence retained on reject
    assert dbb["inspection_draft"] is not None and dbb["envelope_evidence"] is not None
    assert da["human_review"]["decision"] == "APPROVE"
    assert dbb["human_review"]["reason"] == "sensor was bumped"


def test_defer_keeps_status(db):
    st.init_db(db)
    store = st.MongoDecisionStore(db)
    r = _red()
    st.insert_case(db, r)
    hr = store.record(r["analysis_id"], "DEFER", "need second analyst")
    assert hr.decision == "DEFER"
    doc = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    assert doc["status"] == "ANALYST_REVIEW_REQUIRED"
    assert doc["human_review"]["decision"] == "DEFER"


def test_record_unknown_decision_raises(db):
    st.init_db(db)
    store = st.MongoDecisionStore(db)
    r = _red()
    st.insert_case(db, r)
    with pytest.raises(ValueError):
        store.record(r["analysis_id"], "SHIP_IT", "nope")


def test_record_unknown_analysis_raises(db):
    st.init_db(db)
    store = st.MongoDecisionStore(db)
    with pytest.raises(KeyError):
        store.record("missing-id", "APPROVE", "x")


def _refusal():
    r = cs.empty_contract()
    r.update({
        "analysis_id": "Bearing1_3-0155-unverified", "asset_id": "A",
        "status": "ABNORMAL_LOCATION_UNCONFIRMED",
        "refusal_reasons": ["bearing geometry unverified"],
        "inspection_draft": {
            "task_type": "VERIFY_BEARING_GEOMETRY",
            "title": "Verify installed bearing geometry", "asset_id": "A",
            "suspected_element": None, "evidence_locators": [],
            "recommended_action": "Confirm geometry, then re-run.",
            "not_claimed": ["element call without verified geometry"],
        },
        "human_review": {"required": True, "decision": None, "reason": None, "timestamp": None},
    })
    return r


def test_refusal_case_cannot_be_approved(db):
    """The Codex-critical: a geometry-unverified case must never become
    INSPECTION_APPROVED, whatever the client renders."""
    st.init_db(db)
    store = st.MongoDecisionStore(db)
    st.insert_case(db, _refusal())
    with pytest.raises(st.DecisionConflict):
        store.record("Bearing1_3-0155-unverified", "APPROVE", "looks fine")
    doc = db.diagnostic_cases.find_one({"analysis_id": "Bearing1_3-0155-unverified"})
    assert doc["status"] == "ABNORMAL_LOCATION_UNCONFIRMED"
    assert doc["human_review"]["decision"] is None


def test_second_decision_conflicts_not_overwrites(db):
    st.init_db(db)
    store = st.MongoDecisionStore(db)
    r = _red()
    st.insert_case(db, r)
    store.record(r["analysis_id"], "REJECT", "sensor was bumped")
    with pytest.raises(st.DecisionConflict):
        store.record(r["analysis_id"], "APPROVE", "second thoughts")
    doc = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    assert doc["status"] == "INSPECTION_REJECTED"
    assert doc["human_review"]["decision"] == "REJECT"
    assert doc["human_review"]["reason"] == "sensor was bumped"


def test_defer_stays_revisitable_but_final_decisions_lock(db):
    """DEFER means 'decide later', so a later APPROVE must land; once a final
    decision exists, nothing overwrites it."""
    st.init_db(db)
    store = st.MongoDecisionStore(db)
    r = _red()
    st.insert_case(db, r)
    store.record(r["analysis_id"], "DEFER", "need second analyst")
    hr = store.record(r["analysis_id"], "APPROVE", "second analyst agreed")
    assert hr.decision == "APPROVE"
    with pytest.raises(st.DecisionConflict):
        store.record(r["analysis_id"], "REJECT", "too late")
    doc = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    assert doc["status"] == "INSPECTION_APPROVED"
    assert doc["human_review"]["decision"] == "APPROVE"


def test_green_case_with_inspection_order_refused_at_insert(db):
    st.init_db(db)
    green = _red()
    green["analysis_id"] = "B13-0008-green"
    green["status"] = "NO_ANOMALY_DETECTED"
    with pytest.raises(ValueError):
        st.insert_case(db, green)


def test_attach_never_overwrites_existing_draft(db):
    st.init_db(db)
    r = _red()
    st.insert_case(db, r)
    replacement = dict(r["inspection_draft"], title="Replace the bearing")
    assert st.attach_inspection_task(db, r["analysis_id"], replacement) is None
    doc = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    assert doc["inspection_draft"]["title"] == "Inspect outer race, Bearing1_3"


def test_refusal_task_attaches_on_blocked_status(db):
    st.init_db(db)
    refusal = _refusal()
    refusal["inspection_draft"] = None
    st.insert_case(db, refusal)
    task = _refusal()["inspection_draft"]
    assert st.attach_inspection_task(db, refusal["analysis_id"], task) is not None


def test_refresh_updates_stale_evidence_on_undecided_case(db):
    """Regenerated fixture with the same analysis_id must replace stale stored
    evidence (the round-2 drift class: Mongo serving pre-hardening values while
    the report reads the corrected JSON)."""
    st.init_db(db)
    stale = _red()
    stale["candidate_families"] = [dict(stale["candidate_families"][0] if stale["candidate_families"] else {},
                                        family="BPFO", sideband_pairs_median=1, locators=[])]
    st.insert_case(db, stale)
    fresh = _red()
    fresh["candidate_families"] = [{"family": "BPFO", "sideband_pairs_median": 0, "locators": []}]
    assert st.refresh_case_evidence(db, fresh) is True
    doc = db.diagnostic_cases.find_one({"analysis_id": fresh["analysis_id"]})
    assert doc["candidate_families"][0]["sideband_pairs_median"] == 0


def test_decided_case_is_fully_immutable_to_refresh(db):
    """RETIRED PREMISE (whole-repo audit): the old drift-kill let a reseed
    correct a decided case's display evidence. Successor state: a decided
    record never changes AT ALL; a correction is a new analysis, never an
    in-place update."""
    st.init_db(db)
    r = _red()
    st.insert_case(db, r)
    st.MongoDecisionStore(db).record(r["analysis_id"], "REJECT", "sensor was bumped")
    before = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    fresh = _red()
    fresh["candidate_families"] = [{"family": "BPFO", "sideband_pairs_median": 0, "locators": []}]
    fresh["inspection_draft"] = dict(fresh["inspection_draft"], title="A different draft")
    assert st.refresh_case_evidence(db, fresh) is False
    after = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    assert after == before  # byte-for-byte untouched


def test_refresh_noop_when_identical(db):
    st.init_db(db)
    r = _red()
    st.insert_case(db, r)
    assert st.refresh_case_evidence(db, _red()) is False


def test_refresh_refuses_pair_insert_would_refuse(db):
    """Round-3 finding: refresh must not be a side door for task/status pairs the
    insert gate rejects. Stored doc stays untouched on refusal."""
    st.init_db(db)
    r = _red()
    st.insert_case(db, r)
    bad = _red()
    bad["status"] = "WATCH_EARLY"  # inspection order on non-red: invalid pair
    with pytest.raises(ValueError):
        st.refresh_case_evidence(db, bad)
    doc = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    assert doc["status"] == "ANALYST_REVIEW_REQUIRED"


def test_refresh_preserves_standing_defer_note(db):
    """A DEFER is human trail: a SAME-CLASS evidence refresh may update evidence
    but must not reset the DEFER's reason/timestamp. (The old status-crossing
    variant of this test retired: a refusal-shaped payload on a red case is now
    refused outright as identity ambiguity, covered below.)"""
    st.init_db(db)
    r = _red()
    st.insert_case(db, r)
    st.MongoDecisionStore(db).record(r["analysis_id"], "DEFER", "need second analyst")
    fresh = _red()
    fresh["candidate_families"] = [{"family": "BPFO", "sideband_pairs_median": 0, "locators": []}]
    assert st.refresh_case_evidence(db, fresh) is True
    doc = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    assert doc["candidate_families"][0]["sideband_pairs_median"] == 0  # evidence moved
    assert doc["human_review"]["decision"] == "DEFER"                  # the note survived
    assert doc["human_review"]["reason"] == "need second analyst"


def test_refresh_refuses_status_class_crossing(db):
    """Whole-repo audit BLOCKER: engine analysis ids do not encode trust, so a
    live refusal run carries the SAME id as the stored trusted red case. A
    payload whose status class differs from the stored one (decidable vs
    blocked/unconfirmed) is refused, so the refusal can never clobber the red
    evidence (and vice versa)."""
    st.init_db(db)
    r = _red()
    st.insert_case(db, r)
    refusal_shaped = _red()
    refusal_shaped["status"] = "ABNORMAL_LOCATION_UNCONFIRMED"
    refusal_shaped["inspection_draft"] = _refusal()["inspection_draft"]
    refusal_shaped["candidate_families"] = []
    before = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    assert st.refresh_case_evidence(db, refusal_shaped) is False
    after = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    assert after == before


def test_empty_reason_is_refused_at_the_store_boundary(db):
    """Whole-repo audit: the UI's client-side check is not the boundary. Any
    caller recording a final decision with an empty or whitespace reason must
    be refused before the write."""
    st.init_db(db)
    store = st.MongoDecisionStore(db)
    r = _red()
    st.insert_case(db, r)
    for bad in ("", "   ", None):
        with pytest.raises(ValueError, match="non-empty reason"):
            store.record(r["analysis_id"], "REJECT", bad)
    doc = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    assert doc["human_review"]["decision"] is None  # nothing landed


def test_refresh_never_overwrites_decision_landing_mid_refresh(db, monkeypatch):
    """Round-3 race, successor semantics: a final decision recorded between
    refresh's read and write must leave the document COMPLETELY untouched (the
    CAS guard misses, the retry's real read observes the decision, and refresh
    returns False without writing anything)."""
    st.init_db(db)
    r = _red()
    st.insert_case(db, r)
    stale = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    st.MongoDecisionStore(db).record(r["analysis_id"], "REJECT", "sensor was bumped")
    decided = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})

    reads = iter([stale])

    real_get_case = st.get_case

    def stale_then_real(db_, analysis_id):
        return next(reads, None) or real_get_case(db_, analysis_id)

    monkeypatch.setattr(st, "get_case", stale_then_real)
    fresh = _red()
    fresh["candidate_families"] = [{"family": "BPFO", "sideband_pairs_median": 0, "locators": []}]
    fresh["inspection_draft"] = dict(fresh["inspection_draft"], title="A different draft")
    assert st.refresh_case_evidence(db, fresh) is False
    doc = db.diagnostic_cases.find_one({"analysis_id": r["analysis_id"]})
    assert doc == decided  # untouched, decision and all
