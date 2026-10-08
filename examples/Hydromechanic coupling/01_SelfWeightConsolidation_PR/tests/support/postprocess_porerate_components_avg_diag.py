from pathlib import Path
import argparse
import csv
import math
import re
import sys

import matplotlib.pyplot as plt


CASE_ROOT = Path(__file__).resolve().parents[2]
ROOT_SUPPORT = CASE_ROOT / "support"
if str(ROOT_SUPPORT) not in sys.path:
    sys.path.insert(0, str(ROOT_SUPPORT))

import postprocess_self_weight_consolidation as pp
from postprocess_porerate_components_diag import read_arrays


PART_RE = re.compile(r"^Part_(\d+)\s+([0-9.Ee+-]+)\s+(\d+)\s+(\d+)\s+")


def part_index(path):
    return int(path.stem.rsplit("_", 1)[1])


def read_run_steps(run_out):
    steps = {0: 0}
    with run_out.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = PART_RE.match(line.strip())
            if match:
                steps[int(match.group(1))] = int(match.group(3))
    return steps


def rows_from_vtk(path):
    points, arrays = read_arrays(path)
    if "HydroMechLoadAce" not in arrays:
        raise RuntimeError(f"{path} does not contain HydroMechLoadAce")
    if "ExcessPorePress" not in arrays:
        raise RuntimeError(f"{path} does not contain ExcessPorePress")
    rows = []
    for i, (pos, vec, excess) in enumerate(zip(points, arrays["HydroMechLoadAce"], arrays["ExcessPorePress"])):
        excess_value = excess[0] if isinstance(excess, (list, tuple)) else excess
        rows.append({
            "i": i,
            "x": float(pos[0]),
            "z": float(pos[2]),
            "cum_comp_pa_s": float(vec[0]),
            "cum_seep_pa_s": float(vec[1]),
            "cum_head_pa_s": float(vec[2]),
            "excess_pa": float(excess_value),
        })
    return rows


def bottom_indices(rows):
    min_z = min(row["z"] for row in rows)
    return [row["i"] for row in rows if abs(row["z"] - min_z) <= pp.DP * 0.51], min_z


def avg_for_indices(rows, indices, key):
    return sum(rows[i][key] for i in indices) / len(indices)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--particles", required=True, type=Path)
    parser.add_argument("--run-out", required=True, type=Path)
    parser.add_argument("--figdir", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--tout", required=True, type=float)
    parser.add_argument("--tv-offset", type=float, default=0.0)
    args = parser.parse_args()

    args.figdir.mkdir(parents=True, exist_ok=True)
    files = sorted(args.particles.glob("PartFluid_*.vtk"))
    if len(files) < 2:
        raise RuntimeError(f"Need at least two PartFluid VTK files in {args.particles}")

    steps = read_run_steps(args.run_out)
    rows_by_idx = {part_index(path): rows_from_vtk(path) for path in files}
    indices = sorted(rows_by_idx)

    out_rows = []
    for prev_idx, curr_idx in zip(indices[:-1], indices[1:]):
        prev_rows = rows_by_idx[prev_idx]
        curr_rows = rows_by_idx[curr_idx]
        if len(prev_rows) != len(curr_rows):
            raise RuntimeError(f"Particle count changed between PartFluid_{prev_idx:04d} and PartFluid_{curr_idx:04d}")
        bidx, bottom_z = bottom_indices(curr_rows)
        step_delta = steps.get(curr_idx, curr_idx) - steps.get(prev_idx, prev_idx)
        if step_delta <= 0:
            step_delta = round((curr_idx - prev_idx) * args.tout / 1e-6)
        t_start = args.tv_offset + pp.CV_TERZAGHI * (prev_idx * args.tout) / (pp.H * pp.H)
        t_end = args.tv_offset + pp.CV_TERZAGHI * (curr_idx * args.tout) / (pp.H * pp.H)
        comp = avg_for_indices(curr_rows, bidx, "cum_comp_pa_s") - avg_for_indices(prev_rows, bidx, "cum_comp_pa_s")
        seep = avg_for_indices(curr_rows, bidx, "cum_seep_pa_s") - avg_for_indices(prev_rows, bidx, "cum_seep_pa_s")
        head = avg_for_indices(curr_rows, bidx, "cum_head_pa_s") - avg_for_indices(prev_rows, bidx, "cum_head_pa_s")
        p0 = avg_for_indices(prev_rows, bidx, "excess_pa")
        p1 = avg_for_indices(curr_rows, bidx, "excess_pa")
        dt = (curr_idx - prev_idx) * args.tout
        out_rows.append({
            "interval": f"{prev_idx:04d}-{curr_idx:04d}",
            "part_start": f"PartFluid_{prev_idx:04d}.vtk",
            "part_end": f"PartFluid_{curr_idx:04d}.vtk",
            "Tv_start": t_start,
            "Tv_end": t_end,
            "steps": step_delta,
            "bottom_z_m": bottom_z,
            "compression_kpa_s": comp / step_delta / 1000.0,
            "darcy_lapw_kpa_s": seep / step_delta / 1000.0,
            "gravity_head_kpa_s": head / step_delta / 1000.0,
            "total_components_kpa_s": (comp + seep + head) / step_delta / 1000.0,
            "actual_bottom_excess_rate_kpa_s": (p1 - p0) / dt / 1000.0,
            "bottom_excess_start_kpa": p0 / 1000.0,
            "bottom_excess_end_kpa": p1 / 1000.0,
        })

    csv_path = args.figdir / "pore_rate_components_interval_average.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    fig, axes = plt.subplots(2, 1, figsize=(9.2, 7.2), sharex=True, constrained_layout=True)
    ax, ax_net = axes
    tv_mid = [(row["Tv_start"] + row["Tv_end"]) * 0.5 for row in out_rows]
    ax.plot(tv_mid, [row["compression_kpa_s"] for row in out_rows], label="compression")
    ax.plot(tv_mid, [row["darcy_lapw_kpa_s"] for row in out_rows], label="Darcy lapw")
    ax.plot(tv_mid, [row["gravity_head_kpa_s"] for row in out_rows], label="gravity head")
    ax.axhline(0, color="0.4", linewidth=0.8)
    ax.set_ylabel("Bottom pore-pressure rate [kPa/s]")
    ax.set_title(f"{args.case}: interval-averaged bottom pore-rate components")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    ax_net.plot(tv_mid, [row["total_components_kpa_s"] for row in out_rows], "k--", linewidth=1.4, label="component total")
    ax_net.plot(tv_mid, [row["actual_bottom_excess_rate_kpa_s"] for row in out_rows], "o-", markersize=3, label="actual bottom dp/dt")
    ax_net.axhline(0, color="0.4", linewidth=0.8)
    ax_net.set_xlabel("Time factor Tv")
    ax_net.set_ylabel("Net rate [kPa/s]")
    ax_net.grid(True, alpha=0.25)
    ax_net.legend(fontsize=8)
    fig_path = args.figdir / "pore_rate_components_interval_average.png"
    fig.savefig(fig_path, dpi=220)

    print(f"Saved CSV: {csv_path}")
    print(f"Saved figure: {fig_path}")
    print("Last interval:")
    for key, value in out_rows[-1].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
