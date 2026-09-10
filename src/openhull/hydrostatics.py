"""Hydrostatic particulars by numerical integration (plan task 1.4).

Computes, at any even-keel draft, the displacement, waterplane data and
stability-geometry entries of the :class:`Hydrostatics` container defined
in task 1.1.  All integrals are evaluated with the in-package Simpson
rule (no black-box quadrature, AGENTS.md section 7/8); the trapezoidal
rule is provided for convergence comparisons.

Method (whitelisted sources, AGENTS.md section 5):

* Numerical integration - Ship Theory vol. 1 (Sheng Zhenbang, Ship
  Theory vol. 1, 2nd ed.), ch. 2: trapezoidal rule Eqs.(2-8)/(2-14);
  Simpson's first rule (n even) and second rule (n a multiple of 3);
  integrand conventions for area (f = y), first moment (f = y*x) and
  moments of inertia (f = y^3/3 transverse, f = y*x^2 longitudinal).
* Even-keel volume and centre of buoyancy, vertical method - Ship
  Theory vol. 1 ch. 3: grad = integral of Aw dz, KB = integral of
  z*Aw dz / grad, waterplane area Aw, centre of flotation xF and
  waterplane coefficient Cwp.
* Metacentric radii - Ship Theory vol. 1 section 4-2: BMT = I_T/grad
  (Eq. 4-7), BML = I_L/grad; MTC - section 4-4, Eq. (4-16):
  MTC = Delta*BML/(100*Lpp) with GM_L ~ BML; KM = KB + BMT.

Integration directions (each a composite Simpson pass over the
offsets grid, waterline half-breadths interpolated linearly in draft
between tabulated waterlines):

  1. longitudinal, per waterline: Aw, LCF, I_T (f = y^3/3), I_L;
  2. vertical: grad = integral Aw dz, KB = integral z*Aw dz / grad;
  3. per station, vertical: Bonjean section areas (interface for
     plan task 2.2), and the midship section area for Cm.

Only even-keel (upright) hydrostatics are provided; the trimmed
floating attitude is plan task 1.5 (whitelisted iteration Eqs.
(3-25)/(3-26) of Ship Structural Strength).
"""

from __future__ import annotations

import numpy as np

from .geometry import OffsetsTable
from .spec import SEAWATER_DENSITY, Hydrostatics, HydrostaticsTable, SpecValidationError

__all__ = [
    "simpson",
    "trapezoid",
    "waterplane",
    "hydrostatics_at",
    "hydrostatics_table",
    "bonjean_areas",
]


# ---------------------------------------------------------------------------
# Integration kernels (Ship Theory vol. 1, ch. 2)
# ---------------------------------------------------------------------------


def _check_abscissa(values: np.ndarray, name: str) -> None:
    if values.ndim != 1 or values.size < 3:
        raise SpecValidationError(
            name, values.size, "1-D array with >= 3 points",
            f"numerical integration needs at least three {name} points; "
            "fewer cannot span two Simpson intervals.",
        )


def simpson(values: np.ndarray, spacing: float) -> float:
    """Composite Simpson's first rule over equally spaced points.

    integral = h/3 * (y0 + 4*y1 + 2*y2 + ... + 4*y(n-1) + yn)

    The number of intervals (points - 1) must be EVEN: Simpson's first
    rule integrates a parabola through each triple of points, i.e. over
    pairs of intervals (Ship Theory vol. 1, ch. 2 - the book's "n must
    be even").  Exact for polynomials up to degree 3.
    """
    _check_abscissa(values, "values")
    if not np.isfinite(spacing) or spacing <= 0:
        raise SpecValidationError(
            "spacing", spacing, "finite spacing > 0",
            "the Simpson rule needs a positive, finite point spacing; a "
            "zero or negative spacing integrates nothing (or reverses "
            "the integration direction silently, which must not happen).",
        )
    v = np.asarray(values, dtype=float)
    if v.size % 2 == 0:
        raise SpecValidationError(
            "values", v.size,
            "odd number of points (even number of intervals)",
            "Simpson's first rule pairs up intervals: with an even point "
            "count the last interval has no partner and the rule cannot "
            "be applied. Use an even interval count (odd point count), "
            "or combine the first/last four intervals with Simpson's "
            "second rule as the textbook prescribes.",
        )
    return float(
        spacing
        / 3.0
        * (v[0] + v[-1] + 4.0 * v[1:-1:2].sum() + 2.0 * v[2:-1:2].sum())
    )


