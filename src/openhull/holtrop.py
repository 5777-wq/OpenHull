"""Holtrop-Mennen (1982) effective-power method — the second resistance
method, whitelisted for validation and cross-check (AGENTS.md section 5,
whitelist commit c254029 BEFORE this implementation).

Every formula was transcribed from rendered page images of the archived
paper (internal knowledge base Holtrop_1982, pp. 166-170) and verified
against the paper's own section-5 numerical example (L 205 m, 25 kn):
S 7381.45 m2, 1+k1 1.156, L_R 81.385 m, c12 0.5102, CF 0.001390,
iE 12.08 deg, c1 1.398, c2 0.7595, c3 0.02119, c5 0.9592, m1 -2.1274,
m2 -0.17087, lambda 0.6513, CA 0.000352, RF 869.63 kN, RAPP 8.83 kN,
RW 557.11 kN, RB 0.049 kN, RA 221.98 kN, Rtotal 1793.26 kN,
PE 23063 kW — every printed quantity reproduced (tests/test_holtrop.py).

Conventions (both verified against the example):
- Holtrop's lcb is % of the WATERLINE length, datum 1/2 L, forward
  positive.  Task books declare LCB as %Lpp forward of 1/2 Lpp; the
  conversion implemented here (and validated by the example: 2.02 %Lpp
  aft on Lpp 200 / L 205 -> lcb -0.75 %L) is
      lcb_h = (p·Lpp/100 + (L - Lpp)/2) / L · 100,
  i.e. the waterline-length datum sits (L-Lpp)/2 aft of 1/2 Lpp.
- C_B in the wetted-area formula is the block coefficient on L:
  nabla/(L·B·T) reproduces the example's S.
- nu = 1.18831e-6 m2/s (ITTC, 15 degC seawater) reproduces the
  example's Reynolds number / C_F.

Optional geometry (bulb A_BT with centre height h_B, transom area A_T,
appendage wetted area S_APP with 1+k2, stern shape C_stern) defaults to
zero / normal stern — an [ASSUMED] simplification the caller must
state.  Applicability: hulls resembling the regression sample's average
ship (the paper's own limitation); used as a validation / cross-check
method, not wired into the default chain.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .spec import SpecValidationError

SEAWATER_DENSITY = 1025.0  # kg/m3 (the paper's ideal-trial conditions)
GRAVITY = 9.81             # m/s2
KINEMATIC_VISCOSITY = 1.18831e-6  # m2/s, ITTC 15 degC seawater


@dataclass(frozen=True)
class HoltropPowerResult:
    speed_kn: float
    speed_ms: float
    froude_number: float
    lcb_holtrop_pct: float
    length_run_m: float
    form_factor: float                    # 1 + k1
    wetted_area_m2: float                 # S
    reynolds: float
    cf: float                             # ITTC-1957 friction coefficient
    r_friction_kn: float                  # R_F (without form factor)
    r_appendage_kn: float
    r_wave_kn: float
    r_bulb_kn: float
    r_transom_kn: float
    r_correlation_kn: float
    r_total_kn: float
    pe_kw: float                          # effective power = Rt * V
    coefficients: dict


def holtrop_lcb_from_taskbook(lcb_pct_lpp: float, lpp_m: float,
                              lwl_m: float) -> float:
    """Convert a task-book LCB (%Lpp, +forward of 1/2 Lpp) to the
    Holtrop lcb (%LWL, +forward of 1/2 LWL) — the datum convention
    validated against the paper's worked example (see module doc)."""
    offset_m = lcb_pct_lpp / 100.0 * lpp_m + (lwl_m - lpp_m) / 2.0
    return offset_m / lwl_m * 100.0


