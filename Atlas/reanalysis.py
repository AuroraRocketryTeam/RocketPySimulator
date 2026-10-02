"""
Atlas reanalysis: one flight with every parameter at its nominal value (atlas_model.py).

Saves the trajectory as .kml (open it in Google Earth) in reanalysis_output/ and, if asked, the
mass and center of mass over time for tools/mass_analysis/.
"""
from pathlib import Path

import pandas as pd

import atlas_model as model

BASE_DIR = Path(__file__).resolve().parent

#-------------------------------------------------------------------------------------------------------- PARAMETERS
weather_data = 'c'          # c = custom (mean EuRoC week), e = ensemble, f = forecast, i = ISA

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

# save trajectory, .kml can be open in google earth
(BASE_DIR / "reanalysis_output").mkdir(exist_ok=True)
rocket_flight.export_kml(
    file_name=str(BASE_DIR / "reanalysis_output" / "trajectory.kml"),
    extrude=True,
    altitude_mode="relative_to_ground",
)

if export_mass_and_cg:
    # The CG position is measured from the nose tip
    mass_dir = BASE_DIR / "tools" / "mass_analysis"
    pd.DataFrame(Atlas.total_mass.source, columns=["time", "mass"]).to_csv(
        mass_dir / "mass" / "mass_time_rpy" / f"mass_time_rpy_{model.GEOMETRY}.csv", index=False)
    pd.DataFrame(Atlas.center_of_mass.source, columns=["time", "CG"]).to_csv(
        mass_dir / "CG" / "CG_rpy" / f"CG_rpy_{model.GEOMETRY}.csv", index=False)
