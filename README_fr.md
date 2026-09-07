# OpenHull

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

🚧 En construction — Étape 0 terminée (constitution du projet, cahier des
charges, navires de référence, squelette du code) ; noyau de calcul en
développement.

## Feuille de route

- [ ] Étape 1 — Itération des dimensions principales & noyau hydrostatique
- [ ] Étape 2 — Génération paramétrique de carène (transformation du navire mère)
- [ ] Étape 3 — Boucle performance : résistance / propulsion / stabilité
- [ ] Étape 4 — Sorties graphiques (DXF) & rapports de conception
- [ ] Étape 5 — Publication v0.1

## Principes de conception

1. Tout résultat doit être traçable vers une équation ou une référence publiée
2. La validation sur des navires de référence publiés prime sur les nouvelles fonctionnalités
3. Les formules empiriques déclarent leur domaine de validité et refusent les entrées hors domaine
4. Ce qui s'écrit sous forme d'équation est automatisé ; ce qui ne s'y prête pas est laissé à l'ingénieur

## Licence

[MIT](LICENSE)
