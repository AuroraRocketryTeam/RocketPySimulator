dati del sito di lancio, una sotto cartella per versione. in fred_model.py: LAUNCH_SITE = "vx.y"

dentro ogni versione:
1. launch_site.csv: latitudine, longitudine, quota, lunghezza, inclinazione (sull'orizzontale) e heading (dal nord) della rampa
2. file .nc degli ensemble (dati Copernicus)
3. immagine della mappa per il grafico delle ellissi della Monte Carlo

versioni:
- v0_lancio23maggio: aviosuperficie di Villafranca, rampa della simulazione di lancio

il tipo di atmosfera (e = ensemble, f = previsione, i = ISA, m = vento manuale) si sceglie in ogni simulazione.

formato dei file parametri: vedi geometry_data/README.txt
