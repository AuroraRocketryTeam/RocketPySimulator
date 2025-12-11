import matplotlib as mpl
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import time as pytime
from pathlib import Path
import csv
import math
import pandas as pd
from rocketpy import Environment, Flight, Rocket, SolidMotor
from rocketpy.tools import (
quaternions_to_spin,
quaternions_to_nutation,
quaternions_to_precession,
)

# ----------------------------------------------------------------------
# BASE PATH
# ----------------------------------------------------------------------
try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:
    # If running in an environment where __file__ does not exist
    BASE_DIR = Path(".").resolve()

# ----------------------------------------------------------------------
# ENVIRONMENT
# ----------------------------------------------------------------------
env = Environment(latitude=39.3901806, longitude=-8.289189, elevation=160)
env.set_date((2025, 12, 13, 6))  # UTC time
env.set_atmospheric_model(type="Forecast", file="GFS")
env.max_expected_height = 4500

# Environment information
# --- Remove comment to display environment info ---
# 
# env.info()

# ----------------------------------------------------------------------
# PARACHUTE LOGIC
# ----------------------------------------------------------------------

# Definition of global variables, to be used inside and outside parachute functions
global last_negative_time, apogee_detected, sampling_rate, parachute_timer
last_negative_time = None
apogee_detected = False
sampling_rate = 105
parachute_stopwatch = 0

# Persistent parachute deployment state (for logs / CSV)
drogue_deployed = False
main_deployed = False


def check_apogee(vertical_velocity, current_time, threshold=0.1):
    """
    Detects apogee when the vertical velocity is consistently negative for at least 'threshold' seconds.
    """
    global last_negative_time, apogee_detected

    if apogee_detected:
        return True, last_negative_time

    if vertical_velocity < 0:
        if last_negative_time is None:
            last_negative_time = current_time
            return False, last_negative_time
        elif (current_time - last_negative_time) >= threshold:
            apogee_detected = True
            return True, last_negative_time
        else:
            return False, last_negative_time
    else:
        last_negative_time = None
        return False, None


def main_parachute_opening(apogee_detected_flag: bool, altitude: float) -> bool:
    """Opens the main parachute after apogee, when altitude falls below 450 m."""
    return apogee_detected_flag and altitude <= 450.0


def simulator_check_drogue_opening(p, h, y):
    """
    Drogue trigger: uses the apogee detection algorithm.
    """
    global last_negative_time, apogee_detected, parachute_stopwatch, sampling_rate
    global drogue_deployed

    altitude = h
    vertical_velocity = y[5]

    parachute_stopwatch += 1.0 / sampling_rate
    now = parachute_stopwatch

    apogee_flag, last_neg = check_apogee(vertical_velocity, now)
    apogee_detected = apogee_flag
    last_negative_time = last_neg

    if apogee_detected:
        drogue_deployed = True

    return apogee_detected


def simulator_check_main_opening(p, h, y):
    """
    Main trigger: opens the main parachute when apogee is detected and altitude < 450 m.
    """
    global apogee_detected, main_deployed

    altitude = h
    open_flag = main_parachute_opening(apogee_detected, altitude)
    if open_flag:
        main_deployed = True
    return open_flag


# ----------------------------------------------------------------------
# MOTOR DATA
# ----------------------------------------------------------------------
Pro75M8187 = SolidMotor(
    thrust_source=str(BASE_DIR / "Cesaroni_8187M1545_P.csv"),
    dry_mass=0,
    dry_inertia=(0, 0, 0),
    nozzle_radius=29 / 1000,
    grain_number=6,
    grain_density=1758.7,
    grain_outer_radius=35.9 / 1000,
    grain_initial_inner_radius=18.1 / 1000,
    grain_initial_height=156.17 / 1000,
    grain_separation=3 / 1000,
    grains_center_of_mass_position=-0.7343,
    center_of_dry_mass_position=0,
    nozzle_position=-1.296,
    burn_time=5.3,
    throat_radius=20 / 1000,
    coordinate_system_orientation="nozzle_to_combustion_chamber",
)

# Motor information
# --- Remove comment to display motor info ---
# 
# Pro75M8187.info()

# ----------------------------------------------------------------------
# ROCKET
# ----------------------------------------------------------------------
Nemesis = Rocket(
    radius=75 / 1000,
    mass=22.740,
    inertia=(14.304, 14.304, 0.078),
    power_off_drag=str(BASE_DIR / "Nemesis150_v4.0_RAS_CDMACH_pwrOFF.csv"),
    power_on_drag=str(BASE_DIR / "Nemesis150_v4.0_RAS_CDMACH_pwrON.csv"),
    center_of_mass_without_motor=0,
    coordinate_system_orientation="tail_to_nose",
)

rail_buttons = Nemesis.set_rail_buttons(
    upper_button_position=0.980,
    lower_button_position=-0.239,
    angular_position=0,
)

Nemesis.add_motor(Pro75M8187, position=0)

nose_cone = Nemesis.add_nose(length=0.45, kind="vonKarman", position=1.635)

fin_set = Nemesis.add_trapezoidal_fins(
    n=3,
    root_chord=0.30,
    tip_chord=0.093,
    span=0.16,
    position=-0.855,
    cant_angle=0,
    sweep_angle=58,
)

tail = Nemesis.add_tail(
    top_radius=0.075, bottom_radius=0.046, length=0.116, position=-1.155,
)

# Rocket information
# --- Remove comment to display rocket info ---
# 
# Nemesis.all_info()

Main = Nemesis.add_parachute(
    "Main",
    cd_s=0.97 * 10.5070863,
    trigger=simulator_check_main_opening,
    sampling_rate=sampling_rate,
    lag=1.73,
    noise=(0, 6.5, 0.3),
)

Drogue = Nemesis.add_parachute(
    "Drogue",
    cd_s=0.97 * 0.6566929,
    trigger=simulator_check_drogue_opening,
    sampling_rate=sampling_rate,
    lag=1.73,
    noise=(0, 6.5, 0.3),
)

