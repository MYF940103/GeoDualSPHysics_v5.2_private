#!/usr/bin/env python3
"""T4f pore-pressure feedback stabilization diagnostics."""

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

CASES = [
    {"case": "CaseT4f_ConfOnly_FeedbackOffRef", "label": "feedback off", "kind": "reference", "scale": 0.0, "relax": 0.0, "limiter": 0},
    {"case": "CaseT4f_ConfOnly_FullFeedbackNoStab", "label": "full feedback", "kind": "unstabilized", "scale": 1.0, "relax": 0.0, "limiter": 0},
    {"case": "CaseT4f_ConfOnly_RelaxA02", "label": "relax 0.2", "kind": "relaxation", "scale": 1.0, "relax": 0.2, "limiter": 0},
    {"case": "CaseT4f_ConfOnly_CapR25A50", "label": "cap", "kind": "cap", "scale": 1.0, "relax": 0.0, "limiter": 3},
    {"case": "CaseT4f_ConfOnly_RelaxA02CapR25A50", "label": "relax 0.2 + cap", "kind": "relaxation+cap", "scale": 1.0, "relax": 0.2, "limiter": 3},
    {"case": "CaseT4f_ConfOnly_RelaxA02CapR5A10", "label": "relax 0.2 + tight cap", "kind": "targeted tight cap", "scale": 1.0, "relax": 0.2, "limiter": 3},
    {"case": "CaseT4f_AxialGentle_RelaxA02CapR25A50", "label": "axial smoke", "kind": "axial smoke", "scale": 1.0, "relax": 0.2, "limiter": 3},
]

R = 0.03
H = 0.10


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
        return {"mean": np.nan, "std": np.nan, "min": np.nan, "max": np.nan, "maxabs": np.nan}
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "maxabs": float(np.max(np.abs(values))),
    }


