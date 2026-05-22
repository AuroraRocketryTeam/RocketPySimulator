import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# set path
BASE_DIR = Path(__file__).resolve().parent

# 1. Carica il file (cambia 'tuo_file.csv' con il nome reale)
df = pd.read_csv(str(BASE_DIR/"thrust"))

# 2. Plotta i dati (usa la prima colonna come X)
df.plot(x=df.columns[0])

# 3. Mostra il grafico
plt.show()