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
import math
from pathlib import Path

import numpy as np
import pandas as pd

#-------------------------------------------------------------------------------------------------------- VERSIONS
GEOMETRY = "v1.6"                                   # simulation_inputs/geometry_data/<version>/
AERODYNAMICS = "v1.4/CD_Mach_Test_Atlas_v_1.2_SDRAD_cd_mach.csv"         # simulation_inputs/aerodynamic_data/rocket_body/<file>
MOTOR = "SRAD/vPROVA"             # simulation_inputs/propulsion_data/<motor>/
RECOVERY = "v1.0"                                   # simulation_inputs/recovery_data/<version>/
AIRBRAKES = "vPROVA"                                    # None = no airbrakes, or "v1.0"
LAUNCH_SITE = "santa_margarida"                     # simulation_inputs/environment_data/<site>/
LAUNCH_DATE = (2024, 10, 11, 12)                    # (Year, Month, Day, Hour UTC)

# Airbrake controller: 1 = predictive scan of 13 openings, 2 = Simulink model (apogee predictor + PI + servo)
funz_di_controllo = 1

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
    table = pd.read_csv(path, comment="#", skipinitialspace=True, dtype=str)
    incomplete = [row.name for row in table.itertuples(index=False) if "---" in (row.value, row.std)]
    if incomplete:
        raise ValueError(f"{path}: fields still to fill (---): {', '.join(incomplete)}")
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
        #burn_time=s["burn_time"],                                       #
        reshape_thrust_curve=False,#(s["burn_time"], s["impulse"]),      # anche se gli dai thrust file lo sovrascrive
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
#--------------------------------------------------------------------------------------------------------


#-------------------------------------------------------------------------------------------------------- AIRBRAKE CONTROLLERS
# Settings shared by the two controllers
G = 9.80665
MACH_MAX = 1.2      # upper limit of the precomputed Cd tables

# ---- Servo dynamics (both controllers): rate limiter between the commanded and the actual opening ----
# The speed limits are read from airbrakes.csv: servo_rise and servo_fall, in 1/s (1.0 = 100 % of the stroke per second)
SERVO_IC = 0.0              # ? initial opening of the servo


def servo_step(position, command, Ts, rise, fall):
    """One step of the servo: moves from `position` towards `command`, with max opening rate `rise`
    and max closing rate `fall` (both in 1/s)."""
    change = min(max(command - position, -fall * Ts), rise * Ts)
    return position + change


# ---- Controller 1: predictive scan ----
NSTEP = 13          # opening candidates: 0, 1/12, ..., 1
DT = 0.1            # prediction step [s]
NMAX = 600          # max prediction steps


