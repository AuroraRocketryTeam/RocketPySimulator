"""
FRED2.0 model: the single definition of rocket, motor, recovery and launch site used by the
simulation scripts.

Choose the version of each part below. Every version is a folder in simulation_inputs/ holding a
CSV with the parameters (name, value, std, unit, note), where std is the standard deviation used by
the Monte Carlo simulations.

Typical use:
    import fred_model as model
    params = model.load_parameters()
    setting = model.nominal(params)             # or model.sample(params, rng) for a Monte Carlo run
    env = model.build_environment("m")
    flight = model.simulate(setting, env)
"""

from pathlib import Path

import pandas as pd

#-------------------------------------------------------------------------------------------------------- VERSIONS
GEOMETRY = "v0_lancio23maggio"                      # simulation_inputs/geometry_data/<version>/
AERODYNAMICS = "v0_lancio23maggio"                  # simulation_inputs/aerodynamic_data/<version>/
MOTOR = "SRAD/v0_lancio23maggio"                    # simulation_inputs/propulsion_data/<motor>/
RECOVERY = "v0_lancio23maggio"                      # simulation_inputs/recovery_data/<version>/
LAUNCH_SITE = "v0_lancio23maggio"                   # simulation_inputs/environment_data/<version>/
LAUNCH_DATE = (2026, 5, 23, 14)                     # (Year, Month, Day, Hour UTC); Italy in May is UTC + 2

# Multiplier of the drag curve, to add uncertainty to the aerodynamic data (mean, std)
DRAG_FACTOR = (1.0, 0.001)

# Manual wind (weather_data = "m"): speed on the ground (m/s) and heading (deg from north, where the
# wind goes: a wind from north has heading 180). The speed grows of 5% every 50 m up to 300 m.
MANUAL_WIND = (8.7, 315)
#--------------------------------------------------------------------------------------------------------

INPUTS = Path(__file__).resolve().parent / "simulation_inputs"

GEOMETRY_FILE = INPUTS / "geometry_data" / GEOMETRY / "geometry.csv"
DRAG_FILE = INPUTS / "aerodynamic_data" / AERODYNAMICS / "cd_mach.csv"
MOTOR_FILE = INPUTS / "propulsion_data" / MOTOR / "motor.csv"
THRUST_FILE = INPUTS / "propulsion_data" / MOTOR / "thrust_curve.csv"
RECOVERY_FILE = INPUTS / "recovery_data" / RECOVERY / "recovery.csv"
SITE_DIR = INPUTS / "environment_data" / LAUNCH_SITE
SITE_FILE = SITE_DIR / "launch_site.csv"


#-------------------------------------------------------------------------------------------------------- PARAMETERS
def read_csv(path):
    """{name: (value, std)} from one parameter file."""
    table = pd.read_csv(path, comment="#", skipinitialspace=True, dtype=str)
    incomplete = [row.name for row in table.itertuples(index=False) if "---" in (row.value, row.std)]
    if incomplete:
        raise ValueError(f"{path}: fields still to fill (---): {', '.join(incomplete)}")
    return {row.name: (float(row.value), float(row.std)) for row in table.itertuples(index=False)}


def load_parameters():
    """All the parameters of the chosen versions, as {name: (value, std)}."""
    params = {"drag_factor": DRAG_FACTOR}
    for path in [GEOMETRY_FILE, MOTOR_FILE, RECOVERY_FILE, SITE_FILE]:
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
        if min(setting["main_lag"], setting["electronics_lag"]) < 0:
            continue
        return setting
#--------------------------------------------------------------------------------------------------------


#-------------------------------------------------------------------------------------------------------- RECOVERY LOGIC
class RecoveryLogic:
    """Python representation of the on-board C code that opens the parachute.

    Main (the only parachute): apogee acknowledged after apogee_threshold s of continuous negative
    vertical velocity (on the rocket this comes from the IMU).
    A new object is needed for every flight.
    """

    def __init__(self, setting):
        self.sampling_rate = setting["sampling_rate"]
        self.apogee_threshold = setting["apogee_threshold"]
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

    def main_trigger(self, p, h, y):
        self.stopwatch += 1 / self.sampling_rate
        self.apogee_detected = self.check_apogee(y[5], self.stopwatch)
        return self.apogee_detected
#--------------------------------------------------------------------------------------------------------


