# OpenHull

[![ci](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml)

**English** | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Deutsch](README_de.md) | [Français](README_fr.md) | [Español](README_es.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

Open-source parametric ship hull design toolchain, orchestrated by AI agents.

Provide a task book (ship type, deadweight, service speed, trading range) —
the agent pipeline returns principal dimensions, hydrostatics, a lines plan,
resistance / propulsion / stability estimates, and drawing outputs (DXF).

## Status

**v0.4 released** — stage 4 complete: the toolchain now ships its first DRAWING AND REPORT deliverables from one command (see [examples/demo_outputs](examples/demo_outputs)) — a hydrostatic curves chart in the textbook layout, a general-arrangement schematic as chart and layered DXF, and a Chinese Markdown design report. Seakeeping joins the loop in two layers: textbook first-level estimates (natural periods, resonance verdicts against reference seas) and zero-speed RAOs via the optional capytaine extra (`pip install 'openhull[seakeeping]'`). Every number traceable to the formula whitelist (see [VALIDATION.md](VALIDATION.md)). One command: `openhull run examples/taskbook_bulk_carrier.yaml --report design_report.md --hydro-curve-chart curves.png`.

## Roadmap

- [x] Stage 1 — Principal dimension iteration & hydrostatics core (**v0.1**)
- [x] Stage 2 — Parametric hull form generation (mother-ship transformation) (**v0.2**)
- [x] Stage 3 — Performance loop: resistance / propulsion / stability (**v0.3**)
- [x] Stage 4 — Drawings & reports: hydrostatic curves, GA schematic (DXF), design report; seakeeping two-layer (+ optional capytaine RAOs) (**v0.4**)
- [ ] Stage 5 — Documentation & community release (v1.0)

## Design principles

1. Every output must be traceable to an equation or a published reference
2. Validation against published benchmark ships comes before new features
3. Empirical formulas declare their applicability range and refuse out-of-range input
4. What can be written as an equation is automated; what cannot is left to the engineer

## License

[MIT](LICENSE)
