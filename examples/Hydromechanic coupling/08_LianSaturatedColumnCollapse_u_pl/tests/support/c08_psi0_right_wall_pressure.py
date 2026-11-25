"""Plot the same rightmost soil column before and after the C08 wall release."""
import argparse
import csv
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CASE / "support"))
from postprocess_lian_release import PRE_IDS, RELEASE_IDS, SOIL_IDS, native


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New directory for the CSV and figure")
    output = parser.parse_args().output
    preload = CASE / "CaseLianCollapse_psi0_pre_GPU_out/data"
    release = CASE / "CaseLianCollapse_psi0_GPU_out/data"
    _, initial = native(preload / "Part_0000.bi4")
    if not np.array_equal(initial["Idp"], PRE_IDS):
        raise ValueError("Unexpected initial material IDs")
    soil_x = initial["Posd"][SOIL_IDS, 0]
    column = SOIL_IDS[np.isclose(soil_x, soil_x.max(), rtol=0, atol=1e-8)]
    if len(column) != 50:
        raise ValueError("Expected 50 materials in the original rightmost column")
    z0 = initial["Posd"][column, 2]
    frames = [(preload, 1000, "Wall present", "#24749a", "o"),
              (release, 0, "First released step", "#c3661c", "s"),
              (release, 1, "After 0.010005 s", "#79599b", "^")]

    rows = []
    fig, ax = plt.subplots(figsize=(7.8, 4.4), layout="constrained")
    for folder, part, label, color, marker in frames:
        path = folder / f"Part_{part:04d}.bi4"
        meta, fields = native(path)
        ids = fields["Idp"]
        if not np.array_equal(ids, PRE_IDS if folder == preload else RELEASE_IDS):
            raise ValueError(f"Unexpected native IDs in {path}")
        idx = np.searchsorted(ids, column)
        if not np.array_equal(ids[idx], column):
            raise ValueError(f"Missing tracked particles in {path}")
        time_s = meta["TimeStep"]
        pressure = fields["PorePress"][idx].astype("f8") / 1000
        fs = fields["FSType"][idx]
        if folder == preload:
            wall_time_s = time_s
        elif meta["GravityPreloadActualTime"] != wall_time_s:
            raise ValueError("Receiver wall event differs from the last preload clock")
        for j, i in enumerate(idx):
            rows.append((path.relative_to(CASE).as_posix(), time_s, time_s - wall_time_s,
                         int(ids[i]), z0[j], *fields["Posd"][i, [0, 2]], int(fs[j]), pressure[j],
                         float(fields["PorePress0"][i]) / 1000, float(fields["ExcessPorePress"][i]) / 1000))
        ax.plot(pressure, z0, color=color, lw=1.4, marker=marker, markersize=3,
                markevery=3, label=f"{label}  ({np.count_nonzero(pressure == 0)}/50 at zero)")
    ax.set(xlabel="Gauge pore pressure (kPa)", ylabel="Initial material elevation (m)",
           title="C08 · 0° dilatancy · rightmost soil column", ylim=(-.04, 2.06))
    ax.axvline(0, color="0.35", lw=.75, ls=":", zorder=0)
    ax.grid(alpha=.18)
    ax.legend(loc="upper right", fontsize=9)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "pressure.csv").open("x", newline="", encoding="utf8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("source", "native_time_s", "since_release_s", "material_id", "initial_z_m",
                         "x_m", "z_m", "fs_type", "p_kPa", "p0_kPa", "excess_kPa"))
        writer.writerows(rows)
    fig.savefig(output / "pressure.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
