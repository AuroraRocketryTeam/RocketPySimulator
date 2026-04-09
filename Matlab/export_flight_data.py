import numpy as np
import json

def convert_numpy(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def export_flight_data(flight_setting, flight_data, exec_time, dispersion_input_file, dispersion_output_file):
    # Flight results
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
        "apogee_altitude": flight_data.apogee - flight_data.env.elevation,
        "apogee_x": flight_data.apogee_x,
        "apogee_y": flight_data.apogee_y,
        "impact_time": flight_data.t_final,
        "impact_x": flight_data.x_impact,
        "impact_y": flight_data.y_impact,
        "impact_velocity": flight_data.impact_velocity,
        "initial_static_margin": flight_data.rocket.static_margin(0),
        "out_of_rail_static_margin": flight_data.rocket.static_margin(flight_data.out_of_rail_time),
        "final_static_margin": flight_data.rocket.static_margin(flight_data.rocket.motor.burn_out_time),
        "number_of_events": len(flight_data.parachute_events),
        "execution_time": exec_time
    }

    # Parachute
    if len(flight_data.parachute_events) > 0:
        trigger = flight_data.parachute_events[0][0]
        lag = flight_data.parachute_events[0][1].lag
        flight_result["drogue_triggerTime"] = trigger
        flight_result["drogue_inflated_time"] = trigger + lag
        flight_result["drogue_inflated_velocity"] = flight_data.speed(trigger + lag)
    else:
        flight_result["drogue_triggerTime"] = 0
        flight_result["drogue_inflated_time"] = 0
        flight_result["drogue_inflated_velocity"] = 0

    # Write JSON directly to files
    with open(dispersion_input_file, "a") as f_in:
        if isinstance(flight_setting, list):
            for fs in flight_setting:
                f_in.write(json.dumps(fs, default=convert_numpy) + "\n")
        else:
            f_in.write(json.dumps(flight_setting, default=convert_numpy) + "\n")

    with open(dispersion_output_file, "a") as f_out:
        f_out.write(json.dumps(flight_result, default=convert_numpy) + "\n")

    return flight_result