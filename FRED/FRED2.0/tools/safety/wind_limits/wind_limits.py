"""
Wind limits for FRED2.0: for every rail heading, every wind direction and every wind speed, a Monte Carlo
of the flight tells whether the rocket can land on the houses around the launch site.

Every cell of the grid is a rail heading, a wind direction and a wind speed (at 10 m, boundary-layer profile
"mbl" of fred_model.py). In its flights vary: the wind around the cell values (WIND_SPEED_STD, the resolution of
the weather station, and WIND_DIRECTION_STD), the rail pointing (RAIL_STD on heading and inclination) and all the
parameters of rocket, motor and recovery with the std of their simulation_inputs files; the total parachute lag
is LAG_TOTAL. Versions and launch site are the ones at the top of fred_model.py.

Houses zone: the inhabited area widened by BUFFER m. Inhabited area = the side of the houses of the line drawn
in <site>/houses_line.csv where there is one, elsewhere the OpenStreetMap footprints of <site>/buildings.geojson
(buildings.py) widened by ENVELOPE m with the gaps between near houses closed.
Colour of a cell:
  red    at least one landing in the houses zone (the cell shows the % of landings there)
  yellow no landing in the zone, but the 3-sigma ellipse of the landing points touches it
  green  3-sigma ellipse outside the zone (the cell shows its minimum distance from the zone)

Outputs in <site>/<RUN_NAME>/ next to this script:
  config.json               versions of fred_model.py used by the flights (a resumed run must use the same)
  impacts.csv               one row per flight, landing points relative to the rail (resumable: the cells
                            already there are skipped)
  launch_points.csv/.png    every launch point of <site>/launch_area.csv (GRID_STEP m): highest gust admitted
                            from every direction, with the best heading of every cell and with each heading
  launch_points_heading<h>.png   the same with one heading for every cell
  summary.csv               one row per cell for the chosen launch point: % in the zone, ellipse, distance, colour
  lookup_heading<h>.png     look-up table of every heading for the chosen launch point
  lookup_best_heading.png   look-up table with the best heading of every cell
  map_heading<h>.png        landing points and 3-sigma ellipses of every cell on the map

Launch point: moving the rail by (e, n) moves every landing point by (e, n) (flat ground, same wind
everywhere), so one grid of flights serves every launch point. The chosen one is the point of the launch
area with the highest gust admitted from every direction (heading chosen on the field for every cell), then
the largest margin; --launch E N gives the tables of another point, in the subfolder launch_<E>E_<N>N.

Usage:
    python FRED/FRED2.0/tools/safety/wind_limits/wind_limits.py            # simulate the missing cells, then tables
    python FRED/FRED2.0/tools/safety/wind_limits/wind_limits.py --tables   # only tables and maps from impacts.csv
    python FRED/FRED2.0/tools/safety/wind_limits/wind_limits.py --tables --launch 10 -5   # tables of that point
    python FRED/FRED2.0/tools/safety/wind_limits/wind_limits.py --tables --run v1.1_8mm_ott26_inc80   # another run
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
FRED_DIR = HERE.parents[2]
sys.path.insert(0, str(FRED_DIR))
import fred_model as model  # noqa: E402

#-------------------------------------------------------------------------------------------------------- PARAMETERS
RUN_NAME = None                     # output folder in <site>/; None = <geometry>_<motor>_inc<inclination> of fred_model.py
HEADINGS = (140, 160, 180)          # rail heading (deg from north)
INCLINATION = 80                    # rail inclination (deg from the horizontal)
# Wind directions: where the wind COMES FROM (deg from north). At Villafranca only the winds from W to SE
# (through S) can carry the rocket towards the houses; from E to NW (through N) it lands on the fields.
DIRECTIONS = {"O": 270, "OSO": 247.5, "SO": 225, "SSO": 202.5, "S": 180, "SSE": 157.5, "SE": 135}
SPEEDS = (1, 2, 3, 4, 5, 6)         # wind speed at WIND_REF_HEIGHT [m/s]: the max gust read at the station
WIND_REF_HEIGHT = 7.5               # m above the ground, height of the anemometer of the weather station
N_RUNS = 200                        # flights per cell
BUFFER = 10                         # m of margin around the inhabited area
ENVELOPE = 15                       # m around the houses where houses_line.csv does not reach
RAIL_STD = 1.5                      # deg, std of rail heading and inclination (+-3 deg taken as 2 sigma)
WIND_DIRECTION_STD = 8              # deg (the station gives 16 sectors of 22.5 deg: 6.5 deg from the sector alone)
WIND_SPEED_STD = 0.5                # m/s (accuracy of a cup anemometer of a hobby weather station)
LAG_TOTAL = 1.0                     # s, from the apogee detection to the parachute fully inflated
SEED = 2026
MULTIPLE_CORE = True
GRID_STEP = 2                       # m, spacing of the launch points tried inside <site>/launch_area.csv
#--------------------------------------------------------------------------------------------------------

SITE_DIR = HERE / model.LAUNCH_SITE


def set_run(name):
    """Output folder of the run (and its files) in SITE_DIR."""
    global RUN_NAME, RUN_DIR, IMPACTS, CONFIG
    RUN_NAME = name
    RUN_DIR = SITE_DIR / RUN_NAME
    IMPACTS = RUN_DIR / "impacts.csv"
    CONFIG = RUN_DIR / "config.json"       # versions of fred_model.py used by the flights


set_run(RUN_NAME or f"{model.GEOMETRY}_{model.MOTOR.split('/')[-1]}_inc{INCLINATION}")
CELL = ["heading", "direction", "speed"]


def cell_parameters(heading):
    params = model.load_parameters()
    params["heading"] = (heading, RAIL_STD)
    params["inclination"] = (INCLINATION, RAIL_STD)
    params["main_lag"] = (LAG_TOTAL, params["main_lag"][1])
    params["electronics_lag"] = (0, 0)
    return params


def run_one(task):
    """One flight of one cell."""
    heading, direction, speed, run, run_seed = task
    rng = np.random.default_rng(run_seed)
    setting = model.sample(cell_parameters(heading), rng)
    wind_speed = max(rng.normal(speed, WIND_SPEED_STD), 0)
    wind_from = rng.normal(DIRECTIONS[direction], WIND_DIRECTION_STD)
    model.MANUAL_BL_WIND = (wind_speed, (wind_from + 180) % 360)     # where the wind goes
    model.MANUAL_WIND_BL_REF_HEIGHT = WIND_REF_HEIGHT
    row = {"heading": heading, "direction": direction, "speed": speed, "run": run, "seed": run_seed,
           "wind_speed": wind_speed, "wind_from": wind_from % 360,
           "rail_heading": setting["heading"], "rail_inclination": setting["inclination"]}
    try:
        flight = model.simulate(setting, model.build_environment("mbl"))
        row.update(impact_x=flight.x_impact, impact_y=flight.y_impact, apogee=flight.apogee - flight.env.elevation,
                   apogee_x=flight.apogee_x, apogee_y=flight.apogee_y, rail_velocity=flight.out_of_rail_velocity,
                   impact_time=flight.t_final, error="")
    except Exception as error:  # noqa: BLE001 - one failed flight must not stop the grid
        row.update(error=repr(error))
    return row


def configuration():
    """Versions of fred_model.py used by the flights of the run."""
    return {"geometry": model.GEOMETRY, "motor": model.MOTOR, "aerodynamics": model.AERODYNAMICS,
            "recovery": model.RECOVERY}


def simulate():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    # The run keeps the versions of its flights: a resumed run must use the same ones, and the tables print them
    if CONFIG.exists():
        saved = json.loads(CONFIG.read_text())
        if saved != configuration():
            raise ValueError(f"{RUN_DIR.name} was simulated with {saved}, fred_model.py now has {configuration()}: "
                             "use the same versions or a new RUN_NAME")
    else:
        CONFIG.write_text(json.dumps(configuration(), indent=1) + "\n")
    done = set()
    if IMPACTS.exists():
        done = set(map(tuple, pd.read_csv(IMPACTS)[CELL].drop_duplicates().itertuples(index=False)))
    cells = [(h, d, s) for h in HEADINGS for d in DIRECTIONS for s in SPEEDS if (h, d, s) not in done]
    print(f"{len(cells)} cells to simulate ({len(done)} already in {IMPACTS.name}), {N_RUNS} flights each")
    pool = mp.get_context("fork" if "fork" in mp.get_all_start_methods() else "spawn").Pool(os.cpu_count()) \
        if MULTIPLE_CORE else None
    start = time.time()
    for k, (heading, direction, speed) in enumerate(cells, start=1):
        # The seeds depend only on the cell: a resumed run gives the same flights
        cell_seed = np.random.SeedSequence([SEED, heading, int(DIRECTIONS[direction] * 10), speed])
        tasks = [(heading, direction, speed, run, int(s)) for run, s in enumerate(cell_seed.generate_state(N_RUNS))]
        rows = pool.map(run_one, tasks) if pool else list(map(run_one, tasks))
        pd.DataFrame(rows).to_csv(IMPACTS, mode="a", header=not IMPACTS.exists(), index=False)
        errors = sum(bool(r["error"]) for r in rows)
        left = (time.time() - start) / k * (len(cells) - k)
        print(f"[{k}/{len(cells)}] heading {heading}, wind {speed} m/s from {direction}: "
              f"{errors} errors, {left / 60:.0f} min left", flush=True)
    if pool:
        pool.close()
        pool.join()


#-------------------------------------------------------------------------------------------------------- ANALYSIS
# The landing points are relative to the launch point and the ground is flat with the same wind everywhere:
# moving the rail by (e, n) moves every landing point by (e, n). So one grid of flights gives the tables of
# every launch point of the launch area.

def houses_zone():
    """Footprints, houses zone, OSM info, drawn line (or None) and inhabited area."""
    from shapely.geometry import LineString, Polygon
    from shapely.ops import unary_union

    data = json.loads((SITE_DIR / "buildings.geojson").read_text())
    footprints = [Polygon(f["properties"]["east_north"]) for f in data["features"]]
    # Footprints widened by ENVELOPE m, with the gaps under about 2 * (ENVELOPE + 10) m closed
    inhabited = unary_union(footprints).buffer(ENVELOPE + 10).buffer(-10)
    line = None
    line_file = SITE_DIR / "houses_line.csv"
    if line_file.exists():
        line = LineString(pd.read_csv(line_file, comment="#").to_numpy())
        # Where the line is drawn it is the limit: the houses are on its left side, all the left side is closed
        field_side = line.buffer(-80, single_sided=True)
        house_side = line.buffer(60, single_sided=True)
        inhabited = unary_union([inhabited.difference(field_side), house_side])
    return footprints, inhabited.buffer(BUFFER), data["properties"], line, inhabited


def launch_area():
    """Polygon of the launch area (<site>/launch_area.csv, from locate_screenshot.py), or None."""
    from shapely.geometry import MultiPoint

    path = SITE_DIR / "launch_area.csv"
    return MultiPoint(pd.read_csv(path, comment="#").to_numpy()).convex_hull if path.exists() else None


def ellipse_outline(x, y, sigma=3, points=180):
    """3-sigma ellipse of the points, same definition as montecarlo.py (semi-axes sigma * sqrt(eigenvalues))."""
    values, vectors = np.linalg.eigh(np.cov(x, y))
    t = np.linspace(0, 2 * np.pi, points, endpoint=False)
    axes = sigma * np.sqrt(np.maximum(values, 0))
    return (np.mean(x), np.mean(y)) + (vectors @ (axes[:, None] * np.vstack([np.cos(t), np.sin(t)]))).T


def clouds(impacts):
    """{cell: (landing points relative to the rail, 3-sigma ellipse outline)} of the flights without errors."""
    good = impacts[impacts["error"].fillna("") == ""]
    result = {}
    for cell, rows in good.groupby(CELL, sort=False):
        x, y = rows["impact_x"].to_numpy(), rows["impact_y"].to_numpy()
        result[tuple(cell)] = (np.column_stack([x, y]), ellipse_outline(x, y))
    return result


def evaluate(cell_clouds, zone, launch=(0.0, 0.0)):
    """Colour, % of landings in the zone and distance of the ellipse from the zone of every cell, with the
    rail in `launch` (m east, north of the launch point of launch_site.csv)."""
    import shapely
    from shapely.geometry import Polygon

    rows = []
    for (heading, direction, speed), (points, outline) in cell_clouds.items():
        moved = points + launch
        inside = shapely.contains_xy(zone, moved[:, 0], moved[:, 1])
        ellipse = Polygon(outline + launch)
        touches = ellipse.intersects(zone)
        rows.append({
            "heading": heading, "direction": direction, "speed": speed, "flights": len(points),
            "in_zone": int(inside.sum()), "in_zone_pct": 100 * inside.mean(),
            "mean_x": moved[:, 0].mean(), "mean_y": moved[:, 1].mean(),
            "std_x": points[:, 0].std(), "std_y": points[:, 1].std(),
            "ellipse_distance": 0.0 if touches else ellipse.distance(zone),
            "colour": "red" if inside.any() else ("yellow" if touches else "green"),
        })
    return pd.DataFrame(rows)


def best_heading(summary):
    """For every wind cell the heading with GO and the largest distance (or the least bad one)."""
    rank = {"green": 2, "yellow": 1, "red": 0}
    ordered = summary.assign(rank=summary["colour"].map(rank), minus_pct=-summary["in_zone_pct"])
    ordered = ordered.sort_values(["rank", "ellipse_distance", "minus_pct"], ascending=False)
    return ordered.groupby(["direction", "speed"], sort=False).head(1).drop(columns=["rank", "minus_pct"])


def admitted_wind(best):
    """Highest speed V such that every direction is GO up to V (0 if not even the lowest one), and the
    smallest distance from the zone among those cells (margin)."""
    admitted, margin = 0, np.nan
    for speed in SPEEDS:
        cells = best[best["speed"] <= speed]
        if (cells["colour"] != "green").any() or cells["direction"].nunique() < len(DIRECTIONS):
            break
        admitted, margin = speed, cells["ellipse_distance"].min()
    return admitted, margin


def scan(cell_clouds, zone, area):
    """Admitted wind and margin of every launch point on a GRID_STEP grid inside the launch area."""
    import shapely
    from shapely.geometry import box

    # Only the part of the zone that the landings can reach, to keep the geometry small
    reach = max(np.abs(points).max() + np.ptp(outline) for points, outline in cell_clouds.values())
    near_zone = zone.intersection(box(*area.buffer(reach).bounds))
    xmin, ymin, xmax, ymax = area.bounds
    grid = [(e, n) for e in np.arange(xmin, xmax + 1e-9, GRID_STEP) for n in np.arange(ymin, ymax + 1e-9, GRID_STEP)
            if shapely.contains_xy(area, e, n)]
    rows = []
    for k, launch in enumerate(grid, start=1):
        summary = evaluate(cell_clouds, near_zone, launch)
        row = {"east": launch[0], "north": launch[1]}
        row["admitted"], row["margin"] = admitted_wind(best_heading(summary))
        for heading in HEADINGS:
            row[f"admitted_{heading}"], row[f"margin_{heading}"] = admitted_wind(summary[summary["heading"] == heading])
        rows.append(row)
        if k % 100 == 0:
            print(f"  {k}/{len(grid)} launch points", flush=True)
    return pd.DataFrame(rows)


def to_lat_lon(east, north):
    launch = model.nominal(model.read_csv(model.SITE_FILE))
    lat0, lon0 = launch["latitude"], launch["longitude"]
    lat = lat0 + np.degrees(north / 6371000)
    lon = lon0 + np.degrees(east / (6371000 * np.cos(np.radians(lat0))))
    return lat, lon


#-------------------------------------------------------------------------------------------------------- GRAPHS
COLOURS = {"green": "#1baf7a", "yellow": "#eda100", "red": "#d03b3b"}
LABELS = {"green": "GO", "yellow": "LIMITE", "red": "NO-GO"}
INK, MUTED = "#1a1a19", "#6b6a63"


def lookup_table(table, title, path, info, show_heading=False):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    table = table.set_index(["direction", "speed"])
    rows, cols = list(DIRECTIONS), list(SPEEDS)
    fig, ax = plt.subplots(figsize=(10.5, 7.6))
    for i, direction in enumerate(rows):
        for j, speed in enumerate(cols):
            cell = table.loc[(direction, speed)]
            y = len(rows) - 1 - i
            ax.add_patch(Rectangle((j, y), 1, 1, facecolor=COLOURS[cell["colour"]], edgecolor="white", lw=3))
            text = {"red": f"{cell['in_zone_pct']:.1f}%", "yellow": "",
                    "green": f"{cell['ellipse_distance']:.0f} m"}[cell["colour"]]
            label = LABELS[cell["colour"]] + (f"  {int(cell['heading'])}°" if show_heading and cell["colour"] == "green" else "")
            ax.text(j + 0.5, y + (0.62 if text else 0.5), label, ha="center", va="center", color="white", fontsize=11,
                    fontweight="bold")
            ax.text(j + 0.5, y + 0.33, text, ha="center", va="center", color="white", fontsize=10)
    ax.set_xlim(0, len(cols))
    ax.set_ylim(0, len(rows))
    ax.set_xticks(np.arange(len(cols)) + 0.5, [f"{s} m/s\n{s * 3.6:.0f} km/h" for s in cols])
    ax.set_yticks(np.arange(len(rows)) + 0.5, [f"da {d} ({DIRECTIONS[d]:g}°)" for d in reversed(rows)])
    ax.xaxis.tick_top()
    ax.set_xlabel(f"raffica massima alla stazione ({WIND_REF_HEIGHT} m dal suolo)", color=INK)
    ax.xaxis.set_label_position("top")
    ax.tick_params(length=0, colors=INK)
    ax.minorticks_off()
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.suptitle(title, x=0.5, y=0.985, ha="center", fontsize=14, color=INK)
    fig.text(0.5, 0.935, f"Punto di lancio {info['launch_text']}", ha="center", fontsize=10.5, color=MUTED)
    # Meaning of the cells, centred, then limit and configuration, on the right
    legend = [("GO", "l'ellisse 3σ degli atterraggi resta fuori dal limite; il numero è la distanza minima dal limite"),
              ("LIMITE", "nessun atterraggio oltre il limite, ma l'ellisse 3σ lo tocca"),
              ("NO-GO", "almeno un atterraggio oltre il limite; il numero è la percentuale di atterraggi oltre il limite")]
    for k, (name, meaning) in enumerate(legend):
        fig.text(0.5, 0.135 - 0.027 * k, f"{name}: {meaning}", ha="center", fontsize=8.5, color=INK)
    fig.text(0.97, 0.045, f"limite = perimetro dell'abitato con {BUFFER} m di margine", ha="right", fontsize=8,
             color=MUTED)
    fig.text(0.97, 0.02, info["config"], ha="right", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.16, 1, 0.92))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def background(ax):
    from imageio.v2 import imread

    sys.path.insert(0, str(FRED_DIR))
    from montecarlo import MAP_EXTENT  # same photo extent as the Monte Carlo maps

    image = next(f for f in sorted(model.SITE_DIR.iterdir()) if f.suffix.lower() in (".jpg", ".png"))
    ax.imshow(imread(image), extent=MAP_EXTENT)


def draw_houses(ax, footprints, zone, line, inhabited):
    """Safety zone (houses + BUFFER, white), OSM footprints, drawn line of the houses (black) and the mission
    control (<site>/mission_control.csv, black box)."""
    for footprint in footprints:
        ax.plot(*footprint.exterior.xy, color="#86b6ef", lw=0.5)
    for polygon in getattr(zone, "geoms", [zone]):
        ax.fill(*polygon.exterior.xy, color="#ffffff", alpha=0.25, lw=0)
        ax.plot(*polygon.exterior.xy, color="white", lw=1.2)
    if line is not None:
        ax.plot(*line.xy, color="black", lw=2)
    mission_control = SITE_DIR / "mission_control.csv"
    if mission_control.exists():
        ax.fill(*pd.read_csv(mission_control, comment="#").to_numpy().T, color="black", lw=0, zorder=5)


def lat_lon_axes(ax):
    """Axes in latitude / longitude instead of metres from the launch point (ticks every 0.0005 deg), and a
    50 m scale bar. The local metres are flat-Earth around the point of launch_site.csv, as in to_lat_lon."""
    from matplotlib.ticker import FixedLocator, FuncFormatter

    lat0, lon0 = to_lat_lon(0, 0)
    metres_per_deg_lat = np.radians(1) * 6371000
    metres_per_deg_lon = metres_per_deg_lat * np.cos(np.radians(lat0))
    step = 0.0005
    (xmin, xmax), (ymin, ymax) = ax.get_xlim(), ax.get_ylim()
    lons = np.arange(np.ceil((lon0 + xmin / metres_per_deg_lon) / step), (lon0 + xmax / metres_per_deg_lon) / step) * step
    lats = np.arange(np.ceil((lat0 + ymin / metres_per_deg_lat) / step), (lat0 + ymax / metres_per_deg_lat) / step) * step
    ax.xaxis.set_major_locator(FixedLocator((lons - lon0) * metres_per_deg_lon))
    ax.yaxis.set_major_locator(FixedLocator((lats - lat0) * metres_per_deg_lat))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{lon0 + x / metres_per_deg_lon:.4f}°E"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{lat0 + y / metres_per_deg_lat:.4f}°N"))
    ax.minorticks_off()
    ax.set_xlabel("longitudine")
    ax.set_ylabel("latitudine")
    x0, y0 = xmin + 0.04 * (xmax - xmin), ymin + 0.05 * (ymax - ymin)
    ax.plot([x0, x0 + 50], [y0, y0], color="black", lw=5, solid_capstyle="butt")
    ax.plot([x0, x0 + 50], [y0, y0], color="white", lw=3, solid_capstyle="butt")
    ax.text(x0 + 25, y0 + 0.02 * (ymax - ymin), "50 m", ha="center", va="bottom", fontsize=9, color="white",
            fontweight="bold")


def landing_map(cell_clouds, summary, heading, launch, houses, path):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 9))
    background(ax)
    draw_houses(ax, *houses)
    for (h, direction, speed), (points, outline) in cell_clouds.items():
        if h != heading:
            continue
        row = summary[(summary["heading"] == h) & (summary["direction"] == direction) & (summary["speed"] == speed)]
        colour = COLOURS[row["colour"].iloc[0]]
        ax.scatter(points[:, 0] + launch[0], points[:, 1] + launch[1], s=2, color=colour, alpha=0.5, lw=0)
        ax.plot(*np.vstack([outline, outline[:1]]).T + np.array(launch)[:, None], color=colour, lw=1)
    ax.plot(*launch, marker="*", color="white", markeredgecolor=INK, ms=16)
    span = 160
    ax.set_xlim(launch[0] - span, launch[0] + span)
    ax.set_ylim(launch[1] - span, launch[1] + span)
    ax.set_aspect("equal")
    ax.set_xlabel("est [m]")
    ax.set_ylabel("nord [m]")
    ax.set_title(f"Atterraggi e ellissi 3σ di tutte le caselle - heading {heading}°, inclinazione {INCLINATION}°",
                 loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def scan_map(points, area, houses, path, heading=None):
    """Highest gust admitted from every direction at every launch point of the launch area, with the best
    heading of every cell (heading None) or with one heading for all the cells."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Polygon as PolygonPatch
    from scipy import ndimage

    fig, ax = plt.subplots(figsize=(11, 8))
    background(ax)
    draw_houses(ax, *houses)
    levels = [0, *SPEEDS]
    cmap = ListedColormap(["#d03b3b", "#f0a35e", "#f2d36b", "#bfe3a0", "#7fcf9f", "#3fb28a", "#127a5a"][:len(levels)])
    norm = BoundaryNorm(np.arange(-0.5, len(levels)), cmap.N)
    # The launch points are on a regular grid: one transparent cell each, cut on the border of the launch area
    column = "admitted" if heading is None else f"admitted_{heading}"
    grid = points.assign(level=[levels.index(v) for v in points[column]]).pivot(index="north", columns="east",
                                                                                  values="level")
    east, north = grid.columns.to_numpy(), grid.index.to_numpy()
    # Cells without a point (centre just outside the area) take the nearest point, so the clipped border is full
    values = grid.to_numpy()
    nearest = ndimage.distance_transform_edt(np.isnan(values), return_distances=False, return_indices=True)
    mesh = ax.pcolormesh(np.append(east, east[-1] + GRID_STEP) - GRID_STEP / 2,
                         np.append(north, north[-1] + GRID_STEP) - GRID_STEP / 2,
                         values[tuple(nearest)], cmap=cmap, norm=norm, lw=0,
                         antialiased=False, rasterized=True)
    outline = PolygonPatch(np.array(area.exterior.coords), closed=True, fill=False, ec="white", lw=1.2)
    ax.add_patch(outline)
    mesh.set_clip_path(outline)
    bar = fig.colorbar(mesh, ax=ax, ticks=range(len(levels)), shrink=0.8)
    bar.ax.set_yticklabels([f"{v * 3.6:.0f} km/h" if v else "nessuna" for v in levels])
    bar.ax.minorticks_off()
    bar.set_label("raffica massima ammessa da tutte le direzioni")
    xmin, ymin, xmax, ymax = area.bounds
    ax.set_xlim(xmin - 90, xmax + 90)
    ax.set_ylim(ymin - 60, ymax + 90)
    ax.set_aspect("equal")
    lat_lon_axes(ax)
    ax.set_title("Raffica massima ammessa da tutte le direzioni: "
                 + ("heading migliore per ogni casella" if heading is None else f"rampa heading {heading}°")
                 + f", inclinazione {INCLINATION}°", loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def tables(launch=None):
    """Tables and maps. launch = (east, north) of the rail; None = the best point of the launch area (or the
    launch point of launch_site.csv when there is no launch area). The tables of a point given with launch
    go in the subfolder launch_<east>E_<north>N."""
    impacts = pd.read_csv(IMPACTS)
    footprints, zone, osm, line, inhabited = houses_zone()
    houses = (footprints, zone, line, inhabited)
    cell_clouds = clouds(impacts)
    area = launch_area()
    out = RUN_DIR if launch is None else RUN_DIR / f"launch_{launch[0]:+.0f}E_{launch[1]:+.0f}N"
    out.mkdir(exist_ok=True)
    if area is not None:
        print("Scanning the launch area...")
        points = scan(cell_clouds, zone, area)
        if launch is None:
            points.round(3).to_csv(RUN_DIR / "launch_points.csv", index=False)
            best = points.sort_values(["admitted", "margin"], ascending=False).iloc[0]
            launch = (float(best["east"]), float(best["north"]))
        scan_map(points, area, houses, out / "launch_points.png")
        for heading in HEADINGS:
            scan_map(points, area, houses, out / f"launch_points_heading{heading}.png", heading)
    launch = launch or (0.0, 0.0)
    lat, lon = to_lat_lon(*launch)
    summary = evaluate(cell_clouds, zone, launch)
    summary.round(3).to_csv(out / "summary.csv", index=False)
    best = best_heading(summary)
    admitted, margin = admitted_wind(best)
    config = json.loads(CONFIG.read_text()) if CONFIG.exists() else configuration()
    info = {"config": f"Geometria: {config['geometry']}, Motore: {config['motor']}, Aerodinamica: "
                      f"{config['aerodynamics']}, Ritardo: {LAG_TOTAL:g} s",
            "launch_text": f"{lat:.6f} N, {lon:.6f} E"}
    for heading in HEADINGS:
        lookup_table(summary[summary["heading"] == heading],
                     f"FRED2.0 - limiti di vento: rampa heading {heading}°, inclinazione {INCLINATION}°",
                     out / f"lookup_heading{heading}.png", info)
        landing_map(cell_clouds, summary, heading, launch, houses, out / f"map_heading{heading}.png")
    lookup_table(best, f"FRED2.0 - limiti di vento con l'heading migliore per ogni casella, inclinazione {INCLINATION}°",
                 out / "lookup_best_heading.png", info, show_heading=True)
    print(f"Launch point {lat:.6f} N {lon:.6f} E ({launch[0]:+.1f} m E, {launch[1]:+.1f} m N): admitted gust "
          f"{admitted} m/s ({admitted * 3.6:.0f} km/h) from every direction, margin {margin:.0f} m -> {out}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tables", action="store_true", help="only tables and maps from impacts.csv")
    parser.add_argument("--launch", type=float, nargs=2, metavar=("EAST", "NORTH"),
                        help="tables for this rail position (m from launch_site.csv) instead of the best one")
    parser.add_argument("--run", help=f"output folder in {SITE_DIR.name}/ (default {RUN_NAME}, from fred_model.py)")
    args = parser.parse_args()
    if args.run:
        set_run(args.run)
    if not args.tables:
        simulate()
    tables(tuple(args.launch) if args.launch else None)


if __name__ == "__main__":
    main()
