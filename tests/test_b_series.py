"""B-series regression acceptance (task 3.3 route 2).

The data module is a page-referenced transcription of Bernitsas/Ray/
Kinley, U-M Report No. 237 (May 1981), verified by the report's own
figure 41 overlay.  The referees here are independent of that check:
the textbook's table 8-12 optimum-line readings (AU5-50 chart) and the
NMRI MP687 measured open-water table (declared cross-family check,
model-scale Rn).
"""

import math

import pytest

from openhull import b_series
from openhull.propeller import (
    b_series_open_water,
    check_cavitation,
    solve_optimal_propeller,
    terminal_design,
)
from openhull.spec import SpecValidationError


def test_transcription_term_counts():
    # guards against a truncated coefficient table
    assert len(b_series.KT_COEFFICIENTS) == 39
    assert len(b_series.KQ_COEFFICIENTS) == 47
    assert len(b_series.DELTA_KT_COEFFICIENTS) == 9
    assert len(b_series.DELTA_KQ_COEFFICIENTS) == 13


def test_figure_41_frozen_values():
    # pixel-calibrated overlay acceptance of the transcription against
    # the report's own B4-70 chart (report p.47 / PDF p.59)
    assert b_series.kt(0.5, 1.0, 0.70, 4) == pytest.approx(0.2710432)
    assert b_series.kq(0.5, 1.0, 0.70, 4) == pytest.approx(0.04244781)


def test_table_8_12_optimum_line_etao_within_1p5_percent():
    # the textbook's AU5-50 chart readings at the optimum line; the
    # closest B-series family member (same Z and expanded-area ratio)
    # must land on the same efficiency - series families differ in
    # KT/KQ, hardly at all in eta_o
    anchors = [
        (0.4035, 0.672, 0.519),
        (0.4347, 0.700, 0.544),
        (0.4663, 0.728, 0.567),
        (0.4978, 0.752, 0.588),
    ]
    for j, pd, eta_au in anchors:
        eta_b = b_series.eta0(j, pd, 0.50, 5)
        assert eta_b == pytest.approx(eta_au, rel=0.015)


# NMRI MP687 measured open-water table (Tokyo 2015 workshop benchmark
# propeller: AU-type, Z=5, P/D=0.750, A_E/A_0=0.500, Rn(d)=4.0e5),
# file Open_Water_Tests_for_JBC_NMRI.txt (internal archive, source
# linked from DATA_SOURCES).  Declared caveats: B-vs-AU cross-family,
# and the measured run is at model-scale Reynolds number.
MP687 = [
    (0.10, 0.3267, 0.03748), (0.15, 0.3112, 0.03629),
    (0.20, 0.2949, 0.03500), (0.25, 0.2777, 0.03361),
    (0.30, 0.2598, 0.03210), (0.35, 0.2410, 0.03047),
    (0.40, 0.2214, 0.02871), (0.45, 0.2010, 0.02682),
    (0.50, 0.1798, 0.02479), (0.55, 0.1577, 0.02261),
    (0.60, 0.1349, 0.02027), (0.65, 0.1112, 0.01777),
    (0.70, 0.0867, 0.01509), (0.75, 0.0614, 0.01224),
    (0.80, 0.0353, 0.00921),
]


def test_mp687_measured_etao_referee():
    devs = []
    for j, kt_m, kq_m in MP687:
        eta_m = j * kt_m / (2 * math.pi * kq_m)
        eta_b = b_series.eta0(j, 0.75, 0.50, 5)
        devs.append(abs(eta_b - eta_m) / eta_m)
    assert sum(devs) / len(devs) < 0.04          # mean |d eta_o| < 4 %
    j_peak = 0.65                                 # measured peak-efficiency point
    eta_m_peak = j_peak * 0.1112 / (2 * math.pi * 0.01777)
    assert b_series.eta0(j_peak, 0.75, 0.50, 5) == pytest.approx(
        eta_m_peak, rel=0.02)


def test_rn_correction_moves_the_right_way():
    kt_base = b_series.kt(0.5, 1.0, 0.70, 4, 2e6)
    kq_base = b_series.kq(0.5, 1.0, 0.70, 4, 2e6)
    kt_full = b_series.kt(0.5, 1.0, 0.70, 4, 1e7)
    kq_full = b_series.kq(0.5, 1.0, 0.70, 4, 1e7)
    # higher Reynolds number: relatively thinner boundary layer ->
    # slightly more thrust, less torque (Lerbs correction direction)
    assert kt_full > kt_base
    assert kq_full < kq_base


