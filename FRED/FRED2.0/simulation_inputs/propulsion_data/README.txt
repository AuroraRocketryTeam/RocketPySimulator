dati del motore. il modello legge la cartella scelta in fred_model.py: MOTOR = "SRAD/vx.y"
- SRAD/: una cartella per versione del motore sviluppato da noi (BRICO 45)

dentro ogni cartella:
1. thrust_curve.csv: curva di spinta (tempo [s], spinta [N])
2. motor.csv: impulso, tempo di combustione, ugello, grain, massa e inerzie a secco, posizioni misurate dall'uscita dell'ugello verso la camera

il modello deforma la curva di spinta perché duri burn_time e abbia impulso impulse (nella Monte Carlo variano con la loro std).
l'hardware del motore è nella motor_dry_mass ed è escluso dalla massa del razzo.

versioni:
- SRAD/v0_lancio23maggio: ugello 7 mm, curva del test al banco del 21/05/2026 (tagliata con tools/propulsion/thrust_curve/thrust_curve_visualizer.py)

formato dei file parametri: vedi geometry_data/README.txt
