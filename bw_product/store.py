"""MongoDB backbone for the product loop (PLAN.md 2.1 + 2.2).

Three collections, per BUILD_SPEC 2.5 and the Shared Contracts table:

  asset_configs      regular, schema-validated, immutable versions (insert-only; a
                     version is never edited, corrections are a new version)
  feature_windows    time-series (raw waveforms stay files; this holds per-window
                     features, source path, sha256)
  diagnostic_cases   regular, schema-validated, unique analysis_id, embedded task

The deterministic Python tools own all reads and writes. Task creation is a
conditional single-document update: no work order without its evidence record.
`MongoDecisionStore` implements the engine lane's DecisionStore.record() protocol
structurally; the returned object matches HumanReview field-for-field.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from .contract_shape import DECISIONS, FIELDS, STATUSES, TASK_TYPES

MONGO_URI = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017/bearing_witness")
DB_NAME = "bearing_witness"

# The one status whose inspection work order a human may APPROVE/REJECT/DEFER.
_DECIDABLE_STATUS = "ANALYST_REVIEW_REQUIRED"
# Statuses that may carry a non-inspection remediation task (geometry, speed, recapture).
_BLOCKED_STATUSES = ("BLOCKED_SIGNAL", "BLOCKED_BASELINE", "ABNORMAL_LOCATION_UNCONFIRMED")


class DecisionConflict(RuntimeError):
    """The case exists but is not awaiting an inspection decision (wrong status,
    wrong task type, or a decision is already recorded)."""


@dataclass
class HumanReview:
    required: bool
    decision: str | None = None
    reason: str | None = None
    timestamp: str | None = None


_INSPECTION_DRAFT_SCHEMA = {
    "bsonType": ["object", "null"],
    "properties": {
        "task_type": {"enum": list(TASK_TYPES)},
        "title": {"bsonType": "string"},
        "asset_id": {"bsonType": "string"},
        "suspected_element": {"bsonType": ["string", "null"]},
        "evidence_locators": {"bsonType": "array"},
        "recommended_action": {"bsonType": "string"},
        "not_claimed": {"bsonType": "array"},
    },
}

_CASE_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": list(FIELDS),
        "properties": {
            "analysis_id": {"bsonType": "string", "minLength": 1},
            "asset_id": {"bsonType": "string"},
            "source_window": {"bsonType": "object"},
            "input_trust": {"bsonType": "object"},
            "anomaly_evidence": {"bsonType": "object"},
            "machine_components": {"bsonType": "object"},
            "ordinary_spectrum_evidence": {"bsonType": "object"},
            "envelope_evidence": {"bsonType": "object"},
            "candidate_families": {"bsonType": "array"},
            "suspected_location": {"bsonType": ["string", "null"]},
            "status": {"enum": list(STATUSES)},
            "refusal_reasons": {"bsonType": "array"},
            "inspection_draft": _INSPECTION_DRAFT_SCHEMA,
            "human_review": {"bsonType": ["object", "null"]},
        },
    }
}

_ASSET_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["asset_id", "version", "geometry", "regime", "created_at"],
        "properties": {
            "asset_id": {"bsonType": "string", "minLength": 1},
            "version": {"bsonType": "int", "minimum": 1},
            "geometry": {
                "bsonType": "object",
                "required": ["bearing_model", "n_balls", "ball_diameter_mm",
                             "pitch_diameter_mm", "contact_angle_deg", "provenance"],
            },
            "regime": {"bsonType": "object"},
            "created_at": {"bsonType": "string"},
        },
    }
}


def connect(uri: str = MONGO_URI) -> Database:
    return MongoClient(uri, serverSelectionTimeoutMS=2000)[DB_NAME]


def init_db(db: Database) -> None:
    """Create the collections, then enforce validators and indexes on EVERY startup.

    collMod + create_index run unconditionally so a collection created by an older
    version (or another lane's bring-up) cannot keep stale or missing validation.
    feature_windows is a time-series collection; MongoDB does not support JSON-schema
    validators on time-series collections, so its shape is enforced by the writer.
    Duplicate data that blocks the unique index raises here: fail closed.
    """
    names = set(db.list_collection_names())
    if "asset_configs" not in names:
        db.create_collection("asset_configs")
    db.command("collMod", "asset_configs",
               validator=_ASSET_VALIDATOR, validationLevel="strict", validationAction="error")
    db.asset_configs.create_index(
        [("asset_id", ASCENDING), ("version", ASCENDING)], unique=True)
    if "feature_windows" not in names:
        db.create_collection(
            "feature_windows",
            timeseries={"timeField": "ts", "metaField": "meta", "granularity": "seconds"})
    if "diagnostic_cases" not in names:
        db.create_collection("diagnostic_cases")
    db.command("collMod", "diagnostic_cases",
               validator=_CASE_VALIDATOR, validationLevel="strict", validationAction="error")
    db.diagnostic_cases.create_index([("analysis_id", ASCENDING)], unique=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- asset_configs: immutable versions ---------------------------------------

def insert_asset_config_version(db: Database, asset_id: str, version: int,
                                geometry: dict, regime: dict) -> None:
    db.asset_configs.insert_one({
        "asset_id": asset_id, "version": int(version), "geometry": geometry,
        "regime": regime, "created_at": _now(),
    })


def put_asset_config(db: Database, asset_id: str, geometry: dict, regime: dict) -> int:
    """Append the next immutable version for this asset; returns the new version.

    Read-then-insert races are resolved by the unique (asset_id, version) index:
    the loser's DuplicateKeyError re-reads and retries instead of surfacing.
    Immutability is insert-only by convention in this codebase; nothing calls
    update/delete on asset_configs.
    """
    for _ in range(5):
        latest = current_asset_config(db, asset_id)
        version = (latest["version"] + 1) if latest else 1
        try:
            insert_asset_config_version(db, asset_id, version, geometry, regime)
            return version
        except DuplicateKeyError:
            continue
    raise RuntimeError(f"asset config version contention for {asset_id}")


def current_asset_config(db: Database, asset_id: str) -> dict | None:
    return db.asset_configs.find_one({"asset_id": asset_id}, sort=[("version", -1)])


# --- feature_windows: time-series --------------------------------------------

def insert_feature_window(db: Database, asset_id: str, condition: str, window: int,
                          features: dict, source_file: str, sha256: str,
                          ts: datetime | None = None) -> None:
    db.feature_windows.insert_one({
        "ts": ts or datetime.now(timezone.utc),
        "meta": {"asset_id": asset_id, "condition": condition},
        "window": int(window), "features": features,
        "source_file": source_file, "sha256": sha256,
    })


# --- diagnostic_cases ---------------------------------------------------------

def insert_case(db: Database, result: dict[str, Any]) -> None:
    """Insert a contract-shaped case. The task/status relationship is enforced here
    because a JSON-schema validator cannot relate two fields: an INSPECTION_WORK_ORDER
    may only ride on ANALYST_REVIEW_REQUIRED; other task types (geometry, speed,
    recapture, review) only on blocked/unconfirmed statuses."""
    doc = {f: result[f] for f in FIELDS}
    draft = doc.get("inspection_draft")
    if draft is not None:
        _check_draft_status(draft.get("task_type"), doc.get("status"))
    doc["created_at"] = _now()
    db.diagnostic_cases.insert_one(doc)


def _check_draft_status(task_type: str | None, status: str | None) -> None:
    if task_type not in TASK_TYPES:
        raise ValueError(f"bad task_type: {task_type!r}")
    if task_type == "INSPECTION_WORK_ORDER":
        if status != _DECIDABLE_STATUS:
            raise ValueError(
                f"INSPECTION_WORK_ORDER requires status {_DECIDABLE_STATUS}, got {status!r}")
    elif status not in _BLOCKED_STATUSES:
        raise ValueError(
            f"{task_type} requires a blocked/unconfirmed status, got {status!r}")


def get_case(db: Database, analysis_id: str) -> dict | None:
    return db.diagnostic_cases.find_one({"analysis_id": analysis_id})


def recorded_windows(db: Database) -> set[int]:
    """Window numbers that already have a case on record. The watch loop reads
    this at start so a restarted agent resumes where the DATABASE says it left
    off instead of replaying from window 1: the loop's memory is Mongo, not the
    process. On a failed query, return empty and log the cause: the loop then
    replays from the start, which is safe (duplicate inserts reconcile by
    readback) and merely slower, never silent data loss."""
    try:
        return {int(w) for w in db.diagnostic_cases.distinct("source_window.record")
                if w is not None}
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("recorded_windows query failed: %s", exc)
        return set()


# fields a fixture regeneration may refresh; identity and the human trail never move
_EVIDENCE_FIELDS = tuple(f for f in FIELDS if f not in ("analysis_id", "status", "human_review"))


def refresh_case_evidence(db: Database, result: dict[str, Any]) -> bool:
    """Bring a stored case's evidence up to date with a regenerated fixture that
    kept the same analysis_id, WITHOUT touching the human trail: a recorded
    decision, its status, and the draft it ruled on are preserved. Returns True
    when the stored doc changed. Kills the drift class where Mongo serves
    pre-hardening evidence while the report reads the corrected JSON.

    The regenerated payload passes the same task/status gate as insert_case
    (refresh must not be a side door for pairs insert would refuse), and the
    write is compare-and-set on the EXACT observed decision (None, DEFER, or the
    final value) so neither a final decision nor a DEFER note landing between
    the read and the write is ever overwritten. Identity is analysis_id: the
    caller is trusted to pass the regenerated payload for the same logical case.

    DECIDED CASES ARE IMMUTABLE HERE, for every caller: correcting a decided
    case's evidence would leave a human's recorded reason attached to evidence
    they never saw; a correction is a new analysis, never an in-place update.
    The CAS guard also closes the mid-flight race: a decision landing between
    read and write mismatches the guard, the retry re-reads, observes it, and
    returns False instead of writing."""
    draft = result.get("inspection_draft")
    if draft is not None:
        _check_draft_status(draft.get("task_type"), result.get("status"))
    for _ in range(3):
        doc = get_case(db, result["analysis_id"])
        if doc is None:
            return False
        observed = (doc.get("human_review") or {}).get("decision")
        decided = observed in ("APPROVE", "REJECT")
        if decided:
            # a decided record is immutable, full stop (whole-repo audit finding:
            # evidence must never change beneath a recorded decision; supersession
            # would be a NEW analysis id, never an in-place update)
            return False
        # identity-ambiguity guard: the engine's analysis_id does not encode trust
        # context, so a refusal-shaped payload can carry the SAME id as a stored
        # trusted red case (verified live 2026-08-22). Refusing status-CLASS
        # crossings keeps a live unverified run from clobbering the trusted case.
        if (doc.get("status") == _DECIDABLE_STATUS) != (result.get("status") == _DECIDABLE_STATUS):
            return False
        fields = list(_EVIDENCE_FIELDS)
        update = {f: result[f] for f in fields if doc.get(f) != result[f]}
        if not decided and doc.get("status") != result["status"]:
            update["status"] = result["status"]
            # a standing DEFER is human trail too: only a pristine review resets
            if observed is None:
                update["human_review"] = result["human_review"]
        if not update:
            return False
        res = db.diagnostic_cases.update_one(
            {"analysis_id": result["analysis_id"], "human_review.decision": observed},
            {"$set": update})
        if res.matched_count:
            return True
        # the review state changed under us; re-read and recompute
    raise RuntimeError(f"refresh contention for {result['analysis_id']}")


def attach_inspection_task(db: Database, analysis_id: str, draft: dict) -> dict | None:
    """Conditional single-document update: the embedded task is created only when the
    gate state is present AND no draft exists yet (attach is create-once, never
    overwrite). Returns the updated doc, or None when the gate refused."""
    task_type = draft.get("task_type")
    if task_type not in TASK_TYPES:
        raise ValueError(f"bad task_type: {task_type!r}")
    status_filter: dict[str, Any] = (
        {"status": _DECIDABLE_STATUS} if task_type == "INSPECTION_WORK_ORDER"
        else {"status": {"$in": list(_BLOCKED_STATUSES)}})
    return db.diagnostic_cases.find_one_and_update(
        {"analysis_id": analysis_id, "inspection_draft": None, **status_filter},
        {"$set": {"inspection_draft": draft}},
        return_document=True,
    )


# --- Stage 4: the human decision ----------------------------------------------

_DECISION_STATUS = {"APPROVE": "INSPECTION_APPROVED", "REJECT": "INSPECTION_REJECTED"}


class MongoDecisionStore:
    """Same record() signature as the engine's JsonDecisionStore. Approval and
    rejection both persist; the evidence record is retained either way."""

    def __init__(self, db: Database):
        self.db = db

    def record(self, analysis_id: str, decision: str, reason: str) -> HumanReview:
        """Compare-and-set: the decision lands only on a case that is awaiting
        inspection review (ANALYST_REVIEW_REQUIRED, an INSPECTION_WORK_ORDER draft,
        no prior FINAL decision). Anything else raises instead of silently
        overwriting, so a refusal case can never become INSPECTION_APPROVED and a
        final decision is never erased. Accepted scope: a repeated DEFER updates
        the standing DEFER's reason/timestamp (single-analyst demo; an append-only
        review history is the production shape, out of scope here)."""
        if decision not in DECISIONS:
            raise ValueError(f"bad decision: {decision!r} (allowed: {DECISIONS})")
        reason = (reason or "").strip()
        if not reason:
            # the audit trail is the product: a final decision with no reason is
            # not recordable through ANY caller, not just the UI's client check
            raise ValueError("a stored decision requires a non-empty reason")
        hr = HumanReview(required=True, decision=decision, reason=reason, timestamp=_now())
        update: dict[str, Any] = {"human_review": hr.__dict__}
        if decision in _DECISION_STATUS:
            update["status"] = _DECISION_STATUS[decision]
        doc = self.db.diagnostic_cases.find_one_and_update(
            {"analysis_id": analysis_id,
             "status": _DECIDABLE_STATUS,
             "inspection_draft.task_type": "INSPECTION_WORK_ORDER",
             # DEFER stays revisitable; APPROVE/REJECT are final (they also flip
             # the status out of _DECIDABLE_STATUS, a second lock)
             "human_review.decision": {"$in": [None, "DEFER"]}},
            {"$set": update}, return_document=True)
        if doc is None:
            existing = self.db.diagnostic_cases.find_one({"analysis_id": analysis_id})
            if existing is None:
                raise KeyError(f"unknown analysis_id: {analysis_id}")
            prior = (existing.get("human_review") or {}).get("decision")
            raise DecisionConflict(
                f"{analysis_id} not awaiting inspection decision "
                f"(status={existing['status']}, prior_decision={prior})")
        return hr
