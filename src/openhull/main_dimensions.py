"""Principal dimension estimation.

Derives first estimates of the principal dimensions (L, B, D, T and Cb)
from the task-book requirements — deadweight and service speed — using
whitelisted statistical methods: the deadweight/displacement ratio,
Watson & Gilfillan (1977) relations, and statistical checks of the
dimension ratios against bulk-carrier ranges.

Inputs: task-book requirements (deadweight, service speed, constraints)
Outputs: a principal-dimension proposal (L, B, D, T, Cb)

See AGENTS.md §5 (formula whitelist) and §4 (acceptance tolerances).
"""
