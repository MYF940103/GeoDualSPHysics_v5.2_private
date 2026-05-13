#!/usr/bin/env python3
"""Postprocess M3d feedback-off MCC platen refinement cases."""

from __future__ import annotations

import csv
import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

CASES = {
    "mcc_high_pc": "CaseM3d_MCCHighPc_Extended",
    "mcc_mild_yield": "CaseM3d_MCCMildYield_Extended",
}

RADIUS = 0.03
HEIGHT = 0.10
AREA0 = math.pi * RADIUS * RADIUS


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


def parse_summary(case_key: str, case: str) -> dict[str, float | int | str]:
    run = ROOT / f"{case}_out" / "Run.out"
    txt = run.read_text(errors="ignore") if run.exists() else ""
    out: dict[str, float | int | str] = {
        "case": case_key,
        "case_name": case,
        "code": 0 if "Finished execution (code=0)" in txt else -1,
        "excluded": 0,
        "dtmin_adjustments": 0,
        "mcc_stress_update_logged": 1 if "MCC CPU stress update: enabled" in txt else 0,
        "gpu_deferred": 1,
    }
    for key, pattern in [
        ("excluded", r"Excluded particles\.+:\s+(\d+)"),
        ("dtmin_adjustments", r"DTs adjusted to DtMin\.+:\s+(\d+)"),
    ]:
        m = re.search(pattern, txt)
        if m:
            out[key] = int(m.group(1))
    return out


def parse_reactions(case_key: str, case: str) -> list[dict[str, float | str]]:
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
    rows = []
    for line in run.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if not m:
            continue
        d = {k: float(v.rstrip(".")) for k, v in m.groupdict().items() if k != "step"}
        rows.append({"case": case_key, "step": int(m.group("step")), **d})
    return rows


def parse_confinement(case_key: str, case: str) -> list[dict[str, float | int | str]]:
    run = ROOT / f"{case}_out" / "Run.out"
    if not run.exists():
        return []
    cpu_rx = re.compile(
        r"FlexibleConfiningStress CPU diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[0-9Ee+\-.]+), "
        r"p0_eff=(?P<p0>[0-9Ee+\-.]+) Pa, targets=(?P<targets>\d+), legacy_targets=(?P<legacy>\d+).*?"
        r"total_abs_force=(?P<force>[0-9Ee+\-.]+) N, max_accel=(?P<maxacc>[0-9Ee+\-.]+) m/s2, "
        r"com_accel=(?P<comacc>[0-9Ee+\-.]+) m/s2, symmetry_residual=(?P<sym>[0-9Ee+\-.]+), "
        r"lateral_selector_active=(?P<latactive>\d+)"
    )
    ext_rx = re.compile(
        r"FlexibleConfiningStress extended diagnostics: step=(?P<step>\d+), .*?"
        r"fi_selected=(?P<fi_selected>\d+), .*?"
        r"lateral_fi_selected=(?P<lat_selected>\d+), cap_fi_selected=(?P<cap_selected>\d+), "
        r"lateral_inward_radial_accel_mean=(?P<lat_mean>[0-9Ee+\-.]+), "
        r"lateral_inward_radial_accel_max=(?P<lat_max>[0-9Ee+\-.]+), "
        r"cap_abs_axial_accel_mean=(?P<cap_mean>[0-9Ee+\-.]+), cap_abs_axial_accel_max=(?P<cap_max>[0-9Ee+\-.]+)"
    )
    by_step: dict[int, dict[str, float | int | str]] = {}
    for line in run.read_text(errors="ignore").splitlines():
        m = cpu_rx.search(line)
        if m:
            step = int(m.group("step"))
            by_step[step] = {
                "case": case_key,
                "step": step,
                "time": float(m.group("time")),
                "p0_eff": float(m.group("p0")),
                "active_targets": int(m.group("targets")),
                "legacy_targets": int(m.group("legacy")),
                "total_abs_force": float(m.group("force")),
                "max_accel": float(m.group("maxacc")),
                "com_accel": float(m.group("comacc")),
                "symmetry_residual": float(m.group("sym")),
                "lateral_selector_active": int(m.group("latactive")),
            }
        m = ext_rx.search(line)
        if m:
            step = int(m.group("step"))
            row = by_step.setdefault(step, {"case": case_key, "step": step})
            row.update(
                {
                    "fi_selected": int(m.group("fi_selected")),
                    "lateral_fi_selected": int(m.group("lat_selected")),
                    "cap_fi_selected": int(m.group("cap_selected")),
                    "lateral_inward_radial_accel_mean": float(m.group("lat_mean")),
                    "lateral_inward_radial_accel_max": float(m.group("lat_max")),
                    "cap_abs_axial_accel_mean": float(m.group("cap_mean")),
                    "cap_abs_axial_accel_max": float(m.group("cap_max")),
                }
            )
    return [by_step[k] for k in sorted(by_step)]


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


