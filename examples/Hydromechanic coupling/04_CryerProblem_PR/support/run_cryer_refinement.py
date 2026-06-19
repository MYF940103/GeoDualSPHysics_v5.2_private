from pathlib import Path
import csv
import json
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
RUNROOT = ROOT / "refinement"
FIGDIR = ROOT / "figures"

GENCASE = BIN / "GenCase_win64.exe"
DUAL_DEBUG = BIN / "DualSPHysics5.2CPU_win64_debug.exe"
DUAL_RELEASE = BIN / "DualSPHysics5.2CPU_win64.exe"
DUAL_GPU_RELEASE = BIN / "DualSPHysics5.2_GEO_win64.exe"
PARTVTK = BIN / "PartVTK_win64.exe"

VARS = "+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress"
RUN_TIMEOUT = 1200.0
POLL_SECONDS = 0.5


def set_value(root, xpath, value):
    node = root.find(xpath)
    if node is None:
        raise RuntimeError(f"XML node not found: {xpath}")
    node.set("value", str(value))


def ensure_soil_value(root, name, value, comment=None):
    soils = root.find(".//soils")
    if soils is None:
        raise RuntimeError("XML soils node not found")
    node = soils.find(name)
    if node is None:
        node = ET.SubElement(soils, name)
    node.set("value", str(value))
    if comment is not None:
        node.set("comment", comment)


def remove_soil_value(root, name):
    soils = root.find(".//soils")
    if soils is None:
        raise RuntimeError("XML soils node not found")
    node = soils.find(name)
    if node is not None:
        soils.remove(node)


def set_newvar(root, name, value):
    for node in root.findall(".//newvarcte"):
        if node.get("name") == name:
            node.set("value", str(value))
            return
        if name in node.attrib:
            node.set(name, str(value))
            return
    raise RuntimeError(f"newvarcte not found: {name}")


def write_variant_xml(dst, cfg):
    tree = ET.parse(BASE_XML)
    root = tree.getroot()
    set_newvar(root, "Dp", cfg["dp"])
    ensure_soil_value(root, "HydroMechInitMode", cfg["init_mode"])
    ensure_soil_value(root, "HydroMechDrainageMode", cfg["drainage_mode"])
    if str(cfg["drainage_mode"]).lower() == "freesurface":
        remove_soil_value(root, "HydroMechDrainageRadius")
        remove_soil_value(root, "HydroMechDrainageThickness")
    else:
        ensure_soil_value(root, "HydroMechDrainageRadius", cfg["radius"])
        ensure_soil_value(root, "HydroMechDrainageThickness", cfg.get("drainage_thickness", cfg["dp"]))
    set_value(root, ".//HydroMechTopLoadRampTime", cfg["load_ramp"])
    set_value(root, ".//HydroMechDrainageStartTime", cfg["drain_start"])
    set_value(root, ".//PoreDtSafety", cfg["pore_dt"])
    set_value(root, ".//PoreShepardRegularization", cfg["shepard"])
    set_value(root, ".//PoreShepardInterval", cfg["shepard_interval"])
    set_value(root, ".//parameter[@key='SoilDampingCoef']", cfg["damping"])
    set_value(root, ".//parameter[@key='Visco']", cfg["visco"])
    set_value(root, ".//parameter[@key='ShiftTFS']", cfg["shift_tfs"])
    set_value(root, ".//parameter[@key='DtIni']", min(1e-6, cfg["tout"] / 20.0))
    set_value(root, ".//parameter[@key='DtFixed']", min(1e-6, cfg["tout"] / 20.0))
    set_value(root, ".//parameter[@key='DtMin']", min(1e-8, cfg["tout"] / 2000.0))
    set_value(root, ".//parameter[@key='TimeMax']", cfg["time_max"])
    set_value(root, ".//parameter[@key='TimeOut']", cfg["tout"])
    tree.write(dst, encoding="UTF-8", xml_declaration=True)


def run_process(args, cwd, stdout_path, stderr_path, runout_path=None):
    with stdout_path.open("w") as out, stderr_path.open("w") as err:
        proc = subprocess.Popen(args, cwd=str(cwd), stdout=out, stderr=err)
        start = time.time()
        finished_by_log = False
        while proc.poll() is None:
            if runout_path and runout_path.exists():
                tail = runout_path.read_text(errors="ignore")[-4096:]
                if "Finished execution (code=0)." in tail:
                    finished_by_log = True
                    break
            if time.time() - start > RUN_TIMEOUT:
                proc.kill()
                raise RuntimeError(f"Timed out: {' '.join(map(str, args))}")
            time.sleep(POLL_SECONDS)
        if finished_by_log and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)
            return 0
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"Command failed with code {code}: {' '.join(map(str, args))}")
    return code


