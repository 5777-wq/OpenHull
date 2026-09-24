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
uv tool install "git+https://github.com/5777-wq/OpenHull"
# 没有 uv 时：
pip install "git+https://github.com/5777-wq/OpenHull"
```

安装后验证：

```bash
openhull --version        # 应输出 openhull 1.0.0 或更高
```

若依赖下载报镜像站 403（国内镜像偶发），改用官方源：
`UV_DEFAULT_INDEX=https://pypi.org/simple uv tool install "git+https://github.com/5777-wq/OpenHull"`（网络受限时配合代理）。

耐波性 RAO 是可选扩展（capytaine），主流程不需要；需要时：
`uv tool install "git+https://github.com/5777-wq/OpenHull[seakeeping]"`。

## 第二步：拿一份可用的任务书

最快路径：用本技能的模板 `assets/minimal_taskbook.yaml`（5 万吨散货船），
复制到工作目录后按用户需求改数字。任务书**仅四个字段必需**：

```yaml
schema_version: 1
taskbook_id: MIN-50000
ship_type: bulk_carrier          # bulk_carrier / tanker / container …
requirements:
  deadweight_t: 50000            # 载重量
  service_speed_kn: 14.5         # 服务航速
  kg_m: 9.0                      # 可选：装载重心高，填了才有稳性/耐波性
  drafts:
    design_draft_m: 11.8         # 设计吃水
constraints:
  block_coefficient_design: 0.82 # 方形系数（方案阶段按母型/统计取值）
```

可选块（详见仓库 `examples/taskbook_bulk_carrier.yaml`）：`propeller:`
（螺旋桨：叶数/盘面比/转速/轴浸深）、`stability.weather_criterion:`（受风
面积等）、`arrangement:`（总布置分舱表）。

**航速-长度带提醒**：艾亚阻力法仅在 V/√L ≈ 0.50–1.20 kn/√ft 有效。若用户
给的航速对此船偏低（大船低速常见），`run` 的螺旋桨块会声明式跳过——如实
转述跳过原因，不要换方法硬凑。

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
  （PASS/FAIL）→ 恶劣海况 → 螺旋桨 → 耐波性（谐摇判定）；
- 出现"声明式跳过/拒绝"时，原样转述原因（例如"航速低于艾亚法速度带"），
  并说明这是白名单纪律——工具宁可拒绝也不给不可信的数；
- 生成的 `design_report.md` 是中文报告，可直接交付给用户；
- 方案扫描的结论应连同"逐级拒绝直方图"一起讲：被拒的每一点都有阶段和
  原因记录（零外推）。

## 常见追问的答法

- "这个数靠谱吗？" → 指路验证记录：公开基准船（JBC / DTMB 1712 /
  NMRI MP687）+ 书内算例 + 348 项测试，见仓库 VALIDATION.md；
- "能不能算 XX 船型/XX 衡准？" → 先查仓库 AGENTS.md §5 白名单与 §7 红线：
  白名单外的方法不能实现，如实说明并建议走 Issue 提案流程；
- 用户想调参数重跑 → 改任务书 YAML 再跑，不要手改 Python。
