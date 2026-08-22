"""PLAN 2.8: the seam between the product loop and the engine lane's CLI.

Contract (PLAN.md Shared Contracts, locked): the engine is invoked as

    python -m bearing_witness analyze --root R --condition C --bearing B --record N
        [--geometry-unverified]

and prints one contract JSON on stdout. This module shells out to that contract,
validates the result twice (our shape tripwire + the engine's own pydantic
ResultContract when importable), and lands it in Mongo through the same gated
writes the fixtures use. It is import-free with respect to engine INTERNALS:
the CLI text contract is the whole interface, per the integration protocol.

Until the engine lane lands its __main__ (engine plan Task 12), engine_available()
is honestly False and every UI surface built on this module stays hidden.
Built Friday night as disclosed scaffolding (D5); first wired run is Saturday's
2.8 gate.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time

from pymongo.errors import DuplicateKeyError

from . import store as st
from .contract_shape import FIELDS, validate_shape
from .fixtures import BEARING, CONDITION, data_root

ENGINE_TIMEOUT_S = 180
_PROBE_RETRY_S = 30.0


class EngineError(RuntimeError):
    """The engine CLI failed, or produced output that violates the contract."""


def _cli_cmd(record: int, geometry_unverified: bool, root: str,
             condition: str, bearing: str, cache_dir: str | None = None) -> list[str]:
    cmd = [sys.executable, "-m", "bearing_witness", "analyze",
           "--root", root, "--condition", condition, "--bearing", bearing,
           "--record", str(record)]
    if geometry_unverified:
        cmd.append("--geometry-unverified")
    if cache_dir:
        cmd += ["--cache-dir", cache_dir]
    return cmd


_probe_state: dict = {"available": False, "checked_at": None,
                      "in_flight": False, "lock": threading.Lock()}


def engine_available() -> bool:
    """True only when `python -m bearing_witness` actually answers. The probe is
    a real invocation, not an import check: a package skeleton without its CLI
    must read as NOT available (an import-based probe would false-positive today).

    A True result is cached for the process lifetime; a False result is retried
    after a short TTL, so the live row genuinely self-reveals once the engine
    lands mid-session (a permanently cached False would need a restart)."""
    if _probe_state["available"]:
        return True
    # single-flight: while one probe runs, every other caller answers False
    # immediately instead of stacking blocking subprocesses; the cooldown
    # anchors to probe COMPLETION so a hung probe cannot burn its own TTL
    with _probe_state["lock"]:
        if _probe_state["available"]:
            return True
        if _probe_state["in_flight"]:
            return False
        if (_probe_state["checked_at"] is not None
                and time.monotonic() - _probe_state["checked_at"] < _PROBE_RETRY_S):
            return False
        _probe_state["in_flight"] = True
    try:
        proc = subprocess.run([sys.executable, "-m", "bearing_witness", "--help"],
                              capture_output=True, text=True, timeout=30)
        ok = proc.returncode == 0
    except Exception:
        ok = False
    finally:
        with _probe_state["lock"]:
            _probe_state["in_flight"] = False
            _probe_state["checked_at"] = time.monotonic()
    with _probe_state["lock"]:
        _probe_state["available"] = _probe_state["available"] or ok
    return ok


def analyze_record(record: int, *, geometry_unverified: bool = False,
                   root: str | None = None, condition: str = CONDITION,
                   bearing: str = BEARING, timeout: int = ENGINE_TIMEOUT_S,
                   cache_dir: str | None = None) -> dict:
    """Run the engine CLI for one record and return its VALIDATED contract dict.
    Raises EngineError with the CLI's stderr (never a silent fallback: a failed
    analysis must not quietly become fixture data).

    cache_dir matters a lot for a late-life window on a long-running bearing
    (e.g. Bearing3_1 has 2538 windows): without it every call recomputes
    windows 1..N from scratch (~15 ms/window, ~40s for that one), since the
    replay-discipline baseline/z-score math genuinely needs every prior
    window's features, not just the requested one."""
    root = root or os.environ.get("BW_ENGINE_ROOT") or str(data_root())
    cmd = _cli_cmd(record, geometry_unverified, root, condition, bearing, cache_dir)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise EngineError(f"engine timed out after {timeout}s: {' '.join(cmd)}") from exc
    if proc.returncode != 0:
        raise EngineError(
            f"engine exit {proc.returncode}: {proc.stderr.strip()[:800] or '(no stderr)'}")
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise EngineError(
            f"engine printed non-JSON (first 200 chars): {proc.stdout[:200]!r}") from exc
    if not isinstance(result, dict):
        raise EngineError(
            f"engine printed JSON of type {type(result).__name__}, expected the contract object")
    problems = validate_shape(result)
    if problems:
        raise EngineError(f"engine output violates the contract shape: {problems}")
    try:
        from bearing_witness.contract import ResultContract
        ResultContract.model_validate(result)
    except ImportError:
        pass  # shape tripwire above already ran; pydantic layer joins when importable
    except Exception as exc:
        raise EngineError(f"engine output fails its own ResultContract: {exc}") from exc
    return result


