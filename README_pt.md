# OpenHull

[![ci](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml)

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Deutsch](README_de.md) | [Français](README_fr.md) | [Español](README_es.md) | [Italiano](README_it.md) | **Português** | [Русский](README_ru.md)

> Design the shell that carries it all.

Cadeia de ferramentas open source de projeto paramétrico de navios,
orquestrada por agentes de IA.

A partir de um caderno de encargo (tipo de navio, porte bruto, velocidade
de serviço, zona de navegação), o pipeline de agentes produz dimensões
principais, hidrostática, plano de formas, avaliações de resistência /
propulsão / estabilidade e desenhos de saída (DXF).

## Estado

**v1.0 publicado** — as cinco etapas do roteiro estão concluídas: o ciclo do livreto de tarefas a dimensões, estabilidade IS Code, desempenho, navegabilidade (nível de livro + RAO capytaine opcional), uma estimativa de perda de velocidade de Kwon, desenhos (curvas hidrostáticas, esquema GA, DXF em camadas) e relatório de projeto em Markdown chinês está fechado. Saídas de exemplo em [examples/demo_outputs](examples/demo_outputs); site de documentação, modelos de contribuição e a disciplina de lista branca de fórmulas em [CONTRIBUTING.md](CONTRIBUTING.md). Registro de validação: [VALIDATION.md](VALIDATION.md). Comando: `openhull run examples/taskbook_bulk_carrier.yaml --report design_report.md --hydro-curve-chart curves.png`.

## Roteiro

- [x] Etapa 1 — Iteração das dimensões principais e núcleo hidrostático (**v0.1**)
- [x] Etapa 2 — Geração paramétrica de formas (transformação do navio-mãe) (**v0.2**)
- [x] Etapa 3 — Ciclo de desempenho: resistência / propulsão / estabilidade (**v0.3**)
- [x] Etapa 4 — Desenhos e relatórios: curvas hidrostáticas, esquema GA (DXF), relatório de projeto; navegabilidade em dois níveis (+ RAO capytaine opcional) (**v0.4**)
- [x] Etapa 5 — Documentação e lançamento comunitário (**v1.0**)

## Princípios de projeto

1. Todo resultado deve ser rastreável a uma equação ou a uma referência publicada
2. A validação com navios de referência publicados vem antes de novas funcionalidades
3. Fórmulas empíricas declaram sua faixa de aplicabilidade e rejeitam entradas fora dela
4. O que pode ser escrito como equação é automatizado; o resto fica a cargo do engenheiro

## Licença

[MIT](LICENSE)
