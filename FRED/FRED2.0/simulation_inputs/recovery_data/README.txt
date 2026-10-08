dati del sistema di recupero (paracadute e logica di apertura), una sotto cartella per versione.
il modello legge recovery.csv della versione scelta in fred_model.py: RECOVERY = "vx.y"

recovery.csv contiene:
- CdS del main (un solo paracadute aperto all'apogeo)
- ritardi: dal segnale di espulsione al paracadute aperto (main_lag) e dell'elettronica (electronics_lag)
- logica di apertura: frequenza e discesa continua prima di riconoscere l'apogeo
- rumore del barometro

versioni:
- v0_lancio23maggio: Rocketman 4 ft, valori della simulazione di lancio

formato dei file parametri: vedi geometry_data/README.txt
