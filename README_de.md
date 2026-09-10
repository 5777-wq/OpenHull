# OpenHull

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | **Deutsch** | [Français](README_fr.md) | [Español](README_es.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

Open-Source-Toolchain für den parametrischen Schiffsentwurf, orchestriert
von KI-Agenten.

Aus einem Lastenheft (Schiffstyp, Tragfähigkeit, Dienstgeschwindigkeit,
Fahrtgebiet) liefert die Agenten-Pipeline Hauptabmessungen, hydrostatische
Kennwerte, einen Linienriss, Widerstands-/Propulsions-/Stabilitäts-
bewertungen und Zeichnungsausgaben (DXF).

## Status

🚧 Im Aufbau — Stufe 1 läuft: Kerndatenstrukturen und Hauptabmessungsschätzung sind fertig und gegen das Benchmark-Schiff JBC validiert; der hydrostatische Kern ist in Arbeit.

## Fahrplan

- [ ] Stufe 1 — Iteration der Hauptabmessungen & hydrostatischer Kern
- [ ] Stufe 2 — Parametrische Rumpfformgenerierung (Mutterschiff-Transformation)
- [ ] Stufe 3 — Leistungsschleife: Widerstand / Antrieb / Stabilität
- [ ] Stufe 4 — Zeichnungsausgabe (DXF) & Entwurfsberichte
- [ ] Stufe 5 — v0.1-Veröffentlichung

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
