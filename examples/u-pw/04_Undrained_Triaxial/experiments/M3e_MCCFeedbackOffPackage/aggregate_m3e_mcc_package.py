#!/usr/bin/env python3
"""Aggregate M3c-M3d3 MCC feedback-off diagnostics for the M3e package.

This script does not run GeoDualSPHysics. It reads already generated CSV files
from M3c, M3d, M3d2, and M3d3 and writes package-level tables and figures.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parent
FIG = ROOT / "figures"


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def num(row: Dict[str, str], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        val = row.get(key)
        if val not in (None, ""):
            try:
                return float(val)
            except ValueError:
                return default
    return default


def text(row: Dict[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        val = row.get(key)
        if val not in (None, ""):
            return val
    return default


def final_row(path: Path, case: str) -> Dict[str, str]:
    rows = [r for r in read_csv(path) if r.get("case") == case]
    if not rows:
        raise RuntimeError(f"Missing case {case} in {path}")
    return rows[-1]


def final_time(path: Path, case: str) -> float:
    rows = rows_for(path, case)
    if not rows:
        return 0.0
    return num(rows[-1], "time")


def rows_for(path: Path, case: str) -> List[Dict[str, str]]:
    return [r for r in read_csv(path) if r.get("case") == case]


def normalize_row(stage: str, case: str, source: str, row: Dict[str, str], desc: str,
                  speed: str = "normal", sub: str = "off", fallback: str = "off") -> Dict[str, object]:
    status = text(row, "MccReturnStatus_counts", "final_status_counts")
    return {
        "stage": stage,
        "case": case,
        "description": desc,
        "source_csv": source,
        "code": num(row, "code"),
        "excluded": num(row, "excluded"),
        "DtMin": num(row, "dtmin_adjustments"),
        "TimeMax": num(row, "time", default=0.0),
        "loading_speed": speed,
        "substepping": sub,
        "fallback": fallback,
        "ReturnStatus_counts": status,
        "ReturnStatus_minus3_count": num(row, "final_status_line_search_count", "MccLineSearchFailure_count"),
        "ReturnStatus_minus5_count": num(row, "final_MccFallbackUsed_count", "MccFallbackUsed_count"),
        "axial_strain_proxy": num(row, "final_axial_strain_proxy", "axial_strain_proxy"),
        "MccPc_min": num(row, "final_MccPc_min", "MccPc_min"),
        "MccPc_mean": num(row, "final_MccPc_mean", "MccPc_mean"),
        "MccPc_max": num(row, "final_MccPc_max", "MccPc_max"),
        "MccVoidRatio_min": num(row, "final_MccVoidRatio_min", "MccVoidRatio_min"),
        "MccVoidRatio_mean": num(row, "final_MccVoidRatio_mean", "MccVoidRatio_mean"),
        "MccVoidRatio_max": num(row, "final_MccVoidRatio_max", "MccVoidRatio_max"),
        "MccPlasticVolStrain_mean": num(row, "final_MccPlasticVolStrain_mean", "MccPlasticVolStrain_mean"),
        "MccEqPlasticStrain_max": num(row, "final_MccEqPlasticStrain_max", "MccEqPlasticStrain_max"),
        "MccYieldFlag_count": num(row, "MccYieldFlag_count", default=0.0) if "MccYieldFlag_count" in row else "",
        "MccYieldFlag_fraction": num(row, "final_yield_fraction", "MccYieldFlag_fraction"),
        "MccReturnIterations_max": num(row, "final_return_iterations_max", "MccReturnIterations_max"),
        "MccReturnIterations_mean": num(row, "MccReturnIterations_mean"),
        "MccYieldResidual_converged_max": num(row, "final_yield_residual_converged_maxAbs", "MccYieldResidual_converged_maxAbs"),
        "MccYieldResidual_raw_max": num(row, "final_yield_residual_maxAbs", "MccYieldResidual_maxAbs"),
        "Kplastic_max": num(row, "final_Kplastic_max", "Kplastic_max"),
        "Kplastic_mean": "",
        "pairwise_reaction_avg": num(row, "final_pairwise_reaction_avg", "pairwise_reaction_avg_abs", "pairwise_reaction_avg_compression"),
        "Fz_proxy": num(row, "final_Fz_proxy", "Fz_proxy"),
        "pairwise_over_Fz_proxy": num(row, "pairwise_over_Fz_proxy", default=math.nan),
        "p_proxy": num(row, "final_p_proxy", "p_proxy"),
        "q_proxy": num(row, "final_q_proxy", "q_proxy"),
        "q_over_p": "",
        "PorePress_mean": num(row, "final_PorePress_mean", "PorePress_mean"),
        "PorePress_std": num(row, "final_PorePress_std", "PorePress_std"),
        "PorePressRate_maxAbs": num(row, "final_PorePressRate_maxAbs", "PorePressRate_maxAbs"),
        "velocity_max": num(row, "final_velocity_max", "velocity_max"),
        "cap_leakage": 0,
        "lateral_active_targets": 112,
        "force_balance_error": num(row, "final_force_balance_error", "force_balance_error"),
        "MccSubstepCount_max": num(row, "final_MccSubstepCount_max", "MccSubstepCount_max"),
        "MccSubstepFailureCount_sum": num(row, "final_MccSubstepFailureCount_sum", "MccSubstepFailureCount_sum"),
        "MccAdmissibilityFailureCount_sum": num(row, "final_MccAdmissibilityFailureCount_sum", "MccAdmissibilityFailureCount_sum"),
    }


def patch_ratios(rows: List[Dict[str, object]]) -> None:
    for row in rows:
        p = float(row["p_proxy"])
        q = float(row["q_proxy"])
        fz = float(row["Fz_proxy"])
        pair = float(row["pairwise_reaction_avg"])
        row["q_over_p"] = q / p if abs(p) > 1e-12 else ""
        if math.isnan(float(row["pairwise_over_Fz_proxy"])):
            row["pairwise_over_Fz_proxy"] = pair / fz if abs(fz) > 1e-12 else ""


def load_summary_rows() -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    m3c = EXPERIMENTS / "M3c_MCCStressUpdateCpu" / "m3c_case_summary.csv"
    m3d = EXPERIMENTS / "M3d_MCCFeedbackOffRefinement" / "m3d_case_summary.csv"
    m3d2 = EXPERIMENTS / "M3d2_MCCReturnRobustness" / "m3d2_case_summary.csv"
    m3d2_ts = EXPERIMENTS / "M3d2_MCCReturnRobustness" / "m3d2_return_status_comparison.csv"
    m3d3 = EXPERIMENTS / "M3d3_MCCSubstepping" / "m3d3_case_summary.csv"
    m3d3_ts = EXPERIMENTS / "M3d3_MCCSubstepping" / "m3d3_return_status_comparison.csv"
    out.append(normalize_row("M3c", "m3c_high_pc_smoke", str(m3c), final_row(m3c, "mcc_high_pc"), "high-pc MCC smoke", "normal", "off", "off"))
    out.append(normalize_row("M3c", "m3c_mild_smoke", str(m3c), final_row(m3c, "mcc_mild_yield"), "mild MCC smoke", "normal", "off", "off"))
    out.append(normalize_row("M3d", "m3d_high_pc_extended", str(m3d), final_row(m3d, "mcc_high_pc"), "high-pc extended", "normal", "off", "off"))
    out.append(normalize_row("M3d", "m3d_mild_extended", str(m3d), final_row(m3d, "mcc_mild_yield"), "mild extended", "normal", "off", "off"))
    out.append(normalize_row("M3d2", "m3d2_half_speed", str(m3d2), final_row(m3d2, "slower_half_velocity"), "slower loading diagnostic", "half", "off", "off"))
    out.append(normalize_row("M3d2", "m3d2_early_stop", str(m3d2), final_row(m3d2, "early_stop"), "early-stop diagnostic", "normal", "off", "off"))
    out.append(normalize_row("M3d2", "m3d2_tight_return", str(m3d2), final_row(m3d2, "tight_return"), "tighter tolerance/max-iteration diagnostic", "normal", "off", "off"))
    out.append(normalize_row("M3d3", "m3d3_baseline", str(m3d3), final_row(m3d3, "baseline"), "baseline no substepping", "normal", "off", "off"))
    out.append(normalize_row("M3d3", "m3d3_fixed_substeps4", str(m3d3), final_row(m3d3, "fixed_substeps4"), "fixed 4 substeps", "normal", "fixed-4", "off"))
    out.append(normalize_row("M3d3", "m3d3_adaptive_substeps16", str(m3d3), final_row(m3d3, "adaptive_substeps16"), "adaptive substeps max 16", "normal", "adaptive-16", "off"))
    out.append(normalize_row("M3d3", "m3d3_adaptive_fallback16", str(m3d3), final_row(m3d3, "adaptive_fallback16"), "adaptive max 16 with partial fallback", "normal", "adaptive-16", "partial"))
    out.append(normalize_row("M3d3", "m3d3_half_speed_adaptive", str(m3d3), final_row(m3d3, "half_speed_adaptive"), "half-speed adaptive diagnostic", "half", "adaptive", "off"))
    time_overrides = {
        "m3d2_half_speed": final_time(m3d2_ts, "slower_half_velocity"),
        "m3d2_early_stop": final_time(m3d2_ts, "early_stop"),
        "m3d2_tight_return": final_time(m3d2_ts, "tight_return"),
        "m3d3_baseline": final_time(m3d3_ts, "baseline"),
        "m3d3_fixed_substeps4": final_time(m3d3_ts, "fixed_substeps4"),
        "m3d3_adaptive_substeps16": final_time(m3d3_ts, "adaptive_substeps16"),
        "m3d3_adaptive_fallback16": final_time(m3d3_ts, "adaptive_fallback16"),
        "m3d3_half_speed_adaptive": final_time(m3d3_ts, "half_speed_adaptive"),
    }
    for row in out:
        if row["case"] in time_overrides:
            row["TimeMax"] = time_overrides[row["case"]]
    patch_ratios(out)
    return out


SUMMARY_FIELDS = [
    "stage", "case", "description", "source_csv", "code", "excluded", "DtMin",
    "TimeMax", "loading_speed", "substepping", "fallback", "ReturnStatus_counts",
    "ReturnStatus_minus3_count", "ReturnStatus_minus5_count", "MccPc_min",
    "MccPc_mean", "MccPc_max", "MccVoidRatio_min", "MccVoidRatio_mean",
    "MccVoidRatio_max", "MccPlasticVolStrain_mean", "MccEqPlasticStrain_max",
    "MccYieldFlag_count", "MccYieldFlag_fraction", "MccReturnIterations_max",
    "MccReturnIterations_mean", "MccYieldResidual_converged_max",
    "MccYieldResidual_raw_max", "Kplastic_max", "Kplastic_mean",
    "pairwise_reaction_avg", "Fz_proxy", "pairwise_over_Fz_proxy", "p_proxy",
    "q_proxy", "q_over_p", "PorePress_mean", "PorePress_std",
    "PorePressRate_maxAbs", "velocity_max", "cap_leakage",
    "lateral_active_targets", "force_balance_error", "MccSubstepCount_max",
    "MccSubstepFailureCount_sum", "MccAdmissibilityFailureCount_sum",
]


def write_package_tables(summary: List[Dict[str, object]]) -> None:
    inventory_fields = ["stage", "case", "description", "source_csv", "TimeMax", "loading_speed", "substepping", "fallback"]
    write_csv(ROOT / "m3e_case_inventory.csv", summary, inventory_fields)
    write_csv(ROOT / "m3e_summary_metrics.csv", summary, SUMMARY_FIELDS)
    write_csv(ROOT / "m3e_return_status_summary.csv", summary, [
        "stage", "case", "ReturnStatus_counts", "ReturnStatus_minus3_count",
        "ReturnStatus_minus5_count", "MccReturnIterations_max",
        "MccYieldResidual_converged_max", "MccYieldResidual_raw_max",
        "MccSubstepCount_max", "MccSubstepFailureCount_sum",
        "MccAdmissibilityFailureCount_sum",
    ])
    write_csv(ROOT / "m3e_mcc_state_summary.csv", summary, [
        "stage", "case", "MccPc_min", "MccPc_mean", "MccPc_max",
        "MccVoidRatio_min", "MccVoidRatio_mean", "MccVoidRatio_max",
        "MccPlasticVolStrain_mean", "MccEqPlasticStrain_max",
        "MccYieldFlag_fraction", "Kplastic_max",
    ])
    write_csv(ROOT / "m3e_reaction_summary.csv", summary, [
        "stage", "case", "pairwise_reaction_avg", "Fz_proxy",
        "pairwise_over_Fz_proxy", "force_balance_error", "p_proxy", "q_proxy",
    ])
    write_csv(ROOT / "m3e_pore_pressure_summary.csv", summary, [
        "stage", "case", "PorePress_mean", "PorePress_std",
        "PorePressRate_maxAbs", "velocity_max",
    ])
    write_csv(ROOT / "m3e_stress_path_summary.csv", summary, [
        "stage", "case", "axial_strain_proxy", "p_proxy", "q_proxy",
        "q_over_p", "pairwise_reaction_avg", "Fz_proxy",
    ])


def load_timeseries() -> Dict[str, List[Dict[str, str]]]:
    series: Dict[str, List[Dict[str, str]]] = {}
    m3c_path = EXPERIMENTS / "M3c_MCCStressUpdateCpu" / "m3c_stress_path_metrics.csv"
    m3d_path = EXPERIMENTS / "M3d_MCCFeedbackOffRefinement" / "m3d_stress_path_metrics.csv"
    m3d_axial = EXPERIMENTS / "M3d_MCCFeedbackOffRefinement" / "m3d_axial_stress_strain_metrics.csv"
    m3d2_path = EXPERIMENTS / "M3d2_MCCReturnRobustness" / "m3d2_return_status_comparison.csv"
    m3d3_path = EXPERIMENTS / "M3d3_MCCSubstepping" / "m3d3_return_status_comparison.csv"
    axial_maps: Dict[str, Dict[Tuple[str, str], str]] = {}
    if m3d_axial.exists():
        for r in read_csv(m3d_axial):
            axial_maps[(r.get("case", ""), r.get("part", ""))] = r.get("pairwise_reaction_avg_abs", "")
    for label, path, case in [
        ("M3c high-pc", m3c_path, "mcc_high_pc"),
        ("M3c mild", m3c_path, "mcc_mild_yield"),
        ("M3d high-pc", m3d_path, "mcc_high_pc"),
        ("M3d mild", m3d_path, "mcc_mild_yield"),
        ("M3d2 half-speed", m3d2_path, "slower_half_velocity"),
        ("M3d2 tight-return", m3d2_path, "tight_return"),
        ("M3d3 baseline", m3d3_path, "baseline"),
        ("M3d3 fixed-4", m3d3_path, "fixed_substeps4"),
        ("M3d3 adaptive-16", m3d3_path, "adaptive_substeps16"),
        ("M3d3 fallback-16", m3d3_path, "adaptive_fallback16"),
        ("M3d3 half-speed adaptive", m3d3_path, "half_speed_adaptive"),
    ]:
        if path.exists():
            rows = rows_for(path, case)
            if path == m3d_path:
                for r in rows:
                    val = axial_maps.get((case, r.get("part", "")))
                    if val:
                        r["pairwise_reaction_avg"] = val
            series[label] = rows
    return series


def plot_lines(path: Path, series: Dict[str, List[Dict[str, str]]], xkey: str, ykey: str,
               title: str, xlabel: str, ylabel: str, selected: Iterable[str] | None = None) -> None:
    selected_set = set(selected) if selected else None
    plt.figure(figsize=(7.2, 4.6))
    for label, rows in series.items():
        if selected_set is not None and label not in selected_set:
            continue
        x = [num(r, xkey) for r in rows]
        y = [num(r, ykey) for r in rows]
        if x and y:
            plt.plot(x, y, marker="o", markersize=2.5, linewidth=1.2, label=label)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(path.with_suffix(".png"), dpi=180)
    plt.savefig(path.with_suffix(".svg"))
    plt.close()


def make_figures() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    series = load_timeseries()
    core = ["M3d high-pc", "M3d mild", "M3d3 half-speed adaptive", "M3d3 fallback-16"]
    all_sub = ["M3d3 baseline", "M3d3 fixed-4", "M3d3 adaptive-16", "M3d3 fallback-16", "M3d3 half-speed adaptive"]
    plot_lines(FIG / "m3e_pq_path_main", series, "p_proxy", "q_proxy", "MCC p'-q paths", "p' proxy (Pa)", "q proxy (Pa)", core)
    plot_lines(FIG / "m3e_reaction_stress_strain_main", series, "axial_strain_proxy", "pairwise_reaction_avg", "Pairwise reaction vs axial strain", "axial strain proxy", "pairwise reaction (N)", core)
    plot_lines(FIG / "m3e_pc_evolution_main", series, "axial_strain_proxy", "MccPc_mean", "MCC pc evolution", "axial strain proxy", "pc mean (Pa)", core)
    plot_lines(FIG / "m3e_void_ratio_evolution_main", series, "axial_strain_proxy", "MccVoidRatio_mean", "Void ratio evolution", "axial strain proxy", "void ratio mean", core)
    plot_lines(FIG / "m3e_plastic_vol_strain_main", series, "axial_strain_proxy", "MccPlasticVolStrain_mean", "Plastic volumetric strain", "axial strain proxy", "plastic volumetric strain mean", core)
    plot_lines(FIG / "m3e_eq_plastic_strain_main", series, "axial_strain_proxy", "MccEqPlasticStrain_max", "Equivalent plastic strain", "axial strain proxy", "equivalent plastic strain max", core)
    plot_lines(FIG / "m3e_return_failure_counts_main", series, "time", "status_failure_count", "Return failure counts", "time (s)", "status failure count", all_sub)
    plot_lines(FIG / "m3e_line_search_failure_counts_main", series, "time", "status_line_search_count", "Line-search failure counts", "time (s)", "line-search failure count", all_sub)
    plot_lines(FIG / "m3e_pore_pressure_main", series, "axial_strain_proxy", "PorePress_mean", "Pore pressure vs axial strain", "axial strain proxy", "mean pore pressure (Pa)", core)
    plot_lines(FIG / "m3e_porepressrate_supp", series, "time", "PorePressRate_maxAbs", "PorePressRate maxAbs", "time (s)", "PorePressRate maxAbs (Pa/s)", all_sub)
    plot_lines(FIG / "m3e_velocity_supp", series, "time", "velocity_max", "Velocity max", "time (s)", "velocity max (m/s)", all_sub)
    plot_lines(FIG / "m3e_return_iterations_supp", series, "time", "return_iterations_max", "Return iterations", "time (s)", "max return iterations", all_sub)
    plot_lines(FIG / "m3e_yield_residual_supp", series, "time", "yield_residual_converged_maxAbs", "Converged yield residual", "time (s)", "yield residual", all_sub)
    plot_lines(FIG / "m3e_substep_count_supp", series, "time", "MccSubstepCount_max", "Substep count", "time (s)", "max substep count", all_sub)


def write_readme(summary: List[Dict[str, object]]) -> None:
    clean = next(r for r in summary if r["case"] == "m3d3_half_speed_adaptive")
    fallback = next(r for r in summary if r["case"] == "m3d3_adaptive_fallback16")
    text = f"""# M3e MCC Feedback-Off Package

This package consolidates existing M3c, M3d, M3d2, and M3d3 MCC feedback-off
triaxial diagnostics. It does not contain new solver runs.

Key package conclusion:

- high-pc MCC remains elastic-like in the feedback-off platen workflow.
- mild MCC yields and updates pc, void ratio, and plastic strain.
- original-rate mild MCC still has local return failures.
- adaptive fallback removes final -3 status by marking partial fallback (-5), so it is
  a safety diagnostic rather than a validation setting.
- half-speed adaptive is the cleanest final-frame route:
  `{clean['ReturnStatus_counts']}`.
- fallback final status is `{fallback['ReturnStatus_counts']}`.

Generated tables and figures are kept in this directory. Heavy solver outputs are
not included.
"""
    (ROOT / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    summary = load_summary_rows()
    write_package_tables(summary)
    make_figures()
    write_readme(summary)


if __name__ == "__main__":
    main()
