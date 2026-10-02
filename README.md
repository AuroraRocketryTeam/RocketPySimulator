# RocketPySimulator

Simulazioni di volo del team Aurora Rocketry con [RocketPy](https://github.com/RocketPy-Team/RocketPy).

## Cartelle
- `Atlas/`: razzo per EuRoC. `Atlas_v1.0/` contiene Monte Carlo, reanalysis, studio paracadute e dati di input; `Airbrake/` lo studio degli airbrake.
- `FRED/`: prototipo per i test flight dell'avionica.
- `Nemesis/`: razzo già lanciato, progetto chiuso.
- `RealTimeSimulation/`: reanalysis sulla telemetria di volo, in sviluppo.
- `Matlab/`: script Matlab per Monte Carlo ed esportazione dei dati, in sviluppo.
- `Borealis/`

Ogni script legge i dati dalla propria cartella `simulation_inputs/` e scrive in `montecarlo_output/`.

## Output
`montecarlo_output/prova/` non va su git: ogni run la sovrascrive. Per salvare dei risultati, prima della run si imposta un `output_dir_name` nuovo e poi si fa il push di quella cartella.
