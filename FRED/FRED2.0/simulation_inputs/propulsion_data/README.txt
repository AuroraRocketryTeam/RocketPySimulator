dati del motore. il modello legge la cartella scelta in fred_model.py: MOTOR = "SRAD/<ugello>"
- SRAD/: una cartella per ugello del motore sviluppato da noi (BRICO 45): 7mm o 8mm

dentro ogni cartella:
1. thrust_curve.csv: curva di spinta (tempo [s], spinta [N])
2. motor.csv: impulso, tempo di combustione, ugello, grain, massa e inerzie a secco, posizioni misurate dall'uscita dell'ugello verso la camera

il modello deforma la curva di spinta perché duri burn_time e abbia impulso impulse (nella Monte Carlo variano con la loro std).
l'hardware del motore è nella motor_dry_mass ed è escluso dalla massa del razzo.

motori:
- SRAD/7mm: motore del lancio del 23 maggio, curva del test al banco del 21/05/2026 (tagliata con tools/propulsion/thrust_curve/thrust_curve_visualizer.py)
  geometria dal file di propulsione in tools/propulsion/motor_geometry/7mm/; baricentri e inerzie a secco con motor_mass_properties.py; massa a secco pesata
- SRAD/8mm: curva del test al banco del 21/05/2026 ore 20:44 (tools/propulsion/thrust_curve/8mm/); geometria da tools/propulsion/motor_geometry/8mm/; massa a secco stimata dal 7 mm (da pesare)

formato dei file parametri: vedi geometry_data/README.txt
