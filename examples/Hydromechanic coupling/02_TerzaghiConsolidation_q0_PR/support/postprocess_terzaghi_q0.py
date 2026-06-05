from pathlib import Path
import csv
import math
import re
import struct

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
PARTICLES = ROOT / "CaseTerzaghiConsolidation_q0_PR_out" / "particles"
FIGDIR = ROOT / "figures"

H = 1.0
DP = 0.01
Q0 = 10000.0
TL = 0.01
RHO_W = 1000.0
G_REF = 9.81
E = 2.0e6
NU = 0.3
K_HYD = 1.0e-3
TOUT = 0.0025
TIME_MAX = 3.66
TARGET_TV = [0.0, 0.005, 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0]

K_BULK = E / (3.0 * (1.0 - 2.0 * NU))
G_SHEAR = E / (2.0 * (1.0 + NU))
M_CONSTRAINED = K_BULK + 4.0 * G_SHEAR / 3.0
CV = K_HYD * M_CONSTRAINED / (RHO_W * G_REF)
MV = 1.0 / M_CONSTRAINED


def read_line(data, offset):
    end = data.find(b"\n", offset)
    if end < 0:
        return data[offset:].decode("ascii", errors="ignore").strip(), len(data)
    line = data[offset:end].decode("ascii", errors="ignore").strip()
    return line, end + 1


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


def reshape(values, components):
    if components == 1:
        return list(values)
    return [tuple(values[i:i + components]) for i in range(0, len(values), components)]


def read_part_vtk(path):
    data = path.read_bytes()
    offset = 0

    for _ in range(4):
        _, offset = read_line(data, offset)

    line, offset = read_line(data, offset)
    parts = line.split()
    if len(parts) != 3 or parts[0] != "POINTS":
        raise RuntimeError(f"Unexpected VTK POINTS line in {path}: {line}")
    npoints = int(parts[1])
    values, offset = read_values(data, offset, parts[2], npoints * 3)
    points = reshape(values, 3)
    offset = skip_line_end(data, offset)

    line, offset = read_line(data, offset)
    parts = line.split()
    if len(parts) >= 3 and parts[0] == "VERTICES":
        _, offset = read_values(data, offset, "int", int(parts[2]))
        offset = skip_line_end(data, offset)
        line, offset = read_line(data, offset)

    parts = line.split()
    if len(parts) != 2 or parts[0] != "POINT_DATA":
        raise RuntimeError(f"Unexpected VTK POINT_DATA line in {path}: {line}")
    ndata = int(parts[1])

    arrays = {}
    while offset < len(data):
        line, offset = read_line(data, offset)
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
            _, offset = read_line(data, offset)
            values, offset = read_values(data, offset, type_name, ndata * components)
            arrays[name] = reshape(values, components)
            offset = skip_line_end(data, offset)
            continue

        if parts[0] == "VECTORS":
            name = parts[1]
            type_name = parts[2]
            values, offset = read_values(data, offset, type_name, ndata * 3)
            arrays[name] = reshape(values, 3)
            offset = skip_line_end(data, offset)
            continue

        if len(parts) >= 4 and parts[1].isdigit() and parts[2].isdigit():
            name = parts[0]
            components = int(parts[1])
            tuples = int(parts[2])
            type_name = parts[3]
            values, offset = read_values(data, offset, type_name, tuples * components)
            arrays[name] = reshape(values, components)
            offset = skip_line_end(data, offset)
            continue

        break

    required = ["PorePress", "PorePress0", "ExcessPorePress"]
    for name in required:
        if name not in arrays:
            raise RuntimeError(f"{path} does not contain required array {name}")

    rows = []
    vel = arrays.get("Vel")
    sigma_kk = arrays.get("Sigma_kk")
    for i, (pos, p, p0, pe) in enumerate(zip(points, arrays["PorePress"], arrays["PorePress0"], arrays["ExcessPorePress"])):
        row = {
            "x": float(pos[0]),
            "z": float(pos[2]),
            "pore": float(p),
            "pore0": float(p0),
            "excess": float(pe),
        }
        if vel is not None:
            vx, vy, vz = vel[i]
            row["speed"] = math.sqrt(float(vx) ** 2 + float(vy) ** 2 + float(vz) ** 2)
        if sigma_kk is not None:
            diag = sigma_kk[i]
            if isinstance(diag, tuple) and len(diag) >= 3:
                row["sigma_kk"] = float(diag[0]) + float(diag[1]) + float(diag[2])
            else:
                row["sigma_kk"] = float(diag)
        rows.append(row)
    return rows


