print("importing libraries...", end='\r')
# Plotting and visualization
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

# RocketPy core classes
from rocketpy import Environment, SolidMotor, Rocket, Flight, CompareFlights
from rocketpy.tools import load_monte_carlo_data
from rocketpy.sensitivity import SensitivityModel

# Time measurement utilities
from datetime import datetime
from time import process_time
import time

# Numerical computations and random sampling
import numpy as np
from numpy.random import normal, choice
from scipy.stats import norm

# File and directory management
from pathlib import Path

# Data serialization and storage
import json
import pickle

# Image loading
from imageio.v2 import imread

# 
from typing import Literal

# Motor repositories
import numpy as np
from scipy.optimize import root_scalar
import math
from rocketcea.cea_obj_w_units import CEA_Obj
from rocketcea.cea_obj import add_new_propellant
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# set path
BASE_DIR = Path(__file__).resolve().parent

output_dir_name = 'FRED_v1.5_SRAD_motor_test'

#-------------------------------------------------------------------------------------------------------- MOTOR SECTION
"""**FUNCTIONS**"""

def get_pe_over_p0_from_AeAt(AeAt, gamma):

    def fun(M):
        M = max(M, 1.001)  # no subsonic solutions
        val = (2/(gamma+1)*(1 + (gamma-1)/2*M**2))**((gamma+1)/(2*(gamma-1)))
        return (1/M)*val - AeAt

    # --- MODIFIED: STABILITY CHECK FOR M_e AND Pe_P0 --- #
    # Widened the bracket to handle higher expansion ratios safely.
    # Added a try-except block to fallback to Newton method if Brentq fails.
    try:
        sol = root_scalar(fun, bracket=[1.001, 20.0], method='brentq')
        M_e = sol.root
    except ValueError:
        sol = root_scalar(fun, x0=3.0, method='newton')
        M_e = sol.root
    # --------------------------------------------------- #

    # Pe/P0 relation, clamp to <1
    pe_p0 = min((1 + (gamma-1)/2 * M_e**2)**(-gamma/(gamma-1)), 0.9999)
    return pe_p0, M_e

"""**ENVIRONMENTAL PARAMETERS**"""

T_amb = 21+273.15   # [K] ambient temperature
P_amb=101325        # [Pa] ambient pressure
g = 9.80665         # [m/s^2] gravity acc

"""**MOTOR DESIGN**"""

Mdry = 2.086                            # [kg] empty mass of rocket

# MOTOR DESIGN

# casing
D_cc =  0.044                           #  [m] internal diameter of the casing      0.075                                       INPUT
L_cc =  0.200                           # [m] length of the casing                       0.165                                        INPUT
L_bulkhead = 0.02                       # [m] length of the bulkhead of the motor
th_casing = 0.003                       # [m] thickness of the casing
rho_casing_mat = 2700                   # [kg/m^3] Casing density (6068 T6)
yield_casing_mat = 260e6                # [Pa] Yield strength     (6068 T6)
SF_casing = 3                           # imposing safety factor for casing thickness

# 1. Casing Weight Computation
V_casing = np.pi/4 * ((D_cc + 2*th_casing)**2 - D_cc**2) * L_cc + np.pi * ((D_cc + 2*th_casing)/2)**2 * th_casing + np.pi/4 * (D_cc**2 - (D_cc - th_casing)**2) * L_bulkhead  # CHANGED
M_casing = V_casing * rho_casing_mat

# thermal protections
tp_thickness = 0.003     # thickness of the thermal protections [m]
rho_phenolic = 1500     # [kg/m^3] Thermal protection density (Phenolic - bachelite)
recession_rate = 0.0004 # [m/s] Estimated recession rate for phenolic thermal protection

# 2. Thermal Protection Weight Computation   # CHANGED
V_fw_cl = tp_thickness * np.pi * (D_cc/2)**2         # volume of the forword closure (made of thermal protections on the bulkhead of the motor)
V_tp = np.pi/4 * (D_cc**2 - (D_cc - 2*tp_thickness)**2) * L_cc + V_fw_cl  # volume of the thermal protections
M_tp = V_tp * rho_phenolic     # thermal protection mass

# nozzle
exp_ratio = 5.2                                                                                            # INPUT
D_throat = 0.01                  # [m] diameter of the throat section                                        # INPUT

conv_angle = np.deg2rad(35)  # convergent angle
div_angle  = np.deg2rad(15)  # divergent angle

A_throat = np.pi * (D_throat / 2)**2    # [m^2] throat section
A_exit = A_throat * exp_ratio           # [m^2] exit section

D_exit = 2 * np.sqrt(A_exit / np.pi)    # [m] exit diameter

L_conv = (((D_cc-2*tp_thickness)/2) - D_throat/2) / np.tan(conv_angle)  # [m] length of the convergent
L_div  = (D_exit/2 - D_throat/2) / np.tan(div_angle)                    # [m] length of the divergent

L_total = L_conv + L_div            # total length of the nozzle

eta_CF = (1 + np.cos(div_angle))/2  # divergence losses for conical nozzle

rho_nozzle_mat = 3700      # [kg/m^3] Nozzle density (Allumina)

# 3. Nozzle Weight Computation
V_nozzle = (np.pi/12) * (
    L_conv * (D_cc**2 + D_cc*D_throat + D_throat**2) +
    L_div  * (D_exit**2 + D_exit*D_throat + D_throat**2)
)   # volume is overestimated in the divergent part that is thinwalled
M_nozzle = V_nozzle * rho_nozzle_mat

"""**GRAIN CONFIGURATION**"""

card_str = """
name SORBITOL  C 6.0000  H 14.0000  O 6.0000  wt%=34.60
h,cal=-323633.566   t(k)=298.15   rho=1.490

name KNO3  K 1.0000  N 1.0000  O 3.0000  wt%=64.40
h,cal=-118186.337   t(k)=298.15   rho=2.110

name FE2O3  FE 2.0000  O 3.0000  wt%=1.00
h,cal=-197312.735   t(k)=298.15   rho=5.240
"""

add_new_propellant('KNSB_FE', card_str)

# reactants mass fractions
w = np.array([
   0.346,     # Sorbitol   purity 91%
   0.644,     # KNO3       purity 99.5% from datasheet
    0.01      # Fe2O3
])

# reactants density [kg/m^3]
rho = np.array([
    1490,   # Sorbitol
    2110,   # KNO3
    5240    # Fe2O3
])


D_ext = D_cc - 2 * tp_thickness                         # [m] external diameter of the cilindrical grain
D_int= 0.015                                            # [m] internal diameter of the cilindrical grain                                                                               # INPUT
n_grains = 1                                            # number of cilindrical grains                                                                                                 # INPUT
grains_distance = 0.002                                 # [m] keep it also with 1 grain to let the basis burn
L_single_grain = ((L_cc - L_conv - tp_thickness - L_bulkhead)-(n_grains+1)*grains_distance)/n_grains   # CHANGED


rho_mix = 1.0 / np.sum(w / rho)
V_grain = n_grains * np.pi * ((D_ext/2)**2 - (D_int/2)**2) * L_single_grain   # [m^3] grain volume
M_mix = V_grain * rho_mix     # this value is only theoretical and it is the one we want to reach [kg]


M_pr=M_mix                     # [kg] once we make the grains in the lab, their real mass is then known (subtract the weight of any other material used to shape them)

rho_quality = M_pr/M_mix                # density ratio (quality), if less then 0.9 it is not good
rho_pr = rho_quality * rho_mix          # [kg/m^3] solid propellant density

# Vieille parameters
a_psig_cm= 0.146                        # [cm/sec * psig^-n] for KNDX doped with red iron oxid
n= 0.342                                # for KNDX doped with red iron oxid
a=(a_psig_cm * (1/6894.757) ** n)/100   # converted into [m/sec * Pa^-n]

# Combustion
eta_comb = 0.85               # https://drive.google.com/file/d/1Ty7f5tD8JdtLnNn2mRNsAeE03-D1Lo25/view?usp=drive_link
cea = CEA_Obj(
    propName='KNSB_FE',
    isp_units='sec',
    cstar_units='m/s',
    pressure_units='Pa',
    temperature_units='K',
    sonic_velocity_units = 'm/sec',
    )

rocket_dry_mass = Mdry + M_nozzle + M_tp + M_casing

"""**MOTOR DIMENSIONS**"""

