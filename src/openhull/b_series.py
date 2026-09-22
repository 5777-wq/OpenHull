# -*- coding: utf-8 -*-
"""Distributed copy of the OpenHull internal transcription (2026-09-22).
Transcribed and page-referenced from the report scan described below;
the internal verification session also overlaid this transcription on
the report's own figure 41 and cross-checked it against the NMRI MP687
measured open-water table and the Ship Theory table 8-12 readings (see
tests/test_b_series.py and VALIDATION.md).
"""
# -*- coding: utf-8 -*-
"""
Wageningen B-series open-water regression (K_T, K_Q, eta_0) — verbatim transcription
of the ORIGINAL published report:

    Bernitsas, M.M., Ray, D., Kinley, P. (1981),
    "K_T, K_Q and Efficiency Curves for the Wageningen B-Series Propellers",
    Department of Naval Architecture and Marine Engineering, College of
    Engineering, The University of Michigan, Ann Arbor, Michigan 48109.
    Report No. 237, May 1981.                     <-- verified from title page

IDENTITY VERIFICATION (R7 provenance)
-------------------------------------
Source PDF : Bernitsas_Ray_Kinley_1981_UM_Report_237.pdf (115-page scan, no text
layer; every number below was read from rendered page images at 150-300 dpi).
Original distribution channel of that scan:
    - Publisher's record: UM Deep Blue, handle 2027.42/91702
      (file Publication_No_237.pdf / 001.pdf) — downloads geo-blocked from this
      location at access time (2026-09-22); the Deep Blue block page itself was
      returned by the server.
    - Bit-identical content obtained via the boatdesign.net forum mirror of the
      same scanned report (8,058,452 bytes):
      https://www.boatdesign.net/attachments/kt-kq-eta-curves-wageningen-b-series-propellers-bernitsas-1981-pdf.79596/

Title-page facts (PDF page 1 of the scan):
    "[Report] No. 237, May 1981"
    Title: "K_T, K_Q and Efficiency Curves for the Wageningen B-Series Propellers"
    by M.M. Bernitsas, D. Ray, P. Kinley
    Department of Naval Architecture and Marine Engineering, College of
    Engineering, The University of Michigan, Ann Arbor, Michigan 48109.
    NOTE: the report number is 237, NOT 282/283 as sometimes miscited.
    (Reports 282/283 are the related 1975/76 B'-Screw Series data/chart reports
    by Krishnappan/Bernitsas; this 1981 report is No. 237.)

PAGE CONVENTION
---------------
"PDF p.N"  = page N of the 115-page scan file (1-based).
"report p.N" = the printed page number on that scanned page.
Mapping used below: report p.1..p.102 = PDF p.13..p.114 (front matter i-xii = PDF 1-12).

CONTENTS OF THIS MODULE
-----------------------
1. Regression form (report p.3 / PDF p.15, eqs. 7-8):
       K_T = sum_{s,t,u,v} C^T_{s,t,u,v} (J)^s (P/D)^t (A_E/A_O)^u (Z)^v
       K_Q = sum_{s,t,u,v} C^Q_{s,t,u,v} (J)^s (P/D)^t (A_E/A_O)^u (Z)^v
   with the coefficient/term values of TABLE 1 (report p.4 / PDF p.16),
   "Coefficients and terms of the K_T and K_Q polynomials for the Wageningen
   B-screw Series for R_n = 2x10^6. Reproduced from [1]" where reference [1] is
       Oosterveld, M.W.C. and P. Van Oossanen, "Further Computer-Analyzed Data
       of the Wageningen B-Screw Series," IV International Symposium on Ship
       Automation, Genova, Italy, Nov. 1974.   (report p.6 / PDF p.18)
   -> 39 K_T terms and 47 K_Q terms (counted on the page).
2. Reynolds-number corrections (report p.5 / PDF p.17, TABLE 2,
   "Polynomials for Reynolds number effect (above R_n = 2x10^6) on K_T and K_Q"),
   eqs. (9)-(10): Delta K_T(Re, J, P/D, A_E/A_O, z), Delta K_Q(...).
   -> 9 Delta-K_T terms and 13 Delta-K_Q terms (incl. constants).
3. Validity ranges (report p.6 / PDF p.18, eqs. 11-13).
4. Variant coverage (report p.iii / PDF p.3 and report p.6 / PDF p.18).
5. Evaluator functions kt(), kq(), eta0() and a B-series designation helper.

Every numeric list entry is a tuple whose last element is the page reference
it was read from. NOTHING in this file is filled in from memory of the
literature; where the report is ambiguous this is stated explicitly (see
UNREADABLE/UNCERTAIN at the bottom of the module docstring).

UNREADABLE / UNCERTAIN ITEMS
----------------------------
* None of the Table 1 / Table 2 digits were unreadable (K_Q block re-verified
  at 600 dpi, K_T block at 300 dpi; every term confirmed twice).
* The report writes "(logRn - 0.301)" in Table 2 without stating the logarithm
  base; 0.301 = log10(2) and the standard Oosterveld & van Oossanen usage imply
  log10, which this module assumes (marked ASSUMPTION).
* The report does not print numeric worked examples; acceptance anchors are the
  plotted curves (96 figures). Pixel-calibrated overlay of THIS transcription
  onto Figure 41 (B4-70, report p.47 / PDF p.59) reproduces (a) the dashed
  K_T curves and (b) the solid K_Q curves (right axis, 0-0.20, scale 6.58
  KT-units) of the printed chart. The solid eta parabolas in the figures are
  fairings and do NOT equal the raw polynomial eta (which has a pole at the
  K_Q zero crossing, J ~= 1.02 for B4-70 at P/D = 1.0, just before the K_T
  zero crossing at J ~= 1.06). USAGE CAUTION: keep J well below the K_Q zero
  crossing; the report itself warns (report p.6 / PDF p.18) that "at the
  extremes of the above ranges the results are not fully reliable".
* TABLE 2 at Rn = 2e6 gives a small non-zero residual (dK_T ~ -7e-5, 0.03% of
  K_T): the empirical fit does not vanish exactly at the baseline; this is a
  property of the published polynomials, not a transcription error.
"""

