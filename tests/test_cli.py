"""Tests for the command line interface (plan task 1.8).

The CLI streams to stdout (no file writes), so tests capture stdout
and parse it back: the CSV bytes the user redirects are exactly what
these assertions see.
"""

import json

import pytest

from openhull.cli import main, run_taskbook

TASKBOOK = "examples/taskbook_bulk_carrier.yaml"


@pytest.fixture(scope="module")
def summary():
    return run_taskbook(TASKBOOK)


def test_run_returns_stage1_chain_results(summary):
    assert summary["taskbook_id"] == "TB-001"
    assert summary["algorithm_id"] == "component_cubic"
    # the balance closes on the JBC displacement anchor within 1 %
    assert abs(summary["displacement_t"] - 182829.1) / 182829.1 < 0.01
    assert summary["iterations"] == 3
    assert summary["norman_coefficient"] > 1.0
    assert len(summary["hydrostatics"]) == 10  # 0.1 T step (P2-2)
    design = summary["hydrostatics"][-1]
    # ONE design draft for the whole chain (review-response 2026-09-24):
    # the top hydrostatic row IS the balance draft, not the declared
    # task-book draft
    assert design["draft_m"] == pytest.approx(summary["draft_m"], abs=0.01)
    assert abs(design["km_m"] - 18.59) / 18.59 < 0.02


def test_propeller_design_declares_the_ayre_band_skip(summary):
    # TB-001 at 14.5 kn sits below the Ayre V/sqrt(L) table band for a
    # 280 m ship - the propeller design block must skip DECLARED, not
    # extrapolate the resistance method
    prop = summary["propeller_design"]
    assert prop["skipped"] is True
    assert prop["stage"] == "ayre"       # staged refusal (review batch)
    assert "0.486" in prop["reason"]


def test_cli_summary_text(capsys):
    rc = main(["run", TASKBOOK])
    out = capsys.readouterr().out
    assert rc == 0
    assert "OpenHull run" in out
    assert "TB-001" in out
    assert "KM = KB + BMT" in out


def test_cli_csv_flag_streams_parseable_table(capsys):
    rc = main(["run", TASKBOOK, "--csv"])
    captured = capsys.readouterr()
    out_bytes = captured.out.encode("utf-8", errors="replace")
    assert rc == 0
    text = out_bytes.decode("utf-8-sig")
    lines = text.strip().splitlines()
    assert lines[0].split(",")[0] == "draft_m"
    assert len(lines) == 11  # header + ten drafts (0.1 T step)
    header = lines[0].split(",")
    row = dict(zip(header, lines[-1].split(",")))
    assert float(row["draft_m"]) == pytest.approx(16.7674, abs=0.01)
    # task 2.6 switched the CLI hull from the stage-1 fitted parent
    # (KM pinned to the anchor) to the real mother-ship chain: the
    # anchor band (±2 %, AGENTS.md section 4) still governs, and the
    # new exact value is pinned so drift shows up as a number
    assert abs(float(row["km_m"]) - 18.59) / 18.59 < 0.02
    # the top row now sits at the BALANCE draft (16.7674 m), so KM
    # re-pinned at that draft (was 18.6978 at the old 16.5 m row)
    assert float(row["km_m"]) == pytest.approx(18.6896, abs=0.005)


