# OpenHull

[![ci](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml)

**English** | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Deutsch](README_de.md) | [Français](README_fr.md) | [Español](README_es.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

Open-source parametric ship hull design toolchain, orchestrated by AI agents.

Provide a task book (ship type, deadweight, service speed, trading range) —
the agent pipeline returns principal dimensions, hydrostatics, a lines plan,
resistance / propulsion / stability estimates, and drawing outputs (DXF).

## Status

**v0.3 released** — stage 3 complete, the performance loop is closed: Ayre resistance estimation, Holtrop propulsion factors with a service-speed solver, Wageningen B-series propeller design (published regression, Burrill cavitation check, thrust-led design), large-angle stability with the IS Code 2.2 criteria and the severe wind & rolling criterion, plus a design-space optimizer (`openhull optimize`) that sweeps dimension ratios into feasible, criteria-passing designs with a Pareto trade-off chart. Validated against the JBC benchmark ship, DTMB Report 1712 and the measured NMRI MP687 open-water data (see [VALIDATION.md](VALIDATION.md)). One command: `openhull run examples/taskbook_bulk_carrier.yaml`.

## Roadmap

- [x] Stage 1 — Principal dimension iteration & hydrostatics core (**v0.1**)
- [x] Stage 2 — Parametric hull form generation (mother-ship transformation) (**v0.2**)
- [x] Stage 3 — Performance loop: resistance / propulsion / stability (**v0.3**)
- [ ] Stage 4 — Drawing output (DXF) & design reports
- [ ] Stage 5 — Documentation & community release (v1.0)

## Design principles

1. Every output must be traceable to an equation or a published reference
2. Validation against published benchmark ships comes before new features
3. Empirical formulas declare their applicability range and refuse out-of-range input
4. What can be written as an equation is automated; what cannot is left to the engineer

## License

[MIT](LICENSE)
