"""Design-space scan tests (plan task 3.6).

The CI grid is deliberately small (a full 192-point acceptance scan of
the TB-001S scenario is recorded in VALIDATION.md).  The assertions
cover the chain integrity, the declared refusal gates, determinism and
the Pareto extraction.
"""

import dataclasses
import math

import pytest

from openhull.optimize import (
    ScanCandidate,
    ScanConfig,
    SweepGrid,
    _tip_clearance_ok,
    design_space_scan,
    pareto_front,
)
from openhull.propulsion import propulsion_factors
from openhull.resistance import ayre_effective_power
from openhull.spec import ShipSpec, knots_to_ms

FT_PER_M = 1.0 / 0.3048

# TB-001S scan scenario: the 14.5 kn [NMRI] service speed sits below
# the whitelisted Ayre speed-length band for a 280 m ship, so the scan
# scenario studies 16.0 kn (declared deviation, see the scenario task
# book and VALIDATION.md)
SPEC = ShipSpec(
    deadweight=149920.0,
    service_speed=knots_to_ms(16.0),
    cb=0.85,
    draft=16.5,
)
CONFIG_KW = dict(kg_m=13.29, shaft_immersion_m=8.5,
                 relative_rotative_eff=0.982)

SMALL_GRID = SweepGrid(
    l_over_b=(5.8, 6.2, 2),
    b_over_t=(2.7, 3.1, 2),
    cb=(0.82, 0.85, 2),
)


@pytest.fixture(scope="module")
def scan():
    return design_space_scan(SPEC, kg_m=13.29, grid=SMALL_GRID,
                             config=ScanConfig(**CONFIG_KW))


def test_small_grid_finds_feasible_designs(scan):
    assert 1 <= len(scan.feasible) <= 8
    assert len(scan.rejected) + len(scan.feasible) == 8


def test_every_feasible_candidate_carries_a_full_record(scan):
    for cand in scan.feasible:
        d = cand.to_dict()
        for key in ("lpp_m", "beam_m", "draft_m", "displacement_t",
                    "gm_m", "eta_open_water", "propeller_diameter_m",
                    "propeller_pitch_ratio", "advance_coefficient",
                    "thrust_n"):
            assert key in d
        # stability and weather gates passed by construction; the
        # recorded numbers must be physical
        assert cand.gm_m > 0.5
        assert 0.40 <= cand.eta_open_water <= 0.85
        assert cand.lpp_m > 0 and cand.beam_m > 0 and cand.draft_m > 0


def test_reference_speed_axis_is_populated_where_the_band_allows(scan):
    """The attainable-speed axis is the median feasible shaft power.

    A design can be placed on it only if its effective-power curve
    crosses that power INSIDE the Ayre speed-length band.  Hulls that
    already absorb more than the reference at the band floor (0.50) can
    only reach it by going slower than the validated band, so the task
    3.2 solver refuses and ``pareto_front`` drops them by design.  Both
    populations are pinned against the model rather than assuming the
    axis is always full (this is what the corrected propulsion stage
    exposes: 0.3-1.3 % of nothing, see the speed-unit note in
    optimize.py).
    """
    assert scan.reference_power_kw is not None
    band_lo, band_hi = 0.50, 1.20
    placed = 0
    for cand in scan.feasible:
        speed = cand.speed_at_reference_power_kn
        if speed is not None:
            placed += 1
            assert band_lo <= speed / math.sqrt(cand.lpp_m * FT_PER_M) <= band_hi
            continue
        # not placed: the band floor already absorbs more than the
        # reference power, so no in-band balance exists
        factors = propulsion_factors(
            lpp_m=cand.lpp_m, lwl_m=cand.lpp_m, beam_m=cand.beam_m,
            draft_m=cand.draft_m, cb=cand.cb, cp=cand.cp, cm=cand.cm,
            cwp=cand.cwp, lcb_pct_fwd=cand.lcb_pct_fwd,
            propeller_diameter_m=cand.propeller_diameter_m,
            speed_ms=SPEC.service_speed, screw="single",
            eta_r=CONFIG_KW["relative_rotative_eff"])
        target = (scan.reference_power_kw * cand.eta_open_water
                  * CONFIG_KW["relative_rotative_eff"] * factors.eta_h)
        floor_kn = band_lo * math.sqrt(cand.lpp_m * FT_PER_M)
        floor_pe = ayre_effective_power(
            displacement_t=cand.displacement_t, speed_kn=floor_kn,
            lpp_m=cand.lpp_m, beam_m=cand.beam_m, draft_m=cand.draft_m,
            cb=cand.cb, xc_pct_fwd=cand.lcb_pct_fwd,
            lwl_m=cand.lpp_m,  # the scan passes the waterline it has
            screw="single").pe_bare_kw
        assert floor_pe > target, (cand.l_over_b, cand.b_over_t, cand.cb)
    assert placed >= 1, "the axis must be populated for some design"


