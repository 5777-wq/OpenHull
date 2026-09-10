"""Weight-buoyancy balance iteration (plan task 1.3).

Solves the flotation equilibrium

    displacement Delta = deadweight DW + lightweight LW

where LW depends on the principal dimensions, which in turn depend on
Delta.  The loop (the first turn of the "design spiral") is:

    Delta_0 = DW / deadweight-ratio            (starting estimate)
    repeat:  dimensions from Delta_k   (main_dimensions chain, buoyancy
                                     equation grad = L*B*T*Cb)
             LW_k = f(dimensions)      (selectable algorithm below)
             Delta_{k+1} = DW + LW_k
    until |Delta_{k+1} - Delta_k| / Delta_{k+1} <= tolerance

The convergence criterion is the static-balance requirement of
"Ship Structural Strength" (Zhang & Zhang, National Defense Industry
Press, 2024), section 3.2.2, Eq.(3-27): |W - B|/W <= (0.1-0.5) %, of
which the lower bound 0.1 % is adopted here; for this fixed-point loop
the buoyancy B of pass k equals Delta_k, so the criterion is evaluated
as the relative step between successive displacements.

Algorithms (registry, AGENTS.md section 8):

  deadweight_ratio
      LW = DW * (1 - eta_DW) / eta_DW.
      Xie Yunping et al., "Ship Design Principles" (National Defense
      Industry Press), section 2.2.2, Eqs.(2-3)/(2-4); identical to Lin
      Yan, "Ship Design Principles" (4th ed., Dalian University of
      Technology Press), section 2.1.3, Eqs.(2-6)/(2-7) (cross-checked).
      eta_DW = 0.82 for TB-001 is owner-approved and lies inside the
      double-hull bulk-carrier band 0.78-0.86 of Lin Yan section 4.3.3
      Table 4-3.

  component_cubic  (default)
      Component estimation: steel W_H = C_H*L*B*D (cubic modulus, Xie
      section 2.2.2 Eq.(2-13); Lin Eq.(2-11)), outfit W_O = C_O*L*B
      (area modulus, Xie Eq.(2-42); the sources prefer the area form
      over the cubic form for cargo ships because deck machinery
      dominates outfit weight), machinery W_M = r_M*LW (weight-share
      residual, Xie Table 2-3: large cargo ships W_H/LW 0.61-0.68 and
      W_O/LW 0.17-0.23, machinery takes the remainder).  Hence
      LW = (C_H*L*B*D + C_O*L*B) / (1 - r_M).

  component_exponent
      Steel weight through the published exponent regression
      W_H = C_H5 * L^a * B^b * D^c * T^d * Cb^e with the bulk-carrier
      exponents (a, b, c, d, e) = (1.878, 0.695, -0.189, 0.158, 0.197)
      from Xie Table 2-4, Eq.(2-22); outfit and machinery as above.

Machinery formulas based on shaft power (Lin Eq.(2-34), Xie Eqs.(2-50)
and (2-51)) are deliberately NOT implemented: engine power is unknown
at this design stage (task 3.2) and writing those coefficients from
memory is forbidden by AGENTS.md section 5.

ANTI-OVERFIT DESIGN: every coefficient below is a *parent-ship input*,
never a universal constant.  The sources require calibration from a
close parent ship of the same type and size class; the calibration
helpers expose exactly that workflow.  The method (not the constants)
is validated against two independent published cases:

  * the worked example of Xie section 2.2.2: a 35,000 t bulk carrier
    (Lpp 178, B 30, D 15, Cb 0.815) whose parent (39,800 t, steel
    8,295 t) yields W_H = 7,384 t by the cubic modulus and 7,378 t by
    the exponent method - asserted in tests, zero circularity;
  * the TB-001/JBC closed loop (coefficients calibrated to the
    owner-approved JBC neighbourhood) reproducing the displacement
    anchor 182,829 t within 1 %.

Series 60 is not usable as a weight anchor: no lightweight data exist
in its public report (it is a resistance/offsets report), so it stays
the anchor for lines/hydrostatics stages instead.

Provisional calibration, declared per AGENTS.md rules: the TB-001
default coefficients below are derived from the owner-approved
displacement split (eta_DW = 0.82, Table 2-3 mid shares); they inherit
the circularity already declared in task 1.2 and are replaced by real
parent data as soon as the owner supplies them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .main_dimensions import RatioParameters, _chain_solve
from .spec import ShipSpec, SpecValidationError

# ---------------------------------------------------------------------------
# Registry metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WeightAlgorithmInfo:
    """Registry entry for one lightweight-estimation algorithm.

    Attributes:
        algorithm_id: stable selection id (task books / frontends use it).
        name: human-readable method name.
        citation: whitelist source (AGENTS.md section 5).
        applicability: declared applicability range (AGENTS.md section 6).
        implemented: False = registered placeholder; calling it raises
            with an explanation instead of returning numbers.
    """

    algorithm_id: str
    name: str
    citation: str
    applicability: str
    implemented: bool = True


WEIGHT_ALGORITHMS: dict[str, WeightAlgorithmInfo] = {
    "deadweight_ratio": WeightAlgorithmInfo(
        algorithm_id="deadweight_ratio",
        name="deadweight-ratio (carrying-capacity coefficient) method",
        citation=(
            "Xie Yunping et al., Ship Design Principles (National Defense "
            "Industry Press), section 2.2.2 Eqs.(2-3)(2-4); Lin Yan, Ship "
            "Design Principles 4th ed. (Dalian University of Technology "
            "Press), section 2.1.3 Eqs.(2-6)(2-7); eta_DW band: Lin Yan "
            "section 4.3.3 Table 4-3"
        ),
        applicability=(
            "initial design of deadweight-type ships (bulk carriers, "
            "tankers); rough by construction - all weights are assumed "
            "proportional to displacement"
        ),
    ),
    "component_cubic": WeightAlgorithmInfo(
        algorithm_id="component_cubic",
        name="component estimation, cubic-modulus steel weight",
        citation=(
            "Xie Yunping et al., section 2.2.2: Eq.(2-13) steel cubic "
            "modulus, Eq.(2-42) outfit area modulus, Table 2-3 component "
            "shares of lightweight; Lin Yan, section 2.1.3 Eqs.(2-11)"
            "(2-29)"
        ),
        applicability=(
            "large full-form cargo ships with weight coefficients "
            "calibrated from a close parent ship of the same type and "
            "size class"
        ),
    ),
    "component_exponent": WeightAlgorithmInfo(
        algorithm_id="component_exponent",
        name="component estimation, exponent-regression steel weight",
        citation=(
            "Xie Yunping et al., section 2.2.2 Eq.(2-22) with Table 2-4 "
            "bulk-carrier exponents alpha=1.878 beta=0.695 gamma=-0.189 "
            "sigma=0.158 tau=0.197"
        ),
        applicability=(
            "bulk carriers inside the statistical population behind "
            "Table 2-4; coefficients still calibrated from a close parent"
        ),
    ),
}

DEFAULT_WEIGHT_ALGORITHM = "component_cubic"

#: Bulk-carrier steel-weight exponents, Xie Yunping et al. Table 2-4.
BULK_CARRIER_STEEL_EXPONENTS = (1.878, 0.695, -0.189, 0.158, 0.197)

# ---------------------------------------------------------------------------
# Tunable parameters (all parent-ship inputs, see module docstring)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComponentWeightParameters:
    """Parent-calibrated coefficients of the component algorithms.

    Attributes:
        deadweight_ratio: eta_DW used for the starting displacement
            Delta_0 = DW / eta_DW; TB-001 owner-approved 0.82 (inside the
            Lin Yan Table 4-3 double-hull bulk-carrier band 0.78-0.86).
        steel_cubic_coefficient: C_H of W_H = C_H*L*B*D, t per m^3,
            calibrated from the parent steel weight (Xie Eq.(2-13)).
        outfit_area_coefficient: C_O of W_O = C_O*L*B, t per m^2,
            calibrated from the parent outfit weight (Xie Eq.(2-42)).
        machinery_share: r_M = W_M / LW (Xie Table 2-3 residual; large
            cargo ships 1 - 0.61..0.68 - 0.17..0.23 = 0.09..0.22).
        steel_exponent_coefficient: C_H5 of the exponent form (Xie
            Eq.(2-22)), calibrated from the parent steel weight.
        steel_exponents: (a, b, c, d, e) of Xie Table 2-4 (bulk carrier).
        lightship_margin_ratio: displacement margin added to LW (Lin Yan
            section 2.1.3.3: 2-5 % of LW at preliminary design, large
            ships take the low end).  Default 0 keeps the TB-001 anchor
            reproducible; raise it for real designs.
        tolerance: convergence bound on |W-B|/W (Ship Structural Strength
            section 3.2.2 Eq.(3-27) lower bound).
        max_iterations: hard cap; exceeding it aborts with an error
            instead of returning an unconverged result.
    """

    deadweight_ratio: float = 0.82
    steel_cubic_coefficient: float = 0.06738564459930316
    outfit_area_coefficient: float = 0.5223693379790942
    machinery_share: float = 0.155
    steel_exponent_coefficient: float = 0.0464604769372369
    steel_exponents: tuple[float, float, float, float, float] = (
        BULK_CARRIER_STEEL_EXPONENTS
    )
    lightship_margin_ratio: float = 0.0
    tolerance: float = 0.001
    max_iterations: int = 30

    def __post_init__(self) -> None:
        bands = (
            ("deadweight_ratio", self.deadweight_ratio, 0.5, 1.0),
            ("steel_cubic_coefficient", self.steel_cubic_coefficient,
             0.02, 0.20),
            ("outfit_area_coefficient", self.outfit_area_coefficient,
             0.05, 2.0),
            ("machinery_share", self.machinery_share, 0.02, 0.40),
            ("steel_exponent_coefficient", self.steel_exponent_coefficient,
             0.005, 0.20),
            ("lightship_margin_ratio", self.lightship_margin_ratio, 0.0, 0.10),
            ("tolerance", self.tolerance, 1e-6, 0.01),
        )
        for name, value, lo, hi in bands:
            if not math.isfinite(value) or not lo <= value <= hi:
                raise SpecValidationError(
                    name, value, f"{lo} <= {name} <= {hi}",
                    "sanity band for parent-calibrated weight coefficients; "
                    "values outside it are almost certainly a unit or "
                    "decimal slip, not a new ship class. Recalibrate from "
                    "the parent ship with the *_from_parent helpers.",
                )
        if self.machinery_share >= 1.0 - 1e-9:
            raise SpecValidationError(
                "machinery_share", self.machinery_share, "machinery_share < 1",
                "the steel and outfit shares already fill the lightweight; "
                "a machinery share of 1 or more leaves nothing for the hull.",
            )
        if not math.isfinite(self.max_iterations) or self.max_iterations < 2:
            raise SpecValidationError(
                "max_iterations", self.max_iterations, "max_iterations >= 2",
                "the balance loop needs at least two passes to measure an "
                "imbalance between successive displacements.",
            )


# ---------------------------------------------------------------------------
# Parent calibration helpers (the workflow the sources prescribe)
# ---------------------------------------------------------------------------


def _positive(value: float, name: str) -> float:
    if not math.isfinite(value) or value <= 0:
        raise SpecValidationError(
            name, value, f"finite {name} > 0",
            "parent-ship geometry and weights must be positive physical "
            "quantities; a zero or negative value cannot be calibrated "
            "from.",
        )
    return value


def steel_cubic_coefficient_from_parent(
    parent_lpp: float, parent_beam: float, parent_depth: float,
    parent_steel_t: float,
) -> float:
    """Calibrate C_H of W_H = C_H*L*B*D from a parent ship.

    Inverse of Xie Yunping Eq.(2-13): C_H3 = W_H0 / (L0*B0*D0).
    """
    for value, name in (
        (parent_lpp, "parent_lpp"), (parent_beam, "parent_beam"),
        (parent_depth, "parent_depth"), (parent_steel_t, "parent_steel_t"),
    ):
        _positive(value, name)
    return parent_steel_t / (parent_lpp * parent_beam * parent_depth)


def outfit_area_coefficient_from_parent(
    parent_lpp: float, parent_beam: float, parent_outfit_t: float,
) -> float:
    """Calibrate C_O of W_O = C_O*L*B from a parent ship (Xie Eq.(2-42))."""
    for value, name in (
        (parent_lpp, "parent_lpp"), (parent_beam, "parent_beam"),
        (parent_outfit_t, "parent_outfit_t"),
    ):
        _positive(value, name)
    return parent_outfit_t / (parent_lpp * parent_beam)


def steel_exponent_coefficient_from_parent(
    parent_lpp: float, parent_beam: float, parent_depth: float,
    parent_draft: float, parent_cb: float, parent_steel_t: float,
    exponents: tuple[float, float, float, float, float] = (
        BULK_CARRIER_STEEL_EXPONENTS
    ),
) -> float:
    """Calibrate C_H5 of W_H = C_H5*L^a*B^b*D^c*T^d*Cb^e (Xie Eq.(2-22))."""
    for value, name in (
        (parent_lpp, "parent_lpp"), (parent_beam, "parent_beam"),
        (parent_depth, "parent_depth"), (parent_draft, "parent_draft"),
        (parent_cb, "parent_cb"), (parent_steel_t, "parent_steel_t"),
    ):
        _positive(value, name)
    a, b, c, d, e = exponents
    modulus = (
        parent_lpp**a * parent_beam**b * parent_depth**c
        * parent_draft**d * parent_cb**e
    )
    return parent_steel_t / modulus


# ---------------------------------------------------------------------------
# Statistical deadweight-ratio regression (guarded)
# ---------------------------------------------------------------------------


def bulkcarrier_deadweight_ratio_statistics(deadweight_t: float) -> float:
    """Bulk-carrier eta_DW regression, Xie Yunping Eq.(2-5).

        eta_DW = 0.734 + 0.02839*DW - 0.00221*DW^2,  DW in 10,000 t

    Declared applicability: DW = 5,000-60,000 t (0.5-6.0 * wan t in the
    source).  Outside that band the regression is extrapolation and the
    call refuses, per AGENTS.md section 6.  Note the regression peaks at
    eta_DW ~ 0.825 near its upper bound, which corroborates (as a trend,
    not a substitute) the owner-approved 0.82 of the much larger TB-001.
    """
    if not 5000.0 <= deadweight_t <= 60000.0:
        raise SpecValidationError(
            "deadweight", deadweight_t, "5,000 t <= DW <= 60,000 t",
            "the bulk-carrier deadweight-ratio regression (Xie Yunping "
            "Eq.(2-5)) was compiled for ships of 5,000-60,000 t "
            "deadweight; outside that range it extrapolates and the "
            "module refuses. For larger ships use a close parent ship "
            "of the same size class instead.",
        )
    dw_wan = deadweight_t / 10000.0
    return 0.734 + 0.02839 * dw_wan - 0.00221 * dw_wan**2


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LightweightBreakdown:
    """Component split of the lightweight, t.

    Attributes:
        steel_t: hull steel weight W_H.
        outfit_t: outfitting weight W_O.
        machinery_t: machinery weight W_M (share residual of LW).
        total_t: LW = W_H + W_O + W_M.
    """

    steel_t: float
    outfit_t: float
    machinery_t: float
    total_t: float

    def __post_init__(self) -> None:
        parts = (self.steel_t, self.outfit_t, self.machinery_t, self.total_t)
        if not all(math.isfinite(v) and v >= 0 for v in parts):
            raise SpecValidationError(
                "lightweight", parts, "all components finite and >= 0",
                "negative or non-finite weight components are physically "
                "meaningless; check the parent calibration.",
            )
        if not math.isclose(
            self.steel_t + self.outfit_t + self.machinery_t, self.total_t,
            rel_tol=1e-9, abs_tol=1e-6,
        ):
            raise SpecValidationError(
                "total_t", self.total_t,
                "total_t == steel_t + outfit_t + machinery_t",
                "the lightweight breakdown must sum exactly; storing an "
                "inconsistent total would corrupt every downstream check.",
            )


@dataclass(frozen=True)
class BalanceStep:
    """One pass of the balance loop, fully recorded for auditing.

    Attributes:
        iteration: 1-based pass number.
        displacement_in_t: trial displacement Delta_k driving this pass, t.
        lpp / beam / depth / draft: dimensions from the buoyancy equation
            at Delta_k, m.
        lightweight: component breakdown at those dimensions, t.
        lightship_with_margin_t: LW including the displacement margin, t.
        displacement_out_t: Delta_{k+1} = DW + LW(with margin), t.
        imbalance_ratio: |Delta_out - Delta_in| / Delta_out, the
            |W-B|/W form of the Eq.(3-27) criterion for this loop.
    """

    iteration: int
    displacement_in_t: float
    lpp: float
    beam: float
    depth: float
    draft: float
    lightweight: LightweightBreakdown
    lightship_with_margin_t: float
    displacement_out_t: float
    imbalance_ratio: float


@dataclass(frozen=True)
class WeightBalanceResult:
    """Converged weight-buoyancy balance (JSON-serializable, AGENTS.md 8).

    Attributes:
        converged: True when the Eq.(3-27) criterion was met.
        iterations: number of passes actually executed.
        algorithm_id: registry id of the lightweight algorithm used.
        citation: whitelist citation of that algorithm.
        deadweight_t: task-book deadweight DW, t.
        displacement_t: converged displacement Delta, t (margin included).
        displacement_volume_m3: Delta / 1.025, m^3.
        lightship_t: estimated lightweight without margin, t.
        lightship_with_margin_t: LW * (1 + lightship_margin_ratio), t.
        lightship_margin_ratio: margin actually applied (echo).
        lpp / beam / depth / draft: converged principal dimensions, m.
        cb: block coefficient used (task-book constraint), dimensionless.
        deadweight_ratio_achieved: DW / Delta of the converged design.
        norman_coefficient: N = Delta / (Delta - W_H - 0.46*W_O - 0.40*W_M)
            (Lin Yan section 4.3.4), a convergence/growth diagnostic;
            None for algorithms without a component split.
        imbalance_ratio: final |W-B|/W, dimensionless.
        steps: per-pass audit trail.
    """

    converged: bool
    iterations: int
    algorithm_id: str
    citation: str
    deadweight_t: float
    displacement_t: float
    displacement_volume_m3: float
    lightship_t: float
    lightship_with_margin_t: float
    lightship_margin_ratio: float
    lpp: float
    beam: float
    depth: float
    draft: float
    cb: float
    deadweight_ratio_achieved: float
    norman_coefficient: float | None
    imbalance_ratio: float
    steps: tuple[BalanceStep, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe dict (nested, no object identity references)."""
        def step_dict(step: BalanceStep) -> dict[str, Any]:
            return {
                "iteration": step.iteration,
                "displacement_in_t": step.displacement_in_t,
                "lpp": step.lpp,
                "beam": step.beam,
                "depth": step.depth,
                "draft": step.draft,
                "lightweight": {
                    "steel_t": step.lightweight.steel_t,
                    "outfit_t": step.lightweight.outfit_t,
                    "machinery_t": step.lightweight.machinery_t,
                    "total_t": step.lightweight.total_t,
                },
                "lightship_with_margin_t": step.lightship_with_margin_t,
                "displacement_out_t": step.displacement_out_t,
                "imbalance_ratio": step.imbalance_ratio,
            }

        return {
            "converged": self.converged,
            "iterations": self.iterations,
            "algorithm_id": self.algorithm_id,
            "citation": self.citation,
            "deadweight_t": self.deadweight_t,
            "displacement_t": self.displacement_t,
            "displacement_volume_m3": self.displacement_volume_m3,
            "lightship_t": self.lightship_t,
            "lightship_with_margin_t": self.lightship_with_margin_t,
            "lightship_margin_ratio": self.lightship_margin_ratio,
            "lpp": self.lpp,
            "beam": self.beam,
            "depth": self.depth,
            "draft": self.draft,
            "cb": self.cb,
            "deadweight_ratio_achieved": self.deadweight_ratio_achieved,
            "norman_coefficient": self.norman_coefficient,
            "imbalance_ratio": self.imbalance_ratio,
            "steps": [step_dict(s) for s in self.steps],
        }


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _norman_coefficient(
    displacement_t: float, lw: LightweightBreakdown,
) -> float:
    """N = Delta / (Delta - W_H - 0.46*W_O - 0.40*W_M), Lin Yan 4.3.4.

    The 0.46 / 0.40 factors are the source's merchant-ship power
    assumptions (3/5 of outfit and machinery scaling with Delta^(2/3),
    part of it with Delta^(1/3) or not at all).
    """
    denominator = (
        displacement_t - lw.steel_t - 0.46 * lw.outfit_t - 0.40 * lw.machinery_t
    )
    if denominator <= 0:
        raise SpecValidationError(
            "displacement", displacement_t,
            "Delta > W_H + 0.46*W_O + 0.40*W_M",
            "the Norman coefficient denominator vanished: the parent "
            "coefficients claim a ship whose weight-sensitive parts "
            "already exceed the displacement - recalibrate, the numbers "
            "do not describe a buildable ship.",
        )
    return displacement_t / denominator


