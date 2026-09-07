"""Drawing and report outputs.

Renders engineering deliverables from computed results: hydrostatic
curves and stability curves as matplotlib engineering plots, lines-plan
views (body plan, half-breadth plan, sheer plan) as black-and-white
engineering drawings, and DXF output via ezdxf with organised layers
(lines / dimensions / frame).

Inputs: computed results (hydrostatics, offsets, stability) and options
Outputs: PNG plots, DXF files, report-ready figures

See AGENTS.md §8 (third-party packages limited to numpy, matplotlib,
ezdxf, pyyaml, pytest).
"""
