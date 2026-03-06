def simulator_check_drogue_opening(p, h, y):
    global last_negative_time, apogee_detected, parachute_stopwatch, sampling_rate
    altitude = h
    vertical_velocity = y[5]

    # Update counter for flight time to apogee: each time this function is called, the timer advances of 1 over the frequency at which the function is called. This is a workaround to get a measure of in-flight time
    # into the apogee detection algorythm and successfully implement its "consistent descent signal" principle.
    parachute_stopwatch += 1/sampling_rate

    # Mark instant at which the current call is being made
    now = parachute_stopwatch
    
    # Call apogee detection algorythm
    apogee_detected, last_negative_time = check_apogee(
        vertical_velocity,
        now,  
    )
    return apogee_detected