import csv

# === PARAMETRI DA MODIFICARE ===
input_file = "c:/Users/Caio/Downloads/V2_square.CSV"
output_file = "C:/Users/Caio/Documents/Aurora Rocketry/Atlas/Sim/Atlas_v1.0_sim/square_power_on.CSV"
colonne = [0, 1, 7,8]     # col1, col2, col3, col4  # indici delle colonne da prendere (0 = prima colonna) 5,6 off e7,8 on
max_righe = 120
# ================================

righe_output = []

with open(input_file, newline='', encoding='utf-8') as csv_in:
    reader = csv.reader(csv_in, delimiter=',')

    # Salta la prima riga
    next(reader, None)

    for i, riga in enumerate(reader):
        if i >= max_righe:
            break
        try:
            c1 = riga[colonne[0]].strip()
            c2 = riga[colonne[1]].strip()
            c3 = riga[colonne[2]].strip()
            c4 = riga[colonne[3]].strip()

            nuova_riga = f"{c1}.{c2},{c3}.{c4}"
            righe_output.append([nuova_riga])

        except IndexError:
            continue

with open(output_file, 'w', newline='', encoding='utf-8') as csv_out:
    writer = csv.writer(csv_out, delimiter=',')
    writer.writerows(righe_output)

print(f"Creato {output_file} con {len(righe_output)} righe (formato col1.col2,col3.col4).")