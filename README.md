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
[![官网（中文）](https://img.shields.io/badge/%E5%AE%98%E7%BD%91-%E4%B8%AD%E6%96%87-success)](https://5777-wq.github.io/openhull-site/)

**[Documentation](https://5777-wq.github.io/OpenHull/)** ·
**[官网 Website（中文）](https://5777-wq.github.io/openhull-site/)** ·
**[中文说明](README_zh.md)** ·
[日本語](README_ja.md) · [한국어](README_ko.md) · [Deutsch](README_de.md) · [Français](README_fr.md) · [Español](README_es.md) · [Italiano](README_it.md) · [Português](README_pt.md) · [Русский](README_ru.md)

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

```bash
git clone https://github.com/5777-wq/OpenHull.git
cd OpenHull
uv sync                        # or: pip install -e .
uv run openhull run examples/taskbook_bulk_carrier.yaml
```

With drawings and report:

```bash
uv run openhull run examples/taskbook_bulk_carrier.yaml \
  --report design_report.md \
  --hydro-curve-chart curves.png \
  --arrangement-chart ga.png \
  --arrangement-dxf ga.dxf
```

Design-space scan and RAOs:

```bash
uv run openhull optimize examples/taskbook_bulk_carrier.yaml   # scan + Pareto chart
uv sync --extra seakeeping                                     # optional capytaine extra
uv run openhull rao examples/taskbook_bulk_carrier.yaml        # zero-speed RAOs
```

## The discipline

1. **Whitelist first.** An empirical formula is implemented only if
   its source is listed in [AGENTS.md §5](AGENTS.md) — amended before
   the code, transcriptions verified against page images of the
   source.
2. **Acceptance by numbers.** Book worked examples, independent-path
   cross-checks and public benchmarks pin every feature — 348 tests,
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
| KCS speed loss (published comparison) | speed ratio f_w within 0.01 |

## Documentation

- [Documentation site](https://5777-wq.github.io/OpenHull/) — quick
  start & methods in Chinese, reference pages in English
- [官网（中文主页）](https://5777-wq.github.io/openhull-site/) — the
  project website, in Chinese
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
  version      = {1.0.0},
  year         = {2026},
  url          = {https://github.com/5777-wq/OpenHull}
}
```
