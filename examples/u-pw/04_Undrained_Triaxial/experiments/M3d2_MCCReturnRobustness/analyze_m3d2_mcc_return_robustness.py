#!/usr/bin/env python3
"""Postprocess M3d2 MCC return-robustness diagnostics."""

from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

CASES = {
    "baseline": "CaseM3d2_MCCMildBaseline",
    "slower_half_velocity": "CaseM3d2_MCCMildSlowerHalfVelocity",
    "early_stop": "CaseM3d2_MCCMildEarlyStop",
    "tight_return": "CaseM3d2_MCCMildTightReturn",
}

RADIUS = 0.03
HEIGHT = 0.10
AREA0 = math.pi * RADIUS * RADIUS
EDGE_R = 0.020
CAP_Z = 0.015


def read_rows(path: Path) -> list[dict[str, float | int]]:
    with path.open(newline="") as f:
        reader = csv.reader(f, delimiter=";")
        headers = [h.strip() for h in next(reader) if h.strip()]
        rows: list[dict[str, float | int]] = []
        for raw in reader:
            if len(raw) < len(headers):
                continue
            row: dict[str, float | int] = {}
            for key, val in zip(headers, raw):
                if key in {"Idp", "Type"}:
                    row[key] = int(float(val))
                else:
                    try:
                        row[key] = float(val)
                    except ValueError:
                        row[key] = float("nan")
            rows.append(row)
        return rows


def part_index(path: Path) -> int:
    return int(path.stem.split("_")[-1])


def part_files(case: str) -> list[Path]:
    return sorted((ROOT / f"{case}_out" / "data").glob("PartCsv_*.csv"), key=part_index)


def parse_times(case: str) -> dict[int, float]:
    run = ROOT / f"{case}_out" / "Run.out"
    times = {0: 0.0}
    if not run.exists():
        return times
    rx = re.compile(r"Part_(\d+)\s+([0-9]+\.[0-9Ee+\-.]*)")
    for line in run.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if m:
            times[int(m.group(1))] = float(m.group(2))
    return times


def parse_run_summary(case_key: str, case: str) -> dict[str, float | int | str]:
    run = ROOT / f"{case}_out" / "Run.out"
    txt = run.read_text(errors="ignore") if run.exists() else ""
    out: dict[str, float | int | str] = {
        "case": case_key,
        "case_name": case,
        "code": 0 if "Finished execution (code=0)" in txt else -1,
        "excluded": 0,
        "dtmin_adjustments": 0,
    }
    for key, pattern in [
        ("excluded", r"Excluded particles\.+:\s+(\d+)"),
        ("dtmin_adjustments", r"DTs adjusted to DtMin\.+:\s+(\d+)"),
    ]:
        m = re.search(pattern, txt)
        if m:
            out[key] = int(m.group(1))
    return out


def parse_reactions(case_key: str, case: str) -> list[dict[str, float | int | str]]:
    run = ROOT / f"{case}_out" / "Run.out"
    if not run.exists():
        return []
    rx = re.compile(
        r"PlatenReaction diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[0-9Ee+\-.]+).*?"
        r"top_force=\((?P<tfx>[0-9Ee+\-.]+),(?P<tfy>[0-9Ee+\-.]+),(?P<tfz>[0-9Ee+\-.]+)\).*?"
        r"bottom_force=\((?P<bfx>[0-9Ee+\-.]+),(?P<bfy>[0-9Ee+\-.]+),(?P<bfz>[0-9Ee+\-.]+)\).*?"
        r"top_axial_stress=(?P<topstress>[0-9Ee+\-.]+).*?"
        r"bottom_axial_stress=(?P<bottomstress>[0-9Ee+\-.]+).*?"
        r"force_balance_error=(?P<balance>[0-9Ee+\-.]+)"
    )
    rows: list[dict[str, float | int | str]] = []
    for line in run.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if not m:
            continue
        vals = {k: float(v.rstrip(".")) for k, v in m.groupdict().items() if k != "step"}
        rows.append({"case": case_key, "step": int(m.group("step")), **vals})
    return rows


