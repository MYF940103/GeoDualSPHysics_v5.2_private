from pathlib import Path
import argparse
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import importlib

ROOT = Path(__file__).resolve().parent
REFINEMENT = ROOT.parent
CASE_ROOT = REFINEMENT.parent
REPO_ROOT = ROOT.parents[4]
BIN = REPO_ROOT / "bin" / "windows"
SUPPORT = CASE_ROOT / "support"
FIGURES = CASE_ROOT / "figures"
sys.path.insert(0, str(SUPPORT))

os.environ.setdefault("CRYER_DP", "0.003")
os.environ.setdefault("CRYER_Q0", "10000")
os.environ.setdefault("CRYER_K_HYD", "1e-4")

import postprocess_cryer as cryer

TEMPLATE = REFINEMENT / "r010_drain0_full_20260620" / "Case_r010_drain0_full_Def.xml"
GENCASE = BIN / "GenCase_win64.exe"
DUALSPH = BIN / "DualSPHysics5.2_GEO_win64.exe"
PARTVTK = BIN / "PartVTK_win64.exe"

Q0 = 10000.0
RADIUS = 0.05
VARS = "+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace"


def set_xml_value(root, tag, value):
    node = root.find(f".//{tag}")
    if node is None:
        raise RuntimeError(f"Missing XML node {tag}")
    node.set("value", str(value))


def set_parameter(root, key, value):
    for node in root.findall(".//parameter"):
        if node.get("key") == key:
            node.set("value", str(value))
            return
    raise RuntimeError(f"Missing parameter {key}")


def write_case_xml(folder, case_name, ramp, drainage_start, tmax, tout, khyd):
    tree = ET.parse(TEMPLATE)
    root = tree.getroot()
    set_xml_value(root, "HydroMechTopLoadRampTime", ramp)
    set_xml_value(root, "HydroMechDrainage", 1)
    set_xml_value(root, "HydroMechDrainageStartTime", drainage_start)
    set_xml_value(root, "HydraulicConductivity", khyd)
    set_parameter(root, "TimeMax", tmax)
    set_parameter(root, "TimeOut", tout)
    xml = folder / f"{case_name}_Def.xml"
    tree.write(xml, encoding="UTF-8", xml_declaration=True)
    return xml


def run_command(cmd, cwd, log_path):
    start = time.time()
    with log_path.open("w", encoding="utf-8", errors="ignore") as log:
        log.write("COMMAND: " + " ".join(str(x) for x in cmd) + "\n\n")
        log.flush()
        result = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, text=True)
    if result.returncode:
        raise RuntimeError(f"Command failed with code {result.returncode}: {' '.join(str(x) for x in cmd)}")
    return time.time() - start


def read_part_times(runout):
    times = {0: 0.0}
    pattern = re.compile(r"^Part_(\d+)\s+([0-9.Ee+-]+)\s+\d+")
    for line in runout.read_text(errors="ignore").splitlines():
        match = pattern.match(line.strip())
        if match:
            times[int(match.group(1))] = float(match.group(2))
    return times


def mean(values):
    return sum(values) / len(values) if values else 0.0


def std(values):
    if not values:
        return 0.0
    mu = mean(values)
    return math.sqrt(sum((value - mu) ** 2 for value in values) / len(values))


def global_stats(rows):
    pore = [row["pore"] / Q0 for row in rows]
    return {
        "all_mean": mean(pore),
        "all_std": std(pore),
        "all_min": min(pore),
        "all_max": max(pore),
    }


