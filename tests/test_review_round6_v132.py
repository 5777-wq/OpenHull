"""Review round 6 (2026-09-27) — the run-path chart guards.

The round-5 fix guarded only `optimize`'s chart; the verifier showed
`run`'s two chart options were still unguarded - a broken plotting
stack aborted the whole chain (exit 1, 17-line third-party traceback,
and with --report the PRIMARY deliverable was lost to an optional
chart).  Pinned here:

- `--hydro-curve-chart` / `--arrangement-chart` degrade to a declared
  note (stderr, with the remedy); the report and all data products
  survive; no phantom chart path in stdout or JSON;
- `check` mentions missing plotting deps (existence probes only,
  milliseconds) WITHOUT touching its exit-code contract - console
  hint only, never in --json.
"""

import json

from openhull.cli import main

BASE = """\
schema_version: 1
taskbook_id: R6-{tag}
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


def _taskbook(tmp_path, tag):
    path = tmp_path / f"{tag}.yaml"
    path.write_text(BASE.format(tag=tag), encoding="utf-8")
    return str(path)


def test_run_hydro_chart_degrade_keeps_the_report(tmp_path, monkeypatch,
                                                  capsys):
    import openhull.hydrostatics_chart as hc

    def broken(*args, **kwargs):
        raise ModuleNotFoundError("No module named 'cycler'")

    monkeypatch.setattr(hc, "write_hydrostatic_curves_chart", broken)
    tb = _taskbook(tmp_path, "HYDRO")
    report = tmp_path / "r.md"
    png = tmp_path / "c.png"
    rc = main(["run", tb, "--report", str(report),
               "--hydro-curve-chart", str(png)])
    assert rc == 0
    # the PRIMARY deliverable survives an OPTIONAL chart
    assert report.exists()
    assert "# OpenHull" in report.read_text(encoding="utf-8")
    assert not png.exists()
    err = capsys.readouterr().err
    assert "hydrostatic curves chart unavailable" in err
    assert "remedy" in err


def test_run_arrangement_chart_degrade(tmp_path, monkeypatch, capsys):
    import openhull.arrangement as arr

    def broken(*args, **kwargs):
        raise ModuleNotFoundError("No module named 'cycler'")

    monkeypatch.setattr(arr, "write_arrangement_chart", broken)
    tb = _taskbook(tmp_path, "GA")
    png = tmp_path / "ga.png"
    rc = main(["run", tb, "--arrangement-chart", str(png)])
    assert rc == 0
    assert not png.exists()
    err = capsys.readouterr().err
    assert "arrangement chart unavailable" in err


def test_run_json_carries_chart_notes_not_phantom_paths(tmp_path,
                                                        monkeypatch):
    import openhull.hydrostatics_chart as hc

    def broken(*args, **kwargs):
        raise ModuleNotFoundError("No module named 'cycler'")

    monkeypatch.setattr(hc, "write_hydrostatic_curves_chart", broken)
    tb = _taskbook(tmp_path, "JSON")
    json_path = tmp_path / "s.json"
    rc = main(["run", tb, "--json", str(json_path),
               "--hydro-curve-chart", str(tmp_path / "c.png")])
    assert rc == 0
    summary = json.loads(json_path.read_text(encoding="utf-8"))
    assert summary["hydrostatic_curve_chart"] is None
    assert any("hydrostatic curves chart" in n
               for n in summary["chart_notes"])
    assert "remedy" in summary["chart_notes"][0]


def test_check_warns_missing_chart_deps_without_exit_change(tmp_path,
                                                            monkeypatch,
                                                            capsys):
    import importlib.util

    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name, *args, **kwargs):
        if name in ("matplotlib", "cycler"):
            return None
        return real_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    tb = _taskbook(tmp_path, "CHK")
    rc = main(["check", tb])
    out = capsys.readouterr().out
    assert rc == 0
    assert "plotting deps missing" in out
    assert "exit code unchanged" in out


def test_check_json_stays_clean_of_the_dep_hint(tmp_path, monkeypatch,
                                                capsys):
    import importlib.util

    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name, *args, **kwargs):
        if name in ("matplotlib", "cycler"):
            return None
        return real_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    tb = _taskbook(tmp_path, "CHKJ")
    rc = main(["check", tb, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert "plotting" not in json.dumps(payload)