# ----------------------------------------------------------------------
# WRAPPER FOR DRAG CURVES (AIRBRAKES)
# ----------------------------------------------------------------------
class DragCurveWithAirbrakes:
    """
    Adds extra Cd when the airbrakes are open.
    """

    def __init__(self, base_curve, controller, extra_cd):
        self.base_curve = base_curve
        self.controller = controller
        self.extra_cd = extra_cd

    def get_value_opt(self, mach):
        base_cd = self.base_curve.get_value_opt(mach)
        if self.controller.airbrakes_deployed:
            return base_cd + self.extra_cd
        else:
            return base_cd

    def __call__(self, mach):
        try:
            base_cd = self.base_curve(mach)
        except TypeError:
            base_cd = self.base_curve.get_value_opt(mach)

        if self.controller.airbrakes_deployed:
            return base_cd + self.extra_cd
        else:
            return base_cd

    def __getattr__(self, name):
        return getattr(self.base_curve, name)
    

# ----------------------------------------------------------------------
# PHYSICS MODELS (GRAVITY & MAGNETIC)
# ----------------------------------------------------------------------
def compute_gravity_vector(latitude_deg, altitude_m):
    """
    Calculate the local gravity vector (down) based on Latitude and Altitude.
    Model: WGS84 Ellipsodal gravity + inverse square law for altitude.
    Returns: numpy vector [gx, gy, gz] in the inertial frame (ENU: Z is active).
    """
    # Constants WGS84
    g_e = 9.7803253359      # Gravity acceleration at the equator [m/s²]
    k = 0.00193185265241    # Somigliana's formula constant (relates polar/equatorial gravity)
    e2 = 0.00669437999014   # First eccentricity squared of WGS84 ellipsoid
    R_e = 6378137.0         # Earth's equatorial radius [m]

    sin_lat = np.sin(np.radians(latitude_deg))
    
    # Somigliana's formula for gravity at sea level at given latitude
    g_loc_0 = g_e * (1 + k * sin_lat**2) / np.sqrt(1 - e2 * sin_lat**2)
    
    # Altitude correction (Inverse Square Law)
    # g decreases as it goes up. Since Z is "up", the vector is [0, 0, -g]
    g_h = g_loc_0 * (R_e / (R_e + altitude_m))**2
    
    return np.array([0.0, 0.0, -g_h])

def compute_magnetic_field(latitude_deg, longitude_deg, altitude_m):
    """
    Estimate the magnetic field vector (North, East, Down) using an Inclined Dipole model.
    Return: numpy vector [Bx, By, Bz] in the local inertial frame (ENU).
    Note: For maximum precision you would need the 'geomag' library (WMM2020), but this is enough to simulate vector dynamics.
    """
    # Approximate location (latitude and longitude) of the North Magnetic Pole (year 2025)
    mag_north_lat = 86.50
    mag_north_lon = 164.04
    
    # Earth Radius
    R_e = 6371000.0 
    r = R_e + altitude_m
    
    # Conversion to spherical coordinates (radians)
    lat_rad = np.radians(latitude_deg)
    lon_rad = np.radians(longitude_deg)
    pole_lat_rad = np.radians(mag_north_lat)
    pole_lon_rad = np.radians(mag_north_lon)

    # Geomagnetic coordinate calculation (pole shift)
    # Simplification of the rotated coaxial dipole
    clat = np.cos(lat_rad)                      # Cosine of geographic latitude
    slat = np.sin(lat_rad)                      # Sine of geographic latitude
    cpole = np.cos(pole_lat_rad)                # Cosine of magnetic pole latitude
    spole = np.sin(pole_lat_rad)                # Sine of magnetic pole latitude
    cdeltalon = np.cos(lon_rad - pole_lon_rad)  # Cosine of longitude difference from magnetic pole
    
    sin_mag_lat = slat * spole + clat * cpole * cdeltalon
    mag_lat = np.arcsin(sin_mag_lat) # Geomagnetic latitude
    
    # Field intensity at the magnetic equator (Tesla) ~ 31000 nT
    B0 = 31.0e-6 
    
    # Distance-dependent dipole intensity (1/r^3) and magnetic lat
    # B_r = -2 * B0 * (Re/r)^3 * sin(mag_lat)
    # B_theta = B0 * (Re/r)^3 * cos(mag_lat)
    
    scale = B0 * (R_e / r)**3
    Br = -2 * scale * np.sin(mag_lat)      # Radial Component (Magnetic Up/Down)
    Bt = scale * np.cos(mag_lat)           # Tangential Component (Magnetic North)
    
    # Now we need to project Br and Bt (which are in the geomagnetic frame) 
    # in the local geographic frame (North, East, Down).
    # This is an estimate: we assume that the local Magnetic North diverges from the True North
    # for the approximate declination angle.
    
    # Calculation Approximate declination (angle between True North and Magnetic North)
    y = np.sin(pole_lon_rad - lon_rad) * np.cos(pole_lat_rad)
    x = np.cos(lat_rad) * np.sin(pole_lat_rad) - np.sin(lat_rad) * np.cos(pole_lat_rad) * np.cos(pole_lon_rad - lon_rad)
    declination = np.arctan2(y, x)
    
    # Components in the NED frame (North, East, Down)
    # B_north = Bt * cos(declination)
    # B_east  = Bt * sin(declination)
    # B_down  = -Br (since Br is outgoing radial, and Down is incoming)
    
    B_north = Bt * np.cos(declination)
    B_east = Bt * np.sin(declination)
    B_down = -Br 
    
    # Final conversion from NED to ENU (East-North-Up) using RocketPy/Matplotlib alone
    # ENU X = East
    # ENU Y = North
    # ENU Z = Up = -Down
    
    B_enu = np.array([B_east, B_north, -B_down])
    
    # Returns the value in Tesla [T]
    return B_enu

