"""Mother-ship chain tests: packaged parent -> scale -> Lackenby -> hydro.

Anchors (AGENTS.md section 3/4; provenance in examples/data/DATA_SOURCES.md):
  * JBC at the design draft: displacement volume 178369.9 m3 (+-1 %),
    Cb 0.8580 (+-0.005), KM 18.59 m (+-2 %), LCB +2.5475 %Lpp;
  * affine-scaling invariance: coefficients must NOT move when only
    the size changes;
  * Bonjean vs hydrostatics volume consistency on the chain table.
"""

from pathlib import Path

import numpy as np
import pytest

from openhull.cli import run_taskbook
from openhull.geometry import (
    load_offsets_csv,
    load_parent_offsets,
    scale_offsets,
)
from openhull.hydrostatics import bonjean_areas, hydrostatics_at, simpson
from openhull.linesplan import parent_to_taskbook

EXAMPLES_CSV = Path(__file__).resolve().parents[1] / "examples" / "data" / \
    "parent_hull_offsets.csv"
GRAD_ANCHOR = 178369.9   # [NMRI] m3
KM_ANCHOR = 18.59        # [NMRI] m


@pytest.fixture(scope="module")
def jbc_chain():
    """The chain at the JBC dimensions, pinned to the JBC targets."""
    table, report = parent_to_taskbook(
        lpp=280.0, beam=45.0, draft=16.5,
        target_cb=0.8580, target_lcb_pct=2.5475,
    )
    return table, report, hydrostatics_at(table, 16.5)


# ---------------------------------------------------------------------------
# packaged data and affine scaling
# ---------------------------------------------------------------------------


def test_packaged_parent_is_byte_identical_to_examples_csv():
    packaged = load_parent_offsets()
    from_csv = load_offsets_csv(
        str(EXAMPLES_CSV), lpp=280.0, beam=45.0, draft=16.5
    )
    assert np.array_equal(packaged.half_breadths, from_csv.half_breadths)
    assert np.array_equal(packaged.stations, from_csv.stations)
    assert np.array_equal(packaged.waterlines, from_csv.waterlines)


def test_scale_offsets_conserves_all_coefficients():
    parent = load_parent_offsets()
    scaled = scale_offsets(parent, lpp=140.0, beam=22.5, draft=8.25)
    assert scaled.lpp == pytest.approx(140.0)
    assert scaled.beam == pytest.approx(22.5)
    assert scaled.waterlines[-1] == pytest.approx(8.25)
    assert scaled.half_breadths.shape == parent.half_breadths.shape
    # affine invariants: the shape is the same, only its size changed
    assert scaled.half_breadths / 22.5 == pytest.approx(
        parent.half_breadths / 45.0
    )


def test_scale_offsets_volume_scales_with_the_cube():
    parent = load_parent_offsets()
    half = scale_offsets(parent, lpp=140.0, beam=22.5, draft=8.25)
    from openhull.hydrostatics import hydrostatics_at
    v_full = hydrostatics_at(parent, 16.5).displacement_volume
    v_half = hydrostatics_at(half, 8.25).displacement_volume
    assert v_half == pytest.approx(v_full / 8.0, rel=1e-9)


def test_scale_offsets_rejects_bad_dimensions():
    parent = load_parent_offsets()
    for kwargs in ({"lpp": 0.0, "beam": 45.0, "draft": 16.5},
                   {"lpp": 280.0, "beam": -1.0, "draft": 16.5},
                   {"lpp": 280.0, "beam": 45.0, "draft": float("nan")}):
        with pytest.raises(Exception, match="target dimension"):
            scale_offsets(parent, **kwargs)


# ---------------------------------------------------------------------------
# the chain at the JBC anchors (acceptance, plan task 2.6)
# ---------------------------------------------------------------------------


def test_chain_displacement_volume_within_one_percent(jbc_chain):
    _, _, h = jbc_chain
    assert abs(h.displacement_volume - GRAD_ANCHOR) / GRAD_ANCHOR < 0.01


def test_chain_block_coefficient_within_tolerance(jbc_chain):
    _, report, h = jbc_chain
    assert abs(h.cb - 0.8580) < 0.005
    assert abs(report.achieved["cb"] - 0.8580) < 0.003


def test_chain_km_within_two_percent(jbc_chain):
    _, _, h = jbc_chain
    assert abs(h.km - KM_ANCHOR) / KM_ANCHOR < 0.02


def test_chain_lcb_reproduced(jbc_chain):
    _, _, h = jbc_chain
    assert h.lcb == pytest.approx(2.5475, abs=0.02)


def test_chain_report_records_real_parent(jbc_chain):
    _, report, _ = jbc_chain
    assert report.identity is False
    assert report.iterations >= 1
    # the digitised parent's own anchors (DTMB 1712 Table 7): Cp 0.805
    # total, Cm 0.994-ish measured on the resampled grid
    assert report.parent["cp"] == pytest.approx(0.8033, abs=0.002)
    assert report.parent["cm"] == pytest.approx(0.9906, abs=0.002)
    assert report.achieved["cb"] == pytest.approx(0.8578, abs=0.001)


def test_chain_tpc_positive_and_consistent(jbc_chain):
    _, _, h = jbc_chain
    assert h.tpc == pytest.approx(1.025 * h.aw / 100.0, rel=1e-9)
    assert h.tpc > 100.0  # capesize scale: 45 m beam, ~24k m2 waterplane


# ---------------------------------------------------------------------------
# Bonjean -> hydrostatics consistency on the chain table
# ---------------------------------------------------------------------------


def test_bonjean_volume_matches_hydrostatics(jbc_chain):
    table, _, h = jbc_chain
    levels, areas = bonjean_areas(table)
    dx = float(table.stations[1] - table.stations[0])
    grad = simpson(areas[:, -1], dx)
    assert grad == pytest.approx(h.displacement_volume, rel=1e-4)


# ---------------------------------------------------------------------------
# CLI end-to-end on the real chain
# ---------------------------------------------------------------------------


def test_cli_run_reports_real_offsets_chain(tmp_path):
    summary = run_taskbook("examples/taskbook_bulk_carrier.yaml")
    assert "Series 60 parent" in summary["hull_source"]
    assert summary["transform_passes"] >= 1
    design = summary["hydrostatics"][-1]
    # the design row sits at the task-book draft (grid top = balance
    # draft, slightly deeper), so Cb is within the anchor band but not
    # pin-point: tolerance per AGENTS.md section 4
    assert abs(design["cb"] - 0.8580) < 0.005
    assert abs(design["km_m"] - KM_ANCHOR) / KM_ANCHOR < 0.02


def test_cli_run_is_deterministic():
    a = run_taskbook("examples/taskbook_bulk_carrier.yaml")
    b = run_taskbook("examples/taskbook_bulk_carrier.yaml")
    assert a["hydrostatics"] == b["hydrostatics"]
    assert a["cb_achieved"] == b["cb_achieved"]
