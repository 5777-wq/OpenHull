"""Ayre effective-power tests: Ship Theory vol. 1 section 7-1 (task 3.1).

The binding anchor is the worked example of table 7-8 — a published
estimate for a ship with Lbp 122 m / Lwl 125.5 m / B 16.8 m / T 7.94 m,
Delta 11,970 t, Cb 0.721, LCB 0.50 %L forward: C4 = 441 / 401 and
Pe = 1860 / 2521 kW at 14 / 15 kn.  Reproducing it validates the chart
digitisation (C0(5.33, 0.70) = 449.5, C0(5.33, 0.75) = 424.2 are the
chain-inverted chart values), every correction formula (7-22..7-25,
including the fuller-ship sign flip and the three-part LCB rule) and
the units trap (V/sqrt(L) in knots/sqrt-ft).

Units and applicability guards follow AGENTS.md section 6: the Ayre
band is V/sqrt(L) 0.50-1.20 and (v1) the digitised C0 band is
L/Delta^(1/3) 4.88-6.41 — the JBC service speed (14.5 kn on 280 m,
V/sqrt(L) = 0.478) is correctly REFUSED.
"""

import json

import pytest

from openhull.resistance import (
    RESISTANCE_ALGORITHMS,
    ayre_effective_power,
    resistance_algorithms,
)
from openhull.spec import SpecValidationError

EXAMPLE = dict(
    displacement_t=11970.0,
    lpp_m=122.0,
    beam_m=16.8,
    draft_m=7.94,
    cb=0.721,
    xc_pct_fwd=0.50,
    lwl_m=125.5,
)


@pytest.fixture(scope="module")
def at_14():
    return ayre_effective_power(speed_kn=14.0, **EXAMPLE)


@pytest.fixture(scope="module")
def at_15():
    return ayre_effective_power(speed_kn=15.0, **EXAMPLE)


# ---------------------------------------------------------------------------
# the published worked example (table 7-8)
# ---------------------------------------------------------------------------


def test_worked_example_c4(at_14, at_15):
    assert at_14.c4 == pytest.approx(441, abs=3)
    assert at_15.c4 == pytest.approx(401, abs=3)


def test_worked_example_effective_power(at_14, at_15):
    assert at_14.pe_kw == pytest.approx(1860, rel=0.02)
    assert at_15.pe_kw == pytest.approx(2521, rel=0.02)


def test_worked_example_correction_chain(at_14):
    # the 14 kn ship is THINNER than standard (Cb 0.721 < Cbc 0.730):
    # the Cb correction increases C0 by table 7-6 (~0.51 %), the LCB
    # sits behind the standard position and is penalised in full
    labels = [c.label for c in at_14.corrections]
    assert labels == [
        "Cb correction", "B/T correction", "LCB correction",
        "Lwl correction",
    ]
    assert at_14.corrections[0].percent == pytest.approx(0.51, abs=0.06)
    assert at_14.corrections[0].delta > 0
    assert at_14.corrections[2].delta < 0
    # the B/T is 2.12 against the standard 2.0 -> penalty
    assert at_14.corrections[1].percent < 0


def test_fuller_ship_flips_the_cb_correction_and_suppresses_lcb():
    # at 15 kn the standard Cbc drops to 0.705 < Cb 0.721: the ship is
    # now FULLER, Eq. 7-22 gives a negative correction, and the LCB
    # deviation is within its abs penalty -> no LCB correction
    res = ayre_effective_power(speed_kn=15.0, **EXAMPLE)
    assert res.corrections[0].percent < 0
    assert res.corrections[0].percent == pytest.approx(-4.83, abs=0.1)
    assert res.corrections[2].delta == 0.0


def test_units_trap_speed_length_ratio(at_14):
    # 14 kn on 122 m: knots/sqrt-ft = 0.70, NOT 14/sqrt(122) = 1.27
    assert at_14.v_sqrt_l == pytest.approx(0.700, abs=0.004)
    assert at_14.fr == pytest.approx(0.208, abs=0.002)
    assert at_14.length_ratio == pytest.approx(5.33, abs=0.01)


def test_bare_hull_power_is_pe_over_1_08(at_14):
    assert at_14.pe_bare_kw == pytest.approx(at_14.pe_kw / 1.08)


# ---------------------------------------------------------------------------
# registry and guards
# ---------------------------------------------------------------------------


def test_registry_lists_ayre_implemented_and_holtrop_pending():
    assert RESISTANCE_ALGORITHMS["ayre"].implemented
    assert not RESISTANCE_ALGORITHMS["holtrop_mennen"].implemented
    assert "ayre" in resistance_algorithms()
    assert "Ship Theory vol. 1" in RESISTANCE_ALGORITHMS["ayre"].citation


def test_jbc_service_speed_is_refused_outside_the_band():
    # JBC: 14.5 kn on Lbp 280 m -> V/sqrt(L) = 0.478 < 0.50
    with pytest.raises(SpecValidationError) as err:
        ayre_effective_power(
            displacement_t=182_829.1, speed_kn=14.5, lpp_m=280.0,
            beam_m=45.0, draft_m=16.5, cb=0.858, xc_pct_fwd=2.5475,
            lwl_m=285.0,
        )
    assert "0.478" in str(err.value)


def test_digitised_length_ratio_band_is_enforced():
    # Delta 5000 t on 122 m: L/Delta^(1/3) = 7.13 > 6.41
    with pytest.raises(SpecValidationError) as err:
        ayre_effective_power(
            displacement_t=5000.0, speed_kn=12.0, lpp_m=122.0,
            beam_m=16.8, draft_m=7.94, cb=0.721, xc_pct_fwd=0.5,
        )
    assert "4.88-6.41" in str(err.value)


def test_lcb_offset_beyond_tables_is_refused():
    # LCB 1.0 %L AFT vs the 14 kn standard 1.31 %L fwd: gap 2.31 %L
    with pytest.raises(SpecValidationError) as err:
        ayre_effective_power(speed_kn=14.0, **{**EXAMPLE, "xc_pct_fwd": -1.0})
    assert "2 %L" in str(err.value)


def test_bad_screw_and_nonpositive_inputs_refused():
    with pytest.raises(SpecValidationError):
        ayre_effective_power(speed_kn=14.0, **{**EXAMPLE, "screw": "triple"})
    with pytest.raises(SpecValidationError):
        ayre_effective_power(speed_kn=14.0, **{**EXAMPLE, "cb": 1.5})


# ---------------------------------------------------------------------------
# twin screw, serialization, determinism
# ---------------------------------------------------------------------------


def test_twin_screw_raises_standard_cbc(at_14):
    twin = ayre_effective_power(speed_kn=14.0, **{**EXAMPLE, "screw": "twin"})
    assert twin.cbc_std == pytest.approx(at_14.cbc_std + 0.01)


def test_json_round_trip(at_14):
    payload = json.loads(json.dumps(at_14.to_dict()))
    assert payload["c4"] == pytest.approx(at_14.c4)
    assert payload["pe_kw"] == pytest.approx(at_14.pe_kw)
    assert len(payload["corrections"]) == 4
    assert payload["corrections"][0]["label"] == "Cb correction"


def test_determinism(at_14):
    again = ayre_effective_power(speed_kn=14.0, **EXAMPLE)
    assert again.to_dict() == at_14.to_dict()