# ----------------------------------------------------------------------
# REAL-TIME CONTROLLER (plot + CSV logging at 20 Hz)
# ----------------------------------------------------------------------
class RealTimeController:
    def __init__(self, rocket, environment, motor,
                 target_speed=1.0, refresh_rate=10, extra_cd=1.0,
                 csv_target_rate=50.0, csv_path=None):
        """
        rocket: Rocket instance (Nemesis)
        environment: Environment instance
        motor: SolidMotor instance (Pro75M8187)
        target_speed: 1.0 = simulation time ≈ real time
        refresh_rate: plot refresh rate in Hz
        extra_cd: additional Cd when airbrakes are open
        csv_target_rate: logging rate in Hz for CSV    -------------IMPORTANT--------------
        csv_path: path to CSV file
        """
        self.rocket = rocket
        self.environment = environment
        self.motor = motor
        self.target_speed = target_speed

        # --- TIME / PLOTTING MANAGEMENT ---
        self.last_plot_time = 0.0
        self.plot_interval = 1.0 / refresh_rate

        self.airbrakes_deployed = False
        self.start_wall_time = None
        self.current_extension = 0.0   # Actual phisical state (da 0.0 a 1.0)
        self.actuator_speed = 0.5 # 1/seconds to fully open/close

        # --- AERODYNAMIC PARAMETER ---
        self.extra_cd = extra_cd

        # Original curves
        self.base_power_off_drag = rocket.power_off_drag
        self.base_power_on_drag = rocket.power_on_drag

        # Wrap curves adding Cd when airbrakes are open
        rocket.power_off_drag = DragCurveWithAirbrakes(
            self.base_power_off_drag, self, self.extra_cd
        )
        rocket.power_on_drag = DragCurveWithAirbrakes(
            self.base_power_on_drag, self, self.extra_cd
        )

        # --- LOGGING VARIABLES FOR PLOTS (at 10 Hz) ---
        self.time_log = []
        self.alt_log = []
        self.vx_log = []
        self.vy_log = []
        self.vz_log = []
        self.x_log = []
        self.y_log = []
        self.z_log = []

        self.x_ab_log = []
        self.y_ab_log = []
        self.z_ab_log = []

        # Log for color mapping
        self.ab_val_log = []

        self.z_max_real = 4000.0

        # --- LOGGING DATA TO CSV FILE AT 20 Hz ---
        self.csv_interval = 1.0 / csv_target_rate
        self.last_csv_time = -np.inf

        self.csv_data = []

        # File / writer for streaming CSV
        self.csv_file = None
        self.csv_writer = None
        if csv_path is not None:
            self.csv_file = open(csv_path, "w", newline="")
            self.csv_writer = csv.writer(self.csv_file)

            # --- COLUMN NAMES (SECOND HEADER ROW) ---
            header = [
                # Calibrations
                "calibration_sys", "calibration_gyro", "calibration_accel", "calibration_mag",
                # Orientations
                "orientation_x", "orientation_y", "orientation_z",
                #Angular velocities
                "angular_velocity_x", "angular_velocity_y", "angular_velocity_z",
                # Linear accelerations
                "linear_acceleration_x", "linear_acceleration_y", "linear_acceleration_z",
                # Total Accelerations (Gravity + linear)
                "acceleration_x", "acceleration_y", "acceleration_z",
                # Gravity components
                "gravity_x", "gravity_y", "gravity_z",
                # Magnetic field components
                "magnetometer_x", "magnetometer_y", "magnetometer_z",
                # Quaternions
                "quaternion_w", "quaternion_x", "quaternion_y", "quaternion_z",
                # Barometer readings
                "pressure", "temperature", "altitude",
                # Time 
                "timestamp"
            ]

            # --- CATEGORY NAMES (FIRST HEADER ROW) ---
            categories = [
                # Calibrations
                "Calibration (sys)", "Calibration (gyro)", "Calibration (accel)", "Calibration (mag)",
                # Orientations
                "Roll [deg]", "Pitch [deg]", "Yaw [deg]",
                #Angular velocities
                "Angular velocity (x)", "Angular velocity (y)", "Angular velocity (z)",
                # Linear accelerations
                "Linear acceleration (x)", "Linear acceleration (y)", "Linear acceleration (z)",
                # Accelerations (Gravity + linear)
                "Acceleration (x)", "Acceleration (y)", "Acceleration (z)",
                # Gravity components
                "Gravity (x)", "Gravity (y)", "Gravity (z)",
                # Magnetic field components
                "Magnetometer (x)", "Magnetometer (y)", "Magnetometer (z)",
                # Quaternions
                "Quaternion (w)", "Quaternion (x)", "Quaternion (y)", "Quaternion (z)",
                # Barometer readings
                "Pressure [Pa]", "Temperature [K]", "Altitude [m]",
                # Time 
                "Time [s]"
            ]

            # Safety check: they must have same length
            assert len(categories) == len(header), "Category row and header row length mismatch"

            # Write first the category row, then the actual header row
            self.csv_writer.writerow(categories)
            self.csv_writer.writerow(header)
            self.csv_file.flush()
            print(f"complete CSV logging at {csv_target_rate} Hz -> {csv_path}")

        # --- INTERACTIVE GRAPHICS ---
        plt.ion()

        self.fig = plt.figure(figsize=(14, 9))
        try:
            self.fig.canvas.manager.set_window_title('Telemetry Dashboard')
        except Exception:
            pass

        # Axes
        self.ax1 = self.fig.add_subplot(2, 2, 1)
        self.ax2 = self.fig.add_subplot(2, 2, 3, sharex=self.ax1)
        self.ax_3d = self.fig.add_subplot(2, 2, 2, projection='3d')
        self.ax_xy = self.fig.add_subplot(2, 2, 4)

        self.fig.canvas.mpl_connect("key_press_event", self.toggle_airbrakes)

        # --------- Altitude plot (ax1) ---------
        (self.line_alt,) = self.ax1.plot([], [], 'k-', label='Altitude (m)')
        self.ax1.set_ylabel("z [m]")
        self.ax1.set_xlabel("Time of the simulation [s]")
        self.ax1.grid(True)
        self.ax1.legend(loc='upper right')
        self.ax1.set_title("Altitude")

        # --------- Velocity components plot (ax2) ---------
        (self.line_vx,) = self.ax2.plot([], [], 'r-', label='Vx (m/s)')
        (self.line_vy,) = self.ax2.plot([], [], 'g-', label='Vy (m/s)')
        (self.line_vz,) = self.ax2.plot([], [], 'b-', label='Vz (m/s)')

        self.ax2.set_ylabel("Velocity [m/s]")
        self.ax2.set_xlabel("Time of the simulation [s]")
        self.ax2.grid(True)
        self.ax2.legend(loc='upper right')
        self.ax2.set_title("Velocity components")

        # --------- 3D trajectory (ax_3d) ---------
        self.ax_3d.set_xlabel("x [m]")
        self.ax_3d.set_ylabel("y [m]")
        self.ax_3d.set_zlabel("z [m]")
        self.ax_3d.set_title("3D trajectory (Color = Airbrakes %)")

        # Initialize Scatter for 3D
        # We use a colormap (cmap) 'turbo' or 'jet' or 'coolwarm'
        # vmin=0 (closed/blue), vmax=1 (open/red)
        self.scat_3d = self.ax_3d.scatter([], [], [], c=[], cmap='jet', vmin=0, vmax=1, s=0.5)

        self.ax_3d.legend(loc='upper right')
        self.ax_3d.set_xlim(-2000, 2000)
        self.ax_3d.set_ylim(-2000, 2000)
        self.ax_3d.set_zlim(0, self.z_max_real)
        self.ax_3d.set_box_aspect((1, 1, 1))

        real_ticks = np.linspace(0, self.z_max_real, 5)
        self.ax_3d.set_zticks(real_ticks)
        self.ax_3d.set_zticklabels([f"{v:.0f}" for v in real_ticks])

        # --------- Ground track x-y (ax_xy) ---------
        self.ax_xy.set_xlabel("x [m]")
        self.ax_xy.set_ylabel("y [m]")
        self.ax_xy.set_title("Ground Track (x–y)")
        self.ax_xy.grid(True)

        self.scat_xy = self.ax_xy.scatter([], [], c=[], cmap='jet', vmin=0, vmax=1, s=0.5)

        self.ax_xy.legend(loc='upper right')
        self.ax_xy.set_xlim(-2000, 2000)
        self.ax_xy.set_ylim(-2000, 2000)

        # Colorbar
        cbar_ax = self.fig.add_axes([0.92, 0.15, 0.02, 0.7])
        self.cbar = self.fig.colorbar(self.scat_3d, cax=cbar_ax)
        self.cbar.set_label('Airbrake Extension (0.0 - 1.0)')

        # --------- Live status text ---------
        self.status_text = self.ax1.text(
            0.05, 0.9, "PRE-LAUNCH",
            transform=self.ax1.transAxes,
            bbox=dict(facecolor='white', alpha=0.8)
        )

        # --------- Airbrake status text ---------
        self.ab_text = self.fig.text(0.5, 0.98, "AIRBRAKES: 0%",
            ha="center", va="top", 
            bbox=dict(facecolor='blue', alpha=0.3)
        )
        self.fig.tight_layout(rect=[0, 0, 0.9, 0.95])
        self.fig.tight_layout(rect=[0, 0, 1, 0.94])

        # Previous values for derivatives
        self.prev_time = None
        self.prev_vx = None
        self.prev_vy = None
        self.prev_vz = None

        self.prev_omega1 = None
        self.prev_omega2 = None
        self.prev_omega3 = None

    # ----------------- HELPERS -----------------
    def toggle_airbrakes(self, event):
        """
        Callback activated when the space bar is pressed.
        """
        if event.key == ' ': #spacebar
            self.airbrakes_deployed = not self.airbrakes_deployed
            print(f"| COMMAND: Airbrakes {'OPEN' if self.airbrakes_deployed else 'CLOSE'} |")

    @staticmethod
    def quat_to_rotation_matrix(e0, e1, e2, e3):
        """
        Rotation matrix from body to inertial frame.
        """
        norm = np.sqrt(e0**2 + e1**2 + e2**2 + e3**2)
        if norm == 0:
            return np.eye(3)
        e0, e1, e2, e3 = e0 / norm, e1 / norm, e2 / norm, e3 / norm

        r00 = 1 - 2 * (e2**2 + e3**2)
        r01 = 2 * (e1 * e2 - e0 * e3)
        r02 = 2 * (e1 * e3 + e0 * e2)

        r10 = 2 * (e1 * e2 + e0 * e3)
        r11 = 1 - 2 * (e1**2 + e3**2)
        r12 = 2 * (e2 * e3 - e0 * e1)

        r20 = 2 * (e1 * e3 - e0 * e2)
        r21 = 2 * (e2 * e3 + e0 * e1)
        r22 = 1 - 2 * (e1**2 + e2**2)

        return np.array([[r00, r01, r02],
                         [r10, r11, r12],
                         [r20, r21, r22]])
         
    @staticmethod 
    def quat_to_euler(e0, e1, e2, e3):
        """
        Gives roll, pitch and yaw angles (in degrees) recalling Rocketpy functions
          roll  = φ (Spin Angle)
          pitch = θ (Nutation Angle)
          yaw   = ψ (Precession Angle)
        """

        # I guarantee they are 1D arrays of length 1
        e0_arr = np.atleast_1d(float(e0))
        e1_arr = np.atleast_1d(float(e1))
        e2_arr = np.atleast_1d(float(e2))
        e3_arr = np.atleast_1d(float(e3))

        # Vector [e1,e2,e3] for nutation (like RocketPy does in theta())
        e_vec_arr = np.column_stack([e1_arr, e2_arr, e3_arr])  # shape (1, 3)

        # 1) Spin angle φ (Roll) - 4 arguments
        roll_arr = quaternions_to_spin(e0_arr, e1_arr, e2_arr, e3_arr)

        # 2) Nutation angle θ (Pitch) - 2 arguments: e0, [e1,e2,e3]
        pitch_arr = quaternions_to_nutation(e1_arr, e2_arr)

        # 3) Precession angle ψ (Yaw) - 4 arguments
        yaw_arr = quaternions_to_precession(e0_arr, e1_arr, e2_arr, e3_arr)

        # I extract the first element and convert it to float (no ndarray)
        roll  = float(np.asarray(roll_arr).reshape(-1)[0])
        pitch = float(np.asarray(pitch_arr).reshape(-1)[0])
        yaw   = float(np.asarray(yaw_arr).reshape(-1)[0])

        return roll, pitch, yaw # degrees

    # ------------------------------------------------------------------
    # REAL-TIME CONTROL (CALLED BY ROCKETPY)
    # ------------------------------------------------------------------
    def control_loop(
        self,
        sim_time,
        sampling_rate,
        state,
        state_history,
        observed_variables,
        interactive_objects,
    ):
        """
        Control function called by RocketPy at ~sampling_rate Hz.
        Returns airbrake deployment level (0-1).
        """
        from __main__ import drogue_deployed, main_deployed

        t = sim_time

        # Extract full state vector from Rocketpy
        x, y, z = state[0], state[1], state[2]
        vx, vy, vz = state[3], state[4], state[5]
        e0, e1, e2, e3 = state[6], state[7], state[8], state[9]
        omega1, omega2, omega3 = state[10], state[11], state[12]

        # Airbrake signal (0 or 1; controller can be extended to analog later)
        airbrake_ext = 1.0 if self.airbrakes_deployed else 0.0

        # 1. Real-time timer initialization
        if self.start_wall_time is None:
            self.start_wall_time = pytime.time()
            self.prev_time = t
            self.prev_vx = vx
            self.prev_vy = vy
            self.prev_vz = vz
            self.prev_omega1 = omega1
            self.prev_omega2 = omega2
            self.prev_omega3 = omega3
            print(">>> LAUNCH DETECTED - DISPLAY ACTIVE - "
                  "PRESS SPACEBAR TO ACTIVATE AIRBRAKES <<<")

        # 2. Time synchronization (approximate real-time)
        wall_elapsed = pytime.time() - self.start_wall_time
        sim_target_time = wall_elapsed * self.target_speed

        if t > sim_target_time:
            sleep_duration = (t - sim_target_time) / self.target_speed
            if sleep_duration > 0.001:
                pytime.sleep(sleep_duration)

        # --- ACTUATOR DYNAMICS (Proportional Sim) ---
        dt = t - self.prev_time if (self.prev_time and t > self.prev_time) else 0.0
        
        target = 1.0 if self.airbrakes_deployed else 0.0
        step = self.actuator_speed * dt
        
        if self.current_extension < target:
            self.current_extension = min(target, self.current_extension + step)
        elif self.current_extension > target:
            self.current_extension = max(target, self.current_extension - step)

        # 3. Calculations + CSV log at ~csv_target_rate
        if (t - self.last_csv_time) >= self.csv_interval:
            self.last_csv_time = t

            # --- TIME STEP FOR DERIVATIVES ---
            dt = t - self.prev_time if (self.prev_time is not None and t > self.prev_time) else 0.0

            # --- CALIBRATIONS (MOCKED) ---
            cal_sys = 3
            cal_gyro = 3
            cal_accel = 3
            cal_mag = 3

            # --- ORIENTATIONS (EULAR ANGLES) ---
            roll, pitch, yaw = self.quat_to_euler(e0, e1, e2, e3)
            
            # --- ENVIRONMENT / ATMOSPHERE (geodetic altitude) ---
            lat_base = self.environment.latitude
            lon_base = self.environment.longitude
            elev_base = self.environment.elevation
            geodetic_alt = elev_base + z

            try:
                pressure = self.environment.pressure(geodetic_alt)
                temperature = self.environment.temperature(geodetic_alt)
                density = self.environment.density(geodetic_alt)
                speed_of_sound = self.environment.speed_of_sound(geodetic_alt)
                wind_vx = self.environment.wind_velocity_x(geodetic_alt)
                wind_vy = self.environment.wind_velocity_y(geodetic_alt)
            except Exception:
                # Simple ISA-like fallback + no wind
                pressure = 101325.0 * np.exp(-geodetic_alt / 8500.0)
                temperature = 288.15 - 0.0065 * geodetic_alt
                density = pressure / (287.05 * temperature)
                speed_of_sound = np.sqrt(1.4 * 287.05 * temperature)
                wind_vx = 0.0
                wind_vy = 0.0

            # --- GEODETIC COORDINATES (approximate flat-Earth) ---
            meters_per_degree_lat = 111320.0
            meters_per_degree_lon = 111320.0 * np.cos(np.radians(lat_base))

            latitude = lat_base + y / meters_per_degree_lat
            longitude = lon_base + x / meters_per_degree_lon
            altitude_geod = geodetic_alt

            # --- AIR-RELATIVE VELOCITY AND SPEED ---
            vrx = vx - wind_vx
            vry = vy - wind_vy
            vrz = vz  # assuming no vertical wind component

            airspeed = np.sqrt(vrx**2 + vry**2 + vrz**2)
            speed = airspeed  # not currently logged, but kept if needed later

            # --- INERTIAL ACCELERATIONS (finite differences) ---
            if dt > 0.0 and self.prev_vx is not None:
                ax_I = (vx - self.prev_vx) / dt
                ay_I = (vy - self.prev_vy) / dt
                az_I = (vz - self.prev_vz) / dt
            else:
                ax_I = ay_I = az_I = 0.0

            # --- ROTATION MATRIX ---
            R = self.quat_to_rotation_matrix(e0, e1, e2, e3)

            # --- GRAVITY VECTOR (Assumed constant) ---
            # Inertial frame gravity vector (m/s²)
            g_inertial = compute_gravity_vector(latitude, altitude_geod)
            # Body frame gravity vector
            g_body = R.T @ g_inertial
            gx_b, gy_b, gz_b = g_body

            # --- 2. MAGNETIC FIELD VECTOR (Inertial & Body) ---
            # B inertial frame (based on lat/lon/alt)
            mag_inertial = compute_magnetic_field(latitude, longitude, altitude_geod)
            # B body frame
            mag_body = R.T @ mag_inertial
            mag_x, mag_y, mag_z = mag_body

            # microTesla (μT) conversion (optional)
            mag_x = mag_x * 1e6
            mag_y = mag_y * 1e6
            mag_z = mag_z * 1e6

            # --- BODY-FRAME ACCELERATIONS ---
            a_body = R.T @ np.array([ax_I, ay_I, az_I])
            ax_b, ay_b, az_b = a_body

            # --- TOTAL ACCELERATIONS (gravity + linear) ---
            atot_x = ax_b + gx_b
            atot_y = ay_b + gy_b
            atot_z = az_b + gz_b

            # --- BODY-FRAME VELOCITY (inertial velocity expressed in body axes) ---
            v_body = R.T @ np.array([vx, vy, vz])
            vx_b, vy_b, vz_b = v_body

            # Update previous linear quantities
            self.prev_time = t
            self.prev_vx = vx
            self.prev_vy = vy
            self.prev_vz = vz

            # --- DYNAMIC PRESSURE (not logged but may be useful) ---
            dynamic_pressure = 0.5 * density * airspeed**2

            # Update previous angular rates
            self.prev_omega1 = omega1
            self.prev_omega2 = omega2
            self.prev_omega3 = omega3

            # --- DEPLOYMENT STATES ---
            airbrakes_state = 1 if self.airbrakes_deployed else 0
            drogue_state = 1 if drogue_deployed else 0
            main_state = 1 if main_deployed else 0

            # --- BUILD CSV ROW (MATCHES HEADER ABOVE) ---
            row = [
                cal_sys, cal_gyro, cal_accel, cal_mag,
                f"{roll:.4f}", f"{pitch:.4f}", f"{yaw:.4f}", # Orientations
                f"{omega1:.4f}", f"{omega2:.4f}", f"{omega3:.4f}", # Ang. Vel.
                f"{ax_b:.4f}", f"{ay_b:.4f}", f"{az_b:.4f}", # Lin. Acc.
                f"{atot_x:.4f}", f"{atot_y:.4f}", f"{atot_z:.4f}", # Total Acc.
                f"{gx_b:.4f}", f"{gy_b:.4f}", f"{gz_b:.4f}", # Gravity Vector
                f"{mag_x:.4f}", f"{mag_y:.4f}", f"{mag_z:.4f}", # Magnetometer
                f"{e0:.6f}", f"{e1:.6f}", f"{e2:.6f}", f"{e3:.6f}", # Quaternions
                f"{pressure:.2f}" ,f"{temperature:.2f}", f"{altitude_geod:.2f}", # Ambient
                f"{t:.4f}" # Time
            ]

            # Optional in-memory storage
            self.csv_data.append(row)

            # Streaming write to CSV
            if self.csv_writer is not None:
                self.csv_writer.writerow(row)
                self.csv_file.flush()

        # 4. Plot update (~refresh_rate)
        if (t - self.last_plot_time) >= self.plot_interval:
            self.last_plot_time = t

            # Logs for plots
            self.time_log.append(t)
            self.alt_log.append(z)
            self.vx_log.append(vx)
            self.vy_log.append(vy)
            self.vz_log.append(vz)
            self.x_log.append(x)
            self.y_log.append(y)
            self.z_log.append(z)

            # Append current extension level for color
            self.ab_val_log.append(self.current_extension)

            # Plot 1 and 2

            self.line_alt.set_data(self.time_log, self.alt_log)

            self.line_vx.set_data(self.time_log, self.vx_log)
            self.line_vy.set_data(self.time_log, self.vy_log)
            self.line_vz.set_data(self.time_log, self.vz_log)

            self.ax1.relim()
            self.ax1.autoscale_view()

            self.ax2.relim()
            self.ax2.autoscale_view()

            # Plot 3 and 4 (Scatter with Color)
            # Ground track
            self.scat_xy.set_offsets(np.c_[self.x_log, self.y_log])
            self.scat_xy.set_array(np.array(self.ab_val_log))
            
            # 3D
            self.scat_3d._offsets3d = (self.x_log, self.y_log, self.z_log)
            self.scat_3d.set_array(np.array(self.ab_val_log))

            # Texts
            self.status_text.set_text(f"T+: {t:.2f}s | Alt: {z:.0f}m | Vz: {vz:.0f}m/s")
            
            pct = int(self.current_extension * 100)
            color_intensity = self.current_extension
            # Text background changes from blue to red
            self.ab_text.set_text(f"AIRBRAKES: {pct}%")
            self.ab_text.set_bbox(dict(facecolor=plt.cm.jet(color_intensity), alpha=0.5))

            plt.pause(0.001)

        return airbrake_ext

    def close(self):
        """Close CSV file (call after the simulation ends)."""
        if self.csv_file is not None:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None


