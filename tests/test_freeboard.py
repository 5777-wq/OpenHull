"""Tests for the freeboard check (plan task 1.6).

The rule table (Lin Yan Table 3-9, transcribing ICLL 1966) was visually
verified against the scanned original before implementation (PDF part 1
page 71, book page 60).  Tests pin: the JBC table row, interpolation,
every correction term against hand-computed values, and the TB-001
verdict (actual freeboard 8.5 m = D - T against the computed minimum).
"""

import json

import pytest

from openhull import (
    FreeboardResult,
    SpecValidationError,
    TABLE_3_9_BASIC_FREEBOARD,
    minimum_freeboard,
    tabular_basic_freeboard,
)

# ---------------------------------------------------------------------------
# table integrity
# ---------------------------------------------------------------------------


def test_table_jbc_row_pins_the_anchor():
    assert TABLE_3_9_BASIC_FREEBOARD[280] == (3176, 4397)
    assert tabular_basic_freeboard(280.0, "A") == 3176.0
    assert tabular_basic_freeboard(280.0, "B") == 4397.0


def test_table_endpoints():
    assert TABLE_3_9_BASIC_FREEBOARD[24] == (200, 200)
    assert TABLE_3_9_BASIC_FREEBOARD[365] == (3433, 5303)


def test_table_monotone_and_type_b_not_lighter():
    """Data integrity: freeboard grows with length; type B is never
    below type A (equal up to 60 m, larger from 70 m on)."""
    lengths = sorted(TABLE_3_9_BASIC_FREEBOARD)
    for lo, hi in zip(lengths, lengths[1:]):
        for column in (0, 1):
            assert TABLE_3_9_BASIC_FREEBOARD[lo][column] <= (
                TABLE_3_9_BASIC_FREEBOARD[hi][column]
            )
    for length in lengths:
        a, b = TABLE_3_9_BASIC_FREEBOARD[length]
        assert b >= a
    _, (a70, b70) = (70, TABLE_3_9_BASIC_FREEBOARD[70])
    assert b70 > a70  # the two columns separate from 70 m on


def test_interpolation_midpoint():
    """L = 285 m: halfway between the 280 and 290 m rows."""
    expected = (4397 + 4513) / 2.0
    assert tabular_basic_freeboard(285.0, "B") == pytest.approx(expected)


def test_length_outside_table_refuses():
    with pytest.raises(SpecValidationError):
        tabular_basic_freeboard(370.0, "B")
    with pytest.raises(SpecValidationError):
        tabular_basic_freeboard(20.0, "A")


def test_unknown_ship_type_refuses():
    with pytest.raises(SpecValidationError):
        tabular_basic_freeboard(280.0, "C")


# ---------------------------------------------------------------------------
# corrections, each hand-checked against its equation
# ---------------------------------------------------------------------------


def test_f1_only_for_short_b_ships_short_of_superstructure():
    """Eq.(3-16): 7.5*(100-L)*(0.35-E/L) = 11.25 mm at L=90, E/L=0.2."""
    result = minimum_freeboard(
        90.0, "B", depth_s=6.0, cb_at_085d=0.68,
        actual_freeboard_mm=800.0, superstructure_ratio=0.2,
    )
    assert result.f1 == pytest.approx(11.25, abs=1e-9)
    # type A: no f1; B with E/L >= 0.35: no f1 either
    type_a = minimum_freeboard(
        90.0, "A", depth_s=6.0, cb_at_085d=0.68,
        actual_freeboard_mm=800.0, superstructure_ratio=0.2,
    )
    assert type_a.f1 == 0.0
    long_ship = minimum_freeboard(
        280.0, "B", depth_s=25.0, cb_at_085d=0.68,
        actual_freeboard_mm=8500.0, superstructure_ratio=0.2,
    )
    assert long_ship.f1 == 0.0


def test_f2_block_coefficient_correction():
    """Eq.(3-17) at L=280, B: (4397)*((0.858+0.68)/1.36 - 1)."""
    result = minimum_freeboard(
        280.0, "B", depth_s=18.6, cb_at_085d=0.858,
        actual_freeboard_mm=8500.0,
    )
    expected = 4397.0 * ((0.858 + 0.68) / 1.36 - 1.0)
    assert result.f2 == pytest.approx(expected, rel=1e-12)
    # standard-ship Cb = 0.68: no correction
    neutral = minimum_freeboard(
        280.0, "B", depth_s=18.6, cb_at_085d=0.68,
        actual_freeboard_mm=8500.0,
    )
    assert neutral.f2 == 0.0


