# Vento vicino al suolo (ERA5 single levels)

`surface_wind.py` legge un GRIB del Copernicus CDS, dataset *ERA5 hourly data on single levels from 1940 to present*, prodotto *Reanalysis*, variabili *10m u/v-component of wind*, *100m u/v-component of wind*, *2m temperature*, *Surface pressure*. Scrive:

- `simulation_inputs/environment_data/<sito>/<sito>_surface_<periodo>.csv`: un'ora per riga, valori interpolati nel punto della rampa (`launch_site.csv`). È il meteo climatologico (opzione `c`) di `fred_model.py`;
- `<sito>/<periodo>/surface_wind.png`: vento medio dal suolo a 150 m per ogni ora, con il 90° percentile dell'intensità.

```bash
python FRED/FRED2.0/tools/environment/surface_wind/surface_wind.py FRED/FRED2.0/tools/environment/surface_wind/Villafranca/Villafranca_surface_20to30oct2010to2025.grib Villafranca 20to30oct2010to2025
```

Serve `pip install cfgrib xarray`; la lettura del GRIB richiede circa un minuto. I GRIB scaricati stanno in `<sito>/` accanto allo script.

Il profilo tra il suolo e 200 m si costruisce dal vento a 10 m e a 100 m (`fred_model.surface_wind`): intensità con una legge di potenza che passa per i due valori, direzione che ruota dalla prima alla seconda; sotto 10 m e sopra 100 m la stessa legge con l'esponente tra 0 e 0,6, sopra 200 m costante. Temperatura da quella a 2 m con il gradiente standard (−6,5 K/km), pressione da quella al suolo.

Villafranca, 20–30 ottobre 2010–2025, 12–18 UTC (176 giorni, 1232 ore):

| quota | media | mediana | P90 | P95 | P99 | massimo |
|---|---|---|---|---|---|---|
| 10 m | 2,3 m/s | 2,0 | 4,0 | 4,8 | 7,4 | 9,3 |
| 100 m | 3,7 m/s | 3,2 | 6,7 | 7,7 | 12,1 | 13,7 |

Vicino al suolo la direzione media gira nel pomeriggio da NO (12 UTC) a E–SE (17–18 UTC): brezza di mare. Più in alto (livelli di pressione, sopra circa 200 m) il vento resta da SO.
