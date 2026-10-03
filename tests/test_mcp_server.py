"""Tests for the MCP server surface (v1.7.0).

The wrapper's contract is "the CLI, verbatim, in a child process": so
the tests pin the exact spawn command cross-process, exercise the tools
end-to-end on the JBC task book, and check the refusal/hint payloads.
The FastMCP wiring tests skip cleanly when the optional
``openhull[mcp]`` extra is not installed (per-call importorskip, never
at module level, mirroring the seakeeping marker discipline).
"""

import json
import os
import subprocess
import sys
from importlib.metadata import version as package_version
from pathlib import Path

import pytest

import openhull.mcp_server as mcp_server
from openhull.mcp_server import (
    build_server,
    taskbook_template_text,
    tool_check,
    tool_optimize,
    tool_rao,
    tool_run,
    tool_version,
)

TASKBOOK = "examples/taskbook_bulk_carrier.yaml"
SCAN_TASKBOOK = "examples/taskbook_bulk_carrier_scan16kn.yaml"

MCP_TOOLS = {
    "openhull_version", "openhull_check", "openhull_run",
    "openhull_optimize", "openhull_rao",
}


def _jbc_yaml() -> str:
    with open(TASKBOOK, encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------- cross-
# process contract: the wrapper spawns exactly this, so pin exactly this


def test_cli_reachable_via_the_wrapper_spawn_command():
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "openhull.cli", "--version"],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip().startswith("openhull ")


def test_module_import_does_not_pull_the_mcp_sdk():
    # the lazy-import guarantee: importing the module must work (and
    # must not drag the SDK in) even without openhull[mcp] installed
    code = (
        "import sys, openhull.mcp_server; "
        "assert not any(k == 'mcp' or k.startswith('mcp.') "
        "for k in sys.modules); print('clean')")
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", code],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "clean" in proc.stdout


# ---------------------------------------------------------------- tools


def test_tool_version_reports_versions_and_extras():
    doc = json.loads(tool_version())
    assert doc["ok"] is True
    assert doc["openhull"] == package_version("openhull")
    assert doc["extras"]["seakeeping"] in (True, False)
    assert doc["cli"].startswith("openhull ")


def test_tool_check_jbc_preflight_produces_gates():
    doc = json.loads(tool_check(_jbc_yaml()))
    # exit 1 (a band-edge predicted refusal) is a meaningful preflight
    # outcome, so ok stays true as long as the gate list parsed
    assert doc["ok"] is True
    assert doc["result"]["taskbook_id"] == "TB-001"
    gates = {g["gate"]: g["pass"] for g in doc["result"]["gates"]}
    assert "Ayre speed band V/sqrt(L)" in gates
    assert doc["refusal_predicted"] is True


def test_tool_check_refuses_a_grossly_out_of_band_speed():
    # 40 kn on a full-form hull: the CLI's input validation refuses
    # outright (exit 2) instead of extrapolating the merchant-ship
    # statistics — the payload must carry that reason, not a traceback
    yaml_text = _jbc_yaml().replace("service_speed_kn: 14.5",
                                    "service_speed_kn: 40.0")
    doc = json.loads(tool_check(yaml_text))
    assert doc["ok"] is False
    assert doc["exit_code"] == 2
    assert doc["result"] is None
    assert "refusing" in doc["stderr_tail"]


@pytest.fixture(scope="module")
def run_doc(tmp_path_factory):
    outdir = tmp_path_factory.mktemp("mcp_run")
    return outdir, json.loads(tool_run(_jbc_yaml(), output_dir=str(outdir)))


def test_tool_run_full_chain_ok_with_live_artifacts(run_doc):
    outdir, doc = run_doc
    assert doc["ok"] is True, doc["stderr_tail"]
    assert doc["result"]["taskbook_id"] == "TB-001"
    assert doc["result"]["displacement_t"] > 0
    expected = {"taskbook", "result.json", "design_report.md",
                "ga_schematic.dxf", "ga_schematic.png",
                "hydrostatic_curves.png"}
    assert expected <= set(doc["artifacts"])
    for name in expected:
        path = doc["artifacts"][name]
        assert os.path.isfile(path), name
        assert str(Path(path)).startswith(str(outdir)), name


