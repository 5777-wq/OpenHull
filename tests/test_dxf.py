"""Tests for the DXF lines-plan export (plan task 2.7).

Acceptance: distinct layers (sections / waterlines / buttocks / DWL /
labels / frame), the file round-trips through ezdxf, and every TEXT
entity is pure ASCII so AutoCAD opens it without mojibake in any
locale.
"""

from pathlib import Path

import ezdxf
import pytest

from openhull.drawing import DXF_LAYERS, save_lines_plan_dxf
from openhull.geometry import load_raw_offsets

CSV = Path(__file__).resolve().parents[1] / "examples" / "data" / \
    "parent_hull_offsets.csv"


@pytest.fixture(scope="module")
def dxf_path(tmp_path_factory):
    raw = load_raw_offsets(str(CSV), lpp=280.0, beam=45.0, draft=16.5)
    out = tmp_path_factory.mktemp("dxf") / "lines_plan.dxf"
    written = save_lines_plan_dxf(
        raw, str(out), title="Series 60 parent -> JBC targets (Lackenby)"
    )
    return Path(written)


def test_dxf_roundtrips_through_ezdxf(dxf_path):
    doc = ezdxf.readfile(str(dxf_path))  # no audit errors raised
    assert not list(doc.audit())
    msp = doc.modelspace()
    kinds = {e.dxftype() for e in msp}
    assert {"LWPOLYLINE", "LINE", "TEXT"} <= kinds


def test_dxf_has_the_planned_layers(dxf_path):
    doc = ezdxf.readfile(str(dxf_path))
    names = {l.dxf.name for l in doc.layers}
    assert set(DXF_LAYERS) <= names


def test_dxf_curves_live_on_their_layers(dxf_path):
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    per_layer: dict[str, int] = {}
    for e in msp:
        if e.dxftype() in ("LWPOLYLINE", "LINE"):
            per_layer[e.dxf.layer] = per_layer.get(e.dxf.layer, 0) + 1
    assert per_layer["SECTIONS"] >= 19          # 21 stations minus ends
    assert per_layer["WATERLINES"] >= 7         # tabulated waterlines
    assert per_layer["BUTTOCKS"] == 3           # 25/50/75 %
    assert per_layer["DWL"] == 2                # body plan + sheer view
    assert per_layer["FRAME"] >= 3              # outer + inner + strip


def test_dxf_text_is_ascii_only(dxf_path):
    doc = ezdxf.readfile(str(dxf_path))
    texts = [e.dxf.text for e in doc.modelspace()
             if e.dxftype() == "TEXT"]
    assert len(texts) >= 6
    assert all(t.isascii() for t in texts)


def test_dxf_non_ascii_title_is_ascii_folded(tmp_path):
    raw = load_raw_offsets(str(CSV), lpp=280.0, beam=45.0, draft=16.5)
    out = tmp_path / "lines_plan.dxf"
    save_lines_plan_dxf(raw, str(out), title="型线图 lines plan")
    doc = ezdxf.readfile(str(out))
    texts = [e.dxf.text for e in doc.modelspace()
             if e.dxftype() == "TEXT"]
    assert all(t.isascii() for t in texts)
    assert any("lines plan" in t for t in texts)