def airbrake_controller_1(env, motor, rocket, s):
    """Predictive controller: every call it simulates the coast up to apogee for NSTEP openings (all
    together, vectorized) and commands the opening that makes the apogee equal to target_apogee (AGL).
    Closed below deployment_altitude (AGL) and during the burn. The cache lives in the closure, so every
    flight (Monte Carlo included) has its own. The commanded opening goes through the servo dynamics."""
    cache = {}
    Ts = 1.0 / s["airbrake_sampling_rate"]
    servo = {"position": SERVO_IC}

    def build_tables(air_brakes):
        h = np.arange(env.elevation, env.elevation + env.max_expected_height + 1, 50.0)
        mach = np.linspace(0, MACH_MAX, round(MACH_MAX / 0.01) + 1)
        levels = np.linspace(0, 1, NSTEP)
        rocket_cda = np.array([rocket.power_off_drag(m) for m in mach]) * rocket.area
        override = getattr(air_brakes, "override_rocket_drag", True)
        cda = np.empty((NSTEP, mach.size))
        for k, level in enumerate(levels):
            if level == 0:                      # RocketPy applies the airbrakes only above level 0
                cda[k] = rocket_cda
            else:
                ab = np.array([air_brakes.drag_coefficient(level, m) for m in mach]) * air_brakes.reference_area
                cda[k] = ab if override else rocket_cda + ab
        cache.update(
            h=h, rho=np.array([env.density(x) for x in h]), a=np.array([env.speed_of_sound(x) for x in h]),
            mach=mach, dmach=mach[1] - mach[0], cda=cda, levels=levels, rows=np.arange(NSTEP),
        )

    def predict_apogee(v0, h0, t0, mass):
        """Vertical coast of the NSTEP candidates at once -> (apogee ASL, apogee time) arrays."""
        c = cache
        v = np.full(NSTEP, float(v0))
        h = np.full(NSTEP, float(h0))
        apo = np.empty(NSTEP)
        t_apo = np.empty(NSTEP)
        active = np.ones(NSTEP, bool)
        t = t0
        for _ in range(NMAX):
            rho = np.interp(h, c["h"], c["rho"])
            a_s = np.interp(h, c["h"], c["a"])
            x = np.clip(v / a_s, 0, MACH_MAX) / c["dmach"]
            i = np.minimum(x.astype(int), c["mach"].size - 2)
            w = x - i
            cda = c["cda"][c["rows"], i] * (1 - w) + c["cda"][c["rows"], i + 1] * w
            v_new = v + (-0.5 * rho * cda * v * v / mass - G) * DT
            h_new = h + v_new * DT
            t += DT
            done = active & (v_new < 0)
            apo[done], t_apo[done] = h_new[done], t
            active &= ~done
            v = np.where(active, v_new, v)
            h = np.where(active, h_new, h)
            if not active.any():
                break
        apo[active], t_apo[active] = h[active], t     # horizon exceeded
        return apo, t_apo

    def controller(time, sampling_rate, state, state_history, observed_variables, air_brakes):
        altitude_asl = state[2]
        vz = state[5]

        if time < motor.burn_out_time:
            return None

        if not cache:
            build_tables(air_brakes)

        level, apogee_agl = 0.0, 0.0
        if altitude_asl - env.elevation >= s["deployment_altitude"] and vz > 0:   # deployment altitude is AGL
            target = s["target_apogee"] + env.elevation            # target is AGL
            apo, _ = predict_apogee(vz, altitude_asl, time, float(rocket.total_mass(time)))
            levels = cache["levels"]
            below = np.nonzero(apo <= target)[0]
            if below.size == 0:                 # even fully open it overshoots -> max opening
                level, apogee_agl = levels[-1], apo[-1] - env.elevation
            elif below[0] == 0:                 # even closed it undershoots -> stay closed
                level, apogee_agl = levels[0], apo[0] - env.elevation
            else:                               # interpolate between the last above and the first below
                k = below[0]
                w = (apo[k - 1] - target) / (apo[k - 1] - apo[k])
                level = levels[k - 1] + w * (levels[k] - levels[k - 1])
                apogee_agl = s["target_apogee"]

        # Servo dynamics: the actual opening follows the command with a limited speed
        servo["position"] = servo_step(servo["position"], float(level), Ts, s["servo_rise"], s["servo_fall"])
        air_brakes.deployment_level = float(min(max(servo["position"], 0.0), 1.0))

        free_stream_speed = np.sqrt(
            (env.wind_velocity_x(altitude_asl) - state[3]) ** 2
            + (env.wind_velocity_y(altitude_asl) - state[4]) ** 2
            + state[5] ** 2
        )
        mach = free_stream_speed / env.speed_of_sound(altitude_asl)
        # Saved in observed_variables
        return time, air_brakes.deployment_level, air_brakes.drag_coefficient(air_brakes.deployment_level, mach), apogee_agl

    return controller


# ---- Controller 2: Simulink model (Apogee Predictor + PI + servo) ----
# All the openings are 0-1 (the x100 block of the Simulink model is not needed).
PRED_DT = 0.05              # prediction step [s]
PRED_NMAX = 1000            # max prediction steps
PRED_UPDATE_RHO = True      # update rho and speed of sound with altitude inside the prediction

# <-- CHECK these against the Simulink model (the ones marked ? are not visible in the picture)
KP = 0.001                  # proportional gain
KI = 0.004                  # gain before the discrete-time integrator
INTEGRATOR_IC = 0.0         # ? integrator initial condition (value after reset)
SAT_MIN, SAT_MAX = 0.0, 1.0 # ? Saturation limits (before x100, so 0-1)
OPENING_MIN = 0.0           # ? openingMin as a fraction (a value of 5 % in Simulink -> 0.05)
# (servo dynamics: servo_rise and servo_fall come from airbrakes.csv, SERVO_IC is defined above; shared with controller 1)
DELAY_IC = 0.0              # ? Unit Delay (1/z) initial condition


def _isa_atmosphere(h):
    """Simplified ISA, troposphere (valid up to 11 km)."""
    T0, p0, L = 288.15, 101325.0, 0.0065
    g0, R, gam = 9.80665, 287.058, 1.4
    h = min(max(h, 0.0), 11000.0)
    T = T0 - L * h
    p = p0 * (T / T0) ** (g0 / (R * L))
    return p / (R * T), math.sqrt(gam * R * T)


