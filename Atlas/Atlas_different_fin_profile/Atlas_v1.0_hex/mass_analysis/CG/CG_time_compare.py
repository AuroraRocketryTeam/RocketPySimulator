import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# set path
BASE_DIR = Path(__file__).resolve().parent

# Load the .csv

file1 = BASE_DIR / "CG_rpy.csv"
file2 = BASE_DIR / "CG_openrocket.csv"

# Read
df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)

# Plot
fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(
    df1["time"], df1["CG"],
    color="royalblue",
    linewidth=1.5,
    label=f"RocketPy ({len(df1)} points)"
)

ax.plot(
    df2["time"], df2["CG"],
    color="crimson",
    linewidth=1.5,
    markersize=4,
    label=f"OpenRocket ({len(df2)} points)"
)

ax.set_xlabel("Time [s]", fontsize=13)
ax.set_ylabel("CG position from nose tip  [cm]", fontsize=13)
ax.set_title("CG position comparison", fontsize=15)
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
ax.tick_params(labelsize=11)

plt.tight_layout()
plt.savefig(BASE_DIR / "images/initial_CG_compare.png", dpi=200)   # save image
plt.show()