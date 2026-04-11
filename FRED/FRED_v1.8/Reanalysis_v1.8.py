
from pathlib import Path
from rocketpy import Environment, Flight, Rocket, SolidMotor 
import json
import numpy as np
import pandas as pd
from typing import Literal

# set path
BASE_DIR = Path(__file__).resolve().parent

#-------------------------------------------------------------------------------------------------------- PARAMETERS
# The following parameters are centralized here for convenience. 
# Core internal variables remain defined within their respective modules.

show_graph = False

latitude = 44.290583
longitude = 12.027111
elevation = 18
date_of_launch = (2025, 5, 9, 12)          #(Year, Month, Day, Hour UTC)
weather_data: Literal['c','e','f','i'] = 'e'        #(Custom, Ensemble, Forecast, Isa)

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
#--------------------------------------------------------------------------------------------------------

#-------------------------------------------------------------------------------------------------------- ENVIRONMENT
Env = Environment(
    date = date_of_launch,
    longitude = longitude,
    latitude = latitude,
    elevation = elevation,
    max_expected_height = 4500
)

# There are 4 possible choices of weather data:
if weather_data=='c':
    # A custom atmosphere defined with the mean environment values calculated in the week on EuRoC 
    # from 2005 to 2024 between the 10th and the 15th october. 
    # In order to define the mean environment features, we used the built-in function "Environment Analysis"  
    # from RocketPy. This generates a .json file with the mean environment values based on a sample 
    # of 19 years, from 2005 to 2024, between the 10th and 15th of October, by feeding the NetCDF4 data  
    # from Copernicus. The .json file contains a series of .csv profiles based on the altitude that   
    # define pressure, temperature and wind vectors on an hourly basis.
    # For more information consult the "mean_environment_values.json" file inside the directory.

    # import the .json with the mean environment values oustide the defition of the atmospheric model
    with open(BASE_DIR/"simulation_inputs/environment_data/mean_environment_values.json", "r") as f:
        data = json.load(f)

    Env.set_atmospheric_model(

        # set the atmosphere model
        type="custom_atmosphere",

        # define the values (pressure, temperature and wind [E,N]) from the .json
        pressure = data["atmospheric_model_pressure_profile"][str(Env.date[3])],
        temperature= data["atmospheric_model_temperature_profile"][str(Env.date[3])],
        wind_u= data["atmospheric_model_wind_velocity_x_profile"][str(Env.date[3])],
        wind_v= data["atmospheric_model_wind_velocity_y_profile"][str(Env.date[3])]

    )
elif weather_data=='e':
    # Select a date during the EuRoC week: October 10th-15th from 2005 to 2024 (change the date in the 
    # environment definition), in this case the weather data will match the date chosen by the user.
    Env.set_atmospheric_model(
        type="Ensemble",                                                                                           
        file=str(BASE_DIR/"simulation_inputs/environment_data/Villafranca_ensemble_5to11may2020to2026.nc"),                                     
        # This section creates an updated dictionary to read the NetCDF4 files,                                           
        # as the built-in ECMWF dictionary inside RocketPy is outdated and can't read NetCDF4 
        # files in the new format     
        dictionary= {                                                                                                     
            "ensemble": "number",                                                                                         
            "time": "valid_time",                                                                                         
            "latitude": "latitude",                                                                                       
            "longitude": "longitude",                                                                                     
            "level": "pressure_level",                                                                                    
            "temperature": "t",                                                                                           
            "surface_geopotential_height": None,                                                                          
            "geopotential_height": None,                                                                                  
            "geopotential": "z",                                                                                          
            "u_wind": "u",                                                                                                
            "v_wind": "v",                                                                                                
        },
    )
elif weather_data=='f':
    # The Forecast: let the user simulate in the future by using the GFS (Global Forecast System) 
    # weather data, (change the date in the environment definition).
    Env.set_atmospheric_model(
        type="Forecast",
        file="GFS"
    )
elif weather_data!='i':
    # The default weather data type is the International Standard Atmosphere (ISA).
    # If none of the previously listed options is selected, this model will be applied automatically.
    print('<!> International Standard Atmosphere (ISA) as defined by ISO 2533 is initialized as weather data <!>')
#---------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------
## DEFINE THE ROCKET PARTS

#   SRAD motor info v1.1
impulse = 309
burn_time = 0.968
grain_external_radius = 0.038 / 2
grain_internal_radius = 0.015 / 2 
grain_length = 0.1530
grain_volume = 3.14*((grain_external_radius**2)-(grain_internal_radius**2))*grain_length
grain_mass = 0.4019
grain_dens = grain_mass / grain_volume

