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
from .linesplan import parent_to_taskbook
from .propeller import b_series_open_water, check_cavitation, solve_optimal_propeller
from .propulsion import propulsion_factors
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


def run_taskbook(taskbook_path: str) -> dict:
    """Run the design chain for one task book; returns the summary dict.

    Pure computation and stdout formatting live apart: this function
    only computes and returns; the caller decides how to render.
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
    args = parser.parse_args(argv)

    try:
        if args.command == "run":
            summary = run_taskbook(args.taskbook)
            if args.csv:
                _print_csv(summary)
            elif args.json:
                _print_json(summary)
            else:
                _print_summary(summary)
    except SpecValidationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 3
    return 0


def _package_version() -> str:
    try:
        return version("openhull")
    except PackageNotFoundError:
        return "0.0.0.dev0"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
