#!/usr/bin/env python3
"""T4m all-surface isotropic confinement diagnostics."""

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
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

R = 0.03
H = 0.10
CAP = 0.015
EDGE = 0.015

CASES = [
    {
        "case": "CaseT4m_T4lReference_FeedbackOff",
        "label": "T4l lateral+cap, feedback off",
        "route": "lateral_cap",
        "feedback": "off",
    },
    {
        "case": "CaseT4m_AllSurface_FeedbackOff",
        "label": "all-surface f_i, feedback off",
        "route": "all_surface",
        "feedback": "off",
    },
    {
        "case": "CaseT4m_AllSurface_FeedbackDelayed",
        "label": "all-surface f_i, delayed feedback",
        "route": "all_surface",
        "feedback": "delayed",
    },
]

REGION_NAMES = {
    1: "interior",
    2: "lateral",
    3: "top_cap",
    4: "bottom_cap",
    5: "edge",
    6: "outside",
}


def fnum(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(str(value).strip().rstrip("."))
    except Exception:
        return default


def write_table(path: Path, rows, fieldnames=None):
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_partcsv(path: Path):
    with path.open(newline="") as f:
        reader = csv.reader(f, delimiter=";")
        header = [h.strip() for h in next(reader) if h.strip()]
        rows = []
        for raw in reader:
            vals = [v.strip() for v in raw[: len(header)]]
            if len(vals) != len(header):
                continue
            rows.append({key: fnum(value) for key, value in zip(header, vals)})
        return rows


def arr(rows, key):
    return np.array([row.get(key, 0.0) for row in rows], dtype=float)


def stats(values):
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "maxabs": 0.0}
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "maxabs": float(np.max(np.abs(values))),
    }


def classify(x, y, z):
    r = np.sqrt(x * x + y * y)
    s = z
    inaxis = (s >= -CAP) & (s <= H + CAP)
    radialnear = np.abs(r - R) <= EDGE
    top = (s >= H - CAP) & (s <= H + CAP)
    bottom = (s >= -CAP) & (s <= CAP)
    cls = np.ones_like(r, dtype=int)
    cls[(~inaxis) | (r > R + EDGE)] = 6
    cls[radialnear & (top | bottom)] = 5
    cls[radialnear & (s > CAP) & (s < H - CAP)] = 2
    cls[(cls == 1) & top] = 3
    cls[(cls == 1) & bottom] = 4
    return cls


def parse_runout(path: Path):
    text = path.read_text(errors="ignore") if path.exists() else ""
    times = {0: 0.0}
    for m in re.finditer(r"Part_(\d{4})\s+([0-9.eE+-]+)", text):
        times[int(m.group(1))] = fnum(m.group(2))
    code = None
    m = re.search(r"Finished execution \(code=(\d+)\)", text)
    if m:
        code = int(m.group(1))
    excluded = None
    m = re.search(r"Excluded particles\.*:\s+(\d+)", text)
    if m:
        excluded = int(m.group(1))
    dtmin = None
    m = re.search(r"DTs adjusted to DtMin\.*:\s+(\d+)", text)
    if m:
        dtmin = int(m.group(1))
    return {"text": text, "times": times, "code": code, "excluded": excluded, "dtmin": dtmin}


