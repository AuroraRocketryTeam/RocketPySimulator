"""
Centers of mass and inertias of an SRAD motor, from the parameters file written by the propulsion
notebook (ATLAS_PARAMETERS_*.txt: lengths in mm, masses in kg).

Prints mass and center of mass of every part, center of mass and inertias of the dry motor, of the
grains and of the loaded motor; saves them in mass_properties.csv and draws the motor section
(motor_section.png / .pdf), next to the parameters file or in --output.
Then checks the part masses against the notebook ones (warning above 0.1 %).

Axis x from the nozzle exit (x = 0) towards the combustion chamber, as RocketPy's
coordinate_system_orientation="nozzle_to_combustion_chamber". Inertias are about the center of mass of
the same group of parts: I_11 perpendicular to the axis, I_33 around it.

Layout (the lengths the notebook uses to size the grains, which then fill the casing exactly):
  nozzle            0 -> L_total             divergent from the exit, then convergent
  casing            L_total - (L_nozzle_ring + nozzle_housing_length) -> + L_cc
                    the nozzle sits in its last 70 mm: nozzle ring at the aft end, then the housing
  grains and gaps   L_total -> + length_tp   inside the thermal protection liner
  thermal protection forward closure (tp_thickness), then the bulkhead (L_bulkhead)
  casing closure    the notebook adds a disc 2*th_casing thick and keeps no length for it: it is the
                    closed face of the bulkhead, against the thermal protection closure
The masses use the notebook formulas, so they add up to M_motor_dry and M_pr.

Usage:
    python Atlas/tools/propulsion/motor_geometry/motor_mass_properties.py "<ATLAS_PARAMETERS file>.txt"
    python Atlas/tools/propulsion/motor_geometry/motor_mass_properties.py <file> --rho-nozzle 1800 --output <folder>
    python Atlas/tools/propulsion/motor_geometry/motor_mass_properties.py <file> --no-drawing
"""
import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Material densities of the propulsion notebook (kg/m^3), not written in the parameters file
RHO_CASING = 2700       # aluminium 6082 T6: casing, bulkhead, nozzle ring
RHO_PHENOLIC = 1500     # thermal protection
RHO_NOZZLE = 1950       # graphite nozzle

N_SLICES = 4000
MASS_TOLERANCE = 0.001  # relative difference from the notebook masses that gives a warning


@dataclass
class Part:
    name: str
    group: str          # "dry" or "propellant"
    density: float
    x0: float
    x1: float
    r_out: object       # radius as a function of x (m)
    r_in: object
    color: str

    def slices(self):
        x = np.linspace(self.x0, self.x1, N_SLICES + 1)
        xc = (x[:-1] + x[1:]) / 2
        ro, ri = self.r_out(xc), self.r_in(xc)
        dx = np.diff(x)
        dm = self.density * np.pi * (ro**2 - ri**2) * dx
        return xc, dm, ro, ri, dx


def constant(value):
    return lambda x: np.full_like(x, value, dtype=float)


def read_parameters(path):
    """{name: value} from the notebook file: one '"name" = value' per line."""
    parameters = {}
    for line in Path(path).read_text().splitlines():
        if "=" in line:
            name, value = line.split("=")
            parameters[name.strip().strip('"')] = float(value)
    return parameters


