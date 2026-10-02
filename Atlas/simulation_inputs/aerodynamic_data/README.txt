cartella che contiene i dati aerodinamici (CD-Mach) del razzo e degli airbrakes.

rocket_body/vx.y/: i vari file CD-Mach da testare per quella versione della geometria.
il modello ne importa uno solo, usato sia power on che power off (per il nostro razzo sono uguali).
in atlas_model.py: AERODYNAMICS = "v1.3/CD_Test_45_square.csv"

airbrakes/vx.y/:
- cd_mach.csv: CD in funzione di apertura e Mach
- airbrakes.csv: area di riferimento, apertura, quota di apertura, frequenza del controller
in atlas_model.py: AIRBRAKES = "v1.0" per attivarli, None per toglierli

formato dei file parametri: vedi geometry_data/README.txt
