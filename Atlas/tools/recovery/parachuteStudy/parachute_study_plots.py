"""
Tables and plots for parachute_study.py.

Reads runs_drogue.csv / runs_main.csv / profiles_drogue.pickle from the study output folder and
writes summary.csv, summary.md, the plots/{png,svg,pdf}/ folders and the LaTeX tables and
numbers used by the report (report/generated/).
"""

import json
import pickle
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator, MaxNLocator
import numpy as np
import pandas as pd

from parachute_study import (
    DROGUE_LINES_CAPACITY,
    EUROC_DROGUE_RANGE,
    EUROC_MAIN_MAX,
    MAIN_DEPLOY_ALTITUDE,
    MAIN_LINES_CAPACITY,
    PROPELLANT_MASS,
)

#-------------------------------------------------------------------------------------------------------- STYLE
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
LIMIT = "#52514e"
LIMIT_FILL = "#1baf7a"

# Categorical order (blue, orange, aqua, yellow, magenta) for series
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
# Ordinal ramps (light -> dark): blue for the drogue delay, orange for the main delay
DROGUE_RAMP = ["#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]
MAIN_RAMP = ["#ec9466", "#e8743d", "#d2581f", "#a84215", "#72290b"]

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": TEXT_SECONDARY,
    "axes.labelcolor": TEXT_PRIMARY,
    "axes.titlesize": 12,
    "axes.titlelocation": "center",
    "axes.titlepad": 12,
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "xtick.color": TEXT_SECONDARY,
    "ytick.color": TEXT_SECONDARY,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8.5,
    "legend.frameon": False,
    "lines.linewidth": 1.8,
    "lines.markersize": 5,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
})

DROGUE_LEGEND = "Apogeo -> piena apertura\ndrogue"
MAIN_LEGEND = "450 m AGL -> piena apertura\nmain"
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- HELPERS
def p01(x):
    return np.nanpercentile(x, 1)


def p99(x):
    return np.nanpercentile(x, 99)


def mean_3sigma(x):
    return np.nanmean(x) + 3 * np.nanstd(x)


STATS = ["mean", "std", p01, p99, "min", "max", mean_3sigma]


def case_order(cases):
    return sorted(cases, key=float)


def case_label(case):
    return f"T = {case} s"


def ramp_colors(cases, ramp):
    index = np.linspace(0, len(ramp) - 1, max(len(cases), 1)).round().astype(int)
    return {case: ramp[i] for case, i in zip(cases, index)}


def numeric_columns(df):
    return [c for c in df.columns if df[c].dtype.kind == "f" and c != "dry_mass_case"]


def grouped_by_mass(df, metrics):
    return df.groupby("dry_mass_case")[metrics].agg(STATS)


def limit_line(ax, value, text, axis="y", side=None):
    if axis == "y" and side == "legend":
        # Label in the legend instead of on the plot (empty text: no legend entry)
        ax.axhline(value, color=LIMIT, linestyle=":", linewidth=1.2, label=text or "_nolegend_")
    elif axis == "y":
        ax.axhline(value, color=LIMIT, linestyle="--", linewidth=1)
        # Label on the inner side of the line, so it never touches the axis frame
        bottom, top = ax.get_ylim()
        above = value < (bottom + top) / 2 if side is None else side == "above"
        ax.annotate(text, xy=(1, value), xycoords=("axes fraction", "data"), xytext=(-4, 4 if above else -4),
                    textcoords="offset points", ha="right", va="bottom" if above else "top",
                    fontsize=8, color=TEXT_SECONDARY)
    else:
        ax.axvline(value, color=LIMIT, linestyle="--", linewidth=1)


FORMATS = ("png", "svg", "pdf")


def save(fig, plots_dir, name, subfolder=""):
    """Save the figure as plots/<format>/<subfolder>/<name>.<format>."""
    for fmt in FORMATS:
        folder = plots_dir / fmt / subfolder
        folder.mkdir(parents=True, exist_ok=True)
        fig.savefig(folder / f"{name}.{fmt}")
    plt.close(fig)
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- PLOTS
def mass_axis(ax, masses):
    """Dry mass on the bottom axis, take-off mass on the top one, ticks on the simulated masses."""
    masses = sorted(masses)
    ax.set_xticks(masses, [f"{m:g}" for m in masses])
    ax.set_xlim(masses[0] - 0.4, masses[-1] + 0.4)
    ax.set_xlabel("Massa a secco (kg)")
    top = ax.secondary_xaxis("top", functions=(lambda m: m + PROPELLANT_MASS, lambda m: m - PROPELLANT_MASS))
    top.set_xticks([m + PROPELLANT_MASS for m in masses], [f"{m + PROPELLANT_MASS:.1f}" for m in masses])
    top.set_xlabel("Massa al decollo (kg)", color=TEXT_SECONDARY, fontsize=9)
    top.tick_params(colors=TEXT_SECONDARY, labelsize=8)


