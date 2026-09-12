"""Drawing and report outputs.

Renders engineering deliverables from computed results.  Task 2.4 adds
the lines-plan three-view drawing (body plan / sheer / half-breadth
plan) with the three views in the house black-on-white engineering
style, plus offsets-table CSV export.

The drawing consumes the RAW tabulated grid (25 stations incl. half
stations, ALL eight data columns from the baseline tangent up to the
1.50 T waterline) — every scrap of shape information the source table
carries.  Curves are connected with a hand-written Fritsch-Carlson
monotone cubic (PCHIP): exact at the offsets, fair between them, no
scipy dependency (AGENTS.md §8).

See AGENTS.md §8 (third-party packages limited to numpy, matplotlib,
ezdxf, pyyaml, pytest).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .geometry import OffsetsTable

#: tabulated waterline fractions of the source table
_DRAUGHT_FRACTIONS = (0.075, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50)

#: labels for those fractions on the half-breadth plan
_WL_LABELS = {0.075: "0.075T", 0.25: "0.25T", 0.5: "0.50T", 0.75: "0.75T",
              1.0: "DWL", 1.25: "1.25T", 1.5: "1.50T"}


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
    Path(path).write_text(text, encoding="utf-8", newline="")
    return text


def pchip(x: np.ndarray, y: np.ndarray, factor: int = 8) -> tuple:
    """Fritsch–Carlson monotone cubic interpolation, dense output.

    Passes exactly through every data point and connects the points
    with C1 arcs that do not overshoot between them — the drawing-board
    definition of a fair line: exact at the offsets, fair between them.

    Returns (xq, yq) with `factor` sub-intervals per original segment.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = np.concatenate(([True], np.diff(x) > 0.0))
    x, y = x[keep], y[keep]          # drop duplicated abscissae
    if y.size < 3:                   # too few points: fall back to linear
        xq = np.linspace(x[0], x[-1], (max(y.size - 1, 1)) * factor + 1)
        return xq, np.interp(xq, x, y)
    h = np.diff(x)
    delta = np.diff(y) / h

    m = np.empty_like(y)
    for k in range(1, y.size - 1):
        if delta[k - 1] * delta[k] <= 0.0:
            m[k] = 0.0
        else:
            w1 = 2.0 * h[k - 1] + h[k]
            w2 = h[k - 1] + 2.0 * h[k]
            m[k] = (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k])
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
    """Dense (half-breadth, height) pairs of one station section."""
    nz = np.nonzero(y > 1e-12)[0]
    if nz.size < 3:
        return y, z
    i0, i1 = nz[0], nz[-1]
    yq, zq = pchip(y[i0:i1 + 1], z[i0:i1 + 1], factor=factor)
    if i0 > 0:
        yq = np.concatenate(([0.0], yq))
        zq = np.concatenate(([z[i0 - 1]], zq))
    return yq, zq


def _buttock_height(y_col: np.ndarray, heights: np.ndarray,
                    target: float) -> float:
    """Height where one station's section is ``target`` wide, m.

    Convention: the TOPMOST crossing wins.  A bulbous section is wider
    at the bulb than at the neck above it, so half-breadths are NOT
    monotone in height and a section can cross the target more than
    once; the sheer-view buttock is the visible upper limit of the
    offset line, i.e. the highest intersection.  Returns 0.0 when the
    section is at least ``target`` wide at its lowest tabulated level
    (the offset line runs on the shell, effectively along the flat
    bottom), and NaN when the section never reaches ``target`` or has
    no usable (finite) entries.
    """
    m = ~np.isnan(y_col)
    if m.sum() < 1:
        return float("nan")
    z, y = heights[m], y_col[m]
    if target <= y.min() + 1e-12:
        return 0.0          # whole section wider: line runs on the bottom
    if target > y.max():
        return float("nan")
    for k in range(y.size - 1, 0, -1):      # topmost crossing first
        if y[k - 1] < target <= y[k] or y[k] < target <= y[k - 1]:
            # linear interpolation between the two bracketing levels
            z0, z1, y0, y1 = z[k - 1], z[k], y[k - 1], y[k]
            return float(z0 + (target - y0) * (z1 - z0) / (y1 - y0))
    return float("nan")


def _dense_buttock(x: np.ndarray, z_at: np.ndarray, factor: int = 6):
    """Dense (x, z) pairs of one buttock line over its valid span."""
    valid = ~np.isnan(z_at)
    if valid.sum() < 3:
        return x, z_at
    i0, i1 = int(np.argmax(valid)), x.size - 1 - int(np.argmax(valid[::-1]))
    return pchip(x[i0:i1 + 1], z_at[i0:i1 + 1], factor=factor)


