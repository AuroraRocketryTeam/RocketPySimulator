curve CD-Mach del razzo, una sotto cartella per versione. il modello ne usa una sola, sia a motore acceso sia spento
(in RASAero power-off e power-on sono uguali). in fred_model.py: AERODYNAMICS = "vx.y"

cd_mach.csv: righe mach,cd senza intestazione, solo angolo d'attacco 0.
gli export di RASAero (in tools/aerodynamic/cd_mach_rasaero_convert/<versione>/) hanno tre blocchi uno dopo l'altro per alfa = 0, 2 e 4 gradi:
qui si tiene solo il primo. quegli export hanno anche la virgola come separatore decimale: vanno riesportati con il punto.

versioni:
- v0_lancio23maggio: CD_power_on_v2.3_TEST.csv usato nella simulazione di lancio (export RASAero CD-Mach_FRED_2.3.CSV)
- v1.0: FRED2.0 (export RASAero CD-mach_FRED2.0_v1.0.csv)

formato dei file parametri: vedi geometry_data/README.txt
