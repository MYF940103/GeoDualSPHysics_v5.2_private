from pathlib import Path
import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parents[2]
BIN = REPO / "bin" / "windows"
BASE_XML = ROOT / "CaseCryerProblem_PR_Def.xml"
CASE = "CaseCryerProblem_PR"
RUNROOT = ROOT / "refinement" / "k1e5_convergence_20260622"
FIGDIR = ROOT / "figures"

GENCASE = BIN / "GenCase_win64.exe"
DUAL_GPU_RELEASE = BIN / "DualSPHysics5.2_GEO_win64.exe"
PARTVTK = BIN / "PartVTK_win64.exe"

RADIUS = 0.05
Q0 = 10000.0
E = 2.0e6
NU = 0.3
K_HYD = 1.0e-5
DT_FIXED = 5.0e-6
FULL_DP = 0.0025
RHO_W = 1000.0
G_REF = 9.81
K_BULK = E / (3.0 * (1.0 - 2.0 * NU))
G_SHEAR = E / (2.0 * (1.0 + NU))
M_CONSTRAINED = K_BULK + 4.0 * G_SHEAR / 3.0
CV = K_HYD * M_CONSTRAINED / (RHO_W * G_REF)
TV1_TIME = RADIUS * RADIUS / CV
ETA = (1.0 - NU) / (1.0 - 2.0 * NU)

PARTVTK_VARS = (
    "+idp,+mk,+vel,+rhop,+press,+fstype,+fsnormal,"
    "+porepress,+porepress0,+excessporepress,+hydromechloadace"
)


def set_value(root, xpath, value):
    node = root.find(xpath)
    if node is None:
        raise RuntimeError(f"XML node not found: {xpath}")
    node.set("value", str(value))


def set_hydro_value(root, name, value, comment=None):
    hydro = root.find(".//hydromechanics")
    if hydro is None:
        raise RuntimeError("XML hydromechanics node not found")
    node = hydro.find(name)
    if node is None:
        node = ET.SubElement(hydro, name)
    node.set("value", str(value))
    if comment is not None:
        node.set("comment", comment)


def set_newvar_dp(root, dp):
    for node in root.findall(".//newvarcte"):
        if "Dp" in node.attrib or node.get("name") == "Dp":
            if "Dp" in node.attrib:
                node.set("Dp", str(dp))
            else:
                node.set("value", str(dp))
            return
    raise RuntimeError("newvarcte Dp not found")


def set_parameter(root, key, value):
    node = root.find(f".//parameter[@key='{key}']")
    if node is None:
        raise RuntimeError(f"parameter not found: {key}")
    node.set("value", str(value))


def write_xml(path, cfg):
    tree = ET.parse(BASE_XML)
    root = tree.getroot()
    set_newvar_dp(root, cfg["dp"])
    set_hydro_value(root, "HydraulicConductivity", K_HYD, "One-stage drained convergence test: drainage is active from t=0")
    set_hydro_value(root, "HydroMechInitMode", 0)
    set_hydro_value(root, "HydroMechTopLoadMode", 2)
    set_hydro_value(root, "HydroMechTopLoadRampTime", 0.0, "No ramp for the k=1e-5 convergence test")
    set_hydro_value(root, "HydroMechDrainage", 1, "Drainage is active from the start of the calculation")
    set_hydro_value(root, "HydroMechDrainageStartTime", 0.0, "Drainage starts at t=0")
    set_hydro_value(root, "PoreShepardRegularization", 0)
    set_parameter(root, "SoilDampingCoef", 0.02)
    set_parameter(root, "Visco", 0.1)
    set_parameter(root, "ShiftTFS", 2.75)
    set_parameter(root, "DtIni", DT_FIXED)
    set_parameter(root, "DtFixed", DT_FIXED)
    set_parameter(root, "DtMin", 1.0e-8)
    set_parameter(root, "TimeMax", cfg["time_max"])
    set_parameter(root, "TimeOut", cfg["tout"])
    tree.write(path, encoding="UTF-8", xml_declaration=True)


