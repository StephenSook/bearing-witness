"""Fixture + store wiring for the UI.

Loads the contract-shaped fixtures (real Bearing1_3 data) and gives every screen
one interface for cases and decisions. Mongo is the backbone when reachable
(cases seeded idempotently, decisions persist via MongoDecisionStore); when it
is not, the UI says so in the HUD and falls back to a local JSON decision log,
mirroring the abandon ladder (file-backed fallback AND the Mongo claim is cut).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .. import store as st
from ..contract_shape import FIELDS

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures_data"

# replay order: one real bearing walked through its life. Scenario windows sit
# ON the engine's own story (verified live 2026-08-22): W11 = first judged
# window after the baseline (W8 would be BLOCKED_BASELINE), W60 = abnormal but
# not yet persistent (the engine's actual WATCH_EARLY window), W155 = two views
# agree. A judge live-analyzing any scenario window gets the same status the
# seeded card shows.
SCENARIOS = {
    "green": {"window": 11, "phase": "BASELINE.", "caption": "first judged window after the baseline"},
    "yellow": {"window": 60, "phase": "DETECT THE CHANGE.", "caption": "the change appears; keep trending"},
    "red": {"window": 155, "phase": "EXPLAIN THE SPECTRUM.", "caption": "two views agree: outer race"},
    "refusal": {"window": 155, "phase": "REFUSE WITHOUT TRUST.", "caption": "geometry unverified: localization blocked"},
}
TOTAL_WINDOWS = 158
FLEET_TOTAL = 15  # XJTU-SY bearings; only Bearing1_3 is loaded as fixtures tonight


def load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / f"fixture_{name}.json").read_text())


def trend() -> dict:
    return json.loads((FIXTURE_DIR / "trend.json").read_text())


EVAL_RESULTS = FIXTURE_DIR.parent.parent / "eval" / "results_v3.json"


def evaluation() -> dict | None:
    """The engine lane's frozen v3 evaluator run (landed Fri 2026-08-21 ~23:5x:
    0 wrong / 10 correct / 1 cage-consistent / 4 abstain / 0 missed over all 15
    bearings, thresholds sha embedded). None when the file is absent, and every
    consumer must render the honest pre-evaluator state in that case."""
    try:
        return json.loads(EVAL_RESULTS.read_text())
    except Exception:
        return None


@dataclass
class Backend:
    kind: str                 # "mongo" | "file"
    store: object             # has .record(analysis_id, decision, reason)
    db: object | None = None
    # scenario names whose Mongo record could not be seeded: their evidence still
    # renders from the fixture, but decisions are disabled (an actionable case
    # with no database record would KeyError on record())
    unpersisted: frozenset = frozenset()
    # scenarios whose STORED record could not be read on the most recent render:
    # the fixture stands in for evidence, but it may hide a persisted decision,
    # so decisions are disabled until a read succeeds again (self-healing)
    degraded: set = field(default_factory=set)

    def decidable_here(self, name: str) -> bool:
        return name not in self.unpersisted and name not in self.degraded

    def case(self, name: str) -> dict:
        """Serve the stored case when readable, the fixture otherwise. A Mongo
        read failure at render time degrades to fixture evidence instead of
        crashing the page, and marks the scenario `degraded` because the fixture
        cannot represent a persisted APPROVE/REJECT; a later successful read
        clears the mark."""
        fx = load(name)["result"]
        if self.kind == "mongo":
            try:
                doc = st.get_case(self.db, fx["analysis_id"])
            except Exception as exc:
                self.degraded.add(name)
                logging.getLogger(__name__).warning(
                    "case read failed for %s, serving fixture evidence, decisions disabled: %s",
                    name, exc)
                return fx
            if doc:
                # only a real document heals: an empty read is absence, not recovery
                self.degraded.discard(name)
                return {f: doc[f] for f in FIELDS}
            if name not in self.unpersisted:
                # the record existed at startup and is gone now (deleteMany without
                # a restart, rollback): the undecided fixture must not become
                # actionable against a vanished record
                self.degraded.add(name)
                logging.getLogger(__name__).warning(
                    "stored case for %s is missing, decisions disabled", name)
        else:
            patch = self.store.cases.get(fx["analysis_id"])
            if patch:
                fx.update(patch)
        return fx


class FileDecisionStore:
    """Same record() shape as MongoDecisionStore; JSON log + in-memory case patch.

    Prior decisions are HYDRATED from the log on startup so a process restart
    cannot defeat the final-decision lock, and the log is written via atomic
    replace. Last-ditch single-process fallback: concurrent writers are out of
    scope (the Mongo store is the concurrent-safe path)."""

    def __init__(self, path: Path):
        self.path = path
        self.cases: dict[str, dict] = {}
        if path.exists():
            for row in json.loads(path.read_text()):
                hr = {k: row[k] for k in ("required", "decision", "reason", "timestamp")}
                patch: dict = {"human_review": hr}
                if row["decision"] == "APPROVE":
                    patch["status"] = "INSPECTION_APPROVED"
                elif row["decision"] == "REJECT":
                    patch["status"] = "INSPECTION_REJECTED"
                self.cases.setdefault(row["analysis_id"], {}).update(patch)

    def record(self, analysis_id: str, decision: str, reason: str):
        if decision not in ("APPROVE", "REJECT", "DEFER"):
            raise ValueError(decision)
        reason = (reason or "").strip()
        if not reason:
            raise ValueError("a stored decision requires a non-empty reason")
        # mirror MongoDecisionStore's gate: only an undecided inspection review
        prior = self.cases.get(analysis_id, {})
        fx = next((load(n)["result"] for n in SCENARIOS
                   if load(n)["result"]["analysis_id"] == analysis_id), None)
        current = {**fx, **prior} if fx else prior
        draft = current.get("inspection_draft") or {}
        if (current.get("status") != "ANALYST_REVIEW_REQUIRED"
                or draft.get("task_type") != "INSPECTION_WORK_ORDER"
                or (current.get("human_review") or {}).get("decision") not in (None, "DEFER")):
            raise st.DecisionConflict(
                f"{analysis_id} not awaiting inspection decision "
                f"(status={current.get('status')}, "
                f"prior_decision={(current.get('human_review') or {}).get('decision')})")
        hr = {"required": True, "decision": decision, "reason": reason,
              "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        rows = json.loads(self.path.read_text()) if self.path.exists() else []
        rows.append({"analysis_id": analysis_id, **hr})
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rows, indent=1))
        tmp.replace(self.path)
        patch: dict = {"human_review": hr}
        if decision == "APPROVE":
            patch["status"] = "INSPECTION_APPROVED"
        elif decision == "REJECT":
            patch["status"] = "INSPECTION_REJECTED"
        self.cases.setdefault(analysis_id, {}).update(patch)
        return type("HR", (), hr)()


def connect_backend() -> Backend:
    """Mongo when reachable, file fallback when NOT. Only the connection layer
    (connect/ping/init) demotes to the file store: a seed or refresh failure on
    one fixture is logged and skipped, because stale-but-served evidence on the
    Mongo path is strictly better than silently abandoning the decided cases
    already stored there (a Mongo-decided case would reappear undecided on an
    empty file log)."""
    try:
        db = st.connect()
        db.client.admin.command("ping")
        st.init_db(db)
    except Exception as exc:
        # the CAUSE matters during demo recovery: auth failure, validator defect,
        # and a plain outage need different fixes, so it goes to the log even
        # though the HUD only shows the generic offline chip
        logging.getLogger(__name__).warning(
            "Mongo unavailable, using file fallback (%s: %s)", type(exc).__name__, exc)
        return Backend("file", FileDecisionStore(FIXTURE_DIR / "decisions_local.json"))
    log = logging.getLogger(__name__)
    unpersisted = set()
    for name in SCENARIOS:
        try:
            fx = load(name)["result"]
            existing = st.get_case(db, fx["analysis_id"])
        except Exception as exc:
            # a post-ping read failure must not crash app startup; the case's
            # persistence is unknown, so its decisions are disabled
            unpersisted.add(name)
            log.warning("existence read failed for %s, decisions disabled: %s", name, exc)
            continue
        if existing is None:
            # initial seed: a case with no database record must never render as
            # actionable (record() would KeyError), so a failure here disables
            # that case's decisions instead of being treated like a refresh blip
            try:
                st.insert_case(db, fx)
            except Exception as exc:
                # the write may have landed anyway (lost ack) or a concurrent
                # seeder may have won the check-then-insert race (DuplicateKey):
                # reconcile by re-reading before declaring the case unpersisted
                try:
                    recheck = st.get_case(db, fx["analysis_id"])
                except Exception:
                    recheck = None
                if recheck is None:
                    unpersisted.add(name)
                    log.warning("seed FAILED for %s, decisions disabled: %s", name, exc)
                else:
                    log.warning("seed race reconciled for %s (record exists): %s", name, exc)
        else:
            try:
                # same analysis_id, regenerated fixture: refresh evidence so the
                # live UI can never contradict the report; the human trail stays
                st.refresh_case_evidence(db, fx)
            except Exception as exc:
                log.warning("refresh skipped for %s: %s", name, exc)
    try:
        geometry = {k: v for k, v in load("red")["result"]["input_trust"]["geometry"].items()
                    if k != "verified"}
        if st.current_asset_config(db, load("red")["result"]["asset_id"]) is None:
            st.put_asset_config(db, load("red")["result"]["asset_id"], geometry,
                                load("red")["result"]["input_trust"]["regime"])
    except Exception as exc:
        logging.getLogger(__name__).warning("asset config seed skipped: %s", exc)
    return Backend("mongo", st.MongoDecisionStore(db), db, unpersisted=frozenset(unpersisted))
