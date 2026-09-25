"""Product-review round 6 (2026-09-25): P0-1/P0-2/P0-3 + quick wins.

Every test pins one finding from the external product review performed
as a real user walking the full design chain (100,000 t / 20 kn):

- P0-1  the digitised C0 family's peak zone flattens or inflates the
        V^3 power growth; the tool must SAY so (display-only
        diagnostics: peak-zone flag, local slope, Admiralty corridor);
- P0-2  an out-of-band cavitation sigma is UNCHECKED, not "skipped" —
        the report must say 未校核（非通过）, name the side, keep the
        full provenance note untruncated, and give direction hints;
- P0-3  stdout is the agent-facing contract: the quickness section must
        appear in ALL states (result / refused / not requested);
- P1-1a the report must not claim "no speed-loss formula exists" while
        Kwon sits implemented and tested in the library;
- P1-2  the refusal block points to `openhull optimize` for the
        feasibility sweep instead of leaving the user blind.
"""

import json

import pytest

from openhull.cli import main, run_taskbook
from openhull.report import write_report_md
from openhull.resistance import admiralty_corridor, ayre_effective_power

# the reviewer's design point: 100,000 t / 20 kn / Cb 0.76
REVIEW_TASKBOOK = """\
schema_version: 1
taskbook_id: REVIEW-P0
ship_type: bulk_carrier
requirements:
  deadweight_t: 100000
  service_speed_kn: 20.0
  kg_m: 11.0
  drafts:
    design_draft_m: 15.42
constraints:
  block_coefficient_design: 0.76
propeller:
  blades_z: 4
  expanded_area_ratio: 0.55
  rpm: 105
  shaft_immersion_m: 7.7
  shaft_efficiency: 0.98
  relative_rotative_eff: 0.982
"""


@pytest.fixture(scope="module")
def review_summary(tmp_path_factory):
    path = tmp_path_factory.mktemp("p0") / "review.yaml"
    path.write_text(REVIEW_TASKBOOK, encoding="utf-8")
    return run_taskbook(str(path))


# ---------------------------------------------------------------------------
# P0-1: the C0 peak-zone diagnostics
# ---------------------------------------------------------------------------


def test_c0_peak_zone_diagnostics_fire_at_the_reviewers_point():
    """V/sqrt(L) 0.699 sits on the digitised family's own peak (0.70):
    the diagnostic must flag it and measure the local slope."""
    res = ayre_effective_power(
        displacement_t=124909.3, speed_kn=20.0, lpp_m=249.74, beam_m=41.62,
        draft_m=15.42, cb=0.76, xc_pct_fwd=2.5, screw="single")
    assert res.in_c0_peak_zone is True
    assert res.c0_family_peak_v_sqrt_l == pytest.approx(0.70)
    assert res.c0_local_slope_pct_per_0p05 == pytest.approx(-4.8, abs=1.0)


def test_low_speed_run_does_not_flag_the_peak_zone():
    """The method's normal regime (steep rise below the peak) is not
    the peak zone: a 16 kn in-band bulk carrier must stay unflagged."""
    res = ayre_effective_power(
        displacement_t=45_000 / 0.82, speed_kn=16.0, lpp_m=188.58,
        beam_m=31.43, draft_m=11.64, cb=0.80, xc_pct_fwd=2.5,
        screw="single")
    assert res.in_c0_peak_zone is False


def test_admiralty_corridor_is_display_only_and_band_clamped():
    corr = admiralty_corridor(
        displacement_t=124909.3, speed_kn=20.0, lpp_m=249.74, beam_m=41.62,
        draft_m=15.42, cb=0.76, xc_pct_fwd=2.5)
    # 19/20/21 kn all inside the Ayre band for this hull
    assert set(corr) == {19.0, 20.0, 21.0}
    assert all(v > 0 for v in corr.values())


def test_summary_carries_the_sensitivity_and_report_declares_it(
        review_summary, tmp_path):
    prop = review_summary["propeller_design"]
    assert prop is not None and not prop.get("skipped")
    sens = prop["resistance_sensitivity"]
    assert sens["in_c0_peak_zone"] is True
    assert sens["admiralty_corridor"]
    text = write_report_md(
        review_summary, tmp_path / "p01.md").read_text(encoding="utf-8")
    assert "方法敏感性" in text
    assert "不宜直接用于主机选型" in text
    assert "诊断只加文字" in text  # the numbers are untouched


# ---------------------------------------------------------------------------
# P0-2: the cavitation UNCHECKED wording
# ---------------------------------------------------------------------------


