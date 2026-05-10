#!/usr/bin/env python3
"""Summarise SW-3h Scenario 2 particle CSV outputs.
Run from the case directory or pass the SW3h run directory as argv[1].
"""
import csv
import math
import re
import sys
import time
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
OUT_DIRS = sorted(ROOT.glob("*_out"))
if not OUT_DIRS:
    raise SystemExit(f"No *_out directory found under {ROOT}")
OUT = OUT_DIRS[0]
DATA = OUT / "data"
RUNOUT = OUT / "Run.out"
FRAME_OUT = ROOT / "sw3h_frame_metrics.csv"
SUMMARY_OUT = ROOT / "sw3h_case_summary.csv"

DP = 0.01
KERNEL_H_FALLBACK = 0.018
TOP_THICKNESS = KERNEL_H_FALLBACK
BOTTOM_THICKNESS = KERNEL_H_FALLBACK
KW = 2e8
N = 0.3

run_text = RUNOUT.read_text(errors="ignore") if RUNOUT.exists() else ""
def grab(pattern, default=None, cast=float):
    m = re.search(pattern, run_text, re.I)
    return cast(m.group(1)) if m else default
steps = grab(r"Steps of simulation[^0-9]*([0-9]+)", 0, int)
# Runtime labels differ among builds; keep best-effort parsing.
runtime = grab(r"(?:RunTime|Runtime|Total time)[^0-9]*([0-9]+(?:\.[0-9]+)?)", math.nan, float)
dt_pore = grab(r"dt_pore\s*[:=]\s*([0-9Ee+\-.]+)", math.nan, float)

part_files = sorted(DATA.glob("PartCsv_*.csv"))
if not part_files:
    raise SystemExit(f"No PartCsv_*.csv files found in {DATA}")

def read_rows(path):
    with path.open(newline="", errors="ignore") as f:
        sample = f.read(4096)
        f.seek(0)
        delimiter = ";" if sample.count(";") >= sample.count(",") else ","
        return list(csv.DictReader(f, delimiter=delimiter))

def fval(row, *names, default=0.0):
    # CSV headers can include units, e.g. "Pos.z [m]". Match exact
    # names first, then compare against the part before the units.
    for name in names:
        if name in row and row[name] != "":
            try:
                return float(row[name])
            except ValueError:
                pass
    for key, value in row.items():
        base = key.split("[")[0].strip()
        for name in names:
            if base == name and value != "":
                try:
                    return float(value)
                except ValueError:
                    pass
    return default

def is_material(row):
    typ = str(row.get("Type", row.get("Type ", row.get("type", "")))).lower()
    if typ in ("fluid", "3"):
        return True
    # These SW runs save only fluid/material in PartVTK, but CSV can include type text.
    return typ == "" or "fluid" in typ