def tight_y(ax, values, limits=(), nbins=10):
    """Y range from the plotted curves (bands included), rounded out to the nearest major tick.

    limits: (value, text) or (value, text, "above"/"below"/"legend") for the label placement.
    A limit line is drawn only if it is close to the curves (within 30% of their span),
    otherwise it is listed as off scale, so it does not squeeze the curves together.
    """
    values = np.asarray(values, dtype=float).ravel()
    values = values[np.isfinite(values)]
    low, high = values.min(), values.max()
    span = high - low
    shown, off_scale = [], []
    for value, text, *side in limits:
        if low - 0.3 * span <= value <= high + 0.3 * span:
            shown.append((value, text, side[0] if side else None))
        else:
            off_scale.append(text)
    low = min([low] + [value for value, _, _ in shown])
    high = max([high] + [value for value, _, _ in shown])

    locator = MaxNLocator(nbins=nbins, steps=[1, 2, 2.5, 5, 10])
    ticks = locator.tick_values(low, high)
    ax.set_ylim(ticks[ticks <= low].max(), ticks[ticks >= high].min())
    ax.yaxis.set_major_locator(MaxNLocator(nbins=nbins, steps=[1, 2, 2.5, 5, 10]))
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.grid(which="minor", color=GRID, linewidth=0.3)

    for value, text, side in shown:
        limit_line(ax, value, text, side=side)
    if off_scale:
        ax.text(0.99, 0.99, "fuori scala: " + "; ".join(off_scale), transform=ax.transAxes,
                ha="right", va="top", fontsize=8, color=TEXT_SECONDARY)


def band(ax, x, grouped, metric, color, label, marker="o", linestyle="-", fill=True):
    """Mean line with markers and a P1-P99 band (fill=False: only the mean). Returns the plotted values."""
    low, mean, high = grouped[(metric, "p01")], grouped[(metric, "mean")], grouped[(metric, "p99")]
    if not fill:
        ax.plot(x, mean, color=color, marker=marker, linestyle=linestyle, label=label)
        return [mean.values]
    ax.fill_between(x, low, high, color=color, alpha=0.15, linewidth=0)
    ax.plot(x, mean, color=color, marker=marker, linestyle=linestyle, label=label)
    return [low.values, mean.values, high.values]


def legend_right(ax, title=None):
    ax.legend(title=title, title_fontsize=8.5, loc="center left", bbox_to_anchor=(1.01, 0.5), alignment="left")


def mass_plot(df, plots_dir, series, ylabel, title, name, limits=()):
    """One or more metrics as a function of the dry mass, all cases pooled."""
    grouped = grouped_by_mass(df, [metric for metric, _ in series])
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    values = []
    for (metric, label), color in zip(series, SERIES_COLORS):
        values += band(ax, grouped.index, grouped, metric, color, label)
    mass_axis(ax, grouped.index)
    tight_y(ax, values, limits)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if len(series) > 1:
        legend_right(ax)
    save(fig, plots_dir, name)


def delay_plot(df, plots_dir, case_column, ramp, legend_title, metric, ylabel, title, name,
               limits=(), reference=None, bands="all"):
    """A metric as a function of the dry mass, one curve per delay case.

    reference = (metric, label): an extra curve that does not depend on the delay (all cases pooled);
    (metric, label, "band"): only the pooled P1-P99 band of the metric, without the mean curve.
    bands = "none": only the mean curves of the delay cases (the reference keeps its P1-P99 band),
    for metrics where the delay effect is smaller than the dispersion and the bands would overlap.
    """
    cases = case_order(df[case_column].unique())
    colors = ramp_colors(cases, ramp)
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    values = []
    for case in cases:
        grouped = grouped_by_mass(df[df[case_column] == case], [metric])
        values += band(ax, grouped.index, grouped, metric, colors[case], case_label(case), fill=bands == "all")
    if reference is not None and reference[2:] == ("band",):
        grouped = grouped_by_mass(df, [reference[0]])
        low, high = grouped[(reference[0], "p01")], grouped[(reference[0], "p99")]
        ax.fill_between(grouped.index, low, high, color=TEXT_SECONDARY, alpha=0.15, linewidth=0, label=reference[1])
        values += [low.values, high.values]
    elif reference is not None:
        grouped = grouped_by_mass(df, [reference[0]])
        values += band(ax, grouped.index, grouped, reference[0], TEXT_SECONDARY, reference[1],
                       marker="s", linestyle="--")
    mass_axis(ax, sorted(df.dry_mass_case.unique()))
    tight_y(ax, values, limits)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    legend_right(ax, legend_title)
    save(fig, plots_dir, name)