def _cd_at_mach(Cd_table, Mach_bp, mach):
    """Linear interpolation along Mach -> vector Cd(opening) at this Mach."""
    n = len(Mach_bp)
    M = min(max(mach, Mach_bp[0]), Mach_bp[n - 1])
    k = 0
    while k < n - 2 and M > Mach_bp[k + 1]:
        k += 1
    w = (M - Mach_bp[k]) / (Mach_bp[k + 1] - Mach_bp[k])
    return (1 - w) * Cd_table[:, k] + w * Cd_table[:, k + 1]


def _opening_to_cd_row(Cd_table, Opening_bp, opening):
    """Linear interpolation along opening -> row vector Cd(Mach) at this opening."""
    n = len(Opening_bp)
    op = min(max(opening, Opening_bp[0]), Opening_bp[n - 1])
    k = 0
    while k < n - 2 and op > Opening_bp[k + 1]:
        k += 1
    w = (op - Opening_bp[k]) / (Opening_bp[k + 1] - Opening_bp[k])
    return (1 - w) * Cd_table[k, :] + w * Cd_table[k + 1, :]


def _interp_cd(Mach_bp, CdRow, mach):
    """Linear interpolation of the Cd row along Mach, clamped to the table range
    (np.interp does exactly this, and it is much faster than the while loop inside the prediction)."""
    return np.interp(mach, Mach_bp, CdRow)


def _opening_to_cd(CdVec, Opening_bp, opening):
    """Linear interpolation of the Cd(opening) vector at the current Mach."""
    n = len(Opening_bp)
    op = min(max(opening, Opening_bp[0]), Opening_bp[n - 1])
    k = 0
    while k < n - 2 and op > Opening_bp[k + 1]:
        k += 1
    w = (op - Opening_bp[k]) / (Opening_bp[k + 1] - Opening_bp[k])
    return (1 - w) * CdVec[k] + w * CdVec[k + 1]


def _predict_apogee(CdRow, Mach_bp, v0, h0, t0, m, Aref, dt, Nmax, update_rho, rho0, a0):
    g = 9.80665
    v, h, t, rho, a_s = v0, h0, t0, rho0, a0
    for _ in range(Nmax):
        if update_rho:
            rho, a_s = _isa_atmosphere(h)
        Cd = _interp_cd(Mach_bp, CdRow, v / a_s)
        a = -0.5 * Cd * rho * Aref * v ** 2 / m - g
        v = v + a * dt
        h = h + v * dt
        t = t + dt
        if v < 0:
            return h, t
    return h, t                 # horizon exceeded (should not happen in a normal coast)


def _apogee_predictor(opening, v_vert, alt, time, dry_mass, Aref, opening_alt, target_alt, Cd_table, Mach_bp, Opening_bp):
    """MATLAB fcn: predicted apogee holding `opening` from now on.
    Returns apogeeAlt, t_apogee, Cd_cmd, resetPID (1 = controller not active)."""
    m = dry_mass
    # 1) ISA at the current altitude -> Mach
    rho0, a0 = _isa_atmosphere(alt)
    mach = abs(v_vert) / a0
    # 2) Cd of the tested opening at the current Mach (log only)
    CdVec = _cd_at_mach(Cd_table, Mach_bp, mach)
    Cd_cmd = _opening_to_cd(CdVec, Opening_bp, opening)
    # default outputs (controller not active: zero error, PID reset)
    apogee_alt, t_apogee, reset_pid = target_alt, 0.0, 1
    if alt < opening_alt or v_vert <= 0:
        return apogee_alt, t_apogee, Cd_cmd, reset_pid
    # 3) predict the apogee with the current opening
    reset_pid = 0
    CdRow = _opening_to_cd_row(Cd_table, Opening_bp, opening)
    apogee_alt, t_apogee = _predict_apogee(CdRow, Mach_bp, v_vert, alt, time, m, Aref,
                                           PRED_DT, PRED_NMAX, PRED_UPDATE_RHO, rho0, a0)
    return apogee_alt, t_apogee, Cd_cmd, reset_pid


