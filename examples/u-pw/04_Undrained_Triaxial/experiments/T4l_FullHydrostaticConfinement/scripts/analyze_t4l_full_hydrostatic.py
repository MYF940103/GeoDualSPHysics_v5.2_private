#!/usr/bin/env python3
"""T4l full hydrostatic confinement staging diagnostics."""

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

CASES = [
    {
        "case": "CaseT4l_CurrentMismatch_FeedbackOff",
        "label": "lateral only, feedback off",
        "cap": "off",
        "feedback": "off",
        "axial": "no",
    },
    {
        "case": "CaseT4l_FullHydrostatic_FeedbackOff",
        "label": "full support, feedback off",
        "cap": "on",
        "feedback": "off",
        "axial": "no",
    },
    {
        "case": "CaseT4l_FullHydrostatic_FeedbackDelayed",
        "label": "full support, delayed feedback",
        "cap": "on",
        "feedback": "delayed",
        "axial": "no",
    },
]


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
            if not raw:
                continue
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
        r"targets=(\d+).*?max_accel=([0-9.eE+-]+).*?com_accel=([0-9.eE+-]+).*?symmetry_residual=([0-9.eE+-]+)"
    )
    ext = re.compile(
        r"FlexibleConfiningStress extended diagnostics: step=(\d+).*?"
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
            "lateral_max_accel": fnum(m.group(5)),
            "com_accel": fnum(m.group(6)),
            "symmetry_residual": fnum(m.group(7)),
        }
        if step in ext_by_step:
            vals = ext_by_step[step]
            row.update(
                {
                    "lateral_accel_mean": fnum(vals[0]),
                    "lateral_accel_max": fnum(vals[1]),
                    "cap_axial_leakage_mean": fnum(vals[2]),
                    "cap_axial_leakage_max": fnum(vals[3]),
                }
            )
        rows.append(row)
    return rows


def parse_cap_diag(text: str):
    rows = []
    pat = re.compile(
        r"CapConfiningStress CPU diagnostics: step=(\d+), TimeStep=([0-9.eE+-]+), p0_eff=([0-9.eE+-]+) Pa, "
        r"top_targets=(\d+), bottom_targets=(\d+), edge_skipped=(\d+), "
        r"top_accel_mean=([0-9.eE+-]+), top_accel_max=([0-9.eE+-]+), "
        r"bottom_accel_mean=([0-9.eE+-]+), bottom_accel_max=([0-9.eE+-]+), "
        r"net_force=\(([0-9.eE+-]+),([0-9.eE+-]+),([0-9.eE+-]+)\) N, "
        r"total_abs_force=([0-9.eE+-]+) N, com_accel=([0-9.eE+-]+) m/s2, symmetry_residual=([0-9.eE+-]+)"
    )
    for m in pat.finditer(text):
        rows.append(
            {
                "step": int(m.group(1)),
                "time": fnum(m.group(2)),
                "p0_eff": fnum(m.group(3)),
                "top_targets": int(m.group(4)),
                "bottom_targets": int(m.group(5)),
                "edge_skipped": int(m.group(6)),
                "top_accel_mean": fnum(m.group(7)),
                "top_accel_max": fnum(m.group(8)),
                "bottom_accel_mean": fnum(m.group(9)),
                "bottom_accel_max": fnum(m.group(10)),
                "net_force_x": fnum(m.group(11)),
                "net_force_y": fnum(m.group(12)),
                "net_force_z": fnum(m.group(13)),
                "total_abs_force": fnum(m.group(14)),
                "com_accel": fnum(m.group(15)),
                "symmetry_residual": fnum(m.group(16)),
            }
        )
    return rows


def parse_feedback_diag(text: str):
    rows = []
    pat = re.compile(
        r"PorePressureFeedback diagnostics: step=(\d+), TimeStep=([0-9.eE+-]+), factor=([0-9.eE+-]+), applied=(\d+), "
        r"class_skipped=(\d+), raw_max=([0-9.eE+-]+), raw_mean=([0-9.eE+-]+), used_max=([0-9.eE+-]+), "
        r"used_mean=([0-9.eE+-]+).*?limited=(\d+), relaxed=(\d+)"
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
                "feedback_limited": int(m.group(10)),
                "feedback_relaxed": int(m.group(11)),
            }
        )
    return rows


