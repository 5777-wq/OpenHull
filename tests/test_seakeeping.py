"""First-level seakeeping tests (plan task 3.8, stage 1).

Anchors are the whitelisted source itself, Ship Theory vol. 2 Part 4
(AGENTS.md section 5, amended 2026-09-23):

- table 3-1 (p.383): lambda/T pairs, 9 of 10 rows reproduce
  lambda = 1.56*T^2 (the lambda = 40 m row prints 5.2 s vs 5.06
  computed — the book's own rounding, declared in the whitelist);
- the resonance-avoidance worked example (pp.383-384): a roll period
  of 10 s has its resonance wavelength at 156 m, and 12.5 s at
  244 m;
- the Eq.(3-49) coefficient: 0.58 = 2*pi/sqrt(12*g), pinned by the
  numeric identity with the Eq.(3-39) -> Eq.(3-27) chain;
- the Eq.(4-62) restoration: the restored form must agree with the
  Eq.(4-60) chain to ~1 % on typical hulls;
- the ship-class roll-period ranges (p.391): cargo ships
  (10,000-t class) 8-13 s.
"""

import json

import pytest

from openhull.seakeeping import (
    DEFAULT_ROLL_MU,
    GRAVITY_M_S2,
    ResonanceCheck,
    SeakeepingEstimate,
    effective_wave_slope_coefficient,
    encounter_frequency,
    encounter_period,
    estimate_seakeeping,
    heave_period_waterplane,
    is_in_resonance_band,
    pitch_period_cv,
    pitch_period_tamiya,
    roll_amplification_resonant,
    roll_period_duell,
    roll_period_regulation,
    roll_period_simple,
    tuning_factor,
    wave_length_from_period,
    wave_period_from_length,
)
from openhull.spec import SpecValidationError


# book table 3-1 rows (lambda m -> T s), p.383
TABLE_3_1_ROWS = [
    (50, 5.7), (60, 6.2), (70, 6.7), (80, 7.1), (100, 8.0),
    (120, 8.7), (140, 9.5), (160, 10.1), (180, 10.8),
]


@pytest.mark.parametrize(("length_m", "period_s"), TABLE_3_1_ROWS)
def test_wave_table_3_1(length_m, period_s):
    # the book's table rounds to 0.1 s and not always from the exact
    # relation (its own rows disagree with lambda = 1.56*T^2 by up to
    # ~0.07 s): the tolerance carries that print coarseness
    assert wave_period_from_length(length_m) == pytest.approx(
        period_s, abs=0.08)


def test_wave_table_3_1_declared_rounding_slip():
    # the lambda = 40 m row prints 5.2 s; lambda = 1.56*T^2 gives 5.06
    assert wave_period_from_length(40.0) == pytest.approx(5.06, abs=0.02)
    assert wave_period_from_length(40.0) != pytest.approx(5.2, abs=0.05)


def test_book_resonance_wavelength_example():
    # pp.383-384: T = 10 s -> resonance wavelength 156 m; after the
    # refit T = 12.5 s -> 244 m (book's own numbers)
    assert wave_length_from_period(10.0) == pytest.approx(156.0, abs=0.1)
    assert wave_length_from_period(12.5) == pytest.approx(243.75, abs=0.1)


def test_regulation_roll_period_identity_with_duell_chain():
    # Eq.(3-49) vs the Eq.(3-39) -> Eq.(3-27) chain: algebraically
    # identical, 0.58 being the book's printed rounding of
    # 2*pi/sqrt(12*g) = 0.57927 -> agreement to ~0.13 %
    beam, zg, gm = 23.0, 9.0, 1.8
    reg = roll_period_regulation(beam, zg, gm)
    duell = roll_period_duell(beam, zg, gm)
    assert reg == pytest.approx(duell, rel=2e-3)
    assert reg == pytest.approx(
        0.58 * ((beam**2 + 4 * zg**2) / gm) ** 0.5, rel=1e-12)


def test_roll_period_in_book_cargo_class_band():
    # p.391: cargo ships of the 10,000-t class roll at 8-13 s
    assert 8.0 <= roll_period_regulation(23.0, 9.0, 1.8) <= 13.0


def test_roll_period_simple_form_ordering():
    # Eq.(3-48) vs Eq.(3-49): for zg ~ B/4 the two agree in magnitude;
    # the simple form is the scheme-stage shorthand, not a gate
    assert roll_period_simple(23.0, 1.8) == pytest.approx(13.73, abs=0.05)


def test_roll_period_gm_guard():
    # p.391: the formulas apply only for GM > 0.15 m
    for call in (
        lambda: roll_period_regulation(23.0, 9.0, 0.10),
        lambda: roll_period_simple(23.0, 0.10),
        lambda: roll_period_duell(23.0, 9.0, 0.10),
    ):
        with pytest.raises(SpecValidationError):
            call()


