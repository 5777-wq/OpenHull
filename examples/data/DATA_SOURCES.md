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

## Secondary validation ship — Series 60, total prismatic coefficient = 0.805

Classic systematic series parent form — Model 4214W-B4 — from
F.H. Todd, "Series 60 — Methodical Experiments with Models of
Single-Screw Merchant Ships", DTMB Report 1712 (July 1963).
(In the literature the series parents are customarily labelled by
their prismatic coefficient; "Series 60, Cb = 0.80" refers to the
0.805-prismatic parent digitized here.)

- Digitized offsets: [`parent_hull_offsets.csv`](parent_hull_offsets.csv)
  (Table 7 of the report, page V-10; text layer cross-checked visually
  against the rendered page at 300 dpi; the whole table re-verified
  row-by-row against the 300-dpi render during task 2.3 — one
  transposed-cell suspicion on the AP row investigated and cleared).
- Loading conventions (`openhull.geometry.load_offsets_csv`): each
  waterline column holds half-breadths as fractions of THAT waterline's
  maximum half-breadth; the `max_half_beam` row holds per-column maxima
  as fractions of B/2 — its FIRST value (0.850) belongs to the `Tan.`
  column (baseline tangent), the rest to the waterlines. Absolute
  half-breadth = value × column maximum × B/2. The grid is resampled
  to 21 equal stations / 27 equal waterline fractions (Simpson-ready).
  Acceptance anchors: rebuilt Cp total/fore/aft = 0.8033/0.8564/0.7501
  vs printed 0.805/0.861/0.750 (±0.005 band, see VALIDATION.md).
- Full report (public domain, US Government): DTIC accession
  [AD0419990](https://apps.dtic.mil/sti/citations/ADA419990), mirrored
  at [archive.org/items/DTIC_AD0419990](https://archive.org/details/DTIC_AD0419990).
- Role: mother hull for Lackenby transformation (Stage 2) and second
  validation ship for the v1.0 release gate
