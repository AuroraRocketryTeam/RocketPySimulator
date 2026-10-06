"""
Positions of every component of an OpenRocket file (.ork), measured from the nose tip, and the
values that go in geometry.csv, compared with the geometry.csv next to the .ork. Writes a new
geometry.csv in <version>/ next to this script, with "---" in the fields that the .ork can't give
(mass, inertias and center of mass without motor, rail button angle): fill them and copy the file
into simulation_inputs/geometry_data/<version>/.

Reads only the geometry written in the .ork (XML, zipped or not): no OpenRocket, no Java. The motor
of the .ork is ignored: in RocketPy the motor is modelled on its own (motor.csv), so the rocket is the
configuration without motor. Masses, center of mass and inertias are not computed here: they come
from an OpenRocket simulation (openrocket_simulationdata.csv).

Usage:
    python Atlas/tools/geometry/ork_positions/ork_positions.py Atlas/simulation_inputs/geometry_data/<version>/rocket.ork
    python Atlas/tools/geometry/ork_positions/ork_positions.py <file>.ork --geometry <geometry.csv> --output <file>.csv
"""
import argparse
import math
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

# Components that make the outer body, one after the other from the nose
EXTERNAL = {"nosecone", "bodytube", "transition"}
# RocketPy nose cone kinds for the OpenRocket shapes ("haack" depends on the shape parameter)
NOSE_KINDS = {"conical": "conical", "ogive": "ogive", "ellipsoid": "elliptical", "power": "powerseries",
              "parabolic": "parabolic"}
HERE = Path(__file__).resolve().parent
MISSING = "---"
TOLERANCE = 0.001        # m: differences from geometry.csv above this are marked
ANGLE_TOLERANCE = 0.1    # deg, for fin_sweep_angle


