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
RUNROOT = ROOT / "refinement" / "damping_sweep_20260622"
FIGDIR = ROOT / "figures"

GENCASE = BIN / "GenCase_win64.exe"
DUAL_GPU_RELEASE = BIN / "DualSPHysics5.2_GEO_win64.exe"
PARTVTK = BIN / "PartVTK_win64.exe"

RADIUS = 0.05
Q0 = 10000.0
E = 2.0e6
NU = 0.3
K_HYD = 1.0e-5
DP = 0.0025
DT_FIXED = 5.0e-6
RHO_W = 1000.0
G_REF = 9.81
K_BULK = E / (3.0 * (1.0 - 2.0 * NU))
G_SHEAR = E / (2.0 * (1.0 + NU))
M_CONSTRAINED = K_BULK + 4.0 * G_SHEAR / 3.0
CV = K_HYD * M_CONSTRAINED / (RHO_W * G_REF)
TV1_TIME = RADIUS * RADIUS / CV
ETA = (1.0 - NU) / (1.0 - 2.0 * NU)
TV_MAX = 0.01
TV_OUT = 1.0e-4
TV_MIN_METRIC = 0.001

PARTVTK_VARS = (
    "+idp,+mk,+vel,+rhop,+press,+fstype,+fsnormal,"
    "+porepress,+porepress0,+excessporepress,+hydromechloadace"
)


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
    set_newvar_dp(root, DP)
    set_hydro_value(root, "HydraulicConductivity", K_HYD)
    set_hydro_value(root, "HydroMechInitMode", 0)
    set_hydro_value(root, "HydroMechTopLoadMode", 2)
    set_hydro_value(root, "HydroMechTopLoadRampTime", 0.0)
    set_hydro_value(root, "HydroMechDrainage", 1)
    set_hydro_value(root, "HydroMechDrainageStartTime", 0.0)
    set_hydro_value(root, "PoreShepardRegularization", 0)
    set_parameter(root, "SoilDamping", 1)
    set_parameter(root, "SoilDampingCoef", cfg["damping"])
    set_parameter(root, "Visco", 0.1)
    set_parameter(root, "ShiftTFS", 2.75)
    set_parameter(root, "DtIni", DT_FIXED)
    set_parameter(root, "DtFixed", DT_FIXED)
    set_parameter(root, "DtMin", 1.0e-8)
    set_parameter(root, "TimeMax", TV1_TIME * TV_MAX)
    set_parameter(root, "TimeOut", TV1_TIME * TV_OUT)
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


def damping_tag(value):
    return f"damp_{value:g}".replace(".", "p").replace("-", "m")


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
        "CRYER_DP": str(DP),
        "CRYER_Q0": str(Q0),
        "CRYER_TL": "0",
        "CRYER_LOAD_RAMP": "0",
        "CRYER_E": str(E),
        "CRYER_NU": str(NU),
        "CRYER_K_HYD": str(K_HYD),
        "CRYER_TOUT": str(TV1_TIME * TV_OUT),
        "CRYER_TIME_MAX": str(TV1_TIME * TV_MAX),
        "CRYER_TV_MIN": "0",
    })
    log = work / "logs" / "postprocess.log"
    with log.open("w", encoding="utf-8", errors="replace") as f:
        code = subprocess.call([sys.executable, str(ROOT / "support" / "postprocess_cryer.py")], cwd=str(work), env=env, stdout=f, stderr=subprocess.STDOUT)
    if code != 0:
        raise RuntimeError(f"Postprocess failed for {cfg['name']}")
    return analysis / f"{cfg['name']}.csv"


