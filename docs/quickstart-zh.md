# 快速上手（中文）

## 安装

需要 Python ≥ 3.11。两种方式任选：

```bash
# 方式一：uv（推荐，自动管理虚拟环境）
git clone https://github.com/5777-wq/OpenHull.git
cd OpenHull
uv sync

# 方式二：pip
pip install -e .
```

耐波性 RAO 功能需要可选扩展（capytaine 波浪计算库）：

```bash
uv sync --extra seakeeping      # 或：pip install -e '.[seakeeping]'
```

## 五条核心命令

### 1. 跑完整设计链

```bash
openhull run examples/taskbook_bulk_carrier.yaml
```

输出：重量浮力平衡（诺曼系数迭代）、主尺度、静水力表、大倾角稳性与
IS Code 六项衡准、恶劣风浪衡准、螺旋桨初步设计、耐波性初估，全部
打印到终端；`--json` / `--csv` 可重定向为文件。

### 2. 出静水力曲线图

```bash
openhull run 任务书.yaml --hydro-curve-chart curves.png
```

教材版式：吃水轴竖直向下，12 个面板（排水量、KB、BMT、KM、BML、
TPC、MTC、LCB、LCF、Cb、Cw）。

### 3. 出总布置简图

```bash
openhull run 任务书.yaml --arrangement-chart ga.png --arrangement-dxf ga.dxf
```

侧视 + 俯视简图与分层 DXF（GA-SIDE / GA-PLAN / GA-DB / GA-LABELS
图层）。分舱默认用内置散货船方案（艉尖舱/机舱/五个货舱/艏尖舱，
双层底高 max(B/20, 1.0 m)），可在任务书 `arrangement:` 块里逐舱覆盖。

### 4. 方案空间扫描

```bash
openhull optimize 任务书.yaml
```

L/B × B/T × Cb 网格逐点跑完整白名单链，输出可行方案集 CSV、
航速-排水量-初稳性权衡图（帕累托前沿高亮）与逐级拒绝直方图。
样例场景：192 个候选 → 64 个可行 → 14 个帕累托最优。

### 5. 耐波性 RAO（可选扩展）

```bash
openhull rao 任务书.yaml --periods 6,8,12,16,20
```

capytaine 势流求解器 + 白名单质量/刚度链：顶浪/横浪的垂荡、横摇、
纵摇运动 RAO 表（JSON 用 `--json`）。

### 6. 速度损失估算

```bash
# 在 Python 里调用（CLI 集成在路线图上）：
from openhull.seakeeping import kwon_speed_loss_percent
pct, ratio = kwon_speed_loss_percent(
    cb=0.65, fr=0.26, bn=6.0, nabla_m3=52030.0,
    direction="head", ship_type="container", loading="normal")
# pct = 4.32 (%), ratio = 0.957 —— Kwon 方法（出处见"方法与数据来源"）
```

## 成果示例

仓库 [examples/demo_outputs](https://github.com/5777-wq/OpenHull/tree/main/examples/demo_outputs)
里有一整套现成输出：中文设计报告、静水力曲线图、总布置简图（PNG+DXF）、
静水力表 CSV，附复现命令。

## 交给 AI 智能体（推荐路径）

不想自己敲命令？把这句话发给任何支持技能的 AI 智能体即可：

> 请安装并使用 OpenHull 技能
> （https://github.com/5777-wq/OpenHull/tree/main/skills/openhull），
> 然后帮我设计一条 5 万吨散货船，服务航速 14.5 节。

智能体会自动完成：安装 CLI（`uv tool install
"git+https://github.com/5777-wq/OpenHull"`）→ 用技能内置模板写任务书
→ 运行设计链 → 把结果（含声明式跳过项）解释给你。技能源码见仓库
`skills/openhull/SKILL.md`。

## 常见问题

**Q：某些衡准显示"声明式跳过"是怎么回事？**
A：工具不编数字。当某模块的适用域覆盖不到当前船（例如航速低于艾亚
法的速度-长度带下限，螺旋桨设计无法进行），输出会如实声明跳过原因，
而不是给一个不可信的数。

**Q：谐摇判定为"处于谐摇区"会否决方案吗？**
A：不会。耐波性结果只报告不设门槛——是否规避谐摇区是船舶工程师的
专业判断，工具的边界由项目章程（AGENTS.md 第 7 节）明确。

**Q：公式可信吗？**
A：每条经验公式实现前必须进入项目白名单（AGENTS.md 第 5 节），转录
内容对照原书/论文页面影像逐条核对；验收全部用书上算例、独立路径
互检或公开基准数据（JBC、DTMB 1712、NMRI MP687），完整记录见
[VALIDATION.md](https://github.com/5777-wq/OpenHull/blob/main/VALIDATION.md)。
