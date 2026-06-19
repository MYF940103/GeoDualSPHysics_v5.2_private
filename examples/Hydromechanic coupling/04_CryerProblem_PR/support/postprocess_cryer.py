from pathlib import Path
import csv
import json
import math
import os
import re
import struct

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent


def env_path(name, default):
    return Path(os.environ.get(name, str(default)))


def env_float(name, default):
    value = os.environ.get(name)
    return float(value) if value is not None else default


PARTICLES = env_path("CRYER_PARTICLES", ROOT / "CaseCryerProblem_PR_out" / "particles")
FIGDIR = env_path("CRYER_FIGDIR", ROOT / "figures")
OUTTAG = os.environ.get("CRYER_OUTTAG", "cryer_center_pressure")
SUMMARY_JSON = os.environ.get("CRYER_SUMMARY_JSON")

RADIUS = env_float("CRYER_RADIUS", 0.05)
DP = env_float("CRYER_DP", 0.01)
Q0 = env_float("CRYER_Q0", 10000.0)
TL = env_float("CRYER_TL", 0.0)
LOAD_RAMP = env_float("CRYER_LOAD_RAMP", TL)
RHO_W = env_float("CRYER_RHO_W", 1000.0)
G_REF = env_float("CRYER_G_REF", 9.81)
E = env_float("CRYER_E", 2.0e6)
NU = env_float("CRYER_NU", 0.3)
K_HYD = env_float("CRYER_K_HYD", 1.0e-3)
TOUT = env_float("CRYER_TOUT", 0.0001)
TIME_MAX = env_float("CRYER_TIME_MAX", 0.005)
CENTER_SAMPLE_RADIUS = env_float("CRYER_CENTER_SAMPLE_RADIUS", 2.0 * DP)
NROOTS = 360

K_BULK = E / (3.0 * (1.0 - 2.0 * NU))
G_SHEAR = E / (2.0 * (1.0 + NU))
M_CONSTRAINED = K_BULK + 4.0 * G_SHEAR / 3.0
CV = K_HYD * M_CONSTRAINED / (RHO_W * G_REF)
ETA = (1.0 - NU) / (1.0 - 2.0 * NU)


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

    required = ["PorePress", "ExcessPorePress", "FSType"]
    for name in required:
        if name not in arrays:
            raise RuntimeError(f"{path} does not contain required array {name}")

    rows = []
    vel = arrays.get("Vel")
    for i, (pos, pore, excess, fstype) in enumerate(zip(points, arrays["PorePress"], arrays["ExcessPorePress"], arrays["FSType"])):
        row = {
            "x": float(pos[0]),
            "y": float(pos[1]),
            "z": float(pos[2]),
            "r": math.sqrt(float(pos[0]) ** 2 + float(pos[1]) ** 2 + float(pos[2]) ** 2),
            "pore": float(pore),
            "excess": float(excess),
            "fstype": int(fstype),
        }
        if vel is not None:
            vx, vy, vz = vel[i]
            row["speed"] = math.sqrt(float(vx) ** 2 + float(vy) ** 2 + float(vz) ** 2)
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


def mean(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def load_q(time):
    if time <= 0.0:
        return 0.0
    if time < LOAD_RAMP:
        return Q0 * time / LOAD_RAMP
    return Q0


def tv_from_time(time):
    return CV * max(0.0, time - TL) / (RADIUS * RADIUS)


def cryer_root_function(z):
    return (1.0 - ETA * z * z) * math.sin(z) - z * math.cos(z)


def bisection_root(a, b):
    fa = cryer_root_function(a)
    fb = cryer_root_function(b)
    if fa * fb > 0.0:
        raise RuntimeError("Root interval does not bracket a sign change")
    for _ in range(80):
        c = 0.5 * (a + b)
        fc = cryer_root_function(c)
        if fa * fc <= 0.0:
            b = c
            fb = fc
        else:
            a = c
            fa = fc
    return 0.5 * (a + b)


def cryer_roots(nroots):
    roots = []
    k = 0
    while len(roots) < nroots:
        a = k * math.pi + 1e-10
        b = (k + 1) * math.pi - 1e-10
        x0 = a
        f0 = cryer_root_function(x0)
        found = False
        for j in range(1, 65):
            x1 = a + (b - a) * j / 64.0
            f1 = cryer_root_function(x1)
            if f0 * f1 < 0.0:
                roots.append(bisection_root(x0, x1))
                found = True
                break
            x0 = x1
            f0 = f1
        if not found and k > nroots + 8:
            raise RuntimeError("Unable to find enough Cryer roots")
        k += 1
    return roots


CRYER_ROOTS = cryer_roots(NROOTS)


def cryer_center_pressure(tv):
    if tv <= 0.0:
        return 1.0
    value = 0.0
    for z in CRYER_ROOTS:
        den = ETA * z * math.cos(z) + (2.0 * ETA - 1.0) * math.sin(z)
        coef = 2.0 * ETA * (math.sin(z) - z) / den
        value += coef * math.exp(-z * z * tv)
    return value


def center_stats(rows):
    items = [row for row in rows if row["r"] <= CENTER_SAMPLE_RADIUS]
    if not items:
        nearest = min(rows, key=lambda row: row["r"])
        items = [nearest]
    return {
        "count": len(items),
        "radius_mean": mean([row["r"] for row in items]),
        "pore": mean([row["pore"] for row in items]),
        "excess": mean([row["excess"] for row in items]),
        "max_speed": max([row.get("speed", 0.0) for row in rows]),
        "free_surface_count": sum(1 for row in rows if row["fstype"] in (2, 3)),
    }


def write_history_csv(series):
    path = FIGDIR / f"{OUTTAG}.csv"
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "time_s",
            "tv_after_load",
            "load_pa",
            "center_pore_pa",
            "center_pore_over_q0",
            "theory_pore_over_q0",
            "center_excess_pa",
            "sample_count",
            "sample_radius_mean_m",
            "free_surface_count",
            "max_speed_m_per_s",
        ])
        for item in series:
            stat = center_stats(item["rows"])
            tv = tv_from_time(item["time"])
            writer.writerow([
                f"{item['time']:.8g}",
                f"{tv:.8g}",
                f"{load_q(item['time']):.8g}",
                f"{stat['pore']:.8g}",
                f"{stat['pore'] / Q0:.8g}",
                f"{cryer_center_pressure(tv):.8g}" if item["time"] >= TL else "",
                f"{stat['excess']:.8g}",
                stat["count"],
                f"{stat['radius_mean']:.8g}",
                stat["free_surface_count"],
                f"{stat['max_speed']:.8g}",
            ])
    return path


