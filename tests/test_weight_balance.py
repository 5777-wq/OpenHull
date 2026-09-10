"""Tests for the weight-buoyancy balance (plan task 1.3).

Two independent validation layers, per the anti-overfit requirement:

* Method layer (zero circularity): the worked example of Xie Yunping,
  Ship Design Principles, section 2.2.2 - a 35,000 t bulk carrier whose
  parent (39,800 t deadweight, steel 8,295 t) yields steel weights of
  7,384 t (cubic modulus) and 7,378 t (exponent regression).  These are
  published numbers, not our outputs.

* Calibration layer: the TB-001/JBC closed loop.  Coefficients are
  calibrated to the owner-approved JBC neighbourhood (declared
  circularity, same as task 1.2) and must reproduce the displacement
  anchor 182,829.1 t within 1 % while converging per the Eq.(3-27)
  criterion |W-B|/W <= 0.1 %.
"""

import json

import pytest

from openhull import (
    BULK_CARRIER_STEEL_EXPONENTS,
    ComponentWeightParameters,
    DEFAULT_WEIGHT_ALGORITHM,
    RatioParameters,
    ShipSpec,
    SpecValidationError,
    WEIGHT_ALGORITHMS,
    bulkcarrier_deadweight_ratio_statistics,
    knots_to_ms,
    solve_weight_balance,
    steel_cubic_coefficient_from_parent,
    steel_exponent_coefficient_from_parent,
)

#: JBC full-load displacement anchor, t (DATA_SOURCES.md: 178,369.9 m3 x 1.025)
ANCHOR_DISPLACEMENT_T = 178369.9 * 1.025


def task_book_spec() -> ShipSpec:
    """TB-001 requirements only - no dimensions known yet."""
    return ShipSpec(
        ship_type="bulk_carrier",
        deadweight=149920.0,
        service_speed=knots_to_ms(14.5),
        cb=0.8580,
    )


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


def test_registry_contains_approved_algorithms():
    assert set(WEIGHT_ALGORITHMS) == {
        "deadweight_ratio",
        "component_cubic",
        "component_exponent",
    }
    assert DEFAULT_WEIGHT_ALGORITHM == "component_cubic"
    for info in WEIGHT_ALGORITHMS.values():
        assert info.citation and info.applicability


def test_unknown_algorithm_id_raises_with_registry_listing():
    with pytest.raises(SpecValidationError) as excinfo:
        solve_weight_balance(task_book_spec(), "magic_lightship")
    message = str(excinfo.value)
    assert "unknown lightweight algorithm id" in message
    assert "component_cubic" in message


# ---------------------------------------------------------------------------
# method layer: Xie Yunping worked example (published numbers)
# ---------------------------------------------------------------------------


def test_example_cubic_modulus_reproduces_7384t():
    """Xie section 2.2.2: parent C_H3 = 0.09218 -> new ship W_H = 7384 t."""
    c_h3 = steel_cubic_coefficient_from_parent(185.0, 32.0, 15.2, 8295.0)
    assert c_h3 == pytest.approx(0.092183, rel=1e-4)
    steel = c_h3 * 178.0 * 30.0 * 15.0
    assert steel == pytest.approx(7384.0, abs=1.0)


def test_example_exponent_reproduces_7378t():
    """Xie section 2.2.2: Table 2-4 exponents -> new ship W_H = 7378 t."""
    c_h5 = steel_exponent_coefficient_from_parent(
        185.0, 32.0, 15.2, 10.0, 0.825, 8295.0, BULK_CARRIER_STEEL_EXPONENTS
    )
    assert c_h5 == pytest.approx(0.049753, rel=1e-3)
    a, b, c, d, e = BULK_CARRIER_STEEL_EXPONENTS
    steel = c_h5 * 178.0**a * 30.0**b * 15.0**c * 10.0**d * 0.815**e
    assert steel == pytest.approx(7378.0, abs=1.0)


def test_example_statistical_formula_value_for_reference():
    """Xie Eq.(2-24) checks K and the 6480 t value the book itself doubts."""
    k = 10.75 - ((300.0 - 178.0) / 100.0) ** 1.5
    assert k == pytest.approx(9.402, abs=5e-4)
    steel = 3.90 * k * 178.0**2 * 30.0 * (0.815 + 0.7) * 1e-4 + 1200.0
    assert steel == pytest.approx(6480.0, abs=1.0)


# ---------------------------------------------------------------------------
# guarded statistical regression
# ---------------------------------------------------------------------------