def part_index(path):
    match = re.search(r"PartFluid_(\d+)\.vtk$", path.name)
    if not match:
        raise RuntimeError(f"Unexpected particle file name: {path.name}")
    return int(match.group(1))


def load_series(folder):
    data = []
    for path in sorted(folder.glob("PartFluid_*.vtk")):
        idx = part_index(path)
        time = min(TIME_MAX, idx * TOUT)
        rows = read_part_vtk(path)
        data.append({"name": path.name, "index": idx, "time": time, "rows": rows})
    if not data:
        raise RuntimeError(f"No PartFluid VTK files found in {folder}")
    return data


def layer_average(rows, value_key):
    bins = {}
    for row in rows:
        if value_key not in row:
            continue
        key = int(math.floor(row["z"] / DP + 0.5 + 1e-6))
        bins.setdefault(key, []).append(row)
    prof = []
    for _, items in sorted(bins.items()):
        z = sum(p["z"] for p in items) / len(items)
        value = sum(p[value_key] for p in items) / len(items)
        prof.append((z, value))
    return prof


def top_layer_z(rows):
    zmax = max(row["z"] for row in rows)
    items = [row for row in rows if row["z"] >= zmax - 0.55 * DP]
    return sum(row["z"] for row in items) / len(items)


def load_q(time):
    if time <= 0.0:
        return 0.0
    if time < TL:
        return Q0 * time / TL
    return Q0


def tv_from_time(time):
    return CV * max(0.0, time - TL) / (H * H)


def time_from_tv(tv):
    return TL + tv * H * H / CV


def terzaghi_excess(z, t_rel, nterms=240):
    value = 0.0
    for n in range(nterms):
        lam = (2 * n + 1) * math.pi / (2.0 * H)
        an = 2.0 * Q0 * math.sin(lam * H) / (H * lam)
        value += an * math.cos(lam * z) * math.exp(-lam * lam * CV * t_rel)
    return value


def degree_theory(tv, nterms=240):
    value = 0.0
    for n in range(nterms):
        m = (2 * n + 1) * math.pi / 2.0
        value += 2.0 / (m * m) * math.exp(-m * m * tv)
    return 1.0 - value


def nearest_snapshot(series, time):
    return min(series, key=lambda item: abs(item["time"] - time))


def mean_value(rows, key):
    values = [row[key] for row in rows if key in row]
    if not values:
        return 0.0
    return sum(values) / len(values)


def max_value(rows, key):
    values = [row[key] for row in rows if key in row]
    if not values:
        return 0.0
    return max(values)


def write_history_csv(series, z0_top):
    path = FIGDIR / "terzaghi_q0_history.csv"
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "time_s",
            "tv_after_drainage",
            "load_pa",
            "mean_excess_pa",
            "u_num_from_mean_excess",
            "u_theory",
            "top_settlement_m",
            "settlement_theory_m",
            "max_speed_m_per_s",
        ])
        for item in series:
            time = item["time"]
            tv = tv_from_time(time)
            u_theory = degree_theory(tv) if time >= TL else 0.0
            mean_excess = mean_value(item["rows"], "excess")
            u_num = 1.0 - mean_excess / Q0 if time >= TL else 0.0
            settlement = z0_top - top_layer_z(item["rows"])
            s_theory = H * Q0 * MV * u_theory
            writer.writerow([
                f"{time:.8g}",
                f"{tv:.8g}",
                f"{load_q(time):.8g}",
                f"{mean_excess:.8g}",
                f"{u_num:.8g}",
                f"{u_theory:.8g}",
                f"{settlement:.8g}",
                f"{s_theory:.8g}",
                f"{max_value(item['rows'], 'speed'):.8g}",
            ])
    return path


def write_target_csv(series):
    path = FIGDIR / "terzaghi_q0_targets.csv"
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["target_tv", "snapshot", "time_s", "actual_tv", "mean_excess_pa", "u_num", "u_theory"])
        for tv in TARGET_TV:
            item = nearest_snapshot(series, time_from_tv(tv))
            mean_excess = mean_value(item["rows"], "excess")
            u_num = 1.0 - mean_excess / Q0 if item["time"] >= TL else 0.0
            writer.writerow([
                f"{tv:.8g}",
                item["name"],
                f"{item['time']:.8g}",
                f"{tv_from_time(item['time']):.8g}",
                f"{mean_excess:.8g}",
                f"{u_num:.8g}",
                f"{degree_theory(tv_from_time(item['time'])):.8g}",
            ])
    return path


