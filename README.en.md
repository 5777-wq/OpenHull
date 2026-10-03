<div align="center">

# OpenHull

**Design the shell that carries it all.**

An open-source, agent-orchestrated parametric ship preliminary-design
toolchain: from a task book to principal dimensions, hydrostatics,
IS Code stability, resistance & propulsion, propeller design,
seakeeping, drawings and a design report — with **every number
traceable to a formula whitelist**.

[![tests](https://github.com/5777-wq/OpenHull/actions/workflows/tests.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/tests.yml)
[![release](https://img.shields.io/github/v/release/5777-wq/OpenHull)](https://github.com/5777-wq/OpenHull/releases)
[![license](https://img.shields.io/github/license/5777-wq/OpenHull)](LICENSE)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![docs](https://img.shields.io/website?url=https%3A%2F%2F5777-wq.github.io%2FOpenHull%2F)](https://5777-wq.github.io/OpenHull/)
[![website](https://img.shields.io/badge/website-%E4%B8%AD%E6%96%87-success)](https://5777-wq.github.io/openhull-site/)

**English** | [简体中文](README.md)

</div>

---

## What it does

Write one **task book** (YAML) describing the ship you need; OpenHull
runs the whole preliminary-design chain and produces:

| stage | deliverable |
|---|---|
| dimensions & weight | Norman-iterated displacement balance, deadweight-ratio methods |
| hull form | digitised Series 60 parent + Lackenby transformation, real offsets |
| hydrostatics | tables, Bonjean, textbook-layout hydrostatic curves chart |
| stability | large-angle GZ, IMO 2008 IS Code 2.2 criteria, severe wind & rolling (2.3) |
| freeboard | load-line type-B summer minimum check (ICLL 1966 transcription, in the run chain) |
| performance | Ayre resistance, Holtrop propulsion factors, B-series propeller design |
| design space | ratio-grid scan with per-stage refusal records and a Pareto front |
| seakeeping | textbook natural periods & resonance verdicts; zero-speed RAOs via capytaine (optional) |
| speed loss | Kwon's method (Beaufort, wave direction, loading condition) |
| deliverables | layered DXF, charts, Chinese Markdown design report |

Sample outputs (report, curves chart, GA schematic, DXF, CSV) are
committed under
[examples/demo_outputs](examples/demo_outputs) — one command
regenerates all of them.

## Quick start

Install the CLI (pinned to the release tag — reproducible, auditable):

```bash
uv tool install "git+https://github.com/5777-wq/OpenHull@v1.6.0"
openhull run examples/taskbook_bulk_carrier.yaml
# optional seconds-level preflight of all guard bands:
openhull check examples/taskbook_bulk_carrier.yaml
```

> Honest note: TB-001 is the JBC validation ship at its REAL 14.5 kn
> service speed, which sits below the whitelisted Ayre speed band
> (V/√L ≈ 0.48 < 0.50) — the power & propeller section is therefore
> DECLINED with a declared refusal while dimensions, hydrostatics,
> stability and the arrangement compute normally.  That is the
> refuse-over-extrapolate discipline working, not a failure.  For a
> first run through the FULL chain including the propeller, use the
> skill's `minimal_taskbook.yaml` (45,000 t / 16 kn).

From source (development):

```bash
git clone https://github.com/5777-wq/OpenHull.git
cd OpenHull
uv sync                        # or: pip install -e .
uv run openhull run examples/taskbook_bulk_carrier.yaml
```

With drawings and report:

```bash
openhull run examples/taskbook_bulk_carrier.yaml \
  --report design_report.md \
  --hydro-curve-chart curves.png \
  --arrangement-chart ga.png \
  --arrangement-dxf ga.dxf
```

Design-space scan and RAOs:

```bash
openhull optimize examples/taskbook_bulk_carrier.yaml   # scan + Pareto chart
uv sync --extra seakeeping                                     # optional capytaine extra
openhull rao examples/taskbook_bulk_carrier.yaml        # zero-speed RAOs
```

## Use it from an AI agent

OpenHull is designed to be orchestrated by AI agents. Send your
agent this one sentence and it installs the tool, writes the task
book and runs the whole chain itself:

> Please install and use the OpenHull skill
> (https://github.com/5777-wq/OpenHull/tree/main/skills/openhull),
> then design a 50,000 t bulk carrier at 14.5 kn service speed with
> a design report and a general-arrangement schematic.

The skill ships in [`skills/openhull/`](skills/openhull/SKILL.md)
with a minimal task-book template; any agent that can read a
SKILL.md can install it from the URL alone.

Prefer MCP? Since v1.7.0 OpenHull ships an MCP server (`openhull-mcp`,
stdio): register it once and Codex, ZCode, Claude, DeepSeek or any
MCP-capable harness can call the same tools (preflight, full design
chain, dimension scans, RAOs). Install and per-harness snippets:
[docs/mcp.md](docs/mcp.md).

## The discipline

1. **Whitelist first.** An empirical formula is implemented only if
   its source is listed in [AGENTS.md §5](AGENTS.md) — amended before
   the code, transcriptions verified against page images of the
   source.
2. **Acceptance by numbers.** Book worked examples, independent-path
   cross-checks and public benchmarks pin every feature — 473 tests
   (marked skips without the optional extras),
   full record in [VALIDATION.md](VALIDATION.md).
3. **Declared approximations.** Wall-sided decks, damping ranges,
   suppressed degrees of freedom: stated where they live.
4. **The tool reports; the naval architect decides.** Whether a
   resonance band or a criterion vetoes a design is professional
   judgement, kept human on purpose.

## Validation highlights

| anchor | agreement |
|---|---|
| NMRI JBC benchmark ship | displacement volume, Cb, Cm, LCB reproduced |
| DTMB Report 1712 (Series 60) | speed reproduction ±0.32 kn from published SHP |
| NMRI MP687 measured open-water data | B-series ηo mean \|Δ\| 2.8 % |
| book worked examples (Ship Theory vol. 2) | propeller terminal design 0.07 kn; roll-period identities exact |
| panel-mesh vs station integration | displacement volume 0.1 % |
| KCS speed loss (published comparison) | speed ratio f_w 0.929 vs 0.932 |
| Holtrop-Mennen 1982 paper worked example | all twenty printed quantities reproduced (R_total 1793.26 kN, P_E 23063 kW) |

## Documentation

- [Website (Chinese portal)](https://5777-wq.github.io/openhull-site/) — the project website
- [Documentation site](https://5777-wq.github.io/OpenHull/) — quick
  start & methods in Chinese, reference pages in English
- [VALIDATION.md](VALIDATION.md) — the full acceptance record,
  item by item
- [CHANGELOG.md](CHANGELOG.md) — release history

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR: formula
sources go through the whitelist process, transcriptions are
page-verified against the source, and acceptance is numerical. Bug
reports and formula-source proposals have dedicated issue templates.

## License

[MIT](LICENSE)

## Citation

If OpenHull contributes to your research, please cite it via
[CITATION.cff](CITATION.cff):

```bibtex
@software{openhull,
  author       = {5777-wq},
  title        = {OpenHull: agent-orchestrated parametric ship
                  preliminary design},
  version      = {1.6.0},
  year         = {2026},
  url          = {https://github.com/5777-wq/OpenHull}
}
```
