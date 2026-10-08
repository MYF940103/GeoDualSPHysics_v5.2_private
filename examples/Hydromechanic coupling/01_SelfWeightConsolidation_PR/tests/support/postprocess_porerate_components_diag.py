from pathlib import Path
import argparse
import csv
import math
import sys

import matplotlib.pyplot as plt


CASE_ROOT = Path(__file__).resolve().parents[2]
ROOT_SUPPORT = CASE_ROOT / "support"
if str(ROOT_SUPPORT) not in sys.path:
    sys.path.insert(0, str(ROOT_SUPPORT))

import postprocess_self_weight_consolidation as pp


def read_arrays(path):
    data = path.read_bytes()
    offset = 0

    for _ in range(4):
        _, offset = pp.read_line(data, offset)

    line, offset = pp.read_line(data, offset)
    parts = line.split()
    if len(parts) != 3 or parts[0] != "POINTS":
        raise RuntimeError(f"Unexpected VTK POINTS line in {path}: {line}")
    npoints = int(parts[1])
    values, offset = pp.read_values(data, offset, parts[2], npoints * 3)
    points = pp.reshape(values, 3)
    offset = pp.skip_line_end(data, offset)

    line, offset = pp.read_line(data, offset)
    parts = line.split()
    if len(parts) >= 3 and parts[0] == "VERTICES":
        _, offset = pp.read_values(data, offset, "int", int(parts[2]))
        offset = pp.skip_line_end(data, offset)
        line, offset = pp.read_line(data, offset)

    parts = line.split()
    if len(parts) != 2 or parts[0] != "POINT_DATA":
        raise RuntimeError(f"Unexpected VTK POINT_DATA line in {path}: {line}")
    ndata = int(parts[1])

    arrays = {}
    while offset < len(data):
        line, offset = pp.read_line(data, offset)
        if not line:
            continue
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "FIELD":
            continue
        if parts[0] == "SCALARS":
            name = parts[1]
            type_name = parts[2]
            components = int(parts[3]) if len(parts) > 3 else 1
            _, offset = pp.read_line(data, offset)
            values, offset = pp.read_values(data, offset, type_name, ndata * components)
            arrays[name] = pp.reshape(values, components)
            offset = pp.skip_line_end(data, offset)
            continue
        if parts[0] == "VECTORS":
            name = parts[1]
            type_name = parts[2]
            values, offset = pp.read_values(data, offset, type_name, ndata * 3)
            arrays[name] = pp.reshape(values, 3)
            offset = pp.skip_line_end(data, offset)
            continue
        if len(parts) >= 4 and parts[1].isdigit() and parts[2].isdigit():
            name = parts[0]
            components = int(parts[1])
            tuples = int(parts[2])
            type_name = parts[3]
            values, offset = pp.read_values(data, offset, type_name, tuples * components)
            arrays[name] = pp.reshape(values, components)
            offset = pp.skip_line_end(data, offset)
            continue
        break
    return points, arrays


def rows_from_vtk(path):
    points, arrays = read_arrays(path)
    if "HydroMechLoadAce" not in arrays:
        raise RuntimeError(f"{path} does not contain HydroMechLoadAce")
    rows = []
    for pos, vec in zip(points, arrays["HydroMechLoadAce"]):
        comp, seep, head = vec
        rows.append({
            "x": float(pos[0]),
            "z": float(pos[2]),
            "rate_comp_pa_s": float(comp),
            "rate_seep_pa_s": float(seep),
            "rate_head_pa_s": float(head),
            "rate_total_pa_s": float(comp) + float(seep) + float(head),
        })
    return rows


