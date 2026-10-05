# Validation

> OpenHull treats validation as the spine of the project: every computed
> quantity is asserted against a published benchmark or an owner-ratified
> anchor, and every approximation is declared next to its number.
> Benchmarks and data sources: [`examples/data/DATA_SOURCES.md`](examples/data/DATA_SOURCES.md).
> Binding conventions: [`AGENTS.md`](AGENTS.md) (tolerances in section 4).

Status: **stages 1–2 complete** (dimensions + hydrostatics core +
parametric hull generation on real offsets); stage 3 in progress —
stability pillar complete (3.4/3.5/3.5b), resistance estimation
(3.1, Ayre), propulsion factors with the service-speed solver (3.2),
and the propeller module (3.3): Burrill cavitation check, the
Wageningen B-series open-water regression and the optimum-propeller /
terminal-design engine.  279 tests green.
`openhull run` reproduces the chain end to end — dimensions,
hydrostatics, the large-angle GZ curve, the general criteria verdict
and the weather criterion (with `requirements.kg_m` and the
`constraints.stability.weather_criterion` windage block in the task
book).

## Stage-1 acceptance summary (TB-001 / JBC-anchored)

Each quantity is reported separately, per AGENTS.md section 4.

### Main dimensions (task 1.2, chain estimation)

Back-inference from the task-book deadweight (owner-ratified 149,920 t)
against the JBC dimensions:

| Quantity | JBC | Computed | Error | Tolerance |
|---|---|---|---|---|
| Lpp | 280.0 m | 272.4 m | −2.7 % | ±5 % |
| B | 45.0 m | 45.40 m | +0.9 % | ±5 % |
| T | 16.5 m | 16.81 m | +1.9 % | ±5 % |
| D | 25.0 m | 24.32 m | −2.7 % | ±5 % |
| Cb | 0.8580 | pinned by task book | — | ±0.02 |

### Weight–buoyancy balance (task 1.3)

| Check | Result | Criterion |
|---|---|---|
| Balance convergence | 3 passes, final imbalance 0.018 % | \|W−B\|/W ≤ 0.1 % (Eq. 3-27) |
| Displacement reproduction | 181,306 t vs anchor 182,829.1 t → **−0.83 %** | < 1 % |
| Norman coefficient | 1.16 (> 1, physically required) | sanity |
| Method anchor (zero circularity) | Xie Yunping worked example: steel 7,384 t cubic / 7,378 t exponent, reproduced exactly | published numbers |

### Hydrostatics (task 1.4, fitted stage-1 parent hull)

| Quantity | Benchmark | Computed | Error | Tolerance |
|---|---|---|---|---|
| Displacement volume, design draft | 178,369.9 m³ [NMRI] | 178,741.5 m³ | **+0.21 %** | ±1 % |
| KM = KB + BMT | 18.59 m [NMRI GM 5.30 + KG 13.29] | 18.590 m | **+0.000 %** | ±2 % |
| Cb | 0.8580 [NMRI] | 0.85975 | +0.0018 | ±0.005 |
| LCB | +2.5475 %Lpp [NMRI] | +2.5397 %Lpp | −0.008 %Lpp | declared |
| Integrator self-proof | box hull + parabolic hull, closed forms | exact | < 1e-9 | — |
| Cross-flux (Bonjean vs waterline path) | — | −0.001 % | declared | — |

TPC / Aw / KB / LCF have **no published JBC values** (NMRI publishes
none), so per AGENTS.md section 3 they carry definition-identity tests
and closed-form self-proof instead of benchmark assertions; their
benchmark check is scheduled with the real offset tables (stage 2.6).

### Initial stability and floating attitude (task 1.5)

| Check | Result | Criterion |
|---|---|---|
| GM at full load (KG 13.29 m) | 5.300 m vs 5.30 m [NMRI] | ±5 % / 0.05 m |
| JBC ballast condition [NMRI] (never used in any fit) | 89,185.9 m³ at drafts 10.015/7.215 m recovered as 9.942/7.145 m | −0.7 % / −1.0 % |
| Box-hull trim vs closed form | exact to 1e-3 | self-proof |

The GM number is arithmetic on the KM anchor (KM was fitted to
GM + KG in task 1.4, declared circularity). The **ballast condition is
the non-circular check**: those drafts never entered any fit.

### Freeboard (task 1.6)

> Wired into `run` on 2026-09-30 (round-9b): the summary JSON
> (`freeboard`), the console and report §1 now carry this check on the
> balance dimensions; see item 34 for the wiring checks.

| Check | Result |
|---|---|
| Rule minimum (plain type B, ICLL 1966 as transcribed in Lin Yan Table 3-9) | 6,555.8 mm (F0 4,397 + f2 575.5 + f3 1,583.3) |
| Actual freeboard (TB-001: D − T) | 8,500 mm |
| Verdict | **PASS**, margin 1,944 mm |

Table 3-9 was visually verified against the scanned original (rendered
PDF page) before implementation: all 36 rows × 2 columns match, zero
OCR errors.

### Parent-hull transform (task 2.3, Lackenby method)

| Check | Result | Criterion |
|---|---|---|
| Loader: Series 60 parent Cp total / fore / aft (DTMB 1712 printed values 0.805 / 0.861 / 0.750) | 0.8033 / 0.8564 / 0.7501 | ±0.005 each |
| Identity: zero request returns the parent bit-for-bit | exact (array equality) | diff = 0 |
| Transform function closure (parabolic curve y = 1−u²) | Cp 2/3, x_bf 3/8, K² 1/5, B_f 3/5 — printed B_f formula (5-41) equals the moment integral of the shift field | analytic |
| Parallel body fixed at dl = 0 | shift field ≡ 0 on the detected parallel body | by construction (tested) |
| ΔCb = +0.02 on the carried table (acceptance case) | +0.0200 achieved, LCB drift 0.0017 %L | ±0.005 / ±0.02 %L |
| Pure LCB shift +0.5 %L | volume drift −0.00005 Cb | ±0.001 |
| Hydrostatics module re-check on the transformed table | agrees with the table-layer Cb | ±5e-4 |
| Series 60 → JBC demonstration (Cb 0.8580, LCB +2.5475 %L) | lands at 0.8579 / +2.5429 %L in two serial sub-transforms (14 iterations) | demonstration, loose band |
| Cm held through every transform | 0.990582 unchanged | exact |

**How to read the anchors**: the DTMB 1712 prismatic coefficients are a
genuine non-circular anchor (printed in 1963, never entered the code);
the parabolic closure pins the textbook formulas against transcription
errors; the identity check is the natural regression test of a shift
method. The Series 60 → JBC run demonstrates the pipeline reaches an
independent modern benchmark from a 1963 parent without refitting
anything.

### Numerical fairness checks (task 2.5)

| Check | Result | Criterion |
|---|---|---|
| Digitised Series 60 parent (known fair, DTMB 1712 Table 7) | **zero issues** over 27 waterlines × 21 stations | plan acceptance: no false alarms |
| Calibration basis | parent's max measured curvature contrast 12.2 (dimensionless, Lpp²/B scale); absolute alarm floor set to 25 (~2×) | margin test: max contrast < 0.7 × floor |
| Planted single-point spike (+0.06 B at one bow station) | flagged as curvature jump at the right waterline and station | must catch the guilty |
| Planted slope kink (+0.15 m per station ramp) | flagged as curvature jump | must catch the guilty |
| Planted lobe break (plateau dent −0.05 B) | flagged as non-monotonic | must catch the guilty |
| Planted parallel-body wobble (−0.06 m inside the run) | flagged as parallel wobble | must catch the guilty |
| Smooth bulb bump on a low waterline (fair feature) | no alarm (contrast below floor; monotonicity scoped out below 0.5 draft) | no false alarms |
| Real-ship demo (94 m coastal ship, owner's DXF rebuild) | rebuild verified cell-by-cell against the authoritative printed table (273/273 match after 4 printed-sheet corrections); checker reports no mid-body defects (an earlier "3 stern-bottom flags" report was an artefact of the demo grid's z=0 left-fill, retracted) | verification |

### Mother-ship chain on real offsets (task 2.6)

The `openhull run` hull is now built from REAL tabulated offsets: the
packaged digitised Series 60 parent (byte-identical to the examples
CSV, pinned by test; ships inside the built wheel), affine-scaled onto
the balanced task-book dimensions, then Lackenby-transformed onto the
task-book block coefficient.

| Check | Result | Criterion |
|---|---|---|
| Chain at JBC dimensions/targets: displacement volume | within ±1 % of 178,369.9 m³ [NMRI] | ±1 % |
| Chain Cb | 0.8578 vs 0.8580 [NMRI] | ±0.005 |
| Chain KM (CLI end-to-end) | 18.698 m vs 18.59 m [NMRI] → **+0.58 %** | ±2 % |
| Chain LCB | +2.5411 %L vs +2.5475 [NMRI] | ±0.02 %L |
| Affine scaling invariants | coefficients unchanged; half-scale ship displaces exactly 1/8 | exact |
| Bonjean ×-integration vs hydrostatics volume on the chain table | agrees | rel 1e-4 |
| CLI determinism (same task book, two runs) | identical output | equality |
| Packaged data file ships in the built wheel | verified by wheel inspection | — |

TPC / Aw / KB / LCF still have **no published JBC values**; they are
now computed on the real-offsets chain and carry definition-identity
tests plus the cross-flux check.

### Static stability curve (task 3.4)

`gz_curve` computes l(φ) by the equal-displacement method (Ship Theory
vol. 1, sec. 5-2): per heel angle the equal-volume heeled waterline is
found by iterating its centreline crossing (the book's update
z_i += dΔ/(w·A_Wφ), bracketed bisection as fallback), with per-station
immersed areas and moments from exact polygon clipping of the tabulated
sections (the Vlasov integrals of Eq. 3-41, realized without
draft-direction quadrature).  Formula pages 45/88–91/102–103 were
visually verified against the scanned original before implementation.

