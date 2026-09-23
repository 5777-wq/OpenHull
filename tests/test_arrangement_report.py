"""General-arrangement schematic tests (plan task 4.2).

The default bulk-carrier scheme is DECLARED data (module docstring);
the tests pin its rules so the drawing can never silently drift:
compartment ordering and containment, the B/20 double-bottom
convention, hold division, and both output writers (PNG chart,
layered DXF).
"""

import ezdxf
import pytest

from openhull.arrangement import (
    arrangement_from_taskbook,
    default_bulk_carrier_arrangement,
    export_arrangement_dxf,
    write_arrangement_chart,
)


@pytest.fixture(scope="module")
def arr():
    return default_bulk_carrier_arrangement(280.0, 25.0, 45.0, n_holds=5)


def test_default_scheme_rules(arr):
    kinds = {c.name: c.kind for c in arr.compartments}
    assert kinds["Aft Peak Tank"] == "peak"
    assert kinds["Engine Room"] == "machinery"
    assert kinds["Fore Peak Tank"] == "peak"
    assert sum(1 for k in kinds.values() if k == "hold") == 5
    # aft peak starts at the AP, fore peak ends at the FP
    assert arr.compartments[0].x0_m == pytest.approx(0.0)
    assert arr.compartments[-1].x1_m == pytest.approx(280.0)
    # holds tile their region without gaps or overlaps
    holds = [c for c in arr.compartments if c.kind == "hold"]
    assert holds[0].x0_m == pytest.approx(0.095 * 280.0)
    assert holds[-1].x1_m == pytest.approx(0.940 * 280.0)
    for a, b in zip(holds, holds[1:]):
        assert a.x1_m == pytest.approx(b.x0_m)
    # engine room above the double bottom, peaks full depth
    er = next(c for c in arr.compartments if c.name == "Engine Room")
    assert er.z0_m == pytest.approx(arr.double_bottom_top_m)
    assert arr.compartments[0].z1_m == pytest.approx(25.0)


def test_double_bottom_b20_convention(arr):
    # B/20 = 2.25 m governs at this beam; the 1.0 m floor never binds
    assert arr.double_bottom_top_m == pytest.approx(45.0 / 20.0)
    small = default_bulk_carrier_arrangement(40.0, 6.0, 5.0)
    assert small.double_bottom_top_m == pytest.approx(1.0)


def test_taskbook_override_and_default():
    # no block -> default scheme
    arr = arrangement_from_taskbook({}, 100.0, 12.0, 20.0)
    assert arr.source == "default bulk-carrier scheme"
    assert len(arr.compartments) == 8  # 2 peaks + ER + 5 holds
    # n_holds override
    arr3 = arrangement_from_taskbook({"arrangement": {"n_holds": 3}},
                                     100.0, 12.0, 20.0)
    assert sum(1 for c in arr3.compartments if c.kind == "hold") == 3
    # manual compartment table wins entirely
    manual = {"arrangement": {"compartments": [
        {"name": "Tank", "kind": "tank", "x0_m": 0.0, "x1_m": 10.0,
         "z0_m": 0.0, "z1_m": 12.0}]}}
    arr_m = arrangement_from_taskbook(manual, 100.0, 12.0, 20.0)
    assert arr_m.source == "task-book arrangement block"
    assert [c.name for c in arr_m.compartments] == ["Tank"]


def test_writers_produce_png_and_dxf(arr, tmp_path):
    png = write_arrangement_chart(arr, tmp_path / "ga.png", title="T")
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    dxf = export_arrangement_dxf(arr, tmp_path / "ga.dxf")
    doc = ezdxf.readfile(dxf)
    assert {"GA-SIDE", "GA-PLAN", "GA-DB", "GA-LABELS"} <= {
        layer.dxf.name for layer in doc.layers}
