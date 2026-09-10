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


def test_cli_summary_text(capsys):
    rc = main(["run", TASKBOOK])
    out = capsys.readouterr().out
    assert rc == 0
    assert "OpenHull stage-1 run" in out
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
    assert float(row["km_m"]) == pytest.approx(18.59, abs=0.01)


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