def specimen(row: dict[str, float | int]) -> bool:
    return int(row.get("Type", -1)) == 3


def safe_mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else float("nan")


def safe_std(values: Iterable[float]) -> float:
    vals = list(values)
    if len(vals) < 2:
        return 0.0 if vals else float("nan")
    mu = safe_mean(vals)
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))


def velocity_mag(row: dict[str, float | int]) -> float:
    return math.sqrt(
        float(row.get("Vel.x [m/s]", 0.0)) ** 2
        + float(row.get("Vel.y [m/s]", 0.0)) ** 2
        + float(row.get("Vel.z [m/s]", 0.0)) ** 2
    )


def stress_invariants(row: dict[str, float | int]) -> tuple[float, float]:
    sx = float(row.get("Sigma_kk.x", 0.0))
    sy = float(row.get("Sigma_kk.y", 0.0))
    sz = float(row.get("Sigma_kk.z", 0.0))
    sxy = float(row.get("Sigma_ij.x", 0.0))
    syz = float(row.get("Sigma_ij.y", 0.0))
    sxz = float(row.get("Sigma_ij.z", 0.0))
    p = -(sx + sy + sz) / 3.0
    mean = (sx + sy + sz) / 3.0
    dxx, dyy, dzz = sx - mean, sy - mean, sz - mean
    j2 = 0.5 * (dxx * dxx + dyy * dyy + dzz * dzz + 2.0 * (sxy * sxy + syz * syz + sxz * sxz))
    q = math.sqrt(max(0.0, 3.0 * j2))
    return p, q


def frame_stress(rows: list[dict[str, float | int]]) -> tuple[float, float, float]:
    spec = [r for r in rows if specimen(r)]
    sx = safe_mean(float(r.get("Sigma_kk.x", 0.0)) for r in spec)
    sy = safe_mean(float(r.get("Sigma_kk.y", 0.0)) for r in spec)
    sz = safe_mean(float(r.get("Sigma_kk.z", 0.0)) for r in spec)
    p = -(sx + sy + sz) / 3.0
    qvals = [stress_invariants(r)[1] for r in spec]
    return p, safe_mean(qvals), -sz * AREA0


def region(row: dict[str, float | int], zmin: float, zmax: float) -> str:
    x = float(row.get("Pos.x [m]", 0.0))
    y = float(row.get("Pos.y [m]", 0.0))
    z = float(row.get("Pos.z [m]", 0.0))
    r = math.hypot(x, y)
    near_top = z >= zmax - CAP_Z
    near_bottom = z <= zmin + CAP_Z
    near_lateral = r >= EDGE_R
    if near_lateral and (near_top or near_bottom):
        return "edge"
    if near_top:
        return "top_cap_zone"
    if near_bottom:
        return "bottom_cap_zone"
    if near_lateral:
        return "lateral_boundary"
    return "interior"


def axial_strain(rows: list[dict[str, float | int]]) -> float:
    spec = [r for r in rows if specimen(r)]
    if not spec:
        return float("nan")
    height = max(float(r["Pos.z [m]"]) for r in spec) - min(float(r["Pos.z [m]"]) for r in spec)
    return (HEIGHT - height) / HEIGHT


def nearest_reaction(case_key: str, time: float, reactions: list[dict[str, float | int | str]]) -> dict[str, float | int | str] | None:
    vals = [r for r in reactions if r["case"] == case_key]
    if not vals:
        return None
    return min(vals, key=lambda r: abs(float(r["time"]) - time))