def test_cli_json_flag_roundtrips(capsys):
    rc = main(["run", TASKBOOK, "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    loaded = json.loads(out)
    assert loaded["deadweight_t"] == 149920.0
    assert len(loaded["hydrostatics"]) == 10  # 0.1 T step (P2-2)


def test_missing_taskbook_keys_exit_code_2(tmp_path, capsys):
    bad = tmp_path / "bad_taskbook.yaml"
    bad.write_text("taskbook_id: TB-BAD\nship_type: bulk_carrier\n",
                   encoding="utf-8")
    rc = main(["run", str(bad)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "required keys present" in err


def test_nonexistent_taskbook_file_exit_code_2(capsys):
    rc = main(["run", "examples/does_not_exist.yaml"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "existing YAML file" in err


def test_optimize_subcommand_runs_and_writes_outputs(tmp_path):
    out = tmp_path / "scan"
    rc = main([
        "optimize", "examples/taskbook_bulk_carrier_scan16kn.yaml",
        "--grid-lob", "5.8:6.2:2",
        "--grid-bt", "2.7:3.1:2",
        "--grid-cb", "0.82:0.85:2",
        "--out", str(out),
    ])
    assert rc == 0
    assert (out / "feasible_designs.csv").exists()
    assert (out / "tradeoff_speed_displacement_gm.png").exists()
    assert (out / "scan_summary.json").exists()


def test_hydro_curve_chart_flag_writes_png(tmp_path, capsys):
    out = tmp_path / "hydro_curves.png"
    rc = main(["run", TASKBOOK, "--hydro-curve-chart", str(out)])
    assert rc == 0
    assert out.exists()
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    captured = capsys.readouterr().err
    assert f"hydrostatic curves chart -> {out}" in captured


def test_seakeeping_block_in_summary(summary):
    # task 3.8 stage 1: the run summary carries the seakeeping layer
    sk = summary["seakeeping"]
    assert sk["roll_period_s"] > 0
    assert len(sk["resonance_checks"]) == 4


def test_rao_subcommand_runs(tmp_path, capsys):
    pytest.importorskip("capytaine",
                        reason="capytaine not installed")
    rc = main(["rao", TASKBOOK, "--periods", "8,12,20"])
    assert rc == 0
    captured = capsys.readouterr().out
    assert "zero-speed RAOs" in captured
    assert "(head)" in captured and "(beam)" in captured


def test_rao_subcommand_json(tmp_path, capsys):
    pytest.importorskip("capytaine",
                        reason="capytaine not installed")
    rc = main(["rao", TASKBOOK, "--periods", "8,12", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mesh_info"]["n_faces"] > 0
    assert len(payload["points"]) == 2 * 2 * 3


def test_report_and_arrangement_flags(tmp_path, capsys):
    report = tmp_path / "report.md"
    dxf = tmp_path / "ga.dxf"
    ga = tmp_path / "ga.png"
    rc = main(["run", TASKBOOK, "--report", str(report),
               "--arrangement-dxf", str(dxf),
               "--arrangement-chart", str(ga)])
    assert rc == 0
    text = report.read_text(encoding="utf-8")
    assert "OpenHull 初步设计报告" in text
    assert "总布置简图" in text
    assert dxf.exists() and ga.exists()
    captured = capsys.readouterr().err   # confirmations live on stderr
    assert "design report ->" in captured
    assert "arrangement DXF ->" in captured
    assert "arrangement chart ->" in captured


def test_freeboard_wired_into_run(summary):
    """Round 9: the task-1.6 load-line check has been library-complete
    and validated since v0.1.0 (VALIDATION, Freeboard section) — the
    run chain now surfaces it.  The TB-001 numbers are the VALIDATION
    anchor row: F0 4,397 + f2 575.5 + f3 1,583.3 = 6,556 mm minimum,
    actual 8,500 mm, PASS with 1,944 mm margin."""
    fb = summary["freeboard"]
    assert not fb.get("skipped")
    assert fb["ship_type"] == "B"
    # the chain calibre: the check runs on the BALANCE dims (the
    # one-design-draft rule), not the declared task-book sizes — so
    # F0 interpolates Table 3-9 at the balance Lpp 271.63 m
    # (270 -> 280: 4276 + 0.1633 x 121), and the actual freeboard is
    # balance depth - balance draft
    assert fb["f0"] == pytest.approx(4295.75, abs=0.5)
    assert fb["f1"] == fb["f4"] == fb["f5"] == 0.0
    assert fb["f2"] > 0 and fb["f3"] > 0
    assert fb["minimum_freeboard_mm"] == pytest.approx(
        fb["f0"] + fb["f2"] + fb["f3"], abs=1e-9)
    assert fb["actual_freeboard_mm"] == pytest.approx(
        (summary["depth_m"] - summary["draft_m"]) * 1000.0, abs=1.0)
    assert fb["verdict"] == "PASS" and fb["margin_mm"] > 0
    # the module itself still reproduces the VALIDATION anchor row
    # (declared task-book sizes: L 280 / Ds 25 / T 16.5)
    from openhull.freeboard import minimum_freeboard
    anchor = minimum_freeboard(
        lpp=280.0, ship_type="B", depth_s=25.0, cb_at_085d=0.858,
        actual_freeboard_mm=8500.0)
    assert anchor.f0 == pytest.approx(4397.0, abs=0.5)
    assert anchor.minimum_freeboard_mm == pytest.approx(6555.8, abs=1.0)
    assert anchor.verdict == "PASS"
    assert anchor.margin_mm == pytest.approx(1944.2, abs=2.0)


def test_freeboard_report_and_console(tmp_path, capsys):
    """The report restates the freeboard verdict and the console
    declares it; a run WITHOUT the section would be the silent-drop
    pattern the unchecked-is-not-passed contract forbids."""
    import io

    report = tmp_path / "r.md"
    rc = main(["run", TASKBOOK, "--report", str(report)])
    assert rc == 0
    text = report.read_text(encoding="utf-8")
    assert "载重线干舷" in text and "PASS" in text
    out = io.StringIO()
    saved = __import__("sys").stdout
    import sys
    sys.stdout = out
    try:
        main(["run", TASKBOOK])
    finally:
        sys.stdout = saved
    assert "load-line freeboard" in out.getvalue()
