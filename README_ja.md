# OpenHull

[![ci](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml)

[English](README.md) | [简体中文](README_zh.md) | **日本語** | [한국어](README_ko.md) | [Deutsch](README_de.md) | [Français](README_fr.md) | [Español](README_es.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

AIエージェントがオーケストレーションする、オープンソースの
パラメトリック船体初期設計ツールチェーン。

タスクブック（船種、デッドウェイト、サービス速度、航行海域）を
入力すると、エージェントパイプラインが主寸法、静水性能、線図、
抵抗／推進／復原性評価、図面出力（DXF）を自動で生成します。

## 現在の状況

**v1.0 リリース** —— ロードマップ全 5 ステージ完了：タスクブックから主要目、IS Code 復原性、性能、耐波性（教科書層＋オプション capytaine RAO）、Kwon 速度損失推定、図面（静水力曲線図・総配置略図・レイヤー DXF）、中国語 Markdown 設計報告書までのループが閉じました。サンプル出力は [examples/demo_outputs](examples/demo_outputs)；ドキュメントサイト・貢献テンプレート・公式ホワイトリスト規律は [CONTRIBUTING.md](CONTRIBUTING.md)。検証記録：[VALIDATION.md](VALIDATION.md)。実行：`openhull run examples/taskbook_bulk_carrier.yaml --report design_report.md --hydro-curve-chart curves.png`。

## ロードマップ

- [x] ステージ 1 — 主寸法反復と静水性能計算コア (**v0.1**)
- [x] ステージ 2 — パラメトリック船型生成（母型船変換）(**v0.2**)
- [x] ステージ 3 — 性能ループ：抵抗／推進／復原性 (**v0.3**)
- [x] ステージ 4 — 図面と報告書：静水力曲線図、総配置略図（DXF）、設計報告書；耐波性二層（＋オプション capytaine RAO）(**v0.4**)
- [x] ステージ 5 — ドキュメント & コミュニティリリース（**v1.0**）

## 設計原則

1. すべての出力は数式または公開文献に遡って検証可能であること
2. 新機能の追加より、公開ベンチマーク船データとの検証を優先する
3. 実験式は適用範囲を明示し、範囲外の入力は拒否する
4. 数式で書けるものは自動化し、書けないものはエンジニアに任せる

## ライセンス

[MIT](LICENSE)