from math import log10, pi

# ----------------------------------------------------------------------------- 
# Provenance constants
# -----------------------------------------------------------------------------
PDF_FILE = "Bernitsas_Ray_Kinley_1981_UM_Report_237.pdf"
PDF_PAGES_TOTAL = 115

PAGE_TITLE = "PDF p.1"                 # title page: Report No. 237, May 1981
PAGE_ABSTRACT = "PDF p.3 (report p.iii)"
PAGE_TOC = "PDF p.7 (report p.vii)"
PAGE_REGRESSION_FORM = "PDF p.15 (report p.3)"     # eqs. (7)-(10)
PAGE_TABLE1 = "PDF p.16 (report p.4)"             # TABLE 1: K_T, K_Q coefficients
PAGE_TABLE2 = "PDF p.17 (report p.5)"             # TABLE 2: Rn corrections
PAGE_LIMITS = "PDF p.18 (report p.6)"             # eqs. (11)-(13) + REFERENCES
PAGE_LOF = "PDF p.9-11 (report p.ix-xi)"          # list of figures
PAGE_FIG_B470 = "PDF p.59 (report p.47)"          # Figure 41 = B4-70 chart

# -----------------------------------------------------------------------------
# TABLE 1 — base polynomials, valid as printed for Rn = 2x10^6
# (report p.4 / PDF p.16). Each entry: (coefficient, (s, t, u, v), page)
# where the term is coefficient * J^s * (P/D)^t * (A_E/A_O)^u * Z^v.
# Transcribed row-by-row from the printed table (left block = K_T,
# right block = K_Q; each block carries its own s,t,u,v columns).
# -----------------------------------------------------------------------------
KT_COEFFICIENTS = [
    (+0.00880496,  (0, 0, 0, 0), PAGE_TABLE1),
    (-0.204554,    (1, 0, 0, 0), PAGE_TABLE1),
    (+0.166351,    (0, 1, 0, 0), PAGE_TABLE1),
    (+0.158114,    (0, 2, 0, 0), PAGE_TABLE1),
    (-0.147581,    (2, 0, 1, 0), PAGE_TABLE1),
    (-0.481497,    (1, 1, 1, 0), PAGE_TABLE1),
    (+0.415437,    (0, 2, 1, 0), PAGE_TABLE1),
    (+0.0144043,   (0, 0, 0, 1), PAGE_TABLE1),
    (-0.0530054,   (2, 0, 0, 1), PAGE_TABLE1),
    (+0.0143481,   (0, 1, 0, 1), PAGE_TABLE1),
    (+0.0606826,   (1, 1, 0, 1), PAGE_TABLE1),
    (-0.0125894,   (0, 0, 1, 1), PAGE_TABLE1),
    (+0.0109689,   (1, 0, 1, 1), PAGE_TABLE1),
    (-0.133698,    (0, 3, 0, 0), PAGE_TABLE1),
    (+0.00638407,  (0, 6, 0, 0), PAGE_TABLE1),
    (-0.00132718,  (2, 6, 0, 0), PAGE_TABLE1),
    (+0.168496,    (3, 0, 1, 0), PAGE_TABLE1),
    (-0.0507214,   (0, 0, 2, 0), PAGE_TABLE1),
    (+0.0854559,   (2, 0, 2, 0), PAGE_TABLE1),
    (-0.0504475,   (3, 0, 2, 0), PAGE_TABLE1),
    (+0.010465,    (1, 6, 2, 0), PAGE_TABLE1),
    (-0.00648272,  (2, 6, 2, 0), PAGE_TABLE1),
    (-0.00841728,  (0, 3, 0, 1), PAGE_TABLE1),
    (+0.0168424,   (1, 3, 0, 1), PAGE_TABLE1),
    (-0.00102296,  (3, 3, 0, 1), PAGE_TABLE1),
    (-0.0317791,   (0, 3, 1, 1), PAGE_TABLE1),
    (+0.018604,    (1, 0, 2, 1), PAGE_TABLE1),
    (-0.00410798,  (0, 2, 2, 1), PAGE_TABLE1),
    (-0.000606848, (0, 0, 0, 2), PAGE_TABLE1),
    (-0.0049819,   (1, 0, 0, 2), PAGE_TABLE1),
    (+0.0025983,   (2, 0, 0, 2), PAGE_TABLE1),
    (-0.000560528, (3, 0, 0, 2), PAGE_TABLE1),
    (-0.0016352,   (1, 2, 0, 2), PAGE_TABLE1),
    (-0.000328787, (1, 6, 0, 2), PAGE_TABLE1),
    (+0.000116502, (2, 6, 0, 2), PAGE_TABLE1),
    (+0.000690904, (0, 0, 1, 2), PAGE_TABLE1),
    (+0.00421749,  (0, 3, 1, 2), PAGE_TABLE1),
    (+0.0000565229,(3, 6, 1, 2), PAGE_TABLE1),
    (-0.00146564,  (0, 3, 2, 2), PAGE_TABLE1),
]  # 39 terms (counted on page)

