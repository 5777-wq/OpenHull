"""Design-engine tests (task 3.3) on an analytic mock series.

The engine maths - torque-demand inversion, diameter sweep, optimum
selection, and the attainable-speed bisection - is series-independent,
so it is verified here against a smooth analytic stand-in.  The real
series (route experiments) plug into the same OpenWaterSeries interface
with their own acceptance tests.
"""

import math

import pytest

from openhull.propeller import (
    OpenWaterSeries,
    solve_optimal_propeller,
    solve_speed_thrust_balance,
    terminal_design,
)
from openhull.spec import SpecValidationError


def _mock_kt(j: float, pd: float) -> float:
    jmax = 1.2 * pd + 0.3
    if j >= jmax:
        return 0.0
    return 0.5 * pd ** 1.2 * (1.0 - j / jmax) ** 1.5


def _mock_kq(j: float, pd: float) -> float:
    jmax = 1.2 * pd + 0.3
    if j >= jmax:
        return 0.0
    return 0.06 * pd ** 1.3 * (1.0 - j / jmax) ** 1.8


MOCK = OpenWaterSeries(
    name="MOCK",
    kt=_mock_kt,
    kq=_mock_kq,
    j_domain=(0.05, 1.4),
    pd_domain=(0.4, 1.2),
    aeao_available=0.5,
    provenance="analytic stand-in for engine tests only",
)


def test_optimum_propeller_is_interior_and_consistent():
    res = solve_optimal_propeller(8500.0, 5.45, 1.975, MOCK)
    assert 0.4 <= res.pitch_ratio <= 1.2
    # open-water identity: thrust power = eta_o * delivered power
    identity = res.thrust_n * res.va_ms - res.eta_o * res.delivered_power_kw * 1e3
    assert abs(identity) < 1e-5 * res.delivered_power_kw * 1e3
    # efficiency is the series efficiency at the operating point
    assert res.eta_o == pytest.approx(
        res.j * res.kt / (2 * math.pi * res.kq), rel=1e-12)


def test_torque_demand_is_solved_exactly():
    res = solve_optimal_propeller(8500.0, 5.45, 1.975, MOCK)
    kq_required = res.delivered_power_kw * 1e3 / (
        2 * math.pi * 1025.9 * res.n_rps ** 3 * res.diameter_m ** 5)
    assert res.kq == pytest.approx(kq_required, rel=1e-9)
    assert MOCK.kq(res.j, res.pitch_ratio) == pytest.approx(
        kq_required, rel=1e-9)


def test_optimum_beats_neighbouring_diameters():
    res = solve_optimal_propeller(8500.0, 5.45, 1.975, MOCK)
    for d in (res.diameter_m * 0.9, res.diameter_m * 1.1):
        j = res.va_ms / (1.975 * d)
        kq_req = 8500e3 / (2 * math.pi * 1025.9 * 1.975 ** 3 * d ** 5)
        lo, hi = MOCK.pd_domain
        # only compare where the torque demand is reachable at all -
        # outside that band the engine itself would have refused
        if not (MOCK.kq(j, lo) <= kq_req <= MOCK.kq(j, hi)):
            continue
        a, b = lo, hi
        for _ in range(80):
            mid = 0.5 * (a + b)
            if MOCK.kq(j, mid) < kq_req:
                a = mid
            else:
                b = mid
        pd = 0.5 * (a + b)
        assert MOCK.eta_o(j, pd) <= res.eta_o + 1e-9


def test_out_of_envelope_operating_point_refused():
    # with the diameter band constrained away from the series domain,
    # every diameter maps to an advance coefficient outside it
    with pytest.raises(SpecValidationError):
        solve_optimal_propeller(8500.0, 60.0, 1.0, MOCK,
                                d_bounds_m=(5.0, 8.0))


def test_negative_power_refused():
    with pytest.raises(SpecValidationError):
        solve_optimal_propeller(-1.0, 5.0, 2.0, MOCK)


