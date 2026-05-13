#!/usr/bin/env python3
"""T4e feedback-gated confinement diagnostics."""

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
T4D = ROOT.parent / "T4d_ConfinementEquilibration"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

R = 0.03
H = 0.10
CAP = 0.015
EDGE = 0.015

CASES = [
    {
        "case": "CaseT4e_ConfOnly_FeedbackOffExtended",
        "label": "feedback off",
        "feedback": 0,
        "feedback_start": "",
        "feedback_ramp_end": "",
        "feedback_scale": 0.0,
        "p0": 50.0,
        "ramp_end": 0.001,
        "axial_start": "",
        "kind": "feedback-off equilibration",
    },
    {
        "case": "CaseT4e_ConfOnly_FeedbackDelayedAbrupt",
        "label": "abrupt full feedback",
        "feedback": 1,
        "feedback_start": 0.003,
        "feedback_ramp_end": 0.0,
        "feedback_scale": 1.0,
        "p0": 50.0,
        "ramp_end": 0.001,
        "axial_start": "",
        "kind": "delayed feedback",
    },
    {
        "case": "CaseT4e_ConfOnly_FeedbackDelayedShortRamp",
        "label": "short full ramp",
        "feedback": 1,
        "feedback_start": 0.003,
        "feedback_ramp_end": 0.0035,
        "feedback_scale": 1.0,
        "p0": 50.0,
        "ramp_end": 0.001,
        "axial_start": "",
        "kind": "ramped feedback",
    },
    {
        "case": "CaseT4e_ConfOnly_FeedbackDelayedLongRamp",
        "label": "long full ramp",
        "feedback": 1,
        "feedback_start": 0.003,
        "feedback_ramp_end": 0.0045,
        "feedback_scale": 1.0,
        "p0": 50.0,
        "ramp_end": 0.001,
        "axial_start": "",
        "kind": "ramped feedback",
    },
    {
        "case": "CaseT4e_ConfOnly_FeedbackDelayedLongRampScale025",
        "label": "long ramp scale 0.25",
        "feedback": 1,
        "feedback_start": 0.003,
        "feedback_ramp_end": 0.0045,
        "feedback_scale": 0.25,
        "p0": 50.0,
        "ramp_end": 0.001,
        "axial_start": "",
        "kind": "scaled feedback diagnostic",
    },
]


