# import python library
from rocketpy import Environment, Flight, Rocket, SolidMotor
from pathlib import Path
import json
# set path
BASE_DIR = Path(__file__).resolve().parent





#-------------------------------------------------------------------------------------------------------- PARAMETERS
# The following parameters are centralized here for convenience. 
# Core internal variables remain defined within their respective modules.

# WEATHER
date_of_launch = (2024, 10, 13, 16)          #(Year, Month, Day, Hour UTC)
latitude = 39.389700
longitude = -8.288964
elevation = 160                              
weather_data: ['c','e','f','i'] = 'c'        #(Custom, Ensemble, Forecast, Isa)

# RAIL
rail_length = 12.0
rail_inclination = 84.0
rail_heading = 144.0                         

# ROCKET (after engine burn)
rocket_mass = 27.740
rocket_inertia = (14.631,14.631,0.075)
rocket_center_of_mass = 1.61919
#--------------------------------------------------------------------------------------------------------





print("Initializing rocket subsystems:")
#-------------------------------------------------------------------------------------------------------- ENVIRONMENT
Env = Environment(
    date = date_of_launch,
    longitude = longitude,
    latitude = latitude,
    elevation = elevation,
    max_expected_height = 4500
)

# There are 3 possible choices of weather data:

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
    with open(BASE_DIR/"environment_data/mean_environment_values.json", "r") as f:
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
        file=str(BASE_DIR/"environment_data/SantaMargarida_Ensemble_09to16oct2010to2024.nc"),                                        
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
print("- Environment module initialized successfully.")





#-------------------------------------------------------------------------------------------------------- ROCKET
Atlas = Rocket(
    radius = 75 / 1000,
    mass = rocket_mass,
    inertia = rocket_inertia,
    power_off_drag=str(BASE_DIR/"Hexagonal_blunt_base_power_off.csv"),
    power_on_drag=str(BASE_DIR/"Hexagonal_blunt_base_power_on.csv"),
    center_of_mass_without_motor=rocket_center_of_mass,
    coordinate_system_orientation="nose_to_tail",
)
#--------------------------------------------------------------------------------------------------------
print("- Rocket module initialized successfully.")





#-------------------------------------------------------------------------------------------------------- MOTOR
Pro75_9977M2245 = SolidMotor(
    thrust_source=str(BASE_DIR/"Cesaroni_9977_M2245.csv"),
    dry_mass=0,
    dry_inertia=(0, 0, 0),
    nozzle_radius=29 / 1000,
    grain_number=6,
    grain_density=1758.7,
    grain_outer_radius= 35.9/ 1000,
    grain_initial_inner_radius=18.1/ 1000,
    grain_initial_height=156.17 / 1000,
    grain_separation=3 / 1000,
    grains_center_of_mass_position=0.5125,
    center_of_dry_mass_position=0,
    nozzle_position=0,
    burn_time=(0.136, 4.3),
    throat_radius=20/ 1000,
    coordinate_system_orientation="nozzle_to_combustion_chamber",
)

Atlas.add_motor(Pro75_9977M2245, position=3.08)
#--------------------------------------------------------------------------------------------------------
print("- Motor module initialized successfully.")





#-------------------------------------------------------------------------------------------------------- RAIL BUTTONS
Rail_Buttons = Atlas.set_rail_buttons(
    upper_button_position=0.57,
    lower_button_position=2.14,
    angular_position=0,
)
#--------------------------------------------------------------------------------------------------------
print("- Rail buttons module initialized successfully.")





#-------------------------------------------------------------------------------------------------------- SURFACES
nose_cone = Atlas.add_nose(
    length=0.43, 
    kind="vonKarman", 
    position=0
)

fin_set = Atlas.add_trapezoidal_fins(
    n=3,
    root_chord=0.28,
    tip_chord=0.06,
    span=0.142,
    position=2.71,
    cant_angle=0,
    sweep_angle=58.2,
)

tail = Atlas.add_tail(
    top_radius=0.075,
    bottom_radius=0.05,
    length=0.075,
    position=3.005,
)
#--------------------------------------------------------------------------------------------------------
print("- Aerodynamic surface modules initialized successfully.")