def test_propeller_advance_speed_is_the_ship_speed(scan):
    """P0 pin (review 2026-09-24 follow-up): the scan's propulsion stage
    must run at the ship's speed.

    optimize.py divided by the knots->m/s factor instead of multiplying
    it, so this stage designed propellers for a phantom vessel 3.78x
    faster (Va 25.7 m/s for a 20 kn ship).  Every recorded design carries
    J, n and D, so the implied advance speed can be checked against the
    ship speed: with a wake fraction in its physical band (0..0.4, the
    project's own guard) it must lie in [0.6, 1.0] x V.
    """
    v_ms = SPEC.service_speed
    n_rps = ScanConfig(**CONFIG_KW).propeller_rpm / 60.0
    assert scan.feasible, "the scenario must produce designs to check"
    for cand in scan.feasible:
        va = cand.advance_coefficient * n_rps * cand.propeller_diameter_m
        assert 0.55 * v_ms <= va <= v_ms, (cand.l_over_b, cand.b_over_t,
                                           cand.cb, va / v_ms)


def test_band_endpoint_grid_leaves_no_propulsion_stage_refusal():
    """N3 end-to-end (review 2026-09-24): the grid endpoint B/T = 3.5 is
    the guard band's own ceiling, and the chain recomputes B/T from a
    cube-root round trip - 3.5000000000000004 for some L/B.  A point
    refused there is a floating-point artifact, not a design verdict, so
    run the grid the reviewer ran and assert the weight-balance stage
    refuses none of its endpoints.
    """
    grid = SweepGrid(l_over_b=(6.0, 7.0, 2), b_over_t=(2.5, 3.5, 2),
                     cb=(0.81, 0.81, 1))
    res = design_space_scan(SPEC, kg_m=13.29, grid=grid,
                            config=ScanConfig(**CONFIG_KW))
    for r in res.rejected:
        assert r.stage != "weight_balance", r.reason
    assert len(res.feasible) + len(res.rejected) == 4


def test_seakeeping_columns_reported_not_gating(scan):
    # task 3.8 stage-1 columns: natural periods and roll resonance
    # verdicts ride along on every feasible candidate; they are NOT
    # feasibility gates (resonance avoidance is the owner's judgement)
    for cand in scan.feasible:
        assert cand.roll_period_s is not None
        assert cand.pitch_period_s is not None
        assert cand.heave_period_s is not None
        # a Valemax-class beam (B ~ 45 m) rolls slower than the
        # 10,000-t cargo class band but far from pitch/heave periods
        assert 8.0 <= cand.roll_period_s <= 25.0
        assert 3.0 <= cand.pitch_period_s <= 15.0
        assert cand.pitch_period_s == pytest.approx(
            cand.heave_period_s, rel=0.25)
        assert isinstance(cand.roll_resonant_6s, bool)
        assert isinstance(cand.roll_resonant_8s, bool)
    # a 6 s short wave tunes every large-ship roll period out of the
    # band from below (Lambda > 1.3): the flag must be False here
    assert all(cand.roll_period_s / 6.0 > 1.3 for cand in scan.feasible)


def test_scan_is_deterministic():
    a = design_space_scan(SPEC, kg_m=13.29, grid=SMALL_GRID,
                          config=ScanConfig(**CONFIG_KW))
    b = design_space_scan(SPEC, kg_m=13.29, grid=SMALL_GRID,
                          config=ScanConfig(**CONFIG_KW))
    assert a.to_dicts() == b.to_dicts()
    assert ([(r.stage, r.reason) for r in a.rejected]
            == [(r.stage, r.reason) for r in b.rejected])


def test_ayre_band_gate_declares_the_short_speed():
    # the original TB-001 task book: 14.5 kn on a ~280 m hull gives
    # V/sqrt(L) below the Ayre band - every point must be refused at
    # the declared gate, none silently evaluated
    slow = ShipSpec(
        deadweight=149920.0,
        service_speed=knots_to_ms(14.5),
        cb=0.85,
        draft=16.5,
    )
    one = SweepGrid(l_over_b=(6.2, 6.2, 1), b_over_t=(2.7, 2.7, 1),
                    cb=(0.85, 0.85, 1))
    res = design_space_scan(slow, kg_m=13.29, grid=one,
                            config=ScanConfig(**CONFIG_KW))
    assert res.feasible == []
    assert len(res.rejected) == 1
    assert res.rejected[0].stage == "ayre_band"


