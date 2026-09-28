"""Holtrop-Mennen (1982) effective-power anchors (round-8 backlog).

The acceptance anchor is the paper's OWN section-5 worked example
(L 205 m, B 32 m, T 10 m, nabla 37,500 m3, 25 kn) — a published worked
example, the charter's own anchor class.  Every quantity the paper
prints is pinned to its printed digits: geometry intermediates at
printed precision, resistance components at 0.5 % (rounding in the
printed table), totals at 1 %.  The example reproduces WITH ZERO
declared defects — including R_B = 0.049 kN.
"""

import pytest

from openhull.holtrop import (holtrop_lcb_from_taskbook,
                              holtrop_mennen_power)

EXAMPLE = dict(
    speed_kn=25.0, lwl_m=205.0, lpp_m=200.0, beam_m=32.0, draft_m=10.0,
    draft_fp_m=10.0, displacement_volume_m3=37500.0, cm=0.980,
    cwp=0.750, lcb_pct_lpp=-2.02, cp=0.5833,
    bulb_area_m2=20.0, bulb_centre_above_keel_m=4.0,
    transom_area_m2=16.0, appendage_area_m2=50.0, appendage_factor=1.50,
    c_stern=10.0,
)


@pytest.fixture(scope="module")
def result():
    return holtrop_mennen_power(**EXAMPLE)


def test_lcb_datum_conversion_matches_the_example():
    # 2.02 %Lpp aft on Lpp 200 / L 205 -> lcb -0.75 %L (the paper's own
    # table value; verifies the 1/2-L datum convention)
    assert holtrop_lcb_from_taskbook(-2.02, 200.0, 205.0) == \
        pytest.approx(-0.75, abs=0.01)


def test_geometry_intermediates(result):
    c = result.coefficients
    assert result.length_run_m == pytest.approx(81.385, abs=0.01)
    assert c["c12"] == pytest.approx(0.5102, abs=5e-4)
    assert c["c13"] == pytest.approx(1.030, abs=1e-6)
    assert result.form_factor == pytest.approx(1.156, abs=0.002)
    assert result.wetted_area_m2 == pytest.approx(7381.45, rel=5e-4)
    assert result.reynolds == pytest.approx(2.2185e9, rel=2e-3)
    assert result.cf == pytest.approx(0.001390, abs=2e-6)


def test_wave_chain_intermediates(result):
    c = result.coefficients
    assert c["c7"] == pytest.approx(0.1561, abs=5e-4)
    assert c["iE_deg"] == pytest.approx(12.08, abs=0.02)
    assert c["c1"] == pytest.approx(1.398, abs=0.005)
    assert c["c3"] == pytest.approx(0.02119, abs=1e-4)
    assert c["c2"] == pytest.approx(0.7595, abs=5e-4)
    assert c["c5"] == pytest.approx(0.9592, abs=5e-4)
    assert c["m1"] == pytest.approx(-2.1274, abs=0.003)
    assert c["c15"] == pytest.approx(-1.69385, abs=1e-6)
    assert c["m2"] == pytest.approx(-0.17087, abs=5e-4)
    assert c["lambda"] == pytest.approx(0.6513, abs=5e-4)


def test_resistance_components_and_effective_power(result):
    assert result.r_friction_kn == pytest.approx(869.63, rel=5e-3)
    assert result.r_appendage_kn == pytest.approx(8.83, rel=5e-3)
    assert result.r_wave_kn == pytest.approx(557.11, rel=5e-3)
    # the paper prints CA rounded to 0.000352; R_A back-solves to
    # 0.0003526 - the 0.6 % gap is print rounding, not method
    assert result.coefficients["CA"] == pytest.approx(0.000352, abs=2e-6)
    assert result.r_correlation_kn == pytest.approx(221.98, rel=0.01)
    assert result.r_transom_kn == pytest.approx(0.0, abs=1e-9)
    assert result.r_total_kn == pytest.approx(1793.26, rel=0.01)
    assert result.pe_kw == pytest.approx(23063.0, rel=0.01)


def test_rb_anchor(result):
    # the bulb component the round-8 transcription hand-check first got
    # wrong by a decade — pinned positively: 0.049 kN as printed
    assert result.r_bulb_kn == pytest.approx(0.049, rel=0.03)
    assert result.coefficients["PB"] == pytest.approx(0.6261, abs=2e-3)
    assert result.coefficients["FnI"] == pytest.approx(1.5084, abs=2e-3)


def test_structural_refusals():
    with pytest.raises(Exception):
        holtrop_mennen_power(**{**EXAMPLE, "cm": 0.10})
    # derived-Cp refusal: a 30 % displacement drops the waterline-length
    # Cp to 0.17, below the L_R degeneration bound
    slim = {**EXAMPLE}
    slim.pop("cp")
    slim["displacement_volume_m3"] = 37500.0 * 0.3
    with pytest.raises(Exception):
        holtrop_mennen_power(**slim)