# ----------------------------------------------------------------------
# LINKING CONTROLLER TO AIRBRAKES
# ----------------------------------------------------------------------
csv_path = BASE_DIR / "flight_telemetry_50Hz_v8.csv"

controller = RealTimeController(
    rocket=Nemesis,
    environment=env,  # pass environment for atmospheric data
    motor=Pro75M8187,
    target_speed=8.0,
    refresh_rate=10,
    extra_cd=1.5,
    csv_target_rate=50.0,
    csv_path=csv_path,
)


def airbrakes_drag_function(deployment_level, mach):
    """
    Computes the additional Cd from the airbrakes.
    """
    base_drag_added = 0.0
    return base_drag_added * deployment_level


Nemesis.add_air_brakes(
    drag_coefficient_curve=airbrakes_drag_function,
    controller_function=controller.control_loop,
    sampling_rate=sampling_rate,
    clamp=True,
)

print("Setup completed. Starting Flight...")

# ----------------------------------------------------------------------
# RUN REAL-TIME SIMULATION
# ----------------------------------------------------------------------
test_flight = Flight(
    rocket=Nemesis,
    environment=env,
    rail_length=12,
    inclination=84,
    heading=144,
)

# Close CSV file
controller.close()
print(f"CSV saved at: {csv_path}")


