# Plotting and visualization
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from cycler import cycler #serve solo x ciclare colori nel grafico 
# RocketPy core classes for environment setup, motor/rocket definition, and flight simulation
from rocketpy import Environment, SolidMotor, Rocket, Flight, CompareFlights
# Time measurement utilities (CPU time and wall time)
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

# set path
BASE_DIR = Path(__file__).resolve().parent





#-------------------------------------------------------------------------------------------------------- PARAMETERS
# The following parameters are centralized here for convenience. 
# Core internal variables remain defined within their respective modules.

# Name of the output folder (can be a new folder or an existing one to overwrite)
output_dir_name = 'output prova'
number_of_simulations = 50

latitude = 39.389700
longitude = -8.288964
elevation = 160.0
date_of_launch = (2024, 10, 11, 12)          #(Year, Month, Day, Hour UTC)
weather_data: ['c','e','f','i'] = 'c'        #(Custom, Ensemble, Forecast, Isa)

use_airbrake = False
   
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
#--------------------------------------------------------------------------------------------------------










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


# The following function is a Python representation of the C code that will be used on the rocket to detect the apogee condition. 
# In the actual code, detection of negative velocity is achieved thanks to the readings from the IMU sensor
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
    

# The following function is a Python representation of the C code that will be used on the rocket to detect the main parachute opening condition.
# In the code, the height is determined by filtering barometer readings with a Kalman filter
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

#Airbrake
def controller_function(time, sampling_rate, state, state_history, observed_variables, air_brakes):
    # state = [x, y, z, vx, vy, vz, e0, e1, e2, e3, wx, wy, wz]
    altitude_ASL = state[2]
    altitude_AGL = altitude_ASL - Env.elevation
    vx, vy, vz = state[3], state[4], state[5]

    # Get winds in x and y directions
    wind_x, wind_y = Env.wind_velocity_x(altitude_ASL), Env.wind_velocity_y(altitude_ASL)

    # Calculate Mach number
    free_stream_speed = (
        (wind_x - vx) ** 2 + (wind_y - vy) ** 2 + (vz) ** 2
        ) ** 0.5
    mach_number = free_stream_speed / Env.speed_of_sound(altitude_ASL)

    # Get previous state from state_history
    previous_state = state_history[-1]
    previous_vz = previous_state[5]

    # If we wanted to we could get the returned values from observed_variables:
    # returned_time, deployment_level, drag_coefficient = observed_variables[-1]

    # Check if the rocket has reached burnout
    if time < Pro75_9977M2245.burn_out_time:
        return None

    # If below 1500 meters above ground level, air_brakes are not deployed
    if altitude_ASL < 1500:  # or vz<0:
        air_brakes.deployment_level = 0

    # Else calculate the deployment level
    else:
        air_brakes.deployment_level = 0.7

    # Return variables of interest to be saved in the observed_variables list
    
    # print(f'{round(time,1)}\t{air_brakes.deployment_level}\t{air_brakes.reference_area}\t
    # {air_brakes.drag_coefficient(air_brakes.deployment_level, mach_number)}\t
    # {round(free_stream_speed,0)}\t{altitude_ASL}\t{vz}\t{mach_number}')
    #print(f'{round(time,1)}\t{vz}')

    return (
        time,
        air_brakes.deployment_level,
        air_brakes.drag_coefficient(air_brakes.deployment_level, mach_number),
    )











#-------------------------------------------------------------------------------------------------------- PATH, FOLDER & FILE

# Paths
output_path = Path(str(BASE_DIR/"montecarlo_output"/output_dir_name))
filename = str(output_path/"Atlas")
output_folder_pickle = Path(output_path/"pickle")
output_folder_svg = Path(output_path/"svg")

print("Montecarlo Rocket flight simulator\n")
print(f"- Filename is: \033[32m{filename}\033[0m")
print(f"- Number of simulations: \033[32m{number_of_simulations}\033[0m")
print(f"- Output directory: \033[32m{output_dir_name}\033[0m")


