"""Trust / provenance panel (PLAN.md 2.6).

Shows what the system is allowed to believe and why: replay context, speed
setpoint vs the measured slip, geometry provenance, and the exact blocks and
tasks the trust gate produced. The slip line is live evidence for why
TRUSTED_FOR_REPLAY is not TRUSTED_MEASURED and why the search windows are
uncertainty-aware (Randall & Antoni 2011: bearing frequencies typically deviate
1-2% from calculated and wander around the mean).
"""
from __future__ import annotations

from nicegui import ui

# The panel renders BOTH nested dialects: the fixtures' transcription
# (bearing_model / n_balls / condition / load_kN, verified on geometry) and the
# live engine's contract (model_number / n_elements / condition_id / load_kn,
# verified on machine_components). Live/watch writes land engine JSON on the
# same analysis ids, so every read below must survive either shape.


def _first(d: dict, *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def geometry_line(geometry: dict) -> str:
    model = _first(geometry, "bearing_model", "model_number", default="?")
    n = _first(geometry, "n_balls", "n_elements", default="?")
    return f"{model} · {n} balls"


def regime_line(regime: dict) -> str:
    cond = _first(regime, "condition", "condition_id", default="?")
    load = _first(regime, "load_kN", "load_kn")
    return f"{cond} · {load:.0f} kN" if load is not None else str(cond)


def geometry_verified(result: dict) -> bool:
    mc = result.get("machine_components") or {}
    if "geometry_verified" in mc:
        return bool(mc["geometry_verified"])
    return bool((result["input_trust"].get("geometry") or {}).get("verified"))


def slip_line(result: dict) -> str:
    measured = (result.get("machine_components") or {}).get("shaft_hz_measured")
    if measured:
        nominal = (result["machine_components"].get("shaft_hz_nominal")
                   or result["input_trust"]["speed"].get("value_hz") or 0) or 0
        pct = f" ({(nominal - measured) / nominal * 100:.1f}% low: slip)" if nominal else ""
        return f"{measured:.2f} Hz{pct}"
    return "~34.7 Hz (0.8-1.5% low: slip, prep measurement)"


def _row(key: str, value: str, accent: bool = False) -> None:
    with ui.element("div").classes("bw-caprow").style("margin-top:6px"):
        ui.label(key.upper()).style("opacity:0.6")
        ui.element("span").classes("leader")
        ui.label(value.upper()).style("font-weight:700" + (";background:var(--lime);color:var(--ink);padding:0 6px" if accent else ""))


def panel(result: dict) -> None:
    trust = result["input_trust"]
    verified = geometry_verified(result)
    with ui.element("div").classes("bw-card w-full").style("cursor:default"):
        ui.label("STAGE 0 · TRUST & PROVENANCE").classes("bw-mono").style("font-weight:700")
        _row("trust level", trust["trust_level"])
        _row("speed source", str(trust["speed"].get("source", "dataset setpoint")))
        setpoint = trust["speed"].get("value_hz")
        if setpoint:
            _row("speed setpoint", f"{setpoint:.1f} Hz")
        _row("measured 1x runs", slip_line(result), accent=True)
        _row("search windows", "max(half bin, 2% x f) - slip-aware")
        _row("bearing", geometry_line(trust.get("geometry") or {}))
        _row("geometry verified", "YES" if verified else "NO - LOCALIZATION BLOCKED",
             accent=not verified)
        _row("geometry provenance", "Wang et al. 2020 (DOI 10.1109/TR.2018.2882682)")
        _row("signal", f'{result["source_window"]["channel"]} · sha {result["source_window"]["sha256"][:8]}')
        _row("regime", regime_line(trust.get("regime") or {}))
        if trust["blocks"]:
            _row("blocks", ", ".join(trust["blocks"]), accent=True)
        if trust["tasks"]:
            _row("tasks created", ", ".join(trust["tasks"]), accent=True)
        for note in trust.get("notes") or []:
            ui.label(str(note).upper()).classes("bw-mono").style("opacity:0.5;margin-top:8px;font-size:9px")
