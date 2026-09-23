# OpenHull

[![ci](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml)

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | **Deutsch** | [Français](README_fr.md) | [Español](README_es.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

Open-Source-Toolchain für den parametrischen Schiffsentwurf, orchestriert
von KI-Agenten.

Aus einem Lastenheft (Schiffstyp, Tragfähigkeit, Dienstgeschwindigkeit,
Fahrtgebiet) liefert die Agenten-Pipeline Hauptabmessungen, hydrostatische
Kennwerte, einen Linienriss, Widerstands-/Propulsions-/Stabilitäts-
bewertungen und Zeichnungsausgaben (DXF).

## Status

**v0.3 veröffentlicht** — Stufe 3 abgeschlossen, die Leistungsschleife ist geschlossen: Ayre-Widerstandsschätzung, Holtrop-Propulsionsfaktoren mit Dienstgeschwindigkeitslöser, Wageningen-B-Serienpropellerentwurf (veröffentlichte Regression, Burrill-Kavitationsnachweis, schubgeführter Entwurf), Großwinkelstabilität mit den IS-Code-2.2-Kriterien und dem Wind-und-Seegangskriterium, dazu ein Entwurfsraum-Optimierer (`openhull optimize`), der Dimensionsverhältnisse zu zulässigen, kriterienbestehenden Entwürfen durchsucht, inklusive Pareto-Diagramm. Validiert gegen JBC, DTMB Report 1712 und die gemessenen NMRI-MP687-Freiwasserdaten (siehe [VALIDATION.md](VALIDATION.md)). Ausführen: `openhull run examples/taskbook_bulk_carrier.yaml`.

## Fahrplan

- [x] Stufe 1 — Iteration der Hauptabmessungen & hydrostatischer Kern (**v0.1**)
- [x] Stufe 2 — Parametrische Rumpfformgenerierung (Mutterschiff-Transformation) (**v0.2**)
- [x] Stufe 3 — Leistungsschleife: Widerstand / Antrieb / Stabilität (**v0.3**)
- [ ] Stufe 4 — Zeichnungsausgabe (DXF) & Entwurfsberichte
- [ ] Stufe 5 — Dokumentation & Community-Release (v1.0)

## Entwurfsgrundsätze

1. Jedes Ergebnis muss auf eine Gleichung oder eine veröffentlichte
   Quelle zurückführbar sein
2. Validierung an veröffentlichten Benchmark-Schiffen geht vor neuen
   Funktionen
3. Erfahrungsgleichungen deklarieren ihren Gültigkeitsbereich und lehnen
   Eingaben außerhalb dieses Bereichs zurück
4. Was sich als Gleichung schreiben lässt, wird automatisiert; was nicht,
   bleibt beim Ingenieur

## Lizenz

[MIT](LICENSE)
