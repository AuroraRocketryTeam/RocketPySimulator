"""
Atlas parachute study: dry mass x drogue opening delay.

Monte Carlo sweep of the Atlas flight (same model as Atlas_v1.0.py) over the rocket dry mass
(everything that does not burn, motor hardware included) and, depending on the campaign:
- drogue: time between apogee and drogue full inflation (main delay dispersed around 4 s)
- main: time between the 450 m AGL crossing and main full inflation (drogue delay fixed)

For each flight it extracts ascent data, the drogue/main opening loads computed with the
RocketPy parachute model and the descent velocities, then writes runs_<campaign>.csv, summary
tables and plots into montecarlo_output/parachute_study/.

Usage (from the repo root, no GUI needed):
    MPLBACKEND=Agg .venv/bin/python Atlas/Atlas_v1.0/parachute_study.py --campaign drogue --n-sims 100
    MPLBACKEND=Agg .venv/bin/python Atlas/Atlas_v1.0/parachute_study.py --campaign main --n-sims 100
    MPLBACKEND=Agg .venv/bin/python Atlas/Atlas_v1.0/parachute_study.py --analyze-only
"""

import argparse
import csv
import json
import multiprocessing as mp
import os
import pickle
import time
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent

#-------------------------------------------------------------------------------------------------------- PARAMETERS
# Launch site and date (same as Atlas_v1.0.py)
LATITUDE = 39.389700
LONGITUDE = -8.288964
ELEVATION = 160.0
DATE_OF_LAUNCH = (2024, 10, 11, 12)          # (Year, Month, Day, Hour UTC)

# Drag curves (same case as Atlas_v1.0.py)
DRAG_CASE = "CD_Test_45_square"

# Cesaroni Pro75 9977M2245-P: loaded 8182 g, burnout 2873 g -> 5309 g expelled.
# The grains defined below weigh exactly this much, and the motor dry mass is ~0,
# so rocket_dry_mass is everything that does not burn (motor hardware included).
PROPELLANT_MASS = 5.309

# Reference dry mass and inertias of Atlas_v1.0.py, used to scale inertias with mass
REFERENCE_DRY_MASS = 26.470
REFERENCE_INERTIA_11 = (16.305, 0.187)
REFERENCE_INERTIA_33 = (0.087, 0.00122)

# Recovery logic
SAMPLING_RATE = 105             # Hz, recovery algorithm sampling rate
APOGEE_THRESHOLD = 0.1          # s of continuous descent before apogee is acknowledged
MAIN_DEPLOY_ALTITUDE = 450.0    # m AGL

# Rocketman standard chutes: 4 shroud lines, 1/4" 250 lb (3 ft) and 3/8" 550 lb (8-16 ft)
LBF = 4.44822
DROGUE_LINES_CAPACITY = 4 * 250 * LBF
MAIN_LINES_CAPACITY = 4 * 550 * LBF

# EuRoC requirements (RQT-0360, RQT-0380)
EUROC_DROGUE_RANGE = (23.0, 46.0)
EUROC_MAIN_MAX = 9.0

# A descent is "steady" once the relative speed is within this fraction of the local terminal velocity
STEADY_TOLERANCE = 0.01

CD_S_DROGUE = 0.97 * 0.6567     # rocketman 3ft
CD_S_MAIN = 0.97 * 14.3013      # rocketman 14ft

