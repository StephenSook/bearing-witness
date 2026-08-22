"""FileDecisionStore fallback semantics: restart durability and the decision gate.

No mongod needed; exercises the file-backed last-ditch path only.
"""
import json

import pytest

from bw_product import store as st
from bw_product.tests.conftest import needs_mongod
from bw_product.ui.casedata import FIXTURE_DIR, SCENARIOS, FileDecisionStore, load


def _red_id() -> str:
    return load("red")["result"]["analysis_id"]


def _refusal_id() -> str:
    return load("refusal")["result"]["analysis_id"]


def test_restart_keeps_final_decision_lock(tmp_path):
    path = tmp_path / "decisions.json"
    first = FileDecisionStore(path)
    first.record(_red_id(), "APPROVE", "pattern matches")
    # process restart: a fresh store over the same log
    second = FileDecisionStore(path)
    with pytest.raises(st.DecisionConflict):
        second.record(_red_id(), "REJECT", "second thoughts")
    assert second.cases[_red_id()]["status"] == "INSPECTION_APPROVED"
    rows = json.loads(path.read_text())
    assert [r["decision"] for r in rows] == ["APPROVE"]


def test_restart_after_defer_stays_revisitable(tmp_path):
    path = tmp_path / "decisions.json"
    FileDecisionStore(path).record(_red_id(), "DEFER", "need second analyst")
    second = FileDecisionStore(path)
    hr = second.record(_red_id(), "APPROVE", "second analyst agreed")
    assert hr.decision == "APPROVE"


def test_refusal_case_cannot_be_approved_via_file_store(tmp_path):
    store = FileDecisionStore(tmp_path / "decisions.json")
    with pytest.raises(st.DecisionConflict):
        store.record(_refusal_id(), "APPROVE", "judge clicked it")
    assert not (tmp_path / "decisions.json").exists()


def test_log_write_is_atomic_replace(tmp_path):
    path = tmp_path / "decisions.json"
    store = FileDecisionStore(path)
    store.record(_red_id(), "REJECT", "sensor was bumped")
    assert not path.with_suffix(".json.tmp").exists()
    assert json.loads(path.read_text())[0]["reason"] == "sensor was bumped"


def test_every_scenario_window_present_in_trend():
    trend = json.loads((FIXTURE_DIR / "trend.json").read_text())
    for meta in SCENARIOS.values():
        assert meta["window"] in trend["windows"], meta


@needs_mongod
def test_connect_backend_survives_refresh_failure(db, monkeypatch):
    """Grok round-4 HIGH: a refresh failure on one fixture must NOT demote the
    backend to the file store (which would show Mongo-decided cases as
    undecided). Only connection/init failures fall back. The red fixture is
    pre-inserted so the refresh branch actually runs (round-5 finding: without
    this, a fresh test DB takes the insert branch and the test is vacuous)."""
    import bw_product.ui.casedata as cd

    st.init_db(db)
    st.insert_case(db, load("red")["result"])
    calls = []

    def exploding_refresh(*a, **k):
        calls.append(1)
        raise RuntimeError("boom")

    monkeypatch.setattr(st, "connect", lambda uri=None: db)
    monkeypatch.setattr(st, "refresh_case_evidence", exploding_refresh)
    backend = cd.connect_backend()
    assert calls, "refresh branch never ran; test would be vacuous"
    assert backend.kind == "mongo"
    assert "red" not in backend.unpersisted  # refresh failure is not a seed failure


@needs_mongod
def test_existence_read_failure_disables_case_not_startup(db, monkeypatch):
    """Round-6 HIGH: a get_case failure after a successful ping must not crash
    connect_backend (it runs at app startup). The affected case is disabled,
    the others seed normally, the backend stays Mongo."""
    import bw_product.ui.casedata as cd

    red_id = load("red")["result"]["analysis_id"]
    real_get_case = st.get_case

    def failing_red_read(db_, analysis_id):
        if analysis_id == red_id:
            raise RuntimeError("connection reset")
        return real_get_case(db_, analysis_id)

    monkeypatch.setattr(st, "connect", lambda uri=None: db)
    monkeypatch.setattr(st, "get_case", failing_red_read)
    backend = cd.connect_backend()  # must not raise
    assert backend.kind == "mongo"
    assert "red" in backend.unpersisted
    assert "green" not in backend.unpersisted
    # round-7 finding: the PERSISTENT failure must also not crash page render;
    # fixture evidence serves, and decide.py keeps controls off via unpersisted
    result = backend.case("red")
    assert result["status"] == "ANALYST_REVIEW_REQUIRED"
    assert result["analysis_id"] == red_id
    # a healthy scenario still reads through to Mongo
    assert backend.case("green")["status"] == "NO_ANOMALY_DETECTED"