def parse_run_out(path: Path):
    text = path.read_text(errors="ignore")
    times = {0: 0.0}
    for line in text.splitlines():
        match = re.match(r"^\s*Part_(\d{4})\s+([0-9.Ee+\-]+)\s+\d+\s+\d+\s+", line)
        if match:
            times[int(match.group(1))] = fnum(match.group(2))

    def one(pattern, default=0.0):
        match = re.search(pattern, text)
        return fnum(match.group(1), default) if match else default

    warnings = []
    for match in re.finditer(r"DTs adjusted to DtMin \(t:([0-9.Ee+\-]+), nstep:([0-9]+)\)", text):
        warnings.append({"time": fnum(match.group(1)), "nstep": fnum(match.group(2)), "warning": "DtMin"})
    for match in re.finditer(r"excluded .* \(t:([0-9.Ee+\-]+), nstep:([0-9]+)\)", text, re.IGNORECASE):
        warnings.append({"time": fnum(match.group(1)), "nstep": fnum(match.group(2)), "warning": "excluded"})

    status = {
        "code": 0 if "Finished execution (code=0)" in text else 1,
        "excluded": one(r"Excluded particles\.+:\s+([0-9]+)"),
        "steps": one(r"Steps of simulation\.+:\s+([0-9]+)"),
        "part_files": one(r"PART files\.+:\s+([0-9]+)"),
        "dtmin_adjusted": one(r"DTs adjusted to DtMin\.+:\s+([0-9]+)"),
        "runtime_sec": one(r"Total Runtime\.+:\s+([0-9.Ee+\-]+)"),
    }

    conf_rows = []
    re_conf = re.compile(
        r"FlexibleConfiningStress CPU diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[-+0-9.Ee]+), p0_eff=(?P<p0_eff>[-+0-9.Ee]+) Pa, targets=(?P<targets>\d+), legacy_targets=(?P<legacy_targets>\d+), net_force=\((?P<net_fx>[-+0-9.Ee]+),(?P<net_fy>[-+0-9.Ee]+),(?P<net_fz>[-+0-9.Ee]+)\) N, total_abs_force=(?P<total_abs_force>[-+0-9.Ee]+) N, max_accel=(?P<max_accel>[-+0-9.Ee]+) m/s2, com_accel=(?P<com_accel>[-+0-9.Ee]+) m/s2, symmetry_residual=(?P<symmetry_residual>[-+0-9.Ee]+)"
    )
    re_ext = re.compile(
        r"FlexibleConfiningStress extended diagnostics: step=(?P<step>\d+), fi_min=(?P<fi_min>[-+0-9.Ee]+), fi_max=(?P<fi_max>[-+0-9.Ee]+), fi_mean=(?P<fi_mean>[-+0-9.Ee]+), fi_threshold=(?P<fi_threshold>[-+0-9.Ee]+), fi_selected=(?P<fi_selected>\d+), class_interior=(?P<class_interior>\d+), class_lateral=(?P<class_lateral>\d+), class_top=(?P<class_top>\d+), class_bottom=(?P<class_bottom>\d+), class_edge=(?P<class_edge>\d+), class_outside=(?P<class_outside>\d+), lateral_fi_selected=(?P<lateral_fi_selected>\d+), cap_fi_selected=(?P<cap_fi_selected>\d+), lateral_inward_radial_accel_mean=(?P<lat_accel_mean>[-+0-9.Ee]+), lateral_inward_radial_accel_max=(?P<lat_accel_max>[-+0-9.Ee]+), cap_abs_axial_accel_mean=(?P<cap_axial_mean>[-+0-9.Ee]+), cap_abs_axial_accel_max=(?P<cap_axial_max>[-+0-9.Ee]+)"
    )
    by_step = {}
    for match in re_conf.finditer(text):
        data = {key: fnum(value) for key, value in match.groupdict().items()}
        by_step[int(data["step"])] = data
    for match in re_ext.finditer(text):
        step = int(match.group("step"))
        by_step.setdefault(step, {"step": step, "time": np.nan})
        by_step[step].update({key: fnum(value) for key, value in match.groupdict().items()})
    conf_rows = [by_step[k] for k in sorted(by_step)]

    fb_rows = []
    re_fb = re.compile(
        r"PorePressureFeedback diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[-+0-9.Ee]+), factor=(?P<factor>[-+0-9.Ee]+), applied=(?P<applied>\d+), raw_max=(?P<raw_max>[-+0-9.Ee]+), raw_mean=(?P<raw_mean>[-+0-9.Ee]+), used_max=(?P<used_max>[-+0-9.Ee]+), used_mean=(?P<used_mean>[-+0-9.Ee]+), pre_accel_max=(?P<pre_accel_max>[-+0-9.Ee]+), used_to_reference_ratio_max=(?P<ratio_max>[-+0-9.Ee]+), confining_ref=(?P<confining_ref>[-+0-9.Ee]+), limited=(?P<limited>\d+), relaxed=(?P<relaxed>\d+), cap_min=(?P<cap_min>[-+0-9.Ee]+)"
    )
    re_fb_class = re.compile(
        r"PorePressureFeedback class diagnostics: step=(?P<step>\d+), lateral_used_max=(?P<lateral_used_max>[-+0-9.Ee]+), cap_edge_used_max=(?P<cap_edge_used_max>[-+0-9.Ee]+), interior_used_max=(?P<interior_used_max>[-+0-9.Ee]+)"
    )
    by_fb = {}
    for match in re_fb.finditer(text):
        data = {key: fnum(value) for key, value in match.groupdict().items()}
        by_fb[int(data["step"])] = data
    for match in re_fb_class.finditer(text):
        step = int(match.group("step"))
        by_fb.setdefault(step, {"step": step, "time": np.nan})
        by_fb[step].update({key: fnum(value) for key, value in match.groupdict().items()})
    fb_rows = [by_fb[k] for k in sorted(by_fb)]
    return times, status, warnings, conf_rows, fb_rows


def region_masks(rows):
    x, y, z = arr(rows, "Pos.x [m]"), arr(rows, "Pos.y [m]"), arr(rows, "Pos.z [m]")
    r = np.sqrt(x * x + y * y)
    return {
        "all": np.ones(len(rows), dtype=bool),
        "center_core": (r <= 0.015) & (z >= 0.025) & (z <= 0.075),
        "specimen_no_caps_edge": (r <= 0.025) & (z >= 0.02) & (z <= 0.08),
    }


