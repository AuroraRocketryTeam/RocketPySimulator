"""
CD-Mach curve for RocketPy from a RASAero export ("Export to CSV" of the aerodynamic data).

The export holds one block of rows for each angle of attack (0, 2, 4 deg): only one block is kept
(default 0 deg), otherwise RocketPy sorts the rows by Mach and mixes the CD of different angles.
Works both with the decimal point and with the decimal comma of an Italian Windows (where every
decimal number is split in two fields by the comma).

Writes "mach,cd" rows without header, as the files in simulation_inputs/aerodynamic_data/rocket_body/.
The RASAero exports are kept next to this script, one folder per geometry version (v1.4/...): write the
CD-Mach file straight into simulation_inputs with -o.

Usage (one or more files):
    python Atlas/tools/aerodynamic/cd_mach_rasaero_convert/rasaero_cdmach_generator.py <RASAero export>.CSV
    python Atlas/tools/aerodynamic/cd_mach_rasaero_convert/rasaero_cdmach_generator.py <folder>/*.CSV --column on --max-mach 3
    python Atlas/tools/aerodynamic/cd_mach_rasaero_convert/rasaero_cdmach_generator.py <export>.CSV -o <folder>/<name>.csv
    python Atlas/tools/aerodynamic/cd_mach_rasaero_convert/rasaero_cdmach_generator.py Atlas/tools/aerodynamic/cd_mach_rasaero_convert/v1.4/<export>.CSV \
        -o Atlas/simulation_inputs/aerodynamic_data/rocket_body/v1.4/<export>_cd_mach.csv
Paths start from the folder where the command is launched; quote them if they contain spaces.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

COLUMNS = {"cd": "CD", "off": "CD Power-Off", "on": "CD Power-On"}


def parse_row(line, n_columns):
    """First five values of a row (Mach, Alpha, CD, CD Power-Off, CD Power-On)."""
    fields = line.strip().split(",")
    if len(fields) == n_columns:
        # Decimal point: one field per value
        return [float(value) for value in fields[:5]]
    # Decimal comma: Mach is always written with two decimals ("0,01"), Alpha as an integer ("0"),
    # the CDs with their decimals ("0,4806..."), so the first five values take 2+1+2+2+2 fields
    mach = float(f"{fields[0]}.{fields[1]}")
    alpha = float(fields[2])
    cds = [float(f"{fields[i]}.{fields[i + 1]}") for i in (3, 5, 7)]
    return [mach, alpha, *cds]


def read_export(path):
    lines = Path(path).read_text(encoding="utf-8-sig", errors="replace").splitlines()
    header = [name.strip() for name in lines[0].split(",")]
    if header[:5] != ["Mach", "Alpha", "CD", "CD Power-Off", "CD Power-On"]:
        raise ValueError(f"{path}: not a RASAero aerodynamic export (header {header[:5]})")
    data = np.array([parse_row(line, len(header)) for line in lines[1:] if line.strip()])
    # Sanity checks of the decimal-comma parsing
    if np.any(data[:, 2:] <= 0) or np.any(data[:, 2:] > 10):
        raise ValueError(f"{path}: CD values out of range, the file was not read correctly")
    return data


def convert(path, output, column, alpha, max_mach):
    if not path.is_file():
        raise ValueError(f"{path}: file not found (paths start from the current folder {Path.cwd()})")
    if not output.parent.is_dir():
        raise ValueError(f"{output.parent}: output folder not found (paths start from the current folder {Path.cwd()})")
    data = read_export(path)
    alphas = np.unique(data[:, 1])
    if alpha not in alphas:
        raise ValueError(f"{path}: no rows at alpha = {alpha:g} deg (available: {', '.join(f'{a:g}' for a in alphas)})")
    rows = data[(data[:, 1] == alpha) & (data[:, 0] <= max_mach)]
    if np.any(np.diff(rows[:, 0]) <= 0):
        raise ValueError(f"{path}: Mach not increasing at alpha = {alpha:g} deg")

    index = 2 + list(COLUMNS).index(column)
    np.savetxt(output, rows[:, [0, index]], delimiter=",", fmt=["%.2f", "%.15g"])

    same = np.allclose(rows[:, 3], rows[:, 4])
    print(f"{Path(path).name} -> {output}")
    print(f"  {COLUMNS[column]} at alpha {alpha:g} deg, {len(rows)} rows, Mach {rows[0, 0]:g}-{rows[-1, 0]:g}"
          f" (alpha in the export: {', '.join(f'{a:g}' for a in alphas)})")
    if not same:
        print("  <!> CD Power-On and Power-Off differ: export the other one with --column and use both files")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", type=Path, help="RASAero CSV exports")
    parser.add_argument("-o", "--output", type=Path,
                        help="output file (only with one input); default <input name>_cd_mach.csv next to the input")
    parser.add_argument("--column", choices=COLUMNS, default="off",
                        help="off = CD Power-Off (default), on = CD Power-On, cd = CD")
    parser.add_argument("--alpha", type=float, default=0, help="angle of attack in deg (default 0)")
    parser.add_argument("--max-mach", type=float, default=np.inf, help="drop the rows above this Mach")
    args = parser.parse_args()

    if args.output and len(args.files) > 1:
        parser.error("--output works with one input file only")
    errors = 0
    for path in args.files:
        output = args.output or path.with_name(f"{path.stem}_cd_mach.csv")
        try:
            convert(path, output, args.column, args.alpha, args.max_mach)
        except ValueError as error:
            print(f"<!> {error}", file=sys.stderr)
            errors += 1
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
