"""MCP server surface for OpenHull (v1.7.0).

The constitution (AGENTS.md section 8, "Agent-facing contract") pins the
stable invocation boundary: the CLI plus YAML task books, so that future
MCP servers, skills, or plugins wrap the toolkit without touching the
numerics.  This module is exactly that wrapper: a Model Context Protocol
(MCP) stdio server whose tools shell out to ``python -m openhull.cli``
and return the CLI's JSON stdout contract verbatim.

Why a subprocess wrapper instead of in-process imports:

- the CLI stdout contract is tested cross-process; reusing the CLI as a
  child process inherits exactly that tested behaviour (the 2026-09-24
  lesson: import-time prints can pollute a JSON stream only when the
  consumer shares the process);
- every call starts from a clean process state (matplotlib, capytaine);
- the MCP SDK stays an optional extra (``openhull[mcp]``) imported
  lazily inside :func:`build_server` / :func:`main` — importing this
  module never requires the SDK, mirroring the seakeeping precedent.

Every tool returns a JSON *text* payload::

    {
      "ok": bool,              # exit 0 and stdout parsed as JSON
      "exit_code": int | null, # null only on spawn failure / timeout
      "command": [...],        # the argv passed to openhull.cli
      "result": {...},         # the CLI's JSON document (or raw tail)
      "stderr_tail": "...",    # last 2000 chars: notes, refusals, hints
      "artifacts": {name: absolute path},  # only files that exist
      "error": null | "..."    # timeout / contract-violation explanation
    }

OpenHull discipline carried over unchanged: the toolchain refuses
out-of-applicability inputs with a stated reason instead of guessing,
and every number is traceable to the formula whitelist.  Stability
criteria outcomes are reported, never decided — the naval architect
owns the verdict.

Run ``openhull-mcp`` (console script) or ``python -m openhull.mcp_server``;
register that command in any MCP-capable harness (Codex, ZCode, Claude,
DeepSeek, ...).  Configuration snippets: ``docs/mcp.md``.
"""

import json
import os
import subprocess
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version as _package_version
from importlib.resources import as_file, files
from pathlib import Path

__all__ = [
    "build_server",
    "main",
    "taskbook_template_text",
    "tool_check",
    "tool_optimize",
    "tool_rao",
    "tool_run",
    "tool_version",
]

# conservative per-call ceilings; each tool exposes timeout_s so the
# calling agent can raise it for slow BEM scans
_DEFAULT_TIMEOUT_S = {"check": 120, "run": 900, "optimize": 1800, "rao": 1800}
_STDOUT_TAIL_CHARS = 4000
_STDERR_TAIL_CHARS = 2000

_INSTALL_HINT_MCP = (
    "the MCP SDK is not installed in this environment; install the "
    "optional extra first: pip install 'openhull[mcp]' (or uv tool "
    "install --extra mcp ...)"
)
_INSTALL_HINT_SEAKEEPING = (
    "the rao tool needs the optional seakeeping extra (capytaine): "
    "pip install 'openhull[seakeeping]'"
)


def _cli_version() -> str:
    """Return the ``openhull --version`` banner, or an error string."""
    try:
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "openhull.cli", "--version"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unreachable: {exc}"
    return proc.stdout.strip() if proc.returncode == 0 else f"exit {proc.returncode}"


