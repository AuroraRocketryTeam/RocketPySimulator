import pandas as pd
import matplotlib.pyplot as plt
import os
# ============================================================
# 1. CARICA I DUE CSV
# ============================================================
# Adatta i nomi dei file e delle colonne ai tuoi CSV reali
# Esempio CSV:  time,mass
#               0.0,50000
#               0.5,49500
#               ...

file1 = "C:/Users/eugen/Documents/AuroraRocketry/RocketPySimulator/Atlas/mass_time_atlas_rpy.csv"   # CSV più denso (più punti)
file2 = "C:/Users/eugen/Documents/AuroraRocketry/RocketPySimulator/Atlas/mass_time_atlas_openrocket.csv"   # CSV più discreto (meno punti)

df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)

# ============================================================
# 2. RINOMINA LE COLONNE (se necessario)
# ============================================================
# Se le colonne hanno nomi diversi tra i due file, uniformale:
# df1.columns = ["time", "mass"]
# df2.columns = ["time", "mass"]

# Controlla cosa hai letto
print("=== Fonte 1 ===")
print(df1.head())
print(f"Punti: {len(df1)}\n")

print("=== Fonte 2 ===")
print(df2.head())
print(f"Punti: {len(df2)}\n")

# ============================================================
# 3. PLOT
# ============================================================
fig, ax = plt.subplots(figsize=(12, 6))

print("Colonne df1:", df1.columns.tolist())
print("Colonne df2:", df2.columns.tolist())

# Fonte 1 — linea continua (ha più punti → appare liscia)
ax.plot(
    df1["time"], df1["mass"],
    color="royalblue",
    linewidth=1.5,
    label=f"RocketPy ({len(df1)} punti)"
)

# Fonte 2 — linea + marker (ha meno punti → mostra i campioni)
ax.plot(
    df2["time"], df2["mass"],
    color="crimson",
    linewidth=1.5,
    markersize=4,
    label=f"OpenRocket ({len(df2)} punti)"
)

# ============================================================
# 4. FORMATTAZIONE
# ============================================================
ax.set_xlabel("Tempo [s]", fontsize=13)
ax.set_ylabel("Massa [kg]", fontsize=13)
ax.set_title("Massa del razzo — confronto tra due fonti", fontsize=15)
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
ax.tick_params(labelsize=11)

plt.tight_layout()
plt.savefig("confronto_massa.png", dpi=200)   # salva immagine
plt.show()