def build_parts(p, rho_casing=RHO_CASING, rho_phenolic=RHO_PHENOLIC, rho_nozzle=RHO_NOZZLE):
    mm = lambda key: p[key] / 1000
    D_cc, D_cc_outer, th_casing, L_cc = mm("D_cc"), mm("D_cc_outer"), mm("th_casing"), mm("L_cc")
    L_bulkhead, th_fillet = mm("L_bulkhead"), mm("th_bulkhead_fillet")
    tp, L_tp = mm("tp_thickness"), mm("length_tp")
    D_throat, D_exit = mm("D_throat"), mm("D_exit")
    L_conv, L_div, L_total = mm("L_conv"), mm("L_div"), mm("L_total")
    L_ring, th_ring, L_housing = mm("L_nozzle_ring"), mm("th_nozzle_ring"), mm("nozzle_housing_length")
    D_ext, D_int, L_grain = mm("D_ext"), mm("D_int"), mm("L_single_grain")
    gap, n_grains = mm("grains_distance"), int(p["n_grains"])

    # Axial stations from the nozzle exit (m)
    x_casing_aft = L_total - (L_ring + L_housing)
    x_grains = L_total
    x_tp_closure = x_grains + L_tp
    x_bulkhead = x_tp_closure + tp
    x_casing_fwd = x_casing_aft + L_cc
    if abs(x_bulkhead + L_bulkhead - x_casing_fwd) > 1e-6:
        raise ValueError("Nozzle, grains, thermal protection and bulkhead do not fill the casing: check the file")

    # Grain density from the propellant mass, as the notebook does
    grain_volume = n_grains * np.pi * ((D_ext / 2) ** 2 - (D_int / 2) ** 2) * L_grain
    rho_grain = p["M_pr"] / grain_volume

    nozzle_bore = lambda x: np.where(
        x < L_div,
        D_exit / 2 + (D_throat - D_exit) / 2 * x / L_div,
        D_throat / 2 + (D_cc - D_throat) / 2 * (x - L_div) / L_conv,
    )
    parts = [
        Part("nozzle", "dry", rho_nozzle, 0, L_total, constant(D_cc / 2), nozzle_bore, "#52514e"),
        Part("nozzle ring", "dry", rho_casing, x_casing_aft, x_casing_aft + L_ring,
             constant(D_cc / 2), constant(D_cc / 2 - th_ring), "#2a78d6"),
        Part("casing tube", "dry", rho_casing, x_casing_aft, x_casing_fwd,
             constant(D_cc_outer / 2), constant(D_cc / 2), "#86b6ef"),
        Part("thermal protection liner", "dry", rho_phenolic, x_grains, x_tp_closure,
             constant(D_cc / 2), constant(D_cc / 2 - tp), "#eda100"),
        Part("thermal protection closure", "dry", rho_phenolic, x_tp_closure, x_bulkhead,
             constant(D_cc / 2), constant(0), "#eda100"),
        Part("bulkhead", "dry", rho_casing, x_bulkhead, x_bulkhead + L_bulkhead,
             constant(D_cc / 2), constant(D_cc / 2 - th_fillet), "#184f95"),
        Part("casing closure", "dry", rho_casing, x_bulkhead, x_bulkhead + 2 * th_casing,
             constant(D_cc / 2), constant(0), "#184f95"),
    ]
    for k in range(n_grains):
        x0 = x_grains + gap + k * (L_grain + gap)
        parts.append(Part(f"grain {k + 1}", "propellant", rho_grain, x0, x0 + L_grain,
                          constant(D_ext / 2), constant(D_int / 2), "#eb6834"))
    return parts


def mass_properties(parts):
    """Mass, center of mass and inertias (about that center of mass) of a list of parts."""
    data = [part.slices() for part in parts]
    x, dm, ro, ri, dx = (np.concatenate([d[i] for d in data]) for i in range(5))
    mass = dm.sum()
    cm = (dm * x).sum() / mass
    I_33 = (0.5 * dm * (ro**2 + ri**2)).sum()
    # every slice is a short hollow cylinder: radial spread + axial spread + transport to the CG
    I_11 = (0.25 * dm * (ro**2 + ri**2) + dm * dx**2 / 12 + dm * (x - cm) ** 2).sum()
    return mass, cm, I_11, I_33


def check_notebook(parts, p):
    """Masses of the script against the ones in the notebook file; warning above MASS_TOLERANCE."""
    mass = {part.name: mass_properties([part])[0] for part in parts}
    grains = sum(m for name, m in mass.items() if name.startswith("grain"))
    dry = sum(m for name, m in mass.items() if not name.startswith("grain"))
    checks = [
        ("M_casing", mass["casing tube"] + mass["bulkhead"] + mass["casing closure"], "casing + bulkhead + closure"),
        ("M_tp", mass["thermal protection liner"] + mass["thermal protection closure"], "liner + closure"),
        ("M_nozzle", mass["nozzle"], "nozzle"),
        ("M_nozzle_ring", mass["nozzle ring"], "nozzle ring"),
        ("M_motor_dry", dry, "dry motor"),
        ("M_pr", grains, "grains"),
    ]
    print(f"\nCheck against the notebook masses [kg]:\n{'':14s} {'script':>8s} {'notebook':>9s} {'diff':>8s}")
    warnings = 0
    for key, value, parts_used in checks:
        if key not in p:
            print(f"{key:14s} {value:8.4f} {'-':>9s}           not in the file")
            continue
        diff = (value - p[key]) / p[key]
        flag = "" if abs(diff) <= MASS_TOLERANCE else "   <!> WARNING"
        warnings += bool(flag)
        print(f"{key:14s} {value:8.4f} {p[key]:9.4f} {diff:+8.3%}  {parts_used}{flag}")
    if warnings:
        print(f"<!> WARNING: {warnings} masses differ from the notebook by more than {MASS_TOLERANCE:.1%}: "
              "check densities (--rho-*) and the parts in build_parts")


