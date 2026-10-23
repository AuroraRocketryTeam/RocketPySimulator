# Limiti di vento (atterraggio lontano dalle case)

Per ogni heading della rampa, ogni direzione e ogni intensità del vento, una Monte Carlo del volo dice se FRED può atterrare sulle case attorno al sito di lancio. Il risultato sono tabelle di consultazione GO / LIMITE / NO-GO, una per heading.

## Come funziona
- **Configurazione:** le versioni in testa a `fred_model.py` (geometria, motore, aerodinamica, recupero, sito).
- **Una casella** = heading della rampa, direzione e intensità del vento a 10 m. Il vento usa il profilo `mbl` di `fred_model.py`: strato limite a legge di potenza, α = `MANUAL_WIND_BL_ALPHA`, direzione costante con la quota.
- **In ogni volo variano:**
  - il vento attorno ai valori della casella: std `WIND_SPEED_STD` = 0,5 m/s (precisione tipica di un anemometro a coppette amatoriale) e `WIND_DIRECTION_STD` = 8° (la stazione dà 16 settori da 22,5°, che da soli valgono 6,5°);
  - il puntamento della rampa: std `RAIL_STD` = 1,5° su heading e inclinazione, cioè ±3° presi come 2σ;
  - tutti i parametri di razzo, motore e recupero, con le std dei file di `simulation_inputs/`.

  Il ritardo totale fino al paracadute completamente aperto è `LAG_TOTAL` = 1 s.
- **Sul campo** si entra in tabella con la **raffica massima** degli ultimi 10 minuti, non con il vento medio. L'intensità è riferita all'altezza dell'anemometro della stazione: `WIND_REF_HEIGHT` = 7,5 m, il traliccio di A.Li Soccorso. Le colonne sono quindi direttamente la lettura della stazione, in m/s e km/h.
- **Punto di lancio:** spostando la rampa di (e, n), con terreno piatto e lo stesso vento ovunque, ogni atterraggio si sposta di (e, n). Gli atterraggi sono salvati rispetto alla rampa, quindi una sola griglia di voli vale per tutti i punti della zona in cui si può mettere la rampa (`<sito>/launch_area.csv`).
  - Lo script prova un punto ogni `GRID_STEP` m e sceglie quello con la raffica più alta ammessa da tutte le direzioni (GO fino a quella intensità), usando per ogni casella l'heading migliore, che si sceglie sul campo; a parità, vince il margine più grande.
  - Per quel punto fa le tabelle dei tre heading e una tabella unica con l'heading da usare in ogni casella.
  - `--launch E N` fa le tabelle di un altro punto.
- **Le case:** zona abitata allargata di `BUFFER` m.
  - Dove c'è la linea disegnata a mano (`<sito>/houses_line.csv`, case a sinistra nel verso dei vertici), il limite è quella linea.
  - Altrove il limite sono le sagome degli edifici di OpenStreetMap (`<sito>/buildings.geojson`, scritto da `buildings.py`), allargate di `ENVELOPE` m e unite dove le case sono vicine.
  - Per Villafranca la zona arriva a 38 m dalla rampa.
- **I colori:**
  - **NO-GO** (rosso): almeno un atterraggio nella zona delle case; nella casella c'è la % di atterraggi lì.
  - **LIMITE** (giallo): nessun atterraggio nella zona, ma l'ellisse 3σ degli atterraggi la tocca.
  - **GO** (verde): ellisse 3σ fuori dalla zona; nella casella c'è la distanza minima tra l'ellisse e il limite della zona. Dalla linea delle case la distanza è quindi questa più `BUFFER`.
- **Le direzioni del vento** simulate a Villafranca sono **da O a SE passando da S** (O, OSO, SO, SSO, S, SSE, SE): sono le sole che possono portare il razzo verso le case. I venti da E a NO, passando da N, lo portano sui campi, e nella prima corsa i venti da ESE ed E restavano ad almeno 76 m. Il pubblico, a NO a circa 200 m, è oltre la deriva massima (circa 130 m).
- **Le direzioni del vento** sono quelle **da cui arriva** (convenzione meteo). Lo script passa a `fred_model` la direzione verso cui va (+180°). La convenzione è verificata: la deriva sotto il paracadute va sottovento.

## Uso
```bash
python FRED/FRED2.0/tools/safety/wind_limits/buildings.py Villafranca
python FRED/FRED2.0/tools/safety/wind_limits/wind_limits.py
python FRED/FRED2.0/tools/safety/wind_limits/wind_limits.py --tables
```
- `buildings.py` va lanciato una volta per sito: scarica gli edifici entro 1 km dalla rampa. Serve `shapely`.
- `locate_screenshot.py <screenshot> <file>.csv` aggancia uno screenshot satellitare (Google Maps, nord in alto) con una linea gialla disegnata sopra alla foto del sito, e scrive i vertici della linea in metri dalla rampa. È servito per `houses_line.csv` e `launch_area.csv`. Il risultato va controllato su un disegno.
- `wind_limits.py` simula le caselle mancanti e poi fa tabelle e mappe. È **riprendibile**: le caselle già in `impacts.csv` si saltano, e i seed dipendono solo dalla casella. Su un portatile a 2 core servono circa 0,4 s per volo.
- `--tables` rifà solo tabelle e mappe da `impacts.csv`, per esempio dopo aver cambiato `BUFFER`.

Le griglie (heading, inclinazione, direzioni, intensità, voli per casella, margine) si scelgono in testa a `wind_limits.py`, con `RUN_NAME` per la cartella di uscita. Per la rampa a 70° basta `INCLINATION = 70` e un `RUN_NAME` nuovo.

## Uscite in `<sito>/<RUN_NAME>/`
- `impacts.csv`: un volo per riga (punto d'impatto, apogeo, velocità di uscita dalla rampa, seed, eventuale errore).
- `launch_points.csv` / `.png`: tutti i punti provati nella zona della rampa, con la raffica ammessa (con l'heading migliore e con ciascun heading) e il margine.
- `summary.csv`: per il punto scelto, una casella per riga (% nella zona, centro e dispersione degli atterraggi, distanza dell'ellisse, colore).
- `lookup_heading<h>.png`: la tabella di consultazione di ogni heading.
- `lookup_best_heading.png`: la tabella unica, con l'heading da usare in ogni casella.
- `map_heading<h>.png`: atterraggi ed ellissi di tutte le caselle sulla foto, con le case e la zona di margine, per controllare a vista.

## Ipotesi
- Vento costante durante il volo, con la stessa direzione a tutte le quote; α fisso. Le raffiche sono coperte dalla regola di usare la raffica massima.
- Paracadute sempre aperto: il volo balistico (paracadute non aperto) non è considerato.
- La foto di Villafranca è allineata alle sagome OSM con l'extent (−1043, 657, −407, 593) di `montecarlo.py`, ricavato facendo combaciare tetti e sagome. Le verifiche usano solo le coordinate OSM, non la foto.
