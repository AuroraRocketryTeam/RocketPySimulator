# `ork_positions.py`: posizioni dei componenti dal file OpenRocket

Legge un file OpenRocket (`.ork`) e stampa:
1. la posizione di ogni componente, da dove a dove si estende, misurata dalla punta dell'ogiva;
2. i valori di posizione e forma che vanno in `geometry.csv`;
3. il confronto con il `geometry.csv` accanto al `.ork`, con `<!>` dove i valori differiscono.

Poi scrive un nuovo `geometry.csv` in `<versione>/` accanto allo script.

Legge solo la geometria scritta nel file (XML, compresso o no): non serve OpenRocket né Java.

```bash
python Atlas/tools/geometry/ork_positions/ork_positions.py Atlas/simulation_inputs/geometry_data/v1.5/rocket.ork
```

Con `--geometry <file>` confronta con un altro `geometry.csv`; con `--output <file>` sceglie dove scrivere quello nuovo.

## Motore
In RocketPy il motore è modellato a parte (`motor.csv`), quindi il razzo di `geometry.csv` è la configurazione senza motore. Lo script ignora i motori del `.ork` e scrive solo quali ha trovato. Per esempio nella v1.5 c'è il motorino G250 messo vicino al baricentro, che serve solo per far girare la simulazione OpenRocket da cui si ricavano le inerzie.

Masse, baricentro e inerzie non li calcola: vengono dalla simulazione OpenRocket (`openrocket_simulationdata.csv`), togliendo la massa del motorino.

## Come calcola le posizioni
- **Corpo esterno:** ogiva, tubi e transizioni stanno uno dopo l'altro; ognuno parte dove finisce il precedente.
- **Componenti interni:** alette, rail button, paratie, tubi interni, masse e paracadute sono posizionati rispetto al componente che li contiene, con il metodo scelto in OpenRocket:

| Metodo | Inizio del componente |
|---|---|
| `top` | inizio del contenitore + offset |
| `middle` | centro del contenitore − metà lunghezza + offset |
| `bottom` | fine del contenitore − lunghezza + offset |
| `absolute` | offset dalla punta |
| `after` | fine del componente precedente + offset |

Come lunghezza usa la corda alla radice per le alette, il diametro esterno per i rail button e la lunghezza da impacchettati per paracadute e masse.

## Valori per `geometry.csv`
| Parametro | Da dove |
|---|---|
| `radius` | raggio massimo dei tubi |
| `nose_length`, `nose_position` | ogiva; la forma è scritta nelle note (`haack` con parametro 0 = Von Kármán, 1/3 = LV-Haack) |
| `fin_*` | primo set di alette; `fin_sweep_angle` = atan(sweep / span) |
| `tail_*` | ultima transizione del corpo (il boat tail) |
| `upper_button_position`, `lower_button_position` | centro del primo e dell'ultimo rail button |
| `motor_position` | fine del razzo, dove sta l'uscita dell'ugello |

Nelle note scrive anche su cosa sono montate le alette (tubo o boat tail) e la forma del boat tail. In RocketPy la coda è sempre conica.

## `geometry.csv` generato
Ha le 3 righe di intestazione e tutti i parametri che legge `atlas_model.py`, nello stesso ordine dei `geometry.csv` della repo.
- **Valori:** quelli della tabella sopra.
- **std:** presi dal `geometry.csv` accanto al `.ork`, se c'è.
- **`---`:** i campi che il `.ork` non dà:
  - `rocket_dry_mass`, `rocket_dry_inertia_11`, `rocket_dry_inertia_33`, `center_of_mass_without_motor`: dalla simulazione OpenRocket, togliendo il motorino;
  - `button_angular_position`.

Si completano i `---` a mano e si copia il file in `simulation_inputs/geometry_data/<versione>/`. Se resta un `---`, `atlas_model.py` si ferma e dice quali campi mancano.