print(f"-------------------PROPELLANT MASS------------------------")
print("\n")
print(f"Theoretical Propellant mass = {M_mix:.4f} [kg]")
print(f"Real propellant mass = {M_pr:.4f} [kg]")
print(f"Density ratio = {rho_quality:.4f}     (if less then 0.9 it is not good)")
print("\n")
print(f"------------------PROPELLANT MIX--------------------------")
print("\n")
print(f"Theoretical mass +5% = {M_mix*1.05:.4f} [kg]            Total mass of propellant for the casting")
print(f"Theoretical SORBITOL mass +5% = {M_mix*1.05*w[0]:.4f} [kg]   Total mass of SORBITOL for the casting")
print(f"Theoretical KNO3 mass +5% = {M_mix*1.05*w[1]:.4f} [kg]       Total mass of KNO3 for the casting")
print(f"Theoretical Fe2O3 mass +5% = {M_mix*1.05*w[2]:.4f}  [kg]      Total mass of Fe2O3 for the casting")
print("\n")
print("--------------------GRAIN GEOMETRY-------------------------")
print("\n")
print(f"Number of grains = {n_grains:.2f}")
print(f"Length of the single grain = {L_single_grain:.4f} [m]")
print(f"External diameter of the grain = {D_ext:.4f}  [m]")
print(f"Internal diameter of the grain = {D_int:.4f}  [m]")
print(f"Distance between the grains = {grains_distance:.4f} [m]")
print("\n")
print("----------------------CASING GEOMETRY---------------------")
print("\n")
print(f"Length of the casing = {L_cc:.4f} [m]")
print(f"Internal diameter of the casing = {D_cc}  [m]")
print(f"External diameter of the casing = {D_cc+2*th_casing:.4f}  [m]")
print(f"Thickness of the casing = {th_casing:.4f} [m]")
# --- ADDED: CASING WEIGHT PRINT --- #
print(f"Est. Casing Weight = {M_casing:.3f} [kg]")
# ---------------------------------- #
print("\n")
print(f"-------------------THERMAL PROTECTION--------------------")
print("\n")
print(f"Thermal protection thickness = {tp_thickness:.4f} [m]")
# --- ADDED: TP WEIGHT PRINT --- #
print(f"Est. Thermal Protection Weight = {M_tp:.3f} [kg]")
# ------------------------------ #
print("\n")
print(f"-------------------NOZZLE GEOMETRY-----------------------")
print("\n")
print(f"Throat diameter = {D_throat:.4f}  [m]")
print(f"Exit diameter = {D_exit:.4f}  [m]")
print(f"Convergent diameter = {D_cc - 2 * tp_thickness:.4f} [m]")
print(f"Aspect ratio = {exp_ratio}")
print(f"Convergent angle = {np.rad2deg(conv_angle):.2f} [deg]")
print(f"Divergent angle = {np.rad2deg(div_angle):.2f} [deg]")
print(f"Convergent length = {L_conv:.4f} [m]")
print(f"Divergent length =  {L_div:.4f} [m]")
print(f"Total length = {L_total:.4f} [m]")
# --- ADDED: NOZZLE WEIGHT PRINT --- #
print(f"Est. Nozzle Weight (Rough) = {M_nozzle:.3f} [kg]")
# ---------------------------------- #
print("\n")
print(f"-------------------MASSES OF THE MOTOR-----------------------")
print("\n")
print(f"Total mass of the motor (with grain) = {M_pr+M_nozzle+M_tp+M_casing:.3f} [kg]")
print(f"Total mass of the motor (burnout) = {M_nozzle+M_tp+M_casing:.3f} [kg]")
print("\n")
print(f"-------------------MASSES OF THE ROCKET-----------------------")
print("\n")
print(f"Total mass of the rocket = {Mdry + M_pr+M_nozzle+M_tp+M_casing:.3f} [kg]")
print(f"Empty mass of the rocket (burnout) = {Mdry + M_nozzle+M_tp+M_casing:.3f} [kg]")

"""**PRE-SIMULATION VERIFICATIONS**"""

core_area = np.pi * D_int * L_single_grain
base_area = 2 * np.pi * ((D_ext/2)**2 - (D_int/2)**2)
Ab_check= n_grains * (core_area + base_area)

Kn_initial = Ab_check / (np.pi * (D_throat/2)**2)
print(f"initial Kn = {Kn_initial:.4f} ")

"""**INTERNAL BALLISTICS SIMULATION**"""

from matplotlib.patches import FancyArrow
# simulation time
t0 = 0
tf = 2       # [sec]
dt = 0.001
time = np.arange(t0, tf+dt, dt)
N = len(time)

# initialize arrays
T = np.zeros(N)       # Thrust [N]
P0 = np.zeros(N)     # CC Pressure [Pa]
CF = np.zeros(N)      # thrust coefficient
T_comb = np.zeros(N)    # [K] theoretical combustion temperature
T_matrix = np.zeros((N, 3)) # 3 values for chamber, throat and exit temperatures [K]

M_pr_array = np.zeros(N)    # propellant mass array [kg]
mdot = np.zeros(N)          # mass flow rate [kg/sec]
r = np.zeros(N)             # burn rate [m/sec]
fac_CR = np.zeros(N)        # contraction ratio [-]

Ab = np.zeros(N)            # burning surface [m^2]
D_int_array = np.zeros(N)   # internal core diameter [m]
L_single_grain_array = np.zeros(N)   # length of single grain array [m]
Kn_geometry = np.zeros(N)

c_star = np.zeros(N)          # characteristic velocity [m/sec]
gamma_nozzle_exit = np.zeros(N)
gamma_chamber = np.zeros(N)
gamma_throat = np.zeros(N)
sonic_chamber = np.zeros(N)
sonic_throat = np.zeros(N)
sonic_exit = np.zeros(N)

Pe_P0 = np.zeros(N)
Pe = np.zeros(N)            # exit pressure [Pa]
M_e = np.zeros(N)
Pe_cea = np.zeros(N)
M_cc = np.zeros(N)          # mach in the chamber

# initialization of quantities
M_pr_array[0] = M_pr                        # initial mass
L_single_grain_array[0] = L_single_grain    # initial length
D_int_array[0] = D_int                      # initial internal diameter
P0[0] = P_amb*10                               # [Pa] initial guess of the CC pressure

for i in range(N-1):

    if D_int_array[i] >= D_ext or L_single_grain_array[i] <= 0: # check to close the loop

        index_burnout = i
        t_burnout = time[i]
        print(f"Burnout time = {t_burnout:.3f} sec")
        break

    if M_pr_array[i] <= 0:
        index_burnout = i
        t_burnout = time[i]
        print(f"Burnout time = {t_burnout:.3f} sec (mass exhausted)")
        break

    # burning surface
    core_area = np.pi * D_int_array[i] * L_single_grain_array[i]
    base_area = 2 * np.pi * ((D_ext/2)**2 - (D_int_array[i]/2)**2)
    Ab[i] = n_grains * (core_area + base_area)            # including internal core and the two bases of each grain
    Kn_geometry[i] = Ab[i] / (np.pi * (D_throat/2)**2)

    # burn rate
    r[i] = a * (P0[i])**n

    # gas generation
    mdot[i] = rho_pr * Ab[i] * r[i]

    # update grain geometry
    D_int_array[i+1] = D_int_array[i] + 2*r[i]*dt
    L_single_grain_array[i+1] = L_single_grain_array[i] - 2*r[i]*dt

    # update propellant mass
    M_pr_array[i+1] = M_pr_array[i] - mdot[i]*dt

    # cc pressure
    c_star[i] = cea.get_Cstar(Pc=P0[i])
    P0[i+1] = (rho_pr * a * c_star[i] * (Ab[i]/A_throat))**(1/(1-n))

    # cc Mach
    fac_CR[i] = (D_int_array[i] / D_throat)**2
    M_cc[i] = cea.get_Chamber_MachNumber(Pc=P0[i+1], fac_CR=fac_CR[i])

    # sonic velocities
    sonic_chamber[i], sonic_throat[i], _  = cea.get_SonicVelocities(Pc=P0[i+1],  eps=exp_ratio, frozen=1, frozenAtThroat=1)

    # Pe/P0
    T_comb[i] = cea.get_Tcomb(Pc=P0[i+1])
    T_matrix[i, :] = np.array(cea.get_Temperatures(Pc=P0[i+1], eps=exp_ratio, frozen=1, frozenAtThroat=1))
    gamma_nozzle_exit[i] = cea.get_exit_MolWt_gamma(Pc=P0[i+1], eps=exp_ratio, frozen=1, frozenAtThroat=1)[1]
    gamma_chamber[i] = cea.get_Chamber_MolWt_gamma(Pc=P0[i+1], eps=exp_ratio, )[1]
    gamma_throat[i] = cea.get_Throat_MolWt_gamma(Pc=P0[i+1], eps=exp_ratio, frozen=1)[1]
    Pe_P0[i], M_e[i] = get_pe_over_p0_from_AeAt(exp_ratio, gamma_nozzle_exit[i])
    Pe[i] = Pe_P0[i] * P0[i+1]
    Pe_cea[i] = P0[i+1]/cea.get_PcOvPe(Pc=P0[i+1], eps=exp_ratio, frozen=1, frozenAtThroat=1)
    R = 8.31446261815324 / ( cea.get_exit_MolWt_gamma(Pc=P0[i+1], eps=exp_ratio, frozen=1, frozenAtThroat=1)[0] / 1000 )
    sonic_exit[i] = np.sqrt(gamma_nozzle_exit[i] * R * T_matrix[i,2])

    # Cf
    term1 = np.sqrt(
        (2*gamma_nozzle_exit[i]**2)/(gamma_nozzle_exit[i]-1) *
        ((2/(gamma_nozzle_exit[i]+1))**((gamma_nozzle_exit[i]+1)/(gamma_nozzle_exit[i]-1))) *
        (1 - (Pe_P0[i])**((gamma_nozzle_exit[i]-1)/gamma_nozzle_exit[i]))
    )
    CF[i] = term1 + ((Pe[i] - P_amb)/P0[i+1])*(A_exit/A_throat)

    # Thrust
    T[i] = P0[i+1] * A_throat * CF[i] * eta_CF * eta_comb

"""**PERFORMANCIES**"""

I_total = np.trapezoid(T[:index_burnout], time[:index_burnout])
I_sp_final = I_total / (M_pr*g)
T_avg = np.mean(T[:index_burnout])


