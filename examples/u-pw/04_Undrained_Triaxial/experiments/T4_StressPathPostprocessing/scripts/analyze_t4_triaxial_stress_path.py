#!/usr/bin/env python3
"""T4 triaxial measurement-region and stress-path postprocessing."""

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
CASE = "CaseT4_StressPath_SelectedConfinement"
OUT = ROOT / f"{CASE}_out"
DATA = OUT / "data"
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

R = 0.03
H = 0.10
CAP = 0.015
EDGE = 0.015
KERNEL_H = 0.018
KERNEL_SIZE = 2.0 * KERNEL_H
MASS_FLUID = 0.0021
WENDLAND_AWEN = 0.41778 / (KERNEL_H ** 3)

CPU_RE = re.compile(
    r"step=(?P<step>\d+), TimeStep=(?P<time>[-+0-9.eE]+), p0_eff=(?P<p0>[-+0-9.eE]+) Pa, "
    r"targets=(?P<targets>\d+), legacy_targets=(?P<legacy>\d+), "
    r"net_force=\((?P<fx>[-+0-9.eE]+),(?P<fy>[-+0-9.eE]+),(?P<fz>[-+0-9.eE]+)\) N, "
    r"total_abs_force=(?P<absforce>[-+0-9.eE]+) N, max_accel=(?P<maxaccel>[-+0-9.eE]+) m/s2, "
    r"com_accel=(?P<comaccel>[-+0-9.eE]+) m/s2, symmetry_residual=(?P<sym>[-+0-9.eE]+)"
)

EXT_RE = re.compile(
    r"step=(?P<step>\d+), fi_min=(?P<fi_min>[-+0-9.eE]+), fi_max=(?P<fi_max>[-+0-9.eE]+), "
    r"fi_mean=(?P<fi_mean>[-+0-9.eE]+), fi_threshold=(?P<fi_threshold>[-+0-9.eE]+), "
    r"fi_selected=(?P<fi_selected>\d+), class_interior=(?P<class_interior>\d+), "
    r"class_lateral=(?P<class_lateral>\d+), class_top=(?P<class_top>\d+), "
    r"class_bottom=(?P<class_bottom>\d+), class_edge=(?P<class_edge>\d+), "
    r"class_outside=(?P<class_outside>\d+), lateral_fi_selected=(?P<lateral_fi_selected>\d+), "
    r"cap_fi_selected=(?P<cap_fi_selected>\d+), "
    r"lateral_inward_radial_accel_mean=(?P<lat_accel_mean>[-+0-9.eE]+), "
    r"lateral_inward_radial_accel_max=(?P<lat_accel_max>[-+0-9.eE]+), "
    r"cap_abs_axial_accel_mean=(?P<cap_axial_mean>[-+0-9.eE]+), "
    r"cap_abs_axial_accel_max=(?P<cap_axial_max>[-+0-9.eE]+)"
)

PART_RE = re.compile(r"Part_(?P<idx>\d+)\s+(?P<time>[-+0-9.eE]+)")


def fnum(value: str) -> float:
    return float(value.strip().rstrip("."))


def read_partcsv(path: Path) -> tuple[list[str], list[dict[str, float]]]:
    with path.open("r", encoding="utf-8") as f:
        header = [h.strip() for h in f.readline().strip().strip(";").split(";")]
        rows = []
        for line in f:
            parts = [p.strip() for p in line.strip().strip(";").split(";")]
            if len(parts) < len(header):
                continue
            row = {}
            for key, val in zip(header, parts):
                try:
                    row[key] = float(val)
                except ValueError:
                    row[key] = math.nan
            rows.append(row)
    return header, rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def classify(pos: np.ndarray) -> np.ndarray:
    classes = []
    for x, y, z in pos:
        r = math.hypot(x, y)
        inaxis = -CAP <= z <= H + CAP
        radialnear = abs(r - R) <= EDGE
        top = H - CAP <= z <= H + CAP
        bottom = -CAP <= z <= CAP
        if (not inaxis) or r > R + EDGE:
            classes.append("outside")
        elif radialnear and (top or bottom):
            classes.append("edge")
        elif radialnear and z > CAP and z < H - CAP:
            classes.append("lateral")
        elif top:
            classes.append("top")
        elif bottom:
            classes.append("bottom")
        else:
            classes.append("interior")
    return np.asarray(classes, dtype=object)