def parse_confinement_diag(text: str):
    rows = []
    pat = re.compile(
        r"FlexibleConfiningStress CPU diagnostics: step=(\d+), TimeStep=([0-9.eE+-]+), p0_eff=([0-9.eE+-]+).*?"
        r"targets=(\d+), legacy_targets=(\d+), net_force=\(([0-9.eE+-]+),([0-9.eE+-]+),([0-9.eE+-]+)\).*?"
        r"total_abs_force=([0-9.eE+-]+).*?max_accel=([0-9.eE+-]+).*?com_accel=([0-9.eE+-]+).*?symmetry_residual=([0-9.eE+-]+)"
    )
    ext = re.compile(
        r"FlexibleConfiningStress extended diagnostics: step=(\d+).*?"
        r"fi_min=([0-9.eE+-]+), fi_max=([0-9.eE+-]+), fi_mean=([0-9.eE+-]+), fi_threshold=([0-9.eE+-]+), "
        r"fi_selected=(\d+), class_interior=(\d+), class_lateral=(\d+), class_top=(\d+), class_bottom=(\d+), "
        r"class_edge=(\d+), class_outside=(\d+), lateral_fi_selected=(\d+), cap_fi_selected=(\d+), "
        r"lateral_inward_radial_accel_mean=([0-9.eE+-]+), lateral_inward_radial_accel_max=([0-9.eE+-]+), "
        r"cap_abs_axial_accel_mean=([0-9.eE+-]+), cap_abs_axial_accel_max=([0-9.eE+-]+)"
    )
    ext_by_step = {int(m.group(1)): m.groups()[1:] for m in ext.finditer(text)}
    for m in pat.finditer(text):
        step = int(m.group(1))
        row = {
            "step": step,
            "time": fnum(m.group(2)),
            "p0_eff": fnum(m.group(3)),
            "active_targets": int(m.group(4)),
            "legacy_targets": int(m.group(5)),
            "net_force_x": fnum(m.group(6)),
            "net_force_y": fnum(m.group(7)),
            "net_force_z": fnum(m.group(8)),
            "total_abs_force": fnum(m.group(9)),
            "max_accel": fnum(m.group(10)),
            "com_accel": fnum(m.group(11)),
            "symmetry_residual": fnum(m.group(12)),
        }
        if step in ext_by_step:
            vals = ext_by_step[step]
            keys = [
                "fi_min",
                "fi_max",
                "fi_mean",
                "fi_threshold",
                "fi_selected",
                "class_interior",
                "class_lateral",
                "class_top",
                "class_bottom",
                "class_edge",
                "class_outside",
                "lateral_fi_selected",
                "cap_fi_selected",
                "lateral_accel_mean",
                "lateral_accel_max",
                "cap_accel_mean",
                "cap_accel_max",
            ]
            for key, value in zip(keys, vals):
                row[key] = int(value) if key.startswith("class_") or key.endswith("_selected") else fnum(value)
        rows.append(row)
    return rows


def parse_cap_diag(text: str):
    rows = []
    pat = re.compile(
        r"CapConfiningStress CPU diagnostics: step=(\d+), TimeStep=([0-9.eE+-]+), p0_eff=([0-9.eE+-]+) Pa, "
        r"top_targets=(\d+), bottom_targets=(\d+), edge_skipped=(\d+), "
        r"top_accel_mean=([0-9.eE+-]+).*?bottom_accel_mean=([0-9.eE+-]+).*?"
        r"total_abs_force=([0-9.eE+-]+) N, com_accel=([0-9.eE+-]+) m/s2, symmetry_residual=([0-9.eE+-]+)"
    )
    for m in pat.finditer(text):
        rows.append(
            {
                "step": int(m.group(1)),
                "time": fnum(m.group(2)),
                "cap_p0_eff": fnum(m.group(3)),
                "cap_top_targets": int(m.group(4)),
                "cap_bottom_targets": int(m.group(5)),
                "cap_edge_skipped": int(m.group(6)),
                "cap_top_accel_mean": fnum(m.group(7)),
                "cap_bottom_accel_mean": fnum(m.group(8)),
                "cap_total_abs_force": fnum(m.group(9)),
                "cap_com_accel": fnum(m.group(10)),
                "cap_symmetry_residual": fnum(m.group(11)),
            }
        )
    return rows


