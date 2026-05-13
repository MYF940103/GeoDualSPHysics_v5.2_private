#!/usr/bin/env python3
"""Postprocess T3 flexible confinement diagnostic smokes."""

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
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

CASES = [
    ("CaseT3_ConfinementOnly_Legacy", "confinement_only_legacy"),
    ("CaseT3_ConfinementOnly_Selected", "confinement_only_selected"),
    ("CaseT3_AxialConfinement_Selected", "axial_confinement_selected"),
]

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


def read_partcsv(path: Path) -> list[dict[str, float]]:
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
    return rows


def classify(x: float, y: float, z: float) -> str:
    r = math.hypot(x, y)
    inaxis = -CAP <= z <= H + CAP
    radialnear = abs(r - R) <= EDGE
    top = H - CAP <= z <= H + CAP
    bottom = -CAP <= z <= CAP
    if (not inaxis) or r > R + EDGE:
        return "outside"
    if radialnear and (top or bottom):
        return "edge"
    if radialnear and z > CAP and z < H - CAP:
        return "lateral"
    if top:
        return "top"
    if bottom:
        return "bottom"
    return "interior"


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


def parse_run(case: str) -> tuple[list[dict[str, float]], dict[int, float], dict[str, float]]:
    run = ROOT / f"{case}_out" / "Run.out"
    rows_by_step: dict[int, dict[str, float]] = {}
    part_times: dict[int, float] = {0: 0.0}
    summary = {"code": math.nan, "excluded": math.nan, "steps": math.nan, "part_files": math.nan}
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
    return [rows_by_step[k] for k in sorted(rows_by_step)], part_times, summary


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIGDIR / f"{name}.svg")
    plt.savefig(FIGDIR / f"{name}.png", dpi=180)
    plt.close()


force_rows: list[dict[str, object]] = []
fi_rows: list[dict[str, object]] = []
class_rows: list[dict[str, object]] = []
case_rows: list[dict[str, object]] = []
pore_rows: list[dict[str, object]] = []
kplastic_rows: list[dict[str, object]] = []
fi_particle_rows: list[dict[str, object]] = []
fi_values_for_hist: dict[str, np.ndarray] = {}

