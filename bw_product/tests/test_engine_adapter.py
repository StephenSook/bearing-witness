"""The 2.8 seam, tested TONIGHT against a stub CLI so Saturday's wiring is a
switch-flip: point the same machinery at the real `python -m bearing_witness`.

The stub prints the red fixture's contract JSON (real measured data), so the
validation path is exercised with exactly the payload shape the engine will emit.
"""
import json
import sys

import pytest

from bw_product import engine_adapter as ea
from bw_product import store as st
from bw_product.tests.conftest import needs_mongod
from bw_product.ui.casedata import load

RED = load("red")["result"]


def _stub_cmd_printing(payload: str):
    """A command whose stdout is exactly `payload` (a real python invocation, so
    the subprocess path is the one production uses)."""
    return [sys.executable, "-c", f"import sys; sys.stdout.write({payload!r})"]


def _reset_probe():
    ea._probe_state.update({"available": False, "checked_at": None, "in_flight": False})


def test_engine_available_reflects_real_cli_invocation():
    """RETIRED PREMISE, asserting the successor state: before Task 12 this test
    asserted False (package present, CLI absent — an import probe would have
    false-positived). Vinh's CLI landed 2026-08-22 ~23:50 (commit e5a70ef), so
    the invocation probe must now answer True wherever the repo's package and
    deps are installed — including CI, which is what caught the expired premise."""
    _reset_probe()
    assert ea.engine_available() is True
    _reset_probe()


def test_probe_recovers_when_the_engine_lands_mid_session(monkeypatch):
    """A cached False must not need a process restart: after the retry TTL the
    probe runs again and flips to True (the self-revealing live row depends on
    exactly this transition)."""
    _reset_probe()
    calls = []

    class FakeProc:
        returncode = 1

    def probe(cmd, **kw):
        calls.append(1)
        return FakeProc() if len(calls) == 1 else type("P", (), {"returncode": 0})()

    monkeypatch.setattr(ea.subprocess, "run", probe)
    assert ea.engine_available() is False
    # inside the TTL: no re-probe, still False
    assert ea.engine_available() is False
    assert len(calls) == 1
    # after the TTL: re-probe, engine now answers, True and cached
    ea._probe_state["checked_at"] -= ea._PROBE_RETRY_S + 1
    assert ea.engine_available() is True
    assert ea.engine_available() is True
    assert len(calls) == 2
    _reset_probe()


def test_analyze_record_happy_path(monkeypatch):
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(RED)))
    result = ea.analyze_record(155, root=".")
    assert result["analysis_id"] == RED["analysis_id"]
    assert result["status"] == "ANALYST_REVIEW_REQUIRED"


def test_analyze_record_rejects_non_json(monkeypatch):
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing("Traceback (most recent call last):"))
    with pytest.raises(ea.EngineError, match="non-JSON"):
        ea.analyze_record(155, root=".")


@pytest.mark.parametrize("payload", ["null", "[1, 2]", '"done"', "42"])
def test_analyze_record_rejects_wrong_top_level_json_type(monkeypatch, payload):
    """Valid JSON that is not an object must become EngineError, never an
    AttributeError escaping into the UI callback."""
    monkeypatch.setattr(ea, "_cli_cmd", lambda *a, **k: _stub_cmd_printing(payload))
    with pytest.raises(ea.EngineError, match="expected the contract object"):
        ea.analyze_record(155, root=".")


def test_analyze_record_rejects_contract_violations(monkeypatch):
    bad = dict(RED, status="HEALTHY")
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(bad)))
    with pytest.raises(ea.EngineError, match="contract"):
        ea.analyze_record(155, root=".")


def test_analyze_record_surfaces_cli_failure(monkeypatch):
    cmd = [sys.executable, "-c", "import sys; sys.stderr.write('boom: no baseline'); sys.exit(3)"]
    monkeypatch.setattr(ea, "_cli_cmd", lambda *a, **k: cmd)
    with pytest.raises(ea.EngineError, match="exit 3.*boom"):
        ea.analyze_record(155, root=".")


@needs_mongod
def test_analyze_and_store_inserts_then_refreshes(db, monkeypatch):
    st.init_db(db)
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(RED)))
    first = ea.analyze_and_store(db, 155, root=".")
    assert st.get_case(db, first["analysis_id"]) is not None
    # second run with changed evidence refreshes through the guarded path
    changed = dict(RED)
    changed["candidate_families"] = [dict(RED["candidate_families"][0], score_current=99.9)]
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(changed)))
    ea.analyze_and_store(db, 155, root=".")
    doc = st.get_case(db, RED["analysis_id"])
    assert doc["candidate_families"][0]["score_current"] == 99.9


@needs_mongod
def test_finalized_case_is_immutable_to_reanalysis(db, monkeypatch):
    """The HIGH from the adapter review: a re-run must never rewrite the
    evidence a human already ruled on, and the caller gets PERSISTED truth
    (final status), never the engine's fresh undecided output."""
    st.init_db(db)
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(RED)))
    ea.analyze_and_store(db, 155, root=".")
    st.MongoDecisionStore(db).record(RED["analysis_id"], "APPROVE", "pattern matches")
    changed = dict(RED)
    changed["candidate_families"] = [dict(RED["candidate_families"][0], score_current=99.9)]
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(changed)))
    returned = ea.analyze_and_store(db, 155, root=".")
    assert returned["status"] == "INSPECTION_APPROVED"  # persisted truth returned
    doc = st.get_case(db, RED["analysis_id"])
    assert doc["candidate_families"][0]["score_current"] != 99.9  # evidence untouched
    assert doc["human_review"]["decision"] == "APPROVE"


