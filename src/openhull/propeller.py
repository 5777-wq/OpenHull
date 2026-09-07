"""Propeller preliminary design.

Estimates preliminary propeller particulars — diameter, pitch ratio,
blade-area ratio, revolutions — for a required thrust/power point, using
AU-series chart data with the regression pinned in AGENTS.md §5
(selected at implementation time).

Inputs: effective power / thrust demand, service speed, wake and thrust
deduction estimates, diameter/revolutions constraints
Outputs: propeller particulars proposal (D, P/D, EAR, efficiency)

See AGENTS.md §5 (whitelist; the exact regression is pinned before any
implementation).
"""
