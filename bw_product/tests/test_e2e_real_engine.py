"""TRUE end-to-end: the REAL engine CLI through the REAL adapter into REAL
Mongo, no stubs anywhere. Needs the XJTU corpus (kit or data/ symlink) and
mongod, so CI skips it honestly; on the dev Mac and the box it runs the exact
loop a judge watches.
"""
import pytest

from bw_product import engine_adapter as ea
from bw_product import store as st
from bw_product.tests.conftest import needs_mongod

try:
    from bw_product.fixtures import data_root
    _CORPUS = True
    data_root()
except Exception:
    _CORPUS = False

needs_corpus = pytest.mark.skipif(
    not _CORPUS, reason="XJTU-SY corpus not mounted (kit drive or data/ symlink)")


@needs_corpus
@needs_mongod
def test_full_loop_red_case_real_engine(db):
    st.init_db(db)
    r = ea.analyze_and_store(db, 155)
    assert r["status"] == "ANALYST_REVIEW_REQUIRED"
    assert r["suspected_location"] == "outer"
    fam = r["candidate_families"][0]
    assert fam["family"] == "BPFO"
    assert 105.0 < fam["found_f0_hz"] < 109.0          # measured, slip-low of 107.9
    assert fam["score_current"] > 9.0                   # frozen family_present floor
    doc = st.get_case(db, r["analysis_id"])
    assert doc is not None and doc["status"] == "ANALYST_REVIEW_REQUIRED"


@needs_corpus
@needs_mongod
def test_full_loop_refusal_real_engine(db):
    st.init_db(db)
    r = ea.analyze_record(155, geometry_unverified=True)
    assert r["status"] == "ABNORMAL_LOCATION_UNCONFIRMED"
    assert r["suspected_location"] is None
    assert r["inspection_draft"]["task_type"] == "VERIFY_BEARING_GEOMETRY"


@needs_corpus
@needs_mongod
def test_full_loop_baseline_honesty_real_engine(db):
    """Window 2 sits inside the 10-window baseline: the engine must refuse to
    judge it (BLOCKED_BASELINE), the exact honesty the watch demo shows."""
    st.init_db(db)
    r = ea.analyze_and_store(db, 2)
    assert r["status"] == "BLOCKED_BASELINE"
