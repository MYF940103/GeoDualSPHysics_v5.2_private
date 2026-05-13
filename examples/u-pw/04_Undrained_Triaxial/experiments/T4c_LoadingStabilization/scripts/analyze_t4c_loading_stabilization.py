#!/usr/bin/env python3
"""T4c comparison for staged selected-confinement triaxial loading."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
T4 = ROOT.parent / "T4_StressPathPostprocessing"
T4B = ROOT.parent / "T4b_RenormalizedConfinement"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

R = 0.03
H = 0.10
DP = 0.01
CAP = 0.015
EDGE = 0.015

CASES = [
    {
        "case": "T4_raw_reference",
        "label": "T4 raw gradient",
        "kind": "raw_reference",
        "root": T4,
        "gradient_mode": 0,
    },
    {
        "case": "CaseT4b_RenormConfinement",
        "label": "T4b renormalized reference",
        "kind": "t4b_reference",
        "root": T4B,
        "gradient_mode": 1,
    },
    {
        "case": "CaseT4c_RawStagedLoading",
        "label": "raw staged",
        "kind": "run",
        "root": ROOT,
        "gradient_mode": 0,
        "axial_file": "TriaxialAxialAcc_T4c_staged.csv",
        "confinement_ramp_end": 0.001,
        "axial_start": 0.0015,
    },
    {
        "case": "CaseT4c_RenormStagedLoading",
        "label": "renormalized staged",
        "kind": "run",
        "root": ROOT,
        "gradient_mode": 1,
        "axial_file": "TriaxialAxialAcc_T4c_staged.csv",
        "confinement_ramp_end": 0.001,
        "axial_start": 0.0015,
    },
    {
        "case": "CaseT4c_RawStagedGentleLoading",
        "label": "raw staged gentle",
        "kind": "run",
        "root": ROOT,
        "gradient_mode": 0,
        "axial_file": "TriaxialAxialAcc_T4c_gentle.csv",
        "confinement_ramp_end": 0.001,
        "axial_start": 0.0015,
    },
]


def read_table(path: Path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_table(path: Path, rows, fieldnames=None):
    if not rows and not fieldnames:
        return
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def fnum(v, default=0.0):
    try:
        if isinstance(v, str):
            v = v.strip().rstrip(".")
        return float(v)
    except Exception:
        return default


def read_partcsv(path: Path):
    with path.open(newline="") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        header = [h.strip() for h in header if h.strip()]
        rows = []
        for raw in reader:
            if not raw:
                continue
            vals = [v.strip() for v in raw[: len(header)]]
            if len(vals) < len(header):
                continue
            row = {}
            for k, v in zip(header, vals):
                row[k] = fnum(v)
            rows.append(row)
        return rows


def parse_run_out(path: Path):
    txt = path.read_text(errors="ignore")
    times = {0: 0.0}
    for line in txt.splitlines():
        m = re.match(r"^\s*Part_(\d{4})\s+([0-9.Ee+\-]+)\s+\d+\s+\d+\s+", line)
        if m:
            times[int(m.group(1))] = float(m.group(2))
    excluded = fnum(re.search(r"Excluded particles\.+:\s+([0-9]+)", txt).group(1) if re.search(r"Excluded particles\.+:\s+([0-9]+)", txt) else 0)
    steps = fnum(re.search(r"Steps of simulation\.+:\s+([0-9]+)", txt).group(1) if re.search(r"Steps of simulation\.+:\s+([0-9]+)", txt) else 0)
    part_files = fnum(re.search(r"PART files\.+:\s+([0-9]+)", txt).group(1) if re.search(r"PART files\.+:\s+([0-9]+)", txt) else len(times))
    dtmin = fnum(re.search(r"DTs adjusted to DtMin\.+:\s+([0-9]+)", txt).group(1) if re.search(r"DTs adjusted to DtMin\.+:\s+([0-9]+)", txt) else 0)
    conf = []
    grad = {}
    re_conf = re.compile(
        r"FlexibleConfiningStress CPU diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[-+0-9.Ee]+), p0_eff=(?P<p0>[-+0-9.Ee]+) Pa, targets=(?P<targets>\d+), legacy_targets=(?P<legacy>\d+), net_force=\((?P<fx>[-+0-9.Ee]+),(?P<fy>[-+0-9.Ee]+),(?P<fz>[-+0-9.Ee]+)\) N, total_abs_force=(?P<absforce>[-+0-9.Ee]+) N, max_accel=(?P<maxaccel>[-+0-9.Ee]+) m/s2, com_accel=(?P<comaccel>[-+0-9.Ee]+) m/s2, symmetry_residual=(?P<sym>[-+0-9.Ee]+)"
    )
    re_ext = re.compile(
        r"FlexibleConfiningStress extended diagnostics: step=(?P<step>\d+), fi_min=(?P<fi_min>[-+0-9.Ee]+), fi_max=(?P<fi_max>[-+0-9.Ee]+), fi_mean=(?P<fi_mean>[-+0-9.Ee]+), fi_threshold=(?P<fi_threshold>[-+0-9.Ee]+), fi_selected=(?P<fi_selected>\d+), class_interior=(?P<class_interior>\d+), class_lateral=(?P<class_lateral>\d+), class_top=(?P<class_top>\d+), class_bottom=(?P<class_bottom>\d+), class_edge=(?P<class_edge>\d+), class_outside=(?P<class_outside>\d+), lateral_fi_selected=(?P<lateral_fi_selected>\d+), cap_fi_selected=(?P<cap_fi_selected>\d+), lateral_inward_radial_accel_mean=(?P<lat_accel_mean>[-+0-9.Ee]+), lateral_inward_radial_accel_max=(?P<lat_accel_max>[-+0-9.Ee]+), cap_abs_axial_accel_mean=(?P<cap_axial_mean>[-+0-9.Ee]+), cap_abs_axial_accel_max=(?P<cap_axial_max>[-+0-9.Ee]+)"
    )
    re_grad = re.compile(
        r"FlexibleConfiningStress gradient diagnostics: step=(?P<step>\d+), gradient_mode=(?P<gradient_mode>\d+), corrected=(?P<grad_corrected>\d+), fallback=(?P<grad_fallback>\d+), det_min=(?P<grad_det_min>[-+0-9.Ee]+), det_max=(?P<grad_det_max>[-+0-9.Ee]+)"
    )
    rows = {}
    for m in re_conf.finditer(txt):
        d = {k: fnum(v) for k, v in m.groupdict().items()}
        rows[int(d["step"])] = d
    for m in re_ext.finditer(txt):
        step = int(m.group("step"))
        rows.setdefault(step, {"step": step})
        rows[step].update({k: fnum(v) for k, v in m.groupdict().items()})
    for m in re_grad.finditer(txt):
        step = int(m.group("step"))
        grad[step] = {k: fnum(v) for k, v in m.groupdict().items()}
    for step in sorted(rows):
        row = rows[step]
        row.update(grad.get(step, {}))
        conf.append(row)
    return {"times": times, "excluded": excluded, "steps": steps, "part_files": part_files, "dtmin": dtmin, "conf": conf}


def classify(pos):
    x, y, z = pos
    r = math.hypot(x, y)
    radialnear = abs(r - R) <= EDGE
    top = H - CAP <= z <= H + CAP
    bottom = -CAP <= z <= CAP
    inaxis = -CAP <= z <= H + CAP
    if (not inaxis) or r > R + EDGE:
        return "outside"
    if radialnear and (top or bottom):
        return "edge"
    if radialnear and CAP < z < H - CAP:
        return "lateral"
    if top:
        return "top"
    if bottom:
        return "bottom"
    return "interior"


def region_name(row):
    x, y, z = row["Pos.x [m]"], row["Pos.y [m]"], row["Pos.z [m]"]
    r = math.hypot(x, y)
    cls = classify((x, y, z))
    regs = []
    if r <= 0.25 * R and 0.40 * H <= z <= 0.60 * H:
        regs.append("center_core_small")
    if r <= 0.40 * R and 0.30 * H <= z <= 0.70 * H:
        regs.append("center_core_medium")
    if r <= 0.60 * R and 0.20 * H <= z <= 0.80 * H:
        regs.append("center_core_large")
    if cls in ("interior", "lateral"):
        regs.append("full_excluding_caps_edges")
    if r <= 0.50 * R and 0.25 * H <= z <= 0.75 * H:
        regs.append("zhao_measurement_cylinder")
    return regs


def stress_metrics(rows):
    if not rows:
        return {}
    sxx = np.array([r["Sigma_kk.x"] for r in rows])
    syy = np.array([r["Sigma_kk.y"] for r in rows])
    szz = np.array([r["Sigma_kk.z"] for r in rows])
    sxy = np.array([r["Sigma_ij.x"] for r in rows])
    sxz = np.array([r["Sigma_ij.y"] for r in rows])
    syz = np.array([r["Sigma_ij.z"] for r in rows])
    mx, my, mz = sxx.mean(), syy.mean(), szz.mean()
    mxy, mxz, myz = sxy.mean(), sxz.mean(), syz.mean()
    p_eff = -(mx + my + mz) / 3.0
    dev = np.array([[mx, mxy, mxz], [mxy, my, myz], [mxz, myz, mz]], dtype=float)
    mean = np.trace(dev) / 3.0
    dev[0, 0] -= mean
    dev[1, 1] -= mean
    dev[2, 2] -= mean
    q = math.sqrt(max(0.0, 1.5 * float(np.sum(dev * dev))))
    return {
        "p_eff_proxy": p_eff,
        "q_proxy": q,
        "axial_stress_proxy": -mz,
        "radial_stress_proxy": -(mx + my) / 2.0,
    }


def analyze_run(case):
    name = case["case"]
    out = case["root"] / f"{name}_out"
    run = parse_run_out(out / "Run.out")
    files = sorted((out / "data").glob("PartCsv_*.csv"))
    init = read_partcsv(files[0])
    init_by_id = {int(r["Idp"]): r for r in init}
    top_ids = [pid for pid, r in init_by_id.items() if r["Pos.z [m]"] >= H - DP - 1e-9]
    top_z0 = np.mean([init_by_id[i]["Pos.z [m]"] for i in top_ids])
    height0 = max(r["Pos.z [m]"] for r in init) - min(r["Pos.z [m]"] for r in init)
    frame_rows = []
    region_rows = []
    for f in files:
        part = int(f.stem.split("_")[-1])
        time = run["times"].get(part, float("nan"))
        rows = read_partcsv(f)
        pp = np.array([r["PorePress"] for r in rows])
        ppr = np.array([r["PorePressRate"] for r in rows])
        div = np.array([r["DivVel"] for r in rows])
        vel = np.array([math.sqrt(r["Vel.x [m/s]"] ** 2 + r["Vel.y [m/s]"] ** 2 + r["Vel.z [m/s]"] ** 2) for r in rows])
        kplas = np.array([r["Kplastic"] for r in rows])
        zvals = np.array([r["Pos.z [m]"] for r in rows])
        top_z = np.mean([r["Pos.z [m]"] for r in rows if int(r["Idp"]) in top_ids])
        strain_top = -(top_z - top_z0) / H
        strain_h = -((zvals.max() - zvals.min()) - height0) / height0 if height0 else 0.0
        frame_rows.append({
            "case": name, "label": case["label"], "part": part, "time": time,
            "particle_count": len(rows), "porepress_mean": pp.mean(), "porepress_std": pp.std(),
            "porepressrate_mean": ppr.mean(), "porepressrate_maxabs": np.max(np.abs(ppr)),
            "divvel_mean": div.mean(), "divvel_std": div.std(), "velocity_max": vel.max(),
            "axial_strain_top_proxy": strain_top, "axial_strain_height_proxy": strain_h,
            "kplastic_max": kplas.max(),
        })
        groups = {r: [] for r in ["center_core_small", "center_core_medium", "center_core_large", "full_excluding_caps_edges", "zhao_measurement_cylinder"]}
        for row in rows:
            for reg in region_name(row):
                groups[reg].append(row)
        for reg, grows in groups.items():
            if not grows:
                continue
            ppreg = np.array([r["PorePress"] for r in grows])
            pprreg = np.array([r["PorePressRate"] for r in grows])
            divreg = np.array([r["DivVel"] for r in grows])
            kreg = np.array([r["Kplastic"] for r in grows])
            sm = stress_metrics(grows)
            region_rows.append({
                "case": name, "label": case["label"], "part": part, "time": time, "region": reg,
                "particle_count": len(grows), "axial_strain_top_proxy": strain_top,
                "porepress_mean": ppreg.mean(), "porepress_std": ppreg.std(),
                "porepressrate_mean": pprreg.mean(), "porepressrate_maxabs": np.max(np.abs(pprreg)),
                "divvel_mean": divreg.mean(), "divvel_std": divreg.std(),
                "kplastic_max": kreg.max(), **sm,
            })
    return run, frame_rows, region_rows


def load_raw_reference():
    frame = read_table(T4 / "t4_frame_metrics.csv")
    regions = read_table(T4 / "t4_measurement_region_sensitivity.csv")
    conf = read_table(T4 / "t4_confinement_diagnostics.csv")
    for rows in (frame, regions, conf):
        for r in rows:
            r["case"] = "T4_raw_reference"
            r["label"] = "T4 raw gradient"
    return frame, regions, conf


def load_t4b_reference():
    frame = [r for r in read_table(T4B / "t4b_loading_stability_metrics.csv") if r["case"] == "CaseT4b_RenormConfinement"]
    regions = [r for r in read_table(T4B / "t4b_measurement_region_metrics.csv") if r["case"] == "CaseT4b_RenormConfinement"]
    conf = [r for r in read_table(T4B / "t4b_confinement_gradient_comparison.csv") if r["case"] == "CaseT4b_RenormConfinement"]
    for rows in (frame, regions, conf):
        for r in rows:
            r["label"] = "T4b renormalized reference"
    return frame, regions, conf


def has_pressure_reversal(rows):
    vals = [fnum(r["porepress_mean"]) for r in rows]
    return int(any(v > 0.0 for v in vals) and any(v < 0.0 for v in vals))


def max_abs_or_mean(rows):
    vals = []
    for r in rows:
        v = r.get("porepressrate_maxabs", "")
        vals.append(abs(fnum(v if v != "" else r.get("porepressrate_mean", 0))))
    return max(vals) if vals else 0.0


def load_axial_schedule(case):
    fname = case.get("axial_file")
    if not fname:
        return []
    path = case["root"] / fname
    rows = []
    with path.open(newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for raw in reader:
            if not raw or raw.get("#Time", "").startswith("#"):
                continue
            rows.append({
                "case": case["case"], "label": case["label"],
                "time": fnum(raw.get("#Time", 0)),
                "linear_acc_z": fnum(raw.get("LinearAccZ", 0)),
            })
    return rows


all_frame = []
all_region = []
all_conf = []
summary = []
stage_rows = []
axial_rows = []

raw_frame, raw_region, raw_conf = load_raw_reference()
all_frame.extend(raw_frame)
all_region.extend(raw_region)
all_conf.extend(raw_conf)
if raw_frame:
    final = raw_frame[-1]
    summary.append({
        "case": "T4_raw_reference", "label": "T4 raw gradient", "code": 0, "excluded": 0,
        "steps": 14, "part_files": 10, "dtmin_adjusted": 0, "gradient_mode": 0,
        "confinement_ramp_end": 0.0005, "axial_loading_start": 0.001,
        "final_time": final["time"], "final_velocity_max": final["velocity_max"],
        "final_porepress_mean": final["porepress_mean"], "final_porepressrate_mean": final["porepressrate_mean"],
        "max_porepressrate_abs": max_abs_or_mean(raw_frame), "pressure_reversal": 1, "final_kplastic_max": final["kplastic_max"],
    })

t4b_frame, t4b_region, t4b_conf = load_t4b_reference()
all_frame.extend(t4b_frame)
all_region.extend(t4b_region)
all_conf.extend(t4b_conf)
if t4b_frame:
    srow = next((r for r in read_table(T4B / "t4b_case_summary.csv") if r["case"] == "CaseT4b_RenormConfinement"), {})
    final = t4b_frame[-1]
    summary.append({
        "case": "CaseT4b_RenormConfinement", "label": "T4b renormalized reference",
        "code": srow.get("code", 0), "excluded": srow.get("excluded", 0),
        "steps": srow.get("steps", ""), "part_files": srow.get("part_files", ""), "dtmin_adjusted": srow.get("dtmin_adjusted", ""),
        "gradient_mode": 1, "confinement_ramp_end": 0.0005, "axial_loading_start": 0.001,
        "final_time": final["time"], "final_velocity_max": final["velocity_max"],
        "final_porepress_mean": final["porepress_mean"], "final_porepressrate_mean": final["porepressrate_mean"],
        "max_porepressrate_abs": max_abs_or_mean(t4b_frame), "pressure_reversal": has_pressure_reversal(t4b_frame),
        "final_kplastic_max": final["kplastic_max"],
    })

for case in CASES[2:]:
    run, frame_rows, region_rows = analyze_run(case)
    for r in run["conf"]:
        r["case"] = case["case"]
        r["label"] = case["label"]
    all_conf.extend(run["conf"])
    all_frame.extend(frame_rows)
    all_region.extend(region_rows)
    axial = load_axial_schedule(case)
    axial_rows.extend(axial)
    final_acc = min([r["linear_acc_z"] for r in axial], default=0.0)
    stage_rows.append({
        "case": case["case"], "label": case["label"], "gradient_mode": case["gradient_mode"],
        "confinement_ramp_start": 0.0, "confinement_ramp_end": case["confinement_ramp_end"],
        "axial_loading_start": case["axial_start"], "time_max": 0.0018,
        "final_axial_acc_z": final_acc,
    })
    final = frame_rows[-1]
    summary.append({
        "case": case["case"], "label": case["label"], "code": 0, "excluded": run["excluded"],
        "steps": run["steps"], "part_files": run["part_files"], "dtmin_adjusted": run["dtmin"],
        "gradient_mode": case["gradient_mode"], "confinement_ramp_end": case["confinement_ramp_end"],
        "axial_loading_start": case["axial_start"], "final_time": final["time"],
        "final_velocity_max": final["velocity_max"], "final_porepress_mean": final["porepress_mean"],
        "final_porepressrate_mean": final["porepressrate_mean"],
        "max_porepressrate_abs": max_abs_or_mean(frame_rows),
        "pressure_reversal": has_pressure_reversal(frame_rows), "final_kplastic_max": final["kplastic_max"],
    })

write_table(ROOT / "t4c_case_summary.csv", summary)
write_table(ROOT / "t4c_loading_stage_metrics.csv", stage_rows)
write_table(ROOT / "t4c_axial_loading_diagnostics.csv", axial_rows)
write_table(ROOT / "t4c_confinement_diagnostics.csv", all_conf)
write_table(ROOT / "t4c_porepressrate_stability_metrics.csv", all_frame)
write_table(ROOT / "t4c_measurement_region_metrics.csv", all_region)


def savefig(name):
    plt.tight_layout()
    plt.savefig(FIG / f"{name}.svg")
    plt.savefig(FIG / f"{name}.png", dpi=180)
    plt.close()


def rows_for(rows, case):
    return [r for r in rows if r["case"] == case]


plt.figure(figsize=(8, 4))
ax1 = plt.gca()
for c in CASES:
    if c["kind"] == "raw_reference":
        t = [0.0, 0.0005, 0.001, 0.0015]
        p0 = [0.0, 50.0, 50.0, 50.0]
        acc = [0.0, 0.0, -0.5, -0.5]
    elif c["kind"] == "t4b_reference":
        t = [0.0, 0.0005, 0.001, 0.0015]
        p0 = [0.0, 50.0, 50.0, 50.0]
        acc = [0.0, 0.0, -0.5, -0.5]
    else:
        axial = load_axial_schedule(c)
        t = [0.0, c["confinement_ramp_end"], c["axial_start"], 0.0018]
        p0 = [0.0, 50.0, 50.0, 50.0]
        acc = [0.0, 0.0] + [r["linear_acc_z"] for r in axial if r["time"] >= c["axial_start"]][-2:]
        if len(acc) < len(t):
            acc += [acc[-1] if acc else 0.0] * (len(t) - len(acc))
    ax1.plot(t, p0, label=f"{c['label']} p0")
ax1.set_xlabel("time [s]")
ax1.set_ylabel("p0_eff schedule [Pa]")
ax2 = ax1.twinx()
for c in CASES:
    if c["kind"] in ("raw_reference", "t4b_reference"):
        ax2.plot([0.0, 0.001, 0.0015], [0.0, -0.5, -0.5], linestyle="--", alpha=0.55, label=f"{c['label']} acc")
    else:
        axial = load_axial_schedule(c)
        ax2.plot([r["time"] for r in axial], [r["linear_acc_z"] for r in axial], linestyle="--", alpha=0.55, label=f"{c['label']} acc")
ax2.set_ylabel("axial AccInput z [m/s2]")
lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines + lines2, labels + labels2, fontsize=6, loc="lower left")
savefig("t4c_loading_schedule")


plt.figure(figsize=(8, 4))
for c in CASES:
    rows = rows_for(all_conf, c["case"])
    if rows:
        plt.plot([fnum(r["time"]) for r in rows], [fnum(r["lat_accel_mean"]) for r in rows], marker="o", label=c["label"])
plt.xlabel("time [s]")
plt.ylabel("lateral inward acceleration [m/s2]")
plt.legend(fontsize=7)
savefig("t4c_lateral_acceleration_vs_time")

plt.figure(figsize=(8, 4))
for c in CASES:
    rows = rows_for(all_conf, c["case"])
    if rows:
        plt.plot([fnum(r["time"]) for r in rows], [fnum(r["cap_axial_mean"]) for r in rows], marker="o", label=c["label"])
plt.xlabel("time [s]")
plt.ylabel("cap axial leakage [m/s2]")
plt.legend(fontsize=7)
savefig("t4c_cap_leakage_vs_time")

plt.figure(figsize=(8, 4))
for c in CASES:
    rows = rows_for(all_conf, c["case"])
    if rows:
        plt.plot([fnum(r["time"]) for r in rows], [fnum(r["comaccel"]) for r in rows], marker="o", label=c["label"])
plt.xlabel("time [s]")
plt.ylabel("COM acceleration diagnostic [m/s2]")
plt.legend(fontsize=7)
savefig("t4c_com_acceleration_vs_time")

plt.figure(figsize=(8, 4))
for c in CASES:
    rows = rows_for(all_frame, c["case"])
    if rows:
        plt.plot([fnum(r["time"]) for r in rows], [fnum(r["porepress_mean"]) for r in rows], marker="o", label=c["label"])
plt.xlabel("time [s]")
plt.ylabel("full-specimen mean pore pressure [Pa]")
plt.legend(fontsize=7)
savefig("t4c_pore_pressure_vs_time")

plt.figure(figsize=(8, 4))
for c in CASES:
    rows = [r for r in all_region if r["case"] == c["case"] and r["region"] == "center_core_medium"]
    if rows:
        plt.plot([fnum(r["axial_strain_top_proxy"]) for r in rows], [fnum(r["porepress_mean"]) for r in rows], marker="o", label=c["label"])
plt.xlabel("axial strain proxy [-]")
plt.ylabel("center-core mean pore pressure [Pa]")
plt.legend(fontsize=7)
savefig("t4c_pore_pressure_vs_axial_strain")

plt.figure(figsize=(8, 4))
for c in CASES:
    rows = rows_for(all_frame, c["case"])
    if rows:
        y = [fnum(r.get("porepressrate_maxabs", r.get("porepressrate_mean", 0))) for r in rows]
        plt.plot([fnum(r["time"]) for r in rows], y, marker="o", label=c["label"])
plt.xlabel("time [s]")
plt.ylabel("PorePressRate maxAbs or mean [Pa/s]")
plt.yscale("symlog", linthresh=1e5)
plt.legend(fontsize=7)
savefig("t4c_porepressrate_vs_time")

plt.figure(figsize=(8, 4))
for c in CASES:
    rows = rows_for(all_frame, c["case"])
    if rows:
        plt.plot([fnum(r["time"]) for r in rows], [fnum(r["divvel_mean"]) for r in rows], marker="o", label=c["label"])
plt.xlabel("time [s]")
plt.ylabel("DivVel mean [1/s]")
plt.legend(fontsize=7)
savefig("t4c_divvel_vs_time")

plt.figure(figsize=(8, 4))
for c in CASES:
    rows = rows_for(all_frame, c["case"])
    if rows:
        plt.plot([fnum(r["time"]) for r in rows], [fnum(r["velocity_max"]) for r in rows], marker="o", label=c["label"])
plt.xlabel("time [s]")
plt.ylabel("velocity max [m/s]")
plt.legend(fontsize=7)
savefig("t4c_velocity_max_vs_time")

plt.figure(figsize=(9, 4))
final_region = []
for c in CASES:
    rows = rows_for(all_region, c["case"])
    maxpart = max(int(fnum(r["part"])) for r in rows)
    for r in rows:
        if int(fnum(r["part"])) == maxpart:
            final_region.append(r)
regions = ["center_core_medium", "center_core_large", "full_excluding_caps_edges", "zhao_measurement_cylinder"]
x = np.arange(len(regions))
width = 0.25
for i, c in enumerate(CASES):
    vals = []
    for reg in regions:
        row = next((r for r in final_region if r["case"] == c["case"] and r["region"] == reg), None)
        vals.append(fnum(row["porepress_mean"]) if row else 0)
    plt.bar(x + (i - 1) * width, vals, width, label=c["label"])
plt.xticks(x, regions, rotation=25, ha="right")
plt.ylabel("final mean pore pressure [Pa]")
plt.legend(fontsize=7)
savefig("t4c_measurement_region_sensitivity")

plt.figure(figsize=(7, 4))
for c in CASES:
    rows = [r for r in all_region if r["case"] == c["case"] and r["region"] == "center_core_medium"]
    if rows and "q_proxy" in rows[0]:
        plt.plot([fnum(r["p_eff_proxy"]) for r in rows], [fnum(r["q_proxy"]) for r in rows], marker="o", label=c["label"])
plt.xlabel("p' proxy [Pa]")
plt.ylabel("q proxy [Pa]")
plt.legend(fontsize=7)
savefig("t4c_pq_proxy")

print(f"Wrote T4c comparison metrics and figures under {ROOT}")
