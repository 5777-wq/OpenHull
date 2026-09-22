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
  `[DIGITIZED]` (added at task 3.3) marks a quantity read off a printed
  chart by programmatic digitisation with a declared tolerance; the
  source book's own worked-example readings bound the reading error.
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
- Sheng Zhenbang & Liu Yingzhong, *Ship Theory*, vol. 1, 2nd ed.
  (Shanghai Jiao Tong University Press) — ch. 2: numerical integration
  (trapezoidal rule Eqs.(2-8)/(2-14); Simpson's first rule, n even;
  second rule, n a multiple of 3; integrand conventions y, y*x, y^3/3,
  y*x^2); ch. 3: even-keel buoyancy by the vertical method
  (∇ = ∫Aw dz, KB = ∫z·Aw dz/∇, Aw, centre of flotation xF, Cwp);
  section 4-2: Eqs.(4-7)/(4-8)/(4-9) transverse and longitudinal
  metacentric radii BMT = I_T/∇, BML = I_LF/∇, I_LF = I_L − Aw·xF²;
  section 4-4: Eqs.(4-15)/(4-16) MTC = Δ·GML/(100·L) ≈ Δ·BML/(100·L).
- Principles of Naval Architecture (SNAME), numerical-integration
  chapters — Simpson's-rule integration conventions.
- Simpson's 1st/2nd-rule integration implemented in-package (no
  black-box quadrature).

**Initial stability / floating attitude**
- Sheng Zhenbang & Liu Yingzhong, *Ship Theory*, vol. 1, 2nd ed. —
  section 4-3: Eqs.(4-10)/(4-11) initial-stability formula
  (M_R = Δ·GM·sinφ ≈ Δ·GM·φ); Eqs.(4-19)/(4-20) GM = KB + BM − KG,
  GM_L = KB + BM_L − KG; section 4-7: Eqs.(4-35)–(4-38) free-surface
  corrections GM_1 = GM − Σw1·i_x/Δ (and Eq. 4-37 with i_y).
- Zhang Jian & Zhang Jing (eds.), *Ship Structural Strength* (2024) —
  also supplies the floating-attitude iteration of section 3.2.2:
  Eqs.(3-25)/(3-26) successive approximation of the fore/aft drafts,
  with the Eq.(3-27) balance criteria on both |W − B|/W and
  |xg − xb|/L.

**Large-angle stability (static stability curve)**
- Sheng Zhenbang & Liu Yingzhong, *Ship Theory*, vol. 1, 2nd ed. —
  chapter 5: Eq.(5-1) l = l_s − l_g = (y_Bφ·cosφ + z_Bφ·sinφ) − KG·sinφ
  (l_s the shape arm, l_g the weight arm); section 5-2 the
  equal-displacement (direct) method and its computer procedure —
  equal-volume heeled waterline per heel angle by iteration on the
  centreline crossing z_i (initial value = the even-keel draft) with
  the update z_i ← c·(z_i + dΔ/(w·A_Wφ)), c = 1, convergence
  |Δ − Δ_φ| ≤ ε with ε = 0.1 % of Δ, heel sequence 10°…80° (pages
  88–91 visually verified against the scanned original, 2026-09-20);
  section 3-5 Eq.(3-41) the Vlasov per-station integrals
  a = ∫y dz, b = ½∫y² dz, c = ∫zy dz — realized by direct polygon
  clipping of the tabulated sections (the book's own sanction of
  numerical integration, p. 46); section 5-5 Eqs.(5-15)/(5-16) the
  origin slope of the GZ curve equals GM (used as a test identity);
  section 5-6 dynamic stability T_R = Δ·∫l dφ; section 5-4 free-surface
  influence δl = M_H/Δ with the 50 %-fill rule (implemented in task 3.5
  for prismatic rectangular tanks).
- Hussain, Md Daluar & Amin, Osman Md (2021), "A Comprehensive Analysis
  of the Stability and Powering Performances of a Hard Sail-Assisted
  Bulk Carrier", Journal of Marine Science and Application, vol. 20,
  no. 3 — published JBC full-load GZ analysis (MAXSURF model of the
  plain hull, before sail installation; their Table 7): angle of
  maximum GZ 40.9° (acceptance anchor, tolerance ±5° per section 4)
  and maximum GZ 3.309 m (loose demonstration band only — the paper's
  KG is unpublished; OpenHull runs the NMRI KG 13.29 m).

**Lines plan**
- Lin Yan (ed.), *Ship Design Principles* (船舶设计原理), 4th ed.
  (Dalian University of Technology Press), chapter 5 lines design,
  "②勒根贝尔(Lackenby)法" pp. 211–212 — the Lackenby transform as
  transcribed in the textbook: Eq.(5-35) quadratic transform function
  dx = c(1−x)(x+d); Eq.(5-36) boundary conditions dx(l_pf) = dl_pf,
  ∫dx·dy = dCp; Eq.(5-37) explicit dx; Eqs.(5-40)–(5-43) moment arms
  h = B − C·dl/dCp with B, C and the second-moment arm K² = ∫x²y dx/Cp
  (plain dx integral — pinned by the parabolic closure check Cp = 2/3,
  x_bf = 3/8, K² = 1/5, B_f = 3/5); Eqs.(5-44)/(5-45) fore/aft split
  with parallel-body changes, (5-46)/(5-47) the dl = 0 case;
  Eqs.(5-31)–(5-34) buoyancy/moment balance. OCR of every formula
  visually verified against the scanned pages 211–212.