analysis_parameters = {
    # === Mass Details === (rocket_dry_mass mean and inertias are overridden per case)
    "rocket_dry_mass": (REFERENCE_DRY_MASS, 0.3),
    "motor_dry_mass": (0.0001, 0.0001),
    "motor_inertia_11": (0, 0),
    "motor_inertia_33": (0.0, 0.0),
    "motor_dry_mass_position": (0.0, 0.001),

    # === Propulsion Details ===
    "impulse": (9977, 5),
    "burn_time": (4.3, 0.1),
    "nozzle_radius": (29 / 1000, 0.5 / 1000),
    "throat_radius": (20 / 1000, 0.5 / 1000),
    "grain_separation": (3 / 1000, 0.01 / 1000),
    "grain_density": (1876.3, 5),
    "grain_outer_radius": (35.9 / 1000, 0.0001),
    "grain_initial_inner_radius": (18.10 / 1000, 0.0001),
    "grain_initial_height": (156.17 / 1000, 0.0001),

    # === Aerodynamic Details ===
    "radius": (75 / 1000, 0.001),
    "nozzle_position": (0, 0.0001),
    "grains_center_of_mass_position": (0.5125, 0.01),
    "power_off_drag_corr": (1.0, 0.001),
    "power_on_drag_corr": (1.0, 0.001),
    "nose_length": (0.60, 0.001),
    "tail_position": (2.990, 0.001),
    "nose_position": (0, 0),
    "fin_span": (0.145, 0.0005),
    "fin_root_chord": (0.20, 0.0005),
    "fin_tip_chord": (0.10, 0.0005),
    "fin_position": (2.99, 0.005),
    "fin_sweep_angle": (45.1, 0.005),
    "tail_length": (0.326, 0.001),
    "tail_bottom_radius": (0.045, 0.001),
    "tail_top_radius": (0.075, 0.001),

    # === Launch Details ===
    "inclination": (84, 0.5),
    "heading": (145, 1),
    "rail_length": (12, 0.005),

    # === Parachute Details === (5% uncertainty on the manufacturer Cd = 0.97)
    "cd_s_drogue": (CD_S_DROGUE, 0.05 * CD_S_DROGUE),
    "cd_s_main": (CD_S_MAIN, 0.05 * CD_S_MAIN),
    # Software decision -> electric ejection impulse (s)
    "t_sw_drogue": (1.0, 0.15),
    "t_sw_main": (1.0, 0.15),
    # Electric ejection impulse -> parachute fully inflated (s)
    "t_infl_drogue": (3.0, 0.5),
    "t_infl_main": (3.0, 0.5),

    # === Rail buttons Details ===
    "upper_button_y": (0.57, 0.005),
    "lower_button_y": (2.14, 0.005),
    "angular_button": (0, 0.01),

    # === Barometer noise ===
    "noise_mean": (0, 0.001),
    "noise_p_stdev": (6.5, 0.01),
    "noise_p_tc": (0.3, 0.01),
}

