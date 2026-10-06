# `rasaero_cdmach_generator.py`: curva CD-Mach da RASAero

Converte l'export dei dati aerodinamici di RASAero ("Export to CSV") nel file CD-Mach che legge `atlas_model.py`: righe `mach,cd` senza intestazione, in `simulation_inputs/aerodynamic_data/rocket_body/<versione>/`.

Gli export di RASAero stanno qui, in una cartella per versione della geometria (`v1.0/`, `v1.2/`, `v1.4/`).

## Uso
```bash
python Atlas/tools/aerodynamic/cd_mach_rasaero_convert/rasaero_cdmach_generator.py Atlas/tools/aerodynamic/cd_mach_rasaero_convert/v1.4/CD_Mach_Test_Atlas_v_1.2_SDRAD.CSV -o Atlas/simulation_inputs/aerodynamic_data/rocket_body/v1.4/CD_Mach_Test_Atlas_v_1.2_SDRAD_cd_mach.csv
```

I percorsi partono dalla cartella da cui si lancia il comando; se contengono spazi vanno tra virgolette. Si possono convertire più export insieme (per esempio `v1.0/*.CSV`); in quel caso ognuno viene scritto accanto al suo export, con nome `<export>_cd_mach.csv`.

| Opzione | Significato |
|---|---|
| `-o <file>` | file di uscita (solo con un export); di default `<export>_cd_mach.csv` accanto all'export |
| `--column off/on/cd` | colonna da usare: `CD Power-Off` (default), `CD Power-On` o `CD` |
| `--alpha <gradi>` | angolo di attacco da tenere (default 0) |
| `--max-mach <M>` | scarta le righe sopra questo Mach |

## Cosa fa
1. **Legge l'export.** Controlla che le prime colonne siano `Mach, Alpha, CD, CD Power-Off, CD Power-On`, altrimenti si ferma: il file non è un export aerodinamico di RASAero.
2. **Gestisce la virgola decimale.** Su Windows in italiano RASAero scrive i decimali con la virgola, che è anche il separatore delle colonne, quindi ogni numero decimale finisce diviso in due campi. Lo script ricompone i primi cinque valori sapendo che il Mach ha sempre due decimali (`0,01`), l'angolo è intero (`0`) e i tre CD hanno la parte decimale: 2 + 1 + 2 + 2 + 2 campi. Se il file usa il punto decimale lo legge direttamente. Dopo la lettura controlla che tutti i CD siano tra 0 e 10: se no, il file non è stato letto bene.
3. **Tiene un solo angolo di attacco.** L'export contiene un blocco di righe per ogni angolo (0°, 2°, 4°), ciascuno da Mach 0,01 a 25. RocketPy ordina le righe per Mach: se restano tutti i blocchi, mescola i CD dei tre angoli. Lo script tiene solo `--alpha` (0° di default) e controlla che il Mach sia crescente.
4. **Scrive `mach,cd`.** Mach con due decimali, CD con tutte le cifre.

Alla fine stampa colonna, angolo, numero di righe e intervallo di Mach. Se `CD Power-On` e `CD Power-Off` sono diversi lo segnala: in quel caso servono due file, uno per colonna. Il modello oggi usa lo stesso file per motore acceso e spento.
