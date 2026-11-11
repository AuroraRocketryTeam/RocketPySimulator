import matplotlib.pyplot as plt
import pickle
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# insert desired pickle directory
with open(BASE_DIR.parents[1] / "simulation_output/montecarlo_output/prova/comparison/pickle/velocities.pickle", "rb") as f:
    fig = pickle.load(f)

plt.show()


'''
import pickle
from pathlib import Path
import matplotlib.pyplot as plt

folder = Path(__file__).resolve().parent
file_path = folder / "velocities.pickle"

print("Cerco:", file_path)       # utile per controllare
print("Esiste:", file_path.exists())

with open(file_path, "rb") as f:
    fig = pickle.load(f)

plt.show()
'''

'''
import dill
from pathlib import Path
import matplotlib.pyplot as plt

file_path = Path(__file__).resolve().parent / "velocities.pickle"

with open(file_path, "rb") as f:
    fig = dill.load(f)

plt.show()
'''