DEFAULT_MASSES = "20,22.5,25,27.5,30"
DEFAULT_DELAYS = "3,5,7,9,11"
DEFAULT_MAIN_DELAYS = "0.75,1.5,2.25,3,3.75"
DEFAULT_DROGUE_DELAY = 4.0
DEFAULT_OUTPUT = BASE_DIR / "montecarlo_output" / "parachute_study"
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- SAMPLING
def sample_setting(rng, dry_mass):
    """Draw one flight setting, with the rocket dry mass centred on dry_mass."""
    parameters = dict(analysis_parameters)
    mass_ratio = dry_mass / REFERENCE_DRY_MASS
    parameters["rocket_dry_mass"] = (dry_mass, analysis_parameters["rocket_dry_mass"][1])
    parameters["rocket_dry_inertia_11"] = tuple(v * mass_ratio for v in REFERENCE_INERTIA_11)
    parameters["rocket_dry_inertia_33"] = tuple(v * mass_ratio for v in REFERENCE_INERTIA_33)

    while True:
        setting = {key: rng.normal(*value) for key, value in parameters.items()}
        # Skip unrealistic draws from the tails of the normal curves
        if min(setting["t_sw_drogue"], setting["t_sw_main"]) <= 0:
            continue
        if min(setting["t_infl_drogue"], setting["t_infl_main"]) < 1.5:
            continue
        return setting
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- RECOVERY LOGIC
class RecoveryLogic:
    """Python representation of the on-board C code (same algorithm as Atlas_v1.0.py).

    Drogue: apogee acknowledged after APOGEE_THRESHOLD s of continuous negative vertical velocity.
    Main: apogee acknowledged and barometric altitude <= MAIN_DEPLOY_ALTITUDE.
    """

    def __init__(self):
        self.last_negative_time = None
        self.apogee_detected = False
        # Advances of 1/SAMPLING_RATE at every call, as a measure of in-flight time
        self.stopwatch = 0.0

    def check_apogee(self, vertical_velocity, current_time):
        if self.apogee_detected:
            return True
        if vertical_velocity < 0:
            if self.last_negative_time is None:
                self.last_negative_time = current_time
                return False
            return (current_time - self.last_negative_time) >= APOGEE_THRESHOLD
        self.last_negative_time = None
        return False

    def drogue_trigger(self, p, h, y):
        self.stopwatch += 1 / SAMPLING_RATE
        self.apogee_detected = self.check_apogee(y[5], self.stopwatch)
        return self.apogee_detected

    def main_trigger(self, p, h, y):
        return self.apogee_detected and h <= MAIN_DEPLOY_ALTITUDE
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- MODEL
def build_environment(weather_data):
    from rocketpy import Environment

    env = Environment(
        date=DATE_OF_LAUNCH,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        elevation=ELEVATION,
        max_expected_height=5000,
    )
    if weather_data == "c":
        # Mean EuRoC-week atmosphere at Santa Margarida (2005-2024), see Atlas_v1.0.py
        with open(BASE_DIR / "simulation_inputs/environment_data/mean_environment_values.json") as f:
            data = json.load(f)
        hour = str(env.date[3])
        env.set_atmospheric_model(
            type="custom_atmosphere",
            pressure=data["atmospheric_model_pressure_profile"][hour],
            temperature=data["atmospheric_model_temperature_profile"][hour],
            wind_u=data["atmospheric_model_wind_velocity_x_profile"][hour],
            wind_v=data["atmospheric_model_wind_velocity_y_profile"][hour],
        )
    return env


