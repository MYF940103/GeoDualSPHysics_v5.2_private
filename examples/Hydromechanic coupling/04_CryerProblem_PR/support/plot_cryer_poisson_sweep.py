from pathlib import Path
import csv
import json
import math
import re
import sys
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
FIGDIR = ROOT / "figures"
RHO_W = 1000.0
G_REF = 9.81
NROOTS = 360
TV_MIN = 0.001

GROUPS = [
    {"tag": "nu010", "case": "CaseCryerProblem_PR_nu010", "nu": 0.1},
    {"tag": "nu020", "case": "CaseCryerProblem_PR_nu020", "nu": 0.2},
    {"tag": "nu030", "case": "CaseCryerProblem_PR", "nu": 0.3},
    {"tag": "nu045", "case": "CaseCryerProblem_PR_nu045", "nu": 0.45},
]


def np_dtype(type_name):
    types = {
        "float": np.dtype(">f4"),
        "double": np.dtype(">f8"),
    }
    if type_name not in types:
        raise RuntimeError(f"Unsupported numeric VTK type: {type_name}")
    return types[type_name]


def read_line(data, offset):
    end = data.find(b"\n", offset)
    if end < 0:
        return data[offset:].decode("ascii", errors="ignore").strip(), len(data)
    line = data[offset:end].decode("ascii", errors="ignore").strip()
    return line, end + 1


def parse_xml(case_name):
    root = ET.parse(ROOT / f"{case_name}_Def.xml").getroot()

    def value(name, default=None):
        node = root.find(f".//{name}")
        return float(node.attrib["value"]) if node is not None else default

    def param(key, default=None):
        node = root.find(f".//parameter[@key='{key}']")
        return float(node.attrib["value"]) if node is not None else default

    radius_node = root.find(".//newvarcte[@radius]")
    dp_node = root.find(".//newvarcte[@Dp]")
    return {
        "radius": float(radius_node.attrib["radius"]),
        "dp": float(dp_node.attrib["Dp"]),
        "q0": value("HydroMechTopLoadQ0"),
        "e": value("ModulusE"),
        "nu": value("PRvs"),
        "khyd": value("HydraulicConductivity"),
        "tout": param("TimeOut"),
        "tmax": param("TimeMax"),
    }


def part_index(path):
    match = re.search(r"PartFluid_(\d+)\.vtk$", path.name)
    if not match:
        raise RuntimeError(f"Unexpected particle file name: {path.name}")
    return int(match.group(1))


def read_center_pore(path, center_radius):
    data = path.read_bytes()
    offset = 0
    for _ in range(4):
        _, offset = read_line(data, offset)

    line, offset = read_line(data, offset)
    parts = line.split()
    if len(parts) != 3 or parts[0] != "POINTS":
        raise RuntimeError(f"Unexpected POINTS line in {path}: {line}")

    npoints = int(parts[1])
    dtype = np_dtype(parts[2])
    points = np.frombuffer(data, dtype=dtype, count=npoints * 3, offset=offset)
    points = points.reshape((npoints, 3)).astype(np.float64, copy=False)
    r2 = np.einsum("ij,ij->i", points, points)
    mask = r2 <= (center_radius * center_radius + 1e-18)
    if not np.any(mask):
        mask[np.argmin(r2)] = True

    pattern = rb"(?:^|\n)PorePress\s+1\s+" + str(npoints).encode("ascii") + rb"\s+([A-Za-z_]+)\r?\n"
    match = re.search(pattern, data)
    if not match:
        raise RuntimeError(f"PorePress array not found in {path}")

    pore_dtype = np_dtype(match.group(1).decode("ascii"))
    pore = np.frombuffer(data, dtype=pore_dtype, count=npoints, offset=match.end())
    pore = pore.astype(np.float64, copy=False)

    return {
        "sample_count": int(np.count_nonzero(mask)),
        "sample_radius_mean_m": float(np.sqrt(r2[mask]).mean()),
        "center_pore_pa": float(pore[mask].mean()),
    }


def material_values(meta):
    e = meta["e"]
    nu = meta["nu"]
    kbulk = e / (3.0 * (1.0 - 2.0 * nu))
    gshear = e / (2.0 * (1.0 + nu))
    mconst = kbulk + 4.0 * gshear / 3.0
    cv = meta["khyd"] * mconst / (RHO_W * G_REF)
    eta = (1.0 - nu) / (1.0 - 2.0 * nu)
    return cv, eta


