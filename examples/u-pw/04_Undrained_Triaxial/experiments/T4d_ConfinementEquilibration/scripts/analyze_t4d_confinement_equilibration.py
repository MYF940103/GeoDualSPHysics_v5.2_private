#!/usr/bin/env python3
"""T4d confinement-only equilibration diagnostics."""

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
T4C = ROOT.parent / "T4c_LoadingStabilization"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

CASES = [
    {
        "case": "CaseT4d_ConfOnly_Raw_FeedbackOn",
        "label": "feedback on",
        "feedback": 1,
        "p0": 50.0,
        "ramp_end": 0.001,
        "damping_xi": 0.05,
        "axial_start": "",
        "kind": "target p0",
    },
    {
        "case": "CaseT4d_ConfOnly_Raw_FeedbackOff",
        "label": "feedback off",
        "feedback": 0,
        "p0": 50.0,
        "ramp_end": 0.001,
        "damping_xi": 0.05,
        "axial_start": "",
        "kind": "feedback off",
    },
    {
        "case": "CaseT4d_ConfOnly_Raw_P0Low_FeedbackOn",
        "label": "low p0",
        "feedback": 1,
        "p0": 12.5,
        "ramp_end": 0.001,
        "damping_xi": 0.05,
        "axial_start": "",
        "kind": "p0 scaling",
    },
    {
        "case": "CaseT4d_ConfOnly_Raw_LongRampDamped_FeedbackOn",
        "label": "long ramp + damping",
        "feedback": 1,
        "p0": 50.0,
        "ramp_end": 0.0018,
        "damping_xi": 0.20,
        "axial_start": "",
        "kind": "ramp damping",
    },
]

R = 0.03
H = 0.10
CAP = 0.015
EDGE = 0.015


def fnum(value, default=0.0):
    try:
        if value is None:
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
    return times, status, conf_rows


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


def frame_metrics(case):
    out = ROOT / f"{case['case']}_out"
    data = out / "data"
    times, status, conf_rows = parse_run_out(out / "Run.out")
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
        frame = {
            "case": case["case"],
            "label": case["label"],
            "time": time,
            "part": part,
            "particle_count": len(rows),
            "p0": case["p0"],
            "p0_eff_expected": case["p0"] * min(1.0, time / case["ramp_end"]) if case["ramp_end"] else case["p0"],
            "feedback": case["feedback"],
            "ramp_end": case["ramp_end"],
            "damping_xi": case["damping_xi"],
            "velocity_max": float(np.max(speed)) if speed.size else np.nan,
            "porepress_mean": stats(pore)["mean"],
            "porepress_std": stats(pore)["std"],
            "porepress_min": stats(pore)["min"],
            "porepress_max": stats(pore)["max"],
            "excess_mean": stats(excess)["mean"],
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
                    "porepress_mean": stats(pore[mask])["mean"],
                    "porepress_std": stats(pore[mask])["std"],
                    "porepressrate_mean": stats(rate[mask])["mean"],
                    "porepressrate_maxabs": stats(rate[mask])["maxabs"],
                    "divvel_mean": stats(divvel[mask])["mean"],
                    "divvel_maxabs": stats(divvel[mask])["maxabs"],
                    "velocity_max": float(np.max(speed[mask])) if np.any(mask) else np.nan,
                    "kplastic_max": stats(kplastic[mask])["max"],
                }
            )
    return frames, regions, status, conf_rows