@needs_mongod
def test_insert_race_reconciles_as_persisted(db, monkeypatch):
    """Round-6 HIGH: an insert exception whose write actually landed (lost ack /
    duplicate-key race) must reconcile by re-read and count as persisted, so a
    live record never has its decision controls hidden."""
    import bw_product.ui.casedata as cd

    red_id = load("red")["result"]["analysis_id"]
    real_insert = st.insert_case

    def landed_then_exploded(db_, result):
        real_insert(db_, result)
        if result["analysis_id"] == red_id:
            raise RuntimeError("socket closed before ack")

    monkeypatch.setattr(st, "connect", lambda uri=None: db)
    monkeypatch.setattr(st, "insert_case", landed_then_exploded)
    backend = cd.connect_backend()
    assert backend.kind == "mongo"
    assert "red" not in backend.unpersisted  # record exists; reconciled
    assert st.get_case(db, red_id) is not None


@needs_mongod
def test_post_startup_read_failure_never_reactivates_a_decided_case(db, monkeypatch):
    """Round-8 HIGH: a healthy startup, a recorded final decision, THEN Mongo
    stops answering. The fixture stands in for evidence but the case must not
    become actionable again (the fixture looks undecided); a later successful
    read self-heals."""
    import bw_product.ui.casedata as cd

    red_id = load("red")["result"]["analysis_id"]
    monkeypatch.setattr(st, "connect", lambda uri=None: db)
    backend = cd.connect_backend()
    assert backend.kind == "mongo" and not backend.unpersisted
    backend.store.record(red_id, "REJECT", "sensor was bumped")

    real_get_case = st.get_case

    def outage(db_, analysis_id):
        raise RuntimeError("mongo stopped answering")

    monkeypatch.setattr(st, "get_case", outage)
    result = backend.case("red")
    assert result["human_review"]["decision"] is None  # fixture stand-in
    assert "red" in backend.degraded                    # so decisions stay OFF
    assert backend.decidable_here("red") is False

    # round-9 finding: an EMPTY read is absence, not recovery. A vanished record
    # (deleteMany without restart) must keep decisions off, not re-arm them
    # against the undecided fixture.
    monkeypatch.setattr(st, "get_case", lambda db_, analysis_id: None)
    vanished = backend.case("red")
    assert vanished["human_review"]["decision"] is None  # fixture stand-in again
    assert "red" in backend.degraded
    assert backend.decidable_here("red") is False

    monkeypatch.setattr(st, "get_case", real_get_case)
    healed = backend.case("red")
    assert healed["status"] == "INSPECTION_REJECTED"    # truth is back
    assert "red" not in backend.degraded                # and decisions logic heals
    assert backend.decidable_here("red") is True


@needs_mongod
def test_seed_failure_disables_that_cases_decisions(db, monkeypatch):
    """Round-5 HIGH: an INITIAL insert failure must not leave an actionable case
    with no database record (record() would KeyError mid-demo). The case is
    marked unpersisted and its decisions are disabled; the backend stays Mongo."""
    import bw_product.ui.casedata as cd

    red_id = load("red")["result"]["analysis_id"]

    real_insert = st.insert_case

    def failing_red_insert(db_, result):
        if result["analysis_id"] == red_id:
            raise RuntimeError("boom")
        return real_insert(db_, result)

    monkeypatch.setattr(st, "connect", lambda uri=None: db)
    monkeypatch.setattr(st, "insert_case", failing_red_insert)
    backend = cd.connect_backend()
    assert backend.kind == "mongo"
    assert "red" in backend.unpersisted
    assert "green" not in backend.unpersisted
