from pathlib import Path
import csv
import math
import re
import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt

import postprocess_self_weight_consolidation as pp


ROOT = Path(__file__).resolve().parent.parent
STAGE1_XML = ROOT / "CaseSelfWeightConsolidation_Stage1_Def.xml"
STAGE1 = ROOT / "CaseSelfWeightConsolidation_Stage1_out" / "particles"
FIGDIR = ROOT / "figures"


def undrained_stage1_pore_pressure(z):
    return pp.UNDRAINED_RATIO * pp.RHO_SOIL * pp.G * max(0.0, pp.H - z)


def effective_stage1_sigma_zz(z):
    return -pp.EFFECTIVE_RATIO * pp.RHO_SOIL * pp.G * max(0.0, pp.H - z)


def xml_parameter(path, key, default):
    root = ET.parse(path).getroot()
    for node in root.findall(".//parameter"):
        if node.attrib.get("key") == key:
            return float(node.attrib.get("value"))
    return default


def part_index(path):
    match = re.search(r"PartFluid_(\d+)\.vtk$", path.name)
    if not match:
        raise RuntimeError(f"Unexpected particle file name: {path.name}")
    return int(match.group(1))


def load_stage1(tout):
    data = []
    for path in sorted(STAGE1.glob("PartFluid_*.vtk")):
        idx = part_index(path)
        rows = pp.read_part_vtk(path)
        data.append({"name": path.name, "index": idx, "time": idx * tout, "rows": rows})
    if not data:
        raise RuntimeError(f"No PartFluid VTK files found in {STAGE1}")
    return data


def bottom_average(rows, key):
    return pp.bottom_average(rows, key)


def rms_error(rows, key, theory):
    return pp.rms_error(rows, key, theory)


def stage1_metrics(data):
    rows = data["rows"]
    zvals = [row["z"] for row in rows]
    bottom_excess, bottom_z = bottom_average(rows, "excess")
    bottom_sigma = None
    bottom_sigma_theory = None
    rms_sigma = None
    if any("sigma_zz" in row for row in rows):
        bottom_sigma, bottom_sigma_z = bottom_average(rows, "sigma_zz")
        bottom_sigma_theory = effective_stage1_sigma_zz(bottom_sigma_z)
        rms_sigma = rms_error(rows, "sigma_zz", effective_stage1_sigma_zz)
    return {
        "name": data["name"],
        "index": data["index"],
        "time": data["time"],
        "bottom_z": bottom_z,
        "bottom_excess_kpa": bottom_excess / 1000.0,
        "bottom_excess_theory_kpa": undrained_stage1_pore_pressure(bottom_z) / 1000.0,
        "mean_excess_kpa": sum(row["excess"] for row in rows) / len(rows) / 1000.0,
        "rms_excess_pa": rms_error(rows, "excess", undrained_stage1_pore_pressure),
        "bottom_sigma_zz_pa": bottom_sigma,
        "bottom_sigma_zz_theory_pa": bottom_sigma_theory,
        "rms_sigma_zz_pa": rms_sigma,
        "max_speed": max(row.get("speed", 0.0) for row in rows),
        "max_kplastic": max(row.get("kplastic", 0.0) for row in rows),
        "height_m": max(zvals) - min(zvals),
        "height_change_mm": (max(zvals) - min(zvals) - (pp.H - pp.DP)) * 1000.0,
        "mean_z_m": sum(zvals) / len(zvals),
    }


