"""Plan-0 draft-mismatch hint (owner-approved 2026-09-24).

When a task book declares a design draft the weight balance cannot
honour, the run says WHAT the declaration would need: the B/T that a
re-solve at the declared draft would require, under one explicitly
stated rule (hold displacement volume, Cb and L/B — L and B both
scale, so B/T ~ T^-1.5).  The rule is a HINT, never an automatic
re-design: the statistics, the guards and the balance are untouched.

Pinned here:

- the back-solve itself (identity at the current draft, the T^-1.5 law
  against an independent volume-based solve, non-positive refusal);
- the band verdict: the hint's band IS the chain-solve guard band, and
  the verdict is taken on the value the reader would type into a task
  book — a raw 3.5002 shown as "3.500" and called in-band must be a
  value the guard accepts (the N2/N3 floating-point lesson);
- the rendered report text in both states, and the JSON contract.
"""

import json

import pytest

from openhull import (
    B_OVER_T_BAND,
    RatioParameters,
    ShipSpec,
    SpecValidationError,
    estimate_main_dimensions,
    knots_to_ms,
    required_b_over_t_at_draft,
    solve_weight_balance,
)
from openhull.cli import main, run_taskbook
from openhull.report import write_report_md

TASKBOOK = """\
schema_version: 1
taskbook_id: DRAFT-HINT
ship_type: bulk_carrier
requirements:
  deadweight_t: 45000
  service_speed_kn: 16.0
  kg_m: 9.5
  drafts:
    design_draft_m: {draft}
constraints:
  block_coefficient_design: 0.80
"""

# 45,000 t / 16 kn / Cb 0.80 balances at T ~ 11.641 m, B/T = 2.700
DECLARED_MATCHING = 11.6    # |mismatch| = 0.041 m <= 5 cm: no hint
DECLARED_DEEPER = 12.5      # deeper than the balance: B/T must come down
DECLARED_SHALLOW = 9.0      # much shallower: B/T must grow out of band


def _run(tmp_path, draft: float):
    path = tmp_path / f"tb_{draft:.4f}.yaml"
    path.write_text(TASKBOOK.format(draft=draft), encoding="utf-8")
    return str(path), run_taskbook(str(path))


# ---------------------------------------------------------------------------
# the back-solve
# ---------------------------------------------------------------------------


def test_back_solve_is_the_identity_at_the_current_draft():
    assert required_b_over_t_at_draft(
        b_over_t=2.700, draft_m=11.641, target_draft_m=11.641
    ) == pytest.approx(2.700)


def test_back_solve_follows_the_t_minus_three_halves_law():
    # the numbers quoted in the R2 assessment: 14.672 m -> 16.5 m
    got = required_b_over_t_at_draft(
        b_over_t=2.700, draft_m=14.672, target_draft_m=16.5)
    assert got == pytest.approx(2.700 * (14.672 / 16.5) ** 1.5)
    assert got == pytest.approx(2.264, abs=0.001)


def test_back_solve_equals_an_explicit_volume_solve():
    """Independent check: solve grad = (L/B)*B^2*T*Cb for B at both
    drafts and compare the ratios — the closed form must agree with the
    volume relation it claims to invert."""
    grad, l_over_b, cb = 118_787.0, 6.0, 0.86
    t_now, t_target = 14.672, 16.5
    b_now = (grad / (l_over_b * t_now * cb)) ** 0.5
    b_target = (grad / (l_over_b * t_target * cb)) ** 0.5
    assert required_b_over_t_at_draft(
        b_over_t=b_now / t_now, draft_m=t_now, target_draft_m=t_target
    ) == pytest.approx(b_target / t_target)


def test_back_solve_refuses_a_non_positive_draft():
    with pytest.raises(SpecValidationError) as excinfo:
        required_b_over_t_at_draft(
            b_over_t=2.700, draft_m=11.641, target_draft_m=0.0)
    assert excinfo.value.field == "draft"


# ---------------------------------------------------------------------------
# the band is the chain-solve guard band, endpoints inclusive
# ---------------------------------------------------------------------------


def _jbc_spec() -> ShipSpec:
    return ShipSpec(
        ship_type="bulk_carrier",
        deadweight=149920.0,
        service_speed=knots_to_ms(14.5),
        cb=0.8580,
    )


@pytest.mark.parametrize("endpoint", B_OVER_T_BAND)
def test_hint_band_endpoints_pass_the_chains_own_guard(endpoint):
    """A ratio the hint calls acceptable must be one the chain accepts:
    the guard band is closed, so exactly 2.00 or 3.50 solves."""
    solved = estimate_main_dimensions(_jbc_spec(), b_over_t=endpoint)
    assert solved.beam / solved.draft == pytest.approx(endpoint)


def test_chain_refuses_just_outside_the_hint_band():
    with pytest.raises(SpecValidationError) as excinfo:
        estimate_main_dimensions(_jbc_spec(), b_over_t=B_OVER_T_BAND[1] + 0.1)
    assert "B/T" in str(excinfo.value)


# ---------------------------------------------------------------------------
# the run-level hint
# ---------------------------------------------------------------------------


def test_no_hint_when_the_declaration_matches_the_balance(tmp_path):
    _, summary = _run(tmp_path, DECLARED_MATCHING)
    assert summary["draft_mismatch_m"] is None
    assert summary["draft_mismatch_hint"] is None


