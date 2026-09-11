# OpenHull

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Deutsch](README_de.md) | [Français](README_fr.md) | [Español](README_es.md) | [Italiano](README_it.md) | **Português** | [Русский](README_ru.md)

> Design the shell that carries it all.

Cadeia de ferramentas open source de projeto paramétrico de navios,
orquestrada por agentes de IA.

A partir de um caderno de encargo (tipo de navio, porte bruto, velocidade
de serviço, zona de navegação), o pipeline de agentes produz dimensões
principais, hidrostática, plano de formas, avaliações de resistência /
propulsão / estabilidade e desenhos de saída (DXF).

## Estado

**v0.1 publicado** — etapa 1 concluída: equilíbrio peso-empuxo por livro de tarefas, dimensões principais, hidrostática, estabilidade inicial e aparado, borda livre — tudo validado contra o navio de referência JBC (veja [VALIDATION.md](VALIDATION.md)). Executar: `openhull run examples/taskbook_bulk_carrier.yaml`.

## Roteiro

- [x] Etapa 1 — Iteração das dimensões principais e núcleo hidrostático (**v0.1**)
- [ ] Etapa 2 — Geração paramétrica de formas (transformação do navio-mãe)
- [ ] Etapa 3 — Ciclo de desempenho: resistência / propulsão / estabilidade
- [ ] Etapa 4 — Desenhos de saída (DXF) e relatórios de projeto
- [ ] Etapa 5 — Documentação e lançamento comunitário (v1.0)

## Princípios de projeto

1. Todo resultado deve ser rastreável a uma equação ou a uma referência publicada
2. A validação com navios de referência publicados vem antes de novas funcionalidades
3. Fórmulas empíricas declaram sua faixa de aplicabilidade e rejeitam entradas fora dela
4. O que pode ser escrito como equação é automatizado; o resto fica a cargo do engenheiro

## Licença

[MIT](LICENSE)
