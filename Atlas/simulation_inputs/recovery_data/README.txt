cartella che contiene i dati del sistema di recupero (paracadute e logica di apertura).
il modello importa recovery.csv dalla versione scelta in atlas_model.py: RECOVERY = "v1.0"

le sotto cartelle rappresentano le versioni: vx.y

recovery.csv contiene:
- CdS di drogue e main
- ritardi: dal segnale di espulsione al paracadute aperto (drogue_lag, main_lag) e dell'elettronica (electronics_lag)
- logica di apertura: frequenza, soglia di apogeo, quota del main
- rumore del barometro

formato dei file parametri: vedi geometry_data/README.txt
