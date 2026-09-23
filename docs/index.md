# OpenHull

**Agent-orchestrated parametric ship preliminary design** — from a
task book to principal dimensions, hydrostatics, IS Code stability,
resistance/propulsion, propeller design, seakeeping, an arrangement
schematic and a design report, with **every number traceable to a
formula whitelist** (AGENTS.md section 5).

## One command

```bash
uv run openhull run examples/taskbook_bulk_carrier.yaml \
  --report design_report.md \
  --hydro-curve-chart curves.png \
  --arrangement-chart ga.png \
  --arrangement-dxf ga.dxf
```

Regenerated sample outputs live in
[examples/demo_outputs](https://github.com/5777-wq/OpenHull/tree/main/examples/demo_outputs).

## What the toolchain does

| stage | deliverable |
|---|---|
| dimensions & weight | Norman-iterated displacement balance |
| hull form | digitised Series 60 parent + Lackenby transform |
| hydrostatics | tables, Bonjean, curves chart |
| stability | IS Code 2.2 criteria + severe wind & rolling |
| performance | Ayre resistance, Holtrop factors, B-series propeller |
| design space | grid scan, refusal histogram, Pareto front |
| seakeeping | textbook first level + capytaine RAOs (optional extra) |
| speed loss | Kwon's method (Beaufort / direction / loading) |
| deliverables | DXF, charts, Chinese Markdown report |

## Discipline

1. every formula whitelisted **before** implementation, page-verified
   against the source;
2. acceptance by numbers: book worked examples, independent-path
   cross-checks, public benchmarks (JBC, DTMB 1712, NMRI MP687);
3. declared approximations in every module docstring;
4. professional judgement stays with the naval architect.

See [VALIDATION.md](https://github.com/5777-wq/OpenHull/blob/main/VALIDATION.md)
for the full acceptance record and
[CONTRIBUTING.md](https://github.com/5777-wq/OpenHull/blob/main/CONTRIBUTING.md)
before proposing formulas.
