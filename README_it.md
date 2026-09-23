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

**v1.0 pubblicato** — tutte e cinque le fasi della roadmap sono completate: il ciclo dal libretto di attività a dimensioni, stabilità IS Code, prestazioni, tenuta al mare (livello da manuale + RAO capytaine opzionale), una stima di perdita di velocità di Kwon, disegni (curve idrostatiche, schema GA, DXF a strati) e relazione di progetto in Markdown cinese è chiuso. Output di esempio in [examples/demo_outputs](examples/demo_outputs); sito di documentazione, template di contributo e disciplina della whitelist delle formule in [CONTRIBUTING.md](CONTRIBUTING.md). Registro di validazione: [VALIDATION.md](VALIDATION.md). Comando: `openhull run examples/taskbook_bulk_carrier.yaml --report design_report.md --hydro-curve-chart curves.png`.

## Roadmap

- [x] Fase 1 — Iterazione delle dimensioni principali e nucleo idrostatico (**v0.1**)
- [x] Fase 2 — Generazione parametrica della carena (trasformazione della nave madre) (**v0.2**)
- [x] Fase 3 — Ciclo delle prestazioni: resistenza / propulsione / stabilità (**v0.3**)
- [x] Fase 4 — Disegni e relazioni: curve idrostatiche, schema GA (DXF), relazione di progetto; tenuta al mare a due livelli (+ RAO capytaine opzionale) (**v0.4**)
- [x] Fase 5 — Documentazione e rilascio di comunità (**v1.0**)

## Principi di progettazione

1. Ogni risultato deve essere riconducibile a un'equazione o a un riferimento pubblicato
2. La validazione su navi di riferimento pubblicate viene prima delle nuove funzionalità
3. Le formule empiriche dichiarano il loro intervallo di applicabilità e rifiutano input fuori intervallo
4. Ciò che si può scrivere come equazione viene automatizzato; il resto è lasciato all'ingegnere

## Licenza

[MIT](LICENSE)