def test_bulkcarrier_eta_regression_matches_source():
    """Xie Eq.(2-5) at DW = 10,000 t: 0.734 + 0.02839 - 0.00221."""
    assert bulkcarrier_deadweight_ratio_statistics(10000.0) == pytest.approx(
        0.7602, abs=1e-4
    )


def test_bulkcarrier_eta_regression_refuses_out_of_band():
    """TB-001 (149,920 t) is far outside the 5,000-60,000 t population."""
    with pytest.raises(SpecValidationError) as excinfo:
        bulkcarrier_deadweight_ratio_statistics(149920.0)
    message = str(excinfo.value)
    assert "5,000-60,000 t" in message
    assert "refuses" in message
    with pytest.raises(SpecValidationError):
        bulkcarrier_deadweight_ratio_statistics(4000.0)


# ---------------------------------------------------------------------------
# calibration layer: TB-001 / JBC closed loop
# ---------------------------------------------------------------------------


def test_tb001_component_cubic_converges_and_reproduces_anchor():
    result = solve_weight_balance(task_book_spec())
    assert result.converged is True
    assert result.algorithm_id == "component_cubic"
    # deterministic loop: converges on pass 3 (0.018 % final imbalance)
    assert result.iterations == 3
    assert result.imbalance_ratio <= 0.001
    # acceptance: JBC displacement reproduced within 1 %
    assert abs(result.displacement_t - ANCHOR_DISPLACEMENT_T) / ANCHOR_DISPLACEMENT_T < 0.01
    # chain values at the converged displacement (pinned, drift = number)
    assert result.lpp == pytest.approx(271.6, rel=0.005)
    assert result.beam == pytest.approx(45.27, rel=0.005)
    assert result.draft == pytest.approx(16.77, rel=0.005)
    assert result.depth == pytest.approx(24.25, rel=0.005)


def test_tb001_lightweight_split_matches_table_2_3_share():
    result = solve_weight_balance(task_book_spec())
    breakdown = result.steps[-1].lightweight
    assert breakdown.total_t == pytest.approx(result.lightship_t)
    # machinery is exactly the Table 2-3 residual share of LW
    assert breakdown.machinery_t == pytest.approx(
        0.155 * breakdown.total_t, rel=1e-9
    )
    assert (
        breakdown.steel_t + breakdown.outfit_t + breakdown.machinery_t
        == pytest.approx(breakdown.total_t, rel=1e-9)
    )


def test_tb001_norman_coefficient_sane():
    result = solve_weight_balance(task_book_spec())
    assert result.norman_coefficient is not None
    assert result.norman_coefficient > 1.0  # Lin Yan: N is always > 1
    assert result.norman_coefficient == pytest.approx(1.16, abs=0.01)


def test_tb001_audit_trail_starts_from_deadweight_ratio():
    result = solve_weight_balance(task_book_spec())
    assert len(result.steps) == result.iterations
    first = result.steps[0]
    assert first.iteration == 1
    assert first.displacement_in_t == pytest.approx(149920.0 / 0.82)
    assert first.lpp == pytest.approx(272.4, rel=0.002)  # 1.2 chain at Delta_0
    imbalances = [s.imbalance_ratio for s in result.steps]
    assert all(
        later <= earlier for earlier, later in zip(imbalances, imbalances[1:])
    )


def test_tb001_exact_parent_ratios_close_in_one_pass():
    """With JBC's own proportions the loop is an identity at pass 1."""
    result = solve_weight_balance(
        task_book_spec(),
        ratios=RatioParameters(
            l_over_b=280.0 / 45.0,
            b_over_t=45.0 / 16.5,
            l_over_depth=280.0 / 25.0,
        ),
    )
    assert result.iterations == 1
    assert result.displacement_t == pytest.approx(149920.0 / 0.82, abs=2.0)
    assert result.lpp == pytest.approx(280.0, rel=1e-4)
    assert result.beam == pytest.approx(45.0, rel=1e-4)
    assert result.draft == pytest.approx(16.5, rel=1e-4)


def test_tb001_component_exponent_converges_within_tolerance():
    result = solve_weight_balance(
        task_book_spec(), "component_exponent"
    )
    assert result.converged is True
    assert result.iterations <= 5
    assert abs(result.displacement_t - ANCHOR_DISPLACEMENT_T) / ANCHOR_DISPLACEMENT_T < 0.01


