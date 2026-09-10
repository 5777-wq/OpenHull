"""Tests for initial stability and floating attitude (plan task 1.5).

Layers:

* free-surface and GM identities (Ship Theory vol. 1 ch. 4, Eqs.
  4-19/4-36/4-38) against hand-computed numbers;
* box-hull trim against the exact closed-form trim line (the iteration
  must reproduce it, not just wander near it);
* JBC ballast condition [NMRI]: displacement 89,185.9 m3 at drafts
  10.015/7.215 m (aft/fore) - a published condition never used in any
  fit - recovered by the Eqs.(3-25)/(3-26) iteration within 2.5 %.
"""

import dataclasses
import json

import numpy as np
import pytest

from openhull import (
    OffsetsTable,
    SpecValidationError,
    Tank,
    floating_position,
    free_surface_correction,
    hydrostatics_at,
    initial_stability,
    jbc_parent_offsets,
)

LPP, BEAM, DRAFT = 280.0, 45.0, 16.5
KG_FULL_LOAD = 13.29  # [NMRI]
GM_ANCHOR = 5.30  # [NMRI] full load


@pytest.fixture(scope="module")
def jbc():
    table = jbc_parent_offsets(lpp=LPP, beam=BEAM, draft=DRAFT)
    return table, hydrostatics_at(table, DRAFT)


def box_table() -> OffsetsTable:
    stations = np.linspace(0.0, LPP, 21)
    waterlines = np.linspace(0.0, DRAFT, 33)
    return OffsetsTable(
        lpp=LPP, beam=BEAM, stations=stations, waterlines=waterlines,
        half_breadths=np.full((21, 33), BEAM / 2.0),
    )


# ---------------------------------------------------------------------------
# free surfaces and GM (Ship Theory vol. 1, ch. 4)
# ---------------------------------------------------------------------------


def test_rectangular_tank_inertias():
    tank = Tank.rectangular("store", length=12.0, breadth=4.0, liquid_density=1.0)
    assert tank.i_x == pytest.approx(12.0 * 4.0**3 / 12.0)
    assert tank.i_y == pytest.approx(4.0 * 12.0**3 / 12.0)


def test_tank_rejects_nonphysical_values():
    with pytest.raises(SpecValidationError):
        Tank(name="bad", i_x=-1.0, liquid_density=1.0)
    with pytest.raises(SpecValidationError):
        Tank.rectangular("bad", length=0.0, breadth=2.0)


def test_free_surface_correction_sums_weighted_inertias():
    tanks = (
        Tank("a", i_x=100.0, liquid_density=1.0),
        Tank("b", i_x=50.0, liquid_density=0.9),
    )
    assert free_surface_correction(tanks, 1000.0) == pytest.approx(
        (1.0 * 100.0 + 0.9 * 50.0) / 1000.0
    )
    assert free_surface_correction((), 1000.0) == 0.0
    with pytest.raises(SpecValidationError):
        free_surface_correction(tanks, 0.0)


def test_jbc_full_load_gm(jbc):
    """GM = KM - KG at 5.30 m: consistency on the KM anchor (declared)."""
    _, h = jbc
    st = initial_stability(h, kg=KG_FULL_LOAD)
    assert st.gm == pytest.approx(GM_ANCHOR, abs=0.01)
    assert abs(st.gm - GM_ANCHOR) / GM_ANCHOR < 0.05  # plan tolerance
    assert st.gm_uncorrected == pytest.approx(st.km - st.kg)


def test_free_surface_reduces_gm(jbc):
    _, h = jbc
    tank = Tank.rectangular("bilge_well", length=30.0, breadth=20.0,
                            liquid_density=1.025)
    plain = initial_stability(h, kg=KG_FULL_LOAD)
    with_fs = initial_stability(h, kg=KG_FULL_LOAD, tanks=(tank,))
    assert with_fs.free_surface_correction > 0.0
    assert with_fs.gm == pytest.approx(
        plain.gm - with_fs.free_surface_correction
    )
    assert ("bilge_well", with_fs.free_surface_correction) in [
        (name, value) for name, value in with_fs.tank_contributions
    ]


