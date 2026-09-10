"""Tests for hydrostatics by numerical integration (plan task 1.4).

Three layers, acceptance numbers reported separately per AGENTS.md
section 4:

* integrator self-proof: Simpson/trapezoid against closed-form
  integrals, and a box hull whose hydrostatics are known in closed form;
* JBC anchors at the design draft (task book TB-001): displacement
  volume +-1 %, KM +-2 % (18.59 m from NMRI GM + KG), Cb +-0.005,
  LCB +2.5475 %Lpp (fitted hull, discretization compensated);
* definition identities: TPC, MTC, KM = KB + BMT, Cp = Cb/Cm,
  Archimedes.
"""

import dataclasses
import json

import numpy as np
import pytest

from openhull import (
    OffsetsTable,
    SEAWATER_DENSITY,
    SpecValidationError,
    bonjean_areas,
    hydrostatics_at,
    hydrostatics_table,
    jbc_parent_offsets,
    simpson,
    trapezoid,
)

LPP, BEAM, DRAFT = 280.0, 45.0, 16.5
KM_ANCHOR = 18.59  # [NMRI] GM 5.30 m + KG 13.29 m, full load
GRAD_ANCHOR = 178369.9  # [NMRI] m3


@pytest.fixture(scope="module")
def jbc():
    """One fitted JBC parent + its design-draft hydrostatics (slow fit)."""
    table = jbc_parent_offsets(lpp=LPP, beam=BEAM, draft=DRAFT)
    return table, hydrostatics_at(table, DRAFT)


def box_table(lpp=LPP, beam=BEAM, draft=DRAFT) -> OffsetsTable:
    """Rectangular barge: closed-form hydrostatics for every quantity."""
    stations = np.linspace(0.0, lpp, 21)
    waterlines = np.linspace(0.0, draft, 33)
    y = np.full((21, 33), beam / 2.0)
    return OffsetsTable(
        lpp=lpp, beam=beam, stations=stations,
        waterlines=waterlines, half_breadths=y,
    )


# ---------------------------------------------------------------------------
# integrator kernels
# ---------------------------------------------------------------------------


def test_simpson_is_exact_for_cubics():
    """Integral of x^3 over [0, 2] is 4; Simpson reproduces it exactly."""
    assert simpson(np.array([0.0, 1.0, 8.0]), 1.0) == pytest.approx(4.0)
    x = np.linspace(0.0, 2.0, 9)
    assert simpson(x**3, x[1] - x[0]) == pytest.approx(4.0)


def test_simpson_requires_even_intervals():
    with pytest.raises(SpecValidationError) as excinfo:
        simpson(np.array([1.0, 2.0, 3.0, 4.0]), 1.0)
    assert "even number of intervals" in str(excinfo.value)


def test_simpson_beats_trapezoid_by_orders():
    """Integral of sin over [0, pi]: Simpson error far below trapezoid."""
    x = np.linspace(0.0, np.pi, 21)
    h = x[1] - x[0]
    err_trap = abs(trapezoid(np.sin(x), h) - 2.0)
    err_simp = abs(simpson(np.sin(x), h) - 2.0)
    assert err_simp < err_trap / 100.0


# ---------------------------------------------------------------------------
# offsets container validation
# ---------------------------------------------------------------------------


def test_offsets_table_rejects_transposed_matrix():
    stations = np.linspace(0.0, LPP, 21)
    waterlines = np.linspace(0.0, DRAFT, 33)
    with pytest.raises(SpecValidationError) as excinfo:
        OffsetsTable(
            lpp=LPP, beam=BEAM, stations=stations, waterlines=waterlines,
            half_breadths=np.zeros((33, 21)),
        )
    assert "one row per station" in str(excinfo.value)


def test_offsets_table_rejects_negative_half_breadth():
    stations = np.linspace(0.0, LPP, 21)
    waterlines = np.linspace(0.0, DRAFT, 33)
    y = np.full((21, 33), 1.0)
    y[3, 5] = -0.1
    with pytest.raises(SpecValidationError) as excinfo:
        OffsetsTable(
            lpp=LPP, beam=BEAM, stations=stations, waterlines=waterlines,
            half_breadths=y,
        )
    assert "cannot be negative" in str(excinfo.value)


def test_offsets_table_rejects_even_intervals():
    stations = np.linspace(0.0, LPP, 20)  # 19 intervals: odd -> rejected
    waterlines = np.linspace(0.0, DRAFT, 33)
    with pytest.raises(SpecValidationError) as excinfo:
        OffsetsTable(
            lpp=LPP, beam=BEAM, stations=stations, waterlines=waterlines,
            half_breadths=np.zeros((20, 33)),
        )
    assert "even interval count" in str(excinfo.value)


# ---------------------------------------------------------------------------
# closed-form hulls (integrator self-proof)
# ---------------------------------------------------------------------------


def test_box_hull_matches_closed_forms():
    """Barge: every hydrostatic quantity has a textbook closed form."""
    h = hydrostatics_at(box_table(), DRAFT)
    assert h.displacement_volume == pytest.approx(LPP * BEAM * DRAFT)
    assert h.displacement == pytest.approx(SEAWATER_DENSITY * LPP * BEAM * DRAFT)
    assert h.aw == pytest.approx(LPP * BEAM)
    assert h.kb == pytest.approx(DRAFT / 2.0)
    assert h.bmt == pytest.approx(BEAM**2 / (12.0 * DRAFT))
    assert h.bml == pytest.approx(LPP**2 / (12.0 * DRAFT))
    assert h.cb == pytest.approx(1.0)
    assert h.cm == pytest.approx(1.0)
    assert h.cw == pytest.approx(1.0)
    assert h.cp == pytest.approx(1.0)
    assert h.lcb == pytest.approx(0.0, abs=1e-9)
    assert h.lcf == pytest.approx(0.0, abs=1e-9)


