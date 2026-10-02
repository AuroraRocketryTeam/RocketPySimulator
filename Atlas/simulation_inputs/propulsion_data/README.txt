cartella che contiene i dati del motore.
il modello importa il motore tramite la cartella scelta in atlas_model.py: MOTOR = "COTS/Cesaroni_Pro75_9977M2245"

le sotto cartelle rappresentano la tipologia del motore COTS - SRAD; al livello inferiore:
- COTS: una cartella per motore (nome del motore)
- SRAD: le versioni vx.y

dentro ogni cartella ci sono:
1. thrust_curve.csv: curva di spinta (tempo [s], spinta [N])
2. motor.csv: impulso, tempo di combustione, ugello, grain, massa e inerzie a secco

formato dei file parametri: vedi geometry_data/README.txt
