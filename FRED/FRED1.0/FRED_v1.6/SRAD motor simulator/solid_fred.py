import numpy as np
from scipy.optimize import root_scalar
import math
from rocketcea.cea_obj_w_units import CEA_Obj
from rocketcea.cea_obj import add_new_propellant
from plotly.subplots import make_subplots
import plotly.graph_objects as go

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

Mdry = 2.086  # [kg] empty mass

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


D_ext = D_cc - 2 * tp_thickness                     # [m] external diameter of the cilindrical grain
D_int= 0.015                                        # [m] internal diameter of the cilindrical grain                                                                               # INPUT
n_grains = 1                                        # number of cilindrical grains                                                                                                 # INPUT
grains_distance = 0.002                             # [m] keep it also with 1 grain to let the basis burn
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


import csv

# --- THRUST
thrust_curve = np.column_stack((time[:index_burnout], T[:index_burnout]))

with open('SRAD_thrustcurve.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerows(thrust_curve)

print("thrustcurve salvata in csv")

print("Burnout time = ",t_burnout)

print("Impulse = ",I_total)