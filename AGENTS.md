# OpenHull — AGENTS.md (Project Constitution)

> Chinese version: [AGENTS_zh.md](AGENTS_zh.md). The English version is
> canonical; the two are kept in sync — report a discrepancy as an issue.

Binding technical conventions for humans and AI agents working on OpenHull.
Any code, test, or document that contradicts this file is wrong by definition.

**Amendment rule:** every change to this file requires explicit owner
approval and is recorded in the internal work log. Version history is kept
in git once this file is committed.

---

## 1. Units

- Internal computation is strict SI: **metres, cubic metres, metric tonnes
  (t), kilowatts, seconds**. Speeds are computed in m/s.
- Task books and console/CSV output may accept or display **knots**;
  conversion happens only at input/output boundaries, never inside
  calculation modules.
- **Angles are in degrees everywhere**, including function interfaces.
  Convert to radians only at the trigonometric call site.
- Constants: seawater density ρ = 1.025 t/m³ (fresh water 1.000 unless a
  task book says otherwise), gravitational acceleration g = 9.81 m/s².
  Any other value must come from the task book.

## 2. Symbols

| Symbol | Meaning | Code identifier |
|---|---|---|
| L | length between perpendiculars (Lpp) | `lpp` |
| B | moulded beam | `beam` |
| D | moulded depth | `depth` |
| T | moulded draft (Chinese texts also use d) | `draft` |
| ∇ | displacement volume, m³ | `displacement_volume` |
| △ | displacement mass, t | `displacement` |
| DW | deadweight, t | `deadweight` |
| LW | lightweight, t | `lightweight` |
| Cb, Cm, Cw, Cp | block / midship / waterplane / prismatic coefficient | `cb`, `cm`, `cw`, `cp` |
| LCB, LCF | longitudinal centre of buoyancy / flotation, % Lpp, forward positive | `lcb`, `lcf` |
| KB, KM | centre / metacentre of transverse stability above keel | `kb`, `km` |
| BMT, BML | transverse / longitudinal metacentric radius | `bmt`, `bml` |
| GM | metacentric height (KG + GM = KM) | `gm` |
| TPC | tonnes per centimetre immersion, t/cm | `tpc` |
| MTC | moment to change trim one centimetre, t·m/cm | `mtc` |
| Fn | Froude number, V/√(g·L) | `fn` |

Module and variable names follow design-stage vocabulary (`main_dimensions`,
`hydrostatics`, `linesplan`, `resistance`, `propeller`, `stability`,
`drawing`) so that a naval architect can navigate without a glossary.

## 3. Validation benchmarks

- Validation ships: **JBC** (primary) and **Series 60 Cb = 0.80**
  (secondary / mother hull). Sources and anchors:
  `examples/data/DATA_SOURCES.md`.
- First design task book: `examples/taskbook_bulk_carrier.yaml`.
  Every quantity there carries a provenance tag — `[NMRI]` (official),
  `[DERIV]` (formula stated inline), or `[ASSUMED]` (owner-approved).
- **No test asserts a number without a published source or an owner-approved
  anchor.** Estimated values are never used as validation targets.

## 4. Acceptance tolerances

Central table; per-task criteria in the internal plan defer to it.

| Quantity | Benchmark | Tolerance |
|---|---|---|
| Displacement volume at design draft | JBC | ±1 % |
| Block coefficient at design draft | JBC | ±0.005 |
| KM = KB + BMT | JBC design draft | ±2 % |
| TPC | JBC design draft | ±3 % |
| GM | JBC full load | ±5 % or 0.05 m, whichever is larger |
| Bonjean section areas | published values if available | ±2 % |
| Effective power (Holtrop–Mennen) | JBC / Series 60 published curves | +10…15 % |
| Service speed reproduction | benchmark ship | ±0.5 kn |
| GZ curve maximum point | published curve | angle within ±5° |
| Freeboard check | benchmark ship actual freeboard | reproduce value, identical verdict |
| Weight–buoyancy iteration | convergence | Δdisplacement < 0.1 % between iterations |
| Main dimensions back-estimate | benchmark ship | L, B, D within ±5 %; Cb within ±0.02 |

Report each quantity separately; never merge tolerances or hide a miss
inside an aggregate.

## 5. Formula whitelist

A formula may be implemented **only if its source is listed here**. Each
implementation carries a citation comment (source + equation number or
page, verified against the physical/PDF source at implementation time —
no page numbers from memory).

**Main dimensions**
- Watson, D.G. & Gilfillan, A.W. (1977), "Some Methods of Estimating
  Merchant Ship Powers", Trans. RINA, vol. 119 — deadweight/displacement
  ratio method, Cb–Fn statistical relations.
- Schneekluth, H. & Bertram, V., *Ship Design for Efficiency and Economy*
  (2nd ed., Butterworth-Heinemann) — statistical ranges of principal
  dimension ratios for merchant ships.

**Weight estimation (lightweight) and weight-buoyancy balance**
- Xie Yunping, Chen Yue, Zhang Ruirui & Liu Kefeng, *Ship Design
  Principles* (National Defense Industry Press) — section 2.2.2:
  Eqs.(2-3)/(2-4) deadweight-ratio method; Eq.(2-5) bulk-carrier
  eta_DW regression (applicable DW 5,000–60,000 t only); Table 2-3
  component shares of lightweight; Table 2-4 bulk-carrier steel-weight
  exponents; Eqs.(2-13)/(2-22) cubic-modulus and exponent steel-weight
  forms; Eq.(2-42) outfit area modulus; section 2.2.2 worked example
  (35,000 t bulk carrier) used as the zero-circularity validation
  anchor.
