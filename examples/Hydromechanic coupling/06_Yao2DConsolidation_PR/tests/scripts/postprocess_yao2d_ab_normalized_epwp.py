from pathlib import Path
import argparse
import csv
import re

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "scripts" else SCRIPT_DIR
CASE_OUT = ROOT / "outputs" / "CaseYao2DConsolidation_PR_gpu10s_dp01_damp001_nodiffusion_freeslip_out"
Q0_PA = 5000.0
TIME_OUT = 0.05
POINTS = {
    "A": (2.0, 8.0),
    "B": (8.0, 2.0),
}


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


def part_index(path):
    match = re.search(r"PartFluid_(\d+)\.vtk$", path.name)
    if not match:
        raise ValueError(f"Cannot parse part index from {path}")
    return int(match.group(1))


def find_point_ids(particles_dir):
    pts, arrays = parse_vtk(particles_dir / "PartFluid_0000.vtk")
    idp = arrays["Idp"].astype(int)
    found = {}
    for name, (xt, zt) in POINTS.items():
        dist2 = (pts[:, 0] - xt) ** 2 + (pts[:, 2] - zt) ** 2
        idx = int(np.argmin(dist2))
        found[name] = {
            "idp": int(idp[idx]),
            "x0": float(pts[idx, 0]),
            "z0": float(pts[idx, 2]),
            "distance": float(np.sqrt(dist2[idx])),
        }
    return found


def main():
    parser = argparse.ArgumentParser(
        description="Extract normalized EPWP histories at Yao 2025 Fig. 26 A/B points."
    )
    parser.add_argument(
        "--case-dir",
        type=Path,
        default=CASE_OUT,
        help="Case output directory containing a particles folder.",
    )
    args = parser.parse_args()

    case_out = args.case_dir.resolve()
    particles_dir = case_out / "particles"
    if not particles_dir.exists():
        raise SystemExit(f"Missing particle VTK directory: {particles_dir}")
    vtk_files = sorted(particles_dir.glob("PartFluid_*.vtk"), key=part_index)
    if not vtk_files:
        raise SystemExit(f"No PartFluid VTK files found in {particles_dir}")

    point_ids = find_point_ids(particles_dir)
    rows = []
    for vtk in vtk_files:
        part = part_index(vtk)
        pts, arrays = parse_vtk(vtk)
        idp = arrays["Idp"].astype(int)
        id_to_idx = {int(pid): i for i, pid in enumerate(idp)}
        epwp = arrays["ExcessPorePress"]
        pore = arrays["PorePress"]
        row = {
            "part": part,
            "time_s": part * TIME_OUT,
        }
        for name, meta in point_ids.items():
            idx = id_to_idx[meta["idp"]]
            row[f"{name}_idp"] = meta["idp"]
            row[f"{name}_x"] = float(pts[idx, 0])
            row[f"{name}_z"] = float(pts[idx, 2])
            row[f"{name}_target_distance_m"] = meta["distance"]
            row[f"{name}_epwp_pa"] = float(epwp[idx])
            row[f"{name}_epwp_kpa"] = float(epwp[idx] / 1000.0)
            row[f"{name}_epwp_over_q0"] = float(epwp[idx] / Q0_PA)
            row[f"{name}_porepress_pa"] = float(pore[idx])
        rows.append(row)

    fig_dir = case_out / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    csv_path = fig_dir / "yao2d_ab_normalized_epwp.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    t = np.array([row["time_s"] for row in rows], dtype=float)
    fig, ax = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)
    for name in POINTS:
        y = np.array([row[f"{name}_epwp_over_q0"] for row in rows], dtype=float)
        ax.plot(t, y, lw=1.8, label=f"{name} {POINTS[name]}")
    ax.axvline(0.1, color="0.3", ls="--", lw=1.0)
    ax.set_xlim(0, max(10.0, float(np.nanmax(t))))
    ax.set_xlabel("t (s)")
    ax.set_ylabel("Excess pore pressure / q0")
    ax.grid(True, alpha=0.28)
    ax.legend()
    fig.savefig(fig_dir / "yao2d_ab_normalized_epwp.png", dpi=240)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)
    for name in POINTS:
        y = np.array([row[f"{name}_epwp_kpa"] for row in rows], dtype=float)
        ax.plot(t, y, lw=1.8, label=f"{name} {POINTS[name]}")
    ax.axvline(0.1, color="0.3", ls="--", lw=1.0)
    ax.set_xlim(0, max(10.0, float(np.nanmax(t))))
    ax.set_xlabel("t (s)")
    ax.set_ylabel("Excess pore pressure (kPa)")
    ax.grid(True, alpha=0.28)
    ax.legend()
    fig.savefig(fig_dir / "yao2d_ab_epwp_kpa.png", dpi=240)
    plt.close(fig)

    print(csv_path)
    print(fig_dir / "yao2d_ab_normalized_epwp.png")
    print(fig_dir / "yao2d_ab_epwp_kpa.png")
    for name, meta in point_ids.items():
        print(f"{name}: idp={meta['idp']} sampled=({meta['x0']:.6g},{meta['z0']:.6g}) target_distance={meta['distance']:.6g} m")


if __name__ == "__main__":
    main()
