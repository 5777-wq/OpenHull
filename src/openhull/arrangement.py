"""General-arrangement schematic (plan task 4.2).

A DATA-DRIVEN compartment layout drawing: the compartment table comes
from the task book's optional ``arrangement`` block, or from the
declared default bulk-carrier scheme when the task book carries none.
No empirical formula lives here and NOTHING in this module feeds
back into any calculation — it visualizes and exports declarations.

Default bulk-carrier scheme (single screw, aft engine room), all
positions fractions of Lpp from the aft perpendicular — declared
engineering defaults for a preliminary GA schematic, overridable
per compartment in the task book:

  aft peak tank     0.000 - 0.030 Lpp   (full depth)
  engine room       0.030 - 0.095 Lpp   (above the double bottom)
  cargo holds 1..N  0.095 - 0.940 Lpp   evenly divided (default N = 5)
  fore peak tank    0.940 - 1.000 Lpp   (collision bulkhead at 0.94,
                    the common "5 % L from the FP" preliminary slot)
  double bottom     height max(B/20, 1.0 m) — the common minimum-
                    height convention; holds and engine room start
                    on top of it

The schematic drawing states on its face that it is NOT the real
hull lines plan (the no-drawing red line, AGENTS.md section 7,
concerns geometry deliverables — those stay offsets tables + layered
DXF; the GA schematic is a compartment-LAYOUT diagram and its DXF
export lands on labelled layers, same convention as task 2.4).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .spec import SpecValidationError

__all__ = [
    "Compartment",
    "Arrangement",
    "default_bulk_carrier_arrangement",
    "arrangement_from_taskbook",
    "write_arrangement_chart",
    "export_arrangement_dxf",
]

#: default scheme fractions of Lpp (aft perpendicular origin)
_AFT_PEAK_END = 0.030
_ENGINE_ROOM_END = 0.095
_HOLDS_END = 0.940
_DEFAULT_HOLDS = 5

_CITATION = (
    "declared preliminary GA defaults (module docstring); task-book "
    "arrangement block overrides everything — no calculation input"
)


def _require(condition: bool, field: str, value: Any, constraint: str,
             reason: str) -> None:
    if not condition:
        raise SpecValidationError(field, value, constraint, reason)


@dataclass(frozen=True)
class Compartment:
    """One rectangular compartment of the schematic, metres.

    x measured from the aft perpendicular (0 = AP, Lpp = FP); z
    above keel.  kind: peak / machinery / hold / tank / void.
    """

    name: str
    kind: str
    x0_m: float
    x1_m: float
    z0_m: float
    z1_m: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Arrangement:
    """Compartment layout of one ship (declarative data only)."""

    compartments: tuple[Compartment, ...]
    lpp_m: float
    depth_m: float
    beam_m: float
    double_bottom_top_m: float
    source: str
    citation: str = _CITATION

    def to_dict(self) -> dict[str, Any]:
        return {
            "compartments": [c.to_dict() for c in self.compartments],
            "lpp_m": self.lpp_m,
            "depth_m": self.depth_m,
            "beam_m": self.beam_m,
            "double_bottom_top_m": self.double_bottom_top_m,
            "source": self.source,
            "citation": self.citation,
        }


def default_bulk_carrier_arrangement(lpp_m: float, depth_m: float,
                                     beam_m: float,
                                     n_holds: int = _DEFAULT_HOLDS
                                     ) -> Arrangement:
    """The declared default scheme of the module docstring."""
    for name, value in (("lpp_m", lpp_m), ("depth_m", depth_m),
                        ("beam_m", beam_m)):
        _require(math.isfinite(value) and value > 0.0,
                 name, value, "finite value > 0",
                 "principal dimensions must be positive")
    _require(isinstance(n_holds, int) and 1 <= n_holds <= 12,
             "n_holds", n_holds, "integer 1..12",
             "a preliminary bulk-carrier schematic carries a sane "
             "number of holds")
    db_top = max(beam_m / 20.0, 1.0)
    x_h0, x_h1 = _ENGINE_ROOM_END * lpp_m, _HOLDS_END * lpp_m
    step = (x_h1 - x_h0) / n_holds
    compartments = [
        Compartment("Aft Peak Tank", "peak", 0.0, _AFT_PEAK_END * lpp_m,
                    0.0, depth_m),
        Compartment("Engine Room", "machinery", _AFT_PEAK_END * lpp_m,
                    _ENGINE_ROOM_END * lpp_m, db_top, depth_m),
    ]
    for k in range(n_holds):
        compartments.append(Compartment(
            f"Cargo Hold {k + 1}", "hold",
            x_h0 + k * step, x_h0 + (k + 1) * step, db_top, depth_m))
    compartments.append(Compartment(
        "Fore Peak Tank", "peak", _HOLDS_END * lpp_m, lpp_m, 0.0, depth_m))
    return Arrangement(compartments=tuple(compartments), lpp_m=lpp_m,
                       depth_m=depth_m, beam_m=beam_m,
                       double_bottom_top_m=db_top,
                       source="default bulk-carrier scheme")


def arrangement_from_taskbook(data: dict, lpp_m: float, depth_m: float,
                              beam_m: float) -> Arrangement:
    """Read the optional ``arrangement`` block, else the default scheme.

    Task-book form::

        arrangement:
          double_bottom_top_m: 2.25     # optional
          n_holds: 5                    # optional, with the default scheme
          compartments:                 # optional, full manual override
            - name: Cargo Hold 1
              kind: hold
              x0_m: 26.6
              x1_m: 73.0
              z0_m: 2.25
              z1_m: 25.0
    """
    block = data.get("arrangement")
    if not isinstance(block, dict) or not block.get("compartments"):
        n_holds = int(block.get("n_holds", _DEFAULT_HOLDS)) \
            if isinstance(block, dict) else _DEFAULT_HOLDS
        arr = default_bulk_carrier_arrangement(lpp_m, depth_m, beam_m,
                                               n_holds=n_holds)
        if isinstance(block, dict) and block.get("double_bottom_top_m"):
            override = float(block["double_bottom_top_m"])
            arr = Arrangement(
                compartments=tuple(
                    Compartment(c.name, c.kind, c.x0_m, c.x1_m,
                                override if c.z0_m == arr.double_bottom_top_m
                                else c.z0_m, c.z1_m)
                    for c in arr.compartments),
                lpp_m=arr.lpp_m, depth_m=arr.depth_m, beam_m=arr.beam_m,
                double_bottom_top_m=override, source=arr.source,
            )
        return arr
    comps = []
    for entry in block["compartments"]:
        comps.append(Compartment(
            name=str(entry["name"]), kind=str(entry.get("kind", "void")),
            x0_m=float(entry["x0_m"]), x1_m=float(entry["x1_m"]),
            z0_m=float(entry["z0_m"]), z1_m=float(entry["z1_m"])))
    db_top = float(block.get("double_bottom_top_m", max(beam_m / 20.0, 1.0)))
    return Arrangement(compartments=tuple(comps), lpp_m=lpp_m,
                       depth_m=depth_m, beam_m=beam_m,
                       double_bottom_top_m=db_top,
                       source="task-book arrangement block")


def write_arrangement_chart(arrangement: Arrangement, path,
                            title: str = "") -> Path:
    """Render side view + deck plan schematic to an image file."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    lpp, depth = arrangement.lpp_m, arrangement.depth_m
    fig, (ax_side, ax_plan) = plt.subplots(
        2, 1, figsize=(13.0, 6.4), dpi=150, sharex=True)
    fig.subplots_adjust(left=0.05, right=0.985, top=0.90, bottom=0.08,
                        hspace=0.18)

    kind_color = {"hold": "#dce8f5", "machinery": "#f5ddce",
                  "peak": "#e4f0dc", "tank": "#e4f0dc", "void": "#f0f0f0"}
    for comp in arrangement.compartments:
        color = kind_color.get(comp.kind, "#f0f0f0")
        ax_side.add_patch(Rectangle(
            (comp.x0_m, comp.z0_m), comp.x1_m - comp.x0_m,
            comp.z1_m - comp.z0_m, facecolor=color, edgecolor="#1a3d6d",
            linewidth=0.9))
        width = comp.x1_m - comp.x0_m
        if width > 0.02 * lpp:
            ax_side.text((comp.x0_m + comp.x1_m) / 2.0,
                         (comp.z0_m + comp.z1_m) / 2.0,
                         comp.name, ha="center", va="center", fontsize=7.5,
                         rotation=90 if width < 0.10 * lpp else 0)
    ax_side.add_patch(Rectangle(
        (0.0, 0.0), lpp, arrangement.double_bottom_top_m,
        facecolor="#c9c9c9", edgecolor="#1a3d6d", linewidth=0.9,
        hatch="///"))
    ax_side.text(lpp / 2.0, arrangement.double_bottom_top_m / 2.0,
                 "Double bottom", ha="center", va="center", fontsize=8)
    ax_side.add_patch(Rectangle((0.0, 0.0), lpp, depth, fill=False,
                                edgecolor="black", linewidth=1.6))
    ax_side.plot([0.0, lpp], [0.0, 0.0], color="black", linewidth=2.4)
    ax_side.set_ylabel("z above keel (m)", fontsize=9)
    ax_side.set_ylim(-0.02 * depth, depth * 1.06)
    ax_side.set_title("SIDE VIEW (schematic)", fontsize=10, loc="left")

    hatch_breadth = 0.62 * arrangement.beam_m
    for comp in arrangement.compartments:
        if comp.kind != "hold":
            continue
        ax_plan.add_patch(Rectangle(
            (comp.x0_m, (arrangement.beam_m - hatch_breadth) / 2.0),
            comp.x1_m - comp.x0_m, hatch_breadth, facecolor="#dce8f5",
            edgecolor="#1a3d6d", linewidth=0.9, linestyle="--"))
        ax_plan.text((comp.x0_m + comp.x1_m) / 2.0, arrangement.beam_m / 2.0,
                     comp.name.replace("Cargo ", ""),
                     ha="center", va="center", fontsize=7.5)
    ax_plan.add_patch(Rectangle((0.0, 0.0), lpp, arrangement.beam_m,
                                fill=False, edgecolor="black",
                                linewidth=1.6))
    ax_plan.set_ylabel("y (m)", fontsize=9)
    ax_plan.set_xlabel("x from AP (m)", fontsize=9)
    ax_plan.set_ylim(-0.05 * arrangement.beam_m,
                     arrangement.beam_m * 1.05)
    ax_plan.set_title("DECK PLAN (hatches, schematic)", fontsize=10,
                      loc="left")
    for comp in arrangement.compartments:
        for ax in (ax_side, ax_plan):
            if comp.kind == "hold":
                continue
            ax.axvline(comp.x0_m, color="#888888", linewidth=0.6)
    fig.suptitle((title + " — " if title else "")
                 + "general arrangement SCHEMATIC (declared layout, "
                   "not hull lines)",
                 fontsize=12, fontweight="bold")
    out = Path(path)
    fig.savefig(out)
    plt.close(fig)
    return out


