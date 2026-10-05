# `montecarlo.py`: simulazione Monte Carlo di Atlas

Consente di realizzare molti voli con parametri variabili attorno a una media. Geometria, aerodinamica, motore, recupero e sito di lancio vengono da `atlas_model.py` (vedi [atlas_model.md](atlas_model.md)).

## 1. Uso
```bash
python Atlas/montecarlo.py
```


| Opzione | Significato |
|---|---|
| `output_dir_name` | nome della cartella dei risultati in `simulation_output/montecarlo_output/`; se esiste già chiede se sovrascriverla |
| `number_of_simulations` | numero di run |
| `weather_data` | atmosfera: `c` media della settimana di EuRoC, `e` ensemble, `f` previsione GFS, `i` ISA |
| `seed` | `None` = run diverse ogni volta; un intero = stesse run a ogni lancio |
| `multiple_core` | `True` = run in parallelo su tutti i core, `False` = su un core solo |
| `ballistic` | `True` = voli senza paracadute |
| `show_dispersion_graph` | mostra a schermo istogrammi, mappa e sensibilità (vengono salvati comunque) |
| `show_compare_graph` | mostra i grafici di confronto dei voli |
| `save_compare_graph` | salva i grafici di confronto in `comparison/` |
| `sensitivity_analysis` | analisi di sensibilità (sezione 5); servono almeno 50 run |

La cartella `prova` non va su git. Per salvare dei risultati si usa un `output_dir_name` nuovo e si fa il push di quella cartella.

## 2. Come funziona
1. **Semi casuali.** Ogni run ha il suo generatore di numeri casuali, con un seme proprio. I semi nascono tutti da `seed` (con `SeedSequence` di numpy), che li rende indipendenti tra loro. Così:
   - con `seed` intero si ottengono a ogni lancio esattamente le stesse run, anche in parallelo e in qualsiasi ordine finiscano;
   - con `seed = None` le run cambiano a ogni lancio.
2. **Estrazione dei parametri.** Con il suo generatore, la run chiama `model.sample`. Ogni parametro con std > 0 viene estratto da una distribuzione normale con media il valore nominale e deviazione la sua std; quelli con std = 0 restano al valore nominale. Con l'atmosfera ensemble la run sceglie anche un membro a caso.
3. **Volo.** Simula il volo con `model.simulate` e ne estrae i risultati (sezione 3).
4. **Errori.** Se il volo dà errore, impostazione ed errore finiscono in `Atlas.disp_errors.txt` e la run è scartata.

Con `multiple_core = True` le run girano in parallelo, un processo per core. Con `False`, oppure con `show_compare_graph` o `save_compare_graph` attivi, girano una dopo l'altra nel processo principale, quindi più lentamente: i grafici di confronto hanno bisogno di tutti gli oggetti `Flight`, che restano solo nel processo principale.

Il parallelo funziona su tutti i sistemi. Su Linux e macOS i processi partono come copie di quello principale (`fork`). Su Windows ogni processo rilegge da capo lo script (`spawn`), quindi l'avvio è un po' più lento.

## 3. Risultati di ogni run
| Chiave | Cosa è | Unità |
|---|---|---|
| `out_of_rail_time`, `out_of_rail_velocity` | istante e velocità all'uscita dalla rampa | s, m/s |
| `max_velocity` | velocità massima | m/s |
| `max_acceleration` | accelerazione massima a motore acceso, senza il picco numerico al burnout (`model.max_acceleration_power_on`); su tutto il volo il massimo sarebbe lo strappo del main | m/s² |
| `max_aerodynamic_drag`, `max_aerodynamic_lift` | forze aerodinamiche massime | N |
| `max_aerodynamic_spin_moment`, `max_aerodynamic_bending_moment` | momenti aerodinamici massimi | N·m |
| `apogee_time`, `apogee_altitude` | istante e quota dell'apogeo (AGL) | s, m |
| `apogee_x`, `apogee_y` | posizione dell'apogeo (est, nord) rispetto alla rampa | m |
| `impact_time`, `impact_x`, `impact_y`, `impact_velocity` | istante, posizione e velocità all'atterraggio | s, m, m/s |
| `initial_static_margin`, `out_of_rail_static_margin`, `final_static_margin` | margine statico a t = 0, all'uscita dalla rampa e al burnout | calibri |
| `number_of_events` | paracadute aperti | — |
| `drogue_triggerTime`, `drogue_inflated_time`, `drogue_inflated_velocity` | trigger del drogue, drogue pieno (trigger + ritardo) e velocità in quell'istante | s, s, m/s |
| `execution_time` | tempo di CPU della run | s |

