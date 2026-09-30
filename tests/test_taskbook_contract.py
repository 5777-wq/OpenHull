"""Task-book input contract (round-7 review, OH-16).

The 428-test suite pinned "legal input computes correctly"; nothing
pinned "illegal input is refused READABLY".  One test per contract
point the round-7 review found missing - each asserts the exit code
and the offending field name in stderr, not numbers:

- kg_m absent  -> run SUCCEEDS (documented optional), sections declared;
- unknown key  -> refused, with a did-you-mean suggestion;
- type error   -> refused, naming the field;
- non-UTF-8    -> readable re-save hint, no codec traceback;
- partial weather mapping -> refused, no bare KeyError;
- duplicate key -> refused with the line number;
- output path into a missing directory -> parent dirs auto-created;
- draft_is_hard + optimize -> refused with guidance (OH-07);
- non-bulk ship_type -> refused (OH-14);
- shaft_efficiency 0 -> refused, never silently 1.0 (OH-04);
- missing shaft_immersion_m -> cavitation_skipped DECLARED (OH-05).

Refusals are asserted through main()'s public contract: rc 2 and a
readable one-line message on stderr (never a traceback).
"""

import json

from openhull.cli import main

BASE = """\
schema_version: 1
taskbook_id: C-{tag}
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
  expanded_area_ratio: 0.55
  rpm: 100
  shaft_immersion_m: 6.0
  shaft_efficiency: 0.98
  relative_rotative_eff: 0.99
"""


def _refused(tmp_path, text, tag):
    path = tmp_path / f"{tag}.yaml"
    path.write_text(text, encoding="utf-8")
    rc = main(["run", str(path)])
    return rc


def test_kg_m_absent_still_runs_and_declares(tmp_path):
    text = BASE.format(tag="NOKG").replace("  kg_m: 9.5\n", "")
    path = tmp_path / "NOKG.yaml"
    path.write_text(text, encoding="utf-8")
    json_path = tmp_path / "s.json"
    rc = main(["run", str(path), "--json", str(json_path)])
    assert rc == 0
    summary = json.loads(json_path.read_text(encoding="utf-8"))
    assert summary["gz_curve"] is None
    assert summary["weather_criterion"] is None
    assert summary["seakeeping"] is None


def test_unknown_key_refused_with_suggestion(tmp_path, capsys):
    text = BASE.format(tag="TYPO").replace("  kg_m: 9.5", "  KG_m: 9.5")
    rc = _refused(tmp_path, text, "TYPO2")
    assert rc == 2
    err = capsys.readouterr().err
    assert "KG_m" in err
    assert "kg_m" in err  # the did-you-mean hint
    assert "Traceback" not in err


def test_type_error_refused_readably(tmp_path, capsys):
    text = BASE.format(tag="STR").replace(
        "  kg_m: 9.5", "  kg_m: thirteen")
    rc = _refused(tmp_path, text, "STR")
    assert rc == 2
    assert "requirements.kg_m" in capsys.readouterr().err


