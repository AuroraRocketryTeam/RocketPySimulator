dati della geometria del razzo, una sotto cartella per versione (vx.y).
il modello legge geometry.csv della versione scelta in atlas_model.py: GEOMETRY = "vx.y"

dentro ogni versione:
1. rocket.ork: il modello OpenRocket di riferimento
2. geometry.csv: massa, inerzie e baricentro del razzo senza motore, posizione del motore, ogiva, alette, coda e rail button
3. openrocket_*.csv (se c'è): export della simulazione OpenRocket (massa, inerzie e baricentro nel tempo)

razzo senza motore: il motore è modellato a parte (propulsion_data), quindi geometry.csv descrive il razzo senza motore.
massa, inerzie e baricentro vengono da una simulazione OpenRocket con un motorino messo sul baricentro, togliendo la sua massa.
posizioni e forme si ricavano dal .ork con tools/geometry/ork_positions/ork_positions.py, che scrive anche un geometry.csv da completare.

formato dei file parametri (geometry.csv, motor.csv, recovery.csv, airbrakes.csv, launch_site.csv):
    name,value,std,unit,note
    fin_span,0.195,0.0005,m,
- std = deviazione standard usata dalla Monte Carlo (0 = valore fisso); la reanalysis usa solo value
- le righe che iniziano con # sono commenti (in testa: versione e fonte dei dati)
- --- al posto di un valore = campo da completare: il modello si ferma e dice quali mancano
- niente virgole nelle note: il file non si legge più (errore "Expected 5 fields")
- i nomi sono quelli che usa atlas_model.py: un parametro nuovo va usato anche lì
- posizioni in metri dalla punta dell'ogiva verso la coda
