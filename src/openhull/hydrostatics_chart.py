"""Hydrostatic curves chart (plan task 4.1).

A DATA chart of the computed hydrostatic table: every curve plots
numbers already produced by `hydrostatics_table` (plan task 1.4) —
no new formulas, nothing here can change a result.  The no-drawing
red line (AGENTS.md section 7) concerns hull-geometry deliverables
(those stay offsets tables + layered DXF); this is the classic
hydrostatic-curves chart a naval architect reads like a graph, in
the textbook layout: draft on the vertical axis, increasing
DOWNWARD (keel-side waterlines first), one panel per quantity.

Twelve panels in textbook order: displacement volume and mass, KB,
BMT, KM (KB + BMT), BML, TPC, MTC, LCB, LCF, and the form
coefficients Cb and Cw.  Units per AGENTS.md section 1.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["write_hydrostatic_curves_chart"]

#: panels in plot order: (attribute, label, unit)
_PANELS: tuple[tuple[str, str, str], ...] = (
    ("displacement_volume", "displacement volume", "m3"),
    ("displacement", "displacement", "t"),
    ("kb", "KB", "m"),
    ("bmt", "BMT", "m"),
    ("km", "KM = KB + BMT", "m"),
    ("bml", "BML", "m"),
    ("tpc", "TPC", "t/cm"),
    ("mtc", "MTC", "t*m/cm"),
    ("lcb", "LCB", "%Lpp (+ fwd)"),
    ("lcf", "LCF", "%Lpp (+ fwd)"),
    ("cb", "Cb", "-"),
    ("cw", "Cw", "-"),
)


def write_hydrostatic_curves_chart(hydro_table, path, title: str = "") -> Path:
    """Render the hydrostatic curves chart, textbook layout.

    Args:
        hydro_table: a `HydrostaticsTable` (task 1.4) with at least
            two drafts; the chart interpolates nothing — it draws
            the tabulated points connected, exactly the table.
        path: output image path (extension selects the format,
            e.g. .png).
        title: optional heading (e.g. the task-book id and ship).

    Returns:
        The resolved path written.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    entries = hydro_table.entries
    drafts = [e.draft for e in entries]

    n_rows, n_cols = 4, 3
    fig, axes = plt.subplots(
        n_rows, n_cols, figsize=(12.5, 11.0), dpi=150, sharey=True)
    fig.subplots_adjust(
        left=0.065, right=0.985, bottom=0.045, top=0.925,
        wspace=0.30, hspace=0.24)

    for ax, (attr, label, unit) in zip(axes.flat, _PANELS):
        values = [float(getattr(entry, attr)) for entry in entries]
        ax.plot(values, drafts, color="#1a3d6d", linewidth=1.8,
                marker="o", markersize=3.2)
        ax.set_title(f"{label}  [{unit}]", fontsize=10)
        ax.grid(True, linewidth=0.4, alpha=0.5)
        ax.tick_params(labelsize=8.5)
        # textbook layout: draft grows DOWNWARD (T=0 keel side on top).
        # Explicit inverted limits — invert_yaxis() is unreliable on
        # shared axes once autoscale has fixed the view.
        ax.set_ylim(max(drafts), min(drafts))
        ax.xaxis.set_major_locator(
            matplotlib.ticker.MaxNLocator(6))

    for ax in axes[:, 0]:
        ax.set_ylabel("draft T (m)", fontsize=9)

    fig.suptitle(
        (title + " — " if title else "") + "hydrostatic curves",
        fontsize=13, fontweight="bold")
    out = Path(path)
    fig.savefig(out)
    plt.close(fig)
    return out
