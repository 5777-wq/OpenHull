"""Tests for the selectable parent-hull registry (v1.8.0).

Two mothers are registered: the packaged digitised Series 60 (the
pre-v1.8 default — byte-identical behaviour, pinned by the rest of the
suite) and the analytic JBC-family fit declared in AGENTS.md §5
(Lines plan, 2026-10-04).  Anchors: the NMRI JBC published values
(examples/data/DATA_SOURCES.md).
"""

import math

import pytest

from openhull.geometry import (
    PARENT_HULL_ALGORITHMS,
    ParentHullSpec,
    build_parent_hull,
    parent_hull_defaults_applied,
)
from openhull.hydrostatics import hydrostatics_at
from openhull.optimize import ScanConfig, SweepGrid, design_space_scan
from openhull.spec import ShipSpec, SpecValidationError, knots_to_ms

TASKBOOK = "examples/taskbook_bulk_carrier.yaml"
TASKBOOK_J = "examples/taskbook_bulk_carrier_jbcparent.yaml"

# NMRI JBC anchors (examples/data/DATA_SOURCES.md)
JBC_CB = 0.8580
JBC_LCB_FWD_PCT = 2.5475
JBC_KM_M = 18.59
JBC_VOLUME_M3 = 178369.9


# ---------------------------------------------------------------- registry


def test_registry_members_carry_provenance():
    assert set(PARENT_HULL_ALGORITHMS) == {
        "series60_digitised", "jbc_analytic"}
    for meta in PARENT_HULL_ALGORITHMS.values():
        assert isinstance(meta, ParentHullSpec)
        assert meta.kind in ("digitised", "analytic")
        assert meta.citation.strip()
        assert meta.applicability.strip()
        assert callable(meta.build)


def test_unknown_parent_id_refused_naming_the_registry():
    with pytest.raises(SpecValidationError) as excinfo:
        build_parent_hull("series_60", lpp=280.0, beam=45.0, draft=16.5,
                          cb=0.858)
    message = str(excinfo.value)
    assert "one of:" in message
    assert "series60_digitised" in message
    assert "jbc_analytic" in message


def test_analytic_parent_requires_a_pinned_cb():
    with pytest.raises(SpecValidationError) as excinfo:
        build_parent_hull("jbc_analytic", lpp=280.0, beam=45.0,
                          draft=16.5, cb=None)
    assert "block_coefficient" in str(excinfo.value)


def test_series60_build_ignores_form_targets():
    # the digitised mother is affine-scaled only — the form targets are
    # consumed downstream by the Lackenby transform, so two builds with
    # different cb values must return IDENTICAL tables
    kw = dict(lpp=271.633, beam=45.272, draft=16.767)
    a, _ = build_parent_hull("series60_digitised", cb=None, **kw)
    b, _ = build_parent_hull("series60_digitised", cb=0.5, **kw)
    assert a.half_breadths.shape == b.half_breadths.shape
    assert (a.half_breadths == b.half_breadths).all()
    assert (a.stations == b.stations).all()


# ------------------------------------------------------- analytic parent


def test_analytic_parent_hits_the_cb_lcb_anchors_without_km():
    # km_target=None: the wall-sided base form (k = 0); the Cb/LCB fit
    # is untouched and KM is measured, not tuned
    table, meta = build_parent_hull(
        "jbc_analytic", lpp=280.0, beam=45.0, draft=16.5, cb=JBC_CB)
    assert meta.algorithm == "jbc_analytic"
    hydro = hydrostatics_at(table, 16.5)
    assert abs(hydro.cb - JBC_CB) <= 0.002
    assert abs(hydro.lcb - JBC_LCB_FWD_PCT) <= 0.05
    assert math.isfinite(hydro.km) and hydro.km > 15.0


def test_analytic_parent_km_anchor_within_two_percent():
    table, _ = build_parent_hull(
        "jbc_analytic", lpp=280.0, beam=45.0, draft=16.5, cb=JBC_CB,
        km_target=JBC_KM_M)
    hydro = hydrostatics_at(table, 16.5)
    assert abs(hydro.km - JBC_KM_M) <= 0.02 * JBC_KM_M


