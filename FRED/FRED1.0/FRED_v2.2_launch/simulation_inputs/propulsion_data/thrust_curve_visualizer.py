import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# set path
BASE_DIR = Path(__file__).resolve().parent

filename = "test_2026-05-21_21-07-43"

# Carica i dati del sensore 1 saltando la prima riga (header)
data_test_7mm = np.genfromtxt(str(BASE_DIR/f"{filename}.csv"), delimiter=',')

time = data_test_7mm[:, 0]
thrust = data_test_7mm[:, 1]

t_start = 1.13
t_end = 3.500

print("t_burnout = ", t_end - t_start)

plt.figure(figsize=(10,6))
plt.title("Curva di spinta motore")
plt.plot(time, thrust)
plt.axvline(x = t_start, color = "red")
plt.axvline(x = t_end, color = "red")
plt.grid(True)
plt.show()


# Maschere
data_test_7mm_mask = data_test_7mm[(data_test_7mm[:,0] >= t_start) & (data_test_7mm[:,0] <= t_end)]
data_test_7mm_mask[:,0] = data_test_7mm_mask[:,0] - t_start

time_mask = data_test_7mm_mask[:, 0]
thrust_mask = data_test_7mm_mask[:, 1]

plt.figure(figsize=(10,6))
plt.title("Curva di spinta motore nel tempo selezionato")
plt.plot(time_mask, thrust_mask)
plt.grid(True)
plt.show()


dati_da_salvare = np.column_stack((time_mask, thrust_mask))
np.savetxt(
    str(BASE_DIR/f"reshape_{filename}.csv"),
    dati_da_salvare,
    delimiter=",",
    fmt="%.4f",
)
print("Dati salvati con successo")