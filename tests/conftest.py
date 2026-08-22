from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO / "data" / "XJTU-SY_Bearing_Datasets"
B13 = DATA_ROOT / "35Hz12kN" / "Bearing1_3"

requires_data = pytest.mark.skipif(not B13.exists(), reason="XJTU-SY corpus not present under data/")


@pytest.fixture(scope="session")
def data_root():
    return DATA_ROOT


@pytest.fixture(scope="session")
def b13_dir():
    return B13