| Check | Result | Criterion |
|---|---|---|
| Wall-sided box hull vs closed-form GZ(φ) | exact to 1e-8 at 10/20/30/40° | analytic (derived from Eq. 5-1 with z_i = T) |
| Box equal-volume crossing | z_i = T recovered to 1e-6 | analytic |
| Origin slope of the JBC curve | GZ(5°)/sin 5° = GM within **0.04 %** | sec. 5-5 identity (Eqs. 5-15/5-16) |
| Volume conservation at every angle | worst residual ≤ 0.05 % | sec. 5-2: ε ≤ 0.1 % of Δ |
| KM consistency of the chain used | 18.592 m vs 18.59 m [NMRI] | ±2 % (task 2.6 band) |
| Curve characteristics (chain, KG 13.29 m, Δ 182,829.1 t) | max 2.56 m at 31.0°, vanishing 69.4° | qualitative (single hump, closes in range) |
| Published JBC comparison — Hussain & Amin (2021), JMSA 20(3), Table 7 (MAXSURF, plain hull, full load): max 3.309 m at 40.9° | ours 2.56 m at 31.0° | **demonstration band only** (pinned 25–45° / 2.2–3.4 m) |

**Why the published GZ is a demonstration band, not a ±5° anchor.**
The paper analyses the real JBC lines; the OpenHull hull is the declared
Series 60 + Lackenby approximation, with the topside above the design
draft closed wall-sided up to the deck — and the 30–50° range of the
GZ curve is dominated by exactly that geometry.  The paper's KG is
unpublished (its GM 5.702 m implies ≈ 13.0 m against our KM; we use the
NMRI 13.29 m); re-running our geometry at their implied KG still puts
the maximum near 31°, so the angle difference is hull-model, not
loading.  The comparison is retained as a wide regression band and the
zero-circularity acceptance rests on the box closed form and the
sec. 5-5 slope identity.  Candidates to tighten it later: an
authoritative JBC stability source, or real topside geometry from the
JBC IGES.

### Intact stability criteria (task 3.5)

`intact_stability_criteria` evaluates IMO 2008 IS Code Part A 2.2
(general criteria; text verified verbatim against a public reproduction
of the code, imorules.com, 2026-09-21 — cross-checked with Xie
Yunping's domestic GM ≥ 0.15 m and the Ship Theory vol. 1 table 4-5
requirements column).  Areas integrate the free-surface-corrected arm
curve on a 2.5° grid (Simpson; trapezoid on a terminal partial panel);
free-surface arms follow Ship Theory vol. 1 sec. 5-4 with the 50 %-fill
rule.

| Criterion | Required | TB-001 chain (Δ 182,829.1 t, KG 13.29 m) | Verdict |
|---|---|---|---|
| 2.2.1(a) area 0–30° | ≥ 0.055 m·rad | **0.748 m·rad** | PASS |
| 2.2.1(b) area 0–40° | ≥ 0.09 m·rad | **1.181 m·rad** | PASS |
| 2.2.1(c) area 30–40° | ≥ 0.03 m·rad | **0.433 m·rad** | PASS |
| 2.2.2 static lever at ≥ 30° | ≥ 0.2 m | **2.554 m** | PASS |
| 2.2.3 angle of maximum lever | ≥ 25° | **31.0°** | PASS |
| 2.2.4 initial GM0 | ≥ 0.15 m | **5.306 m** | PASS |

| Check | Result | Criterion |
|---|---|---|
| Verdict agreement with the published JBC analysis (Hussain & Amin 2021, Table 7) | identical: all PASS there and here; their areas 0.781/1.319/0.555 m·rad vs ours 0.748/1.181/0.433 (ratios 0.96/0.90/0.78 — the task 3.4 geometry-model attribution applies) | demonstration |
| Rectangular-tank free-surface arm vs closed form δl = w1·V·tanφ·b²/(12·h)/Δ | exact to 1e-12 at 5/10/20/30° | analytic (sec. 5-4, wall-sided prism at 50 % fill) |
| Flooded tank reduces GM0 by Eq. (4-38) and every area | verified | consistency |
| Down-flooding at φf < 30° drops criterion (c) and re-targets (b) and 2.2.2 | verified | 2.2.1 literal text |
| CLI end-to-end (balanced hull) | all six PASS; areas 0.718/1.074/0.356 m·rad; GM0 5.400 m | determinism |

The severe wind and rolling criterion (IS Code 2.3) is implemented in
task 3.5b — see its section below.

### Severe wind and rolling criterion (task 3.5b)

`weather_criterion` evaluates IS Code part A 2.3. Sources: the
criterion text, formula images and the X1/X2/k/s tables were verified
verbatim against a public reproduction of the code (imorules.com,
2026-09-21) and cross-checked table-by-table against IMO Resolution
A.562(14) (official IMO CDN copy) — which also restores the B/d = 3.3
→ 0.84 X1 row the reproduction omits and pins the normative area
definitions of figure 2.3.1. TB-001 windage inputs are task-book
declared ([ASSUMED] hull-side area 2,380 m², deckhouse neglected —
unconservative direction; [DERIV] Z = 12.5 m; [NMRI] Lwl = 285 m).

| Check | Result | Criterion |
|---|---|---|
| 2.3.4 chain vs independent hand evaluation (X1, X2, k, r, s, C, T, φ₁) | X1 0.9445, X2 1.000, k 1.0, r 0.6133, s 0.0636, C 0.3132, T 12.24 s, **φ₁ 20.33°** — all match the hand calculation | analytic |
| 2.3.2 wind levers | lw1 = 8.36 mm (hand value exact), lw2 = 1.5·lw1 | 2.3.2 formula |
| TB-001 chain (Δ 182,829.1 t, KG 13.29 m) | φ₀ 0.090°, deck edge 20.8°, roll-back −20.2°, θ₂ 50°, **area a 0.345 vs b 1.527 m·rad** | all three verdicts PASS |
| Area integrals under grid refinement (2.5° → 1.25°) | change < 2 % (a) / < 1 % (b) | convergence |
| Bilge keels (Ak 200 m² → k < 1) reduce φ₁ | verified | table behaviour |
| 2.3.5 guards (B/d ≥ 3.5, KG/d−1 ∉ −0.3…0.5, T ≥ 20 s, P > 504 Pa) | refuse with citation | constitution §6 |

**Anchor honesty**: no published JBC weather-criterion evaluation
exists to our knowledge, so — like TPC/KB/LCF in task 1.4 — the
binding acceptance is the independent hand evaluation of the whole
2.3.4/2.3.2 chain plus the exact identities (lw2 = 1.5·lw1, the φ₀
intercept, the θ₂ 50° cap), not an external number. The windage area
is the dominant declared assumption; the verdict margins are wide
(b ≈ 4.4 × a), but a deckhouse estimate would scale lw1 and must be
re-run when the general layout defines it.

### Resistance estimation — Ayre method (task 3.1 v1)

`ayre_effective_power` implements the Ayre method as transcribed in
Ship Theory vol. 1 section 7-1 (Eqs. 7-21..7-27, tables 7-5/7-6/7-7a/b,
figure 7-3).  The C₀ chart is digitised (mid-family curves
L/Δ^(1/3) = 4.88..6.41, V/√L stations 0.50..1.30, reading tolerance
±4 units) and the speed-length ratio uses knots/√ft — the worked
example pins both (14 kn on 122 m → 0.70, not 1.27).

| Check | Result | Criterion |
|---|---|---|
| Table 7-8 worked example (Lbp 122 m, Δ 11,970 t, Cb 0.721): C₄ | **441.3 / 400.7** vs published 441 / 401 | reproduction |
| Table 7-8 effective power | **1862 / 2522 kW** vs published 1860 / 2521 (errors +0.1 % / +0.0 %) | §4 allows +10…15 % |
| Fuller-ship sign flip at 15 kn (Cb 0.721 > Cbc 0.705 → Eq. 7-22 negative, LCB penalty suppressed) | verified | correction rules |
| Guard: JBC service speed 14.5 kn → V/√L = 0.478 < 0.50 | refused with the value | §4 band + §6 |
| Guard: L/Δ^(1/3) outside 4.88..6.41, LCB offset > 2 %L | refused | §6 |

Holtrop & Mennen (the whitelisted method for the JBC band) stays a
registered placeholder until its source paper arrives; JBC-band
resistance validation is therefore scheduled with it.  The digitised
C₀ band (L/Δ^(1/3) 4.88..6.41) covers the table 7-8 example and
typical merchant ships; the remaining chart curves are declared
future data-entry work, and the module refuses outside the band.

### Propulsion factors and service speed (task 3.2)

`propulsion_factors` implements the Holtrop wake/thrust-deduction
correlation as transcribed in Ship Theory vol. 2 sections 5-2/5-3
(Eqs. 5-38..5-52, visually verified against the scanned original
pages, 2026-09-21); `solve_service_speed` inverts it against the
task 3.1 effective-power curve.  Published anchor: DTMB Report 1712
(public domain) — Table 39 supplies the 600-ft-LBP ship of the
Series 60 Cb 0.80 parent (B 92.31 ft, T 36.93 ft, Δ 46,717 long tons,
propeller D 26.03 ft, LCB 2.5 %L forward) and Table 31 its measured
self-propulsion results (model 4214W, the hull OpenHull digitised in
task 2.1).

| Check | Result | Criterion |
|---|---|---|
| Factors (600-ft ship) | w 0.315, t 0.196, ηh 1.175 | physical bands |
| Implied open-water efficiency ηD_pub/(ηR·ηh), 14→17 kn | 0.666 / 0.661 / 0.650 / 0.632 — inside the open-water band, drift < 6 % | consistency vs measured propulsion |
| Speed reproduction from published SHP (ηo calibrated once at 14 kn) | 15 kn −0.03, 16 kn +0.08, 17 kn +0.32 | ±0.5 kn (§4) ✓ |
| Speed reproduction at 14 kn | −0.71 kn | asserted ≤0.75 with declaration: the digitised figure 7-3 knee region (V/√L 0.55-0.60) is the chart-reading tolerance peak |
| Power unreachable inside the Ayre band / bad ηo / bad screw | refused | §6 |

## Declared circularities and approximations

These are features of the current stage, not hidden weaknesses:

1. **Deadweight 149,920 t and η_dw = 0.82** are owner-ratified task-book
   assumptions (JBC is a virtual benchmark; NMRI publishes no deadweight).
2. **Weight coefficients** (steel/outfit cubic coefficients, machinery
   share) are calibrated to the JBC neighbourhood — the standard
   parent-ship practice, declared in the module.
