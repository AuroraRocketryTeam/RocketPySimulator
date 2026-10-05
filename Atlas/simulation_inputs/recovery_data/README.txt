dati del sistema di recupero (paracadute e logica di apertura), una sotto cartella per versione (vx.y).
il modello legge recovery.csv della versione scelta in atlas_model.py: RECOVERY = "vx.y"

recovery.csv contiene:
- CdS di drogue e main
- ritardi: dal segnale di espulsione al paracadute aperto (drogue_lag, main_lag) e dell'elettronica (electronics_lag)
- logica di apertura: frequenza, discesa continua prima di riconoscere l'apogeo, quota del main (AGL)
- rumore del barometro

formato dei file parametri: vedi geometry_data/README.txt
