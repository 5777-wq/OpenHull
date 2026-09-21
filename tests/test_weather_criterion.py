"""Severe wind and rolling criterion tests: IS Code 2.3 (task 3.5b).

Sources (AGENTS.md section 5): the criterion text, the formula images
and the X1/X2/k/s tables were verified verbatim against a public
reproduction of the code (imorules.com, 2026-09-21) and cross-checked
table-by-table against IMO Resolution A.562(14) (official IMO CDN
copy) — which also settles the B/d = 3.3 -> 0.84 X1 row the
reproduction omits and the normative area definitions of figure 2.3.1.

No published JBC weather-criterion anchor exists (declared in
VALIDATION.md), so acceptance rests on:
  * an independent hand evaluation of every 2.3.4 intermediate for the
    JBC chain (X1, X2, k, r, s, T, C, phi_1) and of l_w1 from 2.3.2;
  * exact identities (lw2 = 1.5 lw1, the phi_0 intercept, the 50 deg
    theta_2 cap);
  * grid-refinement convergence of the area integrals;
  * the 2.3.5 applicability guards refusing out-of-band ships.
"""

import json
import math

import pytest

from openhull.cli import main, run_taskbook
from openhull.geometry import OffsetsTable
from openhull.linesplan import parent_to_taskbook
from openhull.spec import SpecValidationError
from openhull.stability import weather_criterion

TASKBOOK = "examples/taskbook_bulk_carrier.yaml"

DELTA = 182_829.1
KG = 13.29
DRAFT = 16.5
B = 45.0
LWL = 285.0
WINDAGE_A = 2380.0
WINDAGE_Z = 12.5


@pytest.fixture(scope="module")
def jbc_hull():
    table, _report = parent_to_taskbook(
        lpp=280.0, beam=B, draft=DRAFT,
        target_cb=0.8580, target_lcb_pct=2.5475,
    )
    return table


@pytest.fixture(scope="module")
def weather(jbc_hull):
    return weather_criterion(
        jbc_hull, DELTA, KG, depth_m=25.0,
        windage_area_m2=WINDAGE_A, windage_lever_z_m=WINDAGE_Z,
        length_waterline_m=LWL,
    )


def test_roll_chain_matches_independent_hand_evaluation(weather):
    # X1: linear interpolation between the 2.7 -> 0.95 and 2.8 -> 0.93
    b_over_d = B / DRAFT
    x1 = 0.95 + (0.93 - 0.95) * (b_over_d - 2.7) / 0.1
    # X2: Cb ~ 0.858 is above the last table row -> 1.00
    # k: no bilge keels -> 1.0; r = 0.73 + 0.6 (KG/d - 1)
    r = 0.73 + 0.6 * (KG / DRAFT - 1.0)
    # C and the rolling period (GM from the chain KM, no free surfaces)
    c = 0.373 + 0.023 * b_over_d - 0.043 * (LWL / 100.0)
    km = 18.592  # chain KM pinned by the task-2.6 tests
    period = 2.0 * c * B / math.sqrt(km - KG)
    s = 0.065 + (0.053 - 0.065) * (period - 12.0) / 2.0
    phi1 = 109.0 * 1.0 * x1 * 1.0 * math.sqrt(r * s)
    assert weather.x1 == pytest.approx(x1, abs=5e-4)
    assert weather.x2 == pytest.approx(1.0)
    assert weather.k_factor == pytest.approx(1.0)
    assert weather.r_factor == pytest.approx(r, abs=5e-4)
    assert weather.c_coefficient == pytest.approx(c, abs=5e-4)
    assert weather.roll_period_s == pytest.approx(period, abs=0.05)
    assert weather.s_factor == pytest.approx(s, abs=5e-4)
    assert weather.phi1_deg == pytest.approx(phi1, abs=0.05)


def test_wind_levers_match_hand_evaluation(weather):
    lw1 = 504.0 * WINDAGE_A * WINDAGE_Z / (1000.0 * 9.81 * DELTA)
    assert weather.lw1_m == pytest.approx(lw1, rel=1e-9)
    assert weather.lw2_m == pytest.approx(1.5 * weather.lw1_m, rel=1e-12)


def test_steady_heel_is_tiny_for_the_capesize(weather):
    # an 183,000 t ship carries a millimetre wind lever: the steady
    # heel is a fraction of a degree and clears both limits easily
    assert 0.0 < weather.phi0_deg < 1.0
    assert weather.all_passed


def test_theta2_respects_the_50_degree_cap(weather):
    assert weather.theta2_deg <= 50.0 + 1e-9
    assert weather.area_b_mrad > weather.area_a_mrad


def test_area_integration_converges_under_refinement(jbc_hull):
    coarse = weather_criterion(
        jbc_hull, DELTA, KG, depth_m=25.0,
        windage_area_m2=WINDAGE_A, windage_lever_z_m=WINDAGE_Z,
        length_waterline_m=LWL, angle_step_deg=2.5,
    )
    fine = weather_criterion(
        jbc_hull, DELTA, KG, depth_m=25.0,
        windage_area_m2=WINDAGE_A, windage_lever_z_m=WINDAGE_Z,
        length_waterline_m=LWL, angle_step_deg=1.25,
    )
    assert coarse.area_a_mrad == pytest.approx(fine.area_a_mrad, rel=0.02)
    assert coarse.area_b_mrad == pytest.approx(fine.area_b_mrad, rel=0.01)