def test_pareto_front_is_non_dominated():
    def cand(speed, disp, gm):
        return ScanCandidate(
            l_over_b=0, b_over_t=0, cb=0, lpp_m=0, beam_m=0, draft_m=0,
            depth_m=0, displacement_t=disp, gm_m=gm, gz_max_m=0,
            eta_open_water=0.6, delivered_power_kw=0, shaft_power_kw=0,
            propeller_diameter_m=0, propeller_pitch_ratio=0,
            advance_coefficient=0, thrust_n=0, cp=0.85, cm=0.99, cwp=0.9,
            lcb_pct_fwd=2.5, cavitation_ok=None,
            cavitation_aeao_required=None,
            speed_at_reference_power_kn=speed)

    pool = [cand(15.0, 180.0, 5.0), cand(16.0, 185.0, 5.5),
            cand(14.0, 200.0, 4.0),   # dominated by the second
            cand(16.0, 190.0, 5.0)]   # dominated by the second
    front = pareto_front(pool)
    assert len(front) == 2
    speeds = {c.speed_at_reference_power_kn for c in front}
    assert speeds == {15.0, 16.0}


def test_grid_values_cover_the_requested_axes():
    grid = SweepGrid(l_over_b=(5.0, 6.0, 3), b_over_t=(2.0, 3.0, 2),
                     cb=(0.80, 0.86, 2))
    values = list(grid.values())
    assert len(values) == 12
    assert values[0] == (5.0, 2.0, 0.8)
    assert values[-1] == (6.0, 3.0, 0.86)


# ---------------------------------------------------------------------------
# one waterline convention across the scan (review 2026-09-24 r4, §3)
# ---------------------------------------------------------------------------


def test_design_point_and_speed_axis_describe_one_ship(scan):
    """The design point and the reference-speed solve must evaluate the
    SAME waterline length.

    The scan used to take the task book's absolute ``length_waterline_m``
    for the speed solve while the design point's effective-power call
    took Ayre's default (1.025*Lpp) - two different ships.  For a
    candidate 20 m longer than the task book's ship that was an 8.4 %
    mismatch, and it produced the impossible combination "absorbs more
    than the reference at the band floor but less at its own design
    speed", refused as unbalanceable.

    Both routes describe one hull, so the effective power at the design
    speed divided by the efficiency chain must reproduce the recorded
    shaft power.  The 2 % band is the declared eta_S / eta_R bookkeeping
    difference between the thrust-led propeller route and the classical
    chain; the defect was 8.4 %.
    """
    for cand in scan.feasible:
        factors = propulsion_factors(
            lpp_m=cand.lpp_m, lwl_m=1.025 * cand.lpp_m, beam_m=cand.beam_m,
            draft_m=cand.draft_m, cb=cand.cb, cp=cand.cp, cm=cand.cm,
            cwp=cand.cwp, lcb_pct_fwd=cand.lcb_pct_fwd,
            propeller_diameter_m=cand.propeller_diameter_m,
            speed_ms=SPEC.service_speed, screw="single",
            eta_r=CONFIG_KW["relative_rotative_eff"])
        eta_d = (cand.eta_open_water * CONFIG_KW["relative_rotative_eff"]
                 * factors.eta_h)
        pe_kw = ayre_effective_power(
            displacement_t=cand.displacement_t, speed_kn=SPEC.service_speed /
            0.514444, lpp_m=cand.lpp_m, beam_m=cand.beam_m,
            draft_m=cand.draft_m, cb=cand.cb, xc_pct_fwd=cand.lcb_pct_fwd,
            lwl_m=1.025 * cand.lpp_m, screw="single").pe_bare_kw
        assert pe_kw / eta_d == pytest.approx(cand.shaft_power_kw, rel=0.02)


def test_off_axis_causes_are_classified_not_summarised(scan):
    """The off-axis population is not single-cause: every candidate
    carries a note, the counts add up, and a candidate whose own design
    point already absorbs MORE than the reference power can only be off
    the axis because the balance lies below the band (review §3: the old
    one-sentence disclosure was wrong for part of the population)."""
    causes = scan.off_axis_causes()
    off = [c for c in scan.feasible if c.speed_at_reference_power_kn is None]
    assert sum(causes.values()) == len(off)
    assert set(causes) <= {"below band", "above band", "validity gap",
                           "unclassified"}
    for cand in off:
        assert cand.reference_speed_note
        if cand.shaft_power_kw >= scan.reference_power_kw:
            assert not cand.reference_speed_note.startswith("balance above")


def test_tip_clearance_gate_accepts_its_own_boundary():
    """The gate bound is constructed by the search window (D = 0.75 T),
    so a diameter landing exactly on it is a design, not an overshoot -
    and one ulp past it must not be refused either (N3's class)."""
    assert _tip_clearance_ok(0.75 * 16.5, 16.5, 0.75)
    assert _tip_clearance_ok(0.75 * 16.5 * (1 + 1e-15), 16.5, 0.75)
    assert not _tip_clearance_ok(0.76 * 16.5, 16.5, 0.75)
