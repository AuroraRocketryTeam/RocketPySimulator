cartella che contiene i dati delle geometrie.
il modello importa la geometria tramite geometry.csv; in atlas_model.py: GEOMETRY = "v1.3"

le sotto cartelle rappresentano le versioni: vx.y

dentro ogni sotto cartella ci sono:
1. rocket.ork: il modello openrocket di riferimento
2. geometry.csv: masse, inerzie, CG, ogiva, alette, coda e rail button
3. openrocket_data.csv (se c'è): dati delle simulazioni openrocket, per esempio massa, inerzie e CG nel tempo

v1.2 non ha geometry.csv: i valori usati con quel modello non sono noti, quindi non è simulabile.

formato dei file parametri (geometry.csv, motor.csv, recovery.csv, airbrakes.csv, launch_site.csv):
    name,value,std,unit,note
    fin_span,0.145,0.0005,m,
- std = deviazione standard usata dalle montecarlo (0 = valore fisso); la reanalysis usa solo value
- le righe che iniziano con # sono commenti (in testa: versione e fonte dei dati)
- i nomi sono quelli che usa atlas_model.py: se ne aggiungi uno nuovo va usato anche lì
