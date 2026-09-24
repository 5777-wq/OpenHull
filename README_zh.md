<div align="center">

# OpenHull

**Design the shell that carries it all.**

开源的、由 AI 智能体编排的参数化船舶初步设计工具链：从一份任务书出发，
自动完成主尺度、静水力、IS Code 稳性、阻力与推进、螺旋桨设计、耐波性、
图纸与设计报告——**每一个数字都可溯源到公式白名单**。

[![tests](https://github.com/5777-wq/OpenHull/actions/workflows/tests.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/tests.yml)
[![release](https://img.shields.io/github/v/release/5777-wq/OpenHull)](https://github.com/5777-wq/OpenHull/releases)
[![license](https://img.shields.io/github/license/5777-wq/OpenHull)](LICENSE)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![文档站](https://img.shields.io/website?url=https%3A%2F%2F5777-wq.github.io%2FOpenHull%2F)](https://5777-wq.github.io/OpenHull/)
[![官网主页](https://img.shields.io/badge/%E5%AE%98%E7%BD%91-%E4%B8%AD%E6%96%87-success)](https://5777-wq.github.io/openhull-site/)

**[中文文档站](https://5777-wq.github.io/OpenHull/)** ·
**[官网主页](https://5777-wq.github.io/openhull-site/)** ·
**[English](README.md)** ·
[日本語](README_ja.md) · [한국어](README_ko.md) · [Deutsch](README_de.md) · [Français](README_fr.md) · [Español](README_es.md) · [Italiano](README_it.md) · [Português](README_pt.md) · [Русский](README_ru.md)

</div>

---

## 它做什么

写一份**任务书**（YAML：船型、载重吨、服务航速、航区），OpenHull
跑完整个初步设计链，交付：

| 环节 | 成果 |
|---|---|
| 主尺度与重量 | 诺曼系数迭代的重量浮力平衡、载重量比法 |
| 船型 | 数字化 Series 60 母型 + Lackenby 变换，真实型值表 |
| 静水力 | 静水力表、邦戎曲线、教材版式静水力曲线图 |
| 稳性 | 大倾角 GZ、IMO 2008 IS Code 2.2 六项衡准、恶劣风浪衡准（2.3） |
| 性能 | 艾亚阻力、Holtrop 推进因子、B 系列螺旋桨设计 |
| 方案空间 | 主尺度比网格扫描、逐级拒绝记录、帕累托前沿 |
| 耐波性 | 书内公式固有周期与谐摇判定；capytaine 零航速 RAO（可选扩展） |
| 失速 | Kwon 方法（蒲福风级、浪向、装载状态） |
| 交付物 | 分层 DXF、图表、中文 Markdown 设计报告 |

样例输出（报告、曲线图、总布置简图、DXF、CSV）已随仓库提交在
[examples/demo_outputs](examples/demo_outputs)——一条命令即可全部再生。

## 快速上手

```bash
git clone https://github.com/5777-wq/OpenHull.git
cd OpenHull
uv sync                        # 或：pip install -e .
uv run openhull run examples/taskbook_bulk_carrier.yaml
```

出图与报告：

```bash
uv run openhull run examples/taskbook_bulk_carrier.yaml \
  --report design_report.md \
  --hydro-curve-chart curves.png \
  --arrangement-chart ga.png \
  --arrangement-dxf ga.dxf
```

方案扫描与耐波性 RAO：

```bash
uv run openhull optimize examples/taskbook_bulk_carrier.yaml   # 方案扫描 + 帕累托图
uv sync --extra seakeeping                                     # 可选 capytaine 扩展
uv run openhull rao examples/taskbook_bulk_carrier.yaml        # 零航速 RAO
```

## 交给 AI 智能体

OpenHull 就是为智能体编排设计的。把下面这句话发给任何支持技能的
AI 智能体，它会自己安装工具、写好任务书、跑完整条设计链：

> 请安装并使用 OpenHull 技能
> （https://github.com/5777-wq/OpenHull/tree/main/skills/openhull），
> 然后帮我设计一条 5 万吨散货船，服务航速 14.5 节，出设计报告和
> 总布置简图。

技能包位于 [`skills/openhull/`](skills/openhull/SKILL.md)，内含最小
任务书模板；能读取 SKILL.md 的智能体只用这一个网址就能自助安装。

## 工程纪律

1. **白名单先行。** 经验公式只有在 [AGENTS.md §5](AGENTS.md) 列明来源
   后才允许实现——先改白名单、后写代码，转录内容对照原书页面影像核对。
2. **验收靠数字。** 书上算例、独立路径互检、公开基准船数据钉住每一个
   功能——359 个测试（未装可选耐波性扩展时个别用例自动跳过），逐条
   记录在 [VALIDATION.md](VALIDATION.md)。
3. **声明式近似。** 直壁甲板、阻尼区间、被约束的自由度：在所在模块的
   文档里如实写明。
4. **工具报告，工程师拍板。** 谐摇区或某条衡准是否否决一个方案，属于
   船舶工程师的专业判断——工具只报告，不替你决定。

## 验证亮点

| 锚点 | 一致性 |
|---|---|
| NMRI JBC 基准船 | 排水体积、Cb、Cm、LCB 复现 |
| DTMB 1712 报告（Series 60） | 按公开轴功率复算航速 ±0.32 kn |
| NMRI MP687 实测敞水数据 | B 系列 ηo 平均偏差 2.8 % |
| 书内算例（《船舶原理》下册） | 螺旋桨终局设计差 0.07 kn；横摇周期恒等式精确 |
| 面板网格 vs 站面积分 | 排水体积差 0.1 % |
| KCS 失速（公开对比） | 速比 f_w 差 0.01 以内 |

## 文档

- [文档站](https://5777-wq.github.io/OpenHull/)——中文快速上手与方法来源，
  英文参考页自动组装
- [官网主页](https://5777-wq.github.io/openhull-site/)——中文项目门户
- [VALIDATION.md](VALIDATION.md)——完整验收记录（22 条，逐条含数字）
- [CHANGELOG.md](CHANGELOG.md)——版本历史

## 参与贡献

提 PR 前请先读 [CONTRIBUTING.md](CONTRIBUTING.md)：公式来源走白名单
流程、转录必须对照来源页面核验、验收必须带数字。Bug 报告与公式来源
提案都有专门的 Issue 模板。

## 许可证

[MIT](LICENSE)

## 引用

若 OpenHull 对你的研究有帮助，请通过 [CITATION.cff](CITATION.cff) 引用：

```bibtex
@software{openhull,
  author       = {5777-wq},
  title        = {OpenHull: agent-orchestrated parametric ship
                  preliminary design},
  version      = {1.0.0},
  year         = {2026},
  url          = {https://github.com/5777-wq/OpenHull}
}
```
