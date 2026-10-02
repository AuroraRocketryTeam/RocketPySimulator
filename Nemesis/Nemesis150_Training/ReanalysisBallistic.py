
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import time
from pathlib import Path
from time import process_time
from rocketpy import Environment, Flight, Rocket, SolidMotor
env = Environment(latitude=39.3901806, longitude=-8.289189, elevation=160)
import datetime
BASE_DIR = Path(__file__).resolve().parent

##DATA

env.set_date(
    (2025, 10, 13, 16)
)  # Hour given in UTC time
env.set_atmospheric_model(type="custom_atmosphere",  
     wind_u=[                                                                                                          
         (0, -1.5), # 10.60 m/s at 0 m                                                                                
         (4500, -1.5), # 10.60 m/s at 3000 m                                                                          
     ],                                                                                                                
     wind_v=[                                                                                                          
         (0, 0), # -16.96 m/s at 3000 m   
         (4500, 0)                                                                     #
     ],)

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

test_flight = Flight(
    rocket=Nemesis, environment=env, rail_length=12, inclination=84, heading=144
)

test_flight.export_kml(
    file_name=str(BASE_DIR/"trajectory.kml"),
    extrude=True,
    altitude_mode="relative_to_ground",
)

test_flight.export_data(BASE_DIR/"sensors_compare/simulated_data.csv", "z", "vz", time_step=0.109)