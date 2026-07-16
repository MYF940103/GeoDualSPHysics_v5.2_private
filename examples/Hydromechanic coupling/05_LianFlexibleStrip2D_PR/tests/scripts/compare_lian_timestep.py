from pathlib import Path
import argparse
import csv
import json
import math
import re

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri


POINTS = ("A", "A_below", "B")


def read_line(buf, idx):
    end = buf.find(b"\n", idx)
    if end < 0:
        raise ValueError("Unexpected end of VTK file.")
    return buf[idx:end].decode("ascii", errors="replace").strip(), end + 1


def skip_ws(buf, idx):
    while idx < len(buf) and buf[idx] in b"\r\n \t":
        idx += 1
    return idx


def dtype_for(vtk_type):
    types = {
        "float": ">f4",
        "double": ">f8",
        "int": ">i4",
        "integer": ">i4",
        "unsigned_int": ">u4",
        "uint": ">u4",
        "short": ">i2",
        "unsigned_short": ">u2",
        "uchar": "u1",
        "unsigned_char": "u1",
    }
    return np.dtype(types[vtk_type.lower()])


def parse_vtk(path):
    buf = path.read_bytes()
    idx = 0
    for _ in range(4):
        _, idx = read_line(buf, idx)
    line, idx = read_line(buf, idx)
    parts = line.split()
    npoints = int(parts[1])
    dtype = dtype_for(parts[2])
    points = np.frombuffer(buf, dtype=dtype, count=npoints * 3, offset=idx).astype(float).reshape(npoints, 3)
    idx += npoints * 3 * dtype.itemsize

    idx = skip_ws(buf, idx)
    line, idx = read_line(buf, idx)
    if not line.startswith("VERTICES"):
        raise ValueError(f"Unexpected VTK record in {path}: {line}")
    total_vertices = int(line.split()[2])
    idx += total_vertices * np.dtype(">i4").itemsize

    idx = skip_ws(buf, idx)
    line, idx = read_line(buf, idx)
    if not line.startswith("POINT_DATA"):
        raise ValueError(f"Unexpected VTK record in {path}: {line}")
    ndata = int(line.split()[1])
    arrays = {}

    while idx < len(buf):
        idx = skip_ws(buf, idx)
        if idx >= len(buf):
            break
        line, idx = read_line(buf, idx)
        if not line:
            continue
        parts = line.split()
        kind = parts[0]
        if kind == "FIELD":
            for _ in range(int(parts[2])):
                idx = skip_ws(buf, idx)
                header, idx = read_line(buf, idx)
                name, comps, tuples, vtk_type = header.split()
                comps, tuples = int(comps), int(tuples)
                dtype = dtype_for(vtk_type)
                data = np.frombuffer(buf, dtype=dtype, count=comps * tuples, offset=idx).astype(float)
                idx += comps * tuples * dtype.itemsize
                data = data.reshape(tuples, comps)
                arrays[name] = data[:, 0] if comps == 1 else data
        elif kind == "SCALARS":
            name, vtk_type = parts[1], parts[2]
            comps = int(parts[3]) if len(parts) > 3 else 1
            _, idx = read_line(buf, idx)
            dtype = dtype_for(vtk_type)
            data = np.frombuffer(buf, dtype=dtype, count=ndata * comps, offset=idx).astype(float)
            idx += ndata * comps * dtype.itemsize
            data = data.reshape(ndata, comps)
            arrays[name] = data[:, 0] if comps == 1 else data
        elif kind == "VECTORS":
            name, vtk_type = parts[1], parts[2]
            dtype = dtype_for(vtk_type)
            arrays[name] = np.frombuffer(buf, dtype=dtype, count=ndata * 3, offset=idx).astype(float).reshape(ndata, 3)
            idx += ndata * 3 * dtype.itemsize
        else:
            raise ValueError(f"Unsupported VTK record in {path}: {line}")
    return points, arrays


def read_times(run_out):
    times = {0: 0.0}
    pattern = re.compile(r"^\s*Part_(\d{4})\s+([0-9.+\-Ee]+)\s+")
    if run_out.exists():
        for line in run_out.read_text(errors="ignore").splitlines():
            match = pattern.search(line)
            if match:
                times[int(match.group(1))] = float(match.group(2))
    return times


def part_index(path):
    match = re.search(r"PartFluid_(\d+)\.vtk$", path.name)
    if not match:
        raise ValueError(f"Cannot parse part index from {path}")
    return int(match.group(1))


def nearest_part(case_dir, target):
    files = sorted((case_dir / "particles").glob("PartFluid_*.vtk"), key=part_index)
    if not files:
        raise SystemExit(f"No PartFluid VTK files in {case_dir / 'particles'}")
    times = read_times(case_dir / "Run.out")
    return min(files, key=lambda path: abs(times.get(part_index(path), part_index(path)) - target)), times


