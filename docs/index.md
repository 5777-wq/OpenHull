# OpenHull 文档站

**Design the shell that carries it all.**

开源的、由 AI 智能体编排的参数化船舶初步设计工具链：从一份任务书出发，
自动完成主尺度、静水力、IS Code 稳性、阻力与推进、螺旋桨设计、耐波性、
失速估算、图纸与设计报告——**每一个数字都可溯源到公式白名单**。

> 🌐 English reference pages: [Validation](validation.md) ·
> [Changelog](changelog.md) · [Contributing](contributing.md)
> 🏠 官网主页：[5777-wq.github.io/openhull-site](https://5777-wq.github.io/openhull-site/)
> 📦 代码仓库：[github.com/5777-wq/OpenHull](https://github.com/5777-wq/OpenHull)

## 三步跑通

**① 写任务书** —— 一份 YAML（船型、载重吨、服务航速、航区），参考
仓库里的 [examples/taskbook_bulk_carrier.yaml](https://github.com/5777-wq/OpenHull/blob/main/examples/taskbook_bulk_carrier.yaml)。

**② 跑一条命令** ——

```bash
uv run openhull run examples/taskbook_bulk_carrier.yaml \
  --report design_report.md \
  --hydro-curve-chart curves.png \
  --arrangement-chart ga.png \
  --arrangement-dxf ga.dxf
```

**③ 拿成果** —— 设计报告（中文 Markdown）、静水力曲线图、总布置
简图、分层 DXF；样例输出已随仓库提交在
[examples/demo_outputs](https://github.com/5777-wq/OpenHull/tree/main/examples/demo_outputs)。

## 本站目录

- **[快速上手（中文）](quickstart-zh.md)** —— 安装、五条核心命令逐条讲解
- **[方法与数据来源（中文）](methods-zh.md)** —— 每个模块用的公式、出处、
  验收数字
- **英文参考页**：[Validation record](validation.md) ·
  [Changelog](changelog.md) · [Contributing](contributing.md)

## 当前状态

**v1.1.0**（2026-09-25）——路线图五个阶段全部完成，393 个测试全绿
（外部审查两批 13 条、复验残留 5 条全部修复；声明吃水反算提示；
设计空间扫描的速度单位错已修正，验收数字见 VALIDATION 第 17 条。）
完整验证记录（23 条验收，逐条含数字）见英文
[Validation](validation.md) 页或仓库
[VALIDATION.md](https://github.com/5777-wq/OpenHull/blob/main/VALIDATION.md)。