def wendland_w(rr: float) -> float:
    q = rr / KERNEL_H
    if q < 0.0 or q > 2.0:
        return 0.0
    return WENDLAND_AWEN * (2.0 * q + 1.0) * ((1.0 - 0.5 * q) ** 4)


def compute_fi(pos: np.ndarray, rhop: np.ndarray) -> np.ndarray:
    fi = np.zeros(len(pos), dtype=float)
    for i in range(len(pos)):
        diff = pos - pos[i]
        rr = np.sqrt(np.sum(diff * diff, axis=1))
        mask = rr <= KERNEL_SIZE
        weights = np.array([wendland_w(r) for r in rr[mask]], dtype=float)
        fi[i] = float(np.sum((MASS_FLUID / rhop[mask]) * weights))
    return fi


def parse_run() -> tuple[dict[int, float], list[dict[str, float]], dict[str, float]]:
    rows_by_step: dict[int, dict[str, float]] = {}
    part_times = {0: 0.0}
    summary = {"code": math.nan, "excluded": math.nan, "steps": math.nan, "part_files": math.nan}
    run = OUT / "Run.out"
    for line in run.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "FlexibleConfiningStress CPU diagnostics" in line:
            m = CPU_RE.search(line)
            if m:
                d = {k: fnum(v) for k, v in m.groupdict().items()}
                d["step"] = int(d["step"])
                rows_by_step[int(d["step"])] = d
        elif "FlexibleConfiningStress extended diagnostics" in line:
            m = EXT_RE.search(line)
            if m:
                d = {k: fnum(v) for k, v in m.groupdict().items()}
                step = int(d["step"])
                d["step"] = step
                rows_by_step.setdefault(step, {"step": step}).update(d)
        elif line.startswith("Part_") and "particles successfully stored" not in line:
            m = PART_RE.search(line)
            if m:
                part_times[int(m.group("idx"))] = fnum(m.group("time"))
        elif "Excluded particles" in line:
            summary["excluded"] = fnum(line.split(":")[-1])
        elif "Steps of simulation" in line:
            summary["steps"] = fnum(line.split(":")[-1])
        elif "PART files" in line:
            summary["part_files"] = fnum(line.split(":")[-1])
        elif "Finished execution (code=" in line:
            summary["code"] = fnum(line.split("code=")[-1].split(")")[0])
    return part_times, [rows_by_step[k] for k in sorted(rows_by_step)], summary


def stress_metrics(sig: np.ndarray, pore: np.ndarray) -> dict[str, float]:
    # Sigma output is treated as skeleton/effective stress in the current branch.
    # Compression is negative in Sigma, so p' is reported positive in compression.
    mean_sig = np.nanmean(sig, axis=0)
    sxx, syy, szz, sxy, sxz, syz = mean_sig
    trace = sxx + syy + szz
    p_eff = -trace / 3.0
    dev = np.array([sxx - trace / 3.0, syy - trace / 3.0, szz - trace / 3.0, sxy, sxz, syz])
    j2_factor = dev[0] ** 2 + dev[1] ** 2 + dev[2] ** 2 + 2.0 * (dev[3] ** 2 + dev[4] ** 2 + dev[5] ** 2)
    q = math.sqrt(max(0.0, 1.5 * j2_factor))
    return {
        "sigma_xx_mean": float(sxx),
        "sigma_yy_mean": float(syy),
        "sigma_zz_mean": float(szz),
        "sigma_xy_mean": float(sxy),
        "sigma_xz_mean": float(sxz),
        "sigma_yz_mean": float(syz),
        "p_eff_proxy": float(p_eff),
        "q_proxy": float(q),
        "axial_stress_proxy": float(-szz),
        "radial_stress_proxy": float(-(sxx + syy) / 2.0),
        "mean_pore_pressure_for_total_proxy": float(np.nanmean(pore)),
    }


