dati del motore. il modello legge la cartella scelta in atlas_model.py: MOTOR = "COTS/<motore>" oppure "SRAD/vx.y"
- COTS/: una cartella per motore commerciale (nome del motore)
- SRAD/: una cartella per versione del motore sviluppato da noi

dentro ogni cartella:
1. thrust_curve.csv: curva di spinta (tempo [s], spinta [N])
2. motor.csv: impulso, tempo di combustione, ugello, grain, massa e inerzie a secco, posizioni misurate dall'uscita dell'ugello verso la camera

il modello deforma la curva di spinta perché duri burn_time e abbia impulso impulse (nella Monte Carlo variano con la loro std).
massa a secco: nei COTS l'hardware del motore è dentro la massa del razzo (motor_dry_mass circa zero);
negli SRAD è nella motor_dry_mass ed è escluso dalla massa del razzo. la geometria va scelta di conseguenza.
per gli SRAD: curva di spinta da tools/propulsion/thrust_curve/, massa e inerzie da tools/propulsion/motor_geometry/

formato dei file parametri: vedi geometry_data/README.txt