#-------------------------------------------------------------------------------------------------------- MODEL
def build_environment(weather_data="m", date=LAUNCH_DATE):
    """Launch site with the chosen weather data:
    e = ensemble of the .nc file in the site folder (select the member with env.select_ensemble_member);
        the date must be inside the file (Villafranca: 5-11 May, 2020-2026)
    f = GFS forecast (date in the future)
    i = International Standard Atmosphere
    m = ISA with the manual wind of MANUAL_WIND (worst case against houses and spectators)
    """
    import math

    from rocketpy import Environment

    site = nominal(read_csv(SITE_FILE))
    env = Environment(
        date=date,
        latitude=site["latitude"],
        longitude=site["longitude"],
        elevation=site["elevation"],
        max_expected_height=1500,
    )
    if weather_data == "e":
        env.set_atmospheric_model(
            type="Ensemble",
            file=str(next(SITE_DIR.glob("*.nc"))),
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
    elif weather_data == "m":
        speed, heading = MANUAL_WIND
        heights = range(0, 301, 50)
        east, north = math.sin(math.radians(heading)), math.cos(math.radians(heading))
        env.set_atmospheric_model(
            type="custom_atmosphere",
            wind_u=[(h, speed * (1 + h / 1000) * east) for h in heights],
            wind_v=[(h, speed * (1 + h / 1000) * north) for h in heights],
        )
    elif weather_data != "i":
        raise ValueError(f"Unknown weather data '{weather_data}' (use e, f, i or m)")
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


def build_rocket(s, logic=None, main_lag=None, recovery=True):
    """FRED2.0 with motor, aerodynamic surfaces and parachute.

    main_lag: time from the trigger to the fully inflated parachute; by default the lag of the
    recovery file plus the electronics lag. recovery=False gives a ballistic flight.
    """
    from rocketpy import Rocket

    fred = Rocket(
        radius=s["radius"],
        mass=s["rocket_dry_mass"],
        inertia=(s["rocket_dry_inertia_11"], s["rocket_dry_inertia_11"], s["rocket_dry_inertia_33"]),
        power_off_drag=str(DRAG_FILE),
        power_on_drag=str(DRAG_FILE),
        center_of_mass_without_motor=s["center_of_mass_without_motor"],
        coordinate_system_orientation="nose_to_tail",
    )
    fred.set_rail_buttons(
        upper_button_position=s["upper_button_position"],
        lower_button_position=s["lower_button_position"],
        angular_position=s["button_angular_position"],
    )
    fred.add_motor(build_motor(s), position=s["motor_position"])
    fred.power_off_drag *= s["drag_factor"]
    fred.power_on_drag *= s["drag_factor"]
    fred.add_nose(length=s["nose_length"], kind="elliptical", position=s["nose_position"])
    fred.add_trapezoidal_fins(
        n=round(s["fin_number"]),
        span=s["fin_span"],
        root_chord=s["fin_root_chord"],
        tip_chord=s["fin_tip_chord"],
        position=s["fin_position"],
        sweep_angle=s["fin_sweep_angle"],
        cant_angle=0,
    )
    fred.add_tail(
        top_radius=s["tail_top_radius"],
        bottom_radius=s["tail_bottom_radius"],
        length=s["tail_length"],
        position=s["tail_position"],
    )

    if recovery:
        logic = logic or RecoveryLogic(s)
        fred.add_parachute(
            "Main", cd_s=s["cd_s_main"], trigger=logic.main_trigger, sampling_rate=s["sampling_rate"],
            lag=s["main_lag"] + s["electronics_lag"] if main_lag is None else main_lag,
            noise=(s["noise_mean"], s["noise_std"], s["noise_time_correlation"]),
        )
    return fred


def simulate(s, env, recovery=True, **rocket_options):
    """Build FRED2.0 and fly it from the launch rail."""
    from rocketpy import Flight

    return Flight(
        rocket=build_rocket(s, recovery=recovery, **rocket_options),
        environment=env,
        rail_length=s["rail_length"],
        inclination=s["inclination"],
        heading=s["heading"],
        max_time=1200,
    )


def max_acceleration_power_on(flight, skip=1e-4):
    """Maximum acceleration with the motor on, without the last `skip` seconds before burnout.

    RocketPy includes in the acceleration the second derivative of the center of mass position,
    computed by finite differences over 1e-6 s. If the thrust ends abruptly, that derivative blows
    up at burnout when the integrator puts a point right there, and flight.max_acceleration_power_on
    is completely off scale. A short tail-off at the end of the thrust curve (25 ms is enough)
    avoids the numerical spike; this function stays as a safety net for curves with a sharp cut.
    """
    t, a = flight.acceleration.source[:, 0], flight.acceleration.source[:, 1]
    return a[t < flight.rocket.motor.burn_out_time - skip].max()
#--------------------------------------------------------------------------------------------------------
