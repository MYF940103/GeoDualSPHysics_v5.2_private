from pathlib import Path
import csv
import math
import re
import struct

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
STAGE1 = ROOT / "CaseSelfWeightConsolidation_Stage1_out" / "particles"
SCENARIO2 = ROOT / "CaseSelfWeightConsolidation_Scenario2_out" / "particles"
FIGDIR = ROOT / "figures"

H = 1.0
DP = 0.01
G = 9.81
RHO_W = 1000.0
RHO_SOIL = 2100.0
RHO_SUBMERGED = RHO_SOIL - RHO_W
E = 2.0e6
NU = 0.3
KW = 2.0e8
POROSITY = 0.3
K_HYD = 1.0e-3

K_BULK = E / (3.0 * (1.0 - 2.0 * NU))
G_SHEAR = E / (2.0 * (1.0 + NU))
M_CONSTRAINED = K_BULK + 4.0 * G_SHEAR / 3.0
CV_TERZAGHI = K_HYD * M_CONSTRAINED / (RHO_W * G)
CV_PR_DIFFUSION = (KW / POROSITY) * K_HYD / (RHO_W * G)
UNDRAINED_RATIO = (KW / POROSITY) / (M_CONSTRAINED + KW / POROSITY)
EFFECTIVE_RATIO = M_CONSTRAINED / (M_CONSTRAINED + KW / POROSITY)

STAGE1_TOUT = 0.001
SCENARIO2_TOUT = 0.02
SCENARIO2_INITIAL_INDEX = 0
SCENARIO2_INITIAL_TIME = 0.0
SCENARIO2_TIME_MAX = 3.85
TARGET_TV = [0.005, 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0]


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
            _, offset = read_line(data, offset)  # LOOKUP_TABLE
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

    rows = []
    required = ["PorePress", "PorePress0", "ExcessPorePress"]
    for name in required:
        if name not in arrays:
            raise RuntimeError(f"{path} does not contain required array {name}")

    optional = {
        "Vel": arrays.get("Vel"),
        "Kplastic": arrays.get("Kplastic"),
        "Sigma_ij": arrays.get("Sigma_ij"),
        "Sigma_kk": arrays.get("Sigma_kk"),
    }
    for i, (pos, p, p0, pe) in enumerate(zip(points, arrays["PorePress"], arrays["PorePress0"], arrays["ExcessPorePress"])):
        row = {
            "x": float(pos[0]),
            "z": float(pos[2]),
            "pore": float(p),
            "pore0": float(p0),
            "excess": float(pe),
        }
        if optional["Vel"] is not None:
            vx, vy, vz = optional["Vel"][i]
            row["speed"] = math.sqrt(float(vx) ** 2 + float(vy) ** 2 + float(vz) ** 2)
        if optional["Kplastic"] is not None:
            row["kplastic"] = float(optional["Kplastic"][i])
        if optional["Sigma_kk"] is not None:
            diag = optional["Sigma_kk"][i]
            if isinstance(diag, tuple) and len(diag) >= 3:
                row["sigma_xx"] = float(diag[0])
                row["sigma_yy"] = float(diag[1])
                row["sigma_zz"] = float(diag[2])
                row["sigma_kk"] = row["sigma_xx"] + row["sigma_yy"] + row["sigma_zz"]
            else:
                row["sigma_kk"] = float(diag)
        if optional["Sigma_ij"] is not None and isinstance(optional["Sigma_ij"][i], tuple) and len(optional["Sigma_ij"][i]) >= 3:
            shear = optional["Sigma_ij"][i]
            row["sigma_xy"] = float(shear[0])
            row["sigma_xz"] = float(shear[1])
            row["sigma_yz"] = float(shear[2])
        rows.append(row)
    return rows


def part_index(path):
    match = re.search(r"PartFluid_(\d+)\.vtk$", path.name)
    if not match:
        raise RuntimeError(f"Unexpected particle file name: {path.name}")
    return int(match.group(1))


def load_series(folder, stage):
    data = []
    for path in sorted(folder.glob("PartFluid_*.vtk")):
        idx = part_index(path)
        if stage == 1:
            time = idx * STAGE1_TOUT
        else:
            time = min(SCENARIO2_TIME_MAX, SCENARIO2_INITIAL_TIME + (idx - SCENARIO2_INITIAL_INDEX) * SCENARIO2_TOUT)
        rows = read_part_vtk(path)
        data.append({"name": path.name, "index": idx, "time": time, "rows": rows})
    if not data:
        raise RuntimeError(f"No PartFluid VTK files found in {folder}")
    return data


