# OpenHull

[![ci](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml)

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Deutsch](README_de.md) | [Français](README_fr.md) | **Español** | [Italiano](README_it.md) | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

Cadena de herramientas open source de diseño paramétrico de buques,
orquestada por agentes de IA.

A partir de un cuaderno de tareas (tipo de buque, peso muerto, velocidad
de servicio, zona de navegación), el flujo de agentes genera dimensiones
principales, hidrostática, plan de formas, evaluaciones de resistencia /
propulsión / estabilidad y planos de salida (DXF).

## Estado

**v0.4 publicado** — etapa 4 completada: primeros entregables de planos e informes en un solo comando (véase [examples/demo_outputs](examples/demo_outputs)) — curvas hidrostáticas en formato de libro de texto, esquema de disposición general como gráfico y DXF por capas, e informe de diseño en Markdown en chino. La estabilidad en la mar se incorpora en dos niveles: estimaciones de libro de primer nivel (periodos naturales, veredictos de resonancia) y RAO a velocidad cero vía la extensión opcional capytaine (`pip install 'openhull[seakeeping]'`). Cada número trazable a la lista blanca de fórmulas (véase [VALIDATION.md](VALIDATION.md)). Comando: `openhull run examples/taskbook_bulk_carrier.yaml --report design_report.md --hydro-curve-chart curves.png`.

## Hoja de ruta

- [x] Etapa 1 — Iteración de dimensiones principales y núcleo hidrostático (**v0.1**)
- [x] Etapa 2 — Generación paramétrica de formas (transformación del buque madre) (**v0.2**)
- [x] Etapa 3 — Bucle de rendimiento: resistencia / propulsión / estabilidad (**v0.3**)
- [x] Etapa 4 — Planos e informes: curvas hidrostáticas, esquema GA (DXF), informe de diseño; estabilidad en la mar en dos niveles (+ RAO capytaine opcional) (**v0.4**)
- [ ] Etapa 5 — Documentación y lanzamiento comunitario (v1.0)

## Principios de diseño

1. Cada resultado debe ser rastreable hasta una ecuación o una referencia publicada
2. La validación con buques de referencia publicados va antes que las nuevas funciones
3. Las fórmulas empíricas declaran su rango de aplicabilidad y rechazan las entradas fuera de rango
4. Lo que puede escribirse como ecuación se automatiza; lo demás queda en manos del ingeniero

## Licencia

[MIT](LICENSE)
