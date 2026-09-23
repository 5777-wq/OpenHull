# OpenHull

[![ci](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml)

[English](README.md) | **简体中文** | [日本語](README_ja.md) | [한국어](README_ko.md) | [Deutsch](README_de.md) | [Français](README_fr.md) | [Español](README_es.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

开源的、由 AI 智能体编排的参数化船舶初步设计工具链。

输入一份设计任务书（船型、载重吨、服务航速、航区），智能体流水线
自动产出：主尺度方案、静水力表、型线图、阻力/推进/稳性评估，以及
DXF 图纸等成果。

## 当前状态

**v0.3 已发布** —— 阶段 3 完成，性能闭环贯通：艾亚阻力估算、Holtrop 推进因子与服务航速解算、瓦根宁根 B 系列螺旋桨设计（公开回归式 + 柏利尔空泡校核 + 推力式设计）、大倾角稳性带 IS Code 2.2 六项衡准与恶劣风浪衡准，以及设计空间寻优器（`openhull optimize`：主尺度比扫描输出可行方案集与帕累托权衡图）。全部通过 JBC 基准船、DTMB 1712 报告与 NMRI MP687 实测开敞水数据验证（见 [VALIDATION.md](VALIDATION.md)）。一条命令运行：`openhull run examples/taskbook_bulk_carrier.yaml`。

## 路线图

- [x] 阶段 1 —— 主尺度迭代与静水力内核（**v0.1**）
- [x] 阶段 2 —— 参数化船型生成（母型船变换）（**v0.2**）
- [x] 阶段 3 —— 性能闭环：阻力 / 推进 / 稳性（**v0.3**）
- [ ] 阶段 4 —— 图纸输出（DXF）与设计报告
- [ ] 阶段 5 —— 文档完善与社区发布（v1.0）

## 设计原则

1. 每一个输出结果都必须可追溯至某条公式或公开文献
2. 与公开基准船数据的验证优先于新功能开发
3. 经验公式必须声明适用范围，超出范围的输入一律拒绝
4. 能写成公式的交给自动化，写不成公式的留给工程师

## 许可证

[MIT](LICENSE)