def fnum(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        if isinstance(value, str):
            value = value.strip().rstrip(".")
        return float(value)
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


def read_table(path: Path):
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


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
            times[int(match.group(1))] = float(match.group(2))

    def one(pattern, default=0.0):
        match = re.search(pattern, text)
        return fnum(match.group(1), default) if match else default

    warning_times = []
    for match in re.finditer(r"DTs adjusted to DtMin \(t:([0-9.Ee+\-]+), nstep:([0-9]+)\)", text):
        warning_times.append({"time": fnum(match.group(1)), "nstep": fnum(match.group(2)), "warning": "DtMin"})
    for match in re.finditer(r"excluded .* \(t:([0-9.Ee+\-]+), nstep:([0-9]+)\)", text, re.IGNORECASE):
        warning_times.append({"time": fnum(match.group(1)), "nstep": fnum(match.group(2)), "warning": "excluded"})

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
    for step in sorted(by_step):
        conf_rows.append(by_step[step])
    return times, status, conf_rows, warning_times


def region_masks(rows):
    x = arr(rows, "Pos.x [m]")
    y = arr(rows, "Pos.y [m]")
    z = arr(rows, "Pos.z [m]")
    r = np.sqrt(x * x + y * y)
    return {
        "all": np.ones(len(rows), dtype=bool),
        "center_core": (r <= 0.015) & (z >= 0.025) & (z <= 0.075),
        "full_no_caps_edges": (z > CAP) & (z < H - CAP) & (r < R - EDGE * 0.25),
        "lateral_shell": (r >= R - 0.012) & (z > CAP) & (z < H - CAP),
        "top_cap": z >= H - CAP,
        "bottom_cap": z <= CAP,
    }


def feedback_factor(case, time):
    if not case["feedback"] or case["feedback_scale"] <= 0:
        return 0.0
    start = fnum(case["feedback_start"], 0.0)
    ramp_end = fnum(case["feedback_ramp_end"], 0.0)
    scale = fnum(case["feedback_scale"], 1.0)
    if time < start:
        return 0.0
    if ramp_end > start and time < ramp_end:
        return scale * (time - start) / (ramp_end - start)
    return scale


def frame_metrics(case):
    out = ROOT / f"{case['case']}_out"
    data = out / "data"
    if not data.exists():
        return [], [], {"code": 1, "excluded": np.nan, "steps": np.nan, "part_files": 0, "dtmin_adjusted": np.nan}, [], []
    times, status, conf_rows, warnings = parse_run_out(out / "Run.out")
    frames = []
    regions = []
    for part_path in sorted(data.glob("PartCsv_*.csv")):
        part = int(part_path.stem.split("_")[-1])
        rows = read_partcsv(part_path)
        time = times.get(part, np.nan)
        vx = arr(rows, "Vel.x [m/s]")
        vy = arr(rows, "Vel.y [m/s]")
        vz = arr(rows, "Vel.z [m/s]")
        speed = np.sqrt(vx * vx + vy * vy + vz * vz)
        pore = arr(rows, "PorePress")
        excess = arr(rows, "ExcessPorePress")
        rate = arr(rows, "PorePressRate")
        divvel = arr(rows, "DivVel")
        kplastic = arr(rows, "Kplastic")
        p0_eff = case["p0"] * min(1.0, time / case["ramp_end"]) if case["ramp_end"] else case["p0"]
        frame = {
            "case": case["case"],
            "label": case["label"],
            "kind": case["kind"],
            "time": time,
            "part": part,
            "particle_count": len(rows),
            "feedback_start": case["feedback_start"],
            "feedback_ramp_end": case["feedback_ramp_end"],
            "feedback_scale": case["feedback_scale"],
            "feedback_factor": feedback_factor(case, time),
            "p0_eff_expected": p0_eff,
            "axial_loading_active": 0,
            "velocity_max": float(np.max(speed)) if speed.size else np.nan,
            "porepress_mean": stats(pore)["mean"],
            "porepress_std": stats(pore)["std"],
            "porepress_min": stats(pore)["min"],
            "porepress_max": stats(pore)["max"],
            "excess_mean": stats(excess)["mean"],
            "excess_std": stats(excess)["std"],
            "porepressrate_mean": stats(rate)["mean"],
            "porepressrate_maxabs": stats(rate)["maxabs"],
            "divvel_mean": stats(divvel)["mean"],
            "divvel_maxabs": stats(divvel)["maxabs"],
            "kplastic_max": stats(kplastic)["max"],
        }
        frames.append(frame)
        masks = region_masks(rows)
        for region, mask in masks.items():
            if not np.any(mask):
                continue
            regions.append(
                {
                    "case": case["case"],
                    "label": case["label"],
                    "time": time,
                    "part": part,
                    "region": region,
                    "count": int(np.sum(mask)),
                    "feedback_factor": frame["feedback_factor"],
                    "porepress_mean": stats(pore[mask])["mean"],
                    "porepress_std": stats(pore[mask])["std"],
                    "excess_mean": stats(excess[mask])["mean"],
                    "porepressrate_mean": stats(rate[mask])["mean"],
                    "porepressrate_maxabs": stats(rate[mask])["maxabs"],
                    "divvel_mean": stats(divvel[mask])["mean"],
                    "divvel_maxabs": stats(divvel[mask])["maxabs"],
                    "velocity_max": float(np.max(speed[mask])) if np.any(mask) else np.nan,
                    "kplastic_max": stats(kplastic[mask])["max"],
                }
            )
    return frames, regions, status, conf_rows, warnings


def reversal_time(rows, key="porepress_mean"):
    ordered = sorted(rows, key=lambda r: fnum(r["time"], np.nan))
    seen_positive = False
    for row in ordered:
        value = fnum(row.get(key), np.nan)
        if math.isnan(value):
            continue
        if value > 0:
            seen_positive = True
        if seen_positive and value < 0:
            return fnum(row.get("time"), np.nan)
    return np.nan


def plot_lines(rows, xkey, ykey, title, ylabel, filename, region=None, logy=False):
    plt.figure(figsize=(7.2, 4.4))
    for case in CASES:
        sub = [r for r in rows if r["case"] == case["case"] and (region is None or r.get("region") == region)]
        sub = sorted(sub, key=lambda r: fnum(r[xkey], np.nan))
        if not sub:
            continue
        x = [fnum(r[xkey], np.nan) for r in sub]
        y = [fnum(r[ykey], np.nan) for r in sub]
        plt.plot(x, y, marker="o", ms=3, lw=1.35, label=case["label"])
    plt.title(title)
    plt.xlabel("time [s]")
    plt.ylabel(ylabel)
    if logy:
        plt.yscale("log")
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIG / f"{filename}.{ext}", dpi=180)
    plt.close()


