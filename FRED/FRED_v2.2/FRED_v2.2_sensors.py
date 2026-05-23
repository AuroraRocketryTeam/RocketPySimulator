# LEGGI PRIMA DI USARE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# Il plot viene salvato in \FRED_v2.2_2xbarre_alte_nozzle7mmtest, inoltre se non serve più togliere la parte dei sensori che rallenta molto
print("importing libraries...", end='\r')
# Plotting and visualization
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

# RocketPy core classes
from rocketpy import Environment, SolidMotor, Rocket, Flight, CompareFlights
from rocketpy.tools import load_monte_carlo_data
from rocketpy.sensitivity import SensitivityModel

# --- NUOVE LIBRERIE PER I SENSORI E UTF-8 ---
from rocketpy import Accelerometer, Barometer
import sys
sys.stdout.reconfigure(encoding='utf-8')
# --------------------------------------------

# Time measurement utilities
from datetime import datetime
from time import process_time
import time

# Numerical computations and random sampling
import numpy as np
from numpy.random import normal, choice
from scipy.stats import norm

# File and directory management
from pathlib import Path

# Data serialization and storage
import json
import pickle

# Image loading
from imageio.v2 import imread

# 
from typing import Literal

# General math usage 
import math

# set path
BASE_DIR = Path(__file__).resolve().parent

#-------------------------------------------------------------------------------------------------------- PARAMETERS
# The following parameters are centralized here for convenience. 
# Core internal variables remain defined within their respective modules.

# Name of the output folder (can be a new folder or an existing one to overwrite)
output_dir_name = 'FRED_v2.2_2xbarre_alte_nozzle7mmtest'
number_of_simulations = 50 # MODIFICARE era 200, usare magari 50 per velocizzare e poi 200 solo per i piu utili
ballistic = True

show_graph = False
sensitivity_analysis = False

latitude = 44.290583 # MODIFICARE SE SERVE, SONO LE COORDINATE
longitude = 12.027111
elevation = 18
date_of_launch = (2025, 5, 24, 16)          #(Year, Month, Day, Hour UTC) MODIFICARE A DATA GIUSTA
weather_data: Literal['c','e','f','i','m'] = 'f'        #(Custom, Ensemble, Forecast, Isa, Manual) MODIFICARE, 'm' per analisi a vento avverso, 'f' normalmente

#========================================================================================================= Parametri FRED

motore: Literal['nozzle 7mm sim','nozzle 8mm sim','nozzle 7mm test','nozzle 8mm test'] = 'nozzle 7mm test'

configurazione: Literal['2x_barre_alte','4x_barre_alte'] = '2x_barre_alte'

#=========================================================================================================

if motore == 'nozzle 8mm test':
    #   SRAD motor info BRICO 45 8mm
    impulse = 234.43507869871195
    t_burnout = 0.9                      # VALORE TEST
    grain_external_radius = 0.033 / 2
    grain_internal_radius = 0.013 / 2 
    grain_length = 0.147
    grain_volume = 3.14*((grain_external_radius*2)-(grain_internal_radius*2))*grain_length
    grain_mass = 196.6 / 1000
    grain_dens = grain_mass / grain_volume
    srad_motor_dry_mass = 622 / 1000                    # SOTTRAENDO GRAIN SIMULATO (196g) DAL MOTORE REALE WET (818g), AGGIORNA CON MASSA SOLIDWORKS
    #thrust_curve = str(BASE_DIR/"simulation_inputs/propulsion_data/SRAD_thrustcurve_8mm.csv")
    thrust_curve = str(BASE_DIR/"simulation_inputs/propulsion_data/reshape_test_2026-05-21_20-44-20.csv")

elif motore == 'nozzle 8mm sim':
    #   SRAD motor info BRICO 45 8mm
    impulse = 234.43507869871195
    t_burnout = 0.735                       # VALORE SIMULATO
    grain_external_radius = 0.033 / 2
    grain_internal_radius = 0.013 / 2 
    grain_length = 0.147
    grain_volume = 3.14*((grain_external_radius*2)-(grain_internal_radius*2))*grain_length
    grain_mass = 196.6 / 1000
    grain_dens = grain_mass / grain_volume
    srad_motor_dry_mass = 622 / 1000                    # SOTTRAENDO GRAIN SIMULATO (196g) DAL MOTORE REALE WET (818g), AGGIORNA CON MASSA SOLIDWORKS
    thrust_curve =str(BASE_DIR/"simulation_inputs/propulsion_data/SRAD_thrustcurve_8mm.csv")

elif motore == 'nozzle 7mm test':
    #   SRAD motor info BRICO 45 7mm
    impulse = 243.96
    t_burnout = 2.37                      # VALORE TEST
    grain_external_radius = 0.033 / 2
    grain_internal_radius = 0.013 / 2 
    grain_length = 0.147
    grain_volume = 3.14*((grain_external_radius*2)-(grain_internal_radius*2))*grain_length
    grain_mass = 196.6 / 1000
    grain_dens = grain_mass / grain_volume
    srad_motor_dry_mass = 622 / 1000  
    thrust_curve =str(BASE_DIR/"simulation_inputs/propulsion_data/reshape_test_2026-05-21_21-07-43.csv")

elif motore == 'nozzle 7mm sim':
    #   SRAD motor info BRICO 45 7mm
    impulse = 243.96
    t_burnout = 0.640                       # VALORE SIMULATO
    grain_external_radius = 0.033 / 2
    grain_internal_radius = 0.013 / 2 
    grain_length = 0.147
    grain_volume = 3.14*((grain_external_radius*2)-(grain_internal_radius*2))*grain_length
    grain_mass = 196.6 / 1000
    grain_dens = grain_mass / grain_volume
    srad_motor_dry_mass = 622 / 1000   
    thrust_curve =str(BASE_DIR/"simulation_inputs/propulsion_data/SRAD_thrustcurve_7mm.csv")

if configurazione == "2x_barre_alte":
    CG_position_from_nose = 397 / 1000          # mm
    dry_mass = 2374 / 1000                      # g
elif configurazione == "4x_barre_alte":
    CG_position_from_nose = 391 / 1000          # mm
    dry_mass =  2618 / 1000                     # g
elif configurazione == "v2.3":

    CG_position_from_nose = 416 / 1000          # mm
    dry_mass = 2692 / 1000                      # g

ballast =  0                           # NON TOCCARE, NON RAPPRESENTA LA REALTA'     #   (kg)