frames = []
initial_z = {}
for idx, path in enumerate(part_files):
    rows_all = read_rows(path)
    rows = [r for r in rows_all if is_material(r)]
    if not rows:
        rows = rows_all
    zs = [fval(r, "Pos.z", "z", "Z") for r in rows]
    xs = [fval(r, "Pos.x", "x", "X") for r in rows]
    zmin, zmax = min(zs), max(zs)
    h = zmax - zmin
    top_thr = zmax - TOP_THICKNESS
    bot_thr = zmin + BOTTOM_THICKNESS
    bot_ref_hi = zmin + 2 * BOTTOM_THICKNESS
    vals = {k: [] for k in ["vel", "p", "hyd", "ex", "rate", "div", "lap", "lapz", "acc", "settle"]}
    top_ex = []
    bot_ex = []
    bot_ref_ex = []
    for r in rows:
        pid = int(fval(r, "Idp", "idp", default=len(initial_z)))
        z = fval(r, "Pos.z", "z", "Z")
        if idx == 0:
            initial_z[pid] = z
        vx = fval(r, "Vel.x", "Velx", "vel.x", "vx")
        vy = fval(r, "Vel.y", "Vely", "vel.y", "vy")
        vz = fval(r, "Vel.z", "Velz", "vel.z", "vz")
        p = fval(r, "PorePress")
        ex = fval(r, "ExcessPorePress")
        rate = fval(r, "PorePressRate")
        div = fval(r, "DivVel")
        lap = fval(r, "LapPorePress")
        lapz = fval(r, "LapZ")
        ax = fval(r, "PorePressureAccelDiff.x", "PorePressureAccelDiff_0", "PorePressureAccelDiff.x")
        ay = fval(r, "PorePressureAccelDiff.y", "PorePressureAccelDiff_1", "PorePressureAccelDiff.y")
        az = fval(r, "PorePressureAccelDiff.z", "PorePressureAccelDiff_2", "PorePressureAccelDiff.z")
        hyd = p - ex
        vals["vel"].append(math.sqrt(vx*vx + vy*vy + vz*vz))
        vals["p"].append(p)
        vals["hyd"].append(hyd)
        vals["ex"].append(ex)
        vals["rate"].append(abs(rate))
        vals["div"].append(abs((KW / N) * div))
        vals["lap"].append(abs((1e-3 / (1000 * 9.81)) * lap + 1e-3 * lapz) * KW / N)
        vals["lapz"].append(lapz)
        vals["acc"].append(math.sqrt(ax*ax + ay*ay + az*az))
        vals["settle"].append(z - initial_z.get(pid, z))
        if z >= top_thr:
            top_ex.append(abs(ex))
        if z <= bot_thr:
            bot_ex.append(ex)
        elif z <= bot_ref_hi:
            bot_ref_ex.append(ex)
    def mn(a): return sum(a)/len(a) if a else 0.0
    def mx(a): return max(a) if a else 0.0
    frame = {
        "frame": idx,
        "time": idx * 0.1,
        "n": len(rows),
        "zmin": zmin,
        "zmax": zmax,
        "velocity_max": mx(vals["vel"]),
        "velocity_mean": mn(vals["vel"]),
        "settlement_mean_z": mn(vals["settle"]),
        "PorePress_min": min(vals["p"]),
        "PorePress_max": max(vals["p"]),
        "PorePress_mean": mn(vals["p"]),
        "hydrostatic_min": min(vals["hyd"]),
        "hydrostatic_max": max(vals["hyd"]),
        "hydrostatic_mean": mn(vals["hyd"]),
        "Excess_min": min(vals["ex"]),
        "Excess_max": max(vals["ex"]),
        "Excess_mean": mn(vals["ex"]),
        "bottom_Excess_mean": mn(bot_ex),
        "top_Excess_maxAbs": mx(top_ex),
        "bottom_grad_proxy": (mn(bot_ex) - mn(bot_ref_ex)) if bot_ex and bot_ref_ex else 0.0,
        "PorePressRate_maxAbs": mx(vals["rate"]),
        "DivVelContribution_maxAbs": mx(vals["div"]),
        "HydraulicContribution_maxAbs": mx(vals["lap"]),
        "PorePressureAccelDiff_maxAbs": mx(vals["acc"]),
    }
    frames.append(frame)

with FRAME_OUT.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(frames[0].keys()))
    writer.writeheader()
    writer.writerows(frames)

summary = {
    "code": 0 if "Exception" not in run_text and "ERROR" not in run_text.upper() else 1,
    "excluded_particles": grab(r"Excluded particles[^0-9]*([0-9]+)", 0, int),
    "steps": steps,
    "runtime_seconds": runtime,
    "dt_pore": dt_pore,
    "nframes": len(frames),
    "final_time": frames[-1]["time"],
    "final_velocity_max": frames[-1]["velocity_max"],
    "final_velocity_mean": frames[-1]["velocity_mean"],
    "final_settlement_mean_z": frames[-1]["settlement_mean_z"],
    "final_PorePress_max": frames[-1]["PorePress_max"],
    "final_hydrostatic_max": frames[-1]["hydrostatic_max"],
    "final_Excess_max": frames[-1]["Excess_max"],
    "final_Excess_mean": frames[-1]["Excess_mean"],
    "final_bottom_Excess_mean": frames[-1]["bottom_Excess_mean"],
    "final_top_Excess_maxAbs": frames[-1]["top_Excess_maxAbs"],
    "final_bottom_grad_proxy": frames[-1]["bottom_grad_proxy"],
    "max_velocity_over_time": max(fr["velocity_max"] for fr in frames),
    "max_PorePressRate_over_time": max(fr["PorePressRate_maxAbs"] for fr in frames),
    "max_DivVelContribution_over_time": max(fr["DivVelContribution_maxAbs"] for fr in frames),
    "max_HydraulicContribution_over_time": max(fr["HydraulicContribution_maxAbs"] for fr in frames),
    "max_PorePressureAccelDiff_over_time": max(fr["PorePressureAccelDiff_maxAbs"] for fr in frames),
}
with SUMMARY_OUT.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
    writer.writeheader()
    writer.writerow(summary)
print(f"Wrote {FRAME_OUT}")
print(f"Wrote {SUMMARY_OUT}")