3. **KM anchor**: the fitted parent hull is fitted to GM + KG, so the GM
   check is a consistency check; the non-circular geometry checks are
   the ballast condition (above) and the textbook steel-weight example.
4. **Statistical ratios** L/B = 6.0, B/T = 2.7, L/D = 11.2 are provisional
   (inside the Lin Yan Table 4-3 band for double-hull bulk carriers);
   they are replaced when the owner's design-practice literature provides
   regression values (Watson 1977 is registered, awaiting the source).
5. **Stage-1 parent hull** is an analytic fit (Cb, Cm, LCB, KM anchors);
   waterlines are geometrically similar families, the bulb overhang
   (L_WL = 285 m > L_pp) is not modelled, Cw = 0.916 is a fit product.
   Real offsets replace it in stage 2.6 without touching this code.
6. **Freeboard v0.1** assumes flush deck, standard sheer, no
   Regulation-27 reductions (the conservative side); the Cb at 0.85 Ds
   uses the design Cb (the waterline table stops at the design draft).
7. **First-order algebra, table-layer convergence.** The Lackenby
   transform neglects second-order terms (as the textbook does); the
   achieved Cb/LCB are therefore measured on the carried offsets table
   after each pass and the requested increments are corrected
   iteratively (≤ 8 passes per sub-transform, 0.8 damped). Large
   changes (|dCp| > 0.035) are split automatically into serial
   sub-transforms. Residual vs goal at convergence: ≤ 1e-4.
