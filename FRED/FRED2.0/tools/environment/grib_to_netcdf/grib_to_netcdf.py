"""
Weather files of a launch site from a GRIB downloaded from the Copernicus CDS (ERA5 hourly data on
pressure levels), converted to netCDF in the same layout as the CDS netCDF downloads, which
fred_model.py reads.

The GRIB can hold the two ERA5 products, which go in two files:
- ensemble members (stream "enda": 10 members, 0.5 deg grid, every 3 hours) -> <site>_ensemble_<period>.nc
- reanalysis (stream "oper": one member, 0.25 deg grid, every hour)          -> <site>_reanalysis_<period>.nc
A product missing in the GRIB is skipped. The files are written in simulation_inputs/environment_data/<site>/.

Needs cfgrib and xarray (pip install cfgrib xarray). Reading the GRIB takes about a minute per product.

Usage:
    python FRED/FRED2.0/tools/environment/grib_to_netcdf/grib_to_netcdf.py <file>.grib <site> <period>
    e.g. ... Villafranca/Villafranca_20to30oct2022to2025.grib Villafranca 20to30oct2022to2025
"""
import argparse
from pathlib import Path

import xarray as xr

FRED_DIR = Path(__file__).resolve().parents[3]
PRODUCTS = {"enda": "ensemble", "oper": "reanalysis"}


def convert(grib, stream):
    """One ERA5 product of the GRIB, with the names of the CDS netCDF files."""
    try:
        data = xr.open_dataset(grib, engine="cfgrib", backend_kwargs={
            "indexpath": "", "filter_by_keys": {"stream": stream, "stepType": "instant"}})
    except Exception as error:
        print(f"- {PRODUCTS[stream]}: not in the file ({error})")
        return None
    if not data.data_vars:
        print(f"- {PRODUCTS[stream]}: not in the file")
        return None
    data = data.drop_vars([name for name in ("step", "number") if name in data.coords and name not in data.dims])
    data = data.swap_dims({"time": "valid_time"}).drop_vars("time").rename({"isobaricInhPa": "pressure_level"})
    data["pressure_level"].attrs.update(long_name="pressure", units="hPa", standard_name="air_pressure")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("grib", type=Path, help="GRIB downloaded from the CDS")
    parser.add_argument("site", help="folder in simulation_inputs/environment_data/")
    parser.add_argument("period", help="part of the file names, e.g. 20to30oct2022to2025")
    args = parser.parse_args()

    output = FRED_DIR / "simulation_inputs" / "environment_data" / args.site
    if not output.is_dir():
        raise SystemExit(f"{output} does not exist: create the site folder with its launch_site.csv first")
    for stream, product in PRODUCTS.items():
        data = convert(args.grib, stream)
        if data is None:
            continue
        path = output / f"{args.site}_{product}_{args.period}.nc"
        data.to_netcdf(path)
        times = data["valid_time"].values
        print(f"- {product}: {dict(data.sizes)}, from {times.min()} to {times.max()}, "
              f"pressure levels {data['pressure_level'].values.tolist()} hPa -> {path}")


if __name__ == "__main__":
    main()