# ----------------------------------------------------------------------
# SUMMARY: Print available flight attributes
# ----------------------------------------------------------------------
print("\n>>> AVAILABLE ATTRIBUTES IN THE FLIGHT OBJECT <<<")
flight_attrs = [attr for attr in dir(test_flight) if not attr.startswith('_')]
print("Available attributes/methods:")
for attr in sorted(flight_attrs):
    print(f"  - {attr}")

# ----------------------------------------------------------------------
# POST-PROCESSING
# ----------------------------------------------------------------------
plt.ioff()
plt.show()

test_flight.export_kml(
    file_name=str(BASE_DIR / "trajectory_reanalysis_v8.kml"),
    extrude=True,
    altitude_mode="relative_to_ground",
)

print("\n>>> SIMULATION COMPLETED <<<")
print("Generated files:")
print(f"  1. {csv_path} (real-time data at 50 Hz)")
print(f"  2. {BASE_DIR / 'trajectory_reanalysis_v8.kml'} (KML trajectory)")

# # # ----------------------------------------------------------------------
# # # DATA COMPARISON: RELATIVE ERRORS (%)
# # # ----------------------------------------------------------------------

# def get_rocketpy_gravity_body_frame(flight_obj, t_array):
#     """
#     Calculate the gravity vector projected onto the rocket axes (Body Frame)
#     using RocketPy's exact environment model.
#     """
#     z = flight_obj.z(t_array)
#     e0 = flight_obj.e0(t_array)
#     e1 = flight_obj.e1(t_array)
#     e2 = flight_obj.e2(t_array)
#     e3 = flight_obj.e3(t_array)
#     g_magnitude = flight_obj.env.gravity(z)
    