def plot_schedule(frames):
    plt.figure(figsize=(7.2, 4.4))
    for case in CASES:
        sub = sorted([r for r in frames if r["case"] == case["case"]], key=lambda r: fnum(r["time"], np.nan))
        if not sub:
            continue
        x = [fnum(r["time"], np.nan) for r in sub]
        plt.plot(x, [fnum(r["p0_eff_expected"], np.nan) for r in sub], lw=1.3, label=f"{case['label']} p0")
        plt.plot(x, [50.0 * fnum(r["feedback_factor"], 0.0) for r in sub], lw=1.0, ls="--", label=f"{case['label']} feedback x50")
    plt.title("T4e confinement and feedback schedule")
    plt.xlabel("time [s]")
    plt.ylabel("p0 [Pa] / feedback factor x 50")
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIG / f"t4e_feedback_p0_axial_schedule_vs_time.{ext}", dpi=180)
    plt.close()


def plot_reversal(frames):
    plt.figure(figsize=(7.2, 4.4))
    for case in CASES:
        sub = sorted([r for r in frames if r["case"] == case["case"]], key=lambda r: fnum(r["time"], np.nan))
        seen_positive = False
        values = []
        for row in sub:
            pp = fnum(row["porepress_mean"], np.nan)
            if pp > 0:
                seen_positive = True
            values.append(1 if seen_positive and pp < 0 else 0)
        if sub:
            plt.step([fnum(r["time"], np.nan) for r in sub], values, where="post", label=case["label"])
    plt.title("T4e pressure reversal indicator")
    plt.xlabel("time [s]")
    plt.ylabel("reversal active")
    plt.ylim(-0.05, 1.05)
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIG / f"t4e_reversal_indicator_vs_time.{ext}", dpi=180)
    plt.close()


def plot_dtmin_markers(warnings):
    plt.figure(figsize=(7.2, 4.4))
    for i, case in enumerate(CASES):
        sub = [w for w in warnings if w["case"] == case["case"]]
        if not sub:
            continue
        plt.scatter([fnum(w["time"], np.nan) for w in sub], [i] * len(sub), s=28, label=case["label"])
    plt.title("T4e DtMin/exclusion warning markers")
    plt.xlabel("time [s]")
    plt.yticks(range(len(CASES)), [c["label"] for c in CASES], fontsize=8)
    plt.grid(True, axis="x", alpha=0.25)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIG / f"t4e_dtmin_adjustment_markers.{ext}", dpi=180)
    plt.close()