@needs_mongod
def test_concurrent_insert_reconciles_instead_of_erroring(db, monkeypatch):
    """Double click / second client: the losing insert reads the winner back."""
    st.init_db(db)
    real_insert = st.insert_case

    def winner_then_duplicate(db_, result):
        real_insert(db_, result)          # the concurrent client lands it first
        real_insert(db_, result)          # our own insert now hits the unique index

    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(RED)))
    monkeypatch.setattr(st, "insert_case", winner_then_duplicate)
    returned = ea.analyze_and_store(db, 155, root=".")  # must not raise
    assert returned["analysis_id"] == RED["analysis_id"]


def test_timed_out_probe_still_gets_its_cooldown(monkeypatch):
    """A probe that hangs to its timeout must anchor the retry TTL to
    COMPLETION: the immediately following call must not spawn another probe."""
    import subprocess as sp
    _reset_probe()
    calls = []

    def hanging_probe(cmd, **kw):
        calls.append(1)
        raise sp.TimeoutExpired(cmd, 30)

    monkeypatch.setattr(ea.subprocess, "run", hanging_probe)
    assert ea.engine_available() is False
    assert ea.engine_available() is False  # inside cooldown: no second probe
    assert len(calls) == 1
    _reset_probe()


def test_concurrent_callers_do_not_stampede_a_hung_probe(monkeypatch):
    """Single-flight: while one probe is blocked, a concurrent caller answers
    False immediately without launching a second subprocess."""
    import threading as th
    _reset_probe()
    calls = []
    started = th.Event()
    release = th.Event()

    def blocking_probe(cmd, **kw):
        calls.append(1)
        started.set()
        release.wait(timeout=10)
        return type("P", (), {"returncode": 1})()

    monkeypatch.setattr(ea.subprocess, "run", blocking_probe)
    t = th.Thread(target=ea.engine_available)
    t.start()
    assert started.wait(timeout=5)
    # probe is in flight and hung: this call must NOT start another probe
    assert ea.engine_available() is False
    assert len(calls) == 1
    release.set()
    t.join(timeout=5)
    assert len(calls) == 1
    _reset_probe()


@needs_mongod
def test_decision_landing_mid_refresh_still_freezes_evidence(db, monkeypatch):
    """The round-2 HIGH: adapter reads UNDECIDED, a decision lands, refresh runs.
    touch_decided=False must refuse the write at the CAS boundary (the retry's
    re-read observes the decision), leaving finalized evidence untouched."""
    st.init_db(db)
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(RED)))
    ea.analyze_and_store(db, 155, root=".")

    stale_undecided = st.get_case(db, RED["analysis_id"])
    st.MongoDecisionStore(db).record(RED["analysis_id"], "APPROVE", "pattern matches")

    # serve the adapter (and refresh's first read) the stale undecided snapshot,
    # exactly as if the decision landed mid-flight; later reads are real
    reads = iter([stale_undecided, stale_undecided])
    real_get_case = st.get_case

    def stale_then_real(db_, analysis_id):
        return next(reads, None) or real_get_case(db_, analysis_id)

    monkeypatch.setattr(st, "get_case", stale_then_real)
    changed = dict(RED)
    changed["candidate_families"] = [dict(RED["candidate_families"][0], score_current=99.9)]
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(changed)))
    returned = ea.analyze_and_store(db, 155, root=".")
    doc = real_get_case(db, RED["analysis_id"])
    assert doc["candidate_families"][0]["score_current"] != 99.9  # evidence frozen
    assert doc["human_review"]["decision"] == "APPROVE"
    assert returned["status"] == "INSPECTION_APPROVED"  # persisted truth returned


@needs_mongod
def test_trust_collision_fails_closed_not_wrong_document(db, monkeypatch):
    """Exit-gate HIGH: with a trusted W155 stored, an unverified run (same
    engine id, refusal-shaped) must raise, never return the stored trusted case
    as this run's answer, and never touch the stored document."""
    st.init_db(db)
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(RED)))
    ea.analyze_and_store(db, 155, root=".")
    before = st.get_case(db, RED["analysis_id"])

    refusal_shaped = dict(load("refusal")["result"])
    refusal_shaped["analysis_id"] = RED["analysis_id"]  # the engine's collision
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(refusal_shaped)))
    with pytest.raises(ea.EngineError, match="identity collision"):
        ea.analyze_and_store(db, 155, root=".")
    assert st.get_case(db, RED["analysis_id"]) == before  # untouched


@needs_mongod
def test_feature_window_condition_comes_from_the_result(db, monkeypatch):
    """Exit-gate MEDIUM: a nondefault-condition analysis must stamp ITS OWN
    condition into the time-series, not the module default."""
    st.init_db(db)
    other = dict(RED)
    other["analysis_id"] = "Bearing2_2-0047-cafecafe"
    other["input_trust"] = dict(RED["input_trust"],
                                regime={"condition_id": "37.5Hz11kN", "load_kn": 11.0})
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(other)))
    ea.analyze_and_store(db, 47, root=".")
    row = db.feature_windows.find_one({"meta.asset_id": other["asset_id"]},
                                      sort=[("ts", -1)])
    assert row["meta"]["condition"] == "37.5Hz11kN"


@needs_mongod
def test_analyze_and_store_never_lands_invalid_output(db, monkeypatch):
    st.init_db(db)
    bad = dict(RED, status="HEALTHY")
    monkeypatch.setattr(ea, "_cli_cmd",
                        lambda *a, **k: _stub_cmd_printing(json.dumps(bad)))
    with pytest.raises(ea.EngineError):
        ea.analyze_and_store(db, 155, root=".")
    assert st.get_case(db, RED["analysis_id"]) is None