def test_factory_range_guards():
    with pytest.raises(SpecValidationError):
        b_series_open_water(8, 0.50)
    with pytest.raises(SpecValidationError):
        b_series_open_water(5, 1.50)
    with pytest.raises(SpecValidationError):
        b_series_open_water(5, 0.50, rn=0.0)
    s = b_series_open_water(5, 0.50)
    with pytest.raises(SpecValidationError):
        s.kt(0.5, 1.6)   # P/D outside the regression validity
    with pytest.raises(SpecValidationError):
        s.kq(0.5, 0.2)   # P/D outside the regression validity


# ---------------------------------------------------------------------------
# end-to-end: the table 8-11/8-12 bulk-carrier terminal design, run
# with the B5-50 series (closest family member of the book's AU5-50)
# ---------------------------------------------------------------------------

_PE_CURVE_HP = [  # table 8-11, speed in kn, effective power in (metric) hp
    (14.0, 4050.0), (14.5, 4570.0), (15.0, 5200.0),
    (15.5, 6090.0), (16.0, 7120.0), (16.5, 8330.0),
]
_HP_TO_KW = 0.735499  # metric horsepower


def _pe_kw(v_ms: float) -> float:
    v_kn = v_ms / 0.514444
    xs = [p[0] for p in _PE_CURVE_HP]
    ys = [p[1] * _HP_TO_KW for p in _PE_CURVE_HP]
    if v_kn <= xs[0]:
        return ys[0]
    if v_kn >= xs[-1]:
        k = -2
        x0, x1 = xs[k], xs[k + 1]
        y0, y1 = ys[k], ys[k + 1]
        return y0 + (y1 - y0) * (v_kn - x0) / (x1 - x0)
    for k in range(len(xs) - 1):
        if xs[k] <= v_kn <= xs[k + 1]:
            return ys[k] + (ys[k + 1] - ys[k]) * (v_kn - xs[k]) / (
                xs[k + 1] - xs[k])
    raise AssertionError


@pytest.fixture(scope="module")
def design_25000t():
    series = b_series_open_water(5, 0.50)
    return terminal_design(
        delivered_power_kw=0.98 * 0.982 * 12000 * _HP_TO_KW,
        n_rps=118.5 / 60.0,
        wake=0.34,
        thrust_deduction=0.26,
        pe_curve=_pe_kw,
        series=series,
        speed_bounds_ms=(7.0, 9.5),
    )


def test_terminal_design_reproduces_the_book_example(design_25000t):
    # book (AU5-50): Vmax 16.11 kn, D 5.897 m, eta_o 0.569
    v_kn = design_25000t.v_max_ms * 1.94384
    assert v_kn == pytest.approx(16.11, abs=0.15)
    assert design_25000t.propeller.eta_o == pytest.approx(0.569, abs=0.02)
    assert design_25000t.propeller.diameter_m == pytest.approx(
        5.897, rel=0.03)
    # pitch ratio is series-family specific (B runs coarser pitch at the
    # same loading); declared, not asserted against the AU value
    assert 0.70 <= design_25000t.propeller.pitch_ratio <= 0.90
    # thrust power crosses the demand (that IS the design condition)
    assert design_25000t.pte_kw == pytest.approx(design_25000t.pe_kw,
                                                 rel=2e-3)


def test_cavitation_check_on_the_designed_propeller(design_25000t):
    prop = design_25000t.propeller
    res = check_cavitation(
        thrust_n=prop.thrust_n,
        va_ms=prop.va_ms,
        n_rps=prop.n_rps,
        diameter_m=prop.diameter_m,
        pitch_ratio=prop.pitch_ratio,
        aeao_available=0.50,
        hs_m=5.99,
    )
    # the operating sigma must sit inside the verified Burrill band,
    # otherwise the check below would be meaningless
    assert 0.387 <= res.sigma_0_7r <= 0.483
    # the book's own example needed AE/A0 0.642 (AU5-65); this design
    # lands in the same regime - the fixed 0.50 area reports a shortfall
    assert res.aeao_required == pytest.approx(0.62, abs=0.03)
    assert not res.ok
