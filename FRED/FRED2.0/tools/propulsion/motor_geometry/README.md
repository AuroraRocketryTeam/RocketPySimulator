# Massa, baricentri e inerzie del motore SRAD

`motor_mass_properties.py` è la copia dello strumento di Atlas (spiegazione in `Atlas/tools/propulsion/motor_geometry/motor_mass_properties.md`) con le densità del simulatore di FRED: case e bulkhead in alluminio 2700 kg/m³, protezione termica 1500 kg/m³, ugello in acciaio C45 7850 kg/m³. Due differenze dal notebook di Atlas: il fondo del case è spesso `th_casing` (non `2*th_casing`) e l'anello dell'ugello manca (`L_nozzle_ring` = 0).

Una cartella per ugello, con il file dei parametri di propulsione:
- `7mm/`: gola 7 mm, rapporto di espansione 6,8 (motore del lancio del 23 maggio);
- `8mm/`: gola 8 mm, rapporto di espansione 5.

```bash
python FRED/FRED2.0/tools/propulsion/motor_geometry/motor_mass_properties.py FRED/FRED2.0/tools/propulsion/motor_geometry/7mm/FRED_45_PARAMETERS_7mm.txt
```

Lo script scrive accanto al file dei parametri `mass_properties.csv` e il disegno della sezione (`motor_section.png` / `.pdf`). In `motor.csv` vanno: `motor_dry_mass_position` = CG dry, `motor_inertia_11/33` = I dry, `grains_center_of_mass_position` = CG propellant.

| ugello | a secco [kg] | CG a secco [m] | I_11 / I_33 a secco [kg·m²] | CG grain [m] | lunghezza [m] |
|---|---|---|---|---|---|
| 7 mm | 0,7775 | 0,0875 | 0,00486 / 0,000231 | 0,1282 | 0,2367 |
| 8 mm | 0,7372 | 0,0873 | 0,00455 / 0,000223 | 0,1235 | 0,2320 |
