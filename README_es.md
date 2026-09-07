# OpenHull

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Deutsch](README_de.md) | [Français](README_fr.md) | **Español** | [Italiano](README_it.md) | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

Cadena de herramientas open source de diseño paramétrico de buques,
orquestada por agentes de IA.

A partir de un cuaderno de tareas (tipo de buque, peso muerto, velocidad
de servicio, zona de navegación), el flujo de agentes genera dimensiones
principales, hidrostática, plan de formas, evaluaciones de resistencia /
propulsión / estabilidad y planos de salida (DXF).

## Estado

🚧 En construcción — Etapa 0 completada (constitución del proyecto,
cuaderno de tareas, buques de referencia, esqueleto del código); núcleo
de cálculo en desarrollo.

## Hoja de ruta

- [ ] Etapa 1 — Iteración de dimensiones principales y núcleo hidrostático
- [ ] Etapa 2 — Generación paramétrica de formas (transformación del buque madre)
- [ ] Etapa 3 — Bucle de rendimiento: resistencia / propulsión / estabilidad
- [ ] Etapa 4 — Planos de salida (DXF) e informes de diseño
- [ ] Etapa 5 — Lanzamiento público v0.1

## Principios de diseño

1. Cada resultado debe ser rastreable hasta una ecuación o una referencia publicada
2. La validación con buques de referencia publicados va antes que las nuevas funciones
3. Las fórmulas empíricas declaran su rango de aplicabilidad y rechazan las entradas fuera de rango
4. Lo que puede escribirse como ecuación se automatiza; lo demás queda en manos del ingeniero

## Licencia

[MIT](LICENSE)
