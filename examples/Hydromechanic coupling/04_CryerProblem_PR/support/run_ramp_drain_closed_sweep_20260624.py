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
RUNROOT = ROOT / "refinement" / "ramp_drain_timing_20260624"

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
TV_MAX = 0.065
TV_OUT = 0.001
TV_MIN = 0.001

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


def set_soil_value(root, name, value):
    node = root.find(f".//soils/{name}")
    if node is None:
        raise RuntimeError(f"soil node not found: {name}")
    node.set("value", str(value))


def ramp_tag(value, drainage_start):
    mode = "closed" if drainage_start > 0.0 else "open"
    if value == 0:
        return "ramp_0_open"
    return f"{mode}_ramp_{value:g}s".replace(".", "p").replace("-", "m")


def write_xml(path, cfg):
    tree = ET.parse(BASE_XML)
    root = tree.getroot()
    ramp = cfg["ramp"]
    drainage_start = cfg["drainage_start"]
    time_max = ramp + TV1_TIME * TV_MAX
    time_out = TV1_TIME * TV_OUT

    set_newvar_dp(root, DP)
    set_soil_value(root, "ModulusE", E)
    set_soil_value(root, "PRvs", NU)
    set_hydro_value(root, "HydraulicConductivity", K_HYD, "k=1e-5 ramp sweep; drainage opens after ramp")
    set_hydro_value(root, "HydroMechInitMode", 0)
    set_hydro_value(root, "HydroMechTopLoadMode", 2, "0=None, 1=TopVertical, 2=FlexibleConfinement")
    set_hydro_value(root, "HydroMechTopLoadQ0", Q0)
    set_hydro_value(root, "HydroMechTopLoadRampTime", ramp, "Linear ramp duration")
    set_hydro_value(root, "HydroMechDrainage", 1, "Drainage enabled; start time controls whether drainage is open during ramp")
    set_hydro_value(root, "HydroMechDrainageStartTime", drainage_start, "0=open during ramp; rampTime=closed during ramp")
    set_hydro_value(root, "PoreShepardRegularization", 0)

    set_parameter(root, "SoilDamping", 1)
    set_parameter(root, "SoilDampingCoef", 0.02)
    set_parameter(root, "Visco", 0.1)
    set_parameter(root, "ShiftTFS", 2.75)
    set_parameter(root, "DtIni", DT_FIXED)
    set_parameter(root, "DtFixed", DT_FIXED)
    set_parameter(root, "DtMin", 1.0e-8)
    set_parameter(root, "TimeMax", f"{time_max:.12g}")
    set_parameter(root, "TimeOut", f"{time_out:.12g}")
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
    ramp = cfg["ramp"]
    time_max = ramp + TV1_TIME * TV_MAX
    time_out = TV1_TIME * TV_OUT
    env = os.environ.copy()
    env.update({
        "CRYER_PARTICLES": str(particles),
        "CRYER_FIGDIR": str(analysis),
        "CRYER_OUTTAG": cfg["name"],
        "CRYER_SUMMARY_JSON": str(summary),
        "CRYER_RADIUS": str(RADIUS),
        "CRYER_DP": str(DP),
        "CRYER_Q0": str(Q0),
        "CRYER_TL": str(ramp),
        "CRYER_LOAD_RAMP": str(ramp),
        "CRYER_E": str(E),
        "CRYER_NU": str(NU),
        "CRYER_K_HYD": str(K_HYD),
        "CRYER_TOUT": str(time_out),
        "CRYER_TIME_MAX": str(time_max),
        "CRYER_TV_MIN": str(TV_MIN),
        "CRYER_CENTER_SAMPLE_RADIUS": str(DP),
    })
    log = work / "logs" / "postprocess.log"
    with log.open("w", encoding="utf-8", errors="replace") as f:
        code = subprocess.call([sys.executable, str(ROOT / "support" / "postprocess_cryer.py")], cwd=str(work), env=env, stdout=f, stderr=subprocess.STDOUT)
    if code != 0:
        raise RuntimeError(f"Postprocess failed for {cfg['name']}")
    data = json.loads(summary.read_text())
    data.update(cfg)
    data["workdir"] = str(work)
    data["history_csv"] = str(analysis / f"{cfg['name']}.csv")
    return data


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
        resolved = work.resolve()
        if not str(resolved).lower().startswith(str(RUNROOT.resolve()).lower()):
            raise RuntimeError(f"Refusing to remove outside run root: {resolved}")
        shutil.rmtree(work)
    (work / "logs").mkdir(parents=True)
    xml = work / f"{CASE}_Def.xml"
    write_xml(xml, cfg)

    ramp = cfg["ramp"]
    time_max = ramp + TV1_TIME * TV_MAX
    time_out = TV1_TIME * TV_OUT

    print(f"[gencase] {cfg['name']}", flush=True)
    run_command([GENCASE, f"{CASE}_Def", f"out/{CASE}", "-save:all"], work, work / "logs" / "gencase.log", 600)

    print(f"[solver] {cfg['name']} ramp={ramp:g}s drainage_start={cfg['drainage_start']:g}s", flush=True)
    run_command([
        DUAL_GPU_RELEASE, "-gpu", f"out/{CASE}", "out", "-dirdataout", "data", "-svres", "-svextraparts:1",
        f"-tmax:{time_max:.12g}", f"-tout:{time_out:.12g}",
    ], work, work / "logs" / "solver.log", cfg.get("solver_timeout", 90000))

    particles = work / "out" / "particles"
    particles.mkdir(exist_ok=True)
    print(f"[partvtk] {cfg['name']}", flush=True)
    run_command([
        PARTVTK, "-dirin", str(work / "out" / "data"), "-savevtk", str(particles / "PartFluid"),
        "-onlytype:-bound", f"-vars:{PARTVTK_VARS}",
    ], work, work / "logs" / "partvtk.log", 7200)

    print(f"[postprocess] {cfg['name']}", flush=True)
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
        a = k * math.pi + 1.0e-10
        b = (k + 1) * math.pi - 1.0e-10
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