def stress_invariants(rows: list[dict[str, float | int]]) -> tuple[float, float, float]:
    sx = safe_mean(float(r["Sigma_kk.x"]) for r in rows)
    sy = safe_mean(float(r["Sigma_kk.y"]) for r in rows)
    sz = safe_mean(float(r["Sigma_kk.z"]) for r in rows)
    sxy = safe_mean(float(r["Sigma_ij.x"]) for r in rows)
    syz = safe_mean(float(r["Sigma_ij.y"]) for r in rows)
    sxz = safe_mean(float(r["Sigma_ij.z"]) for r in rows)
    p = -(sx + sy + sz) / 3.0
    mean = (sx + sy + sz) / 3.0
    dxx, dyy, dzz = sx - mean, sy - mean, sz - mean
    j2 = 0.5 * (dxx * dxx + dyy * dyy + dzz * dzz + 2 * (sxy * sxy + syz * syz + sxz * sxz))
    q = math.sqrt(max(0.0, 3.0 * j2))
    fz_proxy = -sz * AREA0
    return p, q, fz_proxy


def axial_strain(rows: list[dict[str, float | int]]) -> float:
    top = max(float(r["Pos.z [m]"]) for r in rows if specimen(r))
    bottom = min(float(r["Pos.z [m]"]) for r in rows if specimen(r))
    return (HEIGHT - (top - bottom)) / HEIGHT


def process_case(case_key: str, case: str) -> tuple[list[dict[str, float | int | str]], dict[str, float | int | str]]:
    times = parse_times(case)
    rows_out: list[dict[str, float | int | str]] = []
    for path in part_files(case):
        idx = part_index(path)
        rows = read_rows(path)
        spec = [r for r in rows if specimen(r)]
        if not spec:
            continue
        p, q, fz_proxy = stress_invariants(spec)
        mcc_status = Counter(int(round(float(r.get("MccReturnStatus", 0.0)))) for r in spec)
        converged_residuals = [
            abs(float(r.get("MccYieldResidual", 0.0)))
            for r in spec
            if int(round(float(r.get("MccReturnStatus", 0.0)))) == 1
        ]
        failed_residuals = [
            abs(float(r.get("MccYieldResidual", 0.0)))
            for r in spec
            if int(round(float(r.get("MccReturnStatus", 0.0)))) < 0
        ]
        out: dict[str, float | int | str] = {
            "case": case_key,
            "part": idx,
            "time": times.get(idx, float("nan")),
            "specimen_count": len(spec),
            "platen_contamination": 0,
            "axial_strain_proxy": axial_strain(rows),
            "p_proxy": p,
            "q_proxy": q,
            "Fz_proxy": fz_proxy,
            "PorePress_mean": safe_mean(float(r.get("PorePress", 0.0)) for r in spec),
            "PorePress_std": safe_std(float(r.get("PorePress", 0.0)) for r in spec),
            "PorePressRate_maxAbs": max(abs(float(r.get("PorePressRate", 0.0))) for r in spec),
            "DivVel_maxAbs": max(abs(float(r.get("DivVel", 0.0))) for r in spec),
            "velocity_max": max(math.sqrt(float(r["Vel.x [m/s]"])**2 + float(r["Vel.y [m/s]"])**2 + float(r["Vel.z [m/s]"])**2) for r in rows),
            "Kplastic_max": max(float(r.get("Kplastic", 0.0)) for r in spec),
            "MccPc_min": min(float(r.get("MccPc", 0.0)) for r in spec),
            "MccPc_mean": safe_mean(float(r.get("MccPc", 0.0)) for r in spec),
            "MccPc_max": max(float(r.get("MccPc", 0.0)) for r in spec),
            "MccVoidRatio_mean": safe_mean(float(r.get("MccVoidRatio", 0.0)) for r in spec),
            "MccPlasticVolStrain_min": min(float(r.get("MccPlasticVolStrain", 0.0)) for r in spec),
            "MccPlasticVolStrain_mean": safe_mean(float(r.get("MccPlasticVolStrain", 0.0)) for r in spec),
            "MccPlasticVolStrain_max": max(float(r.get("MccPlasticVolStrain", 0.0)) for r in spec),
            "MccEqPlasticStrain_mean": safe_mean(float(r.get("MccEqPlasticStrain", 0.0)) for r in spec),
            "MccEqPlasticStrain_max": max(float(r.get("MccEqPlasticStrain", 0.0)) for r in spec),
            "MccYieldFlag_count": sum(1 for r in spec if float(r.get("MccYieldFlag", 0.0)) > 0.5),
            "MccYieldFlag_fraction": sum(1 for r in spec if float(r.get("MccYieldFlag", 0.0)) > 0.5) / len(spec),
            "MccPlasticMultiplier_max": max(float(r.get("MccPlasticMultiplier", 0.0)) for r in spec),
            "MccReturnIterations_mean": safe_mean(float(r.get("MccReturnIterations", 0.0)) for r in spec),
            "MccReturnIterations_max": max(float(r.get("MccReturnIterations", 0.0)) for r in spec),
            "MccYieldResidual_maxAbs": max(abs(float(r.get("MccYieldResidual", 0.0))) for r in spec),
            "MccYieldResidual_converged_maxAbs": max(converged_residuals or [0.0]),
            "MccReturnFailure_count": sum(v for k, v in mcc_status.items() if k < 0),
            "MccTensionCutoff_count": mcc_status.get(-1, 0),
            "MccLineSearchFailure_count": mcc_status.get(-3, 0),
            "MccReturnConverged_count": mcc_status.get(1, 0),
            "MccReturnStatus_counts": "|".join(f"{k}:{v}" for k, v in sorted(mcc_status.items())),
        }
        rows_out.append(out)
    summary = parse_summary(case_key, case)
    if rows_out:
        summary.update(rows_out[-1])
    return rows_out, summary