def test_non_utf8_taskbook_refused_readably(tmp_path, capsys):
    text = BASE.format(tag="GBK").replace(
        "  kg_m: 9.5", "  kg_m: 9.5  # 中文注释触发编码差")
    path = tmp_path / "GBK.yaml"
    path.write_bytes(text.encode("gbk"))
    rc = main(["run", str(path)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "UTF-8" in err
    assert "GBK" in err or "ANSI" in err
    assert "Traceback" not in err


def test_partial_weather_mapping_refused_not_keyerror(tmp_path, capsys):
    text = BASE.format(tag="WX").replace(
        "constraints:\n  block_coefficient_design: 0.80",
        "constraints:\n  block_coefficient_design: 0.80\n"
        "  stability:\n    weather_criterion:\n"
        "      windage_area_m2: 2380")
    rc = _refused(tmp_path, text, "WX")
    assert rc == 2
    err = capsys.readouterr().err
    assert "windage_lever_z_m" in err
    assert "KeyError" not in err


def test_duplicate_key_refused_with_line(tmp_path, capsys):
    text = BASE.format(tag="DUP").replace(
        "  deadweight_t: 45000",
        "  deadweight_t: 45000\n  deadweight_t: 120000")
    rc = _refused(tmp_path, text, "DUP")
    assert rc == 2
    err = capsys.readouterr().err
    assert "deadweight_t" in err
    assert "line" in err.lower()


def test_output_into_missing_directory_autocreates(tmp_path):
    target = tmp_path / "no" / "such" / "dir" / "r.md"
    rc = main(["run", _write_ok(tmp_path, "MK"), "--report",
               str(target)])
    assert rc == 0
    assert target.exists()


def _write_ok(tmp_path, tag):
    path = tmp_path / f"{tag}.yaml"
    path.write_text(BASE.format(tag=tag), encoding="utf-8")
    return str(path)


def test_optimize_hard_draft_needs_a_single_bt_axis(tmp_path, capsys):
    text = BASE.format(tag="HD").replace(
        "    design_draft_m: 11.6",
        "    design_draft_m: 11.6\n    draft_is_hard: true")
    path = tmp_path / "HD.yaml"
    path.write_text(text, encoding="utf-8")
    rc = main(["optimize", str(path), "--out", str(tmp_path / "out")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "B/T" in err and "solved" in err


def test_non_bulk_ship_type_refused(tmp_path, capsys):
    text = BASE.format(tag="TANK").replace(
        "ship_type: bulk_carrier", "ship_type: tanker")
    rc = _refused(tmp_path, text, "TANK2")
    assert rc == 2
    assert "bulk_carrier" in capsys.readouterr().err


def test_zero_shaft_efficiency_refused_not_silently_one(tmp_path, capsys):
    text = BASE.format(tag="ETA").replace(
        "  shaft_efficiency: 0.98", "  shaft_efficiency: 0")
    rc = _refused(tmp_path, text, "ETA")
    assert rc == 2
    assert "shaft_efficiency" in capsys.readouterr().err


def test_missing_immersion_declares_cavitation_skipped(tmp_path):
    text = BASE.format(tag="IMM").replace(
        "  shaft_immersion_m: 6.0\n", "")
    path = tmp_path / "IMM.yaml"
    path.write_text(text, encoding="utf-8")
    json_path = tmp_path / "s.json"
    rc = main(["run", str(path), "--json", str(json_path)])
    assert rc == 0
    summary = json.loads(json_path.read_text(encoding="utf-8"))
    prop = summary["propeller_design"]
    assert prop["cavitation"] is None
    assert prop["cavitation_unchecked"] is None
    skipped = prop["cavitation_skipped"]
    assert "shaft_immersion_m" in skipped["reason"]


def test_demo_csv_artifact_does_not_drift(tmp_path):
    """Round-7 OH-10: the committed demo CSV had gone 15 versions stale
    (with stray stderr lines inside).  The regenerated artifact is
    pinned byte-for-byte so the folder cannot silently rot again."""
    committed = (tmp_path / "committed.csv")
    committed.write_bytes(
        open("examples/demo_outputs/hydrostatics_table.csv", "rb").read())
    fresh = tmp_path / "fresh.csv"
    rc = main(["run", "examples/taskbook_bulk_carrier.yaml",
               "--csv", str(fresh)])
    assert rc == 0
    assert fresh.read_bytes() == committed.read_bytes()


def test_optimize_bad_blades_refused_readably(tmp_path, capsys):
    """Round-9 B-2: the optimize path parsed blades_z with raw int() —
    a bad value surfaced as an "unexpected ValueError".  Same contract
    as the run path: the field is named, no traceback."""
    text = BASE.format(tag="BLD").replace("  blades_z: 4",
                                          "  blades_z: five")
    path = tmp_path / "BLD.yaml"
    path.write_text(text, encoding="utf-8")
    rc = main(["optimize", str(path), "--out", str(tmp_path / "out")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "propeller.blades_z" in err and "Traceback" not in err


def test_optimize_zero_rpm_refused_not_silently_default(tmp_path, capsys):
    """Round-9 B-2: `rpm or 127.0` silently replaced a declared 0 rpm
    with the default — the OH-04 falsy-0 pattern on the scan path."""
    text = BASE.format(tag="RPM0").replace("  rpm: 100", "  rpm: 0")
    path = tmp_path / "RPM0.yaml"
    path.write_text(text, encoding="utf-8")
    rc = main(["optimize", str(path), "--out", str(tmp_path / "out")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "propeller.rpm" in err and "Traceback" not in err
