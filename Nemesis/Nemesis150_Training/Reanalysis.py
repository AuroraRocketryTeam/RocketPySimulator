
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import time
from pathlib import Path
from time import process_time
from rocketpy import Environment, Flight, Rocket, SolidMotor
env = Environment(latitude=39.3901806, longitude=-8.289189, elevation=160)
import datetime
import pandas as pd
BASE_DIR = Path(__file__).resolve().parent

#parachute functions ect.

# Definition of global variables, to be used inside and outside parachute functions
global last_negative_time, apogee_detected, sampling_rate, parachute_timer
# This variable marks the first instant in which a negative velocity is detected
last_negative_time = None
# This variable indicates whether the algorythm has acknowledged the rocket has reached apogee. A "False" value may mean that negative velocity has not yet been detected, or that it has been detected but has not yet been consistent for enough seconds (the threshold)
apogee_detected = False
# This variable indicates the sampling rate of the recovery activation algorythm
sampling_rate = 105
# This variable keeps track of the flight time from ignition to the first recovery event 
parachute_stopwatch = 0

# The following function is a Python representation of the C code that will be used on the rocket to detect the apogee condition. In the actual code, detection of negative velocity is achieved thanks to the readings from the IMU sensor


def check_apogee(vertical_velocity, current_time, threshold=0.1):

    global last_negative_time, apogee_detected, parachute_stopwatch

    # If the parachute activation signal has already been sent, confirm it and exit the function
    if apogee_detected:
        return True, last_negative_time
    
    # Otherwise, check if the rocket is losing altitude
    if vertical_velocity < 0:

        # if a descent is being detected, check if this is the first time this occurs
        if last_negative_time is None:

            # if it is, mark this instant and exit the function
            last_negative_time = parachute_stopwatch
            return False, last_negative_time
        
        elif (current_time - last_negative_time) >= threshold: #0.1s

            # if it isn't and enough time has passed with a continuous descent, acknowledge apogee and exit the function
            return True, last_negative_time
        
        else:

            # if it isn't and not enough time has passed with a continuous descent, return False and exit the function
            return False, last_negative_time
        
    # if a descent is no longer being (or has never been) detected, return False and exit the function
    else:
        return False, None
    

# The following function is a Python representation of the C code that will be used on the rocket to detect the main parachute opening condition. In the code, the height is determined by filtering barometer readings with a Kalman filter
 

def main_parachute_opening(apogee_detected:bool, altitude:float) -> bool:
    return apogee_detected and altitude <= 450.0 # meters 


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
    apogee_detected, last_negative_time = check_apogee(
        vertical_velocity,
        now,  
    )
    return apogee_detected

# Set up parachute trigger for the main chute
def simulator_check_main_opening(p, h, y):
    global last_negative_time, apogee_detected
    altitude = h

    # Call parachute activation algorythm and return its output value
    return main_parachute_opening(apogee_detected, altitude)



##DATA

env.set_date(
    (2025, 12, 12, 15)
)  # Hour given in UTC time
env.set_atmospheric_model(type="Forecast", file="GFS")
env.max_expected_height = 4500 # adjust the plots to this height
env.info()
# IMPORTANT: modify the file path below to match your own system

Pro75M8187 = SolidMotor(
    thrust_source=str(BASE_DIR/"""Cesaroni_8187M1545_P.csv"""),
    dry_mass=0,
    dry_inertia=(0, 0, 0),
    nozzle_radius=29 / 1000,
    grain_number=6,
    grain_density=1758.7,
    grain_outer_radius= 35.9/ 1000,
    grain_initial_inner_radius=18.1/ 1000,
    grain_initial_height=156.17 / 1000,
    grain_separation=3 / 1000,
    grains_center_of_mass_position=-0.7343,
    center_of_dry_mass_position=0,
    nozzle_position=-1.296,
    burn_time=5.3,
    throat_radius=20/ 1000,
    coordinate_system_orientation="nozzle_to_combustion_chamber",
)
Pro75M8187.info()
# IMPORTANT: modify the file paths below to match your own system

Nemesis = Rocket(
    radius=75 / 1000,
    mass=22.740,
    inertia=(14.304,14.304,0.078),
    power_off_drag=str(BASE_DIR/"""Nemesis150_v4.0_RAS_CDMACH_pwrOFF.csv"""),
    power_on_drag=str(BASE_DIR/"""Nemesis150_v4.0_RAS_CDMACH_pwrON.csv"""),
    center_of_mass_without_motor=0,
    coordinate_system_orientation="tail_to_nose",
)

rail_buttons = Nemesis.set_rail_buttons(
    upper_button_position=0.980,
    lower_button_position=-0.239,
    angular_position=0,
)
Nemesis.add_motor(Pro75M8187, position=0)
nose_cone = Nemesis.add_nose(length=0.45, kind="vonKarman", position=1.635)

# IMPORTANT: modify the file path below to match your own system
fin_set = Nemesis.add_trapezoidal_fins(
    n=3,
    root_chord=0.30,
    tip_chord=0.093,
    span=0.16,
    position=-0.855,
    cant_angle=0,
    sweep_angle=58,
)

tail = Nemesis.add_tail(
    top_radius=0.075, bottom_radius=0.046, length=0.116, position=-1.155,
)
Nemesis.all_info()
Main = Nemesis.add_parachute(
    "Main",
    cd_s=0.97*10.5070863,
    trigger=simulator_check_main_opening,
    sampling_rate=105,
    lag=1.73,
    noise=(0, 6.5, 0.3),
)

Drogue = Nemesis.add_parachute(
    "Drogue",
    cd_s=0.97*0.6566929,
    trigger=simulator_check_drogue_opening,
    sampling_rate=105,
    lag=1.73,
    noise=(0, 6.5, 0.3),
)
test_flight = Flight(
    rocket=Nemesis, environment=env, rail_length=12, inclination=84, heading=144
)
#test_flight.all_info()
#test_flight.speed()
#test_flight.acceleration
#print(test_flight.aerodynamic_drag.max)
#print(test_flight.aerodynamic_lift.max)


test_flight.export_kml(
    file_name=str(BASE_DIR/"trajectory.kml"),
    extrude=True,
    altitude_mode="relative_to_ground",
)