def analyze_and_store(db, record: int, **kwargs) -> dict:
    """Analyze one record live and land it through the SAME gated writes the
    seeded fixtures use. Rules, in order of what they protect:

    - a FINALIZED case (APPROVE/REJECT recorded) is immutable here: a re-run
      must never rewrite the evidence a human already ruled on, so the stored
      document is returned untouched;
    - an undecided existing case gets the guarded evidence refresh;
    - a new case inserts; a concurrent double-insert (double click, second
      client) reconciles by reading the winner instead of erroring;
    - the RETURN VALUE is always the persisted Mongo document, so the dialog
      shows stored truth, never merely what the engine just printed."""
    result = analyze_record(record, **kwargs)
    aid = result["analysis_id"]
    # the time-series lane is written by the PRODUCT LOOP, not only by tests
    # (wired-or-cut: the side-challenge claim must grep to this line): every
    # live analysis streams its window's measured features with provenance
    try:
        sw = result["source_window"]
        regime = result["input_trust"].get("regime") or {}
        # provenance comes from the VALIDATED result, either dialect; the module
        # default would mislabel a nondefault-condition analysis
        condition = (regime.get("condition") or regime.get("condition_id")
                     or kwargs.get("condition", CONDITION))
        st.insert_feature_window(
            db, asset_id=result["asset_id"], condition=condition, window=sw["record"],
            features=result["anomaly_evidence"].get("features") or {},
            source_file=sw["file"], sha256=sw["sha256"])
    except Exception as exc:
        # the diagnostic case is the load-bearing write; a time-series miss is
        # logged, never fatal
        import logging
        logging.getLogger(__name__).warning("feature_window insert skipped: %s", exc)
    doc = st.get_case(db, aid)
    if doc is None:
        try:
            st.insert_case(db, result)
        except DuplicateKeyError:
            pass  # a concurrent analysis won the insert; fall through to readback
        doc = st.get_case(db, aid)
    else:
        # the engine's id does not encode trust context (reported to the engine
        # lane), so a refusal run carries the SAME id as a stored trusted case.
        # The store refuses the write; the adapter must ALSO fail closed rather
        # than hand back the stored trusted document as this run's "result" (an
        # untrusted analysis must never come back decisionable).
        # decided statuses ORIGINATE from the decidable class: a finalized case
        # re-analyzed under full trust is a normal (refused, immutable) refresh,
        # while a refusal-shaped live run against ANY decidable-origin case is
        # the trust collision
        stored_decidable = doc.get("status") in (
            "ANALYST_REVIEW_REQUIRED", "INSPECTION_APPROVED", "INSPECTION_REJECTED")
        live_decidable = result.get("status") == "ANALYST_REVIEW_REQUIRED"
        if stored_decidable != live_decidable:
            raise EngineError(
                f"trust-context identity collision for {aid}: stored "
                f"{doc.get('status')} vs live {result.get('status')}; the live "
                "result was NOT persisted and the stored case is not this run's answer")
        st.refresh_case_evidence(db, result)
        doc = st.get_case(db, aid)
    if doc is None:
        raise EngineError(f"analysis stored then unreadable: {aid}")
    return {f: doc[f] for f in FIELDS}
