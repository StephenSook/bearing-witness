"""The trend chart's y-axis floors at zero. Without rangemode=tozero Plotly
autoscales to the visible span: a healthy screen's 0.02 g of noise fills the
frame and reads as spikes, and the late-life zoom-out flattens the onset step
into a featureless line under the ONSET marker. Found by Vinh at ~17:4x Sat;
one-line presentation fix inside the freeze (claim-correcting: the chart was
miscommunicating measured data). Spectra deliberately keep autoscale."""
from bw_product.ui.charts import trend_figure


def _trend(n=60):
    return {"windows": list(range(1, n + 1)), "rms": [0.5] * n}


def test_trend_yaxis_floors_at_zero():
    fig = trend_figure(_trend(), selected_window=11, onset=59, dark=False)
    assert fig["layout"]["yaxis"]["rangemode"] == "tozero"


def test_trend_marker_still_uses_own_window_value():
    t = _trend()
    t["rms"][10] = 0.77  # window 11
    fig = trend_figure(t, selected_window=11, onset=None, dark=True)
    marker = [d for d in fig["data"] if d.get("name") == "selected"]
    assert marker and marker[0]["y"] == [0.77]
