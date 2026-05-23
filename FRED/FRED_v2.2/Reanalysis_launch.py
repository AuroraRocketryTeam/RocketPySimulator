from pathlib import Path
from rocketpy import Environment, Flight, Rocket, SolidMotor 
import json
import numpy as np
import pandas as pd
from typing import Literal
import math

import matplotlib
import matplotlib.pyplot as plt

# set path
BASE_DIR = Path(__file__).resolve().parent

#-------------------------------------------------------------------------------------------------------- PARAMETERS
# The following parameters are centralized here for convenience. 
# Core internal variables remain defined within their respective modules.

# --- NUOVE LIBRERIE PER I SENSORI E UTF-8 ---
from rocketpy import Accelerometer, Barometer
import sys
sys.stdout.reconfigure(encoding='utf-8')
# --------------------------------------------

show_graph = False
ballistic = False

ballast = 0 / 1000  #1600 / 1000            # kg MODIFICARE

latitude = 44.290583 # MODIFICARE SE SERVE, SONO LE COORDINATE
longitude = 12.027111
elevation = 18
date_of_launch = (2025, 5, 24, 16)          #(Year, Month, Day, Hour UTC) MODIFICARE A DATA GIUSTA
weather_data: Literal['c','e','f','i','m'] = 'f'        #(Custom, Ensemble, Forecast, Isa, Manual) #MODIFICARE, m per analisi a vento avverso, f normalmente

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
    wind_heading = 315                                  # degrees from North

    # CAREFUL:  Heading of the wind means where it is goind
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


#---------------------------------------------------------------------------------------------------------
## DEFINE THE ROCKET PARTS

#   SRAD motor info BRICO 45 7mm
impulse = 243.96
t_burnout = 2.37
grain_external_radius = 0.033 / 2
grain_internal_radius = 0.013 / 2 
grain_length = 0.147
grain_volume = 3.14*((grain_external_radius*2)-(grain_internal_radius*2))*grain_length
grain_mass = 0.19694061309132402
grain_dens = grain_mass / grain_volume
srad_motor_dry_mass = 0.7871568876139587
thrust_curve = str(BASE_DIR/"simulation_inputs/propulsion_data/reshape_test_2026-05-21_20-44-20.csv")
CG_position_from_nose = 397 / 1000                          # (m)

solid_motor = SolidMotor(
    burn_time=t_burnout,
    thrust_source = thrust_curve,
    reshape_thrust_curve=(t_burnout, impulse), 
    grain_number=1,
    #   DRY PARAMETERS
    dry_mass= srad_motor_dry_mass,
    dry_inertia= (0.66, 0.66, 0.00001),
    center_of_dry_mass_position= 99.41 / 1000,
    #   GRAIN PARAMETERS
    grain_density= grain_dens,
    grain_outer_radius= grain_external_radius,
    grain_initial_inner_radius= grain_internal_radius,
    grain_initial_height= grain_length,
    grain_separation= 3 / 1000,
    #   NOZZLE PARAMETERS
    nozzle_radius= 13.71 / 1000,
    nozzle_position=0,
    throat_radius= 9.50/ 1000,
    #   POSITIONING PARAMETERS
    grains_center_of_mass_position= 125 / 1000,
    coordinate_system_orientation="nozzle_to_combustion_chamber",
)

power_off_drag = str(BASE_DIR / "simulation_inputs/aerodynamic_data/FRED_v1.8_CD_power_off.csv")
power_on_drag = str(BASE_DIR / "simulation_inputs/aerodynamic_data/FRED_v1.8_CD_power_on.csv")

FRED = Rocket(
    radius= 42.5 / 1000,
    mass= 2374 / 1000 + ballast,
    inertia=(1.49, 1.49, 0.01),
    power_off_drag=power_off_drag, # use the prevoius defined drag curve^
    power_on_drag=power_on_drag, # use the prevoius defined drag curve 
    center_of_mass_without_motor= 397 / 1000,
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
    position=0.686,
    cant_angle=0,
    sweep_angle=30.3,
)

tail = FRED.add_tail(
    top_radius= 42.5 / 1000,
    bottom_radius= 30 / 1000,
    length= 43 / 1000,
    position= 810 / 1000,
)
if not ballistic:
    Main = FRED.add_parachute(
        "Main",
        cd_s= 0.97 * 1.168,
        trigger=simulator_check_drogue_opening,
        sampling_rate=105,
        lag=2,
        noise=(0, 6.5, 0.3),
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

# Simulate the flight
rocket_flight = Flight(
    rocket=FRED,
    environment=Env,
    rail_length=1.5,  # Da MODIFICARE SE NECESSARIO
    inclination=80, # Da MODIFICARE 2
    heading=180, # Da MODIFICARE 1
)

colored = lambda text: '\033[32m'+str(text)+'\033[0m'   # 32 green

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

#save trajectory, .kml can be open in google earth
if ballistic:
    rocket_flight.export_kml(
        file_name=str(BASE_DIR/"reanalysis_output/ballistic/trajectory.kml"),
        extrude=True,
        altitude_mode="relative_to_ground",
    )
else:
    rocket_flight.export_kml(
        file_name=str(BASE_DIR/"reanalysis_output/nominal/trajectory.kml"),
        extrude=True,
        altitude_mode="relative_to_ground",
    )
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
save_barometer_plot(barom_noisy, barom_clean, rocket_flight, outdir=outdir_sensors, show=show_graph)

print(f"- Sensor graphs and CSV data saved successfully in {colored('FRED_sensors_output')}")