def test_mismatch_hint_carries_the_back_solved_ratio(tmp_path):
    _, summary = _run(tmp_path, DECLARED_DEEPER)
    hint = summary["draft_mismatch_hint"]
    assert hint is not None
    assert hint["b_over_t_band"] == list(B_OVER_T_BAND)
    # deeper declaration -> the ratio has to come down
    assert hint["required_b_over_t"] < hint["current_b_over_t"]
    assert hint["within_band"] is True
    assert hint["required_b_over_t"] == pytest.approx(
        hint["current_b_over_t"]
        * (summary["draft_m"] / DECLARED_DEEPER) ** 1.5, abs=0.001)


def test_shallow_declaration_leaves_the_guard_band(tmp_path):
    _, summary = _run(tmp_path, DECLARED_SHALLOW)
    hint = summary["draft_mismatch_hint"]
    assert hint["within_band"] is False
    assert hint["required_b_over_t"] > hint["b_over_t_band"][1]
    text = write_report_md(
        summary, tmp_path / "shallow.md").read_text(encoding="utf-8")
    assert "高于上限" in text
    assert "不做外推" in text


def test_band_verdict_uses_the_value_the_reader_would_type(tmp_path):
    """N2/N3 lesson at the authoring boundary: a raw required ratio of
    3.5002 is reported as 3.500 and must count as IN band, because
    3.500 is the number a reader would type and the guard accepts it;
    3.5008 rounds to 3.501 and must count as out."""
    _, base = _run(tmp_path, DECLARED_DEEPER)
    b_over_t = base["beam_m"] / base["draft_m"]
    top = B_OVER_T_BAND[1]

    def declared_for(raw_ratio: float) -> float:
        return round(
            base["draft_m"] / (raw_ratio / b_over_t) ** (2.0 / 3.0), 4)

    hint_in = _run(tmp_path, declared_for(top + 0.0002))[1][
        "draft_mismatch_hint"]
    assert hint_in["required_b_over_t"] == top
    assert hint_in["within_band"] is True

    hint_out = _run(tmp_path, declared_for(top + 0.0008))[1][
        "draft_mismatch_hint"]
    assert hint_out["required_b_over_t"] == top + 0.001
    assert hint_out["within_band"] is False


# ---------------------------------------------------------------------------
# rendered text and the machine-readable contract
# ---------------------------------------------------------------------------


def test_report_renders_the_hint_line(tmp_path):
    _, summary = _run(tmp_path, DECLARED_DEEPER)
    hint = summary["draft_mismatch_hint"]
    text = write_report_md(
        summary, tmp_path / "hint.md").read_text(encoding="utf-8")
    assert "反算提示" in text
    assert f"B/T ≈ {hint['required_b_over_t']:.3f}" in text
    assert f"（当前 {hint['current_b_over_t']:.3f}）" in text
    assert "之内" in text
    assert "不做外推" not in text
    # the rule is stated, so the number is not mistaken for the only one
    assert "保持排水量、Cb 与 L/B 不变" in text
    assert "本工具不自动改动" in text
    # and the two limits travel with the number
    assert "未计入重量再平衡" in text
    assert "任务书无此字段" in text


def test_console_summary_shows_the_hint(tmp_path, capsys):
    path, _ = _run(tmp_path, DECLARED_DEEPER)
    assert main(["run", path]) == 0
    out = capsys.readouterr().out
    assert "draft declared" in out
    assert "B/T at declared" in out
    assert "OUTSIDE" not in out


def test_summary_stays_json_serialisable_with_the_hint(tmp_path):
    _, summary = _run(tmp_path, DECLARED_DEEPER)
    payload = json.dumps(summary, ensure_ascii=False)
    hint = json.loads(payload)["draft_mismatch_hint"]
    assert hint["required_b_over_t"]
    # an agent reading only the JSON must not invent a task-book key
    assert "task book has no field" in hint["action_note"]
    assert hint["one_shot_note"]


# ---------------------------------------------------------------------------
# the two limits stated with the hint must stay true
# ---------------------------------------------------------------------------


def test_advised_api_what_if_actually_runs(tmp_path):
    """The hint says what to do about it; that advice must work."""
    spec = ShipSpec(
        ship_type="bulk_carrier",
        deadweight=45000.0,
        service_speed=knots_to_ms(16.0),
        cb=0.80,
    )
    _, summary = _run(tmp_path, DECLARED_DEEPER)
    hint = summary["draft_mismatch_hint"]
    solved = solve_weight_balance(
        spec, ratios=RatioParameters(b_over_t=hint["required_b_over_t"]))
    assert solved.beam / solved.draft == pytest.approx(
        hint["required_b_over_t"], rel=1e-6)


def test_one_shot_residual_stays_declared(tmp_path):
    """The hint is a one-shot back-solve: with the hint ratio the weight
    balance re-iterates on the new dimensions and misses the declared
    draft by ~1 %.  Measured here (45,000 t probe): 0.3-1.3 % for
    declarations 0.4-1.2 m away, always short in the direction of the
    current balance draft.  If this ever becomes exact, the note in the
    report and the JSON must change - hence the band, not an equality.
    """
    spec = ShipSpec(
        ship_type="bulk_carrier",
        deadweight=45000.0,
        service_speed=knots_to_ms(16.0),
        cb=0.80,
    )
    base = solve_weight_balance(spec)
    for declared in (10.5, 11.0, 12.0, 12.5):
        ratio = required_b_over_t_at_draft(
            b_over_t=base.beam / base.draft,
            draft_m=base.draft,
            target_draft_m=declared,
        )
        solved = solve_weight_balance(
            spec, ratios=RatioParameters(b_over_t=ratio))
        residual = (solved.draft - declared) / declared
        assert 0.001 <= abs(residual) <= 0.02, (declared, residual)
        # short of the declaration, i.e. pulled back toward the balance
        assert (residual < 0) == (declared > base.draft)