KQ_COEFFICIENTS = [
    (+0.00379368,   (0, 0, 0, 0), PAGE_TABLE1),
    (+0.00886523,   (2, 0, 0, 0), PAGE_TABLE1),
    (-0.032241,     (1, 1, 0, 0), PAGE_TABLE1),
    (+0.00344778,   (0, 2, 0, 0), PAGE_TABLE1),
    (-0.0408811,    (0, 1, 1, 0), PAGE_TABLE1),
    (-0.108009,     (1, 1, 1, 0), PAGE_TABLE1),
    (-0.0885381,    (2, 1, 1, 0), PAGE_TABLE1),
    (+0.188561,     (0, 2, 1, 0), PAGE_TABLE1),
    (-0.00370871,   (1, 0, 0, 1), PAGE_TABLE1),
    (+0.00513696,   (0, 1, 0, 1), PAGE_TABLE1),
    (+0.0209449,    (1, 1, 0, 1), PAGE_TABLE1),
    (+0.00474319,   (2, 1, 0, 1), PAGE_TABLE1),
    (-0.00723408,   (2, 0, 1, 1), PAGE_TABLE1),
    (+0.00438388,   (1, 1, 1, 1), PAGE_TABLE1),
    (-0.0269403,    (0, 2, 1, 1), PAGE_TABLE1),
    (+0.0558082,    (3, 0, 1, 0), PAGE_TABLE1),
    (+0.0161886,    (0, 3, 1, 0), PAGE_TABLE1),
    (+0.00318086,   (1, 3, 1, 0), PAGE_TABLE1),
    (+0.015896,     (0, 0, 2, 0), PAGE_TABLE1),
    (+0.0471729,    (1, 0, 2, 0), PAGE_TABLE1),
    (+0.0196283,    (3, 0, 2, 0), PAGE_TABLE1),
    (-0.0502782,    (0, 1, 2, 0), PAGE_TABLE1),
    (-0.030055,     (3, 1, 2, 0), PAGE_TABLE1),
    (+0.0417122,    (2, 2, 2, 0), PAGE_TABLE1),
    (-0.0397722,    (0, 3, 2, 0), PAGE_TABLE1),
    (-0.00350024,   (0, 6, 2, 0), PAGE_TABLE1),
    (-0.0106854,    (3, 0, 0, 1), PAGE_TABLE1),
    (+0.00110903,   (3, 3, 0, 1), PAGE_TABLE1),
    (-0.000313912,  (0, 6, 0, 1), PAGE_TABLE1),
    (+0.0035985,    (3, 0, 1, 1), PAGE_TABLE1),
    (-0.00142121,   (0, 6, 1, 1), PAGE_TABLE1),
    (-0.00383637,   (1, 0, 2, 1), PAGE_TABLE1),
    (+0.0126803,    (0, 2, 2, 1), PAGE_TABLE1),
    (-0.00318278,   (2, 3, 2, 1), PAGE_TABLE1),
    (+0.00334268,   (0, 6, 2, 1), PAGE_TABLE1),
    (-0.00183491,   (1, 1, 0, 2), PAGE_TABLE1),
    (-0.000112451,  (3, 2, 0, 2), PAGE_TABLE1),
    (-0.000297228,  (3, 6, 0, 2), PAGE_TABLE1),
    (+0.000269551,  (1, 0, 1, 2), PAGE_TABLE1),
    (+0.00083265,   (2, 0, 1, 2), PAGE_TABLE1),
    (+0.00155334,   (0, 2, 1, 2), PAGE_TABLE1),
    (+0.000302683,  (0, 6, 1, 2), PAGE_TABLE1),
    (-0.0001843,    (0, 0, 2, 2), PAGE_TABLE1),
    (-0.000425399,  (0, 3, 2, 2), PAGE_TABLE1),
    (+0.0000869243, (3, 3, 2, 2), PAGE_TABLE1),
    (-0.0004659,    (0, 6, 2, 2), PAGE_TABLE1),
    (+0.0000554194, (1, 6, 2, 2), PAGE_TABLE1),
]  # 47 terms (counted on page)