def region_masks(pos: np.ndarray, classes: np.ndarray) -> dict[str, np.ndarray]:
    radius = np.hypot(pos[:, 0], pos[:, 1])
    z = pos[:, 2]
    return {
        "center_core_small": (radius <= 0.25 * R) & (z >= 0.40 * H) & (z <= 0.60 * H),
        "center_core_medium": (radius <= 0.40 * R) & (z >= 0.30 * H) & (z <= 0.70 * H),
        "center_core_large": (radius <= 0.60 * R) & (z >= 0.20 * H) & (z <= 0.80 * H),
        "full_excluding_caps_edges": np.isin(classes, ["interior", "lateral"]),
        "zhao_measurement_cylinder": (radius <= 0.50 * R) & (z >= 0.25 * H) & (z <= 0.75 * H),
    }


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIGDIR / f"{name}.svg")
    plt.savefig(FIGDIR / f"{name}.png", dpi=180)
    plt.close()


part_times, conf_rows, run_summary = parse_run()
for row in conf_rows:
    row["case"] = CASE
write_csv(ROOT / "t4_confinement_diagnostics.csv", conf_rows)

part_files = sorted(DATA.glob("PartCsv_*.csv"))
all_headers: list[str] = []
initial_top_z = None
initial_height = None
initial_pos_by_id: dict[int, np.ndarray] = {}

frame_rows: list[dict[str, object]] = []
region_rows: list[dict[str, object]] = []
stress_rows: list[dict[str, object]] = []
pore_strain_rows: list[dict[str, object]] = []
fi_rows: list[dict[str, object]] = []
divvel_history: dict[str, list[tuple[float, float]]] = {}

