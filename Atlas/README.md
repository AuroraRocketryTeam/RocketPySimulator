# Atlas

Razzo per EuRoC. Tutte le simulazioni usano lo stesso modello, `atlas_model.py`.

## Scegliere le versioni
In testa ad `atlas_model.py`, per esempio:

```python
GEOMETRY = "v1.6"                                   # simulation_inputs/geometry_data/<versione>/
AERODYNAMICS = "v1.4/CD_Mach_Test_Atlas_v_1.2_SDRAD_cd_mach.csv"   # simulation_inputs/aerodynamic_data/rocket_body/<file>
MOTOR = "SRAD/v1.0"                                 # simulation_inputs/propulsion_data/<motore>/
RECOVERY = "v1.0"                                   # simulation_inputs/recovery_data/<versione>/
AIRBRAKES = None                                    # None = senza airbrake, oppure "v1.0"
LAUNCH_SITE = "santa_margarida"                     # simulation_inputs/environment_data/<sito>/: santa_margarida o rovigo
LAUNCH_DATE = (2024, 10, 11, 12)                    # (anno, mese, giorno, ora UTC)
FORECAST_MODEL = "icon_eu"                          # modello della previsione Open-Meteo (meteo f)
```

I valori stanno nei CSV delle cartelle in `simulation_inputs/` (formato in `simulation_inputs/geometry_data/README.txt`). Come il modello li usa è spiegato in [docs/atlas_model.md](docs/atlas_model.md).

## Cartelle
- `atlas_model.py`, `montecarlo.py`, `reanalysis.py`: modello e simulazioni (le opzioni sono in testa a ogni script).
- `docs/`: documentazione dei tre script: [atlas_model.md](docs/atlas_model.md), [montecarlo.md](docs/montecarlo.md), [reanalysis.md](docs/reanalysis.md).
- `simulation_inputs/`: dati di input versionati; dentro `vx.y/` ci sono solo i file che legge `atlas_model.py`. I file letti o scritti dagli strumenti stanno nella cartella dello strumento.
- `simulation_output/`: risultati delle simulazioni.
  - `montecarlo_output/<output_dir_name>/`: Monte Carlo e studio dei paracadute; `results.txt` riassume versioni usate, media e deviazione standard di ogni grandezza. Per salvare su git i risultati di una Monte Carlo si usa un `output_dir_name` nuovo; `prova` non va su git.
  - `reanalysis_output/`: traiettoria `.kml` della reanalysis.
- `tools/`: strumenti divisi per argomento, ognuno con i suoi file e la sua documentazione.
  - `geometry/ork_positions/ork_positions.py`: posizioni di tutti i componenti dal file OpenRocket e valori per `geometry.csv`, confrontati con quelli in uso (spiegazione nel [README](tools/geometry/ork_positions/README.md)).
  - `aerodynamic/cd_mach_rasaero_convert/rasaero_cdmach_generator.py`: converte gli export di RASAero (in `<versione>/` accanto allo script) in file CD-Mach per `simulation_inputs/` (spiegazione nel [README](tools/aerodynamic/cd_mach_rasaero_convert/README.md)).
  - `propulsion/motor_geometry/motor_mass_properties.py`: baricentri e inerzie di un motore SRAD dal txt di propulsione, con il disegno della sezione; txt e risultati in `<versione>/` accanto allo script (spiegazione in [motor_mass_properties.md](tools/propulsion/motor_geometry/motor_mass_properties.md)).
  - `propulsion/thrust_curve/`: notebook di propulsione e `run_motor_notebook.py` per eseguirlo in locale e salvare la curva di spinta (istruzioni nel [README](tools/propulsion/thrust_curve/README.md)).
  - `recovery/parachute_study.py`: studio dei paracadute al variare di massa e ritardi di apertura (`--help` per le opzioni); grafici e report con `parachute_study_plots.py`.
  - `recovery/parachute_quick_check.py`: verifica rapida dei requisiti EuRoC con la velocità terminale.
  - `mass_analysis/`: confronto di massa e CG tra RocketPy e OpenRocket.
  - `others/pickle_opener.py`: apre un grafico salvato in `.pickle`; `others/compare_plot_saver.py` salva i grafici di confronto della Monte Carlo.
- `Airbrake/`: vecchio studio degli airbrake.

## Meteo
`weather_data` in testa a `montecarlo.py` e `reanalysis.py`: `c` media della settimana di EuRoC, `e` ensemble, `f` previsione, `i` ISA.

La previsione viene da [Open-Meteo](https://open-meteo.com) per il giorno e l'ora UTC di `LAUNCH_DATE`:
- la prima simulazione scarica `<sito>_forecast_<modello>_<AAAAMMGG>.json` nella cartella del sito e le successive lo riusano: **per una previsione più recente va cancellato**;
- `FORECAST_MODEL`: `icon_d2` per le ultime 48 ore (solo Europa centrale: Rovigo sì, Santa Margarida no), `icon_eu` fino a 5 giorni, `ecmwf_ifs025` fino a 15 giorni come tendenza;
- l'Italia è a UTC+2 con l'ora legale e a UTC+1 dall'ultima domenica di ottobre.

I dettagli sono in [docs/atlas_model.md](docs/atlas_model.md), sezione 4.

Gli script si lanciano dalla radice della repo o da qualsiasi cartella: i percorsi sono relativi alla posizione dello script.
