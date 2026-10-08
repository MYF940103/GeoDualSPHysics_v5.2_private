from pathlib import Path
import argparse
import csv
import math
import sys
import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt


CASE_ROOT = Path(__file__).resolve().parents[2]
ROOT_SUPPORT = CASE_ROOT / "support"
if str(ROOT_SUPPORT) not in sys.path:
    sys.path.insert(0, str(ROOT_SUPPORT))

import postprocess_self_weight_consolidation as pp


def xml_parameter(path, key, default):
    root = ET.parse(path).getroot()
    for node in root.findall(".//parameter"):
        if node.attrib.get("key") == key:
            return float(node.attrib.get("value"))
    return default


def xml_hydro_value(path, key, default):
    root = ET.parse(path).getroot()
    node = root.find(f".//hydromechanics/{key}")
    if node is None:
        return default
    return node.attrib.get("value", default)


def part_index(path):
    stem = path.stem
    return int(stem.rsplit("_", 1)[1])


def undrained_stage1_pore_pressure(z):
    return pp.UNDRAINED_RATIO * pp.RHO_SOIL * pp.G * max(0.0, pp.H - z)


def effective_stage1_sigma_zz(z):
    return -pp.EFFECTIVE_RATIO * pp.RHO_SOIL * pp.G * max(0.0, pp.H - z)


def high_frequency_rms(profile, theory):
    residuals = [value - theory(z) for z, value in profile]
    if len(residuals) < 3:
        return float("nan")
    alt = [residuals[i] - 0.5 * (residuals[i - 1] + residuals[i + 1]) for i in range(1, len(residuals) - 1)]
    return math.sqrt(sum(v * v for v in alt) / len(alt))


def load_series(particles, tout):
    series = []
    for path in sorted(particles.glob("PartFluid_*.vtk")):
        idx = part_index(path)
        series.append({
            "name": path.name,
            "index": idx,
            "time_s": idx * tout,
            "rows": pp.read_part_vtk(path),
        })
    if not series:
        raise RuntimeError(f"No PartFluid VTK files found in {particles}")
    return series


def stage_metrics(item):
    rows = item["rows"]
    pore_profile = pp.layer_average(rows, "pore")
    bottom_pore, bottom_z = pp.bottom_average(rows, "pore")
    bottom_excess, _ = pp.bottom_average(rows, "excess")
    bottom_sigma = float("nan")
    bottom_sigma_theory = float("nan")
    rms_sigma = float("nan")
    if any("sigma_zz" in row for row in rows):
        bottom_sigma, bottom_sigma_z = pp.bottom_average(rows, "sigma_zz")
        bottom_sigma_theory = effective_stage1_sigma_zz(bottom_sigma_z)
        rms_sigma = pp.rms_error(rows, "sigma_zz", effective_stage1_sigma_zz)
    return {
        "part": item["index"],
        "time_s": item["time_s"],
        "bottom_z_m": bottom_z,
        "bottom_pore_kpa": bottom_pore / 1000.0,
        "bottom_pore_theory_kpa": undrained_stage1_pore_pressure(bottom_z) / 1000.0,
        "bottom_excess_kpa": bottom_excess / 1000.0,
        "rms_pore_pa": pp.rms_error(rows, "pore", undrained_stage1_pore_pressure),
        "hf_pore_rms_pa": high_frequency_rms(pore_profile, undrained_stage1_pore_pressure),
        "bottom_sigma_zz_pa": bottom_sigma,
        "bottom_sigma_zz_theory_pa": bottom_sigma_theory,
        "rms_sigma_zz_pa": rms_sigma,
        "max_speed_mps": max(row.get("speed", 0.0) for row in rows),
        "max_kplastic": max(row.get("kplastic", 0.0) for row in rows),
    }