def test_cavitation_unchecked_reads_as_unchecked(review_summary, tmp_path):
    """The reviewer's ship: sigma 0.326 below the verified band — the
    report must say 未校核（非通过）, name the low side, give the
    direction hints, and keep the provenance note untruncated."""
    prop = review_summary["propeller_design"]
    unchecked = prop.get("cavitation_unchecked")
    assert unchecked is not None
    assert unchecked["side"] == "low"
    # below the verified band: the mechanism, not the reviewer's exact
    # number (our rebuilt taskbook differs in rpm/immersion details)
    assert unchecked["sigma_0_7r"] < unchecked["band"][0]
    text = write_report_md(
        review_summary, tmp_path / "p02.md").read_text(encoding="utf-8")
    assert "未校核（非通过）" in text
    assert "空泡状态**未知**" in text
    assert "低侧" in text and "空泡风险更高" in text
    assert "降低转速" in text and "加大盘面比" in text and "增大轴系浸深" in text
    # P2-5: the provenance note is NOT truncated mid-sentence
    note = prop["cavitation_note"]
    assert " ".join(note.split()) in text.replace("工具原文（保留可溯源，不截断）：", "")


# ---------------------------------------------------------------------------
# P0-3: the stdout contract
# ---------------------------------------------------------------------------


def test_stdout_carries_the_quickness_section_on_success(tmp_path, capsys):
    path = tmp_path / "ok.yaml"
    path.write_text(REVIEW_TASKBOOK, encoding="utf-8")
    assert main(["run", str(path)]) == 0
    out = capsys.readouterr().out
    assert "speed & propeller (task 3.3):" in out
    assert "power             : PD" in out
    assert "UNCHECKED" in out and "low side" in out
    assert "C0 PEAK ZONE" in out


def test_stdout_carries_the_quickness_section_on_refusal(tmp_path, capsys):
    taskbook = REVIEW_TASKBOOK.replace(
        "block_coefficient_design: 0.76", "block_coefficient_design: 0.84")
    path = tmp_path / "refused.yaml"
    path.write_text(taskbook, encoding="utf-8")
    assert main(["run", str(path)]) == 0  # refusal, not crash
    out = capsys.readouterr().out
    assert "propeller         : REFUSED at ayre" in out
    assert "see --report" in out


def test_stdout_carries_the_quickness_section_when_not_requested(
        tmp_path, capsys):
    taskbook = "\n".join(
        line for line in REVIEW_TASKBOOK.splitlines()
        if not line.startswith(("propeller:", "  blades_z", "  rpm",
                                "  expanded_area_ratio",
                                "  shaft_immersion_m", "  shaft_efficiency",
                                "  relative_rotative_eff")))
    path = tmp_path / "noprop.yaml"
    path.write_text(taskbook, encoding="utf-8")
    assert main(["run", str(path)]) == 0
    out = capsys.readouterr().out
    assert "not requested" in out


# ---------------------------------------------------------------------------
# P1-1a / P1-2: the wording contracts
# ---------------------------------------------------------------------------


def test_report_does_not_claim_kwon_is_missing(review_summary, tmp_path):
    text = write_report_md(
        review_summary, tmp_path / "kwon.md").read_text(encoding="utf-8")
    assert "白名单书内无失速估算公式" not in text
    assert "已在库层实现并通过测试" in text
    assert "静水" in text  # the powers in this report are calm-water


def test_refusal_block_points_to_optimize(tmp_path):
    # a refusing run: Cb 0.84 is refused at the ayre stage
    taskbook = REVIEW_TASKBOOK.replace(
        "block_coefficient_design: 0.76", "block_coefficient_design: 0.84")
    path = tmp_path / "ref.yaml"
    path.write_text(taskbook, encoding="utf-8")
    summary = run_taskbook(str(path))
    summary["propeller_design"] = {
        "skipped": True, "stage": "ayre",
        "reason": summary["propeller_design"]["reason"]}
    text = write_report_md(
        summary, tmp_path / "ref.md").read_text(encoding="utf-8")
    assert "openhull optimize" in text
    assert "--grid-cb" in text


def test_summary_stays_json_serialisable_with_the_new_fields(
        review_summary):
    payload = json.dumps(review_summary, ensure_ascii=False)
    restored = json.loads(payload)
    prop = restored["propeller_design"]
    assert prop["resistance_sensitivity"]["in_c0_peak_zone"] is True
    assert prop["cavitation_unchecked"]["side"] == "low"
