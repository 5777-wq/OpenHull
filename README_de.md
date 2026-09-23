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

**v0.4 veröffentlicht** — Stufe 4 abgeschlossen: ergebnisorientierte Zeichnungen und Berichte aus einem Befehl (siehe [examples/demo_outputs](examples/demo_outputs)) — Hydrostatikkurven im Lehrbuchlayout, ein Generalarrangement-Schema als Grafik und geschichtetes DXF sowie ein chinesischer Markdown-Entwurfsbericht. Seegang in zwei Ebenen: Formel-Estimates der ersten Stufe (Eigenperioden, Resonanzurteile) und nullgeschwindige RAOs über das optionale capytaine-Extra (`pip install 'openhull[seakeeping]'`). Jede Zahl rückverfolgbar zur Formel-Whitelist (siehe [VALIDATION.md](VALIDATION.md)). Befehl: `openhull run examples/taskbook_bulk_carrier.yaml --report design_report.md --hydro-curve-chart curves.png`.

## Fahrplan

- [x] Stufe 1 — Iteration der Hauptabmessungen & hydrostatischer Kern (**v0.1**)
- [x] Stufe 2 — Parametrische Rumpfformgenerierung (Mutterschiff-Transformation) (**v0.2**)
- [x] Stufe 3 — Leistungsschleife: Widerstand / Antrieb / Stabilität (**v0.3**)
- [x] Stufe 4 — Zeichnungen & Berichte: Hydrostatikkurven, GA-Schema (DXF), Entwurfsbericht; Seegang zweistufig (+ optionale capytaine-RAOs) (**v0.4**)
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
