from pathlib import Path
import argparse
import csv
import math
import struct

import matplotlib.pyplot as plt


def read_line(data, offset):
    end = data.find(b"\n", offset)
    if end < 0:
        return data[offset:].decode("ascii", errors="ignore").strip(), len(data)
    return data[offset:end].decode("ascii", errors="ignore").strip(), end + 1


def skip_line_end(data, offset):
    if offset < len(data) and data[offset] == 13:
        offset += 1
    if offset < len(data) and data[offset] == 10:
        offset += 1
    return offset


def vtk_type(type_name):
    sizes = {
        "float": (4, "f"),
        "double": (8, "d"),
        "int": (4, "i"),
        "unsigned_int": (4, "I"),
        "short": (2, "h"),
        "unsigned_short": (2, "H"),
        "unsigned_char": (1, "B"),
    }
    if type_name not in sizes:
        raise RuntimeError(f"Unsupported VTK binary type: {type_name}")
    return sizes[type_name]


def read_values(data, offset, type_name, count):
    size, code = vtk_type(type_name)
    raw = data[offset:offset + size * count]
    if len(raw) != size * count:
        raise RuntimeError("Unexpected end of VTK binary block")
    values = struct.unpack(">" + code * count, raw)
    return values, offset + size * count


def read_points(path):
    data = path.read_bytes()
    offset = 0
    for _ in range(4):
        _, offset = read_line(data, offset)
    line, offset = read_line(data, offset)
    parts = line.split()
    if len(parts) != 3 or parts[0] != "POINTS":
        raise RuntimeError(f"Unexpected VTK POINTS line in {path}: {line}")
    count = int(parts[1])
    values, offset = read_values(data, offset, parts[2], count * 3)
    points = [values[i:i + 3] for i in range(0, len(values), 3)]
    return points


def read_normals(path):
    data = path.read_bytes()
    offset = 0
    for _ in range(4):
        _, offset = read_line(data, offset)
    line, offset = read_line(data, offset)
    parts = line.split()
    if len(parts) != 3 or parts[0] != "POINTS":
        raise RuntimeError(f"Unexpected VTK POINTS line in {path}: {line}")
    count = int(parts[1])
    values, offset = read_values(data, offset, parts[2], count * 3)
    points = [values[i:i + 3] for i in range(0, len(values), 3)]
    offset = skip_line_end(data, offset)

    marker = b"Normal 3 "
    pos = data.find(marker, offset)
    if pos < 0:
        raise RuntimeError(f"Normal field not found in {path}")
    offset = pos
    line, offset = read_line(data, offset)
    parts = line.split()
    if len(parts) != 4 or parts[0] != "Normal" or parts[1] != "3":
        raise RuntimeError(f"Unexpected Normal field line in {path}: {line}")
    normal_count = int(parts[2])
    values, _ = read_values(data, offset, parts[3], normal_count * 3)
    normals = [values[i:i + 3] for i in range(0, len(values), 3)]
    if normal_count != count:
        raise RuntimeError(f"Normal count mismatch in {path}: {normal_count} != {count}")
    return points, normals


def wendland_wab_fac_2d(rr2, h):
    rad = math.sqrt(rr2)
    if rad <= 0:
        return None
    qq = rad / h
    if qq > 2.0:
        return None
    wqq1 = 1.0 - 0.5 * qq
    wqq2 = wqq1 * wqq1
    awen = 0.557 / (h * h)
    bwen = -2.7852 / (h * h * h)
    fac = bwen * qq * wqq2 * wqq1 / rad
    wab = awen * (qq + qq + 1.0) * wqq2 * wqq2
    return wab, fac


def det3(a):
    return (
        a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
        - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
        + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
    )