def process_case(case_key: str, case: str) -> tuple[
    list[dict[str, float | int | str]],
    list[dict[str, float | int | str]],
    list[dict[str, float | int | str]],
    dict[str, float | int | str],
]:
    times = parse_times(case)
    frames: list[dict[str, float | int | str]] = []
    failed: list[dict[str, float | int | str]] = []
    by_region_rows: list[dict[str, float | int | str]] = []
    reactions = parse_reactions(case_key, case)
    first_spec_z: tuple[float, float] | None = None

    for path in part_files(case):
        part = part_index(path)
        rows = read_rows(path)
        spec = [r for r in rows if specimen(r)]
        if not spec:
            continue
        if first_spec_z is None:
            first_spec_z = (
                min(float(r["Pos.z [m]"]) for r in spec),
                max(float(r["Pos.z [m]"]) for r in spec),
            )
        zmin, zmax = first_spec_z
        statuses = Counter(int(round(float(r.get("MccReturnStatus", 0.0)))) for r in spec)
        converged_res = [
            abs(float(r.get("MccYieldResidual", 0.0)))
            for r in spec
            if int(round(float(r.get("MccReturnStatus", 0.0)))) == 1
        ]
        failures = [r for r in spec if int(round(float(r.get("MccReturnStatus", 0.0)))) < 0]
        p_frame, q_frame, fz_proxy = frame_stress(rows)
        react = nearest_reaction(case_key, times.get(part, 0.0), reactions)
        reaction_avg = float("nan")
        force_balance = float("nan")
        if react:
            reaction_avg = 0.5 * (float(react["tfz"]) - float(react["bfz"]))
            force_balance = float(react["balance"])
        frame = {
            "case": case_key,
            "case_name": case,
            "part": part,
            "time": times.get(part, float("nan")),
            "axial_strain_proxy": axial_strain(rows),
            "p_proxy": p_frame,
            "q_proxy": q_frame,
            "Fz_proxy": fz_proxy,
            "pairwise_reaction_avg": reaction_avg,
            "force_balance_error": force_balance,
            "status_elastic_count": statuses.get(0, 0),
            "status_converged_count": statuses.get(1, 0),
            "status_tension_count": statuses.get(-1, 0),
            "status_line_search_count": statuses.get(-3, 0),
            "status_failure_count": sum(v for k, v in statuses.items() if k < 0),
            "status_counts": "|".join(f"{k}:{v}" for k, v in sorted(statuses.items())),
            "yield_fraction": sum(1 for r in spec if float(r.get("MccYieldFlag", 0.0)) > 0.5) / len(spec),
            "return_iterations_max": max(float(r.get("MccReturnIterations", 0.0)) for r in spec),
            "yield_residual_maxAbs": max(abs(float(r.get("MccYieldResidual", 0.0))) for r in spec),
            "yield_residual_converged_maxAbs": max(converged_res or [0.0]),
            "MccPc_min": min(float(r.get("MccPc", 0.0)) for r in spec),
            "MccPc_mean": safe_mean(float(r.get("MccPc", 0.0)) for r in spec),
            "MccPc_max": max(float(r.get("MccPc", 0.0)) for r in spec),
            "MccVoidRatio_min": min(float(r.get("MccVoidRatio", 0.0)) for r in spec),
            "MccVoidRatio_mean": safe_mean(float(r.get("MccVoidRatio", 0.0)) for r in spec),
            "MccVoidRatio_max": max(float(r.get("MccVoidRatio", 0.0)) for r in spec),
            "MccPlasticVolStrain_mean": safe_mean(float(r.get("MccPlasticVolStrain", 0.0)) for r in spec),
            "MccEqPlasticStrain_max": max(float(r.get("MccEqPlasticStrain", 0.0)) for r in spec),
            "Kplastic_max": max(float(r.get("Kplastic", 0.0)) for r in spec),
            "PorePress_mean": safe_mean(float(r.get("PorePress", 0.0)) for r in spec),
            "PorePress_std": safe_std(float(r.get("PorePress", 0.0)) for r in spec),
            "PorePressRate_maxAbs": max(abs(float(r.get("PorePressRate", 0.0))) for r in spec),
            "DivVel_maxAbs": max(abs(float(r.get("DivVel", 0.0))) for r in spec),
            "velocity_max": max(velocity_mag(r) for r in rows),
        }
        frames.append(frame)

        region_counter: dict[str, Counter[int]] = defaultdict(Counter)
        for r in spec:
            reg = region(r, zmin, zmax)
            region_counter[reg][int(round(float(r.get("MccReturnStatus", 0.0))))] += 1
        for reg, counter in sorted(region_counter.items()):
            by_region_rows.append(
                {
                    "case": case_key,
                    "part": part,
                    "time": frame["time"],
                    "region": reg,
                    "total": sum(counter.values()),
                    "status_elastic_count": counter.get(0, 0),
                    "status_converged_count": counter.get(1, 0),
                    "status_tension_count": counter.get(-1, 0),
                    "status_line_search_count": counter.get(-3, 0),
                    "status_failure_count": sum(v for k, v in counter.items() if k < 0),
                    "status_counts": "|".join(f"{k}:{v}" for k, v in sorted(counter.items())),
                }
            )

        for r in failures:
            p, q = stress_invariants(r)
            x = float(r.get("Pos.x [m]", 0.0))
            y = float(r.get("Pos.y [m]", 0.0))
            z = float(r.get("Pos.z [m]", 0.0))
            failed.append(
                {
                    "case": case_key,
                    "part": part,
                    "time": frame["time"],
                    "Idp": int(r.get("Idp", -1)),
                    "return_status": int(round(float(r.get("MccReturnStatus", 0.0)))),
                    "region": region(r, zmin, zmax),
                    "x": x,
                    "y": y,
                    "z": z,
                    "r": math.hypot(x, y),
                    "distance_to_top": zmax - z,
                    "distance_to_bottom": z - zmin,
                    "distance_to_lateral_surface": RADIUS - math.hypot(x, y),
                    "p_eff": p,
                    "q": q,
                    "MccPc": float(r.get("MccPc", 0.0)),
                    "MccVoidRatio": float(r.get("MccVoidRatio", 0.0)),
                    "MccPlasticVolStrain": float(r.get("MccPlasticVolStrain", 0.0)),
                    "MccEqPlasticStrain": float(r.get("MccEqPlasticStrain", 0.0)),
                    "MccPlasticMultiplier": float(r.get("MccPlasticMultiplier", 0.0)),
                    "MccReturnIterations": float(r.get("MccReturnIterations", 0.0)),
                    "MccYieldResidual": float(r.get("MccYieldResidual", 0.0)),
                    "Kplastic": float(r.get("Kplastic", 0.0)),
                    "PorePress": float(r.get("PorePress", 0.0)),
                    "PorePressRate": float(r.get("PorePressRate", 0.0)),
                    "DivVel": float(r.get("DivVel", 0.0)),
                    "velocity": velocity_mag(r),
                }
            )

    summary = parse_run_summary(case_key, case)
    if frames:
        summary.update({f"final_{k}": v for k, v in frames[-1].items() if k not in {"case", "case_name", "part", "time"}})
        first_fail = next((f for f in frames if int(f["status_failure_count"]) > 0), None)
        if first_fail:
            summary["first_failure_part"] = first_fail["part"]
            summary["first_failure_time"] = first_fail["time"]
            summary["first_failure_count"] = first_fail["status_failure_count"]
        else:
            summary["first_failure_part"] = ""
            summary["first_failure_time"] = ""
            summary["first_failure_count"] = 0
    return frames, failed, by_region_rows, summary


