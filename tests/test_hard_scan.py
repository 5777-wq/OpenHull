"""Hard-draft scan mode (round-8 backlog, the R2-A decision extended
to the scan).

With ``draft_is_hard: true`` the scan sweeps L/B x Cb and SOLVES B/T
per candidate to honour the declared draft (bisection, +-1 cm) — the
scan's feasibility map and the single-point `run` now live in the same
design space.  The B/T grid axis must be pinned to one value (it is
not scanned); the solved B/T lands in every row.
"""

import json

import pytest

from openhull.cli import main
from openhull.weight_balance import solve_weight_balance_for_draft
from openhull.spec import ShipSpec

BASE = """\
schema_version: 1
taskbook_id: HS-{tag}
ship_type: bulk_carrier
requirements:
  deadweight_t: 45000
  service_speed_kn: 16.0
  kg_m: 9.5
  drafts:
    design_draft_m: 11.6
    draft_is_hard: true
constraints:
  block_coefficient_design: {cb}
propeller:
  blades_z: 4
  expanded_area_ratio: 0.55
  rpm: 100
  shaft_immersion_m: 6.0
  shaft_efficiency: 0.98
  relative_rotative_eff: 0.99
"""


def test_hard_scan_solves_bt_and_honours_the_declared_draft(tmp_path):
    path = tmp_path / "hs.yaml"
    path.write_text(BASE.format(tag="OK", cb="0.80"), encoding="utf-8")
    out = tmp_path / "out"
    rc = main(["optimize", str(path), "--out", str(out),
               "--grid-lob", "6.0:6.0:1",
               "--grid-bt", "2.7:2.7:1",
               "--grid-cb", "0.80:0.80:1"])
    assert rc == 0
    summary = json.loads(
        (out / "scan_summary.json").read_text(encoding="utf-8"))
    assert "hard draft" in summary["scan_mode"]
    rows = summary["designs"]
    assert rows, "the in-band candidate should be feasible"
    for row in rows:
        # the whole point: the scan's ship floats at the DECLARED draft
        assert abs(row["draft_m"] - 11.6) <= 0.01
        assert 2.0 <= row["b_over_t"] <= 3.5
    # and the solved B/T matches the single-design hard solve exactly
    spec = ShipSpec(ship_type="bulk_carrier", deadweight=45000.0,
                    service_speed=16.0 * 1852.0 / 3600.0, cb=0.80,
                    draft=11.6)
    balance = solve_weight_balance_for_draft(spec, 11.6)
    assert rows[0]["b_over_t"] == pytest.approx(
        balance.beam / balance.draft, abs=0.01)


def test_hard_scan_records_unreachable_candidates_as_refusals(tmp_path):
    # a deep draft the band cannot reach at Cb 0.72: those candidates
    # must appear in rejected_points with the hard_draft stage
    path = tmp_path / "hs2.yaml"
    path.write_text(BASE.format(tag="DEEP", cb="0.72").replace(
        "    design_draft_m: 11.6", "    design_draft_m: 15.5"),
        encoding="utf-8")
    out = tmp_path / "out"
    rc = main(["optimize", str(path), "--out", str(out),
               "--grid-lob", "6.0:6.0:1",
               "--grid-bt", "2.7:2.7:1",
               "--grid-cb", "0.72:0.72:1"])
    assert rc == 0
    summary = json.loads(
        (out / "scan_summary.json").read_text(encoding="utf-8"))
    assert summary["feasible"] == 0
    stages = {r["stage"] for r in summary["rejected_points"]}
    assert "hard_draft" in stages



