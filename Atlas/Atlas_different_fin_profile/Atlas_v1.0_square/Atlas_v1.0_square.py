# RocketPy Preliminary Simulation of the Atlas rocket, Aurora Rocketry Team, EuRoC 2025
# Authors: Daniele Bandini, Giovanni Bacchini, Caio Scattolini, Leonardo Francesco Neri, Alex Petrani, Federico Pedicini, Lorenzo Pintauro, Alessio Mrass, Andrea Di Maio

# Importing libraries 
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import time
from time import process_time

from rocketpy import Environment, SolidMotor, Rocket, Flight, CompareFlights
import imageio.v2 as imageio
from numpy.random import normal, choice
from scipy.stats import norm
from IPython.display import display
from pathlib import Path
import json
import os
import pickle

   
analysis_parameters = {
    
    # === Mass Details ===
    
    # Rocket's dry mass without grains' weight (kg) and its uncertainty (standard deviation)
    "rocket_dry_mass": (25.590, 0.3),
    # Rocket's dry inertia moment perpendicular to its axis (kg*m^2)
    "rocket_dry_inertia_11": (14.631, 0.187),
    # Rocket's dry inertia moment relative to its axis (kg*m^2)
    "rocket_dry_inertia_33": (0.075, 0.00122),
    # Motors's dry mass without propellant (kg) and its uncertainty (standard deviation). The weight of the motor structure is included in the rocket dry mass
    "motor_dry_mass": (0.0001, 0.0001),
    # Motor's dry inertia moment perpendicular to its axis (kg*m^2)
    "motor_inertia_11": (0, 0), 
    # Motor's dry inertia moment relative to its axis (kg*m^2)
    "motor_inertia_33": (0.0, 0.0), 
    # Distance between the origin of the referential system and motor's center of dry mass (m)
    "motor_dry_mass_position": (0.0, 0.001),

    # === Propulsion Details ===

    # NOTE: many of these values have been estimated based on the few data made available by the motor producers, such as
    # technical drawings for the exterior of the motor and information about the total mass of the grains.
    # You can check the grain_dimensions.m file to see the algorithm we used to calculate the grain inner radius and length from known data.

    # Motor total impulse (N*s)
    "impulse": (9977, 5),
    # Motor burn out time (s)
    "burn_time": (4.3, 0.1),
    # Motor's nozzle radius (m), obtained by scaling the known geometry of a Pro54 rocket motor nozzle (real nozzle geometry for Pro75 motors is not publicly available)
    "nozzle_radius": (29/ 1000, 0.5 / 1000),
    # Motor's nozzle throat radius (m), obtained by scaling the known geometry of a Pro54 rocket motor nozzle (real nozzle geometry for Pro75 motors is not publicly available)
    "throat_radius": (20 / 1000, 0.5 / 1000),
    # Motor's grain separation (axial distance between two grains) (m)
    "grain_separation": (3 / 1000, 0.01 / 1000),
    # Motor's grain density (kg/m^3)
    "grain_density": (1793.7, 1),
    # Motor's grain outer radius (m)
    "grain_outer_radius": (35.9 / 1000, 0.0001),
    # Motor's grain inner radius (m)
    "grain_initial_inner_radius": (18.10 / 1000, 0.0001),
    # Motor's grain height (m)
    "grain_initial_height": (156.17/ 1000, 0.0001),

    # === Aerodynamic Details ===
    
    # Rocket's radius (m)
    "radius": (75 / 1000, 0.001),
    # Origin of the motor coordinate system
    "nozzle_position": (0, 0.0001),
    # Distance between the origin of the referential system and center of propellant mass (m) 
    "grains_center_of_mass_position": (0.5125, 0.01),
    # Multiplier for rocket's power off drag curve to introduce uncertainty
    "power_off_drag_corr": (1.0, 0.001),
    # Multiplier for rocket's power on drag curve to introduce uncertainty
    "power_on_drag_corr": (1.0, 0.001),
    # Rocket's nose cone length (m)
    "nose_length": (0.43, 0.001),
    # Power of the function that describes the shape of the nose cone
    "nose_pwr" : (0.0, 0.001),
    # Axial distance from the tip of the nose (m)
    "tail_position": (3.005, 0.001),
    # The origin of the coordinate system (m)
    "nose_position": (0, 0),
    # Number of fins
    "fin_number" : (3, 0), 
    # Fin span (m)
    "fin_span": (0.142, 0.0005), 
    # Fin root chord (m)
    "fin_root_chord": (0.28, 0.0005), 
    # Fin tip chord (m)
    "fin_tip_chord": (0.06, 0.0005), 
    # Axial distance between rocket's tip and nearest point in its fin (m)
    "fin_position": (2.71, 0.005), 
    # Fin sweep angle (degrees)
    "fin_sweep_angle": (58.2, 0.005), 
    # Tail length (m)
    "tail_length": (0.075, 0.001), 
    # Tail bottom radius (m)
    "tail_bottom_radius": (0.05, 0.001), 
    # Tail top radius (m)
    "tail_top_radius": (0.075, 0.001), 

    # === Launch and Environment Details ===

    # Launch rail inclination angle relative to the horizontal plane (degrees)
    "inclination": (84, 0.5),
    # Launch rail heading relative to north (degrees)
    "heading": (145, 1),
    # Launch rail length (m)
    "rail_length": (11, 0.005),
    # Members of the ensemble forecast to be used
    "ensemble_member": list(range(10)),

    # === Parachute Details ===

    # Drag coefficient times reference area for the rocket drogue chute (m^2)
    "cd_s_drogue": (0.97 * 0.9144,0.006),         #rocketman 3ft without spillout
    # Drag coefficient times reference area for the rocket main chute (m^2)
    "cd_s_main": (0.97 * 14.3013, 0.277),          #rocketman 16ft without spillout
    # Time delay between parachute ejection signal is detected and parachute is inflated (s)
    "lag_rec": (1.73, 0.1),

    # === Rail buttons Details ===
    
    # Position of the rail button closer to the tip of the rocket (m)
    "upper_button_y": (0.57, 0.005),
    # Position of the rail button further to the tip of the rocket (m)
    "lower_button_y": (2.14, 0.005),
    # Angular position of the buttons (degrees)
    "angular_button": (0, 0.01),

    # === Electronic Systems and Sensors Details ===

    # Time delay between sensor signal is received and ejection signal is fired (s)
    "lag_se": (0.05, 0.015),
    # Mean noise value of the Pressure signal (Pa) 
    "noise_mean": (0 , 0.001),
    # Standard deviation of the Pressure signal (Pa)
    "noise_p_stdev": (6.5 , 0.01),
    # Time correlation of the Pressure signal
    "noise_p_tc": (0.3 , 0.01),
}

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