def trapezoid(values: np.ndarray, spacing: float) -> float:
    """Composite trapezoidal rule (Ship Theory vol. 1, ch. 2, Eqs.(2-8)/(2-14)).

    Provided for convergence comparisons; the production path uses
    :func:`simpson` (error O(h^4) versus O(h^2)).
    """
    _check_abscissa(values, "values")
    if not np.isfinite(spacing) or spacing <= 0:
        raise SpecValidationError(
            "spacing", spacing, "finite spacing > 0",
            "the trapezoidal rule needs a positive, finite point spacing.",
        )
    v = np.asarray(values, dtype=float)
    return float(
        spacing * (v.sum() - 0.5 * (v[0] + v[-1]))
    )


# ---------------------------------------------------------------------------
# Waterplane integration (longitudinal direction)
# ---------------------------------------------------------------------------


def waterplane(table: OffsetsTable, draft: float):
    """Waterplane particulars at one draft.

    Args:
        table: offsets grid.
        draft: even-keel draft, m (0 < draft <= waterlines[-1]).

    Returns:
        (aw, lcf_m, ix, iyf): waterplane area m^2, longitudinal centre
        of flotation from the AP, m, transverse inertia about the
        centreline m^4 (integrand y^3/3 per side), longitudinal inertia
        about the centre of flotation m^4 (parallel-axis moved from
        midship).
    """
    if not np.isfinite(draft) or draft < 0 or draft > table.waterlines[-1]:
        raise SpecValidationError(
            "draft", draft,
            f"0 <= draft <= {table.waterlines[-1]} m (deepest waterline)",
            "the waterplane can only be evaluated between the keel and "
            "the deepest tabulated waterline; above it the offsets carry "
            "no shape information. The keel waterline (draft 0) is "
            "allowed: flat-bottom hulls carry their bottom area there "
            "and the vertical volume integration needs it as an endpoint.",
        )
    y = _half_breadths_at(table, draft)
    x = table.stations
    dx = float(x[1] - x[0])
    aw = 2.0 * simpson(y, dx)
    moment = 2.0 * simpson(y * x, dx)
    lcf_m = moment / aw
    ix = 2.0 * simpson(y**3 / 3.0, dx)
    iy_midship = 2.0 * simpson(y * (x - x[-1] / 2.0) ** 2, dx)
    iyf = iy_midship - aw * (lcf_m - x[-1] / 2.0) ** 2
    return aw, lcf_m, ix, iyf


def _half_breadths_at(table: OffsetsTable, draft: float) -> np.ndarray:
    """Half-breadths at an arbitrary draft, linearly interpolated in z.

    Between tabulated waterlines this is an O(dz^2) approximation of
    the true section slope; with 33 waterlines the error is far below
    the acceptance tolerances (documented stage-1 approximation).
    """
    return np.array(
        [np.interp(draft, table.waterlines, row) for row in table.half_breadths]
    )


# ---------------------------------------------------------------------------
# Even-keel hydrostatics (vertical integration, Ship Theory vol. 1, ch. 3)
# ---------------------------------------------------------------------------


