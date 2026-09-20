# Changelog

All notable changes to OpenHull are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versioning
is semantic (MAJOR.MINOR.PATCH).

## [Unreleased]

### Added

- Large-angle stability — the static stability curve (plan task 3.4):
  `gz_curve(table, displacement, kg, depth)` computes l(φ) by the
  equal-displacement method (Ship Theory vol. 1, sec. 5-2): per heel
  angle the equal-volume heeled waterline is iterated on the tabulated
  sections (exact polygon clipping; no draft-direction quadrature) and
  the arm assembled from Eq. (5-1).  The result carries per-angle audit
  points, the maximum arm and its angle (0.25 deg refinement), the
  vanishing angle (bisected) and the dynamic stability arm of sec. 5-6.
  The CLI `run` prints the curve when the task book carries
  `requirements.kg_m` (TB-001: NMRI 13.29 m).  Zero-circularity
  acceptance: a wall-sided box hull reproduces its closed-form GZ curve
  to 1e-8; the curve's origin slope equals GM (sec. 5-5); every point
  holds |Δ−Δ_φ|/Δ ≤ 0.1 %.  A published JBC full-load GZ analysis
  (Hussain & Amin 2021, JMSA 20(3), Table 7: max 3.309 m at 40.9°) is
  recorded as a wide demonstration band — see VALIDATION.md for the
  attribution of the differences.
- Layered DXF lines-plan export (plan task 2.7):
  `save_lines_plan_dxf` writes the three views (body plan / sheer /
  half-breadth plan) onto an A3 frame with one layer per content class
  (sections, waterlines, buttocks, deck, heavy design waterline, grid,
  labels), curves as PCHIP-faired polylines.  All TEXT entities are
  pure ASCII so AutoCAD opens the file without mojibake in any locale;
  a non-ASCII title is ASCII-folded.  Example:
  `examples/lines_plan_series60_to_jbc.dxf`.

## [0.2.0] - 2026-09-14

### Added

- Mother-ship geometry chain (plan task 2.6): the CLI and library now
  build the hull from REAL tabulated offsets — the packaged digitised
  Series 60 parent (`openhull/data/`, byte-identical to the examples
  CSV), affine-scaled onto the balanced task-book dimensions
  (`scale_offsets`, coefficients invariant) and Lackenby-transformed
  onto the task-book block coefficient (`parent_to_taskbook`).
  Acceptance at the JBC anchors: displacement volume within ±1 %,
  Cb ±0.005, KM ±2 %, LCB ±0.02 %Lpp — all met; Bonjean integration
  stays consistent with the hydrostatics volume (rel 1e-4).
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
  the 94 m rebuild was later verified cell-by-cell against the
  authoritative printed offsets table supplied by the owner
  (see Corrected).

### Corrected

- An earlier claim that the 2.5 checker "flags three stern-bottom
  cells" of the 94 m ship was an artefact of the DEMO grid
  construction (stations whose bottom sits above the baseline were
  left-filled with their 1 m-waterline breadth at z = 0), not a
  defect of the rebuilt table.  The owner then supplied the printed
  offsets table: all 273 cells match, four cells differing between
  the CAD text layer and the printed sheet (st1 4000WL, st5/st14
  baseline width, st18 6000WL) were corrected to the printed values.
  With the demo grid fixed the checker reports no mid-body defects;
  the printed non-monotone bow waterlines at st20 are a feature of
  the design and were carried as printed.

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