def test_defaults_applied_declares_only_what_was_substituted():
    everything = parent_hull_defaults_applied(
        "jbc_analytic", cm=0.99, lcb_fwd_pct=2.0, km_target=18.0)
    assert everything == []
    nothing = parent_hull_defaults_applied(
        "jbc_analytic", cm=None, lcb_fwd_pct=None, km_target=None)
    assert len(nothing) == 3
    assert all("JBC anchor" in note or "no anchor" in note
               for note in nothing)
    assert parent_hull_defaults_applied(
        "series60_digitised", cm=None, lcb_fwd_pct=None,
        km_target=None) == []


# ------------------------------------------------------- chain (public API)


@pytest.fixture(scope="module")
def jbc_parent_summary():
    from openhull.cli import run_taskbook
    return run_taskbook(TASKBOOK_J)


@pytest.fixture(scope="module")
def default_summary():
    from openhull.cli import run_taskbook
    return run_taskbook(TASKBOOK)


def test_chain_on_the_analytic_parent_reports_provenance(jbc_parent_summary):
    block = jbc_parent_summary["parent_hull"]
    assert block["algorithm"] == "jbc_analytic"
    assert block["kind"] == "analytic"
    assert "AGENTS.md" in block["citation"]
    # TB-J pins Cm/LCB in hull_form and carries kg_m + gm_reference_m,
    # so the KM target is the task book's own KG + GM — no defaults
    assert block["defaults_applied"] == []


def test_chain_on_the_analytic_parent_hits_the_jbc_anchors(
        jbc_parent_summary):
    assert abs(jbc_parent_summary["cb_achieved"] - JBC_CB) <= 0.005
    row = jbc_parent_summary["hydrostatics"][-1]
    assert abs(row["displacement_volume_m3"] - JBC_VOLUME_M3) <= 0.01 * JBC_VOLUME_M3
    assert abs(row["lcb_pct_lpp"] - JBC_LCB_FWD_PCT) <= 0.05
    assert abs(row["km_m"] - JBC_KM_M) <= 0.02 * JBC_KM_M


def test_default_chain_still_the_digitised_series60(default_summary):
    block = default_summary["parent_hull"]
    assert block["algorithm"] == "series60_digitised"
    assert block["kind"] == "digitised"
    assert block["defaults_applied"] == []
    assert "DTMB Report 1712" in default_summary["hull_source"]


def test_taskbook_with_unknown_parent_refuses_early(tmp_path):
    from openhull.cli import run_taskbook

    with open(TASKBOOK, encoding="utf-8") as fh:
        yaml_text = fh.read()
    bad = yaml_text.replace(
        "ship_type: bulk_carrier",
        "ship_type: bulk_carrier\n\nhull_form:\n  parent: series_60")
    path = tmp_path / "bad_parent.yaml"
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(SpecValidationError) as excinfo:
        run_taskbook(str(path))
    assert "hull_form.parent" in str(excinfo.value)


# ------------------------------------------------------------ scan path


def test_scan_runs_on_the_analytic_parent():
    spec = ShipSpec(
        deadweight=149920.0,
        service_speed=knots_to_ms(16.0),
        cb=0.85,
        draft=16.5,
    )
    grid = SweepGrid(
        # inside the digitised C0-chart band (L/disp^(1/3) >= 4.88 —
        # the lower-edge backlog refuses fatter candidates at ayre)
        l_over_b=(6.2, 6.4, 2), b_over_t=(2.7, 2.7, 1),
        cb=(0.82, 0.84, 2))
    result = design_space_scan(
        spec, kg_m=13.29, grid=grid,
        config=ScanConfig(kg_m=13.29, shaft_immersion_m=8.5,
                          relative_rotative_eff=0.982),
        parent_hull="jbc_analytic",
        parent_form={"cm": 0.9981, "lcb_fwd_pct": 2.5475,
                     "km_target": JBC_KM_M})
    assert len(result.feasible) + len(result.rejected) == 4
    assert len(result.feasible) >= 1
