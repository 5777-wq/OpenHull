"""Resistance estimation in the preliminary-design stage (plan task 3.1).

Selectable algorithms behind a registry (AGENTS.md section 8).  v1
ships the Ayre method (as transcribed in Ship Theory vol. 1, section
7-1, pages 291-296 — formulas, tables 7-5/7-6/7-7a/b and the worked
example of table 7-8), which estimates the effective power of a
standard single-screw merchant form and corrects the C0 chart
coefficient for the design ship's block coefficient, B/T, LCB
position and waterline length.

Units trap, pinned by the worked example (table 7-8): the
speed-length ratio V/sqrt(L) uses KNOTS over the SQUARE ROOT OF FEET
(14 kn on Lbp 122 m -> 0.70), while L/Delta^(1/3) is SI
(122/11970^(1/3) = 5.33) and Fr is SI.

C0 chart (figure 7-3): digitised from the scanned original into
_C0_CURVES — the mid-family curves L/Delta^(1/3) = 4.88..6.41 at
V/sqrt(L) stations 0.50..1.30, cross-checked against the worked
example whose chain inverts to C0(5.33, 0.70) = 449.5 and
C0(5.33, 0.75) = 424.2 (the digitised table interpolates to
448.5 and 423.3).  Chart-reading tolerance is about +-4 C0 units;
outside the digitised band the module refuses rather than
extrapolate (AGENTS.md section 6) — the remaining curves of the
chart are future data-entry work.

Holtrop & Mennen (whitelisted for JBC-band work) is a registered
placeholder until its source paper arrives.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from .spec import SpecValidationError, knots_to_ms, within_band

__all__ = [
    "resistance_algorithms",
    "ayre_effective_power",
    "AyreResult",
    "AyreCorrection",
    "RESISTANCE_ALGORITHMS",
    "ResistanceAlgorithmInfo",
    "AYRE_V_SQRT_L_MIN",
    "AYRE_V_SQRT_L_MAX",
    "FT_PER_M",
]

FT_PER_M = 1.0 / 0.3048
G_ACCEL = 9.81

#: speed-length-ratio band with all sources in range: table 7-5 spans
#: 0.50-1.30 but the LCB correction tables 7-7a/b stop at 1.20
AYRE_V_SQRT_L_MIN = 0.50
AYRE_V_SQRT_L_MAX = 1.20


@dataclass(frozen=True)
class ResistanceAlgorithmInfo:
    """Registry entry for one resistance estimation algorithm."""

    algorithm_id: str
    citation: str
    applicability: str
    implemented: bool


RESISTANCE_ALGORITHMS: dict[str, ResistanceAlgorithmInfo] = {
    "ayre": ResistanceAlgorithmInfo(
        algorithm_id="ayre",
        citation=(
            "Ayre method as transcribed in Ship Theory vol. 1 "
            "(Sheng Zhenbang & Liu Yingzhong, 2nd ed.), section 7-1, "
            "pp. 291-296: Eqs. (7-21)-(7-27), tables 7-5/7-6/7-7a/7-7b, "
            "figure 7-3 and the worked example of table 7-8"
        ),
        applicability=(
            "single/twin-screw merchant ships of moderate speed, "
            "V/sqrt(L) 0.50-1.20 (knots/sqrt-ft), "
            "L/Delta^(1/3) 4.88-6.41 (digitised band v1); includes "
            "about 8 % appendage and air resistance in the result"
        ),
        implemented=True,
    ),
    "holtrop_mennen": ResistanceAlgorithmInfo(
        algorithm_id="holtrop_mennen",
        citation=(
            "Holtrop, J. & Mennen, G.G.J. (1982), 'An Approximate "
            "Power Prediction Method', International Shipbuilding "
            "Progress vol. 29 - whitelisted; awaiting the source paper"
        ),
        applicability="general merchant ships up to Fr 0.55",
        implemented=False,
    ),
}


def resistance_algorithms() -> tuple[str, ...]:
    """Registered algorithm ids (implemented ones last for display)."""
    ids = [k for k, v in RESISTANCE_ALGORITHMS.items() if not v.implemented]
    ids += [k for k, v in RESISTANCE_ALGORITHMS.items() if v.implemented]
    return tuple(ids)


# ---------------------------------------------------------------------------
# table 7-5: standard block coefficient and standard LCB (single screw;
# twin-screw Cbc = value + 0.01).  Columns: V/sqrt(L), Fr, Cbc, xc %L
# forward(+)/aft(-) of midship.  The printed table turns the standard
# LCB aft of midship above V/sqrt(L) ~ 0.82 (magnitude 0.12 forward at
# 0.82, then growing aft values) — stored signed.
# ---------------------------------------------------------------------------
_TABLE_7_5 = (
    (0.50, 0.148, 0.83, 2.00), (0.52, 0.154, 0.82, 1.96),
    (0.54, 0.160, 0.81, 1.93), (0.56, 0.166, 0.80, 1.90),
    (0.58, 0.172, 0.79, 1.85), (0.60, 0.178, 0.78, 1.80),
    (0.62, 0.184, 0.77, 1.73), (0.64, 0.190, 0.76, 1.65),
    (0.66, 0.196, 0.75, 1.55), (0.68, 0.202, 0.74, 1.44),
    (0.70, 0.208, 0.73, 1.31), (0.72, 0.214, 0.72, 1.16),
    (0.74, 0.220, 0.71, 0.99), (0.76, 0.226, 0.70, 0.80),
    (0.78, 0.232, 0.69, 0.55), (0.80, 0.238, 0.68, 0.20),
    (0.82, 0.244, 0.67, 0.12), (0.84, 0.250, 0.66, -0.45),
    (0.86, 0.256, 0.65, -0.75), (0.88, 0.261, 0.64, -1.00),
    (0.90, 0.267, 0.63, -1.20), (0.92, 0.273, 0.62, -1.40),
    (0.94, 0.279, 0.61, -1.58), (0.96, 0.285, 0.60, -1.74),
    (0.98, 0.291, 0.59, -1.88), (1.00, 0.297, 0.58, -1.99),
    (1.02, 0.303, 0.573, -2.09), (1.04, 0.309, 0.568, -2.18),
    (1.06, 0.315, 0.564, -2.25), (1.08, 0.321, 0.560, -2.32),
    (1.10, 0.327, 0.557, -2.37), (1.12, 0.333, 0.554, -2.41),
    (1.14, 0.339, 0.552, -2.44), (1.16, 0.345, 0.549, -2.47),
    (1.18, 0.351, 0.547, -2.49), (1.20, 0.357, 0.545, -2.50),
)

# ---------------------------------------------------------------------------
# table 7-6: Kbc, the per-cent C0 INCREASE when the ship is thinner
# than the standard form; entry 100*(Cbc - Cb)/Cbc
# ---------------------------------------------------------------------------
_TABLE_7_6 = (
    (0.2, 0.08), (0.4, 0.16), (0.6, 0.24), (0.8, 0.32), (1.0, 0.40),
    (1.2, 0.50), (1.4, 0.60), (1.6, 0.70), (1.8, 0.80), (2.0, 0.90),
    (2.2, 1.00), (2.4, 1.10), (2.6, 1.20), (2.8, 1.30), (3.0, 1.40),
    (3.2, 1.52), (3.4, 1.64), (3.6, 1.76), (3.8, 1.88), (4.0, 2.00),
    (4.2, 2.12), (4.4, 2.24), (4.6, 2.36), (4.8, 2.48), (5.0, 2.60),
    (5.2, 2.74), (5.4, 2.88), (5.6, 3.04), (5.8, 3.20), (6.0, 3.36),
    (6.2, 3.52), (6.4, 3.68), (6.6, 3.84), (6.8, 4.00), (7.0, 4.16),
    (7.2, 4.33), (7.4, 4.51), (7.6, 4.69), (7.8, 4.87), (8.0, 5.05),
    (8.2, 5.23), (8.4, 5.41), (8.6, 5.59), (8.8, 5.77), (9.0, 5.95),
    (9.2, 6.13), (9.4, 6.31), (9.6, 6.49), (9.8, 6.67), (10.0, 6.85),
    (10.2, 7.03), (10.4, 7.21), (10.6, 7.40), (10.8, 7.60), (11.0, 7.80),
    (11.2, 8.00), (11.4, 8.20), (11.6, 8.38), (11.8, 8.54), (12.0, 8.70),
    (12.2, 8.88), (12.4, 9.06), (12.6, 9.23), (12.8, 9.39), (13.0, 9.55),
    (13.2, 9.71), (13.4, 9.87), (13.6, 10.02), (13.8, 10.16),
    (14.0, 10.30), (15.0, 11.00), (16.0, 11.60), (17.0, 12.05),
    (18.0, 12.35), (19.0, 12.60), (20.0, 12.80), (21.0, 12.90),
    (22.0, 13.00),
)

# ---------------------------------------------------------------------------
# tables 7-7(a)/(b): Kxc, the per-cent C2 DECREASE when the actual LCB
# sits forward of / behind the standard position; rows V/sqrt(L)
# 0.40-1.20, columns the distance from the standard position in %L
# (0.2-2.0).  OCR transcribed.
# ---------------------------------------------------------------------------
_KXC_COLUMNS = (0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0)
_TABLE_7_7A = {
    0.40: (0.4, 0.8, 1.2, 1.6, 2.0, 2.6, 3.2, 3.8, 4.4, 5.0),
    0.42: (0.3, 0.7, 1.0, 1.4, 1.8, 2.4, 3.0, 3.6, 4.2, 4.8),
    0.44: (0.2, 0.6, 0.9, 1.2, 1.6, 2.2, 2.8, 3.4, 4.0, 4.6),
    0.46: (0.2, 0.5, 0.8, 1.0, 1.4, 2.0, 2.6, 3.2, 3.8, 4.4),
    0.48: (0.2, 0.4, 0.7, 0.9, 1.2, 1.8, 2.4, 3.0, 3.6, 4.2),
    0.50: (0.2, 0.4, 0.6, 0.8, 1.0, 1.6, 2.2, 2.8, 3.4, 4.0),
    0.52: (0.2, 0.4, 0.6, 0.8, 1.0, 1.6, 2.2, 2.8, 3.4, 4.0),
    0.54: (0.2, 0.4, 0.6, 0.8, 1.0, 1.6, 2.2, 2.8, 3.4, 4.0),
    0.56: (0.2, 0.4, 0.6, 0.8, 1.0, 1.6, 2.2, 2.8, 3.4, 4.0),
    0.58: (0.2, 0.4, 0.6, 0.8, 1.0, 1.6, 2.2, 2.8, 3.4, 4.0),
    0.60: (0.2, 0.4, 0.6, 0.8, 1.0, 1.0, 2.2, 2.8, 3.4, 4.0),
    0.62: (0.2, 0.5, 0.8, 1.1, 1.4, 2.0, 2.6, 3.2, 3.8, 4.4),
    0.64: (0.3, 0.7, 1.0, 1.4, 1.8, 2.4, 3.0, 3.6, 4.2, 4.8),
    0.66: (0.4, 0.8, 1.3, 1.7, 2.2, 2.8, 3.4, 4.0, 4.6, 5.2),
    0.68: (0.5, 1.0, 1.5, 2.0, 2.6, 3.2, 3.8, 4.4, 5.0, 5.6),
    0.70: (0.6, 1.2, 1.8, 2.4, 3.0, 3.6, 4.2, 4.8, 5.4, 6.0),
    0.72: (0.6, 1.3, 2.0, 2.7, 3.4, 4.1, 4.7, 5.4, 6.1, 6.8),
    0.74: (0.7, 1.5, 2.2, 3.0, 3.8, 4.5, 5.3, 6.0, 6.8, 7.6),
    0.76: (0.8, 1.6, 2.5, 3.3, 4.2, 5.0, 5.8, 6.7, 7.5, 8.4),
    0.78: (0.8, 1.8, 2.7, 3.6, 4.6, 5.5, 6.4, 7.3, 8.2, 9.2),
    0.80: (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0),
    0.82: (1.0, 2.1, 3.2, 4.3, 5.4, 6.5, 7.6, 8.6, 9.7, 10.8),
    0.84: (1.1, 2.3, 3.4, 4.6, 5.8, 7.0, 8.1, 9.2, 10.4, 11.6),
    0.86: (1.2, 2.4, 3.7, 4.9, 6.2, 7.5, 8.7, 9.9, 11.1, 12.4),
    0.88: (1.2, 2.6, 3.9, 5.2, 6.6, 8.0, 9.2, 10.5, 11.8, 13.2),
    0.90: (1.4, 2.8, 4.2, 5.6, 7.0, 8.4, 9.8, 11.2, 12.6, 14.0),
    0.92: (1.4, 2.9, 4.4, 5.9, 7.4, 8.9, 10.4, 11.8, 13.3, 14.8),
    0.94: (1.5, 3.1, 4.6, 6.2, 7.8, 9.3, 10.9, 12.4, 14.0, 15.6),
    0.96: (1.6, 3.2, 4.9, 6.5, 8.2, 9.8, 11.5, 13.1, 14.7, 16.4),
    0.98: (1.6, 3.4, 5.1, 6.8, 8.6, 10.3, 12.0, 13.7, 15.4, 17.2),
    1.00: (1.8, 3.6, 5.4, 7.2, 9.0, 10.8, 12.6, 14.4, 16.2, 18.0),
    1.02: (1.8, 3.7, 5.6, 7.5, 9.4, 11.3, 13.2, 15.0, 16.9, 18.8),
    1.04: (1.9, 3.9, 5.8, 7.8, 9.8, 11.8, 13.7, 15.6, 17.6, 19.6),
    1.06: (2.0, 4.0, 6.1, 8.1, 10.2, 12.3, 14.3, 16.3, 18.3, 20.4),
    1.08: (2.1, 4.2, 6.3, 8.4, 10.6, 12.7, 14.8, 16.9, 19.1, 21.2),
    1.10: (2.2, 4.4, 6.6, 8.8, 11.0, 13.2, 15.4, 17.6, 19.8, 22.0),
    1.15: (2.4, 4.8, 7.2, 9.6, 12.0, 14.4, 16.8, 19.2, 21.6, 24.0),
    1.20: (2.6, 5.2, 7.8, 10.4, 13.0, 15.6, 18.2, 20.8, 23.4, 26.0),
}
_TABLE_7_7B = {
    0.40: (1.0, 2.0, 3.0, 4.0, 5.0, 6.4, 7.8, 9.2, 10.6, 12.0),
    0.42: (1.9, 1.9, 2.8, 3.8, 4.8, 6.1, 7.5, 8.9, 10.2, 11.6),
    0.44: (0.8, 1.8, 2.7, 3.6, 4.6, 5.8, 7.2, 8.6, 9.8, 11.2),
    0.46: (0.8, 1.7, 2.6, 3.5, 4.4, 5.6, 6.9, 8.3, 9.5, 10.8),
    0.48: (0.8, 1.7, 2.5, 3.4, 4.2, 5.4, 6.6, 8.0, 9.2, 10.4),
    0.50: (0.8, 1.6, 2.4, 3.2, 4.0, 5.2, 6.4, 7.6, 8.8, 10.0),
    0.52: (0.7, 1.5, 2.3, 3.1, 3.8, 4.9, 6.1, 7.2, 8.4, 9.6),
    0.54: (0.6, 1.4, 2.2, 2.9, 3.6, 4.6, 5.8, 6.9, 8.0, 9.2),
    0.56: (0.6, 1.3, 2.0, 2.8, 3.4, 4.4, 5.6, 6.6, 7.6, 8.8),
    0.58: (0.6, 1.2, 1.9, 2.6, 3.2, 4.2, 5.2, 6.3, 7.3, 8.4),
    0.60: (0.6, 1.2, 1.8, 2.4, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0),
    0.62: (0.6, 1.1, 1.7, 2.3, 2.8, 3.7, 4.7, 5.6, 6.6, 7.6),
    0.64: (0.5, 1.1, 1.6, 2.1, 2.6, 3.4, 4.4, 5.3, 6.2, 7.2),
    0.66: (0.5, 1.0, 1.4, 1.9, 2.4, 3.2, 4.1, 5.0, 5.8, 6.8),
    0.68: (0.5, 0.9, 1.3, 1.7, 2.2, 3.0, 3.8, 4.7, 5.5, 6.4),
    0.70: (0.4, 0.8, 1.2, 1.6, 2.0, 2.8, 3.6, 4.4, 5.2, 6.0),
    0.72: (0.4, 0.7, 1.0, 1.4, 1.8, 2.5, 3.2, 4.0, 4.8, 5.6),
    0.74: (0.3, 0.6, 0.9, 1.2, 1.6, 2.3, 2.9, 3.6, 4.4, 5.2),
    0.76: (0.3, 0.5, 0.8, 1.0, 1.4, 2.0, 2.6, 3.3, 4.0, 4.8),
    0.78: (0.2, 0.4, 0.7, 0.9, 1.2, 1.8, 2.4, 3.0, 3.6, 4.4),
    0.80: (0.2, 0.4, 0.6, 0.8, 1.0, 1.6, 2.2, 2.8, 3.4, 4.0),
    0.82: (0.0, 0.2, 0.4, 0.6, 0.8, 1.3, 1.8, 2.4, 3.0, 3.6),
    0.84: (0.0, 0.0, 0.2, 0.4, 0.6, 1.1, 1.6, 2.1, 2.6, 3.2),
    0.86: (0.0, 0.0, 0.0, 0.2, 0.4, 0.8, 1.3, 1.8, 2.3, 2.8),
    0.88: (0.0, 0.0, 0.0, 0.0, 0.2, 0.6, 1.0, 1.4, 1.9, 2.4),
    0.90: (0.0, 0.0, 0.0, 0.0, 0.0, 0.4, 0.8, 1.2, 1.6, 2.0),
    0.92: (0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.6, 1.0, 1.4, 1.6),
    0.94: (0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.5, 0.7, 1.0, 1.2),
    0.96: (0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.4, 0.7, 1.0, 1.2),
    0.98: (0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.6, 0.9, 1.2, 1.6),
    1.00: (0.0, 0.0, 0.0, 0.0, 0.0, 0.4, 0.8, 1.2, 1.6, 2.0),
    1.02: (0.0, 0.0, 0.0, 0.0, 0.2, 0.6, 1.0, 1.5, 1.9, 2.4),
    1.04: (0.0, 0.0, 0.0, 0.2, 0.4, 0.8, 1.3, 1.8, 2.3, 2.8),
    1.06: (0.0, 0.0, 0.2, 0.4, 0.6, 1.1, 1.6, 2.1, 2.6, 3.2),
    1.08: (0.0, 0.2, 0.4, 0.6, 0.8, 1.3, 1.9, 2.4, 3.0, 3.6),
    1.10: (0.2, 0.4, 0.6, 0.8, 1.0, 1.6, 2.2, 2.8, 3.4, 4.0),
    1.15: (0.3, 0.6, 0.9, 1.2, 1.5, 2.2, 2.9, 3.6, 4.3, 5.0),
    1.20: (0.4, 0.8, 1.2, 1.6, 2.0, 2.8, 3.6, 4.4, 5.2, 6.0),
}

# ---------------------------------------------------------------------------
# figure 7-3: C0 of the STANDARD form, digitised from the scanned chart
# (curves L/Delta^(1/3) = 4.88..6.41; stations V/sqrt(L) 0.50-1.30).
# Reading tolerance about +-4 units; validated by the table 7-8 worked
# example (C0(5.33, 0.70) = 449.5, C0(5.33, 0.75) = 424.2 chain-inverted
# from the published Pe; the table interpolates 448.5 / 423.3).
# ---------------------------------------------------------------------------
_C0_STATIONS = (0.50, 0.60, 0.70, 0.75, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30)
_C0_CURVES = {
    4.88: (300, 430, 431, 410, 389, 380, 322, 289, 268, 262),
    5.19: (341, 444, 444.5, 421, 402, 390, 333, 298, 276, 272),
    5.49: (378, 450, 452.5, 425, 413, 400, 343, 308, 283, 281),
    5.80: (410, 456, 458.6, 438.5, 421, 411, 352, 316, 290, 290),
    6.10: (436, 467, 464.5, 447.5, 432, 423, 362, 327, 298, 298),
    6.41: (453.5, 475, 469, 460.9, 449, 438, 376, 337, 304, 308),
}


def _interp_1d(pairs, x):
    """Linear interpolation with end clamping over sorted pairs."""
    if x <= pairs[0][0]:
        return pairs[0][1]
    for (x0, v0), (x1, v1) in zip(pairs, pairs[1:]):
        if x <= x1:
            return v0 + (v1 - v0) * (x - x0) / (x1 - x0)
    return pairs[-1][1]


def _interp_2d(rows: dict, columns, x: float, y: float) -> float:
    """Bilinear interpolation into a printed table (both axes linear)."""
    keys = sorted(rows)
    if x <= keys[0]:
        r0 = r1 = keys[0]
    elif x >= keys[-1]:
        r0 = r1 = keys[-1]
    else:
        r0 = max(k for k in keys if k <= x)
        r1 = min(k for k in keys if k > x)
    lo = _interp_1d(list(zip(columns, rows[r0])), y)
    if r1 == r0:
        return lo
    hi = _interp_1d(list(zip(columns, rows[r1])), y)
    return lo + (hi - lo) * (x - r0) / (r1 - r0)


def _interp_c0(length_ratio: float, speed_ratio: float) -> float:
    """C0 of the standard form from the digitised figure 7-3 family."""
    ratios = sorted(_C0_CURVES)
    if length_ratio <= ratios[0]:
        r0 = r1 = ratios[0]
    elif length_ratio >= ratios[-1]:
        r0 = r1 = ratios[-1]
    else:
        r0 = max(k for k in ratios if k <= length_ratio)
        r1 = min(k for k in ratios if k > length_ratio)
    lo = _interp_1d(list(zip(_C0_STATIONS, _C0_CURVES[r0])), speed_ratio)
    if r1 == r0:
        return lo
    hi = _interp_1d(list(zip(_C0_STATIONS, _C0_CURVES[r1])), speed_ratio)
    return lo + (hi - lo) * (length_ratio - r0) / (r1 - r0)


@dataclass(frozen=True)
class AyreCorrection:
    """One C0 correction step (audit trail of Eqs. 7-22..7-25)."""

    label: str
    percent: float
    delta: float
    c_after: float


@dataclass(frozen=True)
class AyreResult:
    """Effective power by the Ayre method (JSON-serializable).

    Attributes:
        displacement_t / speed_kn: the condition, t / knots.
        lpp_m / beam_m / draft_m / lwl_m: principal dimensions, m.
        cb: block coefficient at the condition.
        xc_pct_fwd: LCB as %L forward of midship (fwd positive).
        screw: 'single' or 'twin'.
        v_sqrt_l: speed-length ratio, knots/sqrt(ft).
        fr: Froude number on Lpp (SI).
        length_ratio: L/Delta^(1/3), SI.
        cbc_std / xc_std_pct: standard form values (table 7-5).
        c0_std: figure 7-3 coefficient of the standard form.
        c4: fully corrected coefficient.
        pe_kw: effective power including ~8 % appendage/air, kW.
        pe_bare_kw: bare-hull effective power (Eq. 7-27), kW.
        corrections: the audit chain C0 -> C4.
    """

    displacement_t: float
    speed_kn: float
    lpp_m: float
    beam_m: float
    draft_m: float
    lwl_m: float
    cb: float
    xc_pct_fwd: float
    screw: str
    v_sqrt_l: float
    fr: float
    length_ratio: float
    cbc_std: float
    xc_std_pct: float
    c0_std: float
    c4: float
    pe_kw: float
    pe_bare_kw: float
    corrections: tuple[AyreCorrection, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["corrections"] = [asdict(c) for c in self.corrections]
        return data


def ayre_effective_power(
    *,
    displacement_t: float,
    speed_kn: float,
    lpp_m: float,
    beam_m: float,
    draft_m: float,
    cb: float,
    xc_pct_fwd: float,
    lwl_m: float | None = None,
    screw: str = "single",
) -> AyreResult:
    """Effective power by the Ayre method (Ship Theory vol. 1, 7-1).

    Args:
        displacement_t: displacement Delta, t (seawater).
        speed_kn: still-water trial speed Vs, knots.
        lpp_m: length between perpendiculars Lbp, m.
        beam_m: moulded beam B, m.
        draft_m: moulded draft T, m.
        cb: block coefficient at the condition.
        xc_pct_fwd: LCB position, %Lpp forward of midship (fwd +),
            compared against the table 7-5 standard position.
        lwl_m: waterline length; defaults to 1.025*Lbp (the standard
            value; the correction delta_4 then vanishes).
        screw: 'single' or 'twin'.

    Returns:
        AyreResult with the full correction audit chain.

    Raises:
        SpecValidationError: inputs out of range or outside the
            digitised applicability band.
    """
    if screw not in ("single", "twin"):
        raise SpecValidationError(
            "screw", screw, "'single' or 'twin'",
            "the standard form and its corrections differ between "
            "single- and twin-screw ships (table 7-5 footnotes).",
        )
    for name, value in (
        ("displacement_t", displacement_t), ("speed_kn", speed_kn),
        ("lpp_m", lpp_m), ("beam_m", beam_m), ("draft_m", draft_m),
    ):
        if not math.isfinite(value) or value <= 0:
            raise SpecValidationError(
                name, value, f"finite {name} > 0",
                "the Ayre estimation works on physical positives.",
            )
    if not math.isfinite(cb) or not 0.0 < cb < 1.0:
        raise SpecValidationError(
            "cb", cb, "0 < Cb < 1",
            "the block coefficient is a volume ratio; Cb = 1 would "
            "mean the ship fills its block (see spec.py).",
        )
    if lwl_m is None:
        lwl_m = 1.025 * lpp_m

    v_sqrt_l = speed_kn / math.sqrt(lpp_m * FT_PER_M)
    fr = knots_to_ms(speed_kn) / math.sqrt(G_ACCEL * lpp_m)
    length_ratio = lpp_m / displacement_t ** (1.0 / 3.0)
    if not within_band(v_sqrt_l, AYRE_V_SQRT_L_MIN, AYRE_V_SQRT_L_MAX):
        raise SpecValidationError(
            "speed", speed_kn,
            f"V/sqrt(L) within {AYRE_V_SQRT_L_MIN}-"
            f"{AYRE_V_SQRT_L_MAX} (knots/sqrt-ft); this speed gives "
            f"{v_sqrt_l:.3f}",
            "the Ayre tables and corrections are tabulated for this "
            "speed-length band only (tables 7-5 and 7-7a/b); outside "
            "it the method refuses rather than extrapolate.",
        )
    if not within_band(length_ratio, 4.88, 6.41):
        raise SpecValidationError(
            "length_ratio", length_ratio,
            "L/Delta^(1/3) within 4.88-6.41 (digitised figure 7-3 "
            "band, v1)",
            "only the mid-family curves of the C0 chart are digitised "
            "so far; outside this band the chart coefficient is not "
            "available and the module refuses to guess.",
        )

    # standard form of section 7-1 and the chart coefficient
    cbc_std = (1.08 if screw == "single" else 1.09) - 1.68 * fr
    xc_std_pct = _interp_1d(
        [(row[0], row[3]) for row in _TABLE_7_5], v_sqrt_l
    )
    c0 = _interp_c0(length_ratio, v_sqrt_l)

    c_after = c0
    corrections: list[AyreCorrection] = []

    # (3)(1) block-coefficient correction (Eq. 7-22 / table 7-6)
    if cb > cbc_std:
        pct = -300.0 * cb * (cb - cbc_std) / cbc_std
    else:
        pct = _interp_1d(_TABLE_7_6, 100.0 * (cbc_std - cb) / cbc_std)
    delta1 = c0 * pct / 100.0
    c_after += delta1
    corrections.append(AyreCorrection("Cb correction", pct, delta1, c_after))

    # (3)(2) B/T correction (Eq. 7-23); the standard B/T is 2.0
    b_over_t = beam_m / draft_m
    pct = -10.0 * cb * (b_over_t - 2.0)
    delta2 = c_after * pct / 100.0
    c_after += delta2
    corrections.append(AyreCorrection("B/T correction", pct, delta2, c_after))

    # (3)(3) LCB correction (Eq. 7-24, tables 7-7a/b): when the
    # block-coefficient correction was negative (fuller ship), that
    # penalty already covers part of the LCB deviation
    xc_gap = abs(xc_pct_fwd - xc_std_pct)
    if xc_gap > 2.0:
        raise SpecValidationError(
            "xc", xc_pct_fwd,
            "within 2 %L of the standard LCB position "
            f"({xc_std_pct:.2f} %L at this speed)",
            "tables 7-7a/b are tabulated to 2 %L of LCB offset; "
            "farther offsets are outside the method.",
        )
    if xc_pct_fwd >= xc_std_pct:
        kxc = _interp_2d(_TABLE_7_7A, _KXC_COLUMNS, v_sqrt_l, xc_gap)
    else:
        kxc = _interp_2d(_TABLE_7_7B, _KXC_COLUMNS, v_sqrt_l, xc_gap)
    delta3_0 = c_after * kxc / 100.0
    delta1 = corrections[0].delta
    if corrections[0].percent > 0:
        delta3 = -delta3_0
    elif delta3_0 <= abs(delta1):
        delta3 = 0.0
    else:
        delta3 = -(delta3_0 - abs(delta1))
    pct = delta3 / c_after * 100.0 if c_after else 0.0
    c_after += delta3
    corrections.append(AyreCorrection("LCB correction", pct, delta3, c_after))

    # (3)(4) waterline-length correction (Eq. 7-25)
    pct = (lwl_m - 1.025 * lpp_m) / (1.025 * lpp_m) * 100.0
    delta4 = c_after * pct / 100.0
    c_after += delta4
    corrections.append(
        AyreCorrection("Lwl correction", pct, delta4, c_after)
    )

    pe = displacement_t**0.64 * speed_kn**3 / c_after * 0.735
    return AyreResult(
        displacement_t=displacement_t,
        speed_kn=speed_kn,
        lpp_m=lpp_m,
        beam_m=beam_m,
        draft_m=draft_m,
        lwl_m=lwl_m,
        cb=cb,
        xc_pct_fwd=xc_pct_fwd,
        screw=screw,
        v_sqrt_l=v_sqrt_l,
        fr=fr,
        length_ratio=length_ratio,
        cbc_std=cbc_std,
        xc_std_pct=xc_std_pct,
        c0_std=c0,
        c4=c_after,
        pe_kw=pe,
        pe_bare_kw=pe / 1.08,
        corrections=tuple(corrections),
    )