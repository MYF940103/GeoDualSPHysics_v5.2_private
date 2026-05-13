#!/usr/bin/env python3
"""Postprocess M3c CPU MCC stress-update smoke cases."""

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
    "mcc_high_pc": "CaseM3c_MCCHighPc_ElasticLike",
    "mcc_mild_yield": "CaseM3c_MCCMildYield",
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
    for key, case in CASES.items():
        rows, summary = process_case(key, case)
        all_rows.extend(rows)
        summaries.append(summary)
        reactions.extend(parse_reactions(key, case))

    write_csv(ROOT / "m3c_case_summary.csv", summaries)
    write_csv(ROOT / "m3c_mcc_state_metrics.csv", all_rows)
    write_csv(ROOT / "m3c_mcc_yield_metrics.csv", all_rows)
    write_csv(ROOT / "m3c_mcc_return_metrics.csv", all_rows)
    write_csv(ROOT / "m3c_stress_path_metrics.csv", all_rows)
    write_csv(ROOT / "m3c_pore_pressure_metrics.csv", all_rows)
    write_csv(ROOT / "m3c_platen_reaction_metrics.csv", reactions)
    comparison = []
    for row in summaries:
        comparison.append({
            "source": "M3c",
            "case": row["case"],
            "p_proxy": row.get("p_proxy", ""),
            "q_proxy": row.get("q_proxy", ""),
            "Kplastic_max": row.get("Kplastic_max", ""),
            "PorePress_mean": row.get("PorePress_mean", ""),
            "Fz_proxy": row.get("Fz_proxy", ""),
        })
    t5b = ROOT.parent / "T5b_DPFeedbackOffRefinement" / "t5b_case_summary.csv"
    if t5b.exists():
        with t5b.open(newline="") as f:
            for row in csv.DictReader(f):
                comparison.append({
                    "source": "T5b",
                    "case": row.get("case", ""),
                    "p_proxy": row.get("final_p_eff_proxy", ""),
                    "q_proxy": row.get("final_q_proxy", ""),
                    "Kplastic_max": row.get("final_kplastic_max", ""),
                    "PorePress_mean": row.get("final_porepress_mean", ""),
                    "Fz_proxy": row.get("final_reaction_force_proxy", ""),
                })
    write_csv(ROOT / "m3c_comparison_to_elastic_dp.csv", comparison)

    plot_series(all_rows, "MccYieldFlag_fraction", "m3c_yield_fraction_vs_time", "MCC yield fraction")
    plot_series(all_rows, "MccPc_mean", "m3c_pc_mean_vs_time", "pc [Pa]")
    plot_series(all_rows, "MccVoidRatio_mean", "m3c_void_ratio_vs_time", "void ratio e")
    plot_series(all_rows, "MccPlasticVolStrain_mean", "m3c_plastic_vol_strain_vs_time", "plastic volumetric strain")
    plot_series(all_rows, "MccEqPlasticStrain_max", "m3c_eq_plastic_strain_vs_time", "max eq plastic strain")
    plot_series(all_rows, "MccReturnIterations_max", "m3c_return_iterations_vs_time", "max return iterations")
    plot_series(all_rows, "MccYieldResidual_maxAbs", "m3c_yield_residual_vs_time", "max |yield residual|")
    plot_series(all_rows, "PorePress_mean", "m3c_pore_pressure_vs_time", "mean pore pressure [Pa]")
    plot_series(all_rows, "q_proxy", "m3c_q_vs_time", "q proxy [Pa]")
    plot_series(all_rows, "p_proxy", "m3c_p_vs_time", "p' proxy [Pa]")
    plot_series(all_rows, "q_proxy", "m3c_q_vs_axial_strain", "q proxy [Pa]", x="axial_strain_proxy")

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
    plt.savefig(FIGDIR / "m3c_pq_path.png", dpi=180)
    plt.savefig(FIGDIR / "m3c_pq_path.svg")
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
        plt.savefig(FIGDIR / "m3c_reaction_force_vs_time.png", dpi=180)
        plt.savefig(FIGDIR / "m3c_reaction_force_vs_time.svg")
        plt.close()


if __name__ == "__main__":
    main()
