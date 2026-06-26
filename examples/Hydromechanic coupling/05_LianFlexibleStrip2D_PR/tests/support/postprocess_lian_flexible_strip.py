import argparse
import csv
import json
import math
import re
import struct
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri


FIELD_NAMES = {
    "epwp": "ExcessPorePress",
    "load": "HydroMechLoadAce",
}

PROBES = {
    "A": (0.1, 10.0),
    "A_below": (0.1, 9.9),
    "B": (1.25, 8.75),
}


def read_vtk(path):
    data = Path(path).read_bytes()
    pos = data.find(b"POINTS ")
    if pos < 0:
        raise RuntimeError(f"POINTS block not found in {path}")
    line_end = data.find(b"\n", pos)
    _, nstr, dtype = data[pos:line_end].decode("ascii").split()
    if dtype != "float":
        raise RuntimeError(f"Unsupported POINTS dtype {dtype} in {path}")
    n = int(nstr)
    off = line_end + 1
    raw = struct.unpack(">" + "f" * (n * 3), data[off:off + n * 3 * 4])
    x = [raw[i * 3] for i in range(n)]
    z = [raw[i * 3 + 2] for i in range(n)]
    fields = {}
    for name in FIELD_NAMES.values():
        token = ("\n" + name + " ").encode("ascii")
        p = data.find(token)
        if p < 0:
            continue
        le = data.find(b"\n", p + 1)
        parts = data[p + 1:le].decode("ascii").split()
        comp = int(parts[1])
        count = int(parts[2])
        dtype = parts[3]
        if dtype != "float":
            continue
        fo = le + 1
        vals = struct.unpack(">" + "f" * (comp * count), data[fo:fo + comp * count * 4])
        fields[name] = (comp, vals)
    return x, z, fields


def read_times(run_out):
    times = {0: 0.0}
    pattern = re.compile(r"^\s*Part_(\d{4})\s+([0-9.+\-Ee]+)\s+\d+\s+\d+\s+")
    if Path(run_out).exists():
        for line in Path(run_out).read_text(errors="ignore").splitlines():
            m = pattern.search(line)
            if m:
                times[int(m.group(1))] = float(m.group(2))
    return times


def idw_value(x, z, values, target, k=8):
    tx, tz = target
    dist = []
    for i, (xi, zi) in enumerate(zip(x, z)):
        d2 = (xi - tx) * (xi - tx) + (zi - tz) * (zi - tz)
        if d2 < 1e-18:
            return values[i], [(i, xi, zi, 1.0)]
        dist.append((d2, i))
    dist.sort(key=lambda row: row[0])
    picked = dist[:k]
    weights = [1.0 / max(d2, 1e-18) for d2, _ in picked]
    wsum = sum(weights)
    val = sum(w * values[i] for w, (_, i) in zip(weights, picked)) / wsum
    meta = [(i, x[i], z[i], w / wsum) for w, (_, i) in zip(weights, picked)]
    return val, meta


def parse_index(path):
    m = re.search(r"PartFluid_(\d{4})\.vtk$", Path(path).name)
    if not m:
        raise RuntimeError(f"Unexpected VTK filename: {path}")
    return int(m.group(1))


