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


def part_index(path):
    return int(path.stem.rsplit("_", 1)[1])


def read_vtk_arrays(path):
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


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else float("nan")


def max_abs(values):
    values = list(values)
    return max((abs(v) for v in values), default=float("nan"))


def layer_groups(points, arrays):
    groups = {}
    for i, pos in enumerate(points):
        key = int(math.floor(float(pos[2]) / pp.DP + 0.5 + 1e-6))
        groups.setdefault(key, []).append(i)
    return [(key, idxs) for key, idxs in sorted(groups.items())]


def layer_average(points, arrays, name, component=None):
    if name not in arrays:
        return []
    out = []
    for _, idxs in layer_groups(points, arrays):
        z = mean(float(points[i][2]) for i in idxs)
        vals = []
        for i in idxs:
            val = arrays[name][i]
            if component is not None:
                val = val[component]
            vals.append(float(val))
        out.append((z, mean(vals)))
    return out


def bottom_indices(points, thickness=0.1):
    ordered = sorted(range(len(points)), key=lambda i: float(points[i][2]))
    count = max(1, int(round(thickness / pp.DP)))
    return ordered[:count]


def bottom_mean(points, arrays, name, component=None, thickness=0.1):
    if name not in arrays:
        return float("nan"), float("nan")
    idxs = bottom_indices(points, thickness)
    vals = []
    for i in idxs:
        val = arrays[name][i]
        if component is not None:
            val = val[component]
        vals.append(float(val))
    return mean(vals), mean(float(points[i][2]) for i in idxs)


def linear_slope(zv):
    if len(zv) < 2:
        return float("nan")
    zs = [p[0] for p in zv]
    vs = [p[1] for p in zv]
    zbar = mean(zs)
    vbar = mean(vs)
    denom = sum((z - zbar) ** 2 for z in zs)
    if denom <= 0:
        return float("nan")
    return sum((z - zbar) * (v - vbar) for z, v in zip(zs, vs)) / denom


def central_derivative(rows, key, xkey="tv"):
    vals = [float("nan")] * len(rows)
    for i in range(len(rows)):
        if i == 0 and len(rows) > 1:
            dx = rows[i + 1][xkey] - rows[i][xkey]
            vals[i] = (rows[i + 1][key] - rows[i][key]) / dx if dx else float("nan")
        elif i == len(rows) - 1 and len(rows) > 1:
            dx = rows[i][xkey] - rows[i - 1][xkey]
            vals[i] = (rows[i][key] - rows[i - 1][key]) / dx if dx else float("nan")
        elif 0 < i < len(rows) - 1:
            dx = rows[i + 1][xkey] - rows[i - 1][xkey]
            vals[i] = (rows[i + 1][key] - rows[i - 1][key]) / dx if dx else float("nan")
    return vals


def sign(x, eps=1e-10):
    if x > eps:
        return 1
    if x < -eps:
        return -1
    return 0


