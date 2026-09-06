# OpenHull

> Design the shell that carries it all.

Open-source parametric ship hull design toolchain, orchestrated by AI agents.

Provide a task book (ship type, deadweight, service speed, trading range) —
the agent pipeline returns principal dimensions, hydrostatics, a lines plan,
resistance / propulsion / stability estimates, and drawing outputs (DXF).

## Status

🚧 Under construction — keel laying stage.

## Roadmap

- [ ] Stage 1 — Principal dimension iteration & hydrostatics core
- [ ] Stage 2 — Parametric hull form generation (mother-ship transformation)
- [ ] Stage 3 — Performance loop: resistance / propulsion / stability
- [ ] Stage 4 — Drawing output (DXF) & design reports
- [ ] Stage 5 — v0.1 public release

## Design principles

1. Every output must be traceable to an equation or a published reference
2. Validation against published benchmark ships comes before new features
3. Empirical formulas declare their applicability range and refuse out-of-range input
4. What can be written as an equation is automated; what cannot is left to the engineer

## License

[MIT](LICENSE)
