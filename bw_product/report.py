"""report.html insurance page (PLAN.md 2.9).

Fully self-contained: inline plotly.js, base64 WAV audio, zero network. If
NiceGUI misbehaves on the projector, this file opens from disk and the story
still lands, ending on the decision + evidence + task, never a lone spectrum.

Generate: .venv-product/bin/python -m bw_product.report
"""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
from plotly.offline import get_plotlyjs

from .contract_shape import traffic_light
from .ui import charts
from .ui.theme import GRAPHITE_DEEP, INK, LAMP, LIME, PAPER, PAPER_BRIGHT

FIXTURE_DIR = Path(__file__).parent / "fixtures_data"
OUT = FIXTURE_DIR / "report.html"

CSS = f"""
body {{ background:{PAPER}; color:{INK}; margin:0;
  font-family:'Helvetica Neue', Arial, sans-serif; }}
.wrap {{ max-width:1100px; margin:0 auto; padding:48px 32px; }}
.mono {{ font-family:ui-monospace, 'SF Mono', Menlo, monospace; font-size:11px;
  letter-spacing:0.14em; text-transform:uppercase; }}
.display {{ font-weight:900; text-transform:uppercase; letter-spacing:-0.02em;
  line-height:0.95; font-size:clamp(40px,7vw,92px); }}
.rule {{ border:none; border-top:1px solid rgba(17,21,18,0.18); margin:34px 0 14px 0; }}
.lamp {{ padding:24px; color:{PAPER_BRIGHT}; border-radius:2px; }}
.lamp .state {{ font-family:ui-monospace,monospace; font-size:15px; letter-spacing:0.18em; }}
.card {{ background:{PAPER_BRIGHT}; border:1px solid rgba(17,21,18,0.18);
  border-radius:2px; padding:20px; margin-top:14px; }}
.kv {{ display:flex; gap:8px; align-items:baseline; margin-top:6px; }}
.kv .k {{ opacity:0.6; }} .kv .leader {{ flex:1; border-bottom:1px dotted #999; }}
.kv .v {{ font-weight:700; }}
.hl {{ background:{LIME}; padding:0 6px; }}
.loc {{ font-family:ui-monospace,monospace; font-size:11px; text-decoration:underline;
  text-underline-offset:3px; word-break:break-all; display:block; margin-top:6px; }}
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
@media (max-width:800px) {{ .grid2 {{ grid-template-columns:1fr; }} }}
footer {{ opacity:0.6; margin-top:44px; font-size:10px; line-height:1.7; }}
"""


def _kv(k: str, v: str, hl: bool = False) -> str:
    vv = f'<span class="hl">{html.escape(v)}</span>' if hl else html.escape(v)
    return (f'<div class="kv mono"><span class="k">{html.escape(k)}</span>'
            f'<span class="leader"></span><span class="v">{vv}</span></div>')


def _fig_html(fig_dict: dict) -> str:
    fig = go.Figure(fig_dict)
    return pio.to_html(fig, include_plotlyjs=False, full_html=False,
                       config={"displayModeBar": False})


def _audio_tag(path: Path, label: str) -> str:
    if not path.exists():
        return ""
    b64 = base64.b64encode(path.read_bytes()).decode()
    return (f'<div><div class="mono">{label}</div>'
            f'<audio controls src="data:audio/wav;base64,{b64}"></audio></div>')


