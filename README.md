<div align="center">

# OpenHull

**Design the shell that carries it all.**

由 AI 智能体编排的开源参数化船舶初步设计工具链：一份任务书，自动完成
主尺度、静水力、IS Code 稳性、阻力与推进、螺旋桨设计、耐波性、失速
估算、图纸与中文设计报告——**每个数字都溯源到公式白名单**。

[![tests](https://github.com/5777-wq/OpenHull/actions/workflows/tests.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/tests.yml)
[![release](https://img.shields.io/github/v/release/5777-wq/OpenHull)](https://github.com/5777-wq/OpenHull/releases)
[![license](https://img.shields.io/github/license/5777-wq/OpenHull)](LICENSE)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![docs](https://img.shields.io/website?url=https%3A%2F%2F5777-wq.github.io%2FOpenHull%2F)](https://5777-wq.github.io/OpenHull/)
[![官网（中文）](https://img.shields.io/badge/%E5%AE%98%E7%BD%91-%E4%B8%AD%E6%96%87-success)](https://5777-wq.github.io/openhull-site/)

**[English](README.en.md)** | 简体中文

</div>

---

## 它做什么

写一份描述需求的**任务书**（YAML），OpenHull 跑完整条初步设计链，产出：

| 环节 | 交付物 |
|---|---|
| 主尺度与重量 | 诺曼系数迭代的重量浮力平衡、载重量比法估算 |
| 船型 | 数字化 Series 60 母型 + Lackenby 变换，真实型值表 |
| 静水力 | 静水力表、邦戎曲线、教材版式静水力曲线图 |
| 稳性 | 大倾角 GZ、IMO 2008 IS Code 2.2 六项衡准 + 恶劣风浪衡准 2.3 |
| 性能 | 艾亚阻力、Holtrop 推进因子、瓦根宁根 B 系列螺旋桨设计 |
| 设计空间 | 主尺度比网格扫描：逐级拒绝记录 + 帕累托前沿 |
| 耐波性 | 书内公式固有周期与谐摇判定；可选 capytaine 零航速 RAO |
| 失速 | Kwon 方法（蒲福风级、浪向、装载状态） |
| 交付物 | 分层 DXF、图表、中文 Markdown 设计报告 |

样例成果（报告、曲线图、总布置图、DXF、CSV）已提交在
[examples/demo_outputs](examples/demo_outputs)——一条命令即可全部重新生成。

## 快速上手

安装命令行工具（锁定发布标签，可复现、可审计）：

```bash
uv tool install "git+https://github.com/5777-wq/OpenHull@v1.4.0"
```

跑通仓库自带的旗舰示例（JBC 基准船锚定的 15 万载重吨级 Capesize
散货船）：

```bash
openhull run examples/taskbook_bulk_carrier.yaml
# 跑全链之前，可先秒级预检 8 道适用域关卡：
openhull check examples/taskbook_bulk_carrier.yaml
```

> 诚实声明：TB-001 是 JBC 在**真实 14.5 kn 服务航速**下的验证船，
> 该点落在艾亚速度带之外（V/√L ≈ 0.48 < 0.50），所以这个示例的
> **功率与螺旋桨段会声明式拒绝**——主尺度、静水力、稳性、
> 总布置照常产出。这是工具"拒绝优于外推"纪律的演示，不是故障。
> 想首次跑通**含螺旋桨的完整链条**，用技能自带的
> `minimal_taskbook.yaml`（45,000 t / 16 kn）。

带图纸与报告：

```bash
openhull run examples/taskbook_bulk_carrier.yaml \
  --report design_report.md \
  --hydro-curve-chart curves.png \
  --arrangement-chart ga.png \
  --arrangement-dxf ga.dxf
```

设计空间扫描与 RAO：

```bash
openhull optimize examples/taskbook_bulk_carrier.yaml   # 扫描 + 帕累托图
openhull rao examples/taskbook_bulk_carrier.yaml        # 零航速 RAO（可选扩展）
```

从源码开发：

```bash
git clone https://github.com/5777-wq/OpenHull.git
cd OpenHull
uv sync                        # 或：pip install -e .
uv run openhull run examples/taskbook_bulk_carrier.yaml
```

## 交给 AI 智能体

OpenHull 就是为智能体编排设计的。把下面这句话发给任何支持技能的
AI 智能体（ZCode、Claude Code 等），它会自己安装工具、写好任务书、
跑完整条设计链：

> 请安装并使用 OpenHull 技能
> （https://github.com/5777-wq/OpenHull/tree/main/skills/openhull），
> 然后帮我设计一条 5 万吨散货船，服务航速 14.5 节，出设计报告和
> 总布置简图。

技能文件在 [`skills/openhull/`](skills/openhull/SKILL.md)，内置最小
任务书模板；任何能读 SKILL.md 的智能体都能凭 URL 自行安装。

## 工程纪律

1. **白名单先行。** 经验公式只有在 [AGENTS.md §5](AGENTS.md) 立账之后
   才能实现——先改章程再改代码，转录对照原书页面核验。
2. **验收靠数字。** 书内算例、独立路径互检、公开基准船钉住每一个功能——
   440 项测试（未装可选扩展时个别用例自动跳过），
   逐条记录见 [VALIDATION.md](VALIDATION.md)。
3. **近似必须声明。** 直壁甲板、阻尼区间、被约束的自由度：假定写在哪里，
   就声明在哪里。
4. **工具报告，工程师拍板。** 谐摇区是否规避、衡准是否否决方案，是船舶
   工程师的专业判断——有意保留给人。

## 验证亮点

| 锚点 | 一致性 |
|---|---|
| NMRI JBC 基准船 | 排水体积 / Cb / Cm / LCB 复现 |
| DTMB 1712 报告（Series 60） | 按公开轴功率复算航速 ±0.32 kn |
| NMRI MP687 实测敞水数据 | B 系列 ηo 平均偏差 2.8 % |
| 书内算例（《船舶原理》下册） | 螺旋桨终局设计差 0.07 kn；横摇周期恒等式精确 |
| 面板网格 vs 站面积分 | 排水体积互差 0.1 % |
| KCS 波浪失速互检（公开对比） | 速比 f_w 0.929 vs 0.932 |
| Holtrop-Mennen 1982 论文算例 | 20 个印刷量全部逐位复现（总阻力 1793.26 kN、有效功率 23063 kW）|

## 文档与链接

- [官网（中文门户）](https://5777-wq.github.io/openhull-site/) — 项目主页
- [文档站](https://5777-wq.github.io/OpenHull/) — 快速上手与方法说明（中文）、参考页（英文）
- [VALIDATION.md](VALIDATION.md) — 完整验收记录，逐条含数字
- [CHANGELOG.md](CHANGELOG.md) — 版本历史

## 参与贡献

提 PR 前请先读 [CONTRIBUTING.md](CONTRIBUTING.md)：公式来源走白名单
流程、转录对照原书页核验、验收必须带数字。缺陷报告与公式来源提案
均有专用 Issue 模板。

## 许可证

[MIT](LICENSE)

## 引用

如果 OpenHull 对你的研究有帮助，请通过 [CITATION.cff](CITATION.cff) 引用：

```bibtex
@software{openhull,
  author       = {5777-wq},
  title        = {OpenHull: agent-orchestrated parametric ship
                  preliminary design},
  version      = {1.4.0},
  year         = {2026},
  url          = {https://github.com/5777-wq/OpenHull}
}
```
