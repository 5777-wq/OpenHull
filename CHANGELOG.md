# Changelog

All notable changes to OpenHull are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versioning
is semantic (MAJOR.MINOR.PATCH).

## [1.3.0] - 2026-09-26

### Added

- **`openhull check` preflight** (P1-3): seconds-level prediction of
  which guard bands a task book would trip — weight balance, Froude,
  L/B, B/T, L/D, the Ayre speed band, the C0 family band, and the
  draft declaration — with the numbers and exit 0 (all clear) / 1 (a
  refusal is predicted); `--json` for agents.  The reviewer's Cb 0.84
  case predicts the C0 refusal at 4.8324, matching their sweep's
  4.832.  The full-chain-only stages are listed, not guessed.
- **Kwon speed loss wired into `run`** (P1-1b):
  `seakeeping.speed_loss: {beaufort, direction}` runs the whitelisted
  method (library-implemented and tested since 2026-09-23); the
  report, console and JSON carry dV/V1, the speed ratio and the lost
  knots; the honest domain is kept (Cb 0.80 at Fr 0.19 refuses —
  page-verified applicability); without the block the report states
  that all powers are calm-water.
- **`weather_criterion: default`** (P1-5): the [ASSUMED] geometric
  derivation productised (area = Lpp x freeboard with the deckhouse
  neglected — the non-conservative direction, declared; lever =
  depth/2; bilge keels 0; LWL = 1.025 x Lpp) in both `run` and
  `optimize`; report section 4 shows the whole derivation.
- **Feasibility hints on refusals** (P1-2 first half): an ayre refusal
  now carries the nearest feasible Cb under the declared held-(Δ,
  ratios) rule (the reviewer's Cb 0.84 case: bound in (0.78, 0.82],
  matching their measured 0.80–0.82 boundary), or the reachable speed
  window for a speed-band refusal — plus the `optimize` pointer
  (already shipped in v1.2.0).

### Changed

- **`--json` / `--csv` accept optional PATHs and combine** (P2-1):
  bare flags keep the historical stdout behaviour; two bare flags
  refuse with guidance since stdout serves one stream; the JSON
  purity contract is re-pinned at the process boundary.
- **`--csv-step`** (P2-2): the hydrostatics table defaults to 0.1 T
  (10 rows, aligned with the curves chart); 0.25 restores the
  historical 4 rows.
