import csv
import math
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[5]
EXPDIR = Path(__file__).resolve().parent
BASE_XML = ROOT / "examples/u-pw/02_SelfWeight_Consolidation/CaseSelfWeightConsolidation_PR_Scenario2_Def.xml"
BIN = ROOT / "bin/windows"
GENCASE = BIN / "GenCase_win64.exe"
DUAL = BIN / "DualSPHysics5.2CPU_win64.exe"
PARTVTK = BIN / "PartVTK_win64.exe"

RHO_W = 1000.0
G_H = 9.81
WATER_LEVEL = 1.0
KERNEL_H = 0.018
FIELDS = "+idp,+vel,+rhop,+type,+mk,+PorePress,+ExcessPorePress,+PorePressRate,+DivVel,+LapPorePress,+LapZ,+PorePressureAccelDiff"


CASES = [
    {
        "test": "hydrostatic",
        "time_max": "0.0005",
        "time_out": "0.0005",
        "gravity_z": "0",
        "init": "1",
        "profile": "3",
        "amp": "0",
        "feedback": "0",
        "damping": "0",
        "shepard": "0",
        "top_start": "0",
    },
    {
        "test": "diffusion_profile",
        "time_max": "0.002",
        "time_out": "0.001",
        "gravity_z": "0",
        "init": "3",
        "profile": "1",
        "amp": "5000",
        "feedback": "0",
        "damping": "0",
        "shepard": "0",
        "top_start": "0",
    },
    {
        "test": "selfweight_short",
        "time_max": "0.005",
        "time_out": "0.0025",
        "gravity_z": "-9.81",
        "init": "1",
        "profile": "3",
        "amp": "0",
        "feedback": "1",
        "damping": "1",
        "shepard": "1",
        "top_start": "0.002",
    },
]


def set_param(root, key, value, comment=None):
    params = root.find("./execution/parameters")
    if params is None:
        raise RuntimeError("Missing execution/parameters")
    for p in params.findall("parameter"):
        if p.get("key") == key:
            p.set("value", str(value))
            if comment is not None:
                p.set("comment", comment)
            return
    p = ET.SubElement(params, "parameter")
    p.set("key", key)
    p.set("value", str(value))
    if comment:
        p.set("comment", comment)


def prepare_cases():
    for cfg in CASES:
        for mode in (0, 1, 2):
            name = f"CaseH1_{cfg['test']}_mode{mode}"
            tree = ET.parse(BASE_XML)
            root = tree.getroot()
            root.find("./casedef/constantsdef/gravity").set("z", cfg["gravity_z"])
            set_param(root, "TimeMax", cfg["time_max"])
            set_param(root, "TimeOut", cfg["time_out"])
            set_param(root, "PorePressureInit", cfg["init"])
            set_param(root, "PorePressureExcessAmp", cfg["amp"])
            set_param(root, "PorePressureAnalyticalProfile", cfg["profile"])
            set_param(root, "PorePressureTopDrained", "1")
            set_param(root, "PorePressureTopDrainedStartTime", cfg["top_start"])
            set_param(root, "PorePressureBottomNoFlux", "1")
            set_param(root, "PorePressureBoundaryOperator", str(mode))
            set_param(root, "PorePressureFeedback", cfg["feedback"])
            set_param(root, "HydromechDamping", cfg["damping"])
            set_param(root, "PorePressureShepard", cfg["shepard"])
            set_param(root, "PorePressureShepardInterval", "10")
            set_param(root, "PorePressureShepardMode", "1")
            set_param(root, "PorePressureDtSafety", "0.20")
            set_param(root, "SavePorePressure", "1")
            set_param(root, "HydraulicGravityX", "0")
            set_param(root, "HydraulicGravityY", "0")
            set_param(root, "HydraulicGravityZ", "-9.81")
            tree.write(EXPDIR / f"{name}_Def.xml", encoding="utf-8", xml_declaration=True)
            (EXPDIR / f"x{name}_win64_CPU_release.bat").write_text(
                "@echo off\r\n"
                f"py run_h1_hydraulic_mdbc_boundary.py --single {name}\r\n"
                "pause\r\n",
                encoding="utf-8",
            )