def reversal_time(rows, key="porepress_mean"):
    ordered = sorted(rows, key=lambda r: fnum(r["time"]))
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
    plt.figure(figsize=(7, 4.2))
    for case in CASES:
        sub = [r for r in rows if r["case"] == case["case"] and (region is None or r.get("region") == region)]
        sub = sorted(sub, key=lambda r: fnum(r[xkey]))
        if not sub:
            continue
        x = [fnum(r[xkey]) for r in sub]
        y = [fnum(r[ykey], np.nan) for r in sub]
        plt.plot(x, y, marker="o", ms=3, lw=1.4, label=case["label"])
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
    plt.figure(figsize=(7, 4.2))
    for case in CASES:
        sub = [r for r in frames if r["case"] == case["case"]]
        sub = sorted(sub, key=lambda r: fnum(r["time"]))
        plt.plot(
            [fnum(r["time"]) for r in sub],
            [fnum(r["p0_eff_expected"]) for r in sub],
            marker="o",
            ms=3,
            lw=1.4,
            label=case["label"],
        )
    plt.title("Confinement ramp schedule")
    plt.xlabel("time [s]")
    plt.ylabel("expected p0_eff [Pa]")
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIG / f"t4d_confinement_p0_ramp_vs_time.{ext}", dpi=180)
    plt.close()


def plot_reversal(frames):
    plt.figure(figsize=(7, 4.2))
    for case in CASES:
        sub = sorted([r for r in frames if r["case"] == case["case"]], key=lambda r: fnum(r["time"]))
        seen_positive = False
        values = []
        for row in sub:
            pp = fnum(row["porepress_mean"], np.nan)
            if pp > 0:
                seen_positive = True
            values.append(1 if seen_positive and pp < 0 else 0)
        plt.step([fnum(r["time"]) for r in sub], values, where="post", label=case["label"])
    plt.title("Pressure reversal indicator")
    plt.xlabel("time [s]")
    plt.ylabel("reversal active")
    plt.ylim(-0.05, 1.05)
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIG / f"t4d_pressure_reversal_indicator_vs_time.{ext}", dpi=180)
    plt.close()


