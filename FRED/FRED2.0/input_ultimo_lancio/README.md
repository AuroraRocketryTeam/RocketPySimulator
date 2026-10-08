# Input dell'ultima simulazione di lancio di FRED 1.0

Copia degli input usati da `FRED/FRED1.0/FRED_v2.2_launch/FRED_v2.2_launch.py` (ramo `Fred-launch`, ultimo commit 09/07/2026), con motore `nozzle 7mm test` e configurazione `v2.3_super_lite`, più gli altri file candidati. Da smistare in `simulation_inputs/` e `tools/` di FRED2.0 come in Atlas.

## File
| Cartella | File | Stato |
|---|---|---|
| `geometry/` | `FRED_v_2.3.ork` | ultimo `.ork` di FRED 1.0 (Leonardo, 23/05); lo script non lo legge |
| | `FRED2.0_v1.0.ork` | primo `.ork` di FRED2.0 |
| `aerodynamic/` | `CD_power_off_v2.3_TEST.csv`, `CD_power_on_v2.3_TEST.csv` | **usati dalla sim di lancio** |
| | `CD-Mach_FRED_2.3.CSV` | export RASAero da cui vengono i due CD v2.3 |
| | `FRED2.0_v1.0_CD_power_on.csv` | CD di FRED2.0 (solo power on) |
| | `CD-mach_FRED2.0_v1.0.csv` | export RASAero di FRED2.0 (decimali con la virgola) |
| `propulsion/` | `reshape_test_2026-05-21_21-07-43.csv` | **curva di spinta usata dalla sim di lancio** (test al banco tagliato) |
| | `test_2026-05-21_21-07-43.csv` | dati grezzi del test al banco |
| | `SRAD_thrustcurve_7mm.csv` | curva simulata, opzione `nozzle 7mm sim` |
| | `SRAD_thrustcurve_BRICO_45_7mm.csv` | curva simulata più vecchia |
| `environment/` | `Villafranca_ensemble_5to11may2020to2026.nc` | ensemble meteo (opzione `e`) |
| | `Villafranca_airfield_launch_site.jpg` | mappa per il grafico della dispersione |

Nella sim di lancio il meteo era `m` (vento manuale) e non legge file.

## Parametri scritti nello script
Valore nominale e deviazione standard, come in `analysis_parameters`.

**Sito e rampa:** lat 44.290583, lon 12.027111, quota 18 m; inclinazione 80 ± 3°, heading 160 ± 5°, rampa 1,5 m. Vento manuale: 8,7 m/s al suolo, heading 315°, ×1,05 ogni 50 m fino a 300 m.

**Razzo (`v2.3_super_lite`):**

| Parametro | Valore |
|---|---|
| massa a secco senza motore | 2,201 ± 0,03 kg |
| CG senza motore, dalla punta | 0,409 m |
| inerzia I11 / I33 | 1,49 ± 0,00187 / 0,01 ± 0,000122 kg·m² |
| raggio | 42,5 mm |
| ogiva | ellittica, lunga 0,14 m |
| alette | 3, span 0,12, root 0,12, tip 0,03 m, sweep 30,3°, a 0,686 m |
| coda | a 0,810 m, lunga 43 mm, raggio 42,5 → 30 mm |
| rail button | 0,424 e 0,625 m |

Le altre configurazioni nello script: `2x_barre_alte` 2,374 kg / 0,397 m, `4x_barre_alte` 2,618 / 0,391, `v2.3` 2,692 / 0,416, `v2.3_lite` 2,490 / 0,402.

**Motore BRICO 45 da 7 mm (`nozzle 7mm test`):**

| Parametro | Valore |
|---|---|
| impulso totale | 202,054 ± 1 N·s (il commento dice 243,96, il valore simulato) |
| burn time | 2,37 ± 0,001 s |
| massa a secco | 0,622 kg (818 g reali wet − 196 g di grain simulato) |
| CG a secco, dall'ugello | 99,41 mm |
| inerzia I11 / I33 | 0,66 / 0,00001 kg·m² |
| grain | 1, Ø esterno 33 mm, Ø interno 13 mm, lungo 147 mm, 196,6 g; CG a 125 mm dall'ugello |
| ugello | raggio 13,71 mm, gola 9,50 mm (presi da Borealis) |
| posizione | fine della coda, 0,853 m dalla punta |

Attenzione: la densità del grain nello script è calcolata con `3.14*(2R-2r)*L` invece di π(R²−r²)L, quindi RocketPy usa circa 2 g di propellente invece di 197 g. In FRED2.0 va usata la densità vera, circa 1850 kg/m³.

**Recupero:** un solo paracadute (main, Rocketman 4 ft), `cd_s` 0,97·1,168 ± 0,0277 m², aperto all'apogeo dall'algoritmo di bordo (velocità verticale negativa per 0,1 s, campionamento 105 Hz). Ritardi: `lag_se` 0,75 ± 0,05 s, `lag_rec` 0,75 ± 0,5 s. Rumore di pressione: media 0, deviazione 6,5 Pa, correlazione 0,3.
