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
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import yaml

from .geometry import jbc_parent_offsets  # noqa: F401  (1.x fitted parent,
#   kept for the validation tests; the run chain uses real offsets - 2.6)
from .hydrostatics import hydrostatics_table
from .optimize import (
    ScanConfig,
    ScanResult,
    SweepGrid,
    design_space_scan,
    write_tradeoff_chart,
)
from .linesplan import parent_to_taskbook
from .propeller import b_series_open_water, check_cavitation, solve_optimal_propeller
from .propulsion import propulsion_factors
from .seakeeping import estimate_seakeeping
from .resistance import ayre_effective_power
from .spec import knots_to_ms, ShipSpec, SpecValidationError
from .stability import gz_curve, intact_stability_criteria, weather_criterion
from .weight_balance import solve_weight_balance


def _design_propeller_at_service(data, balance, hydro_design):
    """Preliminary propeller design at the task book's service speed.

    Returns a summary dict, or a dict with skipped=True and the reason
    when a whitelisted method refuses the operating point (e.g. the
    Ayre speed-length band does not reach this ship's service speed).
    """
    propeller_block = data.get("propeller") or {}
    if propeller_block.get("rpm") is None:
        return None
    try:
        rpm = float(propeller_block["rpm"])
        n_rps = rpm / 60.0
        z = int(propeller_block.get("blades_z", 5))
        aear = float(propeller_block.get("expanded_area_ratio", 0.50))
        eta_r = float(propeller_block.get("relative_rotative_eff") or 1.0)
        service_kn = float(
            (data.get("requirements") or {}).get("service_speed_kn"))
        v_ms = knots_to_ms(service_kn)
        series = b_series_open_water(z, aear)
        d_guess = 0.7 * balance.draft
        prop = None
        factors = None
        for _ in range(3):
            factors = propulsion_factors(
                lpp_m=balance.lpp,
                lwl_m=balance.lwl_m if hasattr(balance, "lwl_m")
                else balance.lpp,
                beam_m=balance.beam,
                draft_m=balance.draft,
                cb=hydro_design.cb, cp=hydro_design.cp,
                cm=hydro_design.cm, cwp=hydro_design.cw,
                lcb_pct_fwd=hydro_design.lcb,
                propeller_diameter_m=d_guess, speed_ms=v_ms,
                screw="single", eta_r=eta_r,
            )
            pe_kw = ayre_effective_power(
                displacement_t=balance.displacement_t, speed_kn=service_kn,
                lpp_m=balance.lpp, beam_m=balance.beam,
                draft_m=balance.draft, cb=hydro_design.cb,
                xc_pct_fwd=hydro_design.lcb, screw="single",
            ).pe_bare_kw
            va_ms = v_ms * (1.0 - factors.wake_fraction)
            pd_ow = pe_kw / (factors.eta_h * 0.55)   # eta_o first guess
            prop = solve_optimal_propeller(
                pd_ow, va_ms, n_rps, series, n_scan=300)
            d_guess = prop.diameter_m
            for _ in range(3):
                pd_ow = pe_kw / (prop.eta_o * factors.eta_h)
                prop = solve_optimal_propeller(
                    pd_ow, va_ms, n_rps, series, n_scan=300)
        shaft_power_kw = prop.delivered_power_kw / (
            float(propeller_block.get("shaft_efficiency") or 1.0) * eta_r)
        cav = None
        hs_m = propeller_block.get("shaft_immersion_m")
        if hs_m is not None:
            cav = check_cavitation(
                thrust_n=prop.thrust_n, va_ms=prop.va_ms, n_rps=n_rps,
                diameter_m=prop.diameter_m,
                pitch_ratio=prop.pitch_ratio, aeao_available=aear,
                hs_m=float(hs_m))
        result = {
            "series": prop.series_name,
            "provenance": prop.provenance,
            "service_speed_kn": service_kn,
            "rpm": rpm,
            "diameter_m": round(prop.diameter_m, 3),
            "pitch_ratio": round(prop.pitch_ratio, 4),
            "advance_coefficient": round(prop.j, 4),
            "eta_open_water": round(prop.eta_o, 4),
            "eta_hull": round(factors.eta_h, 4),
            "wake_fraction": round(factors.wake_fraction, 4),
            "thrust_deduction": round(factors.thrust_deduction, 4),
            "thrust_n": round(prop.thrust_n, 1),
            "delivered_power_kw": round(prop.delivered_power_kw, 1),
            "shaft_power_kw": round(shaft_power_kw, 1),
            "cavitation": None,
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
    except SpecValidationError as refuse:
        return {"skipped": True, "reason": str(refuse)}

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
                 hydro_curve_chart: str | None = None) -> dict:
    """Run the design chain for one task book; returns the summary dict.

    Pure computation and stdout formatting live apart: this function
    only computes and returns; the caller decides how to render.
    With hydro_curve_chart set, also renders the task 4.1 hydrostatic
    curves chart (a finer draft table than the summary CSV, same
    task 1.4 computation) and reports the written path in the
    summary.
    """
    data = _load_taskbook(Path(taskbook_path))
    spec, design_draft = _ship_spec_from_taskbook(data)

    balance = solve_weight_balance(spec)

    # stage-2 chain (task 2.6): REAL offsets — the packaged digitised
    # Series 60 parent, affine-scaled onto the balanced dimensions and
    # Lackenby-transformed onto the task-book block coefficient
    hull, transform = parent_to_taskbook(
        lpp=balance.lpp,
        beam=balance.beam,
        draft=balance.draft,
        target_cb=spec.cb,
    )
    drafts = [round(design_draft * f, 4) for f in (0.25, 0.5, 0.75, 1.0)]
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

    propeller_summary = _design_propeller_at_service(data, balance, hydro_design)

    # task 3.8 stage-1 seakeeping estimate: natural periods and the
    # roll resonance verdicts against the two reference sea bands.
    # Roll uses the GM WITHOUT free-surface correction (regulation
    # usage, Ship Theory vol. 2 p.391); requires the task-book KG.
    seakeeping_summary = None
    if kg_value is not None:
        try:
            seakeep = estimate_seakeeping(
                beam_m=balance.beam,
                draft_m=balance.draft,
                zg_m=float(kg_value),
                gm_m=criteria.gm0_m + criteria.free_surface_correction_m,
                cb=spec.cb,
                cwp=hydro_design.cw,
                speed_ms=spec.service_speed or 0.0,
            )
            seakeeping_summary = seakeep.to_dict()
        except SpecValidationError:
            seakeeping_summary = None

    hydro_curve_chart_path = None
    if hydro_curve_chart:
        from .hydrostatics_chart import write_hydrostatic_curves_chart
        chart_fractions = [0.2 + 0.1 * i for i in range(9)]  # 0.2T..1.0T
        chart_table = hydrostatics_table(
            hull, [round(design_draft * f, 4) for f in chart_fractions])
        hydro_curve_chart_path = str(write_hydrostatic_curves_chart(
            chart_table, hydro_curve_chart,
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
    }
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
        print("-" * 64)
        print("JSON summary and CSV available via --json / --csv redirection.")


def _print_json(summary: dict) -> None:
    print(json.dumps(summary, indent=2, ensure_ascii=False))


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
    fmt = run.add_mutually_exclusive_group()
    fmt.add_argument(
        "--csv", action="store_true",
        help="print the hydrostatics table as CSV (redirect to a .csv "
        "file; BOM included for Excel)",
    )
    fmt.add_argument(
        "--json", action="store_true",
        help="print the full result as JSON",
    )
    run.add_argument(
        "--hydro-curve-chart", default=None, metavar="PATH",
        help="also render the hydrostatic curves chart (task 4.1) to "
             "an image file (e.g. hydrostatic_curves.png)",
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
        help="Cb sweep lo:hi:steps (default 0.81:0.87:4)")
    opt.add_argument(
        "--out", default="optimize_out",
        help="directory for the CSV/JSON/PNG outputs (default "
             "./optimize_out)")
    opt.add_argument(
        "--json", action="store_true",
        help="print the scan summary as JSON",
    )
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
                                   hydro_curve_chart=args.hydro_curve_chart)
            if args.csv:
                _print_csv(summary)
            elif args.json:
                _print_json(summary)
            else:
                _print_summary(summary)
            if summary.get("hydrostatic_curve_chart"):
                print(f"hydrostatic curves chart -> "
                      f"{summary['hydrostatic_curve_chart']}")
        elif args.command == "optimize":
            _run_optimize(args)
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
    spec, design_draft = _ship_spec_from_taskbook(data)
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
    hydro = hydrostatics_table(hull, [round(design_draft * f, 4)
                                      for f in (0.9, 1.0)]).at(design_draft)
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