def export_arrangement_dxf(arrangement: Arrangement, path) -> Path:
    """Export the same layout to a layered DXF (tasks 2.4 convention).

    Layers: GA-SIDE / GA-PLAN geometry, GA-LABELS text, GA-DB the
    double-bottom plate.
    """
    import ezdxf

    doc = ezdxf.new("R2010")
    doc.units = ezdxf.units.M
    msp = doc.modelspace()
    for layer, aci in (("GA-SIDE", 7), ("GA-PLAN", 5), ("GA-DB", 8),
                       ("GA-LABELS", 3)):
        doc.layers.add(layer, color=aci)

    lpp, depth, beam = (arrangement.lpp_m, arrangement.depth_m,
                        arrangement.beam_m)

    def side_rect(comp, layer):
        msp.add_lwpolyline(
            [(comp.x0_m, comp.z0_m), (comp.x1_m, comp.z0_m),
             (comp.x1_m, comp.z1_m), (comp.x0_m, comp.z1_m)],
            close=True, dxfattribs={"layer": layer})
        msp.add_text(comp.name, height=depth * 0.018,
                     dxfattribs={"layer": "GA-LABELS"}).set_placement(
            ((comp.x0_m + comp.x1_m) / 2.0,
             (comp.z0_m + comp.z1_m) / 2.0),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    msp.add_lwpolyline([(0.0, 0.0), (lpp, 0.0), (lpp, depth), (0.0, depth)],
                       close=True, dxfattribs={"layer": "GA-SIDE"})
    db = arrangement.double_bottom_top_m
    msp.add_lwpolyline([(0.0, 0.0), (lpp, 0.0), (lpp, db), (0.0, db)],
                       close=True, dxfattribs={"layer": "GA-DB"})
    for comp in arrangement.compartments:
        side_rect(comp, "GA-SIDE")

    y0 = (beam - 0.62 * beam) / 2.0
    y1 = y0 + 0.62 * beam
    for comp in arrangement.compartments:
        if comp.kind == "hold":
            msp.add_lwpolyline(
                [(comp.x0_m, y0), (comp.x1_m, y0), (comp.x1_m, y1),
                 (comp.x0_m, y1)], close=True,
                dxfattribs={"layer": "GA-PLAN"})
            msp.add_text(comp.name, height=beam * 0.05,
                         dxfattribs={"layer": "GA-LABELS"}).set_placement(
                ((comp.x0_m + comp.x1_m) / 2.0, beam / 2.0),
                align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    offset = depth + 0.25 * beam
    msp.add_lwpolyline([(0.0, offset), (lpp, offset), (lpp, offset + beam),
                        (0.0, offset + beam)], close=True,
                       dxfattribs={"layer": "GA-PLAN"})
    out = Path(path)
    doc.saveas(out)
    return out
