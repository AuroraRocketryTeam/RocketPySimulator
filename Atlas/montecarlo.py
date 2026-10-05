"""
Atlas Monte Carlo.

Every run flies Atlas (atlas_model.py) with all the parameters drawn from a normal distribution
around their nominal value (std from the files in simulation_inputs/). The versions of geometry,
aerodynamics, motor, recovery, airbrakes and launch site are chosen at the top of atlas_model.py.

Outputs in simulation_output/montecarlo_output/<output_dir_name>/: inputs and outputs of every run (json), dispersion
graphs, launch site map with the 1-2-3 sigma ellipses, comparison and sensitivity graphs.
"""
print("importing libraries...", end="\r")
import json
import multiprocessing as mp
import os
import pickle
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from imageio.v2 import imread
from matplotlib.patches import Ellipse
from scipy.stats import norm

import atlas_model as model

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "tools" / "others"))
from compare_plot_saver import save_compare_plots  # noqa: E402

#-------------------------------------------------------------------------------------------------------- PARAMETERS
# Name of the output folder (can be a new folder or an existing one to overwrite)
output_dir_name = 'Atlas_iterazione_2'
number_of_simulations = 200
weather_data = 'c'          # c = custom (mean EuRoC week), e = ensemble, f = forecast, i = ISA
seed = None                 # integer to repeat exactly the same runs
workers = os.cpu_count()

# OPTIONS:
ballistic = False           # True = flight without parachutes
show_dispersion_graph = False
show_compare_graph = False
save_compare_graph = False
sensitivity_analysis = False
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


def loading_bar(initial_time, number_of_iterations, iteration, bar_lenght=24):
    time_for_iteration = (time.time() - initial_time) / iteration
    seconds_remaining = round(time_for_iteration*(number_of_iterations-iteration))

    current_iteration = f"{iteration:0{len(str(number_of_iterations))}d}"
    average_time = f"{time_for_iteration:2.2f}s"
    time_remaining = f"{seconds_remaining//3600:02d}:{(seconds_remaining%3600)//60:02d}:{seconds_remaining%60:02d}"
    bar = f"{'█'*(bar_lenght*iteration//number_of_iterations):░<{bar_lenght}}"
    percentage = f"{100*iteration/number_of_iterations:.1f}%"

    print(f"Current iteration: {colored(current_iteration)}",end=' ')
    print(f"Average time per iteration: {colored(average_time)}",end=' ')
    print(f"Time remaining: {colored(time_remaining)}",end=" ")
    print(f"|{colored(bar)}|[{colored(percentage):<7}]",end="\r")
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- SIMULATION
PARAMETERS = model.load_parameters()

# Environment of the current process (one per worker)
_ENV = None
# Keep the Flight objects only when the comparison graphs need them
_KEEP_FLIGHTS = False


def init_worker(weather, keep_flights):
    global _ENV, _KEEP_FLIGHTS
    _ENV = model.build_environment(weather)
    _KEEP_FLIGHTS = keep_flights


def flight_results(flight, env, execution_time):
    results = {
        "out_of_rail_time": flight.out_of_rail_time,
        "out_of_rail_velocity": flight.out_of_rail_velocity,
        "max_velocity": flight.max_speed,
        # Maximum acceleration with the motor on (the maximum over the whole flight is the main opening
        # shock), without the numerical spike of RocketPy at burnout
        "max_acceleration": model.max_acceleration_power_on(flight),
        "max_aerodynamic_drag": flight.aerodynamic_drag.max,
        "max_aerodynamic_lift": flight.aerodynamic_lift.max,
        "max_aerodynamic_spin_moment": flight.aerodynamic_spin_moment.max,
        "max_aerodynamic_bending_moment": flight.aerodynamic_bending_moment.max,
        "apogee_time": flight.apogee_time,
        "apogee_altitude": flight.apogee - env.elevation,
        "apogee_x": flight.apogee_x,
        "apogee_y": flight.apogee_y,
        "impact_time": flight.t_final,
        "impact_x": flight.x_impact,
        "impact_y": flight.y_impact,
        "impact_velocity": flight.impact_velocity,
        "initial_static_margin": flight.rocket.static_margin(0),
        "out_of_rail_static_margin": flight.rocket.static_margin(flight.out_of_rail_time),
        "final_static_margin": flight.rocket.static_margin(flight.rocket.motor.burn_out_time),
        "number_of_events": len(flight.parachute_events),
        "execution_time": execution_time,
    }
    if flight.parachute_events:
        trigger_time, drogue = flight.parachute_events[0]
        results["drogue_triggerTime"] = trigger_time
        results["drogue_inflated_time"] = trigger_time + drogue.lag
        results["drogue_inflated_velocity"] = flight.speed(trigger_time + drogue.lag)
    return results


