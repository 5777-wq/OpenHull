"""Calm-water resistance and effective power.

Estimates calm-water resistance and effective power from hull form and
speed using the whitelisted empirical chain: ITTC 1957 friction line
plus the Holtrop & Mennen (1982) residual-resistance formulation with
appendage and air corrections.

Every correlation declares its applicability range (Froude number, form
coefficients, size range) as data; out-of-range input raises an error
instead of extrapolating.

Inputs: hull form / principal dimensions, service speed, water conditions
Outputs: resistance breakdown and effective power curve

See AGENTS.md §5 (whitelist), §6 (applicability guards).
"""
