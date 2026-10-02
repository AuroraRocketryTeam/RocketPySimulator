"""
Quick EuRoC check of the parachutes (RQT-0360 and RQT-0380) with the terminal velocity formula,
for a range of rocket masses. Moved here from the end of the old Monte Carlo script.
For the full analysis with RocketPy use parachute_study.py.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import atlas_model as model

# function that takes a text and add code for green color (ANSI Escape Codes)
colored = lambda text: '\033[32m'+str(text)+'\033[0m'   # 32 green

# PARACHUTE ANALYSIS FUNCTIONS 

rho_o = 1.225  # air density [kg/m^3]
rho_450 = 1.167
rho_3000 = 0.909 # air density 3000m [kg/m^3] 
g = 9.80665 


def terminal_velocity_drogue(mass, cd_s, air_density):
    # Steady-state descent velocity under parachute.
    return np.sqrt((2 * mass * g) / (air_density * cd_s))

def terminal_velocity_main(mass, cd_s):
    # Steady-state descent velocity under parachute.
    return np.sqrt((2 * mass * g) / (rho_o * cd_s))

def opening_shock(mass, pre_opening_velocity, cd_s_main, air_density):
    # Estimates opening shock force and equivalent g-load at main parachute deployment.
    F = 0.5 * air_density * cd_s_main * pre_opening_velocity**2
    a_g = (F / mass) / g
    return F, a_g


#--------------------------------------------------------------------------------- EuRoC PARACHUTE, MASS & SHOCK ANALYSIS
if __name__ == "__main__":
    print(colored('\n\nEuRoC PARACHUTE and MASS VALIDATION:'))
    # nominal CdS values
    nominal = model.nominal(model.load_parameters())
    cd_s_drogue = nominal["cd_s_drogue"]
    cd_s_main = nominal["cd_s_main"]

    masses = np.linspace(
        20,
        40,
        200
    )

    # terminal velocities
    main_v = np.array([terminal_velocity_main(m, cd_s_main) for m in masses])

    # air_density = 1 # kg/m^3    
    drogue_v_3000 = np.array([terminal_velocity_drogue(m, cd_s_drogue, rho_3000) for m in masses])
    drogue_v_450 = np.array([terminal_velocity_drogue(m, cd_s_drogue, rho_450) for m in masses])

    # page 30 of System requirements document:

    # EuRoC-LV-RQT-0360: Initial deployment velocity
    # The initial deployment event shall result in a descent velocity between 23 and 46 m/s.
    print(colored('\nDrogue:'))
    print("EuRoC-LV-RQT-0360: Initial deployment velocity")
    print("The initial deployment event shall result in a descent velocity between 23 and 46 m/s.")
    #valid_drogue3000 = (drogue_v_3000 >= 23) & (drogue_v_3000 <= 46)
    valid_drogue450 = (drogue_v_450 >= 23) & (drogue_v_450 <= 46)
    
    if np.any(valid_drogue450):
        m_min = masses[valid_drogue450][0]
        m_max = masses[valid_drogue450][-1]
        
        print(f"\nValid mass range s.t.v is more than 23 m/s and less than 46 m/s: {m_min:.2f} – {m_max:.2f} kg")
        #print(f"Corresponding descent velocity range (3000m): {drogue_v_3000[valid_drogue3000][0]:.2f} – {drogue_v_3000[valid_drogue3000][-1]:.2f} m/s")
        print(f"Corresponding descent velocity range (450m): {drogue_v_450[valid_drogue450][0]:.2f} – {drogue_v_450[valid_drogue450][-1]:.2f} m/s")
        # shock estimate at worst case (max mass)
        # assuming an instantanuous fully inflation 'n' seconds after the apogee with g = 9.81 m/s^2
        seconds_after_apogee = 4
        v_pre = g*seconds_after_apogee
        # F, g_load = opening_shock(m_max, v_pre, cd_s_drogue, rho_3000)

        # print(colored('\nDROGUE DEPLOYMENT SHOCK ESTIMATE (worst case, with maximum mass)'))
        # print(f"- Pre-deployment velocity ({seconds_after_apogee:.2f} seconds after apogee): {v_pre:.2f} m/s")
        # print(f"- Opening force: {F:.0f} N")
        # print(f"- Equivalent load: {g_load:.1f} g")
    else:
        print("\nNO MASS RANGE satisfies EuRoC drogue parachute constraint (≥ 23 m/s and ≤ 46 m/s)")

    # EuRoC-LV-RQT-0380: Main deployment event descent velocity
    # The main deployment event shall result in a descent velocity of less than 9 m/s.
    print(colored('\nMain:'))
    print("EuRoC-LV-RQT-0380: Main deployment event descent velocity")
    print("The main deployment event shall result in a descent velocity of less than 9 m/s.")
    valid_main = main_v <= 9.0

    if np.any(valid_main):
        m_min = masses[valid_main][0]
        m_max = masses[valid_main][-1]
        
        print(f"\nValid mass range s.t. v is less than 9 m/s: {m_min:.2f} – {m_max:.2f} kg")
        print(f"Corresponding descent velocity range: {main_v[valid_main][0]:.2f} – {main_v[valid_main][-1]:.2f} m/s")

        # shock estimate at worst case (max mass)
        # v_pre = terminal_velocity_drogue(m_max, cd_s_drogue, air_density)
        # F, g_load = opening_shock(m_max, v_pre, cd_s_main)

        # print(colored('\nMAIN DEPLOYMENT SHOCK ESTIMATE (worst case, with maximum mass)'))
        # print(f"- Pre-deployment velocity (drogue): {v_pre:.2f} m/s")
        # print(f"- Opening force: {F:.0f} N")
        # print(f"- Equivalent load: {g_load:.1f} g")

    else:
        print("\nNO MASS RANGE satisfies EuRoC main parachute constraint (≤ 9 m/s)")

    # Opening shock is estimated using a quasi-steady aerodynamic model at deployment velocity,
    # assuming instantaneous transition to fully inflated parachute.
    #
    # This does not model parachute inflation dynamics or transient load overshoot, and therefore
    # represents an equivalent steady-state aerodynamic load rather than the true peak opening shock.
    #
    # A physically accurate peak load estimate would require additional manufacturer data,
    # including: inflation time scale, evolution of Cd*S during deployment
    # and experimentally derived opening load factors or peak load curves vs deployment velocity.
#--------------------------------------------------------------------------------------------------------