def holtrop_mennen_power(
    *,
    speed_kn: float,
    lwl_m: float,
    lpp_m: float,
    beam_m: float,
    draft_m: float,
    draft_fp_m: float | None = None,
    displacement_volume_m3: float,
    cm: float,
    cwp: float,
    lcb_pct_lpp: float,
    cp: float | None = None,
    cb_waterline: float | None = None,
    bulb_area_m2: float = 0.0,
    bulb_centre_above_keel_m: float = 0.0,
    transom_area_m2: float = 0.0,
    appendage_area_m2: float = 0.0,
    appendage_factor: float = 1.0,
    c_stern: float = 0.0,
    density_kg_m3: float = SEAWATER_DENSITY,
) -> HoltropPowerResult:
    """Effective power by Holtrop-Mennen (1982), page-verified
    transcription.  Raises SpecValidationError outside the structural
    domain (non-positive geometry, Cp where the printed formulae
    degenerate)."""
    lwl = lwl_m
    t = draft_m
    tf = draft_fp_m if draft_fp_m is not None else t
    nabla = displacement_volume_m3
    v_ms = speed_kn * 1852.0 / 3600.0
    if lwl <= 0 or beam_m <= 0 or t <= 0 or nabla <= 0:
        raise SpecValidationError(
            "holtrop geometry", (lwl, beam_m, t, nabla),
            "all positive",
            "the method needs a positive length, breadth, draught and "
            "displacement volume.")
    if not 0.25 <= cm <= 1.0:
        raise SpecValidationError(
            "cm", cm, "0.25 < CM <= 1.0",
            "the midship coefficient outside this band degenerates the "
            "wetted-area formula (sqrt of a negative or non-physical "
            "section).")
    # Cp/CB are ACCEPTED as declared inputs because the paper computes
    # them on a length between Lpp and LWL (its own example: Cp 0.5833
    # with nabla/(Lpp·B·T) 0.5859 and nabla/(L·B·T) 0.5716); when
    # undeclared they derive on the waterline length and the calibre is
    # stated in the output
    cp_derived = nabla / (lwl * beam_m * t)
    cp = cp_derived if cp is None else float(cp)
    cb = cp_derived if cb_waterline is None else float(cb_waterline)
    if cp <= 0.25:
        raise SpecValidationError(
            "cp", cp, "Cp > 0.25",
            "the L_R formula divides by (4·Cp − 1): at Cp <= 0.25 the "
            "run-length degenerates.")
    if cp >= 0.95:
        raise SpecValidationError(
            "cp", cp, "Cp < 0.95",
            "the form-factor formula divides by (0.95 − Cp)^0.521448.")
    lcb_h = holtrop_lcb_from_taskbook(lcb_pct_lpp, lpp_m, lwl)
    base_term = 1.0 - cp + 0.0225 * lcb_h        # form factor (p. 166)
    i_e_term = 1.0 - cp - 0.0225 * lcb_h         # i_E regression (p. 167)
    if base_term <= 0 or i_e_term <= 0:
        raise SpecValidationError(
            "lcb", lcb_h, "1 − Cp ± 0.0225·lcb > 0 (both signs)",
            "this Cp/lcb combination degenerates the form-factor or "
            "half-angle-of-entrance formulae.")

    # run length, c12, c13, form factor 1+k1 (p. 166)
    lr = lwl * (1.0 - cp + 0.06 * cp * lcb_h / (4.0 * cp - 1.0))
    t_over_l = t / lwl
    if t_over_l > 0.05:
        c12 = t_over_l ** 0.2228446
    elif t_over_l > 0.02:
        c12 = 48.20 * (t_over_l - 0.02) ** 2.078 + 0.479948
    else:
        c12 = 0.479948
    c13 = 1.0 + 0.003 * c_stern
    form_factor = c13 * (0.93 + c12
                         * (beam_m / lr) ** 0.92497
                         * (0.95 - cp) ** -0.521448
                         * base_term ** 0.6906)

    # wetted area (p. 166-167)
    wetted_area = (lwl * (2.0 * t + beam_m) * math.sqrt(cm)
                   * (0.453 + 0.4425 * cb - 0.2862 * cm
                      - 0.003467 * beam_m / t + 0.3696 * cwp)
                   + 2.38 * bulb_area_m2 / cb)

    # friction (ITTC-1957)
    reynolds = v_ms * lwl / KINEMATIC_VISCOSITY
    cf = 0.075 / (math.log10(reynolds) - 2.0) ** 2
    r_friction = 0.5 * density_kg_m3 * v_ms ** 2 * wetted_area * cf

    # appendages (p. 167)
    r_appendage = (0.5 * density_kg_m3 * v_ms ** 2 * appendage_area_m2
                   * appendage_factor * cf)

    # half angle of entrance (p. 167) — the paper's own replacement
    # regression (the [1] original could go negative)
    i_e = 1.0 + 89.0 * math.exp(
        -(lwl / beam_m) ** 0.80856
        * (1.0 - cwp) ** 0.30484
        * i_e_term ** 0.6367
        * (lr / beam_m) ** 0.34574
        * (100.0 * nabla / lwl ** 3) ** 0.16302)

    # bulb coefficients (p. 167-168)
    if bulb_area_m2 > 0:
        c3 = 0.56 * bulb_area_m2 ** 1.5 / (
            beam_m * t * (0.31 * math.sqrt(bulb_area_m2)
                          + tf - bulb_centre_above_keel_m))
    else:
        c3 = 0.0
    c2 = math.exp(-1.89 * math.sqrt(c3))
    c5 = 1.0 - 0.8 * transom_area_m2 / (beam_m * t * cm)

    # wave resistance (p. 167): R_W = c1 c2 c5 nabla rho g
    #                                  * exp{m1 Fn^d + m2 cos(lambda Fn^-2)}
    bl = beam_m / lwl
    if bl < 0.11:
        c7 = 0.229577 * bl ** 0.33333
    elif bl <= 0.25:
        c7 = bl
    else:
        c7 = 0.5 - 0.0625 * lwl / beam_m
    if lwl / beam_m < 12:
        lam = 1.446 * cp - 0.03 * lwl / beam_m
    else:
        lam = 1.446 * cp - 0.36
    if cp < 0.80:
        c16 = 8.07981 * cp - 13.8673 * cp ** 2 + 6.984388 * cp ** 3
    else:
        c16 = 1.73014 - 0.7067 * cp
    m1 = (0.0140407 * lwl / t - 1.75254 * nabla ** (1.0 / 3.0) / lwl
          - 4.79323 * bl - c16)
    disp_length = lwl / nabla ** (1.0 / 3.0)
    if disp_length < 8.0:
        c15 = -1.69385
    elif disp_length <= 12.0:
        c15 = -1.69385 + (disp_length - 8.0) / 2.36
    else:
        c15 = 0.0
    fn = v_ms / math.sqrt(GRAVITY * lwl)
    d_exp = -0.9
    m2 = c15 * cp ** 2 * math.exp(-0.1 * fn ** -2)
    exponent = m1 * fn ** d_exp + m2 * math.cos(lam * fn ** -2)
    c1 = (2223105.0 * c7 ** 3.78613 * (t / beam_m) ** 1.07961
          * (90.0 - i_e) ** -1.37565)
    r_wave = (c1 * c2 * c5 * nabla * density_kg_m3 * GRAVITY
              * math.exp(exponent))

    # bulb near-surface pressure resistance (p. 168) — formula as
    # printed; the paper's example table carries a factor-10 slip on
    # this component (module docstring)
    if bulb_area_m2 > 0:
        p_b = 0.56 * math.sqrt(bulb_area_m2) / (
            tf - 1.5 * bulb_centre_above_keel_m)
        f_ni = v_ms / math.sqrt(
            GRAVITY * (tf - bulb_centre_above_keel_m
                       - 0.25 * math.sqrt(bulb_area_m2))
            + 0.15 * v_ms ** 2)
        r_bulb = (0.11 * math.exp(-3.0 * p_b ** -2) * f_ni ** 3
                  * bulb_area_m2 ** 1.5 * density_kg_m3 * GRAVITY
                  / (1.0 + f_ni ** 2))
    else:
        p_b = 0.0
        f_ni = 0.0
        r_bulb = 0.0

    # immersed transom (p. 168)
    if transom_area_m2 > 0:
        f_nt = v_ms / math.sqrt(
            2.0 * GRAVITY * transom_area_m2 / (beam_m + beam_m * cwp))
        c6 = 0.2 * (1.0 - 0.2 * f_nt) if f_nt < 5 else 0.0
        r_transom = (0.5 * density_kg_m3 * v_ms ** 2 * transom_area_m2
                     * c6)
    else:
        f_nt = 0.0
        r_transom = 0.0

    # model-ship correlation allowance (p. 168)
    c4 = tf / lwl if tf / lwl <= 0.04 else 0.04
    c_a = (0.006 * (lwl + 100.0) ** -0.16 - 0.00205
           + 0.003 * math.sqrt(lwl / 7.5) * cb ** 4 * c2 * (0.04 - c4))
    r_correlation = (0.5 * density_kg_m3 * v_ms ** 2 * wetted_area
                     * c_a)

    # the total sums in NEWTONS (every component above is N); the
    # result converts to kN once, at the dataclass boundary
    r_total_n = (r_friction * form_factor + r_appendage + r_wave
                 + r_bulb + r_transom + r_correlation)
    r_total = r_total_n / 1000.0
    pe = r_total * v_ms

    return HoltropPowerResult(
        speed_kn=speed_kn,
        speed_ms=v_ms,
        froude_number=fn,
        lcb_holtrop_pct=lcb_h,
        length_run_m=lr,
        form_factor=form_factor,
        wetted_area_m2=wetted_area,
        reynolds=reynolds,
        cf=cf,
        r_friction_kn=r_friction / 1000.0,
        r_appendage_kn=r_appendage / 1000.0,
        r_wave_kn=r_wave / 1000.0,
        r_bulb_kn=r_bulb / 1000.0,
        r_transom_kn=r_transom / 1000.0,
        r_correlation_kn=r_correlation / 1000.0,
        r_total_kn=r_total,
        pe_kw=pe,
        coefficients={
            "c1": c1, "c2": c2, "c3": c3, "c5": c5, "c7": c7,
            "c12": c12, "c13": c13, "c15": c15, "c16": c16,
            "lambda": lam, "m1": m1, "m2": m2, "d": d_exp,
            "iE_deg": i_e, "CA": c_a, "c4": c4, "FnT": f_nt,
            "FnI": f_ni, "PB": p_b, "Cp": cp, "CB_waterline": cb,
            "Cp_declared": cp is not None and cp != cp_derived,
            "Cp_derived_lwl": cp_derived,
        },
    )
