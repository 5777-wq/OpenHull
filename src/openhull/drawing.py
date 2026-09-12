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


def pchip(x: np.ndarray, y: np.ndarray, factor: int = 8) -> tuple:
    """Fritsch–Carlson monotone cubic interpolation, dense output.

    Passes exactly through every data point and connects the points
    with C1 arcs that do not overshoot between them — the drawing-board
    definition of a fair line: exact at the offsets, fair between them.
    No scipy dependency (AGENTS.md §8).

    Returns (xq, yq) with `factor` sub-intervals per original segment.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = np.concatenate(([True], np.diff(x) > 0.0))
    x, y = x[keep], y[keep]          # drop duplicated abscissae
    h = np.diff(x)
    delta = np.diff(y) / h

    m = np.empty_like(y)
    # interior tangents: weighted harmonic mean where the slope sign
    # holds, zero at local extrema (keeps the curve from overshooting)
    for k in range(1, y.size - 1):
        if delta[k - 1] * delta[k] <= 0.0:
            m[k] = 0.0
        else:
            w1 = 2.0 * h[k - 1] + h[k]
            w2 = h[k - 1] + 2.0 * h[k]
            m[k] = (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k])
    # end tangents: one-sided three-point formula, clamped to the sign
    # of the adjacent slope and limited to 3*delta (FC paper eqs.)
    m[0] = ((2.0 * h[0] + h[1]) * delta[0] - h[1] * delta[1]) \
        / (h[0] + h[1])
    if m[0] * delta[0] <= 0.0:
        m[0] = 0.0
    elif delta[0] * delta[1] <= 0.0 and abs(m[0]) > abs(3.0 * delta[0]):
        m[0] = 3.0 * delta[0]
    m[-1] = ((2.0 * h[-1] + h[-2]) * delta[-1] - h[-2] * delta[-2]) \
        / (h[-1] + h[-2])
    if m[-1] * delta[-1] <= 0.0:
        m[-1] = 0.0
    elif delta[-1] * delta[-2] <= 0.0 and \
            abs(m[-1]) > abs(3.0 * delta[-1]):
        m[-1] = 3.0 * delta[-1]

    xq = np.empty(y.size + (y.size - 1) * (factor - 1))
    yq = np.empty_like(xq)
    xq[0], yq[0] = x[0], y[0]
    pos = 1
    for k in range(y.size - 1):
        t = np.linspace(0.0, 1.0, factor + 1)[1:]
        t2, t3 = t * t, t * t * t
        h00 = 2.0 * t3 - 3.0 * t2 + 1.0
        h10 = t3 - 2.0 * t2 + t
        h01 = -2.0 * t3 + 3.0 * t2
        h11 = t3 - t2
        xq[pos:pos + factor] = x[k] + t * h[k]
        yq[pos:pos + factor] = (h00 * y[k] + h10 * m[k] * h[k]
                                + h01 * y[k + 1] + h11 * m[k + 1] * h[k])
        pos += factor
    return xq, yq


def _dense_section(z: np.ndarray, y: np.ndarray, factor: int = 5):
    """Dense (half-breadth, height) pairs of one station section.

    Transom-stern sections have a genuine gap (no hull) between keel
    and the lower tangency: the zero run at the bottom is kept as a
    vertical rise, the curved part above it is spline-faired."""
    nz = np.nonzero(y > 1e-12)[0]
    if nz.size < 3:
        return y, z
    i0, i1 = nz[0], nz[-1]
    yq, zq = pchip(y[i0:i1 + 1], z[i0:i1 + 1], factor=factor)
    if i0 > 0:
        yq = np.concatenate(([0.0], yq))
        zq = np.concatenate(([z[i0 - 1]], zq))
    return yq, zq


def _dense_buttock(x: np.ndarray, z_at: np.ndarray, factor: int = 6):
    """Dense (x, z) pairs of one buttock line over its valid span.

    A buttock exists only where the sections actually reach the target
    half-breadth; outside that span the line is not drawn (the NaN
    behaviour of the tabulated data is preserved)."""
    valid = ~np.isnan(z_at)
    if valid.sum() < 3:
        return x, z_at
    i0, i1 = np.argmax(valid), x.size - 1 - np.argmax(valid[::-1])
    xq, zq = pchip(x[i0:i1 + 1], z_at[i0:i1 + 1], factor=factor)
    return xq, zq


def _buttock_heights(table: OffsetsTable, target: float) -> np.ndarray:
    """Height of one buttock line at every station.

    A section already WIDER than the target at its base puts the
    buttock on the baseline (z = 0); a section that never reaches the
    target breadth has no buttock there (NaN, line not drawn).
    """
    z_at = np.full(table.stations.size, np.nan)
    for i in range(table.stations.size):
        y_sec = table.half_breadths[i]
        if target <= y_sec[0] + 1e-12:
            z_at[i] = 0.0
        elif target <= y_sec[-1]:
            z_at[i] = float(np.interp(target, y_sec, table.waterlines))
    return z_at


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

    # ---- body plan (upper left): spline-faired sections ----
    for i in range(1, x.size - 1):
        y_sec, z_sec = _dense_section(table.waterlines,
                                      table.half_breadths[i])
        side = 1.0 if i >= mid else -1.0
        ax_body.plot(side * y_sec, z_sec, color="black", linewidth=0.8)
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
    ax_sheer.annotate("DWL", (0.35 * lpp, z_top), xytext=(0, 3),
                      textcoords="offset points", fontsize=6.5,
                      color="black", ha="center")
    ax_sheer.plot([0.0, 0.0], [0.0, float(table.half_breadths[0, -1])],
                  color="black", linewidth=1.0)
    ax_sheer.plot([lpp, lpp], [0.0, float(table.half_breadths[-1, -1])],
                  color="black", linewidth=1.0)
    for frac, ls in ((0.25, (0, (5, 2))), (0.50, (0, (2, 1.5))),
                     (0.75, (0, (7, 2, 1, 2)))):
        z_at = _buttock_heights(table, frac * half)
        xq, zq = _dense_buttock(x, z_at)
        ax_sheer.plot(xq, zq, color="black", linewidth=0.8, linestyle=ls)
        if not np.isnan(z_at[-1]):
            ax_sheer.annotate(f"{int(frac * 100)}%", (lpp, z_at[-1]),
                              xytext=(4, 0), textcoords="offset points",
                              fontsize=6.5, color="black")
    ax_sheer.set_xlim(-lpp * 0.02, lpp * 1.06)
    ax_sheer.set_ylim(-z_top * 0.08, z_top * 1.12)
    ax_sheer.set_title("Sheer view  (buttocks 25/50/75 % B/2)",
                       fontsize=9.5, color="black", pad=4)
    ax_sheer.set_xlabel("x from AP (m)", fontsize=8)
    ax_sheer.set_ylabel("height above keel (m)", fontsize=8)

    # ---- half-breadth plan (bottom right): faired waterlines ----
    xq_long, _ = pchip(x, yw[:, -1], factor=8)   # dense x along the ship
    x_lab = 0.90 * lpp   # annotations where the waterlines fan apart
    for j, h in enumerate(heights):
        _xq, yq = pchip(x, yw[:, j], factor=8)
        ax_plan.plot(xq_long, yq, color="black", linewidth=0.9)
        y_lab = float(np.interp(x_lab, xq_long, yq))
        ax_plan.annotate(_WL_LABELS[round(h / z_top, 3)],
                         (x_lab, y_lab), xytext=(0, 3),
                         textcoords="offset points", fontsize=6.5,
                         color="black", ha="center")
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