def _component_lightweight(
    dims: ShipSpec, parameters: ComponentWeightParameters, *,
    exponent_steel: bool,
) -> LightweightBreakdown:
    """LW split of the component algorithms at the given dimensions.

    Steel: cubic modulus (Xie Eq.(2-13)) or exponent regression (Xie
    Eq.(2-22) with Table 2-4).  Outfit: area modulus (Xie Eq.(2-42)).
    Machinery: share residual (Xie Table 2-3), so
    LW = (W_H + W_O) / (1 - r_M) with W_M = r_M*LW exactly.
    """
    lpp, beam = dims.lpp, dims.beam
    depth, draft, cb = dims.depth, dims.draft, dims.cb
    if exponent_steel:
        a, b, c, d, e = parameters.steel_exponents
        steel = parameters.steel_exponent_coefficient * (
            lpp**a * beam**b * depth**c * draft**d * cb**e
        )
    else:
        steel = parameters.steel_cubic_coefficient * lpp * beam * depth
    outfit = parameters.outfit_area_coefficient * lpp * beam
    total = (steel + outfit) / (1.0 - parameters.machinery_share)
    machinery = total - steel - outfit
    return LightweightBreakdown(
        steel_t=steel, outfit_t=outfit, machinery_t=machinery, total_t=total,
    )