BASE_DIR = Path(__file__).resolve().parent

# Basic analysis info
filename = BASE_DIR / "Atlas"
print("Filename is:")
print(filename)
number_of_simulations = 3
# Create data files for inputs, outputs and error logging
dispersion_error_file = open(str(filename) + ".disp_errors.txt", "w")
dispersion_input_file = open(str(filename) + ".disp_inputs.json", "w")
dispersion_output_file = open(str(filename) + ".disp_outputs.json", "w")

# Initialize counter and timer
i = 0

initial_wall_time = time.time()
initial_cpu_time = process_time()

# Define basic Environment object
Env = Environment(
    date = (2024, 10, 11, 12),                          #(Year, Month, Day, Hour)
    longitude=-8.288963, latitude=39.3897,
    elevation = 160,
    max_expected_height = 4500
)

# There are 3 possible choices of weather data: [uncomment the choosen one and comment the others]

# 1. A custom atmosphere defined with the mean environment values calculated in the week on EuRoC from 2005 to 2024 between the 10th and the 15th october. 
# In order to define the mean environment features, we used the built-in function "Environment Analysis" from RocketPy. 
# This generates a .json file with the mean environment values based on  a sample of 19 years, from 2005 to 2024, between the 10th and 15th of October, 
# by feeding the NetCDF4 data from Copernicus. 
# The .json file contains a series of .csv profiles based on the altitude that define pressure, temperature and wind vectors on an hourly basis. 
# For more information consult the "mean_environment_values.json" file inside the directory.

# import the .json with the mean environment values oustide the defition of the atmospheric model
with open(BASE_DIR /"""environment_data/mean_environment_values.json""", "r") as f:
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

# 2. Select a date during the EuRoC week: October 10th-15th from 2005 to 2024 (change the date in the environment definition), in this case the weather data will match the date chosen by the user.

# Env.set_atmospheric_model(    
#     type="Ensemble",                                                                                                  
#     file=str(BASE_DIR / """environment_data/SantaMargarida_Ensemble_09to16oct2010to2024.nc"""),                                        
#     # This section creates an updated dictionary to read the NetCDF4 files,                                           
#     # as the built-in ECMWF dictionary inside RocketPy is outdated and can't read NetCDF4 files in the new format     
#     dictionary= {                                                                                                     
#         "ensemble": "number",                                                                                         
#         "time": "valid_time",                                                                                         
#         "latitude": "latitude",                                                                                       
#         "longitude": "longitude",                                                                                     
#         "level": "pressure_level",                                                                                    
#         "temperature": "t",                                                                                           
#         "surface_geopotential_height": None,                                                                          
#         "geopotential_height": None,                                                                                  
#         "geopotential": "z",                                                                                          
#         "u_wind": "u",                                                                                                
#         "v_wind": "v",                                                                                                
#     },
# )

# 3. The Forecast: let the user simulate in the future by using the GFS (Global Forecast System) weather data, (change the date in the environment definition).

# Env.set_atmospheric_model(
#     type="Forecast",
#     file="GFS"
# )

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


# Initiate collection of flight data. This allows to compare different flight from the Montecarlo analysis and visualize data dispersion and overall characteristics of the flight and the simulation itself
flights=[]

