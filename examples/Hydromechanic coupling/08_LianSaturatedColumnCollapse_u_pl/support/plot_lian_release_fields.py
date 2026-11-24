"""Plot C08 material particles and digitized Lian et al. (2023) pressure/geometry panels."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import colors
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import numpy as np


CASE = Path(__file__).resolve().parents[1]
REFERENCE = CASE / "figures/validation_explicit/reference"
PANELS = {"psi0": (14, "0°", (.3, .6, 1.2)),
          "psi2p5": (15, "+2.5°", (.3, .6, 1.2)),
          "psim5": (17, "−5°", (.2, .5, 1.6, 3.0))}


def plot_group(group, figdir):
    """Write a group's shape/pressure comparison to the directory containing its fields.csv."""
    figdir = Path(figdir)
    figure, angle, times = PANELS[group]
    columns = ("part", "time_s", "tau_s", "id", "x_m", "z_m", "p_kPa", "excess_kPa")
    data = np.genfromtxt(figdir / "fields.csv", delimiter=",", names=True, usecols=columns,
                         encoding="utf-8-sig")
    outline = np.genfromtxt(CASE / "support/lian_collapse_outline.csv", delimiter=",",
                            names=True, dtype=None, encoding="utf-8-sig")
    group_points = outline[(outline["group"] == group) & (outline["edge_kind"] == "visible")]
    unique_tau = np.unique(data["tau_s"])
    lo, hi = -10., (20. if figure == 17 else 10.)
    histories = []
    frames = []
    for nominal in times:
        tau = unique_tau[np.argmin(np.abs(unique_tau - nominal))]
        frame = data[data["tau_s"] == tau]
        if (abs(tau - nominal) > 5.01e-6 or frame.size != 5000 or
            not np.array_equal(np.sort(frame["id"]), np.arange(2060, 7060)) or
            not all(np.isfinite(frame[key]).all() for key in columns) or
            np.unique(frame["time_s"]).size != 1 or np.unique(frame["part"]).size != 1):
            raise ValueError(f"Missing or inconsistent native particle frame in {group} at {nominal} s")
        last_pwp = figure == 17 and nominal == 3
        field = "p_kPa" if last_pwp else "excess_kPa"
        values = frame[field]
        below, above = int((values < lo).sum()), int((values > hi).sum())
        points = group_points[group_points["tau_s"] == nominal]
        if not len(points):
            raise ValueError(f"Missing published outline in Fig. {figure} at {nominal} s")
        clipped = bool(points["right_frame_clipped"].any())
        histories.append(dict(group=group, figure=figure, paper_tau_s=nominal,
            native_part=int(frame["part"][0]), native_time_s=frame["time_s"][0], native_tau_s=tau,
            native_tau_minus_paper_s=tau - nominal, paper_right_frame_clipped=clipped,
            printed_pressure_label="PWP" if last_pwp else "Excess pl", native_field=field,
            color_min_kPa=lo, color_max_kPa=hi, native_min_kPa=values.min(),
            native_max_kPa=values.max(), soil_count=len(frame), below_count=below, above_count=above,
            below_fraction=below / len(frame), above_fraction=above / len(frame),
            outside_fraction=(below + above) / len(frame)))
        frames.append((nominal, frame, points, clipped, field))
    xmax = max(8.1, max(frame["x_m"].max() for _, frame, *_ in frames) + .12)
    zmax = max(2.12, max(frame["z_m"].max() for _, frame, *_ in frames) + .10)
    with np.load(REFERENCE / "paper_pressure_samples.npz", allow_pickle=False) as samples:
        cmap = colors.ListedColormap(samples[f"f{figure}_palette"] / 255.)
        norm = colors.Normalize(lo, hi, clip=True)
        fig, axes = plt.subplots(len(times), 3, figsize=(14, 1.75 * len(times) + 1.5),
                                 layout="constrained", sharex=True, sharey=True, squeeze=False)
        for index, ((nominal, frame, points, clipped, field), (shape, paper, native)) in enumerate(zip(frames, axes)):
            shape.scatter(frame["x_m"], frame["z_m"], s=1.0, color="#5784a8", linewidths=0)
            shape.scatter(points["x_m"], points["z_m"], s=2.2, color="#8a3215", linewidths=0)
            key = f"f{figure}_t{int(round(10*nominal))}"
            paper.imshow(samples[key], extent=samples[key + "_extent"], origin="upper", interpolation="nearest")
            native.scatter(frame["x_m"], frame["z_m"], c=frame[field], cmap=cmap, norm=norm,
                           s=1.45, linewidths=0)
            if clipped:
                for ax in (shape, paper):
                    ax.axvline(8, color=".35", ls=":", lw=.85)
                paper.text(7.95, zmax - .03, "frame ends at 8 m", ha="right", va="top",
                           fontsize=7, color=".28")
            paper_label = "PWP" if field == "p_kPa" else r"Excess $p^l$"
            native_label = "Total p" if field == "p_kPa" else r"Material $p-p_0$"
            if index == 0:
                shape.set_title("Native geometry and published outline", fontsize=10, weight="bold")
            for ax, label, heading in ((paper, paper_label, "Published pressure colors"),
                                       (native, native_label, "Native particle pressure")):
                ax.set_title(f"{heading} ({label})" if index == 0 else label, fontsize=10 if index == 0 else 9,
                             weight="bold" if index == 0 else "normal")
            shape.set_ylabel(f"{nominal:g} s\nz (m)")
            for ax in (shape, paper, native):
                ax.set(xlim=(-.08, xmax), ylim=(-.055, zmax), aspect="equal", facecolor="white")
                ax.tick_params(labelsize=8)
                if index == len(frames) - 1:
                    ax.set_xlabel("x (m)")
        shape_handles = [Line2D([], [], marker="o", ls="none", ms=4, color=c, label=label)
                         for c, label in (("#5784a8", "Native soil centers"), ("#8a3215", "Published edge pixels"))]
        axes[0, 0].legend(handles=shape_handles, loc="upper right", fontsize=6.8, frameon=False)
        cb = fig.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), ax=list(axes.flat),
                          orientation="horizontal", shrink=.50, pad=.03, aspect=34)
        cb.set_ticks(np.arange(lo, hi + 1, 10))
        cb.set_label("Published pressure color scale (kPa)")
        fig.suptitle(f"Saturated column     ψ = {angle}     |     Lian et al. (2023), Fig. {figure}")
        png = figdir / "lian_shape_pressure.png"
        try:
            fig.savefig(png.with_suffix(".tmp"), format="png", dpi=165)
            png.with_suffix(".tmp").replace(png)
        finally:
            plt.close(fig)
    result = figdir / "lian_pressure_ranges.csv"
    with result.with_suffix(".tmp").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=tuple(histories[0]))
        writer.writeheader()
        writer.writerows(histories)
    result.with_suffix(".tmp").replace(result)


if __name__ == "__main__":
    cmd = argparse.ArgumentParser(description=__doc__)
    cmd.add_argument("group", choices=PANELS)
    cmd.add_argument("--figdir", type=Path)
    args = cmd.parse_args()
    plot_group(args.group, args.figdir or CASE / "figures/validation_explicit" / args.group)