# -----------------------------------------------------------------------------
# TABLE 2 — Reynolds number corrections for Rn above 2x10^6
# (report p.5 / PDF p.17). The printed terms are monomials in
# J, P/D, A_E/A_O, z and L = (logRn - 0.301), with L squared written explicitly.
# Each entry: (coefficient, (eJ, ePD, eAER, eZ, eL), page)
# meaning coefficient * J^eJ * (P/D)^ePD * (A_E/A_O)^eAER * z^eZ * L^eL.
# ASSUMPTION: logRn = log10(Rn) (base not stated in report; 0.301 = log10 2).
# -----------------------------------------------------------------------------
DELTA_KT_COEFFICIENTS = [
    (+0.000353485,  (0, 0, 0, 0, 0), PAGE_TABLE2),  # constant
    (-0.00333758,   (2, 0, 1, 0, 0), PAGE_TABLE2),  # (A_E/A_O) J^2
    (-0.00478125,   (1, 1, 1, 0, 0), PAGE_TABLE2),  # (A_E/A_O)(P/D) J
    (+0.000257792,  (2, 0, 1, 0, 2), PAGE_TABLE2),  # L^2 (A_E/A_O) J^2
    (+0.0000643192, (2, 6, 0, 0, 1), PAGE_TABLE2),  # L (P/D)^6 J^2
    (-0.0000110636, (2, 6, 0, 0, 2), PAGE_TABLE2),  # L^2 (P/D)^6 J^2
    (-0.0000276305, (2, 0, 1, 1, 2), PAGE_TABLE2),  # L^2 z (A_E/A_O) J^2
    (+0.0000954,    (1, 1, 1, 1, 1), PAGE_TABLE2),  # L z (A_E/A_O)(P/D) J
    (+0.0000032049, (1, 3, 1, 2, 1), PAGE_TABLE2),  # L z^2 (A_E/A_O)(P/D)^3 J
]  # 9 terms (counted on page)

