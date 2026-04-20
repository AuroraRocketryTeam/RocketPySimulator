import sys
import pickle
import shutil
import subprocess
import tempfile
from pathlib import Path

import dill


def _worker_main(payload_file):
    """
    Worker entry point.
    This runs in a separate Python process using a non-interactive
    matplotlib backend so that no plot windows are displayed.
    """
    import matplotlib
    matplotlib.use("Agg")

    import matplotlib.pyplot as plt

    payload_file = Path(payload_file)

    with open(payload_file, "rb") as f:
        payload = dill.load(f)

    comparison_object = payload["comparison_object"]
    plots = payload["plots"]
    output_dir = Path(payload["output_dir"])
    formats = payload["formats"]

    # Create output folders
    format_dirs = {}
    for fmt in formats:
        fmt_dir = output_dir / fmt
        fmt_dir.mkdir(parents=True, exist_ok=True)
        format_dirs[fmt] = fmt_dir

    print(f"Saving {len(plots)} comparison plots...")

    for plot_name, plot_kwargs in plots:
        plot_method = getattr(comparison_object, plot_name)

        figures_before = set(plt.get_fignums())

        # Generate plot
        plot_method(**plot_kwargs)

        figures_after = set(plt.get_fignums())
        new_figures = sorted(figures_after - figures_before)

        if not new_figures:
            print(f"  [WARNING] '{plot_name}' did not produce any figure.")
            continue

        fig = plt.figure(new_figures[-1])

        for fmt in formats:
            output_path = format_dirs[fmt] / f"{plot_name}.{fmt}"

            if fmt == "pickle":
                with open(output_path, "wb") as f:
                    pickle.dump(fig, f)
            else:
                fig.savefig(output_path)

        plt.close(fig)
        print(f"  [OK] {plot_name}")

    plt.close("all")
    print("All comparison plots saved successfully.")


def save_compare_plots(comparison_object, plots, output_dir, formats=None):
    """
    Cross-platform plot saver for RocketPy CompareFlight plots.

    Parameters
    ----------
    comparison_object
        RocketPy CompareFlight object.
    plots : list[tuple[str, dict]]
        Example:
        [
            ("velocities", {"legend": False}),
            ("accelerations", {"legend": False}),
        ]
    output_dir : str | Path
        Root output folder.
    formats : list[str] | None
        Example: ["svg", "pickle"]
    """
    if formats is None:
        formats = ["svg", "pickle"]

    output_dir = Path(output_dir)

    temp_dir = Path(tempfile.mkdtemp(prefix="compare_plot_saver_"))
    payload_file = temp_dir / "payload.dill"

    payload = {
        "comparison_object": comparison_object,
        "plots": plots,
        "output_dir": str(output_dir),
        "formats": formats,
    }

    try:
        with open(payload_file, "wb") as f:
            dill.dump(payload, f)

        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            str(payload_file),
        ]

        result = subprocess.run(command, check=False)

        if result.returncode != 0:
            raise RuntimeError(
                f"Child process failed while saving comparison plots "
                f"(exit code: {result.returncode})."
            )

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        _worker_main(sys.argv[2])
    else:
        raise SystemExit("Invalid arguments.")