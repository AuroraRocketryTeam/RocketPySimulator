import matplotlib.pyplot as plt
import pickle
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# insert desired pickle directory
with open(BASE_DIR.parent / "montecarlo_output/prova/comparison/pickle/velocities.pickle", "rb") as f:
    fig = pickle.load(f)

plt.show()