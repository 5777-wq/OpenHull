"""Backlog batch v1.3.0 — the review's P1 list, done.

Pins one behaviour per deferred item that this batch implements:

- P1-3   `openhull check`: seconds-level preflight of the main
         dimensions and guard bands, exit 0/1, machine-readable JSON;
- P1-5   `weather_criterion: default`: the [ASSUMED] geometric
         derivation (Lpp x freeboard etc.), in `run` AND `optimize`;
- P1-1b  the Kwon speed loss wired into `run` behind
         `seakeeping.speed_loss` (skips honestly outside the domain);
- P1-2   the ayre refusal block carries the nearest feasible Cb (or the
         reachable speed window) under a declared one-shot rule;
- P2-1   `--json PATH` / `--csv PATH` write files, can be combined, and
         the bare flags keep the historical stdout behaviour;
- P2-2   `--csv-step` (default 0.1 -> 10 rows, chart-aligned);
- P2-3   the two roll periods carry a calibre footnote;
- P2-4   `seakeeping.wave_periods` replaces the reference seas.
"""

import json
import subprocess
import sys

import pytest

from openhull.cli import main, run_taskbook
from openhull.report import write_report_md

BASE = """\
schema_version: 1
taskbook_id: {tag}
ship_type: bulk_carrier
requirements:
  deadweight_t: 100000
  service_speed_kn: 20.0
  kg_m: 11.0
  drafts:
    design_draft_m: 15.42
constraints:
  block_coefficient_design: {cb}
{extra}\
propeller:
  blades_z: 4
  expanded_area_ratio: 0.55
  rpm: 105
  shaft_immersion_m: 7.7
  shaft_efficiency: 0.98
  relative_rotative_eff: 0.982
"""

SEAKEEPING_BLOCK = """\
seakeeping:
  wave_periods: [5.0, 7.0]
  speed_loss:
    beaufort: 6
    direction: head
"""


