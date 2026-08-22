"""Bearing Witness -- mock-data NiceGUI dashboard (PREP_PLAN item 6, learning exercise).

Plain NiceGUI + ui.echart only. No external CDNs, no CSS frameworks.
Serves fixtures.json (3 mock analyses: GREEN / YELLOW / RED) on port 8123.
Approve/Reject both append {"decision","reason","timestamp"} to decisions.json.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from nicegui import ui

BASE = Path(__file__).resolve().parent
FIXTURES = json.loads((BASE / 'fixtures.json').read_text())
DECISIONS_PATH = BASE / 'decisions.json'

# Deterministic state string -> lamp color. The state STRING is always rendered
# under the lamp (spec rule: never color alone).
STATE_COLORS = {
    'NO_ANOMALY_DETECTED': '#1e9e5a',
    'ABNORMAL_LOCATION_UNCONFIRMED': '#d99a06',
    'ANALYST_REVIEW_REQUIRED': '#cc3232',
}
BPFO_MARK_HZ = 107.9

selection = {'analysis_id': 'A-B13-140'}  # default to the RED fixture


def get_analysis(analysis_id: str) -> dict:
    return next(a for a in FIXTURES if a['analysis_id'] == analysis_id)


def record_decision(decision: str, reason: str) -> dict:
    """Append a decision record to decisions.json.

    BOTH Approve and Reject go through this single write path (spec rule:
    both paths must write). Record shape is exactly
    {"decision", "reason", "timestamp"}.
    """
    entry = {
        'decision': decision,
        'reason': (reason or '').strip() or '(no reason given)',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    try:
        existing = json.loads(DECISIONS_PATH.read_text())
        assert isinstance(existing, list)
    except Exception:
        existing = []
    existing.append(entry)
    DECISIONS_PATH.write_text(json.dumps(existing, indent=2))
    return entry


# ---------------------------------------------------------------- mock series
def feature_trend(current_record: int):
    """Mock per-record RMS trend over the 158-record life (deterministic)."""
    xs = list(range(1, 159))
    ys = []
    for r in xs:
        base = 0.60 + 0.0012 * r
        if r > 100:
            base += 0.0035 * (r - 100) ** 1.35
        wiggle = 0.02 * math.sin(r * 1.7) + 0.012 * math.sin(r * 0.53 + 1.0)
        ys.append(round(base + wiggle, 4))
    return xs, ys


def envelope_spectrum(analysis: dict):
    """Mock envelope spectrum 0-500 Hz: noise floor + Lorentzian bumps at the
    fixture's envelope_evidence peaks."""
    peaks = analysis['envelope_evidence']['peaks']
    pts = []
    for i in range(0, 1001):
        f = 0.5 * i
        a = 0.0018 + 0.0006 * abs(math.sin(f * 0.11))
        for p in peaks:
            a += p['amp'] / (1.0 + ((f - p['freq_hz']) / 0.9) ** 2)
        pts.append([round(f, 1), round(a, 5)])
    return pts


