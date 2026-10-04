"""
Runs the propulsion notebook locally, without changing it, and saves the thrust curve it computes.

Only the Colab-specific lines are skipped or redirected:
- cell 0 (pip install) and cells 35-38 (static-fire data on the team Drive) are skipped;
- google.colab imports, drive.mount and files.download are removed;
- the Drive CD files of the RocketPy flight (cell 28) are replaced by --cd;
- plotly figures are saved as .html in the output folder instead of being opened.

Writes in the output folder: the notebook files (ATLAS_PARAMETERS_*.txt, ATLAS_chamber_properties.txt),
the figures and thrust_curve.csv ("time [s],thrust [N]", up to burnout).

Usage (with the propulsion venv, see README.md):
    python Atlas/propulsion/run_motor_notebook.py
    python Atlas/propulsion/run_motor_notebook.py --notebook <other notebook>.ipynb --output <folder>
"""
import argparse
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKIP = {0, 35, 36, 37, 38}

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--notebook", type=Path, default=HERE / "Atlas motor correct 1.0.ipynb")
parser.add_argument("--output", type=Path, default=HERE / "output", help="default Atlas/propulsion/output/")
parser.add_argument("--cd", type=Path,
                    default=HERE.parent / "simulation_inputs/aerodynamic_data/rocket_body/v1.4/CD_Mach_Test_Atlas_v_1.2_SDRAD_cd_mach.csv",
                    help="CD-Mach file for the RocketPy flight of the notebook (default: Atlas v1.4)")
args = parser.parse_args()

# Paths are resolved before moving into the output folder, where the notebook writes its files
notebook, output, cd_file = args.notebook.resolve(), args.output.resolve(), args.cd.resolve()
for path in (notebook, cd_file):
    if not path.is_file():
        parser.error(f"{path}: file not found")
output.mkdir(parents=True, exist_ok=True)
os.chdir(output)

import numpy as np
import plotly.graph_objects as go

counter = {"n": 0}


def save_instead_of_show(fig, *args, **kwargs):
    counter["n"] += 1
    title = (fig.layout.title.text or "figure").replace(" ", "_").replace("/", "_")
    fig.write_html(output / f"{counter['n']:02d}_{title}.html")


go.Figure.show = save_instead_of_show

cells = json.loads(notebook.read_text())["cells"]
namespace = {"__name__": "__main__"}
for i, cell in enumerate(cells):
    if cell["cell_type"] != "code" or i in SKIP:
        continue
    lines = []
    for line in "".join(cell["source"]).splitlines():
        if line.strip().startswith(("from google.colab", "drive.mount", "files.download")):
            continue
        if "/content/drive/" in line and "drag" in line:
            line = line.split("=")[0] + f"= {str(cd_file)!r},"  # repr: Windows backslashes stay valid
        lines.append(line)
    print(f"\n######## cell {i}", flush=True)
    exec(compile("\n".join(lines), f"cell_{i}", "exec"), namespace)

# Thrust curve, which the notebook computes but does not save
n = namespace["index_burnout"]
np.savetxt(output / "thrust_curve.csv", np.column_stack((namespace["time"][:n], namespace["T"][:n])),
           delimiter=",", fmt="%.6g", header="time [s],thrust [N]", comments="")
print(f"\nthrust_curve.csv: {n} points, burn time {namespace['t_burnout']:.3f} s")
print(f"propellant density rho_pr = {namespace['rho_pr']:.2f} kg/m^3")
print(f"Saved in {output}")