def frame_metrics(case: str, label: str, outdir: Path, run_info):
    rows = []
    for csv_path in sorted((outdir / "data").glob("PartCsv_*.csv")):
        frame = int(csv_path.stem.split("_")[-1])
        part = read_partcsv(csv_path)
        if not part:
            continue
        x, y, z = arr(part, "Pos.x [m]"), arr(part, "Pos.y [m]"), arr(part, "Pos.z [m]")
        r = np.sqrt(x * x + y * y)
        center = (r <= 0.015) & (z >= 0.025) & (z <= 0.075)
        if not np.any(center):
            center = np.ones_like(r, dtype=bool)
        vx, vy, vz = arr(part, "Vel.x [m/s]"), arr(part, "Vel.y [m/s]"), arr(part, "Vel.z [m/s]")
        vel = np.sqrt(vx * vx + vy * vy + vz * vz)
        pw = arr(part, "PorePress")
        ex = arr(part, "ExcessPorePress")
        rate = arr(part, "PorePressRate")
        divv = arr(part, "DivVel")
        kplast = arr(part, "Kplastic")
        sxx, syy, szz = arr(part, "Sigma_kk.x"), arr(part, "Sigma_kk.y"), arr(part, "Sigma_kk.z")
        sxy, syz, sxz = arr(part, "Sigma_ij.x"), arr(part, "Sigma_ij.y"), arr(part, "Sigma_ij.z")
        p_code = (sxx + syy + szz) / 3.0
        p_comp = -p_code
        dxx, dyy, dzz = sxx - p_code, syy - p_code, szz - p_code
        j2 = 0.5 * (dxx * dxx + dyy * dyy + dzz * dzz) + sxy * sxy + syz * syz + sxz * sxz
        q = np.sqrt(np.maximum(0.0, 3.0 * j2))
        row = {
            "case": case,
            "label": label,
            "frame": frame,
            "time": run_info["times"].get(frame, np.nan),
            "particle_count": len(part),
            "center_count": int(np.sum(center)),
            "velocity_max": stats(vel)["max"],
            "divvel_maxabs": stats(divv)["maxabs"],
            "divvel_center_mean": stats(divv[center])["mean"],
            "porepress_min": stats(pw)["min"],
            "porepress_max": stats(pw)["max"],
            "porepress_mean": stats(pw)["mean"],
            "porepress_center_mean": stats(pw[center])["mean"],
            "excess_center_mean": stats(ex[center])["mean"],
            "porepressrate_maxabs": stats(rate)["maxabs"],
            "porepressrate_center_mean": stats(rate[center])["mean"],
            "negative_pressure_count": int(np.sum(pw < 0.0)),
            "kplastic_max": stats(kplast)["max"],
            "sigma_xx_mean": stats(sxx)["mean"],
            "sigma_yy_mean": stats(syy)["mean"],
            "sigma_zz_mean": stats(szz)["mean"],
            "p_eff_compression_proxy_mean": stats(p_comp)["mean"],
            "q_proxy_mean": stats(q)["mean"],
        }
        rows.append(row)
    return rows


def make_fig(name, rows, ykey, ylabel):
    plt.figure(figsize=(7.0, 4.2))
    for c in CASES:
        cr = [r for r in rows if r["case"] == c["case"]]
        if not cr:
            continue
        plt.plot([r["time"] for r in cr], [r.get(ykey, 0.0) for r in cr], marker="o", ms=3, label=c["label"])
    plt.xlabel("time [s]")
    plt.ylabel(ylabel)
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIG / f"{name}.{ext}", dpi=180)
    plt.close()


def make_diag_fig(name, diag_rows, ykey, ylabel):
    plt.figure(figsize=(7.0, 4.2))
    for c in CASES:
        cr = [r for r in diag_rows if r["case"] == c["case"]]
        if not cr:
            continue
        plt.plot([r["time"] for r in cr], [r.get(ykey, 0.0) for r in cr], marker="o", ms=3, label=c["label"])
    plt.xlabel("time [s]")
    plt.ylabel(ylabel)
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIG / f"{name}.{ext}", dpi=180)
    plt.close()


