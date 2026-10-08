"""Plot reviewed Stage 1 regression histories; does not run or modify solver cases."""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CASE = Path(__file__).resolve().parents[3]
LOG = CASE / "tests/logs/pore_double_stage1"
FIG = CASE / "figures"
BLUE, ORANGE = "#3274A1", "#E1812C"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="Replace only these two generated stage1 figures.")
    args = parser.parse_args()
    with (LOG / "regression_history.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.labelcolor": "#262626", "text.color": "#262626",
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "#E4E4E4", "grid.linewidth": 0.6})
    for suite, dt, title, scope, factor, xlabel in (
        ("q0", 1e-5, "External-load 1D consolidation: pressure-state migration",
         "k = 1e-4 m/s | dt = 10 us | 1,000 soil particles | 0-0.2 s short regression", 1., "Time (s)"),
        ("selfweight", 6.25e-8, "Self-weight restart: pressure-state migration",
         "k = 1e-3 m/s | dt = 62.5 ns | 1,000 soil particles | 0-500 us short regression", 1e6, "Time since restart (us)")
    ):
        destinations = [FIG / f"pore_double_stage1_{suite}_history.{ext}" for ext in ("png", "pdf")]
        if not args.replace and any(p.exists() for p in destinations):
            raise RuntimeError(f"Refusing to replace existing stage1 figures: {destinations}")
        fig, axes = plt.subplots(2, 2, figsize=(12.6, 7.8), sharex="col", sharey="row")
        fig.subplots_adjust(left=.085, right=.975, top=.84, bottom=.22, hspace=.26, wspace=.29)
        fig.suptitle(title, fontsize=16, x=.085, y=.97, ha="left")
        fig.text(.085, .917, scope, fontsize=11)
        for col, backend in enumerate(("cpu", "gpu")):
            selected = [r for r in rows if r["suite"] == suite and r["backend"] == backend
                        and abs(float(r["dt"]) - dt) < dt * 1e-10 and int(r["shepard"]) == 0]
            selected.sort(key=lambda r: float(r["time_s"]))
            if len(selected) < 8:
                raise RuntimeError(f"Insufficient actual history for {suite}/{backend}: {len(selected)}")
            def series(key):
                value = np.asarray([float(r[key]) for r in selected])
                assert np.isfinite(value).all()
                return value
            t = series("time_s") * factor
            assert np.all(np.diff(t) > 0), f"Non-increasing time: {suite}/{backend}"
            ax, delta = axes[:, col]
            ax.set_title(backend.upper(), loc="left", fontweight="bold", fontsize=12)
            ax.plot(t, series("baseline_mean_pressure_pa") / 1000, color=BLUE, lw=1.7,
                    label="Retained high/low patch")
            ax.plot(t, series("double_mean_pressure_pa") / 1000, color=ORANGE, lw=1.4, ls="--",
                    marker="o", markersize=3, markerfacecolor="none", label="Double pressure state")
            ax.set_ylabel("Mean soil pressure (kPa)")
            ax.legend(fontsize=9, frameon=False, loc="best")
            delta.plot(t, series("rms_difference_pa"), color=BLUE, lw=1.7, label="Particle RMS difference")
            delta.plot(t, series("max_abs_difference_pa"), color=ORANGE, lw=1.4, ls="--",
                       label="Max. absolute difference")
            delta.set_xlabel(xlabel)
            delta.set_ylabel("Double - baseline: magnitude (Pa)")
            delta.set_ylim(bottom=0)
            delta.set_xlim(left=0, right=t[-1])
            delta.legend(fontsize=9, frameon=False, loc="best")
            if suite == "q0":
                for threshold, label in ((.1, "Max gate: 0.10 Pa"), (.01, "Pooled RMS gate: 0.01 Pa")):
                    delta.axhline(threshold, color="#737373", lw=.8, ls=":")
                    delta.text(.004, threshold, label, color="#525252", fontsize=8,
                               va="bottom", bbox={"facecolor": "white", "edgecolor": "none", "pad": .3})
            delta.ticklabel_format(axis="y", style="sci", scilimits=(-2, 3), useMathText=True)
            ax.ticklabel_format(axis="y", style="plain", useOffset=False)
        if suite == "q0":
            fig.text(.085, .119, "q0 exceeds the predefined pressure screening gates; overall Stage 1 acceptance is still open.",
                     fontsize=10, fontweight="bold")
        fig.text(.085, .089,
                 "Baseline state = float high + float residual, reconstructed in double; aligned by particle ID and actual output time.",
                 fontsize=9)
        fig.text(.085, .056,
                 "Source: tests/logs/pore_double_stage1/regression_history.csv. Short migration check, not full 2Tv accuracy or performance.",
                 fontsize=9)
        FIG.mkdir(exist_ok=True)
        for destination in destinations:
            fig.savefig(destination, dpi=180, facecolor="white")
            print(destination)
        plt.close(fig)

if __name__ == "__main__":
    main()
