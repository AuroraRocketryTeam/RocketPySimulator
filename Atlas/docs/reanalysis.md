# `reanalysis.py`: volo nominale di Atlas

Un solo volo di Atlas con tutti i parametri al valore nominale. Serve per controllare il volo di riferimento prima di una Monte Carlo e per vederne i grafici completi. Geometria, aerodinamica, motore, recupero e sito di lancio vengono da `atlas_model.py` (vedi [atlas_model.md](atlas_model.md)).

## 1. Uso
```bash
python Atlas/reanalysis.py
```

Le opzioni sono in testa al file:

| Opzione | Significato |
|---|---|
| `weather_data` | atmosfera: `c` media della settimana di EuRoC, `e` ensemble, `f` previsione GFS, `i` ISA |
| `ballistic` | `True` = volo senza paracadute |
| `show_graph` | mostra i grafici di RocketPy |
| `print_info` | stampa il riepilogo del volo di RocketPy |
| `export_mass_and_cg` | salva massa e baricentro nel tempo per `tools/mass_analysis/` |

## 2. Cosa fa
1. Costruisce l'atmosfera e l'impostazione nominale (`model.nominal`) e simula il volo.
2. Stampa le versioni di geometria, aerodinamica, motore, recupero e airbrake usate, così il risultato resta riconoscibile.
3. Con `print_info` stampa `flight.info()`: uscita dalla rampa, apogeo, velocità e accelerazione massime, margine statico, eventi dei paracadute, atterraggio.
4. Con `show_graph` mostra:
   - il disegno del razzo e la massa nel tempo;
   - cinematica lineare e angolare;
   - assetto e angolo della traiettoria;
   - traiettoria 3D;
   - stabilità;
   - forze aerodinamiche e forze sui rail button.
5. Salva la traiettoria in `simulation_output/reanalysis_output/trajectory.kml`, da aprire in Google Earth. Le quote sono relative al terreno.
6. Con `export_mass_and_cg` salva massa e baricentro nel tempo in:
   - `tools/mass_analysis/mass/mass_time_rpy/mass_time_rpy_<geometria>.csv`;
   - `tools/mass_analysis/CG/CG_rpy/CG_rpy_<geometria>.csv`.

   Il baricentro è misurato dalla punta dell'ogiva. Questi file servono al confronto con OpenRocket di `tools/mass_analysis/`.

La traiettoria si sovrascrive a ogni lancio: per conservarne una va copiata altrove o committata subito.
