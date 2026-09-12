"""Draw the 116.6m real ship three-view lines plan from the extracted
tabulated offsets (table116.json), including deck lines, superstructure
deck and bulwark, and the four longitudinal (profile) lines.

Layout follows the real drawing (owner's CAD screenshots):
  body plan upper left  : sections 0-6 aft left, 13-20 fwd right,
                          deck/superstructure/bulwark widths per station
  sheer view upper right: deck side/centre lines (sheer), 4 longitudinals
  plan bottom           : waterlines incl. above-DWL dashed + deck edge
                          line in plan view
"""
import json

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

table = json.load(open(r"D:/OpenHull/内部文档/tmp_r7/table116.json",
                       encoding="utf-8"))
pr = json.load(open(r"D:/OpenHull/内部文档/tmp_r7/principals_116.json",
                    encoding="utf-8"))
LPP = pr["lpp_m"]
BEAM = pr["beam_m"]
half = BEAM / 2.0

STATIONS = sorted(int(k) for k in table)
xs = np.array([st * pr["station_spacing_m"] for st in STATIONS])

WL = ["船底线", "1000WL", "2000WL", "3000WL", "4000WL", "5000WL",
      "6000WL", "7000WL", "8000WL"]
WL_H = np.arange(len(WL), dtype=float)          # 0..8 m
DECK_COLS = ["主甲板宽", "船楼甲板宽", "舷墙宽"]
DECK_H = ["主甲边高", "楼甲边高", "舷墙高"]      # per-station heights
DECK_MID = {"主甲板宽": "主甲中高", "船楼甲板宽": "楼甲中高"}

fig = plt.figure(figsize=(15.0, 8.6), dpi=300, facecolor="white")
gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.9],
                      height_ratios=[1.15, 1.0],
                      left=0.06, right=0.985, top=0.92, bottom=0.07,
                      wspace=0.16, hspace=0.24)
ax_body = fig.add_subplot(gs[0, 0])
ax_sheer = fig.add_subplot(gs[0, 1])
ax_plan = fig.add_subplot(gs[1, 1])
ax_note = fig.add_subplot(gs[1, 0])

for ax in (ax_body, ax_sheer, ax_plan):
    ax.set_facecolor("white")
    ax.grid(True, color="0.87", linewidth=0.4, linestyle="--")
    for spine in ax.spines.values():
        spine.set_color("black")
        spine.set_linewidth(0.7)
    ax.tick_params(colors="black", labelsize=7, length=2.5)

z_max_all = 0.0

# ---- body plan: sections with deck/superstructure/bulwark points ----
for st in STATIONS:
    row = table[str(st)]
    xst = st * pr["station_spacing_m"]
    z = [0.0] + WL_H[1:].tolist()
    y = [row.get("船底线", np.nan)]
    y += [row.get(w, np.nan) for w in WL[1:]]
    for col, hcol in zip(DECK_COLS, DECK_H):
        z.append(row.get(hcol, np.nan) / 1000.0)   # mm -> m
        y.append(row.get(col, np.nan) / 1000.0)    # mm -> m
    z = np.array(z, dtype=float)
    y = np.array(y, dtype=float) / 1000.0        # mm -> m
    ok = ~np.isnan(y)
    z, y = z[ok], y[ok]
    z_max_all = max(z_max_all, z.max() if z.size else 0.0)
    side = 1.0 if xst >= LPP / 2 else -1.0
    ax_body.plot(side * y, z, color="black", linewidth=0.8)
ax_body.axhline(pr["design_draft_m"], color="black", linewidth=1.1)
ax_body.annotate("DWL 7.0 m", (-half * 1.0, pr["design_draft_m"]),
                 xytext=(2, 2), textcoords="offset points", fontsize=6.5,
                 color="black", ha="left")
for h in range(1, 9):
    ax_body.axhline(h, color="0.78", linewidth=0.35, linestyle=":")
ax_body.axhline(0.0, color="black", linewidth=0.7)
ax_body.set_aspect("equal")
ax_body.set_xlim(-half * 1.10, half * 1.10)
ax_body.set_ylim(-0.8, 14.5)
ax_body.set_title("Body plan  (fore right / aft left)",
                  fontsize=9.5, color="black", pad=4)
ax_body.set_xlabel("half breadth (m)", fontsize=8)
ax_body.set_ylabel("height above keel (m)", fontsize=8)

# ---- deck lines (plan + sheer) ----
deck_x = xs
deck_side = np.array([table[str(st)]["主甲板宽"] for st in STATIONS]) / 1000.0
deck_side_z = np.array([table[str(st)]["主甲边高"] for st in STATIONS])
deck_mid_z = np.array([table[str(st)]["主甲中高"] for st in STATIONS])
sup_side = np.array([table[str(st)].get("船楼甲板宽", np.nan)
                     for st in STATIONS]) / 1000.0
sup_side_z = np.array([table[str(st)].get("楼甲边高", np.nan)
                       for st in STATIONS])