def save_profile_csv(path, rows):
    profile = pp.layer_average(rows, "pore")
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["z_m", "z_over_H", "pore_kpa", "pore_theory_kpa", "residual_kpa"])
        for z, value in profile:
            theory = undrained_stage1_pore_pressure(z)
            writer.writerow([z, z / pp.H, value / 1000.0, theory / 1000.0, (value - theory) / 1000.0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--particles", required=True)
    parser.add_argument("--xml", required=True)
    parser.add_argument("--figdir", required=True)
    parser.add_argument("--case", required=True)
    args = parser.parse_args()

    particles = Path(args.particles)
    xmlpath = Path(args.xml)
    figdir = Path(args.figdir)
    figdir.mkdir(parents=True, exist_ok=True)

    tout = xml_parameter(xmlpath, "TimeOut", 0.005)
    damping = xml_parameter(xmlpath, "SoilDampingCoef", float("nan"))
    shepard = xml_hydro_value(xmlpath, "PoreShepardRegularization", "unset")
    drainage = xml_hydro_value(xmlpath, "HydroMechDrainage", "unset")
    series = load_series(particles, tout)
    metrics = [stage_metrics(item) for item in series]
    final = series[-1]
    final_metrics = metrics[-1]

    metrics_csv = figdir / f"{args.case}_stage1_metrics.csv"
    with metrics_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(metrics[0].keys()))
        writer.writeheader()
        writer.writerows(metrics)

    profile_csv = figdir / f"{args.case}_final_profile.csv"
    save_profile_csv(profile_csv, final["rows"])

    times = [row["time_s"] for row in metrics]
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.0), constrained_layout=True)
    ax = axes[0, 0]
    ax.plot(times, [row["bottom_pore_kpa"] for row in metrics], lw=1.6, label="SPH bottom pore")
    ax.plot(times, [row["bottom_pore_theory_kpa"] for row in metrics], "k--", lw=1.0, label="undrained theory")
    ax.set_xlabel("time [s]")
    ax.set_ylabel("bottom pore pressure [kPa]")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    ax.plot(times, [row["rms_pore_pa"] / 1000.0 for row in metrics], lw=1.4, label="profile RMS")
    ax.plot(times, [row["hf_pore_rms_pa"] / 1000.0 for row in metrics], lw=1.4, label="HF RMS")
    ax.set_xlabel("time [s]")
    ax.set_ylabel("pore pressure error [kPa]")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    ax.semilogy(times, [max(row["max_speed_mps"], 1e-12) for row in metrics], lw=1.4)
    ax.set_xlabel("time [s]")
    ax.set_ylabel("max speed [m/s]")
    ax.grid(True, alpha=0.25, which="both")

    ax = axes[1, 1]
    profile = pp.layer_average(final["rows"], "pore")
    zvals = [z for z, _ in profile]
    ax.plot([v / 1000.0 for _, v in profile], [z / pp.H for z, _ in profile], lw=1.8, label="SPH final")
    ax.plot([undrained_stage1_pore_pressure(z) / 1000.0 for z in zvals], [z / pp.H for z in zvals], "k--", lw=1.2, label="undrained theory")
    ax.set_xlabel("pore pressure [kPa]")
    ax.set_ylabel("z/H")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    fig.suptitle(f"{args.case}: drainage={drainage}, Shepard={shepard}, SoilDampingCoef={damping:g}")
    figpath = figdir / f"{args.case}_stage1_diagnostics.png"
    fig.savefig(figpath, dpi=180)
    plt.close(fig)

    summary = figdir / f"{args.case}_summary.txt"
    summary.write_text(
        "\n".join([
            f"case={args.case}",
            f"outputs={particles}",
            f"xml={xmlpath}",
            f"n_outputs={len(series)}",
            f"final_time_s={final_metrics['time_s']:.9g}",
            f"bottom_pore_kpa={final_metrics['bottom_pore_kpa']:.9g}",
            f"bottom_pore_theory_kpa={final_metrics['bottom_pore_theory_kpa']:.9g}",
            f"rms_pore_kpa={final_metrics['rms_pore_pa']/1000.0:.9g}",
            f"hf_pore_rms_kpa={final_metrics['hf_pore_rms_pa']/1000.0:.9g}",
            f"max_speed_mps={final_metrics['max_speed_mps']:.9g}",
            f"max_kplastic={final_metrics['max_kplastic']:.9g}",
        ]),
        encoding="utf-8",
    )

    print(f"Saved metrics: {metrics_csv}")
    print(f"Saved final profile: {profile_csv}")
    print(f"Saved diagnostics: {figpath}")
    print(f"Saved summary: {summary}")
    print(
        "Final Stage1 metrics: "
        f"t={final_metrics['time_s']:.6g}s, "
        f"bottom={final_metrics['bottom_pore_kpa']:.6g} kPa, "
        f"theory={final_metrics['bottom_pore_theory_kpa']:.6g} kPa, "
        f"RMS={final_metrics['rms_pore_pa']/1000.0:.6g} kPa, "
        f"HF={final_metrics['hf_pore_rms_pa']/1000.0:.6g} kPa, "
        f"max_speed={final_metrics['max_speed_mps']:.6g} m/s"
    )


if __name__ == "__main__":
    main()