print(f"TOTAL IMPULSE = {I_total:.2f} [N·s]")
print(f"SPECIFIC IMPULSE = {I_sp_final:.2f} [sec]")
print(f"AVERAGE THRUST = {T_avg:.2f} [N]")
print("\n")
print(f"Residual core diameter = {D_ext-D_int_array[index_burnout]:.4f} [m]")
print(f"Residual single grain length = {L_single_grain_array[index_burnout]:.4f} [m]")
print(f"Residual propellant mass = {M_pr_array[index_burnout]:.4f} [m]")

"""**VERIFICATION**"""

max_p0 = np.max(P0[:index_burnout])
req_casing_th = (max_p0 * (D_cc+2*th_casing) / (2 * yield_casing_mat)) * SF_casing

print(f"Max Chamber Pressure = {max_p0/1e5:.2f} [bar]")
print(f"Required Casing Thickness = {req_casing_th:.4f} [m] (including SF = {SF_casing})")
print(f"Current Casing Thickness = {th_casing:.4f} [m]")

req_tp_thickness = recession_rate * t_burnout
print(f"Required TP Thickness (at {recession_rate*1000} mm/s) = {req_tp_thickness:.4f} [m]")
print(f"Residual TP Thickness = {(tp_thickness - req_tp_thickness)*1000:.2f} [mm]")

# casing verification
if th_casing >= req_casing_th:
    print("\n WARNING: Casing thickness: VERIFIED")
else:
    print("\n WARNING: Casing thickness: NOT VERIFIED")

# thermal protection verification
if tp_thickness >= req_tp_thickness:
    print("WARNING: Thermal protection: VERIFIED")
else:
    print("WARNING: Thermal protection: NOT VERIFIED")

"""**PLOTS**"""

def show_graphics():
    fig = make_subplots(rows=4, cols=3,
                        subplot_titles=("Thrust","CC pressure","c_star","Burn rate","Burning surface",
                                        "Mass flow rate","Propellant mass","CF","Pe and Pamb","gamma","Exit Mach","Temperatures"))

    fig.add_trace(go.Scatter(x=time, y=T, showlegend=False,line=dict(color='red')), row=1, col=1)
    fig.add_trace(go.Scatter(x=time, y=P0/1e5, showlegend=False,line=dict(color='blue')), row=1, col=2)
    fig.add_trace(go.Scatter(x=time, y=c_star, showlegend=False,line=dict(color='yellow')), row=1, col=3)
    fig.add_trace(go.Scatter(x=time, y=r, showlegend=False,line=dict(color='red')), row=2, col=1)
    fig.add_trace(go.Scatter(x=time, y=Ab, showlegend=False,line=dict(color='orange')), row=2, col=2)
    fig.add_trace(go.Scatter(x=time, y=mdot, showlegend=False,line=dict(color='orange')), row=2, col=3)
    fig.add_trace(go.Scatter(x=time, y=M_pr_array, showlegend=False,line=dict(color='orange')), row=3, col=1)
    fig.add_trace(go.Scatter(x=time, y=CF, showlegend=False,line=dict(color='red')), row=3, col=2)
    fig.add_trace(go.Scatter(x=time, y=Pe/1e5, name="Pe",line=dict(color='blue')), row=3, col=3)
    fig.add_trace(go.Scatter(x=time, y=Pe_cea/1e5, name="Pe cea",line=dict(color='yellow')), row=3, col=3)
    fig.add_trace(go.Scatter(x=time, y=np.full_like(time, P_amb/1e5), name="Pamb (sea level)",line=dict(color='red')), row=3, col=3)
    fig.add_trace(go.Scatter(x=time, y=gamma_nozzle_exit, name = "Exit",showlegend=False,line=dict(color='red')), row=4, col=1)
    fig.add_trace(go.Scatter(x=time, y=gamma_chamber, name = "Chamber",showlegend=False,line=dict(color='blue')), row=4, col=1)
    fig.add_trace(go.Scatter(x=time, y=gamma_throat, name = "Throat",showlegend=False,line=dict(color='green')), row=4, col=1)
    fig.add_trace(go.Scatter(x=time, y=M_e, showlegend=False,line=dict(color='blue')), row=4, col=2)

    fig.add_trace(go.Scatter(x=time, y=T_matrix[:,0], name="T_chamber", line=dict(color='red')), row=4, col=3)
    fig.add_trace(go.Scatter(x=time, y=T_matrix[:,1], name="T_throat", line=dict(color='green')), row=4, col=3)
    fig.add_trace(go.Scatter(x=time, y=T_matrix[:,2], name="T_exit", line=dict(color='blue')), row=4, col=3)
    fig.add_trace(go.Scatter(x=time, y=T_comb, name="T_comb", line=dict(color='orange', dash='dash')), row=4, col=3)

    fig.update_xaxes(title_text="Time [s]", row=1, col=1)
    fig.update_xaxes(title_text="Time [s]", row=1, col=2)
    fig.update_xaxes(title_text="Time [s]", row=1, col=3)
    fig.update_xaxes(title_text="Time [s]", row=2, col=1)
    fig.update_xaxes(title_text="Time [s]", row=2, col=2)
    fig.update_xaxes(title_text="Time [s]", row=2, col=3)
    fig.update_xaxes(title_text="Time [s]", row=3, col=1)
    fig.update_xaxes(title_text="Time [s]", row=3, col=2)
    fig.update_xaxes(title_text="Time [s]", row=3, col=3)
    fig.update_xaxes(title_text="Time [s]", row=4, col=1)
    fig.update_xaxes(title_text="Time [s]", row=4, col=2)
    fig.update_xaxes(title_text="Time [s]", row=4, col=3)

    fig.update_yaxes(title_text="Thrust [N]", row=1, col=1)
    fig.update_yaxes(title_text="CC Pressure [bar]", row=1, col=2)
    fig.update_yaxes(title_text="c_star [m/s]", row=1, col=3)
    fig.update_yaxes(title_text="Burn rate [m/s]", row=2, col=1)
    fig.update_yaxes(title_text="Burning surface [m²]", row=2, col=2)
    fig.update_yaxes(title_text="Mass flow rate [kg/s]", row=2, col=3)
    fig.update_yaxes(title_text="Propellant mass [kg]", row=3, col=1)
    fig.update_yaxes(title_text="CF []", row=3, col=2)
    fig.update_yaxes(title_text="Pressure [bar]", row=3, col=3)
    fig.update_yaxes(title_text="gamma", row=4, col=1)
    fig.update_yaxes(title_text="Exit Mach", row=4, col=2)
    fig.update_yaxes(title_text="Temperatures K]", row=4, col=3)

    fig.update_layout(title_text="Internal Ballistics Results", height=900)
    fig.show()

show_graphics()

"""**Kn AND MASS FLUX VERIFICATION**"""

# Kn factor
P_arr = np.linspace(P_amb, 100 * P_amb, 10000)
Kn_computed = (P_arr**(1-n)) / (rho_pr * a * c_star[50])

# mass flux normalized (mdot/port area)
m_flux = mdot[:index_burnout] / (np.pi * (D_int_array[:index_burnout]/2)**2)   # [kg/sec / m^2]
fig = make_subplots(rows=2, cols=2,
                        subplot_titles=("Kn (burn surface/throat surface)", "Normalized mass flux", "Chamber Mach vs contr. ratio","Chamber Mach vs time"))

fig.add_trace(go.Scatter(x=Kn_computed, y=P_arr/1e5, name = "Theoretical Kn",line=dict(color='blue')), row=1, col=1)
fig.add_trace(go.Scatter(x=Kn_geometry[:index_burnout], y=P0[:index_burnout]/1e5, name = "Geometrical Kn",line=dict(color='red')), row=1, col=1)
fig.add_trace(go.Scatter(x=time[:index_burnout] , y = m_flux, name = "Normalized mass flux",line=dict(color='green')), row=1, col=2)
fig.add_hline(y=1406.5, line=dict(color='red', dash='dash'), row=1, col=2)
fig.add_hline(y=1898, line=dict(color='red', dash='dash'), row=1, col=2)
fig.add_trace(go.Scatter(x=fac_CR[:index_burnout], y=M_cc[:index_burnout], showlegend=False,line=dict(color='blue')), row=2, col=1)
fig.add_hline(y=0.7, line=dict(color='red', dash='dash'), row=2, col=1)
fig.add_trace(go.Scatter(x=time[:index_burnout], y=M_cc[:index_burnout], showlegend=False,line=dict(color='blue')), row=2, col=2)
fig.add_hline(y=0.7, line=dict(color='red', dash='dash'), row=2, col=2)


fig.update_xaxes(title_text="Kn []", row=1, col=1)
fig.update_yaxes(title_text="P0 [bar]", row=1, col=1)
fig.update_xaxes(title_text="mdot [kg/sec]", row=1, col=2)
fig.update_yaxes(title_text="Time [sec]", row=1, col=2)
fig.update_xaxes(title_text="Contr. ratio []", row=2, col=1)
fig.update_yaxes(title_text="Mach", row=2, col=1)
fig.update_xaxes(title_text="Time [sec]", row=2, col=2)
fig.update_yaxes(title_text="Mach", row=2, col=2)

fig.update_layout(title_text="Grain geometry verification", height=900)
fig.show()

port_throat = D_int / D_throat
print(f"\n Port throat ratio = {port_throat:.4f}, expected  >= 2")

"""**NOZZLE EXPANSION VERIFICATION**"""

