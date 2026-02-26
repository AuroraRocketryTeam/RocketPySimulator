# Importing libraries

import os
import datetime
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from time import process_time, time

from rocketpy import Environment, SolidMotor, Rocket, Flight
from rocketpy import CompareFlights

import numpy as np
from numpy.random import normal, choice
from IPython.display import display

from pathlib import Path

# import matlab.engine


ECMWF = {
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
    }

analysis_parameters = {
   # Mass Details
   # Rocket's dry mass without motor (kg) and its uncertainty (standard deviation)
   "rocket_mass": (7.938, 0.150),
   # Rocket's inertia moment perpendicular to its axis (kg*m^2)
   "rocket_inertia_11": (1.988, 0.036),
   # Rocket's inertia moment relative to its axis (kg*m^2)
   "rocket_inertia_33": (0.015, 0.00028),
   # Motors's dry mass without propellant (kg) and its uncertainty (standard deviation)
   "motor_dry_mass": (0.001, 0.0001),
   # Motor's dry inertia moment perpendicular to its axis (kg*m^2)
   "motor_inertia_11": (0, 0),
   # Motor's dry inertia moment relative to its axis (kg*m^2)
   "motor_inertia_33": (0.0, 0.0),
   # Distance between the origin of the referential system and motor's center of dry mass (m)
   "center_of_dry_mass_position": (-0.644, 0.016),


   # Propulsion Details - run help(SolidMotor) for more information
   # Motor total impulse (N*s)
   "impulse": (2014, 40.3),
   # Motor burn out time (s)
   "burn_time": (1.69, 0.033),
   # Motor's nozzle radius (m)
   "nozzle_radius": (13.71 / 1000, 0.5 / 1000),
   # Motor's nozzle throat radius (m)
   "throat_radius": (9.50 / 1000, 0.5 / 1000),
   # Motor's grain separation (axial distance between two grains) (m)
   "grain_separation": (2.35 / 1000, 1 / 1000),
   # Motor's grain density (kg/m^3)
   "grain_density": (1617, 50),
   # Motor's grain outer radius (m)
   "grain_outer_radius": (23.60 / 1000, 0.375 / 1000),
   # Motor's grain inner radius (m)
   "grain_initial_inner_radius": (9.55 / 1000, 0.375 / 1000),
   # Motor's grain height (m)
   "grain_initial_height": (81.15 / 1000, 1 / 1000),


   # Aerodynamic Details - run help(Rocket) for more information
   # Rocket's radius (kg*m^2)
   "radius": (50 / 1000, 0.0005),
   # Distance between the origin of the referential system and nozzle exit plane (m) (negative)
   "nozzle_position": (-0.8429, 0.0005),
   # Distance between the origin of the referential system and center of propellant mass (m) (negative)
   "grains_center_of_mass_position": (-612/1000, 0.001),
   # Multiplier for rocket's drag curve. Usually has a mean value of 1 and a uncertainty of 5% to 10%
   "power_off_drag": (0.9081 / 1.05, 0.033),
   # Multiplier for rocket's drag curve. Usually has a mean value of 1 and a uncertainty of 5% to 10%
   "power_on_drag": (0.9081 / 1.05, 0.033),
   # Rocket's nose cone length (m)
   "nose_length": (0.55, 0.0005),
   # Power of the function that describes the shape of the nose cone
   "nose_pwr" : (0.7, 0.001),
   # Axial distance between rocket's center of dry mass and nearest point in its nose cone (m)
   "tail_distance_to_CM": (-0.7276, 0.001),
   # Axial distance between rocket's center of dry mass and nearest point in its nose cone (m)
   "nose_distance_to_CM": (0.6871, 0.001),
   # Number of fins
   "fin_number" : (3, 0),
   # Fin span (m)
   "fin_span": (0.11, 0.0005),
   # Fin root chord (m)
   "fin_root_chord": (0.24, 0.0005),
   # Fin tip chord (m)
   "fin_tip_chord": (0.12, 0.0005),
   # Axial distance between rocket's center of dry mass and nearest point in its fin (m)
   "fin_distance_to_CM": (-0.4876, 0.0005),
   "fin_sweep_angle": (28.6, 0.005),
   # Tail
   "tail_length": (0.10, 0.001),
   "tail_bottom_radius": (0.035, 0.0005),
   "tail_top_radius": (0.05, 0.0005),


   # Launch and Environment Details - run help(Environment) and help(Flight) for more information
   # Launch rail inclination angle relative to the horizontal plane (degrees)
   "inclination": (85, 1),
   # Launch rail heading relative to north (degrees)
   "heading": (180, 2),
   # Launch rail length (m)
   "rail_length": (10, 0.005),
   # Members of the ensemble forecast to be used
   "ensemble_member": list(range(10)),


   # Parachute Details - run help(Rocket) for more information
   # Drag coefficient times reference area for the rocket drogue chute (m^2)
   "cd_s_drogue": (1.5 * 1.13, 0.17), # INCERTEZZA DEL 10%
   # Drag coefficient times reference area for the rocket main chute (m^2)
   "cd_s_main": (0.97 * 7.30, 0.71), # INCERTEZZA DEL 10%
   # Time delay between parachute ejection signal is detected and parachute is inflated (s)
   "lag_rec": (1, 0.5),


   # Electronic Systems Details - run help(Rocket) for more information
   # Time delay between sensor signal is received and ejection signal is fired (s)
   "lag_se": (0.73, 0.16),
}


