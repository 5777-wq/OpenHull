"""Numerical fairness checks on tabulated hull offsets (plan task 2.5).

Fairness here is a property of the tabulated half-breadths along the
length, judged per waterline.  Two classical signals are used
(first- and second-order differences of the offsets, cf. any text on
lines fairing, e.g. Thornton/DTMB practice described in the DTMB 1712
report the parent offsets come from):

* first differences (``non_monotonic``): a waterline of a conventional
  hull is a single lobe — it rises to its maximum half-breadth and then
  tapers to the stem.  A sustained movement back towards the centreline
  beyond a small tolerance indicates a digitising or drafting error.
  Bulbous bows and sonar domes legitimately break this on LOW waterlines,
  so the check only applies at and above ``monotonic_from_fraction`` of
  the judged depth.

* second differences (``curvature_jump``): on a fair curve the curvature
  (second difference) varies smoothly along the length; an isolated
  spike or step means a kink.  Detection is CONTRAST based: each second
  difference is compared against the median of its immediate neighbours,
  scaled by a robust (MAD) estimate of the row's second-difference
  scatter.  This deliberately does NOT compare against a global mean —
  high-curvature regions (bulb shoulders, quarter lengths) are fair and
  must not trigger alarms.  A dimensionless absolute floor keeps
  pathological single-point spikes from slipping through when the whole
  row is otherwise perfectly smooth.

Scope and honesty notes:

* only the displacement part of the hull is judged.  Rows above
  ``z_limit`` (pass the design draft) carry deck sheer and flare, where
  abrupt changes of breadth along the length are intentional styling;
  they are excluded.
* a waterline row is judged only over its live span (where the offsets
  are positive, plus one zero grid point on each side): the natural end
  of a curve — the stem entry, the rise of floor — is a legitimate
  terminus, and second differences AT the terminus are not evidence of
  unfairness.

Acceptance (plan task 2.5): the digitised Series 60 parent — known
fair, printed in DTMB 1712 Table 7 — must pass with ZERO issues; the
alarms must be shown not to frame the innocent.  The defaults for the
absolute curvature floor were calibrated an order of magnitude above
the maximum contrast measured on that parent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .geometry import OffsetsTable

__all__ = [
    "FairnessIssue",
    "FairnessReport",
    "check_fairness",
]


@dataclass(frozen=True)
class FairnessIssue:
    """One flagged location on one waterline.

    Attributes:
        kind: ``"curvature_jump"`` or ``"non_monotonic"``.
        waterline_z: waterline height above keel, m.
        station_x: station position from AP, m (midpoint of the
            offending interval pair for curvature, first offending
            step for monotonicity).
        metric: measured value, m (second-difference contrast for
            curvature jumps, accumulated reverse movement for
            monotonicity).
        limit: the threshold that was exceeded, m.
        detail: human-readable one-line explanation.
    """

    kind: str
    waterline_z: float
    station_x: float
    metric: float
    limit: float
    detail: str


@dataclass(frozen=True)
class FairnessReport:
    """Result of :func:`check_fairness`.

    Attributes:
        issues: flagged locations, empty when the table is fair.
        n_stations: grid size judged, length direction.
        n_waterlines_checked: waterline rows inside the judged depth.
        z_limit: depth up to which rows were judged, m.
        max_contrast: largest |local second-difference contrast| seen,
            dimensionless (scaled by Lpp^2/B) — context for the
            thresholds, not an alarm by itself.
        parallel_segments: detected parallel-middle-body runs as
            ``(waterline_z, x_from, x_to)`` tuples, m.
    """

    issues: tuple[FairnessIssue, ...]
    n_stations: int
    n_waterlines_checked: int
    z_limit: float
    max_contrast: float
    parallel_segments: tuple[tuple[float, float, float], ...]

    @property
    def ok(self) -> bool:
        """True when no issue was raised (the table is judged fair)."""
        return not self.issues

    def summary(self) -> str:
        """Multi-line human-readable verdict."""
        head = (f"fairness: {len(self.issues)} issue(s) over "
                f"{self.n_waterlines_checked} waterlines x "
                f"{self.n_stations} stations (z <= {self.z_limit:g} m)")
        if self.ok:
            return head + " — OK"
        lines = [head]
        for issue in self.issues:
            lines.append(
                f"  [{issue.kind}] z={issue.waterline_z:g} m "
                f"x={issue.station_x:g} m: {issue.detail}"
            )
        return "\n".join(lines)


def _live_span(row: np.ndarray) -> tuple[int, int] | None:
    """Indices (first, last) of a row's live span, one zero outside.

    The span covers all points with positive half-breadth plus a single
    zero grid point on each side when present, so the curve terminus is
    included but is never judged as an interior second difference.
    """
    live = np.flatnonzero(row > 0.0)
    if live.size == 0:
        return None
    i0, i1 = int(live[0]), int(live[-1])
    if i0 > 0:
        i0 -= 1
    if i1 < row.size - 1:
        i1 += 1
    return i0, i1


def _rolling_median_excl_center(values: np.ndarray, half: int = 2) -> np.ndarray:
    """Median of each point's ±``half`` NEIGHBOURS (center excluded).

    At the array ends the window shrinks to the available neighbours;
    points with fewer than 2 neighbours on either side get NaN (not
    judged — there is not enough context).
    """
    n = values.size
    out = np.full(n, np.nan)
    for i in range(n):
        left = values[max(0, i - half):i]
        right = values[i + 1:min(n, i + 1 + half)]
        if left.size >= 2 and right.size >= 2:
            out[i] = float(np.nanmedian(np.concatenate([left, right])))
    return out


def _runs_of(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    """Contiguous True runs of ``mask`` as inclusive (start, end)."""
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for i, flag in enumerate(mask):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            if i - start >= min_len:
                runs.append((start, i - 1))
            start = None
    if start is not None and mask.size - start >= min_len:
        runs.append((start, mask.size - 1))
    return runs


def check_fairness(
    table: OffsetsTable,
    *,
    z_limit: float | None = None,
    curvature_sigma: float = 4.0,
    curvature_abs: float = 25.0,
    monotonic_from_fraction: float = 0.5,
    monotonic_revival: float = 0.01,
    parallel_rel: float = 0.004,
    parallel_wobble: float = 0.0005,
    parallel_min_stations: int = 3,
) -> FairnessReport:
    """Run the plan-task-2.5 fairness checks on an offsets table.

    Args:
        table: the offsets grid to judge.
        z_limit: judge waterline rows with z <= this height, m.  Pass
            the design draft; None judges every row (correct for grids
            that stop at the design waterline, as the Series 60 loader
            builds).
        curvature_sigma: robust alarm level in "contrast sigmas" — a
            second difference deviating more than this many MAD-scaled
            sigmas from its neighbours' median is a candidate kink.
        curvature_abs: dimensionless absolute contrast floor
            (scaled by Lpp^2/B): candidates below it are accepted as
            fair.  Default calibrated to ~2x the maximum contrast
            MEASURED on the Series 60 parent (12.2 on the standard
            21-station grid — see the calibration note in
            tests/test_fairness.py); on that grid it corresponds to a
            minimum detectable single-point spike of about
            ``curvature_abs * B / (2 * (Ns-1)^2 / Lpp^2 * Lpp^2)`` —
            i.e. ~1.4 m, the honest resolution limit of a 14 m station
            spacing.  Finer grids detect proportionally smaller errors.
        monotonic_from_fraction: first-difference (single-lobe) check
            applies at and above this fraction of ``z_limit`` — below
            it, bulbs and domes legitimately break the lobe.
        monotonic_revival: sustained centreward movement exceeding this
            fraction of B is flagged, m.
        parallel_rel: a run of stations holding within this relative
            fraction of the row maximum counts as parallel middle body.
        parallel_wobble: allowed variation inside a parallel run,
            fraction of B — deliberately MUCH tighter than the
            detection window: the run is found with a loose net
            (``parallel_rel``) and then held to a tight constant.
        parallel_min_stations: shortest run accepted as parallel.

    Returns:
        A :class:`FairnessReport`; ``report.ok`` is the pass/fail
        verdict (True = fair, zero alarms).
    """
    if z_limit is None:
        z_limit = float(table.waterlines[-1])
    if not math.isfinite(z_limit) or z_limit <= 0:
        raise ValueError(f"z_limit must be a positive depth, got {z_limit}")

    stations = np.asarray(table.stations, dtype=float)
    waterlines = np.asarray(table.waterlines, dtype=float)
    half = np.asarray(table.half_breadths, dtype=float)
    scale = table.lpp * table.lpp / table.beam  # curvature normalisation

    rows = np.flatnonzero(waterlines <= z_limit + 1e-9)
    if rows.size == 0:
        raise ValueError(
            f"no waterline row at or below z_limit={z_limit}; "
            f"grid spans {waterlines[0]}..{waterlines[-1]} m"
        )

    issues: list[FairnessIssue] = []
    max_contrast = 0.0
    segments: list[tuple[float, float, float]] = []

    for r in rows:
        z = float(waterlines[r])
        row = half[:, r]  # half_breadths is station-major (Ns, Nw)
        span = _live_span(row)
        if span is None:
            continue
        i0, i1 = span
        seg = row[i0:i1 + 1]
        xs = stations[i0:i1 + 1]

        # --- second differences -> local contrast ----------------------
        # exact central second difference on the (possibly non-uniform)
        # grid — the classical fairing signal (d2y/dx2 tables), sharper
        # than a double np.gradient which smears a kink over 3 points
        h1 = xs[1:-1] - xs[:-2]
        h2 = xs[2:] - xs[1:-1]
        d2 = (2.0 / (h1 + h2)
              * ((seg[2:] - seg[1:-1]) / h2 - (seg[1:-1] - seg[:-2]) / h1)
              ) * scale
        d2 = np.concatenate([[np.nan], d2, [np.nan]])  # ends: no context
        med = _rolling_median_excl_center(d2)
        dev = np.abs(d2 - med)
        live_dev = dev[~np.isnan(dev)]
        if live_dev.size:
            max_contrast = max(max_contrast, float(live_dev.max()))
            mad = float(np.median(np.abs(live_dev - np.median(live_dev))))
            sigma = 1.4826 * mad
            for k in range(seg.size):
                if np.isnan(dev[k]):
                    continue  # not enough context at the span ends
                if (dev[k] > curvature_sigma * sigma
                        and dev[k] > curvature_abs):
                    x_mid = 0.5 * (xs[k - 1] + xs[min(k + 1, xs.size - 1)])
                    issues.append(FairnessIssue(
                        kind="curvature_jump",
                        waterline_z=z,
                        station_x=float(x_mid),
                        metric=float(dev[k]),
                        limit=curvature_abs,
                        detail=(
                            f"second difference deviates {dev[k]:.3g} "
                            f"(>{curvature_abs:g} floor and >"
                            f"{curvature_sigma:g} robust sigmas) from "
                            f"neighbours — kink or digitising spike"
                        ),
                    ))

        # --- first differences -> single-lobe monotonicity -------------
        if z >= monotonic_from_fraction * z_limit:
            j_peak = int(np.argmax(seg))
            tol = monotonic_revival * table.beam
            for lo, hi, direction in ((0, j_peak, -1), (j_peak, seg.size - 1, +1)):
                bad = (direction * np.diff(seg[lo:hi + 1])) > tol
                for a, b in _runs_of(bad, 1):
                    issues.append(FairnessIssue(
                        kind="non_monotonic",
                        waterline_z=z,
                        station_x=float(xs[lo + a + 1]),
                        metric=float(direction * np.diff(seg[lo:hi + 1])[a:b + 1].max()),
                        limit=float(tol),
                        detail=(
                            f"waterline moves {'towards' if direction < 0 else 'away from'} "
                            f"its maximum by more than {tol:.3g} m "
                            f"{'before' if direction < 0 else 'after'} the "
                            f"half-breadth peak — lobe is not single"
                        ),
                    ))

        # --- parallel middle body constancy ----------------------------
        y_max = float(seg.max())
        if y_max <= 0 or seg.size < parallel_min_stations + 2:
            continue
        flat = seg >= y_max * (1.0 - parallel_rel)
        interior = [(a, b) for a, b in _runs_of(flat, parallel_min_stations)
                    if a > 0 and b < seg.size - 1]
        for a, b in interior:
            segments.append((z, float(xs[a]), float(xs[b])))
            # the two boundary stations are the taper's landing zone —
            # judge only the interior of the run
            wa, wb = (a, b) if b - a < 2 else (a + 1, b - 1)
            wobble = float(np.abs(seg[wa:wb + 1] - y_max).max())
            if wobble > parallel_wobble * table.beam:
                issues.append(FairnessIssue(
                    kind="parallel_wobble",
                    waterline_z=z,
                    station_x=float(xs[a] + xs[b]) / 2.0,
                    metric=wobble,
                    limit=parallel_wobble * table.beam,
                    detail=(
                        f"parallel-middle-body run x=[{xs[a]:g}, {xs[b]:g}] "
                        f"m wobbles {wobble:.3g} m (> "
                        f"{parallel_wobble * table.beam:.3g} m) — the "
                        f"'parallel' body is not parallel"
                    ),
                ))

    return FairnessReport(
        issues=tuple(issues),
        n_stations=int(stations.size),
        n_waterlines_checked=int(rows.size),
        z_limit=float(z_limit),
        max_contrast=max_contrast,
        parallel_segments=tuple(segments),
    )
