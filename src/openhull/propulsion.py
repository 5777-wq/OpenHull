"""Propulsion factors and the service-speed iteration (plan task 3.2).

The interaction between hull and propeller is estimated with the
Holtrop correlation as transcribed in Ship Theory vol. 2, sections
5-2/5-3 (book pages 58-61; every formula visually verified against
the scanned original, 2026-09-21):

  wake fraction        w   Eq.(5-38) single screw / (5-39) twin
  thrust deduction     t   Eq.(5-48) single screw / (5-49) twin
  relative rot. eff.   eta_R  Eq.(5-51)/(5-52); the no-data fallback
                              Eq.(5-50) eta_R = 1.0 is the v1 default

with the auxiliary chain of 5-38: CV = (1+k)Cf + CA (Cf by the
whitelisted ITTC 1957 line), CA, C2/C3 (bulb), C4 (fore draft), C8/C9,
C11, Cp1 and the wetted-surface S formula.  The hull efficiency is
eta_h = (1 - t)/(1 - w) and the propulsion efficiency
eta_D = eta_o * eta_R * eta_h, where the open-water efficiency eta_o
is an INPUT until the propeller module (plan task 3.3) supplies it.

Honest divergences from other published renderings of the Holtrop
correlation, kept as printed in the whitelisted textbook: the third
and fourth wake terms are plain reciprocals 1/(0.95-Cp), 1/(0.95-Cb)
(not ratio forms); the twin-screw wake uses Cb (unsquared); the CA
term prints the Cb exponent as 4.

The service-speed solver inverts the chain: given delivered power it
bisects for the speed V whose bare-hull effective power (the task 3.1
Ayre estimate) equals eta_D * DHP.  w and t of this correlation do
not depend on speed, so eta_D is constant along the solution.

Units per AGENTS.md section 1; LCB is %Lpp forward positive.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from .resistance import ayre_effective_power
from .spec import SpecValidationError

__all__ = [
    "propulsion_factors",
    "PropulsionFactors",
    "solve_service_speed",
    "SpeedSolution",
    "SEAWATER_KINEMATIC_VISCOSITY",
]

#: seawater kinematic viscosity at 15 deg C, m^2/s (the standard
#: correlation condition; declared, not hidden)
SEAWATER_KINEMATIC_VISCOSITY = 1.18831e-6


def _ittc1957_cf(reynolds: float) -> float:
    """ITTC 1957 model-ship correlation line (whitelisted)."""
    if reynolds <= 0:
        raise SpecValidationError(
            "reynolds", reynolds, "> 0",
            "the friction line needs a positive Reynolds number.",
        )
    return 0.075 / (math.log10(reynolds) - 2.0) ** 2


@dataclass(frozen=True)
class PropulsionFactors:
    """Hull-propeller interaction factors for one loading condition.

    Attributes:
        w: Taylor wake fraction.
        t: thrust deduction fraction.
        eta_r: relative rotative efficiency (input/fallback per
            Eq. 5-50).
        eta_h: hull efficiency (1-t)/(1-w).
        c_v / c_a / c_f: viscous-resistance chain, dimensionless.
        wetted_surface_m2: S of the 5-38 auxiliary chain, m^2.
        c_stern: the stern-shape coefficient echoed.
        form_factor: (1+k) echoed.
    """

    w: float
    t: float
    eta_r: float
    eta_h: float
    c_v: float
    c_a: float
    c_f: float
    wetted_surface_m2: float
    c_stern: float
    form_factor: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def propulsion_factors(
    *,
    lpp_m: float,
    lwl_m: float,
    beam_m: float,
    draft_m: float,
    draft_fore_m: float | None = None,
    draft_aft_m: float | None = None,
    cb: float,
    cp: float,
    cm: float,
    cwp: float,
    lcb_pct_fwd: float,
    propeller_diameter_m: float,
    c_stern: float = 0.0,
    bulb_area_m2: float = 0.0,
    bulb_height_m: float = 0.0,
    form_factor: float = 1.3,
    speed_ms: float = 10.0,
    screw: str = "single",
    eta_r: float | None = None,
) -> PropulsionFactors:
    """Wake fraction, thrust deduction and hull efficiency (Eqs. 5-38..5-49).

    Args:
        lpp_m / lwl_m: Lbp and waterline length, m (the correlation
            uses the waterline length L).
        beam_m / draft_m: moulded beam and mean draft, m.
        draft_fore_m / draft_aft_m: fore/aft drafts, m (default even
            keel); TA = aft draft enters the wake, TF the C4 term.
        cb / cp / cm / cwp: block, prismatic, midship and
            waterplane coefficients.
        lcb_pct_fwd: LCB, %Lpp forward of midship (fwd positive).
        propeller_diameter_m: D, m.
        c_stern: stern-shape coefficient of the correlation (0 for a
            normal single-screw stern; negative pram, positive twin
            transom).
        bulb_area_m2 / bulb_height_m: bulb cross-section area at the
            FP and its centroid height above keel (0 = no bulb).
        form_factor: (1+k) of the viscous-resistance chain.
        speed_ms: speed for the Reynolds number of Cf, m/s.
        screw: 'single' or 'twin'.
        eta_r: relative rotative efficiency; None takes the Eq. 5-50
            no-data fallback 1.0 (the 5-51/5-52 formulae need the
            propeller area ratio, task 3.3).

    Returns:
        PropulsionFactors with w, t, eta_r and eta_h.

    Raises:
        SpecValidationError: inputs out of range or the resulting
            factors leave their physical bands (w outside 0..0.4,
            t outside -0.1..0.3).
    """
    if screw not in ("single", "twin"):
        raise SpecValidationError(
            "screw", screw, "'single' or 'twin'",
            "the wake and thrust-deduction correlations are split by "
            "screw count (Eqs. 5-38/5-39 and 5-48/5-49).",
        )
    for name, value in (
        ("lpp_m", lpp_m), ("lwl_m", lwl_m), ("beam_m", beam_m),
        ("draft_m", draft_m), ("propeller_diameter_m",
                               propeller_diameter_m),
        ("speed_ms", speed_ms),
    ):
        if not math.isfinite(value) or value <= 0:
            raise SpecValidationError(
                name, value, f"finite {name} > 0",
                "the propulsion correlation works on physical "
                "positives.",
            )
    if not 0.0 < cb < 1.0 or not 0.0 < cp <= 1.0 or not 0.0 < cm <= 1.0:
        raise SpecValidationError(
            "coefficients", [cb, cp, cm], "0 < Cb, Cp, Cm <= 1",
            "the hull form coefficients are volume/area ratios.",
        )
    if not math.isfinite(form_factor) or form_factor < 1.0:
        raise SpecValidationError(
            "form_factor", form_factor, ">= 1.0",
            "(1+k) is the viscous-resistance increment over friction; "
            "a value below 1 would mean form relief below the flat "
            "plate.",
        )

    tf = draft_fore_m if draft_fore_m is not None else draft_m
    ta = draft_aft_m if draft_aft_m is not None else draft_m
    length = lwl_m
    beam = beam_m
    draft = draft_m

    # auxiliary chain of Eq. 5-38
    cf = _ittc1957_cf(
        1.025 * speed_ms * length / SEAWATER_KINEMATIC_VISCOSITY
    )
    c4 = min(tf / lpp_m, 0.04)
    c_a = (
        0.006 * (length + 100.0) ** (-0.16) - 0.00205
        + 0.003 * math.sqrt(length / 7.5)
        * cb**4
        * _bulb_c2(bulb_area_m2, bulb_height_m, beam_m, tf)
        * (0.04 - c4)
    )
    c_v = form_factor * cf + c_a

    wetted_surface = (
        length * (2.0 * draft_m + beam_m)
        * cm * (
            0.453 + 0.4425 * cb - 0.2862 * cm
            - 0.003467 * beam / draft_m + 0.3696 * cwp
        )
        + 2.38 * bulb_area_m2 / cb
    )
    c8 = (
        wetted_surface / (length * draft_m)
        if beam / ta < 5
        else wetted_surface * (7.0 * beam / ta - 25.0)
        / (length * (beam / draft_m - 3.0))
    )
    c9 = c8 if c8 < 28 else 32.0 - 16.0 / (c8 - 24.0)
    c11 = (
        ta / propeller_diameter_m
        if ta / propeller_diameter_m < 2
        else 0.0833333 * (ta / propeller_diameter_m) ** 3 + 1.33333
    )
    cp1 = 1.45 * cp - 0.315 - 0.0225 * lcb_pct_fwd

    if screw == "single":
        w = (
            c9 * c_v * (length / ta)
            * (0.0661875 + 1.21756 * c11 * c_v / (1.0 - cp1))
            + 0.24558 * math.sqrt(beam / (length * (1.0 - cp1)))
            - 0.09726 / (0.95 - cp)
            + 0.11434 / (0.95 - cb)
            + 0.75 * c_stern * c_v
            + 0.002 * c_stern
        )
        c10 = (
            beam / length
            if length / beam > 5.2
            else 0.25 - 0.003328402 / (beam / length - 0.134615385)
        )
        t = (
            0.001979 * length / (beam - beam * cp1)
            + 1.0585 * c10 - 0.000524
            - 0.1418 * propeller_diameter_m**2 / (beam * draft_m)
            + 0.0015 * c_stern
        )
    else:
        w = (
            0.3095 * cb + 10.0 * c_v * cb
            - 0.23 * propeller_diameter_m / math.sqrt(beam * draft_m)
        )
        t = (
            0.325 * cb
            - 0.1885 * propeller_diameter_m / math.sqrt(beam * draft_m)
        )

    if not 0.0 <= w <= 0.4:
        raise SpecValidationError(
            "w", w, "0 <= wake fraction <= 0.4",
            "the correlation returned a wake fraction outside its "
            "physical band; check the inputs (this is a refusal, not "
            "an extrapolation).",
        )
    if not -0.1 <= t <= 0.3:
        raise SpecValidationError(
            "t", t, "-0.1 <= thrust deduction <= 0.3",
            "the correlation returned a thrust deduction outside its "
            "physical band; check the inputs.",
        )

    eta_r_value = 1.0 if eta_r is None else eta_r
    if eta_r is not None and (
        not math.isfinite(eta_r) or not 0.8 <= eta_r <= 1.15
    ):
        raise SpecValidationError(
            "eta_r", eta_r, "0.8 <= eta_R <= 1.15",
            "the relative rotative efficiency of conventional screws "
            "stays within this band (book: 0.98-1.05 single screw).",
        )
    eta_h = (1.0 - t) / (1.0 - w)
    return PropulsionFactors(
        w=w, t=t, eta_r=eta_r_value, eta_h=eta_h,
        c_v=c_v, c_a=c_a, c_f=cf,
        wetted_surface_m2=wetted_surface,
        c_stern=c_stern, form_factor=form_factor,
    )


def _bulb_c2(bulb_area_m2: float, bulb_height_m: float, beam_m: float,
             draft_fore_m: float) -> float:
    """C2 = exp(-1.89*sqrt(C3)), C3 per 5-38 (no bulb -> 1.0)."""
    if bulb_area_m2 <= 0:
        return 1.0
    c3 = (
        0.54 * bulb_area_m2 ** 1.5
        / (
            beam_m * draft_fore_m
            * (0.31 * math.sqrt(bulb_area_m2) + draft_fore_m
               - bulb_height_m)
        )
    )
    return math.exp(-1.89 * math.sqrt(c3))


@dataclass(frozen=True)
class SpeedSolution:
    """Service speed solved from delivered power (JSON-ready).

    Attributes:
        speed_kn: the balanced still-water speed, knots.
        dhp_kw: delivered power placed on the propeller, kW.
        eta_d: propulsion efficiency eta_o*eta_R*eta_h used.
        pe_bare_kw: bare-hull effective power at the solution, kW.
        v_sqrt_l: the solution's speed-length ratio (knots/sqrt-ft),
            echoed to show the Ayre band margin.
    """

    speed_kn: float
    dhp_kw: float
    eta_d: float
    pe_bare_kw: float
    v_sqrt_l: float
    factors: PropulsionFactors | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.factors is not None:
            data["factors"] = self.factors.to_dict()
        return data


def solve_service_speed(
    *,
    dhp_kw: float,
    eta_open_water: float,
    lpp_m: float,
    lwl_m: float,
    beam_m: float,
    draft_m: float,
    cb: float,
    cp: float,
    cm: float,
    cwp: float,
    lcb_pct_fwd: float,
    propeller_diameter_m: float,
    displacement_t: float,
    speed_ms: float = 10.0,
    c_stern: float = 0.0,
    bulb_area_m2: float = 0.0,
    bulb_height_m: float = 0.0,
    form_factor: float = 1.3,
    screw: str = "single",
    eta_r: float | None = None,
    shaft_efficiency: float = 1.0,
) -> SpeedSolution:
    """Service speed from delivered power (plan task 3.2 acceptance).

    Solves V such that the bare-hull effective power of the task 3.1
    Ayre estimate equals eta_D * DHP, with eta_D = eta_o * eta_R *
    eta_h from :func:`propulsion_factors`.  The Ayre speed-length band
    (0.50-1.20 knots/sqrt-ft) brackets the search; a power demand that
    cannot be met inside the band is refused.

    Args:
        dhp_kw: delivered power at the propeller, kW (shaft power
            times the shaft efficiency).
        eta_open_water: propeller open-water efficiency eta_o (task
            3.3 supplies it; until then it is a declared input).
        shaft_efficiency: DHP/SHP ratio, default 1.0.

    Returns:
        SpeedSolution with the converged speed and the factor chain.

    Raises:
        SpecValidationError: inputs out of range, or the power cannot
            be balanced within the Ayre speed-length band.
    """
    if not math.isfinite(dhp_kw) or dhp_kw <= 0:
        raise SpecValidationError(
            "dhp_kw", dhp_kw, "finite DHP > 0",
            "the speed iteration balances effective power against the "
            "delivered power; without power there is no balance.",
        )
    if not math.isfinite(eta_open_water) or not 0.4 <= eta_open_water <= 0.85:
        raise SpecValidationError(
            "eta_open_water", eta_open_water, "0.4 <= eta_o <= 0.85",
            "the open-water efficiency of conventional screws stays "
            "within this band; outside it the input is suspect.",
        )
    if not 0.8 <= shaft_efficiency <= 1.0:
        raise SpecValidationError(
            "shaft_efficiency", shaft_efficiency, "0.8 .. 1.0",
            "the shaft transmission loses at most a few per cent.",
        )

    factors = propulsion_factors(
        lpp_m=lpp_m, lwl_m=lwl_m, beam_m=beam_m, draft_m=draft_m,
        cb=cb, cp=cp, cm=cm, cwp=cwp, lcb_pct_fwd=lcb_pct_fwd,
        propeller_diameter_m=propeller_diameter_m,
        c_stern=c_stern, bulb_area_m2=bulb_area_m2,
        bulb_height_m=bulb_height_m, form_factor=form_factor,
        speed_ms=speed_ms, screw=screw, eta_r=eta_r,
    )
    eta_d = eta_open_water * factors.eta_r * factors.eta_h
    target = dhp_kw * shaft_efficiency * eta_d

    def balance_error(speed_kn: float) -> float:
        ayre = ayre_effective_power(
            displacement_t=displacement_t, speed_kn=speed_kn,
            lpp_m=lpp_m, beam_m=beam_m, draft_m=draft_m, cb=cb,
            xc_pct_fwd=lcb_pct_fwd, lwl_m=lwl_m, screw=screw,
        )
        return ayre.pe_bare_kw - target

    ft_per_m = 1.0 / 0.3048
    l_ft = lpp_m * ft_per_m
    # scan the Ayre band for consecutive valid stations that bracket
    # the balance point (the LCB-offset guard of 3.1 can bar parts of
    # the band for a given ship)
    n_steps = 140  # 0.005 in V/sqrt(L)
    prev_v, prev_err = None, None
    lo_v = hi_v = None
    for i in range(n_steps + 1):
        ratio = 0.50 + 0.70 * i / n_steps
        v = ratio * math.sqrt(l_ft)
        try:
            err = balance_error(v)
        except SpecValidationError:
            prev_v, prev_err = None, None
            continue
        if prev_err is not None and (prev_err < 0 <= err or err < 0 <= prev_err):
            lo_v, hi_v = prev_v, v
            break
        prev_v, prev_err = v, err
    if lo_v is None:
        raise SpecValidationError(
            "dhp_kw", dhp_kw,
            "balanceable within the Ayre band (V/sqrt(L) 0.50-1.20)",
            "no speed in the validated band balances the delivered "
            "power against this hull's effective-power curve "
            f"(DHP {dhp_kw:,.0f} kW x eta_D {eta_d:.3f} x eta_S "
            f"{shaft_efficiency:.2f} -> required P_E {target:,.0f} kW); "
            "the power lies outside what the ship can usefully absorb "
            "in that band.",
        )
    for _ in range(50):
        mid = 0.5 * (lo_v + hi_v)
        if balance_error(mid) < 0:
            lo_v = mid
        else:
            hi_v = mid
    speed = 0.5 * (lo_v + hi_v)
    ayre = ayre_effective_power(
        displacement_t=displacement_t, speed_kn=speed, lpp_m=lpp_m,
        beam_m=beam_m, draft_m=draft_m, cb=cb, xc_pct_fwd=lcb_pct_fwd,
        lwl_m=lwl_m, screw=screw,
    )
    return SpeedSolution(
        speed_kn=speed,
        dhp_kw=dhp_kw,
        eta_d=eta_d,
        pe_bare_kw=ayre.pe_bare_kw,
        v_sqrt_l=speed / math.sqrt(l_ft),
        factors=factors,
    )