def build_atlas(setting, drogue_lag, main_lag, logic):
    """Atlas as defined in Atlas_v1.0.py, with the recovery lags given explicitly."""
    from rocketpy import Rocket, SolidMotor

    motor = SolidMotor(
        thrust_source=str(BASE_DIR / "simulation_inputs/propulsion_data/Cesaroni_9977_M2245.csv"),
        burn_time=setting["burn_time"],
        reshape_thrust_curve=(setting["burn_time"], setting["impulse"]),
        interpolation_method="linear",
        nozzle_radius=setting["nozzle_radius"],
        throat_radius=setting["throat_radius"],
        grain_number=6,
        grain_separation=setting["grain_separation"],
        grain_density=setting["grain_density"],
        grain_outer_radius=setting["grain_outer_radius"],
        grain_initial_inner_radius=setting["grain_initial_inner_radius"],
        grain_initial_height=setting["grain_initial_height"],
        nozzle_position=setting["nozzle_position"],
        grains_center_of_mass_position=setting["grains_center_of_mass_position"],
        dry_mass=setting["motor_dry_mass"],
        dry_inertia=(setting["motor_inertia_11"], setting["motor_inertia_11"], setting["motor_inertia_33"]),
        center_of_dry_mass_position=setting["motor_dry_mass_position"],
        coordinate_system_orientation="nozzle_to_combustion_chamber",
    )

    drag_dir = BASE_DIR / "simulation_inputs/aerodynamic_data/v1.2_wedge"
    atlas = Rocket(
        radius=setting["radius"],
        mass=setting["rocket_dry_mass"],
        inertia=(setting["rocket_dry_inertia_11"], setting["rocket_dry_inertia_11"], setting["rocket_dry_inertia_33"]),
        power_off_drag=str(drag_dir / f"{DRAG_CASE}_power_off.csv"),
        power_on_drag=str(drag_dir / f"{DRAG_CASE}_power_on.csv"),
        center_of_mass_without_motor=1.84789,
        coordinate_system_orientation="nose_to_tail",
    )
    atlas.set_rail_buttons(
        upper_button_position=setting["upper_button_y"],
        lower_button_position=setting["lower_button_y"],
        angular_position=setting["angular_button"],
    )
    atlas.add_motor(motor, position=3.32)
    atlas.power_off_drag *= setting["power_off_drag_corr"]
    atlas.power_on_drag *= setting["power_on_drag_corr"]
    atlas.add_nose(length=setting["nose_length"], kind="lvhaack", position=setting["nose_position"])
    atlas.add_trapezoidal_fins(
        n=3,
        span=setting["fin_span"],
        root_chord=setting["fin_root_chord"],
        tip_chord=setting["fin_tip_chord"],
        position=setting["fin_position"],
        sweep_angle=setting["fin_sweep_angle"],
        cant_angle=0,
    )
    atlas.add_tail(
        top_radius=setting["tail_top_radius"],
        bottom_radius=setting["tail_bottom_radius"],
        length=setting["tail_length"],
        position=setting["tail_position"],
    )
    noise = (setting["noise_mean"], setting["noise_p_stdev"], setting["noise_p_tc"])
    atlas.add_parachute(
        "Drogue", cd_s=setting["cd_s_drogue"], trigger=logic.drogue_trigger,
        sampling_rate=SAMPLING_RATE, lag=drogue_lag, noise=noise,
    )
    atlas.add_parachute(
        "Main", cd_s=setting["cd_s_main"], trigger=logic.main_trigger,
        sampling_rate=SAMPLING_RATE, lag=main_lag, noise=noise,
    )
    return atlas
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- POST-PROCESSING
def canopy_state(flight, env, t, parachute, mass):
    """Opening load at the instant t of full inflation, with the RocketPy parachute model.

    RocketPy switches to the full CdS in one step and integrates
        a = (D - m g z) / (m + ma),   D = -1/2 rho CdS |v_rel| v_rel,   ma = Ca rho 2/3 pi R^2 H
    so the canopy drag D is the peak aerodynamic load, and the force transmitted to the rocket
    (everything but gravity acting on it) is m (D + ma g z) / (m + ma).
    """
    z = flight.z.get_value_opt(t)
    rel = np.array([
        flight.vx.get_value_opt(t) - env.wind_velocity_x.get_value_opt(z),
        flight.vy.get_value_opt(t) - env.wind_velocity_y.get_value_opt(z),
        flight.vz.get_value_opt(t),
    ])
    speed = np.linalg.norm(rel)
    rho = env.density.get_value_opt(z)
    g = env.gravity.get_value_opt(z)
    added_mass = (
        parachute.added_mass_coefficient * rho * (2 / 3) * np.pi * parachute.radius**2 * parachute.height
    )
    drag = -0.5 * rho * parachute.cd_s * speed * rel
    on_rocket = mass / (mass + added_mass) * (drag + np.array([0, 0, added_mass * g]))
    return {
        "altitude": z - env.elevation,
        "speed": speed,
        "vz": rel[2],
        "rho": rho,
        "force": 0.5 * rho * parachute.cd_s * speed**2,
        "force_on_rocket": np.linalg.norm(on_rocket),
        "load_factor": np.linalg.norm(on_rocket) / (mass * g),
        "added_mass": added_mass,
    }


def descent_segment(flight, env, t_start, t_end, parachute, mass, n_points=300):
    """Descent under a parachute between t_start and t_end.

    Returns the time the descent becomes steady (relative speed within STEADY_TOLERANCE of the
    local terminal velocity) and the altitude / descent velocity profile from then on.
    """
    times = np.linspace(t_start, t_end, n_points)
    z = np.array([flight.z.get_value_opt(t) for t in times])
    vx = np.array([flight.vx.get_value_opt(t) for t in times])
    vy = np.array([flight.vy.get_value_opt(t) for t in times])
    vz = np.array([flight.vz.get_value_opt(t) for t in times])
    wx = np.array([env.wind_velocity_x.get_value_opt(zi) for zi in z])
    wy = np.array([env.wind_velocity_y.get_value_opt(zi) for zi in z])
    rho = np.array([env.density.get_value_opt(zi) for zi in z])
    g = np.array([env.gravity.get_value_opt(zi) for zi in z])

    speed = np.sqrt((vx - wx) ** 2 + (vy - wy) ** 2 + vz**2)
    terminal = np.sqrt(2 * mass * g / (rho * parachute.cd_s))
    steady = np.nonzero(np.abs(speed - terminal) <= STEADY_TOLERANCE * terminal)[0]
    if len(steady) == 0:
        return None
    first = steady[0]
    return {
        "t_steady": times[first],
        "terminal": terminal[first],
        "altitude": z[first:] - env.elevation,
        "descent_velocity": -vz[first:],
        "transient_peak_speed": speed[: first + 1].max(),
    }


