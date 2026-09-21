# Validation

> OpenHull treats validation as the spine of the project: every computed
> quantity is asserted against a published benchmark or an owner-ratified
> anchor, and every approximation is declared next to its number.
> Benchmarks and data sources: [`examples/data/DATA_SOURCES.md`](examples/data/DATA_SOURCES.md).
> Binding conventions: [`AGENTS.md`](AGENTS.md) (tolerances in section 4).

Status: **stages 1–2 complete** (dimensions + hydrostatics core +
parametric hull generation on real offsets); stage 3 started with the
static stability curve (task 3.4) and the IS Code general criteria
(task 3.5). 208 tests green.
`openhull run` reproduces the chain end to end — dimensions,
hydrostatics, the large-angle GZ curve, and the stability criteria
verdict (with `requirements.kg_m` in the task book).

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

The severe wind and rolling criterion (IS Code 2.3: 504 Pa wind
pressure, levers l_w1/l_w2, the roll-angle formula and its X1/X2/S
coefficient tables) is **not yet implemented** — plan task 3.5b must
transcribe and visually verify those tables first, and the TB-001
windage area is undefined until then.

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

## Reproducing

```bash
uv run pytest                        # 208 tests
uv run openhull run examples/taskbook_bulk_carrier.yaml --csv > table.csv
```

