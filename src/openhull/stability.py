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
    "free_surface_arm",
    "initial_stability",
    "InitialStability",
    "floating_position",
    "FloatingPosition",
    "TrimStep",
    "gz_curve",
    "GZCurveResult",
    "GZPoint",
    "intact_stability_criteria",
    "StabilityCriteriaResult",
    "GZCriterion",
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
        length / breadth / height: optional moulded tank dimensions, m.
            The large-angle free-surface arm of sec. 5-4 shifts the
            actual liquid volume, so it needs the physical prism; the
            initial-GM correction of Eq. (4-38) runs on i_x alone.
    """

    name: str
    i_x: float
    liquid_density: float
    i_y: float | None = None
    length: float | None = None
    breadth: float | None = None
    height: float | None = None

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
        for attr in ("length", "breadth", "height"):
            value = getattr(self, attr)
            if value is not None and (
                not math.isfinite(value) or value <= 0
            ):
                raise SpecValidationError(
                    attr, value, f"finite {attr} > 0",
                    "a tank prism dimension must be positive; the "
                    "sec. 5-4 liquid shift moves the physical volume.",
                )

    @classmethod
    def rectangular(
        cls, name: str, length: float, breadth: float,
        liquid_density: float = 1.0, height: float | None = None,
    ) -> "Tank":
        """Rectangular tank: i_x = l*b^3/12, i_y = b*l^3/12 (ch. 2).

        ``height`` is optional for the initial-GM correction but
        required by the large-angle free-surface arm (sec. 5-4).
        """
        for attr, value in (("length", length), ("breadth", breadth)):
            if not math.isfinite(value) or value <= 0:
                raise SpecValidationError(
                    attr, value, f"finite {attr} > 0",
                    "a tank dimension must be positive; the free-surface "
                    "inertias scale with l*b^3 and b*l^3.",
                )
        if height is not None and (not math.isfinite(height) or height <= 0):
            raise SpecValidationError(
                "height", height, "finite height > 0",
                "the tank depth bounds the liquid prism; the sec. 5-4 "
                "shift needs a positive moulded height.",
            )
        return cls(
            name=name,
            i_x=length * breadth**3 / 12.0,
            liquid_density=liquid_density,
            i_y=breadth * length**3 / 12.0,
            length=length,
            breadth=breadth,
            height=height,
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


# ---------------------------------------------------------------------------
# Intact stability criteria: IMO 2008 IS Code Part A 2.2 (plan task 3.5)
# ---------------------------------------------------------------------------


def free_surface_arm(
    tanks: tuple[Tank, ...], displacement: float, angle_deg: float,
) -> float:
    """Free-surface influence on the stability arm at one heel.

    Ship Theory vol. 1, sec. 5-4: delta_l = M_H/Delta with the liquid
    shifting moment M_H = sum(w1 * V * y_shift).  Tanks are treated as
    prismatic rectangular prisms (length/breadth/height define the
    liquid volume exactly); the liquid sits at 50 % of the tank volume
    per the sec. 5-4 worst-case rule, so its surface passes through the
    tank centre — any line through the centre of a centrally symmetric
    section bisects the area, which pins the surface without
    iteration.  The shifted liquid centroid comes from the same exact
    polygon machinery as the GZ curve.

    Args:
        tanks: tanks with free surfaces; each needs length, breadth
            and height (construct via ``Tank.rectangular(..., height=)``).
        displacement: ship displacement Delta, t.
        angle_deg: heel angle phi, degrees (0 allowed; the arm is 0).

    Returns:
        delta_l, metres to subtract from every GZ of the curve.

    Raises:
        SpecValidationError: displacement non-positive, angle out of
            range, or a tank without its physical prism dimensions.
    """
    if not math.isfinite(displacement) or displacement <= 0:
        raise SpecValidationError(
            "displacement", displacement, "finite Delta > 0",
            "the liquid moment divides by the ship displacement "
            "(delta_l = M_H/Delta).",
        )
    if (
        not math.isfinite(angle_deg) or angle_deg < 0.0
        or angle_deg > GZ_MAX_ANGLE_DEG
    ):
        raise SpecValidationError(
            "angle_deg", angle_deg,
            f"0 <= phi <= {GZ_MAX_ANGLE_DEG} deg",
            "the free-surface arm follows the same heel range as the "
            "stability curve itself.",
        )
    moment = 0.0
    for tank in tanks:
        dims = (tank.length, tank.breadth, tank.height)
        if any(dim is None for dim in dims):
            raise SpecValidationError(
                "tanks", tank.name,
                "length, breadth and height set",
                "the sec. 5-4 arm shifts the actual liquid volume, so "
                f"tank '{tank.name}' needs its physical prism; "
                "construct it via Tank.rectangular(..., height=...).",
            )
        length, breadth, height = (float(d) for d in dims)
        ring = [
            (-breadth / 2.0, 0.0), (breadth / 2.0, 0.0),
            (breadth / 2.0, height), (-breadth / 2.0, height),
        ]
        tan_phi = math.tan(math.radians(angle_deg))
        area, cy, _cz = _area_centroid(
            _clip_below_line(ring, height / 2.0, tan_phi)
        )
        moment += tank.liquid_density * area * length * cy
    return moment / displacement


@dataclass(frozen=True)
class GZCriterion:
    """One evaluated stability criterion (JSON-serializable).

    Attributes:
        criterion_id: the rule section, e.g. "IS Code 2.2.1(a)".
        description: plain-ASCII statement of the requirement.
        required: the required value.
        unit: the unit of both required and actual.
        actual: the value computed for this loading condition.
        passed: actual satisfies required.
    """

    criterion_id: str
    description: str
    required: float
    unit: str
    actual: float
    passed: bool


@dataclass(frozen=True)
class StabilityCriteriaResult:
    """Verdict of the general intact stability criteria (JSON-ready).

    Attributes:
        rule: the rule identification string.
        displacement_t / kg_m / density: the loading condition, t / m /
            t/m^3.
        gm0_m: free-surface-corrected initial metacentric height, m.
        free_surface_correction_m: sum(w1*i_x)/Delta applied, m.
        flooding_angle_deg: down-flooding angle used, degrees (None =
            none declared; areas run to 30/40 deg).
        criteria: one :class:`GZCriterion` per checked requirement.
        area_angles_deg / area_arms_m: the corrected-arm curve the
            areas were integrated on (0..40 deg, fine step).
        all_passed: True when every criterion passed.
        notes: declared assumptions and integration details.
    """

    rule: str
    displacement_t: float
    kg_m: float
    density: float
    gm0_m: float
    free_surface_correction_m: float
    flooding_angle_deg: float | None
    criteria: tuple[GZCriterion, ...]
    area_angles_deg: tuple[float, ...]
    area_arms_m: tuple[float, ...]
    all_passed: bool
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "displacement_t": self.displacement_t,
            "kg_m": self.kg_m,
            "density": self.density,
            "gm0_m": self.gm0_m,
            "free_surface_correction_m": self.free_surface_correction_m,
            "flooding_angle_deg": self.flooding_angle_deg,
            "criteria": [asdict(c) for c in self.criteria],
            "area_angles_deg": list(self.area_angles_deg),
            "area_arms_m": list(self.area_arms_m),
            "all_passed": self.all_passed,
            "notes": list(self.notes),
        }


#: fine angle grid (degrees) the criterion areas integrate on: 0..40 in
#: 2.5 deg steps (16 intervals, Simpson-ready; a flooding angle inside a
#: step closes the last panel trapezoidally)
_CRITERIA_STEP_DEG = 2.5


def intact_stability_criteria(
    table: OffsetsTable,
    displacement_t: float,
    kg_m: float,
    depth_m: float,
    density: float = 1.025,
    *,
    flooding_angle_deg: float | None = None,
    tanks: tuple[Tank, ...] = (),
) -> StabilityCriteriaResult:
    """General intact stability criteria, IMO 2008 IS Code Part A 2.2.

    Text verified verbatim (AGENTS.md section 5 whitelist): 2.2.1 area
    under the GZ curve >= 0.055 m*rad up to 30 deg, >= 0.09 m*rad up
    to 40 deg or the down-flooding angle if less, >= 0.03 m*rad
    between 30 and 40 deg (or to the flooding angle); 2.2.2 a static
    lever of at least 0.2 m at 30 deg or greater; 2.2.3 the maximum
    lever at 25 deg or greater; 2.2.4 GM0 >= 0.15 m.

    Args:
        table: offsets grid of the hull.
        displacement_t: ship displacement Delta, t.
        kg_m: centre of gravity above keel, m.
        depth_m: deck-at-side height for the section closure, m (see
            :func:`gz_curve`).
        density: water density, t/m^3.
        flooding_angle_deg: down-flooding angle of the first
            non-weathertight opening, degrees; None when none is
            declared (the areas then run to 30/40 deg).
        tanks: free-surface tanks; the arm curve is corrected by the
            sec. 5-4 delta_l and GM0 by Eq. (4-38).

    Returns:
        StabilityCriteriaResult with one verdict per criterion.

    Raises:
        SpecValidationError: inputs out of range (see :func:`gz_curve`
            and :func:`free_surface_arm`).
    """
    if flooding_angle_deg is not None and (
        not math.isfinite(flooding_angle_deg)
        or not 0.0 < flooding_angle_deg <= GZ_MAX_ANGLE_DEG
    ):
        raise SpecValidationError(
            "flooding_angle_deg", flooding_angle_deg,
            f"0 < phi_f <= {GZ_MAX_ANGLE_DEG} deg",
            "the down-flooding angle bounds the effective part of the "
            "stability curve; a value outside the computed heel range "
            "cannot be honoured.",
        )

    # GM0 at the even-keel draft of the condition (KM from the
    # stage-1.4 hydrostatics; free-surface correction Eq. 4-38)
    top_waterline = float(table.waterlines[-1])
    lo_z, hi_z = 0.0, top_waterline
    for _ in range(60):
        mid = 0.5 * (lo_z + hi_z)
        if hydrostatics_at(table, mid, density).displacement < displacement_t:
            lo_z = mid
        else:
            hi_z = mid
    draft = 0.5 * (lo_z + hi_z)
    km = hydrostatics_at(table, draft, density).km
    fsc = free_surface_correction(tanks, displacement_t)
    gm0 = km - kg_m - fsc

    # corrected arm curve: full range for the 2.2.3 characteristic, a
    # fine grid for the 2.2.1 areas (delta_l per sec. 5-4 when tanks
    # are given)
    def corrected_arm(arm: float, angle_deg: float) -> float:
        return arm - free_surface_arm(tanks, displacement_t, angle_deg)

    full = gz_curve(table, displacement_t, kg_m, depth_m, density)
    full_corrected = [
        corrected_arm(p.gz_m, p.angle_deg) for p in full.points
    ]
    fine_angles = [
        _CRITERIA_STEP_DEG * i for i in range(1, 17)
    ]  # 2.5 .. 40 deg
    fine = gz_curve(
        table, displacement_t, kg_m, depth_m, density,
        angles_deg=tuple(fine_angles),
    )
    grid_angles = [0.0] + list(fine_angles)
    grid_arms = [0.0] + [
        corrected_arm(p.gz_m, p.angle_deg) for p in fine.points
    ]
    grid_rad = [math.radians(a) for a in grid_angles]

    def area_to(ceiling_deg: float) -> float:
        """Area under the corrected arm curve up to a ceiling, m*rad:
        Simpson over the even count of full 2.5 deg panels, trapezoid
        on the terminal partial panel when the ceiling falls inside (or
        leaves an odd) panel."""
        ceiling = math.radians(ceiling_deg)
        step = grid_rad[1] - grid_rad[0]
        n_full = int(math.floor(round(ceiling / step, 9)))
        n_simpson = n_full if n_full % 2 == 0 else n_full - 1
        area = 0.0
        if n_simpson >= 2:
            area += simpson(np.asarray(grid_arms[:n_simpson + 1]), step)
        last = (
            n_simpson if n_simpson < len(grid_rad) - 1
            else len(grid_rad) - 1
        )
        if ceiling > grid_rad[last] + 1e-12:
            arm_ceiling = float(np.interp(ceiling, grid_rad, grid_arms))
            area += 0.5 * (grid_arms[last] + arm_ceiling) * (
                ceiling - grid_rad[last]
            )
        return area

    phi_f = flooding_angle_deg
    ceiling_b = min(40.0, phi_f) if phi_f is not None else 40.0
    criteria: list[GZCriterion] = []
    notes = [
        "areas integrated by Simpson on a 2.5 deg grid of the "
        "free-surface-corrected curve (trapezoid on any terminal "
        "partial panel)",
    ]

    area_a = area_to(min(30.0, ceiling_b))
    criteria.append(GZCriterion(
        criterion_id="IS Code 2.2.1(a)",
        description="GZ curve area from 0 to "
        f"{min(30.0, ceiling_b):.1f} deg",
        required=0.055, unit="m*rad", actual=area_a,
        passed=area_a >= 0.055,
    ))
    area_b = area_to(ceiling_b)
    criteria.append(GZCriterion(
        criterion_id="IS Code 2.2.1(b)",
        description="GZ curve area from 0 to "
        f"{ceiling_b:.1f} deg (40 deg or down-flooding angle)",
        required=0.09, unit="m*rad", actual=area_b,
        passed=area_b >= 0.09,
    ))
    if phi_f is None or phi_f > 30.0:
        ceiling_c = min(40.0, phi_f) if phi_f is not None else 40.0
        area_c = area_to(ceiling_c) - area_to(30.0)
        criteria.append(GZCriterion(
            criterion_id="IS Code 2.2.1(c)",
            description=f"GZ curve area from 30 to {ceiling_c:.1f} deg",
            required=0.03, unit="m*rad", actual=area_c,
            passed=area_c >= 0.03,
        ))
    else:
        notes.append(
            f"down-flooding at {phi_f:.1f} deg precedes 30 deg: "
            "criterion 2.2.1(c) has no interval and is not evaluated"
        )

    # 2.2.2: a static lever of at least 0.2 m at 30 deg or greater
    # (when the ship floods before 30 deg, judged up to that angle)
    if phi_f is not None and phi_f < 30.0:
        arms_window = [
            arm for a, arm in zip(grid_angles, grid_arms)
            if a <= phi_f + 1e-9
        ]
        window_text = f"up to {phi_f:.1f} deg (down-flooding)"
    else:
        arms_window = [
            arm for a, arm in zip(grid_angles, grid_arms)
            if a >= 30.0 - 1e-9
        ]
        window_text = "at 30 deg or greater"
    lever = max(arms_window)
    criteria.append(GZCriterion(
        criterion_id="IS Code 2.2.2",
        description=f"static lever {window_text}",
        required=0.2, unit="m", actual=lever, passed=lever >= 0.2,
    ))

    # 2.2.3: the maximum lever at 25 deg or greater (full curve).  With
    # no tanks the curve's own 0.25 deg-refined angle is used directly;
    # a free-surface correction moves the maximum, so it is then
    # re-located on the corrected grid arms.
    if tanks:
        angle_max = full.points[
            full_corrected.index(max(full_corrected))
        ].angle_deg
    else:
        angle_max = full.angle_max_deg
    criteria.append(GZCriterion(
        criterion_id="IS Code 2.2.3",
        description="heel angle of the maximum lever (full curve)",
        required=25.0, unit="deg", actual=angle_max,
        passed=angle_max >= 25.0,
    ))
    if angle_max == full.points[-1].angle_deg:
        notes.append(
            "the corrected arm still rises at the last computed angle: "
            "the reported maximum angle is a lower bound"
        )

    # 2.2.4: initial metacentric height
    criteria.append(GZCriterion(
        criterion_id="IS Code 2.2.4",
        description="initial metacentric height GM0 (free-surface "
        "corrected, Eq. 4-38)",
        required=0.15, unit="m", actual=gm0, passed=gm0 >= 0.15,
    ))

    return StabilityCriteriaResult(
        rule="IMO 2008 IS Code, Part A, 2.2 (resolution MSC.267(85))",
        displacement_t=displacement_t,
        kg_m=kg_m,
        density=density,
        gm0_m=gm0,
        free_surface_correction_m=fsc,
        flooding_angle_deg=phi_f,
        criteria=tuple(criteria),
        area_angles_deg=tuple(grid_angles),
        area_arms_m=tuple(grid_arms),
        all_passed=all(c.passed for c in criteria),
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# Severe wind and rolling criterion: IS Code part A 2.3 (plan task 3.5b)
# ---------------------------------------------------------------------------

#: wind pressure of the criterion, Pa (2.3.2; A.562(14): 0.0514 t/m2).
#: Restricted-service reductions are an Administration matter - pass a
#: reduced value explicitly if the task book calls for one.
WEATHER_WIND_PRESSURE_PA = 504.0

#: gust factor of 2.3.1.3: l_w2 = 1.5 * l_w1 (formula image, verbatim)
WEATHER_GUST_FACTOR = 1.5

# factor tables of 2.3.4 with linear interpolation between rows (the
# <=/>= end rows clamp).  X1 values from A.562(14) table 1, which
# carries the B/d = 3.3 -> 0.84 row the imorules reproduction omits.
_X1_TABLE = (
    (2.4, 1.0), (2.5, 0.98), (2.6, 0.96), (2.7, 0.95), (2.8, 0.93),
    (2.9, 0.91), (3.0, 0.90), (3.1, 0.88), (3.2, 0.86), (3.3, 0.84),
    (3.4, 0.82), (3.5, 0.80),
)
_X2_TABLE = (
    (0.45, 0.75), (0.50, 0.82), (0.55, 0.89), (0.60, 0.95),
    (0.65, 0.97), (0.70, 1.00),
)
_K_TABLE = (
    (0.0, 1.0), (1.0, 0.98), (1.5, 0.95), (2.0, 0.88),
    (2.5, 0.79), (3.0, 0.74), (3.5, 0.72), (4.0, 0.70),
)
_S_TABLE = (
    (6.0, 0.100), (7.0, 0.098), (8.0, 0.093), (12.0, 0.065),
    (14.0, 0.053), (16.0, 0.044), (18.0, 0.038), (20.0, 0.035),
)

#: hard cap of the theta_2 definition: min(down-flooding, 50 deg, theta_c)
_THETA2_CAP_DEG = 50.0


def _interp_table(table: tuple[tuple[float, float], ...], x: float) -> float:
    """Linear interpolation into a criterion factor table; the <=/>=
    end rows clamp (2.3.4: intermediate values interpolate linearly)."""
    if x <= table[0][0]:
        return table[0][1]
    for (x0, v0), (x1, v1) in zip(table, table[1:]):
        if x <= x1:
            return v0 + (v1 - v0) * (x - x0) / (x1 - x0)
    return table[-1][1]


@dataclass(frozen=True)
class WeatherCriterionResult:
    """Severe wind and rolling criterion verdict (JSON-ready).

    Every intermediate of the 2.3 chain is reported so the verdict can
    be audited: the wind levers, the roll data (T, C, X1, X2, k, r, s,
    phi_1), the steady-wind heel and its limits, the roll-back angle,
    the areas and the three criterion verdicts.
    """

    rule: str
    displacement_t: float
    kg_m: float
    density: float
    windage_area_m2: float
    windage_lever_z_m: float
    wind_pressure_pa: float
    length_waterline_m: float
    beam_m: float
    draft_m: float
    cb: float
    gm0_m: float
    b_over_d: float
    lw1_m: float
    lw2_m: float
    roll_period_s: float
    c_coefficient: float
    x1: float
    x2: float
    k_factor: float
    r_factor: float
    s_factor: float
    phi1_deg: float
    phi0_deg: float
    deck_edge_angle_deg: float
    roll_back_deg: float
    theta2_deg: float
    area_a_mrad: float
    area_b_mrad: float
    criteria: tuple[GZCriterion, ...]
    all_passed: bool
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "displacement_t": self.displacement_t,
            "kg_m": self.kg_m,
            "density": self.density,
            "windage_area_m2": self.windage_area_m2,
            "windage_lever_z_m": self.windage_lever_z_m,
            "wind_pressure_pa": self.wind_pressure_pa,
            "length_waterline_m": self.length_waterline_m,
            "beam_m": self.beam_m,
            "draft_m": self.draft_m,
            "cb": self.cb,
            "gm0_m": self.gm0_m,
            "b_over_d": self.b_over_d,
            "lw1_m": self.lw1_m,
            "lw2_m": self.lw2_m,
            "roll_period_s": self.roll_period_s,
            "c_coefficient": self.c_coefficient,
            "x1": self.x1,
            "x2": self.x2,
            "k_factor": self.k_factor,
            "r_factor": self.r_factor,
            "s_factor": self.s_factor,
            "phi1_deg": self.phi1_deg,
            "phi0_deg": self.phi0_deg,
            "deck_edge_angle_deg": self.deck_edge_angle_deg,
            "roll_back_deg": self.roll_back_deg,
            "theta2_deg": self.theta2_deg,
            "area_a_mrad": self.area_a_mrad,
            "area_b_mrad": self.area_b_mrad,
            "criteria": [asdict(c) for c in self.criteria],
            "all_passed": self.all_passed,
            "notes": list(self.notes),
        }


def weather_criterion(
    table: OffsetsTable,
    displacement_t: float,
    kg_m: float,
    depth_m: float,
    density: float = 1.025,
    *,
    windage_area_m2: float,
    windage_lever_z_m: float,
    wind_pressure_pa: float = WEATHER_WIND_PRESSURE_PA,
    bilge_keel_area_m2: float = 0.0,
    length_waterline_m: float | None = None,
    flooding_angle_deg: float | None = None,
    tanks: tuple[Tank, ...] = (),
    angle_step_deg: float = 1.25,
) -> WeatherCriterionResult:
    """Severe wind and rolling criterion, IMO 2008 IS Code part A 2.3.

    Sequence of 2.3.1: steady wind lever l_w1 heels the ship to phi_0
    (limited to 16 deg or 80 % of the deck-edge immersion angle); the
    ship rolls to windward by the wave angle phi_1 of 2.3.4; the gust
    lever l_w2 = 1.5 l_w1 then acts.  The areas follow the normative
    figure: a = integral of (l_w1 - GZ) from the roll-back angle
    theta_1 = phi_0 - phi_1 to phi_0 (GZ continued to negative heel by
    odd symmetry - Ship Theory vol. 1, sec. 5-5(6)), b = integral of
    (GZ - l_w2) from the rising intercept of l_w2 with the GZ curve to
    theta_2 = min(down-flooding, 50 deg, falling intercept).  The ship
    survives when b >= a.

    Args:
        table: offsets grid of the hull.
        displacement_t: ship displacement Delta, t.
        kg_m: centre of gravity above keel, m.
        depth_m: deck-at-side height for the section closure, m.
        density: water density, t/m^3.
        windage_area_m2: A, projected lateral area of the ship and
            deck cargo above the waterline, m^2 (task-book input).
        windage_lever_z_m: Z, vertical distance from the centre of A
            to a point at one half the mean draught, m (task-book
            input).
        wind_pressure_pa: P, Pa (504 worldwide; reduced values for
            restricted service are an Administration decision).
        bilge_keel_area_m2: A_k total area of bilge keels (or bar-keel
            lateral projection), m^2; 0 gives the round-bilge k = 1.0.
        length_waterline_m: Lwl for the C coefficient; defaults to the
            table Lpp (declared in the notes when used).
        flooding_angle_deg: down-flooding angle, degrees; None when
            none is declared (the 50 deg cap then usually governs).
        tanks: free-surface tanks (the GM of the rolling period is the
            free-surface-corrected GM, and the arm curve is corrected).
        angle_step_deg: heel grid of the arm curve, degrees.

    Returns:
        WeatherCriterionResult with every intermediate and the three
        verdicts (b >= a, phi_0 <= 16 deg, phi_0 <= 80 % deck edge).

    Raises:
        SpecValidationError: inputs out of range, the 2.3.5
            applicability bounds (B/d < 3.5, KG/d - 1 in -0.3..0.5,
            T < 20 s) are violated, or GM0 is not positive.
        RuntimeError: the steady-wind lever exceeds the maximum
            restoring lever (no equilibrium heel exists).
    """
    if not math.isfinite(windage_area_m2) or windage_area_m2 <= 0:
        raise SpecValidationError(
            "windage_area_m2", windage_area_m2, "finite A > 0",
            "the wind heeling lever l_w1 = P*A*Z/(1000*g*Delta) acts on "
            "the projected lateral area; without it no wind moment "
            "exists.",
        )
    if not math.isfinite(windage_lever_z_m) or windage_lever_z_m <= 0:
        raise SpecValidationError(
            "windage_lever_z_m", windage_lever_z_m, "finite Z > 0",
            "Z distances the centre of the windage area from the "
            "underwater lateral centre (about half the draught).",
        )
    if not math.isfinite(wind_pressure_pa) or not 0 < wind_pressure_pa <= 504:
        raise SpecValidationError(
            "wind_pressure_pa", wind_pressure_pa, "0 < P <= 504 Pa",
            "the criterion's full-sea pressure is 504 Pa (2.3.2); "
            "reduced restricted-service values need the task book to "
            "say so explicitly.",
        )
    if bilge_keel_area_m2 < 0:
        raise SpecValidationError(
            "bilge_keel_area_m2", bilge_keel_area_m2, ">= 0",
            "a negative bilge-keel area has no physical meaning.",
        )
    if flooding_angle_deg is not None and (
        not math.isfinite(flooding_angle_deg)
        or not 0.0 < flooding_angle_deg <= GZ_MAX_ANGLE_DEG
    ):
        raise SpecValidationError(
            "flooding_angle_deg", flooding_angle_deg,
            f"0 < phi_f <= {GZ_MAX_ANGLE_DEG} deg",
            "the down-flooding angle bounds theta_2 of the criterion.",
        )

    top_waterline = float(table.waterlines[-1])
    if depth_m < top_waterline:
        raise SpecValidationError(
            "depth", depth_m, f">= top tabulated waterline "
            f"({top_waterline} m)",
            "the deck closes every section from above (see gz_curve).",
        )

    # the condition's even-keel draft and form data
    lo_z, hi_z = 0.0, top_waterline
    for _ in range(60):
        mid = 0.5 * (lo_z + hi_z)
        if hydrostatics_at(table, mid, density).displacement < displacement_t:
            lo_z = mid
        else:
            hi_z = mid
    draft = 0.5 * (lo_z + hi_z)
    hydro = hydrostatics_at(table, draft, density)
    fsc = free_surface_correction(tanks, displacement_t)
    gm0 = hydro.km - kg_m - fsc
    beam = float(table.beam)
    b_over_d = beam / draft

    notes: list[str] = []
    if length_waterline_m is None:
        length_waterline_m = float(table.lpp)
        notes.append(
            "no Lwl in the task book: the rolling-period coefficient "
            "uses Lpp as Lwl (declared approximation)"
        )
    lwl = float(length_waterline_m)

    # 2.3.5 applicability: B/d < 3.5, (KG/d - 1) in -0.3..0.5
    kg_over_d_minus_1 = kg_m / draft - 1.0
    if not b_over_d < 3.5:
        raise SpecValidationError(
            "B/d", b_over_d, "< 3.5 (IS Code 2.3.5)",
            "the roll-angle formulae are based on ships with B/d below "
            "3.5; outside the band MSC.1/Circ.1200 model experiments "
            "are the alternative.",
        )
    if not -0.3 <= kg_over_d_minus_1 <= 0.5:
        raise SpecValidationError(
            "KG/d - 1", kg_over_d_minus_1, "-0.3 .. 0.5 (IS Code 2.3.5)",
            "the roll-angle formulae are based on ships inside this "
            "gravity-height band; outside it MSC.1/Circ.1200 model "
            "experiments are the alternative.",
        )
    if not math.isfinite(gm0) or gm0 <= 0:
        raise SpecValidationError(
            "GM0", gm0, "> 0",
            "the rolling period T = 2*C*B/sqrt(GM) needs a positive "
            "free-surface-corrected initial stability.",
        )

    # 2.3.4: rolling period, factors and the roll angle phi_1
    c_coeff = 0.373 + 0.023 * b_over_d - 0.043 * (lwl / 100.0)
    roll_period = 2.0 * c_coeff * beam / math.sqrt(gm0)
    if not roll_period < 20.0:
        raise SpecValidationError(
            "T", roll_period, "< 20 s (IS Code 2.3.5)",
            "the roll-angle formulae are based on ships with rolling "
            "periods below 20 s; MSC.1/Circ.1200 model experiments are "
            "the alternative.",
        )
    x1 = _interp_table(_X1_TABLE, b_over_d)
    x2 = _interp_table(_X2_TABLE, hydro.cb)
    if bilge_keel_area_m2 > 0:
        k_factor = _interp_table(
            _K_TABLE, 100.0 * bilge_keel_area_m2 / (lwl * beam)
        )
    else:
        k_factor = 1.0  # round-bilged ship having no bilge or bar keels
    r_factor = 0.73 + 0.6 * (kg_m / draft - 1.0)  # OG = KG - d
    s_factor = _interp_table(_S_TABLE, roll_period)
    phi1 = 109.0 * k_factor * x1 * x2 * math.sqrt(r_factor * s_factor)

    # 2.3.2: wind heeling levers (g = 9.81 m/s^2, AGENTS.md section 1)
    lw1 = (
        wind_pressure_pa * windage_area_m2 * windage_lever_z_m
        / (1000.0 * 9.81 * displacement_t)
    )
    lw2 = WEATHER_GUST_FACTOR * lw1

    # arm curve on a fine uniform grid; GZ(-theta) = -GZ(theta) by the
    # odd symmetry of the static stability curve (sec. 5-5(6))
    step = float(angle_step_deg)
    n_steps = int(round(GZ_MAX_ANGLE_DEG / step))
    fine_angles = [step * i for i in range(1, n_steps + 1)]
    fine = gz_curve(
        table, displacement_t, kg_m, depth_m, density,
        angles_deg=tuple(fine_angles),
    )
    grid_angles = [0.0] + list(fine_angles)
    grid_arms = [0.0] + [
        p.gz_m - free_surface_arm(tanks, displacement_t, p.angle_deg)
        for p in fine.points
    ]
    full_angles = [-a for a in reversed(grid_angles)] + grid_angles[1:]
    full_arms = [-v for v in reversed(grid_arms)] + grid_arms[1:]

    def first_crossing(level: float) -> float:
        """Rising intercept of the arm curve with a constant lever."""
        for a0, v0, a1, v1 in zip(
            grid_angles, grid_arms, grid_angles[1:], grid_arms[1:]
        ):
            if v0 < level <= v1:
                return a0 + (a1 - a0) * (level - v0) / (v1 - v0)
        raise RuntimeError(
            f"the arm curve never reaches the lever {level:.4f} m "
            f"within {GZ_MAX_ANGLE_DEG:.0f} deg: the ship has no "
            "equilibrium heel under this wind - the weather criterion "
            "cannot be evaluated (the vessel capsizes statically)."
        )

    def last_crossing(level: float) -> float | None:
        """Falling intercept after the peak, None if the curve stays
        above the level to the end of the grid."""
        result: float | None = None
        for a0, v0, a1, v1 in zip(
            grid_angles, grid_arms, grid_angles[1:], grid_arms[1:]
        ):
            if v0 >= level > v1:
                result = a0 + (a1 - a0) * (level - v0) / (v1 - v0)
        return result

    phi0 = first_crossing(lw1)

    rings = [
        _section_polygon(row, table.waterlines, depth_m)
        for row in table.half_breadths
    ]
    stations_array = np.asarray(table.stations, dtype=float)

    def deck_immersed(phi_deg: float) -> bool:
        """True when the equal-volume waterline at this heel touches
        the deck at side at any station (wall-sided topside)."""
        tan_phi = math.tan(math.radians(phi_deg))
        z_i, _, _, _, _, _ = _equal_volume_crossing(
            rings, stations_array,
            displacement_t, density, tan_phi, depth_m,
            GZ_VOLUME_TOLERANCE, 30, draft,
        )
        return any(
            depth_m <= z_i + float(row[-1]) * tan_phi
            for row in table.half_breadths
        )

    lo_phi, hi_phi = 0.0, float(fine_angles[-1])
    if deck_immersed(hi_phi):
        for _ in range(12):  # 80 deg / 2^12 < 0.02 deg
            mid = 0.5 * (lo_phi + hi_phi)
            if deck_immersed(mid):
                hi_phi = mid
            else:
                lo_phi = mid
        deck_edge_angle = hi_phi
    else:
        deck_edge_angle = float("inf")
        notes.append(
            "the deck edge never immerses within the computed heel "
            "range: the 80 % deck-edge limit is not active"
        )

    # area a: roll-up energy against l_w1, from theta_1 to phi_0
    roll_back = phi0 - phi1
    if roll_back < -GZ_MAX_ANGLE_DEG:
        raise SpecValidationError(
            "theta_1", roll_back,
            f">= -{GZ_MAX_ANGLE_DEG:.0f} deg",
            "the roll-back angle leaves the computed arm curve; the "
            "roll angle phi_1 of 2.3.4 is implausibly large for this "
            "hull - check the inputs.",
        )
    selected_a = [
        (a, v) for a, v in zip(full_angles, full_arms)
        if roll_back <= a <= phi0
    ]
    points_a = (
        [(roll_back, float(np.interp(roll_back, full_angles, full_arms)))]
        + selected_a
        + [(phi0, float(np.interp(phi0, full_angles, full_arms)))]
    )
    area_a = 0.0
    for (a0, v0), (a1, v1) in zip(points_a, points_a[1:]):
        area_a += 0.5 * ((lw1 - v0) + (lw1 - v1)) * math.radians(a1 - a0)

    # area b: between GZ and l_w2 from the rising intercept to theta_2
    rising = first_crossing(lw2)
    falling = last_crossing(lw2)
    ceiling = _THETA2_CAP_DEG
    if flooding_angle_deg is not None:
        ceiling = min(ceiling, flooding_angle_deg)
    if falling is not None:
        ceiling = min(ceiling, falling)
    selected_b = [
        (a, v) for a, v in zip(grid_angles, grid_arms)
        if rising <= a <= ceiling
    ]
    points_b = (
        [(rising, lw2)]
        + selected_b
        + [(ceiling, float(np.interp(ceiling, grid_angles, grid_arms)))]
    )
    area_b = 0.0
    for (a0, v0), (a1, v1) in zip(points_b, points_b[1:]):
        area_b += 0.5 * ((v0 - lw2) + (v1 - lw2)) * math.radians(a1 - a0)

    criteria = [
        GZCriterion(
            criterion_id="IS Code 2.3.1 area b >= a",
            description="severe wind and rolling: area between GZ and "
            "the gust lever vs roll-up area against the steady lever",
            required=area_a, unit="m*rad", actual=area_b,
            passed=area_b >= area_a,
        ),
        GZCriterion(
            criterion_id="IS Code 2.3.1 steady heel",
            description="steady-wind heel angle phi_0",
            required=16.0, unit="deg", actual=phi0, passed=phi0 <= 16.0,
        ),
        GZCriterion(
            criterion_id="IS Code 2.3.1 deck edge",
            description="steady-wind heel vs 80 % of the deck-edge "
            "immersion angle",
            required=0.8 * deck_edge_angle, unit="deg", actual=phi0,
            passed=phi0 <= 0.8 * deck_edge_angle,
        ),
    ]

    return WeatherCriterionResult(
        rule="IMO 2008 IS Code, Part A, 2.3 (resolution MSC.267(85))",
        displacement_t=displacement_t,
        kg_m=kg_m,
        density=density,
        windage_area_m2=windage_area_m2,
        windage_lever_z_m=windage_lever_z_m,
        wind_pressure_pa=wind_pressure_pa,
        length_waterline_m=lwl,
        beam_m=beam,
        draft_m=draft,
        cb=hydro.cb,
        gm0_m=gm0,
        b_over_d=b_over_d,
        lw1_m=lw1,
        lw2_m=lw2,
        roll_period_s=roll_period,
        c_coefficient=c_coeff,
        x1=x1,
        x2=x2,
        k_factor=k_factor,
        r_factor=r_factor,
        s_factor=s_factor,
        phi1_deg=phi1,
        phi0_deg=phi0,
        deck_edge_angle_deg=deck_edge_angle,
        roll_back_deg=roll_back,
        theta2_deg=ceiling,
        area_a_mrad=area_a,
        area_b_mrad=area_b,
        criteria=tuple(criteria),
        all_passed=all(c.passed for c in criteria),
        notes=tuple(notes),
    )
