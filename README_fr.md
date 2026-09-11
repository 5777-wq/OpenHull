# OpenHull

[![ci](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml)

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md) | [Deutsch](README_de.md) | **Français** | [Español](README_es.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

Chaîne d'outils open source de conception paramétrique de navires,
orchestrée par des agents IA.

À partir d'un cahier des charges (type de navire, port en lourd, vitesse
de service, zone de navigation), le pipeline d'agents produit les
dimensions principales, l'hydrostatique, un plan de formes, des
évaluations de résistance / propulsion / stabilité et des livrables de
plans (DXF).

## État d'avancement

**v0.1 publié** — étape 1 terminée : équilibre poids-poussée piloté par cahier des charges, dimensions principales, hydrostatique, stabilité initiale et assiette, franc-bord — le tout validé sur le navire de référence JBC (voir [VALIDATION.md](VALIDATION.md)). Exécution : `openhull run examples/taskbook_bulk_carrier.yaml`.

## Feuille de route

- [x] Étape 1 — Itération des dimensions principales & noyau hydrostatique (**v0.1**)
- [ ] Étape 2 — Génération paramétrique de carène (transformation du navire mère)
- [ ] Étape 3 — Boucle performance : résistance / propulsion / stabilité
- [ ] Étape 4 — Sorties graphiques (DXF) & rapports de conception
- [ ] Étape 5 — Documentation et publication communautaire (v1.0)

## Principes de conception

1. Tout résultat doit être traçable vers une équation ou une référence publiée
2. La validation sur des navires de référence publiés prime sur les nouvelles fonctionnalités
3. Les formules empiriques déclarent leur domaine de validité et refusent les entrées hors domaine
4. Ce qui s'écrit sous forme d'équation est automatisé ; ce qui ne s'y prête pas est laissé à l'ingénieur

## Licence

[MIT](LICENSE)