def cryer_roots(eta):
    def f(z):
        return (1.0 - 0.5 * eta * z * z) * math.sin(z) - z * math.cos(z)

    def bisect(a, b):
        fa = f(a)
        for _ in range(80):
            c = 0.5 * (a + b)
            fc = f(c)
            if fa * fc <= 0.0:
                b = c
            else:
                a = c
                fa = fc
        return 0.5 * (a + b)

    roots = []
    k = 0
    while len(roots) < NROOTS:
        a = k * math.pi + 1e-10
        b = (k + 1) * math.pi - 1e-10
        x0 = a
        f0 = f(x0)
        for j in range(1, 65):
            x1 = a + (b - a) * j / 64.0
            f1 = f(x1)
            if f0 * f1 < 0.0:
                roots.append(bisect(x0, x1))
                break
            x0 = x1
            f0 = f1
        k += 1
    return roots


def theory_function(nu):
    eta = (1.0 - nu) / (1.0 - 2.0 * nu)
    roots = cryer_roots(eta)

    def pressure(tv):
        if tv <= 0.0:
            return 1.0
        value = 0.0
        for z in roots:
            den = 0.5 * eta * z * math.cos(z) + (eta - 1.0) * math.sin(z)
            coef = eta * (math.sin(z) - z) / den
            value += coef * math.exp(-z * z * tv)
        return value

    return pressure


