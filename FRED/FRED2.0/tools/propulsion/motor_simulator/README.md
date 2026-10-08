# Simulatore del motore SRAD (BRICO 45)

`solid_fred_v2.0_gen.py`: simulatore del motore del team propulsione (copia di `FRED1.0/FRED_v2.2_launch/SRAD motor simulator/`), configurato per l'ugello da 7 mm. Alla fine scrive il file dei parametri del motore (`FRED_45_PARAMETERS_*.txt`) che legge `tools/propulsion/motor_geometry/motor_mass_properties.py`. Serve `rocketcea`, che senza un compilatore Fortran non si installa.

I file dei parametri in uso sono quelli di propulsione, in `tools/propulsion/motor_geometry/7mm/` e `8mm/`.