def analyse_case(meta):
    case = meta["case"]
    out = ROOT / f"{case}_out"
    data_dir = out / "data"
    times, status, warnings, conf_rows, fb_rows = parse_run_out(out / "Run.out")
    frames = []
    region_rows = []
    for csv_path in sorted(data_dir.glob("PartCsv_*.csv")):
        part = int(csv_path.stem.split("_")[-1])
        rows = read_partcsv(csv_path)
        masks = region_masks(rows)
        p = arr(rows, "PorePress")
        ex = arr(rows, "ExcessPorePress")
        pr = arr(rows, "PorePressRate")
        div = arr(rows, "DivVel")
        vx, vy, vz = arr(rows, "Vel.x [m/s]"), arr(rows, "Vel.y [m/s]"), arr(rows, "Vel.z [m/s]")
        vel = np.sqrt(vx * vx + vy * vy + vz * vz)
        kp = arr(rows, "Kplastic")
        frame = {
            **meta,
            "time": times.get(part, np.nan),
            "part": part,
            "particle_count": len(rows),
            "porepress_mean": stats(p)["mean"],
            "porepress_min": stats(p)["min"],
            "porepress_max": stats(p)["max"],
            "excess_mean": stats(ex)["mean"],
            "porepressrate_mean": stats(pr)["mean"],
            "porepressrate_maxabs": stats(pr)["maxabs"],
            "divvel_mean": stats(div)["mean"],
            "divvel_maxabs": stats(div)["maxabs"],
            "velocity_max": stats(vel)["max"],
            "kplastic_max": stats(kp)["max"],
        }
        frames.append(frame)
        for region, mask in masks.items():
            rp, rex, rpr, rdiv, rvel, rkp = p[mask], ex[mask], pr[mask], div[mask], vel[mask], kp[mask]
            region_rows.append({
                **meta,
                "time": times.get(part, np.nan),
                "part": part,
                "region": region,
                "count": int(mask.sum()),
                "porepress_mean": stats(rp)["mean"],
                "porepress_min": stats(rp)["min"],
                "porepress_max": stats(rp)["max"],
                "excess_mean": stats(rex)["mean"],
                "porepressrate_mean": stats(rpr)["mean"],
                "porepressrate_maxabs": stats(rpr)["maxabs"],
                "divvel_mean": stats(rdiv)["mean"],
                "divvel_maxabs": stats(rdiv)["maxabs"],
                "velocity_max": stats(rvel)["max"],
                "kplastic_max": stats(rkp)["max"],
            })
    for row in conf_rows:
        row.update(meta)
    for row in fb_rows:
        row.update(meta)
    summary = {**meta, **status}
    if frames:
        summary.update({
            "porepressrate_maxabs": max(f["porepressrate_maxabs"] for f in frames),
            "velocity_max": max(f["velocity_max"] for f in frames),
            "kplastic_max": max(f["kplastic_max"] for f in frames),
            "final_porepress_mean": frames[-1]["porepress_mean"],
            "final_porepress_min": frames[-1]["porepress_min"],
            "final_porepress_max": frames[-1]["porepress_max"],
        })
    center = [r for r in region_rows if r["region"] == "center_core"]
    neg_center = [r for r in center if r["porepress_mean"] < 0]
    neg_any = [f for f in frames if f["porepress_mean"] < 0 or f["porepress_min"] < 0]
    summary.update({
        "center_reversal": 1 if neg_center else 0,
        "center_reversal_time": neg_center[0]["time"] if neg_center else "",
        "any_negative_pressure": 1 if neg_any else 0,
        "first_negative_time": neg_any[0]["time"] if neg_any else "",
        "dtmin_warning_count": sum(1 for w in warnings if w["warning"] == "DtMin"),
        "warning_count": len(warnings),
    })
    if fb_rows:
        summary.update({
            "feedback_raw_max": max(r.get("raw_max", 0.0) for r in fb_rows),
            "feedback_used_max": max(r.get("used_max", 0.0) for r in fb_rows),
            "feedback_limited_count_total": sum(r.get("limited", 0.0) for r in fb_rows),
            "feedback_relaxed_count_total": sum(r.get("relaxed", 0.0) for r in fb_rows),
        })
    else:
        summary.update({"feedback_raw_max": 0.0, "feedback_used_max": 0.0, "feedback_limited_count_total": 0.0, "feedback_relaxed_count_total": 0.0})
    return summary, frames, region_rows, warnings, conf_rows, fb_rows


