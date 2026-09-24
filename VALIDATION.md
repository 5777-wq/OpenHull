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
    -> 64 feasible, all passing the IS Code 2.2 criteria and the
    weather criterion; refusals: Ayre C_0 band 68, Ayre speed band
    35, propeller envelope 14, weather 9, hydrostatics 2; Pareto
    front 14 designs at the median reference power 24,730.8 kW.
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

## Reproducing

```bash
uv run pytest                        # 375 tests
uv run openhull run examples/taskbook_bulk_carrier.yaml --csv > table.csv
```