def metrics(rows, cfg):
    window = [r for r in rows if TV_MIN <= r["tv"] <= TV_MAX + 1.0e-12]
    if not window:
        raise RuntimeError(f"No metric window rows for {cfg['name']}")
    errors = [r["num"] - r["theory"] for r in window]
    steps = [window[i]["num"] - window[i - 1]["num"] for i in range(1, len(window))]
    peak_num = max(window, key=lambda r: r["num"])
    peak_theory = max(window, key=lambda r: r["theory"])
    at_peak_theory = min(window, key=lambda r: abs(r["tv"] - peak_theory["tv"]))
    early = [r for r in window if r["tv"] <= 0.02 + 1.0e-12]
    early_steps = [early[i]["num"] - early[i - 1]["num"] for i in range(1, len(early))]
    return {
        "name": cfg["name"],
        "drainage_mode": cfg["drainage_mode"],
        "ramp_s": cfg["ramp"],
        "drainage_start_s": cfg["drainage_start"],
        "ramp_tv": cfg["ramp"] / TV1_TIME,
        "points": len(window),
        "rmse": math.sqrt(sum(e * e for e in errors) / len(errors)),
        "mae": sum(abs(e) for e in errors) / len(errors),
        "max_abs_error": max(abs(e) for e in errors),
        "peak_num": peak_num["num"],
        "peak_num_tv": peak_num["tv"],
        "peak_theory_at_peak_num": peak_num["theory"],
        "peak_error_at_peak_num": peak_num["num"] - peak_num["theory"],
        "peak_theory": peak_theory["theory"],
        "peak_theory_tv": peak_theory["tv"],
        "num_at_peak_theory": at_peak_theory["num"],
        "error_at_peak_theory": at_peak_theory["num"] - peak_theory["theory"],
        "max_speed": max(r["speed"] for r in window),
        "mean_abs_step": sum(abs(s) for s in steps) / len(steps) if steps else 0.0,
        "max_abs_step": max(abs(s) for s in steps) if steps else 0.0,
        "early_max_abs_step": max(abs(s) for s in early_steps) if early_steps else 0.0,
        "tv001_num": min(window, key=lambda r: abs(r["tv"] - 0.001))["num"],
        "tv001_theory": min(window, key=lambda r: abs(r["tv"] - 0.001))["theory"],
        "tv01_num": min(window, key=lambda r: abs(r["tv"] - 0.01))["num"],
        "tv01_theory": min(window, key=lambda r: abs(r["tv"] - 0.01))["theory"],
        "min_sample_count": min(r["sample_count"] for r in window),
        "history_csv": cfg.get("history_csv", ""),
    }


def write_csv(path, rows, keys):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in keys})


def plot_histories(cases):
    figdir = RUNROOT / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.6, 5.0), dpi=220)
    tv_grid = [10 ** (math.log10(5.0e-4) + (math.log10(TV_MAX) - math.log10(5.0e-4)) * i / 600) for i in range(601)]
    ax.plot(tv_grid, [cryer_center_pressure(tv) for tv in tv_grid], color="#344AA6", lw=1.5, label="Analytical")
    markers = {"closed": "o", "open": "s"}
    lines = {"closed": "-", "open": "--"}
    for idx, (cfg, rows) in enumerate(cases):
        window = [r for r in rows if TV_MIN <= r["tv"] <= TV_MAX + 1.0e-12]
        label = f"{cfg['drainage_mode']} ramp={cfg['ramp']:g}s"
        ax.plot(
            [r["tv"] for r in window],
            [r["num"] for r in window],
            marker=markers[cfg["drainage_mode"]],
            ms=3.0,
            lw=0.9,
            ls=lines[cfg["drainage_mode"]],
            color="#A34A4A",
            mfc="none",
            mec="#A34A4A",
            label=label,
        )
    ax.set_xscale("log")
    ax.set_xlim(5.0e-4, TV_MAX)
    ax.set_xlabel(r"$T_v$ after drainage opens")
    ax.set_ylabel(r"$p^w(0,t)/p_0$")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    png = figdir / "cryer_k1e5_ramp_drain_timing_tv001_0065.png"
    pdf = figdir / "cryer_k1e5_ramp_drain_timing_tv001_0065.pdf"
    fig.savefig(png)
    fig.savefig(pdf)
    plt.close(fig)
    return png, pdf