def run_variant(cfg):
    name = cfg["name"]
    work = RUNROOT / name
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    xml = work / f"{CASE}_Def.xml"
    outdir = work / f"{CASE}_out"
    data = outdir / "data"
    particles = outdir / "particles"
    figdir = work / "figures"
    support = work / "support"
    support.mkdir()
    figdir.mkdir()
    write_variant_xml(xml, cfg)

    use_gpu = bool(cfg.get("use_gpu", False))
    solver = DUAL_GPU_RELEASE if use_gpu and DUAL_GPU_RELEASE.exists() else (DUAL_RELEASE if DUAL_RELEASE.exists() else DUAL_DEBUG)
    device_arg = "-gpu" if use_gpu and solver == DUAL_GPU_RELEASE else "-cpu"
    run_process([GENCASE, f"{CASE}_Def", f"{CASE}_out/{CASE}", "-save:all"], work, support / "gencase_stdout.log", support / "gencase_stderr.log")
    runout = outdir / "Run.out"
    run_process([solver, device_arg, f"{CASE}_out/{CASE}", f"{CASE}_out", "-dirdataout", "data", "-svres", "-svextraparts:1",
                 f"-tmax:{cfg['time_max']}", f"-tout:{cfg['tout']}"], work, support / "solver_stdout.log", support / "solver_stderr.log", runout)
    run_process([PARTVTK, "-dirin", data, "-savevtk", particles / "PartFluid", "-onlytype:-bound", f"-vars:{VARS}"],
                work, support / "partvtk_stdout.log", support / "partvtk_stderr.log")

    summary = figdir / "summary.json"
    env = os.environ.copy()
    env.update({
        "CRYER_PARTICLES": str(particles),
        "CRYER_FIGDIR": str(figdir),
        "CRYER_OUTTAG": name,
        "CRYER_SUMMARY_JSON": str(summary),
        "CRYER_RADIUS": str(cfg["radius"]),
        "CRYER_DP": str(cfg["dp"]),
        "CRYER_Q0": str(cfg["q0"]),
        "CRYER_TL": str(cfg["drain_start"]),
        "CRYER_LOAD_RAMP": str(cfg["load_ramp"]),
        "CRYER_E": str(cfg["e"]),
        "CRYER_NU": str(cfg["nu"]),
        "CRYER_K_HYD": str(cfg["khyd"]),
        "CRYER_TOUT": str(cfg["tout"]),
        "CRYER_TIME_MAX": str(cfg["time_max"]),
    })
    with (support / "postprocess_stdout.log").open("w") as out, (support / "postprocess_stderr.log").open("w") as err:
        code = subprocess.call([sys.executable, str(ROOT / "support" / "postprocess_cryer.py")], cwd=str(work), env=env, stdout=out, stderr=err)
    if code != 0:
        raise RuntimeError(f"Postprocess failed for {name}")

    metrics = json.loads(summary.read_text())
    metrics.update(cfg)
    metrics["workdir"] = str(work)
    metrics["history_csv"] = str(figdir / f"{name}.csv")
    metrics["history_png"] = str(figdir / f"{name}.png")
    metrics["run_mode"] = "gpu" if device_arg == "-gpu" else "cpu"
    return metrics


def write_summary(rows):
    FIGDIR.mkdir(exist_ok=True)
    path = RUNROOT / "refinement_summary.csv"
    keys = [
        "name", "run_mode", "dp", "tl", "damping", "visco", "shepard", "pore_dt",
        "init_mode", "drainage_mode", "load_ramp", "drain_start", "shift_tfs",
        "snapshots", "rmse", "mae", "load_end_abs_error", "peak_num",
        "peak_num_tv", "peak_theory", "peak_theory_tv", "final_num",
        "final_theory", "final_abs_error", "max_speed", "min_sample_count",
        "min_free_surface_count", "history_png",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in keys})
    return path


def plot_convergence(rows):
    path = FIGDIR / "cryer_refinement_convergence.png"
    fig, ax = plt.subplots(figsize=(7, 4.4))
    xs = [r["dp"] for r in rows]
    ax.plot(xs, [r["rmse"] for r in rows], "o-", label="RMSE")
    ax.plot(xs, [r["load_end_abs_error"] for r in rows], "s-", label="Load-end abs error")
    ax.plot(xs, [abs(r["peak_num"] - r["peak_theory"]) for r in rows], "^-", label="Peak magnitude diff")
    ax.invert_xaxis()
    ax.set_xlabel("Particle spacing dp (m)")
    ax.set_ylabel("Normalized pressure error")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def main():
    base = {
        "radius": 0.05,
        "q0": 10000.0,
        "e": 2.0e6,
        "nu": 0.3,
        "khyd": 1e-3,
        "pore_dt": 0.1,
        "shepard": 0,
        "shepard_interval": 30,
        "init_mode": "0",
        "drainage_mode": "FreeSurface",
        "damping": 4e-5,
        "visco": 0.1,
        "shift_tfs": 2.75,
    }
    configs = [
        dict(base, name="dp0100_freesurface", dp=0.01, load_ramp=0.0, drain_start=0.0, tl=0.0, tout=0.0001, time_max=0.005),
        dict(base, name="dp0075_freesurface", dp=0.0075, load_ramp=0.0, drain_start=0.0, tl=0.0, tout=0.0001, time_max=0.005),
        dict(base, name="dp00625_freesurface", dp=0.00625, load_ramp=0.0, drain_start=0.0, tl=0.0, tout=0.0001, time_max=0.005),
    ]

    rows = []
    for cfg in configs:
        print(f"Running {cfg['name']} ...", flush=True)
        rows.append(run_variant(cfg))
        write_summary(rows)
        plot_convergence(rows)
        last = rows[-1]
        print(f"  rmse={last['rmse']:.4g}, load_end={last['load_end_abs_error']:.4g}, peak={last['peak_num']:.4g}", flush=True)

    summary = write_summary(rows)
    conv = plot_convergence(rows)
    print(f"Saved {summary}")
    print(f"Saved {conv}")


if __name__ == "__main__":
    main()