def run_command(args, cwd, log_path, timeout):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write(" ".join(str(a) for a in args) + "\n\n")
        log.flush()
        proc = subprocess.Popen(args, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT)
        start = time.time()
        while proc.poll() is None:
            if time.time() - start > timeout:
                proc.kill()
                raise RuntimeError(f"Timed out after {timeout}s: {' '.join(str(a) for a in args)}")
            time.sleep(1.0)
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"Command failed with code {code}: {' '.join(str(a) for a in args)}")


def postprocess(work, cfg):
    particles = work / "out" / "particles"
    analysis = work / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    summary = analysis / f"{cfg['name']}_summary.json"
    env = os.environ.copy()
    env.update({
        "CRYER_PARTICLES": str(particles),
        "CRYER_FIGDIR": str(analysis),
        "CRYER_OUTTAG": cfg["name"],
        "CRYER_SUMMARY_JSON": str(summary),
        "CRYER_RADIUS": str(RADIUS),
        "CRYER_DP": str(cfg["dp"]),
        "CRYER_Q0": str(Q0),
        "CRYER_TL": "0",
        "CRYER_LOAD_RAMP": "0",
        "CRYER_E": str(E),
        "CRYER_NU": str(NU),
        "CRYER_K_HYD": str(K_HYD),
        "CRYER_TOUT": str(cfg["tout"]),
        "CRYER_TIME_MAX": str(cfg["time_max"]),
    })
    log = work / "logs" / "postprocess.log"
    with log.open("w", encoding="utf-8", errors="replace") as f:
        code = subprocess.call([sys.executable, str(ROOT / "support" / "postprocess_cryer.py")], cwd=str(work), env=env, stdout=f, stderr=subprocess.STDOUT)
    if code != 0:
        raise RuntimeError(f"Postprocess failed for {cfg['name']}")
    return json.loads(summary.read_text()), analysis / f"{cfg['name']}.csv"


def run_case(cfg, overwrite=False):
    work = RUNROOT / cfg["name"]
    history = work / "analysis" / f"{cfg['name']}.csv"
    summary = work / "analysis" / f"{cfg['name']}_summary.json"
    if history.exists() and summary.exists() and not overwrite:
        print(f"[reuse] {cfg['name']}", flush=True)
        data = json.loads(summary.read_text())
        data.update(cfg)
        data["workdir"] = str(work)
        data["history_csv"] = str(history)
        return data
    if work.exists():
        shutil.rmtree(work)
    (work / "logs").mkdir(parents=True)
    xml = work / f"{CASE}_Def.xml"
    write_xml(xml, cfg)

    print(f"[gencase] {cfg['name']}", flush=True)
    run_command([GENCASE, f"{CASE}_Def", f"out/{CASE}", "-save:all"], work, work / "logs" / "gencase.log", 600)

    print(f"[solver] {cfg['name']} dp={cfg['dp']} TvMax={cfg['tv_max']} dTv={cfg['tv_out']}", flush=True)
    run_command([
        DUAL_GPU_RELEASE, "-gpu", f"out/{CASE}", "out", "-dirdataout", "data", "-svres", "-svextraparts:1",
        f"-tmax:{cfg['time_max']}", f"-tout:{cfg['tout']}"
    ], work, work / "logs" / "solver.log", cfg.get("solver_timeout", 72000))

    print(f"[partvtk] {cfg['name']}", flush=True)
    run_command([
        PARTVTK, "-dirin", "out/data", "-savevtk", "out/particles/PartFluid",
        "-onlytype:-bound", f"-vars:{PARTVTK_VARS}"
    ], work, work / "logs" / "partvtk.log", 7200)

    print(f"[postprocess] {cfg['name']}", flush=True)
    data, csv_path = postprocess(work, cfg)
    data.update(cfg)
    data["workdir"] = str(work)
    data["history_csv"] = str(csv_path)
    return data


def cryer_root_function(z):
    return (1.0 - 0.5 * ETA * z * z) * math.sin(z) - z * math.cos(z)


def bisection_root(a, b):
    fa = cryer_root_function(a)
    fb = cryer_root_function(b)
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


def cryer_roots(nroots=360):
    roots = []
    k = 0
    while len(roots) < nroots:
        a = k * math.pi + 1e-10
        b = (k + 1) * math.pi - 1e-10
        x0 = a
        f0 = cryer_root_function(x0)
        for j in range(1, 65):
            x1 = a + (b - a) * j / 64.0
            f1 = cryer_root_function(x1)
            if f0 * f1 < 0.0:
                roots.append(bisection_root(x0, x1))
                break
            x0 = x1
            f0 = f1
        k += 1
    return roots