def write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    if not rows:
        path.write_text("")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def plot_series(rows: list[dict[str, float | int | str]], y: str, name: str, ylabel: str, x: str = "time") -> None:
    plt.figure(figsize=(7, 4.5))
    for case_key in CASES:
        data = [r for r in rows if r["case"] == case_key]
        if data:
            plt.plot([float(r[x]) for r in data], [float(r[y]) for r in data], marker="o", label=case_key)
    plt.xlabel("time [s]" if x == "time" else x)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGDIR / f"{name}.png", dpi=180)
    plt.savefig(FIGDIR / f"{name}.svg")
    plt.close()


def plot_failed_locations(failed: list[dict[str, float | int | str]]) -> None:
    final_failed = []
    for case_key in CASES:
        vals = [r for r in failed if r["case"] == case_key and int(r["return_status"]) == -3]
        if not vals:
            continue
        max_part = max(int(r["part"]) for r in vals)
        final_failed.extend(r for r in vals if int(r["part"]) == max_part)
    if not final_failed:
        return
    plt.figure(figsize=(5.5, 5))
    for case_key in CASES:
        vals = [r for r in final_failed if r["case"] == case_key]
        if vals:
            plt.scatter([float(r["r"]) for r in vals], [float(r["z"]) for r in vals], label=case_key)
    plt.xlabel("radius r [m]")
    plt.ylabel("z [m]")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGDIR / "m3d2_failed_particle_locations.png", dpi=180)
    plt.savefig(FIGDIR / "m3d2_failed_particle_locations.svg")
    plt.close()