def test_negative_gm_is_allowed_but_explicit(jbc):
    """An unstable loading is a valid computation result (design checks
    that reject it belong to task 3.5)."""
    _, h = jbc
    st = initial_stability(h, kg=h.km + 2.0)
    assert st.gm == pytest.approx(-2.0)


def test_initial_stability_json_roundtrip(jbc):
    _, h = jbc
    st = initial_stability(h, kg=KG_FULL_LOAD)
    loaded = json.loads(json.dumps(st.to_dict()))
    assert loaded["gm"] == pytest.approx(st.gm)
    assert loaded["tank_contributions"] == []


# ---------------------------------------------------------------------------
# floating attitude (Eqs. 3-25/3-26/3-27)
# ---------------------------------------------------------------------------


def test_box_hull_trim_matches_closed_form():
    """Box: trimmed waterline about the LCF, slope s = 12 dm (xg-L/2)/L^2."""
    dm = 10.0
    weight = 1.025 * LPP * BEAM * dm
    result = floating_position(box_table(), weight, lcg_m=144.0)
    slope = 12.0 * dm * (144.0 - LPP / 2.0) / LPP**2
    assert result.draft_aft == pytest.approx(dm - (LPP / 2.0) * slope, rel=1e-3)
    assert result.draft_fore == pytest.approx(dm + (LPP / 2.0) * slope, rel=1e-3)
    assert result.converged is True


def test_even_keel_requires_lcg_at_lcb(jbc):
    """Even keel needs xg = xb, NOT xg = midship: JBC's LCB is +2.55
    %Lpp forward, so a midship LCG trims by the stern."""
    table, h = jbc
    lcg_at_lcb = LPP / 2.0 + h.lcb / 100.0 * LPP
    result = floating_position(table, h.displacement, lcg_m=lcg_at_lcb)
    assert result.trim_m == pytest.approx(0.0, abs=1e-3)
    assert result.draft_aft == pytest.approx(result.draft_fore, abs=1e-3)

    stern_trim = floating_position(table, h.displacement, lcg_m=LPP / 2.0)
    assert stern_trim.trim_m < -1.0  # weight aft of buoyancy: stern sinks


def test_jbc_ballast_condition_reproduced(jbc):
    """[NMRI] ballast: 89,185.9 m3 at 10.015/7.215 m (aft/fore).

    The LCG is the one that holds the published waterline (measured from
    the fitted hull); the iteration must recover the published drafts
    from weight + LCG alone. Drafts were never used in any fit.
    """
    table, _ = jbc
    displacement_t = 89185.9 * 1.025
    lcg_m = LPP / 2.0 + (2.5475 - 2.5475) * 0.0 + 0.814 / 100.0 * LPP
    result = floating_position(table, displacement_t, lcg_m)
    assert result.converged is True
    assert result.draft_aft == pytest.approx(10.015, rel=0.025)
    assert result.draft_fore == pytest.approx(7.215, rel=0.025)
    assert result.buoyancy_residual <= 0.001
    assert result.lcg_residual <= 0.0005


def test_trim_audit_trail(jbc):
    table, h = jbc
    result = floating_position(table, h.displacement, lcg_m=LPP / 2.0 + 2.0)
    assert len(result.steps) == result.iterations
    assert result.steps[-1].buoyancy_residual <= 0.001
    assert result.steps[-1].lcg_residual <= 0.0005
    assert result.to_dict()["steps"][0]["draft_aft"] == pytest.approx(
        result.steps[0].draft_aft
    )


def test_nonconvergence_raises(jbc):
    """Full load sits at the top waterline, so a midship-ish LCG walks
    the trim out of range; use a mid displacement that has room and a
    tolerance the loop cannot meet."""
    table, _ = jbc
    h_mid = hydrostatics_at(table, 12.375)
    with pytest.raises(RuntimeError) as excinfo:
        floating_position(
            table, h_mid.displacement, lcg_m=LPP / 2.0 + 0.5,
            buoyancy_tolerance=1e-6, lcg_tolerance=1e-6, max_iterations=2,
        )
    assert "did not converge" in str(excinfo.value)


def test_lcg_outside_hull_refuses(jbc):
    table, h = jbc
    with pytest.raises(SpecValidationError) as excinfo:
        floating_position(table, h.displacement, lcg_m=LPP + 1.0)
    assert excinfo.value.field == "lcg"