for path in part_files:
    idx = int(path.stem.split("_")[-1])
    header, rows = read_partcsv(path)
    all_headers = header
    if not rows:
        continue
    pos = np.array([[r["Pos.x [m]"], r["Pos.y [m]"], r["Pos.z [m]"]] for r in rows], dtype=float)
    ids = np.array([int(r["Idp"]) for r in rows], dtype=int)
    vel = np.array([[r["Vel.x [m/s]"], r["Vel.y [m/s]"], r["Vel.z [m/s]"]] for r in rows], dtype=float)
    rhop = np.array([r["Rhop [kg/m^3]"] for r in rows], dtype=float)
    pore = np.array([r.get("PorePress", math.nan) for r in rows], dtype=float)
    excess = np.array([r.get("ExcessPorePress", math.nan) for r in rows], dtype=float)
    pprate = np.array([r.get("PorePressRate", math.nan) for r in rows], dtype=float)
    divvel = np.array([r.get("DivVel", math.nan) for r in rows], dtype=float)
    kplastic = np.array([r.get("Kplastic", math.nan) for r in rows], dtype=float)
    sig = np.array([
        [r["Sigma_kk.x"], r["Sigma_kk.y"], r["Sigma_kk.z"], r["Sigma_ij.x"], r["Sigma_ij.y"], r["Sigma_ij.z"]]
        for r in rows
    ], dtype=float)
    classes = classify(pos)
    fi = compute_fi(pos, rhop)
    time = part_times.get(idx, math.nan)
    top_mask = pos[:, 2] >= 0.80 * H
    if idx == 0:
        initial_top_z = float(np.nanmean(pos[top_mask, 2]))
        initial_height = float(np.nanmax(pos[:, 2]) - np.nanmin(pos[:, 2]))
        initial_pos_by_id = {int(i): pos[k].copy() for k, i in enumerate(ids)}
    top_z = float(np.nanmean(pos[top_mask, 2])) if np.any(top_mask) else math.nan
    height = float(np.nanmax(pos[:, 2]) - np.nanmin(pos[:, 2]))
    axial_strain_top = (-(top_z - initial_top_z) / H) if initial_top_z is not None else math.nan
    axial_strain_height = (-(height - initial_height) / initial_height) if initial_height else math.nan
    frame_rows.append({
        "case": CASE,
        "part": idx,
        "time": time,
        "particle_count": len(rows),
        "porepress_mean": float(np.nanmean(pore)),
        "excess_mean": float(np.nanmean(excess)),
        "porepressrate_mean": float(np.nanmean(pprate)),
        "divvel_mean": float(np.nanmean(divvel)),
        "velocity_max": float(np.nanmax(np.sqrt(np.sum(vel * vel, axis=1)))),
        "top_z_mean": top_z,
        "axial_strain_top_proxy": axial_strain_top,
        "axial_strain_height_proxy": axial_strain_height,
        "kplastic_max": float(np.nanmax(kplastic)),
        "fi_min": float(np.nanmin(fi)),
        "fi_mean": float(np.nanmean(fi)),
        "fi_median": float(np.nanmedian(fi)),
        "fi_p95": float(np.nanpercentile(fi, 95)),
        "fi_max": float(np.nanmax(fi)),
        "fi_selected_count": int(np.sum(fi <= 0.70)),
    })

    masks = region_masks(pos, classes)
    for region, mask in masks.items():
        count = int(np.sum(mask))
        if count <= 0:
            continue
        r_sig = sig[mask]
        r_pore = pore[mask]
        sm = stress_metrics(r_sig, r_pore)
        class_counts = {name: int(np.sum(classes[mask] == name)) for name in ["interior", "lateral", "top", "bottom", "edge", "outside"]}
        divvel_mean = float(np.nanmean(divvel[mask]))
        divvel_history.setdefault(region, []).append((time, divvel_mean))
        cumulative_vol_strain = 0.0
        hist = divvel_history[region]
        if len(hist) > 1:
            for (t0, v0), (t1, v1) in zip(hist[:-1], hist[1:]):
                cumulative_vol_strain += -0.5 * (v0 + v1) * (t1 - t0)
        row = {
            "case": CASE,
            "part": idx,
            "time": time,
            "region": region,
            "particle_count": count,
            "axial_strain_top_proxy": axial_strain_top,
            "axial_strain_height_proxy": axial_strain_height,
            "volumetric_strain_divvel_proxy": cumulative_vol_strain,
            "porepress_mean": float(np.nanmean(r_pore)),
            "porepress_std": float(np.nanstd(r_pore)),
            "excess_mean": float(np.nanmean(excess[mask])),
            "excess_std": float(np.nanstd(excess[mask])),
            "divvel_mean": divvel_mean,
            "divvel_std": float(np.nanstd(divvel[mask])),
            "porepressrate_mean": float(np.nanmean(pprate[mask])),
            "porepressrate_std": float(np.nanstd(pprate[mask])),
            "kplastic_max": float(np.nanmax(kplastic[mask])),
            "kplastic_mean": float(np.nanmean(kplastic[mask])),
            "fi_min": float(np.nanmin(fi[mask])),
            "fi_mean": float(np.nanmean(fi[mask])),
            "fi_median": float(np.nanmedian(fi[mask])),
            "fi_max": float(np.nanmax(fi[mask])),
            **sm,
            **{f"class_{k}_count": v for k, v in class_counts.items()},
        }
        region_rows.append(row)
        stress_rows.append({k: row[k] for k in [
            "case", "part", "time", "region", "particle_count",
            "axial_strain_top_proxy", "axial_strain_height_proxy",
            "volumetric_strain_divvel_proxy", "p_eff_proxy", "q_proxy",
            "axial_stress_proxy", "radial_stress_proxy",
            "sigma_xx_mean", "sigma_yy_mean", "sigma_zz_mean",
            "sigma_xy_mean", "sigma_xz_mean", "sigma_yz_mean",
            "mean_pore_pressure_for_total_proxy"
        ]})
        pore_strain_rows.append({k: row[k] for k in [
            "case", "part", "time", "region", "axial_strain_top_proxy",
            "axial_strain_height_proxy", "volumetric_strain_divvel_proxy",
            "porepress_mean", "porepress_std", "excess_mean", "porepressrate_mean",
            "divvel_mean"
        ]})
    if idx == 0:
        for idp, val, cls in zip(ids, fi, classes):
            fi_rows.append({"case": CASE, "part": idx, "idp": int(idp), "class": cls, "fi": float(val), "fi_selected": int(val <= 0.70)})

