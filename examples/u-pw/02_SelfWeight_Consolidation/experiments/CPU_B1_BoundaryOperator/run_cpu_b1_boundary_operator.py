import csv
import math
import os
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
N0 = 0.3
KW = 2.0e8
K_H = 1.0e-3
WATER_LEVEL = 1.0
DP = 0.01
KERNEL_H = 0.018
CV = KW * K_H / (N0 * RHO_W * G_H)

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
        "test": "uniform_excess",
        "time_max": "0.002",
        "time_out": "0.001",
        "gravity_z": "0",
        "init": "3",
        "profile": "3",
        "amp": "5000",
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
        for mode in (0, 1):
            name = f"CaseB1_{cfg['test']}_mode{mode}"
            tree = ET.parse(BASE_XML)
            root = tree.getroot()
            grav = root.find("./casedef/constantsdef/gravity")
            grav.set("z", cfg["gravity_z"])
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
            bat = EXPDIR / f"x{name}_win64_CPU_release.bat"
            bat.write_text(
                "@echo off\r\n"
                f"py run_cpu_b1_boundary_operator.py --single {name}\r\n"
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
    m = re.search(r"Excluded[^\\n\\r]*?([0-9]+)", text, flags=re.IGNORECASE)
    if m:
        excluded = int(m.group(1))
    steps = None
    for pat in (r"Steps\s*[:=]\s*([0-9]+)", r"Nsteps\s*[:=]\s*([0-9]+)"):
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            steps = int(m.group(1))
            break
    return code, excluded, steps


def read_partcsv(path):
    lines = path.read_text(errors="ignore").splitlines()
    time = float(lines[1].split(",")[0])
    header_idx = 3
    raw_headers = [h.strip() for h in lines[header_idx].split(",") if h.strip()]
    headers = []
    for h in raw_headers:
        # Strip unit suffix but keep component names, e.g. "Pos.x [m]" -> "Pos.x".
        headers.append(h.split(" [", 1)[0].strip())
    data = []
    for line in lines[header_idx + 1 :]:
        if not line.strip():
            continue
        vals = [v.strip() for v in line.split(",")]
        if vals and vals[-1] == "":
            vals = vals[:-1]
        if len(vals) < len(headers):
            continue
        data.append([float(v) for v in vals[: len(headers)]])
    arr = np.array(data, dtype=float)
    cols = {name: arr[:, i] for i, name in enumerate(headers)}
    def col(name):
        if name in cols:
            return cols[name]
        for key, value in cols.items():
            if key.strip().lstrip("\ufeff") == name:
                return value
        raise KeyError(f"{name} not found in {path}; headers={headers[:8]}")
    pts = np.column_stack((col("Pos.x"), col("Pos.y"), col("Pos.z")))
    arrays = {k: v for k, v in cols.items() if not k.startswith("Pos.")}
    if {"PorePressureAccelDiff.x", "PorePressureAccelDiff.y", "PorePressureAccelDiff.z"}.issubset(arrays):
        arrays["PorePressureAccelDiff"] = np.column_stack((
            arrays["PorePressureAccelDiff.x"],
            arrays["PorePressureAccelDiff.y"],
            arrays["PorePressureAccelDiff.z"],
        ))
    return time, pts, arrays


def frame_files(outroot):
    csvdir = outroot / "csv_particles"
    return sorted(p for p in csvdir.glob("PartFluid_*.csv") if re.search(r"PartFluid_\d+\.csv$", p.name))


def hydrostatic(z):
    return RHO_W * G_H * np.maximum(WATER_LEVEL - z, 0.0)


def analytical_excess(z, t, kind, amp):
    if amp == 0 or kind == "hydrostatic" or kind == "selfweight_short":
        return np.zeros_like(z)
    zmin = float(np.min(z))
    zmax = float(np.max(z))
    H = max(zmax - zmin, 1e-12)
    eta = np.clip((z - zmin) / H, 0.0, 1.0)
    grid = np.linspace(0.0, 1.0, 1200)
    if kind == "uniform_excess":
        u0 = np.ones_like(grid) * amp
    else:
        u0 = amp * np.sin(np.pi * grid)
    out = np.zeros_like(eta)
    for m in range(180):
        lam = (m + 0.5) * np.pi
        phi_grid = np.cos(lam * grid)
        denom = np.trapz(phi_grid * phi_grid, grid)
        coeff = np.trapz(u0 * phi_grid, grid) / denom
        out += coeff * np.exp(-CV * (lam / H) ** 2 * t) * np.cos(lam * eta)
    return out


def get_array(arrays, *names):
    lower = {k.strip().lstrip("\ufeff").lower(): k for k in arrays}
    for name in names:
        if name in arrays:
            return arrays[name]
        if name.lower() in lower:
            return arrays[lower[name.lower()]]
    return None


def analyse_case(name, cfg, mode):
    outroot = EXPDIR / f"{name}_run"
    files = frame_files(outroot)
    if not files:
        raise RuntimeError(f"No VTK files for {name}")
    code, excluded, steps = parse_run_status(outroot)
    final = files[-1]
    actual_time, pts, arrays = read_partcsv(final)
    z = pts[:, 2]
    pp = get_array(arrays, "PorePress")
    if pp is None:
        raise RuntimeError(f"PorePress missing in {final}")
    excess = get_array(arrays, "ExcessPorePress")
    if excess is None:
        excess = pp - hydrostatic(z)
    ppr = get_array(arrays, "PorePressRate")
    lap_p = get_array(arrays, "LapPorePress")
    lap_z = get_array(arrays, "LapZ")
    divvel = get_array(arrays, "DivVel")
    ace = get_array(arrays, "PorePressureAccelDiff")
    final_time = actual_time
    ana_ex = analytical_excess(z, final_time, cfg["test"], float(cfg["amp"]))
    ana_pp = hydrostatic(z) + ana_ex
    top = z >= np.max(z) - KERNEL_H
    bottom = z <= np.min(z) + KERNEL_H
    ref = (z > np.min(z) + KERNEL_H) & (z <= np.min(z) + 2 * KERNEL_H)
    bottom_proxy = abs(float(np.mean(excess[bottom]) - np.mean(excess[ref]))) if np.any(bottom) and np.any(ref) else math.nan
    head_res = lap_p / (RHO_W * G_H) + lap_z if lap_p is not None and lap_z is not None else np.zeros_like(pp) * math.nan
    row = {
        "test": cfg["test"],
        "mode": mode,
        "case": name,
        "code": code,
        "excluded": excluded,
        "steps": steps if steps is not None else "",
        "frames": len(files),
        "max_PorePressRate_residual": float(np.nanmax(np.abs(ppr))) if ppr is not None else math.nan,
        "top_excess_maxAbs": float(np.nanmax(np.abs(excess[top]))) if np.any(top) else math.nan,
        "bottom_no_flux_proxy": bottom_proxy,
        "total_profile_RMSE": float(np.sqrt(np.mean((pp - ana_pp) ** 2))),
        "excess_profile_RMSE": float(np.sqrt(np.mean((excess - ana_ex) ** 2))),
        "bottom_excess_RMSE": float(np.sqrt(np.mean((excess[bottom] - ana_ex[bottom]) ** 2))) if np.any(bottom) else math.nan,
        "head_residual_maxAbs": float(np.nanmax(np.abs(head_res))),
        "DivVel_maxAbs": float(np.nanmax(np.abs(divvel))) if divvel is not None else math.nan,
        "PorePressureAccelDiff_maxAbs": float(np.nanmax(np.linalg.norm(ace, axis=1))) if ace is not None and ace.ndim == 2 else math.nan,
        "notes": "legacy" if mode == 0 else "boundary-operator",
    }
    profile = {
        "z": z,
        "porepress": pp,
        "excess": excess,
        "ana_porepress": ana_pp,
        "ana_excess": ana_ex,
        "head_res": head_res,
    }
    bottom_series = []
    for idx, f in enumerate(files):
        t, pts_i, arr_i = read_partcsv(f)
        zi = pts_i[:, 2]
        ppi = get_array(arr_i, "PorePress")
        exi = get_array(arr_i, "ExcessPorePress")
        if exi is None:
            exi = ppi - hydrostatic(zi)
        bi = zi <= np.min(zi) + KERNEL_H
        bottom_series.append((t, float(np.mean(exi[bi])), float(np.max(np.abs(exi[bi])))))
    return row, profile, bottom_series


def plot_results(rows, profiles, bottom_series):
    figdir = EXPDIR / "figures"
    figdir.mkdir(exist_ok=True)
    # Hydrostatic residual.
    hyd = [r for r in rows if r["test"] == "hydrostatic"]
    plt.figure(figsize=(6.0, 4.0))
    plt.bar([f"mode {r['mode']}" for r in hyd], [r["head_residual_maxAbs"] for r in hyd], color=["#808080", "#2a6fbb"])
    plt.ylabel("max |LapP/(rho_w g)+LapZ| [1/m]")
    plt.title("Hydrostatic head residual")
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(figdir / f"boundary_operator_hydrostatic_residual.{ext}")
    plt.close()

    # Excess profiles for analytical diffusion.
    plt.figure(figsize=(6.2, 4.4))
    for mode, style in [(0, "--"), (1, "-")]:
        key = ("diffusion_profile", mode)
        if key in profiles:
            p = profiles[key]
            order = np.argsort(p["z"])
            plt.plot(p["excess"][order], p["z"][order], style, label=f"mode {mode} simulated")
            if mode == 1:
                plt.plot(p["ana_excess"][order], p["z"][order], "k:", label="analytical")
    plt.xlabel("Excess pore pressure [Pa]")
    plt.ylabel("z [m]")
    plt.title("Diffusion excess profile, legacy vs boundary operator")
    plt.legend()
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(figdir / f"boundary_operator_excess_profiles_legacy_vs_new.{ext}")
    plt.close()

    # Bottom excess time.
    plt.figure(figsize=(6.2, 4.2))
    for test in ("uniform_excess", "diffusion_profile"):
        for mode, style in [(0, "--"), (1, "-")]:
            key = (test, mode)
            if key in bottom_series:
                data = np.array(bottom_series[key])
                plt.plot(data[:, 0], data[:, 1], style, label=f"{test} mode {mode}")
    plt.xlabel("time [s]")
    plt.ylabel("bottom mean excess [Pa]")
    plt.title("Bottom excess pressure")
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(figdir / f"boundary_operator_bottom_excess_legacy_vs_new.{ext}")
    plt.close()

    # Error vs depth.
    plt.figure(figsize=(6.2, 4.4))
    for mode, style in [(0, "--"), (1, "-")]:
        key = ("diffusion_profile", mode)
        if key in profiles:
            p = profiles[key]
            order = np.argsort(p["z"])
            plt.plot(np.abs(p["excess"][order] - p["ana_excess"][order]), p["z"][order], style, label=f"mode {mode}")
    plt.xlabel("|excess - analytical| [Pa]")
    plt.ylabel("z [m]")
    plt.title("Diffusion profile error vs depth")
    plt.legend()
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(figdir / f"boundary_operator_error_vs_depth.{ext}")
    plt.close()


def cleanup_outputs():
    # Keep XML/BAT/scripts/CSV/figures. Remove heavy generated folders.
    for p in EXPDIR.glob("*_run"):
        shutil.rmtree(p, ignore_errors=True)


def write_csv(rows):
    out = EXPDIR / "boundary_operator_summary_metrics.csv"
    keys = [
        "test", "mode", "case", "code", "excluded", "steps", "frames",
        "max_PorePressRate_residual", "top_excess_maxAbs", "bottom_no_flux_proxy",
        "total_profile_RMSE", "excess_profile_RMSE", "bottom_excess_RMSE",
        "head_residual_maxAbs", "DivVel_maxAbs", "PorePressureAccelDiff_maxAbs", "notes",
    ]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    prepare_cases()
    if len(sys.argv) == 3 and sys.argv[1] == "--single":
        run_case(sys.argv[2])
        return
    rows = []
    profiles = {}
    bottoms = {}
    for cfg in CASES:
        for mode in (0, 1):
            name = f"CaseB1_{cfg['test']}_mode{mode}"
            run_case(name)
            row, profile, bottom = analyse_case(name, cfg, mode)
            rows.append(row)
            profiles[(cfg["test"], mode)] = profile
            bottoms[(cfg["test"], mode)] = bottom
            print(f"{name}: code={row['code']} excluded={row['excluded']} topEx={row['top_excess_maxAbs']:.4g} bottomProxy={row['bottom_no_flux_proxy']:.4g}", flush=True)
    write_csv(rows)
    plot_results(rows, profiles, bottoms)
    cleanup_outputs()


if __name__ == "__main__":
    main()
