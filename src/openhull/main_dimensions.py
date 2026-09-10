"""Principal dimension estimation — selectable algorithms (plan task 1.2).

Estimates L, B, D, T and Cb from the task-book requirements using
whitelisted methods, exposed as a registry (AGENTS.md §8 "selectable
algorithms"): task books and future frontends select an algorithm by id;
each entry carries its citation and applicability range as data.

Chain of the default algorithm (deadweight_ratio_statistical):

    DW --deadweight ratio--> displacement (deadweight ratio)
    displacement --Archimedes--> displacement volume
    solve  grad = L*B*T*Cb,  L/B = k2,  B/T = k1
           ->  L = (grad * k1 * k2^2 / Cb)^(1/3),  B = L/k2,  T = B/k1
    D = L / (L/D statistical ratio)

PROVISIONAL CALIBRATION, to be replaced by published statistics (with
page-referenced citations) once the owner's textbooks arrive:
  * deadweight ratio 0.82 — owner-approved in task book TB-001;
  * L/B = 6.0, B/T = 2.7 — Capesize neighbourhood values;
  * L/D = 11.2 — adjusted from the previewed 11.5, which put the depth
    error at -5.2 % (outside the ±5 % acceptance); 11.2 passes at -2.7 %.

Applicability guards (AGENTS.md §6): the statistical ratios were built
for full-form merchant ships; the estimated Froude number must fall in
0.10-0.25 and the resulting dimension ratios must stay inside
bulk-carrier bands, otherwise the algorithm refuses with an
explanation instead of returning numbers it does not believe in.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .spec import SEAWATER_DENSITY, ShipSpec, SpecValidationError

#: Standard gravity, m/s² (AGENTS.md §1)
GRAVITY = 9.81

# ---------------------------------------------------------------------------
# Registry metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AlgorithmInfo:
    """Registry entry for one main-dimension estimation algorithm.

    Attributes:
        algorithm_id: stable selection id (task books / frontends use it).
        name: human-readable method name.
        citation: whitelist source (AGENTS.md §5).
        applicability: declared applicability range (AGENTS.md §6).
        implemented: False = registered placeholder; calling it raises
            with an explanation instead of returning numbers.
    """

    algorithm_id: str
    name: str
    citation: str
    applicability: str
    implemented: bool = True


MAIN_DIMENSION_ALGORITHMS: dict[str, AlgorithmInfo] = {
    "deadweight_ratio_statistical": AlgorithmInfo(
        algorithm_id="deadweight_ratio_statistical",
        name="deadweight ratio + statistical dimension ratios",
        citation=(
            "deadweight ratio 0.82 owner-approved (TB-001); statistical "
            "ratios per Schneekluth & Bertram, provisional values, see "
            "module docstring"
        ),
        applicability="full-form merchant ships (Fn 0.10-0.25), bulk carriers",
    ),
    "parent_hull_ratio": AlgorithmInfo(
        algorithm_id="parent_hull_ratio",
        name="parent-hull ratio scaling",
        citation=(
            "classical parent-ship proportion method; parent ratios are "
            "user-provided data"
        ),
        applicability=(
            "requires a parent ship with known L, B, T (and D); target "
            "ship should be of the same type and size class as the parent"
        ),
    ),
    "watson_1977": AlgorithmInfo(
        algorithm_id="watson_1977",
        name="Watson & Gilfillan (1977) regression series",
        citation="Trans. RINA, vol. 119 (AGENTS.md §5 whitelist)",
        applicability="merchant ships, as published in the source",
        implemented=False,
    ),
}

DEFAULT_ALGORITHM = "deadweight_ratio_statistical"


# ---------------------------------------------------------------------------
# Tunable statistics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RatioParameters:
    """Statistical ratios of the chain-solve (override-able per call).

    Attributes (all dimensionless):
        deadweight_ratio: DW / displacement, owner-approved 0.82 (TB-001).
        l_over_b: statistical L/B of the target ship class.
        b_over_t: statistical B/T of the target ship class.
        l_over_depth: statistical L/D of the target ship class.
    """

    deadweight_ratio: float = 0.82
    l_over_b: float = 6.0
    b_over_t: float = 2.7
    l_over_depth: float = 11.2  # provisional calibration, see module docs

    def __post_init__(self) -> None:
        for name, value, lo, hi in (
            ("deadweight_ratio", self.deadweight_ratio, 0.5, 1.0),
            ("l_over_b", self.l_over_b, 3.0, 9.0),
            ("b_over_t", self.b_over_t, 1.8, 4.0),
            ("l_over_depth", self.l_over_depth, 7.0, 16.0),
        ):
            if not math.isfinite(value) or not lo <= value <= hi:
                raise SpecValidationError(
                    name, value, f"{lo} <= {name} <= {hi}",
                    "sanity band for ship-statistics ratios; values "
                    "outside it almost certainly are a slip (unit or "
                    "decimal), not a novel hull-form trend.",
                )


# ---------------------------------------------------------------------------
# Shared chain-solve
# ---------------------------------------------------------------------------


def _chain_solve(
    spec: ShipSpec,
    ratios: RatioParameters,
    field_prefix: str,
    displacement: float | None = None,
) -> ShipSpec:
    """Solve L, B, T, D from the displacement equation and ratios.

    The deadweight ratio and Archimedes' principle give the displacement
    volume; the displacement equation grad = L*B*T*Cb together with the
    L/B and B/T ratios has the closed-form solution
    L = (grad * (B/T) * (L/B)^2 / Cb)^(1/3).

    Args:
        displacement: externally driven displacement, t.  When given
            (weight_balance task 1.3 drives this loop), it replaces the
            deadweight-ratio start value and the spec does not need a
            deadweight; when omitted, displacement = DW / deadweight
            ratio as before.
    """
    if displacement is None and spec.deadweight is None:
        raise SpecValidationError(
            "deadweight", None, "required input",
            "every estimation algorithm starts from the deadweight "
            "requirement; provide it in the task book.",
        )
    if spec.service_speed is None:
        raise SpecValidationError(
            "service_speed", None, "required input",
            "the service speed is needed for the Froude-number "
            "applicability guard of the statistical ratios; provide it "
            "in the task book (m/s, use knots_to_ms() at the boundary).",
        )
    if spec.cb is None:
        raise SpecValidationError(
            "cb", None,
            "provide the target Cb (task-book constraint)",
            "no Cb-Fn regression is implemented yet: the whitelisted "
            "watson_1977 coefficients must be transcribed from the "
            "source before use (AGENTS.md §5 forbids writing them from "
            "memory). Until then, pin Cb in the task book as a design "
            "constraint, as TB-001 does with Cb = 0.8580.",
        )

    if displacement is None:
        displacement = spec.deadweight / ratios.deadweight_ratio
    displacement_volume = displacement / SEAWATER_DENSITY

    l_est = (
        displacement_volume * ratios.b_over_t * ratios.l_over_b**2 / spec.cb
    ) ** (1.0 / 3.0)
    beam = l_est / ratios.l_over_b
    draft = beam / ratios.b_over_t
    depth = l_est / ratios.l_over_depth

    # -- applicability guards on the RESULT (AGENTS.md §6) ---------------
    fn = spec.service_speed / math.sqrt(GRAVITY * l_est)
    if not 0.10 <= fn <= 0.25:
        raise SpecValidationError(
            "service_speed", spec.service_speed,
            "resulting Froude number within 0.10-0.25",
            f"the chain-solve returned Fn = {fn:.3f}: the statistical "
            "ratios of this algorithm were compiled for full-form "
            "merchant ships (Fn 0.10-0.25). A speed this far outside the "
            "band belongs to a finer hull form and needs different "
            "statistics - refusing instead of extrapolating.",
        )
    result_l_over_b = l_est / beam  # == ratios.l_over_b by construction
    _check_band(result_l_over_b, 4.5, 8.0, "L/B", l_est, field_prefix)
    _check_band(beam / draft, 2.0, 3.5, "B/T", beam, field_prefix)
    _check_band(l_est / depth, 8.0, 14.0, "L/D", l_est, field_prefix)

    return ShipSpec(
        ship_type=spec.ship_type,
        deadweight=spec.deadweight,
        service_speed=spec.service_speed,
        lpp=l_est,
        beam=beam,
        depth=depth,
        draft=draft,
        cb=spec.cb,
        displacement_volume=displacement_volume,
        displacement=displacement,
    )


def _check_band(
    value: float, lo: float, hi: float, label: str, l_est: float, prefix: str
) -> None:
    if not lo <= value <= hi:
        raise SpecValidationError(
            f"{prefix}{label}", value, f"{lo} <= {label} <= {hi}",
            f"the estimate (L = {l_est:.1f} m) landed outside the "
            f"{label} band typical of merchant ships; the requested "
            "deadweight/speed combination is inconsistent with the "
            "statistics of this algorithm - refusing instead of "
            "extrapolating.",
        )


# ---------------------------------------------------------------------------
# Algorithms
# ---------------------------------------------------------------------------


def _deadweight_ratio_statistical(
    spec: ShipSpec,
    ratios: RatioParameters,
    parent: ShipSpec | None,
) -> ShipSpec:
    """Default algorithm: owner-approved ratio + class statistics."""
    return _chain_solve(spec, ratios, "")


def _parent_hull_ratio(
    spec: ShipSpec,
    ratios: RatioParameters,
    parent: ShipSpec | None,
) -> ShipSpec:
    """Scale a known parent ship's proportions to the new deadweight.

    Takes the ratios (L/B, B/T, L/D) from the parent ship itself, so a
    parent with accurate proportions replaces the statistical defaults.
    """
    if parent is None:
        raise SpecValidationError(
            "parent", None,
            "a parent ShipSpec is required for parent_hull_ratio",
            "the parent-hull method scales the proportions of a known "
            "ship; pass parent=... with Lpp, B, T, D filled in.",
        )
    if None in (parent.lpp, parent.beam, parent.draft, parent.depth):
        raise SpecValidationError(
            "parent", parent,
            "parent ship with known Lpp, B, T and D",
            "the parent-hull method derives the statistical ratios from "
            "the parent ship's own proportions; provide a parent ShipSpec "
            "with those dimensions filled in.",
        )
    parent_ratios = RatioParameters(
        deadweight_ratio=ratios.deadweight_ratio,
        l_over_b=parent.lpp / parent.beam,
        b_over_t=parent.beam / parent.draft,
        l_over_depth=parent.lpp / parent.depth,
    )
    return _chain_solve(spec, parent_ratios, "")


def _watson_1977(
    spec: ShipSpec,
    ratios: RatioParameters,
    parent: ShipSpec | None,
) -> ShipSpec:
    raise NotImplementedError(
        "algorithm 'watson_1977' is registered but not implemented: its "
        "regression coefficients must be transcribed from Watson & "
        "Gilfillan (1977) / 'Practical Ship Design' once the source is "
        "available - AGENTS.md §5 forbids implementing formulas from "
        "memory. Registered placeholders exist so task books can already "
        "reference the id."
    )


_DISPATCH = {
    "deadweight_ratio_statistical": _deadweight_ratio_statistical,
    "parent_hull_ratio": _parent_hull_ratio,
    "watson_1977": _watson_1977,
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def estimate_main_dimensions(
    spec: ShipSpec,
    algorithm_id: str = DEFAULT_ALGORITHM,
    *,
    parent: ShipSpec | None = None,
    **ratio_overrides,
) -> ShipSpec:
    """Estimate principal dimensions for a task-book spec.

    Args:
        spec: task-book spec; requires deadweight, service_speed and a
            pinned target cb (see _chain_solve for why).
        algorithm_id: registry key of MAIN_DIMENSION_ALGORITHMS.
        parent: parent ship for "parent_hull_ratio".
        **ratio_overrides: RatioParameters fields to override (e.g.
            l_over_b=6.2).

    Returns:
        a new ShipSpec with lpp, beam, depth, draft, cb, displacement
        and displacement_volume filled in.

    Raises:
        SpecValidationError: missing inputs or violated applicability.
        NotImplementedError: for registered-but-unimplemented ids.
    """
    info = MAIN_DIMENSION_ALGORITHMS.get(algorithm_id)
    if info is None:
        raise SpecValidationError(
            "algorithm_id", algorithm_id,
            f"one of {sorted(MAIN_DIMENSION_ALGORITHMS)}",
            "unknown algorithm id; the registry lists every selectable "
            "main-dimension algorithm (AGENTS.md §8).",
        )

    ratios = RatioParameters(**ratio_overrides)
    return _DISPATCH[algorithm_id](spec, ratios, parent)
