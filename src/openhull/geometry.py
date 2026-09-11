"""Hull geometry container and the analytic JBC parent (plan task 1.4).

The hydrostatics module consumes an :class:`OffsetsTable` — half-breadths
on a stations x waterlines grid — so that geometry and computation stay
decoupled (AGENTS.md section 8): when plan task 2.1 digitises the real
Series 60 / DTMB 1712 offsets, they feed into the same container and the
hydrostatics code is reused unchanged (plan task 2.6).

Stage-1 geometry source: an analytic parent hull fitted to the JBC
task-book anchors.  The half-breadth field is

    y(xi, zeta) = (B/2) * g(xi)**u(zeta) * hb(zeta)

with normalised length xi = x/Lpp and draft zeta = z/T, and

  * g: a two-power sectional-area-curve shape (parabolic taper of power
    p_a aft of midship, p_f forward), g(1/2) = 1;
  * u(zeta) = 1 + k*(1 - zeta): the vertical exponent.  k = 0 would give
    geometrically similar waterlines, which pins KB at about T/2 for a
    nearly rectangular midship section (Cm = 0.9981) and misses the KM
    anchor by 7 %.  Larger k thins the sections towards the keel — the
    way real end sections narrow towards the bottom — and shifts the
    volume upwards; k is fitted so the table reproduces the KM anchor;
  * hb: an idealised circular bilge rounding at the bottom, with the
    radius derived from the midship-coefficient deficit
    (1 - Cm)*B*T = 2*r^2*(1 - pi/4), reproducing Cm exactly.

The fit solves three conditions in three unknowns (p_a, p_f, k), all by
deterministic bisection on monotone functions:

    Cb  = 0.8580       [NMRI] block coefficient at the design draft
    LCB = +2.5475 %Lpp [NMRI] longitudinal centre of buoyancy, fwd+
    KM  = 18.59 m      derived from [NMRI] full-load GM 5.30 m + KG 13.29 m

Declared stage-1 approximations (approved task-1.4 plan): waterlines
share one shape family; the geometry is built on Lpp (JBC's published
L_WL = 285 m, bulb overhang, is not modelled); the bilge is circular.
The hydrostatics themselves are always NUMERICALLY integrated from the
tabulated offsets — the analytic form only generates the table.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .spec import SpecValidationError

# ---------------------------------------------------------------------------
# Offsets table
# ---------------------------------------------------------------------------


@dataclass(frozen=True, eq=False)
class OffsetsTable:
    """Tabulated moulded half-breadths on a stations x waterlines grid.

    Attributes:
        lpp: Lpp, length between perpendiculars, m (stations[0] = 0 is
            the AP, stations[-1] = lpp the FP).
        beam: B, moulded beam, m (twice the maximum half-breadth).
        stations: (Ns,) station positions from AP, m, strictly
            increasing, first = 0 and last = lpp.  For Simpson
            integration along the length the number of intervals must
            be even, i.e. Ns is odd.
        waterlines: (Nw,) waterline heights above keel, m, strictly
            increasing, first = 0 (keel).  For Simpson integration in
            draft Nw must be odd.
        half_breadths: (Ns, Nw) moulded half-breadths, m, finite, >= 0
            and <= beam/2.

    Units per AGENTS.md section 1.
    """

    lpp: float
    beam: float
    stations: np.ndarray
    waterlines: np.ndarray
    half_breadths: np.ndarray

    def __post_init__(self) -> None:
        if not math.isfinite(self.lpp) or self.lpp <= 0:
            raise SpecValidationError(
                "lpp", self.lpp, "finite Lpp > 0",
                "the offsets grid spans the ship length; without a "
                "positive Lpp the table describes no ship.",
            )
        if not math.isfinite(self.beam) or self.beam <= 0:
            raise SpecValidationError(
                "beam", self.beam, "finite B > 0",
                "the beam bounds every half-breadth; a non-positive beam "
                "describes no ship.",
            )
        stations = np.asarray(self.stations, dtype=float)
        waterlines = np.asarray(self.waterlines, dtype=float)
        y = np.asarray(self.half_breadths, dtype=float)
        if y.ndim != 2 or y.shape != (stations.size, waterlines.size):
            raise SpecValidationError(
                "half_breadths", y.shape,
                f"shape (n_stations, n_waterlines) = "
                f"({stations.size}, {waterlines.size})",
                "the half-breadth matrix must hold one row per station "
                "and one column per waterline; a shape mismatch means "
                "the offsets were transposed or a station/waterline row "
                "is missing.",
            )
        if stations.size < 3 or waterlines.size < 3:
            raise SpecValidationError(
                "stations", stations.size, ">= 3 stations and waterlines",
                "numerical integration needs at least three sections; "
                "fewer points cannot define a hull surface.",
            )
        if not (np.all(np.diff(stations) > 0) and np.isclose(stations[0], 0.0)
                and np.isclose(stations[-1], self.lpp)):
            raise SpecValidationError(
                "stations", stations,
                f"strictly increasing, stations[0] = 0, stations[-1] = Lpp "
                f"({self.lpp})",
                "station positions are the integration abscissa: they must "
                "run from the AP (0) to the FP (Lpp) in order, otherwise "
                "every longitudinal integral is meaningless.",
            )
        if not (np.all(np.diff(waterlines) > 0) and np.isclose(waterlines[0], 0.0)):
            raise SpecValidationError(
                "waterlines", waterlines,
                "strictly increasing, waterlines[0] = 0 (keel)",
                "waterline heights are the vertical integration abscissa: "
                "they must start at the keel (z = 0) and increase, "
                "otherwise volume integration is meaningless.",
            )
        if not np.all(np.isfinite(y)) or np.any(y < 0) or np.any(y > self.beam / 2):
            raise SpecValidationError(
                "half_breadths", "min/max out of range" if np.all(np.isfinite(y))
                else "non-finite entry",
                f"finite, 0 <= y <= B/2 ({self.beam / 2} m)",
                "a half-breadth cannot be negative (the hull is on one "
                "side of the centreline) and cannot exceed half the "
                "moulded beam (the two sides would overlap).",
            )
        if stations.size % 2 == 0 or waterlines.size % 2 == 0:
            raise SpecValidationError(
                "stations", stations.size,
                "odd number of stations AND odd number of waterlines "
                "(even number of intervals)",
                "Simpson's first rule integrates over pairs of intervals, "
                "so each direction needs an even interval count (Ship "
                "Theory vol. 1, ch. 2: n must be even for the 1/3 rule). "
                "Use 21 stations and 33 waterlines, for example.",
            )
        object.__setattr__(self, "stations", stations)
        object.__setattr__(self, "waterlines", waterlines)
        object.__setattr__(self, "half_breadths", y)


# ---------------------------------------------------------------------------
# Analytic JBC parent generator
# ---------------------------------------------------------------------------

#: default KM anchor, m — derived from NMRI full-load GM 5.30 m + KG 13.29 m
JBC_KM_TARGET_M = 18.59


def _taper(xi: np.ndarray, pa: float, pf: float) -> np.ndarray:
    """Two-power sectional-area shape g(xi); g(1/2) = 1, g(0) = g(1) = 0."""
    return np.where(
        xi <= 0.5,
        1.0 - np.clip(1.0 - 2.0 * xi, 0.0, 1.0) ** pa,
        1.0 - np.clip(2.0 * xi - 1.0, 0.0, 1.0) ** pf,
    )


def _simpson_weights(n_points: int, spacing: float) -> np.ndarray:
    """Composite Simpson's first-rule weight vector (n_points odd)."""
    w = np.ones(n_points)
    w[1:-1:2] = 4.0
    w[2:-1:2] = 2.0
    return w * spacing / 3.0