DELTA_KQ_COEFFICIENTS = [
    (-0.000591412,    (0, 0, 0, 0, 0), PAGE_TABLE2),  # constant
    (+0.00696898,     (0, 1, 0, 0, 0), PAGE_TABLE2),  # (P/D)
    (-0.0000666654,   (0, 6, 0, 1, 0), PAGE_TABLE2),  # z (P/D)^6
    (+0.0160818,      (0, 0, 2, 0, 0), PAGE_TABLE2),  # (A_E/A_O)^2
    (-0.000938091,    (0, 1, 0, 0, 1), PAGE_TABLE2),  # L (P/D)
    (-0.00059593,     (0, 2, 0, 0, 1), PAGE_TABLE2),  # L (P/D)^2
    (+0.0000782099,   (0, 2, 0, 0, 2), PAGE_TABLE2),  # L^2 (P/D)^2
    (+0.0000052199,   (2, 0, 1, 1, 1), PAGE_TABLE2),  # L z (A_E/A_O) J^2
    (-0.00000088528,  (1, 1, 1, 1, 2), PAGE_TABLE2),  # L^2 z (A_E/A_O)(P/D) J
    (+0.0000230171,   (0, 6, 0, 1, 1), PAGE_TABLE2),  # L z (P/D)^6
    (-0.00000184341,  (0, 6, 0, 1, 2), PAGE_TABLE2),  # L^2 z (P/D)^6
    (-0.00400252,     (0, 0, 2, 0, 1), PAGE_TABLE2),  # L (A_E/A_O)^2
    (+0.000220915,    (0, 0, 2, 0, 2), PAGE_TABLE2),  # L^2 (A_E/A_O)^2
]  # 13 terms (counted on page)

# -----------------------------------------------------------------------------
# Validity ranges of the regression polynomials
# (report p.6 / PDF p.18, eqs. (11)-(13), transcribed verbatim):
#     2 <= Z <= 7
#     0.30 <= A_E/A_O <= 1.05
#     0.5 <= P/D <= 1.40
# The report adds (same page): "at the extremes of the above ranges the results
# are not fully reliable" (K_T shows a spurious local maximum for low J, high
# Z, low A_E/A_O, high P/D). Rn corrections apply for Rn > 2x10^6
# (report p.3 / PDF p.15); Table 1 values are for Rn = 2x10^6.
# -----------------------------------------------------------------------------
VALID_RANGES = {
    "Z":      (2, 7,      PAGE_LIMITS),
    "AER":    (0.30, 1.05, PAGE_LIMITS),
    "PD":     (0.5, 1.40,  PAGE_LIMITS),
    "Rn_base": 2.0e6,       # Table 1 baseline, report p.4 / PDF p.16
    "Rn_corr_above": 2.0e6, # corrections for Rn above this, report p.3 / PDF p.15
}

# -----------------------------------------------------------------------------
# Variant coverage actually plotted in the report
# (report p.iii / PDF p.3: 120 B-series models tested at NSMB and regressed in
#  [1]; report p.6 / PDF p.18: "96 open-water propeller characteristics curves
#  are included in this report. For each set of blades between 2 and 7, sixteen
#  graphs have been plotted for blade area ratio varying between 0.30 and 1.05
#  in steps of 0.05 and pitch diameter ratio varying between 0.50 and 1.40 in
#  steps of 0.10." plotted at Rn = 2x10^6.)
# The report identifies variants as "Propeller with N blades and A_E/A_O = x.xx"
# (list of figures, report p.ix-xi / PDF p.9-11); the usual "BZ-YY" shorthand
# (e.g. B4-70) corresponds to (Z=4, A_E/A_O=0.70) = Figure 41.
# -----------------------------------------------------------------------------
COVERAGE = {
    "Z_values": [2, 3, 4, 5, 6, 7],                      # report p.6 / PDF p.18
    "AER_values": [round(0.30 + 0.05 * i, 2) for i in range(16)],  # 0.30..1.05
    "PD_curves_per_figure": [round(0.50 + 0.10 * i, 2) for i in range(10)],  # 0.50..1.40
    "figures_total": 96,                                  # report p.6 / PDF p.18
    "plot_Rn": 2.0e6,                                     # abstract, PDF p.3
    "figure_numbering": "Figure no. = 16*(Z-2) + index(AER) + 1, "
                        "first figure on report p.7 (PDF p.19)",
    "page": "report p.iii/PDF p.3 + report p.6/PDF p.18 + list of figures PDF p.9-11",
}