def run_case(cfg, overwrite=False):
    work = RUNROOT / cfg["name"]
    history = work / "analysis" / f"{cfg['name']}.csv"
    if history.exists() and not overwrite:
        print(f"[reuse] {cfg['name']}", flush=True)
        return history
    if work.exists():
        shutil.rmtree(work)
    (work / "logs").mkdir(parents=True)
    xml = work / f"{CASE}_Def.xml"
    write_xml(xml, cfg)
    print(f"[gencase] {cfg['name']}", flush=True)
    run_command([GENCASE, f"{CASE}_Def", f"out/{CASE}", "-save:all"], work, work / "logs" / "gencase.log", 600)
    print(f"[solver] {cfg['name']} damping={cfg['damping']}", flush=True)
    run_command([
        DUAL_GPU_RELEASE, "-gpu", f"out/{CASE}", "out", "-dirdataout", "data", "-svres", "-svextraparts:1",
        f"-tmax:{TV1_TIME * TV_MAX:.12g}", f"-tout:{TV1_TIME * TV_OUT:.12g}",
    ], work, work / "logs" / "solver.log", 90000)
    particles = work / "out" / "particles"
    particles.mkdir(exist_ok=True)
    print(f"[partvtk] {cfg['name']}", flush=True)
    run_command([
        PARTVTK, "-dirin", str(work / "out" / "data"), "-savevtk", str(particles / "PartFluid"),
        "-onlytype:-bound", f"-vars:{PARTVTK_VARS}",
    ], work, work / "logs" / "partvtk.log", 1800)
    print(f"[post] {cfg['name']}", flush=True)
    return postprocess(work, cfg)


def cryer_root_function(z):
    return (1.0 - 0.5 * ETA * z * z) * math.sin(z) - z * math.cos(z)


def bisection_root(a, b):
    fa = cryer_root_function(a)
    for _ in range(80):
        c = 0.5 * (a + b)
        fc = cryer_root_function(c)
        if fa * fc <= 0.0:
            b = c
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


def metrics(rows, damping):
    window = [r for r in rows if TV_MIN_METRIC <= r["tv"] <= TV_MAX + 1e-12]
    if not window:
        raise RuntimeError("No metric window rows")
    errors = [r["num"] - r["theory"] for r in window]
    deltas = [window[i]["num"] - window[i - 1]["num"] for i in range(1, len(window))]
    return {
        "damping": damping,
        "points": len(window),
        "rmse": math.sqrt(sum(e * e for e in errors) / len(errors)),
        "mae": sum(abs(e) for e in errors) / len(errors),
        "max_abs_error": max(abs(e) for e in errors),
        "error_range": max(errors) - min(errors),
        "num_range": max(r["num"] for r in window) - min(r["num"] for r in window),
        "mean_abs_step": sum(abs(d) for d in deltas) / len(deltas) if deltas else 0.0,
        "max_abs_step": max(abs(d) for d in deltas) if deltas else 0.0,
        "max_speed": max(r["speed"] for r in window),
        "tv001_num": min(window, key=lambda r: abs(r["tv"] - 0.001))["num"],
        "tv001_theory": min(window, key=lambda r: abs(r["tv"] - 0.001))["theory"],
        "tv01_num": min(window, key=lambda r: abs(r["tv"] - 0.01))["num"],
        "tv01_theory": min(window, key=lambda r: abs(r["tv"] - 0.01))["theory"],
        "min_sample_count": min(r["sample_count"] for r in window),
        "history_csv": "",
    }


def write_csv(path, rows, keys):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in keys})