def inv3(a, d):
    return [
        [
            (a[1][1] * a[2][2] - a[1][2] * a[2][1]) / d,
            (a[0][2] * a[2][1] - a[0][1] * a[2][2]) / d,
            (a[0][1] * a[1][2] - a[0][2] * a[1][1]) / d,
        ],
        [
            (a[1][2] * a[2][0] - a[1][0] * a[2][2]) / d,
            (a[0][0] * a[2][2] - a[0][2] * a[2][0]) / d,
            (a[0][2] * a[1][0] - a[0][0] * a[1][2]) / d,
        ],
        [
            (a[1][0] * a[2][1] - a[1][1] * a[2][0]) / d,
            (a[0][1] * a[2][0] - a[0][0] * a[2][1]) / d,
            (a[0][0] * a[1][1] - a[0][1] * a[1][0]) / d,
        ],
    ]


def dot(row, vec):
    return sum(a * b for a, b in zip(row, vec))


def linear_q(point, coeff):
    x, _y, z = point
    return coeff[0] + coeff[1] * x + coeff[2] * z


def reconstruct_boundary_q(bound_point, normal, fluid_points, h, dp, coeff, determ_limit):
    gx = bound_point[0] + normal[0]
    gy = bound_point[1] + normal[1]
    gz = bound_point[2] + normal[2]
    a = [[0.0, 0.0, 0.0] for _ in range(3)]
    b = [0.0, 0.0, 0.0]
    sumwab = 0.0
    qsum = 0.0
    neighbours = 0
    for p in fluid_points:
        drx = gx - p[0]
        dry = gy - p[1]
        drz = gz - p[2]
        rr2 = drx * drx + dry * dry + drz * drz
        wf = wendland_wab_fac_2d(rr2, h)
        if wf is None:
            continue
        wab, fac = wf
        vol = dp * dp
        vwab = wab * vol
        vfrx = fac * drx * vol
        vfrz = fac * drz * vol
        q = linear_q(p, coeff)
        sumwab += vwab
        qsum += vwab * q
        b[0] += vwab * q
        b[1] += vfrx * q
        b[2] += vfrz * q
        a[0][0] += vwab
        a[0][1] += drx * vwab
        a[0][2] += drz * vwab
        a[1][0] += vfrx
        a[1][1] += drx * vfrx
        a[1][2] += drz * vfrx
        a[2][0] += vfrz
        a[2][1] += drx * vfrz
        a[2][2] += drz * vfrz
        neighbours += 1
    if sumwab <= 0.0:
        return None
    zero = qsum / sumwab
    determinant = det3(a)
    used_fallback = abs(determinant) < determ_limit
    mls_ghost = zero
    mls_boundary = zero
    if not used_fallback:
        inv = inv3(a, determinant)
        qg = dot(inv[0], b)
        qgx = -dot(inv[1], b)
        qgz = -dot(inv[2], b)
        dposx = -normal[0]
        dposz = -normal[2]
        mls_ghost = qg
        mls_boundary = qg + qgx * dposx + qgz * dposz
    ghost_point = (gx, gy, gz)
    exact_boundary = linear_q(bound_point, coeff)
    exact_ghost = linear_q(ghost_point, coeff)
    return {
        "x": bound_point[0],
        "z": bound_point[2],
        "normal_x": normal[0],
        "normal_z": normal[2],
        "gpos_x": gx,
        "gpos_z": gz,
        "neighbours": neighbours,
        "sumwab": sumwab,
        "determinant": determinant,
        "used_fallback": int(used_fallback),
        "exact_boundary_q": exact_boundary,
        "exact_ghost_q": exact_ghost,
        "zero_q": zero,
        "mls_ghost_q": mls_ghost,
        "mls_boundary_q": mls_boundary,
        "zero_vs_ghost_error": zero - exact_ghost,
        "mls_ghost_error": mls_ghost - exact_ghost,
        "mls_boundary_error": mls_boundary - exact_boundary,
        "boundary_minus_ghost_q": exact_boundary - exact_ghost,
    }


