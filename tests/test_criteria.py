"""Intact stability criteria tests: IMO 2008 IS Code Part A 2.2 (task 3.5).

Acceptance layers (AGENTS.md sections 3/4; criteria text verified
verbatim against a public reproduction of the code, imorules.com,
2026-09-21 — cross-checked with Xie Yunping's domestic GM >= 0.15 m
and the Ship Theory vol. 1 table 4-5 requirements column):

* TB-001 full load: every 2.2 criterion must PASS with the actual
  numbers pinned as regression anchors;
* verdict agreement with the published JBC analysis of Hussain & Amin
  (2021) JMSA 20(3), Table 7 — demonstration band on the areas (their
  model is the real JBC lines; ours is the declared Series 60 +
  Lackenby approximation, see VALIDATION.md task 3.4), exact agreement
  on the PASS verdicts;
* the sec. 5-4 free-surface arm on a rectangular tank reproduces the
  wall-sided box closed form delta_l = w1*V*tan(phi)*b^2/(12*h)/Delta
  exactly; a flooded tank reduces GM0, arms and areas;
* down-flooding: a flooding angle clips the area ceilings per 2.2.1
  and, before 30 deg, removes the 2.2.1(c) interval.
"""

import json
import math

import pytest

from openhull.cli import main, run_taskbook
from openhull.hydrostatics import hydrostatics_at
from openhull.linesplan import parent_to_taskbook
from openhull.spec import SpecValidationError
from openhull.stability import (
    Tank,
    free_surface_arm,
    free_surface_correction,
    intact_stability_criteria,
)

TASKBOOK = "examples/taskbook_bulk_carrier.yaml"

# Hussain & Amin (2021) JMSA 20(3) Table 7, "before sail installation"
# full load: areas 44.715 / 75.573 / 31.794 m*deg (degrees! converted
# with pi/180) — published for the REAL JBC lines
PAPER_AREAS_MRAD = (
    44.715 * math.pi / 180.0,
    75.573 * math.pi / 180.0,
    31.794 * math.pi / 180.0,
)


@pytest.fixture(scope="module")
def jbc_hull():
    table, _report = parent_to_taskbook(
        lpp=280.0, beam=45.0, draft=16.5,
        target_cb=0.8580, target_lcb_pct=2.5475,
    )
    return table


@pytest.fixture(scope="module")
def jbc_criteria(jbc_hull):
    return intact_stability_criteria(jbc_hull, 182_829.1, 13.29, depth_m=25.0)


# ---------------------------------------------------------------------------
# TB-001 full load: all criteria pass, numbers pinned
# ---------------------------------------------------------------------------


def test_tb001_all_criteria_pass(jbc_criteria):
    assert jbc_criteria.all_passed
    assert [c.passed for c in jbc_criteria.criteria] == [True] * len(
        jbc_criteria.criteria
    )
    assert len(jbc_criteria.criteria) == 6


def test_tb001_area_anchors(jbc_criteria):
    # regression pins of the chain curve (demonstration-grade model:
    # the band keeps the pin honest without pretending published precision)
    area_a, area_b, area_c = (
        jbc_criteria.criteria[0].actual,
        jbc_criteria.criteria[1].actual,
        jbc_criteria.criteria[2].actual,
    )
    assert area_a == pytest.approx(0.748, abs=0.05)
    assert area_b == pytest.approx(1.181, abs=0.08)
    assert area_c == pytest.approx(0.433, abs=0.06)
    assert area_b == pytest.approx(area_a + area_c, abs=1e-9)


def test_tb001_lever_angle_gm0_anchors(jbc_criteria):
    lever = jbc_criteria.criteria[3].actual
    angle_max = jbc_criteria.criteria[4].actual
    assert lever == pytest.approx(2.554, abs=0.06)
    assert angle_max == pytest.approx(31.0, abs=2.0)
    assert jbc_criteria.gm0_m == pytest.approx(5.306, abs=0.03)
    assert jbc_criteria.free_surface_correction_m == 0.0


def test_verdicts_agree_with_published_jbc(jbc_criteria):
    # identical verdicts: the paper's full-load JBC also clears every
    # 2.2 requirement; the area magnitudes agree to demonstration grade
    for criterion, paper_area in zip(
        jbc_criteria.criteria[:3], PAPER_AREAS_MRAD
    ):
        assert criterion.passed
        assert 0.5 * paper_area <= criterion.actual <= 1.3 * paper_area


# ---------------------------------------------------------------------------
# free-surface arm (Ship Theory vol. 1, sec. 5-4)
# ---------------------------------------------------------------------------


