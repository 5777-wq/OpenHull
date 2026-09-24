"""Regression tests for the 2026-09-24 external review batch.

Every test here pins one defect from the review report (P0/P1/P2) so
the failure mode cannot come back silently:

- P0-1 propeller chain on the in-band path (old attribute names,
  power-led iteration) — the in-band task book must produce NUMBERS;
- P0-2 one design draft for the whole chain + declared mismatch is
  reported, never a crash and never two conflicting values;
- P0-3/P1-6 report renders staged refusals / not-requested states;
- P1-4/P1-5 optimize writes every artefact it lists and exports the
  rejected points (zero-feasible run included);
- the floating-point draft row at the deepest waterline.
"""

import json
from pathlib import Path

import pytest

from openhull.cli import main, run_taskbook
from openhull.report import write_report_md

# 45,000 t / 16 kn / Cb 0.80: L/Delta^(1/3) ~ 4.95 and V/sqrt(L)
# ~ 0.64, i.e. INSIDE both the Ayre speed band and the digitised C0
# family band — the probe that the review report could never reach.
IN_BAND_TASKBOOK = """\
schema_version: 1
taskbook_id: REVIEW-INBAND
ship_type: bulk_carrier
requirements:
  deadweight_t: 45000
  service_speed_kn: 16.0
  kg_m: 9.5
  drafts:
    design_draft_m: 11.6
constraints:
  block_coefficient_design: 0.80
propeller:
  blades_z: 4
  expanded_area_ratio: 0.50
  rpm: 100
  shaft_immersion_m: 6.0
  shaft_efficiency: 0.98
  relative_rotative_eff: 0.99
"""

# declared draft far from the balance draft: must NOT crash and must
# be reported as a mismatch
MISMATCH_TASKBOOK = """\
schema_version: 1
taskbook_id: REVIEW-DRAFT
ship_type: bulk_carrier
requirements:
  deadweight_t: 45000
  service_speed_kn: 16.0
  kg_m: 9.5
  drafts:
    design_draft_m: 12.5
constraints:
  block_coefficient_design: 0.80
"""


@pytest.fixture(scope="module")
def in_band_taskbook(tmp_path_factory):
    path = tmp_path_factory.mktemp("review") / "in_band.yaml"
    path.write_text(IN_BAND_TASKBOOK, encoding="utf-8")
    return str(path)


@pytest.fixture(scope="module")
def in_band_summary(in_band_taskbook):
    return run_taskbook(in_band_taskbook)


def test_propeller_in_band_path_returns_numbers(in_band_summary):
    # P0-1: the old code crashed here with AttributeError
    prop = in_band_summary["propeller_design"]
    assert prop is not None and not prop.get("skipped"), prop
    for key in ("diameter_m", "pitch_ratio", "eta_open_water",
                "advance_coefficient", "wake_fraction",
                "thrust_deduction", "thrust_n", "delivered_power_kw",
                "shaft_power_kw"):
        assert prop[key] is not None and prop[key] > 0
    assert 0.40 <= prop["eta_open_water"] <= 0.85
    # the cavitation check either runs or declares why it is skipped
    assert prop.get("cavitation") is not None or prop.get(
        "cavitation_note")


def test_one_design_draft_everywhere(in_band_summary):
    # P0-2: the top hydrostatic row equals the balance draft
    design = in_band_summary["hydrostatics"][-1]
    assert design["draft_m"] == pytest.approx(
        in_band_summary["draft_m"], abs=0.01)


def test_declared_draft_mismatch_is_reported_not_fatal(tmp_path):
    # P0-2: declared 12.5 m vs balance ~11.64 m -> run completes and
    # the mismatch is declared with its size
    path = tmp_path / "mismatch.yaml"
    path.write_text(MISMATCH_TASKBOOK, encoding="utf-8")
    summary = run_taskbook(str(path))
    assert summary["draft_declared_m"] == pytest.approx(12.5)
    assert summary["draft_mismatch_m"] == pytest.approx(
        12.5 - summary["draft_m"], abs=0.01)
    assert summary["draft_mismatch_m"] > 0.05


def test_report_renders_staged_refusal_and_not_requested(
        in_band_summary, tmp_path):
    # P0-3: a staged refusal renders as a structured Chinese block
    summary = dict(in_band_summary)
    summary["propeller_design"] = {
        "skipped": True, "stage": "ayre",
        "reason": "Invalid value for 'length_ratio': 4.87 "
                  "allowed: L/Delta^(1/3) within 4.88-6.41"}
    out = write_report_md(summary, tmp_path / "refused.md")
    text = out.read_text(encoding="utf-8")
    assert "未能给出所需航速对应的功率" in text
    assert "艾亚阻力估算" in text
    assert "L/Δ^(1/3) = 4." in text        # the effective ratio shown
    # P1-6: "not requested" is a different state from "refused"
    summary["propeller_design"] = None
    out2 = write_report_md(summary, tmp_path / "noprop.md")
    text2 = out2.read_text(encoding="utf-8")
    assert "**未请求**" in text2
    assert "未能给出所需航速对应的功率" not in text2


