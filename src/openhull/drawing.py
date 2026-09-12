"""Drawing and report outputs.

Renders engineering deliverables from computed results.  Task 2.4 adds
the lines-plan three-view drawing (body plan / sheer / half-breadth
plan) with the three views geometrically aligned — grid cells sized to
the data aspect ratios, equal aspect everywhere — in the house
black-on-white engineering style, plus offsets-table CSV export.

Only the TABULATED waterline fractions of the source table (0.075 ...
1.00 T) are drawn, so the picture shows the offsets themselves rather
than resampling artefacts of the equal-zeta grid.

Hydrostatic/stability curve plots and DXF output follow in later tasks.

See AGENTS.md §8 (third-party packages limited to numpy, matplotlib,
ezdxf, pyyaml, pytest).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .geometry import OffsetsTable

#: tabulated waterline fractions of the source table
_DRAUGHT_FRACTIONS = (0.075, 0.25, 0.50, 0.75, 1.00)

#: labels for those fractions on the half-breadth plan
_WL_LABELS = {1.0: "DWL", 0.75: "0.75T", 0.5: "0.50T", 0.25: "0.25T",
              0.075: "0.075T"}


def save_offsets_csv(table: OffsetsTable, path: str) -> str:
    """Export an offsets table as absolute half-breadths in metres.

    First column: station x from AP (m); one column per waterline
    (header = height above keel, m).
    """
    header = ",".join(["station_m"] + [f"wl_{z:.3f}m"
                                       for z in table.waterlines])
    lines = [header]
    for i, x in enumerate(table.stations):
        row = ",".join([f"{x:.3f}"] + [f"{y:.4f}"
                                       for y in table.half_breadths[i]])
        lines.append(row)
    text = "\n".join(lines) + "\n"
    from pathlib import Path
    target = Path(path)
    target.write_text(text, encoding="utf-8", newline="")
    return text


def _waterlines_at(table: OffsetsTable) -> tuple:
    """(heights, half-breadth matrix) at the tabulated draft fractions,
    interpolated from the equal-zeta resampled grid per station."""
    z_top = float(table.waterlines[-1])
    heights = [f * z_top for f in _DRAUGHT_FRACTIONS]
    cols = []
    for h in heights:
        cols.append([float(np.interp(h, table.waterlines, row))
                     for row in table.half_breadths])
    return heights, np.column_stack(cols)


def draw_lines_plan(table: OffsetsTable, path: str, *,
                    title: str = "Lines plan",
                    dpi: int = 300) -> str:
    """Draw the classic three-view lines plan as a monochrome PNG.

    Body plan upper left (fore body right / aft body left of the
    centreline), sheer view with 25/50/75 % buttock lines upper right,
    half-breadth plan with the tabulated waterlines at the bottom; the
    three views are geometrically aligned.  Station numbering on the
    plan: 0 = AP, 20 = FP.  Returns the written path.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = table.stations
    z_top = float(table.waterlines[-1])
    lpp, beam = table.lpp, table.beam
    mid = x.size // 2
    half = beam / 2.0
    heights, yw = _waterlines_at(table)

    # The body plan keeps a 1:1 aspect (section shapes must not distort);
    # the sheer and half-breadth views decouple the axis scales the way
    # full-size drafting sheets do (dimensions are read off the axes).
    fig = plt.figure(figsize=(15.0, 8.0), dpi=dpi, facecolor="white")
    gs = fig.add_gridspec(
        2, 2,
        width_ratios=[1.0, 1.9],
        height_ratios=[1.1, 1.0],
        left=0.06, right=0.985, top=0.92, bottom=0.07,
        wspace=0.16, hspace=0.24,
    )
    ax_body = fig.add_subplot(gs[0, 0])
    ax_sheer = fig.add_subplot(gs[0, 1])
    ax_plan = fig.add_subplot(gs[1, 1])
    ax_note = fig.add_subplot(gs[1, 0])   # notes under the body plan

    for ax in (ax_body, ax_sheer, ax_plan):
        ax.set_facecolor("white")
        ax.grid(True, color="0.87", linewidth=0.4, linestyle="--")
        for spine in ax.spines.values():
            spine.set_color("black")
            spine.set_linewidth(0.7)
        ax.tick_params(colors="black", labelsize=7, length=2.5)

    # ---- body plan (upper left) ----
    for i in range(1, x.size - 1):
        side = 1.0 if i >= mid else -1.0
        ax_body.plot(side * table.half_breadths[i], table.waterlines,
                     color="black", linewidth=0.8)
    ax_body.axhline(z_top, color="black", linewidth=1.1)
    ax_body.axvline(0.0, color="black", linewidth=0.8)
    for h in heights[:-1]:   # waterline reference lines
        ax_body.axhline(h, color="0.75", linewidth=0.4, linestyle=":")
    ax_body.annotate("DWL", (-half * 1.02, z_top), xytext=(2, 2),
                     textcoords="offset points", fontsize=6.5,
                     color="black", ha="left")
    ax_body.set_aspect("equal")
    ax_body.set_xlim(-half * 1.10, half * 1.10)
    ax_body.set_ylim(-z_top * 0.05, z_top * 1.06)
    ax_body.set_title("Body plan  (fore right / aft left)",
                      fontsize=9.5, color="black", pad=4)
    ax_body.set_xlabel("half breadth (m)", fontsize=8)
    ax_body.set_ylabel("height above keel (m)", fontsize=8)

    # ---- sheer view (upper right): DWL, perpendiculars, buttocks ----
    ax_sheer.plot([0.0, lpp], [z_top, z_top], color="black",
                  linewidth=1.2)
    ax_sheer.plot([0.0, 0.0], [0.0, float(table.half_breadths[0, -1])],
                  color="black", linewidth=1.0)
    ax_sheer.plot([lpp, lpp], [0.0, float(table.half_breadths[-1, -1])],
                  color="black", linewidth=1.0)
    for frac, ls in ((0.25, (0, (5, 2))), (0.50, (0, (2, 1.5))),
                     (0.75, (0, (7, 2, 1, 2)))):
        target = frac * half
        zs = [float(np.interp(target, table.half_breadths[i],
                              table.waterlines,
                              left=np.nan, right=np.nan))
              for i in range(x.size)]
        ax_sheer.plot(x, zs, color="black", linewidth=0.8, linestyle=ls)
        if not np.isnan(zs[-1]):
            ax_sheer.annotate(f"{int(frac * 100)}%", (lpp, zs[-1]),
                              xytext=(4, 0), textcoords="offset points",
                              fontsize=6.5, color="black")
    ax_sheer.set_xlim(-lpp * 0.02, lpp * 1.06)
    ax_sheer.set_ylim(-z_top * 0.08, z_top * 1.12)
    ax_sheer.set_title("Sheer view  (buttocks 25/50/75 % B/2)",
                       fontsize=9.5, color="black", pad=4)
    ax_sheer.set_xlabel("x from AP (m)", fontsize=8)
    ax_sheer.set_ylabel("height above keel (m)", fontsize=8)

    # ---- half-breadth plan (bottom right): tabulated waterlines ----
    x_lab = 0.82 * lpp   # annotations where the waterlines fan apart
    for j, h in enumerate(heights):
        ax_plan.plot(x, yw[:, j], color="black", linewidth=0.9)
        y_lab = float(np.interp(x_lab, x, yw[:, j]))
        ax_plan.annotate(_WL_LABELS[round(h / z_top, 3)], (x_lab, y_lab),
                         xytext=(0, 3), textcoords="offset points",
                         fontsize=6.5, color="black", ha="center")
    ax_plan.axhline(half, color="black", linewidth=0.5)
    ax_plan.set_xlim(-lpp * 0.02, lpp * 1.08)
    ax_plan.set_ylim(-half * 0.14, half * 1.12)
    ax_plan.set_title("Half-breadth plan  (waterlines, station 0 = AP)",
                      fontsize=9.5, color="black", pad=4)
    ax_plan.set_xlabel("x from AP (m)", fontsize=8)
    ax_plan.set_ylabel("half breadth (m)", fontsize=8)

    # ---- notes (bottom left, under the body plan) ----
    ax_note.axis("off")
    ax_note.set_xlim(0.0, 1.0)
    ax_note.set_ylim(0.0, 1.0)
    for k, line in enumerate(("Station numbering: 0 = AP, 20 = FP.",
                              "All dimensions in metres, moulded surface;",
                              "lines drawn to the design waterline.",
                              "Axes scales differ between views.")):
        ax_note.annotate(line, (0.03, 0.90 - 0.13 * k), fontsize=7.5,
                         color="black", ha="left", va="top")

    fig.suptitle(title, fontsize=11, color="black", y=0.975)
    fig.savefig(path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return path