def _run_optimize(args) -> None:
    data = _load_taskbook(Path(args.taskbook))
    spec, _design_draft = _ship_spec_from_taskbook(data)
    requirements = data.get("requirements") or {}
    stability = (data.get("constraints") or {}).get("stability") or {}
    weather_block = stability.get("weather_criterion") or {}
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
        print("[%d/%d] %s" % (done + 1, total, label),
              end=" ", flush=True)

    result = design_space_scan(
        spec, kg_m=float(kg_m), grid=grid, config=config,
        progress=None if args.json else progress)
    print()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "feasible_designs.csv"
    rows = result.to_dicts()
    if rows:
        keys = list(rows[0].keys())
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = __import__("csv").DictWriter(fh, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
    chart_path = out_dir / "tradeoff_speed_displacement_gm.png"
    write_tradeoff_chart(result, chart_path)
    front = [c.to_dict() for c in __import__(
        "openhull.optimize", fromlist=["pareto_front"]).pareto_front(
        result.feasible)]
    summary = {
        "taskbook_id": data.get("taskbook_id", ""),
        "grid": {"l_over_b": args.grid_lob, "b_over_t": args.grid_bt,
                 "cb": args.grid_cb},
        "feasible": len(result.feasible),
        "rejected": len(result.rejected),
        "rejection_histogram": result.rejection_histogram(),
        "reference_power_kw": result.reference_power_kw,
        "pareto_count": len(front),
        "outputs": {"csv": str(csv_path), "chart": str(chart_path)},
        "designs": rows,
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
    print(f"reference power    : {result.reference_power_kw} kW delivered")
    print(f"pareto front       : {len(front)} designs")
    print(f"outputs            : {csv_path}")
    print(f"                     {chart_path}")
    print(f"                     {json_path}")


def _package_version() -> str:
    try:
        return version("openhull")
    except PackageNotFoundError:
        return "0.0.0.dev0"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
