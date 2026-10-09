# Da GRIB a netCDF (meteo ERA5)

`grib_to_netcdf.py` converte un GRIB scaricato dal Copernicus CDS (*ERA5 hourly data on pressure levels*) nei file netCDF che legge `fred_model.py`, con gli stessi nomi di variabili dei netCDF del CDS. Se il GRIB contiene sia *Ensemble members* sia *Reanalysis*, scrive due file:

- `<sito>_ensemble_<periodo>.nc` (opzione meteo `e`);
- `<sito>_reanalysis_<periodo>.nc` (opzione meteo `r`).

Li scrive in `simulation_inputs/environment_data/<sito>/`, che deve già esistere con il suo `launch_site.csv`. Serve `pip install cfgrib xarray`; la lettura del GRIB richiede circa un minuto per prodotto.

```bash
python FRED/FRED2.0/tools/environment/grib_to_netcdf/grib_to_netcdf.py FRED/FRED2.0/tools/environment/grib_to_netcdf/Villafranca/Villafranca_20to30oct2022to2025.grib Villafranca 20to30oct2022to2025
```

I GRIB scaricati stanno in `<sito>/` accanto allo script.

Scelte sul CDS: variabili Geopotential, Temperature, U e V component of wind; livelli di pressione da 1000 hPa in su, fino a coprire l'apogeo con margine; area attorno al sito (Nord, Ovest, Sud, Est). Gli ensemble esistono solo alle ore 00, 03, …, 21 UTC.
