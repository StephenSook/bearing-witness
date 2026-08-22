import numpy as np

from bearing_witness import data


def _write_csv(p, rows):
    p.write_text("Horizontal_vibration_signals,Vertical_vibration_signals\n" +
                 "\n".join(f"{h},{v}" for h, v in rows) + "\n")


def test_load_record_reads_horizontal_column(tmp_path):
    p = tmp_path / "1.csv"
    _write_csv(p, [(-0.7738, 0.5622), (0.1305, 0.4051), (0.25, 0.1)])
    rec = data.load_record(p, 1)
    assert rec.index == 1
    assert rec.n == 3
    np.testing.assert_allclose(rec.x, [-0.7738, 0.1305, 0.25])
    assert rec.fs == 25600.0
    assert rec.duration_s == 3 / 25600.0
    assert rec.channel == "horizontal (column 0)"
    assert len(rec.sha256) == 64 and rec.sha256 == data.sha256_file(p)


def test_count_records_only_counts_numeric_csvs(tmp_path):
    d = tmp_path / "35Hz12kN" / "Bearing1_9"
    d.mkdir(parents=True)
    for k in (1, 2, 3, 10):
        _write_csv(d / f"{k}.csv", [(0.0, 0.0)])
    (d / "notes.csv").write_text("x")
    assert data.count_records(d) == 4
    assert data.record_path(tmp_path, "35Hz12kN", "Bearing1_9", 10) == d / "10.csv"