def draw_lines_plan(raw: dict, path: str, *,
                    title: str = "Lines plan",
                    dpi: int = 300,
                    wl_polylines: list | None = None,
                    sec_polylines: list | None = None) -> str:
    """Draw the classic three-view lines plan as a monochrome PNG.

    ``raw`` is the drawing-grade grid from
    ``openhull.geometry.load_raw_offsets`` (25 tabulated stations
    including half stations, all seven waterline columns plus the
    baseline tangent) — optionally shifted by a Lackenby transform by
    interpolating each column at ``stations - dx`` beforehand.

    Body plan upper left (fore body right / aft body left of the
    centreline), sheer view with 25/50/75 % buttock lines upper right,
    half-breadth plan at the bottom (waterlines above the DWL dashed).
    Station numbering: 0 = AP, 20 = FP.  Returns the written path.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.asarray(raw["stations"], dtype=float)
    heights = np.asarray(raw["heights"], dtype=float)
    yw = np.asarray(raw["half_breadths"], dtype=float)
    lpp = float(x[-1])
    # locate the design waterline by its fraction, never by column
    # position (dense grids have different layer counts)
    fr = raw.get("fractions")
    if fr is not None:
        i_dwl = int(np.argmin(np.abs(np.asarray(fr, dtype=float) - 1.0)))
    else:
        i_dwl = 5
    z_top = float(heights[i_dwl])        # 1.00 T = design waterline
    z_max = float(heights[-1])           # top drawn waterline
    half = float(np.nanmax(yw[:, i_dwl]))  # max half breadth on the DWL
    mid = 0.5 * (lpp)                    # midship
    xi = x / lpp

    fig = plt.figure(figsize=(15.0, 8.0), dpi=dpi, facecolor="white")
    gs = fig.add_gridspec(
        2, 2,
        width_ratios=[1.0, 1.9],
        height_ratios=[1.15, 1.0],
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

    # ---- body plan (upper left): every station, spline-faired ----
    for i in range(1, x.size - 1):
        if sec_polylines is not None:
            z_sec, y_sec = sec_polylines[i]
            if z_sec.size == 0:
                continue
            side = 1.0 if x[i] >= lpp / 2 else -1.0
            ax_body.plot(side * y_sec, z_sec, color="black",
                         linewidth=0.8)
            continue
        y_sec, z_sec = _dense_section(heights, yw[i])
        side = 1.0 if xi[i] >= 0.5 else -1.0
        ax_body.plot(side * y_sec, z_sec, color="black", linewidth=0.8)
    ax_body.axhline(z_top, color="black", linewidth=1.1)
    ax_body.axvline(0.0, color="black", linewidth=0.7)
    for h in heights[1:-1]:   # waterline reference lines
        ax_body.axhline(h, color="0.78", linewidth=0.35, linestyle=":")
    ax_body.annotate("DWL", (-half * 1.02, z_top), xytext=(2, 2),
                     textcoords="offset points", fontsize=6.5,
                     color="black", ha="left")
    ax_body.set_aspect("equal")
    ax_body.set_xlim(-half * 1.10, half * 1.10)
    ax_body.set_ylim(-z_top * 0.05, z_max * 1.06)
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
    ax_sheer.plot([0.0, 0.0], [0.0, float(yw[0, -1])],
                  color="black", linewidth=1.0)
    ax_sheer.plot([lpp, lpp], [0.0, float(yw[-1, -1])],
                  color="black", linewidth=1.0)
    for frac, ls in ((0.25, (0, (5, 2))), (0.50, (0, (2, 1.5))),
                     (0.75, (0, (7, 2, 1, 2)))):
        target = frac * half
        z_at = np.array([_buttock_height(yw[i], heights, target)
                         for i in range(x.size)])
        xq, zq = _dense_buttock(x, z_at)
        ax_sheer.plot(xq, zq, color="black", linewidth=0.8, linestyle=ls)
        if not np.isnan(z_at[-1]):
            ax_sheer.annotate(f"{int(frac * 100)}%", (lpp, z_at[-1]),
                              xytext=(4, 0), textcoords="offset points",
                              fontsize=6.5, color="black")
    ax_sheer.set_xlim(-lpp * 0.02, lpp * 1.06)
    ax_sheer.set_ylim(-z_top * 0.08, z_max * 1.10)
    ax_sheer.set_title("Sheer view  (buttocks 25/50/75 % B/2)",
                       fontsize=9.5, color="black", pad=4)
    ax_sheer.set_xlabel("x from AP (m)", fontsize=8)
    ax_sheer.set_ylabel("height above keel (m)", fontsize=8)

    # ---- half-breadth plan (bottom right): all tabulated waterlines ----
    x_lab = 0.90 * lpp
    if wl_polylines is not None:
        for j, (u, v) in enumerate(wl_polylines):
            if u.size == 0:
                continue
            h = heights[j]
            dashed = h > z_top + 1e-9
            ax_plan.plot(u, v, color="black",
                         linewidth=0.9 if not dashed else 0.55,
                         linestyle="-" if not dashed else (0, (3, 2)))
        for frac in (0.075, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5):
            j = int(np.argmin(np.abs(heights - frac * z_top)))
            u_l, v_l = wl_polylines[j]
            if u_l.size == 0:
                continue
            x_lab_j = min(x_lab, float(u_l[-1]) - 2.0)
            y_lab = float(np.interp(x_lab_j, u_l, v_l))
            if np.isnan(y_lab) or y_lab <= 0.0:
                continue
            ax_plan.annotate(_WL_LABELS[frac], (x_lab_j, y_lab),
                             xytext=(0, 3), textcoords="offset points",
                             fontsize=6.5, color="black", ha="center")
    else:
        for j in range(1, heights.size):
            h = heights[j]
            xq, yq = pchip(x, yw[:, j], factor=8)
            dashed = h > z_top + 1e-9        # above-waterline layers
            ax_plan.plot(xq, yq, color="black",
                         linewidth=0.9 if not dashed else 0.6,
                         linestyle="-" if not dashed else (0, (3, 2)))
            y_lab = float(np.nanmax(yq))
            frac = round(h / z_top, 3)
            label = _WL_LABELS.get(frac, f"{frac:.2f}T")
            ax_plan.annotate(label, (x_lab, y_lab), xytext=(0, 3),
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
                              "waterlines above DWL dashed.",
                              "Axes scales differ between views.")):
        ax_note.annotate(line, (0.03, 0.90 - 0.13 * k), fontsize=7.5,
                         color="black", ha="left", va="top")

    fig.suptitle(title, fontsize=11, color="black", y=0.975)
    fig.savefig(path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return path