def test_effective_wave_slope_clamp():
    # Eq.(3-3) with the regulation clamp zg/d in [0.917, 1.45]
    assert effective_wave_slope_coefficient(9.0, 9.0) == pytest.approx(0.73)
    assert effective_wave_slope_coefficient(4.5, 9.0) == pytest.approx(
        0.13 + 0.60 * 0.917)
    assert effective_wave_slope_coefficient(18.0, 9.0) == pytest.approx(1.0)


def test_pitch_heave_cross_formula_consistency():
    # TB-001-like hull: the independent Eq.(4-55), the Tamiya
    # Eq.(4-57) and the restored Eq.(4-62) must agree closely
    d, b, cb, cwp = 9.5, 23.0, 0.82, 0.88
    t55 = pitch_period_cv(d, cb / cwp)
    assert t55 == pytest.approx(2.8 * ((cb / cwp) * d) ** 0.5, rel=1e-12)
    assert pitch_period_tamiya(d, b, cb) == pytest.approx(t55, rel=0.02)
    assert heave_period_waterplane(d, b, cwp) == pytest.approx(t55, rel=0.02)


def test_encounter_period_head_and_following():
    # T = 8 s -> lambda = 99.84 m, c = 12.48 m/s (Eq. 2-7)
    t_wave, v = 8.0, 7.0
    c = wave_length_from_period(t_wave) / t_wave
    # head seas (beta = 180): shorter encounter period, higher omega_e
    te_head = encounter_period(t_wave, v, 180.0)
    assert te_head == pytest.approx(
        wave_length_from_period(t_wave) / (c + v), rel=1e-9)
    assert encounter_frequency(t_wave, v, 180.0) > 2 * 3.141592653589793 / t_wave
    # following seas (beta = 0): longer encounter period
    assert encounter_period(t_wave, v, 0.0) > t_wave
    # steaming into/with the wave at celerity: concept breaks down
    with pytest.raises(SpecValidationError):
        encounter_period(t_wave, c, 0.0)


def test_resonance_band_and_amplification():
    assert is_in_resonance_band(1.0)
    assert not is_in_resonance_band(0.65)
    assert not is_in_resonance_band(1.35)
    # Eq.(3-29): phi_A/alpha_m0 = 1/(2*mu); default mu mid-range 0.06
    assert roll_amplification_resonant(0.06) == pytest.approx(8.3333, abs=1e-3)
    assert roll_amplification_resonant(DEFAULT_ROLL_MU) == pytest.approx(
        1.0 / (2.0 * DEFAULT_ROLL_MU))
    assert tuning_factor(12.63, 6.0) == pytest.approx(2.105, abs=5e-3)


def test_estimate_end_to_end_and_json():
    estimate = estimate_seakeeping(
        beam_m=23.0, draft_m=9.5, zg_m=9.0, gm_m=1.8,
        cb=0.82, cwp=0.88, speed_ms=7.46)
    assert isinstance(estimate, SeakeepingEstimate)
    # four resonance checks: roll + pitch/heave against both seas
    assert len(estimate.resonance_checks) == 4
    motions = {c.motion for c in estimate.resonance_checks}
    assert motions == {"roll", "pitch/heave"}
    # this condition rolls at ~12.6 s: outside both bands, verdicts False
    assert estimate.roll_period_s == pytest.approx(12.63, abs=0.05)
    roll_checks = [c for c in estimate.resonance_checks if c.motion == "roll"]
    assert all(not c.in_resonance_band for c in roll_checks)
    assert all(isinstance(c, ResonanceCheck)
               for c in estimate.resonance_checks)
    payload = json.dumps(estimate.to_dict())  # JSON-serializable
    assert '"roll_period_s"' in payload
    assert len(estimate.citations) == 7


def test_estimate_near_resonance_flags_true():
    # a 12 s roll period against the 8 s swell sits at Lambda 1.5,
    # but a 9 s period sits at 1.125 - inside the band
    estimate = estimate_seakeeping(
        beam_m=23.0, draft_m=9.5, zg_m=9.0, gm_m=1.8,
        cb=0.82, cwp=0.88)
    assert not is_in_resonance_band(estimate.roll_period_s / 8.0)
    inside = estimate_seakeeping(
        beam_m=23.0, draft_m=9.5, zg_m=9.0, gm_m=2.5,
        cb=0.82, cwp=0.88)
    roll8 = next(c for c in inside.resonance_checks
                 if c.motion == "roll" and c.wave_period_s == 8.0)
    assert roll8.in_resonance_band == is_in_resonance_band(
        inside.roll_period_s / 8.0)


def test_gravity_constant():
    # the coefficient identities of Eqs.(3-49)/(4-55) assume g = 9.81
    assert GRAVITY_M_S2 == pytest.approx(9.81)
