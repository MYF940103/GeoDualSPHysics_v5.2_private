"""Compare native total and material excess pressure on the released 0-degree surface."""

import argparse
import csv
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np

CASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CASE / "support"))
from postprocess_lian_release import PRE_IDS, RELEASE_IDS, native


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New output directory")
    args = parser.parse_args()
    output = args.output
    if output.exists():
        raise FileExistsError(output)

    preload = CASE / "CaseLianCollapse_psi0_pre_GPU_out/data/Part_1000.bi4"
    saves = sorted((CASE / "CaseLianCollapse_psi0_GPU_out/data").glob("Part_????.bi4"))
    if [p.name for p in saves] != [f"Part_{i:04d}.bi4" for i in range(301)]:
        raise ValueError("Expected the completed 301-frame explicit C08 release")

    rows, selected = [], {}
    for number, path in enumerate([preload, *saves], -1):
        meta, fields = native(path)
        ids = fields["Idp"]
        if not np.array_equal(ids, PRE_IDS if number == -1 else RELEASE_IDS):
            raise ValueError(f"Unexpected native particle IDs in {path}")
        soil = ids >= 2060
        face = np.isin(fields["FSType"][soil], [2, 3])
        p = fields["PorePress"][soil]
        p0 = fields["PorePress0"][soil]
        excess = fields["ExcessPorePress"][soil]
        if not (np.isfinite(p).all() and np.array_equal(p - p0, excess)):
            raise ValueError(f"Invalid pressure fields in {path}")
        zero = p[face] == 0
        ez = excess[face][zero]
        rows.append(dict(
            file=path.relative_to(CASE), native_time_s=meta["TimeStep"],
            since_release_s=(meta["TimeStep"] - meta["GravityPreloadActualTime"] if number >= 0 else ""),
            surface_count=int(face.sum()), zero_count=int(zero.sum()),
            negative_count=int((p[face] < 0).sum()), positive_count=int((p[face] > 0).sum()),
            surface_p_min_kPa=float(p[face].min()) / 1000,
            surface_p_max_kPa=float(p[face].max()) / 1000,
            zero_total_excess_min_kPa=float(ez.min()) / 1000 if ez.size else "",
            zero_total_excess_max_kPa=float(ez.max()) / 1000 if ez.size else "",
        ))
        if number in (30, 120):
            selected[number] = fields["Posd"][soil][:, [0, 2]], face, p / 1000, excess / 1000

    fig, axes = plt.subplots(2, 2, figsize=(11, 5.4), layout="constrained", sharex=True, sharey=True)
    norm = Normalize(-25, 25)
    for i, (number, (xz, face, p, excess)) in enumerate(selected.items()):
        for j, (ax, values) in enumerate(zip(axes[i], (p, excess))):
            ax.scatter(*xz.T, c=values, s=4, cmap="RdBu_r", norm=norm, linewidths=0)
            ax.scatter(*xz[face].T, s=9, edgecolor="#606060", facecolor="none", linewidths=.45,
                       label="Free-surface soil (FSType 2/3)")
            ax.scatter(*xz[face & (p == 0)].T, s=17, edgecolor="#111111", facecolor="none",
                       linewidths=.95, label="Exactly zero total pressure")
            if i == 0:
                ax.set_title(("Total pressure", "Material excess pressure (p − p₀)")[j])
            if j == 0:
                count = rows[number + 1]["zero_count"]
                ax.set_ylabel(f"{number/100:.2f} s after release\nz (m)")
                ax.text(.02, .05, f"Zero total pressure: {count} / {face.sum()} surface particles",
                        transform=ax.transAxes, fontsize=8, bbox=dict(facecolor="white", edgecolor="none", alpha=.90))
            if i == 1:
                ax.set_xlabel("x (m)")
            ax.set_aspect("equal")
    axes[0, 0].set_xlim(-.06, 5.25)
    axes[0, 0].set_ylim(-.07, 2.10)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=2, frameon=False)
    fig.colorbar(plt.cm.ScalarMappable(cmap="RdBu_r", norm=norm), ax=axes,
                 extend="both", label="Pressure (kPa)")
    fig.suptitle("C08 column collapse · 0° dilatancy")
    output.mkdir()
    fig.savefig(output / "surface_pressure.png", dpi=180)
    plt.close(fig)
    with (output / "surface_pressure.csv").open("x", encoding="utf8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