pe_active = Pe[:index_burnout]
cf_active = CF[:index_burnout]
Pt = P0 * (2/(gamma_throat+1))**(gamma_throat/(gamma_throat-1))

# 1. Check if Pe = P_amb crosses at least once
crosses_pamb = np.any(np.isclose(pe_active, P_amb, atol=2000)) or (np.max(pe_active) >= P_amb and np.min(pe_active) <= P_amb)
print("\n----------------NOZZLE END OF SCRIPT CHECKS-----------------\n")
print(f"Does Pe equal P_amb (sea level) at least once during fire? {'Yes' if crosses_pamb else 'No'} \n")

# 2. Print logic request
if np.all(pe_active > P_amb):
    print("WARNING: Expansion ratio is too small \n")
if np.sum(pe_active < P_amb) > 0.5 * len(pe_active): # at least 50% of the fire
    print("WARNING: Expansion ratio is too big \n")

# 3. Add Custom Plots
def show_custom_plots():
    gamma_avg = np.mean(gamma_nozzle_exit[:index_burnout])
    p0_avg = np.mean(P0[:index_burnout])
    pa_p0_ratio = P_amb / p0_avg

    # Theoretical Expansion Ratio vs Mach
    m_vals = np.linspace(0.1, 4.0, 200)
    eps_vals = (1/m_vals) * ((2/(gamma_avg+1))*(1 + (gamma_avg-1)/2 * m_vals**2))**((gamma_avg+1)/(2*(gamma_avg-1)))

    fig2 = make_subplots(rows=1, cols=3, subplot_titles=("Pressure","Temperatures","Expansion Ratio vs. Mach Number"))

    # Plot 1: Expansion Ratio vs Mach
    fig2.add_trace(go.Scatter(x=m_vals, y=eps_vals, name='Exp Ratio', showlegend=False, line=dict(color='blue')), row=1, col=3)
    # Add Points & Dashed lines for design points
    m_design = np.mean(M_e[:index_burnout])
    #cf_design = np.mean(CF[:index_burnout])
    fig2.add_trace(go.Scatter(x=[m_design], y=[exp_ratio], mode='markers', name='Design Point', marker=dict(color='red', size=8)), row=1, col=3)
    fig2.add_shape(type="line", x0=m_design, y0=0, x1=m_design, y1=exp_ratio, line=dict(color="red", dash="dot"), row=1, col=3)
    fig2.add_shape(type="line", x0=0, y0=exp_ratio, x1=m_design, y1=exp_ratio, line=dict(color="red", dash="dot"), row=1, col=3)
    fig2.update_xaxes(title_text="Mach Number M", row=1, col=3, range=[0, 4])
    fig2.update_yaxes(title_text="Expansion Ratio eps", row=1, col=3, range=[0, 12])

    fig2.add_trace(go.Scatter(x=time[:index_burnout], y=P0[:index_burnout]/1e5, name='P0 (chamber)', line=dict(color='blue')), row=1, col=1)
    fig2.add_trace(go.Scatter(x=time[:index_burnout], y=Pe[:index_burnout]/1e5, name='Pe (exit)', line=dict(color='green')), row=1, col=1)
    fig2.add_trace(go.Scatter(x=time[:index_burnout], y=Pt[:index_burnout]/1e5, name='Pt (throat)', line=dict(color='red')), row=1, col=1)

    fig2.add_trace(go.Scatter(x=time, y=T_matrix[:,0], name="T_chamber",showlegend=False, line=dict(color='blue')), row=1, col=2)
    fig2.add_trace(go.Scatter(x=time, y=T_matrix[:,1], name="T_throat",showlegend=False, line=dict(color='red')), row=1, col=2)
    fig2.add_trace(go.Scatter(x=time, y=T_matrix[:,2], name="T_exit",showlegend=False, line=dict(color='green')), row=1, col=2)

    fig2.update_layout(height=500, title_text="Nozzle Analytics")
    fig2.show()

show_custom_plots()

# ------------------ CF vs EXPANSION RATIO (visible) ------------------

gamma_avg = np.mean(gamma_nozzle_exit[:index_burnout])
p0_avg = np.mean(P0[:index_burnout])
cf_design = np.mean(CF[:index_burnout])

eps_range = np.logspace(0, np.log10(50), 1000)  # Expansion ratio range

cf_curve = []
cf_curve_vac = []

# Compute CF curves over expansion ratio range
for eps in eps_range:
    pe_p0_val, _ = get_pe_over_p0_from_AeAt(eps, gamma_avg)
    pe_val = pe_p0_val * p0_avg

    term1 = np.sqrt(
        (2 * gamma_avg**2) / (gamma_avg - 1) *
        ((2 / (gamma_avg + 1)) ** ((gamma_avg + 1) / (gamma_avg - 1))) *
        (1 - (pe_p0_val) ** ((gamma_avg - 1) / gamma_avg))
    )

    cf_val = term1 + ((pe_val - P_amb) / p0_avg) * eps
    cf_vac = term1 + (pe_val / p0_avg) * eps

    cf_curve.append(cf_val)
    cf_curve_vac.append(cf_vac)

cf_curve = np.array(cf_curve)
cf_curve_vac = np.array(cf_curve_vac)

# Convergent nozzle CF (ε=1)
cf_conv = ((gamma_avg + 1) * (2 / (gamma_avg + 1)) ** (gamma_avg / (gamma_avg - 1))) - P_amb / p0_avg
cf_conv_vac = ((gamma_avg + 1) * (2 / (gamma_avg + 1)) ** (gamma_avg / (gamma_avg - 1)))

# Normalize CF curves
cf_norm = cf_curve / cf_conv
cf_norm_vac = cf_curve_vac / cf_conv_vac

# Find optimal expansion ratio
idx_max = np.argmax(cf_curve)
eps_opt = eps_range[idx_max]
cf_opt = cf_curve[idx_max]

# --- Create subplots ---
fig = make_subplots(rows=1, cols=3, subplot_titles=("Velocities","CF vs Expansion Ratio", "Normalized CF vs Expansion Ratio"))

# Plot real CF
fig.add_trace(go.Scatter(x=eps_range, y=cf_curve, line=dict(color='blue'), name="CF ambient", showlegend=False), row=1, col=2)
fig.add_trace(go.Scatter(x=eps_range, y=cf_curve_vac, line=dict(color='green', dash='dash'), name="CF vacuum", showlegend=False), row=1, col=2)
fig.add_trace(go.Scatter(x=[exp_ratio], y=[cf_design], mode='markers', marker=dict(color='red', size=10), name="Design"), row=1, col=2)
fig.add_trace(go.Scatter(x=[eps_opt], y=[cf_opt], mode='markers', marker=dict(color='black', size=10), name="Optimal"), row=1, col=2)

# Plot normalized CF
fig.add_trace(go.Scatter(x=eps_range, y=cf_norm, line=dict(color='blue'), name="CF / CF convergent", showlegend=False), row=1, col=3)
fig.add_trace(go.Scatter(x=eps_range, y=cf_norm_vac, line=dict(color='green', dash='dash'), name="CF vacuum / CF convergent", showlegend=False), row=1, col=3)
fig.add_trace(go.Scatter(x=[exp_ratio], y=[cf_design / cf_conv], mode='markers', marker=dict(color='red', size=10), showlegend=False), row=1, col=3)
fig.add_trace(go.Scatter(x=[eps_opt], y=[cf_opt / cf_conv], mode='markers', marker=dict(color='black', size=10), showlegend=False), row=1, col=3)

# --- Add dashed lines for DESIGN and OPTIMAL points ---

# DESIGN lines
fig.add_shape(type="line", x0=exp_ratio, x1=exp_ratio, y0=min(cf_curve), y1=cf_design, line=dict(color="red", dash="dot"), row=1, col=2)
fig.add_shape(type="line", x0=1, x1=exp_ratio, y0=cf_design, y1=cf_design, line=dict(color="red", dash="dot"), row=1, col=2)

fig.add_shape(type="line", x0=exp_ratio, x1=exp_ratio, y0=min(cf_curve / cf_conv), y1=cf_design / cf_conv, line=dict(color="red", dash="dot"), row=1, col=3)
fig.add_shape(type="line", x0=1, x1=exp_ratio, y0=cf_design / cf_conv, y1=cf_design / cf_conv, line=dict(color="red", dash="dot"), row=1, col=3)

# OPTIMAL lines
fig.add_shape(type="line", x0=eps_opt, x1=eps_opt, y0=min(cf_curve), y1=cf_opt, line=dict(color="black", dash="dot"), row=1, col=2)
fig.add_shape(type="line", x0=1, x1=eps_opt, y0=cf_opt, y1=cf_opt, line=dict(color="black", dash="dot"), row=1, col=2)

fig.add_shape(type="line", x0=eps_opt, x1=eps_opt, y0=min(cf_curve / cf_conv), y1=cf_opt / cf_conv, line=dict(color="black", dash="dot"), row=1, col=3)
fig.add_shape(type="line", x0=1, x1=eps_opt, y0=cf_opt / cf_conv, y1=cf_opt / cf_conv, line=dict(color="black", dash="dot"), row=1, col=3)

# Axes
fig.update_xaxes(type="log", title="Expansion ratio ε", row=1, col=2)
fig.update_xaxes(type="log", title="Expansion ratio ε", row=1, col=3)
fig.update_yaxes(title="CF", row=1, col=2, range=[cf_curve.min() * 0.95, cf_curve.max() * 1.05])
fig.update_yaxes(title="CF / CF convergent", row=1, col=3, range=[cf_norm.min() * 0.95, cf_norm.max() * 1.05])