def read_history(case_dir):
    csv_path = case_dir / "figures" / "lian_flexible_strip_ab_epwp.csv"
    if not csv_path.exists():
        raise SystemExit(f"Missing history CSV: {csv_path}")
    rows = []
    with csv_path.open(newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def plot_histories(base_label, base_rows, test_label, test_rows, out_dir):
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), constrained_layout=True)
    for ax, point in zip(axes, ("A", "B")):
        for label, rows, style in ((base_label, base_rows, "-"), (test_label, test_rows, "--")):
            t = np.array([float(r["time_s"]) for r in rows if float(r["time_s"]) > 0.0], dtype=float)
            y = np.array([float(r[f"{point}_epwp_lian_kPa"]) for r in rows if float(r["time_s"]) > 0.0], dtype=float)
            ax.plot(t, y, style, lw=1.8, label=label)
        ax.axvline(1.0, color="0.3", ls=":", lw=1.0)
        ax.set_xscale("log")
        ax.set_xlabel("Elapsed time from load start (s)")
        ax.set_ylabel(f"{point} EPWP (kPa)")
        ax.grid(True, alpha=0.28)
        ax.legend()
    fig.savefig(out_dir / "lian_timestep_ab_overlay.png", dpi=220)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Compare two Lian flexible strip timestep runs.")
    parser.add_argument("--base-dir", type=Path, required=True)
    parser.add_argument("--test-dir", type=Path, required=True)
    parser.add_argument("--base-label", default="base")
    parser.add_argument("--test-label", default="test")
    parser.add_argument("--targets", default="0.5,1.0,3.0")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    test_dir = args.test_dir.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = [float(v) for v in args.targets.split(",") if v.strip()]

    base_rows = read_history(base_dir)
    test_rows = read_history(test_dir)
    plot_histories(args.base_label, base_rows, args.test_label, test_rows, out_dir)

    summary_rows = []
    for target in targets:
        base_vtk, base_times = nearest_part(base_dir, target)
        test_vtk, test_times = nearest_part(test_dir, target)
        base_part = part_index(base_vtk)
        test_part = part_index(test_vtk)
        base_t = base_times.get(base_part, base_part)
        test_t = test_times.get(test_part, test_part)
        base_pts, base_arrays = parse_vtk(base_vtk)
        test_pts, test_arrays = parse_vtk(test_vtk)

        base_id = base_arrays["Idp"].astype(int)
        test_id = test_arrays["Idp"].astype(int)
        test_map = {int(pid): i for i, pid in enumerate(test_id)}
        pairs = [(i, test_map[int(pid)]) for i, pid in enumerate(base_id) if int(pid) in test_map]
        if not pairs:
            raise SystemExit(f"No matching Idp values at target {target}")
        ib = np.array([p[0] for p in pairs], dtype=int)
        it = np.array([p[1] for p in pairs], dtype=int)
        base_epwp = base_arrays["ExcessPorePress"][ib] / 1000.0
        test_epwp = test_arrays["ExcessPorePress"][it] / 1000.0
        diff = test_epwp - base_epwp
        row = {
            "target_s": target,
            "base_part": base_part,
            "test_part": test_part,
            "base_time_s": base_t,
            "test_time_s": test_t,
            "matched_particles": int(len(diff)),
            "base_max_kPa": float(np.nanmax(base_epwp)),
            "test_max_kPa": float(np.nanmax(test_epwp)),
            "mean_abs_diff_kPa": float(np.nanmean(np.abs(diff))),
            "rms_diff_kPa": float(np.sqrt(np.nanmean(diff * diff))),
            "max_abs_diff_kPa": float(np.nanmax(np.abs(diff))),
            "mean_signed_diff_kPa": float(np.nanmean(diff)),
        }
        row["max_abs_diff_over_base_max"] = row["max_abs_diff_kPa"] / max(abs(row["base_max_kPa"]), 1e-12)
        summary_rows.append(row)

    csv_path = out_dir / "lian_timestep_compare_summary.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    fig, ax = plt.subplots(figsize=(8.0, 4.6), constrained_layout=True)
    t = np.array([r["target_s"] for r in summary_rows], dtype=float)
    ax.plot(t, [r["mean_abs_diff_kPa"] for r in summary_rows], "o-", label="mean abs")
    ax.plot(t, [r["rms_diff_kPa"] for r in summary_rows], "s-", label="RMS")
    ax.plot(t, [r["max_abs_diff_kPa"] for r in summary_rows], "^-", label="max abs")
    ax.set_xlabel("Target time (s)")
    ax.set_ylabel(f"{args.test_label} - {args.base_label} EPWP difference (kPa)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.savefig(out_dir / "lian_timestep_field_diff_metrics.png", dpi=220)
    plt.close(fig)

    json_path = out_dir / "lian_timestep_compare_summary.json"
    json_path.write_text(json.dumps({
        "base_dir": str(base_dir),
        "test_dir": str(test_dir),
        "base_label": args.base_label,
        "test_label": args.test_label,
        "summary": summary_rows,
    }, indent=2), encoding="utf-8")

    print(csv_path)
    print(out_dir / "lian_timestep_ab_overlay.png")
    print(out_dir / "lian_timestep_field_diff_metrics.png")
    print(json_path)
    for row in summary_rows:
        print(row)


if __name__ == "__main__":
    main()