def main():
    all_frames = []
    all_regions = []
    all_conf = []
    all_warnings = []
    summaries = []
    reversal_rows = []

    for case in CASES:
        frames, regions, status, conf, warnings = frame_metrics(case)
        all_frames.extend(frames)
        all_regions.extend(regions)
        for row in conf:
            row = dict(row)
            row.update(
                {
                    "case": case["case"],
                    "label": case["label"],
                    "feedback_start": case["feedback_start"],
                    "feedback_ramp_end": case["feedback_ramp_end"],
                    "feedback_scale": case["feedback_scale"],
                    "feedback_factor": feedback_factor(case, fnum(row.get("time"), 0.0)),
                }
            )
            all_conf.append(row)
        for warning in warnings:
            warning = dict(warning)
            warning.update({"case": case["case"], "label": case["label"]})
            all_warnings.append(warning)

        final = sorted(frames, key=lambda r: fnum(r["time"], np.nan))[-1] if frames else {}
        max_rate = max((fnum(r["porepressrate_maxabs"], np.nan) for r in frames), default=np.nan)
        max_vel = max((fnum(r["velocity_max"], np.nan) for r in frames), default=np.nan)
        max_div = max((fnum(r["divvel_maxabs"], np.nan) for r in frames), default=np.nan)
        target_region = [r for r in regions if r["region"] == "center_core"]
        rev_all = reversal_time(frames)
        rev_center = reversal_time(target_region)
        max_lat = max((fnum(r.get("lat_accel_mean"), np.nan) for r in conf), default=np.nan)
        max_cap = max((fnum(r.get("cap_axial_max"), np.nan) for r in conf), default=np.nan)
        final_center = sorted(target_region, key=lambda r: fnum(r["time"], np.nan))[-1] if target_region else {}
        summaries.append(
            {
                "case": case["case"],
                "label": case["label"],
                "kind": case["kind"],
                "code": status["code"],
                "excluded": status["excluded"],
                "steps": status["steps"],
                "part_files": status["part_files"],
                "dtmin_adjusted": status["dtmin_adjusted"],
                "feedback_start": case["feedback_start"],
                "feedback_ramp_end": case["feedback_ramp_end"],
                "feedback_scale": case["feedback_scale"],
                "confinement_ramp_end": case["ramp_end"],
                "axial_loading_start": case["axial_start"],
                "final_time": final.get("time", np.nan),
                "final_particle_count": final.get("particle_count", np.nan),
                "final_porepress_mean": final.get("porepress_mean", np.nan),
                "final_center_porepress_mean": final_center.get("porepress_mean", np.nan),
                "final_porepressrate_mean": final.get("porepressrate_mean", np.nan),
                "max_porepressrate_abs": max_rate,
                "max_divvel_abs": max_div,
                "max_velocity": max_vel,
                "reversal_time_all": rev_all,
                "reversal_time_center_core": rev_center,
                "pressure_reversal": 0 if math.isnan(rev_all) else 1,
                "final_kplastic_max": final.get("kplastic_max", np.nan),
                "max_lateral_accel_mean": max_lat,
                "max_cap_axial_leakage": max_cap,
                "stable_by_t4e_criteria": int(
                    status["code"] == 0
                    and fnum(status["excluded"], 1) == 0
                    and fnum(status["dtmin_adjusted"], 1) == 0
                    and math.isnan(rev_all)
                    and max_rate < 1.0e12
                ),
            }
        )
        reversal_rows.append(
            {
                "case": case["case"],
                "label": case["label"],
                "feedback_start": case["feedback_start"],
                "feedback_ramp_end": case["feedback_ramp_end"],
                "feedback_scale": case["feedback_scale"],
                "reversal_time_all": rev_all,
                "reversal_time_center_core": rev_center,
                "reversal_after_feedback_start": (
                    "" if math.isnan(rev_all) or case["feedback_start"] == "" else int(rev_all >= fnum(case["feedback_start"]))
                ),
            }
        )

    write_table(ROOT / "t4e_case_summary.csv", summaries)
    write_table(ROOT / "t4e_feedback_gating_metrics.csv", all_frames)
    write_table(ROOT / "t4e_confinement_equilibration_metrics.csv", all_regions)
    write_table(ROOT / "t4e_reversal_metrics.csv", reversal_rows)
    write_table(ROOT / "t4e_dtmin_metrics.csv", all_warnings)
    write_table(ROOT / "t4e_confinement_diagnostics.csv", all_conf)
    write_table(
        ROOT / "t4e_axial_loading_metrics.csv",
        [
            {
                "axial_variant_run": 0,
                "reason": "Skipped because no full-scale feedback-on confinement-only variant passed the stability gate.",
            }
        ],
    )

    t4d_summary = read_table(T4D / "t4d_case_summary.csv")
    if t4d_summary:
        write_table(ROOT / "t4e_t4d_reference_summary.csv", t4d_summary)

    plot_schedule(all_frames)
    plot_lines(
        all_frames,
        "time",
        "porepressrate_maxabs",
        "T4e PorePressRate maxAbs",
        "|PorePressRate|max [Pa/s]",
        "t4e_porepressrate_maxabs_vs_time",
        logy=True,
    )
    plot_lines(
        all_regions,
        "time",
        "porepressrate_mean",
        "T4e center-core mean PorePressRate",
        "PorePressRate mean [Pa/s]",
        "t4e_center_porepressrate_mean_vs_time",
        region="center_core",
    )
    plot_lines(
        all_regions,
        "time",
        "porepress_mean",
        "T4e center-core pore pressure",
        "PorePress mean [Pa]",
        "t4e_center_porepress_vs_time",
        region="center_core",
    )
    plot_lines(
        all_regions,
        "time",
        "excess_mean",
        "T4e center-core excess pore pressure",
        "ExcessPorePress mean [Pa]",
        "t4e_center_excess_porepress_vs_time",
        region="center_core",
    )
    plot_lines(
        all_regions,
        "time",
        "divvel_mean",
        "T4e center-core DivVel",
        "DivVel mean [1/s]",
        "t4e_divvel_mean_vs_time",
        region="center_core",
    )
    plot_lines(
        all_frames,
        "time",
        "velocity_max",
        "T4e velocity max",
        "velocity max [m/s]",
        "t4e_velocity_max_vs_time",
    )
    plot_reversal(all_frames)
    plot_dtmin_markers(all_warnings)
    plot_lines(
        all_conf,
        "time",
        "cap_axial_max",
        "T4e cap axial leakage",
        "cap axial leakage max [m/s2]",
        "t4e_cap_leakage_vs_time",
    )
    plot_lines(
        all_conf,
        "time",
        "lat_accel_mean",
        "T4e lateral inward acceleration",
        "mean inward radial accel [m/s2]",
        "t4e_lateral_acceleration_vs_time",
    )


if __name__ == "__main__":
    main()
