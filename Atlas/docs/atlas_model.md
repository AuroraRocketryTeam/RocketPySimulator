# `atlas_model.py`: il modello di Atlas

È ciò che definisce il razzo: geometria, motore, recupero, airbrake e sito di lancio. Gli script non costruiscono Atlas da soli, ma lo prendono da qui:
- `montecarlo.py`;
- `reanalysis.py`;
- `tools/recovery/parachute_study.py`.

```python
import atlas_model as model
params = model.load_parameters()                 # tutti i parametri delle versioni scelte
setting = model.nominal(params)                  # oppure model.sample(params, rng) per una run Monte Carlo
env = model.build_environment("c")
flight = model.simulate(setting, env)            # oggetto Flight di RocketPy
```

## 1. Scegliere le versioni

| Costante | Cosa sceglie | File letto |
|---|---|---|
| `GEOMETRY` | versione della geometria | `simulation_inputs/geometry_data/<versione>/geometry.csv` |
| `AERODYNAMICS` | file CD-Mach del razzo | `simulation_inputs/aerodynamic_data/rocket_body/<file>` |
| `MOTOR` | motore (`COTS/<nome>` o `SRAD/<versione>`) | `simulation_inputs/propulsion_data/<motore>/motor.csv` e `thrust_curve.csv` |
| `RECOVERY` | versione del sistema di recupero | `simulation_inputs/recovery_data/<versione>/recovery.csv` |
| `AIRBRAKES` | `None` senza airbrake, oppure la versione | `simulation_inputs/aerodynamic_data/airbrakes/<versione>/airbrakes.csv` e `cd_mach.csv` |
| `LAUNCH_SITE` | sito di lancio | `simulation_inputs/environment_data/<sito>/` |
| `LAUNCH_DATE` | data e ora (UTC) del lancio, `(anno, mese, giorno, ora)` | — |
| `DRAG_FACTOR` | moltiplicatore del CD, `(valore, std)` | — |

I percorsi partono dalla cartella dello script, quindi il modello funziona da qualsiasi cartella venga lanciato.

## 2. Parametri
Ogni file di parametri ha le colonne `name,value,std,unit,note`. `std` è la deviazione standard usata dalla Monte Carlo; 0 = valore fisso.

- **`read_csv(path)`:** legge un file e restituisce `{nome: (valore, std)}`. Le righe che iniziano con `#` sono commenti. Se un valore o una std è `---` (campo da completare, per esempio nei `geometry.csv` scritti da `tools/geometry/ork_positions/`) si ferma e dice quali campi mancano.
- **`load_parameters()`:** unisce in un solo dizionario geometria, motore, recupero, sito di lancio, airbrake (se attivi) e `drag_factor`. Se lo stesso nome compare in due file si ferma con un errore.
- **`nominal(params)`:** un'impostazione con ogni parametro al valore nominale, `{nome: valore}`.
- **`sample(params, rng)`:** un'impostazione casuale. Ogni parametro è estratto da una normale con media `value` e deviazione `std`. Se un ritardo dei paracadute (`drogue_lag`, `main_lag`, `electronics_lag`) esce negativo, l'estrazione si ripete.

Le funzioni delle sezioni seguenti ricevono l'impostazione data da `nominal` o `sample`, un dizionario chiamato `s`, e ne leggono i valori per nome: per esempio `s["fin_span"]`. Per questo aggiungere una riga a un CSV non basta: il nuovo parametro ha effetto solo quando `atlas_model.py` lo legge.

## 3. Logica di apertura dei paracadute: `RecoveryLogic`
Riproduce in Python il codice di bordo che apre i paracadute. RocketPy chiama i due trigger a `sampling_rate` Hz.

- **Drogue:** `drogue_trigger` riconosce l'apogeo quando la velocità verticale resta negativa per almeno `apogee_threshold` secondi di fila. Il tempo lo misura un cronometro interno che avanza di $1/f$ a ogni chiamata, con $f$ = `sampling_rate`. Sul razzo la velocità viene dall'IMU.
- **Main:** `main_trigger` apre quando l'apogeo è stato riconosciuto e la quota è sotto `main_altitude` (AGL). Sul razzo la quota viene dal barometro filtrato con Kalman.

L'oggetto tiene memoria del volo (apogeo riconosciuto, cronometro): ne serve uno nuovo per ogni volo, e `build_rocket` lo crea da sé.

## 4. Atmosfera: `build_environment(weather_data, date)`
Crea l'`Environment` di RocketPy con latitudine, longitudine e quota di `launch_site.csv` e la data `LAUNCH_DATE`.

