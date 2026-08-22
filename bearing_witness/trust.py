"""Stage 0 — trust. A mathematically correct frequency is still wrong when speed or geometry is wrong.

Trust levels: TRUSTED_MEASURED (per-window telemetry), TRUSTED_FOR_REPLAY (documented setpoint —
XJTU-SY), UNVERIFIED (blocks). Model number is not geometry: geometry is stored per installed bearing.
"""
from __future__ import annotations

from enum import Enum

import numpy as np
from pydantic import BaseModel, Field

from .data import Record
from .dsp import N_EXPECTED, fault_frequencies


class TrustLevel(str, Enum):
    TRUSTED_MEASURED = "TRUSTED_MEASURED"
    TRUSTED_FOR_REPLAY = "TRUSTED_FOR_REPLAY"
    UNVERIFIED = "UNVERIFIED"


class SpeedContext(BaseModel):
    value_hz: float
    source: str
    trust: TrustLevel
    uncertainty_rel: float = 0.02
    vfd_state: str | None = None


class Geometry(BaseModel):
    n_elements: int
    d_mm: float
    D_mm: float
    contact_angle_deg: float = 0.0
    source: str
    trust: TrustLevel
    model_number: str | None = None


class Regime(BaseModel):
    condition_id: str
    load_kn: float | None = None
    source: str
    trust: TrustLevel


class Acquisition(BaseModel):
    fs_hz: float
    channel: str
    axis: str
    source: str
    trust: TrustLevel
    n_expected: int = N_EXPECTED


class MachineMap(BaseModel):
    shaft_orders: int = 10
    line_hz: float | None = None
    gear_teeth: list[int] = Field(default_factory=list)
    blades: list[int] = Field(default_factory=list)
    notes: str = ""


class AssetContext(BaseModel):
    asset_id: str
    speed: SpeedContext
    geometry: Geometry
    regime: Regime
    acquisition: Acquisition
    machine_map: MachineMap = Field(default_factory=MachineMap)

    def fault_frequencies(self) -> dict[str, float]:
        g = self.geometry
        return fault_frequencies(self.speed.value_hz, g.n_elements, g.d_mm, g.D_mm, g.contact_angle_deg)


class TrustResult(BaseModel):
    trust_level: TrustLevel
    signal_ok: bool
    blocks: list[str]     # ORDER_ANALYSIS | LOCALIZATION | BASELINE_COMPARISON | ALL
    tasks: list[str]      # MEASURE_SHAFT_SPEED | VERIFY_BEARING_GEOMETRY | RECAPTURE_SIGNAL
    notes: list[str]


XJTU_CONDITIONS: dict[str, tuple[float, float]] = {  # condition -> (shaft Hz, radial load kN)
    "35Hz12kN": (35.0, 12.0),
    "37.5Hz11kN": (37.5, 11.0),
    "40Hz10kN": (40.0, 10.0),
}


def xjtu_context(condition: str, bearing: str) -> AssetContext:
    f, load = XJTU_CONDITIONS[condition]
    paper = "Lei et al. 2019, XJTU-SY dataset tutorial (documented test condition)"
    return AssetContext(
        asset_id=f"XJTU-SY/{condition}/{bearing}",
        speed=SpeedContext(value_hz=f, source=paper + " — setpoint, not per-window telemetry",
                           trust=TrustLevel.TRUSTED_FOR_REPLAY, uncertainty_rel=0.02),
        geometry=Geometry(n_elements=8, d_mm=7.92, D_mm=34.55, contact_angle_deg=0.0,
                          source=paper, trust=TrustLevel.TRUSTED_FOR_REPLAY, model_number="LDK UER204"),
        regime=Regime(condition_id=condition, load_kn=load, source=paper, trust=TrustLevel.TRUSTED_FOR_REPLAY),
        acquisition=Acquisition(fs_hz=25600.0, channel="horizontal (column 0)", axis="horizontal",
                                source="XJTU-SY CSV header", trust=TrustLevel.TRUSTED_FOR_REPLAY),
        machine_map=MachineMap(shaft_orders=10, line_hz=None, notes="test rig: motor-driven shaft, no gears/belts/vanes documented"),
    )


def with_unverified(ctx: AssetContext, field: str) -> AssetContext:
    """Copy of ctx with one input (speed|geometry|regime|acquisition) marked UNVERIFIED. Demo step 7."""
    sub = getattr(ctx, field).model_copy(update={"trust": TrustLevel.UNVERIFIED})
    return ctx.model_copy(update={field: sub})


def _signal_checks(ctx: AssetContext, rec: Record) -> list[str]:
    notes = []
    if rec.n != ctx.acquisition.n_expected:
        notes.append(f"SAMPLE_COUNT_{rec.n}_EXPECTED_{ctx.acquisition.n_expected}")
    if rec.fs != ctx.acquisition.fs_hz:
        notes.append(f"FS_{rec.fs}_EXPECTED_{ctx.acquisition.fs_hz}")
    x = np.asarray(rec.x, dtype=float)
    if x.size and not np.all(np.isfinite(x)):
        notes.append("NON_FINITE_SAMPLES")
    elif x.size:
        peak = float(np.max(np.abs(x)))
        if peak > 0:
            frac = float(np.mean(np.abs(x) >= 0.999 * peak))
            if frac > 1e-3:
                notes.append(f"CLIPPING_SUSPECTED_{frac:.4f}")
        else:
            notes.append("FLATLINE")
    return notes


def evaluate_trust(ctx: AssetContext, rec: Record) -> TrustResult:
    blocks, tasks, notes = [], [], []
    sig = _signal_checks(ctx, rec)
    if sig:
        return TrustResult(trust_level=TrustLevel.UNVERIFIED, signal_ok=False, blocks=["ALL"],
                           tasks=["RECAPTURE_SIGNAL"], notes=sig)
    if ctx.speed.trust == TrustLevel.UNVERIFIED:
        blocks += ["ORDER_ANALYSIS", "LOCALIZATION"]; tasks.append("MEASURE_SHAFT_SPEED"); notes.append("SPEED_UNVERIFIED")
    if ctx.geometry.trust == TrustLevel.UNVERIFIED:
        if "LOCALIZATION" not in blocks:
            blocks.append("LOCALIZATION")
        tasks.append("VERIFY_BEARING_GEOMETRY"); notes.append("GEOMETRY_UNVERIFIED")
    if ctx.regime.trust == TrustLevel.UNVERIFIED:
        blocks.append("BASELINE_COMPARISON"); notes.append("REGIME_UNVERIFIED")
    if ctx.acquisition.trust == TrustLevel.UNVERIFIED:
        blocks.append("ALL"); tasks.append("RECAPTURE_SIGNAL"); notes.append("ACQUISITION_UNVERIFIED")
    levels = [ctx.speed.trust, ctx.geometry.trust, ctx.regime.trust, ctx.acquisition.trust]
    if TrustLevel.UNVERIFIED in levels:
        level = TrustLevel.UNVERIFIED
    elif TrustLevel.TRUSTED_FOR_REPLAY in levels:
        level = TrustLevel.TRUSTED_FOR_REPLAY
    else:
        level = TrustLevel.TRUSTED_MEASURED
    return TrustResult(trust_level=level, signal_ok=True, blocks=blocks, tasks=tasks, notes=notes)
