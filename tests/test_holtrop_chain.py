"""Tests for the selectable resistance method (v1.9.0).

`performance.resistance_method` selects the effective-power method
behind the run chain: `ayre` (the default — the pre-1.9 chain,
byte-identical, pinned by the rest of the suite) and `holtrop_mennen`
(the v1.5.0 page-verified library module, wired behind the registry
dispatcher `chain_effective_power`).  The design-space scan refuses a
holtrop_mennen task book instead of silently running a different
method than declared.
"""

import pytest

from openhull.holtrop import SEAWATER_DENSITY, holtrop_mennen_power
from openhull.resistance import (
    HOLTROP_MAX_FROUDE,
    RESISTANCE_ALGORITHMS,
    ayre_effective_power,
    chain_effective_power,
    resistance_algorithms,
)
from openhull.spec import SpecValidationError

TASKBOOK = "examples/taskbook_bulk_carrier.yaml"
TASKBOOK_H = "examples/taskbook_bulk_carrier_holtrop.yaml"

# TB-001 near-JBC condition for the dispatcher identity tests
SHIP = dict(
    displacement_t=182829.1, speed_kn=16.0, lpp_m=280.0, beam_m=45.0,
    draft_m=16.5, cb=0.858, lcb_pct_fwd=2.5475, lwl_m=287.0,
    screw="single", cm=0.9981, cwp=0.90,
    cp=178369.85 / (287.0 * 45.0 * 16.5),
)


# ---------------------------------------------------------------- registry


def test_registry_holtrop_is_now_implemented_with_provenance():
    info = RESISTANCE_ALGORITHMS["holtrop_mennen"]
    assert info.implemented is True
    assert "1982" in info.citation
    assert "International Shipbuilding Progress" in info.citation
    assert "Fr 0.55" in info.applicability
    assert "ayre" in resistance_algorithms()
    assert "holtrop_mennen" in resistance_algorithms()


# ------------------------------------------------------- dispatcher


def test_ayre_path_is_the_pre_19_call_verbatim():
    direct = ayre_effective_power(
        displacement_t=SHIP["displacement_t"], speed_kn=SHIP["speed_kn"],
        lpp_m=SHIP["lpp_m"], beam_m=SHIP["beam_m"],
        draft_m=SHIP["draft_m"], cb=SHIP["cb"],
        xc_pct_fwd=SHIP["lcb_pct_fwd"], lwl_m=SHIP["lwl_m"],
        screw=SHIP["screw"])
    via_chain = chain_effective_power(method_id="ayre", **SHIP)
    assert via_chain.method_id == "ayre"
    assert via_chain.pe_bare_kw == direct.pe_bare_kw
    assert via_chain.defaults_applied == ()
    assert via_chain.detail["v_sqrt_l"] == round(direct.v_sqrt_l, 4)


def test_holtrop_path_is_the_module_call_verbatim():
    direct = holtrop_mennen_power(
        speed_kn=SHIP["speed_kn"], lwl_m=SHIP["lwl_m"],
        lpp_m=SHIP["lpp_m"], beam_m=SHIP["beam_m"],
        draft_m=SHIP["draft_m"],
        displacement_volume_m3=SHIP["displacement_t"] * 1000.0
        / SEAWATER_DENSITY,
        cm=SHIP["cm"], cwp=SHIP["cwp"], lcb_pct_lpp=SHIP["lcb_pct_fwd"],
        cp=SHIP["cp"])
    via_chain = chain_effective_power(
        method_id="holtrop_mennen", **SHIP)
    assert via_chain.method_id == "holtrop_mennen"
    assert via_chain.pe_bare_kw == direct.pe_kw
    notes = " | ".join(via_chain.defaults_applied)
    assert len(via_chain.defaults_applied) == 5
    for token in ("appendage", "transom", "bulb", "c_stern",
                  "cb_waterline"):
        assert token in notes
    assert via_chain.detail["froude_number"] == round(
        direct.froude_number, 4)
    assert HOLTROP_MAX_FROUDE == 0.55


def test_holtrop_guard_refuses_above_the_registered_fr_band():
    # a small fast craft: 30 kn on a 28.7 m waterline is Fr ~0.90
    with pytest.raises(SpecValidationError) as excinfo:
        chain_effective_power(
            method_id="holtrop_mennen",
            displacement_t=423.0, speed_kn=30.0, lpp_m=28.0,
            beam_m=8.0, draft_m=3.0, cb=0.60, lcb_pct_fwd=0.0,
            lwl_m=28.7, screw="single", cm=0.85, cwp=0.80, cp=0.65)
    message = str(excinfo.value)
    assert "froude_number" in message
    assert "Fr <= 0.55" in message


def test_unknown_method_refused_naming_the_registry():
    with pytest.raises(SpecValidationError) as excinfo:
        chain_effective_power(method_id="ayre_1853", **SHIP)
    message = str(excinfo.value)
    assert "performance.resistance_method" in message
    assert "one of:" in message
    assert "holtrop_mennen" in message


