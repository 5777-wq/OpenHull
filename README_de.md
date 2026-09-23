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

**v1.0 veröffentlicht** — alle fünf Roadmap-Stufen abgeschlossen: der Kreislauf vom Aufgabenbuch über Dimensionen, IS-Code-Stabilität, Leistung, Seegang (Lehrbuchebene + optionale capytaine-RAOs), eine Kwon-Fahrtgeschwindigkeitsverlustschätzung, Zeichnungen (Hydrostatikkurven, GA-Schema, geschichtetes DXF) und einen chinesischen Markdown-Entwurfsbericht ist geschlossen. Beispieloutputs in [examples/demo_outputs](examples/demo_outputs); Dokumentationsseite, Beitragsvorlagen und die Formel-Whitelist-Disziplin in [CONTRIBUTING.md](CONTRIBUTING.md). Validierungsnachweis: [VALIDATION.md](VALIDATION.md). Befehl: `openhull run examples/taskbook_bulk_carrier.yaml --report design_report.md --hydro-curve-chart curves.png`.

## Fahrplan

- [x] Stufe 1 — Iteration der Hauptabmessungen & hydrostatischer Kern (**v0.1**)
- [x] Stufe 2 — Parametrische Rumpfformgenerierung (Mutterschiff-Transformation) (**v0.2**)
- [x] Stufe 3 — Leistungsschleife: Widerstand / Antrieb / Stabilität (**v0.3**)
- [x] Stufe 4 — Zeichnungen & Berichte: Hydrostatikkurven, GA-Schema (DXF), Entwurfsbericht; Seegang zweistufig (+ optionale capytaine-RAOs) (**v0.4**)
- [x] Stufe 5 — Dokumentation & Community-Release (**v1.0**)

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
