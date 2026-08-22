"""Plotly figure builders for the evidence screens.

dataviz discipline: one axis per chart, thin marks, recessive grid, hover layer on
by default, reference lines direct-labeled (never a rainbow), color follows the
entity: the measured signal is always the red trace, calculated expectations are
always navy dashed, lime highlights the currently-selected evidence. Status
colors stay reserved for the lamp.
"""
from __future__ import annotations

from typing import Any

from .theme import GRAPHITE_DEEP, INK, LIME, PAPER, PAPER_BRIGHT, TRACE_MEASURED, TRACE_PREDICTED

MONO = "Geist Mono, ui-monospace, monospace"

# resolution-aware uncertainty half-width (PREP_PLAN rule):
# max(half a bin, 2% of f) with bin = 25600/32768
BIN_HZ = 25600.0 / 32768.0


def half_width(f: float) -> float:
    return max(0.5 * BIN_HZ, 0.02 * f)


def clip_trend(trend: dict, window: int) -> dict:
    """Replay discipline (D9): window k sees only windows 1..k, never the future.
    Shared by the live UI and the insurance report so neither can drift."""
    visible = [i for i, w in enumerate(trend["windows"]) if w <= window]
    return {k: ([v[i] for i in visible] if isinstance(v, list) else v)
            for k, v in trend.items()}


def _layout(dark: bool, title: str, xaxis: str, yaxis: str) -> dict[str, Any]:
    ink = PAPER if dark else INK
    grid = "rgba(239,237,231,0.10)" if dark else "rgba(17,21,18,0.10)"
    return {
        "title": {"text": title.upper(), "font": {"family": MONO, "size": 11, "color": ink},
                  "x": 0.0, "xanchor": "left"},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": MONO, "size": 10, "color": ink},
        "margin": {"l": 46, "r": 12, "t": 34, "b": 40},
        "hovermode": "x unified",
        "hoverlabel": {"font": {"family": MONO, "size": 10}},
        "xaxis": {"title": {"text": xaxis, "font": {"size": 9}}, "gridcolor": grid,
                  "zeroline": False, "linecolor": grid},
        "yaxis": {"title": {"text": yaxis, "font": {"size": 9}}, "gridcolor": grid,
                  "zeroline": False, "linecolor": grid},
        "showlegend": False,
        "dragmode": False,
    }


def trend_figure(trend: dict, selected_window: int, onset: int | None, dark: bool) -> dict:
    ink = PAPER if dark else INK
    data: list[dict[str, Any]] = [
        {"type": "scatter", "mode": "lines", "name": "RMS",
         "x": trend["windows"], "y": trend["rms"],
         "line": {"color": TRACE_MEASURED, "width": 2},
         "hovertemplate": "w%{x} · rms %{y:.2f}<extra></extra>"},
    ]
    # the marker must be the selected window's OWN value; substituting the nearest
    # record would display one real measurement labeled as another
    if selected_window in trend["windows"]:
        data.append(
            {"type": "scatter", "mode": "markers", "name": "selected",
             "x": [selected_window],
             "y": [trend["rms"][trend["windows"].index(selected_window)]],
             "marker": {"size": 11, "color": LIME, "line": {"color": ink, "width": 1.5}},
             "hovertemplate": "window %{x}<extra>selected</extra>"})
    fig: dict[str, Any] = {
        "data": data,
        # XJTU-SY accelerometer amplitude is in g (dataset convention; a failing
        # bearing at 3.7 RMS is plausible in g, absurd in m/s²)
        "layout": _layout(dark, "Stage-1 trend · broadband RMS vs early baseline",
                          "window (1/min)", "rms (g)"),
    }
    # floor the y-axis at 0 for THIS chart only: without it Plotly autoscales to
    # the visible span, so a healthy screen's 0.02 g of noise fills the frame and
    # reads as spikes, while W155's 4 g failure flattens the 0.06 g onset step
    # into an apparently featureless line under the ONSET marker. The detector
    # scores z against the asset's own baseline MAD; the chart shows grams, and
    # a zero floor keeps the grams honest at every zoom. Spectra keep autoscale.
    fig["layout"]["yaxis"]["rangemode"] = "tozero"
    shapes, annotations = [], []
    # baseline region: windows 1-10 (the asset's own early, condition-matched baseline)
    shapes.append({"type": "rect", "x0": 1, "x1": 10, "yref": "paper", "y0": 0, "y1": 1,
                   "fillcolor": TRACE_PREDICTED, "opacity": 0.10, "line": {"width": 0}})
    annotations.append({"x": 5.5, "yref": "paper", "y": 0.97, "text": "BASELINE 1-10",
                        "showarrow": False, "font": {"family": MONO, "size": 9, "color": ink}})
    if onset:
        shapes.append({"type": "line", "x0": onset, "x1": onset, "yref": "paper",
                       "y0": 0, "y1": 1, "line": {"color": ink, "width": 1, "dash": "dot"}})
        annotations.append({"x": onset, "yref": "paper", "y": 0.05, "text": f"ONSET w{onset}",
                            "showarrow": False, "xanchor": "left",
                            "font": {"family": MONO, "size": 9, "color": ink}})
    fig["layout"]["shapes"] = shapes
    fig["layout"]["annotations"] = annotations
    return fig