analysis_parameters = {
    
    # === Mass Details ===
    
    # Rocket's dry mass without grains' weight (kg) and its uncertainty (standard deviation)2130
    "rocket_dry_mass": ( dry_mass + ballast, 0.03),
    # Rocket's dry inertia moment perpendicular to its axis (kg*m^2)
    "rocket_dry_inertia_11": (1.49, 0.00187),
    # Rocket's dry inertia moment relative to its axis (kg*m^2)
    "rocket_dry_inertia_33": (0.01, 0.000122),

    # === Propulsion Details ===

    # Dry Motor Mass

    # Motors's dry mass without propellant (kg) and its uncertainty (standard deviation).
    "motor_dry_mass": (srad_motor_dry_mass, 0.0001),                                                        # 7 mm
    # Motor's dry inertia moment perpendicular to its axis (kg*m^2)
    "motor_inertia_11": (0.66, 0.00001),                                                                    # 7 mm
    # Motor's dry inertia moment relative to its axis (kg*m^2)
    "motor_inertia_33": (0.00001, 0.00001),                                                                   # 7 mm
    # Distance between the origin of the referential system and motor's center of dry mass (m)
    "motor_dry_mass_position": (99.41 / 1000, 0.001),                                                             # 7 mm
    # "motor_dry_mass_position": (98.86 / 1000, 0.001),                                                            # 8 mm

    # Performance

    # Motor total impulse (N*s)
    "impulse": (impulse, 1),
    # Motor burn out time (s)
    "burn_time": (t_burnout, 0.01),
    # Motor's nozzle radius (m)                                                         # both nozzle dimesions are taken from Borealis
    "nozzle_radius": (13.71 / 1000, 1 / 1000),
    # Motor's nozzle throat radius (m)
    "throat_radius": (9.50 / 1000, 1 / 1000),
    # Origin of the motor coordinate system
    "nozzle_position": (0, 0.001),
    # Motor's grain separation (axial distance between two grains) (m)
    "grain_separation": (3 / 1000, 0.1 / 1000),
    # Motor's grain density (kg/m^3)
    "grain_density": (grain_dens, 1),
    # Motor's grain outer radius (m)
    "grain_outer_radius": (grain_external_radius, 0.0001),
    # Motor's grain inner radius (m)
    "grain_initial_inner_radius": (grain_internal_radius, 0.001),
    # Motor's grain height (m)
    "grain_initial_height": (grain_length, 0.001),
    # Distance between the origin of the referential system and center of propellant mass (m) 
    "grains_center_of_mass_position": (125 / 1000, 0.001), 

    # === Aerodynamic Details ===
    
    # Rocket's radius (m)
    "radius": (42.5 / 1000, 0.001),
    # Multiplier for rocket's power off drag curve to introduce uncertainty
    "power_off_drag_corr": (1.0, 0.001),
    # Multiplier for rocket's power on drag curve to introduce uncertainty
    "power_on_drag_corr": (1.0, 0.001),
    # Rocket's nose cone length (m)

    # Nose

    "nose_length": (0.14, 0.001),
    # Power of the function that describes the shape of the nose cone
    "nose_pwr" : (0.4, 0.001),
    # The origin of the coordinate system (m)
    "nose_position": (0, 0),

    # Fins

    # Number of fins
    "fin_number" : (3, 0), 
    # Fin span (m)
    "fin_span": (0.12, 0.0005), 
    # Fin root chord (m)
    "fin_root_chord": (0.12, 0.0005), 
    # Fin tip chord (m)
    "fin_tip_chord": (0.03, 0.0005), 
    # Axial distance between rocket's tip and nearest point in its fin (m)
    "fin_position": (0.686, 0.005), 
    # Fin sweep angle (degrees)
    "fin_sweep_angle": (30.3, 0.005),

    # Tail

    # Axial distance from the tip of the nose (m)
    "tail_position": (810 / 1000, 0.001),
    # Tail length (m)
    "tail_length": (43 / 1000, 0.001), 
    # Tail bottom radius (m)
    "tail_bottom_radius": (30 / 1000, 0.001), 
    # Tail top radius (m)
    "tail_top_radius": (42.5 / 1000, 0.001), 

    # === Launch and Environment Details ===

    # Launch rail inclination angle relative to the horizontal plane (degrees)
    "inclination": (80, 3), # DA MODIFICARE 2, L'ORIGINALE ERA 80, COME RANGE CONSIDERA 75-84
    # Launch rail heading relative to north (degrees)
    "heading": (180, 5), # MODIFICARE 1, è compreso fra 160 a 180
    # Launch rail length (m)
    "rail_length": (1.5, 0.005), # MODIFICARE 3 SE NECESSARIO
    # Members of the ensemble forecast to be used
    "ensemble_member": list(range(10)),

    # === Parachute Details ===

    # Drag coefficient times reference area for the rocket main chute (m^2)
    "cd_s_main": (0.97 * 1.168, 0.0277),                                                        # 4ft rocketman without spillout
    # Time delay between parachute ejection signal is detected and parachute is inflated (s)
    "lag_rec": (2, 0.5),                                                                        # more conservative, previous was (1.73 , 0.2)
    
    # === Rail buttons Details ===
    
    # Position of the rail button closer to the tip of the rocket (m)
    "upper_button_y": (424 / 1000, 0.005),
    # Position of the rail button further to the tip of the rocket (m)
    "lower_button_y": (625 / 1000, 0.005),
    # Angular position of the buttons (degrees)
    "angular_button": (0, 0.01),

    # === Electronic Systems and Sensors Details ===

    # Time delay between sensor signal is received and ejection signal is fired (s)
    "lag_se": (0.1, 0.05),                                                                          # more conservative
    # Mean noise value of the Pressure signal (Pa) 
    "noise_mean": (0 , 0.001),
    # Standard deviation of the Pressure signal (Pa)
    "noise_p_stdev": (6.5 , 0.01),
    # Time correlation of the Pressure signal
    "noise_p_tc": (0.3 , 0.01),
}

#-------------------------------------------------------------------------------------------------------- START TIMER
# Initialize counter and timer
i = 0

initial_wall_time = time.time()
initial_cpu_time = process_time()
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- FUNCTIONS
# Definition of global variables, to be used inside and outside parachute functions
global last_negative_time, apogee_detected, sampling_rate, parachute_timer

# This variable marks the first instant in which a negative velocity is detected
last_negative_time = None
# This variable indicates whether the algorythm has acknowledged the rocket has reached apogee.
# A "False" value may mean that negative velocity has not yet been detected, 
# or that it has been detected but has not yet been consistent for enough seconds (the threshold)
apogee_detected = False
# This variable indicates the sampling rate of the recovery activation algorythm
sampling_rate = 105
# This variable keeps track of the flight time from ignition to the first recovery event 
parachute_stopwatch = 0

# Definition of useful functions

