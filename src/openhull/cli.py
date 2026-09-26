"""Command line interface: task book in, design chain out.

    openhull run examples/taskbook_bulk_carrier.yaml
    openhull run examples/taskbook_bulk_carrier.yaml --csv > table.csv
    openhull --version

The ``run`` command executes the design chain end to end: weight-buoyancy
balance from the task book (task 1.3), principal dimensions, a
hydrostatics table (task 1.4 machinery) on the real-offsets hull (task
2.6), and — when the task book carries ``requirements.kg_m`` — the
large-angle stability curve (task 3.4).  The human summary goes to
stdout; ``--csv`` prints the hydrostatics table as pure CSV instead, so
the shell redirection stores the table (``--csv`` output is UTF-8 with
BOM, ready for Excel).  Results are deterministic: same task book,
same numbers (AGENTS.md section 8).

The CLI performs no file writes of its own - everything is streamed
through stdout, and the user decides where results land.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import yaml

from .geometry import jbc_parent_offsets  # noqa: F401  (1.x fitted parent,
#   kept for the validation tests; the run chain uses real offsets - 2.6)
from .hydrostatics import hydrostatic_draft_rows, hydrostatics_table
from .optimize import (
    ScanConfig,
    ScanResult,
    SweepGrid,
    design_space_scan,
    write_tradeoff_chart,
)
from .linesplan import parent_to_taskbook
from .main_dimensions import (B_OVER_T_BAND, FN_BAND, GRAVITY,
                              L_OVER_B_BAND, L_OVER_DEPTH_BAND,
                              required_b_over_t_at_draft)
from .propeller import (
    SIGMA_VERIFIED_BAND,
    b_series_open_water,
    check_cavitation,
    solve_optimal_propeller_for_thrust,
)
from .propulsion import propulsion_factors
from .seakeeping import estimate_seakeeping, kwon_speed_loss_percent
from .resistance import (AYRE_V_SQRT_L_MAX, AYRE_V_SQRT_L_MIN,
                         C0_FAMILY_BAND, admiralty_corridor,
                         ayre_effective_power)
from .spec import SEAWATER_DENSITY
from .spec import (knots_to_ms, within_band, ShipSpec,
                   SpecValidationError)
from .stability import gz_curve, intact_stability_criteria, weather_criterion
from .weight_balance import (solve_weight_balance,
                             solve_weight_balance_for_draft)


def _design_propeller_at_service(data, balance, hydro_design):
    """Preliminary propeller design at the task book's service speed.

    Returns a summary dict, or a dict with skipped=True and the reason
    when a whitelisted method refuses the operating point (e.g. the
    Ayre speed-length band does not reach this ship's service speed).
    """
    propeller_block = data.get("propeller") or {}
    if propeller_block.get("rpm") is None:
        return None
    rpm = float(propeller_block["rpm"])
    n_rps = rpm / 60.0
    z = int(propeller_block.get("blades_z", 5))
    aear = float(propeller_block.get("expanded_area_ratio", 0.50))
    eta_r = float(propeller_block.get("relative_rotative_eff") or 1.0)
    service_kn = float(
        (data.get("requirements") or {}).get("service_speed_kn"))
    v_ms = knots_to_ms(service_kn)
    series = b_series_open_water(z, aear)
    # stage 1: the whitelisted resistance method must reach this
    # operating point at all (Ayre speed-length band, digitised C0
    # band) — a refusal here is reported with stage "ayre"
    # ONE waterline length for the run: the task book's declared value
    # (constraints.stability.weather_criterion.length_waterline_m) when
    # present, otherwise Ayre's own standard 1.025*Lpp.  Both the
    # effective-power call and the propeller factors below use it, so
    # the PE and the propeller describe the same ship.
    _weather_block = (
        ((data.get("constraints") or {}).get("stability") or {})
        .get("weather_criterion"))
    declared_lwl = (
        _weather_block.get("length_waterline_m")
        if isinstance(_weather_block, dict) else None)
    run_lwl = (float(declared_lwl) if declared_lwl is not None
               else 1.025 * balance.lpp)
    try:
        ayre_result = ayre_effective_power(
            displacement_t=balance.displacement_t, speed_kn=service_kn,
            lpp_m=balance.lpp, beam_m=balance.beam,
            draft_m=balance.draft, cb=hydro_design.cb,
            xc_pct_fwd=hydro_design.lcb, lwl_m=run_lwl, screw="single",
        )
        pe_kw = ayre_result.pe_bare_kw
    except SpecValidationError as refuse:
        skipped = {"skipped": True, "stage": "ayre", "reason": str(refuse)}
        # P1-2 first half (review 2026-09-25): the refusal names the
        # violated band; a one-shot back-solve under a DECLARED rule
        # gives the nearest feasible value, so the reader does not start
        # from a blind guess.  Same discipline as the draft hint: the
        # rule travels with the number, the weight re-balance moves the
        # exact boundary, `optimize` locates it precisely.
        ratio_now = balance.lpp / balance.displacement_t ** (1.0 / 3.0)
        declared_cb = float(
            (data.get("constraints") or {}).get("block_coefficient_design")
            or hydro_design.cb)
        if refuse.field == "length_ratio":
            lo, hi = C0_FAMILY_BAND
            if ratio_now < lo:
                skipped["feasibility_hint"] = {
                    "field": "block_coefficient_design",
                    "direction": "lower",
                    "bound": round(declared_cb * (ratio_now / lo) ** 3, 3),
                    "band": list(C0_FAMILY_BAND),
                    "rule": ("hold displacement and the L/B, B/T ratios "
                             "(one-shot, before the weight re-balance)"),
                }
            elif ratio_now > hi:
                skipped["feasibility_hint"] = {
                    "field": "block_coefficient_design",
                    "direction": "higher",
                    "bound": round(declared_cb * (ratio_now / hi) ** 3, 3),
                    "band": list(C0_FAMILY_BAND),
                    "rule": ("hold displacement and the L/B, B/T ratios "
                             "(one-shot, before the weight re-balance)"),
                }
        elif refuse.field == "speed":
            lo, hi = AYRE_V_SQRT_L_MIN, AYRE_V_SQRT_L_MAX
            l_ft = balance.lpp / 0.3048
            skipped["feasibility_hint"] = {
                "field": "service_speed_kn",
                "reachable_kn": [round(lo * math.sqrt(l_ft), 2),
                                 round(hi * math.sqrt(l_ft), 2)],
                "declared_kn": round(service_kn, 2),
                "rule": "the Ayre speed-length band on the solved Lpp",
            }
        return skipped
    # P0-1 diagnostic (display only): where the operating point sits in
    # the digitised C0 family, and the Admiralty-coefficient corridor
    # around the design speed
    resistance_sensitivity = {
        "in_c0_peak_zone": ayre_result.in_c0_peak_zone,
        "c0_family_peak_v_sqrt_l": ayre_result.c0_family_peak_v_sqrt_l,
        "c0_local_slope_pct_per_0p05":
            ayre_result.c0_local_slope_pct_per_0p05,
        "v_sqrt_l": round(ayre_result.v_sqrt_l, 4),
        "admiralty_corridor": admiralty_corridor(
            displacement_t=balance.displacement_t, speed_kn=service_kn,
            lpp_m=balance.lpp, beam_m=balance.beam, draft_m=balance.draft,
            cb=hydro_design.cb, xc_pct_fwd=hydro_design.lcb,
            lwl_m=run_lwl),
    }
    # stage 2: thrust-led propeller design (efficiency-independent
    # thrust, no eta_o fixed point — same route as the scan)
    try:
        d_bounds = (0.35 * balance.draft, 0.75 * balance.draft)
        d_guess = 0.55 * balance.draft
        prop = None
        factors = None
        last_error = None
        for _ in range(4):
            try:
                factors = propulsion_factors(
                    lpp_m=balance.lpp,
                    # ONE waterline for the run: the declared value when
                    # the task book carries one, else Ayre's standard
                    # 1.025*Lpp - the same value the effective-power
                    # call above used (Ayre's own default).  Before
                    # v1.0.5 this stage took Lpp while the PE took the
                    # standard, i.e. two slightly different ships.
                    lwl_m=run_lwl,
                    beam_m=balance.beam,
                    draft_m=balance.draft,
                    cb=hydro_design.cb, cp=hydro_design.cp,
                    cm=hydro_design.cm, cwp=hydro_design.cw,
                    lcb_pct_fwd=hydro_design.lcb,
                    propeller_diameter_m=d_guess, speed_ms=v_ms,
                    screw="single", eta_r=eta_r,
                )
                va_ms = v_ms * (1.0 - factors.w)
                thrust_required = pe_kw * 1e3 / (v_ms * (1.0 - factors.t))
                prop = solve_optimal_propeller_for_thrust(
                    thrust_required, va_ms, n_rps, series,
                    d_bounds_m=d_bounds, n_scan=300)
                break
            except SpecValidationError as retry:
                last_error = retry
                d_guess *= 0.85
                if d_guess < d_bounds[0]:
                    break
        if prop is None or factors is None:
            return {"skipped": True, "stage": "propeller",
                    "reason": str(last_error) if last_error
                    else "no admissible diameter inside the tip-clearance "
                         "bounds"}
        eta_sanity = (0.40, 0.85)
        if not within_band(prop.eta_o, *eta_sanity):
            return {"skipped": True, "stage": "propeller",
                    "reason": (
                        f"eta_o {prop.eta_o:.3f} outside the sanity band "
                        f"{eta_sanity}")}
        if prop.diameter_m > 0.75 * balance.draft:
            return {"skipped": True, "stage": "propeller",
                    "reason": (
                        f"diameter {prop.diameter_m:.2f} m exceeds "
                        f"0.75 x draft {balance.draft:.2f} m")}
    except SpecValidationError as refuse:
        return {"skipped": True, "stage": "propeller",
                "reason": str(refuse)}
    shaft_power_kw = prop.delivered_power_kw / (
        float(propeller_block.get("shaft_efficiency") or 1.0) * eta_r)
    cav = None
    cav_note = None
    cav_unchecked = None
    hs_m = propeller_block.get("shaft_immersion_m")
    if hs_m is not None:
        try:
            cav = check_cavitation(
                thrust_n=prop.thrust_n, va_ms=prop.va_ms, n_rps=n_rps,
                diameter_m=prop.diameter_m,
                pitch_ratio=prop.pitch_ratio, aeao_available=aear,
                hs_m=float(hs_m))
        except SpecValidationError as cav_refuse:
            # sigma outside the verified Burrill band: the check is
            # UNAVAILABLE here, not passed (review 2026-09-25, P0-2).
            # Carry the side: below the band is the HIGHER cavitation
            # risk direction and the one that most needs human review.
            cav = None
            cav_note = str(cav_refuse)
            sigma = float(cav_refuse.value)
            lo, hi = SIGMA_VERIFIED_BAND
            cav_unchecked = {
                "sigma_0_7r": round(sigma, 4),
                "band": [round(lo, 4), round(hi, 4)],
                "side": "low" if sigma < lo else "high",
            }
    result = {
        "series": prop.series_name,
        "provenance": prop.provenance,
        "service_speed_kn": service_kn,
        "rpm": rpm,
        "blades_z": z,
        "diameter_m": round(prop.diameter_m, 3),
        "pitch_ratio": round(prop.pitch_ratio, 4),
        "advance_coefficient": round(prop.j, 4),
        "eta_open_water": round(prop.eta_o, 4),
        "eta_hull": round(factors.eta_h, 4),
        "wake_fraction": round(factors.w, 4),
        "thrust_deduction": round(factors.t, 4),
        "thrust_n": round(prop.thrust_n, 1),
        "delivered_power_kw": round(prop.delivered_power_kw, 1),
        "shaft_power_kw": round(shaft_power_kw, 1),
        "cavitation": None,
        "cavitation_note": cav_note,
        "cavitation_unchecked": cav_unchecked,
        "resistance_sensitivity": resistance_sensitivity,
    }
    if cav is not None:
        result["cavitation"] = {
            "sigma_0_7r": round(cav.sigma_0_7r, 4),
            "tau_c_limit": round(cav.tau_c_limit, 4),
            "aeao_required": round(cav.aeao_required, 3),
            "aeao_available": cav.aeao_available,
            "ok": cav.ok,
            "verdict": cav.verdict,
        }
    return result

__all__ = ["main", "run_taskbook"]

_HYDRO_COLUMNS = [
    ("draft", "draft_m"),
    ("displacement_volume", "displacement_volume_m3"),
    ("displacement", "displacement_t"),
    ("aw", "waterplane_area_m2"),
    ("lcf", "lcf_pct_lpp"),
    ("lcb", "lcb_pct_lpp"),
    ("cb", "cb"),
    ("cm", "cm"),
    ("cp", "cp"),
    ("cw", "cw"),
    ("kb", "kb_m"),
    ("bmt", "bmt_m"),
    ("bml", "bml_m"),
    ("km_attr", "km_m"),
    ("tpc", "tpc_t_per_cm"),
    ("mtc", "mtc_tm_per_cm"),
]


def _load_taskbook(path) -> dict:
    if not path.exists():
        raise SpecValidationError(
            "taskbook", str(path), "an existing YAML file",
            "the task book is the input contract of the whole chain; "
            "without it there is nothing to run.",
        )
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise SpecValidationError(
            "taskbook", str(path), "a YAML mapping",
            "the task book must be a YAML mapping of sections "
            f"(requirements, constraints, ...); the file parsed to "
            f"{type(data).__name__}.",
        )
    return data


def _ship_spec_from_taskbook(data: dict) -> tuple[ShipSpec, float]:
    """Extract the validated ShipSpec and design draft from a task book."""
    requirements = data.get("requirements") or {}
    constraints = data.get("constraints") or {}
    drafts = requirements.get("drafts") or {}

    values = {
        "requirements.deadweight_t": requirements.get("deadweight_t"),
        "requirements.service_speed_kn": requirements.get("service_speed_kn"),
        "requirements.drafts.design_draft_m": drafts.get("design_draft_m"),
        "constraints.block_coefficient_design": constraints.get(
            "block_coefficient_design"
        ),
    }
    missing = [key for key, value in values.items() if value is None]
    if missing:
        raise SpecValidationError(
            "taskbook", data.get("taskbook_id", "<unnamed taskbook>"),
            "required keys present: " + ", ".join(missing),
            "the stage-1 chain needs the deadweight, the service speed, "
            "the design draft and a pinned block coefficient; fill them "
            "in the task book (see examples/taskbook_bulk_carrier.yaml).",
        )
    spec = ShipSpec(
        ship_type=str(data.get("ship_type", "bulk_carrier")),
        deadweight=float(values["requirements.deadweight_t"]),
        service_speed=knots_to_ms(
            float(values["requirements.service_speed_kn"])
        ),
        cb=float(values["constraints.block_coefficient_design"]),
        draft=float(values["requirements.drafts.design_draft_m"]),
    )
    return spec, float(values["requirements.drafts.design_draft_m"])


def _table_fractions(step: float) -> tuple[float, ...]:
    """Draft fractions of the hydrostatics table for a requested step.

    P2-2 (review 2026-09-25): the exported table matches the chart's
    granularity - the default step is 0.1 (10 rows); 0.25 restores the
    historical 4.  The last fraction is always exactly 1.0 (the design
    waterline), and the step is clamped into [0.02, 1.0].
    """
    if not (0.02 <= step <= 1.0):
        raise SpecValidationError(
            "csv_step", step, "0.02 <= step <= 1.0",
            "the step is a fraction of the design draft; below 0.02 the "
            "table exceeds 50 rows for no reading benefit.")
    n = max(1, round(1.0 / step))
    return tuple(round(i / n, 6) for i in range(1, n + 1))


def _hydrostatics_rows(hydro_table) -> list[dict]:
    """The hydrostatics table as plain dicts (JSON/CSV ready)."""
    return [
        {
            label: getattr(entry, "km" if attr == "km_attr" else attr)
            for attr, label in _HYDRO_COLUMNS
        }
        for entry in hydro_table.entries
    ]


def run_taskbook(taskbook_path: str,
                 hydro_curve_chart: str | None = None,
                 report_path: str | None = None,
                 arrangement_dxf_path: str | None = None,
                 arrangement_chart_path: str | None = None,
                 hydro_step: float = 0.1) -> dict:
    """Run the design chain for one task book; returns the summary dict.

    Pure computation and stdout formatting live apart: this function
    only computes and returns; the caller decides how to render.
    With hydro_curve_chart set, also renders the task 4.1 hydrostatic
    curves chart (a finer draft table than the summary CSV, same
    task 1.4 computation).  With report_path / arrangement_dxf_path
    set, writes the task 4.3 Markdown design report and the task 4.2
    layered DXF arrangement schematic.
    """
    data = _load_taskbook(Path(taskbook_path))
    spec, design_draft_declared = _ship_spec_from_taskbook(data)
    draft_is_hard = bool(
        ((data.get("requirements") or {}).get("drafts") or {})
        .get("draft_is_hard", False))

    # TWO contract modes for the declared draft (R2-A, owner-approved
    # 2026-09-25).  Default: the weight-balance draft is authoritative
    # and a mismatch beyond 5 cm is REPORTED, never silently mixed.
    # `draft_is_hard: true`: the declared draft is the constraint —
    # B/T is bisected on the converged balance (L/B and Cb held) so the
    # ship IS designed to the declared waterline; an unreachable draft
    # is refused with the band endpoints.
    if draft_is_hard:
        balance = solve_weight_balance_for_draft(spec, design_draft_declared)
    else:
        balance = solve_weight_balance(spec)

    design_draft = balance.draft
    draft_mismatch_m = design_draft_declared - design_draft

    # Plan-0 hint (owner-approved 2026-09-24): a declared draft the
    # balance cannot honour is reported WITH the back-solved B/T the
    # declaration would need, so the reader gets an actionable number
    # instead of "adjust something".  The statistics and the guards are
    # untouched - this only states one explicit rule's consequence.
    draft_hint = None
    if abs(draft_mismatch_m) > 0.05:
        current_b_over_t = balance.beam / balance.draft
        lo, hi = B_OVER_T_BAND
        # judge the value the reader would type into a task book, so a
        # boundary value shown as in-band is one the guard accepts
        required_b_over_t = round(required_b_over_t_at_draft(
            b_over_t=current_b_over_t,
            draft_m=balance.draft,
            target_draft_m=design_draft_declared,
        ), 3)
        draft_hint = {
            "rule": (
                "hold displacement volume, Cb and L/B (L and B both "
                "scale): B/T = B/T_now * (T_now / T_declared)^1.5"
            ),
            "current_b_over_t": round(current_b_over_t, 3),
            "required_b_over_t": required_b_over_t,
            "b_over_t_band": [lo, hi],
            "within_band": lo <= required_b_over_t <= hi,
            # the ratio is an algorithm statistic, not a task-book
            # field - say so, or an agent will invent a YAML key
            "action_note": (
                "B/T is a statistic of the dimension algorithm; the "
                "task book has no field for it.  To act on this: adjust "
                "the declared draft, deadweight or Cb and re-run, or "
                "run the Python API with RatioParameters(b_over_t=...)."
            ),
            # and say how good the number is: the back-solve holds the
            # CURRENT displacement volume, the weight balance does not
            "one_shot_note": (
                "one-shot estimate: the weight balance re-iterates on "
                "the new dimensions, so re-solving with this ratio lands "
                "short of the declared draft in the direction of the "
                "current balance draft - residual of the same order as "
                "the declaration offset (0.3-1.3 % measured on the "
                "45,000 t probe, e.g. declared 12.5 m -> 12.409 m)."
            ),
        }

    # stage-2 chain (task 2.6): REAL offsets — the packaged digitised
    # Series 60 parent, affine-scaled onto the balanced dimensions and
    # Lackenby-transformed onto the task-book block coefficient
    hull, transform = parent_to_taskbook(
        lpp=balance.lpp,
        beam=balance.beam,
        draft=balance.draft,
        target_cb=spec.cb,
    )
    drafts = hydrostatic_draft_rows(hull, design_draft,
                                    _table_fractions(hydro_step))
    hydro_table = hydrostatics_table(hull, drafts)
    hydro_design = hydro_table.at(drafts[-1])

    # large-angle stability (plan tasks 3.4/3.5): runs when the task
    # book carries the loading KG; the deck closes the sections at the
    # moulded depth (wall-sided above the top tabulated waterline) and
    # the IS Code 2.2 criteria are evaluated on the curve
    gz_summary = None
    criteria_summary = None
    kg_value = (data.get("requirements") or {}).get("kg_m")
    if kg_value is not None:
        gz = gz_curve(
            hull,
            balance.displacement_t,
            float(kg_value),
            depth_m=balance.depth,
        )
        gz_summary = gz.to_dict()
        flooding = (
            ((data.get("constraints") or {}).get("stability") or {})
            .get("flooding_angle_deg")
        )
        criteria = intact_stability_criteria(
            hull,
            balance.displacement_t,
            float(kg_value),
            depth_m=balance.depth,
            flooding_angle_deg=None if flooding is None else float(flooding),
        )
        criteria_summary = criteria.to_dict()
        weather_block = (
            ((data.get("constraints") or {}).get("stability") or {})
            .get("weather_criterion")
        )
        weather_assumed = None
        if isinstance(weather_block, str) and weather_block.strip() == "default":
            # P1-5 (review 2026-09-25): a conservative-ASSUMPTION default
            # so the first run answers the wind criterion instead of
            # leaving section 4 empty.  Every line is an [ASSUMED]
            # geometric derivation, the same pattern the JBC task book
            # declares by hand:
            #   windage area   = Lpp x freeboard (aft deckhouse neglected
            #                    - the UNCONSERVATIVE direction, stated);
            #   windage lever  = depth/2 (centre of A at T + F/2 above
            #                    keel, minus the IS Code half-draft point);
            #   bilge keels    = 0 (round bilge, k = 1.0);
            #   waterline      = Ayre's standard 1.025 x Lpp.
            freeboard = balance.depth - balance.draft
            weather_block = {
                "windage_area_m2": balance.lpp * freeboard,
                "windage_lever_z_m": balance.depth / 2.0,
                "bilge_keel_area_m2": 0.0,
                "length_waterline_m": 1.025 * balance.lpp,
            }
            weather_assumed = {
                "windage_area_m2": round(balance.lpp * freeboard, 1),
                "windage_lever_z_m": round(balance.depth / 2.0, 2),
                "freeboard_m": round(freeboard, 2),
            }
        weather_summary = None
        if isinstance(weather_block, dict) and weather_block.get(
            "windage_area_m2"
        ) is not None:
            weather = weather_criterion(
                hull,
                balance.displacement_t,
                float(kg_value),
                depth_m=balance.depth,
                windage_area_m2=float(weather_block["windage_area_m2"]),
                windage_lever_z_m=float(weather_block["windage_lever_z_m"]),
                bilge_keel_area_m2=float(
                    weather_block.get("bilge_keel_area_m2") or 0.0
                ),
                length_waterline_m=(
                    None if weather_block.get("length_waterline_m") is None
                    else float(weather_block["length_waterline_m"])
                ),
                flooding_angle_deg=(
                    None if flooding is None else float(flooding)
                ),
            )
            weather_summary = weather.to_dict()
            if weather_assumed is not None:
                weather_summary["assumed_inputs"] = weather_assumed

    propeller_summary = _design_propeller_at_service(data, balance, hydro_design)

    # task 3.8 stage-1 seakeeping estimate: natural periods and the
    # roll resonance verdicts against the two reference sea bands.
    # Roll uses the GM WITHOUT free-surface correction (regulation
    # usage, Ship Theory vol. 2 p.391); requires the task-book KG.
    seakeeping_summary = None
    seakeeping_block = (data.get("seakeeping") or {})
    if kg_value is not None:
        wave_periods = seakeeping_block.get("wave_periods")
        if wave_periods:
            seas = tuple(
                (float(t), f"task-book sea (T {float(t):g} s)")
                for t in wave_periods)
        else:
            seas = None  # the standard reference seas
        try:
            seakeep = estimate_seakeeping(
                beam_m=balance.beam,
                draft_m=balance.draft,
                zg_m=float(kg_value),
                gm_m=criteria.gm0_m + criteria.free_surface_correction_m,
                cb=spec.cb,
                cwp=hydro_design.cw,
                speed_ms=spec.service_speed or 0.0,
                **({"reference_seas": seas} if seas else {}),
            )
            seakeeping_summary = seakeep.to_dict()
        except SpecValidationError:
            seakeeping_summary = None
        # P1-1b (review 2026-09-25): wire the whitelisted Kwon speed-loss
        # method into the chain - the library has had it since 2026-09-23
        loss_block = seakeeping_block.get("speed_loss")
        if seakeeping_summary is not None and isinstance(loss_block, dict):
            try:
                percent, ratio = kwon_speed_loss_percent(
                    cb=spec.cb,
                    fr=(spec.service_speed
                        / math.sqrt(GRAVITY * balance.lpp)),
                    bn=float(loss_block.get("beaufort", 0)),
                    nabla_m3=balance.displacement_t / 1.025,
                    direction=str(loss_block.get("direction", "head")),
                    ship_type=str(loss_block.get("ship_type", "general")),
                    loading=str(loss_block.get("loading", "loaded")),
                )
                seakeeping_summary["speed_loss"] = {
                    "method": "Kwon (JMSE 2025 transcription; Kwon 1981)",
                    "beaufort": float(loss_block.get("beaufort", 0)),
                    "direction": str(loss_block.get("direction", "head")),
                    "delta_v_percent": round(percent, 2),
                    "speed_ratio_v2_v1": round(ratio, 4),
                    "speed_loss_kn": round(
                        (spec.service_speed or 0.0) / 0.514444
                        * percent / 100.0, 2),
                }
            except SpecValidationError as refused:
                seakeeping_summary["speed_loss"] = {
                    "skipped": True, "reason": str(refused)}

    hydro_curve_chart_path = None
    if hydro_curve_chart:
        from .hydrostatics_chart import write_hydrostatic_curves_chart
        chart_fractions = [0.2 + 0.1 * i for i in range(9)]  # 0.2T..1.0T
        chart_drafts = hydrostatic_draft_rows(
            hull, design_draft, chart_fractions)
        chart_table = hydrostatics_table(hull, chart_drafts)
        hydro_curve_chart_path = str(write_hydrostatic_curves_chart(
            chart_table, hydro_curve_chart,
            title=str(data.get("taskbook_id") or "")))

    from .arrangement import (
        arrangement_from_taskbook,
        export_arrangement_dxf,
        write_arrangement_chart,
    )
    arrangement = arrangement_from_taskbook(
        data, lpp_m=balance.lpp, depth_m=balance.depth,
        beam_m=balance.beam)
    arrangement_dxf_written = None
    if arrangement_dxf_path:
        arrangement_dxf_written = str(
            export_arrangement_dxf(arrangement, arrangement_dxf_path))
    arrangement_chart_written = None
    if arrangement_chart_path:
        arrangement_chart_written = str(write_arrangement_chart(
            arrangement, arrangement_chart_path,
            title=str(data.get("taskbook_id") or "")))

    summary = {
        "taskbook_id": data.get("taskbook_id", ""),
        "ship_type": spec.ship_type,
        "hull_source": (
            "digitised Series 60 parent (DTMB 1712 Table 7) affine-scaled "
            "+ Lackenby"
        ),
        "transform_passes": transform.iterations,
        "cb_target": spec.cb,
        "cb_achieved": round(transform.achieved.get("cb", float("nan")), 4),
        "deadweight_t": balance.deadweight_t,
        "algorithm_id": balance.algorithm_id,
        "displacement_t": round(balance.displacement_t, 3),
        "lightship_t": round(balance.lightship_t, 3),
        "norman_coefficient": balance.norman_coefficient,
        "iterations": balance.iterations,
        "lpp_m": round(balance.lpp, 3),
        "beam_m": round(balance.beam, 3),
        "depth_m": round(balance.depth, 3),
        "draft_m": round(balance.draft, 3),
        "draft_declared_m": round(design_draft_declared, 3),
        "draft_is_hard": draft_is_hard,
        "hard_draft_b_over_t": balance.solved_b_over_t,
        "hard_draft_iterations": balance.hard_draft_iterations,
        "draft_mismatch_m": (
            round(draft_mismatch_m, 3)
            if abs(draft_mismatch_m) > 0.05 else None),
        "draft_mismatch_hint": draft_hint,
        "deadweight_ratio_achieved": round(
            balance.deadweight_ratio_achieved, 4
        ),
        "citation": balance.citation,
        "hydrostatics": _hydrostatics_rows(hydro_table),
        "gz_curve": gz_summary,
        "stability_criteria": criteria_summary,
        "weather_criterion": weather_summary,
        "propeller_design": propeller_summary,
        "seakeeping": seakeeping_summary,
        "hydrostatic_curve_chart": hydro_curve_chart_path,
        "arrangement": arrangement.to_dict(),
    }

    if report_path:
        from .report import write_report_md
        written = write_report_md(
            summary, report_path, chart_path=hydro_curve_chart_path,
            arrangement_summary=arrangement.to_dict())
        summary["report_path"] = str(written)
    if arrangement_dxf_written:
        summary["arrangement_dxf"] = arrangement_dxf_written
    if arrangement_chart_written:
        summary["arrangement_chart"] = arrangement_chart_written
    return summary
    return summary


def _print_summary(summary: dict) -> None:
    hydro = summary["hydrostatics"]
    design = hydro[-1]
    print("=" * 64)
    print(f"OpenHull run - {summary['taskbook_id'] or '(task book)'}")
    print("=" * 64)
    print(f"algorithm           : {summary['algorithm_id']}")
    print(f"deadweight          : {summary['deadweight_t']:>12.1f} t")
    print(f"displacement        : {summary['displacement_t']:>12.1f} t")
    print(f"lightship           : {summary['lightship_t']:>12.1f} t")
    print(f"balance iterations  : {summary['iterations']:>12d}")
    if summary["norman_coefficient"] is not None:
        print(f"norman coefficient  : {summary['norman_coefficient']:>12.3f}")
    print(
        f"Lpp / B / D / T     : "
        f"{summary['lpp_m']:.2f} / {summary['beam_m']:.2f} / "
        f"{summary['depth_m']:.2f} / {summary['draft_m']:.2f} m"
    )
    print(f"deadweight ratio    : {summary['deadweight_ratio_achieved']:>12.4f}")
    if summary.get("draft_is_hard"):
        print(f"draft hard          : designed to the declared "
              f"{summary['draft_declared_m']:.3f} m "
              f"(B/T solved to {summary['hard_draft_b_over_t']:.4f} in "
              f"{summary['hard_draft_iterations']} balance probes)")
    if summary.get("draft_mismatch_m") is not None:
        print(f"draft declared      : {summary['draft_declared_m']:>12.3f} m "
              f"vs balance {summary['draft_m']:.3f} m "
              f"(mismatch {summary['draft_mismatch_m']:+.3f} m; results use "
              f"the balance draft)")
        hint = summary.get("draft_mismatch_hint")
        if hint:
            lo, hi = hint["b_over_t_band"]
            print(f"  B/T at declared   : {hint['required_b_over_t']:>12.3f} "
                  f"(current {hint['current_b_over_t']:.3f}; "
                  f"{'inside' if hint['within_band'] else 'OUTSIDE'} "
                  f"guard band {lo:.2f}-{hi:.2f})")
    print("-" * 64)
    print(f"hydrostatics at {design['draft_m']:.2f} m "
          f"({summary['hull_source']}, {summary['transform_passes']} passes):")
    print(f"  cb achieved          {design['cb']:>10.4f} "
          f"(target {summary['cb_target']:.4f})")
    print(f"  displacement volume {design['displacement_volume_m3']:>10.1f} m3")
    print(
        f"  KM = KB + BMT      {design['km_m']:>10.3f} m "
        f"(KB {design['kb_m']:.3f} + BMT {design['bmt_m']:.3f})"
    )
    print(f"  TPC                {design['tpc_t_per_cm']:>10.2f} t/cm")
    print(f"  LCB                {design['lcb_pct_lpp']:>+10.4f} %Lpp")
    gz = summary.get("gz_curve")
    if gz is not None:
        print("-" * 64)
        print(
            f"large-angle stability at KG {gz['kg_m']:.2f} m "
            f"(displacement {gz['displacement_t']:.1f} t, "
            f"equal-volume waterlines <= {gz['volume_tolerance']:.1%}):"
        )
        print("   phi    GZ(m)  shape l_s  dynamic arm")
        for point in gz["points"]:
            print(
                f"  {point['angle_deg']:4.0f}deg {point['gz_m']:>7.3f} "
                f"{point['shape_arm_m']:>10.3f} "
                f"{point['dynamic_arm_mrad']:>11.4f} m*rad"
            )
        vanishing = gz["angle_vanishing_deg"]
        vanishing_text = (
            f"{vanishing:.1f}deg" if vanishing is not None else "> 80deg"
        )
        print(
            f"  max GZ {gz['gz_max_m']:.3f} m at "
            f"{gz['angle_max_deg']:.1f}deg; vanishing angle "
            f"{vanishing_text}"
        )
    criteria = summary.get("stability_criteria")
    if criteria is not None:
        print("-" * 64)
        print(f"intact stability criteria - {criteria['rule']}:")
        for entry in criteria["criteria"]:
            verdict = "PASS" if entry["passed"] else "FAIL"
            print(
                f"  {entry['criterion_id']:18s} "
                f"required {entry['required']:>8.3f} {entry['unit']:6s} "
                f"actual {entry['actual']:>9.4f}  {verdict}"
            )
        print(
            f"  GM0 {criteria['gm0_m']:.3f} m (KG "
            f"{criteria['kg_m']:.2f} m); overall: "
            f"{'ALL PASS' if criteria['all_passed'] else 'FAILURES PRESENT'}"
        )
    weather = summary.get("weather_criterion")
    if weather is not None:
        print("-" * 64)
        print(f"severe wind and rolling - {weather['rule']}:")
        print(
            f"  A {weather['windage_area_m2']:.0f} m2 at Z "
            f"{weather['windage_lever_z_m']:.2f} m, P "
            f"{weather['wind_pressure_pa']:.0f} Pa -> "
            f"lw1 {weather['lw1_m'] * 1000:.1f} mm, "
            f"lw2 {weather['lw2_m'] * 1000:.1f} mm"
        )
        print(
            f"  roll: T {weather['roll_period_s']:.2f} s, phi_1 "
            f"{weather['phi1_deg']:.2f} deg; steady heel phi_0 "
            f"{weather['phi0_deg']:.3f} deg (deck edge at "
            f"{weather['deck_edge_angle_deg']:.2f} deg)"
        )
        print(
            f"  area a {weather['area_a_mrad']:.4f} vs b "
            f"{weather['area_b_mrad']:.4f} m*rad; overall: "
            f"{'ALL PASS' if weather['all_passed'] else 'FAILURES PRESENT'}"
        )
    seakeep = summary.get("seakeeping")
    if seakeep is not None:
        print("-" * 64)
        print("seakeeping first-level estimate (task 3.8 stage 1):")
        print(
            f"  roll natural period   {seakeep['roll_period_s']:>7.2f} s "
            f"(simple form {seakeep['roll_period_simple_s']:.2f} s)"
        )
        print(
            f"  pitch / heave periods {seakeep['pitch_period_s']:>7.2f} s / "
            f"{seakeep['heave_period_s']:.2f} s"
        )
        print(
            f"  effective wave slope K {seakeep['effective_wave_slope_k']:.3f}; "
            f"resonant roll amplification 1/(2 mu) = "
            f"{seakeep['roll_amplification_resonant']:.1f} at mu "
            f"{seakeep['roll_mu']:.2f}"
        )
        for check in seakeep["resonance_checks"]:
            verdict = (
                "RESONANCE BAND"
                if check["in_resonance_band"] else "outside band"
            )
            print(
                f"  {check['motion']:12s} vs T "
                f"{check['wave_period_s']:.0f} s: Lambda "
                f"{check['tuning_factor']:.2f} -> {verdict}"
            )
        loss = seakeep.get("speed_loss")
        if loss and not loss.get("skipped"):
            print(f"  speed loss (Kwon)  : BN {loss['beaufort']:.0f} "
                  f"{loss['direction']} -> -{loss['delta_v_percent']:.1f}% "
                  f"(V2/V1 {loss['speed_ratio_v2_v1']})")
        elif loss and loss.get("skipped"):
            print(f"  speed loss (Kwon)  : refused - "
                  f"{' '.join(str(loss['reason']).split())[:90]}")
        print("-" * 64)
        # P0-3 (review 2026-09-25): stdout is the agent-facing contract —
    # the chain's terminal product (power, diameter, efficiency) must
    # appear here in ALL its states, not only in the report/JSON.
    prop = summary.get("propeller_design")
    print("-" * 64)
    print("speed & propeller (task 3.3):")
    if prop is None:
        print("  propeller         : not requested (no propeller block "
              "in the task book)")
    elif prop.get("skipped"):
        first = " ".join(str(prop.get("reason", "")).split())[:110]
        print(f"  propeller         : REFUSED at {prop.get('stage')} - "
              f"{first}")
        print("  details           : see --report (structured refusal) "
              "or --json")
    else:
        print(f"  propeller         : {prop.get('series')}, "
              f"D {prop.get('diameter_m')} m, P/D {prop.get('pitch_ratio')}, "
              f"eta_o {prop.get('eta_open_water')}")
        print(f"  power             : PD {prop.get('delivered_power_kw'):,.1f} kW"
              f" / PS {prop.get('shaft_power_kw'):,.1f} kW at "
              f"{prop.get('service_speed_kn')} kn")
        cav = prop.get("cavitation")
        unchecked = prop.get("cavitation_unchecked")
        if cav is not None:
            state = "ok" if cav.get("ok") else "NOT ok (area short)"
            print(f"  cavitation        : sigma {cav.get('sigma_0_7r')} "
              f"CHECKED {state}")
        elif unchecked is not None:
            side = ("low side = higher cavitation risk"
                    if unchecked.get("side") == "low"
                    else "high side = conservative direction")
            print(f"  cavitation        : UNCHECKED - sigma "
                  f"{unchecked.get('sigma_0_7r')} outside the verified band "
                  f"{unchecked.get('band')[0]}-{unchecked.get('band')[1]} "
                  f"({side})")
        else:
            print("  cavitation        : not run (no shaft immersion "
                  "declared)")
        sens = prop.get("resistance_sensitivity")
        if sens and sens.get("in_c0_peak_zone"):
            print(f"  sensitivity       : C0 PEAK ZONE (family peak "
                  f"{sens.get('c0_family_peak_v_sqrt_l')}, local slope "
                  f"{sens.get('c0_local_slope_pct_per_0p05'):+.1f}%/0.05, "
                  f"Ac corridor {sens.get('admiralty_corridor')}) - "
                  f"single-point power is trend-unreliable here")
    print("JSON summary and CSV available via --json / --csv redirection.")


def _print_json(summary: dict) -> None:
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def _write_json(summary: dict, path: str) -> None:
    """P2-1: --json PATH writes the document instead of stdout."""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, indent=2, ensure_ascii=False))


def _write_csv(summary: dict, path: str) -> None:
    """P2-1: --csv PATH writes the UTF-8-SIG table instead of stdout."""
    labels = [label for _, label in _HYDRO_COLUMNS]
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(labels)
        for row in summary["hydrostatics"]:
            writer.writerow([f"{row[label]:.4f}" for label in labels])


def _print_csv(summary: dict) -> None:
    """Stream the CSV as UTF-8-SIG bytes: redirection on any console
    codepage (GBK included) lands Excel-ready bytes in the file."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    labels = [label for _, label in _HYDRO_COLUMNS]
    writer.writerow(labels)
    for row in summary["hydrostatics"]:
        writer.writerow([f"{row[label]:.4f}" for label in labels])
    sys.stdout.buffer.write(buffer.getvalue().encode("utf-8-sig"))
    sys.stdout.buffer.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="openhull",
        description="Agent-orchestrated ship preliminary design (stage 1).",
    )
    parser.add_argument(
        "--version", action="version", version=f"openhull {_package_version()}"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser(
        "run", help="run the design chain for one task book (YAML)"
    )
    run.add_argument("taskbook", help="path to the task book YAML")
    # P2-1 (review 2026-09-25): the two outputs are no longer mutually
    # exclusive and both accept an optional PATH - bare flag keeps the
    # historical stdout behaviour, `--json out.json` / `--csv out.csv`
    # write the file instead
    run.add_argument(
        "--csv", nargs="?", const=True, default=None, metavar="CSV_PATH",
        help="hydrostatics table as CSV: bare flag prints to stdout, "
             "--csv PATH writes the file (UTF-8-SIG, Excel-ready)",
    )
    run.add_argument(
        "--json", nargs="?", const=True, default=None, metavar="JSON_PATH",
        help="full result as JSON: bare flag prints to stdout, "
             "--json PATH writes the file",
    )
    run.add_argument(
        "--csv-step", type=float, default=0.1, metavar="FRACTION",
        help="draft step of the hydrostatics table as a fraction of the "
             "design draft (default 0.1 -> 10 rows, aligned with the "
             "curves chart; 0.25 -> the historical 4 rows); affects the "
             "CSV and JSON table alike",
    )
    run.add_argument(
        "--hydro-curve-chart", default=None, metavar="PATH",
        help="also render the hydrostatic curves chart (task 4.1) to "
             "an image file (e.g. hydrostatic_curves.png)",
    )
    run.add_argument(
        "--report", default=None, metavar="PATH",
        help="also write the Chinese Markdown design report (task 4.3)",
    )
    run.add_argument(
        "--arrangement-dxf", default=None, metavar="PATH",
        help="also export the layered DXF arrangement schematic "
             "(task 4.2)",
    )
    run.add_argument(
        "--arrangement-chart", default=None, metavar="PATH",
        help="also render the arrangement schematic chart (task 4.2)",
    )
    opt = sub.add_parser(
        "optimize",
        help="scan the dimension-ratio space for feasible designs "
             "(plan task 3.6)",
    )
    opt.add_argument("taskbook", help="path to the task book YAML")
    opt.add_argument(
        "--grid-lob", default="5.2:7.0:8",
        help="L/B sweep lo:hi:steps (default 5.2:7.0:8)")
    opt.add_argument(
        "--grid-bt", default="2.5:3.5:6",
        help="B/T sweep lo:hi:steps (default 2.5:3.5:6)")
    opt.add_argument(
        "--grid-cb", default="0.81:0.87:4",
        help="Cb sweep lo:hi:steps (default 0.81:0.87:4).  Adjust for "
             "the task book's speed: the Ayre C0 family band rejects "
             "fat hulls at higher speeds, so fast ships (20 kn class) "
             "usually need the grid shifted DOWN; check with `openhull "
             "check` first")
    opt.add_argument(
        "--out", default="optimize_out",
        help="directory for the CSV/JSON/PNG outputs (default "
             "./optimize_out)")
    opt.add_argument(
        "--json", action="store_true",
        help="print the scan summary as JSON",
    )
    check = sub.add_parser(
        "check",
        help="preflight one task book: main dimensions + guard bands in "
             "seconds (P1-3)",
    )
    check.add_argument("taskbook", help="path to the task book YAML")
    check.add_argument(
        "--json", nargs="?", const=True, default=None, metavar="JSON_PATH",
        help="machine-readable gate list: bare flag prints to stdout, "
             "--json PATH writes the file.  Exit code: 0 all gates "
             "predicted pass, 1 a refusal is predicted.")
    rao = sub.add_parser(
        "rao",
        help="zero-speed rigid-body RAOs via capytaine "
             "(task 3.8 stage 2; needs openhull[seakeeping])",
    )
    rao.add_argument("taskbook", help="path to the task book YAML")
    rao.add_argument(
        "--periods", default="5,6,7,8,10,12,16,20",
        help="comma-separated wave periods in seconds "
             "(default 5,6,7,8,10,12,16,20)")
    rao.add_argument(
        "--json", action="store_true",
        help="print the RAO result as JSON",
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "run":
            summary = run_taskbook(args.taskbook,
                                   hydro_curve_chart=args.hydro_curve_chart,
                                   report_path=args.report,
                                   arrangement_dxf_path=args.arrangement_dxf,
                                   arrangement_chart_path=args.arrangement_chart,
                                   hydro_step=args.csv_step)
            # P2-1: the file forms combine freely; stdout can serve
            # only one stream, so two bare flags are an argument error
            if args.json is True and args.csv is True:
                raise RuntimeError(
                    "--json and --csv cannot both stream to stdout; "
                    "give at least one of them a PATH")
            if args.csv and args.csv is not True:
                _write_csv(summary, args.csv)
            elif args.csv:
                _print_csv(summary)
            if args.json and args.json is not True:
                _write_json(summary, args.json)
            elif args.json:
                _print_json(summary)
            if not args.json and not args.csv:
                _print_summary(summary)
            # artefact confirmations go to stderr: stdout must stay a
            # pure JSON document (--json) or a pure CSV stream (--csv)
            # so both remain pipeable (review 2026-09-24, N4)
            for label, key in (
                    ("hydrostatic curves chart", "hydrostatic_curve_chart"),
                    ("design report", "report_path"),
                    ("arrangement DXF", "arrangement_dxf"),
                    ("arrangement chart", "arrangement_chart")):
                if summary.get(key):
                    print(f"{label} -> {summary[key]}", file=sys.stderr)
        elif args.command == "optimize":
            _run_optimize(args)
        elif args.command == "check":
            return _run_check(args)
        elif args.command == "rao":
            _run_rao(args)
    except SpecValidationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 3
    return 0


def _run_rao(args) -> None:
    """Zero-speed rigid-body RAOs on the transformed real hull (3.8-2)."""
    from .seakeeping_bem import CapytaineUnavailable, compute_rigid_rao

    data = _load_taskbook(Path(args.taskbook))
    spec, _declared = _ship_spec_from_taskbook(data)
    kg_value = (data.get("requirements") or {}).get("kg_m")
    if kg_value is None:
        raise SpecValidationError(
            "requirements.kg_m", None, "the RAO sweep needs the loading KG",
            "the roll/pitch stiffness needs the loading KG in the "
            "task book.")
    balance = solve_weight_balance(spec)
    hull, _transform = parent_to_taskbook(
        lpp=balance.lpp,
        beam=balance.beam,
        draft=balance.draft,
        target_cb=spec.cb,
    )
    design_draft = balance.draft
    rao_drafts = hydrostatic_draft_rows(hull, design_draft, (0.9, 1.0))
    hydro = hydrostatics_table(hull, rao_drafts).at(rao_drafts[-1])
    periods = [float(p.strip()) for p in str(args.periods).split(",")
               if p.strip()]
    try:
        result = compute_rigid_rao(
            hull, float(design_draft),
            displacement_t=balance.displacement_t,
            kg_m=float(kg_value),
            km_m=hydro.km,
            bml_m=hydro.bml,
            waterplane_area_m2=hydro.aw,
            periods_s=periods,
        )
    except CapytaineUnavailable as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return
    info = result.mesh_info
    print("=" * 64)
    print(f"zero-speed RAOs - {data.get('taskbook_id') or '(task book)'} "
          f"({info['n_faces']} panels, deck at {info['deck_z_m']:.2f} m)")
    print("=" * 64)
    print(f"{'T (s)':>7} | {'heave m/m':>22} | "
          f"{'roll deg/m':>22} | {'pitch deg/m':>22}")
    for seas in ("head", "beam"):
        for period in result.periods_s:
            row = {p.motion: p for p in result.points
                   if p.seas == seas and p.period_s == period}
            print(f"{period:>7.1f} | "
                  f"{row['heave'].rao_abs:>22.3f} | "
                  f"{row['roll'].rao_abs:>22.3f} | "
                  f"{row['pitch'].rao_abs:>22.3f}   ({seas})")




def _parse_axis(spec: str) -> tuple[float, float, int]:
    lo, hi, steps = spec.split(":")
    return float(lo), float(hi), int(steps)


def _run_check(args) -> int:
    """P1-3 (review 2026-09-25): seconds-level preflight.

    Runs ONLY the cheap part of the chain - the weight balance and the
    dimension-ratio algebra - and predicts which guard bands the full
    `run` would trip, with the numbers.  The expensive stages (hull
    transform, IS Code criteria, cavitation, seakeeping) are listed as
    full-chain-only instead of being guessed at.
    """
    data = _load_taskbook(Path(args.taskbook))
    spec, declared_draft = _ship_spec_from_taskbook(data)
    hard = bool(((data.get("requirements") or {}).get("drafts") or {})
                .get("draft_is_hard", False))
    gates: list[dict] = []

    def gate(name, value, band, unit=""):
        ok = within_band(value, *band)
        gates.append({"gate": name, "value": round(value, 4),
                      "band": list(band), "pass": ok, "unit": unit})
        return ok

    if hard:
        balance = solve_weight_balance_for_draft(spec, declared_draft)
        hard_note = (f"hard draft {declared_draft:.3f} m -> B/T solved "
                     f"{balance.solved_b_over_t:.4f} in "
                     f"{balance.hard_draft_iterations} probes")
    else:
        balance = solve_weight_balance(spec)
        hard_note = None
    mismatch = abs(declared_draft - balance.draft)

    balance_gate = {"gate": "weight balance",
                    "value": round(balance.imbalance_ratio * 100, 4),
                    "band": ["<= 0.1 %", "converged"], "pass": True,
                    "unit": "% |W-B|/W"}
    gates.insert(0, balance_gate)

    lpp, disp = balance.lpp, balance.displacement_t
    gate("Froude number",
         spec.service_speed / math.sqrt(GRAVITY * lpp), FN_BAND)
    gate("L/B", lpp / balance.beam, L_OVER_B_BAND)
    gate("B/T", balance.beam / balance.draft, B_OVER_T_BAND)
    gate("L/D", lpp / balance.depth, L_OVER_DEPTH_BAND)
    v_sqrt_l = _service_kn(spec) / math.sqrt(lpp / 0.3048)
    gate("Ayre speed band V/sqrt(L)", v_sqrt_l,
         (AYRE_V_SQRT_L_MIN, AYRE_V_SQRT_L_MAX), "kn/sqrt-ft")
    length_ratio = lpp / disp ** (1.0 / 3.0)
    gate("Ayre C0 family band L/Delta^(1/3)", length_ratio,
         C0_FAMILY_BAND, "(Delta in tonnes)")
    if hard:
        # the hard solve either converged above or raised: no draft gate
        gates.append({"gate": "declared draft (hard)",
                      "value": round(mismatch, 3),
                      "band": ["converged to ±0.01 m"], "pass": True,
                      "unit": "m"})
    else:
        # soft mode: a mismatch beyond 5 cm is REPORTED, never fatal
        gates.append({"gate": "declared draft vs balance",
                      "value": round(mismatch, 3),
                      "band": ["<= 0.05 m, else reported"],
                      "pass": True, "fatal": False, "unit": "m",
                      "warn": mismatch > 0.05})

    refused = [g for g in gates if not g["pass"]]
    payload = {
        "taskbook_id": data.get("taskbook_id", ""),
        "hard_draft": hard,
        "hard_draft_note": hard_note,
        "lpp_m": round(lpp, 3), "beam_m": round(balance.beam, 3),
        "depth_m": round(balance.depth, 3),
        "draft_m": round(balance.draft, 3),
        "declared_draft_m": round(declared_draft, 3),
        "displacement_t": round(disp, 3),
        "gates": gates,
        "predicted_refusals": len(refused),
    }
    if getattr(args, "json", None):
        if args.json is not True:
            with open(args.json, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, indent=2,
                                        ensure_ascii=False))
        else:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 1 if refused else 0

    print("=" * 64)
    print(f"OpenHull check - {payload['taskbook_id'] or '(task book)'} "
          f"(preflight: main dimensions + guard bands)")
    print("=" * 64)
    print(f"Lpp / B / D / T     : {lpp:.2f} / {balance.beam:.2f} / "
          f"{balance.depth:.2f} / {balance.draft:.3f} m"
          f"   ({hard_note or 'soft draft mode'})")
    for g in gates:
        band = g["band"]
        band_txt = (f"[{band[0]}, {band[1]}]"
                    if not isinstance(band[0], str) else str(band))
        if not g["pass"]:
            state = "REFUSED (predicted)"
        elif g.get("warn"):
            state = "WARN (reported in run, not fatal)"
        else:
            state = "PASS"
        print(f"{g['gate']:<24s}: {g['value']:>10.4f} {band_txt:<24s} "
              f"{state}")
    if refused:
        print("-" * 64)
        print(f"verdict             : {len(refused)}/{len(gates)} gates "
              f"predict a refusal - adjust the task book above before "
              f"running; `openhull optimize` can sweep the feasible "
              f"region")
        return 1
    print("-" * 64)
    print("verdict             : all gates predicted PASS -> run the "
          "full chain")
    print("full-chain only     : IS Code 2.2/2.3 criteria, cavitation "
          "check, seakeeping, propeller stage")
    return 0


def _service_kn(spec) -> float:
    return spec.service_speed * 3600.0 / 1852.0


def _run_optimize(args) -> None:
    data = _load_taskbook(Path(args.taskbook))
    spec, _design_draft = _ship_spec_from_taskbook(data)
    requirements = data.get("requirements") or {}
    stability = (data.get("constraints") or {}).get("stability") or {}
    weather_block = stability.get("weather_criterion") or {}
    if isinstance(weather_block, str) and weather_block.strip() == "default":
        # P1-5: resolve the assumed default against the task book's OWN
        # ship (the base-spec balance), then the declared scan
        # limitation applies to those numbers unchanged across candidates
        base_balance = solve_weight_balance(spec)
        freeboard = base_balance.depth - base_balance.draft
        weather_block = {
            "windage_area_m2": base_balance.lpp * freeboard,
            "windage_lever_z_m": base_balance.depth / 2.0,
            "bilge_keel_area_m2": 0.0,
            "length_waterline_m": 1.025 * base_balance.lpp,
        }
    kg_m = requirements.get("kg_m")
    if kg_m is None:
        raise SpecValidationError(
            "requirements.kg_m", None,
            "the stability part of the scan needs the loading KG",
            "the scan evaluates the IS Code criteria per candidate, "
            "which requires the loading KG in the task book.")
    flooding = stability.get("flooding_angle_deg")
    grid = SweepGrid(
        l_over_b=_parse_axis(args.grid_lob),
        b_over_t=_parse_axis(args.grid_bt),
        cb=_parse_axis(args.grid_cb),
    )
    config = ScanConfig(
        kg_m=float(kg_m),
        flooding_angle_deg=None if flooding is None else float(flooding),
        windage_area_m2=weather_block.get("windage_area_m2"),
        windage_lever_z_m=weather_block.get("windage_lever_z_m"),
        bilge_keel_area_m2=float(
            weather_block.get("bilge_keel_area_m2") or 0.0),
        length_waterline_m=weather_block.get("length_waterline_m"),
        shaft_immersion_m=(
            float(propeller_block["shaft_immersion_m"])
            if (propeller_block := (data.get("propeller") or {})).get(
                "shaft_immersion_m") is not None else None),
        propeller_blades=int(
            (data.get("propeller") or {}).get("blades_z", 5)),
        propeller_aear=float(
            (data.get("propeller") or {}).get(
                "expanded_area_ratio", 0.50)),
        propeller_rpm=float(
            (data.get("propeller") or {}).get("rpm") or 127.0),
        relative_rotative_eff=float(
            (data.get("propeller") or {}).get(
                "relative_rotative_eff") or 1.0),
    )

    def progress(done: int, total: int, label: str) -> None:
        # one line per candidate keeps redirected logs readable
        print("[%d/%d] %s" % (done + 1, total, label), flush=True)

    result = design_space_scan(
        spec, kg_m=float(kg_m), grid=grid, config=config,
        progress=None if args.json else progress)
    print()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "feasible_designs.csv"
    rows = result.to_dicts()
    # the feasible CSV is ALWAYS written (header only when empty): a
    # missing file would misreport what the run produced
    keys = list(rows[0].keys()) if rows else [
        "l_over_b", "b_over_t", "cb", "lpp_m", "beam_m", "draft_m",
        "depth_m", "displacement_t", "gm_m", "gz_max_m"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = __import__("csv").DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    # full rejected-point export: the scan's zero-extrapolation promise
    # only reaches the user if the refusals themselves are in the file
    rejected_path = out_dir / "rejected_points.csv"
    with rejected_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = __import__("csv").DictWriter(
            fh, fieldnames=["l_over_b", "b_over_t", "cb", "stage",
                            "reason"])
        writer.writeheader()
        for r in result.rejected:
            writer.writerow({
                "l_over_b": r.l_over_b, "b_over_t": r.b_over_t,
                "cb": r.cb, "stage": r.stage,
                "reason": " ".join(str(r.reason).split())[:200]})
    chart_path = out_dir / "tradeoff_speed_displacement_gm.png"
    write_tradeoff_chart(result, chart_path)
    front = [c.to_dict() for c in __import__(
        "openhull.optimize", fromlist=["pareto_front"]).pareto_front(
        result.feasible)]
    # the stage-only histogram hides WHY points were refused: 192
    # refusals can be "3 systematic gaps + 1 physical conclusion".
    # Export a second breakdown by violating field (parsed from the
    # refusal text) so agents do not report data gaps as design
    # verdicts (review 2026-09-24, section 3)
    import re as _re
    from collections import Counter as _Counter

    def _violating_field(reason) -> str:
        match = _re.search(r"Invalid value for '([^']+)'", str(reason))
        return match.group(1) if match else "other"

    refusal_fields = dict(sorted(_Counter(
        f"{r.stage}.{_violating_field(r.reason)}"
        for r in result.rejected).items()))
    # the attainable-speed axis is the reference power; a feasible
    # design whose hull already absorbs more than that at the Ayre band
    # floor cannot be placed on it and is refused (not extrapolated).
    # Count them, so the sparse axis is declared rather than discovered
    # (review 2026-09-24, §3 lesson: composition must be visible)
    off_axis = sum(1 for c in result.feasible
                   if c.speed_at_reference_power_kn is None)
    off_causes = result.off_axis_causes()
    summary = {
        "taskbook_id": data.get("taskbook_id", ""),
        "grid": {"l_over_b": args.grid_lob, "b_over_t": args.grid_bt,
                 "cb": args.grid_cb},
        "feasible": len(result.feasible),
        "rejected": len(result.rejected),
        "rejection_histogram": result.rejection_histogram(),
        "refusal_fields": refusal_fields,
        "reference_power_kw": result.reference_power_kw,
        "off_reference_axis": off_axis,
        "off_reference_causes": off_causes,
        "pareto_count": len(front),
        "outputs": {"csv": str(csv_path), "rejected_csv":
                    str(rejected_path), "chart": str(chart_path)},
        "designs": rows,
        "rejected_points": [
            {"l_over_b": r.l_over_b, "b_over_t": r.b_over_t, "cb": r.cb,
             "stage": r.stage,
             "reason": " ".join(str(r.reason).split())[:200]}
            for r in result.rejected],
        "pareto": front,
    }
    json_path = out_dir / "scan_summary.json"
    json_path.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    if args.json:
        print(json.dumps(summary, indent=1))
        return
    print("=" * 64)
    print(f"OpenHull optimize - {summary['taskbook_id'] or '(task book)'}")
    print("=" * 64)
    print(f"candidates         : {len(result.feasible) + len(result.rejected)}"
          f"  (feasible {len(result.feasible)}, refused "
          f"{len(result.rejected)})")
    print(f"refusal histogram  : {result.rejection_histogram()}")
    if refusal_fields:
        print(f"refusal by field   : {refusal_fields}")
    if result.reference_power_kw is None:
        print("reference power    : unavailable (no feasible design)")
    else:
        print(f"reference power    : "
              f"{result.reference_power_kw:,.1f} kW delivered")
    print(f"pareto front       : {len(front)} designs")
    if result.reference_power_kw is not None:
        # per-candidate causes, counted: the population is not
        # single-cause (review 2026-09-24, §3)
        print(f"off reference axis : {off_axis:>4d} of "
              f"{len(result.feasible)} feasible designs "
              f"(excluded from the Pareto test, not extrapolated)")
        if off_causes:
            print(f"  why off-axis     : {off_causes}")
    print(f"outputs            : {csv_path}")
    print(f"                     {rejected_path}")
    print(f"                     {chart_path}")
    print(f"                     {json_path}")


def _package_version() -> str:
    try:
        return version("openhull")
    except PackageNotFoundError:
        return "0.0.0.dev0"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