def _w_curve(
    xi: np.ndarray,
    pa: float,
    pf: float,
    k: float,
    zeta: np.ndarray,
    wz: np.ndarray,
    hb: np.ndarray,
) -> np.ndarray:
    """Vertical integral of the half-breadth field, in (B/2) units.

    w(xi) = integral of g(xi)**(1 + k*(1-zeta)) * hb(zeta) d(zeta),
    evaluated by Simpson over the zeta grid.  The volume and its
    longitudinal centroid follow from integrals of w over xi.
    """
    g = _taper(xi, pa, pf)[:, None]
    u = 1.0 + k * (1.0 - zeta)[None, :]
    return ((g**u) * hb[None, :]) @ wz


def _fit_pa_pf(
    k: float,
    cb_target: float,
    centroid_target: float,
    xi: np.ndarray,
    wx: np.ndarray,
    zeta: np.ndarray,
    wz: np.ndarray,
    hb: np.ndarray,
) -> tuple[float, float]:
    """Solve (p_a, p_f) so that w has the requested area and centroid.

    Nested bisection on monotone functions: the volume centroid rises
    with p_f (a fuller bow pulls it forward), and — with the centroid
    held at target by p_f — the volume rises with p_a, so the area
    residual brackets cleanly.  Deterministic.
    """

    def field(pa: float, pf: float) -> tuple[float, float]:
        w = _w_curve(xi, pa, pf, k, zeta, wz, hb)
        area = float(wx @ w)
        centroid = float(wx @ (xi * w)) / area
        return area, centroid

    def pf_for_centroid(pa: float) -> float:
        lo, hi = 0.2, 400.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if field(pa, mid)[1] < centroid_target:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    pa_lo, pa_hi = 0.3, 60.0
    for _ in range(60):
        pa_mid = 0.5 * (pa_lo + pa_hi)
        pf = pf_for_centroid(pa_mid)
        if field(pa_mid, pf)[0] < cb_target:
            pa_lo = pa_mid
        else:
            pa_hi = pa_mid
    pa = 0.5 * (pa_lo + pa_hi)
    pf = pf_for_centroid(pa)
    return pa, pf


