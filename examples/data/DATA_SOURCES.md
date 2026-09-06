# Data Sources — Benchmark Ships

> OpenHull validates every computed quantity against published benchmark
> data. Two public benchmark ships serve as validation targets.

## Primary validation ship — JBC (Japan Bulk Carrier)

Capesize bulk carrier with stern duct, published by Japan's NMRI as the
standard benchmark for the Tokyo 2015 CFD workshop.

| Item | Value (full load condition) |
|---|---|
| Lpp | 280.000 m |
| Draft (design) | 16.500 m |
| Displacement volume (hull) | 178,369.9 m³ |
| Block coefficient ∇/(Lpp·BWL·TM) | 0.8580 |
| LCB | 2.5475 % Lpp (fwd+) |
| Service speed | 14.5 kn (Fn = 0.142) |
| Ballast condition | Cb 0.8216, Fn 0.152 |

**Files & links**

- Hull geometry (IGES): <https://t2015.nmri.go.jp/file/Geometry_IGES_files/jbc/JBC_IGES.zip>
- Rudder geometry: <https://t2015.nmri.go.jp/file/Geometry_IGES_files/jbc/jbc-rudder.igs>
- Model propeller MP687 particulars (AU 5-blade, full radial distributions):
  <https://t2015.nmri.go.jp/file/Geometry_IGES_files/jbc/MP687_particulars.zip>
- Conditions & conditions table: <https://t2015.nmri.go.jp/jbc_gc.html>
- NMRI JBC database (reports): <https://www.nmri.go.jp/en/study/intellectual/db/jbc/>

**Validation anchors used by OpenHull tests**

- Hull displacement volume at design draft: 178,369.9 m³ (tolerance ±1 %)
- Cb at design draft: 0.8580 (tolerance ±0.005)
- Tank tests (resistance / self-propulsion) at NMRI, SRC and Osaka University
  provide published reference curves for Stage-3 validation.

> Redistribution note: vendor files (IGES/propeller data) are stored locally
> only (`vendor/` is git-ignored). The repository carries download links and
> extracted parameters, not the vendor data itself.

## Secondary validation ship — Series 60, Cb = 0.80

Classic systematic series parent form (Todd & Frick, DTMB Report 1712,
"Series 60 — Methodical Experiments with Models of Single-Screw Merchant
Ships"). Station-by-station offsets are published in the report and used as
the mother hull for Stage-2 lines-plan generation.

- Report record: <https://trid.trb.org/View/394439>
- Offsets availability: DTMB 1712 (public report; copies commonly accessible
  via university libraries and technical archives)
- Role: mother hull for Lackenby transformation (Stage 2) and second
  validation ship for the v1.0 release gate
