"""Propeller preliminary design (plan task 3.3): cavitation check stage.

Burrill limit-line cavitation check as transcribed in Ship Theory
vol. 2, section 6-5 (every formula visually verified against the
scanned original page, 2026-09-22):

  cavitation number       sigma_0.7R = (p0 - pv) / (1/2 rho V^2_0.7R)
                          Eq.(6-14); the printed p0 = pa + gamma*hs
  thrust loading          tau_c = T / (A_P * 1/2 rho V^2_0.7R)  Eq.(6-15)
  projected area          A_P ~ A_E*(1.067 - 0.229 P/D)       Eq.(6-16)
  relative velocity       V^2_0.7R = V_A^2 + (0.7 pi n D)^2

The commercial-ship limit line tau_c(sigma) is carried as the book's
own chart readings (author-read values, not our digitisation), held in
BURRILL_COMMERCIAL_LINE.  They come from two worked examples:

  table 8-29 row 6 (MAU4-40/55/70 example, read from figure 6-20
  commercial upper limit):   (0.389, 0.162) (0.407, 0.164) (0.416, 0.169)
  table 6-2  row 10 (25,000 t bulk carrier AU5-65 example, read from
  the figure 6-22 re-plotting):  (0.481, 0.175)

The two figures are the same Burrill commercial line in two
re-printings; the four points are mutually consistent and monotone.
Because only these four book-read points are verified, the line is
usable in sigma in [0.389, 0.481] and the module REFUSES outside
(design principle 3).  Extending the line needs a verified source for
the full curve and is parked in the internal data-acquisition backlog.

Note on conventions: table 6-2 computes sigma with p0 alone while
table 8-29 subtracts the vapour pressure (p0 - pv); sigma_0_7r() takes
the effective pressure explicitly so both book conventions are
reproducible.  The vapour pressure at 15 deg C is 174 kgf/m^2 = 1706 Pa
in the book's units.

The open-water series model and the design engine land here after the
route experiment decided by the owner (digitised AU5-50 chart data vs
a published B-series regression) - see AGENTS.md section 5.

Units per AGENTS.md section 1 (SI).  Book anchors are kgf/m^2-based;
conversions use g = 9.80665 and are covered by tests.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

from .spec import SpecValidationError

__all__ = [
    "BURRILL_COMMERCIAL_LINE",
    "burrill_tau_c_limit",
    "sigma_0_7r",
    "required_expanded_area",
    "check_cavitation",
    "CavitationCheck",
    "VAPOUR_PRESSURE_15C_PA",
    "STANDARD_ATMOSPHERE_PA",
]

#: standard atmosphere, Pa (book: pa = 10330 kgf/m^2 = 101326 Pa)
STANDARD_ATMOSPHERE_PA = 101325.0

#: water vapour pressure at 15 deg C, Pa (book: pv = 174 kgf/m^2)
VAPOUR_PRESSURE_15C_PA = 1706.0

#: seawater density, kg/m^3 (book tables use rho = 104.6 kgf*s^2/m^4)
SEAWATER_DENSITY = 1025.9

#: Burrill commercial-ship limit line, book-read anchor points
#: (sigma_0.7R, tau_c_max), sorted by sigma.  Sources: Ship Theory
#: vol. 2 tables 6-2/8-29 (author readings of figures 6-22 / 6-20).
BURRILL_COMMERCIAL_LINE: Tuple[Tuple[float, float], ...] = (
    (0.389, 0.162),
    (0.407, 0.164),
    (0.416, 0.169),
    (0.481, 0.175),
)

# usable sigma domain of the four verified anchor points; the endpoints
# are book prints rounded to 3 significant digits and the book's own
# worked chains carry ~0.3% rounding drift (e.g. sigma 0.481 computes
# to 0.4811-0.4823 from the rounded V_A/V_tip inputs), so the guard
# carries a +/- 0.002 band
_SIGMA_MIN = BURRILL_COMMERCIAL_LINE[0][0] - 2e-3
_SIGMA_MAX = BURRILL_COMMERCIAL_LINE[-1][0] + 2e-3


def _check_positive(name: str, value: float) -> None:
    if value <= 0:
        raise SpecValidationError(
            name, value, "> 0",
            "a non-positive physical quantity cannot describe an "
            "operating propeller (speeds, revolutions, diameter, "
            "thrust and pressures are strictly positive).")


def sigma_0_7r(
    va_ms: float,
    n_rps: float,
    diameter_m: float,
    p0_eff_pa: float,
    *,
    rho: float = SEAWATER_DENSITY,
) -> float:
    """Cavitation number at 0.7R per Eq.(6-14) with V^2_0.7R per the
    printed relative-velocity expression.

    p0_eff_pa is the effective static pressure at the shaft centre as
    used in the sigma numerator, i.e. pa + rho*g*hs, minus pv if the
    caller follows the table 8-29 convention (both book examples are
    reproducible; see module docstring).
    """
    _check_positive("va_ms", va_ms)
    _check_positive("n_rps", n_rps)
    _check_positive("diameter_m", diameter_m)
    _check_positive("p0_eff_pa", p0_eff_pa)
    v_tip = 0.7 * math.pi * n_rps * diameter_m
    v_sq = va_ms * va_ms + v_tip * v_tip
    return p0_eff_pa / (0.5 * rho * v_sq)


def burrill_tau_c_limit(sigma: float) -> float:
    """Commercial-ship Burrill limit tau_c at a verified sigma.

    Piecewise-linear through the book-read anchor points.  Refuses
    sigma outside [0.389, 0.481] - the extent verified by the book's
    own readings.
    """
    if not (_SIGMA_MIN <= sigma <= _SIGMA_MAX):
        raise SpecValidationError(
            "sigma_0_7r", sigma,
            f"in [{_SIGMA_MIN:.3f}, {_SIGMA_MAX:.3f}]",
            "the Burrill commercial-ship limit line is carried only at "
            "the four sigma values read by the book's own examples "
            "(0.389 / 0.407 / 0.416 / 0.481, tables 6-2 and 8-29); "
            "extending the line needs a verified full-curve source, so "
            "operation outside this band is refused rather than "
            "extrapolated.")
    pts = BURRILL_COMMERCIAL_LINE
    # the guard band (book print rounding) may put sigma just outside
    # the end anchors: extend the end segments linearly there (at the
    # low-sigma end this is the conservative direction - it asks for
    # more area, never less)
    if sigma < pts[0][0]:
        (s0, t0), (s1, t1) = pts[0], pts[1]
    elif sigma > pts[-1][0]:
        (s0, t0), (s1, t1) = pts[-2], pts[-1]
    else:
        for (s0, t0), (s1, t1) in zip(pts, pts[1:]):
            if s0 <= sigma <= s1:
                return t0 + (t1 - t0) * (sigma - s0) / (s1 - s0)
        raise AssertionError("unreachable")  # pragma: no cover
    return t0 + (t1 - t0) * (sigma - s0) / (s1 - s0)


def required_expanded_area(
    thrust_n: float,
    va_ms: float,
    n_rps: float,
    diameter_m: float,
    pitch_ratio: float,
    p0_eff_pa: float,
    *,
    rho: float = SEAWATER_DENSITY,
) -> Tuple[float, float, float]:
    """Minimum expanded area to sit on the Burrill commercial limit.

    Returns (sigma, tau_c_limit, A_E_required_m2) using Eq.(6-15)
    inverted for the area and Eq.(6-16) inverted for the expanded
    area: the printed relation is A_P = A_E*(1.067 - 0.229 P/D)
    (verified numerically against table 6-2: A_P 14.80 m2 ->
    A_E 16.68 m2 at P/D 0.782), so A_E = A_P / (1.067 - 0.229 P/D).
    Raises if sigma falls outside the verified domain.
    """
    _check_positive("thrust_n", thrust_n)
    sigma = sigma_0_7r(va_ms, n_rps, diameter_m, p0_eff_pa, rho=rho)
    tau = burrill_tau_c_limit(sigma)
    v_tip = 0.7 * math.pi * n_rps * diameter_m
    q = 0.5 * rho * (va_ms * va_ms + v_tip * v_tip)
    ap_required = thrust_n / (tau * q)
    ae_required = ap_required / (1.067 - 0.229 * pitch_ratio)
    return sigma, tau, ae_required


@dataclass(frozen=True)
class CavitationCheck:
    """Result of a Burrill cavitation check against an installed area."""

    sigma_0_7r: float
    tau_c_limit: float
    ae_required_m2: float
    aeao_required: float
    aeao_available: float
    ok: bool
    margin: float
    """aeao_available - aeao_required (negative = shortfall)."""

    verdict: str
    """Human-readable verdict; a shortfall names the missing area."""


def check_cavitation(
    thrust_n: float,
    va_ms: float,
    n_rps: float,
    diameter_m: float,
    pitch_ratio: float,
    aeao_available: float,
    *,
    hs_m: float,
    pa: float = STANDARD_ATMOSPHERE_PA,
    pv: float = VAPOUR_PRESSURE_15C_PA,
    subtract_vapour: bool = True,
    rho: float = SEAWATER_DENSITY,
) -> CavitationCheck:
    """Full Burrill check of one propeller operating point.

    The static pressure at the shaft centre is pa + rho*g*hs, minus
    pv when subtract_vapour is set (the table 8-29 convention, used
    here as the default because the anchors of table 8-29 anchor the
    lower end of the line).  Raises SpecValidationError when the
    operating sigma falls outside the verified line domain.
    """
    _check_positive("hs_m", hs_m)
    _check_positive("aeao_available", aeao_available)
    p0 = pa + rho * 9.80665 * hs_m
    if subtract_vapour:
        p0 -= pv
    sigma, tau, ae_req = required_expanded_area(
        thrust_n, va_ms, n_rps, diameter_m, pitch_ratio, p0_eff_pa=p0,
        rho=rho)
    a0 = math.pi / 4.0 * diameter_m * diameter_m
    aeao_req = ae_req / a0
    margin = aeao_available - aeao_req
    if margin >= 0.0:
        verdict = (
            f"OK: installed AE/A0 {aeao_available:.3f} covers the "
            f"required {aeao_req:.3f} (margin {margin:+.3f})")
    else:
        verdict = (
            f"SHORTFALL: installed AE/A0 {aeao_available:.3f} is below "
            f"the required {aeao_req:.3f} (margin {margin:+.3f}); a "
            f"larger expanded area is needed at this operating point")
    return CavitationCheck(
        sigma_0_7r=sigma,
        tau_c_limit=tau,
        ae_required_m2=ae_req,
        aeao_required=aeao_req,
        aeao_available=aeao_available,
        ok=margin >= 0.0,
        margin=margin,
        verdict=verdict,
    )