def write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    if not rows:
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


def nearest_reaction(case_key: str, time: float, reactions: list[dict[str, float | str]]) -> dict[str, float | str] | None:
    data = [r for r in reactions if r["case"] == case_key]
    if not data:
        return None
    return min(data, key=lambda r: abs(float(r["time"]) - time))


def reaction_strain_series(
    frames: list[dict[str, float | int | str]],
    reactions: list[dict[str, float | str]],
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for frame in frames:
        case_key = str(frame["case"])
        react = nearest_reaction(case_key, float(frame["time"]), reactions)
        if not react:
            continue
        top_fz = float(react["tfz"])
        bottom_fz = float(react["bfz"])
        favg_abs = 0.5 * (abs(top_fz) + abs(bottom_fz))
        favg_compression = 0.5 * (top_fz - bottom_fz)
        stress_avg = 0.5 * (float(react["topstress"]) + float(react["bottomstress"]))
        fz_proxy = float(frame["Fz_proxy"])
        rows.append(
            {
                "case": case_key,
                "part": frame["part"],
                "time": frame["time"],
                "axial_strain_proxy": frame["axial_strain_proxy"],
                "pairwise_top_fz": top_fz,
                "pairwise_bottom_fz": bottom_fz,
                "pairwise_reaction_avg_abs": favg_abs,
                "pairwise_reaction_avg_compression": favg_compression,
                "reaction_axial_stress_avg": stress_avg,
                "top_axial_stress": react["topstress"],
                "bottom_axial_stress": react["bottomstress"],
                "force_balance_error": react["balance"],
                "Fz_proxy": fz_proxy,
                "pairwise_over_Fz_proxy": favg_compression / fz_proxy if fz_proxy else float("nan"),
                "p_proxy": frame["p_proxy"],
                "q_proxy": frame["q_proxy"],
                "MccPc_mean": frame["MccPc_mean"],
                "MccYieldFlag_fraction": frame["MccYieldFlag_fraction"],
                "MccEqPlasticStrain_max": frame["MccEqPlasticStrain_max"],
            }
        )
    return rows


def plot_series(rows: list[dict[str, float | int | str]], y: str, name: str, ylabel: str, x: str = "time") -> None:
    plt.figure(figsize=(7, 4.5))
    for case_key in CASES:
        vals = [r for r in rows if r["case"] == case_key]
        if vals:
            plt.plot([float(r[x]) for r in vals], [float(r[y]) for r in vals], marker="o", label=case_key)
    plt.xlabel("time [s]" if x == "time" else x)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGDIR / f"{name}.png", dpi=180)
    plt.savefig(FIGDIR / f"{name}.svg")
    plt.close()


