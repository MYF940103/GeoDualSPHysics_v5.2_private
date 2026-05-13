#!/usr/bin/env python3
"""Build the T5d DP feedback-off triaxial validation package from retained CSVs."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
EXP = ROOT.parent
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

CASE_SPECS = [
    {
        "case_id": "T4s_elastic_platen_lateral",
        "stage": "T4s",
        "dir": "T4s_PlatenAxialBaseline",
        "prefix": "t4s",
        "source_case": "platen_lateral_confinement",
        "role": "elastic feedback-off platen baseline",
        "model": "elastic",
        "soil_model": "0",
        "phi_deg": "",
        "cohesion_pa": "",
        "dilatancy_deg": "",
        "series_file": "t4s_specimen_stress_proxy.csv",
        "reaction_series_file": "",
        "reaction_comparison_file": "",
    },
    {
        "case_id": "T4t_elastic_reaction",
        "stage": "T4t",
        "dir": "T4t_TruePlatenReaction",
        "prefix": "t4t",
        "source_case": "elastic",
        "role": "elastic pairwise reaction diagnostic",
        "model": "elastic",
        "soil_model": "0",
        "phi_deg": "",
        "cohesion_pa": "",
        "dilatancy_deg": "",
        "series_file": "t4t_stress_path_metrics.csv",
        "reaction_series_file": "t4t_platen_reaction_metrics.csv",
        "reaction_comparison_file": "t4t_reaction_vs_proxy_comparison.csv",
    },
    {
        "case_id": "T5_dp_high_strength",
        "stage": "T5",
        "dir": "T5_DPFeedbackOffBaseline",
        "prefix": "t5",
        "source_case": "dp_high_strength",
        "role": "DP high-strength feedback-off baseline",
        "model": "DP high strength",
        "soil_model": "1",
        "phi_deg": "33",
        "cohesion_pa": "10000",
        "dilatancy_deg": "0",
        "series_file": "t5_specimen_stress_path_proxy.csv",
        "reaction_series_file": "",
        "reaction_comparison_file": "",
    },
    {
        "case_id": "T5_dp_mild_yield",
        "stage": "T5",
        "dir": "T5_DPFeedbackOffBaseline",
        "prefix": "t5",
        "source_case": "dp_mild_yield",
        "role": "DP mild-yield feedback-off baseline",
        "model": "DP mild yield",
        "soil_model": "1",
        "phi_deg": "30",
        "cohesion_pa": "50",
        "dilatancy_deg": "0",
        "series_file": "t5_specimen_stress_path_proxy.csv",
        "reaction_series_file": "",
        "reaction_comparison_file": "",
    },
    {
        "case_id": "T5b_dp_high_strength",
        "stage": "T5b",
        "dir": "T5b_DPFeedbackOffRefinement",
        "prefix": "t5b",
        "source_case": "dp_high_strength",
        "role": "DP high-strength reaction refinement",
        "model": "DP high strength",
        "soil_model": "1",
        "phi_deg": "33",
        "cohesion_pa": "10000",
        "dilatancy_deg": "0",
        "series_file": "t5b_axial_stress_strain_metrics.csv",
        "reaction_series_file": "t5b_platen_reaction_metrics.csv",
        "reaction_comparison_file": "t5b_reaction_vs_proxy_comparison.csv",
    },
    {
        "case_id": "T5b_dp_mild_yield",
        "stage": "T5b",
        "dir": "T5b_DPFeedbackOffRefinement",
        "prefix": "t5b",
        "source_case": "dp_mild_yield",
        "role": "DP mild-yield reaction refinement",
        "model": "DP mild yield",
        "soil_model": "1",
        "phi_deg": "30",
        "cohesion_pa": "50",
        "dilatancy_deg": "0",
        "series_file": "t5b_axial_stress_strain_metrics.csv",
        "reaction_series_file": "t5b_platen_reaction_metrics.csv",
        "reaction_comparison_file": "t5b_reaction_vs_proxy_comparison.csv",
    },
    {
        "case_id": "T5c_dp_high_strength_extended",
        "stage": "T5c",
        "dir": "T5c_DPExtendedFeedbackOff",
        "prefix": "t5c",
        "source_case": "dp_high_strength",
        "role": "DP high-strength extended response",
        "model": "DP high strength",
        "soil_model": "1",
        "phi_deg": "33",
        "cohesion_pa": "10000",
        "dilatancy_deg": "0",
        "series_file": "t5c_axial_stress_strain_metrics.csv",
        "reaction_series_file": "t5c_platen_reaction_metrics.csv",
        "reaction_comparison_file": "t5c_reaction_vs_proxy_comparison.csv",
    },
    {
        "case_id": "T5c_dp_mild_yield_extended",
        "stage": "T5c",
        "dir": "T5c_DPExtendedFeedbackOff",
        "prefix": "t5c",
        "source_case": "dp_mild_yield",
        "role": "DP mild-yield extended response",
        "model": "DP mild yield",
        "soil_model": "1",
        "phi_deg": "30",
        "cohesion_pa": "50",
        "dilatancy_deg": "0",
        "series_file": "t5c_axial_stress_strain_metrics.csv",
        "reaction_series_file": "t5c_platen_reaction_metrics.csv",
        "reaction_comparison_file": "t5c_reaction_vs_proxy_comparison.csv",
    },
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, str], key: str, default: float = math.nan) -> float:
    val = row.get(key, "")
    if val == "":
        return default
    try:
        return float(val)
    except ValueError:
        return default


def s(row: dict[str, str], key: str, default: str = "") -> str:
    return row.get(key, default)


def final_for_case(rows: list[dict[str, str]], case: str) -> dict[str, str]:
    subset = [r for r in rows if r.get("case") == case]
    return subset[-1] if subset else {}


def rows_for_case(rows: list[dict[str, str]], case: str) -> list[dict[str, str]]:
    return [r for r in rows if r.get("case") == case]


def final_confinement(spec: dict[str, str]) -> dict[str, str]:
    path = EXP / spec["dir"] / f"{spec['prefix']}_confinement_diagnostics.csv"
    return final_for_case(read_csv(path), spec["source_case"])


def final_reaction_comparison(spec: dict[str, str]) -> dict[str, str]:
    filename = spec.get("reaction_comparison_file", "")
    if not filename:
        return {}
    path = EXP / spec["dir"] / filename
    return final_for_case(read_csv(path), spec["source_case"])


def final_summary(spec: dict[str, str]) -> dict[str, str]:
    path = EXP / spec["dir"] / f"{spec['prefix']}_case_summary.csv"
    return final_for_case(read_csv(path), spec["source_case"])


def time_series(spec: dict[str, str]) -> list[dict[str, object]]:
    rows = read_csv(EXP / spec["dir"] / spec["series_file"])
    out: list[dict[str, object]] = []
    for row in rows_for_case(rows, spec["source_case"]):
        out.append({"case_id": spec["case_id"], "stage": spec["stage"], **row})
    return out


def reaction_series(spec: dict[str, str]) -> list[dict[str, object]]:
    filename = spec.get("reaction_series_file", "")
    if not filename:
        return []
    rows = read_csv(EXP / spec["dir"] / filename)
    out: list[dict[str, object]] = []
    for row in rows_for_case(rows, spec["source_case"]):
        out.append({"case_id": spec["case_id"], "stage": spec["stage"], **row})
    return out


def max_for_series(rows: list[dict[str, object]], key: str) -> float:
    vals: list[float] = []
    for row in rows:
        val = row.get(key, "")
        try:
            vals.append(float(val))
        except (TypeError, ValueError):
            pass
    return max(vals) if vals else math.nan


def max_kplastic_growth(rows: list[dict[str, object]]) -> float:
    vals: list[float] = []
    data = sorted(rows, key=lambda r: y(r, "time"))
    last_t: float | None = None
    last_kp: float | None = None
    for row in data:
        t = y(row, "time")
        kp = y(row, "kplastic_max")
        if last_t is not None and last_kp is not None and t > last_t:
            vals.append((kp - last_kp) / (t - last_t))
        last_t = t
        last_kp = kp
    return max(vals) if vals else math.nan


def build_tables() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    inventory: list[dict[str, object]] = []
    summary: list[dict[str, object]] = []
    reaction: list[dict[str, object]] = []
    plasticity: list[dict[str, object]] = []
    pore: list[dict[str, object]] = []
    stress_series: list[dict[str, object]] = []
    reaction_all: list[dict[str, object]] = []

    for spec in CASE_SPECS:
        summ = final_summary(spec)
        conf = final_confinement(spec)
        comp = final_reaction_comparison(spec)
        series = time_series(spec)
        rseries = reaction_series(spec)
        stress_series.extend(series)
        reaction_all.extend(rseries)
        final_time = f(series[-1], "time") if series else math.nan
        source_case = spec["source_case"]
        kplastic_count = f(summ, "final_kplastic_nonzero_count", 0.0)
        specimen_count = f(summ, "final_specimen_count", 407.0)
        kplastic_fraction = f(summ, "final_kplastic_fraction", kplastic_count / specimen_count if specimen_count else math.nan)
        fz_proxy = f(summ, "final_reaction_force_proxy")
        pairwise = f(comp, "reaction_force_avg_compression")
        ratio = f(comp, "reaction_over_proxy_force", pairwise / fz_proxy if fz_proxy and not math.isnan(pairwise) else math.nan)
        reaction_available = 1 if comp else 0
        top_reaction = f(comp, "top_reaction_fz", f(summ, "final_top_force_z"))
        bottom_reaction = f(comp, "bottom_reaction_fz", f(summ, "final_bottom_force_z"))
        q = f(summ, "final_q_proxy")
        p_eff = f(summ, "final_p_eff_proxy")

        inventory.append(
            {
                "case_id": spec["case_id"],
                "stage": spec["stage"],
                "source_case": source_case,
                "role": spec["role"],
                "soil_model": spec["soil_model"],
                "model": spec["model"],
                "phi_deg": spec["phi_deg"],
                "cohesion_pa": spec["cohesion_pa"],
                "dilatancy_deg": spec["dilatancy_deg"],
                "time_max_observed": final_time,
                "pore_pressure_feedback": 0,
                "lateral_confinement": 1,
                "explicit_platen": 1,
                "pairwise_reaction_available": reaction_available,
                "reaction_caveat": "pairwise interaction reaction, not full actuator reaction" if reaction_available else "Fz_proxy only",
            }
        )
        summary.append(
            {
                "case_id": spec["case_id"],
                "stage": spec["stage"],
                "code": s(summ, "code"),
                "excluded": s(summ, "excluded"),
                "dtmin_adjustments": s(summ, "dtmin_adjustments"),
                "time_max_observed": final_time,
                "top_displacement": f(summ, "final_top_platen_displacement"),
                "axial_strain_proxy": f(summ, "final_specimen_axial_strain_proxy"),
                "pairwise_reaction": pairwise,
                "Fz_proxy": fz_proxy,
                "pairwise_over_Fz_proxy": ratio,
                "p_eff_proxy": p_eff,
                "q_proxy": q,
                "q_over_p_eff": q / p_eff if p_eff and not math.isnan(p_eff) else math.nan,
                "kplastic_max": f(summ, "final_kplastic_max"),
                "kplastic_mean": f(summ, "final_kplastic_mean", 0.0),
                "kplastic_nonzero_count": kplastic_count,
                "kplastic_fraction": kplastic_fraction,
                "porepress_mean": f(summ, "final_porepress_mean"),
                "porepress_std": f(summ, "final_porepress_std"),
                "porepressrate_maxabs": f(summ, "final_porepressrate_maxabs"),
                "velocity_max": f(summ, "final_velocity_max"),
                "divvel_maxabs": f(summ, "final_divvel_maxabs"),
                "cap_leakage": f(conf, "cap_abs_axial_accel_max", 0.0),
                "lateral_active_targets": f(conf, "targets", f(conf, "lateral_fi_selected", math.nan)),
                "force_balance_error": f(summ, "final_force_balance_error", f(comp, "force_balance_error")),
            }
        )
        reaction.append(
            {
                "case_id": spec["case_id"],
                "stage": spec["stage"],
                "reaction_available": reaction_available,
                "reaction_type": s(summ, "reaction_type", "Fz_proxy_only"),
                "pairwise_reaction": pairwise,
                "top_reaction_fz": top_reaction,
                "bottom_reaction_fz": bottom_reaction,
                "Fz_proxy": fz_proxy,
                "pairwise_minus_Fz_proxy": pairwise - fz_proxy if not math.isnan(pairwise) and not math.isnan(fz_proxy) else math.nan,
                "pairwise_over_Fz_proxy": ratio,
                "force_balance_error": f(summ, "final_force_balance_error", f(comp, "force_balance_error")),
            }
        )
        plasticity.append(
            {
                "case_id": spec["case_id"],
                "stage": spec["stage"],
                "model": spec["model"],
                "kplastic_max": f(summ, "final_kplastic_max"),
                "kplastic_mean": f(summ, "final_kplastic_mean", 0.0),
                "kplastic_nonzero_count": kplastic_count,
                "kplastic_fraction": kplastic_fraction,
                "max_kplastic_growth_rate": max_kplastic_growth(series),
            }
        )
        pore.append(
            {
                "case_id": spec["case_id"],
                "stage": spec["stage"],
                "porepress_mean": f(summ, "final_porepress_mean"),
                "porepress_std": f(summ, "final_porepress_std"),
                "porepressrate_maxabs_final": f(summ, "final_porepressrate_maxabs"),
                "porepressrate_maxabs_observed": max_for_series(series, "porepressrate_maxabs"),
                "negative_final_mean": 1 if f(summ, "final_porepress_mean") < 0 else 0,
                "feedback": 0,
            }
        )

    write_csv(ROOT / "t5d_case_inventory.csv", inventory)
    write_csv(ROOT / "t5d_summary_metrics.csv", summary)
    write_csv(ROOT / "t5d_reaction_comparison.csv", reaction)
    write_csv(ROOT / "t5d_stress_path_comparison.csv", stress_series)
    write_csv(ROOT / "t5d_plasticity_summary.csv", plasticity)
    write_csv(ROOT / "t5d_pore_pressure_summary.csv", pore)
    return summary, reaction, plasticity, pore, stress_series


def series_from(case_ids: Iterable[str], rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    ids = set(case_ids)
    return {case_id: [r for r in rows if r["case_id"] == case_id] for case_id in ids}


def y(row: dict[str, object], key: str) -> float:
    try:
        return float(row.get(key, "nan"))
    except (TypeError, ValueError):
        return math.nan


def plot_series(rows: list[dict[str, object]], ykey: str, filename: str, ylabel: str, xkey: str = "time") -> None:
    plt.figure(figsize=(7.0, 4.2))
    for case_id in sorted({str(r["case_id"]) for r in rows}):
        data = [r for r in rows if r["case_id"] == case_id]
        if not data:
            continue
        plt.plot([y(r, xkey) for r in data], [y(r, ykey) for r in data], marker="o", markersize=3, label=case_id)
    plt.xlabel("time [s]" if xkey == "time" else xkey)
    plt.ylabel(ylabel)
    plt.legend(fontsize=7)
    plt.tight_layout()
    savefig(filename)


def savefig(name: str) -> None:
    for ext in ("svg", "png"):
        plt.savefig(FIGDIR / f"{name}.{ext}", dpi=180)
    plt.close()
    for svg in FIGDIR.glob("*.svg"):
        lines = svg.read_text(encoding="utf-8").splitlines()
        svg.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


def plot_pq(rows: list[dict[str, object]], filename: str) -> None:
    plt.figure(figsize=(5.4, 4.6))
    for case_id in sorted({str(r["case_id"]) for r in rows}):
        data = [r for r in rows if r["case_id"] == case_id]
        plt.plot([y(r, "p_eff_proxy") for r in data], [y(r, "q_proxy") for r in data], marker="o", markersize=3, label=case_id)
    plt.xlabel("p' proxy [Pa]")
    plt.ylabel("q proxy [Pa]")
    plt.legend(fontsize=7)
    plt.tight_layout()
    savefig(filename)


def plot_bar(rows: list[dict[str, object]], key: str, filename: str, ylabel: str) -> None:
    labels = [str(r["case_id"]) for r in rows]
    vals = [float(r[key]) if r.get(key) not in ("", None) else math.nan for r in rows]
    plt.figure(figsize=(9.0, 4.2))
    plt.bar(range(len(labels)), vals)
    plt.xticks(range(len(labels)), labels, rotation=30, ha="right", fontsize=7)
    plt.ylabel(ylabel)
    plt.tight_layout()
    savefig(filename)


def build_figures(summary: list[dict[str, object]], reaction: list[dict[str, object]], stress_series: list[dict[str, object]]) -> None:
    extra_elastic = []
    for row in rows_for_case(read_csv(EXP / "T5b_DPFeedbackOffRefinement" / "t5b_axial_stress_strain_metrics.csv"), "elastic"):
        extra_elastic.append({"case_id": "T5b_elastic_reference", "stage": "T5b", **row})
    main_ids = [
        "T5b_elastic_reference",
        "T5b_dp_high_strength",
        "T5b_dp_mild_yield",
        "T5c_dp_high_strength_extended",
        "T5c_dp_mild_yield_extended",
    ]
    main_series = [r for r in stress_series if r["case_id"] in main_ids] + extra_elastic
    plot_series(main_series, "reaction_axial_stress_avg", "main_reaction_axial_stress_vs_axial_strain", "reaction axial stress [Pa]", "specimen_axial_strain_proxy")
    plot_pq(main_series, "main_pq_path")
    plot_series(main_series, "kplastic_max", "main_kplastic_evolution", "Kplastic max")
    plot_series(main_series, "porepress_mean", "main_pore_pressure_vs_axial_strain", "PorePress mean [Pa]", "specimen_axial_strain_proxy")
    plot_bar(reaction, "pairwise_over_Fz_proxy", "main_pairwise_reaction_vs_fz_proxy_ratio", "pairwise reaction / Fz_proxy")

    plot_series(main_series, "top_platen_displacement", "supp_top_platen_displacement", "top platen displacement [m]")
    plot_series(main_series, "velocity_max", "supp_velocity_max", "velocity max [m/s]")
    plot_series(main_series, "porepressrate_maxabs", "supp_porepressrate_maxabs", "PorePressRate maxAbs [Pa/s]")
    plot_series(main_series, "divvel_maxabs", "supp_divvel_maxabs", "DivVel maxAbs [1/s]")
    plot_series(main_series, "kplastic_fraction", "supp_kplastic_fraction", "plastic fraction")
    plot_bar(summary, "cap_leakage", "supp_cap_leakage_final", "final cap leakage [m/s2]")
    plot_bar(summary, "lateral_active_targets", "supp_lateral_active_targets", "lateral active targets")
    plot_bar(summary, "force_balance_error", "supp_force_balance_error_final", "final force balance error")


def main() -> None:
    summary, reaction, _plasticity, _pore, stress_series = build_tables()
    build_figures(summary, reaction, stress_series)


if __name__ == "__main__":
    main()