def _require_taskbook_inputs(spec: ShipSpec) -> None:
    if spec.deadweight is None:
        raise SpecValidationError(
            "deadweight", None, "required input",
            "the weight-buoyancy balance closes Delta = DW + LW; without "
            "the deadweight requirement there is nothing to balance. "
            "Provide it in the task book.",
        )
    if spec.service_speed is None:
        raise SpecValidationError(
            "service_speed", None, "required input",
            "the dimension chain needs the service speed for its Froude "
            "number applicability guard; provide it in the task book "
            "(m/s, use knots_to_ms() at the boundary).",
        )
    if spec.cb is None:
        raise SpecValidationError(
            "cb", None, "provide the target Cb (task-book constraint)",
            "the balance loop drives the dimension chain, which solves "
            "grad = L*B*T*Cb; without a pinned Cb the buoyancy side of "
            "the balance is undetermined. Pin Cb in the task book, as "
            "TB-001 does with Cb = 0.8580.",
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def solve_weight_balance(
    spec: ShipSpec,
    algorithm_id: str = DEFAULT_WEIGHT_ALGORITHM,
    *,
    ratios: RatioParameters | None = None,
    parameters: ComponentWeightParameters | None = None,
) -> WeightBalanceResult:
    """Close the weight-buoyancy balance Delta = DW + LW iteratively.

    Args:
        spec: task-book spec; requires deadweight, service_speed and a
            pinned target cb.
        algorithm_id: registry key of WEIGHT_ALGORITHMS.
        ratios: dimension-chain statistics (main_dimensions.RatioParameters).
        parameters: parent-calibrated weight coefficients; defaults are
            the TB-001/JBC-neighbourhood calibration declared in the
            module docstring.

    Returns:
        WeightBalanceResult with the converged displacement, the final
        dimensions, the lightweight breakdown and the full per-pass
        audit trail.

    Raises:
        SpecValidationError: missing inputs, unknown algorithm id, or
            coefficients outside their sanity bands.
        RuntimeError: the loop hit max_iterations without meeting the
            Eq.(3-27) criterion (never returns unconverged numbers).
    """
    info = WEIGHT_ALGORITHMS.get(algorithm_id)
    if info is None:
        raise SpecValidationError(
            "algorithm_id", algorithm_id, f"one of {sorted(WEIGHT_ALGORITHMS)}",
            "unknown lightweight algorithm id; the registry lists every "
            "selectable weight algorithm (AGENTS.md section 8).",
        )
    _require_taskbook_inputs(spec)
    ratios = ratios if ratios is not None else RatioParameters()
    parameters = parameters if parameters is not None else ComponentWeightParameters()
    dw = spec.deadweight

    if algorithm_id == "deadweight_ratio":
        eta = parameters.deadweight_ratio
        lightship = dw * (1.0 - eta) / eta
        displacement = dw + lightship
        dims = _chain_solve(spec, ratios, "", displacement=displacement)
        breakdown = LightweightBreakdown(
            steel_t=lightship, outfit_t=0.0, machinery_t=0.0,
            total_t=lightship,
        )
        steps = (
            BalanceStep(
                iteration=1, displacement_in_t=dw / eta,
                lpp=dims.lpp, beam=dims.beam, depth=dims.depth,
                draft=dims.draft, lightweight=breakdown,
                lightship_with_margin_t=lightship,
                displacement_out_t=displacement, imbalance_ratio=0.0,
            ),
        )
        return WeightBalanceResult(
            converged=True, iterations=1, algorithm_id=info.algorithm_id,
            citation=info.citation, deadweight_t=dw,
            displacement_t=displacement,
            displacement_volume_m3=displacement / 1.025,
            lightship_t=lightship, lightship_with_margin_t=lightship,
            lightship_margin_ratio=0.0, lpp=dims.lpp, beam=dims.beam,
            depth=dims.depth, draft=dims.draft, cb=dims.cb,
            deadweight_ratio_achieved=dw / displacement,
            norman_coefficient=None, imbalance_ratio=0.0, steps=steps,
        )

    exponent_steel = algorithm_id == "component_exponent"
    margin = parameters.lightship_margin_ratio
    delta = dw / parameters.deadweight_ratio
    steps: list[BalanceStep] = []
    final_breakdown: LightweightBreakdown | None = None
    final_dims: ShipSpec | None = None
    converged = False

    for pass_no in range(1, parameters.max_iterations + 1):
        dims = _chain_solve(spec, ratios, "", displacement=delta)
        breakdown = _component_lightweight(
            dims, parameters, exponent_steel=exponent_steel
        )
        lightship_with_margin = breakdown.total_t * (1.0 + margin)
        new_delta = dw + lightship_with_margin
        imbalance = abs(new_delta - delta) / new_delta
        steps.append(
            BalanceStep(
                iteration=pass_no, displacement_in_t=delta,
                lpp=dims.lpp, beam=dims.beam, depth=dims.depth,
                draft=dims.draft, lightweight=breakdown,
                lightship_with_margin_t=lightship_with_margin,
                displacement_out_t=new_delta, imbalance_ratio=imbalance,
            )
        )
        final_breakdown, final_dims = breakdown, dims
        delta = new_delta
        if imbalance <= parameters.tolerance:
            converged = True
            break

    if not converged:
        raise RuntimeError(
            f"weight-buoyancy balance did not converge within "
            f"{parameters.max_iterations} passes (last |W-B|/W = "
            f"{steps[-1].imbalance_ratio:.4%}, criterion "
            f"{parameters.tolerance:.4%}); refusing to return "
            f"unconverged numbers. Check the task book and the parent "
            f"coefficients - a non-converging balance usually means an "
            f"input or calibration error, not a slow ship."
        )

    assert final_breakdown is not None and final_dims is not None
    return WeightBalanceResult(
        converged=True, iterations=len(steps), algorithm_id=info.algorithm_id,
        citation=info.citation, deadweight_t=dw, displacement_t=delta,
        displacement_volume_m3=delta / 1.025,
        lightship_t=final_breakdown.total_t,
        lightship_with_margin_t=final_breakdown.total_t * (1.0 + margin),
        lightship_margin_ratio=margin, lpp=final_dims.lpp,
        beam=final_dims.beam, depth=final_dims.depth,
        draft=final_dims.draft, cb=final_dims.cb,
        deadweight_ratio_achieved=dw / delta,
        norman_coefficient=_norman_coefficient(delta, final_breakdown),
        imbalance_ratio=steps[-1].imbalance_ratio, steps=tuple(steps),
    )