flights = []

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



#def save_rocket_geometry(rocket_radius, nose_pwr, nose_length, nose_distance_to_CM, tail_length, tail_distance_to_CM, tail_bottom_radius, fin_number, fin_span, fin_root_chord, fin_tip_chord, fin_sweep_angle, nozzle_radius):


    #Generate rocket geometry
    #rocket_geometry = {
    #    "x_cg": nose_length + nose_distance_to_CM,
    #    "nose_type": "POWER",
    #    "power": nose_pwr,
    #    "nose_length": nose_length,
    #    "nose_diameter": 2*rocket_radius,
    #    "ctrbody_length": nose_distance_to_CM +abs(tail_distance_to_CM),
    #    "ctrbody_diameter": 2*rocket_radius,
    #    "aftbody_length": tail_length,
    #    "aftbody_diameter": 2*tail_bottom_radius,
    #    "nozzle_diameter": 2*nozzle_radius,
    #    "semi_span": fin_span,
    #    "root_chord": fin_root_chord,
    #    "tip_chord": fin_tip_chord,
    #    "x_le": nose_distance_to_CM + nose_length + abs(tail_distance_to_CM) - fin_root_chord,
    #    "sweep": fin_sweep_angle,
    #    "n_fins": float(fin_number),
    #}
    
    #return rocket_geometry


