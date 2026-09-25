"""Preliminary design report generation (plan task 4.3).

Assembles the run summary dict (the same object the CLI prints) into
a Markdown design report in Chinese — the owner reads Chinese, the
code stays English per AGENTS.md conventions.  The report only
RESTATES computed results and their whitelist citations: it adds no
numbers of its own.  Every section degrades gracefully when a block
was skipped (e.g. the propeller design at task-book speeds outside
the Ayre band).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

__all__ = ["write_report_md"]


def _fmt(value, digits: int = 3) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _section_propeller(prop: dict | None, summary: dict) -> list[str]:
    """Propeller block in three distinct states: not requested,
    refused (with a structured Chinese explanation), or a result."""
    lines = []
    if prop is None:
        lines += [
            "- 本任务书未提供 `propeller:` 块（转速、叶数、盘面比），"
            "**未请求**螺旋桨初步设计。",
            "- 如需功率与桨参数，在任务书加 `propeller: {rpm: 转速, "
            "blades_z: 叶数, expanded_area_ratio: 盘面比}` 后重跑。",
            "",
        ]
        return lines
    if prop.get("skipped"):
        stage = prop.get("stage", "unknown")
        reason = str(prop.get("reason", ""))
        reason_first = " ".join(reason.split())[:400]
        lines += ["- **本方案未能给出所需航速对应的功率。**", ""]
        stage_cn = {
            "ayre": "艾亚阻力估算（ayre）",
            "propeller": "B 系列螺旋桨设计（propeller）",
        }.get(stage, stage)
        lines.append(f"- 拒绝阶段：{stage_cn}")
        lpp = summary.get("lpp_m")
        disp = summary.get("displacement_t")
        if lpp and disp:
            # the Ayre length ratio uses the displacement in TONNES
            # directly (the book's own worked example: L 122 m,
            # Delta 11,970 t -> L/Delta^(1/3) = 5.33)
            ratio = lpp / disp ** (1.0 / 3.0)
            lines.append(
                f"- 生效主尺度：Lpp {lpp:.1f} m / Δ {disp:,.0f} t → "
                f"L/Δ^(1/3) = {ratio:.2f}（艾亚法惯例，Δ 以吨计）")
        lines.append(f"- 工具原文（保留可溯源）：")
        lines.append("")
        lines.append(f"  > {reason_first}")
        lines.append("")
        if stage == "ayre":
            lines += [
                "- 可能原因：服务航速落在艾亚法速度-长度带 "
                "V/√L ∈ [0.50, 1.20] kn/√ft 之外，或 L/Δ^(1/3) 落在已"
                "数字化谱系带 [4.88, 6.41] 之外（图 7-3 目前只录入了"
                "中间谱系）。",
                "- 可行方向：调整 Cb 或主尺度比（L/B、B/T）使本船进入"
                "上述带内；或等待 C₀ 图谱全谱系补录（数据 backlog）。",
            ]
        elif stage == "propeller":
            lines += [
                "- 可能原因：B 系列包线（叶数/盘面比/进速系数域）、"
                "梢隙约束（D ≤ 0.75 T）或 ηo 合理域未能同时满足。",
                "- 可行方向：放宽盘面比/叶数、加大设计吃水以获得桨径"
                "空间，或调整转速。",
            ]
        lines += [
            "- 说明：白名单方法的适用域由项目章程锁定，工具拒绝在域外"
            "给出数字（拒绝优于外推）。是否调整设计需求属于专业判断，"
            "工具不替用户拍板。",
            "- 可行域扫描：`openhull optimize <任务书> --grid-cb "
            "下限:上限:档数` 可自动扫出哪些组合能进入各适用带（例如 "
            "`--grid-cb 0.70:0.84:8`），不必逐点手试（review 2026-09-25 "
            "P1-2）。",
            "",
        ]
        return lines
    lines += [
        f"- 型号系列：B 系列（Bernitsas 报告 237 转录，三重裁判验证）",
        f"- 桨径 D = {_fmt(prop.get('diameter_m'), 3)} m，"
        f"螺距比 P/D = {_fmt(prop.get('pitch_ratio'), 4)}，"
        f"叶数 Z = {_fmt(prop.get('blades_z'), 0)}",
        f"- 敞水效率 ηo = {_fmt(prop.get('eta_open_water'), 4)}，"
        f"进速系数 J = {_fmt(prop.get('advance_coefficient'), 4)}",
        f"- 收到功率 = {_fmt(prop.get('delivered_power_kw'), 1)} kW，"
        f"推力 = {_fmt(prop.get('thrust_n'), 0)} N",
    ]
    sens = prop.get("resistance_sensitivity")
    if sens and sens.get("in_c0_peak_zone"):
        corridor = " / ".join(
            f"{v} kn: {ac}" for v, ac in (sens.get("admiralty_corridor") or {})
            .items())
        lines.append(
            f"- ⚠ 方法敏感性（P0-1）：本运行点位于已数字化 C₀ 族的**峰区**"
            f"（族峰值 V/√L ≈ {_fmt(sens.get('c0_family_peak_v_sqrt_l'), 2)}，"
            f"本点 {_fmt(sens.get('v_sqrt_l'), 3)}，局部斜率 "
            f"{_fmt(sens.get('c0_local_slope_pct_per_0p05'), 1)}%/0.05）——"
            f"峰区内 C₀ 对航速的局部变化会抵消或放大 V³ 增长，**单点功率"
            f"不宜直接用于主机选型**；参考海军部系数 Ac = Δ^(2/3)·V³/PE "
            f"走廊：{corridor}。建议以航速扫描查看趋势并对绝对水平留出"
            f"裕度（本工具尚未接入第二种阻力法交叉复核；诊断只加文字、"
            f"不改任何数值）。")
    cav = prop.get("cavitation")
    if cav is not None:
        verdict = "满足" if cav.get("ok") else "**不满足（盘面比短缺）**"
        lines.append(
            f"- Burrill 空泡校核：σ0.7R {_fmt(cav.get('sigma_0_7r'), 3)}，"
            f"{verdict}；安装盘面比 {_fmt(cav.get('aeao_available'), 3)} vs "
            f"所需 {_fmt(cav.get('aeao_required'), 3)}")
    elif prop.get("cavitation_note"):
        # P0-2 (review 2026-09-25): "declaratively skipped" reads like
        # a pass — the truth is UNCHECKED, and the low side of the band
        # is the higher-risk direction that most needs human review
        unchecked = prop.get("cavitation_unchecked") or {}
        sigma = unchecked.get("sigma_0_7r")
        band = unchecked.get("band") or [None, None]
        side = ("**低侧**——空泡风险更高的一侧，最需要人工复核"
                if unchecked.get("side") == "low"
                else "高侧——偏保守方向")
        lines.append(
            f"- ⚠ **Burrill 空泡校核：未校核（非通过）**：σ0.7R = "
            f"{_fmt(sigma, 3)} 落在已验证带 [{_fmt(band[0], 3)}, "
            f"{_fmt(band[1], 3)}] 外（本方案位于{side}），空泡状态"
            f"**未知**。")
        lines.append(
            f"  - 方向性提示（定性）：把 σ0.7R 拉回带内的常见方向是"
            f"降低转速 n、加大盘面比 AE/A0、增大轴系浸深 h（三者都使 "
            f"σ 上升）；请结合总布置与主机选型复核。")
        full_note = " ".join(str(prop["cavitation_note"]).split())
        lines.append(f"  - 工具原文（保留可溯源，不截断）：{full_note}")
    lines.append("")
    return lines


def _section_seakeeping(sk: dict | None) -> list[str]:
    if not sk:
        return ["- 未运行（任务书缺 KG 时跳过）。", ""]
    lines = [
        f"- 横摇固有周期 {_fmt(sk['roll_period_s'], 2)} s"
        f"（简式 {_fmt(sk['roll_period_simple_s'], 2)} s）、"
        f"纵摇 {_fmt(sk['pitch_period_s'], 2)} s、"
        f"垂荡 {_fmt(sk['heave_period_s'], 2)} s",
        f"- 有效波倾系数 K = {_fmt(sk['effective_wave_slope_k'], 3)}；"
        f"谐摇放大因数 1/(2μ) = {_fmt(sk['roll_amplification_resonant'], 1)}"
        f"（μ = {_fmt(sk['roll_mu'], 2)}，书内区间中值假定）",
        "",
        "| 运动 | 海区 | 波浪周期 | 调谐因数 Λ | 判定 |",
        "|---|---|---|---|---|",
    ]
    for check in sk["resonance_checks"]:
        verdict = "**处于谐摇区**" if check["in_resonance_band"] \
            else "区外"
        lines.append(
            f"| {check['motion']} | {check['label']} "
            f"| {check['wave_period_s']:.0f} s "
            f"| {check['tuning_factor']:.2f} | {verdict} |")
    lines += [
        "",
        "> 波浪失速：Kwon 失速法**已在库层实现并通过测试**"
        "（2026-09-23 白名单化），尚未接入 `run` 链——接入需要任务书"
        "提供海况输入（浪向、Beaufort 级等），当前版本**不输出**失速"
        "修正，本报告所有功率均为**静水**值（review 2026-09-25 P1-1）。",
        ""]
    return lines


def write_report_md(summary: dict, path, chart_path: str | None = None,
                    arrangement_summary: dict | None = None) -> Path:
    """Render the summary dict into a Chinese Markdown report."""
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        from importlib.metadata import version as _pkg_version
        tool_version = f"openhull {_pkg_version('openhull')}"
    except Exception:  # pragma: no cover - source checkout without install
        tool_version = "openhull (source checkout)"
    lines += [
        f"# OpenHull 初步设计报告 — {summary['taskbook_id'] or '未命名任务书'}",
        "",
        f"生成时间：{now} ｜ 工具链：{tool_version}",
        "",
        "## 1. 主尺度与重量",
        "",
        f"- 垂线间长 Lpp = {_fmt(summary['lpp_m'], 2)} m，"
        f"型宽 B = {_fmt(summary['beam_m'], 2)} m，"
        f"型深 D = {_fmt(summary['depth_m'], 2)} m，"
        f"设计吃水 T = {_fmt(summary['draft_m'], 2)} m",
        f"- 方形系数 Cb：目标 {_fmt(summary['cb_target'], 4)}，"
        f"实际 {_fmt(summary.get('cb_achieved'), 4)}"
        f"（Lackenby 变换 {summary['transform_passes']} 次收敛）",
        f"- 载重量 DW = {_fmt(summary['deadweight_t'], 1)} t，"
        f"排水量 Δ = {_fmt(summary['displacement_t'], 1)} t，"
        f"空船重量 LW = {_fmt(summary['lightship_t'], 1)} t",
        f"- 载重量比 = {_fmt(summary['deadweight_ratio_achieved'], 4)}",
    ]
    if summary.get("draft_mismatch_m") is not None:
        # direction words, not a signed number: "差 -0.425 m" makes the
        # reader decode a sign while the sentence already holds both
        # drafts (review 2026-09-24, R-3)
        declared = summary.get("draft_declared_m")
        balance = summary["draft_m"]
        side = "高于" if (declared or 0) > balance else "低于"
        lines.append(
            f"- ⚠ 任务书声明吃水 {_fmt(declared, 2)} m 与重量平衡吃水 "
            f"{_fmt(balance, 3)} m 不一致：声明值{side}平衡值 "
            f"{_fmt(abs(summary['draft_mismatch_m']), 3)} m"
            f"——本报告全部结果按**平衡吃水**完成。")
        hint = summary.get("draft_mismatch_hint")
        if hint:
            lo, hi = hint["b_over_t_band"]
            required = hint["required_b_over_t"]
            if hint["within_band"]:
                verdict = (
                    f"在本工具的量纲比守卫带 "
                    f"[{_fmt(lo, 2)}, {_fmt(hi, 2)}] 之内。")
            else:
                below = required < lo
                verdict = (
                    f"**{'低于下限' if below else '高于上限'} "
                    f"{_fmt(lo if below else hi, 2)}** —— 该吃水下本工具的"
                    f"统计比值链无法给出自洽的常规商船船型，不做外推；"
                    f"建议复核声明吃水或载重量。")
            # number first: it is the actionable part; the two limits
            # (one-shot estimate, B/T is not a task-book field) follow,
            # because a number without them invites over-trust
            lines.append(
                f"- 反算提示：按声明吃水 "
                f"{_fmt(summary.get('draft_declared_m'), 2)} m 设计，所需 "
                f"B/T ≈ {_fmt(required, 3)}"
                f"（当前 {_fmt(hint['current_b_over_t'], 3)}），{verdict}")
            lines.append(
                f"  - 口径与限制：保持排水量、Cb 与 L/B 不变（L、B 同步"
                f"缩放）；一次性估算、未计入重量再平衡（按该值实算的吃水"
                f"与声明值仍有同量级残差，实测 0.3–1.3%）；B/T 属算法统计"
                f"参数、任务书无此字段，本工具不自动改动。")
    if summary.get("draft_is_hard"):
        lines.append(
            f"- 任务书以 `draft_is_hard` 把设计吃水锁定为声明值 "
            f"{_fmt(summary.get('draft_declared_m'), 3)} m：保持 L/B 与 "
            f"Cb 不变，B/T 反解为 {_fmt(summary.get('hard_draft_b_over_t'), 4)}"
            f"（{summary.get('hard_draft_iterations')} 次平衡试探收敛到 "
            f"±1 cm）。硬约束模式下不出现吃水不符提示。")
    if summary.get("norman_coefficient") is not None:
        lines.append(f"- 诺曼系数 N = {_fmt(summary['norman_coefficient'], 3)}"
                     f"（重量浮力平衡 {summary['iterations']} 次收敛）")
    lines.append("")

    lines += ["## 2. 静水力表（设计吃水行）", ""]
    hydro = summary["hydrostatics"]
    if hydro:
        design = hydro[-1]
        rows = [
            ("排水体积 ∇", f"{design['displacement_volume_m3']:,.1f}", "m3"),
            ("排水量 Δ", f"{design['displacement_t']:,.1f}", "t"),
            ("水线面积 Aw", f"{design['waterplane_area_m2']:,.1f}", "m2"),
            ("KB", f"{design['kb_m']:.3f}", "m"),
            ("BMT", f"{design['bmt_m']:.3f}", "m"),
            ("KM = KB+BMT", f"{design['km_m']:.3f}", "m"),
            ("TPC", f"{design['tpc_t_per_cm']:.2f}", "t/cm"),
            ("LCB", f"{design['lcb_pct_lpp']:+.4f}", "%Lpp（+中前）"),
            ("LCF", f"{design['lcf_pct_lpp']:+.4f}", "%Lpp（+中前）"),
            ("Cb / Cw", f"{design['cb']:.4f} / {design['cw']:.4f}", "—"),
        ]
        lines += ["| 要素 | 数值 | 单位 |", "|---|---|---|"]
        lines += [f"| {n} | {v} | {u} |" for n, v, u in rows]
        # two deltas live in this report and they are not the same
        # number: §1 closes the weight balance, §2 integrates the hull
        # on its own deepest waterline.  Say so, with the size of the
        # gap, instead of leaving the reader to find it (review
        # 2026-09-24, R-2)
        closed = summary.get("displacement_t")
        integrated = design.get("displacement_t")
        if closed and integrated and abs(integrated - closed) > 1e-6:
            gap = integrated - closed
            lines.append(
                f"> 口径注：本表 Δ = {_fmt(integrated, 1)} t 是船体在自身最深"
                f"水线（{_fmt(design['draft_m'], 3)} m）积分所得；§1 的 "
                f"Δ = {_fmt(closed, 1)} t 是重量平衡的闭合目标，两者相差 "
                f"{_fmt(abs(gap), 1)} t（{abs(gap) / closed * 100:.4f}%），"
                f"源于浮力积分路径与 Lackenby 变换收敛残差，不是两个互相"
                f"矛盾的数。")
        lines += ["",
                  "> 完整静水力表由 `--csv` 输出；本表仅列设计吃水行。", ""]

    criteria = summary.get("stability_criteria")
    lines += ["## 3. 完整稳性（IMO 2008 IS Code 2.2）", ""]
    if criteria:
        lines += ["| 衡准 | 要求 | 实际 | 判定 |", "|---|---|---|---|"]
        for c in criteria["criteria"]:
            lines.append(
                f"| {c['criterion_id']} | {c['required']:.3f} {c['unit']} "
                f"| {c['actual']:.4f} | {'满足' if c['passed'] else '**不满足**'} |")
        lines += [
            "",
            f"GM0 = {_fmt(criteria['gm0_m'], 3)} m（KG "
            f"{_fmt(criteria['kg_m'], 2)} m，自由液面修正 "
            f"{_fmt(criteria['free_surface_correction_m'], 3)} m）；"
            f"总体：{'**全部满足**' if criteria['all_passed'] else '**存在不满足项**'}",
            "",
        ]
    else:
        lines += ["- 任务书未提供 KG，未运行大倾角稳性。", ""]

    weather = summary.get("weather_criterion")
    lines += ["## 4. 恶劣海况稳性（IS Code 2.3）", ""]
    if weather:
        lines += [
            f"- 波浪衡准：面积 a = {_fmt(weather['area_a_mrad'], 4)} vs "
            f"b = {_fmt(weather['area_b_mrad'], 4)} m·rad → "
            f"{'满足' if weather['all_passed'] else '**不满足**'}",
            f"- 横摇固有周期 {_fmt(weather['roll_period_s'], 2)} s、"
            f"横摇角 φ1 = {_fmt(weather['phi1_deg'], 2)}°",
            "",
        ]
    else:
        lines += ["- 任务书未声明受风面积，未运行。", ""]

    lines += ["## 5. 快速性与螺旋桨初步设计", ""]
    lines += _section_propeller(summary.get("propeller_design"),
                               summary)

    lines += ["## 6. 耐波性初估（第一级，书内公式）", ""]
    lines += _section_seakeeping(summary.get("seakeeping"))

    if arrangement_summary:
        lines += ["## 7. 总布置简图（声明式分舱）", "",
                  f"- 分舱来源：{arrangement_summary['source']}；"
                  f"双层底高 {_fmt(arrangement_summary['double_bottom_top_m'], 2)} m",
                  "- 舱室一览：", "",
                  "| 舱室 | 类型 | 纵向范围 (m) | 垂向范围 (m) |",
                  "|---|---|---|---|"]
        for c in arrangement_summary["compartments"]:
            lines.append(
                f"| {c['name']} | {c['kind']} "
                f"| {c['x0_m']:.1f} – {c['x1_m']:.1f} "
                f"| {c['z0_m']:.2f} – {c['z1_m']:.2f} |")
        lines.append("")

    lines += ["## 附：声明", "",
              "- 本报告由 OpenHull 自动生成，全部数字可溯源至"
              " AGENTS.md 第 5 节公式来源白名单或任务书声明值；"
              "所附简图为声明式布局示意，非真实型线。",
              "- 生成参数与中间量见同目录 JSON/CSV 输出。"]

    if chart_path:
        lines += ["", "## 附图：静水力曲线图", "",
                  f"![hydrostatic curves]({Path(chart_path).name})"]

    out = Path(path)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
