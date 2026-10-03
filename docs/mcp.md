# MCP 服务器（中文）

## 这是什么

MCP（Model Context Protocol，模型上下文协议）是 AI 编程工具之间的
"通用插座"标准：Codex、ZCode、Claude、DeepSeek 等 harness 只要支持
MCP，就能调用同一个服务器暴露的工具，不需要各自改造。

OpenHull 从 v1.7.0 起内置一个 MCP 服务器（`openhull-mcp`）。它**只做
包装、不碰数值内核**——每个工具调用都是在子进程里跑一次经过全量测试
的 `openhull` 命令行，再原样返回其 JSON 输出契约。项目章程
（AGENTS.md §8）早已把这定为面向智能体的正式调用路径。

所有纪律原样生效：公式白名单溯源、拒绝式守卫（不适用域明确拒绝并给
出理由，绝不硬算）、"工具报告，工程师拍板"。

## 安装

需要 Python ≥ 3.11。从 GitHub 安装并带上 MCP 扩展：

```bash
# 方式一：uv tool（推荐，自动管理环境）
uv tool install "git+https://github.com/5777-wq/OpenHull@v1.7.0" --extra mcp

# 方式二：pip
pip install "openhull[mcp] @ git+https://github.com/5777-wq/OpenHull@v1.7.0"
```

装完验证：`where openhull-mcp`（Windows）或 `which openhull-mcp`
（Linux/macOS）能找到命令即可；`openhull --version` 显示 1.7.0。
（`openhull-mcp` 本身没有 `--help`——它启动后直接进入 stdio 服务，
由 harness 负责拉起。）

耐波性 RAO 需要再加 `--extra seakeeping`（capytaine 波浪计算库）。

## 注册到各 harness

服务器类型一律是 **stdio**，命令是 `openhull-mcp`。若 harness 找不到
该命令，先 `where openhull-mcp`（Windows）或 `which openhull-mcp`
（Linux/macOS）拿到绝对路径再填。

### ZCode

用户级（所有项目可用）：编辑 `~/.zcode/cli/config.json`；项目级：编辑
`<项目>/.zcode/config.json`。字段是 `mcp.servers`：

```json
{
  "mcp": {
    "servers": {
      "openhull": {
        "type": "stdio",
        "command": "openhull-mcp"
      }
    }
  }
}
```

注意：ZCode 的 MCP 配置 schema 是严格的（未知字段会导致整条服务器被
丢弃），配置文件里不展开 `${...}` 模板变量——用绝对路径。改完后在
Settings → MCP 里确认状态为 connected。

### Codex CLI

编辑 `~/.codex/config.toml`：

```toml
[mcp_servers.openhull]
command = "openhull-mcp"
args = []
```

### Claude Desktop

编辑 `claude_desktop_config.json`（设置 → 开发者 → 编辑配置）：

```json
{
  "mcpServers": {
    "openhull": {
      "command": "openhull-mcp"
    }
  }
}
```

### 其它 MCP 兼容 harness（DeepSeek 等）

任何支持 MCP 的 harness，找"MCP 服务器 / MCP Servers"设置，粘贴与
Claude Desktop 相同的 JSON（字段名以该 harness 文档为准；stdio +
`openhull-mcp` 这个组合不变）。

## 工具清单

| 工具 | 作用 | 耗时量级 |
|---|---|---|
| `openhull_version` | 版本与可选扩展（seakeeping/mcp）是否可用 | 秒 |
| `openhull_check` | 任务书预检：主尺度 + 守卫带秒级判定 | 秒 |
| `openhull_run` | 完整设计链：主尺度→重量→静水力→IS Code 稳性→阻力推进→螺旋桨→耐波性，出报告/DXF/图 | 分钟 |
| `openhull_optimize` | L/B × B/T × Cb 网格扫描找可行方案 | 分钟级，随网格立方增长 |
| `openhull_rao` | 零速刚体 RAO（需 seakeeping 扩展） | 分钟级，随周期数增长 |

另有一个资源 `openhull://taskbook-template`：JBC 锚定的任务书模板，
每个数量带溯源标签（[NMRI]/[DERIV]/[ASSUMED]）。

## 给智能体的推荐工作流

1. `openhull_version` 先看装了哪些能力；
2. 取 `openhull://taskbook-template`，改数字写自己的任务书（保留溯源
   标注习惯）；
3. `openhull_check` 预检——被预警/拒绝就改任务书，**不要**绕守卫；
4. `openhull_run` 出全链结果与产物（JSON `artifacts` 里是真实存在的
   文件绝对路径），或 `openhull_optimize` 扫描主尺度空间；
5. 需要波浪试验级 RAO 时 `openhull_rao`；
6. 衡准是否否决方案：报告给船舶工程师，由人拍板。

## 工具输出的统一形状

每个工具返回一段 JSON 文本：

```json
{
  "ok": true,
  "exit_code": 0,
  "command": ["check", "taskbook.yaml", "--json"],
  "result": { "…CLI 的 JSON 原样结果…" },
  "stderr_tail": "…尾注/拒绝理由/安装提示…",
  "artifacts": { "design_report.md": "D:\\…\\design_report.md" }
}
```

`artifacts` 只列真实存在的文件；`ok=false` 时 `stderr_tail` 携带原因
（任务书校验错误、守卫拒绝、缺扩展的安装提示等）。

## 已知边界

- MCP 握手默认超时 30 秒：`openhull-mcp` 启动只加载 SDK，秒级即可
  连上；长耗时在**工具调用**阶段，与握手超时无关。
- 默认产物目录是 MCP 服务器进程的当前工作目录下 `openhull_out/`，
  建议调用时显式传绝对路径 `output_dir`。
- 服务器通过 `python -m openhull.cli` 子进程调用 CLI，因此保证与
  `openhull-mcp` 同环境安装的 openhull 版本一致；不要混装多版本。
- Windows 上若客户端不解析 `.exe` 后缀，用绝对路径指向
  `openhull-mcp.exe`。