for case, label in CASES:
    diag_rows, part_times, summary = parse_run(case)
    for row in diag_rows:
        row = dict(row)
        row["case"] = case
        row["label"] = label
        force_rows.append(row)
        fi_rows.append({k: row.get(k, "") for k in [
            "case", "label", "step", "time", "fi_min", "fi_max", "fi_mean",
            "fi_threshold", "fi_selected", "lateral_fi_selected", "cap_fi_selected"
        ]})
        class_rows.append({k: row.get(k, "") for k in [
            "case", "label", "step", "time", "class_interior", "class_lateral",
            "class_top", "class_bottom", "class_edge", "class_outside", "targets", "legacy"
        ]})

    part_files = sorted((ROOT / f"{case}_out" / "data").glob("PartCsv_*.csv"))
    final_metrics = {}
    for path in part_files:
        idx = int(path.stem.split("_")[-1])
        rows = read_partcsv(path)
        if not rows:
            continue
        pos = np.array([[r["Pos.x [m]"], r["Pos.y [m]"], r["Pos.z [m]"]] for r in rows], dtype=float)
        rhop = np.array([r["Rhop [kg/m^3]"] for r in rows], dtype=float)
        pore = np.array([r.get("PorePress", math.nan) for r in rows], dtype=float)
        excess = np.array([r.get("ExcessPorePress", math.nan) for r in rows], dtype=float)
        kplastic = np.array([r.get("Kplastic", math.nan) for r in rows], dtype=float)
        velz = np.array([r.get("Vel.z [m/s]", math.nan) for r in rows], dtype=float)
        classes = np.array([classify(x, y, z) for x, y, z in pos], dtype=object)
        center_mask = (np.hypot(pos[:, 0], pos[:, 1]) <= 0.5 * R) & (pos[:, 2] >= 0.35 * H) & (pos[:, 2] <= 0.65 * H)
        top_mask = pos[:, 2] >= 0.8 * H
        lat_mask = classes == "lateral"
        cap_mask = np.isin(classes, ["top", "bottom", "edge"])
        time = part_times.get(idx, math.nan)
        pore_row = {
            "case": case,
            "label": label,
            "part": idx,
            "time": time,
            "porepress_mean_all": float(np.nanmean(pore)),
            "excess_mean_all": float(np.nanmean(excess)),
            "porepress_mean_center": float(np.nanmean(pore[center_mask])) if np.any(center_mask) else math.nan,
            "excess_mean_center": float(np.nanmean(excess[center_mask])) if np.any(center_mask) else math.nan,
            "porepress_mean_lateral": float(np.nanmean(pore[lat_mask])) if np.any(lat_mask) else math.nan,
            "porepress_mean_cap_edge": float(np.nanmean(pore[cap_mask])) if np.any(cap_mask) else math.nan,
            "top_z_mean": float(np.nanmean(pos[top_mask, 2])) if np.any(top_mask) else math.nan,
            "top_vz_mean": float(np.nanmean(velz[top_mask])) if np.any(top_mask) else math.nan,
        }
        pore_rows.append(pore_row)
        kplastic_rows.append({
            "case": case,
            "label": label,
            "part": idx,
            "time": time,
            "kplastic_max": float(np.nanmax(kplastic)),
            "kplastic_mean": float(np.nanmean(kplastic)),
        })
        if idx == 0:
            counts = {name: int(np.sum(classes == name)) for name in ["interior", "lateral", "top", "bottom", "edge", "outside"]}
            for name, count in counts.items():
                class_rows.append({"case": case, "label": label, "step": "static_part0", "class": name, "count": count})
            fi_static = compute_fi(pos, rhop)
            fi_values_for_hist[label] = fi_static
            for pidx, val in enumerate(fi_static):
                fi_particle_rows.append({
                    "case": case,
                    "label": label,
                    "idp": int(rows[pidx]["Idp"]),
                    "x": pos[pidx, 0],
                    "y": pos[pidx, 1],
                    "z": pos[pidx, 2],
                    "class": classes[pidx],
                    "fi": float(val),
                    "fi_selected": int(val <= 0.70),
                })
            fi_rows.append({
                "case": case,
                "label": label,
                "step": "static_part0_computed",
                "fi_min": float(np.nanmin(fi_static)),
                "fi_p05": float(np.nanpercentile(fi_static, 5)),
                "fi_mean": float(np.nanmean(fi_static)),
                "fi_median": float(np.nanmedian(fi_static)),
                "fi_p95": float(np.nanpercentile(fi_static, 95)),
                "fi_max": float(np.nanmax(fi_static)),
                "fi_threshold": 0.70,
                "fi_selected": int(np.sum(fi_static <= 0.70)),
            })
        final_metrics = {**pore_row, "kplastic_max": float(np.nanmax(kplastic))}

    case_rows.append({
        "case": case,
        "label": label,
        **summary,
        "final_porepress_mean_center": final_metrics.get("porepress_mean_center", math.nan),
        "final_excess_mean_center": final_metrics.get("excess_mean_center", math.nan),
        "final_porepress_mean_lateral": final_metrics.get("porepress_mean_lateral", math.nan),
        "final_top_z_mean": final_metrics.get("top_z_mean", math.nan),
        "final_top_vz_mean": final_metrics.get("top_vz_mean", math.nan),
        "kplastic_max": final_metrics.get("kplastic_max", math.nan),
    })

write_csv(ROOT / "t3_confining_force_metrics.csv", force_rows)
write_csv(ROOT / "t3_confining_fi_stats.csv", fi_rows)
write_csv(ROOT / "t3_confining_particle_classification.csv", class_rows)
write_csv(ROOT / "t3_confining_fi_particle_values.csv", fi_particle_rows)
write_csv(ROOT / "t3_case_summary.csv", case_rows)
write_csv(ROOT / "t3_pore_pressure_metrics.csv", pore_rows)
write_csv(ROOT / "t3_kplastic_metrics.csv", kplastic_rows)