ROOTS = cryer_roots()


def cryer_center_pressure(tv):
    if tv <= 0.0:
        return 1.0
    value = 0.0
    for z in ROOTS:
        den = 0.5 * ETA * z * math.cos(z) + (ETA - 1.0) * math.sin(z)
        value += ETA * (math.sin(z) - z) / den * math.exp(-z * z * tv)
    return value


def read_history(path):
    rows = []
    with Path(path).open(newline="") as f:
        for row in csv.DictReader(f):
            tv = float(row["tv_after_load"])
            rows.append({
                "time": float(row["time_s"]),
                "tv": tv,
                "num": float(row["center_pore_over_q0"]),
                "theory": float(row["theory_pore_over_q0"]) if row["theory_pore_over_q0"] else cryer_center_pressure(tv),
                "speed": float(row["max_speed_m_per_s"]),
                "sample_count": int(float(row["sample_count"])),
            })
    return rows


def metrics_from_rows(rows, tv_limit):
    window = [r for r in rows if r["tv"] <= tv_limit + 1e-12 and r["tv"] > 0]
    if not window:
        raise RuntimeError("No data in requested Tv window")
    peak_num = max(window, key=lambda r: r["num"])
    peak_theory = max(window, key=lambda r: r["theory"])
    rmse = math.sqrt(sum((r["num"] - r["theory"]) ** 2 for r in window) / len(window))
    mae = sum(abs(r["num"] - r["theory"]) for r in window) / len(window)
    return {
        "points": len(window),
        "rmse": rmse,
        "mae": mae,
        "peak_num": peak_num["num"],
        "peak_num_tv": peak_num["tv"],
        "theory_at_peak_num_tv": peak_num["theory"],
        "peak_theory": peak_theory["theory"],
        "peak_theory_tv": peak_theory["tv"],
        "num_at_peak_theory_tv": peak_theory["num"],
        "peak_deficit_at_theory_tv": peak_theory["num"] - peak_theory["theory"],
        "max_speed": max(r["speed"] for r in window),
        "min_sample_count": min(r["sample_count"] for r in window),
        "final_tv": window[-1]["tv"],
        "final_num": window[-1]["num"],
        "final_theory": window[-1]["theory"],
    }


def write_csv(path, rows, keys):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in keys})