def plot_history(series):
    times = [item["time"] for item in series]
    tvs = [tv_from_time(t) for t in times]
    stats = [center_stats(item["rows"]) for item in series]
    pc_num = [stat["pore"] / Q0 for stat in stats]
    load = [load_q(t) / Q0 for t in times]

    tvmax = max(tvs)
    tv_grid = [0.0] + [tvmax * i / 500.0 for i in range(1, 501)]
    theory = [cryer_center_pressure(tv) for tv in tv_grid]

    fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=False)
    axes[0].plot(tvs, pc_num, "o", ms=3, label="SPH center sample")
    axes[0].plot(tv_grid, theory, "k-", lw=1.3, label="Cryer analytical")
    axes[0].axhline(1.0, color="0.45", lw=1, ls=":")
    axes[0].set_xlabel("Tv = cv (t - tL) / R^2")
    axes[0].set_ylabel("p_center / q0")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")

    axes[1].plot(times, pc_num, "C0-", label="SPH p_center/q0")
    axes[1].plot(times, load, "k--", label="q(t)/q0")
    axes[1].axvline(TL, color="0.45", lw=1, ls=":")
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("Normalized pressure")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best")

    fig.tight_layout()
    path = FIGDIR / f"{OUTTAG}.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def history_metrics(series):
    rows = []
    for item in series:
        stat = center_stats(item["rows"])
        tv = tv_from_time(item["time"])
        num = stat["pore"] / Q0
        theory = cryer_center_pressure(tv) if item["time"] >= TL else None
        rows.append({
            "time": item["time"],
            "tv": tv,
            "num": num,
            "theory": theory,
            "sample_count": stat["count"],
            "free_surface_count": stat["free_surface_count"],
            "max_speed": stat["max_speed"],
        })

    after_load = min([r for r in rows if r["time"] >= TL], key=lambda r: abs(r["time"] - TL))
    valid = [r for r in rows if r["theory"] is not None]
    rmse = math.sqrt(mean([(r["num"] - r["theory"]) ** 2 for r in valid]))
    mae = mean([abs(r["num"] - r["theory"]) for r in valid])
    peak_num = max(valid, key=lambda r: r["num"])
    peak_theory = max(valid, key=lambda r: r["theory"])
    final = valid[-1]
    return {
        "snapshots": len(series),
        "cv": CV,
        "eta": ETA,
        "load_end_time": after_load["time"],
        "load_end_tv": after_load["tv"],
        "load_end_num": after_load["num"],
        "load_end_theory": after_load["theory"],
        "load_end_abs_error": abs(after_load["num"] - after_load["theory"]),
        "rmse": rmse,
        "mae": mae,
        "peak_num": peak_num["num"],
        "peak_num_time": peak_num["time"],
        "peak_num_tv": peak_num["tv"],
        "peak_theory_at_peak_num": peak_num["theory"],
        "peak_theory": peak_theory["theory"],
        "peak_theory_time": peak_theory["time"],
        "peak_theory_tv": peak_theory["tv"],
        "num_at_peak_theory": peak_theory["num"],
        "final_num": final["num"],
        "final_theory": final["theory"],
        "final_tv": final["tv"],
        "final_abs_error": abs(final["num"] - final["theory"]),
        "max_speed": max(r["max_speed"] for r in rows),
        "min_sample_count": min(r["sample_count"] for r in rows),
        "min_free_surface_count": min(r["free_surface_count"] for r in rows),
    }


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True)
    series = load_series(PARTICLES)
    history_csv = write_history_csv(series)
    history_png = plot_history(series)

    values = []
    for item in series:
        stat = center_stats(item["rows"])
        values.append((stat["pore"] / Q0, item["time"], tv_from_time(item["time"])))
    peak_num, peak_time, peak_tv = max(values, key=lambda row: row[0])
    peak_theory = cryer_center_pressure(peak_tv)
    final_num, final_time, final_tv = values[-1]
    final_theory = cryer_center_pressure(final_tv)

    print(f"Loaded {len(series)} snapshots from {PARTICLES}")
    print(f"cv = {CV:.6g} m2/s, eta = {ETA:.6g}, final Tv = {final_tv:.6g}")
    print(f"Peak SPH p/q0 = {peak_num:.6g} at t = {peak_time:.6g}s, Tv = {peak_tv:.6g}")
    print(f"Theory p/q0 at peak SPH Tv = {peak_theory:.6g}")
    print(f"Final SPH p/q0 = {final_num:.6g}, theory = {final_theory:.6g}")
    print(f"Saved {history_csv}")
    print(f"Saved {history_png}")
    metrics = history_metrics(series)
    if SUMMARY_JSON:
        with Path(SUMMARY_JSON).open("w") as f:
            json.dump(metrics, f, indent=2)
        print(f"Saved {SUMMARY_JSON}")


if __name__ == "__main__":
    main()
