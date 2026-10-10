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

import numpy as np
import pandas as pd

#-------------------------------------------------------------------------------------------------------- VERSIONS
GEOMETRY = "v1.0"                      # simulation_inputs/geometry_data/<version>/
AERODYNAMICS = "v0_lancio23maggio"                  # simulation_inputs/aerodynamic_data/<version>/
MOTOR = "SRAD/8mm"                                  # simulation_inputs/propulsion_data/<motor>/
RECOVERY = "v0_lancio23maggio"                      # simulation_inputs/recovery_data/<version>/
LAUNCH_SITE = "Villafranca"                         # simulation_inputs/environment_data/<site>/
LAUNCH_DATE = (2025, 10, 23, 14)                    # (Year, Month, Day, Hour UTC); Italy in May is UTC + 2

# Multiplier of the drag curve, to add uncertainty to the aerodynamic data (mean, std)
DRAG_FACTOR = (1.0, 0.001)

# Manual wind (weather_data = "m"): speed on the ground (m/s) and heading (deg from north, where the
# wind goes: a wind from north has heading 180). The speed grows of 5% every 50 m up to 300 m.
MANUAL_WIND = (8.7, 315)

# Climatological weather (weather_data = "c"): ERA5 near-ground weather of the launch site,
# simulation_inputs/environment_data/<site>/<site>_surface_<CLIMATE>.csv, and the UTC hours to use
CLIMATE = "20to30oct2010to2025"
CLIMATE_HOURS = range(12, 19)
#--------------------------------------------------------------------------------------------------------

# Longest integration step (s), shorter than any burn: see simulate()
MAX_TIME_STEP = 0.1

INPUTS = Path(__file__).resolve().parent / "simulation_inputs"

GEOMETRY_FILE = INPUTS / "geometry_data" / GEOMETRY / "geometry.csv"
DRAG_FILE = INPUTS / "aerodynamic_data" / AERODYNAMICS / "cd_mach.csv"
MOTOR_FILE = INPUTS / "propulsion_data" / MOTOR / "motor.csv"
THRUST_FILE = INPUTS / "propulsion_data" / MOTOR / "thrust_curve.csv"
RECOVERY_FILE = INPUTS / "recovery_data" / RECOVERY / "recovery.csv"
SITE_DIR = INPUTS / "environment_data" / LAUNCH_SITE
SITE_FILE = SITE_DIR / "launch_site.csv"
CLIMATE_FILE = SITE_DIR / f"{LAUNCH_SITE}_surface_{CLIMATE}.csv"


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
def _nutation(e1, e2):
    """RocketPy's quaternions_to_nutation with the argument of arcsin clipped to 1.

    Under the parachute the rocket hangs upside down (nutation 180 deg): e1^2 + e2^2 is 1, and the
    integration error on the quaternion (1e-6) makes it slightly larger, so arcsin gives NaN and the
    spline of flight.theta fails (comparison.euler_angles()). Only the post-processed Euler angle is
    affected, not the integrated state (position, velocity, attitude)."""
    return (180 / np.pi) * 2 * np.arcsin(-np.clip((e1**2 + e2**2) ** 0.5, 0, 1))


def _patch_rocketpy():
    import rocketpy.simulation.flight as flight_module

    flight_module.quaternions_to_nutation = _nutation