# Create folders for results if they don't exist
if output_path.is_dir():
    overwrite_folder = input(f'\n<!> The "{output_dir_name}" folder already exists. Do you want to overwrite it? [\033[32my/n\033[0m] - ')
    if not overwrite_folder.lower() in ['y','yes']:
        print("You chose not to overwrite the folder. Stopping the program.")
        raise SystemExit(0)

print("\nStarting...", end='\r')

output_folder_svg.mkdir(parents=True, exist_ok=True)
output_folder_pickle.mkdir(parents=True, exist_ok=True)

# Create data files for inputs, outputs and error logging
dispersion_error_file = open(str(filename) + ".disp_errors.txt", "w")
dispersion_input_file = open(str(filename) + ".disp_inputs.json", "w")
dispersion_output_file = open(str(filename) + ".disp_outputs.json", "w")
#--------------------------------------------------------------------------------------------------------








#?????????????????????????????????????????????????????????????????????????????????????????????????
# Initialize counter and timer
i = 0

initial_wall_time = time.time()
initial_cpu_time = process_time()
#?????????????????????????????????????????????????????????????????????????????????????????????????









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
        file=str(BASE_DIR/"simulation_inputs/environment_data/SantaMargarida_Ensemble_09to16oct2010to2024.nc"),                                        
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






