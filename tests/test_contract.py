import json
import re

import pytest
from pydantic import ValidationError

from bearing_witness import contract


def test_contract_has_exactly_the_14_spec_fields_in_order():
    assert list(contract.ResultContract.model_fields) == [
        "analysis_id", "asset_id", "source_window", "input_trust", "anomaly_evidence",
        "machine_components", "ordinary_spectrum_evidence", "envelope_evidence", "candidate_families",
        "suspected_location", "status", "refusal_reasons", "inspection_draft", "human_review",
    ]


def test_status_is_constrained():
    with pytest.raises(ValidationError):
        contract.ResultContract.model_validate({**contract.EMPTY, "status": "HEALTHY"})


def test_locator_format():
    loc = contract.locator("XJTU-SY/35Hz12kN/Bearing1_3", 155, "abcdef0123456789", "envelope", 107.03, k=1, m=None)
    assert loc == "XJTU-SY/35Hz12kN/Bearing1_3|w155|abcdef01|envelope|107.03Hz|h1"
    assert contract.locator("A", 1, "ff" * 32, "ordinary", 153.1, k=1, m=+1).endswith("|153.10Hz|h1|sb+1")


def test_locator_regex():
    rx = re.compile(r"^[^|]+\|w\d+\|[0-9a-f]{8}\|(ordinary|envelope)\|\d+\.\d{2}Hz(\|h\d+)?(\|sb[+-]\d+)?$")
    assert rx.match(contract.locator("A", 155, "deadbeefcafe", "envelope", 107.91, k=3))
    assert rx.match(contract.locator("A", 155, "deadbeefcafe", "envelope", 107.91, k=3, m=-1))
    assert rx.match(contract.locator("A", 155, "deadbeefcafe", "ordinary", 35.02))
    with pytest.raises(ValueError):
        contract.locator("A", 155, "deadbeefcafe", "envelope", 107.91, m=1)


def test_empty_contract_round_trips_json():
    r = contract.ResultContract.model_validate(contract.EMPTY)
    assert json.loads(r.model_dump_json())["status"] == "BLOCKED_SIGNAL"