def read_ork(path):
    """Root element of the .ork, which can be plain XML or a zip holding rocket.ork."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            name = next(n for n in archive.namelist() if n.endswith(".ork"))
            return ET.fromstring(archive.read(name))
    return ET.parse(path).getroot()


def number(element, tag, default=0.0):
    """Value of a numeric field; OpenRocket writes automatic values as 'auto 0.075'."""
    text = element.findtext(tag)
    if text is None or text.strip() in ("", "auto"):
        return default
    return float(text.split()[-1])


def length(element):
    """Axial length of a component, as OpenRocket uses it to place the component."""
    if element.tag.endswith("finset"):
        return number(element, "rootchord")
    if element.tag == "railbutton":
        return number(element, "outerdiameter")
    if element.find("length") is not None:
        return number(element, "length")
    return number(element, "packedlength")


def placement(element):
    """(method, offset) of a component; without one, it follows the previous component."""
    for tag, key in (("axialoffset", "method"), ("position", "type")):
        field = element.find(tag)
        if field is not None:
            return field.get(key), float(field.text)
    return "after", 0.0


def walk(element, parent_top, parent_length, depth, rows):
    """Absolute position of every component under element (its <subcomponents>)."""
    subcomponents = element.find("subcomponents")
    if subcomponents is None:
        return
    previous_end = parent_top
    for component in subcomponents:
        if component.tag in ("motormount", "motor"):
            continue
        size = length(component)
        method, offset = placement(component)
        if component.tag in EXTERNAL and depth == 0:
            method, offset = "after", 0.0  # the outer body is always one piece after the other
        top = {
            "after": previous_end + offset,
            "top": parent_top + offset,
            "middle": parent_top + (parent_length - size) / 2 + offset,
            "bottom": parent_top + parent_length - size + offset,
            "absolute": offset,
        }[method]
        rows.append({"element": component, "type": component.tag, "name": component.findtext("name"),
                     "from": top, "to": top + size, "depth": depth,
                     "motor_mount": component.find("motormount") is not None})
        previous_end = top + size
        walk(component, top, size, depth + 1, rows)


def components(root):
    rows = []
    for stage in root.iter("stage"):
        walk(stage, 0.0, 0.0, 0, rows)
    return rows


def ignored_motors(root):
    """Motors of the .ork, listed only to say that they are ignored."""
    motors = []
    for mount_tube in root.iter():
        mount = mount_tube.find("motormount")
        if mount is None:
            continue
        for motor in mount.iter("motor"):
            motors.append(f"{motor.findtext('designation')} nel tubo '{mount_tube.findtext('name')}'")
    return motors


def geometry_values(rows):
    """geometry.csv values (positions from the nose tip, in m), with notes for the reader."""
    body = [r for r in rows if r["depth"] == 0]
    nose = next(r for r in body if r["type"] == "nosecone")
    tail = body[-1]
    fins = [r for r in rows if r["type"].endswith("finset")]
    buttons = sorted((r for r in rows if r["type"] == "railbutton"), key=lambda r: r["from"])
    values, notes = {}, []

    radius = max(number(r["element"], "radius", number(r["element"], "aftradius")) for r in body)
    values["radius"] = radius

    shape = nose["element"].findtext("shape")
    if shape == "haack":
        parameter = number(nose["element"], "shapeparameter")
        kind = {0.0: "von karman", round(1 / 3, 3): "lvhaack"}.get(round(parameter, 3), f"haack C = {parameter}")
    else:
        kind = NOSE_KINDS.get(shape, shape)
    values["nose_length"] = nose["to"] - nose["from"]
    values["nose_position"] = nose["from"]
    notes.append(f"ogiva: forma '{kind}' per RocketPy")
    values["nose_kind"] = kind

    if fins:
        fin = fins[0]["element"]
        span, sweep = number(fin, "height"), number(fin, "sweeplength")
        values["fin_number"] = number(fin, "fincount")
        values["fin_span"] = span
        values["fin_root_chord"] = number(fin, "rootchord")
        values["fin_tip_chord"] = number(fin, "tipchord")
        values["fin_position"] = fins[0]["from"]
        values["fin_sweep_angle"] = math.degrees(math.atan2(sweep, span))
        under = [r for r in body if r["from"] < fins[0]["to"] and r["to"] > fins[0]["from"]]
        notes.append("alette sopra: " + ", ".join(f"{r['name']} ({r['type']})" for r in under))

    if tail["type"] == "transition":
        values["tail_top_radius"] = number(tail["element"], "foreradius")
        values["tail_bottom_radius"] = number(tail["element"], "aftradius")
        values["tail_length"] = tail["to"] - tail["from"]
        values["tail_position"] = tail["from"]
        values["tail_shape"] = tail["element"].findtext("shape")
        notes.append(f"coda: forma '{values['tail_shape']}' in OpenRocket, conica in RocketPy")

    if buttons:
        # RocketPy wants the point of each button: its center along the axis
        values["upper_button_position"] = (buttons[0]["from"] + buttons[0]["to"]) / 2
        values["lower_button_position"] = (buttons[-1]["from"] + buttons[-1]["to"]) / 2
        if len(buttons) > 2:
            notes.append(f"{len(buttons)} rail button: RocketPy usa il primo e l'ultimo")

    values["motor_position"] = tail["to"]
    notes.append("motor_position = fine del razzo (uscita dell'ugello)")
    return values, notes


# geometry.csv rows in the order of the file: (name, unit, note); the .ork has no masses or inertias
ROWS = [
    ("rocket_dry_mass", "kg", "razzo senza motore (simulazione OpenRocket meno il motore)"),
    ("rocket_dry_inertia_11", "kg*m^2", "perpendicolare all'asse; razzo senza motore"),
    ("rocket_dry_inertia_33", "kg*m^2", "attorno all'asse; razzo senza motore"),
    ("center_of_mass_without_motor", "m", "razzo senza motore"),
    ("motor_position", "m", "uscita dell'ugello = fine del razzo"),
    ("radius", "m", ""),
    ("nose_length", "m", "ogiva {nose_kind}"),
    ("nose_position", "m", ""),
    ("fin_number", "-", ""),
    ("fin_span", "m", ""),
    ("fin_root_chord", "m", ""),
    ("fin_tip_chord", "m", ""),
    ("fin_position", "m", "inizio della root chord"),
    ("fin_sweep_angle", "deg", ""),
    ("tail_top_radius", "m", ""),
    ("tail_bottom_radius", "m", ""),
    ("tail_length", "m", "forma {tail_shape} nel .ork; conica in RocketPy"),
    ("tail_position", "m", ""),
    ("upper_button_position", "m", "centro del pattino"),
    ("lower_button_position", "m", "centro del pattino"),
    ("button_angular_position", "deg", ""),
]


def write_geometry(values, ork, previous, path):
    """geometry.csv from the .ork; std taken from the previous geometry.csv when it has the parameter."""
    stds = {}
    if previous.is_file():
        table = pd.read_csv(previous, comment="#", skipinitialspace=True).set_index("name")
        stds = {name: f"{float(std):g}" for name, std in table["std"].items()}
    lines = [
        f"# Atlas {ork.parent.name} - geometria del modello OpenRocket {ork.name}, scritta da tools/geometry/ork_positions/ork_positions.py",
        "# Posizioni misurate dalla punta dell'ogiva verso la coda.",
        "# std = deviazione standard usata dalle Monte Carlo (0 = valore fisso); --- = da completare a mano",
        "name,value,std,unit,note",
    ]
    for name, unit, note in ROWS:
        value = f"{values[name]:.5g}" if name in values else MISSING
        lines.append(f"{name},{value},{stds.get(name, MISSING)},{unit},{note.format_map(values)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    missing = [name for name, *_ in ROWS if name not in values]
    print(f"\nScritto {path}\n  da completare: {', '.join(missing)}")


def compare(values, geometry_file):
    table = pd.read_csv(geometry_file, comment="#", skipinitialspace=True).set_index("name")["value"]
    print(f"\nConfronto con {geometry_file}:")
    print(f"{'parametro':24s} {'.ork':>10s} {'geometry':>10s} {'diff':>9s}")
    for name, value in values.items():
        if isinstance(value, str):
            continue
        if name not in table:
            print(f"{name:24s} {value:10.4f} {'-':>10s}")
            continue
        diff = table[name] - value
        tolerance = ANGLE_TOLERANCE if name.endswith("angle") else TOLERANCE
        flag = "   <!>" if abs(diff) > tolerance else ""
        print(f"{name:24s} {value:10.4f} {table[name]:10.4f} {diff:+9.4f}{flag}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ork", type=Path, help="OpenRocket file")
    parser.add_argument("--geometry", type=Path,
                        help="geometry.csv to compare with (default: the one next to the .ork)")
    parser.add_argument("--output", type=Path,
                        help="geometry.csv to write (default: <version>/geometry.csv next to this script)")
    args = parser.parse_args()

    root = read_ork(args.ork)
    rows = components(root)
    print(f"{'componente':44s} {'da [m]':>8s} {'a [m]':>8s}")
    for r in rows:
        label = "  " * r["depth"] + f"{r['name']} ({r['type']})" + (" [porta-motore]" if r["motor_mount"] else "")
        print(f"{label:44s} {r['from']:8.4f} {r['to']:8.4f}")
    for motor in ignored_motors(root):
        print(f"\nMotore ignorato: {motor}")

    values, notes = geometry_values(rows)
    print("\nValori per geometry.csv (dalla punta dell'ogiva):")
    for name, value in values.items():
        if not isinstance(value, str):
            print(f"  {name:24s} {value:.4f}")
    for note in notes:
        print(f"  - {note}")

    geometry_file = args.geometry or args.ork.with_name("geometry.csv")
    if geometry_file.is_file():
        compare(values, geometry_file)
    write_geometry(values, args.ork, geometry_file, args.output or HERE / args.ork.parent.name / "geometry.csv")


if __name__ == "__main__":
    main()