def run_one(run_seed):
    start = time.process_time()
    rng = np.random.default_rng(run_seed)
    setting = model.sample(PARAMETERS, rng)
    if _ENV.atmospheric_model_type == "Ensemble":
        setting["ensemble_member"] = int(rng.integers(getattr(_ENV, "num_ensemble_members", 10)))
        _ENV.select_ensemble_member(setting["ensemble_member"])
    try:
        flight = model.simulate(setting, _ENV, recovery=not ballistic)
        results = flight_results(flight, _ENV, time.process_time() - start)
        return setting, results, None, flight if _KEEP_FLIGHTS else None
    except Exception as error:
        return setting, None, repr(error), None
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- DISPERSION GRAPHS
# The following section generates the output distribution plots and automatically saves them on your PC
# To create each picture, the algorythm performs the following actions:

# - Fits a normal distribution to the dataset and compute the average value and standard deviation;
# - Prints the fitted mean and standard deviation,
# - Creates a histogram of the data and overlays the corresponding normal distribution curve;
# - Adds title, axis labels, and a grid to the plot for better clarity;
# - Saves the plot as a .svg file for high-quality output (e.g., for reports or web use);
# - Saves the entire figure as a pickle file for later reuse or resizing (open it with tools/others/pickle_opener.py)

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


def plot_graph(out_data, x_label, title, unit_of_measure, output_svg, output_pickle):
    s = plt.figure()
    mu_out, std_out = norm.fit(out_data)

    plt.hist(
        out_data,
        bins=int(len(out_data)**0.5),
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

    plt.savefig(str(output_svg/title)+".svg", format='svg')
    with open(str(output_pickle/title)+".pickle", "wb") as f:
        pickle.dump(s, f)

    if show_dispersion_graph:
        plt.show()
    plt.close(s)


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
    "Maximum Aerodynamic Drag":["max_aerodynamic_drag","Drag Force","N"],
    "Maximum Aerodynamic Lift":["max_aerodynamic_lift","Lift Force", "N"],
    "Maximum Aerodynamic Spin Moment":["max_aerodynamic_spin_moment","Spin Moment", "N*m"],
    "Maximum Aerodynamic Bending Moment":["max_aerodynamic_bending_moment","Bending Moment", "N*m"],
    "Drogue Parachute Trigger Time":["drogue_triggerTime","Time", "s"],
    "Drogue Parachute Fully Inflated Time":["drogue_inflated_time","Time", "s"],
    "Drogue Parachute Fully Inflated Velocity":["drogue_inflated_velocity","Velocity", "m/s"],
}
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- LAUNCH SITE
def eigsorted(cov):
    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    return vals[order], vecs[:, order]


