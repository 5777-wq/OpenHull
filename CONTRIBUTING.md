# Contributing to OpenHull

（中文版见下方 / Chinese version below）

## The short version

OpenHull is an **agent-orchestrated parametric ship preliminary
design toolchain**. Its defining discipline: **every number is
traceable** — to a whitelisted formula source, to a declared task-book
value, or to a benchmark validation. If a contribution cannot say
where its numbers come from, it does not get merged.

## Ground rules

1. **Formula whitelist first (AGENTS.md section 5).** An empirical
   formula may be implemented ONLY if its source is listed in
   AGENTS.md section 5 — and the whitelist entry is amended BEFORE
   the implementation PR. Propose the source, get owner approval,
   amend the whitelist, then code. A formula without a whitelisted
   source must not be merged.
2. **Page-verify every formula.** Transcriptions are verified against
   rendered images of the physical/PDF source at implementation time
   (no page numbers from memory, no OCR-only reads). The project's
   history includes several print defects caught exactly this way.
3. **Acceptance is numerical (R3).** Every feature lands with tests
   that pin book worked examples, independent-path cross-checks, or
   public benchmark data. "It runs" is not acceptance.
4. **Declared approximations live in the docs.** Anything the code
   assumes (a wall-sided deck, a damping range, a suppressed degree
   of freedom) is stated in the module docstring and VALIDATION.md.
5. **Professional judgement stays human.** Whether to gate a design
   on a criterion is the naval architect's call; the tool reports,
   it does not decide.
6. **No viscous CFD.** Resistance comes from whitelisted empirical
   methods; linear potential-flow seakeeping (capytaine, optional)
   is the sanctioned numerical solver.

## Development setup

```bash
git clone https://github.com/5777-wq/OpenHull.git
cd OpenHull
uv sync                      # or: pip install -e .
uv run pytest                # everything must stay green

# optional seakeeping extra (stage 3.8 layer 2):
uv sync --extra seakeeping   # or: pip install -e '.[seakeeping]'
```

- Python ≥ 3.11, src layout, type annotations on every public
  function, dataclasses validated at construction.
- Third-party runtime deps are deliberately minimal: numpy,
  matplotlib, ezdxf, pyyaml (+ optional capytaine).
- New computational methods should register behind the existing
  strategy/registry pattern with a stable id, whitelist citation and
  applicability range (AGENTS.md section 8).

## Pull requests

- State the whitelisted source (or declare "no new formulas") in the
  description.
- Include the tests that pin the acceptance numbers.
- Update VALIDATION.md for anything a reader would want to reproduce,
  and CHANGELOG.md under [Unreleased].
- Documentation languages: code and primary docs in English; the
  design report and Chinese README serve Chinese-speaking naval
  architects — keep both honest when behaviour changes.

## 提交中文说明（摘要）

OpenHull 的核心纪律是**每个数都可溯源**：经验公式必须先入
AGENTS.md 第 5 节白名单（先改白名单、后写实现），转录必须对照
原书页面影像核对；验收靠书上算例、独立路径互检或公开基准数据
(R3)；声明式近似写进模块文档与 VALIDATION.md；是否按某衡准否决
方案属于船舶工程师的专业判断，工具只报告不拍板；不做粘性 CFD。
开发环境：`uv sync && uv run pytest`，Python ≥ 3.11，公共函数
全类型标注，依赖保持最小集。PR 请注明公式来源（或声明"零新公
式"），附验收测试，并更新 VALIDATION.md 与 CHANGELOG.md。
