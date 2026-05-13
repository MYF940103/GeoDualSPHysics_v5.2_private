#!/usr/bin/env python3
"""T4k initial hydrostatic effective stress and confinement equilibrium audit."""

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
    {"case": "CaseT4k_InitialStressOnly_FeedbackOff", "label": "initial stress only", "feedback": "off", "flex": "off", "axial": "no"},
    {"case": "CaseT4k_InitialStressPlusConf_FeedbackOff", "label": "initial stress + conf, fb off", "feedback": "off", "flex": "selected", "axial": "no"},
    {"case": "CaseT4k_InitialStressPlusConf_FeedbackDelayed", "label": "initial stress + conf, delayed fb", "feedback": "delayed", "flex": "selected", "axial": "no"},
    {"case": "CaseT4k_InitialStressPlusConf_AxialSmoke", "label": "optional axial smoke", "feedback": "delayed", "flex": "selected", "axial": "yes"},
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
    kplast = 0.0
    return {"text": text, "times": times, "code": code, "excluded": excluded, "dtmin": dtmin, "kplastic_log": kplast}


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
            "max_confining_accel": fnum(m.group(5)),
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
        core = (r <= 0.015) & (z >= 0.025) & (z <= 0.075)
        if not np.any(core):
            core = np.ones_like(r, dtype=bool)
        vx, vy, vz = arr(part, "Vel.x [m/s]"), arr(part, "Vel.y [m/s]"), arr(part, "Vel.z [m/s]")
        vel = np.sqrt(vx * vx + vy * vy + vz * vz)
        pw = arr(part, "PorePress")
        ex = arr(part, "ExcessPorePress")
        rate = arr(part, "PorePressRate")
        divv = arr(part, "DivVel")
        kplast = arr(part, "Kplastic")
        sxx, syy, szz = arr(part, "Sigma_kk.x"), arr(part, "Sigma_kk.y"), arr(part, "Sigma_kk.z")
        sxy, syz, sxz = arr(part, "Sigma_ij.x"), arr(part, "Sigma_ij.y"), arr(part, "Sigma_ij.z")
        p_eff = (sxx + syy + szz) / 3.0
        dxx, dyy, dzz = sxx - p_eff, syy - p_eff, szz - p_eff
        j2 = 0.5 * (dxx * dxx + dyy * dyy + dzz * dzz) + sxy * sxy + syz * syz + sxz * sxz
        q = np.sqrt(np.maximum(0.0, 3.0 * j2))
        row = {
            "case": case,
            "label": label,
            "frame": frame,
            "time": run_info["times"].get(frame, np.nan),
            "particle_count": len(part),
            "center_count": int(np.sum(core)),
            "velocity_max": stats(vel)["max"],
            "divvel_maxabs": stats(divv)["maxabs"],
            "divvel_center_mean": stats(divv[core])["mean"],
            "porepress_min": stats(pw)["min"],
            "porepress_max": stats(pw)["max"],
            "porepress_mean": stats(pw)["mean"],
            "porepress_center_mean": stats(pw[core])["mean"],
            "excess_center_mean": stats(ex[core])["mean"],
            "porepressrate_maxabs": stats(rate)["maxabs"],
            "porepressrate_center_mean": stats(rate[core])["mean"],
            "negative_pressure_count": int(np.sum(pw < 0.0)),
            "kplastic_max": stats(kplast)["max"],
            "sigma_xx_mean": stats(sxx)["mean"],
            "sigma_yy_mean": stats(syy)["mean"],
            "sigma_zz_mean": stats(szz)["mean"],
            "p_eff_proxy_mean": stats(p_eff)["mean"],
            "q_proxy_mean": stats(q)["mean"],
            "q_proxy_max": stats(q)["max"],
        }
        rows.append(row)
    return rows


def plot_series(rows, ykey, filename, ylabel=None):
    plt.figure(figsize=(7, 4))
    for case in sorted({r["case"] for r in rows}):
        cr = [r for r in rows if r["case"] == case]
        cr = sorted(cr, key=lambda r: r["time"])
        label = cr[0].get("label", case)
        plt.plot([r["time"] for r in cr], [r[ykey] for r in cr], marker="o", ms=2, label=label)
    plt.xlabel("time [s]")
    plt.ylabel(ylabel or ykey)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("png", "svg"):
        plt.savefig(FIG / f"{filename}.{ext}")
    plt.close()