- Lin Yan (ed.), *Ship Design Principles*, 4th ed. (Dalian University
  of Technology Press) — section 2.1.3: Eqs.(2-6)/(2-7) deadweight-ratio
  method (cross-checked against Xie, identical), Eqs.(2-11)/(2-29)
  cubic-modulus steel/outfit weights, displacement margin 2–5 % of
  lightweight (large ships take the low end); section 4.3.3 Table 4-3
  eta_DW statistics (double-hull bulk carrier 0.78–0.86); section 4.3.4
  gravity-buoyancy balance and the Norman coefficient (delta-Delta =
  N * delta-DW).
- Zhang Jian & Zhang Jing (eds.), *Ship Structural Strength* (National
  Defense Industry Press, 2024) — section 3.2.2, Eq.(3-27) static
  balance convergence criterion |W − B|/W ≤ (0.1–0.5) %, lower bound
  adopted.

**Hydrostatics / stability geometry**
- Principles of Naval Architecture (SNAME), numerical-integration
  chapters — Simpson's-rule integration conventions.
- Simpson's 1st/2nd-rule integration implemented in-package (no
  black-box quadrature).

**Lines plan**
- Lackenby, H. (1950), "On the systematic geometrical variation of ship
  forms", Trans. INA, vol. 92 — parent-hull transformation.
- Todd, F.H. & Frick, C.A., DTMB Report 1712, "Series 60 — Methodical
  Experiments with Models of Single-Screw Merchant Ships" — offsets and
  form coefficients of the mother hull.

**Resistance**
- ITTC 1957 model–ship correlation line — frictional resistance.
- Holtrop, J. & Mennen, G.G.J. (1982), "An Approximate Power Prediction
  Method", International Shipbuilding Progress, vol. 29 — residual
  resistance, appendage/air corrections, propulsion factors.

**Freeboard**
- International Convention on Load Lines, 1966, as amended by the 1988
  Protocol and subsequent IMO resolutions — Type B tabular freeboard.

**Intact stability criteria**
- IMO Resolution MSC.267(85), International Code on Intact Stability,
  2008 (IS Code) — general stability criteria.

**Propeller (preliminary)**
- AU-series chart data; the specific regression to be pinned here at
  task 3.3 before any implementation.

**Adding a formula:** propose the source, owner approves, this section is
amended first, implementation second. A formula without a whitelisted
source must not be merged.

## 6. Applicability guards

- Every empirical formula declares its applicability range (Froude number,
  form-coefficient ranges, size range) as data next to the implementation.
- Out-of-range input **raises an error** with the violated bounds — the
  module refuses, it does not extrapolate silently.

## 7. Out of scope (red lines)

- No CFD. First-release resistance comes from whitelisted empirical
  formulas; OpenFOAM-class simulation is a post-v2.0 topic.
- No free-form hull surface generation. Hull forms are produced only by
  transforming a parent hull's offsets (Lackenby); fairness creation from
  zero is deferred until the transformation path is proven.
- No detailed design: no structural scantlings, no classification-society
  plan approval workflow, no outfitting. Output is preliminary-design grade.
- No estimated number may be presented as published data; provenance tags
  are mandatory in examples and reports.

## 8. Code standards

- Python ≥ 3.11, managed with uv, src layout (`src/openhull/`).
- Type annotations on every public function; dataclasses validated at
  construction (e.g. `Cb = 1.5` must raise, with an explanation of why
  the value is invalid — constraint plus physical/mathematical reason).
- **Selectable algorithms**: every computational module exposes its
  methods as named algorithms behind a registry (strategy pattern).
  Each algorithm carries a stable id, its whitelist citation, and its
  applicability range as data, so task books and future frontends can
  select algorithms per design step and grey out out-of-range choices.
  The default algorithm per step is pinned in the task book or the
  module default.
- **Agent-facing contract**: every computation is a pure function over
  validated dataclasses, and every result is JSON-serializable. The CLI
  plus YAML task books form the stable invocation contract so that
  future MCP servers, skills, or plugins wrap the toolkit without
  touching the numerics (the end goal: an agent-native ship design
  suite — "Codex/ZCode for ship engineers").
- NumPy arrays for offsets, Bonjean tables, hydrostatic series.
- Every public function docstring states: purpose, inputs, outputs, and
  the unit of every quantity.
- Core numerics (integration, transformation, solvers) are implemented
  in-package; third-party packages are limited to numpy, matplotlib
  (plots), ezdxf (DXF), pyyaml (task books), pytest (tests).
- Every module ships pytest cases: normal value, boundary value, and
  benchmark-ship validation with explicit asserted numbers.
- Programs are deterministic: no hidden globals, no time- or
  machine-dependent results.

## 9. Repository discipline

- Git operations happen in this repository root only.
- Internal notes, work logs, and plans live outside the repository and are
  never committed or pushed.
- Anything pushed must meet the release checklist: professional naming,
  community-facing tone, no personal notes, no private paths, account
  names, or credentials.
- Commit messages follow Conventional Commits
  (`feat:`, `docs:`, `test:`, `chore:` …).
- A task is closed only when its acceptance numbers pass, tests are green,
  and the internal log/status files are updated.