def test_parabolic_hull_block_coefficient_is_two_thirds():
    """g = 1-(2xi-1)^2: Simpson is exact, so Cb = integral g = 2/3."""
    stations = np.linspace(0.0, LPP, 21)
    waterlines = np.linspace(0.0, DRAFT, 33)
    xi = stations / LPP
    g = 1.0 - (2.0 * xi - 1.0) ** 2
    y = (BEAM / 2.0) * np.tile(g[:, None], (1, 33))
    table = OffsetsTable(
        lpp=LPP, beam=BEAM, stations=stations, waterlines=waterlines,
        half_breadths=y,
    )
    h = hydrostatics_at(table, DRAFT)
    assert h.cb == pytest.approx(2.0 / 3.0, rel=1e-9)
    assert h.kb == pytest.approx(DRAFT / 2.0, rel=1e-9)
    assert h.lcb == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# JBC anchors at the design draft (separately reported, AGENTS.md 4)
# ---------------------------------------------------------------------------


def test_jbc_displacement_volume_within_one_percent(jbc):
    _, h = jbc
    assert abs(h.displacement_volume - GRAD_ANCHOR) / GRAD_ANCHOR < 0.01
    # regression pin (drift must show up as a number)
    assert h.displacement_volume == pytest.approx(178741.5, rel=5e-4)


def test_jbc_block_coefficient_within_tolerance(jbc):
    _, h = jbc
    assert abs(h.cb - 0.8580) < 0.005


def test_jbc_km_within_two_percent(jbc):
    _, h = jbc
    assert abs(h.km - KM_ANCHOR) / KM_ANCHOR < 0.02
    assert h.km == pytest.approx(KM_ANCHOR, abs=0.01)


def test_jbc_lcb_reproduced(jbc):
    _, h = jbc
    assert h.lcb == pytest.approx(2.5475, abs=0.02)


def test_jbc_lcb_fwd_of_midship_per_container(jbc):
    """Container field is % Lpp forward positive, like the task book."""
    _, h = jbc
    assert h.lcb > 0.0
    assert -6.0 < h.lcf < 6.0  # sanity band of ShipSpec


# ---------------------------------------------------------------------------
# definition identities
# ---------------------------------------------------------------------------


def test_km_is_kb_plus_bmt(jbc):
    _, h = jbc
    assert h.km == pytest.approx(h.kb + h.bmt, rel=1e-12)


def test_tpc_definition(jbc):
    _, h = jbc
    assert h.tpc == pytest.approx(SEAWATER_DENSITY * h.aw / 100.0, rel=1e-12)


def test_mtc_definition(jbc):
    _, h = jbc
    assert h.mtc == pytest.approx(
        h.displacement * h.bml / (100.0 * LPP), rel=1e-9
    )


def test_cp_is_cb_over_cm(jbc):
    _, h = jbc
    assert h.cp == pytest.approx(h.cb / h.cm, rel=1e-12)


def test_archimedes(jbc):
    _, h = jbc
    assert h.displacement == pytest.approx(
        SEAWATER_DENSITY * h.displacement_volume, rel=1e-12
    )


# ---------------------------------------------------------------------------
# table, bonjean interface, JSON contract
# ---------------------------------------------------------------------------


def test_hydrostatics_table_across_drafts(jbc):
    table, single = jbc
    drafts = [4.125, 8.25, 12.375, 16.5]
    ht = hydrostatics_table(table, drafts)
    assert len(ht.entries) == 4
    row = ht.at(16.5)
    assert row.displacement_volume == pytest.approx(
        single.displacement_volume, rel=1e-12
    )
    # the fitted hull is slimmer towards the keel: Cb grows with draft
    cbs = [e.cb for e in ht.entries]
    assert all(b > a for a, b in zip(cbs, cbs[1:]))


def test_bonjean_interface(jbc):
    table, h = jbc
    levels, areas = bonjean_areas(table)
    assert levels.size == areas.shape[1]
    assert areas[10, 0] == 0.0  # nothing above the keel at the keel line
    amid = areas[10, -1]
    assert amid == pytest.approx(0.9981 * BEAM * DRAFT, rel=5e-3)
    # cross-flux: volume from Bonjean equals the waterline-path volume
    grad_bonjean = simpson(
        areas[:, -1], float(table.stations[1] - table.stations[0])
    )
    assert grad_bonjean == pytest.approx(h.displacement_volume, rel=1e-4)


def test_hydrostatics_is_json_serializable(jbc):
    _, h = jbc
    payload = json.dumps(dataclasses.asdict(h))
    loaded = json.loads(payload)
    assert loaded["displacement_volume"] == pytest.approx(
        h.displacement_volume
    )


# ---------------------------------------------------------------------------
# guards
# ---------------------------------------------------------------------------


def test_draft_above_deepest_waterline_refuses(jbc):
    table, _ = jbc
    with pytest.raises(SpecValidationError) as excinfo:
        hydrostatics_at(table, DRAFT + 0.001)
    assert "deepest waterline" in str(excinfo.value)


def test_nonpositive_density_refuses(jbc):
    table, _ = jbc
    with pytest.raises(SpecValidationError) as excinfo:
        hydrostatics_at(table, DRAFT, density=0.0)
    assert excinfo.value.field == "density"
