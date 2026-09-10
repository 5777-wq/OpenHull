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

Large-angle stability (GZ curves, IS Code criteria) is plan task 3.4
and 3.5, out of scope here.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

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
    "BUOYANCY_TOLERANCE",
    "LCG_TOLERANCE",
]

#: convergence bounds of Eq.(3-27), lower bounds adopted
BUOYANCY_TOLERANCE = 0.001
LCG_TOLERANCE = 0.0005


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
