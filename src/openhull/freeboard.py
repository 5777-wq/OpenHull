"""Freeboard check against the international load-line rules (plan 1.6).

Computes the minimum summer freeboard of an international-voyage ship
and compares it with the actual freeboard of the design.  The rule
framework (International Convention on Load Lines, 1966, as transcribed
in Lin Yan, Ship Design Principles, 4th ed., section 3.4.2):

    F = F0 + f1 + f2 + f3 + f4 + f5            Eq. (3-15)

with

  * F0 - tabulated basic freeboard of the STANDARD ship (flat deck,
    Cb = 0.68, L/Ds = 15, standard sheer), Table 3-9, ship length
    24-365 m in 10 m steps with linear interpolation for intermediate
    lengths, separate columns for type A and type B ships;
  * f1 - B-type ships shorter than 100 m with effective superstructure
    length E < 0.35 L, Eq. (3-16): 7.5*(100 - L)*(0.35 - E/L);
  * f2 - block-coefficient correction, Eq. (3-17):
    (F0 + f1)*((Cb + 0.68)/1.36 - 1), zero when Cb <= 0.68; Cb is the
    rule's calculation block coefficient at draft 0.85*Ds;
  * f3 - depth correction, Eq. (3-18): (Ds - L/15)*R with
    R = L/0.48 for L < 120 m and R = 250 for L >= 120 m, applied when
    Ds > L/15 (never negative);
  * f4 - superstructure correction, Eq. (3-19): k*f0 with f0 = -350 mm
    at L = 24 m, -860 mm at L = 85 m, -1070 mm at L >= 122 m and the
    percentage k from Table 3-11 as a function of E/L (Table 3-11
    column "B, I - forecastle only" is implemented; A-type on request);
  * f5 - sheer correction, Eq. (3-20): 0.5*(W + U)*(0.75 - S/(2L)),
    zero for the standard sheer (the default: W = U = 0).

All correction formulas and the tabulated values are transcribed from
the book; Table 3-9 was visually verified against the scanned original
(part 1, page 71 of the PDF, book page 60) before implementation -
R7 duty done 2026-09-10.  The domestic-rules variant (Xie Yunping
section 2-9, K-coefficient tables for L = 20-230 m) is deliberately
not implemented yet: it targets coastal/inland ships and its length
range does not reach the benchmark ships.

SCOPE (declared): summer freeboard only; seasonal allowances
(tropical/winter/fresh-water, Eq. 3-22 onwards) are later additions.
B-type reductions for hatchway protection (Regulation 27) and the
"reduced freeboard" B-60/B-100 provisions are not implemented - the
module computes the plain B-type minimum, which is the conservative
side of the verdict.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .spec import SpecValidationError

__all__ = [
    "TABLE_3_9_BASIC_FREEBOARD",
    "tabular_basic_freeboard",
    "minimum_freeboard",
    "FreeboardResult",
]

#: Table 3-9: standard-ship basic freeboard, mm, L -> (type A, type B).
#: Transcribed from Lin Yan section 3.4.2 and visually verified against
#: the scanned original (part 1 PDF page 71, book page 60).
TABLE_3_9_BASIC_FREEBOARD: dict[int, tuple[int, int]] = {
    24: (200, 200), 30: (250, 250), 40: (334, 334), 50: (443, 443),
    60: (573, 573), 70: (706, 721), 80: (841, 887), 90: (984, 1075),
    100: (1135, 1271), 110: (1293, 1479), 120: (1459, 1690),
    130: (1632, 1901), 140: (1803, 2109), 150: (1968, 2315),
    160: (2126, 2520), 170: (2268, 2716), 180: (2393, 2915),
    190: (2508, 3098), 200: (2612, 3264), 210: (2705, 3430),
    220: (2792, 3586), 230: (2872, 3735), 240: (2946, 3880),
    250: (3012, 4018), 260: (3072, 4152), 270: (3128, 4276),
    280: (3176, 4397), 290: (3220, 4513), 300: (3262, 4630),
    310: (3298, 4736), 320: (3331, 4844), 330: (3358, 4955),
    340: (3382, 5055), 350: (3406, 5160), 360: (3425, 5260),
    365: (3433, 5303),
}

#: Table 3-11, type B column I (forecastle only): E/L -> k in percent.
_K_TABLE_B_I = (
    (0.0, 0.0), (0.1, 5.0), (0.2, 10.0), (0.3, 15.0), (0.4, 23.5),
    (0.5, 32.0), (0.6, 46.0), (0.7, 63.0), (0.8, 75.3), (0.9, 87.8),
    (1.0, 100.0),
)

#: Table 3-11, type A: E/L -> k in percent.
_K_TABLE_A = (
    (0.0, 0.0), (0.1, 7.0), (0.2, 14.0), (0.3, 21.0), (0.4, 31.0),
    (0.5, 41.0), (0.6, 52.0), (0.7, 63.0), (0.8, 75.3), (0.9, 87.8),
    (1.0, 100.0),
)

#: f0 of Eq.(3-19): (L, f0 mm) knots; constant beyond L >= 122 m.
_F0_SUPERSTRUCTURE = ((24.0, -350.0), (85.0, -860.0), (122.0, -1070.0))


def _interpolate(table: tuple[tuple[float, float], ...], x: float) -> float:
    """Piecewise-linear interpolation over sorted knots (clamped)."""
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x0 <= x <= x1:
            share = (x - x0) / (x1 - x0)
            return y0 + share * (y1 - y0)
    raise RuntimeError("unreachable: interpolation fell through the table")


def tabular_basic_freeboard(lpp: float, ship_type: str = "B") -> float:
    """Standard-ship basic freeboard F0 from Table 3-9, in millimetres.

    Linear interpolation between the 10 m table steps (the source uses
    1 m steps and prescribes interpolation for intermediate lengths;
    our transcription carries 10 m steps, which is the approximation
    declared for v0.1).

    Args:
        lpp: rule length L, m (24 <= L <= 365, the table range).
        ship_type: "A" or "B".
    """
    if ship_type not in ("A", "B"):
        raise SpecValidationError(
            "ship_type", ship_type, '"A" or "B"',
            "the load-line rules define exactly two ship types: type A "
            "(carriage of liquid cargo in bulk) and type B (every other "
            "ship); the freeboard table has a column for each.",
        )
    lengths = sorted(TABLE_3_9_BASIC_FREEBOARD)
    if not lengths[0] <= lpp <= lengths[-1]:
        raise SpecValidationError(
            "lpp", lpp,
            f"{lengths[0]} m <= L <= {lengths[-1]} m (Table 3-9 range)",
            "the transcribed freeboard table covers ship lengths from 24 "
            "to 365 m; outside that range the rules themselves change "
            "character and this module refuses instead of extrapolating.",
        )
    column = 0 if ship_type == "A" else 1
    for lo, hi in zip(lengths, lengths[1:]):
        if lo <= lpp <= hi:
            f_lo = TABLE_3_9_BASIC_FREEBOARD[lo][column]
            f_hi = TABLE_3_9_BASIC_FREEBOARD[hi][column]
            share = (lpp - lo) / (hi - lo)
            return f_lo + share * (f_hi - f_lo)
    raise RuntimeError("unreachable: length inside range but no bracket")


@dataclass(frozen=True)
class FreeboardResult:
    """Minimum summer freeboard and the verdict (JSON-serializable).

    Attributes:
        lpp: rule length, m.
        ship_type: "A" or "B".
        depth_s: calculation depth Ds, m.
        cb_at_085d: calculation block coefficient at 0.85*Ds (-).
        f0 / f1 / f2 / f3 / f4 / f5: basic freeboard and the five
            corrections, mm (positive values increase the freeboard).
        minimum_freeboard_mm: F = F0 + f1 + ... + f5, mm.
        actual_freeboard_mm: moulded freeboard of the design, mm.
        margin_mm: actual - minimum; a negative margin fails the check.
        verdict: "PASS" when actual >= minimum, else "FAIL".
        assumptions: declared approximations of this computation.
    """

    lpp: float
    ship_type: str
    depth_s: float
    cb_at_085d: float
    f0: float
    f1: float
    f2: float
    f3: float
    f4: float
    f5: float
    minimum_freeboard_mm: float
    actual_freeboard_mm: float
    margin_mm: float
    verdict: str
    assumptions: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lpp": self.lpp,
            "ship_type": self.ship_type,
            "depth_s": self.depth_s,
            "cb_at_085d": self.cb_at_085d,
            "f0": self.f0,
            "f1": self.f1,
            "f2": self.f2,
            "f3": self.f3,
            "f4": self.f4,
            "f5": self.f5,
            "minimum_freeboard_mm": self.minimum_freeboard_mm,
            "actual_freeboard_mm": self.actual_freeboard_mm,
            "margin_mm": self.margin_mm,
            "verdict": self.verdict,
            "assumptions": list(self.assumptions),
        }


def minimum_freeboard(
    lpp: float,
    ship_type: str,
    depth_s: float,
    cb_at_085d: float,
    actual_freeboard_mm: float,
    *,
    superstructure_ratio: float = 0.0,
    sheer_difference_w: float = 0.0,
    sheer_difference_u: float = 0.0,
    superstructure_length_s: float = 0.0,
) -> FreeboardResult:
    """Minimum summer freeboard per Eq.(3-15) and the verdict.

    Args:
        lpp: rule length L, m (24-365, Table 3-9 range).
        ship_type: "A" or "B".
        depth_s: calculation depth Ds, m (moulded depth plus freeboard-
            deck stringer plate; see the source for the exact definition).
        cb_at_085d: calculation block coefficient at draft 0.85*Ds (-).
            At stage 1 the deep-draft displacement needed for the exact
            value is beyond the waterline table; using the design-draft
            Cb is a declared approximation (a real hull's Cb at 0.85 Ds
            is slightly below its design Cb, so f2 errs slightly on the
            safe side for verdicts).
        actual_freeboard_mm: the design's moulded freeboard, mm
            (depth - draft).
        superstructure_ratio: effective superstructure length E / L (-),
            0 for a flush-deck ship (the conservative default).
        sheer_difference_w / sheer_difference_u: W and U of Eq.(3-20),
            mm (standard minus actual sheer aft/forward); 0 = standard
            sheer, the v0.1 default.
        superstructure_length_s: total length S of closed
            superstructures, m (enters f5 only).

    Returns:
        FreeboardResult with every correction itemised and the verdict.

    Raises:
        SpecValidationError: length outside the table, unknown ship
            type, non-physical Cb/depth, or E/L outside [0, 1].
    """
    f0 = tabular_basic_freeboard(lpp, ship_type)  # validates L and type
    if not math.isfinite(depth_s) or depth_s <= 0:
        raise SpecValidationError(
            "depth_s", depth_s, "finite Ds > 0",
            "the calculation depth bounds the freeboard from above: "
            "freeboard = depth - draft, so a non-positive depth "
            "describes no surface ship.",
        )
    if not math.isfinite(cb_at_085d) or not 0.0 < cb_at_085d <= 1.0 + 1e-9:
        raise SpecValidationError(
            "cb_at_085d", cb_at_085d, "0 < Cb <= 1",
            "the block coefficient at 0.85*Ds is a ratio of volumes: "
            "the immersed volume at that draft cannot exceed the box "
            "L*B*0.85*Ds that bounds it.",
        )
    if not math.isfinite(superstructure_ratio) or not (
        0.0 <= superstructure_ratio <= 1.0
    ):
        raise SpecValidationError(
            "superstructure_ratio", superstructure_ratio, "0 <= E/L <= 1",
            "the effective superstructure length is a fraction of the "
            "ship length; values outside [0, 1] are not a length ratio.",
        )
    for name, value in (
        ("sheer_difference_w", sheer_difference_w),
        ("sheer_difference_u", sheer_difference_u),
    ):
        if not math.isfinite(value):
            raise SpecValidationError(
                name, value, "a finite number",
                "the sheer differences W and U enter the f5 correction "
                "directly; they must be finite millimetre values.",
            )

    # f1 - Eq.(3-16), B-type ships under 100 m short of 35 % E/L
    f1 = 0.0
    if (
        ship_type == "B"
        and lpp < 100.0
        and superstructure_ratio < 0.35
    ):
        f1 = 7.5 * (100.0 - lpp) * (0.35 - superstructure_ratio)

    # f2 - Eq.(3-17), block-coefficient correction
    f2 = 0.0
    if cb_at_085d > 0.68:
        f2 = (f0 + f1) * ((cb_at_085d + 0.68) / 1.36 - 1.0)

    # f3 - Eq.(3-18), depth correction (never negative)
    f3 = 0.0
    if depth_s > lpp / 15.0:
        r_factor = lpp / 0.48 if lpp < 120.0 else 250.0
        f3 = (depth_s - lpp / 15.0) * r_factor

    # f4 - Eq.(3-19), superstructure correction (reduces the freeboard)
    f4 = 0.0
    if superstructure_ratio > 0.0:
        if lpp < _F0_SUPERSTRUCTURE[0][0]:
            raise SpecValidationError(
                "lpp", lpp, f">= {_F0_SUPERSTRUCTURE[0][0]} m for f4",
                "the superstructure correction f0 is tabulated from 24 m "
                "upwards; below that length the correction itself is "
                "outside its source range.",
            )
        f0_super = _interpolate(_F0_SUPERSTRUCTURE, lpp)
        k_table = _K_TABLE_A if ship_type == "A" else _K_TABLE_B_I
        k_percent = _interpolate(k_table, superstructure_ratio)
        f4 = (k_percent / 100.0) * f0_super

    # f5 - Eq.(3-20), sheer correction (default standard sheer -> 0)
    f5 = 0.5 * (sheer_difference_w + sheer_difference_u) * (
        0.75 - superstructure_length_s / (2.0 * lpp)
    )

    total = f0 + f1 + f2 + f3 + f4 + f5
    margin = actual_freeboard_mm - total
    assumptions = (
        "Table 3-9 interpolated linearly between 10 m steps",
        "Cb at 0.85*Ds approximated by the design-draft Cb",
        "plain type-B minimum: no Regulation-27 reductions, no B-60/B-100",
    )
    if sheer_difference_w == 0.0 and sheer_difference_u == 0.0:
        assumptions = assumptions + ("standard sheer assumed (W = U = 0)",)
    if superstructure_ratio == 0.0:
        assumptions = assumptions + ("flush deck assumed (E = 0, f4 = 0)",)

    return FreeboardResult(
        lpp=lpp,
        ship_type=ship_type,
        depth_s=depth_s,
        cb_at_085d=cb_at_085d,
        f0=f0,
        f1=f1,
        f2=f2,
        f3=f3,
        f4=f4,
        f5=f5,
        minimum_freeboard_mm=total,
        actual_freeboard_mm=actual_freeboard_mm,
        margin_mm=margin,
        verdict="PASS" if margin >= 0.0 else "FAIL",
        assumptions=assumptions,
    )
