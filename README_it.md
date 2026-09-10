# OpenHull

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Deutsch](README_de.md) | [Français](README_fr.md) | [Español](README_es.md) | **Italiano** | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

Toolchain open source per la progettazione parametrica di navi,
orchestrata da agenti IA.

Da un capitolato (tipo di nave, portata lorda, velocità di servizio,
zona di navigazione), la pipeline di agenti produce dimensioni
principali, idrostatica, piano di forme, valutazioni di resistenza /
propulsione / stabilità e output di disegni (DXF).

## Stato

🚧 In costruzione — Fase 1 in corso: strutture dati e stima delle dimensioni principali completate e validate sulla nave di riferimento JBC; nucleo idrostatico in sviluppo.

## Roadmap

- [ ] Fase 1 — Iterazione delle dimensioni principali e nucleo idrostatico
- [ ] Fase 2 — Generazione parametrica della carena (trasformazione della nave madre)
- [ ] Fase 3 — Ciclo delle prestazioni: resistenza / propulsione / stabilità
- [ ] Fase 4 — Output di disegni (DXF) e relazioni di progetto
- [ ] Fase 5 — Rilascio pubblico v0.1

## Principi di progettazione

1. Ogni risultato deve essere riconducibile a un'equazione o a un riferimento pubblicato
2. La validazione su navi di riferimento pubblicate viene prima delle nuove funzionalità
3. Le formule empiriche dichiarano il loro intervallo di applicabilità e rifiutano input fuori intervallo
4. Ciò che si può scrivere come equazione viene automatizzato; il resto è lasciato all'ingegnere

## Licenza

[MIT](LICENSE)