# Initiate collection of flight data. This allows to compare different flight from the Montecarlo analysis 
# and visualize data dispersion and overall characteristics of the flight and the simulation itself
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
    Pro75_9977M2245 = SolidMotor(
        # Thrust data
        thrust_source=str(BASE_DIR/"simulation_inputs/propulsion_data/Cesaroni_9977_M2245.csv"),
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
        power_off_drag=str(BASE_DIR/"simulation_inputs/aerodynamic_data/Hexagonal_blunt_base_power_off.csv"),
        power_on_drag=str(BASE_DIR/"simulation_inputs/aerodynamic_data/Hexagonal_blunt_base_power_on.csv"),

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
    
    if use_airbrake:
        air_brakes = Atlas.add_air_brakes(
            drag_coefficient_curve = str(BASE_DIR/"simulation_inputs/aerodynamic_data/air_brakes_cd.csv"),
            controller_function = controller_function,
            sampling_rate = 10,
            reference_area = 0.0125,
            clamp = False,
            initial_observed_variables = [0, 0, 0],
            override_rocket_drag = False,
            name = "Air Brakes",
        )

    # Run trajectory simulation
    try:
        
        rocket_flight = Flight(
            rocket=Atlas,
            environment=Env,
            rail_length=setting["rail_length"],
            inclination=setting["inclination"],
            heading=setting["heading"],
            time_overshoot = not use_airbrake,
            max_time=1200,
        )

        export_flight_data(setting, rocket_flight, process_time() - start_time)

    except Exception as E:
        print(E)
        export_flight_error(setting)

    flights.append(rocket_flight)


    #...................... Register time and display loading bar
    bar_lenght = 24
    time_for_iteration = (process_time() - initial_cpu_time) / i
    seconds_remaining = round(time_for_iteration*(number_of_simulations-i))
    
    print(f"Current iteration: \033[32m{i:0{len(str(number_of_simulations))}d}\033[0m",end=' ')
    print(f"Average time per iteration: \033[32m{time_for_iteration:2.2f}s\033[0m",end=' ')
    print(f"Time remaining: \033[32m{seconds_remaining//3600:02d}:{(seconds_remaining%3600)//60:02d}:{seconds_remaining%60:02d}\033[0m",end=" ")
    print(f"|\033[32m{'\u2588'*(bar_lenght*i//number_of_simulations):\u2591<{bar_lenght}}\033[0m|{f"[\033[32m{100*i/number_of_simulations:.1f}%\033[0m]":<7}",end="\r")
    #......................



print()


'''

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


'''





#?????????????????????????????????????????????????????????????????????????????????????????????????
## Print and save total time
final_string = f"Completed {i} iterations successfully. Total CPU time: {process_time() - initial_cpu_time} s. Total wall time: {time.time() - initial_wall_time} s"
print(final_string)
#?????????????????????????????????????????????????????????????????????????????????????????????????







## Close files
dispersion_input_file.close()
dispersion_output_file.close()
dispersion_error_file.close()

################################################################################################################## fine parte 1



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
    #"max_load_factor": [],
    #"max_parachute_chord_traction_force": [],
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
#------------------------------------------------------------------------------------------------- riscarica dati?




# Print number of flights simulated
N = len(dispersion_general_results)
print("Number of simulations: ", N)

# Initialize the path in which the graphic results of the simulation will be saved, both in .svg and pickle format. The pickle format was 
# chosen so that the user can open the images/graphs files (using the design file show_images.py) in a format that allows them to
# zoom in and out and examine the pictures more accurately



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
























#--------------------------------------------------------------------------------------------------------update how plots are made
plt.rcParams.update({"axes.titlesize": 12})
plt.rcParams.update({'xtick.labelsize': 8, 'ytick.labelsize': 8})
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['legend.fontsize'] = 8
plt.rcParams['axes.prop_cycle'] = cycler(color=['red', 'limegreen', 'mediumblue'])#'darkorange', 'gold'
plt.rcParams['axes.titlepad'] = 15
plt.rcParams['xtick.minor.visible'] = True
plt.rcParams['ytick.minor.visible'] = True
#--------------------------------------------------------------------------------------------------------


#-------------------------------------------------------------------------------------------------------- plot and save all dispersion
def plot_simple(dispersion_result, x_label, title, dispersion_result_label):
    if not any(x in x_label for x in ['(',')']):
        unit_measure = ''
    else:
        x_label_list = x_label.replace('(','|',-1).replace(')','|',-1).split('|')
        unit_measure = x_label_list[-2]
        if '*' in unit_measure:
            x_label_list[-2] = x_label_list[-2].replace('*','$\\cdot$')
        while '^' in x_label_list[-2]:
            start = x_label_list[-2].find('^')
            end = start+1
            e = True
            while e:
                if end+1<len(x_label_list[-2]):
                    if x_label_list[-2][end+1].isdigit() or x_label_list[-2][end+1] in ['.','-']:
                        end+=1
                    else:
                        e = False
                else:
                    e = False
            x_label_list[-2] = x_label_list[-2][:start]+'$|{'+x_label_list[-2][start+1:end+1]+'}$'+x_label_list[-2][end+1:]
        x_label = x_label_list[0]+'('+x_label_list[-2]+')'
        x_label = x_label.replace('|','^')






    out_data = dispersion_results[dispersion_result]
    mu_out, std_out = norm.fit(out_data)

    print(f'{title}\n\t- Mean Value: {mu_out:0.3f} {unit_measure}')
    print(f'\t- Standard Deviation: {std_out:0.3f} {unit_measure}')

    # Create the figure
    # fig, ax = plt.subplots()
    bars = plt.hist(out_data, bins=int(N**0.5), label=dispersion_result_label, edgecolor="white", alpha=0.5, density=True)

    x_values = np.array([float(list(bars)[1][k]+(list(bars)[1][k+1]-list(bars)[1][k])/2) for k in range(len(list(bars)[1])-1)])
    x_out = np.linspace(min(x_values), max(x_values), 1000)
    pdf_out = norm.pdf(x_out, mu_out, std_out)
    
    plt.plot(x_out, pdf_out, '--k', linewidth=1.5)#, color=bars[-1].patches[-1].get_facecolor())

    plt.fill_between(x_out, pdf_out, color=bars[-1].patches[-1].get_facecolor(), alpha=0.2) #hatch='//'




    offset = 10
    plt.annotate(f'μ = {mu_out:0.3f}\nσ = {std_out:0.3f}', xy=(mu_out,max(pdf_out)), xycoords='data',
        xytext=(offset, -7*offset), textcoords='offset points', bbox={"facecolor":"white", "alpha":0.9, "pad":2},
        arrowprops=dict(arrowstyle='-|>',fc='0.8',
                        connectionstyle="angle,angleA=0,angleB=90,rad=10"))




    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel("Probability Density")

def plot_dispersion(dispersion_result, x_label ,title, dispersion_result_label=None):
    s = plt.figure()
    if isinstance(dispersion_result,list):
        for pd in range(len(dispersion_result)):
            plot_simple(dispersion_result[pd], x_label, title, dispersion_result_label[pd])
            plt.legend()
    else:
        plot_simple(dispersion_result, x_label, title, dispersion_result_label)
    
    plt.ylim(0)
    plt.grid(0)
    
    # Save figure as SVG 
    plt.savefig(str(output_folder_svg/title)+".svg", format='svg', bbox_inches="tight", pad_inches=0.2)

    #Save figure as pickle
    pickle_path = str(output_folder_pickle/title)+".pickle"
    with open(pickle_path, "wb") as f:
        pickle.dump(s, f)

    plt.close(s)    # Stop automatic printing of images


all_plots = {
    "Out of Rail Time" : ["out_of_rail_time", "Time (s)"], # title: [dispersion_result, x_label, dispersion_result_label]
    "Out of Rail Velocity": ["out_of_rail_velocity", "Velocity (m/s)"],
    "Apogee Time":["apogee_time", "Time (s)"],
    "Apogee Altitude":["apogee_altitude","Altitude (m)"],
    "Apogee X Position":["apogee_x","Apogee X Position (m)"],
    "Apogee Y Position":["apogee_y","Apogee Y Position (m)"],
    "Impact Time":["impact_time","Time (s)"],
    "Impact X Position":["impact_x","Impact X Position (m)"],
    "Impact Y Position":["impact_y","Impact Y Position (m)"],
    "Impact Velocity":["impact_velocity","Velocity (m/s)"],
    #"Static Margin":[["initial_static_margin","out_of_rail_static_margin","final_static_margin"],"Static Margin (c)",["Initial","Out of Rail","Final"]],
    "Maximum Velocity":["max_velocity","Velocity (m/s)"],
    "Maximum Acceleration":["max_acceleration","Acceleration (m/s^2)"],
    #"Maximum Load Factor":["max_load_factor","Load Factor (G)"],
    "Maximum Aerodynamic Drag":["max_aerodynamic_drag","Drag Force (N)"],
    "Maximum Aerodynamic Lift":["max_aerodynamic_lift","Lift Force (N)"],
    "Maximum Aerodynamic Spin Moment":["max_aerodynamic_spin_moment","Spin Moment (N*m)"],
    "Maximum Aerodynamic Bending Moment":["max_aerodynamic_bending_moment","Bending Moment (N*m)"],
    "Parachute Events":["number_of_events","Number of Parachute Events"],
    "Drogue Parachute Trigger Time":["drogue_triggerTime","Time (s)"],
    "Drogue Parachute Fully Inflated Time":["drogue_inflated_time","Time (s)"],
    "Drogue Parachute Fully Inflated Velocity":["drogue_inflated_velocity","Velocity (m/s)"],
}


for pp in all_plots:
    plot_dispersion(
        dispersion_result=all_plots[pp][0],
        x_label=all_plots[pp][1],
        title=pp,
        dispersion_result_label = all_plots[pp][2] if len(all_plots[pp])>1 else None
        )























'''

#------------------------------------------------------------------------------------------------------------------------- img launch site
# Import background map
img = imread(str(BASE_DIR / "simulation_inputs/environment_data/santa_margarida_military_shooting_range_launch_site.png"))

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
    r"1$\\sigma$, 2$\\sigma$ and 3$\\sigma$ Dispersion Ellipses: Apogee and Landing Points"
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
#-------------------------------------------------------------------------------------------------------

Atlas.draw()
Atlas.info()
Pro75_9977M2245.draw()
Pro75_9977M2245.info()

#-------------------------------------------------------------------------------------------------------- Sensitivity Analysis

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
'''