8. **Linear interpolation when carrying sections.** Sections are moved
   by interpolating the parent offsets at the shifted station (the
   textbook's higher-precision method); the digitised grid is 21
   equal stations over a table published at 20 + half-stations, and
   the transom-stern AP section (non-linear between waterlines) is
   under-integrated by linear interpolation — visible in the loader
   anchor margin (−0.0017 Cp) and accepted at ±0.005.
9. **Parallel-body detection** uses a 0.05 % band on the area curve
   peak (Series 60: l_pf 0.42, l_pa 0.20 of the half length); it can
   be overridden by explicit dl targets only.
10. **GZ curve approximations (task 3.4).** Sections run wall-sided
    from the top tabulated waterline to the deck (the offsets grid
    ends at the design draft; consistent with the flush-deck freeboard
    assumption of task 1.6); trim coupling is neglected (the textbook's
    own sec. 5-1 assumption); the dynamic arm is accumulated
    trapezoidally over the 10° grid.
11. **Criteria approximations (task 3.5).** TB-001 declares no earlier
    non-weathertight opening, so the 2.2.1 areas run to 30°/40°
    (flooding_angle_deg is a task-book input); free-surface arms are
    exact only for prismatic rectangular tanks (the sec. 5-4 50 %-fill
    rule); criterion areas integrate the 2.5° corrected-arm grid
    (trapezoid on any terminal partial panel).
12. **Weather criterion approximations (task 3.5b).** The TB-001
    windage area is the hull side only (Lpp × freeboard; the aft
    deckhouse is neglected — unconservative direction, task-book
    declared); the negative-heel branch of the arm curve uses the odd
    symmetry of the static stability curve; the area integrals run on
    a 1.25° trapezoidal grid (convergence-tested); Lwl falls back to
    Lpp when the task book omits it (TB-001 carries the NMRI 285 m).
13. **Ayre method approximations (task 3.1 v1).** The C₀ chart is
    hand-digitised (±4 units, anchor-checked against the table 7-8
    example) for the L/Δ^(1/3) = 4.88..6.41 curves only, and the
    V/√L band is 0.50..1.20; the standard-LCB table turns aft above
    V/√L ≈ 0.82 (stored signed); the result includes the method's
    inherent ~8 % appendage/air allowance (Eq. 7-27 divides it out
    for the bare hull); twin-screw LCB sign handling beyond the
    table-7-5 single-screw column is unvalidated (tests use single).
14. **Propulsion approximations (task 3.2).** The textbook
    transcription of the Holtrop correlation is implemented as
    printed (three declared divergences from other published
    renderings — see AGENTS.md section 5); the form factor (1+k),
    Cstern and the open-water efficiency ηo are declared inputs
    (ηo passes to task 3.3); ηR defaults to the book's no-data
    value 1.0 (Eq. 5-50); the wake/thrust factors of this
    correlation do not depend on speed, so ηD is constant along the
    speed solution; the seawater kinematic viscosity is fixed at
    1.18831e-6 m²/s (15 °C).
    **Correction (2026-09-30 read-through, round 9).** The wetted
    surface of the 5-38 auxiliary chain had been transcribed with a
    LINEAR Cm; the book prints sqrt(Cm) (vol. 2, p.59, rendered-scan
    re-check — the 2026-09-21 page pass missed the radical), agreeing
    with the 1982 paper and the independent holtrop module.  The code
    now follows the printed form; a cross-module identity test pins
    S(propulsion) = S(holtrop) for the same hull.  The DTMB 1712
    anchors barely move (this ship's Cm 0.994 → S +0.3 %): w 0.3153,
    t 0.1956, ηh 1.1749; implied ηo 14→17 kn = 0.6664/0.6614/0.6494/
    0.6324; speed reproduction from the published SHP at the 14 kn
    ηo calibration: 15 kn −0.06, 16 kn −0.01, 17 kn +0.15 (was
    −0.03/+0.08/+0.32), 14 kn −0.71 (unchanged, chart-knee
    declaration stands).  All inside the declared bands.
15. **Burrill cavitation check (task 3.3, stage 1).** The limit
    line τc(σ) is carried at the book's own four chart-read anchor
    points (tables 6-2 and 8-29; the module refuses σ outside
    0.387..0.483, i.e. the anchors ± 0.002 print precision, with
    linear extension across that band only).  The two book figures
    (6-20 / 6-22) are re-printings of the same commercial line and
    the four points blend them; the printed Eq. 6-16 relation is
    A_P = A_E*(1.067 − 0.229 P/D) — the division rendering seen in
    some transcriptions contradicts the table 6-2 arithmetic and is
    not used.  Sigma may follow either book convention (with or
    without the vapour pressure subtracted); both book examples are
    reproducible.  Extending the line to the full σ range needs a
    verified full-curve source (data-acquisition backlog).
16. **B-series open-water regression and design engine (task 3.3).**
    The open-water model is the Wageningen B-series regression of
    Bernitsas/Ray/Kinley, U-M Report No. 237 (May 1981), page-
    referenced coefficients; acceptance = the report's own figure 41
    overlay plus two independent referees (table 8-12 optimum-line
    ηo within 1.5 %; NMRI MP687 measured table, mean |dηo| < 4 %,
    declared B-vs-AU cross-family and model-scale-Rn caveats).
    Family difference is physical: at equal (J, P/D) the B series
    carries ~13 % less thrust than the AU chart readings while ηo
    agrees — the design engine balances thrust anyway.  The
    table 8-12 terminal design run with B5-50 reproduces the book
    (AU5-50) attainable speed to 0.07 kn (16.04 vs 16.11 kn,
    tolerance ±0.15); the fixed 0.50 area honestly reports a
    cavitation shortfall at this design point (required ≈ 0.62,
    consistent with the book's AU5-65 needing 0.642).  The Rn
    correction's logarithm base is stated as an assumption
    (log10); the report's own "not fully reliable at the extremes"
    caveat is inherited at the domain corners.  TB-001 itself sits
    BELOW the Ayre speed-length band at 14.5 kn (V/√L = 0.486), so
    its CLI propeller design block skips with a declared reason
    until a whitelisted effective-power source covers that band.
17. **Design-space scan (task 3.6).** The scan orchestrates only
    whitelisted methods; a candidate refused by any method is
    recorded at its refusing stage (nothing extrapolated).  The
    task 3.2 solver's eta_o sanity band (0.40-0.85) and the
    tip-clearance gate (D <= 0.75 T, declared) apply per candidate;
    the B-series search itself caps eta_o at 0.75 (the plotted
    series maximum) because the polynomial eta_o inflates towards
    the K_Q zero crossing.  The windage input of the weather
    criterion is taken from the task book unchanged across
    candidates (not rescaled with ship size).  The attainable-speed
    axis is the speed reached at a fixed reference delivered power
    (median shaft power of the feasible set) - an orchestration
    definition, stated wherever a speed is reported.  Acceptance
    run (TB-001S scenario, 16.0 kn - the 14.5 kn [NMRI] value lies
    below the Ayre speed-length band for this ship): 192 candidates
    -> 61 feasible, all passing the IS Code 2.2 criteria and the
    weather criterion; refusals: Ayre C_0 band 69, Ayre speed band
    35, propeller wake-fraction band 18, weather 9; Pareto front 8
    designs at the median reference power 41,336.0 kW.
    **Correction (2026-09-24, v1.0.4).** The numbers recorded here
    before v1.0.4 were 64 feasible / 14-design front at
    24,730.8 kW, and they were wrong: `optimize.py` converted the
    service speed as `service_kn / 0.514444`, dividing where the
    conversion multiplies, so the propulsion stage of every scan
    since task 3.6 ran at 3.78x the ship speed (V_A 25.7 m/s for a
    20 kn ship).  Every gate downstream judged that phantom vessel:
    whole bands were refused on `d_bounds_m` / `thrust_n` (the
    reviewer's 100,000 t / 20 kn grid returned 0 feasible), and
    where the search still bracketed, it designed propellers for the
    phantom speed - D 10.09-11.25 m, eta_o 0.737-0.750, shaft power
    22.5-27.3 MW on the TB-001S grid.  With `knots_to_ms` in place
    the same 192-point grid gives 61 feasible, an 8-design front at
    41,336.0 kW, D 7.74-8.42 m and eta_o 0.406-0.467, and the
    reviewer's 100,000 t / 20 kn grid goes from 0 to 100 feasible
    designs (median 59,946.3 kW).  Pinned by an independent check on
    every recorded design: the implied advance speed J*n*D must sit
    inside [0.55, 1.0] x V (`test_propeller_advance_speed_is_the_
    ship_speed`).  A window that only partly overlaps the series J
    domain is intersected and searched, never extrapolated; an empty
    intersection is refused with both bands printed.
    The attainable-speed axis is populated where the band allows
    (44 of 61 in the acceptance run after v1.0.5, Pareto front 26).
    Every design left off it carries a per-candidate note and a
    counted cause (`off_reference_axis` + `off_reference_causes` in
    the scan summary): **balance below band** (the hull already
    absorbs more than the reference power at the Ayre floor),
    **balance above band** (less even at the top), or **validity gap**
    (the crossing exists inside the band but the Ayre coverage bars
    it there).  v1.0.5: all 17 off-axis designs in the acceptance run
    are `below band`.
    **Correction (v1.0.5).**  v1.0.4 disclosed the off-axis designs
    with one sentence - "absorbs more than the reference power at the
    Ayre band floor" - which was wrong for part of the population
    and, more importantly, hid a real defect: the speed solve took
    the task book's ABSOLUTE `length_waterline_m` (285 m, the JBC's)
    while the design point's effective-power call took Ayre's own
    default (1.025*Lpp).  Candidates span Lpp 231-301 m, so the two
    calls evaluated different ships: on a 301 m candidate the PE and
    the shaft power disagreed by 8.4 %, and a hull could appear to
    absorb more than the reference at the band floor yet less at its
    own design speed - impossible for one hull - and was refused as
    unbalanceable.  One waterline rule now applies to the whole scan
    (`_candidate_lwl`: Ayre's standard, 1.025*Lpp; the task book's LWL
    keeps its declared role in the weather criterion and in the CLI
    run, where it is the ship's own value), and the identity "PE at
    the design speed / eta_D = the recorded shaft power" holds to
    1.1 % over every candidate (pinned test; it was 8.4 %).  The CLI
    run had the same class of split (PE with the standard, propeller
    factors with Lpp) and now uses one value for both: the declared
    LWL when the task book carries one, else 1.025*Lpp.
    TB-001 at its [NMRI] 14.5 kn correctly returns an empty
    feasible set with every refusal declared - no design of this
    deadweight satisfies the whitelisted method domains at that
    speed (the C_0 digitised band L/Delta^(1/3) >= 4.88 and the
    Ayre band V/sqrt(L) >= 0.50 cannot both hold).

18. **First-level seakeeping estimate (task 3.8, stage 1).** All
    formulas from Ship Theory vol. 2, Part 4, re-verified against
    rendered pages of the text-layer PDF at whitelisting time
    (2026-09-23, AGENTS.md section 5); the whitelist records the two
    declared print defects kept out of the implementation (Eq. 4-56
    coefficient slip; Eq. 4-62 missing 2*pi/sqrt(g), restored via its
    own derivation chain) and the scope boundary (the source prints
    no wave-speed-loss formula, so speed loss is out of scope).
    Seakeeping columns are reported per feasible scan candidate but
    are NOT feasibility gates; resonance avoidance stays with the
    owner.  Checks and results:

| Check | Result | Criterion |
|---|---|---|
| Book table 3-1 wave pairs, 9 rows (p.383) | lambda = 1.56 T^2 reproduces each row within 0.08 s (print coarseness; the lambda = 40 m row's 5.2 s declared as the book's own rounding) | table reproduction |
| Book resonance example (pp.383-384) | T = 10 s -> 156.0 m; T = 12.5 s -> 243.75 m (book: 156 / 244) | worked example |
| Eq.(3-49) vs Eq.(3-39)->(3-27) chain | agree to 0.13 % (0.58 = book's rounding of 2*pi/sqrt(12*g) = 0.57927) | identity |
| Roll period, 25,000-t-class hull (B 23, KG 9, GM 1.8) | 12.63 s — inside the book's cargo-ship (10,000-t class) band 8-13 s (p.391) | sanity band |
| Pitch: Eq.(4-55) vs Tamiya Eq.(4-57), restored Eq.(4-62) | 8.33 s vs 8.24 s (1.1 %) vs 8.29 s (0.5 %) | cross-formula <= 2 % |
| Effective wave slope Eq.(3-3) clamps | zg/d 0.917/1.45 enforced; K in [0.680, 1.0] | clamp |
| GM guard | GM <= 0.15 m refused (p.391 applicability) | guard |
| Encounter Eqs.(2-98)/(2-99) | head sea T_e 5.13 s < T_w 8 s < following T_e 18.2 s (V 7 m/s); V -> celerity refused | physics |
| Scan integration (TB-001S CI grid) | every feasible candidate carries roll/pitch/heave periods + two roll-resonance flags; flags are bool, never gates | wiring |
| CLI `run` | seakeeping block printed; JSON `seakeeping` section; 25,000-t example: roll 13.10 s, pitch/heave 11.1/11.0 s, all Lambda outside both bands | end-to-end |

19. **Hydrostatic curves chart (task 4.1) and BEM RAOs (task 3.8
    stage 2).** The task 4.1 chart is a pure visualization of the
    task 1.4 table (no new formulas; wiring tests assert PNG
    output); the rendered example passed an independent visual
    acceptance review after the draft-axis orientation was corrected
    to the textbook convention (draft increasing downward) — first
    render failed review on exactly that point.  The stage-2 BEM
    layer (capytaine, optional extra `openhull[seakeeping]`) is
    validated by independent-path cross-checks on a 100 m x 20 m x
    6 m Series 60 hull (KG 3 m); capytaine supplies hydrodynamics
    only, all RAO mass/stiffness matrices come from the whitelisted
    chain.  Declared: radiation-only damping (resonance AMPLITUDES
    are qualitative — no whitelisted viscous-damping source), zero
    speed, suppressed surge/sway/yaw, wall-sided deck strip at
    1.15 T, diagonal stiffness.  Checks:

| Check | Result | Criterion |
|---|---|---|
| Mesh volume vs table displacement volume (deck at waterline) | 9608.6 vs 9599.3 m3 — ratio 1.001 | panel vs Simpson integrators, <= 1.5 % |
| Long-wave heave RAO (T = 20 s, lambda/L = 6.25) | head 0.967, beam 0.999 | -> 1 at lambda >> L |
| Short-wave heave RAO (T = 4 s, lambda = 25 m) | 0.065 (head) | -> 0 at lambda << L |
| Head-sea roll excitation | max head 0.000 vs beam peak | hull symmetry |
| Roll RAO peak position | at the stage-1 period x sqrt(1.25) (Duell Jxx = 0.25 Ixx) within one period-grid step | cross-layer consistency |
| Long-wave pitch RAO | 0.010 rad/m at T = 20 s vs wave slope k = 2*pi/625 = 0.010 | ship follows wave slope |
| Print defects found and excluded (lid at waterline kills the FK integral; unit mismatch rho = 1000 default vs 1.025 chain; omega-sorted dataset vs submission order) | all fixed and pinned by tests | engineering log |
| CLI `rao` subcommand | TB-001: 1134 panels, head/beam table printed, JSON schema | end-to-end |

20. **Arrangement schematic (task 4.2) and design report (task
    4.3).** Both are DECLARATIVE deliverables: no empirical formula,
    no feedback into any calculation.  The arrangement layout comes
    from the task book's optional ``arrangement`` block or from the
    declared default bulk-carrier scheme (module docstring:
    aft peak 0-0.03 Lpp, engine room 0.03-0.095, holds 0.095-0.940
    evenly divided, fore peak 0.94-1.0, double bottom max(B/20,
    1.0 m)); the report restates the run summary verbatim.
    Checks:

| Check | Result | Criterion |
|---|---|---|
| Default scheme rules (ordering, containment, hold tiling) | peaks at the ends, holds tile 0.095-0.940 Lpp without gaps, ER above the double bottom | pinned by tests |
| Double-bottom height | max(B/20, 1.0 m) convention (2.25 m at B = 45) | declared |
| Task-book overrides | n_holds, double_bottom_top_m, full compartment table | parsing tests |
| GA chart visual review | independent review FAILED once (unlabelled narrow aft peak) -> fixed (rotated label, threshold 0.02 Lpp) -> PASS | visual gate |
| DXF export | layers GA-SIDE / GA-PLAN / GA-DB / GA-LABELS, reopens in ezdxf | task 2.4 convention |
| Report faithfulness | Lpp/Cb/DW/Delta/GM/roll periods of the summary appear verbatim; skipped blocks declared (e.g. the TB-001 propeller Ayre-band skip) | content tests |
| End-to-end | TB-001 with --report --arrangement-dxf --arrangement-chart --hydro-curve-chart writes all four artefacts and echoes the paths | wiring test |

21. **Roll damping quantification (backlog item resolved from the
    book, 2026-09-23).** The whitelisted source itself carries the
    damping chain (pp.392-394, page-verified): the table 3-6
    closure B = B20*(20/phi_A_deg)^0.32 reproduces all four printed
    rows; the large-cargo-ship table entry prints B15 = 0.0190
    (folds to B20 ~ 0.0173); preliminary estimates use
    B20 = 0.0200; the mu ranges are no-bilge-keel 0.035-0.05,
    with-bilge-keel 0.055-0.07; Eq.(3-26) completes the linear RAO
    curve.  Implementations: `extinction_coefficient`,
    `equivalent_linear_mu` (Eq. 3-59, radians declared),
    `resonant_roll_amplitude` (energy balance
    A = alpha_m0/(2 mu(A)) — REQUIRES the caller's effective wave
    slope; the amplitude is undetermined without a sea state), and
    a book-mu-calibrated equivalent viscous dissipation injected on
    the roll DOF of the BEM RAO (capytaine radiation adds on top —
    conservative).  Checks:

| Check | Result | Criterion |
|---|---|---|
| Table 3-6 closure vs printed rows | 1.248/1.096/1.000/0.878 vs 1.25/1.1/1.0/0.88 | all four rows |
| B20 fold of the large-cargo B15 = 0.0190 | 0.0173 | 0.32 power law |
| Fixed point of the energy balance | A = alpha_m0/(2 mu(A)) holds to 1e-4 relative at three sea severities | self-consistency |
| Physics of the balance | amplitude monotone in sea severity, capped (< 45 deg) by the quadratic damping | sanity |
| Eq.(3-26) at Lambda = 1 | equals Eq.(3-29) 1/(2 mu) | identity |

    Backlog dispositions recorded the same day: speed loss stays
    UNIMPLEMENTED (the in-house design textbooks discuss it
    qualitatively only — Xie 4.3.3, Lin Yan — and no page-verifiable
    Aertssen source is on hand); the Wigley public-RAO referee and
    the ShipD licence decision likewise await a verifiable source;
    the GZ paper anchor is accepted as documented (owner option 1).

22. **Kwon speed-loss estimation (backlog resolved by approved
    open-source retrieval, 2026-09-23).** Owner instruction: find
    usable sources online.  Archived and page-verified: the
    open-access transcription Cheng, C.-W. et al., J. Marine
    Science and Engineering 2025, 13(1), 42 (MDPI, CC-BY),
    section 2.2 (real 23-page PDF from mdpi-res.com after the
    main /pdf endpoint returned a bot page), and the primary
    literature Kwon, Y.J. (1981), Newcastle PhD thesis (349 pp.).
    Equations (1)/(2) and tables 2-4 transcribed verbatim (internal
    知识库/Kwon_speed_loss/SOURCE_NOTES.md); the 2008 RINA original
    is not freely available — declared.  Checks:

| Check | Result | Criterion |
|---|---|---|
| Table 3 dR rows | printed quadratics reproduced (0.65 normal at Fr 0.26 = 0.854) | verbatim transcription |
| Table 2 doubling convention | head sea C_mu = 1.0 (printed 2*C_mu = 2) | paper usage |
| Table 4 C_F forms | 0.5/0.7 linear + BN^6.5/(2.7 or 22.0)nabla^(2/3) | verbatim transcription |
| KCS cross-check (paper table 15: Kwon f_w = 0.932 at SS5) | computed f_w 0.929 | within 0.01, input ambiguity declared |
| Non-positive dR (Cb 0.85 loaded, Fr 0.14) | refused with declared message, not faked | honest-domain guard |
| dV/V1 > 100 % (BN 8 x small nabla) | refused: beyond the method's physical range | guard |
| Domain guards | Cb 0.55-0.85, Fr 0.05-0.30, BN 0-12, printed row set | guards |

    Other backlog dispositions the same day: ShipD confirmed
    MIT-licensed (github.com/noahbagz/ShipD, arXiv:2305.08279) —
    compatible with this MIT project, available for future use;
    Wigley exact-table referee remains open (capytaine wheels ship
    no test data; published Wigley RAOs are figures only — needs a
    page-verifiable table source).

23. **Draft-declaration back-solve hint (owner-approved Plan 0 of the
    R2 decision, 2026-09-24).** When a task book declares a design
    draft the weight balance cannot honour (beyond 5 cm), the run
    reports the B/T a re-solve at that draft would need, under one
    explicitly stated rule: hold the displacement volume, Cb and L/B,
    i.e. L and B both scale and B/T ∝ T^-1.5.  No statistic, guard
    threshold or balance value was touched — the R2 question (design
    draft as a hard constraint) remains open pending a reverse-anchor
    decision.

| Check | Result | Criterion |
|---|---|---|
| Identity at the current draft | required B/T = current B/T (exact) | derived: (B/T)₀·(T₀/T)^1.5 |
| T^-1.5 law vs an independent volume solve | agrees at ∇ = (L/B)·B²·T·Cb = 118,787 m³, L/B 6.0, Cb 0.86, 14.672 → 16.5 m = 2.264 | independent path |
| Verdict band = the chain's own guard band | 2.00 and 3.50 solve, 3.60 is refused by the B/T guard | endpoints inclusive, one constant source (`*_BAND`) |
| Rounding semantics (N2/N3 lesson) | raw 3.5002 → shown 3.500 → counts IN band; raw 3.5008 → 3.501 → out | verdict on the value a reader would type |
| One-shot residual (declared approximation) | re-solving with the hint ratio lands 0.3–1.3 % short of the declared draft, toward the balance draft (45,000 t probe: declared 12.5 m → 12.409 m) | measured at 10.5/11.0/12.0/12.5 m, pinned by test |
| Advised API path works | `solve_weight_balance(spec, ratios=RatioParameters(b_over_t=hint))` reproduces the ratio | the advice must not rot |
| 45,000 t / 16 kn in-band case | declared 11.6 m → no hint (0.041 m ≤ 5 cm); 12.5 m → hint 2.426 vs current 2.700, in band; 9.0 m → 3.972, above the band, declared un-extrapolable | behaviour, three states |
| Honesty of the number | report and JSON carry the rule, the one-shot limit and the "B/T is not a task-book field" action note | declared approximations |

24. **Hard design draft (`draft_is_hard`, R2-A, owner-approved
    2026-09-25).**  With the flag on, the declared draft is the
    CONSTRAINT and B/T the solved variable: bisection over the guard
    band [2.00, 3.50], one full Norman balance per trial, converged
    when the balance draft meets the declaration within 1 cm.  Rule:
    L/B and Cb held — the same rule the v1.0.3 hint declares.  The §5
    whitelist entry was amended BEFORE coding (converged variant, no
    new source); the external review's precondition (a reverse-anchor
    test) gates the merge.

| Check | Result | Criterion |
|---|---|---|
| JBC reverse anchor | DW 149,920 t / Cb 0.858 / hard 16.5 m → L 274.57 m (−1.94 %), B 45.76 m (+1.69 %), D 24.52 m (−1.9 %), T 16.5002 m, B/T 2.7734, 8 probes | anchors amended 2026-09-28 (round-7 OH-09): the solved quantities — B/T vs JBC actual 45/16.5 = 2.727 (+1.7 %, ±5 %), draft residual ±1 cm; the L deviation is dominated by the HELD L/B 6.0 vs JBC 6.222 (−3.57 % by the declared rule, not by the solver) and is reported as calibre, not error |
| Hint ↔ hard consistency | hint B/T 2.7659 vs solved 2.7734 → 0.27 % | within the declared one-shot residual |
| Convergence from both sides | 45,000 t case: declared 12.5 m → B/T 2.3984 (slimmer), declared 11.0 m → wider than 2.7; both to ±1 cm | bisection on a monotone draft(B/T) |
| Refusal, too deep | declared 20.0 m → exit 2: "even at the band floor B/T 2.00 the balance draft is 13.955 m, shallower than the declared 20.000 m" | endpoint numbers in the message |
| Refusal, too shallow | declared 7.0 m → mirrored band-top message | same |
| Default path untouched | flag absent → `draft_is_hard: false`, the new fields stay None | the 384 prior tests unchanged |
| Staged interplay | hard 12.5 m on the 45,000 t case: the chain completes, the propeller stage refuses at L/Δ^(1/3) 4.72 < 4.88 (declared C0 gap) | structured refusal, not a crash |
| Full-chain real-machine run | JBC taskbook with the flag: hard-draft line in §1 and the console, hydrostatics at 16.50 m, no mismatch warning | behaviour |

25. **C0-peak sensitivity diagnostics + honest cavitation/stdout
    contracts (product review round 6, owner-directed 2026-09-25).**
    A product review walked the full chain as a real user (100,000 t /
    20 kn / Cb 0.76) and found three P0s; all three are addressed with
    display-only diagnostics and contract fixes — no numeric result
    changed (the whitelisted formulas, guards and acceptance numbers
    are untouched; the diagnostics derive from the digitised C0 family
    itself, §5 amended before coding, commit 6a78084).

| Check | Result | Criterion |
|---|---|---|
| P0-1 phenomenon reproduced | the reviewer's ship at 15→17 kn: PE grows +9.9 %/kn vs +21 % for pure V³ (C0 rising +28 %/0.05 below the family peak); the digitised family peaks at V/√L = 0.70 on ALL six curves | reproduced from the whitelisted table |
| Peak-zone flag | the reviewer's 20 kn point (V/√L 0.699) flags in_peak_zone=True, family peak 0.70, local slope −4.8 %/0.05; a 16 kn 45,000 t run stays unflagged | data-derived zone, not hand-picked |
| Ac corridor (display only) | at 20 kn: 19 kn 799.3 / 20 kn 754.0 / 21 kn 681.9 — displayed as evidence, never used in any numeric chain | §5 declaration |
| P0-2 cavitation wording | out-of-band sigma renders as ⚠ **未校核（非通过）** with the side (low = higher risk), direction hints (lower rpm / larger AE/A0 / deeper shaft), and the full provenance note untruncated (P2-5) | no "declaratively skipped" wording left |
| P0-3 stdout contract | the quickness section appears in ALL three states: result (D/P/D/ηo/power/cavitation/sensitivity), refused (stage + one line + see --report), not requested; `--json` purity regression untouched | agent contract |
| P1-1a Kwon wording | the report no longer claims "no speed-loss formula exists"; it states Kwon is implemented/tested in the library, not yet wired into `run` (needs sea-state inputs), and all powers are calm-water | library facts |
| P1-2 refusal guidance | the refusal block points to `openhull optimize --grid-cb …` for the feasibility sweep | no more blind retries |
| Self-caught regression at the process boundary | the first v1.2.0 build printed a stray module-level line into `--json` (an edit dedent moved the trailing hint out of `_print_summary`); in-process tests stayed green because capsys starts after import — caught by the cold-install check, fixed, and pinned by a SUBPROCESS-level purity test (in-process capsys cannot see import-time prints) | the contract needs a process-boundary test |
| Regression | 405 tests green (12 new); the 393 prior numbers unchanged | no numeric drift |

26. **Backlog batch v1.3.0 — the review's P1 list cleared
    (owner-directed 2026-09-26).**  "Do what can be done now": the
    five P1 items that had no external blocker, plus the cheap P2s.
    No whitelisted formula changed (the check subcommand only
    orchestrates existing guards; the feasibility hint is the same
    declared-rule algebra class as the draft hint; the weather default
    is the JBC task book's own [ASSUMED] derivation, productised).

| Item | Check | Result | Criterion |
|---|---|---|---|
| P1-3 | `openhull check` | 8 gates in ~1 s; the reviewer's Cb 0.84 case predicts the C0 refusal at 4.8324 (their sweep measured 4.832), exit 0/1; soft-draft mismatch WARNs (reported, not fatal); --json machine-readable | predict, not guess |
| P1-5 | `weather_criterion: default` | run and optimize both resolve it: area = Lpp x freeboard, lever = D/2, bilge keels 0, LWL 1.025 x Lpp — all [ASSUMED], the non-conservative direction declared in report section 4 | JBC task book's own derivation, productised |
| P1-1b | Kwon wired into `run` | `seakeeping.speed_loss: {beaufort 6, head}` on Cb 0.76 @ 18 kn: dV/V1 1.71 %, V2/V1 0.9829, 0.31 kn — matches the library values; the domain is honest (Cb 0.80 @ Fr 0.19 refuses: page-verified applicability, not a defect); absent block declares calm-water powers | library cross-check |
| P1-2 | feasibility hint | the ayre refusal carries the nearest feasible Cb under the declared held-(Delta, ratios) rule (0.78 < bound <= 0.82, the reviewer measured the boundary between 0.80 and 0.82) + the optimize pointer | declared-rule hint, like the draft hint |
| P2-1 | `--json PATH` / `--csv PATH` | files written, combinable; bare flags keep stdout; two bare flags refuse with guidance; --json purity re-pinned at the process boundary | agent contract |
| P2-2 | `--csv-step` | default 0.1 T = 10 rows aligned with the curves chart; 0.25 restores the historical 4 | export granularity |
| P2-3 | roll-period calibre footnote | report section 6 states both periods' formulas (IS Code 2.3 simple form vs the book's Eqs 3-27/3-49) | the two numbers are a calibre difference, not a bug |
| P2-4 | `seakeeping.wave_periods` | custom seas replace the reference seas, labels say "task-book sea" | configurability |
| Regression | 419 tests green (14 new); prior acceptance numbers unchanged | no numeric drift |

27. **Review round 5 (external verifier, 2026-09-26): v1.1.0-v1.3.0
    audit cleared, two code-level findings fixed (v1.3.1).**  The
    round-5 report reproduced every quantitative claim across three
    releases (hard-draft anchors bit-for-bit, check preflight, the
    feasibility-hint bound 0.816 vs an independently measured
    boundary at about 0.815, Kwon 1.71 %, weather default
    A = 980 m2, baseline zero-drift, 419 tests) and found one stale
    agent-facing paragraph plus minor items; all dispositioned here.

| Item | Fix | Check |
|---|---|---|
| 6.1 stale SKILL paragraph | the FAQ Kwon entry still said "not yet wired into run" (v1.2.0-era residue contradicting the same file's v1.3.0 section) - rewritten to the wired contract | agents copy SKILL verbatim; the contradiction is gone |
| 6.2 chart degrade | a broken plotting stack surfaced as a bare third-party traceback from `optimize`; the chart call now degrades to a declared note (console line + `outputs.chart_note`), CSV/JSON products complete | 3 new tests incl. an end-to-end optimize with a monkeypatched-broken chart |
| 6.2 install recovery | the SKILL install section documents the uv `os error 5` malformed-tool recovery (uninstall + purge %APPDATA%\uv\tools\openhull) and the slow-network tarball fallback | agent-facing docs |
| 6.3 JSON paths | SKILL gains a machine-readable-field path quickref (`propeller_design.resistance_sensitivity`, `cavitation_unchecked`, `feasibility_hint`, `seakeeping.speed_loss`) | docs |
| 6.4 console sign | the Kwon line printed "-1.7%" (reads like a gain at a glance); now "1.7% slower" | no bare negative sign remains |
| 6.5 changelog 4.8324 | recorded: the verifier measured 4.8322 on the 45,000 t book (the changelog quoted the 100,000 t book); a noted difference, no change | provenance note |
| README rework | README.md becomes the Chinese full version (the repo default view), English moves to README.en.md, README_zh.md is a redirect stub, the eight minor-language stubs are retired (stale translations are worse than none) | repo facade |
| Regression | 423 tests green (4 new); prior acceptance numbers unchanged | no numeric drift |

28. **Round-6 (the v1.3.1 verifier, 2026-09-27): the same defect class
    on `run`'s chart options, guarded everywhere (v1.3.2).**  The
    controlled cycler-hiding experiment confirmed the round-5
    optimize guard; the same probe then showed `run`'s
    `--hydro-curve-chart` / `--arrangement-chart` unguarded (exit 1,
    a bare 17-line traceback, and with `--report` the PRIMARY
    deliverable lost to an optional chart), plus a residual phantom
    path in the degraded scan's outputs.

| Item | Fix | Check |
|---|---|---|
| run chart guards | the round-5 guard generalised to `_write_optional_chart`, shared by all three chart call sites (hydro curves, arrangement, scan); degrade = declared note on stderr with the remedy + `chart_notes` in the JSON; the report and data products complete | 5 new tests: both run paths degrade with the report surviving; JSON carries notes, not phantom paths |
| outputs invariant restored | a degraded scan lists NO phantom chart path: `outputs.chart` present only when written - the v1.0.1 "every listed file is really on disk" invariant now holds on BOTH the healthy and the degraded path | degraded optimize: no `chart` key, PNG absent, `chart_note` present |
| remedy in the note | the degrade message carries the reinstall remedy (uninstall, purge %APPDATA%\uv\tools\openhull, reinstall), pointing at the SKILL install notes | self-service without reading docs |
| check dep hint | missing matplotlib/cycler surfaces as ONE console line via `importlib.util.find_spec` existence probes (milliseconds, not an import); the exit-code contract stays about the design; the hint never enters `--json` | console hint with exit 0; `--json` payload clean |
| Regression | 428 tests green (5 new); the 45,000 t default path and the TB-001S scan unchanged (verifier re-measured both bit-for-bit) | no numeric drift |

29. **Round-7 (independent end-to-end QA on v1.3.2, owner-commissioned
    2026-09-28): the task-book input contract (v1.4.0).**  The QA run
    (45 probe batteries, source read-through, per-issue repro) found
    the numeric chain healthy and reproducible, with the entire gap
    on the input layer: 16 issues (2 P0 crash, 6 P1 silent wrong
    conclusions, 8 P2).  All 16 dispositioned; 11 of 16 shared one
    root cause - the missing input contract - now implemented.

| ID | Disposition | Check |
|---|---|---|
| OH-01 P0 | `weather_summary`/`weather_assumed` were initialised INSIDE the `if kg_m` block while the summary referenced them unconditionally: `run` without kg_m crashed (UnboundLocalError) although SKILL documents kg_m as optional. Initialisations moved out; the documented optional behaviour restored | contract test: run without kg_m -> rc 0, gz/weather/seakeeping None |
| OH-02 P0 | 8 uncaught-input paths (bare traceback + exit 1, colliding with check's refusal=1). Fixed at three layers: `_load_taskbook` wraps decode/parse (UTF-8 hint incl. GBK guidance, YAML line numbers, directory-path check); a `_number` helper converts every task-book number into a field-named refusal; `main()` gains a catch-all -> exit 2 (OPENHULL_DEBUG re-raises), exit 1 stays check-exclusive; `_parse_axis` validates lo:hi:steps | contract tests: type error / GBK / grid axis each refuse readably, no Traceback |
| OH-03 P1 | unknown/misspelled keys were silently ignored (a typo'd `defualt` removed the whole weather section while the report claimed "not declared"). Key whitelist over the union of consumed keys (TB-001 full form), refusal + case-folded did-you-mean | contract test: `KG_m` refused suggesting `kg_m`. The whitelist flagged a stray key our OWN v1.3.0 weather test had been carrying: vindication on our suite |
| OH-04 P1 | `block.get(key) or 1.0` replaced a declared 0 efficiency with 1.0 (most optimistic), under-reporting shaft power ~2 %. `_efficiency` helper: explicit None + range (0, 1.2] | contract test: shaft_efficiency 0 refused, not silently 1.0 |
| OH-05 P1 | missing shaft_immersion_m silenced the whole cavitation section (null with no note) - bypassing the project's own unchecked-is-not-passed contract. Now `cavitation_skipped.reason` in JSON + a report line (console already declared it) | contract test: skipped declaration present |
| OH-06 P1 | every chart-write failure was diagnosed as "reinstall the tool" (a bad output dir said the same as a broken matplotlib). Typed notes: dependency gap / OSError with the OS text / unexpected + issue hint; parent dirs auto-created upstream | chart-guard tests updated |
| OH-07 P1 | optimize/rao ignored draft_is_hard (the scan evaluated a DIFFERENT ship than run/check on the same book). One resolver (`_resolve_balance`) for run/check/rao; optimize REFUSES hard mode with guidance (B/T is the scan axis; hard-draft scan mode = backlog) | contract test: optimize + draft_is_hard -> rc 2 naming the field |
| OH-08 P1 | the flagship example is a REAL-domain refusal at 14.5 kn, presented as a success demo. README (zh+en) and demo README now state the refusal up front and point at the minimal taskbook for the full chain; JBC-band resistance validation stays scheduled with Holtrop (registered backlog, VALIDATION §3.1) | docs |
| OH-09 P2 | check's L/B and L/D gates are constants of the statistical algebra (B/T too in soft mode); the draft_is_hard anchor's ±5 % L criterion passed by construction (held L/B 6.0 vs JBC 6.222). Gates now labelled `PASS (statistical constant)` (JSON `by_construction`); AGENTS.md + VALIDATION 24 anchor the SOLVED quantities (B/T vs JBC 45/16.5 = 2.727, +1.7 %; draft ±1 cm) and declare the L calibre | check output shows the label; charter amended |
| OH-10 P2 | demo_outputs were 15 versions stale and the committed CSV carried 4 stray stderr lines. All artifacts regenerated from the current chain; demo README corrected (0.1 T / 10 rows, refusal framing); demo CSV pinned by a drift test | regenerated files in repo |
| OH-11 P2 | the scan histogram named one stage twice (`ayre` vs `ayre_band`). Unified to `ayre`; the distinction lives in the reason/field breakdown | test_optimize updated |
| OH-12 P2 | README said 423 tests / pinned @v1.3.1 / CITATION 1.3.1 / "25万吨" - the v1.3.2 release missed the README+CITATION sync, and the example is a 149,920 t (approx 150k deadweight) Capesize, not 250k. Fixed; demo CSV drift test guards future README-number drift at the artifact layer | this release |
| OH-13 P2 | report section 5 now carries the shaft power PS line (the main-engine selection input) next to the delivered power; `--json PATH` stdout silence is kept (contract) - stderr confirmations were already emitted | report line |
| OH-14 P2 | ship_type took no part in any computation (a tanker task book produced a bulk design under a wrong label). Refused until per-type statistics are calibrated; SKILL template and FAQ updated | contract test |
| OH-15 P2 | duplicate YAML keys silently took the last value (a stale line once worth +18.8 % shaft power). Strict loader refuses duplicates with the line number | contract test |
| OH-16 P2 | 11 contract tests in `tests/test_taskbook_contract.py`, one per refusal above, asserting rc + field name + no traceback | this file is the check |
| Regression | 440 tests green (12 new); the numeric chain untouched - every prior acceptance number stands (the QA run re-verified byte-identical reproducibility) | no numeric drift |

30. **Holtrop–Mennen (1982) effective-power method — second
    resistance method, library-validated (round-8 backlog, 2026-09-28).**
    The registered placeholder from §3.1 is discharged: the source
    paper was located, archived and PAGE-VERIFIED (rendered images,
    pp. 166–170; the 1984 re-analysis is archived with it and
    registered, not implemented), the §5 whitelist was amended BEFORE
    coding (f61578d), and the method is implemented as a library
    module (`openhull.holtrop`) for validation and cross-check —
    deliberately NOT wired into the default chain yet (chain wiring +
    guard rework is the follow-up proposal, the Kwon
    library-first pattern).

| Check | Result | Criterion |
|---|---|---|
| Source | Holtrop & Mennen (1982), ISP vol. 29, pp. 166–170 — full scan archived (University of Trieste public course mirror; publisher metadata IOS Press cross-checked) | §5 page-verification rule |
| Worked-example anchor (the paper's own §5 numerical example) | S 7381.45 m², 1+k₁ 1.156, L_R 81.385 m, c₁₂ 0.5102, C_F 0.001390, i_E 12.08°, c₁ 1.398, c₂ 0.7595, c₃ 0.02119, c₅ 0.9592, m₁ −2.1274, m₂ −0.17087, λ 0.6513, C_A 0.000352, R_F 869.63 kN, R_APP 8.83 kN, R_W 557.11 kN, R_B 0.049 kN, R_A 221.98 kN, R_total 1793.26 kN, P_E 23063 kW — every printed quantity reproduced, ZERO declared defects | published worked example (the charter's anchor class) |
| Transcription-fidelity pins | form factor takes (1−Cp+0.0225·lcb) while i_E takes (1−Cp−0.0225·lcb) — the sign genuinely differs between the two printed formulae; pinned by tests | both verified against the example |
| Cp calibre | the paper's Cp 0.5833 sits between ∇/(Lpp·B·T) 0.5859 and ∇/(L·B·T) 0.5716 — the module accepts DECLARED Cp/C_B (the anchor feeds the printed values) or derives on LWL with the calibre stated | declared, not hidden |
| lcb datum | Holtrop lcb is % of LWL, datum ½L — conversion from %-Lpp validated by the example (−2.02 %Lpp → −0.75 %L) | example table |
| JBC-band external anchor | OPEN, declared: the Tokyo 2015 EFD tables live in workshop proceedings not secured at implementation time; the ±10–15 % planned-acceptance row (AGENTS planned table) lands when they are | honest deferral, not a silent drop |
| Regression | 446 tests green (6 new); the default chain untouched — every prior number stands | no numeric drift |

31. **Hard-draft scan mode (round-8 backlog, 2026-09-28).**  The R2-A
    decision extended to `optimize`: with `draft_is_hard: true` the
    scan sweeps L/B x Cb and SOLVES B/T per candidate (the v1.1.0
    bisection, +-1 cm), so the scan's feasibility map and the
    single-point `run` live in the same design space.  The B/T grid
    axis must be pinned to one value (it is not scanned - explicit
    refusal otherwise); the solved B/T lands in every row and the
    scan summary declares the mode.

| Check | Result | Criterion |
|---|---|---|
| Solved draft | 45,000 t / Cb 0.80 / declared 11.6 m, 1x1x1 grid: the feasible row's draft 11.603 m (bisection tolerance) and its B/T matches the single-design hard solve exactly | the scan's ship floats at the DECLARED draft |
| Unreachable candidates | declared 15.5 m at Cb 0.72: the candidate is recorded with stage `hard_draft` and the endpoint reason (zero-extrapolation promise extends to the scan) | declared refusal, not a crash |
| Axis contract | a multi-valued B/T axis with draft_is_hard refuses with guidance (B/T is solved, not scanned) | declared contract |
| Regression | 448 tests green (2 new); the soft scan path untouched - the TB-001S and 100k scan numbers stand | no numeric drift |

32. **Wigley zero-speed RAO external anchor (backlog web-search
    clearance, 2026-09-28).**  The roadmap 3.8 acceptance line
    "Wigley or Series 60 public RAO comparison" closes with
    Journee (1992), TU Delft report 0909 (archived via the Internet
    Archive; constitution section 5 amendment "External anchor
    data: Wigley parabolic hulls").  Geometry = the report's own
    analytic form (data-verified domain xi in [-1, 1]; the printed
    [-0.5, 0.5] is a declared print defect), spot-checked
    digit-by-digit against the report's Table 1-III offsets; the
    form's analytic grad = 0.078000 m3 equals the report's
    tabulated 0.0780 exactly.  The BEM comparison reproduces the
    rig's degrees of freedom (heave + pitch free, roll restrained,
    surge restrained).  Gates sit at lambda/L >= 1.0, the region
    where the source's own SEAWAY / 3-D-panel curves track the
    data (Fig. 16-III); the measured short-wave points scatter
    about the theory band in the source's own figures too.

| Check | Result | Criterion |
|---|---|---|
| Geometry grad (table Simpson) vs report | 0.07786 vs 0.0780 m3 (III), 0.15573 vs 0.1560 (IV) — ratio -0.18 % | keel-sliver + interpolation, <= 0.5 % |
| Cm from table | 0.6655 vs 0.6667 | section integration, <= 0.5 % |
| Heave amplitudes, lambda/L 1.0-2.0 (III + IV) | III: -3 % .. +8 %; IV: -6 % .. +10 % | <= 15 % vs Tables 10-III/IV |
| Pitch theta" amplitudes, lambda/L 1.0-2.0 | III: -14 % .. -9 %; IV: -22 % .. -2 % | <= 25 % |
| Heave-pitch phase difference | III 13-31 deg, IV 9-44 deg — the 44 deg max sits at lambda/L = 1.0 just above the heave-resonance band where the measured phase turns over rapidly (<= 22 deg at lambda/L >= 1.25) | <= 45 deg, convention-independent |
| Heave minimum near lambda/L = 0.75 | BEM reproduces the dip (III 0.093, IV 0.152) below 0.6 x the lambda/L = 1.0 value | qualitative dip gate |
| Short-wave amplitudes (lambda/L < 1.0) | recorded as printed diagnostics, NOT gated: measured points 0.04-0.27 scatter around the theory band exactly as in the source's own validation figures (Fig. 16-III) | honest scope declaration |
| Regression | 448 + 3 tests green; shipped chain and CLI untouched | no numeric drift |

33. **Read-through round 9 (2026-09-30, full-source review): two
    transcription-fidelity dispositions and four robustness fixes.**
    An independent full read-through of all 23 modules re-verified
    the guard/whitelist discipline and found six issues, all
    dispositioned here.  No acceptance anchor moved outside its
    declared band.

| ID | Disposition | Check |
|---|---|---|
| R9-1 (A) | wetted-surface S of the 5-38 auxiliary chain carried a linear Cm; the book prints sqrt(Cm) (vol. 2, p.59, rendered-scan re-check) — a transcription slip, code corrected to the printed form; AGENTS §5 correction note; cross-module identity test S(propulsion) = S(holtrop) (the holtrop side is anchored to the 1982 paper's own worked example) | test_wetted_surface_matches_holtrop_module; DTMB anchors re-measured inside their bands (item 14 correction note); the TB-001S 192-point acceptance scan re-run: 61 feasible / Pareto 26 / refusal histogram 69-35-18-9 / off-axis 17 ALL unchanged, median reference power 41,336.0 → 41,334.1 kW (−0.005 %) |
| R9-2 (A) | Ayre table 7-7(a) row 0.60, column 1.2 = 1.0: the BOOK prints 1.0 (vol. 1, p.305, rendered-scan re-check) where the 0.50–0.58 plateau rows print 1.6 — a suspected misprint in the source, kept as printed per the charter; declaration added at the table and in AGENTS §5 | transcription-fidelity pin freezes the printed cell (test_table_7_7a_printed_cell_is_frozen) |
| R9-3 (B) | the optimum-propeller engines' fallback unpacked a bare eta_o float when the converged midpoint is infeasible (a low-probability TypeError crash); now falls back to the best feasible candidate tuple (scan + golden probes); the dead retry line removed | single-point-series stubs force the fallback in BOTH engines (2 tests) |
| R9-4 (B) | the optimize task-book parsing bypassed the input contract (raw int()/float(), `rpm or 127.0` — the OH-04 falsy-0 pattern on the scan path); now _number everywhere, integral blades, rpm ≤ 0 refused | 2 contract tests: bad blades readably refused, zero rpm refused not defaulted |
| R9-5 (B) | the propeller diameter-retry loop existed twice (CLI run / scan) — the two-calibres class that produced the v1.0.4/1.0.5 scan defects; extracted to `propeller.design_propeller_with_diameter_retry`, both call sites rewired (the waterline calibres stay at the callers: run's declared-LWL rule, scan's 1.025·Lpp per candidate) | scan acceptance suites re-run green (test_optimize / test_hard_scan / test_product_review_round6) |
| R9-6 (B) | documentation drift: the cli.py docstring claimed "no file writes" while --report/--json/--csv write files; README (zh+en) install tag pinned @v1.4.0 with 440 tests and a 1.4.0 citation — synced to v1.6.0 / 451 | grep clean; no numeric change |
| Regression | full suite green; the committed demo CSV (hydrostatics table) is untouched by R9-1 — the byte-for-byte drift pin passes unchanged | pytest |

34. **Round-9b (2026-09-30, same day): the C-level batch — static gate,
    dedup, and the task-1.6 freeboard wiring.**  All behaviour-
    preserving except where stated; full suite green and the committed
    demo CSV byte-pin untouched.

| Item | Disposition | Check |
|---|---|---|
| Static-check gate | `[tool.ruff]` (E/F/W/B; E501 long-table lines and B905 zip-strict recorded as policy) + pytest marker registration; the first pass surfaced 89 findings, ALL dispositioned — including one F821 forward-reference in the new shared propeller helper (real slip, caught by the gate on its first run), BEM-layer dead DOF-`order` list replaced by an explicit Heave/Roll/Pitch guard, blind `pytest.raises(Exception)` tightened | `uvx ruff check src tests` clean; suite green after fixes |
| propeller engine dedup | the scan+golden-section skeleton (with the round-9 candidate-tuple fallback) extracted to `_max_eta_over_j`; both optimum engines are now thin adapters | propeller suites green incl. the two single-point fallback stubs |
| stability dedup | the three even-keel draft bisections (GZ curve / intact criteria / weather criterion) extracted to `_even_keel_draft_of`, step-identical | gz/criteria/weather suites green (59) |
| geometry dedup | the three DTMB Table-7 CSV loaders share `_read_dtmb_table` + `_station_xi`; the row-raggedness refusal text preserved | loader/drawing/DXF/linesplan suites green (77) |
| B007 lesson | renaming a loop variable that is consumed AFTER the loop (`passes_total += passes`) broke 4 chain tests — the noqa now carries the justification comment; recorded so the next lint batch checks post-loop use | the 4 tests re-run green; suite green |
| freeboard wiring (task 1.6) | `run` computes the type-B summer minimum on the BALANCE dims (one-design-draft rule) → summary JSON `freeboard` (declared `skipped` outside 24–365 m), console block, report §1 entry with the calibre note; scan untouched (declarative check, not a gate) | TB-001 run: F0 4,295.75 (Table 3-9 at the balance 271.63 m), minimum 6,393.5 mm, actual 7,485.5 mm, PASS margin 1,092.0 mm — identities pinned; the module anchor row (280/25/16.5 → 6,555.8 mm, margin 1,944.2 mm) re-pinned; 2 new tests |

## v1.7.0 — MCP server surface

| Item | Disposition | Check |
|---|---|---|
| MCP server (`openhull[mcp]`, optional extra) | stdio server in `src/openhull/mcp_server.py`; every tool shells out to `python -m openhull.cli` in a child process and returns the CLI's JSON stdout contract verbatim — no numerics touched, SDK imported lazily (module import pulls nothing MCP) | subprocess test asserts the SDK is absent from `sys.modules` after import; the exact spawn command pinned cross-process |
| Tools | `openhull_version` / `openhull_check` / `openhull_run` / `openhull_optimize` / `openhull_rao` (explicit wire names, `openhull_` prefix) + resource `openhull://taskbook-template` (byte-identical to the JBC example — anti-drift pin) | FastMCP wiring tests (list_tools / list_resources / call_tool roundtrip), skip cleanly without the extra |
| Refusal discipline carried over | predicted-refusal preflights keep `ok=true` with `refusal_predicted`; validation-level refusals (e.g. 40 kn on a full-form hull → "refusing instead of extrapolating", exit 2) surface as `ok=false` with the reason in `stderr_tail`, never a bare traceback | dedicated tests on both paths |
| Windows stdio deadlock found & fixed | inside an MCP stdio server, a child process inheriting the transport's stdin pipe deadlocks on Windows (minimal-repro variant matrix: baseline / close_fds / no_window all TIMEOUT; `stdin=DEVNULL` is the single unlocking variable). Every `_run_cli`/`_cli_version` spawn now passes `stdin=subprocess.DEVNULL` — the CLI never reads stdin, so detaching costs nothing | end-to-end test: a real MCP stdio client drives the real server process and the tool's CLI probe must answer (before the fix the probe hit its 30 s timeout) |
| Regression | full suite 473 passed (459 + 14 new), ruff clean | `pytest` 7m22s; `uvx ruff check src tests` |

## v1.8.0 — selectable parent hulls

| Item | Disposition | Check |
|---|---|---|
| Registry (`hull_form.parent`) | `PARENT_HULL_ALGORITHMS` in geometry.py: `series60_digitised` (default, byte-identical chain) + `jbc_analytic` (§5-declared construction). Unknown ids refuse naming the registry; the analytic parent refuses without a pinned Cb | registry/refusal unit tests |
| Analytic-parent anchors | Cb 0.8579–0.8581 vs 0.8580; LCB 2.5462 vs +2.5475 %Lpp; KM 18.574 m vs 18.59 m (k-fit path) — all inside the §4 gates | unit + chain tests |
| Chain on TB-001J (`examples/taskbook_bulk_carrier_jbcparent.yaml`) | design-draft volume 176,933.9 m³ vs the NMRI 178,369.9 (−0.80 %, ±1 % gate); Cb +0.0001; `parent_hull.defaults_applied` empty (task book pins Cm/LCB and carries KG+GM) | `tests/test_parent_hull.py` chain fixture |
| Default-path identity | TB-001 unchanged: `parent_hull.algorithm == series60_digitised`, no defaults; the rest of the suite (473 tests) green on the same commit | full suite |
| Scan path | `design_space_scan(..., parent_hull=..., parent_form=...)` threaded through `_evaluate_point`; small-grid jbc scan feasible | scan integration test |
| Regression | full suite 485 passed (473 + 12 new), ruff clean | `pytest`; `uvx ruff check src tests` |

## v1.10.0 — lines-plan surface skin

| Item | Disposition | Check |
|---|---|---|
| §5 entry (2026-10-05) | geomdl (MIT, >=5) as a CORE dependency under the capytaine/ezdxf precedent — geometry only, replaces no whitelisted formula; the classical plane-curve curvature κ = \|y''\|/(1+y'²)^{3/2} declared in the same entry as a diagnostic; the NURBS-Book hand-transcription route deferred until the book is legally obtained | AGENTS.md §5 |
| Anchor (a) knot reproduction | the bicubic interpolating skin returns every tabulated offset: max error 5.0e-14 m on the packaged Series 60 parent (gate 1e-6·B/2); a fit that moves the table is refused | test_surface.py exact-equality test |
| Anchor (b) hydrostatics round-trip | dense re-cut does not change the ship: x2 grid 41x53 — ∇ +0.0024 %, Cb +0.0024 %, LCB +0.0038 %Lpp, KM +0.017 %; x4 grid 81x105 — ∇ +0.015 % (gates: ∇ 0.5 %, Cb 0.005, LCB 0.05 %Lpp, KM 1 %) | test_surface.py round-trip test (x2 and x4) |
| Anchor (c) physical re-sampling | geomdl parameterises non-uniformly (grid knots NOT at uniform parameters, probe 2026-10-05) but x depends only on u and z only on v (3.6e-15 spread) — bisection on the surface's own coordinates, non-monotone spans refused | probe + parameterisation guard tests |
| Simpson parity & bounds | odd grid counts in, odd out (intervals doubled/quadrupled); negative cubic undershoots at zero rows clipped to [0, B/2] (declared; measured min 0.0 on the parent) | grid shape/parity test |
| Curvature diagnostics | per-waterline κ and inflection counts; dead keel rows skipped; an injected ±0.45 m zig-zag on the DWL row raises κ >2x and inflections +5 over clean | curvature tests |
| Drawing integration | dense tables feed `draw_lines_plan`/`save_lines_plan_dxf` unchanged via `raw_offsets_for_drawing` (fractions key); waterline labels thinned to <=9 and fanned at the bow ends — visual-judge verified (labels separated, no stacking) | drawing-chain test + visual check of examples/lines_plan_series60_dense.png |
| Regression | full suite 505 passed (496 + 9 new), ruff clean | `pytest`; `uvx ruff check src tests` |

## v1.9.0 — selectable resistance method

| Item | Disposition | Check |
|---|---|---|
| Registry (`performance.resistance_method`) | `RESISTANCE_ALGORITHMS` in resistance.py: `ayre` (default, byte-identical chain) + `holtrop_mennen` (implemented=True, the v1.5.0 page-verified module wired behind `chain_effective_power`). Unknown ids refuse naming the registry | registry/refusal unit tests |
| Dispatcher identities | ayre path == the pre-1.9 `ayre_effective_power(...).pe_bare_kw` verbatim; holtrop path == `holtrop_mennen_power(...).pe_kw` verbatim (same ONE-waterline LWL, displacement converted on 1.025 t/m³) | exact-equality unit tests |
| Applicability guard | Fr > 0.55 on LWL refused with the registered band and citation (registry applicability data, §5 unchanged — no new formulas) | small-craft Fr ~0.90 refusal test |
| Declared defaults | zero appendage / transom / bulb / c_stern / Cb-on-LWL each listed in `propeller_design.resistance.defaults_applied` (5 notes), never silent — the v1.8.0 discipline | defaults test |
| Chain on TB-001H (`examples/taskbook_bulk_carrier_holtrop.yaml`) | P_E 11,103.0 kW at 14.5 kn, Fr 0.1411 (inside the band), 1+k₁ 1.4359, S 19,235.8 m²; propeller designed from the holtrop P_E; `resistance_sensitivity` declares the Ayre-only skip; full chain (stability/freeboard/seakeeping/report) unaffected | `tests/test_holtrop_chain.py` chain fixture |
| Default-path refusal shape | TB-001 at 14.5 kn still refuses with `stage == "ayre"` (the JBC service speed sits below the speed-length band — the declared demo refusal, unchanged); no resistance block on the skipped path | refusal-shape test |
| Ayre success path | the lighter in-band task book pins `resistance.method == ayre`, empty defaults, C0-family diagnostics + Admiralty corridor present | success-path test |
| Scan honesty | a holtrop_mennen task book sent to `optimize` refuses (exit 2) naming `performance.resistance_method` and the scan's Ayre-specific internals — no silent method mixing | scan refusal test |
| Regression | full suite 496 passed (485 + 11 new), ruff clean | `pytest`; `uvx ruff check src tests` |

## Reproducing

```bash
uv run pytest                        # 505 tests (optional-extra tests skip when the extra is absent)
uv run openhull run examples/taskbook_bulk_carrier.yaml --csv > table.csv
```