def spectrum_figure(series: list, dark: bool, *, title: str, xmax: float | None = None,
                    predicted: dict[str, float] | None = None,
                    peaks: list[dict] | None = None, log_y: bool = False) -> dict:
    freqs, amp = series
    ink = PAPER if dark else INK
    fig: dict[str, Any] = {
        "data": [
            {"type": "scatter", "mode": "lines", "name": "measured",
             "x": freqs, "y": amp, "line": {"color": TRACE_MEASURED, "width": 1.6},
             "hovertemplate": "%{x:.2f} Hz · %{y:.4f}<extra></extra>"},
        ],
        "layout": _layout(dark, title, "frequency (Hz)", "amplitude"),
    }
    if xmax:
        fig["layout"]["xaxis"]["range"] = [0, xmax]
    if log_y:
        fig["layout"]["yaxis"]["type"] = "log"
    shapes, annotations = [], []
    for name, f in (predicted or {}).items():
        hw = half_width(f)
        shapes.append({"type": "rect", "x0": f - hw, "x1": f + hw, "yref": "paper",
                       "y0": 0, "y1": 1, "fillcolor": TRACE_PREDICTED, "opacity": 0.12,
                       "line": {"width": 0}})
        shapes.append({"type": "line", "x0": f, "x1": f, "yref": "paper", "y0": 0, "y1": 1,
                       "line": {"color": TRACE_PREDICTED, "width": 1.2, "dash": "dash"}})
        annotations.append({"x": f, "yref": "paper", "y": 1.02, "text": name,
                            "showarrow": False,
                            "font": {"family": MONO, "size": 9, "color": TRACE_PREDICTED}})
    for p in peaks or []:
        # fixture peaks carry an explicit harmonic; engine peaks carry it only
        # inside the label ("BPFO h2"): derive, never crash on live data
        h = p.get("harmonic")
        if h is None:
            tail = str(p.get("label", "")).split("h")[-1]
            h = tail.split()[0] if tail and tail.split() and tail.split()[0].isdigit() else "?"
        annotations.append({"x": p["freq_hz"], "y": p["amp"],
                            "text": f"h{h} · {p['freq_hz']:.2f}",
                            "showarrow": True, "arrowhead": 0, "arrowcolor": ink,
                            "ax": 0, "ay": -26,
                            "font": {"family": MONO, "size": 9, "color": ink},
                            "bgcolor": LIME if not dark else "rgba(216,255,62,0.85)",
                            "bordercolor": INK,
                            "borderpad": 2})
    fig["layout"]["shapes"] = shapes
    fig["layout"]["annotations"] = annotations
    return fig


CONFIG = {"displayModeBar": False, "responsive": True}


def surface_class(dark: bool) -> str:
    return GRAPHITE_DEEP if dark else PAPER_BRIGHT