def main():
    tout = xml_parameter(STAGE1_XML, "TimeOut", 0.001)
    damping = xml_parameter(STAGE1_XML, "SoilDampingCoef", 0.0)
    data = load_stage1(tout)
    metrics = [stage1_metrics(item) for item in data]
    best = min(metrics, key=lambda row: row["rms_excess_pa"])

    FIGDIR.mkdir(exist_ok=True)
    csvpath = FIGDIR / "self_weight_stage1_metrics.csv"
    with csvpath.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(metrics[0].keys()))
        writer.writeheader()
        writer.writerows(metrics)

    times = [row["time"] for row in metrics]
    th_bottom = undrained_stage1_pore_pressure(pp.DP / 2.0) / 1000.0
    fig, axes = plt.subplots(4, 1, figsize=(8.6, 9.5), sharex=True, constrained_layout=True)
    axes[0].plot(times, [row["bottom_excess_kpa"] for row in metrics], "-", linewidth=1.4, label="SPH bottom excess")
    axes[0].axhline(th_bottom, color="k", linestyle="--", linewidth=1.1, label="undrained theory")
    axes[0].set_ylabel("Bottom excess [kPa]")
    axes[0].legend(fontsize=8)
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(times, [row["mean_excess_kpa"] for row in metrics], "-", color="tab:orange", linewidth=1.4)
    axes[1].set_ylabel("Mean excess [kPa]")
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(times, [row["height_change_mm"] for row in metrics], "-", color="tab:green", linewidth=1.4)
    axes[2].set_ylabel("Height change [mm]")
    axes[2].grid(True, alpha=0.25)

    axes[3].plot(times, [row["max_speed"] for row in metrics], "-", color="tab:red", linewidth=1.4)
    axes[3].set_ylabel("Max speed [m/s]")
    axes[3].set_xlabel("Stage 1 time [s]")
    axes[3].grid(True, alpha=0.25)

    fig.suptitle(f"Stage 1 undrained history, SoilDampingCoef={damping:g}, TimeOut={tout:g}s")
    figpath = FIGDIR / "self_weight_stage1_history.png"
    fig.savefig(figpath, dpi=220)

    best_data = next(item for item in data if item["name"] == best["name"])
    final_data = data[-1]
    zgrid = [i / 200.0 * pp.H for i in range(201)]
    fig_prof, ax_prof = plt.subplots(figsize=(6.4, 5.2), constrained_layout=True)
    ax_prof.plot(
        [undrained_stage1_pore_pressure(z) / 1000.0 for z in zgrid],
        [z / pp.H for z in zgrid],
        "k--",
        linewidth=1.5,
        label="undrained theory",
    )
    for label, item in (("best", best_data), ("final", final_data)):
        prof = pp.layer_average(item["rows"], "excess")
        ax_prof.plot(
            [value / 1000.0 for _, value in prof],
            [z / pp.H for z, _ in prof],
            linewidth=1.4,
            label=f"{label} {item['name']} t={item['time']:.3f}s",
        )
    ax_prof.set_xlabel("Excess pore pressure [kPa]")
    ax_prof.set_ylabel("z/H")
    ax_prof.set_title("Stage 1 undrained pore-pressure profile")
    ax_prof.grid(True, alpha=0.25)
    ax_prof.legend(fontsize=8)
    profpath = FIGDIR / "self_weight_stage1_profiles.png"
    fig_prof.savefig(profpath, dpi=220)

    print(f"Saved Stage1 history: {figpath}")
    print(f"Saved Stage1 profiles: {profpath}")
    print(f"Saved Stage1 metrics: {csvpath}")
    print(
        "Best Stage1 by excess-profile RMS: "
        f"{best['name']} t={best['time']:.6g}s, "
        f"bottom excess={best['bottom_excess_kpa']:.6g} kPa "
        f"(theory {best['bottom_excess_theory_kpa']:.6g} kPa), "
        f"RMS excess={best['rms_excess_pa']:.6g} Pa, "
        f"max speed={best['max_speed']:.6g} m/s"
    )
    print(
        "Final Stage1: "
        f"{metrics[-1]['name']} t={metrics[-1]['time']:.6g}s, "
        f"bottom excess={metrics[-1]['bottom_excess_kpa']:.6g} kPa, "
        f"RMS excess={metrics[-1]['rms_excess_pa']:.6g} Pa, "
        f"max speed={metrics[-1]['max_speed']:.6g} m/s"
    )


if __name__ == "__main__":
    main()
