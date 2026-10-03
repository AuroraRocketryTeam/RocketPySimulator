# Propulsione: simulazione del motore SRAD

`Atlas motor correct 1.0.ipynb` è il notebook di propulsione: dimensiona il motore, ne simula la balistica interna e calcola la curva di spinta. È salvato senza i risultati delle celle, che si rigenerano eseguendolo.

## Come eseguirlo
- **Su Colab**, come lo usa propulsione: serve il Drive del team per i file CD e i dati della prova statica.
- **In locale**, con `run_motor_notebook.py`. Esegue il notebook così com'è e salta solo le parti che funzionano solo su Colab:
  - l'installazione dei pacchetti (cella 0);
  - i dati della prova statica su Drive (celle 35–38);
  - i mount del Drive.

  I file CD del volo RocketPy della cella 28 vengono sostituiti da quello di Atlas v1.4 (opzione `--cd`).

## Ambiente (una volta sola, Debian)
`rocketcea` va compilato. Servono gfortran e un Python con gli header di sviluppo: quello di uv li ha già.

```bash
sudo apt install gfortran
```

```bash
uv venv --python 3.13 ~/Documenti/AuroraRocketry/.venv-propulsione
```

```bash
uv pip install --python ~/Documenti/AuroraRocketry/.venv-propulsione -r Atlas/propulsion/requirements.txt
```

## Uso
Dalla radice della repo:

```bash
~/Documenti/AuroraRocketry/.venv-propulsione/bin/python Atlas/propulsion/run_motor_notebook.py
```

Dura circa 30 s. Opzioni: `--notebook` (un altro notebook), `--output` (cartella dei risultati), `--cd` (file CD-Mach per il volo).

Risultati in `Atlas/propulsion/output/`, che non va su git:

| File | Contenuto |
|---|---|
| `ATLAS_PARAMETERS_*.txt` | geometria e masse del motore, input di `tools/motor_mass_properties.py` |
| `ATLAS_chamber_properties.txt` | proprietà della camera di combustione |
| `thrust_curve.csv` | spinta fino al burnout (`time [s],thrust [N]`), che il notebook calcola ma non salva |
| `*.html` | grafici plotly del notebook |

Per una nuova versione del motore si copiano `ATLAS_PARAMETERS_*.txt` e `thrust_curve.csv` in `simulation_inputs/propulsion_data/SRAD/<versione>/`, poi si calcolano baricentri e inerzie con `tools/motor_mass_properties.py` e si compila `motor.csv`.
