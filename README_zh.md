# OpenHull

[![ci](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml)

[English](README.md) | **简体中文** | [日本語](README_ja.md) | [한국어](README_ko.md) | [Deutsch](README_de.md) | [Français](README_fr.md) | [Español](README_es.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

开源的、由 AI 智能体编排的参数化船舶初步设计工具链。

输入一份设计任务书（船型、载重吨、服务航速、航区），智能体流水线
自动产出：主尺度方案、静水力表、型线图、阻力/推进/稳性评估，以及
DXF 图纸等成果。

## 当前状态

**v0.4 已发布** —— 阶段 4 完成：工具链交付首批图纸与报告成果，一条命令出齐（见 [examples/demo_outputs](examples/demo_outputs)）——教材版式静水力曲线图、总布置简图（图+分层 DXF）、中文 Markdown 设计报告。耐波性两级并入闭环：书内公式第一级（固有周期与谐摇判定）+ 可选 capytaine 扩展的零航速 RAO（`pip install 'openhull[seakeeping]'`）。每个数可溯源至公式白名单（见 [VALIDATION.md](VALIDATION.md)）。一条命令：`openhull run examples/taskbook_bulk_carrier.yaml --report design_report.md --hydro-curve-chart curves.png`。

## 路线图

- [x] 阶段 1 —— 主尺度迭代与静水力内核（**v0.1**）
- [x] 阶段 2 —— 参数化船型生成（母型船变换）（**v0.2**）
- [x] 阶段 3 —— 性能闭环：阻力 / 推进 / 稳性（**v0.3**）
- [x] 阶段 4 —— 图纸与报告：静水力曲线图、总布置简图（DXF）、设计报告；耐波性两级（含可选 capytaine RAO）（**v0.4**）
- [ ] 阶段 5 —— 文档完善与社区发布（v1.0）

## 设计原则

1. 每一个输出结果都必须可追溯至某条公式或公开文献
2. 与公开基准船数据的验证优先于新功能开发
3. 经验公式必须声明适用范围，超出范围的输入一律拒绝
4. 能写成公式的交给自动化，写不成公式的留给工程师

## 许可证

[MIT](LICENSE)