# Iterate over flight settings
out = display("Starting", display_id=True)
for setting in flight_settings(analysis_parameters, number_of_simulations):

    last_negative_time = None
    apogee_detected = False
    parachute_stopwatch = 0

    start_time = process_time()
    i += 1
    print(f"\rCurrent iteration: {i}", end="")

    if Env.atmospheric_model_type == "Ensemble":
        # Update environment object
        Env.select_ensemble_member(setting["ensemble_member"])

    # Define COTS motor
    Pro75_9977M2245 = SolidMotor(
        # Thrust data
        thrust_source=str(BASE_DIR /"""Cesaroni_9977_M2245.csv"""),
        burn_time=setting["burn_time"],
        reshape_thrust_curve=(setting["burn_time"], setting["impulse"]),
        interpolation_method="linear",
        # Nozzle data
        nozzle_radius=setting["nozzle_radius"],
        throat_radius=setting["throat_radius"],
        # Grain data
        grain_number=6,
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

    # Create rocket
    Atlas = Rocket(
        radius=setting["radius"],
        mass=setting["rocket_dry_mass"],
        inertia=(
            setting["rocket_dry_inertia_11"],
            setting["rocket_dry_inertia_11"],
            setting["rocket_dry_inertia_33"],
        ),
        power_off_drag=str(BASE_DIR / """square_power_off.CSV"""),
        power_on_drag=str(BASE_DIR / """square_power_on.CSV"""),

        # Define the center of dry mass as the distance from the tip of the nose, and set the positive axis orientation
        center_of_mass_without_motor=1.61919,
        coordinate_system_orientation="nose_to_tail",
    )

    # Define rail buttons
    Atlas.set_rail_buttons(
        upper_button_position= setting["upper_button_y"], 
        lower_button_position= setting["lower_button_y"], 
        angular_position= setting["angular_button"],
    )

    # Add the motor to the rocket assembly
    Atlas.add_motor(Pro75_9977M2245, position=3.08)   # sets the motor's CDM on the rocket's CDM. The "grain center of mass position" parameter will handle the position of the actual motor

    # Add uncertainty to the drag curves, by multiplying them by a small, random corrective factor
    Atlas.power_off_drag *= setting["power_off_drag_corr"]
    Atlas.power_on_drag *= setting["power_on_drag_corr"]

    # Define and add the Nosecone section
    NoseCone = Atlas.add_nose(
        length=setting["nose_length"],
        kind="lvhaack",
        power= "nose_pwr",
        position=setting["nose_position"],
    )

    # Define and add the Fins
    FinSet = Atlas.add_trapezoidal_fins(
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
    Tail = Atlas.add_tail(
        top_radius=setting["tail_top_radius"],
        bottom_radius=setting["tail_bottom_radius"], 
        length=setting["tail_length"], 
        position = setting["tail_position"],
    )

    # Define and add the Drogue parachute
    Drogue = Atlas.add_parachute(
        "Drogue",
        cd_s=setting["cd_s_drogue"],
        trigger=simulator_check_drogue_opening,
        sampling_rate= sampling_rate,
        lag=setting["lag_rec"] + setting["lag_se"],
        noise=(
            setting["noise_mean"],
            setting["noise_p_stdev"],
            setting["noise_p_tc"],
        ),
    )

    # Define and add the Main parachute
    Main = Atlas.add_parachute(
        "Main",
        cd_s=setting["cd_s_main"],
        trigger=simulator_check_main_opening,
        sampling_rate= sampling_rate,
        lag=setting["lag_rec"] + setting["lag_se"],
        noise=(
            setting["noise_mean"],
            setting["noise_p_stdev"],
            setting["noise_p_tc"],
        ),
    )

    # Run trajectory simulation
    try:
        
        rocket_flight = Flight(
            rocket=Atlas,
            environment=Env,
            rail_length=setting["rail_length"],
            inclination=setting["inclination"],
            heading=setting["heading"],
            max_time=600,
        )

        export_flight_data(setting, rocket_flight, process_time() - start_time)

    except Exception as E:
        print(E)
        export_flight_error(setting)

    flights.append(rocket_flight)

# Print comparison graphs to visualize data dispersion during flight
Atlas.draw()
Env.all_info()
comparison = CompareFlights(flights)
comparison.velocities()
comparison.accelerations()
comparison.attitude_angles()
comparison.euler_angles()
comparison.attitude_frequency()
comparison.aerodynamic_forces()
comparison.aerodynamic_moments()
comparison.angular_velocities()
comparison.trajectories_3d()
comparison.rail_buttons_forces()
comparison.stability_margin()

# Done

## Print and save total time
final_string = f"Completed {i} iterations successfully. Total CPU time: {process_time() - initial_cpu_time} s. Total wall time: {time.time() - initial_wall_time} s"
print(final_string)

## Close files
dispersion_input_file.close()
dispersion_output_file.close()
dispersion_error_file.close()

filename = BASE_DIR / "Atlas"

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
# Get file
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

# Print number of flights simulated
N = len(dispersion_general_results)
print("Number of simulations: ", N)

# Initialize the path in which the graphic results of the simulation will be saved, both in .svg and pickle format. The pickle format was 
# chosen so that the user can open the images/graphs files (using the design file show_images.py) in a format that allows them to
# zoom in and out and examine the pictures more accurately

# Create an output folder for .svg files
output_folder_svg = str(BASE_DIR / "images" / "svg")
os.makedirs(output_folder_svg, exist_ok=True)

# Create an output folder for pickle files
output_folder_pickle = str(BASE_DIR / "images" / "pickle")
os.makedirs(output_folder_pickle, exist_ok=True)

# The following section generates the output distribution plots and automatically saves them on your PC, in the same folder this code is located.
# To create each picture, the algorythm performs the following actions:

# - Fits a normal distribution to the dataset and compute the average value and standard deviation;
# - Prints the fitted mean and standard deviation,
# - Creates a histogram of the data and overlays the corresponding normal distribution curve;
# - Adds title, axis labels, and a grid to the plot for better clarity;
# - Saves the plot as a .svg file for high-quality output (e.g., for reports or web use);
# - Saves the entire figure as a pickle file for later reuse or resizing;

# An additional step may be included to prevent automatic sequential display while running the simulation:

# - Closes the figure to prevent automatic sequential display. This would be an obstacle for analysts trying to visualize more plots at once, after they have all been generated

# All distribution plots are generated, saved and made available using this architecture

# OUT OF RAIL TIME
out_data = dispersion_results["out_of_rail_time"]
mu_out, std_out = norm.fit(out_data)

print(f'Out of Rail Time -         Mean Value: {mu_out:0.3f} s')
print(f'Out of Rail Time - Standard Deviation: {std_out:0.3f} s')

# Create the figure
fig, ax = plt.subplots()
ax.hist(out_data, bins=int(len(out_data)**0.5), density=True, alpha=0.6,
        color='lightcoral', edgecolor='black')
x_out = np.linspace(min(out_data), max(out_data), 1000)
pdf_out = norm.pdf(x_out, mu_out, std_out)
ax.plot(x_out, pdf_out, 'k', linewidth=2)
ax.set_title("Out of Rail Time")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Probability Density")
ax.grid(True)

# Save figure as SVG 
fig.savefig(os.path.join(output_folder_svg, "out_of_rail_time.svg"), format='svg')

#Save figure as pickle
pickle_path = os.path.join(output_folder_pickle, "out_of_rail_time.fig.pickle")
with open(pickle_path, "wb") as f:
    pickle.dump(fig, f)

plt.close(fig)    # Stop automatic printing of images


# OUT OF RAIL VELOCITY
vel_data = dispersion_results["out_of_rail_velocity"]
mu_vel, std_vel = norm.fit(vel_data)

print(f'Out of Rail Velocity -         Mean Value: {mu_vel:0.3f} m/s')
print(f'Out of Rail Velocity - Standard Deviation: {std_vel:0.3f} m/s')


# Create the figure
fig_1, ax = plt.subplots()
ax.hist(vel_data, bins=int(N**0.5), density=True, alpha=0.6, color='skyblue', edgecolor='black')
x_vel = np.linspace(min(vel_data), max(vel_data), 1000)
pdf_vel = norm.pdf(x_vel, mu_vel, std_vel)
ax.plot(x_vel, pdf_vel, 'k', linewidth=2)
ax.set_title("Out of Rail Velocity")
ax.set_xlabel("Velocity (m/s)")
ax.set_ylabel("Probability Density")
ax.grid(True)

# Save figure as SVG
fig_1.savefig(os.path.join(output_folder_svg, "out_of_rail_velocity.svg"), format='svg')

# Save figure as pickle
pickle_path = os.path.join(output_folder_pickle, "out_of_rail_velocity.fig.pickle")
with open(pickle_path, "wb") as f:
    pickle.dump(fig_1, f)


plt.close(fig_1)    # Stop automatic printing of images



# === APOGEE TIME ===
apo_data = dispersion_results["apogee_time"]
mu_apo, std_apo = norm.fit(apo_data)

print(f'Apogee Time -         Mean Value: {mu_apo:0.3f} s')
print(f'Apogee Time - Standard Deviation: {std_apo:0.3f} s')


# Create the figure
fig_apo, ax = plt.subplots()
ax.hist(apo_data, bins=int(N**0.5), density=True, alpha=0.6, color='lightgreen', edgecolor='black')
x_apo = np.linspace(min(apo_data), max(apo_data), 1000)
pdf_apo = norm.pdf(x_apo, mu_apo, std_apo)
ax.plot(x_apo, pdf_apo, 'k', linewidth=2)
ax.set_title("Apogee Time")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Probability Density")
ax.grid(True)

# Save figure as SVG and Pickle
fig_apo.savefig(os.path.join(output_folder_svg, "apogee_time.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "apogee_time.fig.pickle"), "wb") as f:
    pickle.dump(fig_apo, f)
plt.close(fig_apo)  # Stop automatic printing of images


# === APOGEE ALTITUDE ===
alt_data = dispersion_results["apogee_altitude"]
mu_alt, std_alt = norm.fit(alt_data)

print(f'Apogee Altitude -         Mean Value: {mu_alt:0.3f} m')
print(f'Apogee Altitude - Standard Deviation: {std_alt:0.3f} m')


# Create the figure
fig_alt, ax = plt.subplots()
ax.hist(alt_data, bins=int(N**0.5), density=True, alpha=0.6, color='skyblue', edgecolor='black')
x_alt = np.linspace(min(alt_data), max(alt_data), 1000)
pdf_alt = norm.pdf(x_alt, mu_alt, std_alt)
ax.plot(x_alt, pdf_alt, 'k', linewidth=2)
ax.set_title("Apogee Altitude")
ax.set_xlabel("Altitude (m)")
ax.set_ylabel("Probability Density")
ax.grid(True)

# # Save figure as SVG and Pickle
fig_alt.savefig(os.path.join(output_folder_svg, "apogee_altitude.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "apogee_altitude.fig.pickle"), "wb") as f:
    pickle.dump(fig_alt, f)
plt.close(fig_alt)   # Stop automatic printing of images


# === APOGEE X POSITION ===
x_data = dispersion_results["apogee_x"]
mu_x, std_x = norm.fit(x_data)

print(f'Apogee X Position -         Mean Value: {mu_x:0.3f} m')
print(f'Apogee X Position - Standard Deviation: {std_x:0.3f} m')


# Create the figure
fig_x, ax = plt.subplots()
ax.hist(x_data, bins=int(N**0.5), density=True, alpha=0.6, color='lightcoral', edgecolor='black')
x_vals = np.linspace(min(x_data), max(x_data), 1000)
pdf_vals = norm.pdf(x_vals, mu_x, std_x)
ax.plot(x_vals, pdf_vals, 'k', linewidth=2)
ax.set_title("Apogee X Position")
ax.set_xlabel("Apogee X Position (m)")
ax.set_ylabel("Probability Density")
ax.grid(True)

# Save figure as SVG and Pickle
fig_x.savefig(os.path.join(output_folder_svg, "apogee_x_position.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "apogee_x_position.fig.pickle"), "wb") as f:
    pickle.dump(fig_x, f)
plt.close(fig_x)  # Stop automatic printing of images


# === APOGEE Y POSITION ===
y_data = dispersion_results["apogee_y"]
mu_y, std_y = norm.fit(y_data)

print(f'Apogee Y Position -         Mean Value: {mu_y:0.3f} m')
print(f'Apogee Y Position - Standard Deviation: {std_y:0.3f} m')

# Create the figure
fig_y, ax = plt.subplots()
ax.hist(y_data, bins=int(N**0.5), density=True, alpha=0.6, color='lightgreen', edgecolor='black')
x_vals = np.linspace(min(y_data), max(y_data), 1000)
pdf_vals = norm.pdf(x_vals, mu_y, std_y)
ax.plot(x_vals, pdf_vals, 'k', linewidth=2)
ax.set_title("Apogee Y Position")
ax.set_xlabel("Apogee Y Position (m)")
ax.set_ylabel("Probability Density")
ax.grid(True)

# Save figure as SVG and Pickle
fig_y.savefig(os.path.join(output_folder_svg, "apogee_y_position.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "apogee_y_position.fig.pickle"), "wb") as f:
    pickle.dump(fig_y, f)
plt.close(fig_y)  # Stop automatic printing of images



# === IMPACT TIME ===
impact_time = dispersion_results["impact_time"]
mu_impact_time, std_impact_time = norm.fit(impact_time)

print(f'Impact Time -         Mean Value: {mu_impact_time:0.3f} s')
print(f'Impact Time - Standard Deviation: {std_impact_time:0.3f} s')

# Create the figure
fig_imp_time, ax = plt.subplots()
ax.hist(impact_time, bins=int(N**0.5), density=True, alpha=0.6, color='skyblue', edgecolor='black')
x_vals = np.linspace(min(impact_time), max(impact_time), 1000)
pdf = norm.pdf(x_vals, mu_impact_time, std_impact_time)
ax.plot(x_vals, pdf, 'k', linewidth=2)
ax.set_title("Impact Time")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Probability Density")
ax.grid(True)


# Save figure as SVG and Pickle
fig_imp_time.savefig(os.path.join(output_folder_svg, "impact_time.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "impact_time.fig.pickle"), "wb") as f:
    pickle.dump(fig_imp_time, f)
plt.close(fig_imp_time)  # Stop automatic printing of images


# === IMPACT X POSITION ===
impact_x = dispersion_results["impact_x"]
mu_x, std_x = norm.fit(impact_x)

print(f'Impact X Position -         Mean Value: {mu_x:0.3f} m')
print(f'Impact X Position - Standard Deviation: {std_x:0.3f} m')

# Create the figure
fig_imp_x, ax = plt.subplots()
ax.hist(impact_x, bins=int(N**0.5), density=True, alpha=0.6, color='lightcoral', edgecolor='black')
x_vals = np.linspace(min(impact_x), max(impact_x), 1000)
pdf = norm.pdf(x_vals, mu_x, std_x)
ax.plot(x_vals, pdf, 'k', linewidth=2)
ax.set_title("Impact X Position")
ax.set_xlabel("Impact X Position (m)")
ax.set_ylabel("Probability Density")
ax.grid(True)


# Save figure as SVG and Pickle
fig_imp_x.savefig(os.path.join(output_folder_svg, "impact_x_position.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "impact_x_position.fig.pickle"), "wb") as f:
    pickle.dump(fig_imp_x, f)
plt.close(fig_imp_x)  # Stop automatic printing of images



# === IMPACT Y POSITION ===
impact_y = dispersion_results["impact_y"]
mu_y, std_y = norm.fit(impact_y)

print(f'Impact Y Position -         Mean Value: {mu_y:0.3f} m')
print(f'Impact Y Position - Standard Deviation: {std_y:0.3f} m')

# Create the figure
fig_imp_y, ax = plt.subplots()
ax.hist(impact_y, bins=int(N**0.5), density=True, alpha=0.6, color='lightgreen', edgecolor='black')
x_vals = np.linspace(min(impact_y), max(impact_y), 1000)
pdf = norm.pdf(x_vals, mu_y, std_y)
ax.plot(x_vals, pdf, 'k', linewidth=2)
ax.set_title("Impact Y Position")
ax.set_xlabel("Impact Y Position (m)")
ax.set_ylabel("Probability Density")
ax.grid(True)


# Save figure as SVG and Pickle
fig_imp_y.savefig(os.path.join(output_folder_svg, "impact_y_position.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "impact_y_position.fig.pickle"), "wb") as f:
    pickle.dump(fig_imp_y, f)
plt.close(fig_imp_y)  # Stop automatic printing of images



# === IMPACT VELOCITY ===
impact_velocity = dispersion_results["impact_velocity"]
mu_v, std_v = norm.fit(impact_velocity)

print(f'Impact Velocity -         Mean Value: {mu_v:0.3f} m/s')
print(f'Impact Velocity - Standard Deviation: {std_v:0.3f} m/s')

# Create the figure
fig_imp_v, ax = plt.subplots()
ax.hist(impact_velocity, bins=int(N**0.5), density=True, alpha=0.6, color='skyblue', edgecolor='black')
x_vals = np.linspace(min(impact_velocity), max(impact_velocity), 1000)
pdf = norm.pdf(x_vals, mu_v, std_v)
ax.plot(x_vals, pdf, 'k', linewidth=2)
ax.set_title("Impact Velocity")
ax.set_xlabel("Velocity (m/s)")
ax.set_ylabel("Probability Density")
ax.grid(True)


# Save figure as SVG and Pickle
fig_imp_v.savefig(os.path.join(output_folder_svg, "impact_velocity.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "impact_velocity.fig.pickle"), "wb") as f:
    pickle.dump(fig_imp_v, f)
plt.close(fig_imp_v)  # Stop automatic printing of images


# === STATIC MARGINS ===
initial_margin = dispersion_results["initial_static_margin"]
out_of_rail_margin = dispersion_results["out_of_rail_static_margin"]
final_margin = dispersion_results["final_static_margin"]

# Fit normal distributions
mu_initial, std_initial = norm.fit(initial_margin)
mu_out, std_out = norm.fit(out_of_rail_margin)
mu_final, std_final = norm.fit(final_margin)

print(f'Initial Static Margin -             Mean Value: {mu_initial:0.3f} c')
print(f'Initial Static Margin -     Standard Deviation: {std_initial:0.3f} c')

print(f'Out of Rail Static Margin -         Mean Value: {mu_out:0.3f} c')
print(f'Out of Rail Static Margin - Standard Deviation: {std_out:0.3f} c')

print(f'Final Static Margin -               Mean Value: {mu_final:0.3f} c')
print(f'Final Static Margin -       Standard Deviation: {std_final:0.3f} c')

# Create the figure
fig_static, ax = plt.subplots()

ax.hist(initial_margin, bins=int(N**0.5), density=True, alpha=0.4,
        label="Initial", color='skyblue', edgecolor='black')
ax.hist(out_of_rail_margin, bins=int(N**0.5), density=True, alpha=0.4,
        label="Out of Rail", color='orange', edgecolor='black')
ax.hist(final_margin, bins=int(N**0.5), density=True, alpha=0.4,
        label="Final", color='lightgreen', edgecolor='black')

x_initial = np.linspace(min(initial_margin), max(initial_margin), 1000)
x_out = np.linspace(min(out_of_rail_margin), max(out_of_rail_margin), 1000)
x_final = np.linspace(min(final_margin), max(final_margin), 1000)

ax.plot(x_initial, norm.pdf(x_initial, mu_initial, std_initial), 'b-', linewidth=2)
ax.plot(x_out, norm.pdf(x_out, mu_out, std_out), 'darkorange', linewidth=2)
ax.plot(x_final, norm.pdf(x_final, mu_final, std_final), 'g-', linewidth=2)

ax.set_title("Static Margin Distribution")
ax.set_xlabel("Static Margin (c)")
ax.set_ylabel("Probability Density")
ax.legend()
ax.grid(True)


# Save figure as SVG and Pickle
fig_static.savefig(os.path.join(output_folder_svg, "static_margin_distribution.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "static_margin_distribution.fig.pickle"), "wb") as f:
    pickle.dump(fig_static, f)

plt.close(fig_static)  # Stop automatic printing of images


# MAXIMUM VELOCITY
max_velocity = dispersion_results["max_velocity"]
mu_max_velocity, std_max_velocity = norm.fit(max_velocity)

print(f'Maximum Velocity -         Mean Value: {mu_max_velocity:0.3f} m/s')
print(f'Maximum Velocity - Standard Deviation: {std_max_velocity:0.3f} m/s')

# Create the figure
fig, ax = plt.subplots()
ax.hist(max_velocity, bins=int(N**0.5), density=True, alpha=0.6, color='lightblue', edgecolor='black')
x_max_velocity = np.linspace(min(max_velocity), max(max_velocity), 1000)
ax.plot(x_max_velocity, norm.pdf(x_max_velocity, mu_max_velocity, std_max_velocity), 'k', linewidth=2)
ax.set_title("Maximum Velocity")
ax.set_xlabel("Velocity (m/s)")
ax.set_ylabel("Probability Density")
ax.grid(True)

# Save figure as SVG and Pickle
fig.savefig(os.path.join(output_folder_svg, "maximum_velocity_plot.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "maximum_velocity_plot.fig.pickle"), "wb") as f:
    pickle.dump(fig, f)
plt.close(fig)  # Stop automatic printing of images

# MAXIMUM ACCELERATION
max_acc = dispersion_results["max_acceleration"]
mu_max_acc, std_max_acc = norm.fit(max_acc)

print(f'Maximum Acceleration -         Mean Value: {mu_max_acc:0.3f} m/s²')
print(f'Maximum Acceleration - Standard Deviation: {std_max_acc:0.3f} m/s²')

# Create the figure
fig, ax = plt.subplots()
ax.hist(max_acc, bins=int(N**0.5), density=True, alpha=0.6, color='lightcoral', edgecolor='black')
x_max_acc = np.linspace(min(max_acc), max(max_acc), 1000)
ax.plot(x_max_acc, norm.pdf(x_max_acc, mu_max_acc, std_max_acc), 'k', linewidth=2)
ax.set_title("Maximum Acceleration")
ax.set_xlabel("Acceleration (m/s²)")
ax.set_ylabel("Probability Density")
ax.grid(True)

# Save figure as SVG and Pickle
fig.savefig(os.path.join(output_folder_svg, "maximum_acceleration_plot.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "maximum_acceleration_plot.fig.pickle"), "wb") as f:
    pickle.dump(fig, f)
plt.close(fig)  # Stop automatic printing of images

# NUMBER OF PARACHUTE EVENTS
# Create the figure
fig, ax = plt.subplots()
ax.hist(dispersion_results["number_of_events"], color='orange', edgecolor='black')
ax.set_title("Parachute Events")
ax.set_xlabel("Number of Parachute Events")
ax.set_ylabel("Number of Occurrences")
ax.grid(True)

# Save figure as SVG and Pickle
fig.savefig(os.path.join(output_folder_svg, "parachute_events_plot.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "parachute_events_plot.fig.pickle"), "wb") as f:
    pickle.dump(fig, f)
plt.close(fig)  # Stop automatic printing of images

# DROGUE PARACHUTE TRIGGER TIME
drogue_trigger = dispersion_results["drogue_triggerTime"]
mu_drogue_trigger, std_drogue_trigger = norm.fit(drogue_trigger)

print(f'Drogue Parachute Trigger Time -         Mean Value: {mu_drogue_trigger:0.3f} s')
print(f'Drogue Parachute Trigger Time - Standard Deviation: {std_drogue_trigger:0.3f} s')

# Create the figure
fig, ax = plt.subplots()
ax.hist(drogue_trigger, bins=int(N**0.5), density=True, alpha=0.6, color='gold', edgecolor='black')
x_drogue_trigger = np.linspace(min(drogue_trigger), max(drogue_trigger), 1000)
ax.plot(x_drogue_trigger, norm.pdf(x_drogue_trigger, mu_drogue_trigger, std_drogue_trigger), 'k', linewidth=2)
ax.set_title("Drogue Parachute Trigger Time")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Probability Density")
ax.grid(True)

# Save figure as SVG and Pickle
fig.savefig(os.path.join(output_folder_svg, "drogue_trigger_time_plot.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "drogue_trigger_time_plot.fig.pickle"), "wb") as f:
    pickle.dump(fig, f)
plt.close(fig)  # Stop automatic printing of images

# DROGUE PARACHUTE FULLY INFLATED TIME
drogue_inflated_time = dispersion_results["drogue_inflated_time"]
mu_drogue_time, std_drogue_time = norm.fit(drogue_inflated_time)

print(f'Drogue Parachute Fully Inflated Time -         Mean Value: {mu_drogue_time:0.3f} s')
print(f'Drogue Parachute Fully Inflated Time - Standard Deviation: {std_drogue_time:0.3f} s')

# Create the figure
fig, ax = plt.subplots()
ax.hist(drogue_inflated_time, bins=int(N**0.5), density=True, alpha=0.6, color='plum', edgecolor='black')
x_drogue_inflated_time = np.linspace(min(drogue_inflated_time), max(drogue_inflated_time), 1000)
ax.plot(x_drogue_inflated_time, norm.pdf(x_drogue_inflated_time, mu_drogue_time, std_drogue_time), 'k', linewidth=2)
ax.set_title("Drogue Fully Inflated Time")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Probability Density")
ax.grid(True)

# Save figure as SVG and Pickle
fig.savefig(os.path.join(output_folder_svg, "drogue_inflated_time_plot.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "drogue_inflated_time_plot.fig.pickle"), "wb") as f:
    pickle.dump(fig, f)
plt.close(fig)  # Stop automatic printing of images

# DROGUE PARACHUTE FULLY INFLATED VELOCITY
drogue_velocity = dispersion_results["drogue_inflated_velocity"]
mu_drogue_vel, std_drogue_vel = norm.fit(drogue_velocity)

print(f'Drogue Parachute Fully Inflated Velocity -         Mean Value: {mu_drogue_vel:0.3f} m/s')
print(f'Drogue Parachute Fully Inflated Velocity - Standard Deviation: {std_drogue_vel:0.3f} m/s')

# Create the figure
fig, ax = plt.subplots()
ax.hist(drogue_velocity, bins=int(N**0.5), density=True, alpha=0.6, color='lightseagreen', edgecolor='black')
x_drogue_velocity = np.linspace(min(drogue_velocity), max(drogue_velocity), 1000)
ax.plot(x_drogue_velocity, norm.pdf(x_drogue_velocity, mu_drogue_vel, std_drogue_vel), 'k', linewidth=2)
ax.set_title("Drogue Inflated Velocity")
ax.set_xlabel("Velocity (m/s)")
ax.set_ylabel("Probability Density")
ax.grid(True)
# Save figure as SVG and Pickle
fig.savefig(os.path.join(output_folder_svg, "drogue_inflated_velocity_plot.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "drogue_inflated_velocity_plot.fig.pickle"), "wb") as f:
    pickle.dump(fig, f)
plt.close(fig)  # Stop automatic printing of images

# MAXIMUM AERODYNAMIC DRAG
drag = dispersion_results["max_aerodynamic_drag"]
mu_drag, std_drag = norm.fit(drag)

print(f'Maximum Aerodynamic Drag -         Mean Value: {mu_drag:0.3f} N')
print(f'Maximum Aerodynamic Drag - Standard Deviation: {std_drag:0.3f} N')

# Create the figure
fig, ax = plt.subplots()
ax.hist(drag, bins=int(N**0.5), density=True, alpha=0.6, color='cornflowerblue', edgecolor='black')
x_drag = np.linspace(min(drag), max(drag), 1000)
ax.plot(x_drag, norm.pdf(x_drag, mu_drag, std_drag), 'k', linewidth=2)
ax.set_title("Maximum Aerodynamic Drag")
ax.set_xlabel("Drag Force (N)")
ax.set_ylabel("Probability Density")
ax.grid(True)
# Save figure as SVG and Pickle
fig.savefig(os.path.join(output_folder_svg, "max_aero_drag_plot.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "max_aero_drag_plot.fig.pickle"), "wb") as f:
    pickle.dump(fig, f)
plt.close(fig)  # Stop automatic printing of images

# MAXIMUM AERODYNAMIC LIFT
lift = dispersion_results["max_aerodynamic_lift"]
mu_lift, std_lift = norm.fit(lift)

print(f'Maximum Aerodynamic Lift -         Mean Value: {mu_lift:0.3f} N')
print(f'Maximum Aerodynamic Lift - Standard Deviation: {std_lift:0.3f} N')

# Create the figure
fig, ax = plt.subplots()
ax.hist(lift, bins=int(N**0.5), density=True, alpha=0.6, color='mediumaquamarine', edgecolor='black')
x_lift = np.linspace(min(lift), max(lift), 1000)
ax.plot(x_lift, norm.pdf(x_lift, mu_lift, std_lift), 'k', linewidth=2)
ax.set_title("Maximum Aerodynamic Lift")
ax.set_xlabel("Lift Force (N)")
ax.set_ylabel("Probability Density")
ax.grid(True)
# Save figure as SVG and Pickle
fig.savefig(os.path.join(output_folder_svg, "max_aero_lift_plot.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "max_aero_lift_plot.fig.pickle"), "wb") as f:
    pickle.dump(fig, f)
plt.close(fig)  # Stop automatic printing of images

# MAXIMUM SPIN MOMENT
spin_moment = dispersion_results["max_aerodynamic_spin_moment"]
mu_spin, std_spin = norm.fit(spin_moment)

print(f'Maximum Aerodynamic Spin Moment -         Mean Value: {mu_spin:0.3f} N*m')
print(f'Maximum Aerodynamic Spin Moment - Standard Deviation: {std_spin:0.3f} N*m')

# Create the figure
fig, ax = plt.subplots()
ax.hist(spin_moment, bins=int(N**0.5), density=True, alpha=0.6, color='lightslategray', edgecolor='black')
x_spin = np.linspace(min(spin_moment), max(spin_moment), 1000)
ax.plot(x_spin, norm.pdf(x_spin, mu_spin, std_spin), 'k', linewidth=2)
ax.set_title("Maximum Aerodynamic Spin Moment")
ax.set_xlabel("Spin Moment (N*m)")
ax.set_ylabel("Probability Density")
ax.grid(True)
# Save figure as SVG and Pickle
fig.savefig(os.path.join(output_folder_svg, "max_spin_moment_plot.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "max_spin_moment_plot.fig.pickle"), "wb") as f:
    pickle.dump(fig, f)
plt.close(fig)  # Stop automatic printing of images

# MAXIMUM BENDING MOMENT
bending_moment = dispersion_results["max_aerodynamic_bending_moment"]
mu_bend, std_bend = norm.fit(bending_moment)

print(f'Maximum Aerodynamic Bending Moment -         Mean Value: {mu_bend:0.3f} N*m')
print(f'Maximum Aerodynamic Bending Moment - Standard Deviation: {std_bend:0.3f} N*m')

# Create the figure
fig, ax = plt.subplots()
ax.hist(bending_moment, bins=int(N**0.5), density=True, alpha=0.6, color='steelblue', edgecolor='black')
x_bend = np.linspace(min(bending_moment), max(bending_moment), 1000)
ax.plot(x_bend, norm.pdf(x_bend, mu_bend, std_bend), 'k', linewidth=2)
ax.set_title("Maximum Aerodynamic Bending Moment")
ax.set_xlabel("Bending Moment (N*m)")
ax.set_ylabel("Probability Density")
ax.grid(True)
# Save figure as SVG and Pickle
fig.savefig(os.path.join(output_folder_svg, "max_bending_moment_plot.svg"), format='svg')
with open(os.path.join(output_folder_pickle, "max_bending_moment_plot.fig.pickle"), "wb") as f:
    pickle.dump(fig, f)
plt.close(fig)  # Stop automatic printing of images



# Import libraries
import imageio.v2 as imageio
from imageio import imread
from matplotlib.patches import Ellipse

# Import background map
img = imread(str(BASE_DIR / """environment_data/santa_margarida_military_shooting_range_launch_site.png"""))

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
plt.figure(num=None, dpi = 150, facecolor="w", edgecolor="k")
ax = plt.subplot(111)

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

# Draw launch point
plt.scatter(0, 0, s=30, marker="*", color="black", label="Launch Point")
# Draw apogee points
plt.scatter(
    apogee_x, apogee_y, s=5, marker="^", color="orange", label="Simulated Apogee"
)
# Draw impact points
plt.scatter(
    impact_x, impact_y, s=5, marker="v", color="yellow", label="Simulated Landing Point"
)

plt.legend()

# Add title and labels to plot
ax.set_title(
    r"1$\sigma$, 2$\sigma$ and 3$\sigma$ Dispersion Ellipses: Apogee and Landing Points"
)
ax.set_ylabel("North (m)")
ax.set_xlabel("East (m)")
# Add background image to plot
# You can translate the basemap by changing dx and dy (in meters)
dx = 0
dy = 0
plt.imshow(img, zorder=0, extent=[-2000-dx, 2000-dx, -2000-dy, 2000-dy])
plt.axhline(0, color="black", linewidth=0.5)
plt.axvline(0, color="black", linewidth=0.5)
plt.xlim(-2000, 2000)
plt.ylim(-1500, 1500)

# Save plot and show result
plt.savefig(str(filename) + ".pdf", bbox_inches="tight", pad_inches=0)
plt.savefig(str(filename) + ".svg", bbox_inches="tight", pad_inches=0)
plt.show()


Atlas.draw()
Atlas.info()
Pro75_9977M2245.draw()
Pro75_9977M2245.info()

# Sensitivity Analysis
from rocketpy.tools import load_monte_carlo_data

target_variables = ["apogee_altitude","max_acceleration"]
parameters = list(analysis_parameters.keys())

parameters_matrix, target_variables_matrix = load_monte_carlo_data(
    input_filename=str(filename)+".disp_inputs.json",
    output_filename=str(filename)+".disp_outputs.json",
    parameters_list=parameters,
    target_variables_list=target_variables,
)

from rocketpy.sensitivity import SensitivityModel


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


model.plots.bar_plot()