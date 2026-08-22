"""XJTU-SY record IO. One CSV = one 1.28 s record; column 0 is the horizontal channel."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .dsp import FS

HEADER = "Horizontal_vibration_signals,Vertical_vibration_signals"
_NUMERIC_CSV = re.compile(r"^\d+\.csv$")


@dataclass(frozen=True)
class Record:
    index: int
    path: str
    x: np.ndarray
    fs: float
    sha256: str
    channel: str = "horizontal (column 0)"

    @property
    def n(self) -> int:
        return int(len(self.x))

    @property
    def duration_s(self) -> float:
        return self.n / self.fs


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record_path(root, condition: str, bearing: str, index: int) -> Path:
    return Path(root) / condition / bearing / f"{index}.csv"


def count_records(record_dir) -> int:
    return sum(1 for p in Path(record_dir).iterdir() if _NUMERIC_CSV.match(p.name))


def load_record(path, index: int, fs: float = FS, column: int = 0) -> Record:
    x = np.loadtxt(path, delimiter=",", skiprows=1, usecols=column, dtype=float)
    return Record(index=index, path=str(path), x=np.atleast_1d(x), fs=fs, sha256=sha256_file(path))
