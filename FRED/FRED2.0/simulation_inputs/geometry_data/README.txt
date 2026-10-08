dati della geometria del razzo, una sotto cartella per versione.
il modello legge geometry.csv della versione scelta in fred_model.py: GEOMETRY = "vx.y"

versioni:
- v0_lancio23maggio: valori dello script della simulazione del lancio del 23 maggio (FRED 1.0, configurazione v2.3_super_lite). il .ork usato non è stato trovato.
- v1.0: FRED2.0 (FRED2.0-V1.0.ork)
- v1.1: FRED2.0 con il componente AMI nell'e-bay (FRED2.0-AMI-V1.0.ork)

dentro ogni versione:
1. rocket.ork: il modello OpenRocket di riferimento
2. geometry.csv: massa, inerzie e baricentro del razzo senza motore, posizione del motore, ogiva, alette, coda e rail button
3. openrocket_*.csv (se c'è): export della simulazione OpenRocket (massa, inerzie e baricentro nel tempo)

razzo senza motore: il motore è modellato a parte (propulsion_data), quindi geometry.csv descrive il razzo senza motore.
massa e baricentro si prendono in OpenRocket nella configurazione senza motore; le inerzie da una simulazione con un motorino messo sul baricentro, subito dopo il burnout.
posizioni e forme si ricavano dal .ork con ork_positions.py di Atlas (Atlas/tools/geometry/ork_positions/), che scrive anche un geometry.csv da completare.
attenzione: ork_positions.py non conta le istanze dei rail button (un componente con 2 pattini dà due posizioni uguali): il secondo pattino va corretto a mano.

formato dei file parametri (geometry.csv, motor.csv, recovery.csv, launch_site.csv):
    name,value,std,unit,note
    fin_span,0.12,0.0005,m,
- std = deviazione standard usata dalla Monte Carlo (0 = valore fisso); la reanalysis usa solo value
- le righe che iniziano con # sono commenti (in testa: versione e fonte dei dati)
- --- al posto di un valore = campo da completare
- niente virgole nelle note: il file non si legge più (errore "Expected 5 fields")
- posizioni in metri dalla punta dell'ogiva verso la coda