def analyze_flight(flight, env, drogue_lag, main_lag):
    rocket = flight.rocket
    mass = rocket.dry_mass
    events = {parachute.name: t for t, parachute in flight.parachute_events}
    parachutes = {parachute.name: parachute for _, parachute in flight.parachute_events}

    row = {
        "apogee_agl": flight.apogee - env.elevation,
        "apogee_time": flight.apogee_time,
        "out_of_rail_time": flight.out_of_rail_time,
        "out_of_rail_velocity": flight.out_of_rail_velocity,
        "out_of_rail_acceleration": flight.acceleration.get_value_opt(flight.out_of_rail_time),
        "max_acceleration_power_on": flight.max_acceleration_power_on,
        "max_acceleration_total": flight.max_acceleration,
        "max_speed": flight.max_speed,
        "max_mach": flight.max_mach_number,
        "out_of_rail_static_margin": rocket.static_margin(flight.out_of_rail_time),
        "impact_time": flight.t_final,
        "impact_velocity": -flight.impact_velocity,
        "impact_x": flight.x_impact,
        "impact_y": flight.y_impact,
    }
    profile = None

    if "Drogue" in events:
        drogue = parachutes["Drogue"]
        t_trigger = events["Drogue"]
        t_inflated = t_trigger + drogue_lag
        state = canopy_state(flight, env, t_inflated, drogue, mass)
        row.update({
            "drogue_trigger_time": t_trigger,
            "drogue_inflated_time": t_inflated,
            "drogue_delay_from_apogee": t_inflated - flight.apogee_time,
            **{f"drogue_{key}": value for key, value in state.items()},
        })
        t_end = events.get("Main", flight.t_final)
        segment = descent_segment(flight, env, t_inflated, t_end, drogue, mass)
        if segment is not None:
            row.update({
                "drogue_steady_time": segment["t_steady"],
                "drogue_steady_altitude": segment["altitude"][0],
                "drogue_descent_max": segment["descent_velocity"].max(),
                "drogue_descent_min": segment["descent_velocity"].min(),
                "drogue_descent_at_main_trigger": segment["descent_velocity"][-1],
                "drogue_terminal_after_transient": segment["terminal"],
                "drogue_transient_peak_speed": segment["transient_peak_speed"],
            })
            keep = np.linspace(0, len(segment["altitude"]) - 1, 60).astype(int)
            profile = (segment["altitude"][keep], segment["descent_velocity"][keep])

    if "Main" in events:
        main = parachutes["Main"]
        t_trigger = events["Main"]
        t_inflated = t_trigger + main_lag
        if t_inflated < flight.t_final:
            state = canopy_state(flight, env, t_inflated, main, mass)
            row.update({
                "main_trigger_time": t_trigger,
                "main_trigger_altitude": flight.z.get_value_opt(t_trigger) - env.elevation,
                "main_inflated_time": t_inflated,
                **{f"main_{key}": value for key, value in state.items()},
            })
            segment = descent_segment(flight, env, t_inflated, flight.t_final, main, mass)
            if segment is not None:
                row.update({
                    "main_steady_altitude": segment["altitude"][0],
                    "main_terminal_after_transient": segment["terminal"],
                    "main_descent_max": segment["descent_velocity"].max(),
                    "main_transient_peak_speed": segment["transient_peak_speed"],
                })
    return row, profile
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- WORKERS
_ENV = None


