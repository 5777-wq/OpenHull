# Demo outputs — TB-001 (task 4.4)

One command reproduces everything in this folder from the task book:

```bash
uv run openhull run examples/taskbook_bulk_carrier.yaml \
  --hydro-curve-chart examples/demo_outputs/hydro_curves.png \
  --arrangement-chart examples/demo_outputs/ga_schematic.png \
  --arrangement-dxf  examples/demo_outputs/ga_schematic.dxf \
  --report          examples/demo_outputs/design_report.md \
  --csv > examples/demo_outputs/hydrostatics_table.csv
```

(Without uv: `pip install -e .` then drop the `uv run` prefix. For
the optional stage-2 RAOs: `pip install -e '.[seakeeping]'` and run
`openhull rao examples/taskbook_bulk_carrier.yaml`.)

## Contents

| file | plan task | what it is |
|---|---|---|
| `design_report.md` | 4.3 | the Chinese Markdown design report — restates the run summary (dimensions, hydrostatics, IS Code stability tables, declared skips, seakeeping verdicts, arrangement table) and links the chart below |
| `hydro_curves.png` | 4.1 | hydrostatic curves chart, textbook layout (draft axis increasing downward), twelve panels of the task 1.4 table |
| `ga_schematic.png` | 4.2 | general-arrangement schematic: side view + deck plan of the DECLARED default bulk-carrier compartment scheme |
| `ga_schematic.dxf` | 4.2 | the same layout as a layered DXF (GA-SIDE / GA-PLAN / GA-DB / GA-LABELS) |
| `hydrostatics_table.csv` | 1.4 | the hydrostatic table at quarter-drafts (Excel-friendly UTF-8-SIG) |

All numbers are traceable to the AGENTS.md section 5 formula
whitelist or to task-book declarations; the arrangement schematic is
a declared layout diagram, not hull lines.  Regenerated on
2026-09-23 from commit history (v0.4.0).