def layer_average(rows, value_key):
    bins = {}
    for row in rows:
        key = int(math.floor(row["z"] / DP + 0.5 + 1e-6))
        bins.setdefault(key, []).append(row)
    prof = []
    for _, items in sorted(bins.items()):
        z = sum(p["z"] for p in items) / len(items)
        value = sum(p[value_key] for p in items if value_key in p) / len([p for p in items if value_key in p])
        prof.append((z, value))
    return prof


def hydrostatic(z):
    return RHO_W * G * max(0.0, H - z)


def undrained_excess(z):
    return UNDRAINED_RATIO * RHO_SUBMERGED * G * max(0.0, H - z)


def undrained_total(z):
    return hydrostatic(z) + undrained_excess(z)


def effective_sigma_zz(z):
    return -EFFECTIVE_RATIO * RHO_SUBMERGED * G * max(0.0, H - z)


def terzaghi_excess(z, t_rel, nterms=180):
    c = UNDRAINED_RATIO * RHO_SUBMERGED * G
    value = 0.0
    for n in range(nterms):
        lam = (2 * n + 1) * math.pi / (2.0 * H)
        an = 2.0 * c / (H * lam * lam)
        value += an * math.cos(lam * z) * math.exp(-lam * lam * CV_TERZAGHI * max(0.0, t_rel))
    return value


def bottom_average(rows, value_key):
    ordered = sorted([r for r in rows if value_key in r], key=lambda r: r["z"])
    count = max(1, int(round(0.1 / DP)))
    items = ordered[:count]
    return sum(p[value_key] for p in items) / len(items), sum(p["z"] for p in items) / len(items)


def rms_error(rows, value_key, theory):
    values = [(row[value_key] - theory(row["z"])) for row in rows if value_key in row]
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else float("nan")


def max_value(rows, value_key):
    values = [row[value_key] for row in rows if value_key in row]
    return max(values) if values else float("nan")


def stage1_metrics(data):
    rows = data["rows"]
    zvals = [row["z"] for row in rows]
    bottom_excess, bottom_z = bottom_average(rows, "excess")
    bottom_total, _ = bottom_average(rows, "pore")
    metrics = {
        "name": data["name"],
        "index": data["index"],
        "time": data["time"],
        "bottom_z": bottom_z,
        "bottom_excess_kpa": bottom_excess / 1000.0,
        "bottom_excess_theory_kpa": undrained_excess(bottom_z) / 1000.0,
        "bottom_total_kpa": bottom_total / 1000.0,
        "bottom_total_theory_kpa": undrained_total(bottom_z) / 1000.0,
        "rms_excess_pa": rms_error(rows, "excess", undrained_excess),
        "rms_total_pa": rms_error(rows, "pore", undrained_total),
        "max_speed": max_value(rows, "speed"),
        "max_kplastic": max_value(rows, "kplastic"),
        "mean_excess_kpa": sum(row["excess"] for row in rows) / len(rows) / 1000.0,
        "height_m": max(zvals) - min(zvals),
        "mean_z_m": sum(zvals) / len(zvals),
    }
    if any("sigma_zz" in r for r in rows):
        bottom_sigma, bottom_sigma_z = bottom_average(rows, "sigma_zz")
        metrics["bottom_sigma_zz_pa"] = bottom_sigma
        metrics["bottom_sigma_zz_theory_pa"] = effective_sigma_zz(bottom_sigma_z)
        metrics["rms_sigma_zz_pa"] = rms_error(rows, "sigma_zz", effective_sigma_zz)
    return metrics