def main():
    all_frames = []
    all_regions = []
    all_conf = []
    summaries = []
    reversal_rows = []
    for case in CASES:
        frames, regions, status, conf = frame_metrics(case)
        all_frames.extend(frames)
        all_regions.extend(regions)
        for row in conf:
            row = dict(row)
            row.update(
                {
                    "case": case["case"],
                    "label": case["label"],
                    "feedback": case["feedback"],
                    "p0": case["p0"],
                    "ramp_end": case["ramp_end"],
                    "damping_xi": case["damping_xi"],
                }
            )
            all_conf.append(row)

        final = sorted(frames, key=lambda r: fnum(r["time"]))[-1] if frames else {}
        max_rate = max((abs(fnum(r["porepressrate_maxabs"])) for r in frames), default=np.nan)
        max_vel = max((fnum(r["velocity_max"]) for r in frames), default=np.nan)
        max_div = max((fnum(r["divvel_maxabs"]) for r in frames), default=np.nan)
        target_region = [r for r in regions if r["region"] == "center_core"]
        rev_all = reversal_time(frames)
        rev_center = reversal_time(target_region)
        max_lat = max((fnum(r.get("lat_accel_mean")) for r in conf), default=np.nan)
        max_cap = max((fnum(r.get("cap_axial_max")) for r in conf), default=np.nan)
        summaries.append(
            {
                "case": case["case"],
                "label": case["label"],
                "code": status["code"],
                "excluded": status["excluded"],
                "steps": status["steps"],
                "part_files": status["part_files"],
                "dtmin_adjusted": status["dtmin_adjusted"],
                "feedback": case["feedback"],
                "p0": case["p0"],
                "ramp_end": case["ramp_end"],
                "damping_xi": case["damping_xi"],
                "final_time": final.get("time", np.nan),
                "final_porepress_mean": final.get("porepress_mean", np.nan),
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
            }
        )
        reversal_rows.append(
            {
                "case": case["case"],
                "label": case["label"],
                "feedback": case["feedback"],
                "p0": case["p0"],
                "ramp_end": case["ramp_end"],
                "damping_xi": case["damping_xi"],
                "reversal_time_all": rev_all,
                "reversal_time_center_core": rev_center,
                "first_axial_loading_time": "",
                "reversal_before_axial": "",
            }
        )

    write_table(ROOT / "t4d_case_summary.csv", summaries)
    write_table(ROOT / "t4d_confinement_only_stability_metrics.csv", all_frames)
    write_table(ROOT / "t4d_measurement_region_metrics.csv", all_regions)
    write_table(ROOT / "t4d_confining_acceleration_metrics.csv", all_conf)
    write_table(ROOT / "t4d_porepressure_reversal_metrics.csv", reversal_rows)

    feedback_rows = [
        row for row in summaries if row["case"] in {"CaseT4d_ConfOnly_Raw_FeedbackOn", "CaseT4d_ConfOnly_Raw_FeedbackOff"}
    ]
    write_table(ROOT / "t4d_feedback_on_off_comparison.csv", feedback_rows)
    p0_rows = [
        row for row in summaries if row["case"] in {"CaseT4d_ConfOnly_Raw_FeedbackOn", "CaseT4d_ConfOnly_Raw_P0Low_FeedbackOn"}
    ]
    write_table(ROOT / "t4d_p0_scaling_metrics.csv", p0_rows)
    ramp_rows = [
        row
        for row in summaries
        if row["case"] in {"CaseT4d_ConfOnly_Raw_FeedbackOn", "CaseT4d_ConfOnly_Raw_LongRampDamped_FeedbackOn"}
    ]
    write_table(ROOT / "t4d_ramp_damping_metrics.csv", ramp_rows)

    plot_schedule(all_frames)
    plot_lines(
        all_frames,
        "time",
        "porepressrate_maxabs",
        "PorePressRate maxAbs",
        "|PorePressRate|max [Pa/s]",
        "t4d_porepressrate_maxabs_vs_time",
        logy=True,
    )
    plot_lines(
        all_regions,
        "time",
        "porepress_mean",
        "Center-core pore pressure",
        "PorePress mean [Pa]",
        "t4d_measurement_porepress_vs_time",
        region="center_core",
    )
    plot_lines(
        all_regions,
        "time",
        "divvel_mean",
        "Center-core DivVel",
        "DivVel mean [1/s]",
        "t4d_divvel_vs_time",
        region="center_core",
    )
    plot_lines(
        all_frames,
        "time",
        "velocity_max",
        "Velocity max",
        "velocity max [m/s]",
        "t4d_velocity_max_vs_time",
    )
    plot_lines(
        all_conf,
        "time",
        "lat_accel_mean",
        "Lateral inward acceleration",
        "mean inward radial accel [m/s2]",
        "t4d_lateral_radial_acceleration_vs_time",
    )
    plot_lines(
        all_conf,
        "time",
        "cap_axial_max",
        "Cap axial leakage",
        "cap axial leakage max [m/s2]",
        "t4d_cap_leakage_vs_time",
    )
    plot_lines(
        [r for r in all_frames if r["case"] in {"CaseT4d_ConfOnly_Raw_FeedbackOn", "CaseT4d_ConfOnly_Raw_FeedbackOff"}],
        "time",
        "porepressrate_maxabs",
        "Feedback on/off PorePressRate",
        "|PorePressRate|max [Pa/s]",
        "t4d_feedback_on_off_comparison",
        logy=True,
    )
    plot_lines(
        [r for r in all_frames if r["case"] in {"CaseT4d_ConfOnly_Raw_FeedbackOn", "CaseT4d_ConfOnly_Raw_P0Low_FeedbackOn"}],
        "time",
        "porepressrate_maxabs",
        "p0 scaling PorePressRate",
        "|PorePressRate|max [Pa/s]",
        "t4d_p0_scaling_comparison",
        logy=True,
    )
    plot_lines(
        [r for r in all_frames if r["case"] in {"CaseT4d_ConfOnly_Raw_FeedbackOn", "CaseT4d_ConfOnly_Raw_LongRampDamped_FeedbackOn"}],
        "time",
        "porepressrate_maxabs",
        "Ramp/damping PorePressRate",
        "|PorePressRate|max [Pa/s]",
        "t4d_ramp_damping_comparison",
        logy=True,
    )
    plot_reversal(all_frames)

    t4c_summary = read_table(T4C / "t4c_case_summary.csv")
    if t4c_summary:
        write_table(ROOT / "t4d_t4c_reference_summary.csv", t4c_summary)


if __name__ == "__main__":
    main()