def plot_drogue_descent_profile(profiles, plots_dir):
    if not profiles:
        return
    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.axvspan(*EUROC_DROGUE_RANGE, color=LIMIT_FILL, alpha=0.08, linewidth=0)
    for value in EUROC_DROGUE_RANGE:
        ax.axvline(value, color=LIMIT, linestyle="--", linewidth=1)
    masses = sorted({p["dry_mass_case"] for p in profiles})
    bins = np.arange(300, 4500, 100)
    for mass, color in zip(masses, SERIES_COLORS):
        altitude = np.concatenate([p["altitude"] for p in profiles if p["dry_mass_case"] == mass])
        velocity = np.concatenate([p["descent_velocity"] for p in profiles if p["dry_mass_case"] == mass])
        index = np.digitize(altitude, bins)
        centers, mean, low, high = [], [], [], []
        for i in np.unique(index):
            selected = velocity[index == i]
            if len(selected) < 20:
                continue
            centers.append(altitude[index == i].mean())
            mean.append(selected.mean())
            low.append(np.percentile(selected, 1))
            high.append(np.percentile(selected, 99))
        ax.fill_betweenx(centers, low, high, color=color, alpha=0.15, linewidth=0)
        ax.plot(mean, centers, color=color, label=f"{mass:g} kg secco")
    ax.text(np.mean(EUROC_DROGUE_RANGE), 0.98, "EuRoC RQT-0360: 23–46 m/s", transform=ax.get_xaxis_transform(),
            ha="center", va="top", fontsize=8, color=TEXT_SECONDARY)
    ax.set_xlabel("Velocità di discesa (m/s)")
    ax.set_ylabel("Quota AGL (m)")
    ax.set_title("Drogue: velocità di discesa lungo la quota")
    ax.set_xlim(20, 48)
    ax.legend(loc="lower right")
    save(fig, plots_dir, "drogue_descent_profile", "extra")


def plot_delay_check(df, plots_dir):
    cases = case_order(df.delay_case.unique())
    colors = ramp_colors(cases, DROGUE_RAMP)
    fig, ax = plt.subplots(figsize=(7, 4))
    for case in cases:
        values = df.loc[df.delay_case == case, "drogue_delay_from_apogee"]
        ax.hist(values, bins=40, color=colors[case], alpha=0.8, label=case_label(case))
    ax.set_xlabel("Tempo effettivo apogeo -> piena apertura drogue (s)")
    ax.set_ylabel("Numero di voli")
    ax.set_title("Verifica: ritardo drogue simulato")
    ax.legend(loc="upper right")
    save(fig, plots_dir, "check_drogue_delay", "extra")