def test_rectangular_tank_free_surface_closed_form():
    tank = Tank.rectangular("test_tank", 20.0, 12.0, 1.0, height=8.0)
    displacement = 50_000.0
    liquid_depth = 4.0  # 50 % of the tank height
    for angle in (5.0, 10.0, 20.0, 30.0):
        got = free_surface_arm((tank,), displacement, angle)
        closed = (
            1.0
            * (20.0 * 12.0 * liquid_depth)
            * (
                math.tan(math.radians(angle))
                * 12.0**2
                / (12.0 * liquid_depth)
            )
            / displacement
        )
        assert got == pytest.approx(closed, abs=1e-12)


def test_tank_reduces_gm0_arms_and_areas(jbc_hull):
    tanks = (
        Tank.rectangular("dbt", 40.0, 30.0, 1.025, height=3.0),
    )
    clean = intact_stability_criteria(jbc_hull, 182_829.1, 13.29, depth_m=25.0)
    flooded = intact_stability_criteria(
        jbc_hull, 182_829.1, 13.29, depth_m=25.0, tanks=tanks
    )
    # GM0: km - kg - sum(w1*i_x)/Delta with the Eq. (4-38) machinery
    expected_fsc = free_surface_correction(tanks, 182_829.1)
    assert flooded.free_surface_correction_m == pytest.approx(expected_fsc)
    assert flooded.gm0_m == pytest.approx(clean.gm0_m - expected_fsc)
    # every area shrinks when the liquid shifts
    for clean_c, flooded_c in zip(
        clean.criteria[:3], flooded.criteria[:3]
    ):
        assert flooded_c.actual < clean_c.actual
        assert flooded_c.passed  # the correction is far from critical here


def test_tank_without_prism_raises():
    from openhull.stability import Tank as _Tank

    bare = _Tank(name="bare", i_x=1.0, liquid_density=1.0)
    with pytest.raises(SpecValidationError) as err:
        free_surface_arm((bare,), 50_000.0, 10.0)
    assert "rectangular" in str(err.value)


# ---------------------------------------------------------------------------
# down-flooding angle handling
# ---------------------------------------------------------------------------


def test_flooding_angle_clips_area_ceilings(jbc_hull):
    full = intact_stability_criteria(jbc_hull, 182_829.1, 13.29, depth_m=25.0)
    clipped = intact_stability_criteria(
        jbc_hull, 182_829.1, 13.29, depth_m=25.0, flooding_angle_deg=35.0
    )
    assert clipped.criteria[1].description.endswith("(40 deg or "
                                                    "down-flooding angle)")
    assert clipped.criteria[1].actual < full.criteria[1].actual
    assert clipped.criteria[2].actual < full.criteria[2].actual
    # 35 deg > 30 deg: the (c) interval is kept, shortened to 30..35
    assert "30 to 35.0 deg" in clipped.criteria[2].description


def test_flooding_before_30_drops_interval_c(jbc_hull):
    early = intact_stability_criteria(
        jbc_hull, 182_829.1, 13.29, depth_m=25.0, flooding_angle_deg=28.0
    )
    ids = [c.criterion_id for c in early.criteria]
    assert "IS Code 2.2.1(c)" not in ids
    assert len(early.criteria) == 5
    assert any("precedes 30 deg" in note for note in early.notes)
    # area (b) is now judged up to the flooding angle
    assert "to 28.0 deg" in early.criteria[1].description
    # criterion 2.2.2 judges the lever up to the flooding angle
    by_id = {c.criterion_id: c for c in early.criteria}
    assert "down-flooding" in by_id["IS Code 2.2.2"].description


def test_flooding_angle_out_of_range_raises(jbc_hull):
    with pytest.raises(SpecValidationError) as err:
        intact_stability_criteria(
            jbc_hull, 182_829.1, 13.29, depth_m=25.0, flooding_angle_deg=95.0
        )
    assert "80" in str(err.value)


# ---------------------------------------------------------------------------
# serialization and CLI integration
# ---------------------------------------------------------------------------


def test_criteria_json_round_trip(jbc_criteria):
    payload = json.loads(json.dumps(jbc_criteria.to_dict()))
    assert payload["rule"].startswith("IMO 2008 IS Code")
    assert payload["kg_m"] == pytest.approx(13.29)
    assert payload["all_passed"] is True
    assert len(payload["criteria"]) == 6
    first = payload["criteria"][0]
    for key in (
        "criterion_id", "description", "required", "unit",
        "actual", "passed",
    ):
        assert key in first
    assert payload["flooding_angle_deg"] is None
    assert len(payload["area_angles_deg"]) == 17
    assert payload["area_angles_deg"][0] == 0.0


def test_cli_includes_criteria_block():
    summary = run_taskbook(TASKBOOK)
    criteria = summary["stability_criteria"]
    assert criteria is not None
    assert criteria["all_passed"] is True
    assert len(criteria["criteria"]) == 6


def test_cli_prints_criteria_table(capsys):
    rc = main(["run", TASKBOOK])
    out = capsys.readouterr().out
    assert rc == 0
    assert "intact stability criteria" in out
    assert "IS Code 2.2.4" in out
    assert "ALL PASS" in out