def convert_numpy(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        raise TypeError(
        f"Object of type {type(obj)} is not JSON serializable"
        )

def flight_settings(analysis_parameters, total_number):
    i = 0
    while i < total_number:
        # Generate a flight setting
        flight_setting = {}
        for parameter_key, parameter_value in analysis_parameters.items():
            if type(parameter_value) is tuple:
                flight_setting[parameter_key] = normal(*parameter_value)
            else:
                flight_setting[parameter_key] = choice(parameter_value)

        # Skip if certain values are negative, which happens due to the normal curve but isnt realistic
        if flight_setting["lag_rec"] < 0 or flight_setting["lag_se"] < 0:
            continue

        # Update counter
        i += 1
        # Yield a flight setting
        yield flight_setting

def export_flight_data(flight_setting, flight_data, exec_time):
    # Generate flight results
    flight_result = {
        "out_of_rail_time": flight_data.out_of_rail_time,
        "out_of_rail_velocity": flight_data.out_of_rail_velocity,
        "max_velocity": flight_data.speed.max,
        "max_acceleration": flight_data.acceleration.max,
        "max_aerodynamic_drag": flight_data.aerodynamic_drag.max,
        "max_aerodynamic_lift": flight_data.aerodynamic_lift.max,
        "max_aerodynamic_spin_moment": flight_data.aerodynamic_spin_moment.max,
        "max_aerodynamic_bending_moment": flight_data.aerodynamic_bending_moment.max,
        "apogee_time": flight_data.apogee_time,
        "apogee_altitude": flight_data.apogee - Env.elevation,
        "apogee_x": flight_data.apogee_x,
        "apogee_y": flight_data.apogee_y,
        "impact_time": flight_data.t_final,
        "impact_x": flight_data.x_impact,
        "impact_y": flight_data.y_impact,
        "impact_velocity": flight_data.impact_velocity,
        "initial_static_margin": flight_data.rocket.static_margin(0),
        "out_of_rail_static_margin": flight_data.rocket.static_margin(
            flight_data.out_of_rail_time
        ),
        "final_static_margin": flight_data.rocket.static_margin(
            flight_data.rocket.motor.burn_out_time
        ),
        "number_of_events": len(flight_data.parachute_events),
        "execution_time": exec_time,
    }

    # Take care of parachute results
    if len(flight_data.parachute_events) > 0:
        flight_result["drogue_triggerTime"] = flight_data.parachute_events[0][0]
        flight_result["drogue_inflated_time"] = (
            flight_data.parachute_events[0][0] + flight_data.parachute_events[0][1].lag
        )
        flight_result["drogue_inflated_velocity"] = flight_data.speed(
            flight_data.parachute_events[0][0] + flight_data.parachute_events[0][1].lag
        )
    else:
        flight_result["drogue_triggerTime"] = 0
        flight_result["drogue_inflated_time"] = 0
        flight_result["drogue_inflated_velocity"] = 0

    # Write flight setting and results to file, in json format for better use in the sensitivity analysis
    dispersion_input_file.write(json.dumps(flight_setting, default=convert_numpy) + "\n")   
    dispersion_output_file.write(json.dumps(flight_result, default=convert_numpy) + "\n")


def export_flight_error(flight_setting):
    dispersion_error_file.write(str(flight_setting) + "\n")


# The following function is a Python representation of the C code that 
# will be used on the rocket to detect the apogee condition. 
# In the actual code, detection of negative velocity is achieved
# thanks to the readings from the IMU sensor
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
    
# Set up parachute trigger for the drogue chute
def simulator_check_chute_opening(p, h, y):
    global last_negative_time, apogee_detected, parachute_stopwatch, sampling_rate
    altitude = h
    vertical_velocity = y[5]

    # Update counter for flight time to apogee:
    # each time this function is called, the timer advances of 1 over the frequency at which the function is called.
    # This is a workaround to get a measure of in-flight time
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

def test_main_timeout_opening(p, h ,y):

    """
    set the desired opening altitude (AGL)
    to achieve this ensure that 'lag' is set '=0' in the parachute definition
    """
    # => OPENING ALTITUDE:
    opening_altitude = 30

    altitude = h    # altitude
    vz = y[5]   # vertical velocity
    
    if vz < 0 and altitude <= opening_altitude:
        return True
    else:
        return False

#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- STYLE
# Matplotlib graph General style
plt.rcParams.update({"axes.titlesize": 12})
plt.rcParams.update({'xtick.labelsize': 8, 'ytick.labelsize': 8})
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['legend.fontsize'] = 8
graph_color = 'red'
plt.rcParams['axes.titlepad'] = 15
plt.rcParams['xtick.minor.visible'] = True
plt.rcParams['ytick.minor.visible'] = True
plt.rcParams['savefig.bbox'] = 'tight'
plt.rcParams['savefig.pad_inches'] = 0.2
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 150

# function that takes a text and add code for green color (ANSI Escape Codes)
colored = lambda text: '\033[32m'+str(text)+'\033[0m'   # 32 green

def loading_bar(initial_time: datetime, number_of_iterations:int, iteration:int, bar_lenght:int=24):
    time_for_iteration = (process_time() - initial_time) / iteration
    seconds_remaining = round(time_for_iteration*(number_of_iterations-iteration))

    current_iteration = f"{iteration:0{len(str(number_of_iterations))}d}"
    average_time = f"{time_for_iteration:2.2f}s"
    time_remaining = f"{seconds_remaining//3600:02d}:{(seconds_remaining%3600)//60:02d}:{seconds_remaining%60:02d}"
    bar = f"{'\u2588'*(bar_lenght*iteration//number_of_iterations):\u2591<{bar_lenght}}"
    percentage = f"{100*iteration/number_of_iterations:.1f}%"

    print(f"Current iteration: {colored(current_iteration)}",end=' ')
    print(f"Average time per iteration: {colored(average_time)}",end=' ')
    print(f"Time remaining: {colored(time_remaining)}",end=" ")
    print(f"|{colored(bar)}|[{colored(percentage):<7}]",end="\r")
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- PATH, FOLDER & FILE
# Paths
output_path = Path(str(BASE_DIR/"montecarlo_output"/output_dir_name))
filename = str(output_path/"FRED")

output_sensitivity = Path(output_path/"sensitivity")

output_comparison = Path(output_path/"comparison")

output_dispersion = Path(output_path/"dispersion")
output_dispersion_pickle = Path(output_dispersion/"pickle")
output_dispersion_svg = Path(output_dispersion/"svg")

output_launch_site = Path(output_path/"launch_site")

output_environmental_conditions = Path(output_path/"environmental_conditions") # aggiunta io
output_environmental_conditions_pickle = Path(output_environmental_conditions/"pickle")
output_environmental_conditions_svg = Path(output_environmental_conditions/"svg")

# First information print
print("Montecarlo Rocket flight simulator\n")
print(f"- Filename is: {colored(filename)}")
print(f"- Number of simulations: {colored(number_of_simulations)}")
print(f"- Output directory: {colored(output_dir_name)}\n")

#WARNINGS

# with less than 50 simulations sensitivity analysis returns errors
if number_of_simulations<50:
    print(f"<!> Less than 50 simulations: {colored('sensitivity analysis deactivated')}")
    sensitivity_analysis = False

# Create or overwrite folders for outputs
if output_path.is_dir():
    overwrite_folder = input(f'<!> The "{output_dir_name}" folder already exists. Do you want to overwrite it? [{colored('y/n')}] - ')
    if not overwrite_folder.lower() in ['y','yes']:
        print("You chose not to overwrite the folder. Stopping the program.")
        raise SystemExit(0)

print("\nStarting...", end='\r')

#create folders
output_sensitivity.mkdir(parents=True, exist_ok=True)
output_comparison.mkdir(parents=True, exist_ok=True)
output_dispersion_pickle.mkdir(parents=True, exist_ok=True)
output_dispersion_svg.mkdir(parents=True, exist_ok=True)
output_launch_site.mkdir(parents=True, exist_ok=True)


# Create data files for inputs, outputs and error logging
dispersion_error_file = open(str(filename) + ".disp_errors.txt", "w")
dispersion_input_file = open(str(filename) + ".disp_inputs.json", "w")
dispersion_output_file = open(str(filename) + ".disp_outputs.json", "w")
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- ENVIRONMENT
Env = Environment(
    date = date_of_launch,
    longitude = longitude,
    latitude = latitude,
    elevation = elevation,
    max_expected_height = 1500
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
        type="Windy",
        file="GFS"
    )
elif weather_data == 'm': # MODIFICARE solo se si usa vento avverso modifica magnitude ed heading in modo da non andare contro spettatori e case e trovare cosi il worst case di vento
    # Manual setting of the wind

    # Wind magnitude on the ground in (m/s)
    wind_magnitude_ground = 8.7                          # m/s, EuRoC limit is 8.7m/s on the ground
    # Heading of the wind from North in degrees
    wind_heading = 315                                  # degrees from North, MODIFICA: LE CASE SONO A: ; GLI SPETTATORI A:

    # CAREFUL:  Heading of the wind means where it is going
    #           Direction means where it comes from
    #               If you want to set a wind from North going South set 180 because it heads South and South is 180 deg from North

    wind_heading_r = math.radians(wind_heading)         # tranforms into radians
    s_heading = math.sin(wind_heading_r)                # sin of the wind profile
    c_heading = math.cos(wind_heading_r)                # cos of the wind profile

    # Creates an array of values to generate a wind profile
    custom_wind_u = [
        ( 0 , wind_magnitude_ground * s_heading),
        ( 50 , 1.05 * wind_magnitude_ground * s_heading),
        ( 100 , 1.1 * wind_magnitude_ground * s_heading),
        ( 150 , 1.15 * wind_magnitude_ground * s_heading),
        ( 200 , 1.2 * wind_magnitude_ground * s_heading),
        ( 250 , 1.25 * wind_magnitude_ground * s_heading),
        ( 300 , 1.3 * wind_magnitude_ground * s_heading),
    ]

    custom_wind_v = [
        ( 0 , wind_magnitude_ground * c_heading),
        ( 50 , 1.05 * wind_magnitude_ground * c_heading),
        ( 100 , 1.1 * wind_magnitude_ground * c_heading),
        ( 150 , 1.15 * wind_magnitude_ground * c_heading),
        ( 200 , 1.2 * wind_magnitude_ground * c_heading),
        ( 250 , 1.25 * wind_magnitude_ground * c_heading),
        ( 300 , 1.3 * wind_magnitude_ground * c_heading),
    ]

    Env.set_atmospheric_model(
    type="custom_atmosphere",
    wind_u=custom_wind_u,
    wind_v=custom_wind_v,
    )

    # Check if the wind profiles are accurate
    Env.all_info()

elif weather_data!='i':
    # The default weather data type is the International Standard Atmosphere (ISA).
    # If none of the previously listed options is selected, this model will be applied automatically.
    print('<!> International Standard Atmosphere (ISA) as defined by ISO 2533 is initialized as weather data <!>')

#---------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- MONTECARLO
# Initiate collection of flight data.
# This allows to compare different flight from the Montecarlo analysis and visualize
# data dispersion and overall characteristics of the flight and the simulation itself
flights=[]

# Iterate over flight settings
for setting in flight_settings(analysis_parameters, number_of_simulations):

    last_negative_time = None
    apogee_detected = False
    parachute_stopwatch = 0

    start_time = process_time()
    i += 1
    #print(f"\rCurrent iteration: {i}", end="")

    if Env.atmospheric_model_type == "Ensemble":
        # Update environment object
        Env.select_ensemble_member(setting["ensemble_member"])

    # Define COTS motor
    Solid_motor = SolidMotor(
        # Thrust data
        thrust_source=thrust_curve,
        burn_time=setting["burn_time"],
        reshape_thrust_curve=(setting["burn_time"], setting["impulse"]),
        interpolation_method="linear",
        # Nozzle data
        nozzle_radius=setting["nozzle_radius"],
        throat_radius=setting["throat_radius"],
        # Grain data
        grain_number=1,
        grain_separation=setting["grain_separation"],
        grain_density=setting["grain_density"],
        grain_outer_radius=setting["grain_outer_radius"],
        grain_initial_inner_radius=setting["grain_initial_inner_radius"],
        grain_initial_height=setting["grain_initial_height"],
        # Geometric data
        nozzle_position=setting["nozzle_position"],
        grains_center_of_mass_position=setting["grains_center_of_mass_position"],
        dry_mass=setting["motor_dry_mass"],
        dry_inertia=(
            setting["motor_inertia_11"],
            setting["motor_inertia_11"],
            setting["motor_inertia_33"],
        ),
        center_of_dry_mass_position=setting["motor_dry_mass_position"],
        coordinate_system_orientation = "nozzle_to_combustion_chamber",
    )

    power_off_drag = str(BASE_DIR / "simulation_inputs/aerodynamic_data/FRED_v2.0_CD_power_off.csv")
    power_on_drag  = str(BASE_DIR / "simulation_inputs/aerodynamic_data/FRED_v2.0_CD_power_on.csv")


# Now create the Rocket

    # Create rocket
    FRED = Rocket(
        radius=setting["radius"],
        mass=setting["rocket_dry_mass"],
        inertia=(
            setting["rocket_dry_inertia_11"],
            setting["rocket_dry_inertia_11"],
            setting["rocket_dry_inertia_33"],
        ),
        power_off_drag=power_off_drag,
        power_on_drag=power_on_drag,
        # Define the center of dry mass as the distance from the tip of the nose, and set the positive axis orientation
        center_of_mass_without_motor=CG_position_from_nose,
        coordinate_system_orientation="nose_to_tail",
    )

    # Define rail buttons
    FRED.set_rail_buttons(
        upper_button_position= setting["upper_button_y"], 
        lower_button_position= setting["lower_button_y"], 
        angular_position= setting["angular_button"],
    )

    # Add the motor to the rocket assembly
    # sets the motor's CDM on the rocket's CDM.
    # The "grain center of mass position" parameter will handle the position of the actual motor
    FRED.add_motor(Solid_motor, position=(setting["tail_position"]+setting["tail_length"]))

    # Add uncertainty to the drag curves, by multiplying them by a small, random corrective factor
    FRED.power_off_drag *= setting["power_off_drag_corr"]
    FRED.power_on_drag *= setting["power_on_drag_corr"]

    # Define and add the Nosecone section
    NoseCone = FRED.add_nose(
        length=setting["nose_length"],
        kind="elliptical",
        power= "nose_pwr",
        position=setting["nose_position"],
    )

    # Define and add the Fins
    FinSet = FRED.add_trapezoidal_fins(
        n=3,
        span=setting["fin_span"],
        root_chord=setting["fin_root_chord"],
        tip_chord=setting["fin_tip_chord"],
        position=setting["fin_position"],
        sweep_angle=setting["fin_sweep_angle"],
        cant_angle=0,
        airfoil = None,
    )

    # Define and add the Boat-tail
    Tail = FRED.add_tail(
        top_radius=setting["tail_top_radius"],
        bottom_radius=setting["tail_bottom_radius"], 
        length=setting["tail_length"], 
        position = setting["tail_position"],
    )

    # Define and add the Main parachute
    if not ballistic:
        Main = FRED.add_parachute(
            name = "Main",
            cd_s=setting["cd_s_main"],
            # trigger=test_main_timeout_opening,
            # trigger = "apogee",
            trigger = simulator_check_chute_opening,
            sampling_rate=sampling_rate,
            lag=setting["lag_se"] + setting["lag_rec"],
            # lag = 0.001,
            noise=(
                setting["noise_mean"],
                setting["noise_p_stdev"],
                setting["noise_p_tc"],
            ),
        )
    
# --- IMPLEMENTAZIONE SENSORI ---
    sensor_position = CG_position_from_nose

    accel_noisy = Accelerometer(
        sampling_rate=105, consider_gravity=True, orientation=(0,0,0), measurement_range=100,
        resolution=0.25, noise_density=0.02, random_walk_density=0.005, constant_bias=1.0,
        temperature_bias=0.05, operating_temperature=25, cross_axis_sensitivity=0.02, name="Accelerometer"
    )
    accel_clean = Accelerometer(
        sampling_rate=105, consider_gravity=True, orientation=(0,0,0), measurement_range=100,
        resolution=0.0, noise_density=0.0, random_walk_density=0.0, constant_bias=0.0,
        operating_temperature=25, temperature_bias=0.0, cross_axis_sensitivity=0.0, name="Clean Accelerometer"
    )
    barom_noisy = Barometer(
        sampling_rate=50, measurement_range=200000, resolution=0.1, noise_density=15.0,
        noise_variance=15.0, random_walk_density=0.01, constant_bias=1.5, operating_temperature=25,
        temperature_bias=0.03, temperature_scale_factor=0.02, name="Noisy Barometer"
    )
    barom_clean = Barometer(
        sampling_rate=50, measurement_range=200000, resolution=0.0, noise_density=0.0,
        constant_bias=0.0, operating_temperature=25, temperature_bias=0.0, name="Clean Barometer"
    )

    FRED.add_sensor(accel_noisy, sensor_position)
    FRED.add_sensor(accel_clean, sensor_position)
    FRED.add_sensor(barom_noisy, sensor_position)
    FRED.add_sensor(barom_clean, sensor_position)
    # --------------------------------



    # Run trajectory simulation
    try: 
        rocket_flight = Flight(
            rocket=FRED,
            environment=Env,
            rail_length=setting["rail_length"],
            inclination=setting["inclination"],
            heading=setting["heading"],
            max_time=1200,
        )

        export_flight_data(setting, rocket_flight, process_time() - start_time)
    except Exception as E:
        print(E)
        export_flight_error(setting)

    flights.append(rocket_flight)

    # Update loading bar
    loading_bar(
        initial_time=initial_cpu_time,
        number_of_iterations=number_of_simulations,
        iteration=i,
        )

# jump a row to not overwrite loading bar
print('\n')


# Print total time
cpu_time = round(process_time() - initial_cpu_time, 2)
wall_time = round(time.time() - initial_wall_time, 2)
final_string = f"Completed {i} iterations successfully. Total CPU time: {colored(cpu_time)} s. Total wall time: {colored(wall_time)} s"
print(final_string)


# Close files
dispersion_input_file.close()
dispersion_output_file.close()
dispersion_error_file.close()
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- READ OUTPUT FILE
# Initialize variable to store all results
dispersion_general_results = []

dispersion_results = {
    "out_of_rail_time": [],
    "out_of_rail_velocity": [],
    "apogee_time": [],
    "apogee_altitude": [],
    "apogee_x": [],
    "apogee_y": [],
    "impact_time": [],
    "impact_x": [],
    "impact_y": [],
    "impact_velocity": [],
    "initial_static_margin": [],
    "out_of_rail_static_margin": [],
    "final_static_margin": [],
    "number_of_events": [],
    "max_velocity": [],
    "max_acceleration": [],
    "max_load_factor": [],
    "max_parachute_chord_traction_force": [],
    "max_aerodynamic_drag": [],
    "max_aerodynamic_lift": [],
    "max_aerodynamic_spin_moment": [],
    "max_aerodynamic_bending_moment": [],
    "drogue_triggerTime": [],
    "drogue_inflated_time": [],
    "drogue_inflated_velocity": [],
    "execution_time": [],
}

# Get all dispersion results
dispersion_output_file = open(str(filename) + ".disp_outputs.json", "r+")

# Read each line of the file and convert to dict
for line in dispersion_output_file:
    # Skip comments lines
    if line[0] != "{":
        continue
    # Eval results and store them
    flight_result = eval(line)
    dispersion_general_results.append(flight_result)
    for parameter_key, parameter_value in flight_result.items():
        dispersion_results[parameter_key].append(parameter_value)

# Close data file
dispersion_output_file.close()
#--------------------------------------------------------------------------------------------------------



#-------------------------------------------------------------------------------------------------------- COMPARISON GRAPHS
# the commented rows are not implemented yet by rocketpy
print(colored('\n\nComparison graphs:'))
comparison = CompareFlights(flights)

if show_graph:
    comparison.velocities()
    comparison.accelerations()
    # comparison.attitude_angles()
    # comparison.euler_angles()
    #comparison.attitude_frequency()
    comparison.aerodynamic_forces()
    # comparison.aerodynamic_moments()
    # comparison.angular_velocities()
    # comparison.trajectories_3d()
    # comparison.rail_buttons_forces()
    #comparison.stability_margin()

comparison.velocities(filename=str(output_comparison/"velocities.svg"),legend=False)
comparison.accelerations(filename=str(output_comparison/"accelerations.svg"),legend=False)
comparison.attitude_angles(filename=str(output_comparison/"attitude_angles.svg"),legend=False)
#comparison.euler_angles(filename=str(output_comparison/"euler_angles.svg"),legend=False)
#comparison.attitude_frequency(filename=str(output_comparison/"attitude_frequency.svg"),legend=False)
comparison.aerodynamic_forces(filename=str(output_comparison/"aerodynamic_forces.svg"),legend=False)
comparison.aerodynamic_moments(filename=str(output_comparison/"aerodynamic_moments.svg"),legend=False)
comparison.angular_velocities(filename=str(output_comparison/"angular_velocities.svg"),legend=False)
comparison.trajectories_3d(filename=str(output_comparison/"trajectories_3d.svg"))
comparison.rail_buttons_forces(filename=str(output_comparison/"rail_buttons_forces.svg"),legend=False)
comparison.stability_margin(filename=str(output_comparison/"stability_margin.svg"), legend=False)
plt.close('all')
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- DISPERSION GRAPHS
# The following section generates the output distribution plots and automatically saves them on your PC
# To create each picture, the algorythm performs the following actions:

# - Fits a normal distribution to the dataset and compute the average value and standard deviation;
# - Prints the fitted mean and standard deviation,
# - Creates a histogram of the data and overlays the corresponding normal distribution curve;
# - Adds title, axis labels, and a grid to the plot for better clarity;
# - Saves the plot as a .svg file for high-quality output (e.g., for reports or web use);
# - Saves the entire figure as a pickle file for later reuse or resizing;

# The pickle format was chosen so that the user can open the images/graphs files
# (using the design file show_images.py) in a format that allows them to zoom in and out
# and examine the pictures more accurately

def plot_unit_of_measure(unit_of_measure: str):
    # correct way to print unit of measure inside plot
    if '*' in unit_of_measure:
        unit_of_measure = unit_of_measure.replace('*','$\\cdot$')
    while '^' in unit_of_measure:
        start = unit_of_measure.find('^')
        end = start+1
        e = True
        while e:
            if end+1<len(unit_of_measure):
                if unit_of_measure[end+1].isdigit() or unit_of_measure[end+1] in ['.','-']:
                    end+=1
                else:
                    e = False
            else:
                e = False
        unit_of_measure = unit_of_measure[:start]+'$@{'+unit_of_measure[start+1:end+1]+'}$'+unit_of_measure[end+1:]
    unit_of_measure = unit_of_measure.replace('@','^')
    return unit_of_measure

def plot_graph(dispersion_result, x_label ,title, unit_of_measure):
    
    s = plt.figure()

    out_data = dispersion_results[dispersion_result]
    mu_out, std_out = norm.fit(out_data)

    bars = plt.hist(
        out_data,
        bins=int(number_of_simulations**0.5),
        label=title, edgecolor="white",
        color=graph_color,
        alpha=0.3,
        density=True
        )

    x_out = np.linspace(min(out_data), max(out_data), 1000)
    pdf_out = norm.pdf(x_out, mu_out, std_out)
    
    plt.plot(x_out, pdf_out, '--k', linewidth=1.5)
    plt.fill_between(x_out, pdf_out, color=graph_color, alpha=0.5)

    plt.figtext(
        .72, .91,
        f'μ = {str(mu_out)[:6]} {plot_unit_of_measure(unit_of_measure)}\nσ = {str(std_out)[:6]} {plot_unit_of_measure(unit_of_measure)}',
        fontsize=10
        )
    plt.title(title, loc='left')

    # labels
    x_label = x_label+(' ('+plot_unit_of_measure(unit_of_measure)+')' if plot_unit_of_measure(unit_of_measure) else '')
    plt.xlabel(x_label)
    plt.ylabel("Probability Density")
    
    plt.ylim(0)
    plt.grid(False)

    # Print information
    print(f'{colored(title)}\n\t- Mean Value: {colored(round(mu_out,3))} {unit_of_measure}')
    print(f'\t- Standard Deviation: {colored(round(std_out,3))} {unit_of_measure}\n')
    

    # SAVE GRAPH
    
    # as SVG 
    plt.savefig(str(output_dispersion_svg/title)+".svg", format='svg')

    # as pickle
    pickle_file = str(output_dispersion_pickle/title)+".pickle"
    with open(pickle_file, "wb") as f:
        pickle.dump(s, f)

    if show_graph:
        plt.show()

    plt.close(s)    # Stop automatic printing of images

all_plots = {
    "Out of Rail Time" : ["out_of_rail_time", "Time","s"],
    "Out of Rail Velocity": ["out_of_rail_velocity", "Velocity", "m/s"],
    "Apogee Time":["apogee_time", "Time", "s"],
    "Apogee Altitude":["apogee_altitude","Altitude", "m"],
    "Apogee X Position":["apogee_x","Apogee X Position", "m"],
    "Apogee Y Position":["apogee_y","Apogee Y Position", "m"],
    "Impact Time":["impact_time","Time","s"],
    "Impact X Position":["impact_x","Impact X Position", "m"],
    "Impact Y Position":["impact_y","Impact Y Position", "m"],
    "Impact Velocity":["impact_velocity","Velocity", "m/s"],
    "Initial Static Margin":["initial_static_margin","Static Margin", "c"],
    "Out of Rail Static Margin":["out_of_rail_static_margin","Static Margin", "c"],
    "Final Static Margin":["final_static_margin","Static Margin", "c"],
    "Maximum Velocity":["max_velocity","Velocity", "m/s"],
    "Maximum Acceleration":["max_acceleration","Acceleration", "m/s^2"],
    # "Maximum Load Factor":["max_load_factor","Load Factor","G"],
    "Maximum Aerodynamic Drag":["max_aerodynamic_drag","Drag Force","N"],
    "Maximum Aerodynamic Lift":["max_aerodynamic_lift","Lift Force", "N"],
    "Maximum Aerodynamic Spin Moment":["max_aerodynamic_spin_moment","Spin Moment", "N*m"],
    "Maximum Aerodynamic Bending Moment":["max_aerodynamic_bending_moment","Bending Moment", "N*m"],
    #"Parachute Events":["number_of_events","Number of Parachute Events"],
    "Drogue Parachute Trigger Time":["drogue_triggerTime","Time", "s"],
    "Drogue Parachute Fully Inflated Time":["drogue_inflated_time","Time", "s"],
    "Drogue Parachute Fully Inflated Velocity":["drogue_inflated_velocity","Velocity", "m/s"],
}

print(colored('\n\nDispersion graphs:\n'))
for pp in all_plots:
    plot_graph(
        title=pp,
        dispersion_result=all_plots[pp][0],
        x_label=all_plots[pp][1],
        unit_of_measure=all_plots[pp][2]
        )
#--------------------------------------------------------------------------------------------------------


#-------------------------------------------------------------------------------------------------------- ENVIRONMENT

current_backend = matplotlib.get_backend()
matplotlib.use('Agg')

try:
    # Pulisce la memoria da grafici precedenti
    plt.close('all')
    
    # 2. Lanciamo all_info con il tuo modello Windy attivo
    # Genererà i grafici direttamente in memoria
    Env.all_info()
    
    # 3. Recuperiamo le figure reali appena generate
    fig_numbers = plt.get_fignums()
    plot_names = ["Environmental_Atmospheric_Model", "Environmental_Wind_Profile"]
    
    for i, num in enumerate(fig_numbers):
        fig = plt.figure(num)
        
        # Assegna il nome dall'array o uno generico se sono più di due
        title = plot_names[i] if i < len(plot_names) else f"Environmental_Graph_{i+1}"
        
        # Salva in formato SVG dentro la tua cartella dedicata
        svg_file = str(output_environmental_conditions_svg / title) + ".svg"
        fig.savefig(svg_file, format='svg', bbox_inches='tight')
        
        # Salva in formato Pickle per il tuo show_images.py
        pickle_file = str(output_environmental_conditions_pickle / title) + ".pickle"
        with open(pickle_file, "wb") as f:
            pickle.dump(fig, f)
            
        print(f"\t- Graph '{colored(title)}' saved successfully.")

except Exception as e:
    print(f"\t- {colored('Error', 'red')}: Could not save graphs. Details: {e}")

finally:
    # 4. Chiude i grafici fatti e RIPRISTINA il backend originale 
    # Così i grafici successivi (es. le dispersioni) potranno mostrasi normalmente se vuoi
    plt.close('all')
    matplotlib.use(current_backend)

print(colored('\n\nEnvironmental graphs saved!\n'))



#-------------------------------------------------------------------------------------------------------- LAUNCH SITE
print(colored('\n\nLaunch site graph:'))
# Import background map
img = imread(str(BASE_DIR / "simulation_inputs/environment_data/Villafranca_airfield_launch_site.jpg"))

# --- NUOVO: Mappatura del tipo di meteo e generazione etichette dinamiche ---
weather_mapping = {
    'c': 'Custom',
    'e': 'Ensemble',
    'f': 'Forecast',
    'i': 'ISA_Standard',
    'm': 'Manual_WorstCase'
}
weather_label = weather_mapping.get(weather_data, 'Unknown')

nominal_inc = analysis_parameters["inclination"][0]
nominal_hdg = analysis_parameters["heading"][0]

# Il nome del file ora includerà anche il tipo di meteo (es. _forecast o _manual_worstcase)
file_suffix = f"_inc{int(nominal_inc)}_hdg{int(nominal_hdg)}_{weather_label.lower()}"
# ----------------------------------------------------------------------------

# Retrieve dispersion data por apogee and impact XY position
apogee_x = np.array(dispersion_results["apogee_x"])
apogee_y = np.array(dispersion_results["apogee_y"])
impact_x = np.array(dispersion_results["impact_x"])
impact_y = np.array(dispersion_results["impact_y"])

# Define function to calculate eigen values
def eigsorted(cov):
    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    return vals[order], vecs[:, order]

# Create plot figure
s = plt.figure(num=None, dpi = 150, facecolor="w", edgecolor="k")
ax = plt.subplot(111)

# Draw launch point
plt.scatter(0, 0, s=30, marker="*", color="red", label="Launch Point")
# Draw apogee points
plt.scatter(
    apogee_x, apogee_y, s=5, marker="^", color="lime", label="Simulated Apogee", alpha=0.7
)
# Draw impact points
plt.scatter(
    impact_x, impact_y, s=5, marker="v", color="cyan", label="Simulated Landing Point", alpha=0.7
)

# Calculate error ellipses for impact
impactCov = np.cov(impact_x, impact_y)
impactVals, impactVecs = eigsorted(impactCov)
impactTheta = np.degrees(np.arctan2(*impactVecs[:, 0][::-1]))
impactW, impactH = 2 * np.sqrt(impactVals)

# Draw error ellipses for impact
impact_ellipses = []
for j in [1, 2, 3]:
    impactEll = Ellipse(
        xy=(np.mean(impact_x), np.mean(impact_y)),
        width=impactW * j,
        height=impactH * j,
        angle=impactTheta,
        color="black",
    )
    impactEll.set_facecolor((0, 0, 1, 0.2))
    impact_ellipses.append(impactEll)
    ax.add_artist(impactEll)

# Calculate error ellipses for apogee
apogeeCov = np.cov(apogee_x, apogee_y)
apogeeVals, apogeeVecs = eigsorted(apogeeCov)
apogeeTheta = np.degrees(np.arctan2(*apogeeVecs[:, 0][::-1]))
apogeeW, apogeeH = 2 * np.sqrt(apogeeVals)

# Draw error ellipses for apogee
for j in [1, 2, 3]:
    apogeeEll = Ellipse(
        xy=(np.mean(apogee_x), np.mean(apogee_y)),
        width=apogeeW * j,
        height=apogeeH * j,
        angle=apogeeTheta,
        color="black",
    )
    apogeeEll.set_facecolor((0, 1, 0, 0.2))
    ax.add_artist(apogeeEll)

plt.legend()

plt.grid(visible=True, which='minor', linestyle='--', color='grey', alpha=0.3, linewidth=0.6)
plt.grid(visible=True, which='major', linestyle='-', color='white', alpha=0.4, linewidth=0.8)

# Add title and labels to plot
ax.set_title(
    f"Dispersion Ellipses [{weather_label}] (Inc: {nominal_inc}°, Hdg: {nominal_hdg}°)\n"
    r"1$\sigma$, 2$\sigma$ and 3$\sigma$ Apogee and Landing Points"
)
ax.set_ylabel("North (m)")
ax.set_xlabel("East (m)")
# ------------------------------------------------------------------------------

# Add background image to plot
# You can translate the basemap by changing dx and dy (in meters)
dx = 250
dy = -150
plt.imshow(img, zorder=0, extent=[-850-dx, 850-dx, -500-dy, 500-dy])
plt.axhline(0, color="black", linewidth=0.5)
plt.axvline(0, color="black", linewidth=0.5)
plt.xlim(-850, 850)
plt.ylim(-500, 500)

# Save plot and show result
svg_file = output_launch_site / f"Villafranca_launch_site{file_suffix}.svg"
plt.savefig(str(svg_file), format='svg', bbox_inches="tight")
# as pickle

pickle_file = output_launch_site / f"Villafranca_launch_site{file_suffix}.pickle"
with open(pickle_file, "wb") as f:
    pickle.dump(s, f)

print(f"- Graph saved successfully as: Villafranca_launch_site{file_suffix}.svg")

if show_graph:
    plt.show()
plt.close('all')
#--------------------------------------------------------------------------------------------------------




#-------------------------------------------------------------------------------------------------------- SENSITIVITY ANALYSIS
if sensitivity_analysis:
    print(colored('\n\nSensitivity analysis graphs:'))


    target_variables = ["apogee_altitude","max_acceleration"]
    parameters = list(analysis_parameters.keys())

    parameters_matrix, target_variables_matrix = load_monte_carlo_data(
        input_filename=str(filename)+".disp_inputs.json",
        output_filename=str(filename)+".disp_outputs.json",
        parameters_list=parameters,
        target_variables_list=target_variables,
    )




    model = SensitivityModel(parameters, target_variables)


    parameters_nominal_mean = [
        analysis_parameters[parameter_name][0]
        for parameter_name in analysis_parameters.keys()
    ]
    parameters_nominal_sd = [
        analysis_parameters[parameter_name][1]
        for parameter_name in analysis_parameters.keys()
    ]
    model.set_parameters_nominal(parameters_nominal_mean, parameters_nominal_sd)
    target_variables_mean=[
    np.mean(dispersion_results["apogee_altitude"]),
    np.mean(dispersion_results["max_acceleration"])
    ]

    #plot the result of the sensitviy analisys
    model.set_target_variables_nominal(target_variables_mean)

    model.fit(parameters_matrix, target_variables_matrix)


    # Workaround (RocketPy doesn't provide a save option):
    # plt.ion() lets the code continue while bar_plot is displayed.
    # Figures are saved and remain open for viewing if desired.
    plt.ion() 
    model.plots.bar_plot()

    for target in range(len(target_variables)):
        sens_fig = plt.figure(target+1)

        svg_file = f"{str(output_sensitivity)}/sensitivity_{target_variables[target]}.svg"
        sens_fig.savefig(svg_file, dpi=300)

    if show_graph:
        plt.pause(99999) # that's a lot of damag...time.

    plt.close("all")
    plt.ioff()


    print("- Sensitivity analysis graphs saved successfully")
#-------------------------------------------------------------------------------------------------------


#-------------------------------------------------------------------------------------------------------- SENSORS OUTPUT
print(colored('\n\nGenerating Sensor graphs (for the last simulated flight):'))
outdir_sensors = BASE_DIR / "FRED_sensors_output"
outdir_sensors.mkdir(parents=True, exist_ok=True)

# Exporting and saving sensors data in csv format
accel_noisy.export_measured_data(str(outdir_sensors / "exported_noisy_accelerometer_data.csv"))
accel_clean.export_measured_data(str(outdir_sensors / "exported_clean_accelerometer_data.csv"))
barom_noisy.export_measured_data(str(outdir_sensors / "exported_noisy_barometer_data.csv"))
barom_clean.export_measured_data(str(outdir_sensors / "exported_clean_barometer_data.csv"))

def save_acceleration_plots(accel_noisy, accel_clean, outdir=outdir_sensors, show=False):
    outdir = Path(outdir)

    time1, ax, ay, az_raw = zip(*accel_noisy.measured_data)
    time2, bx, by, bz_raw = zip(*accel_clean.measured_data)

    # Invertiamo l'asse Z in modo che l'accelerazione verso l'alto sia positiva nei grafici (Richiesta dell'amico!)
    az = [-val for val in az_raw]
    bz = [-val for val in bz_raw]

    for axis_name, data1, data2 in zip(['ax', 'ay', 'az'], [ax, ay, az], [bx, by, bz]):
        plt.figure()
        plt.plot(time1, data1, label="Noisy Accelerometer")
        plt.plot(time2, data2, label="Clean Accelerometer")
        plt.xlabel("Time (s)")
        plt.ylabel(f"Acceleration {axis_name} (m/s^2)")
        plt.legend()
        plt.grid()
        plt.title(f"Acceleration comparison - {axis_name}")
        path = outdir / f"acceleration_{axis_name}.png"
        plt.savefig(path, dpi=200, bbox_inches="tight")
        if show: plt.show()
        plt.close()

    # Total acceleration
    abs_a = (np.array(ax) ** 2 + np.array(ay) ** 2 + np.array(az) ** 2) ** 0.5
    abs_b = (np.array(bx) ** 2 + np.array(by) ** 2 + np.array(bz) ** 2) ** 0.5

    plt.figure()
    plt.plot(time2, abs_b, label="clean")
    plt.plot(time1, abs_a, label="noisy")
    plt.xlabel("Time (s)")
    plt.ylabel("Acceleration (m/s^2)")
    plt.legend()
    plt.grid()
    plt.title("Acceleration")
    path = outdir / "acceleration_total.png"
    plt.savefig(path, dpi=200, bbox_inches="tight")
    if show: plt.show()
    plt.close()

def save_barometer_plot(barom_noisy, barom_clean, test_flight, outdir=outdir_sensors, show=False):
    outdir = Path(outdir)

    time_barometer, pressure_barometer = zip(*barom_clean.measured_data)
    time_barometer_noisy, pressure_barometer_noisy = zip(*barom_noisy.measured_data)
    rocket_pressure = test_flight.pressure.y_array
    rocket_time = test_flight.pressure.x_array

    plt.figure()
    plt.plot(rocket_time, rocket_pressure, label="Rocket")
    plt.plot(time_barometer, pressure_barometer, label="Clean Barometer")
    plt.plot(time_barometer_noisy, pressure_barometer_noisy, label="Noisy Barometer")
    plt.xlabel("Time (s)")
    plt.ylabel("Pressure (Pa)")
    plt.title("Pressure comparison")
    plt.grid()
    plt.legend()
    path = outdir / "barometer_pressure.png"
    plt.savefig(path, dpi=200, bbox_inches="tight")
    if show: plt.show()
    plt.close()

# Genera e salva tutti i grafici nella nuova cartella basandosi sull'ultimo volo del Monte Carlo
save_acceleration_plots(accel_noisy, accel_clean, outdir=outdir_sensors, show=False)
save_barometer_plot(barom_noisy, barom_clean, flights[-1], outdir=outdir_sensors, show=show_graph)

print(f"- Sensor graphs and CSV data saved successfully in {colored('FRED_sensors_output')}")