def layer_average(rows, key):
    bins = {}
    for row in rows:
        iz = int(math.floor(row["z"] / pp.DP + 0.5 + 1e-6))
        bins.setdefault(iz, []).append(row)
    prof = []
    for _, items in sorted(bins.items()):
        z = sum(r["z"] for r in items) / len(items)
        value = sum(r[key] for r in items) / len(items)
        prof.append((z, value))
    return prof


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--particles", required=True, type=Path)
    parser.add_argument("--figdir", required=True, type=Path)
    parser.add_argument("--case", required=True)
    args = parser.parse_args()

    args.figdir.mkdir(parents=True, exist_ok=True)
    files = sorted(args.particles.glob("PartFluid_*.vtk"))
    if not files:
        raise RuntimeError(f"No PartFluid VTK files found in {args.particles}")
    path = files[-1]
    rows = rows_from_vtk(path)

    csv_path = args.figdir / "pore_rate_components_by_layer.csv"
    keys = ["rate_comp_pa_s", "rate_seep_pa_s", "rate_head_pa_s", "rate_total_pa_s"]
    profiles = {key: dict(layer_average(rows, key)) for key in keys}
    z_values = sorted(profiles["rate_total_pa_s"])
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "part",
            "z_m",
            "z_over_H",
            "compression_kpa_s",
            "darcy_lapw_kpa_s",
            "gravity_head_kpa_s",
            "total_kpa_s",
        ])
        for z in z_values:
            writer.writerow([
                path.name,
                z,
                z / pp.H,
                profiles["rate_comp_pa_s"][z] / 1000.0,
                profiles["rate_seep_pa_s"][z] / 1000.0,
                profiles["rate_head_pa_s"][z] / 1000.0,
                profiles["rate_total_pa_s"][z] / 1000.0,
            ])

    bottom_z = z_values[0]
    summary_path = args.figdir / "pore_rate_components_summary.csv"
    with summary_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["part", "sample", "compression_kpa_s", "darcy_lapw_kpa_s", "gravity_head_kpa_s", "total_kpa_s"])
        writer.writerow([
            path.name,
            f"bottom_z={bottom_z:.8g}",
            profiles["rate_comp_pa_s"][bottom_z] / 1000.0,
            profiles["rate_seep_pa_s"][bottom_z] / 1000.0,
            profiles["rate_head_pa_s"][bottom_z] / 1000.0,
            profiles["rate_total_pa_s"][bottom_z] / 1000.0,
        ])
        writer.writerow([
            path.name,
            "column_mean",
            sum(r["rate_comp_pa_s"] for r in rows) / len(rows) / 1000.0,
            sum(r["rate_seep_pa_s"] for r in rows) / len(rows) / 1000.0,
            sum(r["rate_head_pa_s"] for r in rows) / len(rows) / 1000.0,
            sum(r["rate_total_pa_s"] for r in rows) / len(rows) / 1000.0,
        ])

    fig, ax = plt.subplots(figsize=(6.8, 5.2), constrained_layout=True)
    ax.plot([profiles["rate_comp_pa_s"][z] / 1000.0 for z in z_values], [z / pp.H for z in z_values], label="compression")
    ax.plot([profiles["rate_seep_pa_s"][z] / 1000.0 for z in z_values], [z / pp.H for z in z_values], label="Darcy lapw")
    ax.plot([profiles["rate_head_pa_s"][z] / 1000.0 for z in z_values], [z / pp.H for z in z_values], label="gravity head")
    ax.plot([profiles["rate_total_pa_s"][z] / 1000.0 for z in z_values], [z / pp.H for z in z_values], "k--", linewidth=1.4, label="total")
    ax.axvline(0, color="0.4", linewidth=0.8)
    ax.set_xlabel("Pore pressure rate [kPa/s]")
    ax.set_ylabel("z/H")
    ax.set_title(f"{args.case}: temporary pore-rate decomposition ({path.name})")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig_path = args.figdir / "pore_rate_components_profile.png"
    fig.savefig(fig_path, dpi=220)

    print(f"Saved layer CSV: {csv_path}")
    print(f"Saved summary CSV: {summary_path}")
    print(f"Saved figure: {fig_path}")
    print(f"Bottom total rate: {profiles['rate_total_pa_s'][bottom_z] / 1000.0:.6g} kPa/s")


if __name__ == "__main__":
    main()
