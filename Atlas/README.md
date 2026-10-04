# Atlas

Razzo per EuRoC. Tutte le simulazioni usano lo stesso modello, `atlas_model.py`.

## Scegliere le versioni
In testa ad `atlas_model.py`:

```python
GEOMETRY = "v1.3"                                   # simulation_inputs/geometry_data/<versione>/
AERODYNAMICS = "v1.3/CD_Test_45_square.csv"         # simulation_inputs/aerodynamic_data/rocket_body/<file>
MOTOR = "COTS/Cesaroni_Pro75_9977M2245"             # simulation_inputs/propulsion_data/<motore>/
RECOVERY = "v1.0"                                   # simulation_inputs/recovery_data/<versione>/
AIRBRAKES = None                                    # None = senza airbrake, oppure "v1.0"
LAUNCH_SITE = "santa_margarida"                     # simulation_inputs/environment_data/<sito>/
```

I valori stanno nei CSV delle cartelle in `simulation_inputs/` (formato in `simulation_inputs/geometry_data/README.txt`).

## Cartelle
- `atlas_model.py`, `montecarlo.py`, `reanalysis.py`: modello e simulazioni (le opzioni sono in testa a ogni script).
- `simulation_inputs/`: dati di input versionati; dentro `vx.y/` ci sono solo i file che legge `atlas_model.py`. I file letti o scritti dagli strumenti stanno nella cartella dello strumento.
- `simulation_output/`: risultati delle simulazioni.
  - `montecarlo_output/<output_dir_name>/`: Monte Carlo e studio dei paracadute. Per salvare su git i risultati di una Monte Carlo si usa un `output_dir_name` nuovo; `prova` non va su git.
  - `reanalysis_output/`: traiettoria `.kml` della reanalysis.
- `tools/`: strumenti divisi per argomento, ognuno con i suoi file e la sua documentazione.
  - `aerodynamic/cd_mach_rasaero_convert/importcsv.py`: converte gli export di RASAero (in `<versione>/` accanto allo script) in file CD-Mach per `simulation_inputs/` (`-o` per il file di uscita, `--help` per le opzioni).
  - `propulsion/motor_geometry/motor_mass_properties.py`: baricentri e inerzie di un motore SRAD dal txt di propulsione, con il disegno della sezione; txt e risultati in `<versione>/` accanto allo script (spiegazione in [motor_mass_properties.md](tools/propulsion/motor_geometry/motor_mass_properties.md)).
  - `propulsion/thrust_curve/`: notebook di propulsione e `run_motor_notebook.py` per eseguirlo in locale e salvare la curva di spinta (istruzioni nel [README](tools/propulsion/thrust_curve/README.md)).
  - `recovery/parachute_study.py`: studio dei paracadute al variare di massa e ritardi di apertura (`--help` per le opzioni); grafici e report con `parachute_study_plots.py`.
  - `recovery/parachute_quick_check.py`: verifica rapida dei requisiti EuRoC con la velocità terminale.
  - `mass_analysis/`: confronto di massa e CG tra RocketPy e OpenRocket.
  - `others/pickle_opener.py`: apre un grafico salvato in `.pickle`; `others/compare_plot_saver.py` salva i grafici di confronto della Monte Carlo.
- `Airbrake/`: vecchio studio degli airbrake.

Gli script si lanciano dalla radice della repo o da qualsiasi cartella: i percorsi sono relativi alla posizione dello script.
