"""Lines plan — parametric hull-form variation.

Generates hull forms by systematic variation of a parent hull's offsets
(Lackenby transformation), targeting a required block coefficient while
keeping (or scaling) the principal dimensions. Produces the offsets
table (stations × waterlines) that feeds the hydrostatics module.

Inputs: parent-hull offsets table and a target form (Cb, dimensions)
Outputs: transformed offsets table (stations × waterlines half-breadths)

See AGENTS.md §7 — transformation of a parent hull only; no free-form
surface generation.
"""
