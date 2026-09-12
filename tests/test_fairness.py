"""Tests for the fairness checker (plan task 2.5).

Anchors:
  * plan acceptance: the digitised Series 60 parent (DTMB 1712 Table 7,
    known fair) must pass with ZERO issues — the alarm must not frame
    the innocent;
  * tables with a planted spike / kink / lobe break / wobble must be
    flagged — the alarm must catch the guilty;
  * calibration: the parent's maximum measured curvature contrast is
    12.2 (dimensionless, Lpp^2/B scale) on the standard 21-station
    grid, so the default floor of 25 sits at ~2x with margin.  Planted
    errors are sized from the same scale: a single-point spike of depth
    d gives contrast ~ 2*d*(Lpp/dx)^2/B, a slope step s gives ~
    s/dx * Lpp^2/B.
"""

from pathlib import Path

import numpy as np
import pytest

from openhull.geometry import OffsetsTable, load_offsets_csv
from openhull.fairness import FairnessIssue, FairnessReport, check_fairness

CSV = Path(__file__).resolve().parents[1] / "examples" / "data" / \
    "parent_hull_offsets.csv"
LPP, BEAM, DRAFT = 280.0, 45.0, 16.5


def series60() -> OffsetsTable:
    return load_offsets_csv(str(CSV), lpp=LPP, beam=BEAM, draft=DRAFT)


def planted(mutate) -> OffsetsTable:
    """A copy of the parent grid with ``mutate(stations, y)`` applied."""
    base = series60()
    stations = np.array(base.stations, dtype=float)
    y = np.array(base.half_breadths, dtype=float)
    mutate(stations, y)
    return OffsetsTable(lpp=base.lpp, beam=base.beam, stations=stations,
                        waterlines=np.array(base.waterlines, dtype=float),
                        half_breadths=y)


def synthetic_parabola(n_stations: int = 41, lpp: float = 180.0,
                       beam: float = 30.0) -> OffsetsTable:
    """A fair-by-construction hull: every waterline the same parabola.

    y = ymax * (1 - (2x/L - 1)^2) has CONSTANT second difference, so the
    local contrast of the checker is exactly zero — no alarms.
    """
    x = np.linspace(0.0, lpp, n_stations)
    z = np.linspace(0.0, 10.0, 5)
    ymax = beam / 2 * 0.9  # keep clear of the B/2 ceiling
    y = np.tile(ymax * (1.0 - (2.0 * x / lpp - 1.0) ** 2)[:, None], (1, 5))
    return OffsetsTable(lpp=lpp, beam=beam, stations=x, waterlines=z,
                        half_breadths=y)


def _dx(stations: np.ndarray) -> float:
    return float(stations[1] - stations[0])


# ---------------------------------------------------------------------------
# the innocent: plan-task-2.5 acceptance
# ---------------------------------------------------------------------------


def test_series60_parent_zero_issues():
    rep = check_fairness(series60(), z_limit=DRAFT)
    assert isinstance(rep, FairnessReport)
    assert rep.issues == ()
    assert rep.ok
    assert rep.n_stations == 21
    assert rep.n_waterlines_checked == 27
    assert rep.z_limit == pytest.approx(DRAFT)


def test_parent_contrast_margin_under_default_floor():
    # guard the calibration: the fair parent must sit clearly below the
    # absolute floor, not squeeze past it (measured 12.2 vs floor 25)
    rep = check_fairness(series60(), z_limit=DRAFT)
    assert rep.max_contrast < 25.0 * 0.7


def test_parent_parallel_middle_body_detected():
    rep = check_fairness(series60(), z_limit=DRAFT)
    assert rep.parallel_segments, "Series 60 has a parallel middle body"
    for z, x_from, x_to in rep.parallel_segments:
        assert 0.0 < x_from < x_to < LPP
    widths = [x_to - x_from for _, x_from, x_to in rep.parallel_segments]
    assert min(widths) > 1.5 * _dx(series60().stations)


def test_summary_of_fair_table_says_ok():
    rep = check_fairness(series60(), z_limit=DRAFT)
    text = rep.summary()
    assert "0 issue(s)" in text and "OK" in text


def test_fair_parabola_zero_issues():
    rep = check_fairness(synthetic_parabola())
    assert rep.ok, rep.summary()