def parse_feedback_diag(text: str):
    rows = []
    pat = re.compile(
        r"PorePressureFeedback diagnostics: step=(\d+), TimeStep=([0-9.eE+-]+), factor=([0-9.eE+-]+), "
        r"applied=(\d+), class_skipped=(\d+), raw_max=([0-9.eE+-]+), raw_mean=([0-9.eE+-]+), "
        r"used_max=([0-9.eE+-]+), used_mean=([0-9.eE+-]+).*?confining_ref=([0-9.eE+-]+), "
        r"limited=(\d+), relaxed=(\d+)"
    )
    for m in pat.finditer(text):
        rows.append(
            {
                "step": int(m.group(1)),
                "time": fnum(m.group(2)),
                "feedback_factor": fnum(m.group(3)),
                "feedback_applied": int(m.group(4)),
                "feedback_class_skipped": int(m.group(5)),
                "feedback_raw_max": fnum(m.group(6)),
                "feedback_raw_mean": fnum(m.group(7)),
                "feedback_used_max": fnum(m.group(8)),
                "feedback_used_mean": fnum(m.group(9)),
                "feedback_confining_ref": fnum(m.group(10)),
                "feedback_limited": int(m.group(11)),
                "feedback_relaxed": int(m.group(12)),
            }
        )
    return rows


def frame_metrics(case: dict, outdir: Path, run_info):
    frame_rows = []
    region_rows = []
    for csv_path in sorted((outdir / "data").glob("PartCsv_*.csv")):
        frame = int(csv_path.stem.split("_")[-1])
        rows = read_partcsv(csv_path)
        if not rows:
            continue
        x, y, z = arr(rows, "Pos.x [m]"), arr(rows, "Pos.y [m]"), arr(rows, "Pos.z [m]")
        r = np.sqrt(x * x + y * y)
        cls = classify(x, y, z)
        center = (r <= 0.015) & (z >= 0.025) & (z <= 0.075)
        vx, vy, vz = arr(rows, "Vel.x [m/s]"), arr(rows, "Vel.y [m/s]"), arr(rows, "Vel.z [m/s]")
        vel = np.sqrt(vx * vx + vy * vy + vz * vz)
        pw = arr(rows, "PorePress")
        ex = arr(rows, "ExcessPorePress")
        rate = arr(rows, "PorePressRate")
        divv = arr(rows, "DivVel")
        kplast = arr(rows, "Kplastic")
        sxx, syy, szz = arr(rows, "Sigma_kk.x"), arr(rows, "Sigma_kk.y"), arr(rows, "Sigma_kk.z")
        sxy, syz, sxz = arr(rows, "Sigma_ij.x"), arr(rows, "Sigma_ij.y"), arr(rows, "Sigma_ij.z")
        p_code = (sxx + syy + szz) / 3.0
        p_comp = -p_code
        dxx, dyy, dzz = sxx - p_code, syy - p_code, szz - p_code
        j2 = 0.5 * (dxx * dxx + dyy * dyy + dzz * dzz) + sxy * sxy + syz * syz + sxz * sxz
        q = np.sqrt(np.maximum(0.0, 3.0 * j2))
        base = {
            "case": case["case"],
            "label": case["label"],
            "route": case["route"],
            "feedback": case["feedback"],
            "frame": frame,
            "time": run_info["times"].get(frame, np.nan),
        }
        frame_rows.append(
            {
                **base,
                "particle_count": len(rows),
                "center_count": int(np.sum(center)),
                "velocity_max": stats(vel)["max"],
                "divvel_maxabs": stats(divv)["maxabs"],
                "porepress_min": stats(pw)["min"],
                "porepress_mean": stats(pw)["mean"],
                "porepress_center_mean": stats(pw[center])["mean"] if np.any(center) else 0.0,
                "excess_center_mean": stats(ex[center])["mean"] if np.any(center) else 0.0,
                "porepressrate_maxabs": stats(rate)["maxabs"],
                "porepressrate_center_mean": stats(rate[center])["mean"] if np.any(center) else 0.0,
                "negative_pressure_count": int(np.sum(pw < 0.0)),
                "kplastic_max": stats(kplast)["max"],
                "sigma_xx_mean": stats(sxx)["mean"],
                "sigma_yy_mean": stats(syy)["mean"],
                "sigma_zz_mean": stats(szz)["mean"],
                "p_eff_compression_proxy_mean": stats(p_comp)["mean"],
                "q_proxy_mean": stats(q)["mean"],
            }
        )
        for cid, name in REGION_NAMES.items():
            mask = cls == cid
            if not np.any(mask):
                continue
            region_rows.append(
                {
                    **base,
                    "region": name,
                    "region_count": int(np.sum(mask)),
                    "sigma_xx_mean": stats(sxx[mask])["mean"],
                    "sigma_yy_mean": stats(syy[mask])["mean"],
                    "sigma_zz_mean": stats(szz[mask])["mean"],
                    "p_eff_compression_proxy_mean": stats(p_comp[mask])["mean"],
                    "q_proxy_mean": stats(q[mask])["mean"],
                    "porepress_mean": stats(pw[mask])["mean"],
                    "porepress_min": stats(pw[mask])["min"],
                    "porepressrate_maxabs": stats(rate[mask])["maxabs"],
                    "divvel_maxabs": stats(divv[mask])["maxabs"],
                    "velocity_max": stats(vel[mask])["max"],
                }
            )
    return frame_rows, region_rows


