"""Tests for the lines-plan surface skin (v1.10.0, plan task
"lines-plan quick win", AGENTS.md section 5 entry 2026-10-05).

Anchors pinned here (see the section 5 entry and VALIDATION.md):
(a) knot reproduction — the interpolating skin returns every
    tabulated offset exactly (gate 1e-6 x B/2);
(b) hydrostatics round-trip — the dense re-cut does not change the
    ship: displacement volume / Cb / LCB / KM at the design draft
    stay inside the table layer's anchor tolerances;
(c) physical-coordinate re-sampling by bisection (geomdl
    parameterises non-uniformly; x depends only on u, z only on v).
"""

from pathlib import Path

import numpy as np
import pytest

from openhull.drawing import draw_lines_plan, save_lines_plan_dxf
from openhull.geometry import OffsetsTable, load_offsets_csv
from openhull.hydrostatics import hydrostatics_at
from openhull.surface import (
    SURFACE_DEGREE,
    curvature_report,
    dense_offsets_table,
    fit_offsets_surface,
    raw_offsets_for_drawing,
)
from openhull.spec import SpecValidationError

CSV = Path(__file__).resolve().parents[1] / "examples" / "data" / \
    "parent_hull_offsets.csv"
LPP, BEAM, DRAFT = 280.0, 45.0, 16.5


@pytest.fixture(scope="module")
def series60() -> OffsetsTable:
    return load_offsets_csv(str(CSV), lpp=LPP, beam=BEAM, draft=DRAFT)


@pytest.fixture(scope="module")
def skin(series60):
    return fit_offsets_surface(series60)


# ------------------------------------------------- anchor (a): knots


def test_skin_reproduces_every_tabulated_offset(skin, series60):
    assert skin.knot_max_abs_err <= 1e-6 * BEAM / 2.0
    y = np.asarray(series60.half_breadths, dtype=float)
    ev = skin.surface.evaluate_list(
        [(float(u), float(v)) for u in skin.u_nodes for v in skin.v_nodes])
    fitted = np.array(ev)[:, 2].reshape(y.shape)
    assert np.max(np.abs(fitted - y)) == pytest.approx(
        skin.knot_max_abs_err, rel=1e-6, abs=1e-15)


def test_sparse_grid_refused():
    # a valid 3x3 grid (spans the full Lpp) that is still too sparse
    # for a degree-3 interpolating skin
    small = OffsetsTable(
        lpp=LPP, beam=BEAM,
        stations=np.linspace(0.0, LPP, SURFACE_DEGREE),
        waterlines=np.linspace(0.0, DRAFT, SURFACE_DEGREE),
        half_breadths=np.zeros((SURFACE_DEGREE, SURFACE_DEGREE)))
    with pytest.raises(SpecValidationError) as excinfo:
        fit_offsets_surface(small)
    assert "too sparse to skin" in str(excinfo.value)


# ---------------------------------------- anchor (c): dense re-cut grid


def test_dense_grid_shape_and_simpson_parity(skin, series60):
    dense = dense_offsets_table(skin, station_intervals=2,
                                waterline_intervals=2)
    ns = np.asarray(series60.stations).size
    nw = np.asarray(series60.waterlines).size
    assert dense.half_breadths.shape == (2 * (ns - 1) + 1,
                                         2 * (nw - 1) + 1)
    # Simpson parity survives densification (odd counts both ways)
    assert dense.half_breadths.shape[0] % 2 == 1
    assert dense.half_breadths.shape[1] % 2 == 1
    # endpoints preserved exactly; no negative half-breadths (clip rule)
    assert dense.stations[0] == 0.0 and dense.stations[-1] == LPP
    assert float(dense.half_breadths.min()) >= 0.0


def test_dense_intervals_guard(skin):
    with pytest.raises(SpecValidationError):
        dense_offsets_table(skin, station_intervals=0)


# ---------------------------------- anchor (b): hydrostatics round-trip


def test_dense_recut_does_not_change_the_ship(skin, series60):
    base = hydrostatics_at(series60, DRAFT)
    for intervals in (2, 4):
        dense = dense_offsets_table(skin, station_intervals=intervals,
                                    waterline_intervals=intervals)
        got = hydrostatics_at(dense, DRAFT)
        assert got.displacement_volume == pytest.approx(
            base.displacement_volume, rel=0.005), intervals
        assert got.cb == pytest.approx(base.cb, abs=0.005), intervals
        assert got.lcb == pytest.approx(base.lcb, abs=0.05), intervals
        assert got.km == pytest.approx(base.km, rel=0.01), intervals


# ------------------------------------------------ curvature diagnostics


def test_curvature_report_shape_and_dead_row_skip(skin):
    dense = dense_offsets_table(skin)
    rep = curvature_report(dense)
    rows = rep["waterlines"]
    nw = np.asarray(dense.waterlines).size
    assert 5 < len(rows) <= nw
    assert all(r["max_kappa_per_m"] >= 0.0 for r in rows)
    assert all(r["inflections"] >= 0 for r in rows)
    assert "acceptance gate" in rep["note"]


def test_curvature_report_flags_injected_unfairness(skin):
    from types import SimpleNamespace

    dense = dense_offsets_table(skin)
    clean = curvature_report(dense)
    stations = np.asarray(dense.stations, dtype=float)
    waterlines = np.asarray(dense.waterlines, dtype=float)
    y = np.array(dense.half_breadths, dtype=float)
    # inject an alternating zig-zag on the design waterline row; the
    # wobble table is a duck-typed stand-in (no beam-bounds validation
    # - the injected geometry is deliberately unfair, not a real ship)
    j = int(np.argmin(np.abs(waterlines - DRAFT)))
    zig = y[:, j].copy()
    amp = 0.01 * BEAM
    for i in range(5, zig.size - 5):
        zig[i] += amp if (i % 2 == 0) else -amp
    wob = SimpleNamespace(lpp=dense.lpp, beam=dense.beam,
                          stations=stations, waterlines=waterlines,
                          half_breadths=np.column_stack(
                              [y[:, :j], zig, y[:, j + 1:]]))
    bad = curvature_report(wob)
    clean_row = next(r for r in clean["waterlines"]
                     if abs(r["waterline_m"] - DRAFT) < 1e-6)
    bad_row = next(r for r in bad["waterlines"]
                   if abs(r["waterline_m"] - DRAFT) < 1e-6)
    assert bad_row["max_kappa_per_m"] > 2.0 * clean_row["max_kappa_per_m"]
    assert bad_row["inflections"] > clean_row["inflections"] + 5


# ---------------------------------------------------- drawing integration


def test_dense_table_feeds_the_drawing_chain(skin, tmp_path):
    dense = dense_offsets_table(skin)
    raw = raw_offsets_for_drawing(dense, design_draft_m=DRAFT)
    assert set(raw) >= {"stations", "heights", "half_breadths",
                        "fractions"}
    # the DWL fraction is pinned to exactly 1.0 at the nearest row
    assert min(abs(f - 1.0) for f in raw["fractions"]) == 0.0
    png = draw_lines_plan(raw, str(tmp_path / "dense.png"),
                          title="dense skin lines plan")
    dxf = save_lines_plan_dxf(raw, str(tmp_path / "dense.dxf"),
                              title="dense skin lines plan")
    assert Path(png).exists() and Path(dxf).exists()
    assert Path(dxf).stat().st_size > 10_000


def test_drawing_converter_refuses_draft_outside_span(skin, tmp_path):
    dense = dense_offsets_table(skin)
    with pytest.raises(SpecValidationError):
        raw_offsets_for_drawing(dense, design_draft_m=99.0)