def init_worker(weather_data):
    global _ENV
    _ENV = build_environment(weather_data)


def run_one(task):
    from rocketpy import Flight

    start = time.process_time()
    rng = np.random.default_rng(task["seed"])
    setting = sample_setting(rng, task["dry_mass"])

    # Full inflation T seconds after apogee: the detection algorithm already adds APOGEE_THRESHOLD
    if task["campaign"] == "main":
        drogue_case = f"{task['drogue_delay']:g}"
        # The barometric trigger fires when crossing 450 m AGL: the lag is the whole crossing -> inflation time
        main_lag = float(task["case"])
    else:
        drogue_case = task["case"]
        main_lag = setting["t_sw_main"] + setting["t_infl_main"]
    drogue_lag = float(drogue_case) - APOGEE_THRESHOLD

    info = {
        "dry_mass_case": task["dry_mass"],
        "delay_case": drogue_case,
        "main_delay_case": task["case"] if task["campaign"] == "main" else "dispersed",
        "run": task["run"],
        "seed": task["seed"],
        "rocket_dry_mass": setting["rocket_dry_mass"],
        "wet_mass": setting["rocket_dry_mass"] + PROPELLANT_MASS,
        "drogue_lag": drogue_lag,
        "main_lag": main_lag,
        "cd_s_drogue": setting["cd_s_drogue"],
        "cd_s_main": setting["cd_s_main"],
    }
    try:
        logic = RecoveryLogic()
        atlas = build_atlas(setting, drogue_lag, main_lag, logic)
        flight = Flight(
            rocket=atlas,
            environment=_ENV,
            rail_length=setting["rail_length"],
            inclination=setting["inclination"],
            heading=setting["heading"],
            max_time=1200,
        )
        row, profile = analyze_flight(flight, _ENV, drogue_lag, main_lag)
        info["wet_mass"] = flight.rocket.total_mass(0)
        info.update(row)
        info["execution_time"] = time.process_time() - start
        return info, profile, None
    except Exception as error:
        return info, None, repr(error)
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- MAIN
def run_study(args, output_dir):
    campaign = args.campaign
    masses = [float(m) for m in args.masses.split(",")]
    cases = [c.strip() for c in (args.main_delays if campaign == "main" else args.delays).split(",")]
    tasks = []
    for mass in masses:
        for case in cases:
            for run in range(args.n_sims):
                tasks.append({
                    "campaign": campaign, "dry_mass": mass, "case": case, "run": run,
                    "drogue_delay": args.drogue_delay,
                    "seed": args.seed * 1_000_003 + len(tasks),
                })

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / f"study_config_{campaign}.json", "w") as f:
        json.dump({
            "campaign": campaign, "masses": masses, "delay_cases": cases, "n_sims": args.n_sims, "seed": args.seed,
            "fixed_drogue_delay": args.drogue_delay if campaign == "main" else None,
            "weather_data": args.weather, "drag_case": DRAG_CASE, "propellant_mass": PROPELLANT_MASS,
            "analysis_parameters": analysis_parameters,
        }, f, indent=2)

    print(f"Atlas parachute study ({campaign}): {len(masses)} masses x {len(cases)} delay cases x {args.n_sims} runs "
          f"= {len(tasks)} flights on {args.workers} workers", flush=True)

    rows, profiles, errors = [], [], []
    start = time.time()
    context = mp.get_context("fork")
    with context.Pool(args.workers, initializer=init_worker, initargs=(args.weather,)) as pool:
        for done, (info, profile, error) in enumerate(pool.imap_unordered(run_one, tasks), start=1):
            if error is None:
                rows.append(info)
                if profile is not None:
                    profiles.append({"dry_mass_case": info["dry_mass_case"], "delay_case": info["delay_case"],
                                     "altitude": profile[0], "descent_velocity": profile[1]})
            else:
                errors.append({**info, "error": error})
            if done % max(1, len(tasks) // 50) == 0 or done == len(tasks):
                elapsed = time.time() - start
                remaining = elapsed / done * (len(tasks) - done)
                print(f"  {done}/{len(tasks)} flights, {len(errors)} errors, "
                      f"elapsed {elapsed / 60:.1f} min, remaining ~{remaining / 60:.1f} min", flush=True)

    columns = []
    for row in rows:
        columns += [key for key in row if key not in columns]
    with open(output_dir / f"runs_{campaign}.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    with open(output_dir / f"profiles_{campaign}.pickle", "wb") as f:
        pickle.dump(profiles, f)
    with open(output_dir / f"errors_{campaign}.txt", "w") as f:
        for error in errors:
            f.write(json.dumps(error, default=float) + "\n")
    print(f"Completed in {(time.time() - start) / 60:.1f} min: {len(rows)} flights, {len(errors)} errors", flush=True)


def add_terminal_columns(output_dir, weather_data):
    """Terminal velocity under drogue at the end of the opening transient, for runs made before it was saved.

    v_t = sqrt(2 m g / (rho CdS)) at the altitude where the transient ends: under a parachute RocketPy
    reaches a = 0, i.e. drag = weight. Also adds v_t at the main trigger altitude as a check against
    the simulated descent velocity there.
    """
    path = output_dir / "runs_drogue.csv"
    if not path.exists():
        return
    import pandas as pd

    df = pd.read_csv(path, dtype={"delay_case": str, "main_delay_case": str})
    if "drogue_terminal_at_main_trigger" in df.columns and df["drogue_terminal_after_transient"].notna().all():
        return
    env = build_environment(weather_data)

    def terminal(altitude_agl, mass, cd_s):
        z = altitude_agl + env.elevation
        return np.sqrt(2 * mass * env.gravity.get_value_opt(z) / (env.density.get_value_opt(z) * cd_s))

    mass = df.rocket_dry_mass + analysis_parameters["motor_dry_mass"][0]
    df["drogue_terminal_after_transient"] = [
        terminal(h, m, c) for h, m, c in zip(df.drogue_steady_altitude, mass, df.cd_s_drogue)]
    df["drogue_terminal_at_main_trigger"] = [
        terminal(h, m, c) for h, m, c in zip(df.main_trigger_altitude, mass, df.cd_s_drogue)]
    df.to_csv(path, index=False)
    error = df.drogue_terminal_at_main_trigger - df.drogue_descent_at_main_trigger
    print(f"Added drogue terminal velocity columns; check at the main trigger: "
          f"mean error {error.mean():+.3f} m/s, max |error| {error.abs().max():.3f} m/s")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n-sims", type=int, default=100, help="Monte Carlo runs per (mass, delay) case")
    parser.add_argument("--masses", default=DEFAULT_MASSES, help="rocket dry masses in kg, comma separated")
    parser.add_argument("--campaign", choices=["drogue", "main"], default="drogue",
                        help="drogue: sweep of --delays; main: sweep of --main-delays with --drogue-delay fixed")
    parser.add_argument("--delays", default=DEFAULT_DELAYS,
                        help="apogee -> drogue full inflation times in s, comma separated")
    parser.add_argument("--main-delays", default=DEFAULT_MAIN_DELAYS,
                        help="450 m AGL crossing -> main full inflation times in s, comma separated")
    parser.add_argument("--drogue-delay", type=float, default=DEFAULT_DROGUE_DELAY,
                        help="apogee -> drogue full inflation time used in the main campaign (s)")
    parser.add_argument("--workers", type=int, default=os.cpu_count())
    parser.add_argument("--weather", choices=["c", "i"], default="c", help="c = mean Santa Margarida, i = ISA")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--analyze-only", action="store_true", help="only rebuild tables and plots from runs_*.csv")
    args = parser.parse_args()

    if not args.analyze_only:
        run_study(args, args.output)
    add_terminal_columns(args.output, args.weather)

    from parachute_study_plots import make_report
    make_report(args.output)


if __name__ == "__main__":
    main()
