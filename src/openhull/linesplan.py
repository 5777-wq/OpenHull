"""Parametric hull-form transformation - the Lackenby method (task 2.3).

Transforms a digitised parent offsets table onto target values of the
block/prismatic coefficient and longitudinal centre of buoyancy while
holding Lpp, B and T fixed, by shifting sectional areas longitudinally
(Lackenby's quadratic transform function).

Formula source (AGENTS.md section 5 whitelist):

    林焰主编《船舶设计原理》第 4 版, 第 5 章型线设计,
    "②勒根贝尔(Lackenby)法", 式(5-35)~(5-47)  [OCR visually verified
    against the scanned pages 211-212 of the book]

    * (5-35)  transform function  du = c*(1-u)*(u+d),  u: 0 = midship,
              1 = terminal perpendicular (per half body)
    * (5-36)  boundary conditions du(l_p) = dl_p,  INT du*dy = dCp
    * (5-40)~(5-43)  moment arms h_f/h_a from B_f/C_f and K^2
    * (5-31)~(5-34)  fore/aft split from buoyancy & moment balance
              ((5-46)/(5-47) are the dl = 0 case of (5-44)/(5-45))

Declared conventions pinned against the source (R7, see work log 34):
    * y(u) is the dimensionless sectional-area curve, y = A/A_midship
      (peak 1 on the parallel middle body, 0 at the perpendiculars);
    * du > 0 shifts a section TOWARDS its perpendicular (fore body:
      towards FP).  The first-order area change is INT du*(-dy/du) du;
    * K^2 = INT u^2 * y du / Cp  is the SECOND MOMENT of the area curve
      about midship (plain du-integral).  With this reading the printed
      B_f formula (5-41) closes exactly on a parabolic test curve
      (y = 1-u^2 gives Cp = 2/3, x_bf = 3/8, K^2 = 1/5, B_f = 3/5),
      which is used as an analytic anchor in the test suite.

Declared first-order approximations (validated in VALIDATION.md):
    the method neglects second-order terms, so the achieved coefficient
    is measured after each pass and the requested increments are
    corrected iteratively (default up to 8 passes) until the numeric
    targets are met within tolerance.  Sections are carried over from
    the parent unchanged (interpolated at the shifted station), which
    preserves section shape, keeps the parallel body and Cm untouched,
    and leaves the fairness of the parent form intact.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .geometry import OffsetsTable
from .hydrostatics import simpson
from .spec import SpecValidationError

#: algorithm registry id -> description metadata (AGENTS.md section 8)
TRANSFORM_ALGORITHMS = {
    "lackenby": {
        "citation": (
            "Lackenby quadratic transform function, 林焰《船舶设计原理》"
            "(第4版) 式(5-35)~(5-47), sec.5 型线设计"
        ),
        "applicability": (
            "full and semi-full forms with or without parallel middle "
            "body; |dCp| <= 0.08, |dx_b| <= 0.03 half-lengths, target "
            "Cp in [0.55, 0.88]"
        ),
    },
    "one_minus_cp": {
        "citation": (
            "(1-Cp) linear transform, 林焰《船舶设计原理》(第4版) "
            "式(5-27)~(5-30), sec.5 型线设计"
        ),
        "applicability": "same band as lackenby; kept as a cross-check id",
    },
}

#: iteration ceiling for the second-order correction loop
MAX_PASSES = 8
#: convergence tolerances (Cp absolute, x_b in half-length units)
CP_TOL = 1.0e-4
XB_TOL = 1.0e-4
#: guard bands (AGENTS.md section 6)
MAX_ABS_DELTA_CP = 0.08
MAX_ABS_DELTA_XB = 0.03   # half-length units (= 1.5 %Lpp)
CP_VALID_RANGE = (0.55, 0.88)


# ---------------------------------------------------------------------------
# dimensionless area curves
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _HalfCurve:
    """One half of the dimensionless sectional-area curve.

    u: equally spaced abscissa, 0 = midship, 1 = the half body's
    perpendicular.  y: sectional area over the midship area (peak ~1).
    shift: the last solved du field on this grid, if any.
    """

    u: np.ndarray
    y: np.ndarray
    cp: float          # prismatic of the half body
    xb: float          # area-curve centroid, midship = 0, perpendicular = 1
    k2: float          # second moment arm about midship, K^2
    l_parallel: float  # parallel-middle-body length, fraction of L/2
    shift: np.ndarray | None = None


def _vertical_areas(table: OffsetsTable) -> np.ndarray:
    """Sectional areas (m^2) up to the top waterline, one per station."""
    spacing = float(table.waterlines[1] - table.waterlines[0])
    weights = np.ones(table.waterlines.size)
    weights[1:-1:2] = 4.0
    weights[2:-1:2] = 2.0
    weights *= spacing / 3.0
    return table.half_breadths @ weights


def area_curve(table: OffsetsTable, n_points: int = 64) -> tuple:
    """Split the parent area curve into (fore, aft, cm) objects.

    Returns (fore, aft, midship_coefficient).  The midship section is
    the grid middle (stations are equally spaced with an odd count, so
    the middle index sits exactly at Lpp/2).  The parallel-body length
    is detected as the span adjacent to midship where the area curve
    stays within 0.05 % of its peak.
    """
    areas = _vertical_areas(table)
    mid = table.stations.size // 2
    cm = float(2.0 * areas[mid] / (table.beam * table.waterlines[-1]))
    y_all = areas / float(areas[mid])
    x_all = table.stations / table.lpp

    u_q = np.linspace(0.0, 1.0, n_points + 1)
    # forward: u = 2*xi - 1 (0 = midship, 1 = FP); nodes are ascending
    y_f = np.interp(u_q, 2.0 * x_all[mid:] - 1.0, y_all[mid:])
    # aft: u = 1 - 2*xi (0 = midship, 1 = AP); flip so nodes ascend
    y_a = np.interp(u_q, (1.0 - 2.0 * x_all[: mid + 1])[::-1],
                    y_all[: mid + 1][::-1])
    return (_half_curve(u_q, y_f, _detect_parallel(y_f)),
            _half_curve(u_q, y_a, _detect_parallel(y_a)),
            cm)


def _detect_parallel(y: np.ndarray, tol: float = 0.0005) -> float:
    """Parallel-body length (fraction of the half body) adjacent to mid."""
    for i in range(y.size):
        if y[i] < 1.0 - tol:
            return i / (y.size - 1)
    return 1.0


def _half_curve(u: np.ndarray, y: np.ndarray,
                l_parallel: float) -> _HalfCurve:
    """Characteristic integrals of one half of the area curve.

    Conventions per the module docstring: Cp = INT y du, xb = INT u*y
    du / Cp, K^2 = INT u^2*y du / Cp, u running midship (0) ->
    perpendicular (1), Simpson integration on the equal grid.
    """
    step = float(u[1] - u[0])
    cp = simpson(y, step)
    xb = simpson(u * y, step) / cp
    k2 = simpson(u**2 * y, step) / cp
    return _HalfCurve(u, y, float(cp), float(xb), float(k2),
                      float(l_parallel))


# ---------------------------------------------------------------------------
# Lackenby shift on one half body
# ---------------------------------------------------------------------------


def _shift_coeffs(curve: _HalfCurve, delta_cp: float,
                  delta_l: float) -> tuple:
    """Solve du(u) = (1-u)*(alpha + beta*u) for one half body.

    Boundary condition (5-36a): du(l_p) = delta_l (the parallel-body
    end moves by the parallel-body increment).
    Area condition (5-36b): INT du*(-dy/du) du = delta_cp, with the
    discrete slope of the parent curve.

    Returns (alpha, beta) in half-body-length units.
    """
    u, y = curve.u, curve.y
    step = float(u[1] - u[0])
    w = -np.gradient(y, step)              # >= 0 on the taper
    p_int = simpson(u * (1.0 - u) * w, step)
    q_int = simpson((1.0 - u) * w, step)

    lp = curve.l_parallel
    # alpha + beta*lp = rhs1   and   alpha*Q + beta*P = delta_cp
    rhs1 = delta_l / (1.0 - lp)
    det = p_int - lp * q_int
    if abs(det) < 1.0e-12:
        # degenerate (flat curve): fall back to the (1-Cp) shape
        return delta_cp / max(q_int, 1.0e-12), 0.0
    alpha = (rhs1 * p_int - lp * delta_cp) / det
    beta = (delta_cp - rhs1 * q_int) / det
    return alpha, beta


def _apply_shift(curve: _HalfCurve, alpha: float, beta: float,
                 delta_cp: float, delta_l: float) -> _HalfCurve:
    """Carry the parent curve onto the shifted positions.

    y_new(u) = y_old(u - du(u)), du = (1-u)*(alpha + beta*u), by linear
    interpolation on the parent grid.  A (numerically) zero request
    returns the parent curve unchanged.
    """
    u = curve.u
    du = np.where(
        u <= curve.l_parallel,
        # parallel body: rigid shift by the increment only
        delta_l if abs(delta_l) >= 1.0e-12 else 0.0,
        # taper: the quadratic transform function
        (1.0 - u) * (alpha + beta * u),
    )
    if abs(delta_cp) < 1.0e-12 and abs(delta_l) < 1.0e-12:
        return _HalfCurve(u, curve.y.copy(), curve.cp, curve.xb,
                          curve.k2, curve.l_parallel, du)
    y_new = np.interp(np.clip(u - du, u[0], u[-1]), u, curve.y)
    step = float(u[1] - u[0])
    cp = simpson(y_new, step)
    xb = simpson(u * y_new, step) / cp
    k2 = simpson(u**2 * y_new, step) / cp
    return _HalfCurve(u, y_new, float(cp), float(xb), float(k2),
                      curve.l_parallel + delta_l, du)


def _b_and_c(curve: _HalfCurve) -> tuple:
    """B and C of eqs. (5-41)/(5-42) for one half body."""
    lp, cp, xb, k2 = curve.l_parallel, curve.cp, curve.xb, curve.k2
    a_den = cp * (1.0 - 2.0 * xb) - lp * (1.0 - cp)
    if abs(a_den) < 1.0e-9:
        return 0.0, 0.0
    b_val = cp * (2.0 * xb - 3.0 * k2 - lp * (1.0 - 2.0 * xb)) / a_den
    c_val = (b_val * (1.0 - cp) - cp * (1.0 - 2.0 * xb)) / max(1.0 - lp,
                                                               1.0e-9)
    return b_val, c_val


# ---------------------------------------------------------------------------
# fore/aft split (buoyancy + moment balance, eqs. 5-31/5-32 -> 5-44..47)
# ---------------------------------------------------------------------------


def _split(fore, aft, d_cp, d_xb, dl_f, dl_a) -> tuple:
    """Fore/aft prismatic increments (d_cp_f, d_cp_a) and moment arms."""
    x_b = _parent_xb(fore, aft)
    cp_p = _parent_cp(fore, aft)
    b_f, c_f = _b_and_c(fore)
    b_a, c_a = _b_and_c(aft)

    if abs(dl_f) < 1.0e-12 and abs(dl_a) < 1.0e-12:
        # eqs. (5-46)/(5-47) with h = B (dl = 0 reduces (5-40))
        h_f, h_a = b_f, b_a
        denom = h_f + h_a
        if abs(denom) < 1.0e-9:
            raise SpecValidationError(
                "h_f + h_a", denom, "non-zero moment arms",
                "the fore/aft split equations are degenerate for this "
                "parent area curve.",
            )
        d_f = 2.0 * (d_cp * (h_a + x_b) + d_xb * (cp_p + d_cp)) / denom
        d_a = 2.0 * (d_cp * (h_f - x_b) - d_xb * (cp_p + d_cp)) / denom
        return d_f, d_a, h_f, h_a

    # eqs. (5-44)/(5-45): h depends on dCp through (5-40) -> fixed point
    h_f, h_a = b_f, b_a
    d_f = d_a = 0.0
    denom = b_f + b_a
    if abs(denom) < 1.0e-9:
        raise SpecValidationError(
            "B_f + B_a", denom, "non-zero moment arms",
            "the fore/aft split equations are degenerate for this "
            "parent area curve.",
        )
    for _ in range(8):
        h_f = b_f - c_f * dl_f / d_f if abs(d_f) > 1.0e-12 else b_f
        h_a = b_a - c_a * dl_a / d_a if abs(d_a) > 1.0e-12 else b_a
        d_f = (2.0 * (d_cp * (h_a + x_b) + d_xb * (cp_p + d_cp))
               + c_f * dl_f - c_a * dl_a) / denom
        d_a = (2.0 * (d_cp * (h_f - x_b) - d_xb * (cp_p + d_cp))
               - c_f * dl_f + c_a * dl_a) / denom
    return d_f, d_a, h_f, h_a


def _run_once(fore, aft, d_cp, d_xb, dl_f, dl_a):
    """One algebra pass -> shifted half curves with their du fields."""
    d_f, d_a, _, _ = _split(fore, aft, d_cp, d_xb, dl_f, dl_a)
    a_f, b_f = _shift_coeffs(fore, d_f, dl_f)
    a_a, b_a = _shift_coeffs(aft, d_a, dl_a)
    return (_apply_shift(fore, a_f, b_f, d_f, dl_f),
            _apply_shift(aft, a_a, b_a, d_a, dl_a))


# ---------------------------------------------------------------------------
# public transform
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LackenbyReport:
    """What was requested, what the algebra solved, what was achieved."""

    algorithm: str
    citation: str
    parent: dict
    requested: dict
    fore: dict
    aft: dict
    achieved: dict
    iterations: int
    identity: bool
    shift_x_m: list = field(default_factory=list)  # station dx field, m

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "citation": self.citation,
            "parent": dict(self.parent),
            "requested": dict(self.requested),
            "fore": dict(self.fore),
            "aft": dict(self.aft),
            "achieved": dict(self.achieved),
            "iterations": self.iterations,
            "identity": self.identity,
            "shift_x_m": list(self.shift_x_m),
        }


def lackenby_transform(
    table: OffsetsTable,
    *,
    algorithm: str = "lackenby",
    target_cb: float | None = None,
    target_cp: float | None = None,
    target_lcb_pct: float | None = None,
    delta_cb: float | None = None,
    delta_lcb_pct: float | None = None,
    delta_l_pf: float | None = None,
    delta_l_pa: float | None = None,
    max_passes: int = MAX_PASSES,
) -> tuple:
    """Transform a parent table onto target Cb/Cp and LCB.

    Args:
        table: parent :class:`OffsetsTable` (e.g. from
            ``load_offsets_csv`` or ``jbc_parent_offsets``).
        algorithm: registry id (see ``TRANSFORM_ALGORITHMS``); only
            ``lackenby`` is implemented, ``one_minus_cp`` is reserved
            for cross-validation work.
        target_cb / target_cp: desired coefficient at the top waterline
            (give exactly one).  Cm is measured from the parent and
            held (the parallel body does not move for dl = 0).
        target_lcb_pct: desired LCB, % Lpp, forward of midship positive.
        delta_cb / delta_lcb_pct: increments as an alternative to the
            absolute targets.
        delta_l_pf / delta_l_pa: parallel-body length change per half
            body, fraction of L/2 (eq. 5-36a).
        max_passes: ceiling for the second-order correction loop.

    Returns:
        (new OffsetsTable, LackenbyReport).
    """
    meta = TRANSFORM_ALGORITHMS.get(algorithm)
    if meta is None:
        known = ", ".join(sorted(TRANSFORM_ALGORITHMS))
        raise SpecValidationError(
            "algorithm", algorithm, f"one of: {known}",
            "unknown algorithm id; the transform registry lists the "
            "implemented methods.",
        )
    if algorithm != "lackenby":
        raise NotImplementedError(
            f"algorithm '{algorithm}' is not implemented; use 'lackenby'"
        )

    if (target_cb is None and target_cp is None and delta_cb is None
            and target_lcb_pct is None and delta_lcb_pct is None
            and delta_l_pf is None and delta_l_pa is None):
        raise SpecValidationError(
            "target/increment", None,
            "at least one of: Cb goal (target/delta), LCB goal "
            "(target/delta), parallel-body increments",
            "a transform request must state what to change; an empty "
            "request is a caller bug, not an identity operation.",
        )
    dl_f = float(delta_l_pf or 0.0)
    dl_a = float(delta_l_pa or 0.0)

    fore, aft, cm = area_curve(table)
    lcb_pct_parent = _table_lcb_pct(table)
    cb_parent = _table_cb(table)
    xb_parent = 2.0 * lcb_pct_parent / 100.0

    # goals live in the TABLE layer (the numbers hydrostatics sees)
    if sum(x is not None for x in (target_cb, target_cp, delta_cb)) > 1:
        raise SpecValidationError(
            "Cb goal", None, "only one of target_cb, target_cp, delta_cb",
            "target_cp is converted through the measured Cm, so giving "
            "several styles would be redundant or contradictory.",
        )
    if target_cp is not None:
        cb_goal = float(target_cp) * cm
    elif target_cb is not None:
        cb_goal = float(target_cb)
    elif delta_cb is not None:
        cb_goal = cb_parent + float(delta_cb)
    else:
        cb_goal = cb_parent
    if target_lcb_pct is not None:
        xb_goal = 2.0 * float(target_lcb_pct) / 100.0
    elif delta_lcb_pct is not None:
        xb_goal = xb_parent + 2.0 * float(delta_lcb_pct) / 100.0
    else:
        xb_goal = xb_parent

    d_cp = (cb_goal - cb_parent) / cm
    d_xb = xb_goal - xb_parent
    _guard(d_cp, d_xb, cb_goal / cm)

    zero = (abs(d_cp) < 1.0e-12 and abs(d_xb) < 1.0e-12
            and abs(dl_f) < 1.0e-12 and abs(dl_a) < 1.0e-12)
    if zero:
        new_table = OffsetsTable(
            lpp=table.lpp, beam=table.beam,
            stations=table.stations.copy(),
            waterlines=table.waterlines.copy(),
            half_breadths=table.half_breadths.copy(),
        )
        info = _parent_dict(fore, aft, cm, lcb_pct_parent)
        report = LackenbyReport(
            algorithm=algorithm, citation=meta["citation"],
            parent=info, requested={"delta_cp": 0.0, "delta_xb": 0.0,
                                    "delta_l_pf": 0.0, "delta_l_pa": 0.0},
            fore={}, aft={}, achieved=info, iterations=0, identity=True,
        )
        return new_table, report

    # Large perturbations are split into serial sub-transforms (each
    # re-measuring the parent), keeping every algebra step inside the
    # first-order validity band.  Within each step the achieved values
    # are measured on the CARRIED TABLE (the numbers hydrostatics will
    # see) and the residual feeds back into the requested increments.
    n_steps = max(1, int(math.ceil(abs(d_cp) / 0.035)))
    dl_f, dl_a = dl_f / n_steps, dl_a / n_steps
    work = table
    new_fore, new_aft = fore, aft
    passes_total = 0
    for step in range(n_steps):
        f_cur, a_cur, cm_cur = area_curve(work)
        goal_cb_s = _table_cb(work) + (cb_goal - cb_parent) / n_steps
        goal_xb_s = 2.0 * _table_lcb_pct(work) / 100.0 \
            + (xb_goal - xb_parent) / n_steps
        corr_cp = (goal_cb_s - _table_cb(work)) / cm_cur
        corr_xb = goal_xb_s - 2.0 * _table_lcb_pct(work) / 100.0
        new_table = work
        dx_last = np.zeros_like(work.stations)
        passes = 0
        for passes in range(1, min(max_passes, MAX_PASSES) + 1):
            new_fore, new_aft = _run_once(f_cur, a_cur, corr_cp, corr_xb,
                                          dl_f, dl_a)
            new_table, dx_last = _carry_table(work, new_fore, new_aft)
            err_cp = (goal_cb_s - _table_cb(new_table)) / cm_cur
            err_xb = goal_xb_s - 2.0 * _table_lcb_pct(new_table) / 100.0
            if abs(err_cp) < CP_TOL and abs(err_xb) < XB_TOL:
                break
            corr_cp += 0.8 * err_cp
            corr_xb += 0.8 * err_xb
        work = new_table
        passes_total += passes

    report = LackenbyReport(
        algorithm=algorithm, citation=meta["citation"],
        parent=_parent_dict(fore, aft, cm, lcb_pct_parent),
        requested={"delta_cp": round(d_cp, 6), "delta_xb": round(d_xb, 6),
                   "delta_l_pf": delta_l_pf or 0.0,
                   "delta_l_pa": delta_l_pa or 0.0},
        fore=_half_dict("fore", fore, new_fore, dl_f),
        aft=_half_dict("aft", aft, new_aft, dl_a),
        achieved={"cb": round(_table_cb(work), 6),
                  "cp": round(_table_cb(work) / cm, 6),
                  "lcb_pct_lpp": round(_table_lcb_pct(work), 4),
                  "cm_held": round(cm, 6)},
        iterations=passes_total, identity=False,
        shift_x_m=[round(float(v), 4) for v in dx_last],
    )
    return work, report


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _parent_cp(fore: _HalfCurve, aft: _HalfCurve) -> float:
    """Whole-form prismatic: Cp = (Cp_f + Cp_a)/2 (equal half lengths)."""
    return 0.5 * (fore.cp + aft.cp)


def _parent_xb(fore: _HalfCurve, aft: _HalfCurve) -> float:
    """Whole-form centroid, half-length units, forward positive."""
    return (fore.cp * fore.xb - aft.cp * aft.xb) / (fore.cp + aft.cp)


def _table_cb(table: OffsetsTable) -> float:
    """Block coefficient of a table at its top waterline (numerical)."""
    areas = _vertical_areas(table)
    vol = 2.0 * simpson(areas, float(table.stations[1] - table.stations[0]))
    return float(vol / (table.lpp * table.beam * table.waterlines[-1]))


def _table_lcb_pct(table: OffsetsTable) -> float:
    """LCB from the tabulated sections, % Lpp, forward of midship +."""
    areas = _vertical_areas(table)
    x = table.stations
    vol = simpson(areas, float(x[1] - x[0]))
    moment = simpson(areas * x, float(x[1] - x[0]))
    return float((moment / vol - table.lpp / 2.0) / table.lpp * 100.0)


def _parent_dict(fore, aft, cm, lcb_pct) -> dict:
    return {
        "cp": round(_parent_cp(fore, aft), 6),
        "cp_fore": round(fore.cp, 6),
        "cp_aft": round(aft.cp, 6),
        "xb_half_len": round(_parent_xb(fore, aft), 6),
        "lcb_pct_lpp": round(lcb_pct, 4),
        "cm": round(cm, 6),
        "l_pf": round(fore.l_parallel, 4),
        "l_pa": round(aft.l_parallel, 4),
    }


def _half_dict(name, old, new, delta_l) -> dict:
    return {
        f"cp_{name}": {"from": round(old.cp, 6), "to": round(new.cp, 6)},
        f"xb_{name}": {"from": round(old.xb, 6), "to": round(new.xb, 6)},
        f"delta_l_{name[0]}": delta_l,
    }


def _guard(d_cp, d_xb, target_cp) -> None:
    if not CP_VALID_RANGE[0] <= target_cp <= CP_VALID_RANGE[1]:
        raise SpecValidationError(
            "target Cp", target_cp, f"Cp in {CP_VALID_RANGE}",
            "outside this band the shifted form would leave the "
            "applicability of full-form empirical methods downstream.",
        )
    if abs(d_cp) > MAX_ABS_DELTA_CP:
        raise SpecValidationError(
            "delta Cp", d_cp, f"|dCp| <= {MAX_ABS_DELTA_CP}",
            "the Lackenby transform is a small-perturbation method; a "
            "block-coefficient change this large would need a different "
            "parent form, not a shift of this one.",
        )
    if abs(d_xb) > MAX_ABS_DELTA_XB:
        raise SpecValidationError(
            "delta x_b", d_xb,
            f"|dx_b| <= {MAX_ABS_DELTA_XB} half-lengths",
            "moving the longitudinal centre of buoyancy this far in one "
            "step is outside the first-order transform's validity band.",
        )


def _carry_table(table: OffsetsTable, fore, aft) -> OffsetsTable:
    """Move every waterline's offsets by the solved station shifts.

    The new section at station x is the parent section interpolated at
    x - dx(x) (the source book's higher-precision re-interpolation
    method), so each section keeps its shape; Cm, B and T are untouched.
    """
    x = table.stations
    xi = x / table.lpp

    du_fore = np.interp(2.0 * xi - 1.0, fore.u, fore.shift)
    du_aft = np.interp(1.0 - 2.0 * xi, aft.u, aft.shift)
    du = np.where(xi >= 0.5, du_fore, du_aft)
    dx = du * 0.5 * table.lpp * np.where(xi >= 0.5, 1.0, -1.0)
    x_src = np.clip(x - dx, 0.0, table.lpp)
    new_breadths = np.empty_like(table.half_breadths)
    for j in range(table.waterlines.size):
        new_breadths[:, j] = np.interp(x_src, x, table.half_breadths[:, j])
    new_table = OffsetsTable(
        lpp=table.lpp, beam=table.beam, stations=x.copy(),
        waterlines=table.waterlines.copy(), half_breadths=new_breadths,
    )
    return new_table, dx


# ---------------------------------------------------------------------------