def airbrake_controller_2(env, motor, rocket, s):
    """Simulink controller: Apogee Predictor -> error -> P + I (with reset) -> saturation -> + openingMin
    -> Servo Dynamics (rate limiter) -> cmdOpening, fed back to the predictor through a unit delay (1/z).
    Internally altitudes are ASL; deployment_altitude and target_apogee in the csv are AGL."""
    Ts = 1.0 / s["airbrake_sampling_rate"]
    dry_mass = s["rocket_dry_mass"] + s["motor_dry_mass"]
    tables = {}
    st = {"integrator": INTEGRATOR_IC, "servo": SERVO_IC, "delay": DELAY_IC}

    def build_tables(air_brakes):
        """Total Cd table [opening x Mach] referred to Aref, equivalent to what RocketPy applies."""
        Aref = air_brakes.reference_area
        Mach_bp = np.linspace(0, MACH_MAX, round(MACH_MAX / 0.01) + 1)
        Opening_bp = np.linspace(0, 1, 21)
        rocket_cda = np.array([rocket.power_off_drag(m) for m in Mach_bp]) * rocket.area
        override = getattr(air_brakes, "override_rocket_drag", True)
        Cd_table = np.empty((Opening_bp.size, Mach_bp.size))
        for k, level in enumerate(Opening_bp):
            if level == 0:                      # RocketPy applies the airbrakes only above level 0
                cda = rocket_cda
            else:
                ab = np.array([air_brakes.drag_coefficient(level, m) for m in Mach_bp]) * Aref
                cda = ab if override else rocket_cda + ab
            Cd_table[k] = cda / Aref
        tables.update(Aref=Aref, Mach_bp=Mach_bp, Opening_bp=Opening_bp, Cd_table=Cd_table)

    def controller(time, sampling_rate, state, state_history, observed_variables, air_brakes):
        altitude_asl = state[2]
        vz = state[5]

        if time < motor.burn_out_time:
            return None

        if not tables:
            build_tables(air_brakes)

        target_alt = s["target_apogee"] + env.elevation

        # A) Apogee Predictor, tested with the opening of the previous step (unit delay)
        apogee_alt, t_apogee, cd_cmd, reset_pid = _apogee_predictor(
            st["delay"], vz, altitude_asl, time, dry_mass, tables["Aref"], s["deployment_altitude"] + env.elevation,
            target_alt, tables["Cd_table"], tables["Mach_bp"], tables["Opening_bp"])

        # B) error
        err = apogee_alt - target_alt

        # C) PI: proportional + discrete-time integrator (forward Euler K*Ts/(z-1), reset when not active)
        p_term = KP * err
        if reset_pid:
            st["integrator"] = INTEGRATOR_IC
            i_term = INTEGRATOR_IC
        else:
            i_term = st["integrator"]
            st["integrator"] += Ts * KI * err

        # D) saturation -> + openingMin -> servo dynamics (rate limiter)
        u = min(max(p_term + i_term, SAT_MIN), SAT_MAX) + OPENING_MIN
        st["servo"] = servo_step(st["servo"], u, Ts, s["servo_rise"], s["servo_fall"])
        cmd_opening = st["servo"]
        st["delay"] = cmd_opening               # 1/z

        level = min(max(cmd_opening, 0.0), 1.0)  # RocketPy accepts 0-1 only
        air_brakes.deployment_level = float(level)

        free_stream_speed = np.sqrt(
            (env.wind_velocity_x(altitude_asl) - state[3]) ** 2
            + (env.wind_velocity_y(altitude_asl) - state[4]) ** 2
            + state[5] ** 2
        )
        mach = free_stream_speed / env.speed_of_sound(altitude_asl)
        apogee_agl = 0.0 if reset_pid else apogee_alt - env.elevation
        # Saved in observed_variables (same 4 values as controller 1, so the graph works for both)
        return time, air_brakes.deployment_level, air_brakes.drag_coefficient(level, mach), apogee_agl

    return controller


def airbrake_controller(env, motor, rocket, s):
    """Controller chosen with funz_di_controllo (1 or 2)."""
    controllers = {1: airbrake_controller_1, 2: airbrake_controller_2}
    if funz_di_controllo not in controllers:
        raise ValueError(f"funz_di_controllo must be 1 or 2, not {funz_di_controllo}")
    return controllers[funz_di_controllo](env, motor, rocket, s)
#--------------------------------------------------------------------------------------------------------


#-------------------------------------------------------------------------------------------------------- ROCKET AND FLIGHT
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
    atlas.add_nose(length=s["nose_length"], kind="von karman", position=s["nose_position"])
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
            controller_function=airbrake_controller(env, motor, atlas, s),
            sampling_rate=s["airbrake_sampling_rate"],
            reference_area=s["reference_area"],
            clamp=False,
            initial_observed_variables=[0, 0, 0, 0],
            override_rocket_drag=True,
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