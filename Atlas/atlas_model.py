"""
Atlas model: the single definition of rocket, motor, recovery, airbrakes and launch site used by
montecarlo.py, reanalysis.py and parachute_study.py.

Choose the version of each part below. Every version is a folder in simulation_inputs/ holding a
CSV with the parameters (name, value, std, unit, note), where std is the standard deviation used by
the Monte Carlo simulations.

Typical use:
    import atlas_model as model
    params = model.load_parameters()
    setting = model.nominal(params)             # or model.sample(params, rng) for a Monte Carlo run
    env = model.build_environment("c")
    flight = model.simulate(setting, env)
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

#-------------------------------------------------------------------------------------------------------- VERSIONS
GEOMETRY = "v1.4"                                   # simulation_inputs/geometry_data/<version>/
AERODYNAMICS = "v1.4/CD_Mach_Test_Atlas_v_1.2_SDRAD_cd_mach.csv"         # simulation_inputs/aerodynamic_data/rocket_body/<file>
MOTOR = "SRAD/v1.0"             # simulation_inputs/propulsion_data/<motor>/
RECOVERY = "v1.0"                                   # simulation_inputs/recovery_data/<version>/
AIRBRAKES = None                                    # None = no airbrakes, or "v1.0"
LAUNCH_SITE = "santa_margarida"                     # simulation_inputs/environment_data/<site>/
LAUNCH_DATE = (2024, 10, 11, 12)                    # (Year, Month, Day, Hour UTC)

# Multiplier of the drag curve, to add uncertainty to the aerodynamic data (mean, std)
DRAG_FACTOR = (1.0, 0.001)
#--------------------------------------------------------------------------------------------------------

INPUTS = Path(__file__).resolve().parent / "simulation_inputs"

GEOMETRY_FILE = INPUTS / "geometry_data" / GEOMETRY / "geometry.csv"
DRAG_FILE = INPUTS / "aerodynamic_data" / "rocket_body" / AERODYNAMICS
MOTOR_FILE = INPUTS / "propulsion_data" / MOTOR / "motor.csv"
THRUST_FILE = INPUTS / "propulsion_data" / MOTOR / "thrust_curve.csv"
RECOVERY_FILE = INPUTS / "recovery_data" / RECOVERY / "recovery.csv"
SITE_DIR = INPUTS / "environment_data" / LAUNCH_SITE
SITE_FILE = SITE_DIR / "launch_site.csv"
AIRBRAKES_DIR = INPUTS / "aerodynamic_data" / "airbrakes" / AIRBRAKES if AIRBRAKES else None


#-------------------------------------------------------------------------------------------------------- PARAMETERS
def read_csv(path):
    """{name: (value, std)} from one parameter file."""
    table = pd.read_csv(path, comment="#", skipinitialspace=True)
    return {row.name: (float(row.value), float(row.std)) for row in table.itertuples(index=False)}


def load_parameters():
    """All the parameters of the chosen versions, as {name: (value, std)}."""
    files = [GEOMETRY_FILE, MOTOR_FILE, RECOVERY_FILE, SITE_FILE]
    if AIRBRAKES_DIR:
        files.append(AIRBRAKES_DIR / "airbrakes.csv")
    params = {"drag_factor": DRAG_FACTOR}
    for path in files:
        for name, value in read_csv(path).items():
            if name in params:
                raise ValueError(f"Parameter {name} defined twice ({path})")
            params[name] = value
    return params


def nominal(params):
    """One setting with every parameter at its nominal value."""
    return {name: value for name, (value, _) in params.items()}


def sample(params, rng):
    """One random setting for a Monte Carlo run (normal distribution around each nominal value)."""
    while True:
        setting = {name: rng.normal(value, std) for name, (value, std) in params.items()}
        # Skip unrealistic draws from the tails of the normal curves
        if min(setting["drogue_lag"], setting["main_lag"], setting["electronics_lag"]) < 0:
            continue
        return setting
#--------------------------------------------------------------------------------------------------------


#-------------------------------------------------------------------------------------------------------- RECOVERY LOGIC
class RecoveryLogic:
    """Python representation of the on-board C code that opens the parachutes.

    Drogue: apogee acknowledged after apogee_threshold s of continuous negative vertical velocity
    (on the rocket this comes from the IMU).
    Main: apogee acknowledged and altitude <= main_altitude (on the rocket, Kalman-filtered barometer).
    A new object is needed for every flight.
    """

    def __init__(self, setting):
        self.sampling_rate = setting["sampling_rate"]
        self.apogee_threshold = setting["apogee_threshold"]
        self.main_altitude = setting["main_altitude"]
        self.last_negative_time = None
        self.apogee_detected = False
        # Advances of 1/sampling_rate at every call, as a measure of in-flight time
        self.stopwatch = 0.0

    def check_apogee(self, vertical_velocity, current_time):
        if self.apogee_detected:
            return True
        if vertical_velocity < 0:
            if self.last_negative_time is None:
                self.last_negative_time = current_time
                return False
            return (current_time - self.last_negative_time) >= self.apogee_threshold
        self.last_negative_time = None
        return False

    def drogue_trigger(self, p, h, y):
        self.stopwatch += 1 / self.sampling_rate
        self.apogee_detected = self.check_apogee(y[5], self.stopwatch)
        return self.apogee_detected

    def main_trigger(self, p, h, y):
        return self.apogee_detected and h <= self.main_altitude
#--------------------------------------------------------------------------------------------------------


#-------------------------------------------------------------------------------------------------------- MODEL
def build_environment(weather_data="c", date=LAUNCH_DATE):
    """Launch site with the chosen weather data:
    c = custom atmosphere, mean of the EuRoC week (10-15 October, 2005-2024) at the chosen hour
    e = ensemble forecast of the EuRoC week (select the member with env.select_ensemble_member)
    f = GFS forecast (date in the future)
    i = International Standard Atmosphere
    """
    from rocketpy import Environment

    site = nominal(read_csv(SITE_FILE))
    env = Environment(
        date=date,
        latitude=site["latitude"],
        longitude=site["longitude"],
        elevation=site["elevation"],
        max_expected_height=5000,
    )
    if weather_data == "c":
        # Profiles generated with RocketPy's EnvironmentAnalysis from the Copernicus NetCDF4 data
        with open(SITE_DIR / "mean_environment_values.json") as f:
            data = json.load(f)
        hour = str(env.date[3])
        env.set_atmospheric_model(
            type="custom_atmosphere",
            pressure=data["atmospheric_model_pressure_profile"][hour],
            temperature=data["atmospheric_model_temperature_profile"][hour],
            wind_u=data["atmospheric_model_wind_velocity_x_profile"][hour],
            wind_v=data["atmospheric_model_wind_velocity_y_profile"][hour],
        )
    elif weather_data == "e":
        env.set_atmospheric_model(
            type="Ensemble",
            file=str(SITE_DIR / "SantaMargarida_Ensemble_09to16oct2010to2024.nc"),
            # The built-in ECMWF dictionary of RocketPy can't read the new NetCDF4 format
            dictionary={
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
    elif weather_data == "f":
        env.set_atmospheric_model(type="Forecast", file="GFS")
    elif weather_data != "i":
        raise ValueError(f"Unknown weather data '{weather_data}' (use c, e, f or i)")
    return env


def build_motor(s):
    from rocketpy import SolidMotor

    return SolidMotor(
        thrust_source=str(THRUST_FILE),
        burn_time=s["burn_time"],
        reshape_thrust_curve=(s["burn_time"], s["impulse"]),
        interpolation_method="linear",
        nozzle_radius=s["nozzle_radius"],
        throat_radius=s["throat_radius"],
        grain_number=round(s["grain_number"]),
        grain_separation=s["grain_separation"],
        grain_density=s["grain_density"],
        grain_outer_radius=s["grain_outer_radius"],
        grain_initial_inner_radius=s["grain_initial_inner_radius"],
        grain_initial_height=s["grain_initial_height"],
        nozzle_position=s["nozzle_position"],
        grains_center_of_mass_position=s["grains_center_of_mass_position"],
        dry_mass=s["motor_dry_mass"],
        dry_inertia=(s["motor_inertia_11"], s["motor_inertia_11"], s["motor_inertia_33"]),
        center_of_dry_mass_position=s["motor_dry_mass_position"],
        coordinate_system_orientation="nozzle_to_combustion_chamber",
    )


def airbrake_controller(env, motor, s):
    """Controller of the airbrakes: closed during the burn and below deployment_altitude (ASL),
    open at deployment_level above it."""

    def controller(time, sampling_rate, state, state_history, observed_variables, air_brakes):
        altitude_asl = state[2]
        if time < motor.burn_out_time:
            return None
        air_brakes.deployment_level = s["deployment_level"] if altitude_asl >= s["deployment_altitude"] else 0
        free_stream_speed = np.sqrt(
            (env.wind_velocity_x(altitude_asl) - state[3]) ** 2
            + (env.wind_velocity_y(altitude_asl) - state[4]) ** 2
            + state[5] ** 2
        )
        mach = free_stream_speed / env.speed_of_sound(altitude_asl)
        # Saved in observed_variables
        return time, air_brakes.deployment_level, air_brakes.drag_coefficient(air_brakes.deployment_level, mach)

    return controller


def build_rocket(s, env=None, logic=None, drogue_lag=None, main_lag=None, recovery=True):
    """Atlas with motor, aerodynamic surfaces, parachutes and (optionally) airbrakes.

    drogue_lag / main_lag: time from the trigger to the fully inflated parachute; by default the
    lags of the recovery file plus the electronics lag. recovery=False gives a ballistic flight.
    The airbrakes are added when AIRBRAKES is set; their controller needs env.
    """
    from rocketpy import Rocket

    motor = build_motor(s)
    atlas = Rocket(
        radius=s["radius"],
        mass=s["rocket_dry_mass"],
        inertia=(s["rocket_dry_inertia_11"], s["rocket_dry_inertia_11"], s["rocket_dry_inertia_33"]),
        power_off_drag=str(DRAG_FILE),
        power_on_drag=str(DRAG_FILE),
        center_of_mass_without_motor=s["center_of_mass_without_motor"],
        coordinate_system_orientation="nose_to_tail",
    )
    atlas.set_rail_buttons(
        upper_button_position=s["upper_button_position"],
        lower_button_position=s["lower_button_position"],
        angular_position=s["button_angular_position"],
    )
    atlas.add_motor(motor, position=s["motor_position"])
    atlas.power_off_drag *= s["drag_factor"]
    atlas.power_on_drag *= s["drag_factor"]
    atlas.add_nose(length=s["nose_length"], kind="lvhaack", position=s["nose_position"])
    atlas.add_trapezoidal_fins(
        n=round(s["fin_number"]),
        span=s["fin_span"],
        root_chord=s["fin_root_chord"],
        tip_chord=s["fin_tip_chord"],
        position=s["fin_position"],
        sweep_angle=s["fin_sweep_angle"],
        cant_angle=0,
    )
    atlas.add_tail(
        top_radius=s["tail_top_radius"],
        bottom_radius=s["tail_bottom_radius"],
        length=s["tail_length"],
        position=s["tail_position"],
    )

    if recovery:
        logic = logic or RecoveryLogic(s)
        noise = (s["noise_mean"], s["noise_std"], s["noise_time_correlation"])
        atlas.add_parachute(
            "Drogue", cd_s=s["cd_s_drogue"], trigger=logic.drogue_trigger, sampling_rate=s["sampling_rate"],
            lag=s["drogue_lag"] + s["electronics_lag"] if drogue_lag is None else drogue_lag, noise=noise,
        )
        atlas.add_parachute(
            "Main", cd_s=s["cd_s_main"], trigger=logic.main_trigger, sampling_rate=s["sampling_rate"],
            lag=s["main_lag"] + s["electronics_lag"] if main_lag is None else main_lag, noise=noise,
        )

    if AIRBRAKES_DIR:
        if env is None:
            raise ValueError("The airbrake controller needs the environment: build_rocket(s, env=...)")
        atlas.add_air_brakes(
            drag_coefficient_curve=str(AIRBRAKES_DIR / "cd_mach.csv"),
            controller_function=airbrake_controller(env, motor, s),
            sampling_rate=s["airbrake_sampling_rate"],
            reference_area=s["reference_area"],
            clamp=False,
            initial_observed_variables=[0, 0, 0],
            override_rocket_drag=False,
            name="Air Brakes",
        )
    return atlas


def simulate(s, env, recovery=True, **rocket_options):
    """Build Atlas and fly it from the launch rail."""
    from rocketpy import Flight

    rocket = build_rocket(s, env=env, recovery=recovery, **rocket_options)
    return Flight(
        rocket=rocket,
        environment=env,
        rail_length=s["rail_length"],
        inclination=s["inclination"],
        heading=s["heading"],
        # With the airbrakes the controller needs every integration step
        time_overshoot=not AIRBRAKES_DIR,
        max_time=1200,
    )
#--------------------------------------------------------------------------------------------------------