def plot_series(rows, ykey, filename, ylabel=None, region=None):
    plt.figure(figsize=(7.2, 4.6))
    for meta in CASES:
        sub = [r for r in rows if r["case"] == meta["case"] and (region is None or r.get("region") == region)]
        if not sub:
            continue
        sub = sorted(sub, key=lambda r: r["time"])
        plt.plot([r["time"] for r in sub], [r.get(ykey, np.nan) for r in sub], marker="o", markersize=3, label=meta["label"])
    plt.xlabel("time [s]")
    plt.ylabel(ylabel or ykey)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("png", "svg"):
        plt.savefig(FIG / f"{filename}.{ext}", dpi=180)
    plt.close()


def main():
    summaries, frames, regions, warnings, confs, fbs = [], [], [], [], [], []
    for meta in CASES:
        summary, fr, rr, ww, cr, fb = analyse_case(meta)
        summaries.append(summary)
        frames.extend(fr)
        regions.extend(rr)
        warnings.extend({**meta, **w} for w in ww)
        confs.extend(cr)
        fbs.extend(fb)

    write_table(ROOT / "t4f_case_summary.csv", summaries)
    write_table(ROOT / "t4f_confinement_stability_metrics.csv", frames)
    write_table(ROOT / "t4f_measurement_region_metrics.csv", regions)
    write_table(ROOT / "t4f_dtmin_metrics.csv", warnings)
    write_table(ROOT / "t4f_confining_acceleration_metrics.csv", confs)
    write_table(ROOT / "t4f_feedback_acceleration_metrics.csv", fbs)
    write_table(ROOT / "t4f_feedback_limiter_metrics.csv", [
        {
            "case": r["case"],
            "label": r["label"],
            "time": r.get("time", np.nan),
            "factor": r.get("factor", 0.0),
            "limited": r.get("limited", 0.0),
            "relaxed": r.get("relaxed", 0.0),
            "raw_max": r.get("raw_max", 0.0),
            "used_max": r.get("used_max", 0.0),
            "ratio_max": r.get("ratio_max", 0.0),
            "cap_min": r.get("cap_min", 0.0),
        }
        for r in fbs
    ])
    write_table(ROOT / "t4f_reversal_metrics.csv", [
        {
            "case": s["case"],
            "label": s["label"],
            "center_reversal": s["center_reversal"],
            "center_reversal_time": s["center_reversal_time"],
            "any_negative_pressure": s["any_negative_pressure"],
            "first_negative_time": s["first_negative_time"],
            "final_porepress_mean": s.get("final_porepress_mean", np.nan),
            "final_porepress_min": s.get("final_porepress_min", np.nan),
        }
        for s in summaries
    ])
    write_table(ROOT / "t4f_axial_loading_metrics.csv", [
        r for r in regions if r["case"].startswith("CaseT4f_Axial")
    ])

    plot_series(fbs, "raw_max", "t4f_feedback_raw_vs_used_raw", "raw feedback accel max [m/s2]")
    plot_series(fbs, "used_max", "t4f_feedback_raw_vs_used_used", "used feedback accel max [m/s2]")
    plot_series(fbs, "limited", "t4f_limiter_activation", "limited particles")
    plot_series(frames, "porepressrate_maxabs", "t4f_porepressrate_maxabs", "|PorePressRate|max [Pa/s]")
    plot_series(frames, "porepress_mean", "t4f_porepress_mean", "mean PorePress [Pa]")
    plot_series(frames, "divvel_maxabs", "t4f_divvel_maxabs", "|DivVel|max [1/s]")
    plot_series(frames, "velocity_max", "t4f_velocity_max", "velocity max [m/s]")
    plot_series(regions, "porepress_mean", "t4f_center_core_porepress", "center-core PorePress [Pa]", region="center_core")
    plot_series(confs, "lat_accel_mean", "t4f_lateral_acceleration", "lateral inward accel mean [m/s2]")
    plot_series(confs, "cap_axial_max", "t4f_cap_leakage", "cap axial leakage max [m/s2]")
    plot_series(regions, "porepressrate_maxabs", "t4f_center_core_porepressrate", "center-core |PorePressRate|max [Pa/s]", region="center_core")


if __name__ == "__main__":
    main()
