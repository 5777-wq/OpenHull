# Validation

> OpenHull treats validation as the spine of the project: every computed
> quantity is asserted against a published benchmark or an owner-ratified
> anchor, and every approximation is declared next to its number.
> Benchmarks and data sources: [`examples/data/DATA_SOURCES.md`](examples/data/DATA_SOURCES.md).
> Binding conventions: [`AGENTS.md`](AGENTS.md) (tolerances in section 4).

Status: **stage 1 (dimensions + hydrostatics core) complete**, 113 tests
green. `openhull run` reproduces the chain end to end.

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

## Reproducing

```bash
uv run pytest                        # 138 tests
uv run openhull run examples/taskbook_bulk_carrier.yaml --csv > table.csv
```

