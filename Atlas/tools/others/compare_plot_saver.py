import pickle
from contextlib import contextmanager
from pathlib import Path

import matplotlib.pyplot as plt

try:
    import dill
except ImportError:
    dill = None


@contextmanager
def _suppress_show():
    """Disattiva temporaneamente plt.show() (RocketPy lo chiama a fine plot)."""
    original_show = plt.show
    plt.show = lambda *args, **kwargs: None
    try:
        yield
    finally:
        plt.show = original_show


def _dump_figure(fig, path):
    try:
        with open(path, "wb") as f:
            pickle.dump(fig, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        if dill is None:
            raise
        with open(path, "wb") as f:
            dill.dump(fig, f)


def make_compare_plots(comparison, plots, output_dir=None, formats=("svg", "pickle"), show=False):
    """
    Genera i grafici di CompareFlights una sola volta, li salva (opzionale)
    e li mostra (opzionale).

    Parameters
    ----------
    comparison : CompareFlights
    plots : list[tuple[str, dict]]
        Es: [("velocities", {"legend": False}), ("trajectories_3d", {})]
    output_dir : str | Path | None
        Se None, non salva nulla.
    formats : iterable[str]
        Es: ("svg", "pickle", "png")
    show : bool
        Se True, mostra tutte le figure alla fine.
    """
    save = output_dir is not None and len(formats) > 0

    format_dirs = {}
    if save:
        output_dir = Path(output_dir)
        for fmt in formats:
            fmt_dir = output_dir / fmt
            fmt_dir.mkdir(parents=True, exist_ok=True)
            format_dirs[fmt] = fmt_dir

    for plot_name, plot_kwargs in plots:
        plot_method = getattr(comparison, plot_name, None)
        if not callable(plot_method):
            print(f"  [WARNING] '{plot_name}' non è un grafico valido di comparison")
            continue

        figures_before = set(plt.get_fignums())

        with _suppress_show():
            plot_method(**plot_kwargs)

        new_figures = sorted(set(plt.get_fignums()) - figures_before)
        if not new_figures:
            print(f"  [WARNING] '{plot_name}' non ha prodotto nessuna figura.")
            continue

        for i, num in enumerate(new_figures):
            fig = plt.figure(num)
            suffix = "" if len(new_figures) == 1 else f"_{i + 1}"

            if save:
                for fmt in formats:
                    path = format_dirs[fmt] / f"{plot_name}{suffix}.{fmt}"
                    if fmt == "pickle":
                        _dump_figure(fig, path)
                    else:
                        fig.savefig(path)

            if not show:
                plt.close(fig)

        print(f"  [OK] {plot_name}")

    if show:
        plt.show()


'''import sys
import pickle
import shutil
import subprocess
import tempfile
from pathlib import Path

import dill

import os


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
                    dill.dump(fig, f)                         #pickle before
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

        ###
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(p for p in sys.path if p)

        result = subprocess.run(command, check=False, env=env)
        #result = subprocess.run(command, check=False)

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
'''