"""
Near-ground weather of a launch site from a GRIB of "ERA5 hourly data on single levels" downloaded from
the Copernicus CDS: wind at 10 m and 100 m, temperature at 2 m and surface pressure, every hour.

Writes:
- simulation_inputs/environment_data/<site>/<site>_surface_<period>.csv: one row per hour, values interpolated
  (bilinear) at the launch point of launch_site.csv. fred_model.py reads it for the climatological weather (c).
- <site>/<period>/surface_wind.png next to this script: mean wind from the ground to 150 m for every hour of the
  day, with the 90th percentile of the speed.

Needs cfgrib and xarray (pip install cfgrib xarray). Reading the GRIB takes about a minute.

Usage:
    python FRED/FRED2.0/tools/environment/surface_wind/surface_wind.py <file>.grib <site> <period>
    e.g. ... Villafranca/Villafranca_surface_20to30oct2010to2025.grib Villafranca 20to30oct2010to2025
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

HERE = Path(__file__).resolve().parent
FRED_DIR = HERE.parents[2]
VARIABLES = {"u10": "u10", "v10": "v10", "u100": "u100", "v100": "v100", "t2m": "t2m", "sp": "sp"}
HEIGHTS = [10, 25, 50, 75, 100, 125, 150]       # m above the ground, for the graph
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]


def site_table(grib, latitude, longitude):
    """Hourly values at the launch point."""
    data = xr.open_dataset(grib, engine="cfgrib", backend_kwargs={"indexpath": ""})
    missing = [name for name in VARIABLES if name not in data]
    if missing:
        raise SystemExit(f"Variables missing in the GRIB: {', '.join(missing)}")
    point = data[list(VARIABLES)].interp(latitude=latitude, longitude=longitude)
    table = point.to_dataframe()[list(VARIABLES)]
    table.index = pd.DatetimeIndex(point["valid_time"].values, name="time")
    return table.round(4)


def graph(table, site, period, path):
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.transforms import offset_copy

    sys.path.insert(0, str(FRED_DIR))
    import fred_model as model

    hours = sorted(table.index.hour.unique())
    speed = np.zeros((len(HEIGHTS), len(hours)))
    p90, direction = np.zeros_like(speed), np.zeros_like(speed)
    for j, hour in enumerate(hours):
        rows = table[table.index.hour == hour]
        profiles = np.array([model.surface_wind(row, HEIGHTS) for _, row in rows.iterrows()])  # (n, 2, heights)
        u, v = profiles[:, 0], profiles[:, 1]
        s = np.hypot(u, v)
        speed[:, j], p90[:, j] = s.mean(0), np.percentile(s, 90, axis=0)
        direction[:, j] = (np.degrees(np.arctan2(-u.mean(0), -v.mean(0))) + 360) % 360

    ink, muted = "#1a1a19", "#6b6a63"
    cmap = LinearSegmentedColormap.from_list("blue", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": muted, "xtick.color": muted, "ytick.color": muted,
                         "axes.labelcolor": ink})
    fig, ax = plt.subplots(figsize=(11, 7))
    vmin, vmax = np.floor(speed.min()), np.ceil(speed.max())
    rows_y = np.arange(len(HEIGHTS))
    image = ax.imshow(speed, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto",
                      extent=[hours[0] - 0.5, hours[-1] + 0.5, -0.5, len(HEIGHTS) - 0.5])
    for i in rows_y:
        for j, hour in enumerate(hours):
            color = "white" if (speed[i, j] - vmin) / (vmax - vmin) > 0.55 else ink
            angle = np.radians(direction[i, j])
            dx, dy = -np.sin(angle), -np.cos(angle)          # towards where the wind goes
            head = offset_copy(ax.transData, fig=fig, x=12 * dx, y=12 * dy, units="points")
            tail = offset_copy(ax.transData, fig=fig, x=-12 * dx, y=-12 * dy, units="points")
            ax.annotate("", xy=(hour + 0.30, i + 0.05), xycoords=head, xytext=(hour + 0.30, i + 0.05), textcoords=tail,
                        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4, mutation_scale=11))
            ax.text(hour - 0.12, i + 0.17, f"{speed[i, j]:.1f}", ha="center", va="center", color=color,
                    fontsize=11, fontweight="bold")
            compass = COMPASS[int((direction[i, j] + 11.25) // 22.5) % 16]
            ax.text(hour - 0.12, i - 0.17, f"da {compass} {direction[i, j]:.0f}°\nP90 {p90[i, j]:.1f}", ha="center",
                    va="center", color=color, fontsize=7.5)
    for k in range(len(hours) + 1):
        ax.axvline(hours[0] - 0.5 + k, color="white", lw=2)
    for k in range(len(HEIGHTS) + 1):
        ax.axhline(k - 0.5, color="white", lw=2)
    ax.set_xticks(hours, [f"{hour}:00" for hour in hours])
    ax.set_yticks(rows_y, [f"{h} m" for h in HEIGHTS])
    ax.set_xlabel("ora UTC")
    ax.set_ylabel("quota sul terreno")
    days = len(np.unique(table.index.date))
    fig.suptitle(f"Vento vicino al suolo a {site}, {period} (ERA5 single levels, {days} giorni)", x=0.065, ha="left",
                 color=ink, fontsize=13, y=0.985)
    fig.text(0.065, 0.935, "numero = intensità media [m/s]   P90 = 90° percentile dell'intensità   freccia = direzione media, "
             "punta dove va il vento   'da' = da dove arriva\nvento dato a 10 m e 100 m, tra le due quote e sopra profilo "
             "a legge di potenza (fred_model.surface_wind)", color=muted, fontsize=9, va="top")
    for spine in ax.spines.values():
        spine.set_visible(False)
    colorbar = fig.colorbar(image, ax=ax, pad=0.02, shrink=0.85)
    colorbar.set_label("intensità media [m/s]", color=ink)
    colorbar.outline.set_visible(False)
    fig.tight_layout(rect=(0, 0, 1, 0.89))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("grib", type=Path, help="GRIB of ERA5 single levels downloaded from the CDS")
    parser.add_argument("site", help="folder in simulation_inputs/environment_data/")
    parser.add_argument("period", help="part of the file names, e.g. 20to30oct2010to2025")
    args = parser.parse_args()

    site_dir = FRED_DIR / "simulation_inputs" / "environment_data" / args.site
    launch = pd.read_csv(site_dir / "launch_site.csv", comment="#", skipinitialspace=True, index_col="name")["value"]
    table = site_table(args.grib, float(launch["latitude"]), float(launch["longitude"]))
    output = site_dir / f"{args.site}_surface_{args.period}.csv"
    table.to_csv(output, date_format="%Y-%m-%d %H:%M")
    print(f"{len(table)} hours, {len(np.unique(table.index.date))} days, hours {sorted(table.index.hour.unique())} UTC "
          f"-> {output}")
    picture = HERE / args.site / args.period / "surface_wind.png"
    graph(table, args.site, args.period, picture)
    print(f"Graph -> {picture}")


if __name__ == "__main__":
    main()
