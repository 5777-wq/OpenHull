"""Core data structures: ShipSpec and hydrostatics containers.

Every field carries a unit and a validity range. Range violations raise
:class:`SpecValidationError`, whose message states the constraint AND the
physical or mathematical reason behind it — a violation must explain
itself, never fail with a bare number (plan task 1.1 requirement).

Units follow AGENTS.md §1: metres, tonnes, cubic metres; speeds are
stored in m/s internally and converted from/to knots only at the
input/output boundaries; angles in degrees.

Validation is split in two tiers:
  * hard geometric/physical laws — always enforced (e.g. 0 < Cb <= 1,
    draft < depth, displacement = rho * displacement_volume);
  * sanity ranges for merchant ships — generous caps that catch unit
    mistakes (metres vs feet, t vs kg); they are deliberately wide and
    only promise to catch obvious nonsense.

Cross-field consistency checks run after the per-field checks.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Constants (AGENTS.md §1)
# ---------------------------------------------------------------------------

#: 1 knot = 1852 m / 3600 s
KNOTS_TO_MS = 1852.0 / 3600.0

#: Standard seawater density, t/m³ (AGENTS.md §1)
SEAWATER_DENSITY = 1.025


def knots_to_ms(knots: float) -> float:
    """Convert a speed in knots to metres per second."""
    return knots * KNOTS_TO_MS


def ms_to_knots(speed_ms: float) -> float:
    """Convert a speed in metres per second to knots."""
    return speed_ms / KNOTS_TO_MS


# ---------------------------------------------------------------------------
# Validation machinery
# ---------------------------------------------------------------------------


class SpecValidationError(ValueError):
    """A field value violates its validity range — with the reason why.

    Attributes:
        field: name of the offending field.
        value: the offending value.
        constraint: human-readable allowed range / condition.
        reason: physical or mathematical explanation of why the
            constraint exists (formulas included where applicable).
    """

    def __init__(self, field: str, value: object, constraint: str, reason: str):
        self.field = field
        self.value = value
        self.constraint = constraint
        self.reason = " ".join(reason.split())
        super().__init__(
            f"Invalid value for '{field}': {value!r}\n"
            f"  allowed: {self.constraint}\n"
            f"  why: {self.reason}"
        )


def _check(
    condition: bool,
    field: str,
    value: object,
    constraint: str,
    reason: str,
) -> None:
    if not condition:
        raise SpecValidationError(field, value, constraint, reason)


def _check_finite(field: str, value: float) -> None:
    _check(
        isinstance(value, (int, float)) and math.isfinite(value),
        field,
        value,
        "a finite number",
        "the value must be a real, finite number (NaN/inf cannot describe "
        "a physical ship quantity).",
    )


def _check_positive(field: str, value: float, unit: str, what: str) -> None:
    _check_finite(field, value)
    _check(
        value > 0.0,
        field,
        value,
        f"> 0 {unit}",
        f"{what} must be strictly positive; a non-positive {field} cannot "
        "describe a real ship.",
    )


def _check_optional_positive(
    field: str, value: float | None, unit: str, what: str
) -> None:
    if value is not None:
        _check_positive(field, value, unit, what)


# ---------------------------------------------------------------------------
# Explanations reused by several fields
# ---------------------------------------------------------------------------

_WHY_CB = (
    "the block coefficient is defined as Cb = displacement_volume / "
    "(Lpp * B * T): the ratio of the moulded displacement volume to the "
    "volume of the circumscribing rectangular box. A hull cannot displace "
    "more water than the box that bounds it, so Cb <= 1; Cb = 1 would be "
    "a rectangular box. Full-form ships such as bulk carriers lie around "
    "0.75-0.88; benchmark JBC has Cb = 0.8580."
)

_WHY_CM = (
    "the midship section coefficient is defined as Cm = Am / (B * T): "
    "the ratio of the immersed midship section area to the circumscribing "
    "rectangle B * T. The section cannot exceed the rectangle that bounds "
    "it, so Cm <= 1; full ships have Cm near 0.95-0.99 (JBC: 0.9981)."
)

_WHY_CW = (
    "the waterplane coefficient is defined as Cw = Aw / (Lpp * B): the "
    "ratio of the waterplane area to the circumscribing rectangle. The "
    "waterline cannot exceed the rectangle that bounds it, so Cw <= 1."
)

# ---------------------------------------------------------------------------
# ShipSpec
# ---------------------------------------------------------------------------


@dataclass
class ShipSpec:
    """Task book plus principal dimensions — the carrier of design state.

    All dimension fields start as None (only the task-book requirements
    are known) and are filled in by the design modules (plan tasks 1.2
    ff.). Every provided value is validated at construction; fields set
    to None are skipped until filled.

    Attributes (units per AGENTS.md §2):
        ship_type: vessel type tag, e.g. "bulk_carrier".
        deadweight: DW, deadweight, t.
        service_speed: service speed, m/s (use knots_to_ms() at the
            task-book boundary).
        lpp: L, length between perpendiculars, m.
        beam: B, moulded beam, m.
        depth: D, moulded depth, m.
        draft: T, moulded draft (even keel design draft), m.
        cb: block coefficient (-).
        cm: midship section coefficient (-).
        cwp: waterplane coefficient (-).
        lcb: longitudinal centre of buoyancy, % of Lpp, forward positive.
        displacement_volume: ∇, moulded displacement volume, m³.
        displacement: △, displacement mass (= rho * ∇), t.
    """

    ship_type: str = "bulk_carrier"
    deadweight: float | None = None
    service_speed: float | None = None
    lpp: float | None = None
    beam: float | None = None
    depth: float | None = None
    draft: float | None = None
    cb: float | None = None
    cm: float | None = None
    cwp: float | None = None
    lcb: float | None = None
    displacement_volume: float | None = None
    displacement: float | None = None

    def __post_init__(self) -> None:
        if not self.ship_type:
            raise SpecValidationError(
                "ship_type", self.ship_type, "a non-empty string",
                "the vessel type identifies which formula applicability "
                "ranges apply later; an empty tag carries no information.",
            )

        _check_optional_positive(
            "deadweight", self.deadweight, "t", "deadweight"
        )
        if self.deadweight is not None:
            _check(
                1.0 <= self.deadweight <= 1_000_000.0,
                "deadweight", self.deadweight, "1 t <= DW <= 1,000,000 t",
                "sanity range for merchant ships (from small coasters to "
                "the largest ore carriers); values outside it usually "
                "hide a unit mistake (t vs kg vs long tons).",
            )

        _check_optional_positive(
            "service_speed", self.service_speed, "m/s", "service speed"
        )
        if self.service_speed is not None:
            _check(
                self.service_speed <= 30.0,
                "service_speed", self.service_speed,
                "0 < v <= 30 m/s (~58 kn)",
                "sanity range: the fastest merchant ships run ~25-30 kn; "
                "larger values usually mean the speed was given in knots "
                "but stored in m/s (use knots_to_ms()).",
            )

        _check_optional_positive("lpp", self.lpp, "m", "length between perpendiculars")
        if self.lpp is not None:
            _check(
                5.0 <= self.lpp <= 500.0,
                "lpp", self.lpp, "5 m <= Lpp <= 500 m",
                "sanity range covering the smallest working boats to the "
                "largest seagoing merchant ships (~400 m); larger values "
                "usually hide a unit mistake.",
            )

        _check_optional_positive("beam", self.beam, "m", "moulded beam")
        if self.beam is not None:
            _check(
                2.0 <= self.beam <= 70.0,
                "beam", self.beam, "2 m <= B <= 70 m",
                "sanity range for merchant ships; port infrastructure "
                "caps real beams near 60 m.",
            )

        _check_optional_positive("depth", self.depth, "m", "moulded depth")
        if self.depth is not None:
            _check(
                2.0 <= self.depth <= 40.0,
                "depth", self.depth, "2 m <= D <= 40 m",
                "sanity range for merchant ships.",
            )

        _check_optional_positive("draft", self.draft, "m", "moulded draft")
        if self.draft is not None:
            _check(
                0.5 <= self.draft <= 30.0,
                "draft", self.draft, "0.5 m <= T <= 30 m",
                "sanity range for merchant ships; the deepest laden drafts "
                "(large ore carriers) are near 23-24 m.",
            )

        for name, why in (("cb", _WHY_CB), ("cm", _WHY_CM), ("cwp", _WHY_CW)):
            value = getattr(self, name)
            if value is not None:
                _check_finite(name, value)
                _check(
                    0.0 < value <= 1.0,
                    name, value, "0.0 < coefficient <= 1.0", why,
                )

        if self.lcb is not None:
            _check_finite("lcb", self.lcb)
            _check(
                abs(self.lcb) < 50.0,
                "lcb", self.lcb, "-50 % < LCB < +50 % of Lpp",
                "the centre of buoyancy is the centroid of the immersed "
                "volume and must lie within the ship's length; |LCB| >= "
                "50 % would place it outside the hull. Merchant ships "
                "keep |LCB| within a few percent of midship.",
            )
            _check(
                abs(self.lcb) <= 6.0,
                "lcb", self.lcb, "-6 % <= LCB <= +6 % of Lpp",
                "sanity range: merchant ships keep the centre of buoyancy "
                "within about 6 % of midship (full ships 0.5-3 % forward).",
            )

        _check_optional_positive(
            "displacement_volume",
            self.displacement_volume, "m³", "displacement volume",
        )
        if self.displacement_volume is not None:
            _check(
                self.displacement_volume <= 2_000_000.0,
                "displacement_volume", self.displacement_volume,
                "0 < displacement_volume <= 2,000,000 m3",
                "sanity range: the largest ore carriers displace about "
                "600,000 m³; larger values usually hide a unit mistake.",
            )

        _check_optional_positive(
            "displacement", self.displacement, "t", "displacement mass"
        )

        self._check_cross_fields()

    # -- cross-field consistency ------------------------------------------

    def _check_cross_fields(self) -> None:
        # freeboard must be positive: a deck at or below the design
        # waterline leaves no reserve buoyancy
        if self.depth is not None and self.draft is not None:
            _check(
                self.draft < self.depth,
                "draft", self.draft,
                "T < D (positive freeboard)",
                "freeboard F = D - T is the reserve of buoyancy between "
                "waterline and deck; at T >= D the deck would be at or "
                "below the waterline and the ship could not be a stable, "
                "regulation-compliant surface ship. (Statutory minimum "
                "freeboard is checked separately in plan task 1.6.)",
            )

        # displacement must equal rho * displacement_volume (Archimedes)
        if (
            self.displacement is not None
            and self.displacement_volume is not None
        ):
            expected = SEAWATER_DENSITY * self.displacement_volume
            _check(
                abs(self.displacement - expected) <= 0.01 * self.displacement,
                "displacement", self.displacement,
                f"displacement = {SEAWATER_DENSITY} * displacement_volume "
                "(within 1 %)",
                f"Archimedes' principle: displacement = rho * "
                f"displacement_volume, with the seawater density fixed in "
                f"AGENTS.md §1 (rho = {SEAWATER_DENSITY} "
                "t/m³). The two values you provided disagree beyond 1 %, "
                "so they cannot describe the same ship in seawater.",
            )

        # deadweight is carried on top of the lightweight
        if self.deadweight is not None and self.displacement is not None:
            _check(
                self.deadweight < self.displacement,
                "deadweight", self.deadweight,
                "DW < △",
                "deadweight is carried on top of the lightweight: "
                "△ = LW + DW. DW >= △ would mean the cargo alone weighs "
                "at least as much as the whole loaded ship — impossible.",
            )

        # a provided Cb must agree with the dimensions it is defined by
        if self.cb is not None and None not in (
            self.lpp, self.beam, self.draft, self.displacement_volume
        ):
            implied = self.displacement_volume / (
                self.lpp * self.beam * self.draft
            )
            _check(
                abs(self.cb - implied) <= 0.01 * implied + 1e-9,
                "cb", self.cb,
                "cb = displacement_volume / (Lpp * B * T) (within 1 %)",
                f"the provided Cb disagrees with the value implied by the "
                f"provided dimensions and volume ({implied:.4f}); by "
                f"definition Cb = displacement_volume / (Lpp * B * T), so "
                f"the numbers cannot describe the same hull form.",
            )

    # -- derived quantities -------------------------------------------------

    @property
    def service_speed_kn(self) -> float | None:
        """Service speed in knots (for reports; AGENTS.md §1 boundary)."""
        if self.service_speed is None:
            return None
        return ms_to_knots(self.service_speed)

    @property
    def freeboard(self) -> float | None:
        """F = D - T, moulded freeboard at the design draft, m."""
        if self.depth is None or self.draft is None:
            return None
        return self.depth - self.draft

    @property
    def cp(self) -> float | None:
        """Prismatic coefficient Cp = Cb / Cm (None if inputs missing)."""
        if self.cb is None or self.cm is None:
            return None
        return self.cb / self.cm


# ---------------------------------------------------------------------------
# Hydrostatics containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hydrostatics:
    """Hydrostatic particulars at one even-keel draft (plan task 1.4).

    Attributes (units per AGENTS.md §2):
        draft: T, even-keel draft, m.
        displacement_volume: ∇, moulded displacement volume, m³.
        displacement: △, displacement mass, t.
        aw: waterplane area at this draft, m².
        lcf: longitudinal centre of flotation, % of Lpp, forward positive.
        cb: block coefficient at this draft (-).
        cm: midship section coefficient at this draft (-).
        cp: prismatic coefficient at this draft (-).
        cw: waterplane coefficient at this draft (-).
        kb: vertical centre of buoyancy above keel, m.
        bmt: transverse metacentric radius, m.
        bml: longitudinal metacentric radius, m.
        tpc: tonnes per centimetre immersion, t/cm.
        mtc: moment to change trim one centimetre, t*m/cm.
    """

    draft: float
    displacement_volume: float
    displacement: float
    aw: float
    lcf: float
    cb: float
    cm: float
    cp: float
    cw: float
    kb: float
    bmt: float
    bml: float
    tpc: float
    mtc: float

    def __post_init__(self) -> None:
        _check_positive("draft", self.draft, "m", "draft")
        _check_positive(
            "displacement_volume", self.displacement_volume, "m3",
            "displacement volume",
        )
        _check_positive("displacement", self.displacement, "t", "displacement mass")
        _check_positive("aw", self.aw, "m2", "waterplane area")
        _check_positive("tpc", self.tpc, "t/cm", "TPC")
        _check_positive("mtc", self.mtc, "t*m/cm", "MTC")

        for name, why in (("cb", _WHY_CB), ("cm", _WHY_CM), ("cw", _WHY_CW)):
            value = getattr(self, name)
            _check_finite(name, value)
            _check(0.0 < value <= 1.0, name, value, "0.0 < coefficient <= 1.0", why)

        _check_finite("cp", self.cp)
        _check(
            0.0 < self.cp <= 1.0,
            "cp", self.cp, "0.0 < Cp <= 1.0",
            "the prismatic coefficient is defined as Cp = Cb / Cm: the "
            "ratio of the displacement volume to the prism Am * Lpp. "
            "Each sectional area is at most the midship area for a "
            "conventional hull, so the volume cannot exceed that prism "
            "and Cp <= 1.",
        )

        _check_finite("lcf", self.lcf)
        _check(
            abs(self.lcf) < 50.0,
            "lcf", self.lcf, "-50 % < LCF < +50 % of Lpp",
            "the centre of flotation is a centroid of the waterplane and "
            "must lie within the ship's length.",
        )

        _check(
            0.0 < self.kb < self.draft,
            "kb", self.kb, "0 < KB < T",
            "KB is the centroid height of the immersed volume; the "
            "centroid of a volume lying entirely below the waterline "
            "must itself lie below the waterline, so KB < T.",
        )
        _check(
            self.bmt > 0.0,
            "bmt", self.bmt, "> 0 m",
            "the transverse metacentric radius BMT = I_T / ∇ is the ratio "
            "of the waterplane transverse moment of inertia (strictly "
            "positive for any real waterplane) to the displacement "
            "volume, so it cannot be zero or negative.",
        )
        _check(
            self.bml > 0.0,
            "bml", self.bml, "> 0 m",
            "the longitudinal metacentric radius BML = I_L / ∇ is the ratio "
            "of the waterplane longitudinal moment of inertia (strictly "
            "positive for any real waterplane) to the displacement volume.",
        )

    @property
    def km(self) -> float:
        """Transverse metacentre above keel, KM = KB + BMT, m."""
        return self.kb + self.bmt


@dataclass
class HydrostaticsTable:
    """Hydrostatic particulars across a set of drafts (plan task 1.4).

    Attributes:
        entries: one Hydrostatics record per draft, in strictly
            increasing draft order.
    """

    entries: list[Hydrostatics] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.entries:
            raise SpecValidationError(
                "entries", self.entries, "at least one record",
                "a hydrostatic table with no rows carries no information; "
                "compute at least one draft (plan task 1.4).",
            )
        for earlier, later in zip(self.entries, self.entries[1:]):
            _check(
                later.draft > earlier.draft,
                "entries", later.draft,
                "drafts strictly increasing",
                f"draft {later.draft} does not follow {earlier.draft}: a "
                "hydrostatic table is a function of draft, and duplicated "
                "or out-of-order drafts break interpolation.",
            )

    def at(self, draft: float) -> Hydrostatics:
        """Return the record exactly matching a tabulated draft."""
        for entry in self.entries:
            if entry.draft == draft:
                return entry
        raise KeyError(
            f"no record for draft {draft}; tabulated drafts: "
            f"{[e.draft for e in self.entries]}"
        )