def rms(values):
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else float("nan")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fluid", required=True, type=Path)
    parser.add_argument("--normals", required=True, type=Path)
    parser.add_argument("--figdir", required=True, type=Path)
    parser.add_argument("--dp", type=float, default=0.01)
    parser.add_argument("--hdp", type=float, default=1.8)
    parser.add_argument("--determ-limit", type=float, default=1e-3)
    parser.add_argument("--q0", type=float, default=1000.0)
    parser.add_argument("--qx", type=float, default=2500.0)
    parser.add_argument("--qz", type=float, default=15000.0)
    args = parser.parse_args()

    args.figdir.mkdir(parents=True, exist_ok=True)
    fluid_points = read_points(args.fluid)
    bound_points, normals = read_normals(args.normals)
    h = args.dp * args.hdp
    coeff = (args.q0, args.qx, args.qz)

    rows = []
    for point, normal in zip(bound_points, normals):
        # This diagnostic is for the bottom mDBC boundary in the 2D column.
        if normal[2] <= 0.0:
            continue
        item = reconstruct_boundary_q(point, normal, fluid_points, h, args.dp, coeff, args.determ_limit)
        if item is not None:
            rows.append(item)
    if not rows:
        raise RuntimeError("No bottom mDBC boundary rows were reconstructed.")

    csv_path = args.figdir / "bottom_linear_q_recovery.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "n_boundary": len(rows),
        "n_fallback": sum(row["used_fallback"] for row in rows),
        "zero_vs_ghost_rms": rms([row["zero_vs_ghost_error"] for row in rows]),
        "mls_ghost_rms": rms([row["mls_ghost_error"] for row in rows]),
        "mls_boundary_rms": rms([row["mls_boundary_error"] for row in rows]),
        "zero_vs_ghost_max_abs": max(abs(row["zero_vs_ghost_error"]) for row in rows),
        "mls_ghost_max_abs": max(abs(row["mls_ghost_error"]) for row in rows),
        "mls_boundary_max_abs": max(abs(row["mls_boundary_error"]) for row in rows),
        "boundary_minus_ghost_mean": sum(row["boundary_minus_ghost_q"] for row in rows) / len(rows),
        "min_neighbours": min(row["neighbours"] for row in rows),
        "max_neighbours": max(row["neighbours"] for row in rows),
        "min_abs_det": min(abs(row["determinant"]) for row in rows),
        "max_abs_det": max(abs(row["determinant"]) for row in rows),
    }
    summary_path = args.figdir / "bottom_linear_q_recovery_summary.csv"
    with summary_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(summary.keys())
        writer.writerow(summary.values())

    rows_top = [row for row in rows if abs(row["z"] - max(r["z"] for r in rows)) < 1e-9]
    rows_top.sort(key=lambda row: row["x"])
    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    ax.axhline(0.0, color="k", lw=0.8)
    ax.plot([r["x"] for r in rows_top], [r["zero_vs_ghost_error"] for r in rows_top], "o-", label="zero-order vs ghost q")
    ax.plot([r["x"] for r in rows_top], [r["mls_ghost_error"] for r in rows_top], "s-", label="MLS ghost/projection vs ghost q")
    ax.plot([r["x"] for r in rows_top], [r["mls_boundary_error"] for r in rows_top], "^-", label="old MLS boundary-extension vs boundary q")
    ax.set_xlabel("x [m] at top bottom-boundary layer")
    ax.set_ylabel("linear q recovery error [Pa]")
    ax.grid(True, alpha=0.25)
    ax.legend()
    ax.set_title("mDBC bottom boundary linear excess-pore-pressure recovery")
    fig_path = args.figdir / "bottom_linear_q_recovery.png"
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)

    print(f"Saved recovery rows: {csv_path}")
    print(f"Saved recovery summary: {summary_path}")
    print(f"Saved recovery plot: {fig_path}")
    print(
        "Recovery summary: "
        f"n={summary['n_boundary']}, fallback={summary['n_fallback']}, "
        f"zero-vs-ghost RMS={summary['zero_vs_ghost_rms']:.6g} Pa, "
        f"MLS ghost RMS={summary['mls_ghost_rms']:.6g} Pa, "
        f"old boundary-extension RMS={summary['mls_boundary_rms']:.6g} Pa"
    )


if __name__ == "__main__":
    main()
