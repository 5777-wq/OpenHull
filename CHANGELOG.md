# Changelog

All notable changes to OpenHull are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versioning
is semantic (MAJOR.MINOR.PATCH).

## [0.1.0] - 2026-09-11

First public release — stage 1 of the roadmap: the principal-dimension
and hydrostatics core, driven by a YAML task book and validated against
the public JBC benchmark ship.

### Added

- Task-book container `ShipSpec` with explanatory validation errors
  (every rejected value states the violated constraint AND the physical
  reason).
- Principal-dimension estimation behind a selectable algorithm registry
  (`deadweight_ratio_statistical`, `parent_hull_ratio`;
  `watson_1977` registered pending its source).
- Weight-buoyancy balance iteration: deadweight-ratio, component-cubic
  and component-exponent lightweight algorithms, Norman-coefficient
  diagnostic, convergence per |W−B|/W ≤ 0.1 %.
- Analytic JBC parent hull fitted to the task-book anchors (Cb, Cm, LCB,
  KM) over a stations × waterlines offsets container.
- Hydrostatics: in-package Simpson/trapezoid integration, waterplane
  data, even-keel volume/KB, BMT/BML/MTC, hydrostatics tables, Bonjean
  interface.
- Initial stability (GM with free-surface corrections) and floating
  attitude (trim iteration on the Eqs. (3-25)/(3-26) scheme).
- Freeboard check against the load-line rules (ICLL 1966 tabulated
  basic freeboard + the five corrections).
- CLI: `openhull run taskbook.yaml` with `--csv` / `--json` streaming
  output.

### Validation

- JBC anchors: displacement volume +0.21 %, KM +0.000 %, Cb +0.0018,
  LCB −0.008 %Lpp; ballast drafts recovered within −0.7 %/−1.0 %;
  freeboard verdict PASS with 1.94 m margin.
- Zero-circularity anchors: the Xie Yunping worked example (7,384 t /
  7,378 t steel weights) and the published ballast condition.
- Full tables: [VALIDATION.md](VALIDATION.md).

[0.1.0]: https://github.com/5777-wq/OpenHull/releases/tag/v0.1.0