def test_f3_depth_correction_applies_only_above_standard():
    """Eq.(3-18): R = 250 for L >= 120; JBC: (25 - 280/15)*250."""
    result = minimum_freeboard(
        280.0, "B", depth_s=25.0, cb_at_085d=0.68,
        actual_freeboard_mm=8500.0,
    )
    assert result.f3 == pytest.approx((25.0 - 280.0 / 15.0) * 250.0)
    # Ds below L/15: no reduction, f3 stays 0
    shallow = minimum_freeboard(
        280.0, "B", depth_s=18.0, cb_at_085d=0.68,
        actual_freeboard_mm=3000.0,
    )
    assert shallow.f3 == 0.0
    assert shallow.minimum_freeboard_mm == pytest.approx(4397.0)


def test_f4_superstructure_reduces_freeboard():
    """Eq.(3-19): full-length superstructure at L=280 gives f0 = -1070;
    half the length picks k = 32 % (Table 3-11, B column I)."""
    full = minimum_freeboard(
        280.0, "B", depth_s=25.0, cb_at_085d=0.68,
        actual_freeboard_mm=8500.0, superstructure_ratio=1.0,
    )
    assert full.f4 == pytest.approx(-1070.0)
    half = minimum_freeboard(
        280.0, "B", depth_s=25.0, cb_at_085d=0.68,
        actual_freeboard_mm=8500.0, superstructure_ratio=0.5,
    )
    assert half.f4 == pytest.approx(-0.32 * 1070.0)


def test_f5_sheer_deficit_increases_freeboard():
    """Eq.(3-20): 0.5*(W+U)*(0.75 - S/(2L)) with S = 0."""
    result = minimum_freeboard(
        280.0, "B", depth_s=25.0, cb_at_085d=0.68,
        actual_freeboard_mm=8500.0,
        sheer_difference_w=100.0, sheer_difference_u=150.0,
    )
    assert result.f5 == pytest.approx(0.5 * 250.0 * 0.75)


# ---------------------------------------------------------------------------
# TB-001 verdict
# ---------------------------------------------------------------------------


def test_tb001_freeboard_verdict():
    """TB-001: actual freeboard 8.5 m = D - T; the plain type-B minimum
    lands near 6.56 m with the declared approximations."""
    result = minimum_freeboard(
        280.0, "B", depth_s=25.0, cb_at_085d=0.858,
        actual_freeboard_mm=8500.0,
    )
    assert result.f0 == 4397.0
    assert result.minimum_freeboard_mm == pytest.approx(6555.8, abs=1.0)
    assert result.verdict == "PASS"
    assert result.margin_mm == pytest.approx(
        8500.0 - result.minimum_freeboard_mm
    )
    assert "flush deck assumed" in " ".join(result.assumptions)


def test_failing_verdict_is_reported_not_hidden():
    result = minimum_freeboard(
        280.0, "B", depth_s=25.0, cb_at_085d=0.858,
        actual_freeboard_mm=5000.0,
    )
    assert result.verdict == "FAIL"
    assert result.margin_mm < 0.0


def test_result_is_json_serializable():
    result = minimum_freeboard(
        280.0, "B", depth_s=25.0, cb_at_085d=0.858,
        actual_freeboard_mm=8500.0,
    )
    loaded = json.loads(json.dumps(result.to_dict()))
    assert loaded["minimum_freeboard_mm"] == pytest.approx(
        result.minimum_freeboard_mm
    )
    assert loaded["verdict"] == "PASS"


def test_nonphysical_inputs_refuse():
    with pytest.raises(SpecValidationError):
        minimum_freeboard(
            280.0, "B", depth_s=-1.0, cb_at_085d=0.858,
            actual_freeboard_mm=8500.0,
        )
    with pytest.raises(SpecValidationError):
        minimum_freeboard(
            280.0, "B", depth_s=25.0, cb_at_085d=1.2,
            actual_freeboard_mm=8500.0,
        )
    with pytest.raises(SpecValidationError):
        minimum_freeboard(
            280.0, "B", depth_s=25.0, cb_at_085d=0.858,
            actual_freeboard_mm=8500.0, superstructure_ratio=1.5,
        )
