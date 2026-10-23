"""
Footprints of the buildings around a launch site, from OpenStreetMap (Overpass API), for wind_limits.py.

Writes <site>/buildings.geojson next to this script: one polygon per building, with the vertices both in
longitude/latitude and in metres east/north of the launch point of launch_site.csv (keys "east", "north").
Run it once per site; run it again only to update the map.

Data (c) OpenStreetMap contributors, ODbL (https://www.openstreetmap.org/copyright).

Usage:
    python FRED/FRED2.0/tools/safety/wind_limits/buildings.py Villafranca
    python FRED/FRED2.0/tools/safety/wind_limits/buildings.py Villafranca --radius 1500
"""
import argparse
import json
import math
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
FRED_DIR = HERE.parents[2]
OVERPASS = "https://overpass-api.de/api/interpreter"
EARTH_RADIUS = 6371000


def local(lon, lat, lon0, lat0):
    """Metres east and north of (lon0, lat0) (flat Earth, fine within a few km)."""
    east = math.radians(lon - lon0) * EARTH_RADIUS * math.cos(math.radians(lat0))
    north = math.radians(lat - lat0) * EARTH_RADIUS
    return round(east, 2), round(north, 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("site", help="folder in simulation_inputs/environment_data/")
    parser.add_argument("--radius", type=float, default=1000, help="m around the launch point (default 1000)")
    args = parser.parse_args()

    launch = pd.read_csv(FRED_DIR / "simulation_inputs" / "environment_data" / args.site / "launch_site.csv",
                         comment="#", skipinitialspace=True, index_col="name")["value"]
    lat0, lon0 = float(launch["latitude"]), float(launch["longitude"])
    query = f'[out:json][timeout:90];way["building"](around:{args.radius:.0f},{lat0},{lon0});out geom;'
    request = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": query}).encode(),
                                     headers={"User-Agent": "AuroraRocketry-FRED-wind-limits/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        elements = json.load(response)["elements"]

    features = []
    for element in elements:
        ring = [(node["lon"], node["lat"]) for node in element["geometry"]]
        features.append({
            "type": "Feature",
            "properties": {"osm_id": element["id"], "building": element.get("tags", {}).get("building"),
                           "east_north": [local(lon, lat, lon0, lat0) for lon, lat in ring]},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
    output = HERE / args.site / "buildings.geojson"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "type": "FeatureCollection",
        "properties": {"source": "OpenStreetMap via Overpass API, (c) OpenStreetMap contributors, ODbL",
                       "downloaded": date.today().isoformat(), "launch_point": [lon0, lat0], "radius_m": args.radius},
        "features": features,
    }))
    distances = sorted(min(math.hypot(e, n) for e, n in f["properties"]["east_north"]) for f in features)
    print(f"{len(features)} buildings within {args.radius:.0f} m, nearest at {distances[0]:.0f} m -> {output}")


if __name__ == "__main__":
    main()