solid_motor = SolidMotor(
    burn_time=0.968,
    thrust_source =str(BASE_DIR/"simulation_inputs/propulsion_data/SRAD_thrustcurve_v1.1.csv"),
    grain_number=1,
    #   DRY PARAMETERS
    dry_mass= 0,
    dry_inertia= (0, 0, 0),
    center_of_dry_mass_position= 0,
    #   GRAIN PARAMETERS
    grain_density= grain_dens,
    grain_outer_radius= grain_external_radius,
    grain_initial_inner_radius= grain_internal_radius,
    grain_initial_height= grain_length,
    grain_separation= 3 / 1000,
    #   NOZZLE PARAMETERS
    nozzle_radius= 29 / 1000,
    nozzle_position=0,
    throat_radius= 20/ 1000,
    #   POSITIONING PARAMETERS
    grains_center_of_mass_position= 119.5 / 1000,
    coordinate_system_orientation="nozzle_to_combustion_chamber",
)

power_off_drag = str(BASE_DIR / "simulation_inputs/aerodynamic_data/FRED_v1.8_CD_power_off.csv")
power_on_drag = str(BASE_DIR / "simulation_inputs/aerodynamic_data/FRED_v1.8_CD_power_on.csv")

FRED = Rocket(
    radius= 42.5 / 1000,
    mass= 2199.647 / 1000,
    inertia=(0.149,0.149,0.002),
    power_off_drag=power_off_drag, # use the prevoius defined drag curve^
    power_on_drag=power_on_drag, # use the prevoius defined drag curve 
    center_of_mass_without_motor= 432.2 / 1000,
    coordinate_system_orientation="nose_to_tail",
)
FRED.add_motor(solid_motor, position=0.814)

Rail_Buttons = FRED.set_rail_buttons(
    upper_button_position= 424 / 1000,
    lower_button_position= 625 / 1000,
    angular_position=0,
)

nose_cone = FRED.add_nose(
    length=0.14, 
    kind="elliptical", 
    position=0
)

fin_set = FRED.add_trapezoidal_fins(
    n=3,
    root_chord=0.12,
    tip_chord=0.03,
    span=0.12,
    position=0.675,
    cant_angle=0,
    sweep_angle=30.3,
)

tail = FRED.add_tail(
    top_radius= 42.5 / 1000,
    bottom_radius= 33.5 / 1000,
    length=0.047,
    position=0.795,
)

Main = FRED.add_parachute(
    "Main",
    cd_s=0.97*1.168,
    trigger=simulator_check_drogue_opening,
    sampling_rate=105,
    lag=1.73,
    noise=(0, 6.5, 0.3),
)


# Simulate the flight
rocket_flight = Flight(
    rocket=FRED,
    environment=Env,
    rail_length=2,
    inclination=84,
    heading=160,
)

# if activated, shows graphs 
if show_graph:
    FRED.draw()
    FRED.plots.total_mass()
    rocket_flight.plots.linear_kinematics_data()
    rocket_flight.plots.attitude_data()
    rocket_flight.plots.angular_kinematics_data()
    rocket_flight.plots.flight_path_angle_data()
    rocket_flight.plots.trajectory_3d()
    rocket_flight.plots.stability_and_control_data()
    rocket_flight.plots.aerodynamic_forces()
    rocket_flight.plots.rail_buttons_forces()

# print rocket flight info
rocket_flight.info()

# plot speed and acceleration
# rocket_flight.speed()
# rocket_flight.acceleration()

# save trajectory, .kml can be open in google earth
# rocket_flight.export_kml(
#     file_name=str(BASE_DIR/"reanalysis_output/trajectory.kml"),
#     extrude=True,
#     altitude_mode="relative_to_ground",
# )

# ------------------------------------------
# extract mass over time value as .csv

# mass_data = FRED.total_mass.source

# df = pd.DataFrame(mass_data, columns=["time", "mass"])
# df.to_csv(BASE_DIR / "mass_analysis/mass/mass_time_rpy/insertfilename.csv", index=False) 

# ------------------------------------------
# extract cg position over time value as .csv
# the relative position is expressed from the nose tip

# cg_data = FRED.center_of_mass.source

# df_cg = pd.DataFrame(cg_data, columns=["time", "CG"])
# df_cg.to_csv(BASE_DIR / "mass_analysis/CG/CG_rpy/insertfilename.csv", index=False)