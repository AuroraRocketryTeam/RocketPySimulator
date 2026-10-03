"""
Drawing of the SRAD motor geometry for docs/motor_mass_properties.md: the parts built by
tools/motor_mass_properties.py, with the lengths, diameters and stations of the notebook as symbols.

Usage:
    python Atlas/docs/make_motor_geometry_figure.py
writes Atlas/docs/motor_geometry.png (the shape comes from the SRAD v1.0 parameters file).
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon

ATLAS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ATLAS / "tools"))
from motor_mass_properties import build_parts, read_parameters  # noqa: E402

PARAMETERS = ATLAS / "simulation_inputs/propulsion_data/SRAD/v1.0/ATLAS_PARAMETERS_1.0 GRAPHITE.txt"
OUTPUT = Path(__file__).with_name("motor_geometry.png")

p = read_parameters(PARAMETERS)  # mm
parts = build_parts(p)
L_div, L_conv, L_tot = p["L_div"], p["L_conv"], p["L_total"]
L_ring, L_housing, L_cc = p["L_nozzle_ring"], p["nozzle_housing_length"], p["L_cc"]
L_tp, t_tp, L_bulkhead = p["length_tp"], p["tp_thickness"], p["L_bulkhead"]
t_case, t_fillet, t_ring = p["th_casing"], p["th_bulkhead_fillet"], p["th_nozzle_ring"]
D_cc, D_out, D_ext, D_int = p["D_cc"], p["D_cc_outer"], p["D_ext"], p["D_int"]
D_throat, D_exit = p["D_throat"], p["D_exit"]
L_grain, g, n = p["L_single_grain"], p["grains_distance"], int(p["n_grains"])

x_case = L_tot - (L_ring + L_housing)
x_grain = L_tot
x_tp = x_grain + L_tp
x_bh = x_tp + t_tp
x_end = x_case + L_cc
x_last = x_grain + g + (n - 1) * (L_grain + g) + L_grain

NAMES = {
    "nozzle": "ugello (grafite)",
    "nozzle ring": "nozzle ring (alluminio)",
    "casing tube": "case (alluminio)",
    "thermal protection liner": "liner della protezione termica (fenolica)",
    "thermal protection closure": "chiusura della protezione termica (fenolica)",
    "bulkhead": "bulkhead (alluminio)",
    "casing closure": "disco di chiusura del case (alluminio)",
}
COLORS = {"nozzle": "#9a9893", "nozzle ring": "#2a78d6", "casing tube": "#86b6ef",
          "thermal protection liner": "#eda100", "thermal protection closure": "#c98a00",
          "bulkhead": "#184f95", "casing closure": "#5b3fb5"}
GRAIN = "#eb6834"
INK = "#1a1a1a"
DIM = "#c0392b"
STATION = "#2d6a4f"


def draw_parts(ax, k=1.0, halves=(1, -1)):
    """Parts of the motor, radii multiplied by k."""
    for part in parts:
        x = np.linspace(part.x0, part.x1, 300)  # m
        ro, ri = part.r_out(x) * 1000 * k, part.r_in(x) * 1000 * k
        x = x * 1000
        color = GRAIN if part.group == "propellant" else COLORS[part.name]
        for sign in halves:
            outline = np.column_stack((np.r_[x, x[::-1]], sign * np.r_[ro, ri[::-1]]))
            ax.add_patch(Polygon(outline, closed=True, facecolor=color, edgecolor=INK, lw=0.5, alpha=0.85))
    # volumes that the notebook counts in two parts
    for a0, a1, r0, r1 in ((x_case, x_case + L_ring, D_cc / 2 - t_ring, D_cc / 2),
                           (x_bh, x_bh + 2 * t_case, D_cc / 2 - t_fillet, D_cc / 2)):
        for sign in halves:
            y0, y1 = sorted((sign * r0 * k, sign * r1 * k))
            ax.add_patch(plt.Rectangle((a0, y0), a1 - a0, y1 - y0, fill=False, hatch="xxxx", edgecolor=INK, lw=0))
    ax.axhline(0, color="#555555", lw=0.6, ls="-.")


def hdim(ax, x0, x1, y, text, y_from, text_dx=0, outside=False, fs=11):
    """Length between x0 and x1, drawn at height y with extension lines from y_from."""
    for x in (x0, x1):
        ax.plot([x, x], [y_from, y + np.sign(y - y_from) * 2], color=DIM, lw=0.5)
    if outside:
        for x, d in ((x0, -1), (x1, 1)):
            ax.annotate("", xy=(x, y), xytext=(x + d * 9, y),
                        arrowprops=dict(arrowstyle="-|>", color=DIM, lw=0.7, mutation_scale=7))
        ax.plot([x0, x1], [y, y], color=DIM, lw=0.7)
    else:
        ax.annotate("", xy=(x0, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="<|-|>", color=DIM, lw=0.7, mutation_scale=7, shrinkA=0, shrinkB=0))
    ax.text((x0 + x1) / 2 + text_dx, y + 1.5, text, color=DIM, ha="center", va="bottom", fontsize=fs)


def diameter(ax, x, d, text, fs=11):
    """Diameter d drawn across the full section at x, label on its left."""
    ax.annotate("", xy=(x, -d / 2), xytext=(x, d / 2),
                arrowprops=dict(arrowstyle="<|-|>", color=DIM, lw=0.7, mutation_scale=7, shrinkA=0, shrinkB=0))
    ax.text(x - 1.5, d / 2 * 0.4, text, color=DIM, rotation=90, ha="right", va="center", fontsize=fs)


def thickness(ax, x, r0, r1, text, tx, ty, fs=11, ha=None):
    """Radial thickness between r0 and r1 at x, label at (tx, ty)."""
    for r, d in ((r0, -1), (r1, 1)):
        ax.annotate("", xy=(x, r), xytext=(x, r - d * 7),
                    arrowprops=dict(arrowstyle="-|>", color=DIM, lw=0.7, mutation_scale=6))
    ax.annotate(text, xy=(x, (r0 + r1) / 2), xytext=(tx, ty), color=DIM, fontsize=fs, va="center",
                ha=ha or ("left" if tx > x else "right"),
                arrowprops=dict(arrowstyle="-", color=DIM, lw=0.5, shrinkA=1, shrinkB=0))


def station(ax, x, label, y_top, y_bottom, fs=11):
    ax.plot([x, x], [y_bottom, y_top], color=STATION, lw=0.8, ls="--")
    ax.text(x, y_top + 1, label, color=STATION, ha="center", va="bottom", fontsize=fs)


def tidy(ax, title):
    ax.set_aspect("equal")
    ax.set_title(title, loc="center", fontsize=12, fontweight="bold")
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)


fig = plt.figure(figsize=(16, 22))
grid = fig.add_gridspec(4, 2, height_ratios=[1.25, 1.75, 1.6, 1.0], hspace=0.12, wspace=0.05)

# Whole motor, radii x3, parts numbered as in the legend
K = 3
ax = fig.add_subplot(grid[0, :])
draw_parts(ax, k=K)
for x, label in ((0, "$x = 0$"), (x_case, "$x_{case}$"), (x_grain, "$x_{grain}$"), (x_end, "$x_{fine}$")):
    station(ax, x, label, 232, -K * D_out / 2)
hdim(ax, 0, L_tot, 172, "$L_{tot}$", y_from=K * D_cc / 2)
hdim(ax, x_grain, x_tp, 172, "$L_{tp}$  (colonna di grain)", y_from=K * D_cc / 2)
hdim(ax, x_case, x_end, 205, "$L_{cc}$  (case)", y_from=K * D_out / 2)
leaders = [  # number, point on the part (x, r), label x
    (1, (45, 42), 45), (2, (110, 45.5), 120), (3, (750, 48.5), 760), (4, (650, 45.5), 640),
    (8, (450, 34), 450), (5, (x_tp + 1.5, 30), 1185), (7, (x_bh + 3, 12), 1245), (6, (x_end - 8, 37), 1350),
]
for number, (x, r), label_x in leaders:
    ax.annotate(str(number), xy=(x, -K * r), xytext=(label_x, -215), ha="center", va="center", fontsize=11,
                fontweight="bold", bbox=dict(boxstyle="circle,pad=0.25", facecolor="white", edgecolor=INK, lw=0.8),
                arrowprops=dict(arrowstyle="-", color=INK, lw=0.6, shrinkA=0, shrinkB=0))
ax.text(-12, 0, "uscita\nugello", fontsize=11, va="center", ha="right")
ax.text(x_end + 12, 0, "testa", fontsize=11, va="center", ha="left")
ax.set_xlim(-90, x_end + 70)
ax.set_ylim(-235, 250)
tidy(ax, "Motore intero (raggi ingranditi 3 volte)")

# Nozzle end, real proportions
ax = fig.add_subplot(grid[1, :])
draw_parts(ax)
hdim(ax, 0, L_div, 60, "$L_{div}$", y_from=D_exit / 2)
hdim(ax, L_div, L_tot, 60, "$L_{conv}$", y_from=D_cc / 2)
hdim(ax, 0, L_tot, 78, "$L_{tot}$", y_from=62)
hdim(ax, x_case, x_case + L_ring, -62, "$L_{ring}$", y_from=-D_out / 2)
hdim(ax, x_case + L_ring, L_tot, -62, "$L_{housing}$", y_from=-D_out / 2)
hdim(ax, x_grain, x_grain + g, -62, "$g$", y_from=-D_out / 2, outside=True, text_dx=8)
hdim(ax, x_grain + g, x_grain + g + L_grain, -62, "$L_{grain}$", y_from=-D_ext / 2)
hdim(ax, x_grain + g + L_grain, x_grain + 2 * g + L_grain, -62, "$g$", y_from=-D_out / 2, outside=True, text_dx=8)
station(ax, x_case, "$x_{case}$", 92, -50)
station(ax, x_grain, "$x_{grain}$", 92, -50)
diameter(ax, -6, D_exit, "$D_{exit}$")
diameter(ax, L_div, D_throat, "$D_{throat}$")
diameter(ax, 60, D_cc, "$D_{cc}$")
diameter(ax, x_case - 8, D_out, "$D_{cc,est}$")
diameter(ax, 230, D_ext, "$D_{est}$")
diameter(ax, 300, D_int, "$D_{int}$")
thickness(ax, x_case + 15, -D_cc / 2, -(D_cc / 2 - t_ring), "$t_{ring}$", 40, -62)
thickness(ax, 380, D_cc / 2 - t_tp, D_cc / 2, "$t_{tp}$  (liner)", 335, 72)
thickness(ax, 420, D_cc / 2, D_out / 2, "$t_{case}$", 440, 72)
ax.set_xlim(-45, 470)
ax.set_ylim(-78, 104)
tidy(ax, "Estremità dell'ugello (sezione completa, proporzioni reali)")

# Forward end, upper half
ax = fig.add_subplot(grid[2, 0])
draw_parts(ax, halves=(1,))
hdim(ax, x_last, x_tp, 56, "$g$", y_from=D_ext / 2, outside=True, text_dx=-12)
hdim(ax, x_tp, x_bh, 66, "$t_{tp}$", y_from=D_cc / 2, outside=True, text_dx=-12)
hdim(ax, x_bh, x_bh + 2 * t_case, 76, "$2\\,t_{case}$", y_from=D_out / 2, outside=True, text_dx=16)
hdim(ax, x_bh, x_end, 88, "$L_{bulkhead}$", y_from=D_out / 2)
for x, label, y in ((x_tp, "$x_{tp}$", 100), (x_bh, "$x_{bh}$", 108), (x_end, "$x_{fine}$", 100)):
    station(ax, x, label, y, 0)
thickness(ax, x_end - 6, D_cc / 2 - t_fillet, D_cc / 2, "$t_{fillet}$", x_end - 14, 12, ha="left")
ax.text(x_last - 30, 34, f"grain {n}", ha="center", va="center", fontsize=11, color="white", fontweight="bold")
ax.set_xlim(x_end - 85, x_end + 8)
ax.set_ylim(-5, 122)
tidy(ax, "Testa del motore (metà superiore)")

# Legend
ax = fig.add_subplot(grid[2, 1])
ax.axis("off")
handles = [plt.Rectangle((0, 0), 1, 1, facecolor=COLORS[key], edgecolor=INK, alpha=0.85) for key in NAMES]
labels = [f"{i}  {name}" for i, name in enumerate(NAMES.values(), start=1)]
handles.append(plt.Rectangle((0, 0), 1, 1, facecolor=GRAIN, edgecolor=INK, alpha=0.85))
labels.append(f"8  grain 1-{n} (propellente)")
handles.append(plt.Rectangle((0, 0), 1, 1, fill=False, hatch="xxxx", edgecolor=INK))
labels.append("volume contato in due pezzi (come nel notebook)")
legend = ax.legend(handles, labels, loc="center", frameon=False, fontsize=12, title="Legenda", title_fontsize=12)
legend.get_title().set_fontweight("bold")

# Axial coordinates
ax = fig.add_subplot(grid[3, :])
ax.axis("off")
rows = [
    ["$x = 0$", "uscita dell'ugello", "origine dell'asse"],
    ["$x_{case}$", "inizio del case, lato ugello", "$L_{tot} - L_{ring} - L_{housing}$"],
    ["$x_{grain}$", "fine dell'ugello, inizio della colonna di grain", "$L_{tot} = L_{div} + L_{conv}$"],
    ["$x_{tp}$", "fine della colonna di grain, inizio della chiusura TP", "$x_{grain} + L_{tp}$"],
    ["$x_{bh}$", "inizio del bulkhead", "$x_{tp} + t_{tp}$"],
    ["$x_{fine}$", "fine del case, testa del motore", "$x_{case} + L_{cc}$   (= $x_{bh} + L_{bulkhead}$)"],
    ["$L_{tp}$", "lunghezza della colonna di grain", "$n\\,L_{grain} + (n+1)\\,g$"],
]
table = ax.table(cellText=rows, colLabels=["Coordinata", "Posizione", "Formula"],
                 loc="center", cellLoc="left", colWidths=[0.1, 0.45, 0.4])
table.auto_set_font_size(False)
table.set_fontsize(12)
table.scale(1, 2.1)
for (row, _), cell in table.get_celld().items():
    cell.set_edgecolor("#bbbbbb")
    if row == 0:
        cell.set_text_props(fontweight="bold")
        cell.set_facecolor("#eeeeee")
ax.set_title("Coordinate assiali", loc="center", fontsize=12, fontweight="bold")

fig.savefig(OUTPUT, dpi=130, bbox_inches="tight")
print(f"Saved {OUTPUT}")