def make_plots(drogue, main, profiles, plots_dir):
    # Remove the images of previous runs (plots/<format>/..., and the old flat layout)
    for old in [f for fmt in FORMATS for f in plots_dir.rglob(f"*.{fmt}")]:
        old.unlink()
    for folder in sorted((d for d in plots_dir.rglob("*") if d.is_dir()), reverse=True):
        if not any(folder.iterdir()):
            folder.rmdir()

    # 1. Ascent (drogue campaign, all delays pooled: the ascent does not depend on the recovery)
    mass_plot(drogue, plots_dir,
              [("max_acceleration_power_on", "massima col motore acceso"),
               ("out_of_rail_acceleration", "all'uscita dalla rampa")],
              "Accelerazione (m/s²)", "Accelerazione al decollo", "01_ascent_acceleration")
    mass_plot(drogue, plots_dir, [("max_speed", "velocità massima")], "Velocità (m/s)",
              "Velocità massima (fine combustione)", "02_ascent_max_velocity")
    mass_plot(drogue, plots_dir, [("max_mach", "Mach massimo")], "Numero di Mach",
              "Mach massimo (fine combustione)", "03_ascent_max_mach", limits=[(1.0, "Mach 1")])
    mass_plot(drogue, plots_dir, [("out_of_rail_velocity", "uscita rampa")], "Velocità (m/s)",
              "Velocità di uscita dalla rampa (12 m)", "04_ascent_rail_velocity")
    mass_plot(drogue, plots_dir, [("apogee_agl", "apogeo")], "Apogeo AGL (m)", "Apogeo", "05_ascent_apogee")

    # 2. Drogue
    delay_plot(drogue, plots_dir, "delay_case", DROGUE_RAMP, DROGUE_LEGEND, "drogue_terminal_after_transient",
               "Velocità di discesa (m/s)", "Drogue: velocità di discesa a regime", "06_drogue_descent_velocity",
               limits=[(EUROC_DROGUE_RANGE[0], "EuRoC min 23 m/s"), (EUROC_DROGUE_RANGE[1], "EuRoC max 46 m/s")],
               reference=("drogue_descent_at_main_trigger", "a 450 m AGL"), bands="none")
    delay_plot(drogue, plots_dir, "delay_case", DROGUE_RAMP, DROGUE_LEGEND, "drogue_force",
               "Forza di apertura (N)", "Drogue: forza di apertura", "07_drogue_opening_force",
               limits=[(DROGUE_LINES_CAPACITY, f"capacità funi 4 × 250 lb = {DROGUE_LINES_CAPACITY / 1000:.1f} kN")])

    # 3. Main (main campaign, drogue delay fixed)
    if main is not None:
        delay_plot(main, plots_dir, "main_delay_case", MAIN_RAMP, MAIN_LEGEND, "main_terminal_after_transient",
                   "Velocità di discesa (m/s)", "Main: velocità di discesa a regime", "08_main_descent_velocity",
                   limits=[(EUROC_MAIN_MAX, "EuRoC max 9 m/s")],
                   reference=("impact_velocity", "all'impatto"), bands="none")
        delay_plot(main, plots_dir, "main_delay_case", MAIN_RAMP, MAIN_LEGEND, "main_force",
                   "Forza di apertura (N)", "Main: forza di apertura", "09_main_opening_force",
                   limits=[(MAIN_LINES_CAPACITY, f"capacità funi 4 × 550 lb = {MAIN_LINES_CAPACITY / 1000:.1f} kN")],
                   reference=("main_force", "dispersione P1–P99", "band"), bands="none")
        delay_plot(main, plots_dir, "main_delay_case", MAIN_RAMP, MAIN_LEGEND, "main_altitude",
                   "Quota AGL (m)", "Main: quota di piena apertura", "10_main_inflation_altitude",
                   limits=[(MAIN_DEPLOY_ALTITUDE, "segnale main a 450 m")])

    # Extra: checks
    plot_drogue_descent_profile(profiles, plots_dir)
    plot_delay_check(drogue, plots_dir)
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- TABLES
def fmt(stats, metric, digits=0):
    return (f"{stats[(metric, 'mean')]:.{digits}f} "
            f"[{stats[(metric, 'p01')]:.{digits}f} – {stats[(metric, 'p99')]:.{digits}f}]")