# ------------------------------------------------------- chain (public API)


@pytest.fixture(scope="module")
def holtrop_summary():
    from openhull.cli import run_taskbook
    return run_taskbook(TASKBOOK_H)


@pytest.fixture(scope="module")
def default_summary():
    from openhull.cli import run_taskbook
    return run_taskbook(TASKBOOK)


def test_chain_on_holtrop_declares_method_and_defaults(holtrop_summary):
    block = holtrop_summary["propeller_design"]["resistance"]
    assert block["method"] == "holtrop_mennen"
    assert "1982" in block["citation"]
    assert len(block["defaults_applied"]) == 5
    assert 0 < block["pe_bare_kw"] < 100_000
    assert block["detail"]["froude_number"] <= HOLTROP_MAX_FROUDE
    sens = holtrop_summary["propeller_design"]["resistance_sensitivity"]
    assert "Ayre-specific" in sens["note"]


def test_chain_on_holtrop_still_designs_the_propeller(holtrop_summary):
    prop = holtrop_summary["propeller_design"]
    assert "skipped" not in prop
    assert prop["diameter_m"] > 0
    assert prop["thrust_n"] > 0
    assert prop["delivered_power_kw"] > 0


def test_default_chain_refusal_shape_unchanged(default_summary):
    # TB-001's 14.5 kn sits BELOW the Ayre speed-length band — the
    # pre-1.9 chain refuses the power stage, and that declared refusal
    # is byte-identical: the stage is still named by the METHOD id
    # (which for the default is the historical "ayre") and no
    # resistance provenance block leaks anywhere
    prop = default_summary["propeller_design"]
    assert prop["skipped"] is True
    assert prop["stage"] == "ayre"
    assert "resistance" not in prop
    assert "resistance" not in default_summary


@pytest.fixture(scope="module")
def ayre_success_summary(tmp_path_factory):
    # a lighter ship whose solved form sits INSIDE the Ayre bands (the
    # JBC-anchored TB-001 itself refuses the power stage on the C0
    # family band, L/Δ^(1/3) 4.80 < 4.88 — the demo's declared
    # refusal), so the default-method SUCCESS path is pinned here
    from openhull.cli import run_taskbook
    base = """\
schema_version: 1
taskbook_id: AY-OK
ship_type: bulk_carrier
requirements:
  deadweight_t: 45000
  service_speed_kn: 16.0
  kg_m: 9.5
  drafts:
    design_draft_m: 11.6
constraints:
  block_coefficient_design: 0.80
propeller:
  blades_z: 4
  expanded_area_ratio: 0.55
  rpm: 100
  shaft_immersion_m: 6.0
  shaft_efficiency: 0.98
  relative_rotative_eff: 0.99
"""
    path = tmp_path_factory.mktemp("ayre_ok") / "ay_ok.yaml"
    path.write_text(base, encoding="utf-8")
    return run_taskbook(str(path))


def test_default_method_success_path_still_ayre(ayre_success_summary):
    block = ayre_success_summary["propeller_design"]["resistance"]
    assert block["method"] == "ayre"
    assert block["defaults_applied"] == []
    assert 0 < block["pe_bare_kw"] < 100_000
    sens = ayre_success_summary["propeller_design"][
        "resistance_sensitivity"]
    assert "in_c0_peak_zone" in sens
    assert "admiralty_corridor" in sens


def test_taskbook_with_unknown_method_refuses_early(tmp_path):
    from openhull.cli import run_taskbook

    with open(TASKBOOK, encoding="utf-8") as fh:
        yaml_text = fh.read()
    bad = yaml_text.replace(
        "ship_type: bulk_carrier",
        "ship_type: bulk_carrier\n\nperformance:\n"
        "  resistance_method: ayre_1853")
    path = tmp_path / "bad_method.yaml"
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(SpecValidationError) as excinfo:
        run_taskbook(str(path))
    assert "performance.resistance_method" in str(excinfo.value)


# ------------------------------------------------------------ scan path


def test_scan_refuses_a_holtrop_taskbook_instead_of_mixing(
        tmp_path, capsys):
    from openhull.cli import main

    base = """\
schema_version: 1
taskbook_id: HR-1
ship_type: bulk_carrier
performance:
  resistance_method: holtrop_mennen
requirements:
  deadweight_t: 45000
  service_speed_kn: 16.0
  kg_m: 9.5
  drafts:
    design_draft_m: 11.6
constraints:
  block_coefficient_design: 0.80
propeller:
  blades_z: 4
  rpm: 100
"""
    path = tmp_path / "hr.yaml"
    path.write_text(base, encoding="utf-8")
    rc = main(["optimize", str(path), "--out", str(tmp_path / "out"),
               "--grid-lob", "6.0:6.0:1", "--grid-bt", "2.7:2.7:1",
               "--grid-cb", "0.80:0.80:1"])
    assert rc == 2
    captured = capsys.readouterr()
    printed = captured.out + captured.err
    assert "performance.resistance_method" in printed
    assert "ayre (the scan)" in printed