- Lackenby, H. (1950), "On the systematic geometrical variation of ship
  forms", Trans. INA, vol. 92 — original method (optional cross
  reference; not required for implementation).
- Todd, F.H. & Frick, C.A., DTMB Report 1712, "Series 60 — Methodical
  Experiments with Models of Single-Screw Merchant Ships" — offsets and
  form coefficients of the mother hull.

**Resistance**
- Ayre method as transcribed in Ship Theory vol. 1 (Sheng Zhenbang &
  Liu Yingzhong, 2nd ed.), section 7-1, pp. 291–296 — Eqs.(7-21)–(7-27)
  effective power of the standard form and its corrections; tables
  7-5 (standard Cbc and LCB), 7-6 (Kbc), 7-7(a)/(b) (Kxc), figure 7-3
  (C₀ chart, digitised for L/Δ^(1/3) = 4.88–6.41) and the worked
  example of table 7-8 (acceptance anchor).  Units trap pinned by the
  example: V/√L is knots over √feet, L/Δ^(1/3) and Fr are SI.
  Owner approval: task 3.1 implementation plan (2026-09-21).
  Amendment-order note: implemented and whitelisted in the same
  session, whitelist commit immediately following — recorded here
  for transparency.
- ITTC 1957 model–ship correlation line — frictional resistance.
- Holtrop, J. & Mennen, G.G.J. (1982), "An Approximate Power Prediction
  Method", International Shipbuilding Progress, vol. 29 — residual
  resistance, appendage/air corrections, propulsion factors.

**Freeboard**
- International Convention on Load Lines, 1966, as amended by the 1988
  Protocol and subsequent IMO resolutions — Type B tabular freeboard.
- Lin Yan, *Ship Design Principles*, 4th ed., section 3.4.2 — the
  ICLL computation as transcribed in a textbook: Eq.(3-15)
  F = F0 + f1 + ... + f5; Table 3-9 standard-ship basic freeboard
  (L = 24-365 m, types A/B; transcribed values visually verified
  against the scanned original, PDF part 1 page 71 / book page 60);
  Eqs.(3-16)-(3-20) the f1...f5 corrections with Tables 3-10/3-11/3-12.
  The domestic-rules variant (Xie Yunping section 2-9, Tables 2-7/2-8)
  is transcribed in the knowledge base but not implemented - its
  length range (20-230 m) does not reach the benchmark ships, and its
  Table 2-8 carries known OCR-suspect values pending visual check.

**Intact stability criteria**
- IMO Resolution MSC.267(85), International Code on Intact Stability,
  2008 (IS Code) — general stability criteria, Part A section 2.2
  (text verified verbatim against a public reproduction of the code,
  imorules.com, fetched 2026-09-21): 2.2.1 area under the GZ curve
  not less than 0.055 m·rad up to 30°, not less than 0.09 m·rad up to
  40° or the down-flooding angle if less, not less than 0.03 m·rad
  between 30° and 40° (or the down-flooding angle); 2.2.2 static lever
  at least 0.2 m at an heel of 30° or greater; 2.2.3 maximum GZ at an
  angle of at least 25°; 2.2.4 initial GM0 at least 0.15 m.
  Cross-checked against Xie Yunping *Ship Design Principles* (domestic
  rule: cargo ships GM >= 0.15 m) and the Ship Theory vol. 1 worked
  example table 4-5 (requirements column).
- IMO Resolution MSC.267(85), 2008 IS Code, Part A section 2.3
  (severe wind and rolling criterion) — implemented in task 3.5b.
  Text and coefficient tables verified verbatim against a public
  reproduction of the code (imorules.com, formula images read
  individually, 2026-09-21) and cross-checked table-by-table against
  IMO Resolution A.562(14) (official IMO CDN copy): l_w1 =
  P·A·Z/(1000·g·Δ) with P = 504 Pa (A.562: 0.0514 t/m², same value),
  l_w2 = 1.5·l_w1; roll angle phi_1 = 109·k·X1·X2·sqrt(r·s) degrees
  with r = 0.73 + 0.6·OG/d, OG = KG − d, k = 1.0 round bilge without
  keels / 0.7 sharp bilges / table of A_k·100/(Lwl·B), and the X1
  (B/d), X2 (Cb), s (rolling period) tables with linear interpolation;
  rolling period T = 2·C·B/sqrt(GM) with C = 0.373 + 0.023·(B/d) −
  0.043·(Lwl/100), GM free-surface corrected.  Areas per the
  normative figure (both reproductions agree): a = ∫(l_w1 − GZ)dθ
  from the roll-back angle θ1 = φ0 − phi_1 to the steady-wind
  equilibrium φ0 (GZ extended to negative heel by odd symmetry);
  b = ∫(GZ − l_w2)dθ from the rising intercept of l_w2 with the GZ
  curve to θ2 = min(down-flooding angle, 50°, falling intercept);
  criterion b ≥ a, plus φ0 ≤ 16° or 80 % of the deck-edge immersion
  angle.  Applicability (2.3.5): B/d < 3.5, (KG/d − 1) in −0.3…0.5,
  T < 20 s — outside it the module refuses (MSC.1/Circ.1200 model
  tests are the alternative).  Note: the imorules X1 table omits the
  B/d = 3.3 row; the A.562 original carries 3.3 → 0.84 and the
  implementation follows A.562.