def analyze(folder, case_name, ramp, drainage_start, origin):
    times = read_part_times(folder / "out" / "Run.out")
    particles = folder / "out" / "particles"
    series = []
    for path in sorted(particles.glob("PartFluid_*.vtk")):
        idx = cryer.part_index(path)
        if idx not in times:
            continue
        rows = cryer.read_part_vtk(path)
        cstat = cryer.center_stats(rows)
        gstat = global_stats(rows)
        t = times[idx]
        tv = cryer.CV * max(0.0, t - origin) / (RADIUS * RADIUS)
        theory = cryer.cryer_center_pressure(tv)
        num = cstat["pore"] / Q0
        series.append({
            "part": idx,
            "time": t,
            "time_after_origin": max(0.0, t - origin),
            "tv": tv,
            "num": num,
            "theory": theory,
            "signed_error": num - theory,
            "abs_error": abs(num - theory),
            "center_pore_pa": cstat["pore"],
            "center_excess_pa": cstat["excess"],
            "sample_count": cstat["count"],
            "free_surface_count": cstat["free_surface_count"],
            "max_speed": cstat["max_speed"],
            **gstat,
        })
    if not series:
        raise RuntimeError(f"No VTK snapshots found in {particles}")

    def is_post_origin(row):
        if origin <= 1e-12:
            return row["time"] > 1e-12
        return row["time"] + 1e-12 >= origin

    post = [row for row in series if is_post_origin(row)]
    peak_num = max(post, key=lambda row: row["num"])
    peak_theory = max(post, key=lambda row: row["theory"])
    max_abs = max(post, key=lambda row: row["abs_error"])
    final = post[-1]
    origin_candidates = post if post else series
    origin_row = min(origin_candidates, key=lambda row: abs(row["time"] - origin))
    summary = {
        "case": case_name,
        "ramp": ramp,
        "drainage_start": drainage_start,
        "theory_origin": origin,
        "target_tv": final["tv"],
        "snapshots": len(series),
        "post_origin_snapshots": len(post),
        "origin_sample_time": origin_row["time"],
        "origin_center": origin_row["num"],
        "origin_theory": origin_row["theory"],
        "origin_abs_error": origin_row["abs_error"],
        "origin_max_speed": origin_row["max_speed"],
        "peak_num": peak_num["num"],
        "peak_num_time": peak_num["time"],
        "peak_num_tv": peak_num["tv"],
        "theory_at_peak_num": peak_num["theory"],
        "peak_num_abs_error": peak_num["abs_error"],
        "peak_theory": peak_theory["theory"],
        "peak_theory_time": peak_theory["time"],
        "peak_theory_tv": peak_theory["tv"],
        "num_at_peak_theory": peak_theory["num"],
        "max_abs_error": max_abs["abs_error"],
        "max_abs_error_time": max_abs["time"],
        "max_abs_error_tv": max_abs["tv"],
        "rmse": math.sqrt(mean([row["signed_error"] ** 2 for row in post])),
        "mae": mean([row["abs_error"] for row in post]),
        "final_num": final["num"],
        "final_theory": final["theory"],
        "final_abs_error": final["abs_error"],
        "max_speed": max(row["max_speed"] for row in post),
        "final_max_speed": final["max_speed"],
        "max_global_std": max(row["all_std"] for row in post),
        "final_global_std": final["all_std"],
        "min_pore": min(row["all_min"] for row in post),
        "max_pore": max(row["all_max"] for row in post),
    }

    analysis = folder / "analysis"
    with (analysis / f"{case_name}_history.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(series[0].keys()))
        writer.writeheader()
        writer.writerows(series)
    (analysis / f"{case_name}_summary.json").write_text(json.dumps(summary, indent=2))
    return series, summary


def plot(folder, case_name, series, summary, save_figure):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    origin = summary["theory_origin"]
    if origin <= 1e-12:
        post = [row for row in series if row["time"] > 1e-12]
    else:
        post = [row for row in series if row["time"] + 1e-12 >= origin]
    plot_tv = [max(row["tv"], 1.0e-4) for row in post]
    tv_grid = [10.0 ** (-4.0 + 5.0 * i / 800.0) for i in range(801)]

    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    axes[0].plot(plot_tv, [row["num"] for row in post], "o-", ms=3, lw=1.0, label=case_name)
    axes[0].plot(tv_grid, [cryer.cryer_center_pressure(x) for x in tv_grid], "r--", lw=1.4, label="theoretical solution")
    axes[0].axhline(1.0, color="0.45", lw=1, ls=":")
    axes[0].set_xscale("log")
    axes[0].set_xlim(1.0e-4, 1.0e1)
    axes[0].set_ylim(0.0, 1.5)
    axes[0].set_ylabel(r"Normalized pore pressure, $p^w/p_0$")
    axes[0].grid(True, which="both", alpha=0.25)
    axes[0].legend(loc="best")

    axes[1].plot(plot_tv, [row["signed_error"] for row in post], "C3o-", ms=3, lw=1.0)
    axes[1].axhline(0.0, color="0.35", ls=":", lw=1)
    axes[1].set_ylabel("SPH - analytical")
    axes[1].grid(True, which="both", alpha=0.25)

    axes[2].plot(plot_tv, [row["max_speed"] for row in post], "C2-", lw=1.0, label="max speed")
    axes[2].plot(plot_tv, [row["all_std"] for row in post], "C1-", lw=1.0, label="global std(PorePress/q0)")
    axes[2].set_xlabel(r"$T_v$")
    axes[2].set_ylabel("stability")
    axes[2].grid(True, which="both", alpha=0.25)
    axes[2].legend(loc="best")

    fig.suptitle(
        f"{case_name}: RMSE={summary['rmse']:.4g}, peak={summary['peak_num']:.4g}, max speed={summary['max_speed']:.4g}",
        y=0.995,
    )
    fig.tight_layout()
    local = folder / "analysis" / f"{case_name}_paper_axes.png"
    fig.savefig(local, dpi=180)
    figure = None
    if save_figure:
        FIGURES.mkdir(parents=True, exist_ok=True)
        figure = FIGURES / f"cryer_{case_name}_paper_axes.png"
        fig.savefig(figure, dpi=180)
    plt.close(fig)
    return local, figure


def main():
    global cryer
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--ramp", type=float, required=True)
    parser.add_argument("--drainage-start", type=float, required=True)
    parser.add_argument("--origin", type=float, default=None)
    parser.add_argument("--khyd", type=float, default=float(os.environ.get("CRYER_K_HYD", "1e-4")))
    parser.add_argument("--tvmax", type=float, default=0.1)
    parser.add_argument("--tout", type=float, default=0.001)
    parser.add_argument("--tout-tv", type=float, default=None)
    parser.add_argument("--keep-existing", action="store_true")
    parser.add_argument("--save-figure", action="store_true")
    args = parser.parse_args()

    khyd = f"{args.khyd:.17g}"
    os.environ["CRYER_K_HYD"] = khyd
    cryer = importlib.reload(cryer)

    origin = args.origin
    if origin is None:
        origin = max(args.ramp, args.drainage_start)
    tout = args.tout
    if args.tout_tv is not None:
        tout = args.tout_tv * RADIUS * RADIUS / cryer.CV
    tmax = origin + args.tvmax * RADIUS * RADIUS / cryer.CV

    folder = ROOT / args.name
    if folder.exists() and not args.keep_existing:
        shutil.rmtree(folder)
    (folder / "out").mkdir(parents=True, exist_ok=True)
    (folder / "analysis").mkdir(parents=True, exist_ok=True)

    xml = write_case_xml(folder, args.name, args.ramp, args.drainage_start, tmax, tout, khyd)
    casebase = folder / "out" / args.name
    data = folder / "out" / "data"
    particles = folder / "out" / "particles"
    particles.mkdir(exist_ok=True)

    run_command([GENCASE, xml.stem, casebase, "-save:all"], folder, folder / "run_gencase.log")
    run_command([
        DUALSPH, "-gpu", casebase, folder / "out",
        "-dirdataout", "data", "-svres", "-svextraparts:1",
        f"-tmax:{tmax}", f"-tout:{tout}",
    ], folder, folder / "run_solver.log")
    run_command([
        PARTVTK, "-dirin", data, "-savevtk", particles / "PartFluid",
        "-onlytype:-bound", f"-vars:{VARS}",
    ], folder, folder / "run_partvtk.log")

    series, summary = analyze(folder, args.name, args.ramp, args.drainage_start, origin)
    local_plot, figure_plot = plot(folder, args.name, series, summary, args.save_figure)

    print(json.dumps(summary, indent=2))
    print(f"Saved {local_plot}")
    if figure_plot:
        print(f"Saved {figure_plot}")


if __name__ == "__main__":
    main()
