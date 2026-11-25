"""Compare the two actual 10-second preload profiles before the +2.5 degree release."""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CASE / "support"))
from postprocess_lian_release import PRE_IDS, SOIL_IDS, native

OUT = CASE / "figures/validation_explicit/psi2p5_ddt3_comparison"
SOURCES = {0: CASE / "CaseLianCollapse_psi2p5_pre_GPU_out/data",
           3: CASE / "tests/outputs/c08_ddt3_psi2p5_pre_r1/data"}


def save_table(name, rows):
    with (OUT / name).open("w", encoding="utf8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    profiles, stats = [], []
    initial = None
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 4.4), sharey=True, layout="constrained")
    for setting, source in SOURCES.items():
        meta0, first = native(source / "Part_0000.bi4")
        meta, last = native(source / "Part_1000.bi4")
        if (int(meta["Step"]) + 1 != 2_000_000 or meta0["TimeStep"] != 0
                or not all(np.array_equal(a["Idp"], PRE_IDS) for a in (first, last))):
            raise ValueError("Unexpected preload steps or particle identity")
        xz0 = first["Posd"][SOIL_IDS][:, [0, 2]]
        native_p0 = last["PorePress0"][SOIL_IDS]
        if not np.array_equal(first["PorePress0"][SOIL_IDS], native_p0):
            raise ValueError("Material reference pressure changed")
        if initial is None:
            initial = (xz0, native_p0, meta["TimeStep"])
        elif not (np.array_equal(initial[0], xz0) and np.array_equal(initial[1], native_p0)
                  and initial[2] == meta["TimeStep"]):
            raise ValueError("Initial material columns or actual final times differ")
        layer_z, layer, counts = np.unique(xz0[:, 1], return_inverse=True, return_counts=True)
        if len(counts) != 50 or any(counts != 100):
            raise ValueError("Unexpected initial layer geometry")
        z = last["Posd"][SOIL_IDS, 2]
        pressure = last["PorePress"][SOIL_IDS].astype(float) / 1000
        effective = last["SigmaState_kk"][SOIL_IDS, 2] / 1000
        quantities = {"p": pressure, "effective_zz": effective, "total_zz": effective - pressure}
        interior = ((xz0[:, 0] > .5) & (xz0[:, 0] < 3.5) &
                    (xz0[:, 1] > .3) & (xz0[:, 1] < 1.7))
        for region, mask in (("all soil", np.ones(len(z), dtype=bool)), ("fixed initial interior", interior)):
            row = dict(DensityDT=setting, region=region, count=int(sum(mask)), time_s=meta["TimeStep"])
            for key, values in quantities.items():
                slope, intercept = np.polyfit(z[mask], values[mask], 1)
                row[key+"_slope_kPa_per_m"] = slope
                row[key+"_fit_residual_rms_kPa"] = np.sqrt(np.mean((values[mask]-slope*z[mask]-intercept)**2))
            stats.append(row)
        level_rows = [dict(DensityDT=setting, time_s=meta["TimeStep"], initial_z_m=zz, count=100)
                      for zz in layer_z]
        for ax, (key, values) in zip(axes, quantities.items()):
            means = np.bincount(layer, weights=values) / counts
            ax.plot(means, layer_z, "--" if setting == 0 else "-", label=f"DDT{setting}")
            for row, value in zip(level_rows, means):
                row[key+"_mean_kPa"] = value
        profiles.extend(level_rows)
    background = initial[1].astype(float) / 1000
    axes[0].plot(np.bincount(layer, weights=background)/counts, layer_z,
                 ":", color="black", label="Initial hydrostatic")
    for ax, label in zip(axes, ("Pore pressure (kPa)", "Effective vertical stress (kPa)",
                                "Total vertical stress (kPa)")):
        ax.set_xlabel(label)
        ax.grid(alpha=.22)
    axes[0].legend(fontsize=8)
    axes[0].set_ylabel("Initial material layer elevation (m)")
    fig.suptitle("Before wall release at 10 s   |   +2.5°   |   100 particles per layer")
    save_table("preload_layers.csv", profiles)
    save_table("preload_gradients.csv", stats)
    fig.savefig(OUT / "preload_profiles.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
