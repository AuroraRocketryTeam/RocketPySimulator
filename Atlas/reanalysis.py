"""
Atlas reanalysis: one flight with every parameter at its nominal value (atlas_model.py).

Saves the trajectory as .kml (open it in Google Earth) in simulation_output/reanalysis_output/ and, if asked, the
mass and center of mass over time for tools/mass_analysis/.
"""
from pathlib import Path

import pandas as pd

import atlas_model as model

import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent


import numpy as np
import matplotlib.pyplot as plt

def airbrakes_graph(flight, env, target_agl, output_path):
    """Opening, predicted apogee and altitude over time, saved as .svg."""
    if not flight.rocket.air_brakes:
        return
    rows = [r for r in flight.get_controller_observed_variables() if r is not None and len(r) == 4]
    # Drop the initial_observed_variables row (all zeros)
    rows = [r for r in rows if any(v != 0 for v in r)]
    if not rows:
        print("Airbrakes graph skipped: the controller recorded no data")
        return
    t, level, cd, apogee = np.array(rows, dtype=float).T
    apogee = np.where(apogee > 0, apogee, np.nan)         # 0 = controller not predicting


    fig, ax = plt.subplots(3, 1, figsize=(9, 9), sharex=True)

    ax[0].plot(t, flight.z(t) - env.elevation, color="tab:blue")
    ax[0].set_ylabel("Altitude AGL (m)")

    ax[1].step(t, 100 * level, where="post", color="tab:red")
    ax[1].set_ylabel("Airbrakes opening (%)")
    ax[1].set_ylim(-5, 105)

    ax[2].plot(t, apogee, color="tab:green", label="Predicted apogee")
    ax[2].axhline(target_agl, color="k", linestyle="--", label="Target")
    ax[2].set_ylabel("Apogee AGL (m)")
    ax[2].set_xlabel("Time (s)")
    ax[2].legend()

    for a in ax:
        a.grid(True, alpha=0.4)
    fig.suptitle("Airbrakes controller")
    fig.savefig(output_path, bbox_inches="tight")
    return fig

#-------------------------------------------------------------------------------------------------------- PARAMETERS
weather_data = 'c'          # c = custom (mean EuRoC week), e = ensemble, f = forecast (Open-Meteo, FORECAST_MODEL in atlas_model.py), i = ISA

# OPTIONS:
ballistic = False           # True = flight without parachutes
show_graph = False
print_info = True
export_mass_and_cg = False  # mass and CG over time as .csv in tools/mass_analysis/
#--------------------------------------------------------------------------------------------------------

env = model.build_environment(weather_data)
setting = model.nominal(model.load_parameters())
rocket_flight = model.simulate(setting, env, recovery=not ballistic)
Atlas = rocket_flight.rocket

print(f"Geometry {model.GEOMETRY}, aerodynamics {model.AERODYNAMICS}, motor {model.MOTOR}, "
      f"recovery {model.RECOVERY}, airbrakes {model.AIRBRAKES}" + (", ballistic" if ballistic else ""))
if print_info:
    rocket_flight.info()

# if activated, shows graphs
if show_graph:
    ## per mostrare tutto assieme
    #original_show = plt.show
    #plt.show = lambda *args, **kwargs: None   # blocca i show() interni a RocketPy

    Atlas.draw()
    Atlas.plots.total_mass()
    rocket_flight.plots.linear_kinematics_data()
    rocket_flight.plots.attitude_data()
    rocket_flight.plots.angular_kinematics_data()
    rocket_flight.plots.flight_path_angle_data()
    rocket_flight.plots.trajectory_3d()
    rocket_flight.plots.stability_and_control_data()
    rocket_flight.plots.aerodynamic_forces()
    rocket_flight.plots.rail_buttons_forces()

    #plt.show = original_show
    #plt.show()   # mostra tutte le figure insieme


# save trajectory, .kml can be open in google earth
OUTPUT_DIR = BASE_DIR / "simulation_output" / "reanalysis_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
rocket_flight.export_kml(
    file_name=str(OUTPUT_DIR / "trajectory.kml"),
    extrude=True,
    altitude_mode="relative_to_ground",
)

airbrakes_graph(rocket_flight, env, setting["target_apogee"], OUTPUT_DIR / "airbrakes.svg")
plt.show()

if export_mass_and_cg:
    # The CG position is measured from the nose tip
    mass_dir = BASE_DIR / "tools" / "mass_analysis"
    pd.DataFrame(Atlas.total_mass.source, columns=["time", "mass"]).to_csv(
        mass_dir / "mass" / "mass_time_rpy" / f"mass_time_rpy_{model.GEOMETRY}.csv", index=False)
    pd.DataFrame(Atlas.center_of_mass.source, columns=["time", "CG"]).to_csv(
        mass_dir / "CG" / "CG_rpy" / f"CG_rpy_{model.GEOMETRY}.csv", index=False)
