"""Tests for the core data structures (plan task 1.1).

Covers the acceptance case (illegal values raise with an explanation),
the JBC benchmark values as a normal case, boundary values, and the
cross-field consistency checks. Error messages must contain the reason
whenever a validation fires — that is a task 1.1 requirement, so the
tests assert on message content, not just the exception type.
"""

import pytest

from openhull import (
    SEAWATER_DENSITY,
    Hydrostatics,
    HydrostaticsTable,
    ShipSpec,
    SpecValidationError,
    knots_to_ms,
    ms_to_knots,
)


def jbc_spec() -> ShipSpec:
    """A fully valid ShipSpec built from the JBC benchmark values."""
    return ShipSpec(
        ship_type="bulk_carrier",
        deadweight=149920.0,  # owner-approved assumption (task book TB-001)
        service_speed=knots_to_ms(14.5),
        lpp=280.0,
        beam=45.0,
        depth=25.0,
        draft=16.5,
        cb=0.8580,
        cm=0.9981,
        cwp=0.9,
        lcb=2.5475,
        displacement_volume=178369.9,
        displacement=SEAWATER_DENSITY * 178369.9,
    )


# ---------------------------------------------------------------------------
# normal case
# ---------------------------------------------------------------------------


def test_valid_jbc_spec_constructs():
    spec = jbc_spec()
    assert spec.lpp == 280.0
    assert spec.freeboard == pytest.approx(8.5)
    assert spec.cp == pytest.approx(0.8580 / 0.9981)
    assert spec.service_speed_kn == pytest.approx(14.5)


def test_partial_spec_task_book_only_constructs():
    spec = ShipSpec(deadweight=149920.0, service_speed=knots_to_ms(14.5))
    assert spec.lpp is None
    assert spec.freeboard is None


def test_knot_conversion_roundtrip():
    assert knots_to_ms(1.0) == pytest.approx(0.5144444)
    assert ms_to_knots(knots_to_ms(14.5)) == pytest.approx(14.5)


# ---------------------------------------------------------------------------
# boundary and invalid values — each must raise WITH an explanation
# ---------------------------------------------------------------------------


def test_cb_above_one_raises_with_formula_explanation():
    with pytest.raises(SpecValidationError) as excinfo:
        ShipSpec(lpp=280.0, beam=45.0, draft=16.5, cb=1.5)
    message = str(excinfo.value)
    assert excinfo.value.field == "cb"
    assert excinfo.value.value == 1.5
    # the reason must state the defining formula and the geometry behind it
    assert "displacement_volume / (Lpp * B * T)" in message
    assert "circumscribing" in message


def test_cb_of_exactly_one_is_allowed_box_boundary():
    ShipSpec(lpp=10.0, beam=5.0, draft=2.0, cb=1.0)  # rectangular box: legal


def test_cb_zero_and_negative_raise():
    for bad in (0.0, -0.1):
        with pytest.raises(SpecValidationError) as excinfo:
            ShipSpec(cb=bad)
        assert excinfo.value.field == "cb"


def test_cm_above_one_raises_with_area_explanation():
    with pytest.raises(SpecValidationError) as excinfo:
        ShipSpec(cm=1.2)
    message = str(excinfo.value)
    assert "Am / (B * T)" in message
    assert "rectangle" in message


def test_cwp_above_one_raises():
    with pytest.raises(SpecValidationError) as excinfo:
        ShipSpec(cwp=1.05)
    assert excinfo.value.field == "cwp"


def test_non_finite_cb_raises():
    with pytest.raises(SpecValidationError) as excinfo:
        ShipSpec(cb=float("nan"))
    assert "finite" in str(excinfo.value)


# ---------------------------------------------------------------------------
# cross-field consistency
# ---------------------------------------------------------------------------


def test_draft_at_or_above_depth_raises_with_freeboard_explanation():
    with pytest.raises(SpecValidationError) as excinfo:
        ShipSpec(depth=25.0, draft=26.0)
    message = str(excinfo.value)
    assert excinfo.value.field == "draft"
    assert "freeboard" in message


def test_deadweight_above_displacement_raises():
    with pytest.raises(SpecValidationError) as excinfo:
        ShipSpec(displacement=100000.0, deadweight=120000.0)
    message = str(excinfo.value)
    assert "LW + DW" in message


def test_displacement_not_matching_volume_raises_with_archimedes_reason():
    with pytest.raises(SpecValidationError) as excinfo:
        ShipSpec(displacement_volume=178369.9, displacement=150000.0)
    message = str(excinfo.value)
    assert "Archimedes" in message
    assert "rho" in message


def test_cb_inconsistent_with_dimensions_raises():
    with pytest.raises(SpecValidationError) as excinfo:
        ShipSpec(
            lpp=280.0, beam=45.0, draft=16.5,
            displacement_volume=178369.9, cb=0.5000,
        )
    message = str(excinfo.value)
    assert "disagree" in message


def test_lcb_outside_hull_raises():
    with pytest.raises(SpecValidationError) as excinfo:
        ShipSpec(lcb=75.0)
    assert "within the ship's length" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Hydrostatics containers
# ---------------------------------------------------------------------------


def jbc_hydrostatics(draft: float, volume_scale: float) -> Hydrostatics:
    return Hydrostatics(
        draft=draft,
        displacement_volume=178369.9 * volume_scale,
        displacement=SEAWATER_DENSITY * 178369.9 * volume_scale,
        aw=11700.0 * volume_scale,
        lcf=2.5,
        cb=0.8580,
        cm=0.9981,
        cp=0.8596,
        cw=0.9,
        kb=8.5,
        bmt=4.8,
        bml=210.0,
        tpc=118.0,
        mtc=1850.0,
    )


def test_valid_hydrostatics_and_km_property():
    record = jbc_hydrostatics(16.5, 1.0)
    assert record.km == pytest.approx(record.kb + record.bmt)


def test_kb_at_or_above_draft_raises_with_centroid_explanation():
    with pytest.raises(SpecValidationError) as excinfo:
        Hydrostatics(
            draft=10.0,
            displacement_volume=1000.0,
            displacement=1025.0,
            aw=100.0,
            lcf=0.0,
            cb=0.5,
            cm=0.9,
            cp=0.6,
            cw=0.8,
            kb=10.0,  # centroid of a submerged volume at the waterline
            bmt=1.0,
            bml=100.0,
            tpc=10.0,
            mtc=100.0,
        )
    assert "below the waterline" in str(excinfo.value)


def test_table_rejects_out_of_order_drafts():
    with pytest.raises(SpecValidationError) as excinfo:
        HydrostaticsTable(
            entries=[
                jbc_hydrostatics(10.0, 0.4),
                jbc_hydrostatics(16.5, 1.0),
                jbc_hydrostatics(14.0, 0.7),
            ]
        )
    assert "strictly increasing" in str(excinfo.value)


def test_table_lookup_at_tabulated_draft():
    table = HydrostaticsTable(
        entries=[jbc_hydrostatics(14.0, 0.7), jbc_hydrostatics(16.5, 1.0)]
    )
    assert table.at(16.5).draft == 16.5
    with pytest.raises(KeyError):
        table.at(12.0)