def plot_profiles(series):
    cols = 3
    rows = math.ceil(len(TARGET_TV) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(12, 3.4 * rows), sharex=True, sharey=True)
    axes = list(axes.flat)
    zgrid = [i * H / 200.0 for i in range(201)]
    for ax, tv in zip(axes, TARGET_TV):
        item = nearest_snapshot(series, time_from_tv(tv))
        prof = layer_average(item["rows"], "excess")
        t_rel = max(0.0, item["time"] - TL)
        ax.plot([terzaghi_excess(z, t_rel) / 1000.0 for z in zgrid], zgrid, "k-", lw=1.2, label="Terzaghi")
        ax.plot([p / 1000.0 for _, p in prof], [z for z, _ in prof], "o", ms=3, label="SPH")
        ax.set_title(f"Tv={tv_from_time(item['time']):.3g}, t={item['time']:.4g}s")
        ax.grid(True, alpha=0.3)
    for ax in axes[len(TARGET_TV):]:
        ax.axis("off")
    axes[0].legend(loc="best")
    for ax in axes:
        ax.set_xlabel("Excess pore pressure (kPa)")
        ax.set_ylabel("z (m)")
    fig.tight_layout()
    path = FIGDIR / "terzaghi_q0_profiles.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_history(series, z0_top):
    times = [item["time"] for item in series]
    load = [load_q(t) / 1000.0 for t in times]
    mean_excess = [mean_value(item["rows"], "excess") / 1000.0 for item in series]
    u_num = [1.0 - mean_value(item["rows"], "excess") / Q0 if item["time"] >= TL else 0.0 for item in series]
    u_th = [degree_theory(tv_from_time(item["time"])) if item["time"] >= TL else 0.0 for item in series]
    settlement = [(z0_top - top_layer_z(item["rows"])) * 1000.0 for item in series]
    s_th = [H * Q0 * MV * u * 1000.0 for u in u_th]

    fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    axes[0].plot(times, load, "k--", label="q(t)")
    axes[0].plot(times, mean_excess, "C0-", label="Mean excess p")
    axes[0].axvline(TL, color="0.4", lw=1, ls=":")
    axes[0].set_ylabel("kPa")
    axes[0].legend(loc="best")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(times, u_num, "C1-", label="SPH from mean excess")
    axes[1].plot(times, u_th, "k--", label="Terzaghi")
    axes[1].axvline(TL, color="0.4", lw=1, ls=":")
    axes[1].set_ylabel("Degree U")
    axes[1].legend(loc="best")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(times, settlement, "C2-", label="SPH top settlement")
    axes[2].plot(times, s_th, "k--", label="Terzaghi")
    axes[2].axvline(TL, color="0.4", lw=1, ls=":")
    axes[2].set_xlabel("Time (s)")
    axes[2].set_ylabel("Settlement (mm)")
    axes[2].legend(loc="best")
    axes[2].grid(True, alpha=0.3)

    fig.tight_layout()
    path = FIGDIR / "terzaghi_q0_history.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True)
    series = load_series(PARTICLES)
    z0_top = top_layer_z(series[0]["rows"])
    history_csv = write_history_csv(series, z0_top)
    target_csv = write_target_csv(series)
    profiles_png = plot_profiles(series)
    history_png = plot_history(series, z0_top)

    final = series[-1]
    final_tv = tv_from_time(final["time"])
    final_mean = mean_value(final["rows"], "excess")
    final_u = 1.0 - final_mean / Q0
    final_settlement = z0_top - top_layer_z(final["rows"])
    print(f"Loaded {len(series)} snapshots from {PARTICLES}")
    print(f"cv = {CV:.6g} m2/s, final Tv = {final_tv:.6g}")
    print(f"Final mean excess p = {final_mean / 1000.0:.6g} kPa")
    print(f"Final U_num = {final_u:.6g}, U_theory = {degree_theory(final_tv):.6g}")
    print(f"Final top settlement = {final_settlement * 1000.0:.6g} mm")
    print(f"Saved {history_csv}")
    print(f"Saved {target_csv}")
    print(f"Saved {profiles_png}")
    print(f"Saved {history_png}")


if __name__ == "__main__":
    main()