#     # Inertial vector rotation [0, 0, -g] in the body frame
#     gx_body = 2 * (e1 * e3 - e0 * e2) * (-g_magnitude)
#     gy_body = 2 * (e2 * e3 + e0 * e1) * (-g_magnitude)
#     gz_body = (1 - 2 * (e1**2 + e2**2)) * (-g_magnitude)
#     return gx_body, gy_body, gz_body


# def get_rocketpy_accel_body_frame(flight_obj, t_array):
#     """
#     Calculate the linear acceleration vector projected onto the rocket axes (Body Frame)
#     using RocketPy's inertial accelerations and quaternions.
    
#     Returns the body-frame accelerations (ax_body, ay_body, az_body).
#     """
#     # Get inertial frame accelerations from RocketPy
#     ax_I = flight_obj.ax(t_array)
#     ay_I = flight_obj.ay(t_array)
#     az_I = flight_obj.az(t_array)
    
#     # Get quaternions
#     e0 = flight_obj.e0(t_array)
#     e1 = flight_obj.e1(t_array)
#     e2 = flight_obj.e2(t_array)
#     e3 = flight_obj.e3(t_array)
    
#     # Transform from inertial to body frame using R^T (transpose of rotation matrix)
#     # R^T row 1: [1-2(e2²+e3²), 2(e1e2+e0e3), 2(e1e3-e0e2)]
#     # R^T row 2: [2(e1e2-e0e3), 1-2(e1²+e3²), 2(e2e3+e0e1)]
#     # R^T row 3: [2(e1e3+e0e2), 2(e2e3-e0e1), 1-2(e1²+e2²)]
    
