---
name: openhull
description: 用 OpenHull 做船舶初步设计。当用户要求做船舶初步设计/方案设计/主尺度/静水力/稳性校核（IMO IS Code）/阻力与推进估算/螺旋桨设计/耐波性/波浪失速/总布置简图/设计报告，或提到 OpenHull、要"设计一条散货船/油船/集装箱船"、要从任务书出设计方案时使用。技能会自动安装 openhull 命令行工具，按项目章程（公式白名单、拒绝式守卫）运行并把结果解释给用户。Use whenever the user mentions OpenHull, ship preliminary design, principal dimensions, hydrostatics, IS Code stability, resistance/propulsion, propeller design, seakeeping, speed loss, general arrangement, or wants a ship designed from a task book.
---

# OpenHull — 船舶初步设计工具链

OpenHull 是开源的参数化船舶初步设计 CLI（`openhull`）。它从一份任务书
（YAML）出发，自动完成：主尺度与重量平衡 → 参数化船型（Series 60 母型 +
Lackenby 变换）→ 静水力 → 大倾角稳性与 IMO IS Code 2.2/2.3 衡准 →
艾亚阻力与 Holtrop 推进因子 → B 系列螺旋桨设计 → 耐波性（书内公式 + 可选
capytaine RAO）→ Kwon 失速估算 → 总布置简图（DXF）→ 中文设计报告。

**核心纪律（解释结果时必须遵守）**：每个数字都溯源到公式白名单；工具遇到
不适用域会"声明式跳过/拒绝"，绝不编数；谐摇区或衡准是否否决方案属于船舶
工程师的专业判断——工具只报告，不替用户拍板。

项目主页：https://5777-wq.github.io/openhull-site/ ·
文档站：https://5777-wq.github.io/OpenHull/ ·
仓库：https://github.com/5777-wq/OpenHull

## 第一步：安装（一条命令）

```bash
UV_DEFAULT_INDEX=https://pypi.org/simple   uv tool install "git+https://github.com/5777-wq/OpenHull@v1.2.0"
# 没有 uv 时：
pip install "git+https://github.com/5777-wq/OpenHull@v1.2.0"
```

**主命令自带官方源覆盖**：`uv tool install` 会按本机配置的镜像源解析
依赖，而部分国内镜像对个别 wheel 返回 403（已在真机复现）；显式指定
官方源可在任何环境一次装成。本机 uv 已默认官方源时可省略该前缀。
网络受限时给 uv 配置代理（`HTTPS_PROXY=http://host:port`）。

**锁定版本安装**（`@v1.2.0`）：可复现、可审计；需要跟踪最新修复时
换成 `@main` 或具体 commit。安装后验证：

```bash
openhull --version        # 应输出 openhull 1.2.0
```

耐波性 RAO 是可选扩展（capytaine），主流程不需要；需要时：
`uv tool install "git+https://github.com/5777-wq/OpenHull[seakeeping]"`。

## 第二步：拿一份可用的任务书

最快路径：用本技能的模板 `assets/minimal_taskbook.yaml`（45,000 t
散货船，16 kn——刻意选在全部适用带之内，首次运行即可跑通含螺旋桨的
完整链条），复制到工作目录后按用户需求改数字。任务书**仅四个字段
必需**：

```yaml
schema_version: 1
taskbook_id: MIN-45000
ship_type: bulk_carrier          # bulk_carrier / tanker / container …
requirements:
  deadweight_t: 45000            # 载重量
  service_speed_kn: 16.0         # 服务航速
  kg_m: 9.5                      # 可选：装载重心高，填了才有稳性/耐波性
  drafts:
    design_draft_m: 11.6         # 设计吃水（声明值；全链按平衡吃水计算）
constraints:
  block_coefficient_design: 0.80 # 方形系数（方案阶段按母型/统计取值）
propeller:                       # 可选：填了才有螺旋桨设计与功率
  blades_z: 4
  expanded_area_ratio: 0.55
  rpm: 100
  shaft_immersion_m: 6.0
```

（上面这段与随技能提供的 `assets/minimal_taskbook.yaml` 一致——刻意选
在全部适用带之内，首次运行即可跑通含螺旋桨的完整链条。）

可选块（详见仓库 `examples/taskbook_bulk_carrier.yaml`）：
`stability.weather_criterion:`（受风面积等）、`arrangement:`（总布置分舱表）。

**适用域关卡表**（任何一项不满足，对应模块声明式拒绝，报告会给出
结构化中文说明；如实转述，不要换方法硬凑）：

