"""Intact stability.

Evaluates initial stability and large-angle stability: GM with free-
surface correction interface, static-stability arm (GZ) curves from
knuckle..keel to the range of positive stability via hull-form
integration, and compliance checks against the IMO 2008 IS Code
general criteria (GM 0.15 m, area ratios, weather criterion).

Inputs: hull form, loading condition (mass, KG, LCG), free-surface data
Outputs: GM, GZ curve, criterion-by-criterion compliance verdicts

See AGENTS.md §4 (GM tolerance ±5 % or 0.05 m), §5 (IS Code whitelist).
"""
