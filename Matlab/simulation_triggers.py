# Global variables initialization
def define_variables(negative_time, apogee, stopwatch, sampling):
    global last_negative_time, apogee_detected, parachute_stopwatch, sampling_rate
    last_negative_time = negative_time
    apogee_detected = apogee
    parachute_stopwatch = stopwatch
    sampling_rate = sampling


# The following function is a Python representation of the C code that will be used on the rocket to detect the apogee condition. In the actual code, detection of negative velocity is achieved thanks to the readings from the IMU sensor


def check_apogee(vertical_velocity, current_time, threshold=0.1):

    global last_negative_time, apogee_detected
    
    # If the parachute activation signal has already been sent, confirm it and exit the function
    if apogee_detected:
        return True, last_negative_time
    
    # Otherwise, check if the rocket is losing altitude
    if vertical_velocity < 0:

        # if a descent is being detected, check if this is the first time this occurs
        if last_negative_time is None:

            # if it is, mark this instant and exit the function
            last_negative_time = current_time
            return False, last_negative_time
        
        elif (current_time - last_negative_time) >= threshold:  #0.1s
            #apogee_detected = True

            # if it isn't and enough time has passed with a continuous descent, acknowledge apogee and exit the function
            return True, last_negative_time
        
        else:

            # if it isn't and not enough time has passed with a continuous descent, return False and exit the function
            return False, last_negative_time

    # if a descent is no longer being (or has never been) detected, return False and exit the function
    else:
        return False, None

# Set up parachute trigger for the drogue chute
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
    apogee_detected, last_negative_time = check_apogee(vertical_velocity, now)
    return apogee_detected


# The following function is a Python representation of the C code that will be used on the rocket to detect the main parachute opening condition. In the code, the height is determined by filtering barometer readings with a Kalman filter


def main_parachute_opening(apogee_detected, altitude):
    return apogee_detected and altitude <= 450.0

# Set up parachute trigger for the main chute
def simulator_check_main_opening(p, h, y):
    altitude = h

    # Call parachute activation algorythm and return its output value
    return main_parachute_opening(apogee_detected, altitude)