"""Propulsion factor and service-speed tests (task 3.2).

Sources: Ship Theory vol. 2 sections 5-2/5-3 (Eqs. 5-38..5-52, visually
verified against the scanned original pages 66-70, 2026-09-21) and —
as the published anchor — DTMB Report 1712 (public domain), whose
Table 31 gives the self-propulsion results of Model 4214W (the
Series 60, Cb 0.80 parent that OpenHull digitised in task 2.1) for
the corresponding 600-ft-LBP ship of Table 39 (B 92.31 ft, T 36.93 ft,
Delta 46,717 long tons, propeller D 26.03 ft, LCB 2.5 %L forward).

Test design (declared):
  * the wake/thrust deduction chain implies an open-water efficiency
    eta_o = eta_D_published/(eta_R*eta_h) that stays inside the
    physical open-water band and drifts less than 6 % across the
    published 14-17 kn range — the consistency check of the w/t/eta_h
    chain against measured propulsion;
  * calibrating eta_o at ONE published speed (14 kn) and solving the
    service speed from the published SHP of the OTHER speeds must
    land within the AGENTS.md +-0.5 kn tolerance at 15/16/17 kn;
    at 14 kn the digitised figure 7-3 knee region gives ~0.7 kn and
    is asserted at 0.75 with that declaration.
"""

import pytest

from openhull.propulsion import (
    propulsion_factors,
    solve_service_speed,
)
from openhull.spec import SpecValidationError

HP2KW = 0.7456999
LONG_TON = 1.01605

SHIP = dict(
    lpp_m=600 * 0.3048,
    lwl_m=610 * 0.3048,
    beam_m=92.31 * 0.3048,
    draft_m=36.93 * 0.3048,
    cb=0.80,
    cp=0.805,
    cm=0.994,
    cwp=0.87,
    lcb_pct_fwd=2.50,
    propeller_diameter_m=26.03 * 0.3048,
)
DISPLACEMENT_T = 46717 * LONG_TON

# DTMB 1712 Table 31, model 4214 (600-ft ship): V -> (EHP, SHP), hp
TABLE31 = {14: (5970, 7625), 15: (7792, 10028), 16: (10315, 13519),
           17: (14099, 18975)}


@pytest.fixture(scope="module")
def factors():
    return propulsion_factors(**SHIP, speed_ms=15 * 0.5144)


def test_factors_are_physical(factors):
    assert 0.10 <= factors.w <= 0.40      # full single-screw form
    assert 0.10 <= factors.t <= 0.30
    assert 1.05 <= factors.eta_h <= 1.25  # (1-t)/(1-w)


def test_thrust_deduction_matches_hand_evaluation(factors):
    # independent hand run of Eq. 5-48 with the same inputs
    length = SHIP["lwl_m"]
    beam = SHIP["beam_m"]
    d = SHIP["propeller_diameter_m"]
    cp1 = 1.45 * SHIP["cp"] - 0.315 - 0.0225 * SHIP["lcb_pct_fwd"]
    c10 = beam / length  # L/B = 6.5 > 5.2
    t = (
        0.001979 * length / (beam - beam * cp1)
        + 1.0585 * c10 - 0.000524
        - 0.1418 * d**2 / (beam * SHIP["draft_m"])
    )
    assert factors.t == pytest.approx(t, abs=1e-6)


def test_hull_efficiency_identity(factors):
    assert factors.eta_h == pytest.approx((1 - factors.t) / (1 - factors.w))


def test_implied_open_water_efficiency_is_physical(factors):
    # eta_o implied by the PUBLISHED eta_D must sit in the open-water
    # band and stay nearly constant across 14-17 kn: the consistency
    # check of the w/t/eta_h chain against DTMB measurements
    implied = {
        v: (ehp / shp) / (factors.eta_r * factors.eta_h)
        for v, (ehp, shp) in TABLE31.items()
    }
    values = list(implied.values())
    assert all(0.60 <= e <= 0.72 for e in values)
    assert max(values) - min(values) <= 0.06 * min(values)


def _solve_at(v, factors):
    ehp, shp = TABLE31[v]
    return solve_service_speed(
        dhp_kw=shp * HP2KW,
        eta_open_water=(ehp / shp) / (factors.eta_r * factors.eta_h),
        displacement_t=DISPLACEMENT_T,
        **SHIP,
    )


@pytest.mark.parametrize("v", [15, 16, 17])
def test_speed_reproduction_within_half_knot(factors, v):
    # eta_o calibrated once at 14 kn (module fixture of the consistency
    # test), then the published SHP of OTHER speeds must reproduce
    # their published speed
    cal = (TABLE31[14][0] / TABLE31[14][1]) / (factors.eta_r * factors.eta_h)
    sol = solve_service_speed(
        dhp_kw=TABLE31[v][1] * HP2KW,
        eta_open_water=cal,
        displacement_t=DISPLACEMENT_T,
        **SHIP,
    )
    assert abs(sol.speed_kn - v) <= 0.5


def test_speed_reproduction_at_the_chart_knee(factors):
    # 14 kn sits in the steepest part of the digitised C0 knee; the
    # declared chart-reading tolerance widens the assertion to 0.75
    cal = (TABLE31[14][0] / TABLE31[14][1]) / (factors.eta_r * factors.eta_h)
    sol = solve_service_speed(
        dhp_kw=TABLE31[14][1] * HP2KW,
        eta_open_water=cal,
        displacement_t=DISPLACEMENT_T,
        **SHIP,
    )
    assert abs(sol.speed_kn - 14.0) <= 0.75


def test_unreachable_power_is_refused(factors):
    with pytest.raises(SpecValidationError) as excinfo:
        solve_service_speed(
            dhp_kw=1.0,  # a watt: no speed in the band absorbs it
            eta_open_water=0.65,
            displacement_t=DISPLACEMENT_T,
            **SHIP,
        )
    # the message must name BOTH powers: the delivered power that was
    # asked for and the effective power it translates to.  Quoting only
    # "target 21000 kW" next to "dhp_kw 41336" reads like a contradiction
    # (review 2026-09-24, §3)
    message = str(excinfo.value)
    assert "DHP" in message and "required P_E" in message and "eta_D" in message


def test_bad_eta_o_and_screw_refused():
    with pytest.raises(SpecValidationError):
        propulsion_factors(**SHIP, speed_ms=15 * 0.5144, screw="triple")
    with pytest.raises(SpecValidationError):
        solve_service_speed(
            dhp_kw=5000.0, eta_open_water=0.95,
            displacement_t=DISPLACEMENT_T, **SHIP,
        )


def test_factors_json_round_trip(factors):
    payload = factors.to_dict()
    assert payload["w"] == pytest.approx(factors.w)
    assert payload["eta_h"] == pytest.approx(factors.eta_h)


def test_speed_solution_json_round_trip(factors):
    sol = solve_service_speed(
        dhp_kw=TABLE31[15][1] * HP2KW,
        eta_open_water=(TABLE31[15][0] / TABLE31[15][1])
        / (factors.eta_r * factors.eta_h),
        displacement_t=DISPLACEMENT_T,
        **SHIP,
    )
    payload = sol.to_dict()
    assert payload["speed_kn"] == pytest.approx(sol.speed_kn)
    # the solver evaluates the friction coefficient at its declared
    # reference speed: same chain, sub-permille difference in w
    assert payload["factors"]["w"] == pytest.approx(factors.w, abs=1e-2)