- **`seakeeping.wave_periods`** (P2-4) replaces the two reference
  seas; the report's two roll periods now carry a calibre footnote
  (IS Code 2.3 simple form vs the book's Eqs 3-27/3-49) (P2-3); the
  optimize grid help says how the speed shifts the Cb band (P2-6).
- SKILL.md: the check-first workflow, the new flags and the new
  task-book blocks.  Tests 405 → 419.  Froude band hoisted to
  `FN_BAND`, the C0 band to `C0_FAMILY_BAND` (single sources).

### Deferred (still on the books)

- PyPI wheels (P1-4, waiting on the parked licensing decision), R2-B
  second anchor and Wigley referee (source hunts), the feasible-Cb
  hint's weight-re-balance refinement, P2-8 count automation, the
  two-method resistance cross-check (Holtrop transcription).

## [1.2.0] - 2026-09-25

### Added

- **C0-peak sensitivity diagnostics** (product review round 6, P0-1):
  the digitised C0 family peaks at V/√L = 0.70 on all six curves, and
  near that peak the C4 correction cancels or inflates the V³ power
  growth — the reviewer's ship grew +9.9 %/kn at 15→17 kn where pure
  V³ gives +21 %, so a single-point power figure there is
  trend-unreliable for machinery selection.  The tool now computes,
  from the whitelisted digitised table itself, whether the operating
  point sits in the family's own peak zone, the local slope (%/0.05),
  and an Admiralty-coefficient corridor Ac = Δ^(2/3)·V³/PE at
  V−1/V/V+1 — DISPLAY ONLY (§5 amended before coding, commit 6a78084:
  diagnostics add text, never numbers).  Surfaces: a ⚠ declaration in
  report §5, a console line, and `resistance_sensitivity` in the JSON.
- **Cavitation unchecked contract** (P0-2): an out-of-band sigma now
  renders as ⚠ **未校核（非通过）** — not "declaratively skipped" —
  with the side (low side = the higher-risk direction), qualitative
  direction hints (lower rpm / larger AE/A0 / deeper shaft), and
  `cavitation_unchecked` (sigma, band, side) in the JSON.
- **stdout quickness section** (P0-3): `run` now ends with a
  speed-&-propeller section in ALL states — result (series, D, P/D,
  ηo, PD/PS, cavitation status, sensitivity), refused (stage + one
  line + see --report), not requested.  stdout is the agent-facing
  contract; `--json` purity is unchanged.
- Refusal blocks point to `openhull optimize --grid-cb …` for the
  feasibility sweep instead of leaving the user to blind retries
  (P1-2); the seakeeping section states Kwon speed loss is implemented
  and tested in the library but not yet wired into `run`, and that all
  powers are calm-water (P1-1a); the provenance note is no longer
  truncated mid-sentence (P2-5); SKILL.md's guard table gains the C0
  peak-zone row and the cavitation wording.

### Deferred (recorded as backlog)

- `openhull check` preflight subcommand (P1-3), PyPI wheel publication
  (P1-4, interacts with the parked licensing decision), weather-
  criterion default mode (P1-5), Kwon wiring into `run` (P1-1b),
  refusal-block feasible-Cb bound (P1-2 first half), P2-1/2/3/4/6,
  and the mid-term two-method resistance cross-check.

## [1.1.0] - 2026-09-25

### Added

- **Hard design draft** (`requirements.drafts.draft_is_hard: true`,
  owner-approved R2-A of the draft decision): the declared draft
  becomes the CONSTRAINT and B/T the solved variable — bisection over
  the guard band [2.00, 3.50] with one full Norman balance per trial,
  converged to ±1 cm, under the same held-(L/B, Cb) rule the v1.0.3
  hint declares; the one-shot residual is gone (hint and hard solve
  agree to 0.27 %).  A draft the band cannot reach is refused with the
  band-edge numbers (exit 2).  Acceptance = the review's own
  precondition: the JBC reverse anchor lands the solved dimensions
  within ±5 % of the NMRI particulars (L −1.94 %, B +1.69 %).  The
  whitelist §5 entry was amended before coding; the second (Panamax-
  class) reverse anchor stays open as R2-B pending a page-verifiable
  source.  Default behaviour is untouched: the flag is absent from
  every existing task book.
- Surfaces: `draft_is_hard` / `hard_draft_b_over_t` /
  `hard_draft_iterations` in the JSON summary, a §1 report line, a
  console line.  Tests 384 → 393; VALIDATION item 24.

### Added (from the unreleased docs batch)


- The waterline convention is stated where it bites (AGENTS.md §5,
  SKILL.md): one waterline per `run` — the declared task-book value
  when present, else Ayre's standard 1.025*Lpp — and, in the scan, each
  candidate uses its own 1.025*Lpp while the declared task-book L_WL
  feeds only the weather criterion.  Scaling a declared L_WL/Lpp ratio
  with the candidates is recorded as an open direction, deliberately
  not implemented (review round 5: all v1.0.5 claims independently
  reproduced, no new defects; both suggestions adopted).
- `.gitignore` covers the session temp files (`_commit_*.txt`,
  `_release_*.md`, `_probe_*.py`) — a second lock behind the
  stage-explicit-paths rule after the v1.0.5 slip.

## [1.0.5] - 2026-09-24

### Fixed

- **The scan evaluated two different ships per candidate.** The
  reference-speed solve took the task book's ABSOLUTE
  `length_waterline_m` (285 m — the JBC's own waterline) while the
  design point's effective-power call took Ayre's default
  (1.025*Lpp).  Candidates span Lpp 231-301 m, so for a 301 m
  candidate the two calls disagreed by 8.4 % in effective power, and
  a hull could appear to absorb more than the reference power at the
  Ayre band floor yet less at its own design speed — impossible for
  one hull — and was refused as unbalanceable.  One waterline rule now
  applies to the whole scan (`_candidate_lwl`, Ayre's standard); the
  task book's LWL keeps its declared role in the weather criterion.
  The identity "PE at the design speed / eta_D = recorded shaft power"
  now holds to 1.1 % over every candidate and is pinned by a test; it
  was 8.4 %.
- The CLI run had the same split (effective power with Ayre's
  standard, the propeller factors with Lpp): one value is now used for
  both — the declared LWL when the task book carries one, else
  1.025*Lpp.  Move on the 45,000 t in-band case: D 7.425 -> 7.417 m,
  eta_o 0.5632 -> 0.5647, delivered 13,473.8 -> 13,440.6 kW.
- Off-axis disclosure is per candidate and classified
  (`reference_speed_note` on every design, `off_reference_causes` in
  the scan summary): **balance below band** / **balance above band** /
  **validity gap**.  v1.0.4's single sentence ("absorbs more than the
  reference at the Ayre band floor") was wrong for part of the
  population; the acceptance run now shows 17 off-axis designs, all
  `below band`, and 26 of 61 designs on the Pareto front (was 8 — the
  spurious refusals had been shrinking the pool).
- The reference-power refusal names both powers
  (`DHP 41,336 kW x eta_D 0.512 x eta_S 1.00 -> required P_E 21,000 kW`)
  instead of quoting "target 21000 kW" next to "dhp_kw 41336", which
  read like a contradiction.
- Tolerated two more constructed boundaries (same class as N3): the
  tip-clearance gate (D <= 0.75 T, the search window's own edge) and
  the eta_o sanity band, both via `spec.within_band`.

### Changed

- Acceptance (TB-001S, 192 points, 16 kn): 61 feasible, Pareto 26,
  median reference power 41,336.0 kW, refusals Ayre C_0 69 / Ayre band
  35 / propeller wake 18 / weather 9.  Reviewer's 100,000 t / 20 kn
  grid unchanged at 101 feasible / 41 Pareto / 59,919.5 kW.
- Test counts move to 384 (376 passed + 8 skipped without the optional
  seakeeping extra).

## [1.0.4] - 2026-09-24

### Fixed

- **The design-space scan ran its propulsion stage at 3.78x the ship
  speed.** `optimize.py` converted the service speed as
  `service_kn / 0.514444` — dividing where knots->m/s multiplies — so
  every scan since task 3.6 handed `Va = 25.7 m/s` to a 20 kn ship and
  every downstream gate judged that phantom vessel: whole bands were
  refused on `d_bounds_m` (empty J intersection) and `thrust_n`, and
  where the search still bracketed, it reported propellers designed
  for the phantom speed (TB-001S: D 10.09-11.25 m, eta_o 0.737-0.750,
  22.5-27.3 MW; corrected: D 7.74-8.42 m, eta_o 0.406-0.467, 36.0-49.5
  MW).  Corrected numbers and the before/after table are in VALIDATION
  item 17; the reviewer's 100,000 t / 20 kn grid — the basis of the
  "20 kn is not attainable for this ship" reading — goes from 0 to 100
  feasible designs (median reference power 59,946.3 kW).  Pinned by a
  check on every recorded design: the implied advance speed J*n*D must
  lie in [0.55, 1.0] x V.
- **Band guards no longer compare exactly** (`spec.within_band`, 1e-9
  relative): the chain recomputes the guarded ratios through a
  cube-root round trip, so the grid endpoint B/T = 3.5 — the guard
  band's own ceiling — became 3.5000000000000004 for some L/B and the
  point was refused as a floating-point artifact (review N3: the
  producer had been snapped to the endpoint, the consumer kept
  comparing exactly).  Real overshoots are unaffected.  Applied to the
  L/B, B/T, L/D and Froude guards and to both Ayre band guards.
- The propeller diameter window and the series J domain are
  intersected through one shared guard that prints both bands, the
  revolutions and the advance speed on refusal — a unit slip and a bad
  window used to look identical from the outside (R-4).
- Report: the two deltas (§1 weight-balance closure, §2 hull
  integration) are distinguished by a 口径注 with their gap size (R-2),
  and the draft mismatch reads by direction ("声明值低于平衡值
  0.425 m") instead of a signed number (R-3).
- Test collection: `tests/test_seakeeping_bem.py` used a module-level
  `importorskip`, which reports one skip while collecting none of the
  tests — without the optional extra a run printed "collected N"
  smaller than "passed + skipped" and hid how many cases went unrun.
  Marked instead, so the arithmetic is exact (R-5).

### Changed

- The scan summary declares `off_reference_axis`: feasible designs that
  already absorb more than the reference power at the Ayre band floor
  have no in-band balance, are refused rather than extrapolated, and
  stay out of the Pareto test by design (26 of 61 in the acceptance
  run).  The sparse attainable-speed axis is declared, not discovered.
- Acceptance and test counts move to 381 (373 passed + 8 skipped
  without the optional seakeeping extra).

## [1.0.3] - 2026-09-24

### Added

- **Draft-declaration back-solve hint** (owner-approved Plan 0 of the
  R2 decision, 2026-09-24): a task book whose declared design draft
  differs from the weight-balance draft by more than 5 cm now gets the
  B/T the declaration would need, under one explicitly stated rule —
  hold the displacement volume, Cb and L/B, i.e. L and B both scale,
  so B/T ~ T^-1.5 — reported in the console summary, in the Markdown
  report text, and as `draft_mismatch_hint` in the JSON summary.  The
  verdict is taken against the chain's own B/T guard band [2.00, 3.50]
  and on the value a reader would type (3 decimals); a required ratio
  outside the band is declared un-extrapolable instead of being quoted
  as a design point.  Two limits travel with the number instead of
  hiding in a docstring: it is a ONE-SHOT back-solve (the weight
  balance re-iterates on the new dimensions, so acting on it lands
  short of the declared draft by 0.3-1.3 % — measured, pinned by a
  test), and B/T is a statistic of the dimension algorithm rather than
  a task-book field, so the actionable path is stated.  HINT ONLY: the
  statistics, the guards and the weight balance are untouched — no
  automatic re-design, and the R2 question (design draft as a hard
  constraint) stays open pending a reverse-anchor decision.
- `required_b_over_t_at_draft` and the band constants
  `L_OVER_B_BAND` / `B_OVER_T_BAND` / `L_OVER_DEPTH_BAND` are public
  (package `__all__`), so a frontend can ask the same question.

### Changed

- The chain-solve guard bands now come from those constants instead of
  being written twice, so a ratio the hint calls acceptable is one the
  guard accepts.  Regression: 16 new tests (-> 375 total),
  including the T^-1.5 law against an independent volume-based solve,
  the identity at the current draft, and a boundary test pinning the
  rounding semantics (a raw 3.5002 shown as 3.500 counts as IN band,
  because 3.500 is what the guard accepts).

### Fixed

- CHANGELOG bookkeeping: the roll-damping block that sat under
  `[Unreleased]` has shipped since v1.0.0 and is folded into that
  section; the "speed loss stays unimplemented" clause it carried had
  been overtaken by the Kwon implementation listed in the same release.

## [1.0.2] - 2026-09-24

### Fixed (v1.0.1 re-verification batch)

The external reviewer re-tested v1.0.1 on a cold install: 8 of the 9
earlier findings confirmed fixed; four NEW residual defects were
found on the success path and are fixed here (each with a regression
test), plus the reviewer's data-quality suggestion:

- **N1 report rendered the propeller fields as em-dashes**: the
  report asked for `blades_z` / `eta_o`, neither of which the summary
  carried (actual key `eta_open_water`; `blades_z` never written).
  The in-band success report now shows 叶数 Z and ηo with real
  numbers; regression asserts no "= —" in the propeller section.
- **N2 floating-point draft guard missed the scan path**: the scan
  built [0.9T, T] raw and six grid points were refused by a
  sub-nanometre overshoot.  The clamp is now a shared helper
  (`hydrostatic_draft_rows` in hydrostatics.py) used by the CLI
  (three call sites) and the scan - one implementation, one guard.
- **N3 a grid line deleted itself**: the B/T = 3.5 endpoint
  generated as 3.5000000000000004 and was refused by the
  `2.0 <= B/T <= 3.5` band, silently dropping an entire grid line.
  Grid axes now snap their endpoints to the declared bounds.
- **N4 `--json` was not composable**: the artefact confirmation
  lines printed to stdout after the JSON body, breaking the
  machine-readable contract for `--json` (and polluting `--csv`
  redirections).  Confirmations now go to stderr; a regression test
  parses `--json --report` output with json.loads.
- **Refusal breakdown by violating field** (reviewer section 3): the
  scan summary now exports `refusal_fields` (stage + the violating
  field parsed from the refusal text) alongside the stage
  histogram, so data gaps are not reported as design verdicts.
- Documentation alignment: the skill's inline task-book example now
  matches the shipped asset, the mis-attributed skip example is
  corrected, and the documented test count matches reality
  (359; seakeeping cases skip without the optional extra).

## [1.0.1] - 2026-09-24

### Fixed (external review batch — all nine findings)

- **P0 propeller chain on the in-band path**: three stale attribute
  names (wake_fraction/thrust_deduction) crashed every run whose
  service point passed the resistance band; the helper is now
  thrust-led (same route as the scan) with STAGED refusals
  (stage: ayre / propeller) and the cavitation check degrades to a
  declared note when sigma leaves the verified Burrill band.  Pinned
  by a regression test on an in-band task book.
- **P0 one design draft**: the whole chain (hull grid, hydrostatics
  table, charts, RAO) now uses the weight-balance draft; the declared
  task-book draft is checked and any mismatch beyond 5 cm is REPORTED
  in the summary and the report instead of crashing or silently
  mixing two values.  Fixed a rounding guard where draft rows could
  overshoot the deepest tabulated waterline by fractions of a mm.
- **P0/P1 deliverables answer the question**: the report renders a
  staged refusal as a structured Chinese block (refusing stage,
  effective L/Delta^(1/3) in the book's own tonnes convention,
  verbatim reason for traceability, likely causes, actionable
  directions, professional-judgement note) and distinguishes
  NOT-REQUESTED from REFUSED; `reference power` prints as
  "unavailable (no feasible design)" instead of a bare None.
- **P1 optimize truthfulness**: every artefact in `outputs` is now
  actually written (feasible CSV always, header-only when empty);
  the full rejected-point list is exported (rejected_points.csv +
  scan_summary.json); a zero-feasible scan renders a refusal scatter
  coloured by refusing stage instead of silently producing nothing.
- **P2 install path**: uv.lock regenerated against the official PyPI
  index (no downstream mirror 403s); the skill pins installs to the
  release tag.
- Report header now records the tool version; the optimize progress
  output is one line per candidate (readable redirected logs).

## [1.0.0] - 2026-09-23

### Added

- Stage 5 — documentation and community release: MkDocs site
  (auto-assembled from VALIDATION/CHANGELOG/CONTRIBUTING on GitHub
  Pages), bilingual CONTRIBUTING guide, bug/formula-proposal issue
  templates, PR provenance checklist, repository description and
  topics.
- Roll damping quantification from the whitelisted source itself
  (pp.392-394, page-verified): table 3-6 extinction law, table 3-7
  class values (large cargo ships print B15 = 0.0190 -> B20 ~
  0.0173; general preliminary estimate B20 = 0.0200), the mu ranges
  (0.035-0.05 / 0.055-0.07), Eq.(3-26) general magnification, and
  the Eq.(3-59) energy-equivalent quadratic-damping chain — the
  resonant roll amplitude now solves from a declared sea state
  (A = alpha_m0/(2 mu(A))).  The BEM RAO layer injects a
  book-mu-calibrated equivalent viscous damping on the roll DOF
  (capytaine radiation adds on top, conservative).  The GZ paper
  anchor is accepted as documented; the Wigley referee remains open.
- Kwon speed-loss estimation (owner-approved open-source retrieval):
  whitelisted from the open-access transcription (Cheng et al.,
  JMSE 2025, 13(1), 42, section 2.2, page-verified against the
  archived PDF; primary literature Kwon 1981 Newcastle thesis
  archived).  Percent speed loss and weather/calm speed ratio by
  block coefficient, Froude number, Beaufort number, displacement,
  weather direction and loading; the paper's own KCS comparison
  reproduces within 0.01 of f_w; non-positive corrections are
  refused, not faked.

### Changed

- Backlog dispositions recorded (AGENTS.md section 5): speed loss
  implemented via Kwon; ShipD confirmed MIT-licensed (compatible);
  Wigley exact-table referee remains open pending a page-verifiable
  table source.

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
  empty set with every refusal declared.  *(Superseded in v1.0.4: the
  scan's propulsion stage ran at 3.78x the ship speed, so these
  numbers are hull-independent but power-wrong — the same grid now
  gives 61 feasible / 8-design front at 41,336.0 kW, see VALIDATION
  item 17.)*
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
