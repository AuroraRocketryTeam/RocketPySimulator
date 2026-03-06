# Inizializzazione variabili globali
last_negative_time = None
apogee_detected = False
parachute_stopwatch = 0
sampling_rate = 105  # puoi sovrascriverlo da MATLAB

# Funzione di controllo apogeo
def check_apogee(vertical_velocity, current_time, threshold=0.1):
    global last_negative_time, apogee_detected

    if apogee_detected:
        return True, last_negative_time

    if vertical_velocity < 0:
        if last_negative_time is None:
            last_negative_time = current_time
            return False, last_negative_time
        elif (current_time - last_negative_time) >= threshold:
            apogee_detected = True
            return True, last_negative_time
        else:
            return False, last_negative_time
    else:
        last_negative_time = None
        return False, last_negative_time

# Trigger drogue parachute
def simulator_check_drogue_opening(p, h, y):
    global last_negative_time, apogee_detected, parachute_stopwatch, sampling_rate
    vertical_velocity = y[5]
    parachute_stopwatch += 1/sampling_rate
    now = parachute_stopwatch
    apogee_detected, last_negative_time = check_apogee(vertical_velocity, now)
    return apogee_detected

# Trigger main parachute
def main_parachute_opening(apogee_detected, altitude):
    return apogee_detected and altitude <= 450.0

def simulator_check_main_opening(p, h, y):
    altitude = h
    return main_parachute_opening(apogee_detected, altitude)