def main():
    scenario2 = load_series(SCENARIO2, stage=2)
    initial_data = scenario2[0]
    initial_metrics = stage1_metrics(initial_data)
    t0 = initial_data["time"]

    zgrid = [i / 200.0 for i in range(201)]
    FIGDIR.mkdir(exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), constrained_layout=True)
    ax_excess, ax_total, ax_bottom = axes

    ax_excess.plot(
        [undrained_excess(z) / 1000.0 for z in zgrid],
        [z / H for z in zgrid],
        "k--",
        linewidth=1.6,
        label="theory initial excess",
    )
    ax_total.plot(
        [hydrostatic(z) / 1000.0 for z in zgrid],
        [z / H for z in zgrid],
        "k:",
        linewidth=1.8,
        label="theory hydrostatic",
    )
    ax_total.plot(
        [undrained_total(z) / 1000.0 for z in zgrid],
        [z / H for z in zgrid],
        "k--",
        linewidth=1.6,
        label="theory initial total",
    )

    prof_e = layer_average(initial_data["rows"], "excess")
    prof_p = layer_average(initial_data["rows"], "pore")
    ax_excess.plot([v / 1000.0 for _, v in prof_e], [z / H for z, _ in prof_e], "-", linewidth=1.8, label=f"analytical init t={t0:.3f}s")
    ax_total.plot([v / 1000.0 for _, v in prof_p], [z / H for z, _ in prof_p], "-", linewidth=1.8, label=f"analytical init t={t0:.3f}s")

    bottom_rows = []
    for data in scenario2:
        t_rel = max(0.0, data["time"] - t0)
        tv = CV_TERZAGHI * t_rel / (H * H)
        bnum, bz = bottom_average(data["rows"], "excess")
        btheory = terzaghi_excess(bz, t_rel)
        bottom_rows.append((data["time"], t_rel, tv, bnum / 1000.0, btheory / 1000.0, bz))

    selected = []
    used = set()
    for target_tv in TARGET_TV:
        data = min(
            scenario2,
            key=lambda item: abs(CV_TERZAGHI * max(0.0, item["time"] - t0) / (H * H) - target_tv),
        )
        if data["index"] not in used:
            selected.append((target_tv, data))
            used.add(data["index"])

    target_rows = []
    colors = plt.cm.viridis([i / max(1, len(selected) - 1) for i in range(len(selected))])
    for color, (target_tv, data) in zip(colors, selected):
        t_rel = max(0.0, data["time"] - t0)
        tv = CV_TERZAGHI * t_rel / (H * H)
        label = f"Tv={tv:.3f}"
        prof_e = layer_average(data["rows"], "excess")
        prof_p = layer_average(data["rows"], "pore")
        ax_excess.plot([v / 1000.0 for _, v in prof_e], [z / H for z, _ in prof_e], color=color, linewidth=1.35, label=label)
        ax_total.plot([v / 1000.0 for _, v in prof_p], [z / H for z, _ in prof_p], color=color, linewidth=1.35, label=label)
        ax_excess.plot(
            [terzaghi_excess(z, t_rel) / 1000.0 for z in zgrid],
            [z / H for z in zgrid],
            "--",
            color=color,
            linewidth=0.95,
            alpha=0.65,
        )
        ax_total.plot(
            [(hydrostatic(z) + terzaghi_excess(z, t_rel)) / 1000.0 for z in zgrid],
            [z / H for z in zgrid],
            "--",
            color=color,
            linewidth=0.95,
            alpha=0.65,
        )
        bnum, bz = bottom_average(data["rows"], "excess")
        btheory = terzaghi_excess(bz, t_rel)
        target_rows.append((
            target_tv,
            data["name"],
            data["time"],
            t_rel,
            tv,
            bnum / 1000.0,
            btheory / 1000.0,
            rms_error(data["rows"], "excess", lambda z, t_rel=t_rel: terzaghi_excess(z, t_rel)),
            max_value(data["rows"], "speed"),
        ))

    max_tv = max([r[2] for r in bottom_rows] + [0.001])
    tv_grid = [i / 250.0 * max_tv for i in range(251)]
    z_bottom = DP / 2.0
    ax_bottom.plot(
        tv_grid,
        [terzaghi_excess(z_bottom, tv / CV_TERZAGHI) / 1000.0 for tv in tv_grid],
        "k--",
        label="theory bottom excess",
    )
    ax_bottom.plot([r[2] for r in bottom_rows], [r[3] for r in bottom_rows], "o-", label="SPH bottom excess")

    ax_excess.set_xlabel("Excess pore pressure [kPa]")
    ax_excess.set_ylabel("z/H")
    ax_excess.set_title("Excess pore pressure")
    ax_excess.grid(True, alpha=0.25)
    ax_excess.legend(fontsize=8)

    ax_total.set_xlabel("Total pore pressure [kPa]")
    ax_total.set_ylabel("z/H")
    ax_total.set_title("Total pore pressure")
    ax_total.grid(True, alpha=0.25)
    ax_total.legend(fontsize=8)

    ax_bottom.set_xlabel("Tv")
    ax_bottom.set_ylabel("Bottom excess pore pressure [kPa]")
    ax_bottom.set_title("Bottom dissipation")
    ax_bottom.grid(True, alpha=0.25)
    ax_bottom.legend(fontsize=8)

    fig.suptitle("Self-weight consolidation verification, u-pw PR formulation")
    figpath = FIGDIR / "self_weight_consolidation_profiles.png"
    fig.savefig(figpath, dpi=220)

    initial_summary = FIGDIR / "self_weight_scenario2_initial_metrics.csv"
    with initial_summary.open("w", newline="") as f:
        fieldnames = sorted(initial_metrics.keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(initial_metrics)

    scenario2_summary = FIGDIR / "self_weight_consolidation_summary.csv"
    with scenario2_summary.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "t_rel_s", "Tv", "bottom_excess_sph_kPa", "bottom_excess_theory_kPa", "bottom_z_m"])
        writer.writerows(bottom_rows)

    target_summary = FIGDIR / "self_weight_consolidation_targets.csv"
    with target_summary.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "target_Tv",
            "part",
            "time_s",
            "t_rel_s",
            "actual_Tv",
            "bottom_excess_sph_kPa",
            "bottom_excess_theory_kPa",
            "rms_excess_pa",
            "max_speed",
        ])
        writer.writerows(target_rows)

    print(f"Saved figure: {figpath}")
    print(f"Saved Scenario2 initial metrics: {initial_summary}")
    print(f"Saved Scenario2 summary: {scenario2_summary}")
    print(f"Saved Scenario2 target summary: {target_summary}")
    print(
        f"cv_terzaghi={CV_TERZAGHI:.6g} m^2/s, cv_pr_diffusion={CV_PR_DIFFUSION:.6g} m^2/s, "
        f"undrained_ratio={UNDRAINED_RATIO:.6g}, effective_ratio={EFFECTIVE_RATIO:.6g}"
    )
    print(
        "Scenario2 analytical initial state: "
        f"{initial_data['name']} t={initial_metrics['time']:.6g}s, "
        f"bottom excess={initial_metrics['bottom_excess_kpa']:.6g} kPa "
        f"(theory {initial_metrics['bottom_excess_theory_kpa']:.6g} kPa), "
        f"bottom total={initial_metrics['bottom_total_kpa']:.6g} kPa "
        f"(theory {initial_metrics['bottom_total_theory_kpa']:.6g} kPa), "
        f"RMS excess={initial_metrics['rms_excess_pa']:.6g} Pa, "
        f"RMS total={initial_metrics['rms_total_pa']:.6g} Pa, "
        f"max speed={initial_metrics['max_speed']:.6g} m/s, "
        f"max Kplastic={initial_metrics['max_kplastic']:.6g}"
    )
    if "bottom_sigma_zz_pa" in initial_metrics:
        print(
            "Scenario2 analytical effective stress: "
            f"bottom sigma_zz={initial_metrics['bottom_sigma_zz_pa']:.6g} Pa "
            f"(theory {initial_metrics['bottom_sigma_zz_theory_pa']:.6g} Pa), "
            f"RMS sigma_zz={initial_metrics['rms_sigma_zz_pa']:.6g} Pa"
        )
    if bottom_rows:
        last = bottom_rows[-1]
        print(
            "Scenario2 final bottom comparison: "
            f"t={last[0]:.6g}s, Tv={last[2]:.6g}, "
            f"SPH={last[3]:.6g} kPa, theory={last[4]:.6g} kPa"
        )
    if target_rows:
        print("Scenario2 target Tv comparisons:")
        for row in target_rows:
            print(
                f"  target Tv={row[0]:.3g}, actual Tv={row[4]:.6g}, {row[1]}, "
                f"bottom SPH={row[5]:.6g} kPa, theory={row[6]:.6g} kPa, "
                f"RMS={row[7]:.6g} Pa, max speed={row[8]:.6g} m/s"
            )


if __name__ == "__main__":
    main()
