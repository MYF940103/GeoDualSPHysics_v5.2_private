from pathlib import Path
import csv
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri


CASE_OUT = "CaseYao2DConsolidation_PR_gpu2s_dp01_damp002_out"
PARTS = ((5, 0.1), (100, 2.0))


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
    total_vertices = int(line.split()[2])
    idx += total_vertices * np.dtype(">i4").itemsize

    idx = skip_ws(buf, idx)
    line, idx = read_line(buf, idx)
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
            raise ValueError(f"Unsupported VTK record: {line}")
    return points, arrays


def read_part(base, prefix, part):
    return parse_vtk(base / "particles" / f"{prefix}_{part:04d}.vtk")


def mirror_error(x, z, value):
    buckets = {}
    for xi, zi, vi in zip(x, z, value):
        key = (round(abs(float(xi)), 2), round(float(zi), 2))
        buckets.setdefault(key, []).append((xi, vi))
    errors = []
    for entries in buckets.values():
        left = [vi for xi, vi in entries if xi < -1e-6]
        right = [vi for xi, vi in entries if xi > 1e-6]
        if left and right:
            errors.append(abs(float(np.mean(left)) - float(np.mean(right))))
    return (float(np.mean(errors)), float(np.max(errors))) if errors else (float("nan"), float("nan"))


def write_figures(out_dir, data):
    fig_dir = out_dir / "figures_gpu2s_dp01_damp002"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, len(data), figsize=(12.0, 4.4), constrained_layout=True)
    for ax, row in zip(np.atleast_1d(axes), data):
        x, z, p = row["x"], row["z"], row["epwp_kpa"]
        triang = mtri.Triangulation(x, z)
        levels = np.linspace(0, 5, 21)
        cf = ax.tricontourf(triang, np.clip(p, 0, 5), levels=levels, cmap="turbo", extend="max")
        ax.plot([-3, 3], [10, 10], color="black", lw=2.0)
        ax.set_xlim(-10, 10)
        ax.set_ylim(0, 10)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(f"Fluid EPWP, t={row['time_s']:g} s")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("z (m)")
    cbar = fig.colorbar(cf, ax=np.atleast_1d(axes), shrink=0.85, pad=0.02)
    cbar.set_label("Excess pore pressure (kPa), clipped 0-5")
    fig.savefig(fig_dir / "yao2d_epwp_fulldomain_fixed0_5kpa.png", dpi=240)
    plt.close(fig)

    fig, axes = plt.subplots(1, len(data), figsize=(12.0, 4.4), constrained_layout=True)
    for ax, row in zip(np.atleast_1d(axes), data):
        x, z, p = row["x"], row["z"], row["epwp_kpa"]
        mask = x >= -1e-6
        triang = mtri.Triangulation(x[mask], z[mask])
        levels = np.linspace(max(0.0, float(np.nanmin(p[mask]))), max(0.01, float(np.nanmax(p[mask]))), 24)
        cf = ax.tricontourf(triang, p[mask], levels=levels, cmap="turbo", extend="max")
        ax.plot([0, 3], [10, 10], color="black", lw=2.0)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(f"Right half, t={row['time_s']:g} s")
        ax.set_xlabel("x from symmetry line (m)")
        ax.set_ylabel("z (m)")
        fig.colorbar(cf, ax=ax, shrink=0.85, pad=0.02).set_label("kPa")
    fig.savefig(fig_dir / "yao2d_epwp_righthalf_autoscale.png", dpi=240)
    plt.close(fig)

    return fig_dir


def main():
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parent if script_dir.name == "scripts" else script_dir
    outputs_dir = root / "outputs"
    figures_dir = root / "figures"
    out = outputs_dir / CASE_OUT
    particles = out / "particles"
    if not particles.exists():
        raise SystemExit(f"Missing particle output: {particles}")

    rows = []
    plot_rows = []
    for part, time_s in PARTS:
        pts, arrays = read_part(out, "PartFluid", part)
        x, z = pts[:, 0], pts[:, 2]
        epwp = arrays["ExcessPorePress"] / 1000.0
        load_az = arrays["HydroMechLoadAce"][:, 2]
        strip_top = (np.abs(x) <= 3.05) & (z > 9.85)
        open_top = (np.abs(x) > 3.05) & (z > 9.85)
        mean_sym, max_sym = mirror_error(x, z, epwp)
        rows.append({
            "part": part,
            "time_s": time_s,
            "fluid_np": len(x),
            "epwp_min_kpa": float(np.min(epwp)),
            "epwp_max_kpa": float(np.max(epwp)),
            "strip_top_epwp_min_kpa": float(np.min(epwp[strip_top])) if np.any(strip_top) else np.nan,
            "strip_top_epwp_max_kpa": float(np.max(epwp[strip_top])) if np.any(strip_top) else np.nan,
            "open_top_absmax_kpa": float(np.max(np.abs(epwp[open_top]))) if np.any(open_top) else np.nan,
            "loaded_fluid_particles": int(np.count_nonzero(np.abs(load_az) > 1e-12)),
            "mirror_mean_abs_kpa": mean_sym,
            "mirror_max_abs_kpa": max_sym,
        })
        plot_rows.append({"time_s": time_s, "x": x, "z": z, "epwp_kpa": epwp})

    bound_counts = []
    for part, time_s in PARTS:
        bpts, barrays = read_part(out, "PartBound", part)
        bound_counts.append({"part": part, "time_s": time_s, "bound_np": len(bpts), "arrays": ";".join(barrays.keys())})

    fig_dir = write_figures(figures_dir, plot_rows)
    metrics_path = fig_dir / "yao2d_gpu2s_dp01_damp002_metrics.csv"
    with metrics_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    bound_path = fig_dir / "yao2d_gpu2s_dp01_damp002_bound_summary.csv"
    with bound_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(bound_counts[0].keys()))
        writer.writeheader()
        writer.writerows(bound_counts)

    print(metrics_path)
    for row in rows:
        print(row)
    print(bound_path)
    for row in bound_counts:
        print(row)


if __name__ == "__main__":
    main()