#     ax_body = (1 - 2*(e2**2 + e3**2)) * ax_I + 2*(e1*e2 + e0*e3) * ay_I + 2*(e1*e3 - e0*e2) * az_I
#     ay_body = 2*(e1*e2 - e0*e3) * ax_I + (1 - 2*(e1**2 + e3**2)) * ay_I + 2*(e2*e3 + e0*e1) * az_I
#     az_body = 2*(e1*e3 + e0*e2) * ax_I + 2*(e2*e3 - e0*e1) * ay_I + (1 - 2*(e1**2 + e2**2)) * az_I
    
#     return ax_body, ay_body, az_body


# def compare_telemetry(flight_obj, csv_path):
#     print("\n>>> STARTING ANALYSIS: RELATIVE ERRORS (DYNAMICS + ATMOSPHERE + GRAVITY + ACCELERATIONS) <<<")
#     try:
#         df = pd.read_csv(csv_path, header=1, skipinitialspace=True)
#     except FileNotFoundError:
#         print(f"Error: {csv_path} not found."); return

#     # Columns needed (including gravity and accelerations)
#     cols_needed = [
#         'orientation_x', 'orientation_y', 'orientation_z', 
#         'altitude', 'pressure', 'temperature', 'timestamp', 
#         'gravity_x', 'gravity_y', 'gravity_z',
#         'linear_acceleration_x', 'linear_acceleration_y', 'linear_acceleration_z',
#         'acceleration_x', 'acceleration_y', 'acceleration_z'
#     ]
#     for col in cols_needed:
#         if col in df.columns: 
#             df[col] = pd.to_numeric(df[col], errors='coerce')
#     df.dropna(subset=['timestamp'], inplace=True)
#     if len(df) == 0: 
#         print("Error: No valid data found."); return
    
#     t_log = df['timestamp'].values
    
#     # Data from RocketPy (angles, altitude, pressure and temperature)
#     rpy_roll = flight_obj.phi(t_log)
#     rpy_pitch = flight_obj.theta(t_log)
#     rpy_yaw = flight_obj.psi(t_log)
#     rpy_z = flight_obj.z(t_log) + env.elevation
#     rpy_p = flight_obj.pressure(t_log)
#     rpy_T = flight_obj.env.temperature(flight_obj.z(t_log))
    
#     # Gravity (body frame)
#     rpy_gx, rpy_gy, rpy_gz = get_rocketpy_gravity_body_frame(flight_obj, t_log)
    
#     # Linear accelerations (body frame)
#     rpy_ax_lin, rpy_ay_lin, rpy_az_lin = get_rocketpy_accel_body_frame(flight_obj, t_log)

#     # Comparison groups
#     group_orientation = {
#         "Roll":  {"csv_data": df['orientation_x'].values, "rpy_func": rpy_roll,  "units": "deg"},
#         "Pitch": {"csv_data": df['orientation_y'].values, "rpy_func": rpy_pitch, "units": "deg"},
#         "Yaw":   {"csv_data": df['orientation_z'].values, "rpy_func": rpy_yaw,   "units": "deg"},
#     }
    