def plot_metric_summary(rows):
    figdir = RUNROOT / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["drainage_mode"], r["ramp_s"]))
    fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.6), dpi=220)
    for mode, marker, ls in (("closed", "o", "-"), ("open", "s", "--")):
        subset = [r for r in rows if r["drainage_mode"] == mode]
        if not subset:
            continue
        x = [r["ramp_s"] for r in subset]
        axes[0].plot(x, [r["peak_num"] for r in subset], marker=marker, ls=ls, label=f"{mode} SPH peak")
        axes[1].plot(x, [r["error_at_peak_theory"] for r in subset], marker=marker, ls=ls, label=mode)
        axes[2].plot(x, [r["early_max_abs_step"] for r in subset], marker=marker, ls=ls, label=mode)
    if rows:
        axes[0].axhline(rows[0]["peak_theory"], color="k", ls=":", lw=1.0, label="analytical peak")
    axes[0].set_xlabel("Ramp time (s)")
    axes[0].set_ylabel(r"peak $p^w/p_0$")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)

    axes[1].axhline(0.0, color="k", ls="--", lw=0.8)
    axes[1].set_xlabel("Ramp time (s)")
    axes[1].set_ylabel(r"$p^w/p_0$ error")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(fontsize=8)

    axes[2].set_xlabel("Ramp time (s)")
    axes[2].set_ylabel("early oscillation proxy")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(fontsize=8)

    fig.tight_layout()
    png = figdir / "cryer_k1e5_ramp_drain_timing_metrics.png"
    pdf = figdir / "cryer_k1e5_ramp_drain_timing_metrics.pdf"
    fig.savefig(png)
    fig.savefig(pdf)
    plt.close(fig)
    return png, pdf


def configs():
    ramps = [0.0, 0.0025, 0.005, 0.01, 0.02]
    items = []
    for ramp in ramps:
        items.append({
            "name": ramp_tag(ramp, ramp),
            "ramp": ramp,
            "drainage_start": ramp,
            "drainage_mode": "closed" if ramp > 0.0 else "open",
        })
    for ramp in [0.005, 0.01, 0.02]:
        items.append({
            "name": ramp_tag(ramp, 0.0),
            "ramp": ramp,
            "drainage_start": 0.0,
            "drainage_mode": "open",
        })
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()

    RUNROOT.mkdir(parents=True, exist_ok=True)
    print(f"Tv=1 physical time: {TV1_TIME:.12g} s", flush=True)
    print(f"After-drainage window: Tv={TV_MIN:g}..{TV_MAX:g}, output dTv={TV_OUT:g}", flush=True)
    all_cases = []
    all_metrics = []
    for cfg in configs():
        if not args.analyze_only:
            data = run_case(cfg, overwrite=args.overwrite)
            cfg["history_csv"] = data["history_csv"]
        history = RUNROOT / cfg["name"] / "analysis" / f"{cfg['name']}.csv"
        if not history.exists():
            print(f"[skip] missing {history}", flush=True)
            continue
        rows = read_history(history)
        cfg["history_csv"] = str(history)
        m = metrics(rows, cfg)
        all_metrics.append(m)
        all_cases.append((cfg, rows))

    if not all_metrics:
        print("[analyze] no completed ramp cases found", flush=True)
        return 1

    keys = [
        "name", "drainage_mode", "ramp_s", "drainage_start_s", "ramp_tv", "points", "rmse", "mae", "max_abs_error",
        "peak_num", "peak_num_tv", "peak_theory_at_peak_num", "peak_error_at_peak_num",
        "peak_theory", "peak_theory_tv", "num_at_peak_theory", "error_at_peak_theory",
        "max_speed", "mean_abs_step", "max_abs_step", "early_max_abs_step",
        "tv001_num", "tv001_theory", "tv01_num", "tv01_theory",
        "min_sample_count", "history_csv",
    ]
    metrics_csv = RUNROOT / "figures" / "cryer_k1e5_ramp_drain_timing_metrics.csv"
    metrics_json = RUNROOT / "figures" / "cryer_k1e5_ramp_drain_timing_metrics.json"
    sorted_metrics = sorted(all_metrics, key=lambda r: (r["drainage_mode"], r["ramp_s"]))
    write_csv(metrics_csv, sorted_metrics, keys)
    metrics_json.write_text(json.dumps(sorted_metrics, indent=2), encoding="utf-8")
    hist_png, hist_pdf = plot_histories(all_cases)
    met_png, met_pdf = plot_metric_summary(sorted_metrics)

    print(f"[saved] {metrics_csv}", flush=True)
    print(f"[saved] {metrics_json}", flush=True)
    print(f"[saved] {hist_png}", flush=True)
    print(f"[saved] {hist_pdf}", flush=True)
    print(f"[saved] {met_png}", flush=True)
    print(f"[saved] {met_pdf}", flush=True)
    for row in sorted_metrics:
        print(json.dumps(row, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
