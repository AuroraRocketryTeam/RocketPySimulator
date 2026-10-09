dati dei siti di lancio, una sotto cartella per sito. in fred_model.py: LAUNCH_SITE = "<sito>" e LAUNCH_DATE = (anno, mese, giorno, ora UTC)

dentro ogni sito:
1. launch_site.csv: latitudine, longitudine, quota, lunghezza, inclinazione (sull'orizzontale) e heading (dal nord) della rampa
2. file meteo ERA5 del Copernicus CDS (ERA5 hourly data on pressure levels) in netCDF, uno o più per periodo:
   - <sito>_ensemble_<periodo>.nc: 10 membri, ogni 3 ore (opzione e)
   - <sito>_reanalysis_<periodo>.nc: un membro, ogni ora (opzione r)
   il modello usa il file che contiene LAUNCH_DATE (un'ora presente nel file); se nessun file la contiene si ferma,
   perché RocketPy prenderebbe in silenzio la data più vicina.
   i GRIB scaricati dal CDS si convertono con tools/environment/grib_to_netcdf/grib_to_netcdf.py
3. <sito>_surface_<periodo>.csv: meteo vicino al suolo ERA5 (single levels) nel punto della rampa, un'ora per riga:
   vento a 10 m e 100 m (u10 v10 u100 v100 in m/s), temperatura a 2 m (t2m in K), pressione al suolo (sp in Pa).
   è il meteo climatologico (opzione c): in fred_model.py CLIMATE = "<periodo>" e CLIMATE_HOURS = le ore UTC da usare;
   la Monte Carlo pesca per ogni simulazione un giorno e un'ora a caso, la reanalysis usa il giorno tipico all'ora di LAUNCH_DATE.
   si scrive con tools/environment/surface_wind/surface_wind.py
4. immagine della mappa per il grafico delle ellissi della Monte Carlo

siti:
- Villafranca: aviosuperficie, rampa della simulazione del lancio del 23 maggio 2026
  - ensemble 5-11 maggio 2020-2025, ore 9 / 12 / 15 / 18 UTC, 1000-700 hPa (il nome del file dice 2026 ma i dati arrivano al 2025)
  - ensemble e reanalysis 20-30 ottobre 2022-2025: ensemble ore 12 / 15 / 18 UTC, reanalysis ogni ora 12-18 UTC, 1000-925 hPa (fino a circa 800 m)
  - vicino al suolo (opzione c) 20-30 ottobre 2010-2025, ogni ora 12-18 UTC

il tipo di atmosfera (c = climatologica, e = ensemble, r = reanalysis, f = previsione, i = ISA, m = vento manuale) si sceglie in ogni simulazione.
i file a livelli di pressione (e, r) non hanno il vento sotto il livello di 1000 hPa (circa 130 m a Villafranca): per FRED la c è la più adatta.

formato dei file parametri: vedi geometry_data/README.txt