if force_rows:
    labels = sorted(set(r["label"] for r in force_rows))
    plt.figure(figsize=(7, 4))
    for label in labels:
        rows = [r for r in force_rows if r["label"] == label]
        plt.plot([r["time"] for r in rows], [r["lat_accel_mean"] for r in rows], marker="o", label=label)
    plt.xlabel("time [s]")
    plt.ylabel("mean inward radial accel [m/s2]")
    plt.legend(fontsize=8)
    savefig("t3_lateral_radial_acceleration")

    plt.figure(figsize=(7, 4))
    for label in labels:
        rows = [r for r in force_rows if r["label"] == label]
        plt.plot([r["time"] for r in rows], [r["cap_axial_mean"] for r in rows], marker="o", label=label)
    plt.xlabel("time [s]")
    plt.ylabel("mean cap axial leakage [m/s2]")
    plt.legend(fontsize=8)
    savefig("t3_cap_axial_leakage")

    plt.figure(figsize=(7, 4))
    for label in labels:
        rows = [r for r in force_rows if r["label"] == label]
        plt.plot([r["time"] for r in rows], [r["sym"] for r in rows], marker="o", label=label)
    plt.xlabel("time [s]")
    plt.ylabel("net-force symmetry residual [-]")
    plt.legend(fontsize=8)
    savefig("t3_net_force_symmetry_residual")

    first_by_label = {label: next(r for r in force_rows if r["label"] == label) for label in labels}
    x = np.arange(len(labels))
    width = 0.22
    plt.figure(figsize=(8, 4))
    plt.bar(x - width, [first_by_label[l]["class_lateral"] for l in labels], width, label="lateral")
    plt.bar(x, [first_by_label[l]["class_edge"] for l in labels], width, label="edge")
    plt.bar(x + width, [first_by_label[l]["class_top"] + first_by_label[l]["class_bottom"] for l in labels], width, label="caps")
    plt.xticks(x, labels, rotation=20, ha="right")
    plt.ylabel("particle count")
    plt.legend(fontsize=8)
    savefig("t3_particle_class_counts")

    plt.figure(figsize=(7, 4))
    for label in labels:
        vals = fi_values_for_hist.get(label)
        if vals is not None:
            plt.hist(vals, bins=np.linspace(0.35, 1.05, 18), alpha=0.35, label=label)
    plt.axhline(0.70, color="k", linestyle="--", linewidth=1, label="f_i=0.70")
    plt.xlabel("computed f_i")
    plt.ylabel("particle count")
    plt.legend(fontsize=8)
    savefig("t3_fi_histogram")

if pore_rows:
    plt.figure(figsize=(7, 4))
    for label in sorted(set(r["label"] for r in pore_rows)):
        rows = [r for r in pore_rows if r["label"] == label]
        plt.plot([r["time"] for r in rows], [r["porepress_mean_center"] for r in rows], marker="o", label=label)
    plt.xlabel("time [s]")
    plt.ylabel("center pore pressure [Pa]")
    plt.legend(fontsize=8)
    savefig("t3_pore_pressure_response")

    plt.figure(figsize=(7, 4))
    for label in sorted(set(r["label"] for r in pore_rows)):
        rows = [r for r in pore_rows if r["label"] == label]
        plt.plot([r["time"] for r in rows], [r["top_z_mean"] for r in rows], marker="o", label=label)
    plt.xlabel("time [s]")
    plt.ylabel("top-region mean z [m]")
    plt.legend(fontsize=8)
    savefig("t3_axial_displacement_proxy")

    plt.figure(figsize=(7, 4))
    for label in sorted(set(r["label"] for r in pore_rows)):
        rows = [r for r in pore_rows if r["label"] == label]
        plt.plot([r["time"] for r in rows], [r["top_vz_mean"] for r in rows], marker="o", label=label)
    plt.xlabel("time [s]")
    plt.ylabel("top-region mean vz [m/s]")
    plt.legend(fontsize=8)
    savefig("t3_axial_velocity_proxy")

if kplastic_rows:
    plt.figure(figsize=(7, 4))
    for label in sorted(set(r["label"] for r in kplastic_rows)):
        rows = [r for r in kplastic_rows if r["label"] == label]
        plt.plot([r["time"] for r in rows], [r["kplastic_max"] for r in rows], marker="o", label=label)
    plt.xlabel("time [s]")
    plt.ylabel("Kplastic max")
    plt.legend(fontsize=8)
    savefig("t3_kplastic_max")

print(f"Wrote T3 metrics and figures under {ROOT}")