def test_terminal_design_finds_the_crossing():
    # hull demand: 6300 kW at 7 m/s, cubically rising
    pe = lambda v: 6300.0 * (v / 7.0) ** 3  # noqa: E731
    td = terminal_design(8500.0, 1.975, 0.34, 0.26, pe, MOCK,
                         speed_bounds_ms=(4.0, 10.0))
    # at the attainable speed the thrust power crosses the demand
    assert td.pte_kw == pytest.approx(td.pe_kw, rel=2e-3)
    assert td.hull_efficiency == pytest.approx(0.74 / 0.66, abs=1e-9)
    assert 4.0 < td.v_max_ms < 10.0
    assert td.propeller.eta_o > 0.2


def test_terminal_design_refuses_unbracketed_demand():
    pe = lambda v: 1e9 * v ** 3  # noqa: E731  (impossible hull demand)
    with pytest.raises(SpecValidationError):
        terminal_design(8500.0, 1.975, 0.34, 0.26, pe, MOCK,
                        speed_bounds_ms=(4.0, 10.0))


def test_thrust_balance_recovers_a_planted_speed():
    # plant a propeller/condition, derive the hull curve that balances
    # it exactly at v0 = 7 m/s, and check the solver walks back to it:
    # P_E(v) = P_E(v0) * (v/v0)^2 in kW with P_E(v0) chosen so that
    # T_req(v0) = P_E(v0)*1e3/(v0*(1-t)) equals the available thrust
    v0 = 7.0
    pitch, n_rps, d = 0.95, 1.975, 5.5
    t_ded = 0.26
    j0 = v0 * (1.0 - 0.34) / (n_rps * d)
    kt0 = MOCK.kt(j0, pitch)
    t_avail0 = 1025.9 * n_rps ** 2 * d ** 4 * kt0
    pe_v0_kw = t_avail0 * v0 * (1.0 - t_ded) / 1e3

    def pe(v: float) -> float:
        return pe_v0_kw * (v / v0) ** 2

    sol = solve_speed_thrust_balance(
        MOCK, pitch, n_rps, d, pe, wake=0.34, thrust_deduction=t_ded,
        v_bounds_ms=(4.0, 10.0))
    assert sol.v_ms == pytest.approx(v0, abs=5e-3)
    assert sol.thrust_available_n == pytest.approx(
        sol.thrust_required_n, rel=1e-3)
    assert sol.eta_o == pytest.approx(
        sol.j * sol.kt / (2 * math.pi * MOCK.kq(sol.j, pitch)), rel=1e-9)


def test_thrust_balance_refuses_unbracketed_band():
    pe = lambda v: 1e12  # noqa: E731  (hull demand no propeller can meet)
    with pytest.raises(SpecValidationError):
        solve_speed_thrust_balance(
            MOCK, 0.95, 1.975, 5.5, pe, wake=0.34, thrust_deduction=0.26)


def test_disjoint_diameter_window_names_both_bands():
    """R-4 (review 2026-09-24): the window and the J domain are
    INTERSECTED here, so a d_bounds_m refusal means the intersection is
    empty.  When that happens the message must print both bands - the
    reviewer saw 73 of these and could not tell a bad window from a bad
    speed unit, which is exactly how the scan's unit defect (Va 3.78x
    the ship speed) stayed invisible for months.
    """
    with pytest.raises(SpecValidationError) as excinfo:
        # a fast advance speed with a small-propeller window: every J in
        # the window sits ABOVE the series domain
        solve_optimal_propeller(
            10_000.0, va_ms=20.0, n_rps=2.0, series=MOCK,
            d_bounds_m=(0.5, 0.8))
    message = str(excinfo.value)
    assert "D 0.50-0.80 m" in message            # the window
    assert "J 12.500..20.000" in message         # what it maps to
    assert "series domain" in message            # what it missed
    assert "advance speed" in message            # where to look


def test_diameter_window_is_intersected_not_rejected():
    """A window that only PARTLY overlaps the J domain is searched on
    the overlap (intersection is not extrapolation); only an empty
    intersection is refused."""
    # the mock domain is (0.05, 1.35); a window spanning beyond it must
    # still solve
    prop = solve_optimal_propeller(
        500.0, va_ms=4.0, n_rps=2.0, series=MOCK, d_bounds_m=(0.5, 60.0))
    assert prop.diameter_m > 0
    assert MOCK.j_domain[0] <= prop.j <= MOCK.j_domain[1]