**Propulsion factors (wake, thrust deduction, rotative efficiency)**
- Ship Theory vol. 2 (Sheng Zhenbang & Liu Yingzhong), section 5-2/5-3
  (book pages 58-61) — the Holtrop correlation as transcribed:
  Eqs.(5-38)/(5-39) wake fraction with the auxiliary chain CV=(1+k)Cf+CA,
  CA, C2..C4, C8/C9, C11, Cp1 and the wetted-surface S formula;
  Eqs.(5-48)/(5-49) thrust deduction; Eqs.(5-50)/(5-51)/(5-52)
  relative rotative efficiency (5-50, eta_R = 1.0, the sanctioned
  no-data fallback, is the v1 default).  Every formula visually
  verified against the scanned original pages (2026-09-21).  The
  textbook transcription diverges from other published renderings of
  the Holtrop correlation (reciprocal instead of ratio form of two
  wake terms; twin-screw Cb unsquared; Cb exponent printed as 4 in
  CA) — the whitelisted textbook form is implemented and the
  divergences declared.  Owner approval: task 3.2 implementation
  plan (2026-09-21).

**Propeller (preliminary design: open-water series, chart design, cavitation check)**
- Ship Theory vol. 2 (Sheng Zhenbang & Liu Yingzhong), section 8-2
  (B-δ chart design method and its application) and section 6-5
  (cavitation check):
  - section 8-2, figure 8-1 "AU5-50 open-water characteristic curves"
    (KT and 10·KQ vs J on the left axis, ηo vs J on the right axis,
    P/D = 0.4/0.6/0.8/1.0/1.2) — the only open-water chart printed in
    the book — digitised into `openhull/data/au5_50_openwater.csv`
    ([DIGITIZED], axis-calibrated; cross-checked against the duplicate
    print of the same curves as figure 4-4).
  - the Bp–δ optimum-line construction, steps (1)–(5) of section 8-2,
    with the metric chart definitions BP = N·PD^0.5/VA^2.5 and
    δ = ND/VA (AU charts: metric units, seawater-converted; the chart
    optimum diameter is the behind-hull optimum diameter).  The
    implementation constructs this optimum line numerically from the
    digitised curves — no chart reading at run time; the construction
    doubles as the digitisation self-check against table 8-12.
  - worked example, 25,000 t bulk carrier (Lpp 172 m, B 27.2 m, draft
    9.8 m; w 0.34, t 0.26, ηR 0.982, ηS 0.98; PS 12,000 hp,
    N 118.5 rpm; table 8-11 effective-power curve): AU5-50 terminal
    design Vmax 16.11 kn, D 5.897 m, P/D 0.731, ηo 0.569 (table 8-12,
    figure 8-9) — end-to-end acceptance anchor.  The AU5-65 variant of
    the same ship (Vmax 16.05 kn, D 5.747 m, P/D 0.782, ηo 0.559,
    section 6-5) serves as the cavitation-chain anchor.
  - section 6-5: Eqs.(6-14)/(6-15)/(6-16) — Burrill limit-line check,
    σ0.7R = (p0 − pv)/(½ρV²0.7R), τc = T/(AP·½ρV²0.7R),
    AP ≈ AE/(1.067 − 0.229·P/D); the commercial-ship limit line of
    figure 6-20 (Burrill original) and its figure 6-22 re-plotting
    (Yokoo & Yazaki) both digitised ([DIGITIZED], mutually
    cross-checked): anchors from table 6-2 (σ 0.481 → τc 0.175,
    required AE/A0 0.642) and table 8-29 (σ 0.389/0.407/0.416 →
    τc 0.162/0.164/0.169, section 8-5 MAU4 example).
  - Library-scope declaration: the implemented open-water library is
    AU5-50 only (the book prints no Bp–δ charts for the other AU/MAU
    variants; their worked-example readings anchor the cavitation
    chain and the method, not the series).  A design whose required
    AE/A0 exceeds 0.50 is reported as a shortfall, never silently
    accepted.
- Owner approval: task 3.3 implementation plan (2026-09-22, AU5-50
  route; B-series regression deferred as a possible library-extension
  task).

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
- **No drawing deliverables (decided 2026-09-15)**: geometry outputs are
  delivered as the **offsets table + layered DXF vector data** (the CAD
  side produces drawings from them). PNG/SVG renderings are development
  aids only — they are not project deliverables and are not featured in
  the README.

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