def export_flight_data(flight_setting, flight_data, exec_time):
    # Generate flight results
    flight_result = {
        "out_of_rail_time": flight_data.out_of_rail_time,
        "out_of_rail_velocity": flight_data.out_of_rail_velocity,
        "max_velocity": flight_data.speed.max,
        "max_acceleration": flight_data.acceleration.max,
        "max_load_factor": flight_data.acceleration.max/9.80665,
        "max_aerodynamic_drag": flight_data.aerodynamic_drag.max,
        "max_aerodynamic_lift": flight_data.aerodynamic_lift.max,
        "max_aerodynamic_spin_moment": flight_data.aerodynamic_spin_moment.max,
        "max_aerodynamic_bending_moment": flight_data.aerodynamic_bending_moment.max,
    #    "max_parachute_chord_traction_force": (flight_data.acceleration(flight_data.parachute_events[0][0] + flight_data.parachute_events[0][1].lag+0.05))*flight_setting["rocket_mass"],
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

    # Write flight setting and results to file
    dispersion_input_file.write(str(flight_setting) + "\n")
    dispersion_output_file.write(str(flight_result) + "\n")


def export_flight_error(flight_setting):
    dispersion_error_file.write(str(flight_setting) + "\n")


BASE_DIR = Path(__file__).resolve().parent

# Basic analysis info
filename = BASE_DIR / "Borealis"
number_of_simulations = 50

# Create data files for inputs, outputs and error logging
dispersion_error_file = open(str(filename) + ".disp_errors.txt", "w")
dispersion_input_file = open(str(filename) + ".disp_inputs.txt", "w")
dispersion_output_file = open(str(filename) + ".disp_outputs.txt", "w")

# eng = matlab.engine.start_matlab()
# eng.cd(r'C:/Users/Dan/Documents/DAN/Uni/AurRoc_Projects/matcomlib-master', nargout = 0)

# Initialize counter and timer
i = 0

initial_wall_time = time()
initial_cpu_time = process_time()

# Define basic Environment object
#launch_day = datetime.date.today() + datetime.timedelta(days = 2)
Env = Environment(
    date = (2025, 10, 13, 15),
    longitude=11.658333, latitude=44.6,
    elevation = 7
)
#Env.set_elevation("Open-Elevation")
Env.max_expected_height = 3000
Env.set_atmospheric_model(
    type="Ensemble",
    file= BASE_DIR / "environment_data/SantaMargarida_Ensemble_LaunchDayWeatherData.nc",
    dictionary="ECMWF",
)


# Set up parachutes
def drogue_trigger(p, h, y):
    # Check if rocket is going down, i.e. if it has passed the apogee
    vertical_velocity = y[5]
    # Return true to activate parachute once the vertical velocity is negative
    return True if vertical_velocity < 0 else False

def main_trigger(p, h, y):
    # Check if rocket is below threshold
    altitude = h
    vertical_velocity = y[5]
    # Return true to activate parachute once altitude is below the threshold
    return True if altitude < 500 and vertical_velocity < 0 else False


# Iterate over flight settings
out = display("Starting", display_id=True)
for setting in flight_settings(analysis_parameters, number_of_simulations):
    start_time = process_time()
    i += 1

    # Update environment object
    Env.select_ensemble_member(setting["ensemble_member"])

    #rocket_geometry = save_rocket_geometry(setting["radius"], setting["nose_pwr"], setting["nose_length"], setting["nose_distance_to_CM"], setting["tail_length"], setting["tail_distance_to_CM"], setting["tail_bottom_radius"], setting["fin_number"], setting["fin_span"], setting["fin_root_chord"], setting["fin_tip_chord"], setting["fin_sweep_angle"], setting["nozzle_radius"])

    #eng.caseBuilderFromRPY(rocket_geometry, nargout = 0)
    #eng.matcom(nargout = 0)

    # Create motor
    Pro2014K120016A = SolidMotor(
        coordinate_system_orientation = "nozzle_to_combustion_chamber",
        thrust_source="",
        burn_time=setting["burn_time"],
        reshape_thrust_curve=(setting["burn_time"], setting["impulse"]),
        nozzle_radius=setting["nozzle_radius"],
        throat_radius=setting["throat_radius"],
        grain_number=5,
        grain_separation=setting["grain_separation"],
        grain_density=setting["grain_density"],
        grain_outer_radius=setting["grain_outer_radius"],
        grain_initial_inner_radius=setting["grain_initial_inner_radius"],
        grain_initial_height=setting["grain_initial_height"],
        interpolation_method="linear",
        nozzle_position=setting["nozzle_position"],
        grains_center_of_mass_position=setting["grains_center_of_mass_position"],
        dry_mass=setting["motor_dry_mass"],
        dry_inertia=(
            setting["motor_inertia_11"],
            setting["motor_inertia_11"],
            setting["motor_inertia_33"],
        ),
        center_of_dry_mass_position=setting["center_of_dry_mass_position"],
    )
    # Create rocket
    Borealis_A8_10_P = Rocket(
        radius=setting["radius"],
        mass=setting["rocket_mass"],
        inertia=(
            setting["rocket_inertia_11"],
            setting["rocket_inertia_11"],
            setting["rocket_inertia_33"],
        ),
        power_off_drag= BASE_DIR / "BorealisA8_power_off.csv",
        power_on_drag=BASE_DIR / "BorealisA8_power_off.csv",
        center_of_mass_without_motor=0,
        coordinate_system_orientation="tail_to_nose",
    )
    Borealis_A8_10_P.set_rail_buttons(0.224, -0.224, 30)

    Borealis_A8_10_P.add_motor(Pro2014K120016A, position=0)

    # Edit rocket drag

    # Add rocket nose, fins and tail
    NoseCone = Borealis_A8_10_P.add_nose(
        length=setting["nose_length"],
        kind="powerseries",
        power=setting["nose_pwr"],
        position = setting["nose_distance_to_CM"] + setting["nose_length"],
    )
    FinSet = Borealis_A8_10_P.add_trapezoidal_fins(
        n=3,
        span=setting["fin_span"],
        root_chord=setting["fin_root_chord"],
        tip_chord=setting["fin_tip_chord"],
        position=setting["fin_distance_to_CM"],
        sweep_angle=setting["fin_sweep_angle"],
        cant_angle=0,
        airfoil = None,
    )
    Tail = Borealis_A8_10_P.add_tail(
        top_radius=setting["tail_top_radius"],
        bottom_radius=setting["tail_bottom_radius"], 
        length=setting["tail_length"], 
        position = setting["tail_distance_to_CM"],
    )
    
    #export_rocket_geometry(Borealis_A8_10_P, NoseCone, setting["nose_distance_to_CM"], setting["nose_length"], Tail, setting["tail_distance_to_CM"], FinSet, Pro2014K120016A)
    

    #Borealis_A8_10_P.power_off_drag *= setting["power_off_drag"]
    #Borealis_A8_10_P.power_on_drag *= setting["power_on_drag"]

    # Add parachute
    Drogue = Borealis_A8_10_P.add_parachute(
        "Drogue",
        cd_s=setting["cd_s_drogue"],
        trigger=drogue_trigger,
        sampling_rate=105,
        lag=setting["lag_rec"] + setting["lag_se"],
        noise=(0, 8.3, 0.5),
    )
    Main = Borealis_A8_10_P.add_parachute(
        "Main",
        cd_s=setting["cd_s_main"],
        trigger=main_trigger,
        sampling_rate=105,
        lag=setting["lag_rec"] + setting["lag_se"],
        noise=(0, 8.3, 0.5),
    )

    # Run trajectory simulation
    try:
        rocket_flight = Flight(
            rocket=Borealis_A8_10_P,
            environment=Env,
            rail_length=setting["rail_length"],
            inclination=setting["inclination"],
            heading=setting["heading"],
            max_time=600,
        )

        flights.append(rocket_flight)

        #if i != 1:
        #    os.remove("""C:/Users/Dan/Documents/DAN/Uni/AurRoc_Projects/matcomlib-master/results/Borealis_A8_10_PowerOnDrag.csv""")

        if i == 1:
            Borealis_A8_10_P.evaluate_nozzle_gyration_tensor()
            Pro2014K120016A.draw()

        export_flight_data(setting, rocket_flight, process_time() - start_time)

        if i == 1:
            #rocket_flight.all_info()
            #plt.plot(rocket_flight.aerodynamic_bending_moment((1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30)))
            #print(rocket_flight.aerodynamic_bending_moment((1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30)))
            rocket_flight.acceleration()
            Borealis_A8_10_P.draw()

            # Perform a Fourier Analysis
            Fs = 100.0
            # sampling rate
            Ts = 1.0 / Fs
            # sampling interval
            t = np.arange(1, 400, Ts)  # time vector
            ff = 5
            # frequency of the signal
            y = rocket_flight.aerodynamic_bending_moment(t) - np.mean(rocket_flight.aerodynamic_bending_moment(t))
            n = len(y)  # length of the signal
            k = np.arange(n)
            T = n / Fs
            frq = k / T  # two sides frequency range
            frq = frq[range(n // 2)]  # one side frequency range
            Y = np.fft.fft(y) / n  # fft computing and normalization
            Y = Y[range(n // 2)]

            # Create the plot
            fig, ax = plt.subplots(2, 1)
            ax[0].plot(t, y)
            ax[0].set_xlabel("Time")
            ax[0].set_ylabel("Signal")
            ax[0].set_xlim((0, 5))
            ax[0].grid()
            ax[1].plot(frq, abs(Y), "r")  # plotting the spectrum
            ax[1].set_xlabel("Freq (Hz)")
            ax[1].set_ylabel("|Y(freq)|")
            ax[1].set_xlim((0, 5))
            ax[1].grid()
            plt.subplots_adjust(hspace=0.5)
            plt.show()

    except Exception as E:
        print(E)
        export_flight_error(setting)

    # Register time
    #out.update(
    #    f"Current iteration: {i:06d} | Average Time per Iteration: {(process_time() - initial_cpu_time)/i:2.6f} s"
    #)

comparison = CompareFlights(flights)

# Done

## Print and save total time
final_string = f"Completed {i} iterations successfully. Total CPU time: {process_time() - initial_cpu_time} s. Total wall time: {time() - initial_wall_time} s"
#out.update(final_string)
dispersion_input_file.write(final_string + "\n")
dispersion_output_file.write(final_string + "\n")
dispersion_error_file.write(final_string + "\n")

## Close files
dispersion_input_file.close()
dispersion_output_file.close()
dispersion_error_file.close()

filename = BASE_DIR / "Borealis"

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
dispersion_output_file = open(str(filename) + ".disp_outputs.txt", "r+")

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

comparison.aerodynamic_forces()
comparison.aerodynamic_moments()


# Print number of flights simulated
N = len(dispersion_general_results)
print("Number of simulations: ", N)

print(
    f'Out of Rail Time -         Mean Value: {np.mean(dispersion_results["out_of_rail_time"]):0.3f} s'
)
print(
    f'Out of Rail Time - Standard Deviation: {np.std(dispersion_results["out_of_rail_time"]):0.3f} s'
)

plt.figure()
plt.hist(dispersion_results["out_of_rail_time"], bins=int(N**0.5))
plt.title("Out of Rail Time")
plt.xlabel("Time (s)")
plt.ylabel("Number of Occurences")
plt.grid(True)
plt.show()

print(
    f'Out of Rail Velocity -         Mean Value: {np.mean(dispersion_results["out_of_rail_velocity"]):0.3f} m/s'
)
print(
    f'Out of Rail Velocity - Standard Deviation: {np.std(dispersion_results["out_of_rail_velocity"]):0.3f} m/s'
)

plt.figure()
plt.hist(dispersion_results["out_of_rail_velocity"], bins=int(N**0.5))
plt.title("Out of Rail Velocity")
plt.xlabel("Velocity (m/s)")
plt.ylabel("Number of Occurences")
plt.grid(True)
plt.show()

print(
    f'Apogee Time -         Mean Value: {np.mean(dispersion_results["apogee_time"]):0.3f} s'
)
print(
    f'Apogee Time - Standard Deviation: {np.std(dispersion_results["apogee_time"]):0.3f} s'
)

plt.figure()
plt.hist(dispersion_results["apogee_time"], bins=int(N**0.5))
plt.title("Apogee Time")
plt.xlabel("Time (s)")
plt.ylabel("Number of Occurences")
plt.grid(True)
plt.show()


print(
    f'Apogee Altitude -         Mean Value: {np.mean(dispersion_results["apogee_altitude"]):0.3f} m'
)
print(
    f'Apogee Altitude - Standard Deviation: {np.std(dispersion_results["apogee_altitude"]):0.3f} m'
)

plt.figure()
plt.hist(dispersion_results["apogee_altitude"], bins=int(N**0.5))
plt.title("Apogee Altitude")
plt.xlabel("Altitude (m)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Apogee X Position -         Mean Value: {np.mean(dispersion_results["apogee_x"]):0.3f} m'
)
print(
    f'Apogee X Position - Standard Deviation: {np.std(dispersion_results["apogee_x"]):0.3f} m'
)

plt.figure()
plt.hist(dispersion_results["apogee_x"], bins=int(N**0.5))
plt.title("Apogee X Position")
plt.xlabel("Apogee X Position (m)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Apogee Y Position -         Mean Value: {np.mean(dispersion_results["apogee_y"]):0.3f} m'
)
print(
    f'Apogee Y Position - Standard Deviation: {np.std(dispersion_results["apogee_y"]):0.3f} m'
)

plt.figure()
plt.hist(dispersion_results["apogee_y"], bins=int(N**0.5))
plt.title("Apogee Y Position")
plt.xlabel("Apogee Y Position (m)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Impact Time -         Mean Value: {np.mean(dispersion_results["impact_time"]):0.3f} s'
)
print(
    f'Impact Time - Standard Deviation: {np.std(dispersion_results["impact_time"]):0.3f} s'
)

plt.figure()
plt.hist(dispersion_results["impact_time"], bins=int(N**0.5))
plt.title("Impact Time")
plt.xlabel("Time (s)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Impact X Position -         Mean Value: {np.mean(dispersion_results["impact_x"]):0.3f} m'
)
print(
    f'Impact X Position - Standard Deviation: {np.std(dispersion_results["impact_x"]):0.3f} m'
)

plt.figure()
plt.hist(dispersion_results["impact_x"], bins=int(N**0.5))
plt.title("Impact X Position")
plt.xlabel("Impact X Position (m)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Impact Y Position -         Mean Value: {np.mean(dispersion_results["impact_y"]):0.3f} m'
)
print(
    f'Impact Y Position - Standard Deviation: {np.std(dispersion_results["impact_y"]):0.3f} m'
)

plt.figure()
plt.hist(dispersion_results["impact_y"], bins=int(N**0.5))
plt.title("Impact Y Position")
plt.xlabel("Impact Y Position (m)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Impact Velocity -         Mean Value: {np.mean(dispersion_results["impact_velocity"]):0.3f} m/s'
)
print(
    f'Impact Velocity - Standard Deviation: {np.std(dispersion_results["impact_velocity"]):0.3f} m/s'
)

plt.figure()
plt.hist(dispersion_results["impact_velocity"], bins=int(N**0.5))
plt.title("Impact Velocity")
plt.grid()
plt.xlim(-35, 0)
plt.xlabel("Velocity (m/s)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Initial Static Margin -             Mean Value: {np.mean(dispersion_results["initial_static_margin"]):0.3f} c'
)
print(
    f'Initial Static Margin -     Standard Deviation: {np.std(dispersion_results["initial_static_margin"]):0.3f} c'
)

print(
    f'Out of Rail Static Margin -         Mean Value: {np.mean(dispersion_results["out_of_rail_static_margin"]):0.3f} c'
)
print(
    f'Out of Rail Static Margin - Standard Deviation: {np.std(dispersion_results["out_of_rail_static_margin"]):0.3f} c'
)

print(
    f'Final Static Margin -               Mean Value: {np.mean(dispersion_results["final_static_margin"]):0.3f} c'
)
print(
    f'Final Static Margin -       Standard Deviation: {np.std(dispersion_results["final_static_margin"]):0.3f} c'
)

plt.figure()
plt.hist(dispersion_results["initial_static_margin"], label="Initial", bins=int(N**0.5))
plt.hist(
    dispersion_results["out_of_rail_static_margin"],
    label="Out of Rail",
    bins=int(N**0.5),
)
plt.hist(dispersion_results["final_static_margin"], label="Final", bins=int(N**0.5))
plt.legend()
plt.title("Static Margin")
plt.xlabel("Static Margin (c)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Maximum Velocity -         Mean Value: {np.mean(dispersion_results["max_velocity"]):0.3f} m/s'
)
print(
    f'Maximum Velocity - Standard Deviation: {np.std(dispersion_results["max_velocity"]):0.3f} m/s'
)

plt.figure()
plt.hist(dispersion_results["max_velocity"], bins=int(N**0.5))
plt.title("Maximum Velocity")
plt.xlabel("Velocity (m/s)")
plt.ylabel("Number of Occurences")
plt.grid(True)
plt.show()

print(
    f'Maximum Acceleration -         Mean Value: {np.mean(dispersion_results["max_acceleration"]):0.3f} m/s^2'
)
print(
    f'Maximum Acceleration - Standard Deviation: {np.std(dispersion_results["max_acceleration"]):0.3f} m/s^2'
)

plt.figure()
plt.hist(dispersion_results["max_acceleration"], bins=int(N**0.5))
plt.title("Maximum Acceleration")
plt.xlabel("Acceleration (m/s^2)")
plt.ylabel("Number of Occurences")
plt.grid(True)
plt.show()

print(
    f'Maximum Load Factor -         Mean Value: {np.mean(dispersion_results["max_load_factor"]):0.3f} G'
)
print(
    f'Maximum Load Factor - Standard Deviation: {np.std(dispersion_results["max_load_factor"]):0.3f} G'
)

plt.figure()
plt.hist(dispersion_results["max_load_factor"], bins=int(N**0.5))
plt.title("Maximum Load Factor")
plt.xlabel("Load Factor (G)")
plt.ylabel("Number of Occurences")
plt.grid(True)
plt.show()

#print(
#    f'Maximum Parachute Chord Traction Force -         Mean Value: {np.mean(dispersion_results["max_parachute_chord_traction_force"]):0.3f} N'
#)
#print(
#    f'Maximum Parachute Chord Traction Force - Standard Deviation: {np.std(dispersion_results["max_parachute_chord_traction_force"]):0.3f} N'
#)

#plt.figure()
#plt.hist(dispersion_results["max_parachute_chord_traction_force"], bins=int(N**0.5))
#plt.title("Maximum Parachute Chord Traction Force")
#plt.xlabel("Parachute Chord Traction Force (N)")
#plt.ylabel("Number of Occurences")
#plt.show()

print(
    f'Maximum Aerodynamic Drag -         Mean Value: {np.mean(dispersion_results["max_aerodynamic_drag"]):0.3f} N'
)
print(
    f'Maximum Aerodynamic Drag - Standard Deviation: {np.std(dispersion_results["max_aerodynamic_drag"]):0.3f} N'
)

plt.figure()
plt.hist(dispersion_results["max_aerodynamic_drag"], bins=int(N**0.5))
plt.title("Maximum Aerodynamic Drag")
plt.xlabel("Drag Force (N)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Maximum Aerodynamic Lift -         Mean Value: {np.mean(dispersion_results["max_aerodynamic_lift"]):0.3f} N'
)
print(
    f'Maximum Aerodynamic Lift - Standard Deviation: {np.std(dispersion_results["max_aerodynamic_lift"]):0.3f} N'
)

plt.figure()
plt.hist(dispersion_results["max_aerodynamic_lift"], bins=int(N**0.5))
plt.title("Maximum Aerodynamic Lift")
plt.xlabel("Lift Force (N)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Maximum Aerodynamic Spin Moment -         Mean Value: {np.mean(dispersion_results["max_aerodynamic_spin_moment"]):0.3f} N*m'
)
print(
    f'Maximum Aerodynamic Spin Moment - Standard Deviation: {np.std(dispersion_results["max_aerodynamic_spin_moment"]):0.3f} N*m'
)

plt.figure()
plt.hist(dispersion_results["max_aerodynamic_spin_moment"], bins=int(N**0.5))
plt.title("Maximum Aerodynamic Spin Moment")
plt.xlabel("Spin Moment (N*m)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Maximum Aerodynamic Bending Moment -         Mean Value: {np.mean(dispersion_results["max_aerodynamic_bending_moment"]):0.3f} N*m'
)
print(
    f'Maximum Aerodynamic Bending Moment - Standard Deviation: {np.std(dispersion_results["max_aerodynamic_bending_moment"]):0.3f} N*m'
)

plt.figure()
plt.hist(dispersion_results["max_aerodynamic_bending_moment"], bins=int(N**0.5))
plt.title("Maximum Aerodynamic Bending Moment")
plt.xlabel("Bending Moment (N*m)")
plt.ylabel("Number of Occurences")
plt.show()

plt.figure()
plt.hist(dispersion_results["number_of_events"])
plt.title("Parachute Events")
plt.xlabel("Number of Parachute Events")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Drogue Parachute Trigger Time -         Mean Value: {np.mean(dispersion_results["drogue_triggerTime"]):0.3f} s'
)
print(
    f'Drogue Parachute Trigger Time - Standard Deviation: {np.std(dispersion_results["drogue_triggerTime"]):0.3f} s'
)

plt.figure()
plt.hist(dispersion_results["drogue_triggerTime"], bins=int(N**0.5))
plt.title("Drogue Parachute Trigger Time")
plt.xlabel("Time (s)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Drogue Parachute Fully Inflated Time -         Mean Value: {np.mean(dispersion_results["drogue_inflated_time"]):0.3f} s'
)
print(
    f'Drogue Parachute Fully Inflated Time - Standard Deviation: {np.std(dispersion_results["drogue_inflated_time"]):0.3f} s'
)

plt.figure()
plt.hist(dispersion_results["drogue_inflated_time"], bins=int(N**0.5))
plt.title("Drogue Parachute Fully Inflated Time")
plt.xlabel("Time (s)")
plt.ylabel("Number of Occurences")
plt.show()

print(
    f'Drogue Parachute Fully Inflated Velocity -         Mean Value: {np.mean(dispersion_results["drogue_inflated_velocity"]):0.3f} m/s'
)
print(
    f'Drogue Parachute Fully Inflated Velocity - Standard Deviation: {np.std(dispersion_results["drogue_inflated_velocity"]):0.3f} m/s'
)

plt.figure()
plt.hist(dispersion_results["drogue_inflated_velocity"], bins=int(N**0.5))
plt.title("Drogue Parachute Fully Inflated Velocity")
plt.xlabel("Velocity m/s)")
plt.ylabel("Number of Occurences")
plt.show()

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------#

# Dispersion ellipses plot
# Import libraries
import imageio.v2 as imageio
from imageio import imread
from matplotlib.patches import Ellipse

# Import background map
img = imread(BASE_DIR / "environment_data/santa_margarida_military_shooting_range_launch_site.png")

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
    apogee_x, apogee_y, s=5, marker="^", color="green", label="Simulated Apogee"
)
# Draw impact points
plt.scatter(
    impact_x, impact_y, s=5, marker="v", color="blue", label="Simulated Landing Point"
)
# Draw real landing point
#plt.scatter(
#    411.89, -61.07, s=20, marker="X", color="red", label="Measured Landing Point"
#)

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
plt.imshow(img, zorder=0, extent=[-3250 - dx, 3250 - dx, -1375 - dy, 1375 - dy])
plt.axhline(0, color="black", linewidth=0.5)
plt.axvline(0, color="black", linewidth=0.5)
plt.xlim(-500, 1000)
plt.ylim(-750, 750)

# Save plot and show result
plt.savefig(str(filename) + ".pdf", bbox_inches="tight", pad_inches=0)
plt.savefig(str(filename) + ".svg", bbox_inches="tight", pad_inches=0)
plt.show()