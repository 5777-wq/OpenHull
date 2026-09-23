# OpenHull

[![ci](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml)

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Deutsch](README_de.md) | [Français](README_fr.md) | [Español](README_es.md) | **Italiano** | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

Toolchain open source per la progettazione parametrica di navi,
orchestrata da agenti IA.

Da un capitolato (tipo di nave, portata lorda, velocità di servizio,
zona di navigazione), la pipeline di agenti produce dimensioni
principali, idrostatica, piano di forme, valutazioni di resistenza /
propulsione / stabilità e output di disegni (DXF).

## Stato

**v0.3 pubblicato** — fase 3 completata, il ciclo delle prestazioni è chiuso: stima della resistenza di Ayre, fattori di propulsione di Holtrop con solver della velocità di servizio, progettazione dell'elica della serie B di Wageningen (regressione pubblicata, verifica di cavitazione di Burrill, progetto guidato dalla spinta), stabilità a grandi angoli con i criteri IS Code 2.2 e il criterio di vento e onda severi, più un ottimizzatore dello spazio di progetto (`openhull optimize`) che esplora i rapporti dimensionali verso progetti fattibili con diagramma di Pareto. Validato sulla nave di riferimento JBC, sul rapporto DTMB 1712 e sui dati misurati MP687 del NMRI (vedi [VALIDATION.md](VALIDATION.md)). Esecuzione: `openhull run examples/taskbook_bulk_carrier.yaml`.

## Roadmap

- [x] Fase 1 — Iterazione delle dimensioni principali e nucleo idrostatico (**v0.1**)
- [x] Fase 2 — Generazione parametrica della carena (trasformazione della nave madre) (**v0.2**)
- [x] Fase 3 — Ciclo delle prestazioni: resistenza / propulsione / stabilità (**v0.3**)
- [ ] Fase 4 — Output di disegni (DXF) e relazioni di progetto
- [ ] Fase 5 — Documentazione e rilascio di comunità (v1.0)

## Principi di progettazione

1. Ogni risultato deve essere riconducibile a un'equazione o a un riferimento pubblicato
2. La validazione su navi di riferimento pubblicate viene prima delle nuove funzionalità
3. Le formule empiriche dichiarano il loro intervallo di applicabilità e rifiutano input fuori intervallo
4. Ciò che si può scrivere come equazione viene automatizzato; il resto è lasciato all'ingegnere

## Licenza

[MIT](LICENSE)
