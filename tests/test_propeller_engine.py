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
