"""Review round 5 (2026-09-26) — the two code-level findings.

- 6.2   the optimize chart degrades to a declared note when the
        plotting dependency is broken (no bare third-party traceback;
        the scan's CSV/JSON products stay complete either way);
- 6.4   the console Kwon line reads "1.7% slower" instead of a bare
        "-1.7%" that reads like a speed gain at a glance.
"""

import json

from openhull.cli import _write_scan_chart, main

BASE = """\
schema_version: 1
taskbook_id: {tag}
ship_type: bulk_carrier
requirements:
  deadweight_t: 100000
  service_speed_kn: {speed}
  kg_m: 11.0
  drafts:
    design_draft_m: 15.42
constraints:
  block_coefficient_design: {cb}
seakeeping:
  speed_loss:
    beaufort: 6
    direction: head
propeller:
  blades_z: 4
  expanded_area_ratio: 0.55
  rpm: 105
  shaft_immersion_m: 7.7
  shaft_efficiency: 0.98
  relative_rotative_eff: 0.982
"""


def test_chart_failure_degrades_to_a_declared_note(tmp_path, monkeypatch):
    import openhull.cli as cli

    def broken(result, path):
        raise ModuleNotFoundError("No module named 'cycler'")

    monkeypatch.setattr(cli, "write_tradeoff_chart", broken)
    note = _write_scan_chart(object(), tmp_path / "t.png")
    assert note is not None
    assert "ModuleNotFoundError" in note
    assert "unaffected" in note


def test_chart_success_returns_no_note(tmp_path, monkeypatch):
    import openhull.cli as cli

    def ok(result, path):
        path.write_bytes(b"png")

    monkeypatch.setattr(cli, "write_tradeoff_chart", ok)
    assert _write_scan_chart(object(), tmp_path / "t.png") is None


def test_optimize_json_carries_the_chart_note(tmp_path, monkeypatch):
    import openhull.cli as cli

    def broken(result, path):
        raise ModuleNotFoundError("No module named 'cycler'")

    monkeypatch.setattr(cli, "write_tradeoff_chart", broken)
    tb = tmp_path / "tb.yaml"
    tb.write_text(BASE.format(tag="R5-CHART", speed="18.0", cb="0.76"),
                  encoding="utf-8")
    out_dir = tmp_path / "out"
    rc = main(["optimize", str(tb), "--out", str(out_dir)])
    assert rc == 0
    summary = json.loads(
        (out_dir / "scan_summary.json").read_text(encoding="utf-8"))
    assert "ModuleNotFoundError" in summary["outputs"]["chart_note"]


def test_console_kwon_line_says_slower(tmp_path, capsys):
    path = tmp_path / "kwon.yaml"
    path.write_text(BASE.format(tag="R5-KWON", speed="18.0", cb="0.76"),
                    encoding="utf-8")
    rc = main(["run", str(path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "1.7% slower" in out or "% slower" in out
    assert "-> -" not in out