| 关卡 | 约束 | 触发时的表现 |
|---|---|---|
| 艾亚速度带 | V/√L ∈ [0.50, 1.20] kn/√ft | 螺旋桨块跳过（stage=ayre） |
| C₀ 谱系带 | L/Δ^(1/3) ∈ [4.88, 6.41]（Δ 以吨计；图 7-3 目前只录入中间谱系） | 螺旋桨块跳过（stage=ayre） |
| B 系列包线 | 叶数 2–7 / 盘面比 0.30–1.05 / P/D 0.50–1.40 | 螺旋桨块跳过（stage=propeller） |
| 梢隙 | 桨径 D ≤ 0.75 T | 螺旋桨块跳过（stage=propeller） |
| ηo 合理域 | 敞水效率 0.40–0.85 | 螺旋桨块跳过（stage=propeller） |
| Burrill 空泡带 | σ0.7R ∈ [0.387, 0.483]（四锚点限界线） | 空泡校核**未校核（非通过）**——不是通过；低侧（σ 偏小）是空泡风险更高方向，报告会给方向提示 |
| C₀ 峰区（方法敏感性，不拒绝） | V/√L 落在数字化 C₀ 族自身峰值 ±0.05~+0.10（族峰值 ≈0.70） | 不拒绝；报告/控制台出敏感性声明：单点功率不宜直接用于主机选型，建议扫描查看趋势（诊断只加文字不改数字） |
| 重量平衡 | 诺曼迭代收敛 | 整轮拒绝（weight_balance） |
| IS Code 衡准 | 六项 + 恶劣风浪 | 稳定段拒绝或整体 FAIL 判定 |

**任务书吃水说明**：全链只用一个设计吃水——重量平衡吃水；任务书里
声明的 `design_draft_m` 若与平衡吃水相差超过 5 cm，报告会显式声明
（"已按平衡吃水完成计算"），不是错误，如实转述即可。

## 第三步：常用命令

```bash
# 完整设计链（终端报告；--json / --csv 可重定向）
openhull run 任务书.yaml

# 一条命令出齐成果物（报告/曲线图/总布置图+DXF）
openhull run 任务书.yaml \
  --report design_report.md \
  --hydro-curve-chart curves.png \
  --arrangement-chart ga.png \
  --arrangement-dxf ga.dxf

# 方案空间扫描（L/B × B/T × Cb 网格 → 可行方案 + 帕累托前沿 + 图）
openhull optimize 任务书.yaml --out optimize_out

# 零航速 RAO（需 [seakeeping] 扩展）
openhull rao 任务书.yaml --periods 6,8,12,16,20
```

## 第四步：把结果讲给用户

- `run` 输出按节解读：主尺度与重量 → 静水力 → GZ 与 IS Code 逐条判定
  （PASS/FAIL）→ 恶劣海况 → 耐波性（谐摇判定）→ **快速性与螺旋桨段**
  （v1.2.0 起 stdout 末尾固定输出：成功给 D/P/D/ηo/功率/空泡状态，
  拒绝给 stage 与一行原因，未请求给"not requested"；空泡出带时显示
  UNCHECKED 而非通过，C₀ 峰区时附敏感性一行）；
- 出现"声明式跳过/拒绝"时，按上方关卡表核对 `stage`（例如
  stage=ayre 常见原因是 L/Δ^(1/3) 落在已数字化谱系带之外），原样转述
  工具给出的原因，并说明这是白名单纪律——工具宁可拒绝也不给不可信的数；
- 生成的 `design_report.md` 是中文报告，可直接交付给用户；
- 方案扫描的结论应连同"逐级拒绝直方图"一起讲：被拒的每一点都有阶段和
  原因记录（零外推）。

## 常见追问的答法

- "能算波浪失速吗？" → Kwon 失速法已在库层实现并通过测试，但**尚未接入 run 链**（需要海况入参：浪向、Beaufort 级）；当前报告所有功率均为**静水**值，如实转述，不要声称已含失速修正；
- "这个数靠谱吗？" → 指路验证记录：公开基准船（JBC / DTMB 1712 /
  NMRI MP687）+ 书内算例 + 全量测试（当前 405 项；未装 seakeeping
  可选扩展时个别用例自动跳过），见仓库 VALIDATION.md；
- "任务书里的 length_waterline_m 影响功率吗？" → 分两处说清：单船
  `run` 一次运行一个水线值（任务书声明了就用声明的，否则 Ayre 标准
  1.025×Lpp，PE 与螺旋桨因子同值）；设计空间扫描的候选船统一用各自
  的 1.025×Lpp——任务书的水线长属于任务书那艘船，不随候选缩放，只喂
  波浪衡准。将来若需按 L_WL/Lpp 比值缩放，属方法学变更需另行审批；

- "任务书里写的设计吃水算不出来怎么办？" → 报告会给出反算提示：按声明
  吃水设计所需的 B/T、当前 B/T、是否落在守卫带 [2.00, 3.50] 之内。
  转述时必须带上提示里的两条限制：①是一次估算，未计入重量再平衡（按
  该值实算的吃水与声明值还差 1% 量级）；② **B/T 是算法的统计参数，
  任务书没有这个字段**——可执行的动作是调整声明吃水/载重量/Cb 后重跑，
  或用 Python API 的 `RatioParameters(b_over_t=...)` 做 what-if（已验证
  可行）。**若用户确实要把船设计到声明吃水**：任务书在
  `requirements.drafts` 下加 `draft_is_hard: true`（v1.1.0 起）——声明
  吃水成为硬约束，程序对 B/T 二分并把平衡吃水收敛到声明值 ±1 cm；
  守卫带够不到的吃水会被拒绝并给出带端点数字，如实转述该拒绝。提示值
  出带时说明该吃水下统计链路不自洽，不要自行外推；
- "能不能算 XX 船型/XX 衡准？" → 先查仓库 AGENTS.md §5 白名单与 §7 红线：
  白名单外的方法不能实现，如实说明并建议走 Issue 提案流程；
- 用户想调参数重跑 → 改任务书 YAML 再跑，不要手改 Python。
