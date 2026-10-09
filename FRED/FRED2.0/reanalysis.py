"""
FRED2.0 reanalysis: one flight with every parameter at its nominal value (fred_model.py).

Saves the trajectory as .kml (open it in Google Earth) in simulation_output/reanalysis_output/.
"""
from pathlib import Path

import fred_model as model

BASE_DIR = Path(__file__).resolve().parent

#-------------------------------------------------------------------------------------------------------- PARAMETERS
weather_data = 'r'          # c = typical day of the climatological data at the hour of LAUNCH_DATE, e = ensemble,
                            # r = reanalysis, f = forecast, i = ISA, m = manual wind (MANUAL_WIND in fred_model.py)

# OPTIONS:
ballistic = False           # True = flight without parachute
show_graph = True
print_info = True
#--------------------------------------------------------------------------------------------------------

env = model.build_environment(weather_data)
setting = model.nominal(model.load_parameters())
rocket_flight = model.simulate(setting, env, recovery=not ballistic)
FRED = rocket_flight.rocket

print(f"Geometry {model.GEOMETRY}, aerodynamics {model.AERODYNAMICS}, motor {model.MOTOR}, "
      f"recovery {model.RECOVERY}, launch site {model.LAUNCH_SITE}" + (", ballistic" if ballistic else ""))
if print_info:
    rocket_flight.info()

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

from rocketpy.simulation import FlightDataExporter

# save trajectory, .kml can be open in google earth
OUTPUT_DIR = BASE_DIR / "simulation_output" / "reanalysis_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FlightDataExporter(rocket_flight).export_kml(
    file_name=str(OUTPUT_DIR / "trajectory.kml"),
    extrude=True,
    altitude_mode="relative_to_ground",
)