def plot_peak(cases):
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=220)
    tv_grid = [10 ** (-4 + (math.log10(0.12) + 4) * i / 600) for i in range(601)]
    ax.plot(tv_grid, [cryer_center_pressure(tv) for tv in tv_grid], "k-", lw=1.4, label="Cryer analytical")
    for cfg, rows in cases:
        window = [r for r in rows if 0 < r["tv"] <= 0.1 + 1e-12]
        ax.plot([r["tv"] for r in window], [r["num"] for r in window], "o-", ms=2.5, lw=1.0, label=f"dp={cfg['dp']:.4f}")
    ax.set_xscale("log")
    ax.set_xlim(1e-4, 0.12)
    ax.set_ylim(0.8, 1.32)
    ax.set_xlabel(r"$T_v$")
    ax.set_ylabel(r"$p^w(0,t)/p_0$")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    path = FIGDIR / "cryer_k1e5_dp_convergence_20260622_peak_window.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_peak_error_trend(metrics):
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.8), dpi=220)
    xs = [row["dp"] for row in metrics]
    axes[0].plot(xs, [row["peak_num"] for row in metrics], "o-", lw=1.2, label="SPH peak")
    axes[0].axhline(metrics[-1]["peak_theory"], color="k", ls="--", lw=1.1, label="Analytical peak")
    axes[0].invert_xaxis()
    axes[0].set_xlabel("dp (m)")
    axes[0].set_ylabel(r"peak $p^w/p_0$")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best", fontsize=8)

    axes[1].plot(xs, [row["rmse"] for row in metrics], "o-", lw=1.2, label="RMSE")
    axes[1].plot(xs, [abs(row["peak_deficit_at_theory_tv"]) for row in metrics], "s-", lw=1.2, label="peak deficit")
    axes[1].invert_xaxis()
    axes[1].set_xlabel("dp (m)")
    axes[1].set_ylabel("error in peak window")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best", fontsize=8)

    fig.tight_layout()
    path = FIGDIR / "cryer_k1e5_dp_convergence_20260622_error_trend.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_full(full_cases):
    FIGDIR.mkdir(parents=True, exist_ok=True)
    combined = {}
    for cfg, rows in full_cases:
        for row in rows:
            if row["tv"] > 0:
                combined[round(row["tv"], 12)] = row
    rows = [combined[key] for key in sorted(combined)]
    tv_grid = [10 ** (-4 + 4 * i / 900) for i in range(901)]
    tag = f"dp{int(round(FULL_DP * 10000)):04d}"

    def draw_series(path, ylim=None, xlim=(1e-4, 1.0), title=None):
        fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=220)
        grid = [tv for tv in tv_grid if xlim[0] <= tv <= xlim[1]]
        window = [r for r in rows if xlim[0] <= r["tv"] <= xlim[1]]
        ax.plot(grid, [cryer_center_pressure(tv) for tv in grid], "k-", lw=1.4, label="Cryer analytical")
        ax.plot([r["tv"] for r in window], [r["num"] for r in window], "o", ms=2.4, label=f"SPH dp={FULL_DP:.4f}")
        ax.set_xscale("log")
        ax.set_xlim(*xlim)
        if ylim:
            ax.set_ylim(*ylim)
        if title:
            ax.set_title(title, fontsize=10)
        ax.set_xlabel(r"$T_v$")
        ax.set_ylabel(r"$p^w(0,t)/p_0$")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=8)
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)

    fig_path = FIGDIR / f"cryer_k1e5_{tag}_full_20260622_paper_axes.png"
    draw_series(fig_path, ylim=(0.0, 1.35), title="Paper-axis view")

    max_num = max((r["num"] for r in rows), default=1.35)
    fullrange_path = FIGDIR / f"cryer_k1e5_{tag}_full_20260622_fullrange.png"
    draw_series(fullrange_path, ylim=(0.0, max(1.35, max_num * 1.08)), title="Full range including startup oscillation")

    early = [r for r in rows if 1e-4 <= r["tv"] <= 1e-2]
    early_max = max((r["num"] for r in early), default=max_num)
    early_path = FIGDIR / f"cryer_k1e5_{tag}_full_20260622_early_zoom.png"
    draw_series(early_path, ylim=(0.0, max(1.35, early_max * 1.08)), xlim=(1e-4, 1e-2), title="Early window")

    csv_path = FIGDIR / f"cryer_k1e5_{tag}_full_20260622_combined.csv"
    write_csv(csv_path, rows, ["time", "tv", "num", "theory", "speed", "sample_count"])
    metrics = metrics_from_rows(rows, 1.0)
    json_path = FIGDIR / f"cryer_k1e5_{tag}_full_20260622_metrics.json"
    json_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return fig_path, fullrange_path, early_path, csv_path, json_path, metrics


def short_configs():
    return [
        {"name": "dp003_tv010", "dp": 0.003, "tv_max": 0.1, "tv_out": 0.001, "time_max": TV1_TIME * 0.1, "tout": TV1_TIME * 0.001, "solver_timeout": 90000},
        {"name": "dp0025_tv010", "dp": 0.0025, "tv_max": 0.1, "tv_out": 0.001, "time_max": TV1_TIME * 0.1, "tout": TV1_TIME * 0.001, "solver_timeout": 120000},
        {"name": "dp002_tv010", "dp": 0.002, "tv_max": 0.1, "tv_out": 0.001, "time_max": TV1_TIME * 0.1, "tout": TV1_TIME * 0.001, "solver_timeout": 160000},
    ]