def test_tool_run_without_optional_outputs(tmp_path):
    doc = json.loads(tool_run(_jbc_yaml(), output_dir=str(tmp_path),
                              report=False, arrangement_dxf=False,
                              arrangement_chart=False,
                              hydro_curve_chart=False))
    assert doc["ok"] is True, doc["stderr_tail"]
    assert set(doc["artifacts"]) == {"taskbook", "result.json"}


def test_tool_optimize_small_grid(tmp_path):
    with open(SCAN_TASKBOOK, encoding="utf-8") as fh:
        yaml_text = fh.read()
    doc = json.loads(tool_optimize(
        yaml_text,
        grid_lob="5.2:5.6:2", grid_bt="2.5:2.9:2", grid_cb="0.81:0.83:2",
        output_dir=str(tmp_path)))
    assert doc["ok"] is True, doc["stderr_tail"]
    assert "taskbook" in doc["artifacts"]
    assert any(n.endswith((".csv", ".json", ".png"))
               for n in doc["artifacts"])


def test_tool_rao_reports_install_hint_when_seakeeping_missing(monkeypatch):
    fake = {"ok": False, "exit_code": 2, "stdout": "",
            "stderr": "capytaine is required", "command": ["rao"],
            "error": None}
    monkeypatch.setattr(mcp_server, "_run_cli", lambda *a, **k: fake)
    doc = json.loads(tool_rao(_jbc_yaml(), periods="6,8"))
    assert doc["ok"] is False
    assert "openhull[seakeeping]" in doc["note"]


def test_payload_flags_a_broken_json_contract(monkeypatch):
    fake = {"ok": True, "exit_code": 0, "stdout": "Traceback-ish prose",
            "stderr": "", "command": ["run"], "error": None}
    monkeypatch.setattr(mcp_server, "_run_cli", lambda *a, **k: fake)
    doc = json.loads(tool_check(_jbc_yaml()))
    assert doc["ok"] is False
    assert "contract violation" in doc["error"]


# ---------------------------------------------------------------- template


def test_taskbook_template_is_the_jbc_example_verbatim():
    # anti-drift pin: the packaged resource must be byte-identical to
    # the canonical example; edit the example, re-copy, or the pin
    # fails loudly
    assert taskbook_template_text() == _jbc_yaml()
    assert "schema_version: 1" in taskbook_template_text()


# ---------------------------------------------------------------- FastMCP
# wiring (needs the optional extra; skip cleanly without it)


def _server_inspection():
    pytest.importorskip("mcp")
    import anyio

    server = build_server()
    tools = anyio.run(server.list_tools)
    resources = anyio.run(server.list_resources)
    return tools, {str(r.uri) for r in resources}


def test_build_server_lists_openhull_prefixed_tools():
    try:
        tools, resources = _server_inspection()
    except ImportError:
        pytest.skip("openhull[mcp] extra not installed")
    assert MCP_TOOLS <= {t.name for t in tools}
    assert "openhull://taskbook-template" in resources
    for tool in tools:
        assert tool.description, tool.name


def test_fastmcp_tool_call_roundtrip():
    pytest.importorskip("mcp")
    import anyio

    async def call():
        server = build_server()
        return await server.call_tool("openhull_version", {})

    result = anyio.run(call)
    blocks = result[0] if isinstance(result, tuple) else result
    blocks = blocks if isinstance(blocks, list) else blocks.content
    doc = json.loads(blocks[0].text)
    assert doc["ok"] is True
    assert doc["extras"]["mcp"] is True


def test_stdio_session_end_to_end(tmp_path):
    # the harness-shaped gate: a real MCP stdio client drives the real
    # server process.  This is the test that pins the stdin=DEVNULL
    # fix — without it the tool's grandchild CLI spawn inherits the
    # transport pipe and deadlocks on Windows.
    pytest.importorskip("mcp")
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def call():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-X", "utf8", "-m", "openhull.mcp_server"])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                res = await session.call_tool("openhull_version", {})
                return (sorted(t.name for t in tools.tools),
                        res.content[0].text)

    names, text = anyio.run(call)
    assert MCP_TOOLS <= set(names)
    doc = json.loads(text)
    assert doc["ok"] is True
    assert doc["cli"].startswith("openhull ")
