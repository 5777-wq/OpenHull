"""Initial stability and the floating attitude (plan task 1.5).

Two services, both on top of the task-1.4 hydrostatics:

1. Initial stability (Ship Theory vol. 1, ch. 4):
     GM = KB + BM - KG                        Eq. (4-19)
     GM = KM - KG                             (KM = KB + BM)
     GM_1 = GM - sum(w1*i_x)/Delta            Eq. (4-38), free surfaces
   with the free-surface correction w1*i_x/Delta per tank (Eqs. 4-35 to
   4-38; w1 = liquid density, i_x = transverse inertia of the free
   surface) and the longitudinal counterpart with i_y, Eq. (4-37).

2. Floating attitude under a given weight and LCG — the iterative
   even-keel/trim balance of Ship Structural Strength (Zhang & Zhang,
   National Defense Industry Press, 2024), section 3.2.2:
     first approximation                      Eqs. (3-25)
     successive approximation of the drafts   Eqs. (3-26)
     convergence |W - B|/W <= (0.1-0.5) %,    Eq. (3-27)
                |xg - xb|/L <= (0.05-0.1) %
   The lower bounds (0.1 % and 0.05 %) are adopted as the defaults.

The design-draft GM check against JBC is arithmetic on top of the KM
anchor (KM was fitted to GM + KG in task 1.4, so the GM number itself
is a consistency check, declared in the task-book notes).  The
NON-circular validation of this module is the JBC ballast condition
[NMRI]: displacement volume 89,185.9 m3 at drafts 10.015 / 7.215 m
(aft/fore) — drafts never used in any fit — reproduced through the
trim iteration.

Large-angle stability — the static stability curve l(phi) — is also
here (plan task 3.4, Ship Theory vol. 1 ch. 5): Eq. (5-1)
l = l_s - l_g = (y_Bphi*cos(phi) + z_Bphi*sin(phi)) - KG*sin(phi),
computed on the equal-displacement (direct) method of section 5-2:
per heel angle the equal-volume heeled waterline is found by iterating
its centreline crossing z_i (update z_i += dDelta/(w*A_Wphi), the
book's computer procedure) until |Delta - Delta_phi| <= 0.1 % of Delta.
Per-station immersed areas and moments are the Vlasov integrals of
section 3-5, Eq. (3-41), realized by direct polygon clipping of the
tabulated sections (the book sanctions numerical integration, p. 46).
Curve characteristics (maximum arm and angle, vanishing angle, dynamic
stability arm T_R = Delta*integral(l dphi), section 5-6) accompany the
curve; the origin slope equals GM (section 5-5), which the test suite
asserts as an identity.  Free-surface influence on the curve (section
5-4) is deferred to plan task 3.5.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

import numpy as np

from .geometry import OffsetsTable
from .hydrostatics import hydrostatics_at, simpson
from .spec import SpecValidationError

__all__ = [
    "Tank",
    "free_surface_correction",
    "initial_stability",
    "InitialStability",
    "floating_position",
    "FloatingPosition",
    "TrimStep",
    "gz_curve",
    "GZCurveResult",
    "GZPoint",
    "BUOYANCY_TOLERANCE",
    "LCG_TOLERANCE",
    "GZ_VOLUME_TOLERANCE",
    "GZ_MAX_ANGLE_DEG",
]

#: convergence bounds of Eq.(3-27), lower bounds adopted
BUOYANCY_TOLERANCE = 0.001
LCG_TOLERANCE = 0.0005

#: equal-volume waterline convergence |Delta - Delta_phi|/Delta <= eps
#: (Ship Theory vol. 1, sec. 5-2: eps "usually 0.1 % of Delta")
GZ_VOLUME_TOLERANCE = 0.001

#: upper bound of the heel sequence (sec. 5-2: sea ships computed to
#: 70...80 deg; trim coupling is neglected from sec. 5-1 onwards)
GZ_MAX_ANGLE_DEG = 80.0


# ---------------------------------------------------------------------------
# Initial stability (Ship Theory vol. 1, ch. 4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Tank:
    """A liquid tank with a free surface.

    Attributes:
        name: tank identifier (echoed in results).
        i_x: transverse moment of inertia of the free surface about its
            centreline axis, m^4 (integrand y^3/3, Ship Theory vol. 1
            ch. 2 conventions).
        liquid_density: w1, density of the liquid, t/m^3 (fresh water
            1.000, seawater 1.025 — AGENTS.md section 1).
        i_y: optional longitudinal inertia of the free surface, m^4
            (for the GML correction, Eq. 4-37).
    """

    name: str
    i_x: float
    liquid_density: float
    i_y: float | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise SpecValidationError(
                "name", self.name, "a non-empty string",
                "a tank without a name cannot be audited in the "
                "stability report.",
            )
        for attr in ("i_x", "liquid_density"):
            value = getattr(self, attr)
            if not math.isfinite(value) or value <= 0:
                raise SpecValidationError(
                    attr, value, f"finite {attr} > 0",
                    "a free-surface inertia and a liquid density are "
                    "physical positives; a non-positive value cannot "
                    "produce a correction.",
                )
        if self.i_y is not None and (
            not math.isfinite(self.i_y) or self.i_y <= 0
        ):
            raise SpecValidationError(
                "i_y", self.i_y, "finite i_y > 0",
                "the longitudinal free-surface inertia must be a "
                "positive area inertia when provided.",
            )

    @classmethod
    def rectangular(
        cls, name: str, length: float, breadth: float,
        liquid_density: float = 1.0,
    ) -> "Tank":
        """Rectangular tank: i_x = l*b^3/12, i_y = b*l^3/12 (ch. 2)."""
        for attr, value in (("length", length), ("breadth", breadth)):
            if not math.isfinite(value) or value <= 0:
                raise SpecValidationError(
                    attr, value, f"finite {attr} > 0",
                    "a tank dimension must be positive; the free-surface "
                    "inertias scale with l*b^3 and b*l^3.",
                )
        return cls(
            name=name,
            i_x=length * breadth**3 / 12.0,
            liquid_density=liquid_density,
            i_y=breadth * length**3 / 12.0,
        )


def free_surface_correction(
    tanks: tuple[Tank, ...], displacement: float,
) -> float:
    """sum(w1*i_x)/Delta — the GM correction of Eq.(4-38), metres.

    Args:
        tanks: tanks with free surfaces.
        displacement: ship displacement mass at the condition, t.
    """
    if not math.isfinite(displacement) or displacement <= 0:
        raise SpecValidationError(
            "displacement", displacement, "finite displacement > 0",
            "the free-surface correction divides by the displacement: "
            "Eq.(4-38) is undefined without a ship displacement.",
        )
    return sum(t.liquid_density * t.i_x for t in tanks) / displacement


@dataclass(frozen=True)
class InitialStability:
    """Initial stability at one condition (JSON-serializable).

    Attributes:
        draft: even-keel draft of the hydrostatics used, m.
        displacement: ship displacement, t.
        kg: centre of gravity above keel, m.
        km: transverse metacentre above keel (KB + BMT), m.
        gm_uncorrected: KM - KG, m (Eq. 4-19).
        free_surface_correction: sum(w1*i_x)/Delta, m (Eq. 4-38).
        gm: corrected initial stability height, m (GM_1 of Eq. 4-38).
        tank_contributions: (name, w1*i_x/Delta) per tank, metres.
    """

    draft: float
    displacement: float
    kg: float
    km: float
    gm_uncorrected: float
    free_surface_correction: float
    gm: float
    tank_contributions: tuple[tuple[str, float], ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft": self.draft,
            "displacement": self.displacement,
            "kg": self.kg,
            "km": self.km,
            "gm_uncorrected": self.gm_uncorrected,
            "free_surface_correction": self.free_surface_correction,
            "gm": self.gm,
            "tank_contributions": [
                [name, value] for name, value in self.tank_contributions
            ],
        }


def initial_stability(
    hydro,
    kg: float,
    tanks: tuple[Tank, ...] = (),
) -> InitialStability:
    """Initial stability height GM at one condition.

    Args:
        hydro: Hydrostatics record at the considered draft (task 1.4).
        kg: centre of gravity above keel, m.
        tanks: tanks with free surfaces (Eq. 4-38 correction).
    """
    if not math.isfinite(kg) or kg <= 0:
        raise SpecValidationError(
            "kg", kg, "finite KG > 0",
            "the centre of gravity height is a positive physical "
            "coordinate above the keel.",
        )
    fsc = free_surface_correction(tanks, hydro.displacement)
    contributions = tuple(
        (t.name, t.liquid_density * t.i_x / hydro.displacement)
        for t in tanks
    )
    gm_uncorrected = hydro.km - kg
    return InitialStability(
        draft=hydro.draft,
        displacement=hydro.displacement,
        kg=kg,
        km=hydro.km,
        gm_uncorrected=gm_uncorrected,
        free_surface_correction=fsc,
        gm=gm_uncorrected - fsc,
        tank_contributions=contributions,
    )


# ---------------------------------------------------------------------------
# Floating attitude: even-keel/trim balance (Eqs. 3-25/3-26/3-27)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrimStep:
    """One pass of the trim balance loop (audit trail).

    Attributes:
        iteration: 1-based pass number.
        draft_aft / draft_fore: moulded drafts at AP / FP, m.
        buoyancy_t: buoyancy of the trial waterline, t.
        lcb_pct: buoyancy centre, % Lpp forward positive.
        buoyancy_residual: |W - B|/W of this pass.
        lcg_residual: |xg - xb|/L of this pass.
    """

    iteration: int
    draft_aft: float
    draft_fore: float
    buoyancy_t: float
    lcb_pct: float
    buoyancy_residual: float
    lcg_residual: float


@dataclass(frozen=True)
class FloatingPosition:
    """Converged floating attitude (JSON-serializable).

    Attributes:
        converged: True when both Eq.(3-27) criteria are met.
        iterations: passes executed.
        displacement_t: weight W placed on the hull, t.
        lcg_m: longitudinal centre of gravity from the AP, m.
        draft_aft / draft_fore: moulded drafts at AP / FP, m.
        draft_mean: mean of the two, m.
        trim_m: draft_fore - draft_aft, m (positive = bow trim).
        lcb_pct: buoyancy centre, % Lpp forward positive.
        buoyancy_residual: final |W - B|/W.
        lcg_residual: final |xg - xb|/L.
        steps: per-pass audit trail.
    """

    converged: bool
    iterations: int
    displacement_t: float
    lcg_m: float
    draft_aft: float
    draft_fore: float
    draft_mean: float
    trim_m: float
    lcb_pct: float
    buoyancy_residual: float
    lcg_residual: float
    steps: tuple[TrimStep, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "converged": self.converged,
            "iterations": self.iterations,
            "displacement_t": self.displacement_t,
            "lcg_m": self.lcg_m,
            "draft_aft": self.draft_aft,
            "draft_fore": self.draft_fore,
            "draft_mean": self.draft_mean,
            "trim_m": self.trim_m,
            "lcb_pct": self.lcb_pct,
            "buoyancy_residual": self.buoyancy_residual,
            "lcg_residual": self.lcg_residual,
            "steps": [asdict(s) for s in self.steps],
        }


def _section_area(
    table: OffsetsTable, row: np.ndarray, draft: float,
) -> float:
    """Immersed section area at one station and draft (Simpson in draft)."""
    z = np.linspace(0.0, draft, 65)
    y = np.array([np.interp(zi, table.waterlines, row) for zi in z])
    dz = float(z[1] - z[0])
    return 2.0 * simpson(y, dz)


def _buoyancy_of_waterline(
    table: OffsetsTable, draft_aft: float, draft_fore: float,
    density: float,
) -> tuple[float, float]:
    """Buoyancy mass (t) and its centre x_b (m) for a trimmed waterline."""
    x = table.stations
    lpp = float(x[-1])
    local_drafts = draft_aft + (draft_fore - draft_aft) * x / lpp
    areas = np.array([
        _section_area(table, row, float(d))
        for row, d in zip(table.half_breadths, local_drafts)
    ])
    dx = float(x[1] - x[0])
    volume = simpson(areas, dx)
    xb = simpson(areas * x, dx) / volume
    return density * volume, xb


def floating_position(
    table: OffsetsTable,
    displacement_t: float,
    lcg_m: float,
    density: float = 1.025,
    *,
    buoyancy_tolerance: float = BUOYANCY_TOLERANCE,
    lcg_tolerance: float = LCG_TOLERANCE,
    max_iterations: int = 30,
) -> FloatingPosition:
    """Balance weight and buoyancy including trim (Eqs. 3-25/3-26).

    Args:
        table: offsets grid (task 1.4 geometry).
        displacement_t: total weight W = displacement, t.
        lcg_m: longitudinal centre of gravity from the AP, m.
        density: water density, t/m^3.
        buoyancy_tolerance: |W-B|/W bound (Eq. 3-27, lower bound 0.1 %).
        lcg_tolerance: |xg-xb|/L bound (Eq. 3-27, lower bound 0.05 %).
        max_iterations: hard cap; exceeding it aborts with an error.

    Returns:
        FloatingPosition with the converged drafts and audit trail.

    Raises:
        SpecValidationError: inputs out of range, or drafts leaving the
            tabulated waterline range (no geometry there).
        RuntimeError: no convergence within max_iterations.
    """
    if not math.isfinite(displacement_t) or displacement_t <= 0:
        raise SpecValidationError(
            "displacement", displacement_t, "finite W > 0",
            "the weight to float must be positive; W <= 0 floats "
            "nothing.",
        )
    lpp = float(table.stations[-1])
    if not math.isfinite(lcg_m) or not 0.0 < lcg_m < lpp:
        raise SpecValidationError(
            "lcg", lcg_m, f"0 < LCG < Lpp ({lpp} m)",
            "the centre of gravity is a centroid of the ship's weight "
            "and must lie within the length.",
        )
    if not 0.0 < buoyancy_tolerance < 0.05 or not 0.0 < lcg_tolerance < 0.01:
        raise SpecValidationError(
            "buoyancy_tolerance", buoyancy_tolerance,
            "0 < buoyancy tolerance < 5 %, 0 < lcg tolerance < 1 %",
            "looser convergence bounds would report an unbalanced ship "
            "as balanced; Eq.(3-27) works with fractions of a percent.",
        )

    # first approximation (Eq. 3-25 starts from the even-keel draft):
    # even-keel draft whose displacement equals the weight, by bisection
    lo, hi = float(table.waterlines[0]), float(table.waterlines[-1])
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if hydrostatics_at(table, mid, density).displacement < displacement_t:
            lo = mid
        else:
            hi = mid
    d_mean = 0.5 * (lo + hi)

    hydro_mean = hydrostatics_at(table, d_mean, density)
    xb = hydro_mean.lcb / 100.0 * lpp + lpp / 2.0
    x_f_m = hydro_mean.lcf / 100.0 * lpp + lpp / 2.0  # LCF from the AP
    lever = lcg_m - xb
    # Eqs.(3-25) written in AP-origin coordinates: the waterline rotates
    # about the LCF, so the draft change at position x is (x - x_f)*theta
    # with theta = (xg - xb)/R — at the FP that is (L - x_f)*theta, at
    # the AP -(x_f)*theta (the book's (L/2 -+ x_f) with midship origin).
    draft_aft = d_mean - x_f_m * lever / hydro_mean.bml
    draft_fore = d_mean + (lpp - x_f_m) * lever / hydro_mean.bml

    steps: list[TrimStep] = []
    buoyancy = 0.0
    lcb_pct = 0.0
    converged = False
    for pass_no in range(1, max_iterations + 1):
        buoyancy, xb = _buoyancy_of_waterline(
            table, draft_aft, draft_fore, density
        )
        lcb_pct = (xb - lpp / 2.0) / lpp * 100.0
        res_b = abs(displacement_t - buoyancy) / displacement_t
        res_l = abs(lcg_m - xb) / lpp
        steps.append(
            TrimStep(
                iteration=pass_no, draft_aft=draft_aft, draft_fore=draft_fore,
                buoyancy_t=buoyancy, lcb_pct=lcb_pct,
                buoyancy_residual=res_b, lcg_residual=res_l,
            )
        )
        if res_b <= buoyancy_tolerance and res_l <= lcg_tolerance:
            converged = True
            break

        mean_trial = min(0.5 * (draft_aft + draft_fore), float(table.waterlines[-1]))
        hydro_mean = hydrostatics_at(table, mean_trial, density)
        rise = (displacement_t - buoyancy) / (density * hydro_mean.aw)
        lever = lcg_m - xb
        x_f_m = hydro_mean.lcf / 100.0 * lpp + lpp / 2.0
        draft_aft = draft_aft + rise - x_f_m * lever / hydro_mean.bml
        draft_fore = draft_fore + rise + (lpp - x_f_m) * lever / hydro_mean.bml
        if not (0.0 < draft_aft <= table.waterlines[-1]) or not (
            0.0 < draft_fore <= table.waterlines[-1]
        ):
            raise SpecValidationError(
                "draft", [draft_aft, draft_fore],
                f"0 < drafts <= {table.waterlines[-1]} m",
                "the trim iteration walked the waterline outside the "
                "tabulated range; the requested displacement/lcg "
                "combination is not floatable on this geometry.",
            )

    if not converged:
        raise RuntimeError(
            f"floating attitude did not converge within {max_iterations} "
            f"passes (last |W-B|/W = {steps[-1].buoyancy_residual:.4%}, "
            f"|xg-xb|/L = {steps[-1].lcg_residual:.4%}); refusing to "
            f"return an unbalanced floating position."
        )

    return FloatingPosition(
        converged=True, iterations=len(steps), displacement_t=displacement_t,
        lcg_m=lcg_m, draft_aft=draft_aft, draft_fore=draft_fore,
        draft_mean=0.5 * (draft_aft + draft_fore),
        trim_m=draft_fore - draft_aft,
        lcb_pct=lcb_pct, buoyancy_residual=steps[-1].buoyancy_residual,
        lcg_residual=steps[-1].lcg_residual, steps=tuple(steps),
    )


# ---------------------------------------------------------------------------
# Large-angle stability: the static stability curve (plan task 3.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GZPoint:
    """One converged point of the static stability curve.

    Attributes:
        angle_deg: heel angle phi, degrees (right heel positive).
        centreline_crossing_m: z_i, the equal-volume heeled waterline's
            crossing with the centreline, m (the iterated unknown).
        buoyancy_volume_m3: immersed volume at the converged waterline, m^3.
        volume_residual: |Delta - Delta_phi|/Delta at convergence.
        waterplane_area_m2: A_Wphi of the sec. 5-2 update formula, m^2
            (evaluated as dV/dz_i by central difference).
        yb_m / zb_m: centre of buoyancy B_phi(y_phi, z_phi), m.
        shape_arm_m: l_s = y_phi*cos(phi) + z_phi*sin(phi), m (Eq. 5-13).
        gz_m: l = l_s - KG*sin(phi), m (Eqs. 5-1/5-14).
        dynamic_arm_mrad: cumulative integral of l dphi from 0 to this
            angle, m*rad (sec. 5-6 dynamic stability, trapezoidal).
        iterations: equal-volume waterline passes consumed.
    """

    angle_deg: float
    centreline_crossing_m: float
    buoyancy_volume_m3: float
    volume_residual: float
    waterplane_area_m2: float
    yb_m: float
    zb_m: float
    shape_arm_m: float
    gz_m: float
    dynamic_arm_mrad: float
    iterations: int


@dataclass(frozen=True)
class GZCurveResult:
    """Static stability curve for one loading condition (JSON-ready).

    Attributes:
        displacement_t: ship displacement Delta, t.
        kg_m: centre of gravity above keel, m.
        density: water density, t/m^3.
        depth_m: deck-at-side height the sections were closed at, m.
        volume_tolerance: |Delta - Delta_phi|/Delta bound used.
        points: one :class:`GZPoint` per heel angle, ascending.
        gz_max_m: maximum restoring arm on the computed curve, m.
        angle_max_deg: heel angle of the maximum, degrees (located on a
            0.25 deg refinement scan around the coarse grid maximum).
        angle_vanishing_deg: vanishing angle phi_v (first zero beyond the
            maximum, bisected to 0.05 deg); None when the curve does not
            close within the computed angle range (reported "> 80 deg").
    """

    displacement_t: float
    kg_m: float
    density: float
    depth_m: float
    volume_tolerance: float
    points: tuple[GZPoint, ...]
    gz_max_m: float
    angle_max_deg: float
    angle_vanishing_deg: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "displacement_t": self.displacement_t,
            "kg_m": self.kg_m,
            "density": self.density,
            "depth_m": self.depth_m,
            "volume_tolerance": self.volume_tolerance,
            "points": [asdict(p) for p in self.points],
            "gz_max_m": self.gz_max_m,
            "angle_max_deg": self.angle_max_deg,
            "angle_vanishing_deg": self.angle_vanishing_deg,
        }


def _section_polygon(
    row: np.ndarray, waterlines: np.ndarray, depth: float,
) -> list[tuple[float, float]]:
    """Closed moulded section ring: starboard side up, deck across, port
    side down.  Above the top tabulated waterline the side runs
    wall-sided up to the deck at ``depth`` (declared approximation —
    the offsets grid ends at the design draft)."""
    starboard = [
        (float(y), float(z)) for y, z in zip(row, waterlines)
    ]
    ring = list(starboard)
    top = starboard[-1]
    if depth > top[1]:
        ring.append((top[0], depth))
    ring.extend((-y, z) for y, z in reversed(starboard))
    return ring


def _clip_below_line(
    ring: list[tuple[float, float]], z_i: float, tan_phi: float,
) -> list[tuple[float, float]]:
    """Sutherland-Hodgman clip against z - tan(phi)*y - z_i <= 0 (the
    immersed half-plane of the heeled waterline)."""
    out: list[tuple[float, float]] = []
    n = len(ring)
    for k in range(n):
        py, pz = ring[k]
        qy, qz = ring[(k + 1) % n]
        fp = pz - tan_phi * py - z_i
        fq = qz - tan_phi * qy - z_i
        if fp <= 0.0:
            out.append((py, pz))
            if fq > 0.0:
                r = fp / (fp - fq)
                out.append((py + (qy - py) * r, pz + (qz - pz) * r))
        elif fq <= 0.0:
            r = fp / (fp - fq)
            out.append((py + (qy - py) * r, pz + (qz - pz) * r))
    return out


def _area_centroid(
    ring: list[tuple[float, float]],
) -> tuple[float, float, float]:
    """Area and centroid of a closed ring (shoelace + first moments)."""
    if len(ring) < 3:
        return 0.0, 0.0, 0.0
    a = cy = cz = 0.0
    n = len(ring)
    for k in range(n):
        (y1, z1), (y2, z2) = ring[k], ring[(k + 1) % n]
        cross = y1 * z2 - y2 * z1
        a += cross
        cy += (y1 + y2) * cross
        cz += (z1 + z2) * cross
    a *= 0.5
    if abs(a) < 1e-12:
        return 0.0, 0.0, 0.0
    return a, cy / (6.0 * a), cz / (6.0 * a)


def _heel_volume(
    rings: list[list[tuple[float, float]]],
    stations: np.ndarray,
    z_i: float,
    tan_phi: float,
) -> tuple[float, float, float]:
    """Volume and centre of buoyancy under the heeled waterline
    z = z_i + y*tan(phi): the Vlasov integrals of Eq.(3-41) integrated
    along the length by Simpson (per-station immersed area and moments
    from exact polygon geometry, no draft-direction quadrature)."""
    dx = float(stations[1] - stations[0])
    areas = np.empty(stations.size)
    moments_y = np.empty(stations.size)
    moments_z = np.empty(stations.size)
    for i, ring in enumerate(rings):
        area, cy, cz = _area_centroid(_clip_below_line(ring, z_i, tan_phi))
        areas[i] = area
        moments_y[i] = area * cy
        moments_z[i] = area * cz
    volume = simpson(areas, dx)
    if volume <= 1e-12:
        return 0.0, 0.0, 0.0
    return (
        volume,
        simpson(moments_y, dx) / volume,
        simpson(moments_z, dx) / volume,
    )


def _equal_volume_crossing(
    rings: list[list[tuple[float, float]]],
    stations: np.ndarray,
    displacement_t: float,
    density: float,
    tan_phi: float,
    depth_m: float,
    volume_tolerance: float,
    max_iterations: int,
    z_init: float,
) -> tuple[float, float, float, float, float, int]:
    """Iterate the centreline crossing z_i to the equal-volume heeled
    waterline (sec. 5-2 computer procedure): the book's update
    z_i <- z_i + dDelta/(w*A_Wphi) with c = 1, falling back to bracket
    bisection when the Newton step leaves the bracket or stalls.

    Returns (z_i, volume, yb, zb, A_Wphi, iterations).
    """
    half_beam = 0.5 * max(
        abs(y) for ring in rings for y, _ in ring
    )
    lo, hi = 0.0, depth_m + half_beam * tan_phi + float(stations[-1])
    z = z_init
    worsening = 0
    previous = math.inf
    for iteration in range(1, max_iterations + 1):
        volume, yb, zb = _heel_volume(rings, stations, z, tan_phi)
        signed = density * volume - displacement_t
        residual = abs(signed) / displacement_t
        if residual <= volume_tolerance:
            step = max(1e-3, 1e-4 * depth_m)
            aw = (
                _heel_volume(rings, stations, z + step, tan_phi)[0]
                - _heel_volume(rings, stations, z - step, tan_phi)[0]
            ) / (2.0 * step)
            return z, volume, yb, zb, aw, iteration
        if signed < 0.0:  # too light: the waterline must rise
            lo = max(lo, z)
        else:  # too heavy: the waterline must fall
            hi = min(hi, z)
        if residual < previous:
            worsening = 0
        else:
            worsening += 1
        previous = residual
        if worsening < 2:  # the book's Newton step
            step = max(1e-3, 1e-4 * depth_m)
            aw = (
                _heel_volume(rings, stations, z + step, tan_phi)[0]
                - _heel_volume(rings, stations, z - step, tan_phi)[0]
            ) / (2.0 * step)
            if math.isfinite(aw) and aw > 1e-9:
                candidate = z - signed / (density * aw)
                if lo < candidate < hi:
                    z = candidate
                    continue
        z = 0.5 * (lo + hi)  # bisection fallback: always convergent
    raise RuntimeError(
        f"equal-volume heeled waterline did not converge within "
        f"{max_iterations} iterations (last |Delta-Delta_phi|/Delta = "
        f"{previous:.4%}); refusing to return an unconverged stability "
        f"point."
    )


def gz_curve(
    table: OffsetsTable,
    displacement_t: float,
    kg_m: float,
    depth_m: float,
    density: float = 1.025,
    *,
    angles_deg: Sequence[float] = tuple(range(10, 81, 10)),
    volume_tolerance: float = GZ_VOLUME_TOLERANCE,
    max_iterations: int = 30,
) -> GZCurveResult:
    """Static stability curve l(phi) for one loading condition.

    Equal-displacement (direct) method, Ship Theory vol. 1 sec. 5-2:
    per heel angle the equal-volume heeled waterline is iterated, the
    centre of buoyancy B_phi computed from the tabulated sections, and
    the restoring arm assembled from Eq.(5-1):
        l = (y_Bphi*cos(phi) + z_Bphi*sin(phi)) - KG*sin(phi).

    Args:
        table: offsets grid (stations x waterlines half-breadths, m).
        displacement_t: ship displacement Delta, t.
        kg_m: centre of gravity above keel KG, m.
        depth_m: deck-at-side height the sections are closed at, m;
            above the top tabulated waterline the sides run wall-sided
            up to this deck (declared approximation).  Must be >= the
            top waterline of the table.
        density: water density, t/m^3.
        angles_deg: heel sequence, degrees; the book's sea-ship default
            is 10...80 in steps of 10 (sec. 5-2).
        volume_tolerance: |Delta - Delta_phi|/Delta bound (eps of
            sec. 5-2, "usually 0.1 % of Delta").
        max_iterations: per-angle cap on the waterline iteration.

    Returns:
        GZCurveResult with the per-angle audit points, the maximum arm
        and its angle (0.25 deg refinement scan), the vanishing angle
        (bisected; None beyond the computed range), and the dynamic
        stability arm per point (sec. 5-6, trapezoidal, m*rad).

    Raises:
        SpecValidationError: inputs out of range (angle beyond the
            book's 0...80 deg, KG not between 0 and the deck, depth
            below the top waterline, displacement exceeding the hull
            volume to deck, non-Simpson station grid).
        RuntimeError: an equal-volume waterline failed to converge.
    """
    if not math.isfinite(displacement_t) or displacement_t <= 0:
        raise SpecValidationError(
            "displacement", displacement_t, "finite Delta > 0",
            "the loading condition displaces the hull; a non-positive "
            "displacement has no heeled waterline to balance.",
        )
    if not math.isfinite(kg_m) or kg_m <= 0:
        raise SpecValidationError(
            "kg", kg_m, "finite KG > 0",
            "the centre of gravity height is a positive coordinate "
            "above the keel; Eq.(5-1) subtracts KG*sin(phi) from the "
            "shape arm.",
        )
    if kg_m >= depth_m:
        raise SpecValidationError(
            "kg", kg_m, f"< deck at side ({depth_m} m)",
            "the centre of gravity sits at or above the deck: no real "
            "loading condition balances there, and the weight arm "
            "KG*sin(phi) of Eq.(5-1) would exceed every geometric arm "
            "the hull can offer.",
        )
    if not math.isfinite(depth_m) or depth_m <= 0:
        raise SpecValidationError(
            "depth", depth_m, "finite depth > 0",
            "the deck closes every section from above; without a "
            "positive deck height the section polygons are open.",
        )
    top_waterline = float(table.waterlines[-1])
    if depth_m < top_waterline:
        raise SpecValidationError(
            "depth", depth_m, f">= top tabulated waterline "
            f"({top_waterline} m)",
            "the offsets grid ends at the top tabulated waterline; a "
            "deck below it would clip away tabulated hull, a deck "
            "exactly there leaves no topside at all.",
        )
    if not math.isfinite(density) or density <= 0:
        raise SpecValidationError(
            "density", density, "finite rho > 0",
            "the equal-volume iteration converts displacement mass to "
            "volume through the density.",
        )
    if not 0.0 < volume_tolerance < 0.05:
        raise SpecValidationError(
            "volume_tolerance", volume_tolerance, "0 < eps < 5 %",
            "sec. 5-2 works with eps around 0.1 % of Delta; a looser "
            "bound would misplace every point of the curve.",
        )
    stations = np.asarray(table.stations, dtype=float)
    if stations.size % 2 == 0:
        raise SpecValidationError(
            "stations", stations.size, "an odd count (even intervals)",
            "Simpson integration along the length pairs up intervals; "
            "an even station count leaves an unpaired interval.",
        )
    dx = np.diff(stations)
    if not np.allclose(dx, dx[0], rtol=1e-9, atol=1e-9):
        raise SpecValidationError(
            "stations", stations, "equally spaced",
            "the longitudinal Simpson rule needs equal station "
            "spacing; resample the table first "
            "(geometry.load_offsets_csv does).",
        )

    angles = sorted({float(a) for a in angles_deg})
    if len(angles) < 2:
        raise SpecValidationError(
            "angles_deg", angles_deg, "at least two distinct angles",
            "curve characteristics (maximum, vanishing angle, dynamic "
            "arm) need a sequence of heel angles, not a single point.",
        )
    for angle in angles:
        if not math.isfinite(angle) or not 0.0 < angle <= GZ_MAX_ANGLE_DEG:
            raise SpecValidationError(
                "angles_deg", angle,
                f"0 < phi <= {GZ_MAX_ANGLE_DEG} deg",
                "sec. 5-2 computes sea-ship curves over 10...80 deg; "
                "beyond it the neglected trim coupling and the "
                "wall-sided topside stop being defensible, and at phi=0 "
                "the equal-volume waterline is simply the even keel.",
            )

    rings = [
        _section_polygon(row, table.waterlines, depth_m)
        for row in table.half_breadths
    ]
    # existence guard: even with the deck at the waterline the hull
    # cannot immerse more than its full volume (sec. 5-2: the fully
    # submerged hull is the end point of every l_s curve)
    full_volume = _heel_volume(rings, stations, math.inf, 0.0)[0]
    volume_target = displacement_t / density
    if volume_target > full_volume * (1.0 - 1e-9):
        raise SpecValidationError(
            "displacement", displacement_t,
            f"<= hull volume to deck ({full_volume:.1f} m^3 at this "
            f"density)",
            "even with the whole deck at the waterline the hull "
            "cannot immerse the requested displacement, so the "
            "equal-volume heeled waterline does not exist at any "
            "heel; the load case exceeds the ship.",
        )

    # initial value per sec. 5-2 step (2): the even-keel draft of the
    # condition, from the stage-1.4 hydrostatics
    lo_z, hi_z = 0.0, top_waterline
    for _ in range(60):
        mid = 0.5 * (lo_z + hi_z)
        if hydrostatics_at(table, mid, density).displacement < displacement_t:
            lo_z = mid
        else:
            hi_z = mid
    z_init = 0.5 * (lo_z + hi_z)

    arm_by_angle: dict[float, float] = {}
    points: list[GZPoint] = []
    cumulative = 0.0
    previous_arm = 0.0
    previous_angle = 0.0
    for angle in angles:
        phi = math.radians(angle)
        sin_phi, cos_phi = math.sin(phi), math.cos(phi)
        z_i, volume, yb, zb, aw, iterations = _equal_volume_crossing(
            rings, stations, displacement_t, density, sin_phi / cos_phi,
            depth_m, volume_tolerance, max_iterations, z_init,
        )
        shape_arm = yb * cos_phi + zb * sin_phi  # Eq. (5-13)
        arm = shape_arm - kg_m * sin_phi         # Eqs. (5-1)/(5-14)
        cumulative += (
            0.5 * (previous_arm + arm)
            * (phi - math.radians(previous_angle))
        )
        points.append(
            GZPoint(
                angle_deg=angle,
                centreline_crossing_m=z_i,
                buoyancy_volume_m3=volume,
                volume_residual=abs(
                    density * volume - displacement_t
                ) / displacement_t,
                waterplane_area_m2=aw,
                yb_m=yb,
                zb_m=zb,
                shape_arm_m=shape_arm,
                gz_m=arm,
                dynamic_arm_mrad=cumulative,
                iterations=iterations,
            )
        )
        arm_by_angle[angle] = arm
        previous_arm = arm
        previous_angle = angle

    # maximum: refine around the coarse grid peak on a 0.25 deg scan
    coarse_best = max(points, key=lambda p: p.gz_m)
    best_angle, best_arm = coarse_best.angle_deg, coarse_best.gz_m
    index = [p.angle_deg for p in points].index(coarse_best.angle_deg)
    span_lo = points[max(index - 1, 0)].angle_deg
    span_hi = points[min(index + 1, len(points) - 1)].angle_deg
    scan = span_lo + 0.25
    while scan < span_hi - 1e-9:
        if scan in arm_by_angle:
            scan += 0.25
            continue
        phi = math.radians(scan)
        sin_phi, cos_phi = math.sin(phi), math.cos(phi)
        z_i, volume, yb, zb, _, _ = _equal_volume_crossing(
            rings, stations, displacement_t, density, sin_phi / cos_phi,
            depth_m, volume_tolerance, max_iterations, z_init,
        )
        arm = (yb * cos_phi + zb * sin_phi) - kg_m * sin_phi
        arm_by_angle[scan] = arm
        if arm > best_arm:
            best_angle, best_arm = scan, arm
        scan += 0.25

    # vanishing angle: first zero crossing past the maximum, bisected
    ascending = sorted(arm_by_angle.items())
    vanishing: float | None = None
    for (a0, l0), (a1, l1) in zip(ascending, ascending[1:]):
        if a0 >= best_angle and l0 > 0.0 >= l1:
            lo_a, hi_a = a0, a1
            for _ in range(10):  # 10 deg / 2^10 < 0.01 deg
                mid_a = 0.5 * (lo_a + hi_a)
                phi = math.radians(mid_a)
                sin_phi, cos_phi = math.sin(phi), math.cos(phi)
                _, _, yb, zb, _, _ = _equal_volume_crossing(
                    rings, stations, displacement_t, density,
                    sin_phi / cos_phi, depth_m, volume_tolerance,
                    max_iterations, z_init,
                )
                if (yb * cos_phi + zb * sin_phi) - kg_m * sin_phi >= 0.0:
                    lo_a = mid_a
                else:
                    hi_a = mid_a
            vanishing = 0.5 * (lo_a + hi_a)
            break

    return GZCurveResult(
        displacement_t=displacement_t,
        kg_m=kg_m,
        density=density,
        depth_m=depth_m,
        volume_tolerance=volume_tolerance,
        points=tuple(points),
        gz_max_m=best_arm,
        angle_max_deg=best_angle,
        angle_vanishing_deg=vanishing,
    )
