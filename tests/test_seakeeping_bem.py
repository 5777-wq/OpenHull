"""Stage-2 seakeeping (capytaine BEM RAOs) tests, plan task 3.8 stage 2.

The anchors are INDEPENDENT-PATH cross-checks of the same geometry,
not external references:

- mesh volume (panel integration) vs the task 1.4 displacement
  volume (station Simpson integration) — two integrators, one hull;
- long-wave heave RAO -> 1 (a ship follows very long waves);
- short-wave heave RAO -> 0 (little excitation at high frequency);
- roll excitation vanishes in head seas (hull symmetry);
- the roll RAO peak sits near the stage-1 regulation roll period
  lengthened by the Duell added-inertia share (x sqrt(1.25), the
  book's Jxx = 0.25 Ixx), grid-step tolerance declared.

Skipped cleanly when capytaine (the optional seakeeping extra) is
not installed.
"""

import json

import pytest

from openhull.hydrostatics import hydrostatics_table
from openhull.linesplan import parent_to_taskbook
from openhull.seakeeping import roll_period_regulation

capytaine = pytest.importorskip(
    "capytaine", reason="capytaine not installed (openhull[seakeeping])")

from openhull.seakeeping_bem import (  # noqa: E402
    build_hull_body,
    compute_rigid_rao,
)

PERIODS = (4.0, 5.0, 6.0, 8.0, 10.0, 20.0)


@pytest.fixture(scope="module")
def hull_and_hydro():
    hull, _ = parent_to_taskbook(lpp=100.0, beam=20.0, draft=6.0,
                                 target_cb=0.80)
    hydro = hydrostatics_table(hull, [5.7, 6.0]).at(6.0)
    return hull, hydro


@pytest.fixture(scope="module")
def volume_check(hull_and_hydro):
    hull, hydro = hull_and_hydro
    _body, info = build_hull_body(hull, 6.0, deck_z=6.0)
    return info["mesh_volume_m3"] / hydro.displacement_volume


@pytest.fixture(scope="module")
def rao(hull_and_hydro):
    hull, hydro = hull_and_hydro
    return compute_rigid_rao(
        hull, 6.0,
        displacement_t=hydro.displacement,
        kg_m=3.0, km_m=hydro.km, bml_m=hydro.bml,
        waterplane_area_m2=hydro.aw,
        periods_s=PERIODS)


def test_mesh_volume_matches_table_integration(volume_check):
    # panel integration vs station Simpson on the SAME hull: the two
    # independent volume integrators must agree to tight tolerance
    assert volume_check == pytest.approx(1.0, abs=0.015)


def test_long_wave_heave_rao_tends_to_one(rao):
    for seas in ("head", "beam"):
        point = next(p for p in rao.points
                     if p.seas == seas and p.period_s == 20.0
                     and p.motion == "heave")
        assert point.rao_abs == pytest.approx(1.0, abs=0.15)


def test_short_wave_heave_rao_tends_to_zero(rao):
    point = next(p for p in rao.points
                 if p.seas == "head" and p.period_s == 4.0
                 and p.motion == "heave")
    # T = 4 s -> lambda = 25 m on a 100 m hull: heavy cancellation
    assert point.rao_abs < 0.2


def test_head_sea_roll_excitation_vanishes(rao):
    # hull symmetry: head seas produce (near) no roll excitation
    head = [p.rao_abs for p in rao.points
            if p.seas == "head" and p.motion == "roll"]
    beam = [p.rao_abs for p in rao.points
            if p.seas == "beam" and p.motion == "roll"]
    assert max(head) <= 0.05 * max(beam)


def test_roll_peak_near_stage1_period_with_added_inertia(rao, hull_and_hydro):
    # stage-1 regulation period (GM uncorrected = KM - KG) lengthened
    # by the book's Jxx = 0.25*Ixx -> factor sqrt(1.25); the period
    # grid is coarse, so the tolerance is one grid step
    _hull, hydro = hull_and_hydro
    kg = 3.0
    t_stage1 = roll_period_regulation(20.0, kg, hydro.km - kg)
    t_expected = t_stage1 * (1.25 ** 0.5)
    beam_rolls = [(p.period_s, p.rao_abs) for p in rao.points
                  if p.seas == "beam" and p.motion == "roll"]
    t_peak = max(beam_rolls, key=lambda x: x[1])[0]
    assert abs(t_peak - t_expected) <= 1.5


def test_result_is_json_serializable(rao):
    payload = json.dumps(rao.to_dict())
    assert '"mesh_info"' in payload
    assert len(rao.points) == 2 * len(PERIODS) * 3
    assert "capytaine" in rao.notes[0]