def test_optimize_zero_feasible_writes_every_listed_artefact(
        in_band_taskbook, tmp_path, capsys):
    # P1-4/P1-5: every path in `outputs` exists on disk, the rejected
    # points are exported, and the chart is the refusal scatter
    out_dir = tmp_path / "scan"
    rc = main(["optimize", in_band_taskbook,
               "--grid-lob", "5.2:5.6:2", "--grid-bt", "2.5:2.8:2",
               "--grid-cb", "0.80:0.82:2", "--out", str(out_dir)])
    assert rc == 0
    capsys.readouterr()
    summary = json.loads(
        (out_dir / "scan_summary.json").read_text(encoding="utf-8"))
    for key, path in summary["outputs"].items():
        assert Path(path).exists(), (key, path)
    assert (out_dir / "feasible_designs.csv").exists()
    n_rejected = summary["rejected"]
    assert len(summary["rejected_points"]) == n_rejected
    if summary["feasible"] == 0:
        assert summary["reference_power_kw"] is None
        # the zero-feasible chart is still a real file
        assert (out_dir / "tradeoff_speed_displacement_gm.png").stat(
        ).st_size > 10_000


def test_draft_row_never_exceeds_the_waterline_grid():
    # the floating-point guard: round(T*1.0, 4) must not overshoot the
    # deepest tabulated waterline (found on the review probe)
    from openhull.linesplan import parent_to_taskbook

    hull, _ = parent_to_taskbook(lpp=188.0, beam=31.0, draft=11.64055,
                                 target_cb=0.80)
    top = float(hull.waterlines[-1])
    design_draft = 11.6406          # rounds ABOVE the waterline
    drafts = [min(round(design_draft * f, 4), top)
              for f in (0.25, 0.5, 0.75)] + [top]
    assert drafts[-1] <= top
    assert drafts == sorted(drafts)


# ---- v1.0.1 re-verification batch (2026-09-24, second round) ---------


def test_report_in_band_propeller_fields_render(tmp_path, in_band_summary):
    # N1: the in-band report rendered "叶数 Z = —" and "ηo = —" because
    # the report asked for keys the summary never carried
    out = write_report_md(in_band_summary, tmp_path / "r.md")
    text = out.read_text(encoding="utf-8")
    assert "叶数 Z = 4" in text
    assert "= —" not in text.split("## 6")[0]  # section 5 has no dashes
    assert "敞水效率 ηo = 0.5" in text


def test_optimize_grid_endpoints_pass_their_own_guards():
    # N3: B/T = 3.5 generated as 3.5000000000000004 and refused by the
    # 2.0..3.5 sanity band, silently deleting a whole grid line
    from openhull.optimize import SweepGrid

    grid = SweepGrid(l_over_b=(5.2, 7.0, 8), b_over_t=(2.5, 3.5, 6),
                     cb=(0.81, 0.87, 4))
    for lob, bot, cb in grid.values():
        assert 2.0 <= bot <= 3.5
        assert 4.0 <= lob <= 8.0
        assert 0.5 <= cb <= 0.9
    assert 3.5 in {bot for _, bot, _ in grid.values()}


def test_optimize_draft_rows_never_overshoot(tmp_path):
    # N2: the scan built [0.9*T, T] raw and fp overshoot refused six
    # grid points on the re-verification probe
    from openhull.hydrostatics import hydrostatic_draft_rows
    from openhull.linesplan import parent_to_taskbook

    hull, _ = parent_to_taskbook(lpp=205.0, beam=34.0, draft=13.11938,
                                 target_cb=0.85)
    rows = hydrostatic_draft_rows(hull, 13.119377780407651, (0.9, 1.0))
    assert rows == sorted(rows)
    assert rows[-1] <= float(hull.waterlines[-1])


def test_json_stdout_stays_pure_with_artifact_flags(tmp_path, capsys,
                                                    in_band_taskbook):
    # N4: confirmation lines after the JSON body made stdout unparseable
    report = tmp_path / "r.md"
    chart = tmp_path / "c.png"
    rc = main(["run", in_band_taskbook, "--json",
               "--report", str(report), "--hydro-curve-chart", str(chart)])
    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)      # raises if polluted
    assert payload["taskbook_id"] == "REVIEW-INBAND"
    assert "design report ->" in captured.err
    assert report.exists() and chart.exists()


def test_scan_summary_exports_refusal_field_breakdown(tmp_path, capsys):
    # section-3: the stage histogram hides WHY; the field breakdown
    # keeps data gaps from being read as design verdicts
    taskbook = tmp_path / "refuse.yaml"
    taskbook.write_text(MISMATCH_TASKBOOK.replace(
        "REVIEW-DRAFT", "REVIEW-FIELDS").replace(
        "design_draft_m: 12.5", "design_draft_m: 11.6").replace(
        "service_speed_kn: 16.0", "service_speed_kn: 20.0"), encoding="utf-8")
    out_dir = tmp_path / "scan2"
    rc = main(["optimize", str(taskbook),
               "--grid-lob", "5.2:5.6:2", "--grid-bt", "3.0:3.2:2",
               "--grid-cb", "0.80:0.82:2", "--out", str(out_dir)])
    assert rc == 0
    capsys.readouterr()
    summary = json.loads(
        (out_dir / "scan_summary.json").read_text(encoding="utf-8"))
    assert "refusal_fields" in summary
    assert sum(summary["refusal_fields"].values()) == summary["rejected"]
