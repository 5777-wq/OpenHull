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

**v0.3 publicado** — etapa 3 completada, el bucle de rendimiento está cerrado: estimación de resistencia de Ayre, factores de propulsión de Holtrop con solver de velocidad de servicio, diseño de hélice de la serie B de Wageningen (regresión publicada, comprobación de cavitación de Burrill, diseño guiado por empuje), estabilidad a grandes ángulos con los criterios IS Code 2.2 y el criterio de viento y oleaje severos, más un optimizador del espacio de diseño (`openhull optimize`) que barre relaciones de dimensiones hacia diseños factibles con diagrama de Pareto. Validado contra el buque de referencia JBC, el informe DTMB 1712 y los datos medidos MP687 del NMRI (véase [VALIDATION.md](VALIDATION.md)). Ejecutar: `openhull run examples/taskbook_bulk_carrier.yaml`.

## Hoja de ruta

- [x] Etapa 1 — Iteración de dimensiones principales y núcleo hidrostático (**v0.1**)
- [x] Etapa 2 — Generación paramétrica de formas (transformación del buque madre) (**v0.2**)
- [x] Etapa 3 — Bucle de rendimiento: resistencia / propulsión / estabilidad (**v0.3**)
- [ ] Etapa 4 — Planos de salida (DXF) e informes de diseño
- [ ] Etapa 5 — Documentación y lanzamiento comunitario (v1.0)

## Principios de diseño

1. Cada resultado debe ser rastreable hasta una ecuación o una referencia publicada
2. La validación con buques de referencia publicados va antes que las nuevas funciones
3. Las fórmulas empíricas declaran su rango de aplicabilidad y rechazan las entradas fuera de rango
4. Lo que puede escribirse como ecuación se automatiza; lo demás queda en manos del ingeniero

## Licencia

[MIT](LICENSE)