def write_audit_md(
    failed: list[dict[str, float | int | str]],
    region_rows: list[dict[str, float | int | str]],
    return_status_rows: list[dict[str, float | int | str]],
    summaries: list[dict[str, float | int | str]],
) -> None:
    path = ROOT / "m3d2_return_failure_audit.md"
    lines = [
        "# M3d2 Return Failure Audit",
        "",
        "This file is generated by `analyze_m3d2_mcc_return_robustness.py`.",
        "",
        "## Case Summary",
        "",
        "| case | first failure time | final status counts | final failed count | final line-search count |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for row in summaries:
        lines.append(
            f"| {row['case']} | {row.get('first_failure_time','')} | {row.get('final_status_counts','')} | "
            f"{row.get('final_status_failure_count','')} | {row.get('final_status_line_search_count','')} |"
        )
    lines += ["", "## Failed Particle Region Counts", ""]
    final_regions = []
    for case_key in CASES:
        vals = [r for r in region_rows if r["case"] == case_key]
        if vals:
            max_part = max(int(r["part"]) for r in vals)
            final_regions.extend(r for r in vals if int(r["part"]) == max_part and int(r["status_failure_count"]) > 0)
    if final_regions:
        lines += ["| case | region | total | failed | status counts |", "| --- | --- | ---: | ---: | --- |"]
        for r in final_regions:
            lines.append(f"| {r['case']} | {r['region']} | {r['total']} | {r['status_failure_count']} | {r['status_counts']} |")
    else:
        lines.append("No final-frame failed return particles were detected.")
    lines += ["", "## Failed Particle Location Pattern", ""]
    final_failed = []
    for case_key in CASES:
        case_frames = [r for r in return_status_rows if r["case"] == case_key]
        if not case_frames:
            continue
        final_time = case_frames[-1]["time"]
        vals = [r for r in failed if r["case"] == case_key and r["time"] == final_time]
        final_failed.extend(vals)
    if final_failed:
        by_case = defaultdict(list)
        for r in final_failed:
            by_case[str(r["case"])].append(r)
        for case, vals in by_case.items():
            rs = [float(r["r"]) for r in vals]
            zs = [float(r["z"]) for r in vals]
            lines.append(
                f"- `{case}` final failures: {len(vals)} particles, "
                f"r=[{min(rs):.5g},{max(rs):.5g}] m, z=[{min(zs):.5g},{max(zs):.5g}] m."
            )
    else:
        lines.append("No final-frame failures to locate.")
    lines += ["", "## Last Observed Failure Locations", ""]
    for case_key in CASES:
        vals = [r for r in failed if r["case"] == case_key]
        if vals:
            max_part = max(int(r["part"]) for r in vals)
            last_vals = [r for r in vals if int(r["part"]) == max_part]
            rs = [float(r["r"]) for r in last_vals]
            zs = [float(r["z"]) for r in last_vals]
            lines.append(
                f"- `{case_key}` last observed failures: {len(last_vals)} particles at part {max_part}, "
                f"r=[{min(rs):.5g},{max(rs):.5g}] m, z=[{min(zs):.5g},{max(zs):.5g}] m."
            )
        else:
            lines.append(f"- `{case_key}`: no failed return particles recorded.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    all_frames: list[dict[str, float | int | str]] = []
    all_failed: list[dict[str, float | int | str]] = []
    all_regions: list[dict[str, float | int | str]] = []
    summaries: list[dict[str, float | int | str]] = []
    for key, case in CASES.items():
        frames, failed, regions, summary = process_case(key, case)
        all_frames.extend(frames)
        all_failed.extend(failed)
        all_regions.extend(regions)
        summaries.append(summary)

    write_csv(ROOT / "m3d2_case_summary.csv", summaries)
    write_csv(ROOT / "m3d2_return_status_comparison.csv", all_frames)
    write_csv(ROOT / "m3d2_failed_return_particles.csv", all_failed)
    write_csv(ROOT / "m3d2_failed_particle_locations.csv", all_failed)
    write_csv(ROOT / "m3d2_return_status_by_region.csv", all_regions)
    write_csv(ROOT / "m3d2_yield_residual_comparison.csv", all_frames)
    write_csv(ROOT / "m3d2_pc_ev_plastic_strain_comparison.csv", all_frames)
    write_csv(ROOT / "m3d2_reaction_stress_path_comparison.csv", all_frames)
    write_csv(ROOT / "m3d2_pore_pressure_comparison.csv", all_frames)
    write_audit_md(all_failed, all_regions, all_frames, summaries)

    if all_frames:
        plot_series(all_frames, "status_failure_count", "m3d2_return_failure_count_vs_time", "failed return particle count")
        plot_series(all_frames, "status_line_search_count", "m3d2_line_search_failure_count_vs_time", "line-search failure count")
        plot_series(all_frames, "yield_residual_maxAbs", "m3d2_yield_residual_vs_time", "max |yield residual|")
        plot_series(all_frames, "yield_residual_converged_maxAbs", "m3d2_converged_residual_vs_time", "max converged |yield residual|")
        plot_series(all_frames, "MccPc_mean", "m3d2_pc_mean_vs_time", "pc mean [Pa]")
        plot_series(all_frames, "MccVoidRatio_mean", "m3d2_void_ratio_vs_time", "void ratio mean")
        plot_series(all_frames, "MccPlasticVolStrain_mean", "m3d2_plastic_vol_strain_vs_time", "plastic volumetric strain mean")
        plot_series(all_frames, "MccEqPlasticStrain_max", "m3d2_eq_plastic_strain_vs_time", "max eq plastic strain")
        plot_series(all_frames, "pairwise_reaction_avg", "m3d2_pairwise_reaction_vs_axial_strain", "pairwise reaction [N]", x="axial_strain_proxy")
        plot_series(all_frames, "PorePress_mean", "m3d2_pore_pressure_vs_axial_strain", "mean pore pressure [Pa]", x="axial_strain_proxy")
        plot_series(all_frames, "Kplastic_max", "m3d2_kplastic_vs_time", "Kplastic max")
        plot_series(all_frames, "yield_fraction", "m3d2_yield_fraction_vs_time", "yield fraction")
        plot_series(all_frames, "PorePressRate_maxAbs", "m3d2_porepressrate_vs_time", "PorePressRate maxAbs [Pa/s]")
        plot_series(all_frames, "DivVel_maxAbs", "m3d2_divvel_vs_time", "DivVel maxAbs [1/s]")
        plot_series(all_frames, "velocity_max", "m3d2_velocity_max_vs_time", "velocity max [m/s]")
        plt.figure(figsize=(5.5, 5))
        for case_key in CASES:
            vals = [r for r in all_frames if r["case"] == case_key]
            if vals:
                plt.plot([float(r["p_proxy"]) for r in vals], [float(r["q_proxy"]) for r in vals], marker="o", label=case_key)
        plt.xlabel("p' proxy [Pa]")
        plt.ylabel("q proxy [Pa]")
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(FIGDIR / "m3d2_pq_path_comparison.png", dpi=180)
        plt.savefig(FIGDIR / "m3d2_pq_path_comparison.svg")
        plt.close()
    plot_failed_locations(all_failed)


if __name__ == "__main__":
    main()