def plot_contours(records, targets, out_path, value_key="epwp_lian_kpa", cbar_label="Excess pore pressure, compression positive (kPa)"):
    fig, axes = plt.subplots(1, len(targets), figsize=(5.2 * len(targets), 3.7), constrained_layout=True)
    if len(targets) == 1:
        axes = [axes]
    values_for_targets = []
    for rec in records:
        if rec["time_target"] in targets:
            values_for_targets.extend(rec[value_key])
    if value_key == "epwp_lian_kpa":
        maxv = max(values_for_targets) if values_for_targets else 0.0
        levels = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
        if maxv > levels[-1]:
            levels.append(math.ceil(maxv))
    else:
        vmin = min(values_for_targets) if values_for_targets else -1.0
        vmax = max(values_for_targets) if values_for_targets else 1.0
        if abs(vmax - vmin) < 1e-12:
            vmin -= 1e-6
            vmax += 1e-6
        levels = [vmin + (vmax - vmin) * i / 10.0 for i in range(11)]
    for ax, target in zip(axes, targets):
        rec = min(records, key=lambda r: abs(r["time"] - target))
        tri = mtri.Triangulation(rec["x"], rec["z"])
        cn = ax.tricontourf(tri, rec[value_key], levels=levels, cmap="turbo", extend="both")
        ax.tricontour(tri, rec[value_key], levels=levels, colors="k", linewidths=0.25, alpha=0.35)
        ax.set_title(f"t={rec['time']:.3f}s")
        ax.set_xlabel("x (m)")
        ax.set_xlim(0, 20)
        ax.set_ylim(0, 10)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, color="0.85", linewidth=0.4)
        ax.plot([0, 1.25], [10, 10], color="black", linewidth=3.0, solid_capstyle="butt")
        ax.scatter([0.1, 0.1, 1.25], [10.0, 9.9, 8.75], s=24, c=["red", "orange", "white"], edgecolors="black", zorder=5)
    axes[0].set_ylabel("z (m)")
    cbar = fig.colorbar(cn, ax=axes, shrink=0.82, pad=0.015)
    cbar.set_label(cbar_label)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_ab_curve(rows, out_path):
    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    plot_rows = [r for r in rows if r["time_s"] > 0.0]
    t = [r["time_s"] for r in plot_rows]
    ax.plot(t, [r["A_epwp_lian_kPa"] for r in plot_rows], marker="o", linewidth=1.8, label="A: x=0.1, z=10.0")
    ax.plot(t, [r["A_below_epwp_lian_kPa"] for r in plot_rows], marker="^", linewidth=1.4, linestyle="--", label="A below: x=0.1, z=9.9")
    ax.plot(t, [r["B_epwp_lian_kPa"] for r in plot_rows], marker="s", linewidth=1.8, label="B: x=1.25, z=8.75")
    ax.set_xscale("log")
    ax.axvline(1.0, color="0.3", linestyle="--", linewidth=1.0, label="tL=1s")
    ax.set_xlabel("Elapsed time from load start (s)")
    ax.set_ylabel("Excess pore pressure, compression positive (kPa)")
    ax.grid(True, color="0.85", linewidth=0.6)
    ax.legend()
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="DualSPHysics output directory")
    parser.add_argument("--out-dir", default=None, help="Directory for figures and CSV files")
    parser.add_argument("--targets", default="0.5,1.0,3.0", help="Target contour times in seconds")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else run_dir.parent / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    support_dir = run_dir.parent / "support"
    support_dir.mkdir(parents=True, exist_ok=True)
    targets = [float(v) for v in args.targets.split(",") if v.strip()]

    vtk_files = sorted((run_dir / "particles").glob("PartFluid_*.vtk"))
    if not vtk_files:
        raise RuntimeError(f"No PartFluid_*.vtk files found in {run_dir / 'particles'}")
    times = read_times(run_dir / "Run.out")
    records = []
    rows = []
    probe_meta = {}
    for vtk in vtk_files:
        idx = parse_index(vtk)
        time = times.get(idx, idx)
        x, z, fields = read_vtk(vtk)
        if FIELD_NAMES["epwp"] not in fields:
            raise RuntimeError(f"{FIELD_NAMES['epwp']} not found in {vtk}")
        comp, vals = fields[FIELD_NAMES["epwp"]]
        epwp_raw_kpa = [v / 1000.0 for v in vals]
        epwp_lian_kpa = [v / 1000.0 for v in vals]
        probe_vals = {}
        for name, target in PROBES.items():
            raw_val, meta = idw_value(x, z, epwp_raw_kpa, target, k=8)
            lian_val, _ = idw_value(x, z, epwp_lian_kpa, target, k=8)
            probe_vals[f"{name}_epwp_raw_kPa"] = raw_val
            probe_vals[f"{name}_epwp_lian_kPa"] = lian_val
            probe_meta.setdefault(name, meta)
        row = {
            "part": idx,
            "time_s": time,
            "time_after_ramp_s": time - 1.0,
            "max_epwp_lian_kPa": max(epwp_lian_kpa),
            "min_epwp_lian_kPa": min(epwp_lian_kpa),
        }
        row.update(probe_vals)
        rows.append(row)
        if any(abs(time - target) <= 0.5 + 1e-9 for target in targets):
            records.append({
                "part": idx,
                "time": time,
                "time_target": min(targets, key=lambda target: abs(time - target)),
                "x": x,
                "z": z,
                "epwp_raw_kpa": epwp_raw_kpa,
                "epwp_lian_kpa": epwp_lian_kpa,
            })

    rows.sort(key=lambda r: r["time_s"])
    csv_path = support_dir / "lian_flexible_strip_ab_epwp.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "part", "time_s", "time_after_ramp_s",
            "A_epwp_raw_kPa", "A_below_epwp_raw_kPa", "B_epwp_raw_kPa",
            "A_epwp_lian_kPa", "A_below_epwp_lian_kPa", "B_epwp_lian_kPa",
            "max_epwp_lian_kPa", "min_epwp_lian_kPa"
        ])
        writer.writeheader()
        writer.writerows(rows)

    contour_records = []
    for target in targets:
        vtk = min(vtk_files, key=lambda p: abs(times.get(parse_index(p), parse_index(p)) - target))
        idx = parse_index(vtk)
        time = times.get(idx, idx)
        x, z, fields = read_vtk(vtk)
        epwp_lian_kpa = [v / 1000.0 for v in fields[FIELD_NAMES["epwp"]][1]]
        epwp_raw_kpa = [v / 1000.0 for v in fields[FIELD_NAMES["epwp"]][1]]
        contour_records.append({
            "part": idx,
            "time": time,
            "time_target": target,
            "x": x,
            "z": z,
            "epwp_raw_kpa": epwp_raw_kpa,
            "epwp_lian_kpa": epwp_lian_kpa,
        })

    contour_path = out_dir / "lian_flexible_strip_epwp_contours.png"
    contour_raw_path = out_dir / "lian_flexible_strip_epwp_contours_raw.png"
    ab_path = out_dir / "lian_flexible_strip_ab_epwp.png"
    plot_contours(contour_records, targets, contour_path)
    plot_contours(
        contour_records,
        targets,
        contour_raw_path,
        value_key="epwp_raw_kpa",
        cbar_label="Raw ExcessPorePress = PorePress - PorePress0 (kPa)",
    )
    plot_ab_curve(rows, ab_path)

    metrics = {
        "run_dir": str(run_dir),
        "csv": str(csv_path),
        "contours": str(contour_path),
        "raw_contours": str(contour_raw_path),
        "ab_curve": str(ab_path),
        "targets": targets,
        "time_reference": "time_s follows Lian 2023 Fig. 10-11 elapsed time from load start; time_after_ramp_s = time_s - 1.0.",
        "pressure_sign": "raw ExcessPorePress is exported with the code sign convention; compression is positive in this validation, so lian_kPa columns and plots use raw/1000.",
        "probe_points": {
            name: {"x": target[0], "z": target[1], "interpolation": probe_meta.get(name, [])}
            for name, target in PROBES.items()
        },
        "rows": rows,
    }
    metrics_path = support_dir / "lian_flexible_strip_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Wrote {csv_path}")
    print(f"Wrote {contour_path}")
    print(f"Wrote {contour_raw_path}")
    print(f"Wrote {ab_path}")
    print(f"Wrote {metrics_path}")


if __name__ == "__main__":
    main()
