"""Hydrostatics.

Computes hydrostatic particulars at arbitrary drafts from a hull-form
representation: displacement volume and mass, waterplane area, centre
of flotation, TPC, MTC, KB, BMT, BML, and the form coefficients
(Cb, Cp, Cw, Cm). Integrations use in-package Simpson's-rule numerical
integration; a Bonjean-curve interface serves the stability modules.

Inputs: hull form (offsets or an approximation) and a set of drafts
Outputs: hydrostatic tables / a Hydrostatics container per draft

See AGENTS.md §5 (methods), §4 (tolerances: ∇ ±1 %, KM ±2 %, TPC ±3 %).
"""
