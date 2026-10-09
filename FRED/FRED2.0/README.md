# FRED2.0

Razzo di prova dell'avionica, con motore SRAD BRICO 45 e lancio a Villafranca. Tutte le simulazioni usano lo stesso modello, `fred_model.py`, costruito come quello di Atlas.

## Scegliere le versioni
In testa a `fred_model.py`, per esempio:

```python
GEOMETRY = "v0_lancio23maggio"                      # simulation_inputs/geometry_data/<versione>/
AERODYNAMICS = "v0_lancio23maggio"                  # simulation_inputs/aerodynamic_data/<versione>/
MOTOR = "SRAD/7mm"                                  # simulation_inputs/propulsion_data/<motore>/
RECOVERY = "v0_lancio23maggio"                      # simulation_inputs/recovery_data/<versione>/
LAUNCH_SITE = "Villafranca"                        # simulation_inputs/environment_data/<sito>/
LAUNCH_DATE = (2025, 10, 23, 14)                    # (anno, mese, giorno, ora UTC)
CLIMATE = "20to30oct2010to2025"                    # meteo climatologico: <sito>_surface_<periodo>.csv
```

`v0_lancio23maggio` contiene gli input della simulazione del lancio del 23 maggio 2026 (FRED 1.0); il motore del lancio è `SRAD/7mm`. Le versioni successive sono `vx.y`. I valori stanno nei CSV delle cartelle in `simulation_inputs/` (formato in `simulation_inputs/geometry_data/README.txt`).

## Cartelle
- `fred_model.py`, `montecarlo.py`, `reanalysis.py`: modello e simulazioni (le opzioni sono in testa a ogni script). Meteo: `c` climatologico (vento ERA5 a 10 m e 100 m: la Monte Carlo pesca un giorno e un'ora a caso per ogni simulazione), `e` ensemble e `r` reanalysis ERA5 (livelli di pressione, senza dati sotto circa 130 m), `f` previsione, `i` ISA, `m` vento manuale (`MANUAL_WIND` in `fred_model.py`). I file sono in `simulation_inputs/environment_data/<sito>/`.
- `simulation_inputs/`: dati di input versionati; dentro ogni versione ci sono solo i file che legge `fred_model.py`. I file letti o scritti dagli strumenti stanno nella cartella dello strumento.
- `simulation_output/`: risultati delle simulazioni.
  - `montecarlo_output/<output_dir_name>/`: Monte Carlo. Per salvare su git i risultati si usa un `output_dir_name` nuovo; `prova` non va su git.
  - `reanalysis_output/`: traiettoria `.kml` della reanalysis.
- `tools/`: strumenti divisi per argomento.
  - `aerodynamic/cd_mach_rasaero_convert/<versione>/`: export di RASAero da cui vengono i CD.
  - `propulsion/thrust_curve/`: dati dei test al banco (`7mm/`, `8mm/`) e `thrust_curve_visualizer.py` per tagliarli.
  - `propulsion/motor_simulator/`: simulatore del motore SRAD del team propulsione.
  - `propulsion/motor_geometry/motor_mass_properties.py`: massa, baricentri e inerzie del motore dal file dei parametri di propulsione (`7mm/`, `8mm/`), con il disegno della sezione (come in Atlas).
  - `environment/grib_to_netcdf/grib_to_netcdf.py`: converte i GRIB ERA5 a livelli di pressione scaricati dal Copernicus CDS nei netCDF di ensemble e reanalysis.
  - `environment/surface_wind/surface_wind.py`: dal GRIB ERA5 single levels scrive il meteo climatologico vicino al suolo nel punto della rampa e il grafico del vento 0-150 m.
  - `others/pickle_opener.py`: apre un grafico salvato in `.pickle`; `others/compare_plot_saver.py` salva i grafici di confronto della Monte Carlo.

Le posizioni dal file OpenRocket si leggono con `Atlas/tools/geometry/ork_positions/ork_positions.py`. Gli script si lanciano da qualsiasi cartella: i percorsi sono relativi alla posizione dello script.

La documentazione degli script di Atlas (`Atlas/docs/`) vale anche qui, tranne il paracadute: FRED2.0 ne ha uno solo, aperto all'apogeo.
