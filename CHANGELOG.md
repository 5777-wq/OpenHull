# Changelog

All notable changes to OpenHull are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versioning
is semantic (MAJOR.MINOR.PATCH).

## [0.4.0] - 2026-09-23

### Added

- General-arrangement schematic (plan task 4.2): `arrangement.py`
  models the compartment layout as data — the task book's optional
  `arrangement` block overrides everything, otherwise a declared
  default bulk-carrier scheme applies (aft peak / engine room /
  five cargo holds / fore peak, double bottom at max(B/20, 1.0 m)).
  Renders a side-view + deck-plan schematic (`run
  --arrangement-chart`) and exports a layered DXF
  (`--arrangement-dxf`, layers GA-SIDE/GA-PLAN/GA-DB/GA-LABELS).
  Declarative only: no formula, no feedback into calculations.
  The rendered schematic passed an independent visual review after
  the narrow-aft-peak labelling defect was fixed.
- Design report generation (plan task 4.3): `report.py` assembles
  the run summary into a Chinese Markdown report — principal
  dimensions, hydrostatics, IS Code stability tables, propeller
  design (or its declared skip), first-level seakeeping verdicts,
  the arrangement table and an embedded chart reference; new
  `run --report PATH` flag.  The report restates computed results
  and adds no numbers of its own.
- Hydrostatic curves chart (plan task 4.1): `hydrostatics_chart.py`
  renders the classic textbook layout (draft axis vertical,
  increasing downward) with twelve panels from the task 1.4 table —
  displacement, KB, BMT, KM, BML, TPC, MTC, LCB, LCF, Cb, Cw; new
  `run --hydro-curve-chart PATH` flag.  Pure visualization: no new
  formulas, the drawn numbers are exactly the tabulated ones.
  First render was failed by an independent visual review on the
  draft-axis direction and re-passed after the fix.
- Stage-2 seakeeping: zero-speed rigid-body RAOs via capytaine
  (task 3.8 stage 2).  New optional dependency
  (`pip install openhull[seakeeping]`, lazy import, clean refusal
  without it — owner decision 2026-09-23).  `seakeeping_bem.py`
  lofts the task 2.6 offsets table into a closed panel mesh
  (baseline-tangent keel strip, wall-sided deck, perpendicular
  caps, outward winding) and capytaine supplies hydrodynamics only;
  the RAO mass/inertia/stiffness matrices come from the whitelisted
  chain (task 1.4 displacement, Duell roll inertia Eq. 3-39,
  KYY = 0.25 L, rho*g*Aw, rho*grad*GM).  New `openhull rao`
  subcommand (table or JSON).  Validation = independent-path
  cross-checks (mesh volume vs table 0.1 %, long-wave heave -> 1,
  short-wave -> 0, head-sea roll symmetry, roll peak vs stage-1
  period).  Declared: radiation-only damping (resonance amplitudes
  qualitative), zero speed, surge/sway/yaw suppressed.
- First-level seakeeping estimate (plan task 3.8, stage 1):
  `seakeeping.py` implements the whitelisted textbook layer —
  deep-water wave relations (Eq. 2-7), encounter period/frequency
  (Eqs. 2-98/2-99), the regulation roll natural period (Eqs.
  3-49/3-48 with the 3-39/3-27 chain as derivation check, GM > 0.15 m
  guard), the effective wave-slope coefficient (Eq. 3-3 with the
  regulation clamp), resonant roll amplification 1/(2 mu) and the
  0.7-1.3 resonance band, and pitch/heave periods (Eqs. 4-55/4-57/
  4-60 and 4-62 in its derivation-restored form).  Resonance verdicts
  against two reference seas (East China Sea T ~ 6 s, ocean swell
  T = 8 s) are reported in the `run` output and JSON, and ride along
  as scan columns on every feasible design (reported, not gating —
  resonance avoidance is professional judgement).  Wave speed loss
  is out of scope: the source defines the indicator but prints no
  estimation formula.  Whitelist amendment (AGENTS.md section 5)
  precedes implementation; two print defects of the source are
  recorded there and excluded from the code.

## [0.3.0] - 2026-09-23

### Added

- Design-space scan and trade-off extraction (plan task 3.6):
  `optimize.py` sweeps the dimension-ratio grid (L/B, B/T, C_b),
  evaluates every candidate through the full whitelisted chain
  (weight balance, Lackenby hull, hydrostatics, IS Code criteria,
  weather criterion, Ayre resistance, B-series propeller design)
  and records every refusal at its refusing stage.  New CLI
  subcommand `openhull optimize` writes the feasible-design CSV,
  a speed-displacement-GM trade-off chart and a JSON summary.
  Acceptance (TB-001S 16 kn scan scenario): 192 candidates ->
  64 feasible designs, all stability criteria passing, 14-design
  Pareto front; TB-001 at its 14.5 kn service speed returns an
  empty set with every refusal declared.
- Wageningen B-series open-water regression, optimum-propeller
  engine and terminal design (plan task 3.3): `b_series.py` carries
  the page-referenced coefficient transcription of Bernitsas/Ray/
  Kinley, U-M Report No. 237 (May 1981) — 39 K_T + 47 K_Q polynomial
  terms at Rn = 2e6 plus 9 + 13 Reynolds-correction terms, valid
  Z 2-7, A_E/A_0 0.30-1.05, P/D 0.50-1.40.  `propeller.py` adds the
  `OpenWaterSeries` plug-in interface, `solve_optimal_propeller`
  (the section 8-2 optimum-line construction realised numerically:
  J-sweep, torque-demand inversion for pitch, golden-section eta_o
  maximisation), `terminal_design` (the table 8-12 / figure 8-9
  attainable-speed procedure) and `solve_speed_thrust_balance` for a
  fixed propeller.  Acceptance: the report's own figure 41 overlay;
  the textbook table 8-12 optimum-line readings within 1.5 % (B5-50
  vs the AU5-50 chart); the NMRI MP687 measured open-water table at
  mean |d eta_o| < 4 % (declared cross-family, model-scale-Rn
  caveats); the 25,000 t bulk-carrier terminal design run with B5-50
  reproduces the book's attainable speed to 0.07 kn.  The CLI
  `propeller` task-book block designs at the service point and
  reports the Burrill cavitation verdict; TB-001 itself skips with a
  declared reason (its 14.5 kn service speed lies below the Ayre
  speed-length band for a 280 m ship).
