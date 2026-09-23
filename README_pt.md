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

**v0.3 publicado** — etapa 3 concluída, o ciclo de desempenho está fechado: estimativa de resistência de Ayre, fatores de propulsão de Holtrop com solver de velocidade de serviço, projeto de hélice da série B de Wageningen (regressão publicada, verificação de cavitação de Burrill, projeto guiado por empuxo), estabilidade a grandes ângulos com os critérios IS Code 2.2 e o critério de vento e mar severos, mais um otimizador do espaço de projeto (`openhull optimize`) que varre relações de dimensões para projetos viáveis com diagrama de Pareto. Validado contra o navio de referência JBC, o relatório DTMB 1712 e os dados medidos MP687 do NMRI (veja [VALIDATION.md](VALIDATION.md)). Executar: `openhull run examples/taskbook_bulk_carrier.yaml`.

## Roteiro

- [x] Etapa 1 — Iteração das dimensões principais e núcleo hidrostático (**v0.1**)
- [x] Etapa 2 — Geração paramétrica de formas (transformação do navio-mãe) (**v0.2**)
- [x] Etapa 3 — Ciclo de desempenho: resistência / propulsão / estabilidade (**v0.3**)
- [ ] Etapa 4 — Desenhos de saída (DXF) e relatórios de projeto
- [ ] Etapa 5 — Documentação e lançamento comunitário (v1.0)

## Princípios de projeto

1. Todo resultado deve ser rastreável a uma equação ou a uma referência publicada
2. A validação com navios de referência publicados vem antes de novas funcionalidades
3. Fórmulas empíricas declaram sua faixa de aplicabilidade e rejeitam entradas fora dela
4. O que pode ser escrito como equação é automatizado; o resto fica a cargo do engenheiro

## Licença

[MIT](LICENSE)