def full_configs():
    tag = f"dp{int(round(FULL_DP * 10000)):04d}"
    return [
        {"name": f"{tag}_early_tv001_dtv1e-4", "dp": FULL_DP, "tv_max": 0.01, "tv_out": 1e-4, "time_max": TV1_TIME * 0.01, "tout": TV1_TIME * 1e-4, "solver_timeout": 50000},
        {"name": f"{tag}_full_tv1_dtv1e-2", "dp": FULL_DP, "tv_max": 1.0, "tv_out": 1e-2, "time_max": TV1_TIME, "tout": TV1_TIME * 1e-2, "solver_timeout": 360000},
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["short", "full", "all", "analyze"], default="short")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    RUNROOT.mkdir(parents=True, exist_ok=True)
    FIGDIR.mkdir(parents=True, exist_ok=True)
    print(f"Tv=1 physical time for k=1e-5: {TV1_TIME:.12g} s", flush=True)

    if args.phase in ("short", "all"):
        short_results = []
        short_cases = []
        for cfg in short_configs():
            result = run_case(cfg, overwrite=args.overwrite)
            rows = read_history(result["history_csv"])
            m = metrics_from_rows(rows, 0.1)
            short_results.append({**cfg, **m, "history_csv": result["history_csv"], "workdir": result["workdir"]})
            short_cases.append((cfg, rows))
        keys = ["name", "dp", "tv_max", "tv_out", "points", "rmse", "mae", "peak_num", "peak_num_tv", "theory_at_peak_num_tv", "peak_theory", "peak_theory_tv", "num_at_peak_theory_tv", "peak_deficit_at_theory_tv", "max_speed", "min_sample_count", "final_tv", "final_num", "final_theory", "history_csv", "workdir"]
        csv_path = FIGDIR / "cryer_k1e5_dp_convergence_20260622_peak_metrics.csv"
        write_csv(csv_path, short_results, keys)
        json_path = FIGDIR / "cryer_k1e5_dp_convergence_20260622_peak_metrics.json"
        json_path.write_text(json.dumps(short_results, indent=2), encoding="utf-8")
        fig_path = plot_peak(short_cases)
        trend_path = plot_peak_error_trend(short_results)
        print(f"[saved] {csv_path}", flush=True)
        print(f"[saved] {json_path}", flush=True)
        print(f"[saved] {fig_path}", flush=True)
        print(f"[saved] {trend_path}", flush=True)

    if args.phase in ("full", "all"):
        full_cases_rows = []
        for cfg in full_configs():
            result = run_case(cfg, overwrite=args.overwrite)
            full_cases_rows.append((cfg, read_history(result["history_csv"])))
        fig_path, fullrange_path, early_path, csv_path, json_path, metrics = plot_full(full_cases_rows)
        print(f"[saved] {fig_path}", flush=True)
        print(f"[saved] {fullrange_path}", flush=True)
        print(f"[saved] {early_path}", flush=True)
        print(f"[saved] {csv_path}", flush=True)
        print(f"[saved] {json_path}", flush=True)
        print(json.dumps(metrics, indent=2), flush=True)

    if args.phase == "analyze":
        short_cases = []
        short_results = []
        for cfg in short_configs():
            history = RUNROOT / cfg["name"] / "analysis" / f"{cfg['name']}.csv"
            if history.exists():
                rows = read_history(history)
                short_cases.append((cfg, rows))
                short_results.append({**cfg, **metrics_from_rows(rows, 0.1), "history_csv": str(history), "workdir": str(RUNROOT / cfg["name"])})
        if short_cases:
            keys = ["name", "dp", "tv_max", "tv_out", "points", "rmse", "mae", "peak_num", "peak_num_tv", "theory_at_peak_num_tv", "peak_theory", "peak_theory_tv", "num_at_peak_theory_tv", "peak_deficit_at_theory_tv", "max_speed", "min_sample_count", "final_tv", "final_num", "final_theory", "history_csv", "workdir"]
            write_csv(FIGDIR / "cryer_k1e5_dp_convergence_20260622_peak_metrics.csv", short_results, keys)
            (FIGDIR / "cryer_k1e5_dp_convergence_20260622_peak_metrics.json").write_text(json.dumps(short_results, indent=2), encoding="utf-8")
            print(plot_peak(short_cases), flush=True)
            print(plot_peak_error_trend(short_results), flush=True)
        full_cases_rows = []
        for cfg in full_configs():
            history = RUNROOT / cfg["name"] / "analysis" / f"{cfg['name']}.csv"
            if history.exists():
                full_cases_rows.append((cfg, read_history(history)))
        if len(full_cases_rows) == len(full_configs()):
            print(plot_full(full_cases_rows), flush=True)


if __name__ == "__main__":
    main()
