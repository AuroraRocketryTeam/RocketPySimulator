import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# set path
BASE_DIR = Path(__file__).resolve().parent

# Load the .csv

file1 = BASE_DIR / "mass_time_rpy/mass_time_rpy_2.csv"
file2 = BASE_DIR / "mass_time_openrocket.csv"

# Read
df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)

# Plot
fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(
    df1["time"], df1["mass"],
    color="royalblue",
    linewidth=1.5,
    label=f"RocketPy ({len(df1)} points)"
)

ax.plot(
    df2["time"], df2["mass"],
    color="crimson",
    linewidth=1.5,
    markersize=4,
    label=f"OpenRocket ({len(df2)} points)"
)

ax.set_xlabel("Time [s]", fontsize=13)
ax.set_ylabel("Mass [kg]", fontsize=13)
ax.set_title("Rocket Mass Comparison", fontsize=15)
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
ax.tick_params(labelsize=11)

plt.tight_layout()
plt.savefig(BASE_DIR / "images/mass_compare_1_1.png", dpi=200)   # save image
plt.show()