fig.add_trace(go.Scatter(x=time, y=M_e * sonic_exit, line=dict(color='green'), name="Exit", showlegend=False), row=1, col=1)
fig.add_trace(go.Scatter(x=time, y=M_cc * sonic_chamber, line=dict(color='blue'), name="Chamber", showlegend=False), row=1, col=1)
M_t = np.zeros(N)+1
fig.add_trace(go.Scatter(x=time, y=M_t * sonic_throat, line=dict(color='red'), name="Throat", showlegend=False), row=1, col=1)


fig.update_layout(title="Nozzle Performance Analysis - AVERAGE CONDITIONS", height=500)
fig.show()

# Check if design point is close to maximum CF
is_close_to_max = np.isclose(exp_ratio, eps_opt, rtol=0.15)

print(f"\n----------------- DESIGN POINT VS CF MAX CHECK -----------------")
print(f"Design point ε = {exp_ratio:.3f} (CF = {cf_design:.3f})")
print(f"Maximum CF at ε = {eps_opt:.3f} (CF = {cf_opt:.3f})")
print(f"Is the design point close to the CF maximum? {'Yes' if is_close_to_max else 'No'}")
print(f"(You are at ε = {exp_ratio}, Max is at ε ≈ {eps_opt:.2f})\n")

# --- THRUST
thrust_curve = np.column_stack((time[:index_burnout], T[:index_burnout]))


#-------------------------------------------------------------------------------------------------------- MONTECARLO PARAMETERS
# The following parameters are centralized here for convenience. 
# Core internal variables remain defined within their respective modules.

# Name of the output folder (can be a new folder or an existing one to overwrite)
output_dir_name = 'FRED_v1.5_SRAD_motor_test'
number_of_simulations = 50

show_graph = False
sensitivity_analysis = True

latitude = 44.290583
longitude = 12.027111
elevation = 18
date_of_launch = (2025, 5, 9, 12)          #(Year, Month, Day, Hour UTC)
weather_data: Literal['c','e','f','i'] = 'e'        #(Custom, Ensemble, Forecast, Isa)

#   SRAD motor info v1.1

CG_position_from_nose = 412 / 1000

std_p = 2                              # standard percentage variation

def std_gen(measure,percentage):
    return measure*(percentage/100)

analysis_parameters = {
    
    # === Mass Details ===
    
    # Rocket's dry mass without grains' weight (kg) and its uncertainty (standard deviation)
    "rocket_dry_mass": (rocket_dry_mass, std_gen(rocket_dry_mass, std_p)),
    # Rocket's dry inertia moment perpendicular to its axis (kg*m^2)
    "rocket_dry_inertia_11": (0.115, std_gen(0.115, std_p)),
    # Rocket's dry inertia moment relative to its axis (kg*m^2)
    "rocket_dry_inertia_33": (0.004, std_gen(0.004, std_p)),
    # Motors's dry mass without propellant (kg)
    "motor_dry_mass": (0.0001, std_gen(0.0001, std_p)),
    # Motor's dry inertia moment perpendicular to its axis (kg*m^2)
    "motor_inertia_11": (0, 0), 
    # Motor's dry inertia moment relative to its axis (kg*m^2)
    "motor_inertia_33": (0.0, 0.0), 
    # Distance between the origin of the referential system and motor's center of dry mass (m)
    "motor_dry_mass_position": (0.0, std_gen(0.0, std_p)),

    # === Propulsion Details ===

    # Motor total impulse (N*s)
    "impulse": (I_total, std_gen(I_total, std_p)),
    # Motor burn out time (s)
    "burn_time": (t_burnout, std_gen(t_burnout, std_p)),
    # Motor's nozzle radius (m)
    "nozzle_radius": (D_exit/2, std_gen(D_exit/2, std_p)),
    # Motor's nozzle throat radius (m)
    "throat_radius": (D_throat/2, std_gen(D_throat/2, std_p)),
    # Motor's grain separation (axial distance between two grains) (m)
    "grain_separation": (grains_distance, std_gen(grains_distance, std_p)),
    # Motor's grain density (kg/m^3)
    "grain_density": (rho_pr, std_gen(rho_pr, std_p)),
    # Motor's grain outer radius (m)
    "grain_outer_radius": (D_ext/2, std_gen(D_ext/2, std_p)),
    # Motor's grain inner radius (m)
    "grain_initial_inner_radius": (D_int/2, std_gen(D_int/2, std_p)),
    # Motor's grain height (m)
    "grain_initial_height": (L_single_grain, std_gen(L_single_grain, std_p)),

    # === Aerodynamic Details ===
    
    # Rocket's radius (m)
    "radius": (42.5 / 1000, std_gen(42.5 / 1000, std_p)),
    # Origin of the motor coordinate system
    "nozzle_position": (0, std_gen(0, std_p)),
    # Distance between the origin of the referential system and center of propellant mass (m) 
    "grains_center_of_mass_position": (125 / 1000, std_gen(125 / 1000, std_p)), 
    # Multiplier for rocket's power off drag curve
    "power_off_drag_corr": (1.0, std_gen(1.0, std_p)),
    # Multiplier for rocket's power on drag curve
    "power_on_drag_corr": (1.0, std_gen(1.0, std_p)),
    # Rocket's nose cone length (m)
    "nose_length": (0.14, std_gen(0.14, std_p)),
    # Power of the function that describes the shape of the nose cone
    "nose_pwr" : (0.4, std_gen(0.4, std_p)),                          
    # Axial distance from the tip of the nose (m)
    "tail_position": (0.77, std_gen(0.77, std_p)),
    # The origin of the coordinate system (m)
    "nose_position": (0, 0),
    # Number of fins
    "fin_number" : (3, 0), 
    # Fin span (m)
    "fin_span": (0.12, std_gen(0.12, std_p)), 
    # Fin root chord (m)
    "fin_root_chord": (0.12, std_gen(0.12, std_p)), 
    # Fin tip chord (m)
    "fin_tip_chord": (0.03, std_gen(0.03, std_p)), 
    # Axial distance between rocket's tip and nearest point in its fin (m)
    "fin_position": (0.65, std_gen(0.65, std_p)), 
    # Fin sweep angle (degrees)
    "fin_sweep_angle": (30.3, std_gen(30.3, std_p)), 
    # Tail length (m)
    "tail_length": (0.044, std_gen(0.044, std_p)), 
    # Tail bottom radius (m)
    "tail_bottom_radius": (29 / 1000, std_gen(29 / 1000, std_p)), 
    # Tail top radius (m)
    "tail_top_radius": (42.5 / 1000, std_gen(42.5 / 1000, std_p)), 

    # === Launch and Environment Details ===

    # Launch rail inclination angle (degrees)
    "inclination": (84, std_gen(84, std_p)),
    # Launch rail heading relative to north (degrees)
    "heading": (160, std_gen(160, std_p)),
    # Launch rail length (m)
    "rail_length": (2, std_gen(2, std_p)),
    # Members of the ensemble forecast
    "ensemble_member": list(range(10)), # Qui il 10 rimane per il range dell'ensemble

    # === Parachute Details ===

    # Drag coefficient times reference area (m^2)
    "cd_s_main": (0.97 * 1.168, std_gen(0.97 * 1.168, std_p)),
    # Time delay for inflation (s)
    "lag_rec": (1.73, std_gen(1.73, std_p)),

    # === Rail buttons Details ===
    
    # Position of the upper rail button (m)
    "upper_button_y": (0.14, std_gen(0.14, std_p)),
    # Position of the lower rail button (m)
    "lower_button_y": (0.545, std_gen(0.545, std_p)),
    # Angular position of the buttons (degrees)
    "angular_button": (0, std_gen(0, std_p)),

    # === Electronic Systems and Sensors Details ===

    # Time delay for ejection signal (s)
    "lag_se": (0.05, std_gen(0.05, std_p)),
    # Mean noise value of the Pressure signal (Pa) 
    "noise_mean": (0, std_gen(0, std_p)),
    # Standard deviation of the Pressure signal (Pa)
    "noise_p_stdev": (6.5, std_gen(6.5, std_p)),
    # Time correlation of the Pressure signal
    "noise_p_tc": (0.3, std_gen(0.3, std_p)),
}

#-------------------------------------------------------------------------------------------------------- START TIMER
# Initialize counter and timer
i = 0

initial_wall_time = time.time()
initial_cpu_time = process_time()
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- FUNCTIONS
# Definition of global variables, to be used inside and outside parachute functions
global last_negative_time, apogee_detected, sampling_rate, parachute_timer

# This variable marks the first instant in which a negative velocity is detected
last_negative_time = None
# This variable indicates whether the algorythm has acknowledged the rocket has reached apogee.
# A "False" value may mean that negative velocity has not yet been detected, 
# or that it has been detected but has not yet been consistent for enough seconds (the threshold)
apogee_detected = False
# This variable indicates the sampling rate of the recovery activation algorythm
sampling_rate = 105
# This variable keeps track of the flight time from ignition to the first recovery event 
parachute_stopwatch = 0

# Definition of useful functions