def plot_histories(cases):
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.6, 5.0), dpi=220)
    tv_grid = [10 ** (-3 + (math.log10(0.0105) + 3) * i / 400) for i in range(401)]
    ax.plot(tv_grid, [cryer_center_pressure(tv) for tv in tv_grid], "k-", lw=1.4, label="Cryer analytical")
    for cfg, rows in cases:
        window = [r for r in rows if TV_MIN_METRIC <= r["tv"] <= TV_MAX + 1e-12]
        ax.plot([r["tv"] for r in window], [r["num"] for r in window], "o-", ms=2.0, lw=0.9, label=f"d={cfg['damping']:g}")
    ax.set_xscale("log")
    ax.set_xlim(1e-3, 1.05e-2)
    ax.set_ylim(0.88, 1.16)
    ax.set_xlabel(r"$T_v$")
    ax.set_ylabel(r"$p^w(0,t)/p_0$")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=7)
    fig.tight_layout()
    path = FIGDIR / "cryer_k1e5_dp0025_damping_sweep_20260622_tv001_001.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_metric_summary(rows):
    FIGDIR.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: r["damping"])
    fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.6), dpi=220)
    x = [r["damping"] for r in rows]
    axes[0].plot(x, [r["rmse"] for r in rows], "o-", label="RMSE")
    axes[0].plot(x, [r["mae"] for r in rows], "s-", label="MAE")
    axes[0].set_xlabel("SoilDampingCoef")
    axes[0].set_ylabel("error")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)

    axes[1].plot(x, [r["mean_abs_step"] for r in rows], "o-", label="mean |Delta p/p0|")
    axes[1].plot(x, [r["max_abs_step"] for r in rows], "s-", label="max |Delta p/p0|")
    axes[1].set_xlabel("SoilDampingCoef")
    axes[1].set_ylabel("oscillation proxy")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(fontsize=8)

    axes[2].plot(x, [r["tv01_num"] for r in rows], "o-", label=r"SPH at $T_v=0.01$")
    axes[2].axhline(rows[0]["tv01_theory"], color="k", ls="--", lw=1.0, label="analytical")
    axes[2].set_xlabel("SoilDampingCoef")
    axes[2].set_ylabel(r"$p^w(0,t)/p_0$")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(fontsize=8)

    fig.tight_layout()
    path = FIGDIR / "cryer_k1e5_dp0025_damping_sweep_20260622_metrics.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def configs():
    values = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2]
    return [{"name": damping_tag(v), "damping": v} for v in values]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()

    RUNROOT.mkdir(parents=True, exist_ok=True)
    print(f"Tv=1 physical time: {TV1_TIME:.12g} s", flush=True)
    print(f"Sweep window: Tv={TV_MIN_METRIC:g}..{TV_MAX:g}, output dTv={TV_OUT:g}", flush=True)
    all_cases = []
    all_metrics = []
    for cfg in configs():
        history = RUNROOT / cfg["name"] / "analysis" / f"{cfg['name']}.csv"
        if not args.analyze_only:
            history = run_case(cfg, overwrite=args.overwrite)
        if not history.exists():
            print(f"[skip] missing {history}", flush=True)
            continue
        rows = read_history(history)
        m = metrics(rows, cfg["damping"])
        m["history_csv"] = str(history)
        all_metrics.append(m)
        all_cases.append((cfg, rows))

    keys = [
        "damping", "points", "rmse", "mae", "max_abs_error", "error_range", "num_range",
        "mean_abs_step", "max_abs_step", "max_speed", "tv001_num", "tv001_theory",
        "tv01_num", "tv01_theory", "min_sample_count", "history_csv",
    ]
    if not all_metrics:
        print("[analyze] no completed damping cases found", flush=True)
        return
    metrics_csv = FIGDIR / "cryer_k1e5_dp0025_damping_sweep_20260622_metrics.csv"
    write_csv(metrics_csv, sorted(all_metrics, key=lambda r: r["damping"]), keys)
    metrics_json = FIGDIR / "cryer_k1e5_dp0025_damping_sweep_20260622_metrics.json"
    metrics_json.write_text(json.dumps(sorted(all_metrics, key=lambda r: r["damping"]), indent=2), encoding="utf-8")
    history_fig = plot_histories(all_cases)
    metrics_fig = plot_metric_summary(all_metrics)
    print(f"[saved] {metrics_csv}", flush=True)
    print(f"[saved] {metrics_json}", flush=True)
    print(f"[saved] {history_fig}", flush=True)
    print(f"[saved] {metrics_fig}", flush=True)
    for row in sorted(all_metrics, key=lambda r: r["damping"]):
        print(json.dumps(row, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