def plot_series(name, rows, ykey, ylabel):
    plt.figure(figsize=(7.0, 4.2))
    for case in CASES:
        cr = [r for r in rows if r["case"] == case["case"]]
        if not cr:
            continue
        plt.plot([r["time"] for r in cr], [r.get(ykey, 0.0) for r in cr], marker="o", ms=3, label=case["label"])
    plt.xlabel("time [s]")
    plt.ylabel(ylabel)
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIG / f"{name}.{ext}", dpi=180)
    plt.close()


def plot_region_q(region_rows):
    plt.figure(figsize=(7.0, 4.2))
    for region in ("interior", "lateral", "top_cap", "bottom_cap", "edge"):
        rr = [r for r in region_rows if r["case"] == "CaseT4m_AllSurface_FeedbackOff" and r["region"] == region]
        if rr:
            plt.plot([r["time"] for r in rr], [r["q_proxy_mean"] for r in rr], marker="o", ms=3, label=region)
    plt.xlabel("time [s]")
    plt.ylabel("region q proxy [Pa]")
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIG / f"t4m_region_q_all_surface_feedback_off.{ext}", dpi=180)
    plt.close()


def plot_force_diag(conf_rows):
    for key, ylabel, name in [
        ("active_targets", "active confinement targets", "t4m_fi_selected_targets"),
        ("lateral_accel_mean", "lateral inward accel [m/s2]", "t4m_lateral_acceleration"),
        ("cap_accel_mean", "cap axial accel [m/s2]", "t4m_cap_acceleration"),
        ("symmetry_residual", "force symmetry residual", "t4m_force_symmetry_residual"),
    ]:
        plt.figure(figsize=(7.0, 4.2))
        for case in CASES:
            cr = [r for r in conf_rows if r["case"] == case["case"]]
            if cr:
                plt.plot([r["time"] for r in cr], [r.get(key, 0.0) for r in cr], marker="o", ms=3, label=case["label"])
        plt.xlabel("time [s]")
        plt.ylabel(ylabel)
        plt.legend(fontsize=8)
        plt.tight_layout()
        for ext in ("svg", "png"):
            plt.savefig(FIG / f"{name}.{ext}", dpi=180)
        plt.close()


