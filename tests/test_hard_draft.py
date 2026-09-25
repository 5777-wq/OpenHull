"""R2-A: the optional hard design draft (owner-approved 2026-09-25).

`requirements.drafts.draft_is_hard: true` makes the declared draft the
CONSTRAINT: B/T is bisected on the converged weight balance (L/B and Cb
held, the same rule the Plan-0 hint declares) so the ship is designed to
the declared waterline instead of merely reporting a mismatch.

Pinned here:

- the JBC reverse anchor: a hard 16.5 m draft on the owner-ratified
  deadweight/Cb must land back on the NMRI particulars (±5 %) — the
  precondition the external review set for any hard-draft machinery;
- hint vs hard solve: the one-shot hint and the converged solve must
  agree within the declared one-shot residual;
- the two refusal directions, each with the band endpoints in the
  message;
- the default path (flag absent) is untouched, and the run-level
  summary/report/console surfaces say what happened.
"""

import json

import pytest

from openhull.cli import main, run_taskbook
from openhull.report import write_report_md
from openhull.spec import ShipSpec, knots_to_ms, SpecValidationError
from openhull.weight_balance import (
    solve_weight_balance,
    solve_weight_balance_for_draft,
)

TASKBOOK = """\
schema_version: 1
taskbook_id: HARD-DRAFT
ship_type: bulk_carrier
requirements:
  deadweight_t: 45000
  service_speed_kn: 16.0
  kg_m: 9.5
  drafts:
    design_draft_m: {draft}
    draft_is_hard: {hard}
constraints:
  block_coefficient_design: 0.80
propeller:
  blades_z: 4
  expanded_area_ratio: 0.50
  rpm: 100
  shaft_immersion_m: 6.0
  shaft_efficiency: 0.98
  relative_rotative_eff: 0.99
"""

JBC_SPEC = ShipSpec(
    ship_type="bulk_carrier",
    deadweight=149920.0,          # owner-ratified assumption (TB-001)
    service_speed=knots_to_ms(14.5),
    cb=0.8580,
)


def _run(tmp_path, draft: float, hard: bool):
    path = tmp_path / f"tb_{draft:.2f}_{'hard' if hard else 'soft'}.yaml"
    path.write_text(
        TASKBOOK.format(draft=draft, hard="true" if hard else "false"),
        encoding="utf-8")
    return str(path), run_taskbook(str(path))


# ---------------------------------------------------------------------------
# the JBC reverse anchor (the review's precondition)
# ---------------------------------------------------------------------------


def test_jbc_reverse_anchor():
    res = solve_weight_balance_for_draft(JBC_SPEC, 16.5)
    assert res.hard_draft is True
    assert res.draft == pytest.approx(16.5, abs=0.01)
    # NMRI particulars: Lpp 280.0, B 45.0, D 25.0
    assert res.lpp == pytest.approx(280.0, rel=0.05)
    assert res.beam == pytest.approx(45.0, rel=0.05)
    assert res.depth == pytest.approx(25.0, rel=0.05)
    # and the solved ratio sits inside the guard band, as every other
    # chain result must
    assert 2.0 <= res.solved_b_over_t <= 3.5


def test_hint_and_hard_solve_agree_within_the_declared_residual():
    """The Plan-0 hint (one-shot, displacement held) and the converged
    hard solve must tell the same story: their B/T values differ only by
    the declared 0.3-1.3 % one-shot residual."""
    plain = solve_weight_balance(JBC_SPEC)
    hint = required_b_over_t(plain)
    hard = solve_weight_balance_for_draft(JBC_SPEC, 16.5)
    assert hard.solved_b_over_t == pytest.approx(hint, rel=0.015)


def required_b_over_t(plain):
    from openhull import required_b_over_t_at_draft
    return required_b_over_t_at_draft(
        b_over_t=plain.beam / plain.draft,
        draft_m=plain.draft,
        target_draft_m=16.5,
    )


# ---------------------------------------------------------------------------
# the two refusal directions
# ---------------------------------------------------------------------------


def test_too_deep_declaration_is_refused_with_the_band_floor():
    with pytest.raises(SpecValidationError) as excinfo:
        solve_weight_balance_for_draft(
            ShipSpec(ship_type="bulk_carrier", deadweight=45000.0,
                     service_speed=knots_to_ms(16.0), cb=0.80),
            20.0)
    message = str(excinfo.value)
    assert "band floor B/T 2.00" in message
    assert "shallower than the declared 20.000" in message


def test_too_shallow_declaration_is_refused_with_the_band_top():
    with pytest.raises(SpecValidationError) as excinfo:
        solve_weight_balance_for_draft(
            ShipSpec(ship_type="bulk_carrier", deadweight=45000.0,
                     service_speed=knots_to_ms(16.0), cb=0.80),
            7.0)
    message = str(excinfo.value)
    assert "band top B/T 3.50" in message
    assert "deeper than the declared 7.000" in message


# ---------------------------------------------------------------------------
# run level: convergence from both sides, surfaces, default path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("declared", [12.5, 11.0])
def test_bisection_converges_from_both_sides(tmp_path, declared):
    """The 45,000 t case balances at ~11.64 m: 12.5 m needs a slimmer
    beam (B/T down), 11.0 m a wider one (B/T up) — both must converge
    onto the declared waterline within 1 cm, on opposite sides of 2.7."""
    _, summary = _run(tmp_path, declared, hard=True)
    assert summary["draft_is_hard"] is True
    assert summary["draft_m"] == pytest.approx(declared, abs=0.01)
    assert summary["draft_mismatch_m"] is None
    solved = summary["hard_draft_b_over_t"]
    assert 2.0 <= solved <= 3.5
    assert (solved < 2.7) == (declared > 11.64)


def test_default_path_is_untouched(tmp_path):
    _, summary = _run(tmp_path, 11.6, hard=False)
    assert summary["draft_is_hard"] is False
    assert summary["hard_draft_b_over_t"] is None
    assert summary["hard_draft_iterations"] is None


def test_report_and_console_declare_the_hard_mode(tmp_path, capsys):
    path, summary = _run(tmp_path, 12.5, hard=True)
    text = write_report_md(
        summary, tmp_path / "hard.md").read_text(encoding="utf-8")
    assert "draft_is_hard" in text
    assert "B/T 反解为" in text
    assert "不出现吃水不符提示" in text
    # the mismatch warning must NOT fire in hard mode
    assert "与重量平衡吃水" not in text

    assert main(["run", path]) == 0
    out = capsys.readouterr().out
    assert "draft hard" in out
    assert "B/T solved to" in out


def test_summary_stays_json_serialisable_in_hard_mode(tmp_path):
    _, summary = _run(tmp_path, 12.5, hard=True)
    payload = json.dumps(summary, ensure_ascii=False)
    restored = json.loads(payload)
    assert restored["draft_is_hard"] is True
    assert restored["hard_draft_b_over_t"]