def tool_version() -> str:
    """Report the toolchain versions and which optional extras are live.

    Inputs: none.  Output: JSON with the OpenHull version, the Python
    running the MCP server, the MCP SDK version, an ``extras`` map
    (``seakeeping`` = capytaine RAOs available, ``mcp`` = this server's
    SDK) and the CLI banner produced by the exact spawn command the
    other tools use.  Call this first when a harness session starts so
    the agent knows which capabilities are installed.
    """
    import importlib.util
    import platform

    extras = {
        "seakeeping": importlib.util.find_spec("capytaine") is not None,
        "mcp": importlib.util.find_spec("mcp") is not None,
    }
    try:
        sdk = _package_version("mcp")
    except PackageNotFoundError:
        sdk = None
    payload = {
        "ok": True,
        "openhull": _package_version("openhull"),
        "python": platform.python_version(),
        "mcp_sdk": sdk,
        "extras": extras,
        "cli": _cli_version(),
        "install_hints": {
            "mcp": _INSTALL_HINT_MCP if not extras["mcp"] else None,
            "seakeeping": (_INSTALL_HINT_SEAKEEPING
                           if not extras["seakeeping"] else None),
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _run_cli(args: list[str], cwd: Path, timeout_s: int) -> dict:
    """Run ``python -m openhull.cli <args>`` and capture the streams.

    Returns ``{ok, exit_code, stdout, stderr, command, error}``.  The
    child is forced to UTF-8 (the GBK-console silent-failure lesson)
    and never shares this process' state.  ``stdin=DEVNULL`` is
    mandatory, not hygiene: this process' stdin is the MCP transport
    pipe, and a child that inherits it deadlocks on Windows (verified
    by a minimal-repro variant matrix — DEVNULL is the single
    unlocking variable).  The CLI never reads stdin, so detaching it
    costs nothing.
    """
    cmd = [sys.executable, "-X", "utf8", "-m", "openhull.cli", *args]
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    base = {
        "ok": False, "exit_code": None, "stdout": "", "stderr": "",
        "command": args, "error": None,
    }
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), env=env, timeout=timeout_s,
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        tail = exc.stderr if isinstance(exc.stderr, str) else ""
        base["stderr"] = tail or ""
        base["error"] = (
            f"CLI timed out after {timeout_s}s; raise timeout_s or shrink "
            "the job (e.g. fewer grid points / periods)")
        return base
    except OSError as exc:
        base["error"] = f"failed to spawn the CLI interpreter: {exc}"
        return base
    base.update(
        ok=proc.returncode == 0, exit_code=proc.returncode,
        stdout=proc.stdout, stderr=proc.stderr,
    )
    return base


def _payload(run: dict, artifacts: dict[str, Path] | None = None,
             note: str | None = None) -> str:
    """Assemble the tool payload: parse stdout JSON, list live files."""
    stdout = run.get("stdout", "")
    result: object
    parsed = False
    if stdout.strip():
        try:
            result = json.loads(stdout)
            parsed = True
        except json.JSONDecodeError:
            result = {"raw_stdout_tail": stdout[-_STDOUT_TAIL_CHARS:]}
    else:
        result = None
    ok = bool(run.get("ok")) and parsed
    error = run.get("error")
    if run.get("ok") and not parsed:
        error = ("CLI exited 0 but stdout is not a JSON document - "
                 "invocation-contract violation; raw tail attached")
    live = {}
    for name, path in (artifacts or {}).items():
        try:
            if path.is_file():
                live[name] = str(path.resolve())
        except OSError:  # unreadable path: never fabricate an artifact
            pass
    payload = {
        "ok": ok,
        "exit_code": run.get("exit_code"),
        "command": run.get("command", []),
        "result": result,
        "stderr_tail": run.get("stderr", "")[-_STDERR_TAIL_CHARS:],
        "artifacts": live,
        "error": error,
    }
    if note:
        payload["note"] = note
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _write_taskbook(taskbook_yaml: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(taskbook_yaml, encoding="utf-8", newline="\n")


def _default_out(output_dir: str, stage: str) -> Path:
    """Resolve the artifact directory (absolute); default cwd/openhull_out.

    An explicitly given ``output_dir`` is used as-is (the caller owns the
    layout); the default is namespaced per stage so repeated ad-hoc
    calls do not mix run and optimize outputs.
    """
    if output_dir:
        return Path(output_dir).expanduser().resolve()
    return (Path.cwd() / "openhull_out" / stage).resolve()


def tool_check(taskbook_yaml: str, timeout_s: int = _DEFAULT_TIMEOUT_S["check"]) -> str:
    """Preflight one task book: gates in seconds, no full design chain.

    Inputs: ``taskbook_yaml`` — the task book YAML *text* (units: m, t,
    kn; SI inside).  Output: JSON whose ``result`` is the CLI's gate
    list; ``refusal_predicted`` is true when at least one guard predicts
    a refusal (the CLI then exits 1 — a meaningful outcome, not a
    failure of this tool).  Call this before run/optimize: OpenHull
    refuses out-of-applicability inputs with a stated reason instead of
    computing a number, so a predicted refusal tells the agent what to
    fix (dimensions, ratios, or the task book itself).
    """
    with tempfile.TemporaryDirectory(prefix="openhull_mcp_check_") as tmp:
        tb = Path(tmp) / "taskbook.yaml"
        _write_taskbook(taskbook_yaml, tb)
        run = _run_cli(["check", str(tb), "--json"], cwd=Path(tmp),
                       timeout_s=timeout_s)
    payload = _payload(run)
    doc = json.loads(payload)
    if (doc["exit_code"] == 1 and doc["result"] is not None
            and doc["error"] is None):
        # a predicted refusal is the preflight doing its job, not a
        # tool failure: the gate list was produced and parsed cleanly
        doc["ok"] = True
    doc["refusal_predicted"] = run.get("exit_code") == 1
    return json.dumps(doc, ensure_ascii=False, indent=2)


def tool_run(
    taskbook_yaml: str,
    output_dir: str = "",
    report: bool = True,
    arrangement_dxf: bool = True,
    arrangement_chart: bool = True,
    hydro_curve_chart: bool = True,
    csv_step: float = 0.1,
    timeout_s: int = _DEFAULT_TIMEOUT_S["run"],
) -> str:
    """Run the full design chain for one task book and collect artifacts.

    Inputs: ``taskbook_yaml`` — task book YAML text (m, t, kn); optional
    ``output_dir`` (absolute path recommended; default
    ``<cwd>/openhull_out/run``); toggles for the report / arrangement
    DXF / arrangement & hydrostatic-curve charts; ``csv_step`` —
    hydrostatic table draft step as a fraction of design draft (default
    0.1 → 10 rows).  Output: JSON whose ``result`` is the full summary
    (main dimensions, weight balance, hydrostatics, stability verdicts,
    resistance & propulsion, propeller, seakeeping) and whose
    ``artifacts`` maps taskbook/result.json/design_report.md/
    ga_schematic.dxf/ga_schematic.png/hydrostatic_curves.png to absolute
    paths that really exist.  Charts degrade to declared notes instead
    of failing the chain.  Every number is whitelist-traceable; refusals
    (with reasons) appear in ``result`` / ``stderr_tail``.
    """
    out = _default_out(output_dir, "run")
    out.mkdir(parents=True, exist_ok=True)
    tb = out / "taskbook.yaml"
    _write_taskbook(taskbook_yaml, tb)
    args = ["run", str(tb), "--json", "--csv-step", str(csv_step)]
    if report:
        args += ["--report", str(out / "design_report.md")]
    if arrangement_dxf:
        args += ["--arrangement-dxf", str(out / "ga_schematic.dxf")]
    if arrangement_chart:
        args += ["--arrangement-chart", str(out / "ga_schematic.png")]
    if hydro_curve_chart:
        args += ["--hydro-curve-chart", str(out / "hydrostatic_curves.png")]
    run = _run_cli(args, cwd=out, timeout_s=timeout_s)
    artifacts = {
        "taskbook": tb,
        "design_report.md": out / "design_report.md",
        "ga_schematic.dxf": out / "ga_schematic.dxf",
        "ga_schematic.png": out / "ga_schematic.png",
        "hydrostatic_curves.png": out / "hydrostatic_curves.png",
    }
    text = _payload(run, artifacts=artifacts)
    doc = json.loads(text)
    if doc["ok"] and doc["result"] is not None:
        result_json = out / "result.json"
        result_json.write_text(json.dumps(doc["result"], ensure_ascii=False,
                                          indent=2), encoding="utf-8")
        if result_json.is_file():
            doc["artifacts"]["result.json"] = str(result_json.resolve())
    return json.dumps(doc, ensure_ascii=False, indent=2)


def tool_optimize(
    taskbook_yaml: str,
    grid_lob: str = "5.2:7.0:8",
    grid_bt: str = "2.5:3.5:6",
    grid_cb: str = "0.81:0.87:4",
    output_dir: str = "",
    timeout_s: int = _DEFAULT_TIMEOUT_S["optimize"],
) -> str:
    """Scan the dimension-ratio space for feasible designs (task 3.6).

    Inputs: task book YAML text; grids as ``lo:hi:steps`` — ``grid_lob``
    (L/B), ``grid_bt`` (B/T), ``grid_cb`` (Cb); ``output_dir`` (default
    ``<cwd>/openhull_out/optimize``).  Output: JSON whose ``result`` is
    the scan summary and whose ``artifacts`` lists every file written to
    the scan directory (CSV table, JSON, PNG map).  Sizing hint: the
    Ayre C0 family band rejects fat hulls at higher speeds — shift the
    Cb grid DOWN for fast ships and preflight with ``openhull_check``.
    Grid volume is steps-cubed; each candidate runs the resistance
    chain, so keep grids small first, then refine.
    """
    out = _default_out(output_dir, "optimize")
    scan = out / "scan"
    out.mkdir(parents=True, exist_ok=True)
    tb = out / "taskbook.yaml"
    _write_taskbook(taskbook_yaml, tb)
    args = ["optimize", str(tb),
            "--grid-lob", grid_lob, "--grid-bt", grid_bt,
            "--grid-cb", grid_cb, "--out", str(scan), "--json"]
    run = _run_cli(args, cwd=out, timeout_s=timeout_s)
    artifacts = {"taskbook": tb}
    if scan.is_dir():
        for path in sorted(scan.iterdir()):
            if path.is_file():
                artifacts[path.name] = path
    return _payload(run, artifacts=artifacts)


def tool_rao(
    taskbook_yaml: str,
    periods: str = "5,6,7,8,10,12,16,20",
    timeout_s: int = _DEFAULT_TIMEOUT_S["rao"],
) -> str:
    """Zero-speed rigid-body RAOs via capytaine (task 3.8 stage 2).

    Inputs: task book YAML text; ``periods`` — comma-separated wave
    periods in seconds (default 5,6,7,8,10,12,16,20).  Output: JSON
    whose ``result`` carries heave/roll/pitch RAO magnitudes per period.
    Needs the optional seakeeping extra (``openhull[seakeeping]``); when
    capytaine is missing the payload is ``ok=false`` with an install
    hint instead of a traceback.  BEM cost grows with the period count —
    probe with 2-3 periods first.  Remember the discipline: resonance
    amplitudes and criterion outcomes are reported, not decided.
    """
    with tempfile.TemporaryDirectory(prefix="openhull_mcp_rao_") as tmp:
        tb = Path(tmp) / "taskbook.yaml"
        _write_taskbook(taskbook_yaml, tb)
        run = _run_cli(["rao", str(tb), "--periods", periods, "--json"],
                       cwd=Path(tmp), timeout_s=timeout_s)
    note = None if run.get("ok") else _INSTALL_HINT_SEAKEEPING
    return _payload(run, note=note)


def taskbook_template_text() -> str:
    """Return the packaged task book template (JBC-anchored example).

    Every quantity carries a provenance tag — [NMRI] (official
    benchmark value), [DERIV] (formula stated inline), [ASSUMED]
    (owner-approved engineering assumption).  Copy it, change the
    numbers, keep the tags: provenance is the discipline that keeps the
    whitelist auditable.
    """
    ref = files("openhull").joinpath("data", "taskbook_template.yaml")
    with as_file(ref) as path:
        return Path(path).read_text(encoding="utf-8")


def build_server():
    """Build the FastMCP server (requires ``openhull[mcp]``).

    The SDK import is deliberately inside this factory: importing the
    module (and running the tests) must not require the optional extra.
    """
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "openhull",
        instructions=(
            "OpenHull — parametric ship preliminary design (SI units: "
            "m, t, kW, s; speeds kn at the boundary).  Workflow: 1) "
            "openhull_version to see installed capabilities; 2) fetch "
            "resource openhull://taskbook-template and adapt it into a "
            "task book; 3) openhull_check to preflight the guards; 4) "
            "openhull_run for the full chain (dimensions, weight, "
            "hydrostatics, IMO IS Code stability, resistance/propulsion, "
            "propeller, seakeeping) or openhull_optimize to sweep "
            "dimension ratios; 5) openhull_rao for zero-speed RAOs "
            "(needs the seakeeping extra).  The toolchain refuses "
            "out-of-applicability inputs with a stated reason — never "
            "bypass a refusal by editing the guard; fix the task book.  "
            "Stability criteria outcomes are reported, never decided: "
            "the verdict belongs to the naval architect."
        ),
    )
    # explicit wire names: harnesses flatten tool lists across servers,
    # so generic names like "check" would collide — every tool carries
    # the openhull_ prefix (the code-side names stay tool_*)
    for fn, name in (
        (tool_version, "openhull_version"),
        (tool_check, "openhull_check"),
        (tool_run, "openhull_run"),
        (tool_optimize, "openhull_optimize"),
        (tool_rao, "openhull_rao"),
    ):
        mcp.tool(name=name)(fn)
    mcp.resource("openhull://taskbook-template")(taskbook_template_text)
    return mcp


def main() -> int:
    """Console-script entry: serve MCP over stdio (blocks)."""
    server = build_server()
    server.run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