def find_turning_windows(rows, derivative_key="bottom_error_dtv_kpa"):
    windows = []
    prev_sign = 0
    prev_idx = None
    for i, row in enumerate(rows):
        s = sign(row[derivative_key], eps=0.05)
        if s == 0:
            continue
        if prev_sign and s != prev_sign and prev_idx is not None:
            j0 = max(0, i - 2)
            j1 = min(len(rows) - 1, i + 2)
            windows.append({
                "kind": "residual_slope_sign_change",
                "part_start": rows[j0]["part"],
                "part_end": rows[j1]["part"],
                "part_center": row["part"],
                "tv_start": rows[j0]["tv"],
                "tv_end": rows[j1]["tv"],
                "tv_center": row["tv"],
                "from_sign": prev_sign,
                "to_sign": s,
                "bottom_error_kpa": row["bottom_error_kpa"],
                "bottom_error_dtv_kpa": row[derivative_key],
                "bottom_vz_m_s": row.get("bottom_vz_m_s", float("nan")),
                "bottom_vz_dtv_m_s": row.get("bottom_vz_dtv_m_s", float("nan")),
                "dvz_dz_bottom_proxy_1_s": row.get("dvz_dz_bottom_proxy_1_s", float("nan")),
                "dvz_dz_bottom_dtv_1_s": row.get("dvz_dz_bottom_dtv_1_s", float("nan")),
                "bottom_sigma_zz_error_pa": row.get("bottom_sigma_zz_error_pa", float("nan")),
                "sigma_zz_error_dtv_pa": row.get("sigma_zz_error_dtv_pa", float("nan")),
                "max_speed_m_s": row.get("max_speed_m_s", float("nan")),
            })
        prev_sign = s
        prev_idx = i
    return windows


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--particles", required=True, type=Path)
    parser.add_argument("--figdir", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--tout", required=True, type=float)
    parser.add_argument("--tmax", required=True, type=float)
    parser.add_argument("--tv-offset", type=float, default=0.0)
    args = parser.parse_args()

    paths = sorted(args.particles.glob("PartFluid_*.vtk"), key=part_index)
    if not paths:
        raise RuntimeError(f"No PartFluid VTK files found in {args.particles}")
    args.figdir.mkdir(parents=True, exist_ok=True)

    rows = []
    available_arrays = None
    for path in paths:
        idx = part_index(path)
        time_s = min(args.tmax, idx * args.tout)
        tv = args.tv_offset + pp.CV_TERZAGHI * time_s / (pp.H * pp.H)
        points, arrays = read_vtk_arrays(path)
        if available_arrays is None:
            available_arrays = sorted(arrays)
        b_excess, bz = bottom_mean(points, arrays, "ExcessPorePress")
        theory = pp.terzaghi_excess(bz, time_s)
        b_sigma_zz, _ = bottom_mean(points, arrays, "Sigma_kk", component=2)
        b_sigma_xx, _ = bottom_mean(points, arrays, "Sigma_kk", component=0)
        b_sigma_kk = b_sigma_xx + bottom_mean(points, arrays, "Sigma_kk", component=1)[0] + b_sigma_zz
        b_speed = float("nan")

        if "Vel" in arrays:
            b_vx, _ = bottom_mean(points, arrays, "Vel", component=0)
            b_vz, _ = bottom_mean(points, arrays, "Vel", component=2)
            layer_vz = layer_average(points, arrays, "Vel", component=2)
            bottom_layers = layer_vz[:6]
            middle_layers = layer_vz[2:12]
            dvz_dz_bottom = linear_slope(bottom_layers)
            dvz_dz_lower = linear_slope(middle_layers)
            max_speed = max(math.sqrt(float(v[0]) ** 2 + float(v[1]) ** 2 + float(v[2]) ** 2) for v in arrays["Vel"])
            max_vz = max_abs(float(v[2]) for v in arrays["Vel"])
            b_speed = mean(
                math.sqrt(float(arrays["Vel"][i][0]) ** 2 + float(arrays["Vel"][i][1]) ** 2 + float(arrays["Vel"][i][2]) ** 2)
                for i in bottom_indices(points)
            )
        else:
            b_vx = b_vz = dvz_dz_bottom = dvz_dz_lower = max_speed = max_vz = float("nan")

        row = {
            "part": path.name,
            "part_index": idx,
            "time_s": time_s,
            "tv": tv,
            "bottom_z_m": bz,
            "bottom_excess_sph_kpa": b_excess / 1000.0,
            "bottom_excess_theory_kpa": theory / 1000.0,
            "bottom_error_kpa": (b_excess - theory) / 1000.0,
            "bottom_vx_m_s": b_vx,
            "bottom_vz_m_s": b_vz,
            "bottom_speed_m_s": b_speed,
            "max_speed_m_s": max_speed,
            "max_abs_vz_m_s": max_vz,
            "dvz_dz_bottom_proxy_1_s": dvz_dz_bottom,
            "dvz_dz_lower_proxy_1_s": dvz_dz_lower,
            "bottom_sigma_xx_pa": b_sigma_xx,
            "bottom_sigma_zz_pa": b_sigma_zz,
            "bottom_sigma_kk_pa": b_sigma_kk,
            "bottom_sigma_zz_theory_pa": pp.effective_sigma_zz(bz),
            "bottom_sigma_zz_error_pa": b_sigma_zz - pp.effective_sigma_zz(bz),
            "rms_excess_pa": float("nan"),
            "rms_sigma_zz_pa": float("nan"),
        }

        pp_rows = pp.read_part_vtk(path)
        row["rms_excess_pa"] = pp.rms_error(pp_rows, "excess", lambda z, t=time_s: pp.terzaghi_excess(z, t))
        if any("sigma_zz" in r for r in pp_rows):
            row["rms_sigma_zz_pa"] = pp.rms_error(pp_rows, "sigma_zz", pp.effective_sigma_zz)
        rows.append(row)

    for key, out_key in [
        ("bottom_error_kpa", "bottom_error_dtv_kpa"),
        ("bottom_excess_sph_kpa", "bottom_sph_dtv_kpa"),
        ("bottom_excess_theory_kpa", "bottom_theory_dtv_kpa"),
        ("bottom_vz_m_s", "bottom_vz_dtv_m_s"),
        ("dvz_dz_bottom_proxy_1_s", "dvz_dz_bottom_dtv_1_s"),
        ("bottom_sigma_zz_error_pa", "sigma_zz_error_dtv_pa"),
    ]:
        vals = central_derivative(rows, key)
        for row, val in zip(rows, vals):
            row[out_key] = val

    windows = find_turning_windows(rows)

    fields = list(rows[0].keys())
    out_csv = args.figdir / "scenario2_baseline_oscillation_timeseries.csv"
    write_csv(out_csv, rows, fields)

    win_csv = args.figdir / "scenario2_baseline_oscillation_windows.csv"
    if windows:
        write_csv(win_csv, windows, list(windows[0].keys()))
    else:
        win_csv.write_text("kind\n", encoding="utf-8")

    arrays_txt = args.figdir / "available_vtk_arrays.txt"
    arrays_txt.write_text("\n".join(available_arrays or []) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(5, 1, figsize=(13, 15), sharex=True, constrained_layout=True)
    tv = [r["tv"] for r in rows]
    axes[0].plot(tv, [r["bottom_excess_sph_kpa"] for r in rows], label="SPH bottom excess", color="#1f77b4")
    axes[0].plot(tv, [r["bottom_excess_theory_kpa"] for r in rows], "--", label="Terzaghi theory", color="#444444")
    axes[0].set_ylabel("Bottom EPWP [kPa]")
    axes[0].legend()
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(tv, [r["bottom_error_kpa"] for r in rows], label="SPH - theory", color="#d62728")
    axes[1].plot(tv, [r["bottom_error_dtv_kpa"] for r in rows], label="d(error)/dTv", color="#9467bd", alpha=0.8)
    axes[1].axhline(0, color="k", linewidth=0.8)
    axes[1].set_ylabel("Bottom residual")
    axes[1].legend()
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(tv, [r["bottom_vz_m_s"] for r in rows], label="bottom mean vz", color="#2ca02c")
    axes[2].plot(tv, [r["max_abs_vz_m_s"] for r in rows], label="max |vz|", color="#17becf", alpha=0.75)
    axes[2].axhline(0, color="k", linewidth=0.8)
    axes[2].set_ylabel("Velocity [m/s]")
    axes[2].legend()
    axes[2].grid(True, alpha=0.25)

    axes[3].plot(tv, [r["dvz_dz_bottom_proxy_1_s"] for r in rows], label="bottom dvz/dz proxy", color="#ff7f0e")
    axes[3].plot(tv, [r["dvz_dz_lower_proxy_1_s"] for r in rows], label="lower-column dvz/dz proxy", color="#bcbd22", alpha=0.8)
    axes[3].axhline(0, color="k", linewidth=0.8)
    axes[3].set_ylabel("Proxy [1/s]")
    axes[3].legend()
    axes[3].grid(True, alpha=0.25)

    axes[4].plot(tv, [r["bottom_sigma_zz_error_pa"] / 1000.0 for r in rows], label="bottom sigma_zz error", color="#8c564b")
    axes[4].plot(tv, [r["rms_sigma_zz_pa"] / 1000.0 for r in rows], label="RMS sigma_zz error", color="#e377c2", alpha=0.8)
    axes[4].axhline(0, color="k", linewidth=0.8)
    axes[4].set_ylabel("Stress residual [kPa]")
    axes[4].set_xlabel("Time factor Tv")
    axes[4].legend()
    axes[4].grid(True, alpha=0.25)

    for ax in axes:
        for w in windows:
            ax.axvspan(w["tv_start"], w["tv_end"], color="gold", alpha=0.12, linewidth=0)

    fig.suptitle(f"{args.case}: baseline mid/late oscillation diagnosis")
    figpath = args.figdir / "scenario2_baseline_oscillation_diagnostics.png"
    fig.savefig(figpath, dpi=220)

    print(f"Saved time series: {out_csv}")
    print(f"Saved windows: {win_csv}")
    print(f"Saved arrays list: {arrays_txt}")
    print(f"Saved figure: {figpath}")
    print("Available arrays:", ", ".join(available_arrays or []))
    print("Detected residual slope sign-change windows:")
    for w in windows:
        print(
            f"  Tv {w['tv_start']:.3f}-{w['tv_end']:.3f} center {w['tv_center']:.3f}: "
            f"{w['from_sign']} -> {w['to_sign']}, error={w['bottom_error_kpa']:.4f} kPa"
        )


if __name__ == "__main__":
    main()
