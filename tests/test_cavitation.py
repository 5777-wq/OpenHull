"""Burrill cavitation check (task 3.3, propeller.py) against the book's
own worked examples.  All book values are in kgf/m^2 engineering units;
SI conversions use g = 9.80665 exactly as documented in the module."""

import math

import pytest

from openhull.propeller import (
    BURRILL_COMMERCIAL_LINE,
    burrill_tau_c_limit,
    check_cavitation,
    required_expanded_area,
    sigma_0_7r,
)
from openhull.spec import SpecValidationError

G = 9.80665

# table 6-2 (25,000 t bulk carrier, AU5-65): printed working values
T62 = dict(
    va_ms=5.46,             # row 3: V_A = 0.515 (1-w) V = 5.46 m/s
    n_rps=118.5 / 60.0,     # 118.5 r/min
    diameter_m=5.747,
    pitch_ratio=0.782,
    hs_m=5.99,
    p0_kgf=16470.0,         # row 2: p0 = pa + gamma*hs = 10330 + 6140
    thrust_n=88800.0 * G,   # row 11: T = 88800 kgf
)

# table 8-29 (MAU4-40/55/70 example): printed sigma values, p0-pv convention
# rows are (V_A m/s, V^2_0.7R = V_A^2 + (0.7*pi*N*D/60)^2 (m/s)^2, sigma)
T829 = [
    (5.223, 797.92, 0.389),
    (5.176, 763.53, 0.407),
    (5.109, 747.87, 0.416),
]
P0_MINUS_PV_829 = 16255.0 * G  # p0 - pv = 16255 kgf/m^2 (section 8-5)


def test_line_carries_four_book_anchors():
    assert BURRILL_COMMERCIAL_LINE == (
        (0.389, 0.162), (0.407, 0.164), (0.416, 0.169), (0.481, 0.175))


def test_sigma_reproduces_table_6_2():
    p0_eff = T62["p0_kgf"] * G
    s = sigma_0_7r(T62["va_ms"], T62["n_rps"], T62["diameter_m"], p0_eff)
    assert s == pytest.approx(0.481, abs=0.002)


def test_line_reads_back_the_anchors_exactly():
    for s, t in BURRILL_COMMERCIAL_LINE:
        assert burrill_tau_c_limit(s) == pytest.approx(t, abs=1e-12)


def test_line_monotone_between_anchors():
    assert burrill_tau_c_limit(0.42) == pytest.approx(0.16945, abs=1e-4)
    assert burrill_tau_c_limit(0.45) > burrill_tau_c_limit(0.42)


@pytest.mark.parametrize("va,v2sq,sigma_expected", T829)
def test_sigma_reproduces_table_8_29(va, v2sq, sigma_expected):
    # invert the printed relative-velocity square for the diameter*revs
    # product: v_tip = sqrt(v2sq - va^2); the book prints
    # (0.7*pi*N*D/60)^2 directly, so pick n*D to reproduce it exactly
    v_tip = math.sqrt(v2sq - va * va)
    n_rps = 2.0
    d = v_tip / (0.7 * math.pi * n_rps)
    s = sigma_0_7r(va, n_rps, d, P0_MINUS_PV_829)
    assert s == pytest.approx(sigma_expected, abs=0.0015)


def test_required_area_reproduces_table_6_2_rows_12_to_15():
    p0_eff = T62["p0_kgf"] * G
    sigma, tau, ae_req = required_expanded_area(
        T62["thrust_n"], T62["va_ms"], T62["n_rps"], T62["diameter_m"],
        T62["pitch_ratio"], p0_eff)
    assert sigma == pytest.approx(0.481, abs=0.002)
    assert tau == pytest.approx(0.175, abs=0.001)
    ap_req = ae_req * (1.067 - 0.229 * T62["pitch_ratio"])
    assert ap_req == pytest.approx(14.80, abs=0.15)   # row 12
    assert ae_req == pytest.approx(16.68, abs=0.20)   # row 13
    a0 = math.pi / 4.0 * T62["diameter_m"] ** 2
    assert a0 == pytest.approx(26.00, abs=0.10)       # row 14 (loose print)
    assert ae_req / a0 == pytest.approx(0.642, abs=0.005)  # row 15


def test_check_cavitation_passes_designed_area():
    p0_eff = T62["p0_kgf"] * G
    res = check_cavitation(
        T62["thrust_n"], T62["va_ms"], T62["n_rps"], T62["diameter_m"],
        T62["pitch_ratio"], 0.65, hs_m=T62["hs_m"], subtract_vapour=False)
    # the book designed AE/A0 = 0.65 against a required 0.642
    assert res.ok
    assert res.aeao_required == pytest.approx(0.642, abs=0.006)
    assert res.margin == pytest.approx(0.65 - 0.642, abs=0.006)


def test_check_cavitation_reports_shortfall_for_au5_50():
    p0_eff = T62["p0_kgf"] * G
    res = check_cavitation(
        T62["thrust_n"], T62["va_ms"], T62["n_rps"], T62["diameter_m"],
        T62["pitch_ratio"], 0.50, hs_m=T62["hs_m"], subtract_vapour=False)
    assert not res.ok
    assert res.margin == pytest.approx(0.50 - 0.642, abs=0.006)
    assert "SHORTFALL" in res.verdict


def test_line_refuses_outside_verified_domain():
    with pytest.raises(SpecValidationError):
        burrill_tau_c_limit(0.30)
    with pytest.raises(SpecValidationError):
        burrill_tau_c_limit(0.60)


def test_check_cavitation_propagates_domain_guard():
    # huge diameter -> sigma far below the verified line domain
    with pytest.raises(SpecValidationError):
        check_cavitation(
            5e5, 5.0, 2.0, 20.0, 0.7, 0.5, hs_m=6.0)


def test_negative_thrust_refused():
    with pytest.raises(SpecValidationError):
        required_expanded_area(
            -1.0, 5.0, 2.0, 5.0, 0.7, 160000.0)
