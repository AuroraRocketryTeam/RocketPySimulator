cartella che contiene i dati dei siti di lancio, una sotto cartella per sito; in atlas_model.py: LAUNCH_SITE = "santa_margarida"

dentro ogni sotto cartella ci sono:
1. launch_site.csv: latitudine, longitudine, quota, lunghezza, inclinazione e heading della rampa
2. mean_environment_values.json: atmosfera media della settimana di EuRoC (generata con EnvironmentAnalysis di RocketPy)
3. i file .nc degli ensemble (dati Copernicus)
4. l'immagine della mappa per il grafico delle ellissi

il tipo di atmosfera (c, e, f, i) e la data si scelgono nelle simulazioni e in atlas_model.py (LAUNCH_DATE).

formato dei file parametri: vedi geometry_data/README.txt