- Burrill cavitation check (plan task 3.3, stage 1): `check_cavitation`
  and helpers in `propeller.py` implement the Ship Theory vol. 2
  section 6-5 chain — cavitation number at 0.7R (Eq. 6-14 with the
  printed relative-velocity square), thrust loading (Eq. 6-15), the
  projected/expanded area relation (Eq. 6-16, verified against the
  table 6-2 arithmetic), and the required expanded area ratio.  The
  commercial-ship limit line is carried at the book's own four
  chart-read anchors (tables 6-2/8-29) and refuses sigma outside that
  verified band (0.387..0.483).  Acceptance: the table 6-2 chain of
  the 25,000 t bulk-carrier example reproduces end to end (sigma
  0.481, tau_c 0.175, required AE/A0 0.642 vs the designed 0.65), and
  the table 8-29 sigma values of the MAU4 example reproduce to
  ±0.0015.
- Propulsion factors and service-speed solver (plan task 3.2):
  `propulsion_factors` evaluates the Holtrop wake fraction, thrust
  deduction and hull efficiency as transcribed in Ship Theory vol. 2
  sections 5-2/5-3 (Eqs. 5-38..5-52, with the full auxiliary chain —
  ITTC 1957 friction, correlation allowance, bulb and stern
  coefficients, wetted surface); `solve_service_speed` iterates the
  speed whose bare-hull effective power (task 3.1) balances the
  delivered power times eta_D = eta_o*eta_R*eta_h.  Validated against
  the published self-propulsion results of DTMB Report 1712 for the
  digitised Series 60 parent (Table 31/39): the implied open-water
  efficiency stays at 0.63-0.67 across the published 14-17 kn range,
  and service speeds reproduce within ±0.5 kn (14 kn within 0.75, the
  declared chart-knee tolerance).  Applicability guards refuse
  nonphysical wake/thrust values and out-of-band open-water
  efficiencies.
- Ayre resistance estimation (plan task 3.1 v1):
  `ayre_effective_power` implements the Ayre method as transcribed in
  Ship Theory vol. 1 section 7-1 — the standard-form effective power
  (Eq. 7-21) with the figure 7-3 C₀ coefficient digitised from the
  scanned chart, the four corrections (block coefficient via Eq. 7-22
  / table 7-6, B/T via Eq. 7-23, LCB via Eq. 7-24 / tables 7-7a,b
  with the three-part suppression rule, waterline length via
  Eq. 7-25) reported as an audit chain, and the bare-hull power of
  Eq. 7-27.  Guards: V/√L 0.50–1.20 (knots/√ft — the worked example
  pins the units) and the digitised C₀ band L/Δ^(1/3) 4.88–6.41.
  Acceptance: the published table 7-8 example reproduces to
  +0.1 % / +0.0 % on effective power (C₄ 441.3/400.7 vs 441/401).
  Holtrop & Mennen remains a registered placeholder pending its
  source paper; a selectable-algorithm registry is in place.
- Severe wind and rolling criterion (plan task 3.5b):
  `weather_criterion` evaluates IMO 2008 IS Code part A 2.3 end to
  end — the wind levers (lw1 = P·A·Z/(1000·g·Δ) at 504 Pa, gust
  lw2 = 1.5·lw1), the 2.3.4 roll chain (X1/X2/k/s factor tables with
  linear interpolation, r = 0.73 + 0.6·OG/d, rolling period
  T = 2·C·B/√GM on the free-surface-corrected GM, φ₁ = 109·k·X1·X2·
  √(r·s)), the steady-wind heel against the 16° / 80 %-deck-edge
  limits, and the normative areas a and b with the b ≥ a verdict.
  Applicability guards refuse ships outside B/d < 3.5,
  KG/d − 1 = −0.3…0.5, T < 20 s (2.3.5; MSC.1/Circ.1200 model tests
  are the alternative).  Sources: criterion text and tables verified
  verbatim against a public reproduction of the code and
  cross-checked against IMO resolution A.562(14) — which restores the
  B/d = 3.3 X1 row the reproduction omits.  TB-001 passes with wide
  margins (a 0.345 vs b 1.527 m·rad); the task book now carries the
  windage block ([ASSUMED] hull-side area, deckhouse neglected).
- Intact stability criteria (plan task 3.5): `intact_stability_criteria`
  evaluates IMO 2008 IS Code Part A 2.2 — the three GZ-curve area
  requirements (0.055/0.09/0.03 m·rad with down-flooding angle
  handling), the 0.2 m lever at 30° or greater, the 25° maximum-angle
  requirement and GM0 ≥ 0.15 m — one JSON-serializable verdict per
  criterion.  `free_surface_arm` applies the Ship Theory vol. 1
  sec. 5-4 free-surface correction (50 %-fill rule, prismatic
  rectangular tanks) to the arm curve; `Tank` now carries optional
  moulded prism dimensions.  The CLI `run` prints the criteria table
  after the GZ curve; the task book takes an optional
  `constraints.stability.flooding_angle_deg`.  TB-001 full load: all
  six criteria PASS (areas 0.748/1.181/0.433 m·rad, GM0 5.306 m).
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
