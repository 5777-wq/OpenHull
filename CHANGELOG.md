# Changelog

All notable changes to OpenHull are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versioning
is semantic (MAJOR.MINOR.PATCH).

## [Unreleased]

### Added

- Lackenby hull-form transform (plan task 2.3): `lackenby_transform`
  with fore/aft prismatic-coefficient split, parallel-middle-body
  shift, table-level convergence iteration and guard rails; selectable
  algorithm registry with citation/applicability metadata.
- Lines-plan three-view drawing and offsets CSV export (plan task 2.4):
  `draw_lines_plan` renders body / sheer / half-breadth views from the
  RAW tabulated grid with hand-written Fritsch–Carlson monotone spline
  fairing; waterlines above the DWL dashed, Lackenby-shifted tables
  supported.
- Numerical fairness checks (plan task 2.5): `check_fairness` runs
  first/second-difference alarms over the tabulated half-breadths with
  robust LOCAL-CONTRAST detection (MAD against neighbouring second
  differences), single-lobe monotonicity above 0.5 draft, and
  parallel-middle-body constancy.  Acceptance: the digitised Series 60
  parent passes with ZERO issues; planted spike/kink/lobe-break/wobble
  defects are all flagged.
- Real-ship verification data path: the 116.6 m cargo ship and the
  94 m coastal open-top container ship were rebuilt from their DXF
  offset tables (text-layer extraction → offsets table → lines plan);
  on the latter the 2.5 checker flags three stern-bottom cells
  (baseline width jumping 25 mm → 6195 mm between adjacent stations)
  for human review.

### Fixed

- Sheer-view buttock heights: topmost-crossing convention for bulbous
  sections whose half-breadths are NOT monotone in height (np.interp
  silently misanswered such descending columns); NaN-safe sparse
  columns; whole-section-wider sections correctly map to the bottom.
- CI: force the official PyPI index (mirror URLs recorded in uv.lock
  by a local uv configuration returned 403 on GitHub runners).

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