def _table_from(
    pa: float,
    pf: float,
    k: float,
    *,
    lpp: float,
    beam: float,
    draft: float,
    hb_waterlines: np.ndarray,
    n_stations: int,
    n_waterlines: int,
) -> OffsetsTable:
    """Build the offsets table for one set of fitted parameters."""
    xi = np.linspace(0.0, 1.0, n_stations)
    zeta = np.linspace(0.0, 1.0, n_waterlines)
    g = _taper(xi, pa, pf)[:, None]
    u = 1.0 + k * (1.0 - zeta)[None, :]
    y = (beam / 2.0) * (g**u) * hb_waterlines[None, :]
    return OffsetsTable(
        lpp=lpp,
        beam=beam,
        stations=xi * lpp,
        waterlines=zeta * draft,
        half_breadths=y,
    )


def jbc_parent_offsets(
    *,
    lpp: float = 280.0,
    beam: float = 45.0,
    draft: float = 16.5,
    cb: float = 0.8580,
    cm: float = 0.9981,
    lcb_fwd_pct: float = 2.5475,
    km_target: float = JBC_KM_TARGET_M,
    n_stations: int = 21,
    n_waterlines: int = 33,
) -> OffsetsTable:
    """Analytic parent hull fitted to the JBC task-book anchors.

    Reproduces through the numerical pipeline:

        Cb  = 0.8580        [NMRI] block coefficient at design draft
        Cm  = 0.9981        [NMRI] midship coefficient (via the bilge)
        LCB = +2.5475 %Lpp  [NMRI] forward of midship
        KM  = 18.59 m       [NMRI] GM 5.30 m + KG 13.29 m

    Args:
        lpp / beam / draft: moulded dimensions, m.
        cb / cm / lcb_fwd_pct: form-coefficient targets (-, -, % Lpp).
        km_target: transverse metacentre above keel, m, fitted via the
            vertical-exponent parameter k.
        n_stations / n_waterlines: grid sizes (both odd, see
            OffsetsTable; defaults 21 x 33 per the classic 20-station
            hull splitting).

    Returns:
        OffsetsTable on the stations x waterlines grid.
    """
    if n_stations % 2 == 0 or n_waterlines % 2 == 0:
        raise SpecValidationError(
            "n_stations", n_stations,
            "odd n_stations and odd n_waterlines",
            "Simpson's first rule needs an even interval count in both "
            "directions (Ship Theory vol. 1, ch. 2).",
        )
    if not 0.0 < cm < 1.0:
        raise SpecValidationError(
            "cm", cm, "0 < Cm < 1",
            "the bilge radius is derived from the midship-coefficient "
            "deficit; Cm = 1 (pure box) leaves no bilge to derive and "
            "Cm <= 0 describes no section.",
        )

    # circular bilge radius from the Cm deficit (exact: the section-area
    # loss of two quarter-circles of radius r is 2*r^2*(1 - pi/4))
    r_bilge = math.sqrt(
        (1.0 - cm) * beam * draft / (2.0 * (1.0 - math.pi / 4.0))
    )

    # fit grids (odd point counts, Simpson along both fit axes)
    xi_fit = np.linspace(0.0, 1.0, 101)
    zeta_fit = np.linspace(0.0, 1.0, 17)
    wz = _simpson_weights(zeta_fit.size, float(zeta_fit[1] - zeta_fit[0]))
    wx = _simpson_weights(xi_fit.size, float(xi_fit[1] - xi_fit[0]))

    z_fit = zeta_fit * draft
    loss = np.where(
        z_fit < r_bilge,
        r_bilge - np.sqrt(np.clip(r_bilge**2 - (r_bilge - z_fit) ** 2, 0.0, None)),
        0.0,
    )
    hb_fit = 1.0 - (2.0 / beam) * loss

    hb_waterlines = np.interp(
        np.linspace(0.0, 1.0, n_waterlines), zeta_fit, hb_fit
    )
    hb_waterlines = np.maximum(hb_waterlines, 1.0 - (2.0 / beam) * r_bilge)

    centroid_fit = 0.5 + lcb_fwd_pct / 100.0

    from .hydrostatics import (  # lazy: avoids import cycle
        bonjean_areas,
        hydrostatics_at,
        simpson,
    )

    def build_once(centroid_target: float) -> OffsetsTable:
        """Fit (p_a, p_f, k) and build the table for one centroid target."""

        def build(k: float) -> OffsetsTable:
            pa, pf = _fit_pa_pf(
                k, cb, centroid_target, xi_fit, wx, zeta_fit, wz, hb_fit
            )
            return _table_from(
                pa, pf, k, lpp=lpp, beam=beam, draft=draft,
                hb_waterlines=hb_waterlines,
                n_stations=n_stations, n_waterlines=n_waterlines,
            )

        # bisection: KM rises with k (volume shifts upwards)
        k_lo, k_hi = 0.0, 12.0
        for _ in range(32):
            k_mid = 0.5 * (k_lo + k_hi)
            if hydrostatics_at(build(k_mid), draft).km < km_target:
                k_lo = k_mid
            else:
                k_hi = k_mid
        return build(0.5 * (k_lo + k_hi))

    # The (p_a, p_f) fit targets the volume centroid on a fine continuum
    # grid; the tabulated pipeline (21 x 33, Simpson) measures it with a
    # small discretization offset.  One compensation pass feeds the
    # measured offset back into the fit target, the way a naval architect
    # re-runs a lines plan after the first offset table.
    table = build_once(centroid_fit)
    for _ in range(2):
        levels, areas = bonjean_areas(table)
        volume = simpson(areas[:, -1], float(table.stations[1] - table.stations[0]))
        moment = simpson(
            areas[:, -1] * table.stations,
            float(table.stations[1] - table.stations[0]),
        )
        lcb_pct = (moment / volume - lpp / 2.0) / lpp * 100.0
        delta = lcb_pct - lcb_fwd_pct
        if abs(delta) < 0.02:
            break
        centroid_fit -= delta / 100.0
        table = build_once(centroid_fit)
    return table