def main() -> None:
    all_rows: list[dict[str, float | int | str]] = []
    summaries: list[dict[str, float | int | str]] = []
    reactions: list[dict[str, float | str]] = []
    confinement: list[dict[str, float | int | str]] = []
    for key, case in CASES.items():
        rows, summary = process_case(key, case)
        case_reactions = parse_reactions(key, case)
        if case_reactions:
            rfinal = case_reactions[-1]
            top_fz = float(rfinal["tfz"])
            bottom_fz = float(rfinal["bfz"])
            favg_abs = 0.5 * (abs(top_fz) + abs(bottom_fz))
            favg_compression = 0.5 * (top_fz - bottom_fz)
            summary.update(
                {
                    "pairwise_top_fz": top_fz,
                    "pairwise_bottom_fz": bottom_fz,
                    "pairwise_reaction_avg_abs": favg_abs,
                    "pairwise_reaction_avg_compression": favg_compression,
                    "reaction_axial_stress_avg": 0.5 * (float(rfinal["topstress"]) + float(rfinal["bottomstress"])),
                    "force_balance_error": rfinal["balance"],
                    "pairwise_over_Fz_proxy": favg_compression / float(summary.get("Fz_proxy", 0.0)) if float(summary.get("Fz_proxy", 0.0)) else float("nan"),
                    "reaction_type": "pairwise_fluid_bound_accumulator",
                }
            )
        all_rows.extend(rows)
        summaries.append(summary)
        reactions.extend(case_reactions)
        confinement.extend(parse_confinement(key, case))
    reaction_strain = reaction_strain_series(all_rows, reactions)

    write_csv(ROOT / "m3d_case_summary.csv", summaries)
    write_csv(ROOT / "m3d_mcc_state_metrics.csv", all_rows)
    write_csv(ROOT / "m3d_mcc_yield_return_metrics.csv", all_rows)
    write_csv(ROOT / "m3d_stress_path_metrics.csv", all_rows)
    write_csv(ROOT / "m3d_pore_pressure_metrics.csv", all_rows)
    write_csv(ROOT / "m3d_platen_reaction_metrics.csv", reactions)
    write_csv(ROOT / "m3d_confinement_diagnostics.csv", confinement)
    write_csv(ROOT / "m3d_axial_stress_strain_metrics.csv", reaction_strain)
    write_csv(ROOT / "m3d_stability_metrics.csv", all_rows)
    comparison = []
    for row in summaries:
        comparison.append({
            "source": "M3d",
            "case": row["case"],
            "p_proxy": row.get("p_proxy", ""),
            "q_proxy": row.get("q_proxy", ""),
            "Kplastic_max": row.get("Kplastic_max", ""),
            "PorePress_mean": row.get("PorePress_mean", ""),
            "Fz_proxy": row.get("Fz_proxy", ""),
            "pairwise_reaction_force_avg": row.get("pairwise_reaction_avg_compression", ""),
            "pairwise_over_Fz_proxy": row.get("pairwise_over_Fz_proxy", ""),
            "force_balance_error": row.get("force_balance_error", ""),
        })
    t5c = ROOT.parent / "T5c_DPExtendedFeedbackOff" / "t5c_case_summary.csv"
    if t5c.exists():
        with t5c.open(newline="") as f:
            for row in csv.DictReader(f):
                comparison.append({
                    "source": "T5c",
                    "case": row.get("case", ""),
                    "p_proxy": row.get("final_p_eff_proxy", ""),
                    "q_proxy": row.get("final_q_proxy", ""),
                    "Kplastic_max": row.get("final_kplastic_max", ""),
                    "PorePress_mean": row.get("final_porepress_mean", ""),
                    "Fz_proxy": row.get("final_reaction_force_proxy", ""),
                    "pairwise_reaction_force_avg": "",
                    "force_balance_error": row.get("final_force_balance_error", ""),
                })
    write_csv(ROOT / "m3d_comparison_to_dp_t5c.csv", comparison)

    plot_series(all_rows, "MccYieldFlag_fraction", "m3d_yield_fraction_vs_time", "MCC yield fraction")
    plot_series(all_rows, "MccPc_mean", "m3d_pc_mean_vs_time", "pc [Pa]")
    plot_series(all_rows, "MccPc_mean", "m3d_pc_vs_axial_strain", "pc [Pa]", x="axial_strain_proxy")
    plot_series(all_rows, "MccVoidRatio_mean", "m3d_void_ratio_vs_time", "void ratio e")
    plot_series(all_rows, "MccVoidRatio_mean", "m3d_void_ratio_vs_axial_strain", "void ratio e", x="axial_strain_proxy")
    plot_series(all_rows, "MccPlasticVolStrain_mean", "m3d_plastic_vol_strain_vs_time", "plastic volumetric strain")
    plot_series(all_rows, "MccPlasticVolStrain_mean", "m3d_plastic_vol_strain_vs_axial_strain", "plastic volumetric strain", x="axial_strain_proxy")
    plot_series(all_rows, "MccEqPlasticStrain_max", "m3d_eq_plastic_strain_vs_time", "max eq plastic strain")
    plot_series(all_rows, "MccEqPlasticStrain_max", "m3d_eq_plastic_strain_vs_axial_strain", "max eq plastic strain", x="axial_strain_proxy")
    plot_series(all_rows, "MccReturnIterations_max", "m3d_return_iterations_vs_time", "max return iterations")
    plot_series(all_rows, "MccYieldResidual_maxAbs", "m3d_yield_residual_vs_time", "max |yield residual|")
    plot_series(all_rows, "MccYieldResidual_converged_maxAbs", "m3d_converged_yield_residual_vs_time", "max converged |yield residual|")
    plot_series(all_rows, "MccReturnFailure_count", "m3d_return_failure_count_vs_time", "return failure particle count")
    plot_series(all_rows, "PorePress_mean", "m3d_pore_pressure_vs_time", "mean pore pressure [Pa]")
    plot_series(all_rows, "PorePress_mean", "m3d_pore_pressure_vs_axial_strain", "mean pore pressure [Pa]", x="axial_strain_proxy")
    plot_series(all_rows, "PorePressRate_maxAbs", "m3d_porepressrate_vs_time", "PorePressRate maxAbs [Pa/s]")
    plot_series(all_rows, "DivVel_maxAbs", "m3d_divvel_vs_time", "DivVel maxAbs [1/s]")
    plot_series(all_rows, "velocity_max", "m3d_velocity_max_vs_time", "velocity max [m/s]")
    plot_series(all_rows, "q_proxy", "m3d_q_vs_time", "q proxy [Pa]")
    plot_series(all_rows, "p_proxy", "m3d_p_vs_time", "p' proxy [Pa]")
    plot_series(all_rows, "q_proxy", "m3d_q_vs_axial_strain", "q proxy [Pa]", x="axial_strain_proxy")
    plot_series(all_rows, "p_proxy", "m3d_p_vs_axial_strain", "p' proxy [Pa]", x="axial_strain_proxy")

    plt.figure(figsize=(5.5, 5))
    for case_key in CASES:
        vals = [r for r in all_rows if r["case"] == case_key]
        if vals:
            plt.plot([float(r["p_proxy"]) for r in vals], [float(r["q_proxy"]) for r in vals], marker="o", label=case_key)
    plt.xlabel("p' proxy [Pa]")
    plt.ylabel("q proxy [Pa]")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGDIR / "m3d_pq_path.png", dpi=180)
    plt.savefig(FIGDIR / "m3d_pq_path.svg")
    plt.close()

    if reactions:
        plt.figure(figsize=(7, 4.5))
        for case_key in CASES:
            vals = [r for r in reactions if r["case"] == case_key]
            if vals:
                avg = [(abs(float(r["tfz"])) + abs(float(r["bfz"]))) * 0.5 for r in vals]
                plt.plot([float(r["time"]) for r in vals], avg, marker="o", label=case_key)
        plt.xlabel("time [s]")
        plt.ylabel("pairwise reaction average |Fz| [N]")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(FIGDIR / "m3d_pairwise_reaction_vs_time.png", dpi=180)
        plt.savefig(FIGDIR / "m3d_pairwise_reaction_vs_time.svg")
        plt.close()
    if reaction_strain:
        plot_series(reaction_strain, "reaction_axial_stress_avg", "m3d_reaction_axial_stress_vs_strain", "reaction axial stress avg [Pa]", x="axial_strain_proxy")
        plot_series(reaction_strain, "pairwise_over_Fz_proxy", "m3d_pairwise_proxy_ratio_vs_time", "pairwise reaction / Fz_proxy")
    if confinement:
        plot_series(confinement, "active_targets", "m3d_lateral_active_targets_vs_time", "active confinement targets")
        plot_series(confinement, "lateral_inward_radial_accel_mean", "m3d_lateral_accel_vs_time", "lateral inward accel mean [m/s2]")
        plot_series(confinement, "cap_abs_axial_accel_max", "m3d_cap_axial_accel_vs_time", "cap axial accel max [m/s2]")


if __name__ == "__main__":
    main()