# ------------------------------------------------------------------ dashboard
@ui.refreshable
def dashboard() -> None:
    a = get_analysis(selection['analysis_id'])
    status = a['status']
    color = STATE_COLORS[status]
    rec = a['source_window']['record']

    with ui.row().classes('w-full items-start q-gutter-md'):
        # --- traffic light: color lamp with the state string ALWAYS under it
        with ui.card().classes('traffic-light items-center'):
            ui.element('div').style(
                f'width:72px;height:72px;border-radius:50%;background:{color};'
                'border:3px solid #444;box-shadow:0 0 14px ' + color + ';')
            ui.label(status).classes('state-string font-mono text-base text-center')
            ui.label(f"asset: {a['asset_id']}").classes('text-xs')
            ui.label(f"window: record {rec}").classes('text-xs')

        # --- feature trend chart
        with ui.card().classes('grow'):
            ui.label('Feature trend (RMS per record, mock)').classes('text-sm')
            xs, ys = feature_trend(rec)
            ui.echart({
                'grid': {'left': 45, 'right': 15, 'top': 20, 'bottom': 30},
                'xAxis': {'type': 'category', 'data': xs, 'name': 'record'},
                'yAxis': {'type': 'value', 'name': 'RMS (g)'},
                'series': [{
                    'type': 'line', 'data': ys, 'showSymbol': False,
                    'lineStyle': {'width': 1.5},
                    'markLine': {'symbol': 'none',
                                 'label': {'formatter': f'this window (rec {rec})'},
                                 'data': [{'xAxis': rec}]},
                }],
            }).classes('h-56 w-full')

        # --- envelope spectrum chart with BPFO marker
        with ui.card().classes('grow'):
            ui.label('Envelope spectrum (mock) -- BPFO line at 107.9 Hz').classes('text-sm')
            ui.echart({
                'grid': {'left': 50, 'right': 15, 'top': 20, 'bottom': 30},
                'xAxis': {'type': 'value', 'name': 'Hz', 'max': 500},
                'yAxis': {'type': 'value', 'name': 'env amp'},
                'series': [{
                    'type': 'line', 'data': envelope_spectrum(a),
                    'showSymbol': False, 'lineStyle': {'width': 1},
                    'markLine': {'symbol': 'none',
                                 'lineStyle': {'color': '#cc3232', 'type': 'dashed'},
                                 'label': {'formatter': f'BPFO {BPFO_MARK_HZ}'},
                                 'data': [{'xAxis': BPFO_MARK_HZ}]},
                }],
            }).classes('h-56 w-full')

    with ui.row().classes('w-full items-start q-gutter-md'):
        # --- evidence panel: locators
        with ui.card().classes('evidence-panel grow'):
            ui.label('Evidence locators').classes('text-lg')
            sw = a['source_window']
            ui.label(f"asset: {a['asset_id']}")
            ui.label(f"window: record {sw['record']} -- {sw['file']} "
                     f"({sw['n_samples']} samples @ {sw['fs_hz']} Hz, {sw['channel']})")
            ui.label(f"source sha256: {sw['sha256']}")
            ui.label(f"input trust: {a['input_trust']['trust_level']}")
            ui.label(f"anomaly: RMS {a['anomaly_evidence']['rms_g']} g "
                     f"({a['anomaly_evidence']['rms_ratio']}x baseline), "
                     f"kurtosis {a['anomaly_evidence']['kurtosis']} -- "
                     f"{a['anomaly_evidence']['verdict']}")
            band = a['envelope_evidence']['band_hz']
            ui.label(f"envelope band: {band[0]}-{band[1]} Hz")
            if a['envelope_evidence']['peaks']:
                for p in a['envelope_evidence']['peaks']:
                    ui.label(f"envelope peak: {p['freq_hz']} Hz "
                             f"(amp {p['amp']}, SNR {p['snr_db']} dB)")
            else:
                ui.label('envelope peaks: none above threshold')
            for fam in a['candidate_families']:
                ui.label(f"family {fam['family']}: f0={fam['f0_measured_hz']} Hz, "
                         f"harmonics {fam['harmonics_detected_hz']}, "
                         f"sidebands present: {fam['sidebands_present']}, "
                         f"score {fam['score']}")
            ui.label(f"suspected location: {a['suspected_location']}").classes('font-bold')

        # --- refusal reasons
        with ui.card().classes('refusal-panel grow'):
            ui.label('Refusal reasons').classes('text-lg')
            if a['refusal_reasons']:
                for r in a['refusal_reasons']:
                    ui.label(f"[{r['code']}] {r['detail']}")
                    ui.label(f"required action: {r['required_action']}").classes('font-bold text-amber-8')
            else:
                ui.label('none')

        # --- inspection draft + human review decision
        with ui.card().classes('draft-panel grow'):
            ui.label('Inspection draft').classes('text-lg')
            draft = a['inspection_draft']
            if draft is None:
                ui.label('No inspection draft for this analysis.')
            else:
                ui.label(draft['title']).classes('font-bold')
                ui.label(draft['summary']).classes('text-sm')
                loc = draft['evidence_locators']
                ui.label(f"cites: asset={loc['asset']} | window={loc['window']} | "
                         f"sha256={loc['source_sha256']} | f0={loc['fundamental_hz']} Hz | "
                         f"harmonics={loc['harmonics_hz']} | "
                         f"sidebands@{loc['sidebands']['spacing_checked_hz']} Hz "
                         f"present={loc['sidebands']['present']}").classes('text-xs font-mono')
                ui.label(f"recommended: {draft['recommended_action']}").classes('text-sm')
            reason_in = ui.input('Reviewer reason (optional)').props('id=reason-input').classes('w-full')

            def on_decision(decision: str) -> None:
                entry = record_decision(decision, reason_in.value)
                ui.notify(f"recorded: {entry['decision']} @ {entry['timestamp']}")

            with ui.row():
                ui.button('Approve', on_click=lambda: on_decision('approved')) \
                    .props('id=approve-btn color=positive' + (' disable' if draft is None else ''))
                ui.button('Reject', on_click=lambda: on_decision('rejected')) \
                    .props('id=reject-btn color=negative' + (' disable' if draft is None else ''))


# ---------------------------------------------------------------------- page
ui.label('Bearing Witness -- mock dashboard').classes('text-2xl')
ui.select(
    {a['analysis_id']: f"{a['asset_id']} | rec {a['source_window']['record']} | {a['status']}"
     for a in FIXTURES},
    value=selection['analysis_id'],
    label='Asset / analysis',
    on_change=lambda e: (selection.update(analysis_id=e.value), dashboard.refresh()),
).classes('w-96').props('id=asset-select')
dashboard()

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(port=8123, show=False, reload=False, title='Bearing Witness (mock)')
