dati aerodinamici del razzo e degli airbrake.

rocket_body/vx.y/: i file CD-Mach da provare con quella versione della geometria (righe mach,cd senza intestazione).
il modello ne usa uno solo, sia a motore acceso sia spento (per il nostro razzo sono uguali); in atlas_model.py: AERODYNAMICS = "vx.y/<file>.csv"
i file si generano dagli export di RASAero con tools/aerodynamic/cd_mach_rasaero_convert/rasaero_cdmach_generator.py;
qui resta anche il modello RASAero (.CDX1) o OpenRocket da cui vengono.

airbrakes/vx.y/: in atlas_model.py AIRBRAKES = "vx.y" per attivarli, None per toglierli
- cd_mach.csv: CD in funzione di apertura (0-1) e Mach
- airbrakes.csv: area di riferimento, apertura, quota da cui si aprono (sul livello del mare), frequenza del controller

formato dei file parametri: vedi geometry_data/README.txt
