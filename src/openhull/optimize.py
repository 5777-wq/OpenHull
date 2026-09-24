"""Design-space scan and trade-off extraction (plan task 3.6).

Orchestrates the whitelisted chain — weight balance (task 1.3),
Lackenby hull (2.6), hydrostatics, large-angle stability and the IS
Code criteria (3.4/3.5), the severe wind and rolling criterion
(3.5b), Ayre resistance (3.1) and the B-series propeller design
(3.3) — over a grid of dimension-ratio candidates.  NO new empirical
formulas live here: every gate composes whitelisted methods, each
with its own declared domain, and a candidate refused by any method
is recorded with the refusing stage (nothing is extrapolated).

Feasibility gates, in evaluation order:
  1. weight balance        Norman iteration converges (task 1.3)
  2. Ayre speed band       V/sqrt(L) within 0.50-1.20 knots/sqrt-ft
                           (task 3.1's declared table band)
  3. hull transform        Lackenby reaches the target Cb (task 2.6)
  4. propeller design      B-series envelope + eta_o sanity
                           (0.40-0.85) + tip clearance D <= 0.75 T
                           (declared engineering gate)
  5. intact stability      all IS Code 2.2 criteria pass (task 3.5)
  6. weather criterion     area b >= a (task 3.5b)

The attainable-speed axis of the trade-off is defined as the service
speed the candidate would reach at a FIXED REFERENCE delivered power
(the median shaft power of the feasible set) via the task 3.2 solver
- so faster hulls are the ones that convert the same power into more
speed.  The definition is orchestration, not hydrodynamics, and is
stated wherever a speed is reported.

Task 3.8 stage-1 seakeeping columns (roll/pitch/heave natural
periods, roll resonance flags against the two reference sea bands)
are REPORTED per feasible candidate but are NOT feasibility gates:
whether to avoid a resonance band is professional judgement, which
stays with the owner (AGENTS.md red lines).

Only whitelisted methods are called; the windage input of the weather
criterion is taken from the task book unchanged across candidates
(declared approximation: it is not rescaled with ship size).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Callable, Iterator, Sequence

from .hydrostatics import hydrostatic_draft_rows, hydrostatics_table
from .linesplan import parent_to_taskbook
from .main_dimensions import RatioParameters
from .propeller import (
    b_series_open_water,
    check_cavitation,
    solve_optimal_propeller_for_thrust,
)
from .propulsion import propulsion_factors, solve_service_speed
from .resistance import ayre_effective_power
from .seakeeping import estimate_seakeeping
from .spec import ShipSpec, SpecValidationError, knots_to_ms
from .stability import gz_curve, intact_stability_criteria, weather_criterion
from .weight_balance import solve_weight_balance

__all__ = [
    "SweepGrid",
    "ScanConfig",
    "ScanCandidate",
    "RejectedPoint",
    "ScanResult",
    "design_space_scan",
    "pareto_front",
]

_FT_PER_M = 1.0 / 0.3048
_AYRE_BAND = (0.50, 1.20)
_ETA_SANITY = (0.40, 0.85)


@dataclass(frozen=True)
class SweepGrid:
    """Three-axis grid of dimension-ratio candidates (lo, hi, steps)."""

    l_over_b: Tuple3 = (5.0, 7.5, 5)
    b_over_t: Tuple3 = (2.3, 3.5, 4)
    cb: Tuple3 = (0.82, 0.88, 4)

    def values(self) -> Iterator[tuple[float, float, float]]:
        for lob in _axis(self.l_over_b):
            for bot in _axis(self.b_over_t):
                for cb in _axis(self.cb):
                    yield round(lob, 6), round(bot, 6), round(cb, 6)


Tuple3 = tuple[float, float, int]


def _axis(spec: Tuple3) -> list[float]:
    lo, hi, steps = spec
    if steps < 1:
        raise SpecValidationError(
            "grid steps", steps, ">= 1",
            "a sweep axis needs at least one sample.")
    if steps == 1:
        return [float(lo)]
    values = [lo + (hi - lo) * i / (steps - 1) for i in range(steps)]
    # snap the ENDPOINTS to the declared bounds: floating-point drift
    # made the top grid line 3.5000000000000004 and the B/T <= 3.5
    # guard then refused the whole line silently (review 2026-09-24)
    values[0] = float(lo)
    values[-1] = float(hi)
    return values


@dataclass(frozen=True)
class ScanConfig:
    """Fixed inputs of the scan (everything the grid does not vary)."""

    kg_m: float
    deadweight_ratio: float = 0.82
    l_over_depth: float = 11.2
    propeller_blades: int = 5
    propeller_aear: float = 0.50
    propeller_rpm: float = 127.0
    shaft_immersion_m: float | None = None
    relative_rotative_eff: float = 1.0
    shaft_efficiency: float = 1.0
    flooding_angle_deg: float | None = None
    windage_area_m2: float | None = None
    windage_lever_z_m: float | None = None
    bilge_keel_area_m2: float = 0.0
    length_waterline_m: float | None = None
    max_tip_diameter_draft_ratio: float = 0.75


@dataclass(frozen=True)
class RejectedPoint:
    l_over_b: float
    b_over_t: float
    cb: float
    stage: str
    reason: str


@dataclass(frozen=True)
class ScanCandidate:
    l_over_b: float
    b_over_t: float
    cb: float
    lpp_m: float
    beam_m: float
    draft_m: float
    depth_m: float
    displacement_t: float
    gm_m: float
    gz_max_m: float
    eta_open_water: float
    delivered_power_kw: float
    shaft_power_kw: float
    propeller_diameter_m: float
    propeller_pitch_ratio: float
    advance_coefficient: float
    thrust_n: float
    cp: float
    cm: float
    cwp: float
    lcb_pct_fwd: float
    cavitation_ok: bool | None
    cavitation_aeao_required: float | None
    speed_at_reference_power_kn: float | None = None
    roll_period_s: float | None = None
    pitch_period_s: float | None = None
    heave_period_s: float | None = None
    roll_resonant_6s: bool | None = None
    roll_resonant_8s: bool | None = None

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class ScanResult:
    feasible: list[ScanCandidate] = field(default_factory=list)
    rejected: list[RejectedPoint] = field(default_factory=list)
    reference_power_kw: float | None = None

    def rejection_histogram(self) -> dict[str, int]:
        hist: dict[str, int] = {}
        for r in self.rejected:
            hist[r.stage] = hist.get(r.stage, 0) + 1
        return hist

    def to_dicts(self) -> list[dict]:
        return [c.to_dict() for c in self.feasible]


def pareto_front(
    candidates: Sequence[ScanCandidate],
) -> list[ScanCandidate]:
    """Non-dominated set: maximise speed and GM, minimise displacement.

    Candidates whose reference-speed is unknown (the task 3.2 solver
    refused the reference power) take no part in the domination test.
    """
    pool = [c for c in candidates if c.speed_at_reference_power_kn is not None]

    def dominates(a: ScanCandidate, b: ScanCandidate) -> bool:
        ge = (a.speed_at_reference_power_kn >= b.speed_at_reference_power_kn
              and a.gm_m >= b.gm_m
              and a.displacement_t <= b.displacement_t)
        gt = (a.speed_at_reference_power_kn > b.speed_at_reference_power_kn
              or a.gm_m > b.gm_m
              or a.displacement_t < b.displacement_t)
        return ge and gt

    return [c for c in pool if not any(dominates(o, c) for o in pool
                                       if o is not c)]


def design_space_scan(
    base_spec: ShipSpec,
    *,
    kg_m: float,
    grid: SweepGrid | None = None,
    config: ScanConfig | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> ScanResult:
    """Sweep the dimension-ratio grid and evaluate every candidate.

    base_spec carries the task-book requirements (deadweight, service
    speed, design draft); the grid varies the dimension ratios and the
    target block coefficient.  Every refusal is recorded, nothing is
    silently dropped.
    """
    grid = grid or SweepGrid()
    config = config or ScanConfig(kg_m=kg_m)
    service_kn = base_spec.service_speed * 3600.0 / 1852.0
    n_rps = config.propeller_rpm / 60.0
    series = b_series_open_water(
        config.propeller_blades, config.propeller_aear)
    result = ScanResult()
    points = list(grid.values())
    for index, (lob, bot, cb) in enumerate(points):
        if progress is not None:
            progress(index, len(points), f"L/B {lob:.2f} B/T {bot:.2f} "
                                        f"Cb {cb:.3f}")
        outcome = _evaluate_point(
            base_spec, lob, bot, cb, service_kn, n_rps, series, config)
        if isinstance(outcome, RejectedPoint):
            result.rejected.append(outcome)
        else:
            result.feasible.append(outcome)
    # second pass: attainable speed at a fixed reference power (the
    # median shaft power of the feasible set) - see module docstring
    if result.feasible:
        powers = sorted(c.shaft_power_kw for c in result.feasible)
        k = len(powers) // 2
        reference = (powers[k] if len(powers) % 2 == 1
                     else 0.5 * (powers[k - 1] + powers[k]))
        result.reference_power_kw = round(reference, 1)
        enriched: list[ScanCandidate] = []
        for cand in result.feasible:
            speed = _speed_at_reference_power(
                base_spec, cand, reference, config)
            enriched.append(replace(
                cand, speed_at_reference_power_kn=speed))
        result.feasible = enriched
    return result


def _speed_at_reference_power(
    base_spec: ShipSpec,
    cand: ScanCandidate,
    reference_kw: float,
    config: ScanConfig,
) -> float | None:
    try:
        solution = solve_service_speed(
            dhp_kw=reference_kw,
            eta_open_water=cand.eta_open_water,
            lpp_m=cand.lpp_m,
            lwl_m=config.length_waterline_m or cand.lpp_m,
            beam_m=cand.beam_m,
            draft_m=cand.draft_m,
            cb=cand.cb,
            cp=cand.cp,
            cm=cand.cm,
            cwp=cand.cwp,
            lcb_pct_fwd=cand.lcb_pct_fwd,
            propeller_diameter_m=cand.propeller_diameter_m,
            displacement_t=cand.displacement_t,
            speed_ms=base_spec.service_speed,
            eta_r=config.relative_rotative_eff,
        )
        return round(solution.speed_kn, 3)
    except (SpecValidationError, RuntimeError):
        return None


def _evaluate_point(
    base_spec: ShipSpec,
    lob: float,
    bot: float,
    cb: float,
    service_kn: float,
    n_rps: float,
    series,
    config: ScanConfig,
):
    spec = replace(base_spec, cb=cb)
    try:
        balance = solve_weight_balance(spec, ratios=RatioParameters(
            deadweight_ratio=config.deadweight_ratio,
            l_over_b=lob, b_over_t=bot, l_over_depth=config.l_over_depth))
    except (SpecValidationError, RuntimeError) as error:
        return RejectedPoint(lob, bot, cb, "weight_balance", str(error)[:200])

    v_ratio = service_kn / math.sqrt(balance.lpp * _FT_PER_M)
    if not _AYRE_BAND[0] <= v_ratio <= _AYRE_BAND[1]:
        return RejectedPoint(
            lob, bot, cb, "ayre_band",
            f"V/sqrt(L) = {v_ratio:.3f} outside "
            f"{_AYRE_BAND[0]}-{_AYRE_BAND[1]} at Lpp {balance.lpp:.1f} m")

    try:
        hull, _transform = parent_to_taskbook(
            lpp=balance.lpp, beam=balance.beam, draft=balance.draft,
            target_cb=cb)
    except (SpecValidationError, RuntimeError) as error:
        return RejectedPoint(lob, bot, cb, "hull", str(error)[:200])

    try:
        hydro = hydrostatics_table(
            hull, hydrostatic_draft_rows(
                hull, balance.draft, (0.9, 1.0))).entries[-1]
    except SpecValidationError as error:
        return RejectedPoint(lob, bot, cb, "hydro", str(error)[:200])
    try:
        pe_kw = ayre_effective_power(
            displacement_t=balance.displacement_t, speed_kn=service_kn,
            lpp_m=balance.lpp, beam_m=balance.beam,
            draft_m=balance.draft, cb=cb,
            xc_pct_fwd=hydro.lcb, screw="single",
        ).pe_bare_kw
    except SpecValidationError as error:
        return RejectedPoint(lob, bot, cb, "ayre", str(error)[:200])

    # ship speed in m/s — the scan's propulsion stage must use the same
    # conversion as the CLI path (knots_to_ms).  Dividing by 0.514444
    # here instead of multiplying ran this stage at 3.78x the ship
    # speed for as long as the scan existed: every gate downstream then
    # judged a phantom vessel (Va 25.7 m/s for a 20 kn ship), refusing
    # whole bands on d_bounds_m/thrust_n and, where the search survived,
    # reporting propellers designed for that speed.  Pinned by
    # test_scan_propeller_advance_speed_is_the_ship_speed.
    v_ms = knots_to_ms(service_kn)
    d_guess = 0.55 * balance.draft
    d_bounds = (0.35 * balance.draft,
                config.max_tip_diameter_draft_ratio * balance.draft)
    prop = None
    factors = None
    last_error: Exception | None = None
    for _attempt in range(6):
        try:
            factors = propulsion_factors(
                lpp_m=balance.lpp, lwl_m=balance.lpp,
                beam_m=balance.beam, draft_m=balance.draft,
                cb=cb, cp=hydro.cp, cm=hydro.cm, cwp=hydro.cw,
                lcb_pct_fwd=hydro.lcb,
                propeller_diameter_m=d_guess, speed_ms=v_ms,
                screw="single", eta_r=config.relative_rotative_eff,
            )
            va_ms = v_ms * (1.0 - factors.w)
            # thrust-led design: the required thrust T = P_E/(V(1-t))
            # is efficiency-independent, so no eta_o fixed-point is
            # needed (the power-led iteration diverges near the
            # series' eta_o pole)
            thrust_required = pe_kw * 1e3 / (v_ms
                                             * (1.0 - factors.t))
            prop = solve_optimal_propeller_for_thrust(
                thrust_required, va_ms, n_rps, series,
                d_bounds_m=d_bounds, n_scan=300)
            break
        except SpecValidationError as error:
            # shrink the diameter guess and retry: the Holtrop wake
            # depends on the guessed diameter and can leave its
            # physical band at the first guess
            last_error = error
            d_guess *= 0.85
            if d_guess < d_bounds[0]:
                break
    if prop is None or factors is None:
        return RejectedPoint(lob, bot, cb, "propeller",
                             str(last_error)[:200] if last_error
                             else "no admissible diameter")
    if not _ETA_SANITY[0] <= prop.eta_o <= _ETA_SANITY[1]:
        return RejectedPoint(
            lob, bot, cb, "propeller",
            f"eta_o {prop.eta_o:.3f} outside the sanity band "
            f"{_ETA_SANITY}")
    if prop.diameter_m > config.max_tip_diameter_draft_ratio * balance.draft:
        return RejectedPoint(
            lob, bot, cb, "propeller",
            f"diameter {prop.diameter_m:.2f} m exceeds "
            f"{config.max_tip_diameter_draft_ratio:.2f} x draft "
            f"{balance.draft:.2f} m")

    try:
        gz = gz_curve(hull, balance.displacement_t, config.kg_m,
                      depth_m=balance.depth)
        criteria = intact_stability_criteria(
            hull, balance.displacement_t, config.kg_m,
            depth_m=balance.depth,
            flooding_angle_deg=config.flooding_angle_deg)
    except (SpecValidationError, RuntimeError) as error:
        return RejectedPoint(lob, bot, cb, "stability", str(error)[:200])
    if not criteria.all_passed:
        failed = [c.id for c in criteria.criteria if not c.passed]
        return RejectedPoint(
            lob, bot, cb, "stability",
            "IS Code criteria failed: " + ", ".join(failed))
    if (config.windage_area_m2 is not None
            and config.windage_lever_z_m is not None):
        try:
            weather = weather_criterion(
                hull, balance.displacement_t, config.kg_m,
                depth_m=balance.depth,
                windage_area_m2=config.windage_area_m2,
                windage_lever_z_m=config.windage_lever_z_m,
                bilge_keel_area_m2=config.bilge_keel_area_m2,
                length_waterline_m=config.length_waterline_m,
                flooding_angle_deg=config.flooding_angle_deg)
        except (SpecValidationError, RuntimeError) as error:
            return RejectedPoint(lob, bot, cb, "weather", str(error)[:200])
        if not weather.all_passed:
            return RejectedPoint(
                lob, bot, cb, "weather",
                f"area a {weather.area_a_mrad:.3f} > b "
                f"{weather.area_b_mrad:.3f} m*rad")

    cav_ok = None
    cav_req = None
    if config.shaft_immersion_m is not None:
        try:
            cav = check_cavitation(
                thrust_n=prop.thrust_n, va_ms=prop.va_ms, n_rps=n_rps,
                diameter_m=prop.diameter_m, pitch_ratio=prop.pitch_ratio,
                aeao_available=config.propeller_aear,
                hs_m=config.shaft_immersion_m)
            cav_ok = cav.ok
            cav_req = round(cav.aeao_required, 3)
        except SpecValidationError:
            # sigma outside the verified Burrill band: the check is
            # unavailable here (line carried at 4 book-read anchors)
            cav_ok = None
            cav_req = None

    shaft_power = prop.delivered_power_kw / (
        config.relative_rotative_eff * config.shaft_efficiency)

    # task 3.8 stage-1 seakeeping columns (reported, not a gate):
    # natural periods and roll resonance against the two reference
    # sea bands.  Roll uses the GM WITHOUT free-surface correction
    # (regulation usage, Ship Theory vol. 2 p.391); Cvp = Cb/Cw.
    roll_period_s = None
    pitch_period_s = None
    heave_period_s = None
    roll_resonant_6s = None
    roll_resonant_8s = None
    gm_uncorrected = criteria.gm0_m + criteria.free_surface_correction_m
    try:
        seakeep = estimate_seakeeping(
            beam_m=balance.beam, draft_m=balance.draft, zg_m=config.kg_m,
            gm_m=gm_uncorrected, cb=cb, cwp=hydro.cw)
        roll_period_s = round(seakeep.roll_period_s, 2)
        pitch_period_s = round(seakeep.pitch_period_s, 2)
        heave_period_s = round(seakeep.heave_period_s, 2)
        for check in seakeep.resonance_checks:
            if check.motion == "roll":
                if check.wave_period_s == 6.0:
                    roll_resonant_6s = check.in_resonance_band
                elif check.wave_period_s == 8.0:
                    roll_resonant_8s = check.in_resonance_band
    except SpecValidationError:
        pass  # e.g. GM <= 0.15 m: periods undefined, columns stay None

    return ScanCandidate(
        l_over_b=lob,
        b_over_t=bot,
        cb=cb,
        lpp_m=round(balance.lpp, 3),
        beam_m=round(balance.beam, 3),
        draft_m=round(balance.draft, 3),
        depth_m=round(balance.depth, 3),
        displacement_t=round(balance.displacement_t, 2),
        gm_m=round(criteria.gm0_m, 4),
        gz_max_m=round(gz.gz_max_m, 4),
        eta_open_water=round(prop.eta_o, 4),
        delivered_power_kw=round(prop.delivered_power_kw, 1),
        shaft_power_kw=round(shaft_power, 1),
        propeller_diameter_m=round(prop.diameter_m, 3),
        propeller_pitch_ratio=round(prop.pitch_ratio, 4),
        advance_coefficient=round(prop.j, 4),
        thrust_n=round(prop.thrust_n, 1),
        cp=round(hydro.cp, 4),
        cm=round(hydro.cm, 4),
        cwp=round(hydro.cw, 4),
        lcb_pct_fwd=round(hydro.lcb, 4),
        cavitation_ok=cav_ok,
        cavitation_aeao_required=cav_req,
        roll_period_s=roll_period_s,
        pitch_period_s=pitch_period_s,
        heave_period_s=heave_period_s,
        roll_resonant_6s=roll_resonant_6s,
        roll_resonant_8s=roll_resonant_8s,
    )


def write_tradeoff_chart(result: ScanResult, path) -> None:
    """Speed - displacement scatter, GM-coloured, with the Pareto front.

    A data chart of the scan output (analysis artifact), not a hull
    drawing - the no-drawing red line (AGENTS.md section 7) concerns
    geometry deliverables.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=150)
    feas = [c for c in result.feasible
            if c.speed_at_reference_power_kn is not None]
    if not feas:
        # zero feasible designs: plot the REFUSED points instead —
        # coloured by the refusing stage, in the Cb-B/T plane, so the
        # run still ends with an actionable picture
        stages = sorted({r.stage for r in result.rejected})
        palette = ["#c0392b", "#e67e22", "#8e44ad", "#16a085",
                   "#2c3e50", "#7f8c8d"]
        for i, stage in enumerate(stages):
            pts = [r for r in result.rejected if r.stage == stage]
            ax.scatter([p.b_over_t for p in pts], [p.cb for p in pts],
                       s=64, alpha=0.75, edgecolors="black",
                       linewidths=0.4,
                       color=palette[i % len(palette)],
                       label=f"{stage} ({len(pts)})", zorder=3)
        ax.set_xlabel("B/T")
        ax.set_ylabel("Cb")
        ax.grid(True, alpha=0.3)
        if stages:
            ax.legend(loc="best", fontsize=9, title="refusing stage")
        ax.set_title(
            "OpenHull design scan - 0 feasible / %d refused "
            "(points coloured by the refusing stage)" % len(
                result.rejected))
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        return
    xs = [c.displacement_t / 1000.0 for c in feas]
    ys = [c.speed_at_reference_power_kn for c in feas]
    gs = [c.gm_m for c in feas]
    sc = ax.scatter(xs, ys, c=gs, cmap="viridis", s=64,
                    edgecolors="black", linewidths=0.6, zorder=3)
    front = pareto_front(result.feasible)
    front.sort(key=lambda c: c.displacement_t)
    fx = [c.displacement_t / 1000.0 for c in front]
    fy = [c.speed_at_reference_power_kn for c in front]
    ax.plot(fx, fy, "r--o", linewidth=1.4, markersize=5,
            label="Pareto front", zorder=4)
    ax.set_xlabel("displacement (kt)")
    ax.set_ylabel("attainable speed at reference power (kn)")
    cb_label = ax.figure.colorbar(sc, ax=ax)
    cb_label.set_label("GM (m)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")
    ax.set_title(
        "OpenHull design scan - %d feasible / %d total" % (
            len(result.feasible),
            len(result.feasible) + len(result.rejected)))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