def test_deadweight_ratio_algorithm_is_the_starting_estimate():
    """LW = DW*(1-eta)/eta, Xie Eq.(2-4): closes without iteration."""
    result = solve_weight_balance(task_book_spec(), "deadweight_ratio")
    assert result.converged is True
    assert result.iterations == 1
    assert result.displacement_t == pytest.approx(149920.0 / 0.82)
    assert result.lightship_t == pytest.approx(149920.0 * 0.18 / 0.82)
    assert result.norman_coefficient is None  # no component split available
    assert result.lpp == pytest.approx(272.4, rel=0.005)


def test_lightship_margin_increases_displacement():
    """Margin shift must match the fixed point AND exhibit N > 1 (Lin Yan
    section 4.3.4: the displacement increment always exceeds the added
    weight increment, because the lightship itself grows with Delta)."""
    base = solve_weight_balance(task_book_spec())
    margined = solve_weight_balance(
        task_book_spec(),
        parameters=ComponentWeightParameters(lightship_margin_ratio=0.02),
    )
    assert margined.lightship_with_margin_t == pytest.approx(
        margined.lightship_t * 1.02, rel=1e-12
    )
    # closed-form fixed points: Delta = DW / (1 - a) and DW / (1 - 1.02*a)
    # with a = LW / Delta of the base equilibrium
    a = base.lightship_t / base.displacement_t
    dw = base.deadweight_t
    expected_margined = dw / (1.0 - 1.02 * a)
    assert margined.displacement_t == pytest.approx(expected_margined, rel=1e-4)
    shift = margined.displacement_t - base.displacement_t
    assert shift > 0.02 * base.lightship_t  # Norman amplification, N > 1


# ---------------------------------------------------------------------------
# failure modes refuse loudly (AGENTS.md section 6)
# ---------------------------------------------------------------------------


def test_nonconvergence_raises_instead_of_returning_numbers():
    with pytest.raises(RuntimeError) as excinfo:
        solve_weight_balance(
            task_book_spec(),
            parameters=ComponentWeightParameters(
                tolerance=1e-6, max_iterations=2
            ),
        )
    message = str(excinfo.value)
    assert "did not converge" in message
    assert "refusing" in message


def test_missing_deadweight_raises_with_explanation():
    spec = ShipSpec(service_speed=knots_to_ms(14.5), cb=0.858)
    with pytest.raises(SpecValidationError) as excinfo:
        solve_weight_balance(spec)
    assert excinfo.value.field == "deadweight"
    assert "Delta = DW + LW" in str(excinfo.value)


def test_nonsense_coefficients_raise_with_band():
    with pytest.raises(SpecValidationError) as excinfo:
        ComponentWeightParameters(machinery_share=0.9)
    assert excinfo.value.field == "machinery_share"
    with pytest.raises(SpecValidationError):
        ComponentWeightParameters(steel_cubic_coefficient=1.0)


# ---------------------------------------------------------------------------
# agent-facing contract (AGENTS.md section 8)
# ---------------------------------------------------------------------------


def test_result_is_json_serializable():
    result = solve_weight_balance(task_book_spec())
    payload = json.dumps(result.to_dict())  # must not raise
    loaded = json.loads(payload)
    assert loaded["displacement_t"] == pytest.approx(result.displacement_t)
    assert loaded["converged"] is True
    assert loaded["steps"][0]["lightweight"]["steel_t"] > 0
    assert loaded["norman_coefficient"] == pytest.approx(
        result.norman_coefficient
    )


# ---------------------------------------------------------------------------
# calibration provenance pins
# ---------------------------------------------------------------------------


def test_default_eta_inside_cross_book_statistics_band():
    """Lin Yan Table 4-3: double-hull bulk carrier eta_DW = 0.78-0.86.

    Cross-book corroboration of the owner-approved 0.82 (Xie Eq.(2-5)
    peaks at ~0.825 near its 60,000 t bound - same trend, see module
    docstring).  This test pins that the default never drifts outside
    the published band silently.
    """
    assert 0.78 <= ComponentWeightParameters().deadweight_ratio <= 0.86


def test_default_coefficients_match_declared_parent_split():
    """Defaults = JBC-neighbourhood split (Table 2-3 mids), see docstring."""
    params = ComponentWeightParameters()
    steel = params.steel_cubic_coefficient * 280.0 * 45.0 * 25.0
    outfit = params.outfit_area_coefficient * 280.0 * 45.0
    lightship = 149920.0 * (1.0 - 0.82) / 0.82
    assert steel == pytest.approx(0.645 * lightship, rel=1e-3)
    assert outfit == pytest.approx(0.20 * lightship, rel=1e-3)