def draw(parts, results, path):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    fig, ax = plt.subplots(figsize=(13, 3.6))
    labelled = set()
    for part in parts:
        x = np.linspace(part.x0, part.x1, 200)
        ro, ri = part.r_out(x) * 1000, part.r_in(x) * 1000
        label = "grain" if part.group == "propellant" else part.name
        if label.startswith("thermal protection"):
            label = "thermal protection"
        for sign in (1, -1):
            outline = np.column_stack((np.r_[x, x[::-1]] * 1000, sign * np.r_[ro, ri[::-1]]))
            ax.add_patch(Polygon(outline, closed=True, facecolor=part.color, edgecolor="#0b0b0b", linewidth=0.4,
                                 label=label if (label not in labelled and sign == 1) else None))
        labelled.add(label)

    markers = {"dry": ("o", "#0b0b0b"), "propellant": ("s", "#eb6834"), "loaded": ("D", "#1baf7a")}
    for key, (marker, color) in markers.items():
        _, cm, _, _ = results[key]
        ax.plot(cm * 1000, 0, marker=marker, color=color, markersize=8, linestyle="none",
                markeredgecolor="white", label=f"CG {key}: {cm * 1000:.0f} mm")
    ax.axhline(0, color="#52514e", linewidth=0.6, linestyle="-.")

    length = max(part.x1 for part in parts) * 1000
    ax.set_xlim(-20, length + 20)
    ax.set_ylim(-65, 65)
    ax.set_aspect("equal")
    ax.set_xlabel("distanza dall'uscita dell'ugello [mm]")
    ax.set_ylabel("raggio [mm]")
    ax.set_title("Motore SRAD: sezione e baricentri", loc="center")
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    for suffix in (".png", ".pdf"):
        fig.savefig(path.with_suffix(suffix), dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("parameters", type=Path, help="ATLAS_PARAMETERS_*.txt written by the propulsion notebook")
    parser.add_argument("--output", type=Path, help="output folder (default: the folder of the parameters file)")
    parser.add_argument("--rho-casing", type=float, default=RHO_CASING, help="kg/m^3")
    parser.add_argument("--rho-phenolic", type=float, default=RHO_PHENOLIC, help="kg/m^3")
    parser.add_argument("--rho-nozzle", type=float, default=RHO_NOZZLE, help="kg/m^3")
    parser.add_argument("--no-drawing", action="store_true")
    args = parser.parse_args()

    p = read_parameters(args.parameters)
    parts = build_parts(p, args.rho_casing, args.rho_phenolic, args.rho_nozzle)
    dry = [part for part in parts if part.group == "dry"]
    propellant = [part for part in parts if part.group == "propellant"]
    results = {
        "dry": mass_properties(dry),
        "propellant": mass_properties(propellant),
        "loaded": mass_properties(parts),
    }

    print(f"{'part':28s} {'mass [kg]':>10s} {'from [m]':>9s} {'to [m]':>8s} {'CG [m]':>8s}")
    for part in parts:
        mass, cm, _, _ = mass_properties([part])
        print(f"{part.name:28s} {mass:10.4f} {part.x0:9.4f} {part.x1:8.4f} {cm:8.4f}")

    print(f"\n{'':12s} {'mass [kg]':>10s} {'CG [m]':>8s} {'I_11 [kg*m^2]':>14s} {'I_33 [kg*m^2]':>14s}")
    for key, (mass, cm, I_11, I_33) in results.items():
        print(f"{key:12s} {mass:10.4f} {cm:8.4f} {I_11:14.4f} {I_33:14.5f}")
    print(f"\nnotebook: M_motor_dry = {p['M_motor_dry']:.4f} kg, M_pr = {p['M_pr']:.4f} kg; "
          f"motor length {max(part.x1 for part in parts):.4f} m")
    print("For RocketPy (motor.csv): motor_dry_mass_position = CG dry, motor_inertia_11/33 = I dry, "
          "grains_center_of_mass_position = CG propellant")

    output = args.output or args.parameters.parent
    output.mkdir(parents=True, exist_ok=True)
    with open(output / "mass_properties.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["# from " + args.parameters.name + "; positions from the nozzle exit, "
                         "inertias about the center of mass of each group"])
        writer.writerow(["group", "mass [kg]", "CG [m]", "I_11 [kg*m^2]", "I_33 [kg*m^2]"])
        for key, values in results.items():
            writer.writerow([key] + [f"{value:.6g}" for value in values])
        writer.writerow([])
        writer.writerow(["part", "mass [kg]", "from [m]", "to [m]", "CG [m]"])
        for part in parts:
            mass, cm, _, _ = mass_properties([part])
            writer.writerow([part.name, f"{mass:.6g}", f"{part.x0:.6g}", f"{part.x1:.6g}", f"{cm:.6g}"])
    if not args.no_drawing:
        draw(parts, results, output / "motor_section")
    print(f"\nSaved in {output}")

    check_notebook(parts, p)


if __name__ == "__main__":
    main()
