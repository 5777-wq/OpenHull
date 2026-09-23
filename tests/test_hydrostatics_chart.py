"""Hydrostatic curves chart tests (plan task 4.1).

The chart is a pure data visualization of the task 1.4 table, so the
assertions check the wiring (file produced, PNG, non-trivial size)
and that every drawn quantity is one of the tabulated attributes.
"""

from pathlib import Path

import pytest

from openhull.hydrostatics import hydrostatics_table
from openhull.hydrostatics_chart import _PANELS, write_hydrostatic_curves_chart
from openhull.linesplan import parent_to_taskbook


@pytest.fixture(scope="module")
def table():
    hull, _ = parent_to_taskbook(lpp=100.0, beam=20.0, draft=6.0,
                                 target_cb=0.80)
    return hydrostatics_table(
        hull, [round(6.0 * f, 4) for f in (0.2, 0.4, 0.6, 0.8, 1.0)])


def test_panels_cover_the_twelve_classic_quantities():
    attrs = [attr for attr, _, _ in _PANELS]
    assert attrs == [
        "displacement_volume", "displacement", "kb", "bmt", "km", "bml",
        "tpc", "mtc", "lcb", "lcf", "cb", "cw",
    ]


def test_chart_renders_png(table, tmp_path):
    out = write_hydrostatic_curves_chart(
        table, tmp_path / "hydro_curves.png", title="TEST")
    assert out == tmp_path / "hydro_curves.png"
    data = out.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic
    assert len(data) > 30_000  # twelve plotted panels, not a blank canvas


def test_chart_accepts_pathlike_and_str(table, tmp_path):
    out = write_hydrostatic_curves_chart(table, str(tmp_path / "b.png"))
    assert Path(out).exists()