def convert_numpy(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        raise TypeError(
        f"Object of type {type(obj)} is not JSON serializable"
        )

def flight_settings(analysis_parameters, total_number):
    i = 0
    while i < total_number:
        # Generate a flight setting
        flight_setting = {}
        for parameter_key, parameter_value in analysis_parameters.items():
            if type(parameter_value) is tuple:
                flight_setting[parameter_key] = normal(*parameter_value)
            else:
                flight_setting[parameter_key] = choice(parameter_value)

        # Skip if certain values are negative, which happens due to the normal curve but isnt realistic
        if flight_setting["lag_rec"] < 0 or flight_setting["lag_se"] < 0:
            continue

        # Update counter
        i += 1
        # Yield a flight setting
        yield flight_setting

def export_flight_data(flight_setting, flight_data, exec_time):
    # Generate flight results
    flight_result = {
        "out_of_rail_time": flight_data.out_of_rail_time,
        "out_of_rail_velocity": flight_data.out_of_rail_velocity,
        "max_velocity": flight_data.speed.max,
        "max_acceleration": flight_data.acceleration.max,
        "max_aerodynamic_drag": flight_data.aerodynamic_drag.max,
        "max_aerodynamic_lift": flight_data.aerodynamic_lift.max,
        "max_aerodynamic_spin_moment": flight_data.aerodynamic_spin_moment.max,
        "max_aerodynamic_bending_moment": flight_data.aerodynamic_bending_moment.max,
        "apogee_time": flight_data.apogee_time,
        "apogee_altitude": flight_data.apogee - Env.elevation,
        "apogee_x": flight_data.apogee_x,
        "apogee_y": flight_data.apogee_y,
        "impact_time": flight_data.t_final,
        "impact_x": flight_data.x_impact,
        "impact_y": flight_data.y_impact,
        "impact_velocity": flight_data.impact_velocity,
        "initial_static_margin": flight_data.rocket.static_margin(0),
        "out_of_rail_static_margin": flight_data.rocket.static_margin(
            flight_data.out_of_rail_time
        ),
        "final_static_margin": flight_data.rocket.static_margin(
            flight_data.rocket.motor.burn_out_time
        ),
        "number_of_events": len(flight_data.parachute_events),
        "execution_time": exec_time,
    }

    # Take care of parachute results
    if len(flight_data.parachute_events) > 0:
        flight_result["drogue_triggerTime"] = flight_data.parachute_events[0][0]
        flight_result["drogue_inflated_time"] = (
            flight_data.parachute_events[0][0] + flight_data.parachute_events[0][1].lag
        )
        flight_result["drogue_inflated_velocity"] = flight_data.speed(
            flight_data.parachute_events[0][0] + flight_data.parachute_events[0][1].lag
        )
    else:
        flight_result["drogue_triggerTime"] = 0
        flight_result["drogue_inflated_time"] = 0
        flight_result["drogue_inflated_velocity"] = 0

    # Write flight setting and results to file, in json format for better use in the sensitivity analysis
    dispersion_input_file.write(json.dumps(flight_setting, default=convert_numpy) + "\n")   
    dispersion_output_file.write(json.dumps(flight_result, default=convert_numpy) + "\n")


def export_flight_error(flight_setting):
    dispersion_error_file.write(str(flight_setting) + "\n")


# The following function is a Python representation of the C code that 
# will be used on the rocket to detect the apogee condition. 
# In the actual code, detection of negative velocity is achieved
# thanks to the readings from the IMU sensor
def check_apogee(vertical_velocity, current_time, threshold=0.1):

    global last_negative_time, apogee_detected, parachute_stopwatch

    # If the parachute activation signal has already been sent, confirm it and exit the function
    if apogee_detected:
        return True, last_negative_time
    
    # Otherwise, check if the rocket is losing altitude
    if vertical_velocity < 0:

        # if a descent is being detected, check if this is the first time this occurs
        if last_negative_time is None:

            # if it is, mark this instant and exit the function
            last_negative_time = parachute_stopwatch
            return False, last_negative_time
        
        elif (current_time - last_negative_time) >= threshold: #0.1s

            # if it isn't and enough time has passed with a continuous descent, acknowledge apogee and exit the function
            return True, last_negative_time
        
        else:

            # if it isn't and not enough time has passed with a continuous descent, return False and exit the function
            return False, last_negative_time
        
    # if a descent is no longer being (or has never been) detected, return False and exit the function
    else:
        return False, None
    
# Set up parachute trigger for the drogue chute
def simulator_check_chute_opening(p, h, y):
    global last_negative_time, apogee_detected, parachute_stopwatch, sampling_rate
    altitude = h
    vertical_velocity = y[5]

    # Update counter for flight time to apogee:
    # each time this function is called, the timer advances of 1 over the frequency at which the function is called.
    # This is a workaround to get a measure of in-flight time
    # into the apogee detection algorythm and successfully implement its "consistent descent signal" principle.
    parachute_stopwatch += 1/sampling_rate

    # Mark instant at which the current call is being made
    now = parachute_stopwatch
    
    # Call apogee detection algorythm
    apogee_detected, last_negative_time = check_apogee(
        vertical_velocity,
        now,  
    )
    return apogee_detected
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

def loading_bar(initial_time: datetime, number_of_iterations:int, iteration:int, bar_lenght:int=24):
    time_for_iteration = (process_time() - initial_time) / iteration
    seconds_remaining = round(time_for_iteration*(number_of_iterations-iteration))

    current_iteration = f"{iteration:0{len(str(number_of_iterations))}d}"
    average_time = f"{time_for_iteration:2.2f}s"
    time_remaining = f"{seconds_remaining//3600:02d}:{(seconds_remaining%3600)//60:02d}:{seconds_remaining%60:02d}"
    bar = f"{'\u2588'*(bar_lenght*iteration//number_of_iterations):\u2591<{bar_lenght}}"
    percentage = f"{100*iteration/number_of_iterations:.1f}%"

    print(f"Current iteration: {colored(current_iteration)}",end=' ')
    print(f"Average time per iteration: {colored(average_time)}",end=' ')
    print(f"Time remaining: {colored(time_remaining)}",end=" ")
    print(f"|{colored(bar)}|[{colored(percentage):<7}]",end="\r")
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- PATH, FOLDER & FILE
# Paths
output_path = Path(str(BASE_DIR/"montecarlo_output"/output_dir_name))
filename = str(output_path/"FRED")

output_sensitivity = Path(output_path/"sensitivity")

output_comparison = Path(output_path/"comparison")

output_dispersion = Path(output_path/"dispersion")
output_dispersion_pickle = Path(output_dispersion/"pickle")
output_dispersion_svg = Path(output_dispersion/"svg")

output_launch_site = Path(output_path/"launch_site")

# First information print
print("Montecarlo Rocket flight simulator\n")
print(f"- Filename is: {colored(filename)}")
print(f"- Number of simulations: {colored(number_of_simulations)}")
print(f"- Output directory: {colored(output_dir_name)}\n")

#WARNINGS

# with less than 50 simulations sensitivity analysis returns errors
if number_of_simulations<50:
    print(f"<!> Less than 50 simulations: {colored('sensitivity analysis deactivated')}")
    sensitivity_analysis = False

# Create or overwrite folders for outputs
if output_path.is_dir():
    overwrite_folder = input(f'<!> The "{output_dir_name}" folder already exists. Do you want to overwrite it? [{colored('y/n')}] - ')
    if not overwrite_folder.lower() in ['y','yes']:
        print("You chose not to overwrite the folder. Stopping the program.")
        raise SystemExit(0)

print("\nStarting...", end='\r')

#create folders
output_sensitivity.mkdir(parents=True, exist_ok=True)
output_comparison.mkdir(parents=True, exist_ok=True)
output_dispersion_pickle.mkdir(parents=True, exist_ok=True)
output_dispersion_svg.mkdir(parents=True, exist_ok=True)
output_launch_site.mkdir(parents=True, exist_ok=True)


# Create data files for inputs, outputs and error logging
dispersion_error_file = open(str(filename) + ".disp_errors.txt", "w")
dispersion_input_file = open(str(filename) + ".disp_inputs.json", "w")
dispersion_output_file = open(str(filename) + ".disp_outputs.json", "w")
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- ENVIRONMENT
Env = Environment(
    date = date_of_launch,
    longitude = longitude,
    latitude = latitude,
    elevation = elevation,
    max_expected_height = 1500
)

# There are 4 possible choices of weather data:
if weather_data=='c':
    # A custom atmosphere defined with the mean environment values calculated in the week on EuRoC 
    # from 2005 to 2024 between the 10th and the 15th october. 
    # In order to define the mean environment features, we used the built-in function "Environment Analysis"  
    # from RocketPy. This generates a .json file with the mean environment values based on a sample 
    # of 19 years, from 2005 to 2024, between the 10th and 15th of October, by feeding the NetCDF4 data  
    # from Copernicus. The .json file contains a series of .csv profiles based on the altitude that   
    # define pressure, temperature and wind vectors on an hourly basis.
    # For more information consult the "mean_environment_values.json" file inside the directory.

    # import the .json with the mean environment values oustide the defition of the atmospheric model
    with open(BASE_DIR/"simulation_inputs/environment_data/mean_environment_values.json", "r") as f:
        data = json.load(f)

    Env.set_atmospheric_model(

        # set the atmosphere model
        type="custom_atmosphere",

        # define the values (pressure, temperature and wind [E,N]) from the .json
        pressure = data["atmospheric_model_pressure_profile"][str(Env.date[3])],
        temperature= data["atmospheric_model_temperature_profile"][str(Env.date[3])],
        wind_u= data["atmospheric_model_wind_velocity_x_profile"][str(Env.date[3])],
        wind_v= data["atmospheric_model_wind_velocity_y_profile"][str(Env.date[3])]

    )
elif weather_data=='e':
    # Select a date during the EuRoC week: October 10th-15th from 2005 to 2024 (change the date in the 
    # environment definition), in this case the weather data will match the date chosen by the user.
    Env.set_atmospheric_model(
        type="Ensemble",                                                                                                  
        file=str(BASE_DIR/"simulation_inputs/environment_data/Villafranca_ensemble_5to11may2020to2026.nc"),                                        
        # This section creates an updated dictionary to read the NetCDF4 files,                                           
        # as the built-in ECMWF dictionary inside RocketPy is outdated and can't read NetCDF4 
        # files in the new format     
        dictionary= {                                                                                                     
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
elif weather_data=='f':
    # The Forecast: let the user simulate in the future by using the GFS (Global Forecast System) 
    # weather data, (change the date in the environment definition).
    Env.set_atmospheric_model(
        type="Forecast",
        file="GFS"
    )
elif weather_data!='i':
    # The default weather data type is the International Standard Atmosphere (ISA).
    # If none of the previously listed options is selected, this model will be applied automatically.
    print('<!> International Standard Atmosphere (ISA) as defined by ISO 2533 is initialized as weather data <!>')
#---------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- MONTECARLO
# Initiate collection of flight data.
# This allows to compare different flight from the Montecarlo analysis and visualize
# data dispersion and overall characteristics of the flight and the simulation itself
flights=[]

# Iterate over flight settings
for setting in flight_settings(analysis_parameters, number_of_simulations):

    last_negative_time = None
    apogee_detected = False
    parachute_stopwatch = 0

    start_time = process_time()
    i += 1
    #print(f"\rCurrent iteration: {i}", end="")

    if Env.atmospheric_model_type == "Ensemble":
        # Update environment object
        Env.select_ensemble_member(setting["ensemble_member"])

    # Define COTS motor
    Solid_motor = SolidMotor(
        # Thrust data
        thrust_source=thrust_curve,
        burn_time=setting["burn_time"],
        reshape_thrust_curve=(setting["burn_time"], setting["impulse"]),
        interpolation_method="linear",
        # Nozzle data
        nozzle_radius=setting["nozzle_radius"],
        throat_radius=setting["throat_radius"],
        # Grain data
        grain_number=1,
        grain_separation=setting["grain_separation"],
        grain_density=setting["grain_density"],
        grain_outer_radius=setting["grain_outer_radius"],
        grain_initial_inner_radius=setting["grain_initial_inner_radius"],
        grain_initial_height=setting["grain_initial_height"],
        # Geometric data
        nozzle_position=setting["nozzle_position"],
        grains_center_of_mass_position=setting["grains_center_of_mass_position"],
        dry_mass=setting["motor_dry_mass"],
        dry_inertia=(
            setting["motor_inertia_11"],
            setting["motor_inertia_11"],
            setting["motor_inertia_33"],
        ),
        center_of_dry_mass_position=setting["motor_dry_mass_position"],
        coordinate_system_orientation = "nozzle_to_combustion_chamber",
    )

    power_off_drag = str(BASE_DIR / "simulation_inputs/aerodynamic_data/FRED_v1.4_CD_power_off.csv")
    power_on_drag  = str(BASE_DIR / "simulation_inputs/aerodynamic_data/FRED_v1.4_CD_power_on.csv")


# Now create the Rocket

    # Create rocket
    FRED = Rocket(
        radius=setting["radius"],
        mass=setting["rocket_dry_mass"],
        inertia=(
            setting["rocket_dry_inertia_11"],
            setting["rocket_dry_inertia_11"],
            setting["rocket_dry_inertia_33"],
        ),
        power_off_drag=power_off_drag,
        power_on_drag=power_on_drag,
        # Define the center of dry mass as the distance from the tip of the nose, and set the positive axis orientation
        center_of_mass_without_motor=CG_position_from_nose,
        coordinate_system_orientation="nose_to_tail",
    )

    # Define rail buttons
    FRED.set_rail_buttons(
        upper_button_position= setting["upper_button_y"], 
        lower_button_position= setting["lower_button_y"], 
        angular_position= setting["angular_button"],
    )

    # Add the motor to the rocket assembly
    # sets the motor's CDM on the rocket's CDM.
    # The "grain center of mass position" parameter will handle the position of the actual motor
    FRED.add_motor(Solid_motor, position=(setting["tail_position"]+setting["tail_length"]))

    # Add uncertainty to the drag curves, by multiplying them by a small, random corrective factor
    FRED.power_off_drag *= setting["power_off_drag_corr"]
    FRED.power_on_drag *= setting["power_on_drag_corr"]

    # Define and add the Nosecone section
    NoseCone = FRED.add_nose(
        length=setting["nose_length"],
        kind="elliptical",
        power= "nose_pwr",
        position=setting["nose_position"],
    )

    # Define and add the Fins
    FinSet = FRED.add_trapezoidal_fins(
        n=3,
        span=setting["fin_span"],
        root_chord=setting["fin_root_chord"],
        tip_chord=setting["fin_tip_chord"],
        position=setting["fin_position"],
        sweep_angle=setting["fin_sweep_angle"],
        cant_angle=0,
        airfoil = None,
    )

    # Define and add the Boat-tail
    Tail = FRED.add_tail(
        top_radius=setting["tail_top_radius"],
        bottom_radius=setting["tail_bottom_radius"], 
        length=setting["tail_length"], 
        position = setting["tail_position"],
    )

    # Define and add the Main parachute
    Main = FRED.add_parachute(
        "Main",
        cd_s=setting["cd_s_main"],
        trigger=simulator_check_chute_opening,
        sampling_rate= sampling_rate,
        lag=setting["lag_rec"] + setting["lag_se"],
        noise=(
            setting["noise_mean"],
            setting["noise_p_stdev"],
            setting["noise_p_tc"],
        ),
    )
    
    # Run trajectory simulation
    try: 
        rocket_flight = Flight(
            rocket=FRED,
            environment=Env,
            rail_length=setting["rail_length"],
            inclination=setting["inclination"],
            heading=setting["heading"],
            max_time=1200,
        )

        export_flight_data(setting, rocket_flight, process_time() - start_time)
    except Exception as E:
        print(E)
        export_flight_error(setting)

    flights.append(rocket_flight)

    # Update loading bar
    loading_bar(
        initial_time=initial_cpu_time,
        number_of_iterations=number_of_simulations,
        iteration=i,
        )

# jump a row to not overwrite loading bar
print('\n')


# Print total time
cpu_time = round(process_time() - initial_cpu_time, 2)
wall_time = round(time.time() - initial_wall_time, 2)
final_string = f"Completed {i} iterations successfully. Total CPU time: {colored(cpu_time)} s. Total wall time: {colored(wall_time)} s"
print(final_string)


# Close files
dispersion_input_file.close()
dispersion_output_file.close()
dispersion_error_file.close()
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- READ OUTPUT FILE
# Initialize variable to store all results
dispersion_general_results = []

dispersion_results = {
    "out_of_rail_time": [],
    "out_of_rail_velocity": [],
    "apogee_time": [],
    "apogee_altitude": [],
    "apogee_x": [],
    "apogee_y": [],
    "impact_time": [],
    "impact_x": [],
    "impact_y": [],
    "impact_velocity": [],
    "initial_static_margin": [],
    "out_of_rail_static_margin": [],
    "final_static_margin": [],
    "number_of_events": [],
    "max_velocity": [],
    "max_acceleration": [],
    "max_load_factor": [],
    "max_parachute_chord_traction_force": [],
    "max_aerodynamic_drag": [],
    "max_aerodynamic_lift": [],
    "max_aerodynamic_spin_moment": [],
    "max_aerodynamic_bending_moment": [],
    "drogue_triggerTime": [],
    "drogue_inflated_time": [],
    "drogue_inflated_velocity": [],
    "execution_time": [],
}

# Get all dispersion results
dispersion_output_file = open(str(filename) + ".disp_outputs.json", "r+")

# Read each line of the file and convert to dict
for line in dispersion_output_file:
    # Skip comments lines
    if line[0] != "{":
        continue
    # Eval results and store them
    flight_result = eval(line)
    dispersion_general_results.append(flight_result)
    for parameter_key, parameter_value in flight_result.items():
        dispersion_results[parameter_key].append(parameter_value)

# Close data file
dispersion_output_file.close()
#--------------------------------------------------------------------------------------------------------



#-------------------------------------------------------------------------------------------------------- COMPARISON GRAPHS
# the commented rows are not implemented yet by rocketpy
print(colored('\n\nComparison graphs:'))
comparison = CompareFlights(flights)

if show_graph:
    comparison.velocities()
    comparison.accelerations()
    comparison.attitude_angles()
    comparison.euler_angles()
    #comparison.attitude_frequency()
    comparison.aerodynamic_forces()
    comparison.aerodynamic_moments()
    comparison.angular_velocities()
    comparison.trajectories_3d()
    comparison.rail_buttons_forces()
    #comparison.stability_margin()

comparison.velocities(filename=str(output_comparison/"velocities.svg"),legend=False)
comparison.accelerations(filename=str(output_comparison/"accelerations.svg"),legend=False)
comparison.attitude_angles(filename=str(output_comparison/"attitude_angles.svg"),legend=False)
comparison.euler_angles(filename=str(output_comparison/"euler_angles.svg"),legend=False)
#comparison.attitude_frequency(filename=str(output_comparison/"attitude_frequency.svg"),legend=False)
comparison.aerodynamic_forces(filename=str(output_comparison/"aerodynamic_forces.svg"),legend=False)
comparison.aerodynamic_moments(filename=str(output_comparison/"aerodynamic_moments.svg"),legend=False)
comparison.angular_velocities(filename=str(output_comparison/"angular_velocities.svg"),legend=False)
comparison.trajectories_3d(filename=str(output_comparison/"trajectories_3d.svg"))
comparison.rail_buttons_forces(filename=str(output_comparison/"rail_buttons_forces.svg"),legend=False)
#comparison.stability_margin(filename=str(output_comparison/"stability_margin.svg"), legend=False)
plt.close('all')
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- DISPERSION GRAPHS
# The following section generates the output distribution plots and automatically saves them on your PC
# To create each picture, the algorythm performs the following actions:

# - Fits a normal distribution to the dataset and compute the average value and standard deviation;
# - Prints the fitted mean and standard deviation,
# - Creates a histogram of the data and overlays the corresponding normal distribution curve;
# - Adds title, axis labels, and a grid to the plot for better clarity;
# - Saves the plot as a .svg file for high-quality output (e.g., for reports or web use);
# - Saves the entire figure as a pickle file for later reuse or resizing;

# The pickle format was chosen so that the user can open the images/graphs files
# (using the design file show_images.py) in a format that allows them to zoom in and out
# and examine the pictures more accurately

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

def plot_graph(dispersion_result, x_label ,title, unit_of_measure):
    
    s = plt.figure()

    out_data = dispersion_results[dispersion_result]
    mu_out, std_out = norm.fit(out_data)

    bars = plt.hist(
        out_data,
        bins=int(number_of_simulations**0.5),
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
    

    # SAVE GRAPH
    
    # as SVG 
    plt.savefig(str(output_dispersion_svg/title)+".svg", format='svg')

    # as pickle
    pickle_file = str(output_dispersion_pickle/title)+".pickle"
    with open(pickle_file, "wb") as f:
        pickle.dump(s, f)

    if show_graph:
        plt.show()

    plt.close(s)    # Stop automatic printing of images

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
    #"Maximum Load Factor":["max_load_factor","Load Factor","G"],
    "Maximum Aerodynamic Drag":["max_aerodynamic_drag","Drag Force","N"],
    "Maximum Aerodynamic Lift":["max_aerodynamic_lift","Lift Force", "N"],
    "Maximum Aerodynamic Spin Moment":["max_aerodynamic_spin_moment","Spin Moment", "N*m"],
    "Maximum Aerodynamic Bending Moment":["max_aerodynamic_bending_moment","Bending Moment", "N*m"],
    #"Parachute Events":["number_of_events","Number of Parachute Events"],
    "Drogue Parachute Trigger Time":["drogue_triggerTime","Time", "s"],
    "Drogue Parachute Fully Inflated Time":["drogue_inflated_time","Time", "s"],
    "Drogue Parachute Fully Inflated Velocity":["drogue_inflated_velocity","Velocity", "m/s"],
}

print(colored('\n\nDispersion graphs:\n'))
for pp in all_plots:
    plot_graph(
        title=pp,
        dispersion_result=all_plots[pp][0],
        x_label=all_plots[pp][1],
        unit_of_measure=all_plots[pp][2]
        )
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- LAUNCH SITE
print(colored('\n\nLaunch site graph:'))
# Import background map
img = imread(str(BASE_DIR / "simulation_inputs/environment_data/Villafranca_airfield_launch_site.jpg"))

# Retrieve dispersion data por apogee and impact XY position
apogee_x = np.array(dispersion_results["apogee_x"])
apogee_y = np.array(dispersion_results["apogee_y"])
impact_x = np.array(dispersion_results["impact_x"])
impact_y = np.array(dispersion_results["impact_y"])

# Define function to calculate eigen values
def eigsorted(cov):
    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    return vals[order], vecs[:, order]

# Create plot figure
s = plt.figure(num=None, dpi = 150, facecolor="w", edgecolor="k")
ax = plt.subplot(111)

# Draw launch point
plt.scatter(0, 0, s=30, marker="*", color="red", label="Launch Point")
# Draw apogee points
plt.scatter(
    apogee_x, apogee_y, s=5, marker="^", color="lime", label="Simulated Apogee", alpha=0.7
)
# Draw impact points
plt.scatter(
    impact_x, impact_y, s=5, marker="v", color="cyan", label="Simulated Landing Point", alpha=0.7
)

# Calculate error ellipses for impact
impactCov = np.cov(impact_x, impact_y)
impactVals, impactVecs = eigsorted(impactCov)
impactTheta = np.degrees(np.arctan2(*impactVecs[:, 0][::-1]))
impactW, impactH = 2 * np.sqrt(impactVals)

# Draw error ellipses for impact
impact_ellipses = []
for j in [1, 2, 3]:
    impactEll = Ellipse(
        xy=(np.mean(impact_x), np.mean(impact_y)),
        width=impactW * j,
        height=impactH * j,
        angle=impactTheta,
        color="black",
    )
    impactEll.set_facecolor((0, 0, 1, 0.2))
    impact_ellipses.append(impactEll)
    ax.add_artist(impactEll)

# Calculate error ellipses for apogee
apogeeCov = np.cov(apogee_x, apogee_y)
apogeeVals, apogeeVecs = eigsorted(apogeeCov)
apogeeTheta = np.degrees(np.arctan2(*apogeeVecs[:, 0][::-1]))
apogeeW, apogeeH = 2 * np.sqrt(apogeeVals)

# Draw error ellipses for apogee
for j in [1, 2, 3]:
    apogeeEll = Ellipse(
        xy=(np.mean(apogee_x), np.mean(apogee_y)),
        width=apogeeW * j,
        height=apogeeH * j,
        angle=apogeeTheta,
        color="black",
    )
    apogeeEll.set_facecolor((0, 1, 0, 0.2))
    ax.add_artist(apogeeEll)

plt.legend()

plt.grid(visible=True, which='minor', linestyle='--', color='grey', alpha=0.3, linewidth=0.6)
plt.grid(visible=True, which='major', linestyle='-', color='white', alpha=0.4, linewidth=0.8)

# Add title and labels to plot
ax.set_title(
    r"1$\sigma$, 2$\sigma$ and 3$\sigma$ Dispersion Ellipses: Apogee and Landing Points"
)
ax.set_ylabel("North (m)")
ax.set_xlabel("East (m)")
# Add background image to plot
# You can translate the basemap by changing dx and dy (in meters)
dx = 250
dy = -150
plt.imshow(img, zorder=0, extent=[-850-dx, 850-dx, -500-dy, 500-dy])
plt.axhline(0, color="black", linewidth=0.5)
plt.axvline(0, color="black", linewidth=0.5)
plt.xlim(-850, 850)
plt.ylim(-500, 500)

# Save plot and show result
plt.savefig(str(output_launch_site) + "/Villafranca_launch_site.svg", format='svg', bbox_inches="tight")
# as pickle
pickle_file = str(output_launch_site) + "/Villafranca_launch_site.pickle"
with open(pickle_file, "wb") as f:
    pickle.dump(s, f)

print("- Villafranca launch site graph saved successfully")

if show_graph:
    plt.show()
plt.close('all')
#--------------------------------------------------------------------------------------------------------





#-------------------------------------------------------------------------------------------------------- SENSITIVITY ANALYSIS
if sensitivity_analysis:
    print(colored('\n\nSensitivity analysis graphs:'))


    target_variables = ["apogee_altitude","max_acceleration"]
    parameters = list(analysis_parameters.keys())

    parameters_matrix, target_variables_matrix = load_monte_carlo_data(
        input_filename=str(filename)+".disp_inputs.json",
        output_filename=str(filename)+".disp_outputs.json",
        parameters_list=parameters,
        target_variables_list=target_variables,
    )




    model = SensitivityModel(parameters, target_variables)


    parameters_nominal_mean = [
        analysis_parameters[parameter_name][0]
        for parameter_name in analysis_parameters.keys()
    ]
    parameters_nominal_sd = [
        analysis_parameters[parameter_name][1]
        for parameter_name in analysis_parameters.keys()
    ]
    model.set_parameters_nominal(parameters_nominal_mean, parameters_nominal_sd)
    target_variables_mean=[
    np.mean(dispersion_results["apogee_altitude"]),
    np.mean(dispersion_results["max_acceleration"])
    ]

    #plot the result of the sensitviy analisys
    model.set_target_variables_nominal(target_variables_mean)

    model.fit(parameters_matrix, target_variables_matrix)


    # Workaround (RocketPy doesn't provide a save option):
    # plt.ion() lets the code continue while bar_plot is displayed.
    # Figures are saved and remain open for viewing if desired.
    plt.ion() 
    model.plots.bar_plot()

    for target in range(len(target_variables)):
        sens_fig = plt.figure(target+1)

        svg_file = f"{str(output_sensitivity)}/sensitivity_{target_variables[target]}.svg"
        sens_fig.savefig(svg_file, dpi=300)

    if show_graph:
        plt.pause(99999) # that's a lot of damag...time.

    plt.close("all")
    plt.ioff()

    print("- Sensitivity analysis graphs saved successfully")
#-------------------------------------------------------------------------------------------------------

FRED.draw()
Solid_motor.draw()