def _taskbook(tmp_path, tag, cb="0.76", extra="", speed="20.0",
              draft="15.42"):
    path = tmp_path / f"{tag}.yaml"
    path.write_text(
        BASE.format(tag=tag, cb=cb, extra=extra).replace(
            "service_speed_kn: 20.0", f"service_speed_kn: {speed}").replace(
            "design_draft_m: 15.42", f"design_draft_m: {draft}"),
        encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# P1-3: the preflight
# ---------------------------------------------------------------------------


def test_check_all_pass_exits_zero(tmp_path, capsys):
    path = _taskbook(tmp_path, "CHECK-OK", cb="0.76")
    assert main(["check", path]) == 0
    out = capsys.readouterr().out
    assert "all gates predicted PASS" in out
    assert "Froude number" in out and "C0 family band" in out


def test_check_predicts_the_c0_refusal_with_exit_one(tmp_path, capsys):
    # the reviewer's Cb 0.84 case: the C0 gate refuses with the same
    # number their sweep measured
    path = _taskbook(tmp_path, "CHECK-REFUSE", cb="0.84")
    assert main(["check", path]) == 1
    out = capsys.readouterr().out
    assert "REFUSED (predicted)" in out
    assert "4.83" in out  # their sweep measured 4.832


def test_check_soft_draft_mismatch_warns_but_does_not_fail(tmp_path, capsys):
    path = _taskbook(tmp_path, "CHECK-WARN", cb="0.76", draft="14.0")
    assert main(["check", path]) == 0        # reported, not fatal
    out = capsys.readouterr().out
    assert "WARN (reported in run, not fatal)" in out


def test_check_json_is_machine_readable(tmp_path, capsys):
    path = _taskbook(tmp_path, "CHECK-JSON", cb="0.84")
    assert main(["check", path, "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["predicted_refusals"] >= 1
    assert any(not g["pass"] for g in payload["gates"])
    # and the process-boundary contract: the file form parses too
    out_path = tmp_path / "check.json"
    assert main(["check", path, "--json", str(out_path)]) == 1
    restored = json.loads(out_path.read_text(encoding="utf-8"))
    assert restored["predicted_refusals"] == payload["predicted_refusals"]


def test_check_hard_draft_reports_the_solved_ratio(tmp_path, capsys):
    taskbook = BASE.format(tag="CHECK-HARD", cb="0.76", extra="").replace(
        "    design_draft_m: 15.42",
        "    design_draft_m: 15.42\n    draft_is_hard: true")
    path = tmp_path / "hard.yaml"
    path.write_text(taskbook, encoding="utf-8")
    assert main(["check", str(path)]) == 0
    out = capsys.readouterr().out
    assert "hard draft 15.420 m -> B/T solved" in out


# ---------------------------------------------------------------------------
# P1-5: the assumed weather default
# ---------------------------------------------------------------------------


def test_weather_default_runs_the_criterion(tmp_path):
    taskbook = BASE.format(
        tag="WX-DEFAULT", cb="0.76", extra="").replace(
        "propeller:",
        "  weather_criterion: default\npropeller:")
    # the weather block lives under constraints.stability
    taskbook = taskbook.replace(
        "constraints:\n  block_coefficient_design: 0.76",
        "constraints:\n  block_coefficient_design: 0.76\n"
        "  stability:\n    weather_criterion: default")
    path = tmp_path / "wx.yaml"
    path.write_text(taskbook, encoding="utf-8")
    summary = run_taskbook(str(path))
    weather = summary["weather_criterion"]
    assert weather["assumed_inputs"]["windage_area_m2"] > 0
    text = write_report_md(
        summary, tmp_path / "wx.md").read_text(encoding="utf-8")
    assert "[ASSUMED] 默认推导" in text
    assert "偏不保守方向" in text


# ---------------------------------------------------------------------------
# P1-1b: the Kwon speed loss
# ---------------------------------------------------------------------------


def test_kwon_wired_into_run(tmp_path):
    # Cb 0.76 at 18 kn is INSIDE the Kwon domain (the method refuses the
    # fat/fast combinations - Cb 0.80 at Fr 0.19 is already out; that is
    # its own page-verified applicability, not a defect)
    path = _taskbook(tmp_path, "KWON", cb="0.76",
                     extra=SEAKEEPING_BLOCK, speed="18.0")
    summary = run_taskbook(str(path))
    loss = summary["seakeeping"]["speed_loss"]
    assert loss["delta_v_percent"] == pytest.approx(1.71, abs=0.05)
    assert 0 < loss["speed_ratio_v2_v1"] < 1
    assert loss["speed_loss_kn"] > 0
    text = write_report_md(
        summary, tmp_path / "kwon.md").read_text(encoding="utf-8")
    assert "ΔV/V₁" in text and "Kwon" in text


def test_kwon_absent_declares_calm_water(tmp_path):
    path = _taskbook(tmp_path, "KWON-OFF")
    summary = run_taskbook(str(path))
    assert "speed_loss" not in summary["seakeeping"]
    text = write_report_md(
        summary, tmp_path / "calm.md").read_text(encoding="utf-8")
    assert "均为静水值" in text
    assert "未提供海况输入" in text


def test_custom_wave_periods_replace_the_reference_seas(tmp_path):
    path = _taskbook(tmp_path, "SEAS", extra="seakeeping:\n"
                                            "  wave_periods: [5.0, 7.0]\n")
    summary = run_taskbook(str(path))
    labels = [c["label"] for c in summary["seakeeping"]["resonance_checks"]]
    assert any("task-book sea (T 5 s)" in lab for lab in labels)
    assert any("task-book sea (T 7 s)" in lab for lab in labels)
    assert not any("East China Sea" in lab for lab in labels)


# ---------------------------------------------------------------------------
# P1-2: the feasibility hint
# ---------------------------------------------------------------------------


def test_ayre_refusal_carries_the_feasible_cb_bound(tmp_path):
    path = _taskbook(tmp_path, "HINT", cb="0.84")
    summary = run_taskbook(str(path))
    prop = summary["propeller_design"]
    assert prop.get("skipped") and prop.get("stage") == "ayre"
    hint = prop["feasibility_hint"]
    assert hint["direction"] == "lower"
    # the reviewer measured the boundary between 0.80 (pass) and 0.82
    assert 0.78 < hint["bound"] <= 0.82
    text = write_report_md(
        summary, tmp_path / "hint.md").read_text(encoding="utf-8")
    assert "可行方向（一次反算" in text
    assert "openhull optimize --grid-cb" in text


# ---------------------------------------------------------------------------
# P2-1 / P2-2: the output flags
# ---------------------------------------------------------------------------


def test_json_and_csv_paths_write_files_and_can_combine(tmp_path):
    path = _taskbook(tmp_path, "FLAGS")
    json_path, csv_path = tmp_path / "s.json", tmp_path / "t.csv"
    assert main(["run", path, "--json", str(json_path),
                 "--csv", str(csv_path)]) == 0
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["taskbook_id"] == "FLAGS"
    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert csv_text.splitlines()[0].startswith("draft_m")
    assert len(csv_text.strip().splitlines()) == 11  # 0.1 T default


def test_bare_flags_keep_the_stdout_behaviour(tmp_path):
    path = _taskbook(tmp_path, "BARE")
    assert main(["run", path, "--json"]) == 0


def test_csv_step_option_scales_the_table(tmp_path):
    path = _taskbook(tmp_path, "STEP")
    coarse = tmp_path / "coarse.csv"
    assert main(["run", path, "--csv", str(coarse),
                 "--csv-step", "0.25"]) == 0
    assert len(coarse.read_text(encoding="utf-8-sig")
               .strip().splitlines()) == 5  # header + 4
    fine = tmp_path / "fine.csv"
    assert main(["run", path, "--csv", str(fine),
                 "--csv-step", "0.5"]) == 0
    assert len(fine.read_text(encoding="utf-8-sig")
               .strip().splitlines()) == 3  # header + 2


def test_json_output_is_pure_at_the_process_boundary(tmp_path):
    """The v1.2.0 lesson, kept: the contract is verified across the
    process boundary, not only in-process."""
    path = _taskbook(tmp_path, "PURE")
    result = subprocess.run(
        [sys.executable, "-m", "openhull.cli", "run", str(path),
         "--json", "--csv-step", "0.25"],
        capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["taskbook_id"] == "PURE"
