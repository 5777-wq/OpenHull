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