def run_cmd(cmd, cwd):
    print("RUN:", " ".join(str(x) for x in cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed with code {proc.returncode}: {' '.join(str(x) for x in cmd)}")


def run_case(name):
    outroot = EXPDIR / f"{name}_run"
    outdir = outroot / f"{name}_out"
    datadir = outdir / "data"
    csvdir = outroot / "csv_particles"
    if outroot.exists():
        shutil.rmtree(outroot)
    outroot.mkdir(parents=True, exist_ok=True)
    run_cmd([GENCASE, f"{name}_Def", str(outdir / name), "-save:all"], EXPDIR)
    run_cmd([DUAL, "-cpu", "-mdbc", str(outdir / name), str(outdir), "-dirdataout", "data", "-sv:binx,csv"], EXPDIR)
    csvdir.mkdir(parents=True, exist_ok=True)
    run_cmd([
        PARTVTK,
        "-dirin", str(datadir),
        "-filexml", str(outdir / f"{name}.xml"),
        "-savecsv", str(csvdir / "PartFluid"),
        "-onlytype:-all,+fluid",
        f"-vars:{FIELDS}",
        "-csvsep:1",
    ], EXPDIR)
    return outroot


def parse_run_status(outroot):
    runout = next(outroot.glob("*_out/Run.out"), None)
    text = runout.read_text(errors="ignore") if runout and runout.exists() else ""
    code = 0 if ("Run finished" in text or "Finished execution" in text or "Execution finished" in text) else 0
    excluded = 0
    for pat in (r"Excluded[^0-9]*([0-9]+)", r"Particles out[^0-9]*([0-9]+)"):
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            excluded = int(m.group(1))
            break
    return code, excluded


def read_partcsv(path):
    lines = path.read_text(errors="ignore").splitlines()
    time = float(lines[1].split(",")[0])
    header_idx = None
    for idx, line in enumerate(lines):
        if "Pos.x" in line and "Pos.z" in line:
            header_idx = idx
            break
    if header_idx is None:
        raise RuntimeError(f"Cannot find particle CSV header in {path}")
    headers = [h.split(" [", 1)[0].strip().lstrip("\ufeff") for h in lines[header_idx].split(",") if h.strip()]
    rows = []
    for line in lines[header_idx + 1:]:
        if not line.strip():
            continue
        vals = [v.strip() for v in line.split(",")]
        if vals and vals[-1] == "":
            vals = vals[:-1]
        if len(vals) >= len(headers):
            rows.append([float(v) for v in vals[:len(headers)]])
    arr = np.array(rows, dtype=float)
    cols = {h: arr[:, i] for i, h in enumerate(headers)}
    pts = np.column_stack((cols["Pos.x"], cols["Pos.y"], cols["Pos.z"]))
    return time, pts, cols


def frame_files(outroot):
    pat = re.compile(r"PartFluid_\d+\.csv$")
    return sorted(p for p in (outroot / "csv_particles").glob("PartFluid_*.csv") if pat.match(p.name))


def layer_masks(z):
    zmin = float(np.min(z))
    zmax = float(np.max(z))
    top = z >= zmax - KERNEL_H
    bottom = z <= zmin + KERNEL_H
    ref = (z > zmin + KERNEL_H) & (z <= zmin + 2.0 * KERNEL_H)
    return zmin, zmax, top, bottom, ref


def profile_rows(test, mode, frame, time, pts, cols):
    z = pts[:, 2]
    idx = np.argsort(z)
    return [
        {
            "test": test,
            "mode": mode,
            "frame": frame,
            "time": time,
            "z": float(z[i]),
            "PorePress": float(cols["PorePress"][i]),
            "ExcessPorePress": float(cols["ExcessPorePress"][i]),
            "PorePressRate": float(cols["PorePressRate"][i]),
            "LapPorePress": float(cols["LapPorePress"][i]),
            "LapZ": float(cols["LapZ"][i]),
        }
        for i in idx
    ]


def analyze_case(name, test, mode, outroot):
    files = frame_files(outroot)
    if not files:
        raise RuntimeError(f"No PartFluid csv files for {name}")
    final = files[-1]
    time, pts, cols = read_partcsv(final)
    z = pts[:, 2]
    zmin, zmax, top, bottom, ref = layer_masks(z)
    excess = cols["ExcessPorePress"]
    lapp = cols["LapPorePress"]
    lapz = cols["LapZ"]
    headres = lapp / (RHO_W * G_H) + lapz
    refmean = float(np.mean(excess[ref])) if np.any(ref) else 0.0
    bottommean = float(np.mean(excess[bottom])) if np.any(bottom) else 0.0
    code, excluded = parse_run_status(outroot)
    return {
        "test": test,
        "mode": mode,
        "code": code,
        "excluded": excluded,
        "frames": len(files),
        "final_time": time,
        "max_porepressrate_abs": float(np.max(np.abs(cols["PorePressRate"]))),
        "head_residual_max_abs": float(np.max(np.abs(headres))),
        "top_excess_max_abs": float(np.max(np.abs(excess[top]))) if np.any(top) else 0.0,
        "bottom_excess_mean": bottommean,
        "bottom_noflux_proxy": abs(bottommean - refmean),
        "excess_max_abs": float(np.max(np.abs(excess))),
    }, profile_rows(test, mode, len(files)-1, time, pts, cols)


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def standalone_operator_metrics():
    # These are the O1-revised one-dimensional operator diagnostics used as the
    # H1 expectation for the material-only and ideal boundary-particle limits.
    return [
        {"mode": 0, "model": "material_only", "eigenmode": 0, "s0": 0.91197, "note": "Current material-material PR operator diagnostic."},
        {"mode": 1, "model": "virtual_ghost", "eigenmode": 0, "s0": 0.91202, "note": "Simple virtual contribution has little effect in the 1D diagnostic."},
        {"mode": 2, "model": "hydraulic_boundary_particles", "eigenmode": 0, "s0": 0.99529, "note": "Idealized boundary-particle hydraulic state target from O1-revised."},
        {"mode": 2, "model": "1d_mls_reference", "eigenmode": 0, "s0": 0.99990, "note": "Standalone 1D MLS target; not production corrected-gradient."},
    ]


def make_figures(metrics, profiles):
    figdir = EXPDIR / "figures"
    figdir.mkdir(exist_ok=True)
    modes = sorted({int(r["mode"]) for r in metrics})
    tests = sorted({r["test"] for r in metrics})

    for key, fname, ylabel in [
        ("head_residual_max_abs", "h1_hydrostatic_residual_near_boundary", "max |LapP/(rho g)+LapZ|"),
        ("bottom_noflux_proxy", "h1_boundary_contribution_diagnostics", "bottom no-flux proxy [Pa]"),
        ("top_excess_max_abs", "h1_boundary_hydraulic_state_profiles", "top |excess| [Pa]"),
    ]:
        plt.figure(figsize=(7, 4))
        for test in tests:
            vals = [next((r[key] for r in metrics if r["test"] == test and int(r["mode"]) == m), np.nan) for m in modes]
            plt.plot(modes, vals, marker="o", label=test)
        plt.xlabel("PorePressureBoundaryOperator mode")
        plt.ylabel(ylabel)
        plt.legend()
        plt.tight_layout()
        plt.savefig(figdir / f"{fname}.png", dpi=200)
        plt.savefig(figdir / f"{fname}.svg")
        plt.close()

    profile_tests = ["diffusion_profile", "selfweight_short"]
    for test, fname in [
        ("diffusion_profile", "h1_pressure_diffusion_profiles_mode0_1_2"),
        ("selfweight_short", "h1_selfweight_short_excess_profiles_mode0_1_2"),
    ]:
        plt.figure(figsize=(6, 5))
        for mode in modes:
            rows = [r for r in profiles if r["test"] == test and int(r["mode"]) == mode]
            if not rows:
                continue
            rows.sort(key=lambda r: r["z"])
            plt.plot([r["ExcessPorePress"] for r in rows], [r["z"] for r in rows], marker=".", label=f"mode {mode}")
        plt.xlabel("Excess pore pressure [Pa]")
        plt.ylabel("z [m]")
        plt.legend()
        plt.tight_layout()
        plt.savefig(figdir / f"{fname}.png", dpi=200)
        plt.savefig(figdir / f"{fname}.svg")
        plt.close()

    op = standalone_operator_metrics()
    plt.figure(figsize=(6, 4))
    plt.bar([f"mode {r['mode']}\n{r['model']}" for r in op], [r["s0"] for r in op])
    plt.axhline(1.0, color="k", linestyle="--", linewidth=1)
    plt.ylabel("effective eigenmode-0 Laplacian scale")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(figdir / "h1_eigenmode_operator_scaling.png", dpi=200)
    plt.savefig(figdir / "h1_eigenmode_operator_scaling.svg")
    plt.close()


def clean_outputs():
    for p in EXPDIR.glob("*_run"):
        if p.is_dir():
            shutil.rmtree(p)


def run_all(single=None):
    prepare_cases()
    metrics = []
    profiles = []
    cases = []
    for cfg in CASES:
        for mode in (0, 1, 2):
            name = f"CaseH1_{cfg['test']}_mode{mode}"
            if single and single != name:
                continue
            cases.append((name, cfg["test"], mode))
    for name, test, mode in cases:
        outroot = run_case(name)
        m, prof = analyze_case(name, test, mode, outroot)
        metrics.append(m)
        profiles.extend(prof)
    write_csv(EXPDIR / "h1_hydrostatic_residual_metrics.csv", [r for r in metrics if r["test"] == "hydrostatic"])
    write_csv(EXPDIR / "h1_pressure_diffusion_metrics.csv", [r for r in metrics if r["test"] == "diffusion_profile"])
    write_csv(EXPDIR / "h1_selfweight_short_metrics.csv", [r for r in metrics if r["test"] == "selfweight_short"])
    write_csv(EXPDIR / "h1_boundary_state_metrics.csv", metrics)
    write_csv(EXPDIR / "h1_profiles_summary.csv", profiles)
    write_csv(EXPDIR / "h1_operator_scaling_metrics.csv", standalone_operator_metrics())
    make_figures(metrics, profiles)
    clean_outputs()


if __name__ == "__main__":
    one = None
    if len(sys.argv) == 3 and sys.argv[1] == "--single":
        one = sys.argv[2]
    run_all(one)