def make_summary(drogue, main, output_dir):
    frames = {"drogue": drogue, "main": main}
    summaries = []
    for campaign, df in frames.items():
        if df is None:
            continue
        column = "delay_case" if campaign == "drogue" else "main_delay_case"
        summary = df.groupby(["dry_mass_case", column])[numeric_columns(df)].agg(STATS)
        summary.columns = [f"{metric}_{stat}" for metric, stat in summary.columns]
        summary.index.names = ["dry_mass_case", "delay_case"]
        summary.insert(0, "campaign", campaign)
        summaries.append(summary)
    pd.concat(summaries).to_csv(output_dir / "summary.csv")

    drogue_config = json.loads((output_dir / "study_config_drogue.json").read_text())
    by_mass = grouped_by_mass(drogue, numeric_columns(drogue))
    by_case = drogue.groupby(["dry_mass_case", "delay_case"])[numeric_columns(drogue)].agg(STATS)
    masses = sorted(drogue.dry_mass_case.unique())
    cases = case_order(drogue.delay_case.unique())

    lines = [
        "# Atlas: studio paracadute (massa × ritardi di apertura)",
        "",
        f"- Campagna drogue: {len(drogue)} voli, {drogue_config['n_sims']} per ogni coppia (massa, T drogue)",
        f"- Atmosfera: `{drogue_config['weather_data']}` (c = media EuRoC Santa Margarida 2005–2024, ore 12); "
        f"drag `{drogue_config.get('drag_case') or drogue_config['versions']['aerodynamics']}`",
        f"- Massa a secco = tutto ciò che non brucia; massa al decollo ≈ secca + {PROPELLANT_MASS} kg",
        "- Valori: **media [P1 – P99]** sulle simulazioni",
        "",
        "## Salita",
        "",
        "| Massa secca (kg) | Massa decollo (kg) | Apogeo AGL (m) | V uscita rampa (m/s) | A uscita rampa (m/s²) "
        "| A max motore (m/s²) | V max (m/s) | Mach max |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for mass, stats in by_mass.iterrows():
        lines.append(
            f"| {mass:g} | {stats[('wet_mass', 'mean')]:.1f} | {fmt(stats, 'apogee_agl')} | "
            f"{fmt(stats, 'out_of_rail_velocity', 1)} | {fmt(stats, 'out_of_rail_acceleration')} | "
            f"{fmt(stats, 'max_acceleration_power_on')} | {fmt(stats, 'max_speed')} | {fmt(stats, 'max_mach', 2)} |"
        )

    lines += [
        "",
        "## Drogue: apertura (T = apogeo -> piena apertura)",
        "",
        f"Forza = ½ρ·CdS·v² alla piena apertura (modello RocketPy). Capacità funi ≈ {DROGUE_LINES_CAPACITY:.0f} N.",
        "",
        "| Massa secca (kg) | T | Quota apertura (m) | V apertura (m/s) | Forza (N) | Forza max (N) | Carico P99 (g) |",
        "|---|---|---|---|---|---|---|",
    ]
    for mass in masses:
        for case in cases:
            stats = by_case.loc[(mass, case)]
            lines.append(
                f"| {mass:g} | {case} s | {fmt(stats, 'drogue_altitude')} | {fmt(stats, 'drogue_speed', 1)} | "
                f"{fmt(stats, 'drogue_force')} | {stats[('drogue_force', 'max')]:.0f} | "
                f"{stats[('drogue_load_factor', 'p99')]:.1f} |"
            )

    lines += [
        "",
        "## Drogue: discesa a regime (EuRoC RQT-0360: 23–46 m/s)",
        "",
        "Velocità terminale √(2mg/ρCdS) alla quota di fine transitorio (massima) e velocità a 450 m (minima).",
        "",
        "| Massa secca (kg) | " + " | ".join(f"T = {c} s" for c in cases) + " | a 450 m | Esito |",
        "|---|" + "---|" * (len(cases) + 2),
    ]
    for mass in masses:
        stats = by_mass.loc[mass]
        low = stats[("drogue_descent_at_main_trigger", "p01")]
        high = by_case.loc[mass][("drogue_terminal_after_transient", "p99")].max()
        ok = EUROC_DROGUE_RANGE[0] <= low and high <= EUROC_DROGUE_RANGE[1]
        lines.append(
            f"| {mass:g} | " + " | ".join(fmt(by_case.loc[(mass, c)], "drogue_terminal_after_transient", 1)
                                          for c in cases)
            + f" | {fmt(stats, 'drogue_descent_at_main_trigger', 1)} | {'OK' if ok else '**FUORI RANGE**'} |"
        )

    if main is not None:
        main_config = json.loads((output_dir / "study_config_main.json").read_text())
        main_case = main.groupby(["dry_mass_case", "main_delay_case"])[numeric_columns(main)].agg(STATS)
        main_cases = case_order(main.main_delay_case.unique())
        lines += [
            "",
            "## Main (T = passaggio a 450 m AGL -> piena apertura)",
            "",
            f"Campagna main: {len(main)} voli, {main_config['n_sims']} per ogni coppia (massa, T main); "
            f"drogue fisso con T = {main_config['fixed_drogue_delay']:g} s. Capacità funi ≈ {MAIN_LINES_CAPACITY:.0f} N.",
            "",
            "| Massa secca (kg) | T | Quota apertura (m) | V apertura (m/s) | Forza (N) | Forza max (N) "
            "| V discesa a regime (m/s) | V impatto (m/s) | EuRoC < 9 m/s |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for mass in sorted(main.dry_mass_case.unique()):
            for case in main_cases:
                stats = main_case.loc[(mass, case)]
                ok = stats[("main_terminal_after_transient", "p99")] < EUROC_MAIN_MAX
                lines.append(
                    f"| {mass:g} | {case} s | {fmt(stats, 'main_altitude')} | {fmt(stats, 'main_speed', 1)} | "
                    f"{fmt(stats, 'main_force')} | {stats[('main_force', 'max')]:.0f} | "
                    f"{fmt(stats, 'main_terminal_after_transient', 2)} | {fmt(stats, 'impact_velocity', 2)} | "
                    f"{'OK' if ok else '**NO**'} |"
                )

    lines += [
        "",
        "## Note sul modello",
        "",
        "- RocketPy porta il CdS al valore pieno in un istante (nessuna curva di gonfiaggio né overshoot): "
        "la forza riportata è quella quasi-stazionaria alla piena apertura. "
        "Drogue (calotta piccola, razzo pesante): la velocità non cala durante il gonfiaggio, il valore è una base "
        "corretta ma il picco reale può superarlo del fattore di sovragonfiaggio Cx (letteratura ~1.1–1.8, "
        "non noto per Rocketman). Main (calotta grande, razzo leggero): il razzo rallenta mentre la calotta si "
        "gonfia, un modello con tempo di gonfiaggio dà un picco 5–10 volte più basso, quindi il valore è conservativo. "
        "Nessuno dei due modelli include lo strappo al tendersi delle funi (snatch).",
        "- Velocità di discesa a regime = velocità terminale √(2mg/ρCdS) alla quota in cui finisce il transitorio "
        "di apertura: dipende dal ritardo di apertura attraverso la quota (densità).",
        "- Inerzie scalate con la massa, CG a secco fisso (1.848 m dalla punta).",
    ]
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n")
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- LATEX
def tex_num(value, digits=0):
    return f"\\num{{{value:.{digits}f}}}"


def tex_cell(stats, metric, digits=0):
    """mean with the P1-P99 range in small print."""
    return (f"{tex_num(stats[(metric, 'mean')], digits)} {{\\scriptsize "
            f"[{tex_num(stats[(metric, 'p01')], digits)}--{tex_num(stats[(metric, 'p99')], digits)}]}}")


def write_tabular(path, columns, header, rows, full_width=False):
    """booktabs table; full_width spreads the columns over the whole text width."""
    if full_width:
        begin, end = f"\\begin{{tabular*}}{{\\textwidth}}{{@{{\\extracolsep{{\\fill}}}}{columns}}}", "\\end{tabular*}"
    else:
        begin, end = f"\\begin{{tabular}}{{{columns}}}", "\\end{tabular}"
    lines = [begin, "\\toprule", header + " \\\\", "\\midrule"]
    lines += [" & ".join(row) + " \\\\" for row in rows]
    lines += ["\\bottomrule", end]
    path.write_text("\n".join(lines) + "\n")


def macro_lines(prefix, grouped, keys):
    """\\csname definitions for every (key..., metric, stat) of a grouped statistics table."""
    lines = []
    for key, stats in grouped.iterrows():
        key = key if isinstance(key, tuple) else (key,)
        name = "@".join(f"{k:g}" if isinstance(k, float) else str(k) for k in key)
        for (metric, stat), value in stats.items():
            if stat in ("mean", "std", "p01", "p99", "min", "max") and np.isfinite(value):
                lines.append(f"\\expandafter\\def\\csname {prefix}@{metric}@{name}@{stat}\\endcsname{{{value:.6g}}}")
    return lines


def make_latex(drogue, main, output_dir):
    """Tables and number macros for report/parachute_study.tex, so the text follows the data."""
    generated = output_dir / "report" / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    for old in generated.glob("*.tex"):
        old.unlink()
    masses = sorted(drogue.dry_mass_case.unique())
    by_mass = grouped_by_mass(drogue, numeric_columns(drogue))
    by_case = drogue.groupby(["dry_mass_case", "delay_case"])[numeric_columns(drogue)].agg(STATS)
    cases = case_order(drogue.delay_case.unique())
    drogue_config = json.loads((output_dir / "study_config_drogue.json").read_text())
    terminal_error = (drogue.drogue_terminal_at_main_trigger - drogue.drogue_descent_at_main_trigger).abs().max()
    spread_450 = (drogue.groupby(["dry_mass_case", "delay_case"]).drogue_descent_at_main_trigger.mean()
                  .groupby(level=0).agg(lambda x: x.max() - x.min()).max())

    # Number macros, used in the text through \val (drogue campaign, by mass), \valD (drogue, by mass and T),
    # \valM (main campaign, by mass and T) and \valMP (main campaign, by mass)
    lines = [
        "% Generated by parachute_study_plots.py - do not edit",
        f"\\newcommand{{\\NFlightsDrogue}}{{\\num{{{len(drogue)}}}}}",
        f"\\newcommand{{\\NSims}}{{\\num{{{drogue_config['n_sims']}}}}}",
        f"\\newcommand{{\\PropellantMass}}{{\\num{{{PROPELLANT_MASS}}}}}",
        f"\\newcommand{{\\DrogueLinesCapacity}}{{\\num{{{DROGUE_LINES_CAPACITY:.0f}}}}}",
        f"\\newcommand{{\\MainLinesCapacity}}{{\\num{{{MAIN_LINES_CAPACITY:.0f}}}}}",
        f"\\newcommand{{\\TerminalCheckError}}{{\\num{{{terminal_error:.2f}}}}}",
        f"\\newcommand{{\\DrogueSpreadAtMain}}{{\\num{{{spread_450:.2f}}}}}",
    ]
    lines += macro_lines("val", by_mass, ["dry_mass_case"])
    lines += macro_lines("valD", by_case, ["dry_mass_case", "delay_case"])

    # Ascent
    write_tabular(
        generated / "tab_ascent.tex", "S[table-format=2.1]S[table-format=2.1]cccccc",
        "{Secca (kg)} & {Decollo (kg)} & Apogeo AGL (m) & $v_\\text{rampa}$ (m/s) & $a_\\text{rampa}$ (m/s$^2$) "
        "& $a_\\text{max}$ (m/s$^2$) & $v_\\text{max}$ (m/s) & Mach max",
        [[f"{m:g}", f"{by_mass.loc[m, ('wet_mass', 'mean')]:.1f}", tex_cell(by_mass.loc[m], "apogee_agl"),
          tex_cell(by_mass.loc[m], "out_of_rail_velocity", 1), tex_cell(by_mass.loc[m], "out_of_rail_acceleration"),
          tex_cell(by_mass.loc[m], "max_acceleration_power_on"), tex_cell(by_mass.loc[m], "max_speed"),
          tex_cell(by_mass.loc[m], "max_mach", 2)] for m in masses],
    )

    # Drogue
    header = "{Secca (kg)} & " + " & ".join(f"$T = \\SI{{{c}}}{{s}}$" for c in cases)
    write_tabular(
        generated / "tab_drogue_force.tex", "S[table-format=2.1]" + "c" * len(cases), header,
        [[f"{m:g}"] + [f"{tex_num(by_case.loc[(m, c), ('drogue_force', 'mean')])} {{\\scriptsize "
                       f"({tex_num(by_case.loc[(m, c), ('drogue_force', 'p99')])})}}" for c in cases] for m in masses],
        full_width=True,
    )
    rows = []
    for m in masses:
        low = by_mass.loc[m, ("drogue_descent_at_main_trigger", "p01")]
        high = by_case.loc[m][("drogue_terminal_after_transient", "p99")].max()
        ok = EUROC_DROGUE_RANGE[0] <= low and high <= EUROC_DROGUE_RANGE[1]
        rows.append([f"{m:g}"]
                    + [tex_num(by_case.loc[(m, c), ("drogue_terminal_after_transient", "mean")], 1) for c in cases]
                    + [tex_cell(by_mass.loc[m], "drogue_descent_at_main_trigger", 1),
                       "\\textcolor{ok}{conforme}" if ok else "\\textcolor{ko}{P1 sotto 23}"])
    write_tabular(generated / "tab_drogue_descent.tex", "S[table-format=2.1]" + "c" * (len(cases) + 2),
                  header + " & a \\SI{450}{m} & RQT-0360", rows)

    # Main
    if main is not None:
        main_config = json.loads((output_dir / "study_config_main.json").read_text())
        main_case = main.groupby(["dry_mass_case", "main_delay_case"])[numeric_columns(main)].agg(STATS)
        main_mass = grouped_by_mass(main, numeric_columns(main))
        main_cases = case_order(main.main_delay_case.unique())
        main_masses = sorted(main.dry_mass_case.unique())
        slope = np.polyfit(main.main_lag, main.main_altitude, 1)[0]
        lines += [
            f"\\newcommand{{\\NFlightsMain}}{{\\num{{{len(main)}}}}}",
            f"\\newcommand{{\\MainFixedDrogueDelay}}{{\\num{{{main_config['fixed_drogue_delay']:g}}}}}",
            f"\\newcommand{{\\MainAltitudeSlope}}{{\\num{{{-slope:.0f}}}}}",
        ]
        lines += macro_lines("valM", main_case, ["dry_mass_case", "main_delay_case"])
        lines += macro_lines("valMP", main_mass, ["dry_mass_case"])

        header = "{Secca (kg)} & " + " & ".join(f"$T = \\SI{{{c}}}{{s}}$" for c in main_cases)
        write_tabular(
            generated / "tab_main_force.tex", "S[table-format=2.1]" + "c" * len(main_cases), header,
            [[f"{m:g}"] + [f"{tex_num(main_case.loc[(m, c), ('main_force', 'mean')])} {{\\scriptsize "
                           f"({tex_num(main_case.loc[(m, c), ('main_force', 'p99')])})}}" for c in main_cases]
             for m in main_masses],
        )
        write_tabular(
            generated / "tab_main_altitude.tex", "S[table-format=2.1]" + "c" * len(main_cases), header,
            [[f"{m:g}"] + [tex_cell(main_case.loc[(m, c)], "main_altitude") for c in main_cases] for m in main_masses],
        )
        rows = []
        for m in main_masses:
            high = main_case.loc[m][("main_terminal_after_transient", "p99")].max()
            ok = high < EUROC_MAIN_MAX
            rows.append([f"{m:g}"]
                        + [tex_num(main_case.loc[(m, c), ("main_terminal_after_transient", "mean")], 2)
                           for c in main_cases]
                        + [tex_cell(main_mass.loc[m], "impact_velocity", 2),
                           "\\textcolor{ok}{conforme}" if ok else "\\textcolor{ko}{no}"])
        write_tabular(generated / "tab_main_descent.tex", "S[table-format=2.1]" + "c" * (len(main_cases) + 2),
                      header + " & impatto & RQT-0380", rows)

        # EuRoC requirements, worst case over all delays
        rows = []
        for m in masses:
            drogue_low = by_mass.loc[m, ("drogue_descent_at_main_trigger", "p01")]
            drogue_high = by_case.loc[m][("drogue_terminal_after_transient", "p99")].max()
            main_high = main_case.loc[m][("main_terminal_after_transient", "p99")].max()
            drogue_ok = EUROC_DROGUE_RANGE[0] <= drogue_low and drogue_high <= EUROC_DROGUE_RANGE[1]
            main_ok = main_high < EUROC_MAIN_MAX
            rows.append([f"{m:g}", tex_num(drogue_low, 1), tex_num(drogue_high, 1),
                         "\\textcolor{ok}{conforme}" if drogue_ok else "\\textcolor{ko}{non conforme}",
                         tex_num(main_high, 2),
                         "\\textcolor{ok}{conforme}" if main_ok else "\\textcolor{ko}{non conforme}"])
        write_tabular(generated / "tab_euroc.tex", "S[table-format=2.1]ccccc",
                      "{Secca (kg)} & Drogue: $v$ min P1 (m/s) & Drogue: $v$ max P99 (m/s) & RQT-0360 "
                      "& Main: $v$ max P99 (m/s) & RQT-0380", rows)

    (generated / "numbers.tex").write_text("\n".join(lines) + "\n")
#--------------------------------------------------------------------------------------------------------





def make_report(output_dir):
    output_dir = Path(output_dir)
    dtypes = {"delay_case": str, "main_delay_case": str}
    drogue = pd.read_csv(output_dir / "runs_drogue.csv", dtype=dtypes)
    main_file = output_dir / "runs_main.csv"
    main = pd.read_csv(main_file, dtype=dtypes) if main_file.exists() else None
    profiles_file = output_dir / "profiles_drogue.pickle"
    profiles = pickle.loads(profiles_file.read_bytes()) if profiles_file.exists() else []
    make_summary(drogue, main, output_dir)
    make_plots(drogue, main, profiles, output_dir / "plots")
    make_latex(drogue, main, output_dir)
    print(f"Summary and plots written to {output_dir}")