def hydrostatics_at(
    table: OffsetsTable,
    draft: float,
    density: float = SEAWATER_DENSITY,
) -> Hydrostatics:
    """Full even-keel hydrostatic particulars at one draft.

    Args:
        table: offsets grid.
        draft: even-keel draft, m (within the tabulated waterlines).
        density: water density, t/m^3 (default seawater, AGENTS.md 1).

    Returns:
        Hydrostatics (the task-1.1 container).
    """
    if not np.isfinite(density) or density <= 0:
        raise SpecValidationError(
            "density", density, "finite density > 0",
            "water density converts volumes to masses via Archimedes' "
            "principle; a non-positive density is unphysical.",
        )
    aw, lcf_m, ix, iyf = waterplane(table, draft)

    # vertical integration over a fine draft grid (even intervals)
    n_intervals = 64
    z = np.linspace(0.0, draft, n_intervals + 1)
    aw_z = np.array([waterplane(table, zi)[0] for zi in z])
    dz = float(z[1] - z[0])
    grad = simpson(aw_z, dz)
    moment_z = simpson(aw_z * z, dz)
    kb = moment_z / grad

    # midship section area for Cm (Simpson in draft at the midship station)
    mid = table.half_breadths.shape[0] // 2  # 21 stations -> index 10
    y_mid_z = np.array(
        [np.interp(zi, table.waterlines, table.half_breadths[mid]) for zi in z]
    )
    section_area = 2.0 * simpson(y_mid_z, dz)

    # volume centre of buoyancy from the sectional areas (Bonjean path):
    # LCB = integral A(x)*x dx / integral A(x) dx, Ship Theory vol. 1 ch. 3
    x = table.stations
    dx = float(x[1] - x[0])
    section_areas = np.array(
        [
            2.0 * simpson(
                np.array([
                    np.interp(zi, table.waterlines, row) for zi in z
                ]),
                dz,
            )
            for row in table.half_breadths
        ]
    )
    volume_x = simpson(section_areas, dx)
    moment_x = simpson(section_areas * x, dx)
    lcb_m = moment_x / volume_x

    lpp = float(table.stations[-1])
    beam = float(table.beam)
    displacement = density * grad
    bml = iyf / grad
    return Hydrostatics(
        draft=draft,
        displacement_volume=grad,
        displacement=displacement,
        aw=aw,
        lcf=(lcf_m - lpp / 2.0) / lpp * 100.0,  # % Lpp, forward positive
        cb=grad / (lpp * beam * draft),
        cm=section_area / (beam * draft),
        cp=(grad / (lpp * beam * draft)) / (section_area / (beam * draft)),
        cw=aw / (lpp * beam),
        kb=kb,
        bmt=ix / grad,
        bml=bml,
        tpc=density * aw / 100.0,
        mtc=displacement * bml / (100.0 * lpp),
        lcb=(lcb_m - lpp / 2.0) / lpp * 100.0,  # % Lpp, forward positive
    )


def hydrostatics_table(
    table: OffsetsTable,
    drafts: np.ndarray | list[float],
    density: float = SEAWATER_DENSITY,
) -> HydrostaticsTable:
    """Hydrostatic particulars at an increasing set of drafts.

    Args:
        table: offsets grid.
        drafts: strictly increasing drafts, m, all within the waterlines.
        density: water density, t/m^3.

    Returns:
        HydrostaticsTable (the task-1.1 container).
    """
    values = [float(d) for d in drafts]
    if len(values) < 2 or any(b <= a for a, b in zip(values, values[1:])):
        raise SpecValidationError(
            "drafts", values, "at least two strictly increasing drafts",
            "a hydrostatic table is a function of draft: duplicated or "
            "out-of-order drafts break interpolation and plotting.",
        )
    return HydrostaticsTable(
        entries=[hydrostatics_at(table, d, density) for d in values]
    )


# ---------------------------------------------------------------------------
# Bonjean interface (plan task 2.2 preview)
# ---------------------------------------------------------------------------


def bonjean_areas(table: OffsetsTable) -> tuple[np.ndarray, np.ndarray]:
    """Section areas up to each waterline (Bonjean numbers).

    Integrates each station's half-breadths vertically with Simpson's
    rule.  Simpson in draft needs an even interval count from the keel,
    so areas are returned at every SECOND tabulated waterline.

    Returns:
        (levels, areas): levels (Nw_odd,) waterline heights, m; areas
        (Ns, Nw_odd) immersed section areas, m^2.
    """
    levels = table.waterlines[::2]
    areas = np.zeros((table.half_breadths.shape[0], levels.size))
    for i, row in enumerate(table.half_breadths):
        # j = 0 is the keel waterline: the integral up to zero height is 0
        for j in range(1, levels.size):
            prefix = row[: 2 * j + 1]
            dz = float(table.waterlines[1] - table.waterlines[0])
            areas[i, j] = 2.0 * simpson(prefix, dz)
    return levels, areas
