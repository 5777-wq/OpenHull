"""Tests for the Lackenby hull-form transform (plan task 2.3).

Anchors:
  * analytic parabolic area curve y = 1-u^2 (the golden values from the
    R7 source verification: Cp = 2/3, x_bf = 3/8, K^2 = 1/5, B_f = 3/5);
  * the digitised Series 60 parent (DTMB 1712 Table 7) and its printed
    prismatic coefficients;
  * the acceptance numbers of plan task 2.3 (identity at zero shift,
    Cb target hit through a full hydrostatics re-check).
"""

import json
from pathlib import Path

import numpy as np
import pytest

from openhull import SpecValidationError
from openhull.geometry import OffsetsTable, load_offsets_csv
from openhull.hydrostatics import hydrostatics_at
from openhull.linesplan import (
    TRANSFORM_ALGORITHMS,
    _b_and_c,
    _half_curve,
    _parent_xb,
    _table_cb,
    _table_lcb_pct,
    area_curve,
    lackenby_transform,
)

CSV = Path(__file__).resolve().parents[1] / "examples" / "data" / \
    "parent_hull_offsets.csv"


def series60() -> OffsetsTable:
    return load_offsets_csv(str(CSV), lpp=280.0, beam=45.0, draft=16.5)


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


def test_registry_contains_lackenby_and_cross_check_id():
    assert set(TRANSFORM_ALGORITHMS) == {"lackenby", "one_minus_cp"}
    for info in TRANSFORM_ALGORITHMS.values():
        assert info["citation"] and info["applicability"]


def test_unknown_algorithm_id_raises_with_registry_listing():
    table = series60()
    with pytest.raises(SpecValidationError) as excinfo:
        lackenby_transform(table, target_cb=0.82, algorithm="magic")
    message = str(excinfo.value)
    assert "unknown algorithm id" in message
    assert "lackenby" in message


def test_one_minus_cp_placeholder_raises_not_implemented():
    with pytest.raises(NotImplementedError) as excinfo:
        lackenby_transform(series60(), target_cb=0.82,
                           algorithm="one_minus_cp")
    assert "not implemented" in str(excinfo.value)


# ---------------------------------------------------------------------------
# goal validation and guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kwargs", [
    {},                                   # no goal at all
    {"target_cb": 0.82, "target_cp": 0.83},   # two absolute styles
    {"delta_cb": 0.02, "target_cb": 0.82},    # target + increment
])
def test_contradictory_goals_raise(kwargs):
    with pytest.raises(SpecValidationError):
        lackenby_transform(series60(), **kwargs)


def test_guard_rejects_large_cb_change():
    from openhull.linesplan import _guard
    with pytest.raises(SpecValidationError) as excinfo:
        _guard(d_cp=0.10, d_xb=0.0, target_cp=0.85)
    message = str(excinfo.value)
    assert "|dCp| <= 0.08" in message
    assert "small-perturbation" in message


def test_guard_rejects_large_lcb_shift():
    from openhull.linesplan import _guard
    with pytest.raises(SpecValidationError) as excinfo:
        _guard(d_cp=0.0, d_xb=0.05, target_cp=0.80)
    assert "half-lengths" in str(excinfo.value)


def test_guard_rejects_target_cp_out_of_band():
    with pytest.raises(SpecValidationError) as excinfo:
        lackenby_transform(series60(), target_cb=0.9, delta_lcb_pct=0.0)
    assert "Cp in (0.55, 0.88)" in str(excinfo.value)


# ---------------------------------------------------------------------------
# analytic anchor: parabolic area curve
# ---------------------------------------------------------------------------


def test_parabolic_curve_golden_values():
    """y = 1-u^2: Cp = 2/3, x_bf = 3/8, K^2 = 1/5 (Simpson exact)."""
    u = np.linspace(0.0, 1.0, 65)
    curve = _half_curve(u, 1.0 - u**2, 0.0)
    assert curve.cp == pytest.approx(2.0 / 3.0, abs=1e-12)
    assert curve.xb == pytest.approx(0.375, abs=1e-12)
    assert curve.k2 == pytest.approx(0.2, abs=1e-6)  # Simpson O(h^4) on u^4


