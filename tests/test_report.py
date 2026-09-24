"""Design report generation tests (plan task 4.3).

The report must restate the computed summary faithfully — the tests
pin the key numbers of a run summary into the text and verify the
graceful-degradation paths (skipped propeller block, absent KG).
"""

import json

from openhull.report import write_report_md


def _summary() -> dict:
    return {
        "taskbook_id": "T-TEST",
        "lpp_m": 100.0, "beam_m": 20.0, "depth_m": 12.0, "draft_m": 6.0,
        "cb_target": 0.80, "cb_achieved": 0.7999, "transform_passes": 2,
        "deadweight_t": 5000.0, "displacement_t": 6200.0,
        "lightship_t": 1200.0, "norman_coefficient": 1.05,
        "iterations": 3, "deadweight_ratio_achieved": 0.806,
        "hydrostatics": [{
            "draft_m": 6.0, "displacement_volume_m3": 6048.8,
            "displacement_t": 6200.0, "waterplane_area_m2": 1720.0,
            "kb_m": 3.1, "bmt_m": 2.4, "km_m": 5.5, "tpc_t_per_cm": 17.6,
            "lcb_pct_lpp": 2.0, "lcf_pct_lpp": 1.0, "cb": 0.7999,
            "cw": 0.86, "bml_m": 110.0, "lcf_pct_lpp": 1.0,
            "cp": 0.86, "cm": 0.93, "mtc_tm_per_cm": 150.0,
        }],
        "stability_criteria": None,
        "weather_criterion": None,
        "propeller_design": {"skipped": True, "reason": "band"},
        "seakeeping": None,
        "arrangement": None,
    }


def test_report_restates_key_numbers(tmp_path):
    out = write_report_md(_summary(), tmp_path / "r.md")
    text = out.read_text(encoding="utf-8")
    assert "T-TEST" in text
    assert "100.00" in text and "6,200.0" in text
    assert "0.7999" in text
    assert "未能给出所需航速对应的功率" in text  # staged refusal block
    assert "工具原文" in text                    # verbatim reason kept
    assert "未运行" in text       # absent KG blocks


def test_report_embeds_chart_and_arrangement(tmp_path):
    summary = _summary()
    summary["seakeeping"] = {
        "roll_period_s": 5.2, "roll_period_simple_s": 6.1,
        "pitch_period_s": 4.4, "heave_period_s": 4.5,
        "effective_wave_slope_k": 0.73,
        "roll_amplification_resonant": 8.3, "roll_mu": 0.06,
        "resonance_checks": [{
            "motion": "roll", "label": "test sea", "wave_period_s": 6.0,
            "ship_period_s": 5.2, "tuning_factor": 0.87,
            "in_resonance_band": True, "citation": "x"}],
    }
    summary["arrangement"] = {
        "source": "default bulk-carrier scheme",
        "double_bottom_top_m": 1.0,
        "compartments": [{"name": "Cargo Hold 1", "kind": "hold",
                          "x0_m": 9.5, "x1_m": 28.25, "z0_m": 1.0,
                          "z1_m": 12.0}],
    }
    out = write_report_md(summary, tmp_path / "r.md",
                          chart_path=tmp_path / "hydro.png",
                          arrangement_summary=summary["arrangement"])
    text = out.read_text(encoding="utf-8")
    assert "处于谐摇区" in text          # the in-band verdict renders
    assert "hydro.png" in text           # chart embedded by reference
    assert "Cargo Hold 1" in text        # compartment table present
    assert "default bulk-carrier scheme" in text
    json.dumps(summary["arrangement"])   # sanity: json-safe data
