"""B-spline surface skin over the offsets table (lines-plan quick win).

The drawing-grade route to fair-looking lines plans: fit a bicubic
(degree 3 x 3) interpolating B-spline surface through the tabulated
offsets grid (stations x waterlines, moulded half-breadths), then
RE-CUT the dense stations and waterlines from that skin instead of
connecting the sparse table points directly — the drawing becomes a
projection of a smooth surface, the way commercial tools produce
lines plans.

Constitution provenance (AGENTS.md section 5, entry 2026-10-05):
the fitting/evaluation engine is geomdl (MIT, NURBS-Python), pinned
``>=5`` — the capytaine/ezdxf dependency precedent.  It supplies
GEOMETRY ONLY (the interpolating surface and its evaluation); it
replaces no whitelisted naval formula and every hydrostatic quantity
stays in the table layer's Simpson chain.  The hand-transcribed
NURBS Book route is deferred until the book is legally obtained.
Formula content implemented here and declared in the same entry: the
classical plane-curve curvature kappa = |y''| / (1 + y'^2)^(3/2) of a
sampled waterline, used as a DIAGNOSTIC verdict only — the
difference-based fairness checks of task 2.6 remain the acceptance
gate.

Anchors (pinned by tests/test_surface.py, recorded in VALIDATION.md):
(a) knot reproduction — the surface returns every tabulated offset
exactly (gate 1e-6 x B/2); (b) hydrostatics round-trip — the dense
re-cut does not change the ship (displacement volume / Cb / LCB / KM
at the design draft inside the table layer's anchor tolerances);
(c) physical-coordinate re-sampling by bisection on the surface's own
x(u), z(v) coordinates, which geomdl's non-uniform parameterisation
makes necessary (probe 2026-10-05: grid knots do NOT sit at uniform
parameters, but x depends only on u and z only on v to 1e-15).

Declared approximation: the skin interpolates the tabulated range
only — no extrapolation above the top waterline or beyond AP/FP
(refused, AGENTS.md section 6); small negative cubic undershoots at
keel/ends where the table itself reads zero are clipped to zero.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import OffsetsTable
from .spec import SpecValidationError

__all__ = [
    "OffsetSurface",
    "SURFACE_DEGREE",
    "fit_offsets_surface",
    "dense_offsets_table",
    "curvature_report",
    "raw_offsets_for_drawing",
]

#: bicubic skin (§5 entry 2026-10-05); both grid directions need more
#: tabulated rows/columns than the degree
SURFACE_DEGREE = 3


@dataclass(frozen=True)
class OffsetSurface:
    """The fitted skin plus its parameter mapping (JSON-free handle).

    ``u_nodes`` / ``v_nodes`` are the surface parameters of the
    tabulated stations / waterlines, recovered by inverting the
    surface's own x(u) / z(v) coordinates (geomdl parameterises by
    arc-type averaging, not by grid index).  ``knot_max_abs_err`` is
    anchor (a): the largest half-breadth mismatch at the knots.
    """

    surface: object
    table: OffsetsTable
    u_nodes: np.ndarray
    v_nodes: np.ndarray
    knot_max_abs_err: float


def _invert_monotone(surface, values: np.ndarray, *, axis: str,
                     sample: int = 3001) -> np.ndarray:
    """Parameters whose x(u) [z(v)] hit ``values`` (anchor (c)).

    The surface's coordinate along ``axis`` depends only on that
    parameter (tensor separability, probe 2026-10-05: 3.6e-15 spread)
    and is monotone because the tabulated stations / waterlines are
    strictly increasing.  Coarse lookup + bisection refinement; a
    missed target (non-monotone span) is refused, not extrapolated.
    """
    ts = np.linspace(0.0, 1.0, sample)
    if axis == "u":
        coords = np.array([p[0] for p in
                           surface.evaluate_list([(t, 0.0) for t in ts])])
    else:
        coords = np.array([p[1] for p in
                           surface.evaluate_list([(0.0, t) for t in ts])])
    lo_t = np.interp(values, coords, ts)
    out = np.empty_like(values, dtype=float)
    for k, (target, t0) in enumerate(zip(values, lo_t)):
        lo, hi = float(t0) - 1.0 / sample, float(t0) + 1.0 / sample
        lo, hi = max(0.0, lo), min(1.0, hi)
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            t = mid
            c = (surface.evaluate_list([(t, 0.0)])[0][0] if axis == "u"
                 else surface.evaluate_list([(0.0, t)])[0][1])
            if c < target:
                lo = mid
            else:
                hi = mid
        t = 0.5 * (lo + hi)
        c = (surface.evaluate_list([(t, 0.0)])[0][0] if axis == "u"
             else surface.evaluate_list([(0.0, t)])[0][1])
        if abs(c - target) > 1e-7 * max(1.0, abs(target)):
            raise SpecValidationError(
                f"surface {axis} parameterisation", float(target),
                "a monotone reachable coordinate",
                "the surface coordinate along the requested axis is not "
                "monotone over the tabulated span; the skin refuses to "
                "re-sample rather than extrapolate.")
        out[k] = t
    return out


def fit_offsets_surface(table: OffsetsTable) -> OffsetSurface:
    """Fit the bicubic interpolating skin over one offsets table.

    Anchor (a) is enforced here: the surface must reproduce every
    tabulated half-breadth within 1e-6 x B/2 — a violation means the
    fit is not an interpolation of THIS table and is refused.
    """
    from geomdl import fitting

    stations = np.asarray(table.stations, dtype=float)
    waterlines = np.asarray(table.waterlines, dtype=float)
    y = np.asarray(table.half_breadths, dtype=float)
    if stations.size <= SURFACE_DEGREE or waterlines.size <= SURFACE_DEGREE:
        raise SpecValidationError(
            "offsets grid", (stations.size, waterlines.size),
            f"more than {SURFACE_DEGREE} stations and waterlines",
            f"a degree-{SURFACE_DEGREE} interpolating surface needs at "
            f"least {SURFACE_DEGREE + 1} tabulated rows in each "
            f"direction; this grid is too sparse to skin.")
    points = [[float(stations[i]), float(waterlines[j]), float(y[i, j])]
              for i in range(stations.size)
              for j in range(waterlines.size)]
    surface = fitting.interpolate_surface(
        points, int(stations.size), int(waterlines.size),
        degree_u=SURFACE_DEGREE, degree_v=SURFACE_DEGREE)
    u_nodes = _invert_monotone(surface, stations, axis="u")
    v_nodes = _invert_monotone(surface, waterlines, axis="v")
    ev = surface.evaluate_list(
        [(float(u), float(v)) for u in u_nodes for v in v_nodes])
    fitted = np.array(ev)[:, 2].reshape(stations.size, waterlines.size)
    err = float(np.max(np.abs(fitted - y)))
    gate = 1e-6 * table.beam / 2.0
    if not (err <= gate):
        raise SpecValidationError(
            "surface knot reproduction", err, f"<= {gate:.2e} m",
            "the fitted surface does not pass through the tabulated "
            "offsets; an interpolation that moves the table is a "
            "different ship and is refused.")
    return OffsetSurface(surface=surface, table=table,
                         u_nodes=u_nodes, v_nodes=v_nodes,
                         knot_max_abs_err=err)


def dense_offsets_table(skin: OffsetSurface, *,
                        station_intervals: int = 2,
                        waterline_intervals: int = 2) -> OffsetsTable:
    """Re-cut the skin at dense, uniform-in-coordinates grid lines.

    ``station_intervals = 2`` halves every tabulated station spacing
    (25 tabulated stations -> 49 cut stations).  Simpson parity is
    preserved by construction: odd grid counts in, odd grid counts
    out (intervals are doubled/quadrupled).  Anchor (b) pins that the
    resulting table describes the SAME ship hydrostatically.
    Negative cubic undershoots where the table reads zero (keel ends)
    are clipped to zero — declared, and measured by the tests.
    """
    if station_intervals < 1 or waterline_intervals < 1:
        raise SpecValidationError(
            "dense intervals",
            (station_intervals, waterline_intervals),
            ">= 1 in each direction",
            "the re-cut grid multiples the tabulated spacing; a "
            "sub-unity multiple would thin the table.")
    table = skin.table
    n_s = station_intervals * (np.asarray(table.stations).size - 1) + 1
    n_w = waterline_intervals * (np.asarray(table.waterlines).size - 1) + 1
    stations = np.linspace(0.0, table.lpp, n_s)
    waterlines = np.linspace(
        float(table.waterlines[0]), float(table.waterlines[-1]), n_w)
    us = _invert_monotone(skin.surface, stations, axis="u")
    vs = _invert_monotone(skin.surface, waterlines, axis="v")
    ev = skin.surface.evaluate_list(
        [(float(u), float(v)) for u in us for v in vs])
    y = np.array(ev)[:, 2].reshape(n_s, n_w)
    y = np.clip(y, 0.0, table.beam / 2.0)
    return OffsetsTable(lpp=table.lpp, beam=table.beam,
                        stations=stations, waterlines=waterlines,
                        half_breadths=y)


def curvature_report(table: OffsetsTable) -> dict:
    """Sampled plane-curve curvature diagnostics per waterline.

    For each tabulated waterline y(x): the classical plane-curve
    curvature kappa = |y''| / (1 + y'^2)^(3/2) (AGENTS.md section 5
    entry, 2026-10-05) by central differences, plus the count of
    curvature sign changes (inflections).  A fair waterline shows few
    inflections and no curvature spikes; an unfair one zig-zags in
    curvature.  This is a DIAGNOSTIC: the difference-based
    ``openhull.fairness.check_fairness`` remains the acceptance gate.
    """
    x = np.asarray(table.stations, dtype=float)
    rows = []
    for j, z in enumerate(np.asarray(table.waterlines, dtype=float)):
        y = np.asarray(table.half_breadths[:, j], dtype=float)
        if y.size < 5 or float(np.max(y)) < 0.005 * table.beam:
            # dead rows (keel vicinity): no shape signal, only table
            # quantisation noise — skipped, not counted
            continue
        h1 = x[2:] - x[1:-1]        # forward spacing at the midpoints
        h2 = x[1:-1] - x[:-2]       # backward spacing
        dy = (y[2:] - y[:-2]) / (h1 + h2)
        # non-uniform three-point second difference
        ddy = 2.0 * ((y[2:] - y[1:-1]) / h1
                     - (y[1:-1] - y[:-2]) / h2) / (h1 + h2)
        kappa = np.abs(ddy) / (1.0 + dy * dy) ** 1.5
        sign = np.sign(ddy)
        sign = sign[sign != 0]
        inflections = int(np.sum(sign[1:] * sign[:-1] < 0)) if sign.size else 0
        rows.append({
            "waterline_m": float(z),
            "max_kappa_per_m": float(np.max(kappa)),
            "inflections": inflections,
        })
    return {
        "waterlines": rows,
        "note": ("diagnostic only; the acceptance gate stays "
                 "openhull.fairness.check_fairness (task 2.6)"),
    }


def raw_offsets_for_drawing(table: OffsetsTable,
                            design_draft_m: float) -> dict:
    """Convert an (optionally dense) table to the drawing-grade dict.

    ``openhull.drawing.draw_lines_plan`` /
    ``save_lines_plan_dxf`` consume the ``load_raw_offsets`` dict
    shape; dense grids are located by the ``fractions`` key (height
    over the design draft) exactly as those functions document.  The
    design waterline fraction itself is pinned to 1.0 by clamping the
    nearest row, so the DWL marker lands on the declared draft.
    """
    if not (0.0 < design_draft_m <= float(table.waterlines[-1])):
        raise SpecValidationError(
            "design_draft_m", design_draft_m,
            f"(0, {float(table.waterlines[-1]):.3f}] m",
            "the drawing's design waterline must lie inside the "
            "tabulated span of the skinned table.")
    fractions = np.asarray(table.waterlines, dtype=float) / design_draft_m
    i_dwl = int(np.argmin(np.abs(fractions - 1.0)))
    fractions[i_dwl] = 1.0
    return {
        "stations": np.asarray(table.stations, dtype=float).tolist(),
        "heights": np.asarray(table.waterlines, dtype=float).tolist(),
        "half_breadths":
            np.asarray(table.half_breadths, dtype=float).tolist(),
        "fractions": fractions.tolist(),
    }
