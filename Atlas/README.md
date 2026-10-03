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

## Script
Da lanciare dalla cartella `Atlas/` o dalla radice della repo; le opzioni sono in testa a ogni script.

- `montecarlo.py`: Monte Carlo, risultati in `montecarlo_output/<output_dir_name>/`.
- `reanalysis.py`: un volo con i valori nominali, traiettoria `.kml` in `reanalysis_output/`.
- `parachute_study.py`: studio dei paracadute al variare di massa e ritardi di apertura (`--help` per le opzioni); grafici e report con `parachute_study_plots.py`.
- `tools/`:
  - `parachute_quick_check.py`: verifica rapida dei requisiti EuRoC con la velocità terminale;
  - `mass_analysis/`: confronto di massa e CG tra RocketPy e OpenRocket;
  - `pickle_opener.py`: apre un grafico salvato in `.pickle`;
  - `importcsv.py`: converte gli export di RASAero in file CD-Mach (`python tools/importcsv.py <export>.CSV`, `--help` per le opzioni);
  - `motor_mass_properties.py`: baricentri e inerzie di un motore SRAD dal txt di propulsione, con il disegno della sezione (spiegazione in [docs/motor_mass_properties.md](docs/motor_mass_properties.md)).
- `propulsion/`: notebook di propulsione del motore SRAD e `run_motor_notebook.py` per eseguirlo in locale e salvare la curva di spinta (istruzioni in [propulsion/README.md](propulsion/README.md)).

Per salvare su git i risultati di una Monte Carlo si usa un `output_dir_name` nuovo; `prova` non va su git.