def launch_site_graph(results, output_launch_site):
    # Import background map
    img = imread(str(model.SITE_DIR / "santa_margarida_military_shooting_range_launch_site.png"))

    apogee_x = np.array([r["apogee_x"] for r in results])
    apogee_y = np.array([r["apogee_y"] for r in results])
    impact_x = np.array([r["impact_x"] for r in results])
    impact_y = np.array([r["impact_y"] for r in results])

    s = plt.figure(num=None, dpi = 150, facecolor="w", edgecolor="k")
    ax = plt.subplot(111)

    plt.scatter(0, 0, s=30, marker="*", color="red", label="Launch Point")
    plt.scatter(apogee_x, apogee_y, s=5, marker="^", color="lime", label="Simulated Apogee", alpha=0.7)
    plt.scatter(impact_x, impact_y, s=5, marker="v", color="cyan", label="Simulated Landing Point", alpha=0.7)

    # 1, 2 and 3 sigma error ellipses for impact and apogee
    for x, y, face in [(impact_x, impact_y, (0, 0, 1, 0.2)), (apogee_x, apogee_y, (0, 1, 0, 0.2))]:
        vals, vecs = eigsorted(np.cov(x, y))
        theta = np.degrees(np.arctan2(*vecs[:, 0][::-1]))
        width, height = 2 * np.sqrt(vals)
        for j in [1, 2, 3]:
            ellipse = Ellipse(xy=(np.mean(x), np.mean(y)), width=width * j, height=height * j, angle=theta, color="black")
            ellipse.set_facecolor(face)
            ax.add_artist(ellipse)

    plt.legend()
    plt.grid(visible=True, which='minor', linestyle='--', color='grey', alpha=0.3, linewidth=0.6)
    plt.grid(visible=True, which='major', linestyle='-', color='white', alpha=0.4, linewidth=0.8)

    ax.set_title(r"1$\sigma$, 2$\sigma$ and 3$\sigma$ Dispersion Ellipses: Apogee and Landing Points")
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

    plt.savefig(str(output_launch_site) + "/Santa_Margarida_launch_site.svg", format='svg', bbox_inches="tight")
    with open(str(output_launch_site) + "/Santa_Margarida_launch_site.pickle", "wb") as f:
        pickle.dump(s, f)
    print("- Santa Margarida launch site graph saved successfully")

    if show_dispersion_graph:
        plt.show()
    plt.close('all')
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- SENSITIVITY ANALYSIS
def sensitivity_graphs(filename, results, output_sensitivity):
    from rocketpy.sensitivity import SensitivityModel
    from rocketpy.tools import load_monte_carlo_data

    target_variables = ["apogee_altitude", "max_acceleration"]
    # Only the parameters that actually vary
    parameters = [name for name, (_, std) in PARAMETERS.items() if std > 0]

    parameters_matrix, target_variables_matrix = load_monte_carlo_data(
        input_filename=str(filename)+".disp_inputs.json",
        output_filename=str(filename)+".disp_outputs.json",
        parameters_list=parameters,
        target_variables_list=target_variables,
    )

    sensitivity = SensitivityModel(parameters, target_variables)
    sensitivity.set_parameters_nominal(
        [PARAMETERS[name][0] for name in parameters],
        [PARAMETERS[name][1] for name in parameters],
    )
    sensitivity.set_target_variables_nominal([np.mean([r[t] for r in results]) for t in target_variables])
    sensitivity.fit(parameters_matrix, target_variables_matrix)

    # Workaround (RocketPy doesn't provide a save option):
    # plt.ion() lets the code continue while bar_plot is displayed.
    # Figures are saved and remain open for viewing if desired.
    plt.ion()
    sensitivity.plots.bar_plot()

    for target in range(len(target_variables)):
        sens_fig = plt.figure(target+1)
        sens_fig.savefig(f"{str(output_sensitivity)}/sensitivity_{target_variables[target]}.svg", dpi=300)

    if show_dispersion_graph:
        plt.pause(99999) # that's a lot of damag...time.

    plt.close("all")
    plt.ioff()
    print("- Sensitivity analysis graphs saved successfully")
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- MAIN
def main():
    global sensitivity_analysis

    # Paths
    output_path = BASE_DIR/"simulation_output"/"montecarlo_output"/output_dir_name
    filename = str(output_path/"Atlas")
    output_sensitivity = output_path/"sensitivity"
    output_comparison = output_path/"comparison"
    output_dispersion_pickle = output_path/"dispersion"/"pickle"
    output_dispersion_svg = output_path/"dispersion"/"svg"
    output_launch_site = output_path/"launch_site"

    # First information print
    print("Montecarlo Rocket flight simulator\n")
    print(f"- Filename is: {colored(filename)}")
    print(f"- Number of simulations: {colored(number_of_simulations)}")
    print(f"- Output directory: {colored(output_dir_name)}")
    print(f"- Geometry {colored(model.GEOMETRY)}, aerodynamics {colored(model.AERODYNAMICS)}, "
          f"motor {colored(model.MOTOR)}, recovery {colored(model.RECOVERY)}, airbrakes {colored(model.AIRBRAKES)}\n")

    #WARNINGS
    if ballistic:
        print(f"<!> Parachutes: {colored('deactivated (ballistic flight)')}")

    # with less than 50 simulations sensitivity analysis returns errors
    if number_of_simulations<50 and sensitivity_analysis:
        print(f"<!> Less than 50 simulations: {colored('sensitivity analysis deactivated')}")
        sensitivity_analysis = False

    # Create or overwrite folders for outputs
    if output_path.is_dir():
        overwrite_folder = input(f'<!> The "{output_dir_name}" folder already exists. Do you want to overwrite it? [{colored('y/n')}] - ')
        if not overwrite_folder.lower() in ['y','yes']:
            print("You chose not to overwrite the folder. Stopping the program.")
            raise SystemExit(0)

    print("\nStarting...", end='\r')
    for folder in [output_sensitivity, output_comparison, output_dispersion_pickle, output_dispersion_svg, output_launch_site]:
        folder.mkdir(parents=True, exist_ok=True)

    # The comparison graphs need all the Flight objects: in that case the runs are made in this process
    keep_flights = show_compare_graph or save_compare_graph
    run_seeds = np.random.SeedSequence(seed).generate_state(number_of_simulations)
    initial_time = time.time()
    initial_cpu_time = time.process_time()
    results, flights, errors = [], [], 0

    with open(filename + ".disp_inputs.json", "w") as input_file, \
         open(filename + ".disp_outputs.json", "w") as output_file, \
         open(filename + ".disp_errors.txt", "w") as error_file:
        if keep_flights:
            init_worker(weather_data, True)
            runs = map(run_one, run_seeds)
        else:
            pool = mp.get_context("fork").Pool(workers, initializer=init_worker, initargs=(weather_data, False))
            runs = pool.imap_unordered(run_one, run_seeds)

        for i, (setting, flight_result, error, flight) in enumerate(runs, start=1):
            if error is None:
                # Inputs and outputs on the same line number, as needed by the sensitivity analysis
                input_file.write(json.dumps(setting, default=float) + "\n")
                output_file.write(json.dumps(flight_result, default=float) + "\n")
                results.append(flight_result)
                if flight is not None:
                    flights.append(flight)
            else:
                errors += 1
                print(f"\n{error}")
                error_file.write(json.dumps({**setting, "error": error}, default=float) + "\n")
            loading_bar(initial_time, number_of_simulations, i)

        if not keep_flights:
            pool.close()
            pool.join()

    # jump a row to not overwrite loading bar
    print('\n')
    cpu_time = round(time.process_time() - initial_cpu_time, 2)
    wall_time = round(time.time() - initial_time, 2)
    print(f"Completed {len(results)} iterations successfully, {errors} errors. "
          f"Total CPU time (main process): {colored(cpu_time)} s. Total wall time: {colored(wall_time)} s")
    
    # COMPARISON GRAPHS
    if keep_flights:
        from rocketpy import CompareFlights
        
        print(colored('\n\nComparison graphs:'))
        comparison = CompareFlights(flights)
        if show_compare_graph:
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
        if save_compare_graph:
            save_compare_plots(
                comparison_object=comparison,
                plots=[
                    ("velocities", {"legend": False}),
                    ("accelerations", {"legend": False}),
                    ("attitude_angles", {"legend": False}),
                    ("euler_angles", {"legend": False}),
                    ("aerodynamic_forces", {"legend": False}),
                    ("aerodynamic_moments", {"legend": False}),
                    ("angular_velocities", {"legend": False}),
                    ("trajectories_3d", {}),
                    ("rail_buttons_forces", {"legend": False}),
                    ("stability_margin", {"legend": False}),
                ],
                output_dir=output_comparison,
                formats=["svg", "pickle"],
            )

    # DISPERSION GRAPHS
    print(colored('\n\nDispersion graphs:\n'))
    for title, (key, x_label, unit) in all_plots.items():
        data = [r[key] for r in results if key in r]
        if len(data) > 1:
            plot_graph(data, x_label, title, unit, output_dispersion_svg, output_dispersion_pickle)

    print(colored('\n\nLaunch site graph:'))
    launch_site_graph(results, output_launch_site)

    if sensitivity_analysis:
        print(colored('\n\nSensitivity analysis graphs:'))
        sensitivity_graphs(filename, results, output_sensitivity)


if __name__ == "__main__":
    main()
    
#-------------------------------------------------------------------------------------------------------