write_csv(ROOT / "t4_frame_metrics.csv", frame_rows)
write_csv(ROOT / "t4_measurement_region_sensitivity.csv", region_rows)
write_csv(ROOT / "t4_stress_path_metrics.csv", stress_rows)
write_csv(ROOT / "t4_pore_pressure_strain_metrics.csv", pore_strain_rows)
write_csv(ROOT / "t4_fi_particle_metrics.csv", fi_rows)

final = frame_rows[-1] if frame_rows else {}
case_summary = [{
    "case": CASE,
    **run_summary,
    "final_time": final.get("time", math.nan),
    "final_velocity_max": final.get("velocity_max", math.nan),
    "final_axial_strain_top_proxy": final.get("axial_strain_top_proxy", math.nan),
    "final_axial_strain_height_proxy": final.get("axial_strain_height_proxy", math.nan),
    "final_porepress_mean": final.get("porepress_mean", math.nan),
    "final_kplastic_max": final.get("kplastic_max", math.nan),
    "field_header": ";".join(all_headers),
}]
write_csv(ROOT / "t4_case_summary.csv", case_summary)

regions = ["center_core_small", "center_core_medium", "center_core_large", "full_excluding_caps_edges", "zhao_measurement_cylinder"]

plt.figure(figsize=(8, 4))
for region in regions:
    rows = [r for r in region_rows if r["region"] == region]
    plt.plot([r["time"] for r in rows], [r["porepress_mean"] for r in rows], marker="o", markersize=3, label=region)
plt.xlabel("time [s]")
plt.ylabel("mean pore pressure [Pa]")
plt.legend(fontsize=7)
savefig("t4_pore_pressure_vs_time_regions")

plt.figure(figsize=(8, 4))
for region in regions:
    rows = [r for r in region_rows if r["region"] == region]
    plt.plot([r["axial_strain_top_proxy"] for r in rows], [r["porepress_mean"] for r in rows], marker="o", markersize=3, label=region)
plt.xlabel("axial strain proxy [-]")
plt.ylabel("mean pore pressure [Pa]")
plt.legend(fontsize=7)
savefig("t4_pore_pressure_vs_axial_strain")

plt.figure(figsize=(7, 4))
for region in ["center_core_medium", "full_excluding_caps_edges", "zhao_measurement_cylinder"]:
    rows = [r for r in stress_rows if r["region"] == region]
    plt.plot([r["p_eff_proxy"] for r in rows], [r["q_proxy"] for r in rows], marker="o", markersize=3, label=region)
plt.xlabel("p' proxy, compression positive [Pa]")
plt.ylabel("q proxy [Pa]")
plt.legend(fontsize=7)
savefig("t4_pq_path_proxy")

plt.figure(figsize=(7, 4))
for region in ["center_core_medium", "full_excluding_caps_edges", "zhao_measurement_cylinder"]:
    rows = [r for r in stress_rows if r["region"] == region]
    plt.plot([r["axial_strain_top_proxy"] for r in rows], [r["q_proxy"] for r in rows], marker="o", markersize=3, label=region)
plt.xlabel("axial strain proxy [-]")
plt.ylabel("q proxy [Pa]")
plt.legend(fontsize=7)
savefig("t4_q_vs_axial_strain")