def main():
    frame_rows = []
    region_rows = []
    conf_rows = []
    feedback_rows = []
    cap_rows = []
    summary_rows = []

    for case in CASES:
        outdir = ROOT / f"{case['case']}_out"
        run_info = parse_runout(outdir / "Run.out")
        frames, regions = frame_metrics(case, outdir, run_info)
        frame_rows.extend(frames)
        region_rows.extend(regions)

        conf = parse_confinement_diag(run_info["text"])
        cap = parse_cap_diag(run_info["text"])
        feedback = parse_feedback_diag(run_info["text"])
        for collection in (conf, cap, feedback):
            for row in collection:
                row.update({"case": case["case"], "label": case["label"], "route": case["route"], "feedback": case["feedback"]})
        conf_rows.extend(conf)
        cap_rows.extend(cap)
        feedback_rows.extend(feedback)

        final = frames[-1] if frames else {}
        conf_last = conf[-1] if conf else {}
        cap_last = cap[-1] if cap else {}
        summary_rows.append(
            {
                "case": case["case"],
                "label": case["label"],
                "route": case["route"],
                "feedback": case["feedback"],
                "code": run_info["code"],
                "excluded": run_info["excluded"],
                "dtmin_adjustments": run_info["dtmin"],
                "frames": len(frames),
                "final_time": final.get("time", 0.0),
                "kplastic_max": max((r["kplastic_max"] for r in frames), default=0.0),
                "velocity_max": max((r["velocity_max"] for r in frames), default=0.0),
                "divvel_maxabs": max((r["divvel_maxabs"] for r in frames), default=0.0),
                "porepressrate_maxabs": max((r["porepressrate_maxabs"] for r in frames), default=0.0),
                "porepress_min": min((r["porepress_min"] for r in frames), default=0.0),
                "negative_pressure_max_count": max((r["negative_pressure_count"] for r in frames), default=0),
                "final_porepress_center_mean": final.get("porepress_center_mean", 0.0),
                "final_porepress_mean": final.get("porepress_mean", 0.0),
                "final_p_eff_compression_proxy_mean": final.get("p_eff_compression_proxy_mean", 0.0),
                "final_q_proxy_mean": final.get("q_proxy_mean", 0.0),
                "active_targets": conf_last.get("active_targets", 0),
                "fi_selected": conf_last.get("fi_selected", 0),
                "lateral_fi_selected": conf_last.get("lateral_fi_selected", 0),
                "cap_fi_selected": conf_last.get("cap_fi_selected", 0),
                "lateral_accel_mean": conf_last.get("lateral_accel_mean", 0.0),
                "cap_accel_mean": conf_last.get("cap_accel_mean", 0.0),
                "cap_support_top_targets": cap_last.get("cap_top_targets", 0),
                "cap_support_bottom_targets": cap_last.get("cap_bottom_targets", 0),
                "feedback_used_max": max((r["feedback_used_max"] for r in feedback), default=0.0),
            }
        )

    write_table(ROOT / "t4m_case_summary.csv", summary_rows)
    write_table(ROOT / "t4m_hydrostatic_equilibrium_metrics.csv", frame_rows)
    write_table(ROOT / "t4m_region_stress_metrics.csv", region_rows)
    write_table(ROOT / "t4m_confinement_force_balance.csv", conf_rows + cap_rows)
    write_table(ROOT / "t4m_feedback_stability_metrics.csv", feedback_rows)

    plot_series("t4m_p_eff_proxy_vs_time", frame_rows, "p_eff_compression_proxy_mean", "compression p' proxy [Pa]")
    plot_series("t4m_q_proxy_vs_time", frame_rows, "q_proxy_mean", "q proxy [Pa]")
    plot_series("t4m_sigma_xx_vs_time", frame_rows, "sigma_xx_mean", "mean sigma_xx [Pa]")
    plot_series("t4m_sigma_yy_vs_time", frame_rows, "sigma_yy_mean", "mean sigma_yy [Pa]")
    plot_series("t4m_sigma_zz_vs_time", frame_rows, "sigma_zz_mean", "mean sigma_zz [Pa]")
    plot_region_q(region_rows)
    plot_series("t4m_velocity_max_vs_time", frame_rows, "velocity_max", "velocity max [m/s]")
    plot_series("t4m_divvel_maxabs_vs_time", frame_rows, "divvel_maxabs", "|DivVel| max [1/s]")
    plot_series("t4m_porepressrate_maxabs_vs_time", frame_rows, "porepressrate_maxabs", "|PorePressRate| max [Pa/s]")
    plot_series("t4m_pore_pressure_center_vs_time", frame_rows, "porepress_center_mean", "center pore pressure [Pa]")
    plot_series("t4m_negative_pressure_count_vs_time", frame_rows, "negative_pressure_count", "negative pressure count")
    plot_force_diag(conf_rows)


if __name__ == "__main__":
    main()
