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


def _section_propeller(prop: dict | None) -> list[str]:
    lines = []
    if not prop or prop.get("skipped"):
        reason = prop.get("reason") if prop else "未运行"
        lines += [f"- 螺旋桨设计**声明式跳过**：{reason}", ""]
        return lines
    lines += [
        f"- 型号系列：B 系列（Bernitsas 报告 237 转录，三重裁判验证）",
        f"- 桨径 D = {_fmt(prop.get('diameter_m'), 3)} m，"
        f"螺距比 P/D = {_fmt(prop.get('pitch_ratio'), 4)}，"
        f"叶数 Z = {_fmt(prop.get('blades_z'), 0)}",
        f"- 敞水效率 ηo = {_fmt(prop.get('eta_o'), 4)}，"
        f"进速系数 J = {_fmt(prop.get('advance_coefficient'), 4)}",
        f"- 收到功率 = {_fmt(prop.get('delivered_power_kw'), 1)} kW，"
        f"推力 = {_fmt(prop.get('thrust_n'), 0)} N",
    ]
    if prop.get("cavitation_ok") is not None:
        verdict = "满足" if prop["cavitation_ok"] else "**不满足**"
        lines.append(f"- Burrill 空泡校核：{verdict}"
                     f"（所需盘面比 {_fmt(prop.get('cavitation_aeao_required'), 3)}）")
    elif prop.get("cavitation_aeao_required") is None:
        lines.append("- Burrill 空泡校核：σ 落在已验证带外，声明式跳过")
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
    lines += ["", "> 波浪失速不在本层范围：白名单书内无失速估算公式。", ""]
    return lines


def write_report_md(summary: dict, path, chart_path: str | None = None,
                    arrangement_summary: dict | None = None) -> Path:
    """Render the summary dict into a Chinese Markdown report."""
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines += [
        f"# OpenHull 初步设计报告 — {summary['taskbook_id'] or '未命名任务书'}",
        "",
        f"生成时间：{now} ｜ 工具链版本见 pyproject.toml",
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
    lines += _section_propeller(summary.get("propeller_design"))

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
