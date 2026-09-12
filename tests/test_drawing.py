"""Tests for lines-plan drawing and offsets export (plan task 2.4)."""

import csv
from pathlib import Path

import numpy as np

from openhull.drawing import draw_lines_plan, save_offsets_csv
from openhull.geometry import load_offsets_csv

CSV = Path(__file__).resolve().parents[1] / "examples" / "data" / \
    "parent_hull_offsets.csv"


def series60():
    return load_offsets_csv(str(CSV), lpp=280.0, beam=45.0, draft=16.5)


def test_draw_lines_plan_writes_png(tmp_path):
    table = series60()
    out = tmp_path / "lines.png"
    written = draw_lines_plan(table, str(out), title="test sheet")
    assert Path(written) == out
    assert out.stat().st_size > 50_000   # a real sheet, not a blank canvas
    with open(out, "rb") as fh:
        assert fh.read(8) == b"\x89PNG\r\n\x1a\n"


def test_save_offsets_csv_layout(tmp_path):
    table = series60()
    out = tmp_path / "offsets.csv"
    save_offsets_csv(table, str(out))
    rows = list(csv.reader(out.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == table.stations.size + 1          # header + stations
    assert len(rows[0]) == table.waterlines.size + 1     # station + WLs
    assert rows[0][0] == "station_m"
    body = np.array([[float(v) for v in r] for r in rows[1:]])
    assert np.allclose(body[:, 0], table.stations, atol=1e-3)
    assert np.allclose(body[:, 1:], table.half_breadths, atol=5e-5)


def test_transformed_table_round_trips_through_export(tmp_path):
    from openhull.linesplan import lackenby_transform
    table = series60()
    transformed, _report = lackenby_transform(table, delta_cb=0.02)
    out = tmp_path / "offsets_transformed.csv"
    save_offsets_csv(transformed, str(out))
    rows = list(csv.reader(out.read_text(encoding="utf-8").splitlines()))
    body = np.array([[float(v) for v in r] for r in rows[1:]])
    assert body.shape == (table.stations.size, table.waterlines.size + 1)
    # sections stay inside the moulded beam after the transform
    assert body[:, 1:].max() <= table.beam / 2 + 1e-9


def test_pchip_passes_through_knots_without_overshoot():
    """The faired curve is exact at the offsets and stays in range."""
    from openhull.drawing import pchip
    u = np.linspace(0.0, 1.0, 21)
    y = 1.0 - u**2
    xq, yq = pchip(u, y, factor=10)
    assert np.all(np.diff(xq) > 0)
    for ui, yi in zip(u, y):
        assert abs(np.interp(ui, xq, yq) - yi) < 1e-12
    assert yq.min() > -1e-12 and yq.max() < 1.0 + 1e-12
    # monotone data stay monotone (no false wiggles between offsets)
    assert np.all(np.diff(yq) <= 1e-12)


def test_buttock_rides_the_baseline_where_the_hull_is_wider():
    """Sections already wider than the target at the base put the
    buttock on the baseline (z = 0), not NaN."""
    from openhull.drawing import _buttock_heights
    table = series60()
    z_at = _buttock_heights(table, 0.25 * table.beam / 2)
    mid = table.stations.size // 2
    assert z_at[mid] == 0.0                       # parallel body: baseline
    assert np.isnan(z_at[0])                      # transom AP: no line
    assert not np.isnan(z_at[-2])                 # fore body: exists
