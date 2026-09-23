"""First-level seakeeping estimate (plan task 3.8, stage 1).

Textbook formulas only, Ship Theory vol. 2 (Sheng Zhenbang & Liu
Yingzhong), Part 4 (seakeeping) — whitelisted in AGENTS.md section 5
(2026-09-23); every formula re-verified against rendered pages of the
text-layer PDF at whitelisting time (printed page = PDF page - 5):

  wave relations        Eq.(2-7)    lambda = 1.56*T^2, T ≈ 0.8*sqrt(lambda)
  encounter             Eqs.(2-98)/(2-99)  beta: 0 deg following, 180 head
  roll natural period   Eqs.(3-27)/(3-39)/(3-49)/(3-48), GM > 0.15 m
  effective wave slope  Eq.(3-3)    K = 0.13 + 0.60*zg/d, clamp [0.917, 1.45]
  resonance             Eq.(3-29)   amplification 1/(2*mu), band 0.7<Lambda<1.3
  pitch / heave         Eqs.(4-55)/(4-57)/(4-60)/(4-62)

Declared print defects, kept OUT of the implementation (AGENTS.md 5):
  Eq.(4-56) prints 2.4*sqrt(d), inconsistent with Eq.(4-55) at
  Cvp = 0.9 (which gives 2.66*sqrt(d)) — book slip, not implemented;
  Eq.(4-62) prints T_z = sqrt((d + 0.24B)/Cw) with the 2*pi/sqrt(g)
  factor lost — restored through its own derivation chain
  (4-59)/(4-60) and flagged [DERIV]; the printed form is NOT used.

The roll-period formulas use the GM value the caller passes; per the
book's regulation usage (p.391) that is the GM WITHOUT free-surface
correction.  Damping coefficients: the book prints ranges (roll
0.05-0.07, p.427); the module takes mu as an input with 0.06 as the
declared default (mid-range assumption).

Out of scope: wave speed loss — the source defines the indicator
(Eqs.(5-1)-(5-3)) but prints NO estimation formula (AGENTS.md 5,
scope boundary).

Units per AGENTS.md section 1.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from .spec import SpecValidationError

__all__ = [
    "wave_length_from_period",
    "wave_period_from_length",
    "encounter_period",
    "encounter_frequency",
    "effective_wave_slope_coefficient",
    "roll_period_regulation",
    "roll_period_simple",
    "roll_period_duell",
    "pitch_period_cv",
    "pitch_period_tamiya",
    "heave_period_waterplane",
    "heave_period_cv",
    "tuning_factor",
    "is_in_resonance_band",
    "roll_amplification_resonant",
    "roll_amplification",
    "extinction_coefficient",
    "resonant_roll_amplitude",
    "ResonanceCheck",
    "SeakeepingEstimate",
    "estimate_seakeeping",
]

#: standard gravity, m/s^2 (AGENTS.md section 1)
GRAVITY_M_S2 = 9.81

#: roll decay coefficient mu, declared default — book range 0.055-0.07
#: for ships WITH bilge keels (p.394), mid-range assumption [ASSUMED]
DEFAULT_ROLL_MU = 0.06

#: book mu ranges (p.394): linear range, model-test totals
ROLL_MU_RANGES = {
    "no bilge keel": (0.035, 0.05),
    "with bilge keel": (0.055, 0.07),
}

#: preliminary-estimate extinction coefficient B20, general ships
#: (p.393: "在初步估算时, 一般船舶可取 B20 = 0.0200"); the book's
#: large-cargo-ship table value prints B15 = 0.0190, which folds to
#: B20 ~ 0.0173 through the 0.32 power law of table 3-6
DEFAULT_B20 = 0.02

#: resonance amplitude solve convergence
_AMPLITUDE_TOL = 1e-6

#: resonance band 0.7 < Lambda < 1.3 (p.383)
RESONANCE_BAND = (0.7, 1.3)

#: minimum GM for which the roll-period formulas apply (p.391)
GM_MIN_M = 0.15

#: wave periods of the reference sea areas, s — East China Sea
#: commonly lambda 50-60 m (T ~ 6 s) and ocean swell lambda ~ 100 m
#: (T = 8 s), book resonance-avoidance examples (pp.383-384)
REFERENCE_SEAS: tuple[tuple[float, str], ...] = (
    (6.0, "East China Sea short wave (lambda 50-60 m)"),
    (8.0, "ocean swell (lambda ~ 100 m)"),
)

_CITATION_WAVE = "Ship Theory vol. 2, Eq.(2-7), p.344"
_CITATION_ENCOUNTER = "Ship Theory vol. 2, Eqs.(2-98)/(2-99), p.367"
_CITATION_WAVE_SLOPE = "Ship Theory vol. 2, Eq.(3-3), p.377"
_CITATION_ROLL = (
    "Ship Theory vol. 2, Eqs.(3-27)/(3-39)/(3-49)/(3-48), pp.389-391"
)
_CITATION_PITCH = "Ship Theory vol. 2, Eqs.(4-55)/(4-57)/(4-60), pp.427-428"
_CITATION_HEAVE = (
    "Ship Theory vol. 2, Eq.(4-62) restored via Eqs.(4-59)/(4-60), p.428"
)
_CITATION_RESONANCE = "Ship Theory vol. 2, Eq.(3-29) and band 0.7<Lambda<1.3, p.383"


def _require(condition: bool, field: str, value: Any, constraint: str,
             reason: str) -> None:
    if not condition:
        raise SpecValidationError(field, value, constraint, reason)


def wave_length_from_period(period_s: float) -> float:
    """Deep-water wavelength from the wave period, Eq.(2-7) p.344.

    lambda = 1.56 * T^2 (m, s).
    """
    _require(math.isfinite(period_s) and period_s > 0.0,
             "period_s", period_s, "finite T > 0",
             "wave period must be positive")
    return 1.56 * period_s * period_s


def wave_period_from_length(length_m: float) -> float:
    """Deep-water wave period from the wavelength, Eq.(2-7) p.344."""
    _require(math.isfinite(length_m) and length_m > 0.0,
             "length_m", length_m, "finite lambda > 0",
             "wavelength must be positive")
    return math.sqrt(length_m / 1.56)


def encounter_period(period_s: float, speed_ms: float,
                     wave_dir_deg: float) -> float:
    """Encounter period, Eq.(2-98) p.367.

    Te = lambda/(c - V*cos(beta)) with beta the encounter angle:
    0 deg following seas, 180 deg head seas (book convention, ch.1).
    """
    _require(math.isfinite(period_s) and period_s > 0.0,
             "period_s", period_s, "finite T > 0",
             "wave period must be positive")
    _require(math.isfinite(speed_ms) and speed_ms >= 0.0,
             "speed_ms", speed_ms, "finite V >= 0",
             "ship speed must be non-negative")
    _require(-180.0 <= wave_dir_deg <= 180.0,
             "wave_dir_deg", wave_dir_deg, "|beta| <= 180",
             "encounter angle out of range")
    length_m = 1.56 * period_s * period_s
    c_ms = length_m / period_s
    denom = c_ms - speed_ms * math.cos(math.radians(wave_dir_deg))
    _require(denom > 1e-9, "speed_ms", speed_ms,
             "V*cos(beta) < wave celerity",
             "following-seas speed reaches the wave celerity: the "
             "steady encounter concept breaks down")
    return length_m / denom


def encounter_frequency(period_s: float, speed_ms: float,
                        wave_dir_deg: float) -> float:
    """Encounter frequency, Eq.(2-99) p.367: omega_e = omega - omega^2*V*cos(beta)/g."""
    period = encounter_period(period_s, speed_ms, wave_dir_deg)
    return 2.0 * math.pi / period


def effective_wave_slope_coefficient(zg_m: float, draft_m: float) -> float:
    """Effective wave-slope coefficient, Eq.(3-3) p.377.

    K = 0.13 + 0.60*zg/d with the regulation clamp zg/d in
    [0.917, 1.45] (p.377: K shall not be too small nor exceed 1).
    """
    _require(math.isfinite(zg_m) and zg_m > 0.0,
             "zg_m", zg_m, "finite zg > 0", "KG must be positive")
    _require(math.isfinite(draft_m) and draft_m > 0.0,
             "draft_m", draft_m, "finite d > 0", "draft must be positive")
    ratio = zg_m / draft_m
    ratio = min(max(ratio, 0.917), 1.45)
    return 0.13 + 0.60 * ratio


def _gm_guard(gm_m: float) -> None:
    _require(math.isfinite(gm_m) and gm_m > GM_MIN_M,
             "gm_m", gm_m, f"finite GM > {GM_MIN_M} m",
             "roll-period formulas are applicable only for "
             f"GM > {GM_MIN_M} m (Ship Theory vol. 2, p.391)")


def roll_period_regulation(beam_m: float, zg_m: float, gm_m: float) -> float:
    """Roll natural period, regulation form Eq.(3-49) p.391.

    T_phi = 0.58*sqrt((B^2 + 4*zg^2)/GM); the printed coefficient
    0.58 absorbs g (= 2*pi/sqrt(12*g) = 0.57927 to the book's
    rounding, verified against the Eq.(3-39) -> Eq.(3-27) chain to
    0.13 %), so the radical contains no g.
    GM per the regulation usage: WITHOUT free-surface correction
    (p.391).  Applicable only for GM > 0.15 m.
    """
    _require(math.isfinite(beam_m) and beam_m > 0.0,
             "beam_m", beam_m, "finite B > 0", "beam must be positive")
    _require(math.isfinite(zg_m) and zg_m > 0.0,
             "zg_m", zg_m, "finite zg > 0", "KG must be positive")
    _gm_guard(gm_m)
    return 0.58 * math.sqrt((beam_m**2 + 4.0 * zg_m**2) / gm_m)


def roll_period_simple(beam_m: float, gm_m: float) -> float:
    """Scheme-stage roll period, Eq.(3-48) p.390: T_phi = 0.8*B/sqrt(GM)."""
    _require(math.isfinite(beam_m) and beam_m > 0.0,
             "beam_m", beam_m, "finite B > 0", "beam must be positive")
    _gm_guard(gm_m)
    return 0.8 * beam_m / math.sqrt(gm_m)


def roll_period_duell(beam_m: float, zg_m: float, gm_m: float) -> float:
    """Roll period through the Duell inertia, Eqs.(3-39)/(3-27) pp.389.

    Ixx' = D/(12*g)*(B^2 + 4*zg^2), T = 2*pi*sqrt(Ixx'/(D*GM));
    the displacement cancels, leaving
    T = 2*pi*sqrt((B^2 + 4*zg^2)/(12*g*GM)).  Implemented as the
    derivation cross-check of Eq.(3-49): algebraically identical,
    the printed 0.58 being the book's rounding of
    2*pi/sqrt(12*g) (agreement 0.13 %, pinned in tests).
    Applicable only for GM > 0.15 m.
    """
    _require(math.isfinite(beam_m) and beam_m > 0.0,
             "beam_m", beam_m, "finite B > 0", "beam must be positive")
    _require(math.isfinite(zg_m) and zg_m > 0.0,
             "zg_m", zg_m, "finite zg > 0", "KG must be positive")
    _gm_guard(gm_m)
    return 2.0 * math.pi * math.sqrt(
        (beam_m**2 + 4.0 * zg_m**2) / (12.0 * GRAVITY_M_S2 * gm_m))


def pitch_period_cv(draft_m: float, cvp: float) -> float:
    """Pitch natural period, Eq.(4-55) p.427: T_theta = 2.8*sqrt(Cvp*d).

    The coefficient absorbs g (verified through the printed
    derivation chain 4-53 -> 4-55).  Cvp is the VERTICAL prismatic
    coefficient Cvp = Cb/Cw (not the longitudinal Cp).
    """
    _require(math.isfinite(draft_m) and draft_m > 0.0,
             "draft_m", draft_m, "finite d > 0", "draft must be positive")
    _require(math.isfinite(cvp) and 0.0 < cvp <= 1.0,
             "cvp", cvp, "0 < Cvp <= 1",
             "vertical prismatic coefficient out of range")
    return 2.8 * math.sqrt(cvp * draft_m)


def pitch_period_tamiya(draft_m: float, beam_m: float, cb: float) -> float:
    """Pitch natural period, Tamiya formula Eq.(4-57) p.427.

    T_theta = 2.01*sqrt((0.77*Cb + 0.26)*(0.92*d + 0.44*B)).
    """
    _require(math.isfinite(draft_m) and draft_m > 0.0,
             "draft_m", draft_m, "finite d > 0", "draft must be positive")
    _require(math.isfinite(beam_m) and beam_m > 0.0,
             "beam_m", beam_m, "finite B > 0", "beam must be positive")
    _require(math.isfinite(cb) and 0.0 < cb <= 1.0,
             "cb", cb, "0 < Cb <= 1", "block coefficient out of range")
    return 2.01 * math.sqrt((0.77 * cb + 0.26) * (0.92 * draft_m + 0.44 * beam_m))


def heave_period_waterplane(draft_m: float, beam_m: float,
                            cwp: float) -> float:
    """Heave natural period, Eq.(4-62) p.428, restored form [DERIV].

    The print reads T_z = sqrt((d + 0.24*B)/Cw), which is
    dimensionally incomplete (sqrt of a length); the 2*pi/sqrt(g)
    factor was lost.  Restored through the equation's own derivation
    chain (Eqs.(4-59)/(4-60), which give T_z = 2.8*sqrt(Cvp*d)):
    T_z = 2*pi*sqrt((d + 0.24*B)/(g*Cw)).  The restored and the
    4-60 forms agree to ~1 % for typical hulls (pinned in tests).
    """
    _require(math.isfinite(draft_m) and draft_m > 0.0,
             "draft_m", draft_m, "finite d > 0", "draft must be positive")
    _require(math.isfinite(beam_m) and beam_m > 0.0,
             "beam_m", beam_m, "finite B > 0", "beam must be positive")
    _require(math.isfinite(cwp) and 0.0 < cwp <= 1.0,
             "cwp", cwp, "0 < Cw <= 1", "waterplane coefficient out of range")
    return 2.0 * math.pi * math.sqrt(
        (draft_m + 0.24 * beam_m) / (GRAVITY_M_S2 * cwp))


def heave_period_cv(draft_m: float, cvp: float) -> float:
    """Heave natural period, Eq.(4-60) p.428: T_z = 2.8*sqrt(Cvp*d).

    Algebraically identical to Eq.(4-55); the book states
    T_theta = T_z (Eq.(4-61)).  Kept as a separate entry point for
    citation clarity.
    """
    return pitch_period_cv(draft_m, cvp)


def tuning_factor(ship_period_s: float, wave_period_s: float) -> float:
    """Tuning factor Lambda = T_ship/T_wave (p.383: omega_wave/omega_ship)."""
    _require(math.isfinite(ship_period_s) and ship_period_s > 0.0,
             "ship_period_s", ship_period_s, "finite T > 0",
             "ship natural period must be positive")
    _require(math.isfinite(wave_period_s) and wave_period_s > 0.0,
             "wave_period_s", wave_period_s, "finite T > 0",
             "wave period must be positive")
    return ship_period_s / wave_period_s


def is_in_resonance_band(tuning: float) -> bool:
    """True inside the resonance band 0.7 < Lambda < 1.3 (p.383)."""
    return RESONANCE_BAND[0] < tuning < RESONANCE_BAND[1]


def roll_amplification_resonant(roll_mu: float) -> float:
    """Resonant roll amplification, Eq.(3-29) p.388: phi_A/alpha_m0 = 1/(2*mu)."""
    _require(math.isfinite(roll_mu) and roll_mu > 0.0,
             "roll_mu", roll_mu, "finite mu > 0",
             "decay coefficient must be positive")
    return 1.0 / (2.0 * roll_mu)


def roll_amplification(tuning: float, roll_mu: float) -> float:
    """General roll magnification, Eq.(3-26) p.381.

    phi_A/alpha_m0 = 1/sqrt((1 - Lambda^2)^2 + 4*mu^2*Lambda^2).
    """
    _require(math.isfinite(roll_mu) and roll_mu > 0.0,
             "roll_mu", roll_mu, "finite mu > 0",
             "decay coefficient must be positive")
    return 1.0 / math.sqrt((1.0 - tuning**2) ** 2
                           + 4.0 * roll_mu**2 * tuning**2)


def extinction_coefficient(phi_a_deg: float,
                           b20: float = DEFAULT_B20) -> float:
    """Amplitude-dependent quadratic-roll extinction coefficient.

    Book closure of table 3-6 (p.393): B = B20*(20/phi_A_deg)^0.32,
    per DEGREE (the book's extinction curves plot degrees).  B20 is
    the value at 20 deg: 0.0200 for preliminary estimates of general
    ships (p.393); the large-cargo-ship table entry prints
    B15 = 0.0190, folding to B20 ~ 0.0173 through this law.
    """
    _require(math.isfinite(phi_a_deg) and phi_a_deg > 0.0,
             "phi_a_deg", phi_a_deg, "finite phi_A > 0",
             "roll amplitude must be positive")
    _require(math.isfinite(b20) and b20 > 0.0,
             "b20", b20, "finite B20 > 0",
             "extinction coefficient must be positive")
    return b20 * (20.0 / phi_a_deg) ** 0.32


def equivalent_linear_mu(phi_a_rad: float,
                         b20: float = DEFAULT_B20) -> float:
    """Equivalent linear decay coefficient of the quadratic roll
    damping at amplitude phi_A, Eq.(3-59) p.394.

    2*mu = (2/pi)*phi_A*B with phi_A in RADIANS and B in 1/radian;
    the book's extinction values are per degree, so the radian
    conversion is part of this declared implementation.
    """
    _require(math.isfinite(phi_a_rad) and phi_a_rad > 0.0,
             "phi_a_rad", phi_a_rad, "finite phi_A > 0",
             "roll amplitude must be positive")
    b_per_rad = extinction_coefficient(
        math.degrees(phi_a_rad), b20) * (180.0 / math.pi)
    return phi_a_rad * b_per_rad / math.pi


def resonant_roll_amplitude(effective_wave_slope_rad: float,
                            b20: float = DEFAULT_B20) -> float:
    """Resonant roll amplitude under quadratic damping, p.394 chain.

    Energy balance at resonance: the linear-theory amplification
    A/alpha_m0 = 1/(2*mu) (Eq. 3-29) with mu itself amplitude-
    dependent through the equivalent linearisation (Eq. 3-59), so
    A solves A = alpha_m0/(2*mu(A)) by fixed-point iteration.  The
    self-limiting behaviour is physical: a larger amplitude raises
    the equivalent damping, which caps the growth.  The excitation
    (effective wave slope alpha_m0 = K * 2*pi*zeta_A/lambda at the
    roll period) must come from the caller — without a sea state the
    resonant amplitude is undetermined.
    """
    _require(math.isfinite(effective_wave_slope_rad)
             and effective_wave_slope_rad > 0.0,
             "effective_wave_slope_rad", effective_wave_slope_rad,
             "finite alpha_m0 > 0",
             "the effective wave slope must be positive")
    amplitude = 0.2  # rad, ~11.5 deg starting point
    for _ in range(200):
        mu = equivalent_linear_mu(amplitude, b20)
        amplitude_new = effective_wave_slope_rad / (2.0 * mu)
        if abs(amplitude_new - amplitude) < _AMPLITUDE_TOL:
            return amplitude_new
        amplitude = amplitude_new
    return amplitude  # pragma: no cover - fixed point converges quickly


@dataclass(frozen=True)
class ResonanceCheck:
    """Resonance verdict of one natural period against one sea band."""

    label: str
    motion: str
    wave_period_s: float
    ship_period_s: float
    tuning_factor: float
    in_resonance_band: bool
    citation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SeakeepingEstimate:
    """First-level seakeeping estimate of one loading condition.

    All periods in seconds.  gm_m is echoed as passed in — per the
    regulation usage (p.391) the caller supplies the GM WITHOUT
    free-surface correction for the roll period.
    """

    beam_m: float
    draft_m: float
    zg_m: float
    gm_m: float
    roll_period_s: float
    roll_period_simple_s: float
    roll_period_duell_s: float
    effective_wave_slope_k: float
    pitch_period_s: float
    pitch_period_tamiya_s: float
    heave_period_s: float
    heave_period_cv_s: float
    roll_mu: float
    roll_amplification_resonant: float
    resonance_checks: tuple[ResonanceCheck, ...]
    citations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["resonance_checks"] = [c.to_dict() for c in self.resonance_checks]
        return data


def estimate_seakeeping(
    beam_m: float,
    draft_m: float,
    zg_m: float,
    gm_m: float,
    cb: float,
    cwp: float,
    speed_ms: float = 0.0,
    roll_mu: float = DEFAULT_ROLL_MU,
) -> SeakeepingEstimate:
    """Full first-level estimate for one condition (stage-1 layer).

    Pitch/heave resonance is checked at the head-sea encounter period
    of each reference sea at the given speed (Eqs.(2-98)/(2-99));
    roll resonance is checked against the wave period itself (beam
    seas, encounter = wave period, ch.3 assumption 1).
    """
    roll_reg = roll_period_regulation(beam_m, zg_m, gm_m)
    pitch_cv = pitch_period_cv(draft_m, cb / cwp)
    checks: list[ResonanceCheck] = []
    for wave_t, label in REFERENCE_SEAS:
        roll_tuning = tuning_factor(roll_reg, wave_t)
        checks.append(ResonanceCheck(
            label=label, motion="roll", wave_period_s=wave_t,
            ship_period_s=roll_reg, tuning_factor=roll_tuning,
            in_resonance_band=is_in_resonance_band(roll_tuning),
            citation=_CITATION_RESONANCE))
        enc_t = encounter_period(wave_t, speed_ms, 180.0)
        pitch_tuning = tuning_factor(pitch_cv, enc_t)
        checks.append(ResonanceCheck(
            label=f"{label}, head-sea encounter at "
                  f"{speed_ms:.1f} m/s", motion="pitch/heave",
            wave_period_s=wave_t, ship_period_s=pitch_cv,
            tuning_factor=pitch_tuning,
            in_resonance_band=is_in_resonance_band(pitch_tuning),
            citation=_CITATION_RESONANCE))
    return SeakeepingEstimate(
        beam_m=beam_m, draft_m=draft_m, zg_m=zg_m, gm_m=gm_m,
        roll_period_s=roll_reg,
        roll_period_simple_s=roll_period_simple(beam_m, gm_m),
        roll_period_duell_s=roll_period_duell(beam_m, zg_m, gm_m),
        effective_wave_slope_k=effective_wave_slope_coefficient(zg_m, draft_m),
        pitch_period_s=pitch_cv,
        pitch_period_tamiya_s=pitch_period_tamiya(draft_m, beam_m, cb),
        heave_period_s=heave_period_waterplane(draft_m, beam_m, cwp),
        heave_period_cv_s=heave_period_cv(draft_m, cb / cwp),
        roll_mu=roll_mu,
        roll_amplification_resonant=roll_amplification_resonant(roll_mu),
        resonance_checks=tuple(checks),
        citations=(_CITATION_WAVE, _CITATION_ENCOUNTER, _CITATION_WAVE_SLOPE,
                   _CITATION_ROLL, _CITATION_PITCH, _CITATION_HEAVE,
                   _CITATION_RESONANCE,
                   "Ship Theory vol. 2, damping chain Eqs.(3-51)/(3-57)-"
                   "(3-59) and tables 3-6/3-7, pp.392-394"),
    )