def test_parabolic_bf_matches_moment_definition():
    """Printed B_f (eq. 5-41) equals the moment integral of the shift
    field on the parabolic curve — the closure check from the R7 pass."""
    u = np.linspace(0.0, 1.0, 129)
    curve = _half_curve(u, 1.0 - u**2, 0.0)
    b_f, _c_f = _b_and_c(curve)
    assert b_f == pytest.approx(0.6, abs=1e-7)

    from openhull.linesplan import _shift_coeffs
    from openhull.hydrostatics import simpson

    delta = 0.01
    alpha, beta = _shift_coeffs(curve, delta, 0.0)
    du = (1.0 - u) * (alpha + beta * u)
    slope = np.gradient(curve.y, float(u[1] - u[0]))
    moment = simpson(u * du * (-slope), float(u[1] - u[0]))
    assert moment / delta == pytest.approx(b_f, rel=2e-3)


def test_shift_field_vanishes_on_parallel_body():
    """dl = 0 must keep the whole parallel body fixed: du(u<=l_p) = 0."""
    fore, _aft, _cm = area_curve(series60())
    from openhull.linesplan import _apply_shift, _shift_coeffs
    alpha, beta = _shift_coeffs(fore, 0.02, 0.0)
    shifted = _apply_shift(fore, alpha, beta, 0.02, 0.0)
    u = fore.u
    on_parallel = u <= fore.l_parallel + 1e-12
    assert np.allclose(shifted.shift[on_parallel], 0.0, atol=1e-12)
    # and the curve itself is untouched there
    assert np.allclose(shifted.y[on_parallel], fore.y[on_parallel],
                       atol=1e-12)


# ---------------------------------------------------------------------------
# loader anchors (digitised Series 60, DTMB 1712 Table 7)
# ---------------------------------------------------------------------------


def test_loader_reproduces_report_prismatic_coefficients():
    fore, aft, cm = area_curve(series60())
    assert 0.5 * (fore.cp + aft.cp) == pytest.approx(0.805, abs=0.005)
    assert fore.cp == pytest.approx(0.861, abs=0.005)
    assert aft.cp == pytest.approx(0.750, abs=0.005)
    assert cm == pytest.approx(0.99, abs=0.01)


def test_loader_matches_report_area_fraction_column():
    """Third-party check: every station's normalised area (except the
    transom-stern AP end, where the report integrates a non-linear
    section) matches the table's own area_fraction column."""
    import csv

    lines = [l for l in CSV.read_text(encoding="utf-8-sig").splitlines()
             if l.strip() and not l.startswith("#")]
    rows = list(csv.reader(lines))
    col = rows[0].index("area_fraction")
    frac = {r[0]: float(r[col]) for r in rows[1:]
            if r and r[0] != "max_half_beam" and r[col].strip()}

    table = series60()
    fore, aft, _cm = area_curve(table)
    worst = 0.0
    for i, x in enumerate(table.stations):
        station = 20.0 * (1.0 - x / table.lpp)
        name = "FP" if station < 1e-6 else (
            "AP" if station > 20 - 1e-6 else
            f"{station:.1f}".rstrip("0").rstrip("."))
        if name not in frac or name == "AP":
            continue
        xi = x / table.lpp
        if xi >= 0.5:
            y_norm = float(np.interp(2.0 * xi - 1.0, fore.u, fore.y))
        else:
            y_norm = float(np.interp(1.0 - 2.0 * xi, aft.u, aft.y))
        worst = max(worst, abs(y_norm - frac[name]))
    assert worst <= 0.015


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------


def test_identity_zero_delta_returns_parent_bit_for_bit():
    table = series60()
    snapshot = table.half_breadths.copy()
    new_table, report = lackenby_transform(table, delta_cb=0.0)
    assert report.identity is True
    assert report.iterations == 0
    assert np.array_equal(new_table.half_breadths, table.half_breadths)
    assert np.array_equal(table.half_breadths, snapshot)  # parent intact


def test_identity_report_round_trips_through_json():
    _t, report = lackenby_transform(series60(), delta_cb=0.0)
    payload = json.dumps(report.to_dict())
    assert "identity" in payload


# ---------------------------------------------------------------------------
# acceptance numbers (plan task 2.3)
# ---------------------------------------------------------------------------