#-------------------------------------------------------------------------------------------------------- PARACHUTE
# Definition of global variables, to be used inside and outside parachute functions
global last_negative_time, apogee_detected, sampling_rate, parachute_timer
# This variable marks the first instant in which a negative velocity is detected
last_negative_time = None
# This variable indicates whether the algorythm has acknowledged the rocket has reached apogee.
# A "False" value may mean that negative velocity has not yet been detected, or that
# it has been detected but has not yet been consistent for enough seconds (the threshold)
apogee_detected = False
# This variable indicates the sampling rate of the recovery activation algorythm
sampling_rate = 105
# This variable keeps track of the flight time from ignition to the first recovery event 
parachute_stopwatch = 0

# The following function is a Python representation of the C code that will be used on the rocket to 
# detect the apogee condition. In the actual code, detection of negative velocity is achieved thanks
#  to the readings from the IMU sensor
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

            # if it isn't and enough time has passed with a continuous descent,
            # acknowledge apogee and exit the function
            return True, last_negative_time
        
        else:

            # if it isn't and not enough time has passed with a continuous descent,
            # return False and exit the function
            return False, last_negative_time
        
    # if a descent is no longer being (or has never been) detected,
    # return False and exit the function
    else:
        return False, None
    
# The following function is a Python representation of the C code that will be used on the rocket to 
# detect the main parachute opening condition. In the code, the height is determined by filtering  
# barometer readings with a Kalman filter
def main_parachute_opening(apogee_detected:bool, altitude:float) -> bool:
    return apogee_detected and altitude <= 450.0 # meters 

# Set up parachute trigger for the drogue chute
def simulator_check_drogue_opening(p, h, y):
    global last_negative_time, apogee_detected, parachute_stopwatch, sampling_rate
    altitude = h
    vertical_velocity = y[5]

    # Update counter for flight time to apogee: each time this function is called,
    # the timer advances of 1 over the frequency at which the function is called. 
    # This is a workaround to get a measure of in-flight time
    # into the apogee detection algorythm and successfully implement its 
    # "consistent descent signal" principle.
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


Main = Atlas.add_parachute(
    "Main",
    cd_s=0.97*10.5070863,
    trigger=simulator_check_main_opening,
    sampling_rate=105,
    lag=1.73,
    noise=(0, 6.5, 0.3),
)

Drogue = Atlas.add_parachute(
    "Drogue",
    cd_s=0.97*0.6566929,
    trigger=simulator_check_drogue_opening,
    sampling_rate=105,
    lag=1.73,
    noise=(0, 6.5, 0.3),
)
#--------------------------------------------------------------------------------------------------------
print("- Parachute module initialized successfully.")





#-------------------------------------------------------------------------------------------------------- AIR BRAKES
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

    return (
        time,
        air_brakes.deployment_level,
        air_brakes.drag_coefficient(air_brakes.deployment_level, mach_number),
    )

air_brakes = Atlas.add_air_brakes(
    drag_coefficient_curve = str(BASE_DIR/"air_brakes_cd.csv"),
    controller_function = controller_function,
    sampling_rate = 10,
    reference_area = 0.0150,
    clamp = False,
    initial_observed_variables = [0, 0, 0],
    override_rocket_drag = False,
    name = "Air Brakes",
)
#--------------------------------------------------------------------------------------------------------
print("- Air brakes module initialized successfully.")





print("\nRunning the simulation...")
#-------------------------------------------------------------------------------------------------------- FLIGHT
rocket_flight = Flight(
    rocket = Atlas, 
    environment = Env, 
    rail_length = rail_length, 
    inclination = rail_inclination, 
    heading = rail_heading,
    time_overshoot = False,
    verbose = True,
)
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- OUTPUT
#Env.info()

#Pro75_9977M2245.all_info()
#Pro75_9977M2245.draw()

#Atlas.all_info()
#Atlas.draw()

#rocket_flight.all_info()
#print(rocket_flight.parachute_events)
#rocket_flight.speed()
#rocket_flight.acceleration()
#rocket_flight.plots.trajectory_3d()
print(f'Apogee: {round(rocket_flight.apogee,4)} m')
#rocket_flight.aerodynamic_drag()
#print(rocket_flight.out_of_rail_stability_margin)

'''
rocket_flight.export_kml(
    file_name="Atlas_trajectory.kml",
    extrude=True,
    altitude_mode="relative_to_ground",
)
'''
#--------------------------------------------------------------------------------------------------------