# ---------------------------------------------------------------------------
# the guilty: planted defects must be caught
# ---------------------------------------------------------------------------


def test_single_point_spike_flagged_as_curvature_jump():
    # 2.7 m mis-read at one bow station of a LOW waterline (there is
    # headroom below B/2 in the bow of this full-form parent; the DWL
    # already sits at B/2 almost to the bow).  i=17 = x=238 m.
    def bump(s, y):
        y[17, 7] += 0.06 * BEAM

    rep = check_fairness(planted(bump), z_limit=DRAFT)
    jumps = [i for i in rep.issues if i.kind == "curvature_jump"
             and i.waterline_z == pytest.approx(4.4423, rel=1e-3)
             and 0.8 * LPP < i.station_x < 0.9 * LPP]
    assert jumps, rep.summary()


def test_slope_kink_flagged_as_curvature_jump():
    table = planted_kink(synthetic_parabola())
    rep = check_fairness(table)
    jumps = [i for i in rep.issues if i.kind == "curvature_jump"
             and 0.6 * table.lpp < i.station_x < 0.8 * table.lpp]
    assert jumps, rep.summary()


def planted_kink(table: OffsetsTable) -> OffsetsTable:
    s = np.array(table.stations, dtype=float)
    y = np.array(table.half_breadths, dtype=float)
    ramp = np.where(s >= s[28], 0.15 * (s - s[28]), 0.0)
    y += ramp[:, None]
    return OffsetsTable(lpp=table.lpp, beam=table.beam, stations=s,
                        waterlines=np.array(table.waterlines, dtype=float),
                        half_breadths=y)


def test_lobe_break_flagged_as_non_monotonic():
    # dent the plateau of an in-band waterline: after the peak the
    # waterline must not step back AWAY from the maximum
    def dip(s, y):
        y[10, 19] -= 0.05 * BEAM  # z ~ 12.06 m >= 0.5 * draft

    rep = check_fairness(planted(dip), z_limit=DRAFT)
    mono = [i for i in rep.issues if i.kind == "non_monotonic"
            and i.waterline_z == pytest.approx(12.0577, rel=1e-3)]
    assert mono, rep.summary()


def test_parallel_body_wobble_flagged():
    # a dent SMALL enough to stay inside the loose run window
    # (0.004 * ymax ~ 0.09 m) yet far beyond the tight wobble limit
    # (0.0005 * B = 0.0225 m)
    def dent(s, y):
        y[11, 8] -= 0.06

    rep = check_fairness(planted(dent), z_limit=DRAFT)
    kinds = [i.kind for i in rep.issues]
    assert "parallel_wobble" in kinds, rep.summary()


def test_smooth_bulb_below_half_draft_not_flagged():
    # a fair bulb is smooth: a broad, low bump on a LOW waterline must
    # pass both the curvature and (by design scope) the lobe check.
    # r=2 -> z=1.27 m, a realistic bulb height, and the only rows with
    # headroom below B/2 (the sides are vertical from ~0.1 draft up).
    def bulb(s, y):
        r = 2
        bump = 0.6 * np.exp(-((s - 0.9 * LPP) / (2 * _dx(s))) ** 2)
        y[:, r] += bump

    rep = check_fairness(planted(bulb), z_limit=DRAFT)
    assert rep.ok, rep.summary()


# ---------------------------------------------------------------------------
# scope plumbing
# ---------------------------------------------------------------------------


def test_z_limit_narrows_the_judged_rows():
    rep = check_fairness(series60(), z_limit=8.0)
    assert rep.n_waterlines_checked == 13  # z = 0 .. 7.615 <= 8.0
    assert rep.issues == ()


def test_invalid_z_limit_raises():
    with pytest.raises(ValueError, match="z_limit"):
        check_fairness(series60(), z_limit=-1.0)
    with pytest.raises(ValueError, match="z_limit"):
        check_fairness(series60(), z_limit=float("nan"))


def test_issue_dataclass_holds_position_and_metric():
    rep = check_fairness(planted_kink(synthetic_parabola()))
    assert rep.issues
    issue = next(i for i in rep.issues if i.kind == "curvature_jump")
    assert isinstance(issue, FairnessIssue)
    assert 0.0 <= issue.station_x <= table_lpp_kink()
    assert issue.metric > issue.limit
    assert issue.detail


def table_lpp_kink() -> float:
    return 180.0