def test_cb_target_hit_on_carried_table():
    table = series60()
    goal = 0.02
    new_table, report = lackenby_transform(table, delta_cb=goal)
    achieved = _table_cb(new_table) - _table_cb(table)
    assert achieved == pytest.approx(goal, abs=5e-4)
    assert report.achieved["cb"] == pytest.approx(_table_cb(new_table),
                                                  abs=1e-6)


def test_cb_change_keeps_lcb():
    table = series60()
    new_table, _report = lackenby_transform(table, delta_cb=0.02)
    assert (_table_lcb_pct(new_table) - _table_lcb_pct(table)) == \
        pytest.approx(0.0, abs=0.02)


def test_pure_lcb_shift_conserves_volume():
    table = series60()
    new_table, _report = lackenby_transform(table, delta_lcb_pct=0.5)
    assert _table_cb(new_table) - _table_cb(table) == \
        pytest.approx(0.0, abs=1e-3)


def test_pure_lcb_shift_hits_target():
    table = series60()
    goal_pct = _table_lcb_pct(table) + 0.5
    new_table, _report = lackenby_transform(table, delta_lcb_pct=0.5)
    assert _table_lcb_pct(new_table) == pytest.approx(goal_pct, abs=0.01)


def test_hydrostatics_module_agrees_with_table_layer():
    table = series60()
    new_table, _report = lackenby_transform(table, delta_cb=0.02)
    draft = new_table.waterlines[-1]
    hydro = hydrostatics_at(new_table, draft)
    cb_hydro = hydro.displacement_volume / (
        new_table.lpp * new_table.beam * draft)
    assert cb_hydro == pytest.approx(_table_cb(new_table), abs=5e-4)


def test_transformed_table_respects_offsets_invariants():
    table = series60()
    new_table, _report = lackenby_transform(table, delta_cb=0.02)
    assert new_table.half_breadths.shape == table.half_breadths.shape
    assert np.all(new_table.half_breadths >= 0.0)
    assert np.all(new_table.half_breadths <= new_table.beam / 2 + 1e-9)
    # the parallel body (detected length) must not have moved
    mid = new_table.stations.size // 2
    n_mid = int(fore_l := 0) or mid  # parallel band around midship
    half_span = int(round(0.15 * mid))
    assert np.allclose(
        new_table.half_breadths[mid - half_span:mid + half_span + 1, -1],
        table.half_breadths[mid - half_span:mid + half_span + 1, -1],
    )


def test_parallel_body_increment_smoke():
    table = series60()
    new_table, report = lackenby_transform(table, delta_l_pf=0.1,
                                           delta_l_pa=0.05)
    # volume ~ conserved, iterations finite, report honest
    assert _table_cb(new_table) - _table_cb(table) == \
        pytest.approx(0.0, abs=5e-3)
    assert 0 < report.iterations <= 8


# ---------------------------------------------------------------------------
# JBC-anchored demonstration (report values, loose band)
# ---------------------------------------------------------------------------


def test_series60_to_jbc_demonstration():
    """Two-step transform of Series 60 onto the JBC task-book anchors;
    the landing point is asserted loosely (this is a demonstration of
    no-overfitting, not a fitting target)."""
    table = series60()
    new_table, report = lackenby_transform(table, target_cb=0.8580,
                                           target_lcb_pct=2.5475)
    assert _table_cb(new_table) == pytest.approx(0.8580, abs=2e-3)
    assert _table_lcb_pct(new_table) == pytest.approx(2.5475, abs=0.05)
    assert report.iterations > 0
    # Cm must be held: the parallel body does not move
    _f, _a, cm_new = area_curve(new_table)
    _f0, _a0, cm_old = area_curve(table)
    assert cm_new == pytest.approx(cm_old, abs=1e-6)


# ---------------------------------------------------------------------------
# parent-centroid bookkeeping
# ---------------------------------------------------------------------------


def test_parent_centroid_from_half_curves_matches_table_lcb():
    fore, aft, _cm = area_curve(series60())
    xb = _parent_xb(fore, aft)          # half-lengths, fwd+
    assert xb == pytest.approx(2.0 * _table_lcb_pct(series60()) / 100.0,
                              abs=2e-3)