def test_bilge_keels_reduce_the_roll_angle(jbc_hull):
    bare = weather_criterion(
        jbc_hull, DELTA, KG, depth_m=25.0,
        windage_area_m2=WINDAGE_A, windage_lever_z_m=WINDAGE_Z,
        length_waterline_m=LWL,
    )
    keeled = weather_criterion(
        jbc_hull, DELTA, KG, depth_m=25.0,
        windage_area_m2=WINDAGE_A, windage_lever_z_m=WINDAGE_Z,
        length_waterline_m=LWL, bilge_keel_area_m2=200.0,
    )
    assert keeled.k_factor < 1.0
    assert keeled.phi1_deg < bare.phi1_deg


def test_flooding_angle_tightens_theta2(jbc_hull, weather):
    clipped = weather_criterion(
        jbc_hull, DELTA, KG, depth_m=25.0,
        windage_area_m2=WINDAGE_A, windage_lever_z_m=WINDAGE_Z,
        length_waterline_m=LWL, flooding_angle_deg=40.0,
    )
    assert clipped.theta2_deg <= 40.0 + 1e-9
    assert clipped.area_b_mrad < weather.area_b_mrad


# ---------------------------------------------------------------------------
# applicability guards (2.3.5) and input validation
# ---------------------------------------------------------------------------


def _box(lpp, beam, draft, depth, kg):
    return OffsetsTable(
        lpp=lpp, beam=beam,
        stations=[lpp * i / 10 for i in range(11)],
        waterlines=[draft * i / 12 for i in range(13)],
        half_breadths=[[beam / 2.0] * 13 for _ in range(11)],
    ), kg, depth


def test_rejects_ship_outside_b_over_d_band():
    # B/d = 60/15 = 4.0 is outside the 2.3.5 band
    table, kg, depth = _box(120.0, 60.0, 15.0, 20.0, 10.0)
    with pytest.raises(SpecValidationError) as err:
        weather_criterion(
            table, 1.025 * 120 * 60 * 15, kg, depth_m=depth,
            windage_area_m2=500.0, windage_lever_z_m=3.0,
        )
    assert "2.3.5" in str(err.value)


def test_rejects_ship_outside_kg_over_d_band(jbc_hull):
    # KG 25 m: KG/d - 1 = 0.515 > 0.5
    with pytest.raises(SpecValidationError) as err:
        weather_criterion(
            jbc_hull, DELTA, 25.0, depth_m=25.0,
            windage_area_m2=WINDAGE_A, windage_lever_z_m=WINDAGE_Z,
            length_waterline_m=LWL,
        )
    assert "2.3.5" in str(err.value)


def test_rejects_roll_period_of_20_seconds_and_over():
    # wide shallow box: positive GM inside the KG band but T >= 20 s
    table, kg, depth = _box(150.0, 100.0, 30.0, 35.0, 40.0)
    displacement = 1.025 * 150 * 100 * 30
    with pytest.raises(SpecValidationError) as err:
        weather_criterion(
            table, displacement, kg, depth_m=depth,
            windage_area_m2=2000.0, windage_lever_z_m=5.0,
            length_waterline_m=150.0,
        )
    assert "2.3.5" in str(err.value)


def test_rejects_wind_pressure_outside_the_code_band(jbc_hull):
    with pytest.raises(SpecValidationError):
        weather_criterion(
            jbc_hull, DELTA, KG, depth_m=25.0,
            windage_area_m2=WINDAGE_A, windage_lever_z_m=WINDAGE_Z,
            wind_pressure_pa=600.0,
        )


# ---------------------------------------------------------------------------
# serialization and CLI integration
# ---------------------------------------------------------------------------


def test_json_round_trip_and_determinism(weather, jbc_hull):
    payload = json.loads(json.dumps(weather.to_dict()))
    assert payload["lw2_m"] == pytest.approx(1.5 * payload["lw1_m"])
    assert payload["all_passed"] is True
    assert len(payload["criteria"]) == 3
    again = weather_criterion(
        jbc_hull, DELTA, KG, depth_m=25.0,
        windage_area_m2=WINDAGE_A, windage_lever_z_m=WINDAGE_Z,
        length_waterline_m=LWL,
    )
    assert again.to_dict() == weather.to_dict()


def test_cli_runs_weather_criterion():
    summary = run_taskbook(TASKBOOK)
    weather = summary["weather_criterion"]
    assert weather is not None
    assert weather["all_passed"] is True
    assert weather["windage_area_m2"] == pytest.approx(2380.0)


def test_cli_prints_weather_block(capsys):
    rc = main(["run", TASKBOOK])
    out = capsys.readouterr().out
    assert rc == 0
    assert "severe wind and rolling" in out
    assert "ALL PASS" in out