def main():
    all_frames = []
    case_rows = []
    conf_rows = []
    fb_rows = []
    for meta in CASES:
        case = meta["case"]
        outdir = ROOT / f"{case}_out"
        if not outdir.exists():
            continue
        run_info = parse_runout(outdir / "Run.out")
        frames = frame_metrics(case, meta["label"], outdir, run_info)
        all_frames.extend(frames)
        conf = parse_confinement_diag(run_info["text"])
        for r in conf:
            r.update({"case": case, "label": meta["label"]})
        conf_rows.extend(conf)
        fb = parse_feedback_diag(run_info["text"])
        for r in fb:
            r.update({"case": case, "label": meta["label"]})
        fb_rows.extend(fb)
        final = frames[-1] if frames else {}
        first_negative = next((r["time"] for r in frames if r["negative_pressure_count"] > 0), "")
        case_rows.append(
            {
                "case": case,
                "label": meta["label"],
                "code": run_info["code"],
                "excluded": run_info["excluded"],
                "dtmin_adjustments": run_info["dtmin"],
                "frames": len(frames),
                "final_time": final.get("time", ""),
                "kplastic_max": max((r["kplastic_max"] for r in frames), default=0.0),
                "max_velocity": max((r["velocity_max"] for r in frames), default=0.0),
                "max_divvel_abs": max((r["divvel_maxabs"] for r in frames), default=0.0),
                "max_porepressrate_abs": max((r["porepressrate_maxabs"] for r in frames), default=0.0),
                "final_center_porepress": final.get("porepress_center_mean", ""),
                "final_porepress_min": final.get("porepress_min", ""),
                "final_negative_pressure_count": final.get("negative_pressure_count", ""),
                "first_negative_pressure_time": first_negative,
                "final_sigma_xx_mean": final.get("sigma_xx_mean", ""),
                "final_sigma_yy_mean": final.get("sigma_yy_mean", ""),
                "final_sigma_zz_mean": final.get("sigma_zz_mean", ""),
                "final_p_eff_proxy_mean": final.get("p_eff_proxy_mean", ""),
                "final_q_proxy_mean": final.get("q_proxy_mean", ""),
            }
        )

    write_table(ROOT / "t4k_case_summary.csv", case_rows)
    write_table(ROOT / "t4k_initial_stress_metrics.csv", all_frames)
    write_table(ROOT / "t4k_equilibrium_metrics.csv", all_frames)
    write_table(ROOT / "t4k_feedback_stability_metrics.csv", fb_rows)
    write_table(ROOT / "t4k_stress_path_proxy_metrics.csv", all_frames)
    write_table(ROOT / "t4k_confinement_diagnostics.csv", conf_rows)
    write_table(ROOT / "t4k_axial_smoke_metrics.csv", [])

    if all_frames:
        plot_series(all_frames, "p_eff_proxy_mean", "t4k_initial_stress_components_proxy", "mean p' proxy [Pa]")
        plot_series(all_frames, "q_proxy_mean", "t4k_q_proxy_vs_time", "q proxy [Pa]")
        plot_series(all_frames, "velocity_max", "t4k_velocity_max", "velocity max [m/s]")
        plot_series(all_frames, "divvel_maxabs", "t4k_divvel_maxabs", "|DivVel|max [1/s]")
        plot_series(all_frames, "porepressrate_maxabs", "t4k_porepressrate_maxabs", "|PorePressRate|max [Pa/s]")
        plot_series(all_frames, "porepress_center_mean", "t4k_center_porepress", "center pore pressure [Pa]")
    if fb_rows:
        plot_series(fb_rows, "feedback_used_max", "t4k_feedback_acceleration", "used feedback accel max [m/s2]")
    if conf_rows:
        plot_series(conf_rows, "lateral_accel_mean", "t4k_lateral_acceleration", "lateral inward accel mean [m/s2]")
        plot_series(conf_rows, "cap_axial_leakage_max", "t4k_cap_leakage", "cap axial leakage max [m/s2]")


if __name__ == "__main__":
    main()