# ---------------------------------------------------------------------------
# Digitised Series 60 parent (plan task 2.1) loader
# ---------------------------------------------------------------------------

#: expected form coefficients of the digitised parent (DTMB 1712 report
#: values for Model 4214W-B4, "Series 60, Cb = 0.80" = Cp 0.805)
SERIES60_CP_TOTAL = 0.805
SERIES60_CP_FORE = 0.861
SERIES60_CP_AFT = 0.750


def load_offsets_csv(
    path: str,
    *,
    lpp: float,
    beam: float,
    draft: float,
    n_stations: int = 21,
    n_waterlines: int = 27,
) -> OffsetsTable:
    """Load the digitised DTMB 1712 Table-7 offsets into an OffsetsTable.

    The CSV layout (examples/data/parent_hull_offsets.csv) follows the
    report's Table 7: half-breadths are FRACTIONS of each waterline's
    maximum half-breadth, the ``max_half_beam`` row holds each
    waterline's maximum half-breadth as a fraction of B/2, and the
    ``tan_line`` column is the baseline tangent half-breadth as a
    fraction of B/2.  Stations run FP..AP in twentieths of Lpp with
    extra half-stations, so the grid is NOT equally spaced; it is
    resampled onto ``n_stations`` equal stations (Simpson-compatible)
    by linear interpolation per waterline, and the five tabulated
    waterline fractions (0.075..1.00) plus the baseline are resampled
    onto ``n_waterlines`` equal intervals of draft.

    Acceptance anchors (validated in the test suite): the rebuilt table
    reproduces the report's Cp = 0.805 total / 0.861 fore / 0.750 aft.
    """
    import csv

    rows: list[list[str]] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.reader(line for line in fh if not line.startswith("#")):
            if row:
                rows.append([cell.strip() for cell in row])

    header = rows[0]
    body = {r[0]: r for r in rows[1:]}
    for name, row in body.items():  # fail loudly on ragged rows: a
        if len(row) != len(header):  # missing cell would silently shift
            raise ValueError(        # every later column of the row
                f"row '{name}' in {path} has {len(row)} fields, "
                f"expected {len(header)}"
            )
    wl_names = [name for name in header if name.startswith("wl_")]
    wl_fracs = [float(name.removeprefix("wl_")) for name in wl_names]
    wl_cols = [header.index(name) for name in wl_names]
    tan_col = header.index("tan_line")
    # "Max. half beam" row: per-column maxima as fractions of B/2 —
    # first value belongs to the Tan. column, the rest to the waterlines
    mh_row = [float(v) for v in body["max_half_beam"][1:] if v != ""]
    tan_max, wl_max = mh_row[0], mh_row[1:]

    # absolute half-breadths (m) at the tabulated levels, station-major
    tab_stations: list[float] = []
    tab_y: list[list[float]] = []  # (station, level)
    for name, row in body.items():
        if name == "max_half_beam":
            continue
        xi = 1.0 if name == "FP" else (0.0 if name == "AP"
                                       else 1.0 - float(name) / 20.0)
        abs_wl = [float(row[c]) * mh * beam / 2.0
                  for c, mh in zip(wl_cols, wl_max)]
        tan_abs = float(row[tan_col]) * tan_max * beam / 2.0
        tab_stations.append(xi * lpp)
        # levels: baseline (tan line), then the tabulated waterlines
        tab_y.append([tan_abs] + abs_wl)

    order = sorted(range(len(tab_stations)), key=lambda i: tab_stations[i])
    tab_stations = [tab_stations[i] for i in order]
    tab_y = [tab_y[i] for i in order]

    levels = [0.0] + [f * draft for f in wl_fracs]  # z heights, m
    stations_q = np.linspace(0.0, lpp, n_stations)
    zeta_q = np.linspace(0.0, draft, n_waterlines)
    # the tabulated grid is NOT equally spaced (extra half stations),
    # so resample BOTH directions: vertical per station, then
    # longitudinal per waterline
    vert = np.array([np.interp(zeta_q, levels, row) for row in tab_y])
    grid = np.column_stack([
        np.interp(stations_q, tab_stations, vert[:, j])
        for j in range(n_waterlines)
    ])
    return OffsetsTable(
        lpp=lpp, beam=beam, stations=stations_q,
        waterlines=zeta_q, half_breadths=grid,
    )
