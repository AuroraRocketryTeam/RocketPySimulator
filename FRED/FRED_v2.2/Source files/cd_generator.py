import csv
# File and directory management
from pathlib import Path


# set path
BASE_DIR = Path(__file__).resolve().parent


import pandas as pd

def estrai_mach_e_cd(input_csv_path, output_csv_path):
    risultati = []
    
    try:
        with open(input_csv_path, mode='r', encoding='utf-8') as file:
            # Usiamo la virgola come separatore
            lettore = csv.reader(file, delimiter=',')
            
            # Leggiamo l'header (la prima riga)
            header = next(lettore)
            
            for riga in lettore:
                # Salta le righe vuote o quelle troncate alla fine del file
                if len(riga) < 10:
                    continue
                
                # Ricostruiamo il Mach: uniamo la colonna 0 (es. "0") e la colonna 1 (es. "01")
                # per formare il float corretto (es. "0.01")
                mach_valore = f"{riga[0]}.{riga[1]}"
                
                # Guardando la struttura dei tuoi dati, il "CD Power-On" si trova 
                # nella colonna con indice 4 (la quinta colonna)
                cd_power_on_valore = f"{riga[7]}.{riga[8]}"
                
                risultati.append([mach_valore, cd_power_on_valore])
                
        # Scrittura del nuovo file CSV con i dati puliti
        with open(output_csv_path, mode='w', newline='', encoding='utf-8') as file_out:
            scrittore = csv.writer(file_out, delimiter=',')
            # Scriviamo il nuovo header pulito
            scrittore.writerow(['Mach', 'CD Power-On'])
            # Scriviamo i dati
            scrittore.writerows(risultati)
            
        print(f"Elaborazione completata con successo! Salvato in: {output_csv_path}")

    except Exception as e:
        print(f"Si è verificato un errore durante l'elaborazione: {e}")

# --- COME ESEGUIRE IL CODICE ---
# Sostituisci i nomi dei file con i tuoi per testarlo
file_input = str(BASE_DIR/"CD-Mach_FRED_2.3.CSV")
file_output = str(BASE_DIR/"CD_power_off_v2.3_TEST.csv")

# Esecuzione della funzione
estrai_mach_e_cd(file_input, file_output)