## 4. File prodotti
In `simulation_output/montecarlo_output/<output_dir_name>/`:

| File | Contenuto |
|---|---|
| `Atlas.disp_inputs.json` | l'impostazione di ogni run, una riga per run |
| `Atlas.disp_outputs.json` | i risultati di ogni run, sulla stessa riga dell'impostazione |
| `Atlas.disp_errors.txt` | le run fallite, con l'errore |
| `dispersion/svg/`, `dispersion/pickle/` | un istogramma per grandezza |
| `launch_site/` | mappa del sito con apogei, atterraggi ed ellissi |
| `comparison/` | grafici di confronto dei voli (con `save_compare_graph`) |
| `sensitivity/` | analisi di sensibilità (con `sensitivity_analysis`) |

I `.pickle` sono le figure matplotlib intere: si riaprono, anche per ridimensionarle, con `tools/others/pickle_opener.py`.

## 5. Grafici e analisi
**Istogrammi.** Per ogni grandezza della tabella di `all_plots`:
- istogramma normalizzato con $\sqrt{N}$ barre, dove $N$ è il numero di run;
- la normale con media $\mu$ e deviazione standard $\sigma$ stimate dai dati (`scipy.stats.norm.fit`);
- $\mu$ e $\sigma$ scritte nel grafico e stampate a terminale.

**Ellissi di dispersione.** Per gli apogei e per gli atterraggi:
1. si calcola la matrice di covarianza delle posizioni (est, nord);
2. i suoi autovalori $\lambda_1 \ge \lambda_2$ e il primo autovettore danno assi e orientamento: l'ellisse a $k\sigma$ ha assi $2k\sqrt{\lambda_1}$ e $2k\sqrt{\lambda_2}$ ed è centrata nella media;
3. si disegnano le ellissi per $k$ = 1, 2, 3 sopra la mappa del sito, centrata sulla rampa (finestra di 4 × 3 km).
**Quanti punti stanno dentro.** Per una sola variabile, entro ±1σ dalla media cade il 68% dei valori (95% entro 2σ, 99,7% entro 3σ). Con due variabili insieme (est e nord) un punto sta dentro l'ellisse solo se non è troppo lontano dal centro in nessuna delle due direzioni, quindi ne restano dentro meno. La frazione dentro l'ellisse a $k\sigma$ è $1 - e^{-k^2/2}$:

| Ellisse | Punti dentro |
|---|---|
| 1σ | 39% |
| 2σ | 86% |
| 3σ | 99% |

Per esempio, per un'area che contenga il 95% degli atterraggi serve l'ellisse a circa 2,45σ.

**Analisi di sensibilità.** Usa il `SensitivityModel` di RocketPy: un modello lineare che stima quanto della varianza di apogeo e accelerazione massima dipende da ciascun parametro. Entrano solo i parametri con std > 0. Il modello legge i due file `.json`, per questo impostazione e risultati di una run devono stare sulla stessa riga. Con meno di 50 run viene disattivata.

## 6. Il codice blocco per blocco
**Parametri e stile.** Le opzioni della sezione 1, lo stile dei grafici matplotlib e `loading_bar`, la barra di avanzamento a terminale con tempo medio per run e tempo rimanente.

**`init_worker(weather, keep_flights)`.** Gira una volta in ogni processo: costruisce l'atmosfera, così non va ricostruita a ogni run.

**`run_one(run_seed)`.** Una run: genera l'impostazione dal suo seme, sceglie il membro dell'ensemble se serve, simula, restituisce impostazione, risultati, eventuale errore e (solo se servono i confronti) il `Flight`.

**`flight_results(flight, env, execution_time)`.** Estrae dal `Flight` le grandezze della sezione 3.

**`plot_unit_of_measure` e `plot_graph`.** La prima trasforma le unità (`m/s^2`, `N*m`) nella notazione dei grafici. La seconda disegna, salva e stampa un istogramma.

**`eigsorted` e `launch_site_graph`.** Autovalori e autovettori della covarianza in ordine decrescente; mappa con le ellissi.

**`sensitivity_graphs`.** Analisi di sensibilità e salvataggio dei grafici.

**`main()`.**
1. Stampa versioni del modello e opzioni; disattiva la sensibilità sotto le 50 run.
2. Chiede se sovrascrivere la cartella, se esiste già, e crea le sottocartelle.
3. Lancia le run (in parallelo o nel processo principale) e scrive impostazioni, risultati ed errori man mano che arrivano.
4. Stampa run riuscite, errori e tempi.
5. Grafici di confronto, istogrammi, mappa e sensibilità.