def build(out: Path = OUT) -> Path:
    red = json.loads((FIXTURE_DIR / "fixture_red.json").read_text())
    refusal = json.loads((FIXTURE_DIR / "fixture_refusal.json").read_text())
    trend = json.loads((FIXTURE_DIR / "trend.json").read_text())
    r = red["result"]
    lamp = traffic_light(r["status"])
    draft = r["inspection_draft"]

    # same replay discipline as the live UI: the W155 page never plots windows > 155
    trend_fig = charts.trend_figure(charts.clip_trend(trend, 155), 155,
                                    r["anomaly_evidence"]["onset_window"], False)
    ord_fig = charts.spectrum_figure(red["series"]["ordinary"], False,
                                     title="View A · ordinary spectrum", xmax=2000, log_y=True)
    env_fig = charts.spectrum_figure(red["series"]["envelope"], False,
                                     title="View B · envelope spectrum (2-4 kHz demod)",
                                     xmax=450, predicted=r["machine_components"]["predicted_hz"],
                                     peaks=r["envelope_evidence"]["peaks"])

    locators = [loc for fam in r["candidate_families"] for loc in fam["locators"]]
    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        "<title>Bearing Witness · Evidence Report</title>",
        f"<style>{CSS}</style>",
        f"<script>{get_plotlyjs()}</script>",
        "</head><body><div class='wrap'>",
        "<div class='mono'><b>BEARING WITNESS</b> · HERMIT CRAB · SELF-CONTAINED EVIDENCE REPORT</div>",
        "<div class='display'>Detect the change.<br>Explain the spectrum.<br>Escalate with evidence.</div>",
        "<div class='mono' style='margin-top:10px;opacity:0.65'>CHRONOLOGICAL REPLAY OF REAL "
        "XJTU-SY MEASUREMENTS · 25.6 KHZ · 32768 PTS / 1.28 S · DATASET SETPOINTS, NOT LIVE SENSORS</div>",

        "<hr class='rule'><div class='mono'>STAGE 1 · TREND VS THE ASSET'S OWN EARLY BASELINE</div>",
        _fig_html(trend_fig),

        "<hr class='rule'><div class='mono'>STAGE 0 · TRUST & PROVENANCE</div><div class='card'>",
        _kv("asset", r["asset_id"]),
        _kv("trust level", r["input_trust"]["trust_level"]),
        _kv("speed setpoint", "35.0 Hz (documented)"),
        _kv("measured 1x runs", "~34.7 Hz (0.8-1.5% low: slip)", hl=True),
        _kv("bearing", f'{r["input_trust"]["geometry"]["bearing_model"]} · 8 balls'),
        _kv("geometry provenance", "Wang et al. 2020, DOI 10.1109/TR.2018.2882682"),
        _kv("source window", f'{r["source_window"]["file"]} · sha {r["source_window"]["sha256"][:8]}'),
        "</div>",

        "<hr class='rule'><div class='mono'>STAGE 3 · TWO VIEWS, SIDE BY SIDE</div>",
        f"<div class='grid2'><div>{_fig_html(ord_fig)}</div><div>{_fig_html(env_fig)}</div></div>",

        "<div class='mono' style='margin-top:16px'>EVIDENCE LOCATORS</div>",
        "".join(f"<span class='loc'>{html.escape(l)}</span>" for l in locators),

        "<hr class='rule'><div class='mono'>STAGE 4 · A HUMAN SAYS YES</div>",
        f"<div class='lamp' style='background:{LAMP[lamp]};margin-top:12px'>"
        f"<div class='state'>{r['status']}</div>"
        "<div class='mono' style='opacity:0.85;margin-top:6px'>TWO SIGNAL VIEWS SUPPORT AN "
        "INSPECTION DRAFT. HUMAN REVIEW REQUIRED. INSPECT, NEVER REPLACE.</div></div>",
        "<div class='card'>",
        _kv("drafted task", draft["task_type"]),
        f"<div class='display' style='font-size:34px;margin-top:8px'>{html.escape(draft['title'])}</div>",
        f"<div class='mono' style='margin-top:8px;text-transform:none;font-size:12px'>"
        f"{html.escape(draft['recommended_action'])}</div>",
        _kv("not claimed", ", ".join(draft["not_claimed"])),
        _kv("decision state", "AWAITING HUMAN REVIEW · THE LIVE APP RECORDS "
            "APPROVE / REJECT / DEFER TO MONGODB"),
        "</div>",

        "<hr class='rule'><div class='mono'>THE SAME WAVEFORM WITHOUT TRUST</div><div class='card'>",
        _kv("geometry verified", "NO", hl=True),
        _kv("status", refusal["result"]["status"]),
        _kv("localization", "BLOCKED"),
        _kv("task created", refusal["result"]["inspection_draft"]["task_type"], hl=True),
        "</div>",

        "<hr class='rule'><div class='mono'>AUDIO · TWO NATIVE-SPEED 1.28 S RECORDS "
        "(EQUAL LOUDNESS, MEASURED)</div>",
        f"<div class='grid2' style='margin-top:10px'>"
        f"{_audio_tag(FIXTURE_DIR / 'beat_early.wav', 'EARLY · WINDOW 8')}"
        f"{_audio_tag(FIXTURE_DIR / 'beat_late.wav', 'LATE · WINDOW 155')}</div>",

        "<footer class='mono'>"
        "Chronological replay of real XJTU-SY run-to-failure measurements with dataset-provided "
        "setpoints. Dataset-bounded evidence, not plant-wide validation. No RUL, no severity "
        "grading, no autonomous action: a human approves or rejects every draft.<br>"
        "Dataset: Wang, Lei, Li, Li, IEEE Trans. Reliability 69(1), 2020, DOI 10.1109/TR.2018.2882682. "
        "Method context: Randall & Antoni, MSSP 25(2), 2011 (1-2% frequency deviation; sideband rules); "
        "Antoni, MSSP 21(1), 2007 (fast kurtogram)."
        "</footer>",
        "</div></body></html>",
    ]
    out.write_text("".join(parts))
    return out


if __name__ == "__main__":
    p = build()
    print(p, f"{p.stat().st_size / 1e6:.1f} MB")
