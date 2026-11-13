dati dei siti di lancio, una sotto cartella per sito; in atlas_model.py: LAUNCH_SITE = "<sito>"

dentro ogni sito:
1. launch_site.csv: latitudine, longitudine, quota, lunghezza, inclinazione (sull'orizzontale) e heading (dal nord) della rampa
2. mean_environment_values.json: atmosfera media della settimana di EuRoC per ogni ora (generata con EnvironmentAnalysis di RocketPy)
3. file .nc degli ensemble (dati Copernicus)
4. immagine della mappa per il grafico delle ellissi della Monte Carlo (nome e limiti della mappa sono in testa a montecarlo.py)
5. <sito>_forecast_<modello>_<AAAAMMGG>.json: previsione scaricata da Open-Meteo (meteo f), scritta dal modello alla prima
   simulazione del giorno e poi riusata: va cancellata per scaricarne una più recente

siti: santa_margarida (EuRoC), rovigo

il tipo di atmosfera (c = media, e = ensemble, f = previsione Open-Meteo, i = ISA) si sceglie in ogni simulazione;
la data e l'ora UTC in atlas_model.py (LAUNCH_DATE). con l'atmosfera media l'ora deve essere una di quelle nel .json.

formato dei file parametri: vedi geometry_data/README.txt