# ---- sheer view ----
ax_sheer.plot(deck_x, deck_side_z, color="black", linewidth=1.2,
              label="main deck side line")
ax_sheer.plot(deck_x, deck_mid_z, color="black", linewidth=0.9,
              linestyle=(0, (4, 2)), label="main deck centreline")
ok = ~np.isnan(sup_side)
ax_sheer.plot(deck_x[ok], sup_side_z[ok], color="black", linewidth=1.0,
              label="superstructure deck side")
ax_sheer.axhline(pr["design_draft_m"], color="black", linewidth=1.0)
ax_sheer.annotate("DWL", (0.35 * LPP, pr["design_draft_m"]),
                  xytext=(0, 3), textcoords="offset points",
                  fontsize=6.5, color="black", ha="center")
# longitudinals: height of hull surface at offset = 1/3/5/7 m per station
wl_heights = dict(zip(WL, WL_H))
for b, ls in ((1.0, (0, (5, 2))), (3.0, (0, (2, 1.5))),
              (5.0, (0, (7, 2, 1, 2))), (7.0, (0, (4, 1.5, 1, 1.5)))):
    zs = []
    for st in STATIONS:
        row = table[str(st)]
        col = f"{int(b * 1000)}纵剖线"
        v = row.get(col, np.nan)
        zs.append(v / 1000.0 if v is not None and not np.isnan(v)
                  else np.nan)
    zs = np.array(zs, dtype=float)
    ok = ~np.isnan(zs)
    if ok.sum() >= 2:
        ax_sheer.plot(xs[ok], zs[ok], color="black", linewidth=0.8,
                      linestyle=ls)
        ax_sheer.annotate(f"{int(b)}L", (xs[ok][-1], zs[ok][-1]),
                          xytext=(4, 0), textcoords="offset points",
                          fontsize=6.5, color="black")
ax_sheer.set_xlim(-LPP * 0.02, LPP * 1.06)
ax_sheer.set_ylim(-0.8, 14.0)
ax_sheer.set_title("Sheer view  (longitudinals 1/3/5/7 m)",
                   fontsize=9.5, color="black", pad=4)
ax_sheer.set_xlabel("x from AP (m)", fontsize=8)
ax_sheer.set_ylabel("height above keel (m)", fontsize=8)
ax_sheer.legend(fontsize=6.5, loc="lower right", framealpha=0.9)

# ---- half-breadth plan ----
for k, w in enumerate(WL[1:], start=1):
    ys = np.array([table[str(st)].get(w, np.nan) for st in STATIONS]) \
        / 1000.0
    ok = ~np.isnan(ys)
    dashed = WL_H[k] > pr["design_draft_m"]
    ax_plan.plot(xs[ok], ys[ok], color="black",
                 linewidth=0.9 if not dashed else 0.6,
                 linestyle="-" if not dashed else (0, (3, 2)))
    if ok.any():
        ax_plan.annotate(w, (xs[ok][-1], ys[ok][-1]), xytext=(4, 0),
                         textcoords="offset points", fontsize=6.5,
                         color="black")
ax_plan.plot(deck_x, deck_side, color="black", linewidth=1.3,
             label="main deck edge (plan)")
ax_plan.axhline(half, color="black", linewidth=0.5)
ax_plan.set_xlim(-LPP * 0.02, LPP * 1.08)
ax_plan.set_ylim(-half * 0.14, half * 1.15)
ax_plan.set_title("Half-breadth plan  (waterlines, station 0 = AP)",
                  fontsize=9.5, color="black", pad=4)
ax_plan.set_xlabel("x from AP (m)", fontsize=8)
ax_plan.set_ylabel("half breadth (m)", fontsize=8)
ax_plan.legend(fontsize=6.5, loc="lower left", framealpha=0.9)

# ---- notes ----
ax_note.axis("off")
ax_note.set_xlim(0, 1)
ax_note.set_ylim(0, 1)
for k, line in enumerate((
        f"116.6 m coastal cargo  -  Lpp {LPP:.1f} / B {BEAM:.1f} / "
        f"D {pr['depth_m']:.2f} / T {pr['design_draft_m']:.2f} m",
        "Station 0 = AP, spacing 5.40 m; station 20 = FP.",
        "Dimensions in metres, moulded surface; deck/superstructure/"
        "bulwark lines from the offset table.",
        "Axes scales differ between views.")):
    ax_note.annotate(line, (0.03, 0.90 - 0.13 * k), fontsize=7.5,
                     color="black", ha="left", va="top")

fig.suptitle("116.6 m coastal cargo ship  -  lines plan rebuilt from "
             "the owner's offset table", fontsize=11, color="black",
             y=0.975)
out = r"D:/OpenHull/内部文档/tmp_r7/lines_116_real.png"
fig.savefig(out, dpi=300, facecolor="white")
plt.close(fig)
print("saved", out)