def main():
    frame_rows = []
    conf_rows = []
    cap_rows = []
    feedback_rows = []
    summary_rows = []
    stress_rows = []

    for case in CASES:
        outdir = ROOT / f"{case['case']}_out"
        run_info = parse_runout(outdir / "Run.out")
        rows = frame_metrics(case["case"], case["label"], outdir, run_info)
        frame_rows.extend(rows)
        conf = parse_confinement_diag(run_info["text"])
        cap = parse_cap_diag(run_info["text"])
        fb = parse_feedback_diag(run_info["text"])
        for row in conf:
            row.update({"case": case["case"], "label": case["label"]})
        for row in cap:
            row.update({"case": case["case"], "label": case["label"]})
        for row in fb:
            row.update({"case": case["case"], "label": case["label"]})
        conf_rows.extend(conf)
        cap_rows.extend(cap)
        feedback_rows.extend(fb)

        final = rows[-1] if rows else {}
        ppr_max = max((r["porepressrate_maxabs"] for r in rows), default=0.0)
        vel_max = max((r["velocity_max"] for r in rows), default=0.0)
        div_max = max((r["divvel_maxabs"] for r in rows), default=0.0)
        min_pw = min((r["porepress_min"] for r in rows), default=0.0)
        neg_any = max((r["negative_pressure_count"] for r in rows), default=0)
        kplast = max((r["kplastic_max"] for r in rows), default=0.0)
        cap_last = cap[-1] if cap else {}
        conf_last = conf[-1] if conf else {}
        fb_max = max((r["feedback_used_max"] for r in fb), default=0.0)
        summary_rows.append(
            {
                "case": case["case"],
                "label": case["label"],
                "cap_support": case["cap"],
                "feedback": case["feedback"],
                "axial": case["axial"],
                "code": run_info["code"],
                "excluded": run_info["excluded"],
                "dtmin_adjustments": run_info["dtmin"],
                "frames": len(rows),
                "final_time": final.get("time", 0.0),
                "kplastic_max": kplast,
                "velocity_max": vel_max,
                "divvel_maxabs": div_max,
                "porepressrate_maxabs": ppr_max,
                "porepress_min": min_pw,
                "negative_pressure_max_count": neg_any,
                "final_porepress_center_mean": final.get("porepress_center_mean", 0.0),
                "final_porepress_mean": final.get("porepress_mean", 0.0),
                "final_p_eff_compression_proxy_mean": final.get("p_eff_compression_proxy_mean", 0.0),
                "final_q_proxy_mean": final.get("q_proxy_mean", 0.0),
                "lateral_active_targets": conf_last.get("active_targets", 0),
                "lateral_accel_mean_logged": conf_last.get("lateral_accel_mean", 0.0),
                "cap_top_targets": cap_last.get("top_targets", 0),
                "cap_bottom_targets": cap_last.get("bottom_targets", 0),
                "cap_edge_skipped": cap_last.get("edge_skipped", 0),
                "cap_top_accel_mean_logged": cap_last.get("top_accel_mean", 0.0),
                "cap_bottom_accel_mean_logged": cap_last.get("bottom_accel_mean", 0.0),
                "cap_symmetry_residual": cap_last.get("symmetry_residual", 0.0),
                "feedback_used_max": fb_max,
            }
        )
        for r in rows:
            stress_rows.append(
                {
                    "case": r["case"],
                    "label": r["label"],
                    "frame": r["frame"],
                    "time": r["time"],
                    "sigma_xx_mean": r["sigma_xx_mean"],
                    "sigma_yy_mean": r["sigma_yy_mean"],
                    "sigma_zz_mean": r["sigma_zz_mean"],
                    "p_eff_compression_proxy_mean": r["p_eff_compression_proxy_mean"],
                    "q_proxy_mean": r["q_proxy_mean"],
                }
            )

    write_table(ROOT / "t4l_case_summary.csv", summary_rows)
    write_table(ROOT / "t4l_initial_stress_balance_metrics.csv", stress_rows)
    write_table(ROOT / "t4l_cap_support_metrics.csv", cap_rows)
    write_table(ROOT / "t4l_lateral_confinement_metrics.csv", conf_rows)
    write_table(ROOT / "t4l_feedback_stability_metrics.csv", feedback_rows)
    write_table(ROOT / "t4l_equilibrium_metrics.csv", frame_rows)
    write_table(ROOT / "t4l_axial_smoke_metrics.csv", [])

    make_fig("t4l_initial_stress_components_sigma_xx", frame_rows, "sigma_xx_mean", "mean sigma_xx [Pa]")
    make_fig("t4l_p_eff_proxy_vs_time", frame_rows, "p_eff_compression_proxy_mean", "compression p' proxy [Pa]")
    make_fig("t4l_q_proxy_vs_time", frame_rows, "q_proxy_mean", "q proxy [Pa]")
    make_diag_fig("t4l_cap_support_acceleration", cap_rows, "top_accel_mean", "top cap acceleration [m/s2]")
    make_diag_fig("t4l_lateral_confinement_acceleration", conf_rows, "lateral_accel_mean", "lateral inward acceleration [m/s2]")
    make_fig("t4l_velocity_max_vs_time", frame_rows, "velocity_max", "velocity max [m/s]")
    make_fig("t4l_divvel_maxabs_vs_time", frame_rows, "divvel_maxabs", "|DivVel| max [1/s]")
    make_fig("t4l_porepressrate_maxabs_vs_time", frame_rows, "porepressrate_maxabs", "|PorePressRate| max [Pa/s]")
    make_fig("t4l_pore_pressure_center_vs_time", frame_rows, "porepress_center_mean", "center pore pressure [Pa]")
    make_fig("t4l_negative_pressure_count_vs_time", frame_rows, "negative_pressure_count", "negative-pressure particle count")
    make_diag_fig("t4l_cap_leakage_vs_time", conf_rows, "cap_axial_leakage_max", "flexible cap leakage max [m/s2]")


if __name__ == "__main__":
    main()
