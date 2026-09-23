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
    assert len(summary["hydrostatics"]) == 4
    design = summary["hydrostatics"][-1]
    assert design["draft_m"] == pytest.approx(16.5)
    assert abs(design["km_m"] - 18.59) / 18.59 < 0.02


def test_propeller_design_declares_the_ayre_band_skip(summary):
    # TB-001 at 14.5 kn sits below the Ayre V/sqrt(L) table band for a
    # 280 m ship - the propeller design block must skip DECLARED, not
    # extrapolate the resistance method
    prop = summary["propeller_design"]
    assert prop["skipped"] is True
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
    assert len(lines) == 5  # header + four drafts
    header = lines[0].split(",")
    row = dict(zip(header, lines[-1].split(",")))
    assert float(row["draft_m"]) == pytest.approx(16.5)
    # task 2.6 switched the CLI hull from the stage-1 fitted parent
    # (KM pinned to the anchor) to the real mother-ship chain: the
    # anchor band (±2 %, AGENTS.md section 4) still governs, and the
    # new exact value is pinned so drift shows up as a number
    assert abs(float(row["km_m"]) - 18.59) / 18.59 < 0.02
    assert float(row["km_m"]) == pytest.approx(18.6978, abs=0.005)


def test_cli_json_flag_roundtrips(capsys):
    rc = main(["run", TASKBOOK, "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    loaded = json.loads(out)
    assert loaded["deadweight_t"] == 149920.0
    assert len(loaded["hydrostatics"]) == 4


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
    captured = capsys.readouterr().out
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
    captured = capsys.readouterr().out
    assert "design report ->" in captured
    assert "arrangement DXF ->" in captured
    assert "arrangement chart ->" in captured
