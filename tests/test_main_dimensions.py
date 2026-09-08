"""Tests for main-dimension estimation (plan task 1.2).

The acceptance case reverses the task-book deadweight back into
principal dimensions and compares against the JBC benchmark:
L, B, D within ±5 %, T via the chain (same ±5 % band), Cb pinned by the
task book. Chain-level values are asserted explicitly so any drift in
the math shows up as a number, not as a vague failure.
"""

import pytest

from openhull import (
    MAIN_DIMENSION_ALGORITHMS,
    DEFAULT_ALGORITHM,
    RatioParameters,
    ShipSpec,
    SpecValidationError,
    estimate_main_dimensions,
    knots_to_ms,
)


def task_book_spec() -> ShipSpec:
    """TB-001 requirements only — no dimensions known yet."""
    return ShipSpec(
        ship_type="bulk_carrier",
        deadweight=149920.0,
        service_speed=knots_to_ms(14.5),
        cb=0.8580,
    )


def jbc_parent() -> ShipSpec:
    """JBC dimensions as a parent ship (for the roundtrip test)."""
    return ShipSpec(
        lpp=280.0, beam=45.0, depth=25.0, draft=16.5, cb=0.8580,
        displacement_volume=178369.9,
    )


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


def test_registry_contains_approved_algorithms():
    assert set(MAIN_DIMENSION_ALGORITHMS) == {
        "deadweight_ratio_statistical",
        "parent_hull_ratio",
        "watson_1977",
    }
    assert DEFAULT_ALGORITHM == "deadweight_ratio_statistical"
    assert MAIN_DIMENSION_ALGORITHMS["watson_1977"].implemented is False
    for info in MAIN_DIMENSION_ALGORITHMS.values():
        assert info.citation and info.applicability


def test_unknown_algorithm_id_raises_with_registry_listing():
    with pytest.raises(SpecValidationError) as excinfo:
        estimate_main_dimensions(task_book_spec(), "magic_formula")
    message = str(excinfo.value)
    assert "unknown algorithm id" in message
    assert "deadweight_ratio_statistical" in message


# ---------------------------------------------------------------------------
# acceptance: deadweight_ratio_statistical reverses TB-001 into JBC
# ---------------------------------------------------------------------------


def test_acceptance_reverse_inference_within_tolerance():
    result = estimate_main_dimensions(task_book_spec())
    assert abs(result.lpp - 280.0) / 280.0 < 0.05
    assert abs(result.beam - 45.0) / 45.0 < 0.05
    assert abs(result.draft - 16.5) / 16.5 < 0.05
    assert abs(result.depth - 25.0) / 25.0 < 0.05
    assert result.cb == pytest.approx(0.8580)


def test_chain_exact_values():
    """Pin the closed-form chain: L = (grad*k1*k2^2/Cb)^(1/3)."""
    result = estimate_main_dimensions(task_book_spec())
    assert result.lpp == pytest.approx(272.4, rel=0.005)
    assert result.beam == pytest.approx(45.40, rel=0.005)
    assert result.draft == pytest.approx(16.81, rel=0.005)
    assert result.depth == pytest.approx(24.32, rel=0.005)
    # displacement consistency survives (validated again in ShipSpec)
    assert result.displacement == pytest.approx(
        result.displacement_volume * 1.025
    )


def test_result_spec_carries_requirements():
    result = estimate_main_dimensions(task_book_spec())
    assert result.deadweight == 149920.0
    assert result.service_speed == knots_to_ms(14.5)
    assert result.freeboard == pytest.approx(24.32 - 16.81, abs=0.05)


# ---------------------------------------------------------------------------
# parent_hull_ratio
# ---------------------------------------------------------------------------


def test_parent_hull_ratio_roundtrip_recovers_parent():
    """With the parent's own proportions the chain is an identity."""
    result = estimate_main_dimensions(
        task_book_spec(), "parent_hull_ratio", parent=jbc_parent()
    )
    assert result.lpp == pytest.approx(280.0, rel=1e-3)
    assert result.beam == pytest.approx(45.0, rel=1e-3)
    assert result.draft == pytest.approx(16.5, rel=1e-3)
    assert result.depth == pytest.approx(25.0, rel=1e-3)


def test_parent_hull_ratio_requires_parent():
    with pytest.raises(SpecValidationError) as excinfo:
        estimate_main_dimensions(task_book_spec(), "parent_hull_ratio")
    assert "parent" in str(excinfo.value)


def test_parent_hull_ratio_requires_parent_dimensions():
    with pytest.raises(SpecValidationError) as excinfo:
        estimate_main_dimensions(
            task_book_spec(), "parent_hull_ratio",
            parent=ShipSpec(lpp=280.0),
        )
    assert "proportions" in str(excinfo.value)


# ---------------------------------------------------------------------------
# guards
# ---------------------------------------------------------------------------


def test_missing_cb_raises_with_task_book_pin_advice():
    spec = ShipSpec(deadweight=149920.0, service_speed=knots_to_ms(14.5))
    with pytest.raises(SpecValidationError) as excinfo:
        estimate_main_dimensions(spec)
    message = str(excinfo.value)
    assert "watson_1977" in message
    assert "pin Cb in the task book" in message


def test_missing_service_speed_raises():
    with pytest.raises(SpecValidationError) as excinfo:
        estimate_main_dimensions(ShipSpec(deadweight=149920.0, cb=0.858))
    assert excinfo.value.field == "service_speed"


def test_froude_number_out_of_band_refuses():
    fast = ShipSpec(
        ship_type="bulk_carrier",
        deadweight=149920.0,
        service_speed=knots_to_ms(27.0),  # Fn ~ 0.27 on the estimated L
        cb=0.8580,
    )
    with pytest.raises(SpecValidationError) as excinfo:
        estimate_main_dimensions(fast)
    message = str(excinfo.value)
    assert "Fn" in message
    assert "full-form" in message


def test_invalid_ratio_override_raises():
    with pytest.raises(SpecValidationError) as excinfo:
        estimate_main_dimensions(task_book_spec(), l_over_b=12.0)
    assert excinfo.value.field == "l_over_b"


# ---------------------------------------------------------------------------
# registered placeholder
# ---------------------------------------------------------------------------


def test_watson_placeholder_raises_not_implemented():
    with pytest.raises(NotImplementedError) as excinfo:
        estimate_main_dimensions(task_book_spec(), "watson_1977")
    assert "not implemented" in str(excinfo.value)


def test_ratio_parameters_reject_nonsense():
    with pytest.raises(SpecValidationError):
        RatioParameters(b_over_t=0.5)