def write_csv(path, rows):
    keys = [
        "nu", "time_s", "tv", "center_pore_pa", "center_pore_over_p0",
        "theory_pore_over_p0", "sample_count", "sample_radius_mean_m",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return [{k: float(v) if k != "sample_count" else int(float(v))
                 for k, v in row.items()} for row in csv.DictReader(f)]


def process_group(group, force=False):
    meta = parse_xml(group["case"])
    nu = meta["nu"]
    out_csv = FIGDIR / f"cryer_poisson_{group['tag']}_center_r1dp.csv"
    if out_csv.exists() and not force:
        rows = read_csv(out_csv)
        return meta, rows

    particles = ROOT / f"{group['case']}_out" / "particles"
    files = sorted(particles.glob("PartFluid_*.vtk"))
    if not files:
        raise RuntimeError(f"No PartFluid files found in {particles}")

    cv, _ = material_values(meta)
    theory = theory_function(nu)
    rows = []
    for pos, path in enumerate(files, start=1):
        idx = part_index(path)
        time = min(meta["tmax"], idx * meta["tout"])
        tv = cv * time / (meta["radius"] * meta["radius"])
        if tv + 1e-12 < TV_MIN or tv > 1.0 + 1e-9:
            continue
        stat = read_center_pore(path, meta["dp"])
        rows.append({
            "nu": nu,
            "time_s": time,
            "tv": tv,
            "center_pore_pa": stat["center_pore_pa"],
            "center_pore_over_p0": stat["center_pore_pa"] / meta["q0"],
            "theory_pore_over_p0": theory(tv),
            "sample_count": stat["sample_count"],
            "sample_radius_mean_m": stat["sample_radius_mean_m"],
        })
        if pos % 100 == 0:
            print(f"{group['tag']}: processed {pos}/{len(files)} VTK files", flush=True)

    write_csv(out_csv, rows)
    print(f"{group['tag']}: wrote {out_csv}", flush=True)
    return meta, rows


def metrics_for(rows):
    errors = [r["center_pore_over_p0"] - r["theory_pore_over_p0"] for r in rows]
    peak_num = max(rows, key=lambda r: r["center_pore_over_p0"])
    peak_theory = max(rows, key=lambda r: r["theory_pore_over_p0"])
    return {
        "nu": rows[0]["nu"],
        "points": len(rows),
        "rmse": math.sqrt(sum(e * e for e in errors) / len(errors)),
        "mae": sum(abs(e) for e in errors) / len(errors),
        "peak_num": peak_num["center_pore_over_p0"],
        "peak_num_tv": peak_num["tv"],
        "peak_theory": peak_theory["theory_pore_over_p0"],
        "peak_theory_tv": peak_theory["tv"],
        "num_at_peak_theory_tv": peak_theory["center_pore_over_p0"],
        "final_num": rows[-1]["center_pore_over_p0"],
        "final_theory": rows[-1]["theory_pore_over_p0"],
        "sample_count_min": min(r["sample_count"] for r in rows),
        "sample_count_max": max(r["sample_count"] for r in rows),
    }


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True)
    force = "--force" in sys.argv
    all_rows = []
    group_data = []

    for group in GROUPS:
        meta, rows = process_group(group, force=force)
        all_rows.extend(rows)
        group_data.append((group, meta, rows, metrics_for(rows)))

    combined_csv = FIGDIR / "cryer_poisson_sweep_center_r1dp.csv"
    write_csv(combined_csv, all_rows)

    metrics = [item[3] for item in group_data]
    metrics_json = FIGDIR / "cryer_poisson_sweep_center_r1dp_metrics.json"
    metrics_json.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    plt.rcParams.update({
        "font.size": 11,
        "axes.labelsize": 13,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 10,
    })

    theory_color = "#3445a4"
    sph_color = "#c44e52"
    sph_markers = ["o", "s", "^", "D"]
    fig, ax = plt.subplots(figsize=(7.4, 5.7), dpi=220)

    theory_tvs = np.logspace(math.log10(5e-4), math.log10(5.0), 800)
    ymax = 1.0
    annotation_specs = {
        0.1: {"xy_tv": 0.060, "text": (0.135, 1.43)},
        0.2: {"xy_tv": 0.055, "text": (0.135, 1.31)},
        0.3: {"xy_tv": 0.080, "text": (0.045, 0.70)},
        0.45: {"xy_tv": 0.090, "text": (0.045, 0.56)},
    }

    for i, (group, meta, rows, _) in enumerate(group_data):
        nu = meta["nu"]
        theory = theory_function(nu)
        tv = np.array([r["tv"] for r in rows])
        num = np.array([r["center_pore_over_p0"] for r in rows])
        theory_vals = np.array([theory(float(x)) for x in theory_tvs])
        ymax = max(ymax, float(np.nanmax(num)), float(np.nanmax(theory_vals)))

        ax.plot(theory_tvs, theory_vals, color=theory_color,
                linestyle=(0, (6, 4)), linewidth=1.8,
                label="theoretical solution")
        ax.plot(tv, num, linestyle="none", marker=sph_markers[i], markevery=12,
                markersize=3.7, markerfacecolor="none", markeredgewidth=1.0,
                color=sph_color, label=rf"u-pw-GeoDualSPHysics, $\nu={nu:g}$")

        spec = annotation_specs.get(round(nu, 2))
        if spec:
            xy_tv = spec["xy_tv"]
            ax.annotate(
                rf"$\nu={nu:g}$",
                xy=(xy_tv, theory(xy_tv)),
                xytext=spec["text"],
                textcoords="data",
                fontsize=11,
                arrowprops={
                    "arrowstyle": "->",
                    "linewidth": 1.0,
                    "color": "black",
                    "shrinkA": 2,
                    "shrinkB": 2,
                },
            )

    ax.set_xscale("log")
    ax.set_xlim(5e-4, 5.0)
    ax.set_ylim(0.0, ymax * 1.08)
    ax.set_xlabel(r"$T_v$")
    ax.set_ylabel(r"Normalized pore pressure, $p^w/p_0$")
    ax.grid(True, which="both", alpha=0.25)
    legend_handles = [
        Line2D([0], [0], color=theory_color, linestyle=(0, (6, 4)),
               linewidth=1.8,
               label="theoretical solution"),
        Line2D([0], [0], linestyle="none", linewidth=0,
               label="u-pw-GeoDualSPHysics"),
    ]
    for i, (_, meta, _, _) in enumerate(group_data):
        nu = meta["nu"]
        legend_handles.append(
            Line2D([0], [0], linestyle="none", marker=sph_markers[i],
                   markersize=5.0, markerfacecolor="none", markeredgewidth=1.0,
                   color=sph_color, label=rf"$\nu={nu:g}$")
        )

    ax.legend(
        handles=legend_handles,
        loc="lower left",
        frameon=True,
        fancybox=False,
        edgecolor="0.35",
        framealpha=0.95,
    )
    fig.tight_layout()

    png = FIGDIR / "cryer_poisson_sweep_center_r1dp_paper_axes.png"
    pdf = FIGDIR / "cryer_poisson_sweep_center_r1dp_paper_axes.pdf"
    fig.savefig(png)
    fig.savefig(pdf)
    plt.close(fig)

    print(f"Wrote {combined_csv}")
    print(f"Wrote {metrics_json}")
    print(f"Wrote {png}")
    print(f"Wrote {pdf}")
    for row in metrics:
        print(
            f"nu={row['nu']:.2f}: peak num={row['peak_num']:.6g} "
            f"at Tv={row['peak_num_tv']:.6g}, "
            f"theory peak={row['peak_theory']:.6g} "
            f"at Tv={row['peak_theory_tv']:.6g}, "
            f"RMSE={row['rmse']:.6g}",
            flush=True,
        )


if __name__ == "__main__":
    main()
