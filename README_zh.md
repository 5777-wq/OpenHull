# OpenHull

[English](README.md) | **简体中文** | [日本語](README_ja.md) | [한국어](README_ko.md) | [Deutsch](README_de.md) | [Français](README_fr.md) | [Español](README_es.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

开源的、由 AI 智能体编排的参数化船舶初步设计工具链。

输入一份设计任务书（船型、载重吨、服务航速、航区），智能体流水线
自动产出：主尺度方案、静水力表、型线图、阻力/推进/稳性评估，以及
DXF 图纸等成果。

## 当前状态

**v0.1 已发布** —— 阶段 1 完成：任务书驱动的重量浮力平衡、主尺度、静水力、初稳性与浮态、干舷校核，全部通过 JBC 基准船验证（见 [VALIDATION.md](VALIDATION.md)）。一条命令运行：`openhull run examples/taskbook_bulk_carrier.yaml`。

## 路线图

- [x] 阶段 1 —— 主尺度迭代与静水力内核（**v0.1**）
- [ ] 阶段 2 —— 参数化船型生成（母型船变换）
- [ ] 阶段 3 —— 性能闭环：阻力 / 推进 / 稳性
- [ ] 阶段 4 —— 图纸输出（DXF）与设计报告
- [ ] 阶段 5 —— 文档完善与社区发布（v1.0）

## 设计原则

1. 每一个输出结果都必须可追溯至某条公式或公开文献
2. 与公开基准船数据的验证优先于新功能开发
3. 经验公式必须声明适用范围，超出范围的输入一律拒绝
4. 能写成公式的交给自动化，写不成公式的留给工程师

## 许可证

[MIT](LICENSE)