plt.figure(figsize=(7, 4))
for region in ["center_core_medium", "full_excluding_caps_edges", "zhao_measurement_cylinder"]:
    rows = [r for r in stress_rows if r["region"] == region]
    plt.plot([r["axial_strain_top_proxy"] for r in rows], [r["p_eff_proxy"] for r in rows], marker="o", markersize=3, label=region)
plt.xlabel("axial strain proxy [-]")
plt.ylabel("p' proxy [Pa]")
plt.legend(fontsize=7)
savefig("t4_p_eff_vs_axial_strain")

plt.figure(figsize=(7, 4))
plt.plot([r["time"] for r in frame_rows], [r["axial_strain_top_proxy"] for r in frame_rows], marker="o", markersize=3, label="top displacement")
plt.plot([r["time"] for r in frame_rows], [r["axial_strain_height_proxy"] for r in frame_rows], marker="s", markersize=3, label="height")
plt.xlabel("time [s]")
plt.ylabel("axial strain proxy [-]")
plt.legend(fontsize=8)
savefig("t4_axial_strain_vs_time")

plt.figure(figsize=(8, 4))
for region in ["center_core_medium", "full_excluding_caps_edges"]:
    rows = [r for r in region_rows if r["region"] == region]
    plt.plot([r["time"] for r in rows], [r["divvel_mean"] for r in rows], marker="o", markersize=3, label=f"{region} DivVel")
plt.xlabel("time [s]")
plt.ylabel("DivVel mean [1/s]")
plt.legend(fontsize=7)
savefig("t4_divvel_vs_time")

plt.figure(figsize=(8, 4))
for region in ["center_core_medium", "full_excluding_caps_edges"]:
    rows = [r for r in region_rows if r["region"] == region]
    plt.plot([r["time"] for r in rows], [r["porepressrate_mean"] for r in rows], marker="o", markersize=3, label=f"{region} PorePressRate")
plt.xlabel("time [s]")
plt.ylabel("PorePressRate mean [Pa/s]")
plt.legend(fontsize=7)
savefig("t4_porepressrate_vs_time")

plt.figure(figsize=(7, 4))
plt.plot([r["time"] for r in frame_rows], [r["kplastic_max"] for r in frame_rows], marker="o")
plt.xlabel("time [s]")
plt.ylabel("Kplastic max")
savefig("t4_kplastic_max_vs_time")

plt.figure(figsize=(7, 4))
plt.plot([r["time"] for r in conf_rows], [r["lat_accel_mean"] for r in conf_rows], marker="o", label="lateral inward accel")
plt.plot([r["time"] for r in conf_rows], [r["cap_axial_mean"] for r in conf_rows], marker="s", label="cap axial leakage")
plt.xlabel("time [s]")
plt.ylabel("acceleration diagnostic [m/s2]")
plt.legend(fontsize=8)
savefig("t4_confinement_accel_diagnostics")

plt.figure(figsize=(7, 4))
if fi_rows:
    plt.hist([r["fi"] for r in fi_rows], bins=np.linspace(0.35, 1.05, 18), alpha=0.7)
plt.axvline(0.70, color="k", linestyle="--", linewidth=1)
plt.xlabel("computed f_i at Part_0000")
plt.ylabel("particle count")
savefig("t4_fi_histogram")

plt.figure(figsize=(9, 4))
final_rows = [r for r in region_rows if r["part"] == max(rr["part"] for rr in region_rows)]
x = np.arange(len(final_rows))
plt.bar(x - 0.2, [r["porepress_mean"] for r in final_rows], 0.4, label="pore pressure")
plt.bar(x + 0.2, [r["p_eff_proxy"] for r in final_rows], 0.4, label="p' proxy")
plt.xticks(x, [r["region"] for r in final_rows], rotation=25, ha="right")
plt.ylabel("final metric [Pa]")
plt.legend(fontsize=8)
savefig("t4_measurement_region_sensitivity")

print(f"Wrote T4 metrics and figures under {ROOT}")