#     group_atm = {
#         "Altitude":    {"csv_data": df['altitude'].values,    "rpy_func": rpy_z, "units": "m"},
#         "Pressure":    {"csv_data": df['pressure'].values,    "rpy_func": rpy_p, "units": "Pa"},
#         "Temperature": {"csv_data": df['temperature'].values, "rpy_func": rpy_T, "units": "K"} 
#     }
    
#     group_gravity = {
#         "Gravity X (Body)": {"csv_data": df['gravity_x'].values, "rpy_func": rpy_gx, "units": "m/s²"},
#         "Gravity Y (Body)": {"csv_data": df['gravity_y'].values, "rpy_func": rpy_gy, "units": "m/s²"},
#         "Gravity Z (Body)": {"csv_data": df['gravity_z'].values, "rpy_func": rpy_gz, "units": "m/s²"}
#     }
    
#     group_linear_accel = {
#         "Linear Accel X (Body)": {"csv_data": df['linear_acceleration_x'].values, "rpy_func": rpy_ax_lin, "units": "m/s²"},
#         "Linear Accel Y (Body)": {"csv_data": df['linear_acceleration_y'].values, "rpy_func": rpy_ay_lin, "units": "m/s²"},
#         "Linear Accel Z (Body)": {"csv_data": df['linear_acceleration_z'].values, "rpy_func": rpy_az_lin, "units": "m/s²"}
#     }

#     def plot_group(comparison_dict, title_text, fig_id):
#         n_rows = len(comparison_dict)
#         fig, axes = plt.subplots(n_rows, 2, figsize=(14, 4 * n_rows), sharex=True)
#         fig.suptitle(title_text, fontsize=16)
#         if n_rows == 1: 
#             axes = np.array([axes])
#         idx = 0
#         for key, data in comparison_dict.items():
#             val_manual = data["csv_data"]
#             val_rpy = data["rpy_func"]
#             with np.errstate(divide='ignore', invalid='ignore'):
#                 rel_error_pct = np.abs((val_manual - val_rpy) / val_rpy) * 100.0
#             rel_error_pct[np.abs(val_rpy) < 1e-4] = 0.0
            
#             axes[idx, 0].plot(t_log, val_manual, 'r--', label='Telemetry', lw=2)
#             axes[idx, 0].plot(t_log, val_rpy, 'k-', label='RocketPy', alpha=0.6, lw=2)
#             axes[idx, 0].set_ylabel(f"{key}\n[{data['units']}]")
#             axes[idx, 0].grid(True, linestyle='--', alpha=0.6)
#             if idx == 0: 
#                 axes[idx, 0].legend(loc='upper right')
            
#             axes[idx, 1].plot(t_log, rel_error_pct, 'b-', lw=1)
#             axes[idx, 1].set_ylabel("Rel. Error [%]")
#             axes[idx, 1].grid(True, linestyle='--', alpha=0.6)
#             axes[idx, 1].set_ylim(0, 50)
#             idx += 1
#         axes[-1, 0].set_xlabel("Time [s]")
#         axes[-1, 1].set_xlabel("Time [s]")
#         plt.tight_layout(rect=[0, 0.03, 1, 0.97])

#     # Plot all comparison groups
#     plot_group(group_orientation, "Dynamic Comparison (Orientation)", 1)
#     plot_group(group_atm, "Atmosphere Comparison", 2)
#     plot_group(group_gravity, "Gravity Vector Comparison (Body Frame)", 3)
#     plot_group(group_linear_accel, "Linear Acceleration Comparison (Body Frame)", 4)
    
#     plt.show()


# compare_telemetry(test_flight, csv_path)

# ----------------------------------------------------------------------
# COMPARISON COMMENT
# ----------------------------------------------------------------------

# The comparison was limited to five groups of parameters:
# 1. ORIENTATION (Roll, Pitch, Yaw)
# 2. ATMOSPHERIC CONDITIONS (Altitude, Pressure, Temperature)
# 3. GRAVITY VECTOR (Body Frame: Gx, Gy, Gz)
# 4. LINEAR ACCELERATIONS (Body Frame: ax, ay, az)

# These are the only quantities that were independently computed or modeled,
# rather than directly extracted from RocketPy's state vector.

# NOTE ON ORIENTATION ANGLES: This code was developed through successive
# approximations until convergence. During development, Euler angles were
# computed using custom formulations, requiring comparison with Rocketpy data 
# at each iteration to validate accuracy. In the CURRENT VERSION, angles are 
# computed by directly calling RocketPy's utility functions, making the
# comparison redundant since the calculations are now identical.

# NOTE ON ACCELERATIONS: Linear accelerations in the body frame were computed
# via finite differences of the inertial velocity components, then rotated 
# into the body frame using the quaternion-derived rotation matrix. Total
# accelerations are the sum of linear accelerations and the gravity vector
# (both independently computed). These numerical approaches may introduce 
# discrepancies compared to RocketPy's internal calculations, which are derived 
# directly from the equations of motion and discretized wrt the solving interval. 
# The comparison validates the accuracy of the finite-difference method, 
# the gravity model, and the coordinate transformations.

# The following quantities were NOT compared because:
# (a) Directly extracted from RocketPy's state vector (and thus identical);
# (b) No RocketPy reference available for comparison.

# - Position (x, y, z): Directly from state vector [state[0:2]]                             (a)

# - Velocity (vx, vy, vz): Directly from state vector [state[3:5]]                          (a)

# - Quaternions (e0, e1, e2, e3): Directly from state vector [state[6:10]]                  (a)

# - Angular Velocities (ω1, ω2, ω3): Directly from state vector [state[10:13]]              (a)

# - Magnetic Field Vector: Computed using `compute_magnetic_field()`, which is              (b)
#       an approximate dipole model. While this IS an independent computation,
#       RocketPy does not provide a built-in magnetic field model for comparison,
#       so validation would require external geomagnetic data (e.g., WMM2020).

# - Calibration values: These are mock/placeholder values (all set to 3) and                (b)
#       have no corresponding RocketPy output.