# ERA5 netCDF files of the Copernicus CDS: the built-in ECMWF dictionary of RocketPy can't read the new format
ERA5_DICTIONARY = {
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


def weather_file(product, date):
    """The .nc of the launch site with `product` (ensemble or reanalysis) in its name that holds `date`.

    RocketPy silently takes the nearest time in the file, so a date outside every file is an error."""
    from datetime import datetime

    import netCDF4

    target = datetime(*date)
    available = []
    for path in sorted(SITE_DIR.glob(f"*{product}*.nc")):
        with netCDF4.Dataset(path) as data:
            times = data.variables["valid_time"]
            dates = netCDF4.num2date(times[:], times.units, getattr(times, "calendar", "standard"),
                                     only_use_cftime_datetimes=False, only_use_python_datetimes=True)
        if target in dates:
            return path
        available.append(f"{path.name} ({min(dates)} - {max(dates)})")
    raise ValueError(f"No {product} file of {LAUNCH_SITE} holds {target} (hours in UTC): "
                     + ("; ".join(available) or "no file"))


def load_climate():
    """Hourly ERA5 near-ground weather at the launch point (wind at 10 m and 100 m, temperature at 2 m,
    surface pressure), only the CLIMATE_HOURS. Written by tools/environment/surface_wind/surface_wind.py."""
    table = pd.read_csv(CLIMATE_FILE, parse_dates=["time"], index_col="time")
    return table[table.index.hour.isin(list(CLIMATE_HOURS))]


def typical_climate(hour):
    """One row like the ones of load_climate() for a typical day at `hour` (UTC): mean speed at 10 m and
    100 m with the direction of the mean wind vector (a plain mean of u and v would lower the speed,
    because the directions of the different days cancel out), mean temperature and pressure."""
    rows = load_climate()
    rows = rows[rows.index.hour == hour]
    if rows.empty:
        raise ValueError(f"No climatological data at {hour} UTC in {CLIMATE_FILE.name} (hours {list(CLIMATE_HOURS)})")
    typical = {"t2m": rows["t2m"].mean(), "sp": rows["sp"].mean()}
    for h in ("10", "100"):
        speed = np.hypot(rows[f"u{h}"], rows[f"v{h}"]).mean()
        angle = np.arctan2(rows[f"u{h}"].mean(), rows[f"v{h}"].mean())
        typical[f"u{h}"], typical[f"v{h}"] = speed * np.sin(angle), speed * np.cos(angle)
    return pd.Series(typical)


def surface_wind(row, heights):
    """Wind (u, v) at `heights` (m above the ground) from the ERA5 wind at 10 m and 100 m of one row of
    load_climate(). Speed: power law through the two values between 10 and 100 m; below 10 m (down to
    1 m) and above 100 m (up to 200 m, constant higher) the same law with the exponent kept between 0 and
    0.6. Direction: from the one at 10 m to the one at 100 m (on the log of the height), constant outside."""
    h = np.clip(np.asarray(heights, dtype=float), 1, 200)
    s10, s100 = max(np.hypot(row.u10, row.v10), 0.01), max(np.hypot(row.u100, row.v100), 0.01)
    exponent = np.log(s100 / s10) / np.log(10)
    outside = np.clip(exponent, 0, 0.6)
    speed = np.where(h < 10, s10 * (h / 10) ** outside,
                     np.where(h > 100, s100 * (h / 100) ** outside, s10 * (h / 10) ** exponent))
    to10, to100 = np.arctan2(row.u10, row.v10), np.arctan2(row.u100, row.v100)   # where the wind goes
    turn = (to100 - to10 + np.pi) % (2 * np.pi) - np.pi
    angle = to10 + turn * np.clip(np.log10(h / 10), 0, 1)
    return np.array([speed * np.sin(angle), speed * np.cos(angle)])


def build_environment(weather_data="m", date=LAUNCH_DATE, climate=None):
    """Launch site with the chosen weather data:
    c = climatological near-ground weather (load_climate): the row `climate` (a random one for every
        Monte Carlo run) or, if None, the typical day at the hour of `date` (typical_climate)
    e = ERA5 ensemble (10 members, every 3 hours; select the member with env.select_ensemble_member)
    r = ERA5 reanalysis (one member, every hour)
    f = GFS forecast (date in the future)
    i = International Standard Atmosphere
    m = ISA with the manual wind of MANUAL_WIND (worst case against houses and spectators)
    With e and r the date must be one of the times of a file in the site folder (see weather_file).
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
        env.set_atmospheric_model(type="Ensemble", file=str(weather_file("ensemble", date)),
                                  dictionary={"ensemble": "number", **ERA5_DICTIONARY})
    elif weather_data == "r":
        env.set_atmospheric_model(type="Reanalysis", file=str(weather_file("reanalysis", date)),
                                  dictionary=ERA5_DICTIONARY)
    elif weather_data == "f":
        env.set_atmospheric_model(type="Forecast", file="GFS")
    elif weather_data == "m":
        speed, heading = MANUAL_WIND
        heights = range(0, 301, 50)                     # above the ground; RocketPy wants them above sea level
        east, north = math.sin(math.radians(heading)), math.cos(math.radians(heading))
        env.set_atmospheric_model(
            type="custom_atmosphere",
            wind_u=[(site["elevation"] + h, speed * (1 + h / 1000) * east) for h in heights],
            wind_v=[(site["elevation"] + h, speed * (1 + h / 1000) * north) for h in heights],
        )
    elif weather_data == "c":
        row = typical_climate(date[3]) if climate is None else climate
        heights = np.array([0, 2, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 1000, 1500])
        u, v = surface_wind(row, heights)
        asl = site["elevation"] + heights
        # Temperature from the one at 2 m with the standard lapse rate, pressure from the surface one
        temperature = row.t2m - 0.0065 * (heights - 2)
        pressure = row.sp * (1 - 0.0065 * heights / row.t2m) ** 5.2559
        env.set_atmospheric_model(
            type="custom_atmosphere",
            pressure=list(zip(asl, pressure)),
            temperature=list(zip(asl, temperature)),
            wind_u=list(zip(asl, u)),
            wind_v=list(zip(asl, v)),
        )
    elif weather_data != "i":
        raise ValueError(f"Unknown weather data '{weather_data}' (use c, e, r, f, i or m)")
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

    _patch_rocketpy()
    return Flight(
        rocket=build_rocket(s, recovery=recovery, **rocket_options),
        environment=env,
        rail_length=s["rail_length"],
        inclination=s["inclination"],
        heading=s["heading"],
        max_time=1200,
        # At ignition the thrust is below the weight: on the rail every derivative is zero and the
        # integrator tries a first step of 1.2 s. With a burn shorter than that (8 mm nozzle, 0.68 s)
        # the step lands after burnout, is accepted and the rocket never leaves the rail.
        max_time_step=MAX_TIME_STEP,
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