| `weather_data` | Atmosfera | Dati |
|---|---|---|
| `c` | media della settimana di EuRoC (10–15 ottobre, 2005–2024) all'ora della data | `mean_environment_values.json`, generato con `EnvironmentAnalysis` di RocketPy dai dati Copernicus |
| `e` | ensemble della settimana di EuRoC | `SantaMargarida_Ensemble_09to16oct2010to2024.nc`; il membro si sceglie con `env.select_ensemble_member` |
| `f` | previsione GFS | serve una data futura e la connessione |
| `i` | atmosfera standard (ISA) | — |

Per l'ensemble il dizionario delle variabili è scritto a mano, perché quello di RocketPy non legge il nuovo formato NetCDF4 di Copernicus.

## 5. Motore: `build_motor(s)`
Costruisce il `SolidMotor` con i valori di `motor.csv` e la curva `thrust_curve.csv`.
- **Sistema di riferimento:** posizioni misurate dall'uscita dell'ugello verso la camera (`nozzle_to_combustion_chamber`).
- **Curva di spinta:** `reshape_thrust_curve=(burn_time, impulse)` deforma la curva perché duri `burn_time` e abbia impulso `impulse`. Nella Monte Carlo quindi le std di questi due parametri cambiano durata e spinta di ogni run, lasciando la forma della curva.
- **Massa e inerzie a secco:** `motor_dry_mass` nella posizione `motor_dry_mass_position`, con le inerzie `motor_inertia_11` (perpendicolare all'asse, usata anche per $I_{22}$) e `motor_inertia_33` (attorno all'asse), rispetto al baricentro a secco.
- **Grain:** numero, distanza, densità, raggi, altezza e posizione del baricentro della colonna. RocketPy li usa per calcolare come cambiano massa, baricentro e inerzie del propellente durante la combustione.

## 6. Razzo: `build_rocket(s, env, logic, drogue_lag, main_lag, recovery)`
Riferimento dalla punta dell'ogiva verso la coda (`nose_to_tail`).

1. **Corpo:** raggio, massa e inerzie senza motore (`rocket_dry_mass`, `rocket_dry_inertia_11/33`), baricentro senza motore, CD-Mach di `AERODYNAMICS` sia a motore acceso sia spento, moltiplicato per `drag_factor`.
2. **Rail button:** posizioni dei due pattini e angolo attorno all'asse.
3. **Motore:** montato a `motor_position`, cioè dove sta l'uscita dell'ugello.
4. **Superfici aerodinamiche:**
   - ogiva Von Kármán (`nose_length`, `nose_position`), come in OpenRocket e RASAero;
   - alette trapezoidali (`fin_number`, `fin_span`, `fin_root_chord`, `fin_tip_chord`, `fin_position`, `fin_sweep_angle`, senza calettamento);
   - coda conica (`tail_top_radius`, `tail_bottom_radius`, `tail_length`, `tail_position`).
5. **Paracadute** (solo con `recovery=True`): drogue e main con `cd_s_drogue` e `cd_s_main`, trigger di `RecoveryLogic`, rumore del barometro (`noise_mean`, `noise_std`, `noise_time_correlation`). Il ritardo tra il trigger e il paracadute pieno è `drogue_lag` (o `main_lag`) + `electronics_lag`. Gli argomenti `logic`, `drogue_lag` e `main_lag` servono allo studio dei paracadute per imporre altri valori.
6. **Airbrake** (solo con `AIRBRAKES`): CD in funzione di apertura e Mach da `cd_mach.csv`, area di riferimento e frequenza del controller da `airbrakes.csv`. Il controller li tiene chiusi durante la spinta e sotto `deployment_altitude` (sul livello del mare); sopra li apre a `deployment_level`. A ogni passo salva tempo, apertura e CD.

## 7. Volo: `simulate(s, env, recovery, **rocket_options)`
Costruisce il razzo e lo fa volare con il `Flight` di RocketPy:
- rampa lunga `rail_length`, con `inclination` sull'orizzontale e `heading` rispetto al nord (da `launch_site.csv`);
- `max_time` di 1200 s;
- con gli airbrake `time_overshoot` è disattivato, perché il controller deve essere chiamato a ogni passo di integrazione.

## 8. Accelerazione massima: `max_acceleration_power_on(flight, skip)`
Massima accelerazione a motore acceso, escludendo gli ultimi `skip` secondi (0,1 ms) prima del burnout. Nell'accelerazione RocketPy include la derivata seconda della posizione del baricentro, calcolata per differenze finite su 1 µs. Se la spinta finisce di colpo, quella derivata esplode al burnout quando il solutore mette un punto proprio lì, quindi `flight.max_acceleration_power_on` è completamente fuori scala. Si consiglia l'inserimento di un transitorio breve, 25 ms sono sufficienti, alla fine della thrust curve in modo da evitare questo errore numerico. La funzione resta come sicurezza per curve con un taglio netto.