FIGURE_ANCHORS = {
    "B4-70": {"figure": 41, "report_page": 47, "pdf_page": 59,
              "caption": "FIGURE 41. WAGENINGEN B-SERIES PROPELLERS FOR 4 BLADES "
                         "AE/AO= 0.700 P/D=0.50 TO 1.40 (KT, KQ, EFFICIENCY vs J)"},
    "B5-75": {"figure": 58, "report_page": 64, "pdf_page": 76,
              "caption": "FIGURE 58. ... FOR 5 BLADES AE/AO= 0.750 ..."},
}


# -----------------------------------------------------------------------------
# Evaluators
# -----------------------------------------------------------------------------
def _poly_base(coeffs, J, PD, AER, Z):
    return sum(c * (J ** s) * (PD ** t) * (AER ** u) * (Z ** v)
               for c, (s, t, u, v), _ in coeffs)


def _poly_delta(coeffs, J, PD, AER, Z, Rn):
    L = log10(Rn) - 0.301  # ASSUMPTION: log10; see module docstring
    return sum(c * (J ** j) * (PD ** t) * (AER ** u) * (Z ** z) * (L ** l)
               for c, (j, t, u, z, l), _ in coeffs)


def kt_base(J, PD, AER, Z):
    """K_T from TABLE 1 (Rn = 2e6 baseline). report p.4 / PDF p.16."""
    return _poly_base(KT_COEFFICIENTS, J, PD, AER, Z)


def kq_base(J, PD, AER, Z):
    """K_Q from TABLE 1 (Rn = 2e6 baseline). report p.4 / PDF p.16."""
    return _poly_base(KQ_COEFFICIENTS, J, PD, AER, Z)


def kt(J, PD, AER, Z, Rn=None):
    """K_T; if Rn given and > 2e6, adds the TABLE 2 correction (report p.3/p.5)."""
    val = kt_base(J, PD, AER, Z)
    if Rn is not None and Rn > VALID_RANGES["Rn_corr_above"]:
        val += _poly_delta(DELTA_KT_COEFFICIENTS, J, PD, AER, Z, Rn)
    return val


def kq(J, PD, AER, Z, Rn=None):
    """K_Q; if Rn given and > 2e6, adds the TABLE 2 correction (report p.3/p.5)."""
    val = kq_base(J, PD, AER, Z)
    if Rn is not None and Rn > VALID_RANGES["Rn_corr_above"]:
        val += _poly_delta(DELTA_KQ_COEFFICIENTS, J, PD, AER, Z, Rn)
    return val


def eta0(J, PD, AER, Z, Rn=None):
    """Open-water efficiency, eq. (4): eta_0 = J K_T / (2 pi K_Q). PDF p.13."""
    kqv = kq(J, PD, AER, Z, Rn)
    if kqv == 0.0:
        return float("nan")
    return J * kt(J, PD, AER, Z, Rn) / (2.0 * pi * kqv)


def b_series_variant(z, aer_index=None, aer=None):
    """(Z, A_E/A_O) pair from the report's plotted grid (COVERAGE)."""
    if aer is None:
        aer = COVERAGE["AER_values"][aer_index]
    return z, aer


if __name__ == "__main__":
    # Minimal self-demonstration; see selfcheck_bernitsas.py for the full check.
    print("Bernitsas/Ray/Kinley UM Report No. 237 (May 1981) transcription.")
    print("K_T terms:", len(KT_COEFFICIENTS), " K_Q terms:", len(KQ_COEFFICIENTS))
    print("dK_T terms:", len(DELTA_KT_COEFFICIENTS),
          " dK_Q terms:", len(DELTA_KQ_COEFFICIENTS))
    print("B4-70 @ J=0.5, P/D=1.0, Rn=2e6:",
          "KT=%.4f KQ=%.4f eta0=%.3f" % (
              kt(0.5, 1.0, 0.70, 4), kq(0.5, 1.0, 0.70, 4),
              eta0(0.5, 1.0, 0.70, 4)))
