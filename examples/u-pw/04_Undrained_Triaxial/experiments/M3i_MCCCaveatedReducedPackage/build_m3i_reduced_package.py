#!/usr/bin/env python3
"""Build the M3i caveated MCC reduced reporting package.

No solver, GenCase, PartVTK, or source build is invoked here.  The script only
collects existing compact CSV outputs and writes stage-level reporting tables
and figures.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
EXP = ROOT.parent
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows, fields=None):
    rows = list(rows)
    if not rows:
        return
    if fields is None:
        fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fnum(value, default=math.nan):
    try:
        if value in ("", None, "nan"):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def last_by_case(rows, case_field="case"):
    out = {}
    for row in rows:
        out[row[case_field]] = row
    return out


def save(fig, stem):
    fig.tight_layout()
    fig.savefig(FIG / f"{stem}.svg")
    fig.savefig(FIG / f"{stem}.png", dpi=180)
    plt.close(fig)


def case_inventory():
    rows = [
        ("T4s", "elastic feedback-off platen baseline", "established explicit platen + lateral confinement reduced baseline", "T4s_PlatenAxialBaseline", "completed", "reaction was Fz_proxy only"),
        ("T4t", "platen reaction diagnostics", "added pairwise platen/specimen interaction reaction", "T4t_TruePlatenReaction", "completed", "pairwise reaction is not full actuator reaction"),
        ("T5", "DP feedback-off baseline", "first DP skeleton on explicit platen workflow", "T5_DPFeedbackOffBaseline", "completed", "reduced, feedback off"),
        ("T5b", "DP refinement", "elastic/high-strength/mild DP comparison with pairwise reaction", "T5b_DPFeedbackOffRefinement", "completed", "reduced, feedback off"),
        ("T5c", "DP extended response", "slightly longer DP high-strength and mild-yield response", "T5c_DPExtendedFeedbackOff", "completed", "mild DP negative pore pressure is diagnostic"),
        ("M3c", "MCC CPU stress update smoke", "parser/state/output plus CPU MCC branch smoke", "M3c_MCCStressUpdateCpu", "completed", "short smoke only"),
        ("M3d", "MCC feedback-off extended", "high-pc elastic-like and mild-yield MCC extended response", "M3d_MCCFeedbackOffRefinement", "completed", "mild route has local return failures"),
        ("M3d2", "MCC return robustness audit", "localized ReturnStatus=-3 particles and rate/iteration diagnostics", "M3d2_MCCReturnRobustness", "completed", "failure is local, not global"),
        ("M3d3", "MCC substepping diagnostics", "opt-in substepping/guard/fallback tests", "M3d3_MCCSubstepping", "completed", "fallback is not validation"),
        ("M3f", "MCC return/staging refinement", "ramp and proactive adaptive substepping tests", "M3f_MCCReturnStagingRefinement", "completed", "no clean candidate"),
        ("M3h", "admissible line-search diagnostics", "admissible Newton/line-search checks", "M3h_MCCAdmissibleReturn", "completed", "no clean candidate"),
        ("M3j-B", "boundary-induced failure audit", "postprocessed failure localization and boundary role", "M3j_BoundaryFailureAudit", "completed", "points to boundary path"),
        ("M3k", "dense platen/edge diagnostic", "captured failure onset and local support/strain evidence", "M3k_PlatenEdgeDenseDiagnostic", "completed", "very-short dense diagnostic"),
        ("M3l", "platen/specimen smoothing", "tested gap, overhang, and selector-buffer variants", "M3l_PlatenSpecimenSmoothing", "completed", "overhang helps but not clean"),
        ("M3m", "refined platen-edge geometry", "tested overhang045 and edge/cap refinements", "M3m_RefinedPlatenEdgeGeometry", "completed", "extended overhang still not clean"),
        ("M3n", "smooth Cartesian refinement", "higher-resolution cut-cell diagnostic", "M3n_SmoothLayoutDiagnostic", "completed", "support improves but statuses worsen"),
        ("M3o", "fan-like generator feasibility", "standalone radial-ring generator and support diagnostics", "M3o_SmoothFanLayoutPrototype", "completed", "not connected to solver"),
    ]
    return [
        {
            "stage": stage,
            "item": item,
            "role": role,
            "source_directory": src,
            "status": status,
            "main_caveat": caveat,
        }
        for stage, item, role, src, status, caveat in rows
    ]


def summary_metrics():
    rows = []
    t5c = last_by_case(read_csv(EXP / "T5c_DPExtendedFeedbackOff" / "t5c_case_summary.csv"))
    m3d = last_by_case(read_csv(EXP / "M3d_MCCFeedbackOffRefinement" / "m3d_case_summary.csv"))
    m3d3 = last_by_case(read_csv(EXP / "M3d3_MCCSubstepping" / "m3d3_case_summary.csv"))
    m3m = read_csv(EXP / "M3m_RefinedPlatenEdgeGeometry" / "m3m_case_summary.csv")
    m3n = read_csv(EXP / "M3n_SmoothLayoutDiagnostic" / "m3n_case_summary.csv")
    m3o = read_csv(EXP / "M3o_SmoothFanLayoutPrototype" / "m3o_layout_comparison.csv")

    def add(stage, case, model, code="", excluded="", dtmin="", time="", p="", q="", reaction="", pore="", kplastic="", status="", caveat=""):
        rows.append(
            {
                "stage": stage,
                "case": case,
                "model": model,
                "code": code,
                "excluded": excluded,
                "dtmin_adjustments": dtmin,
                "time": time,
                "p_proxy": p,
                "q_proxy": q,
                "pairwise_reaction_avg": reaction,
                "pore_pressure_mean": pore,
                "kplastic_max": kplastic,
                "return_status_counts": status,
                "caveat": caveat,
            }
        )

    for case, label in [("dp_high_strength", "T5c high-strength DP"), ("dp_mild_yield", "T5c mild DP")]:
        row = t5c[case]
        pairwise_avg = 0.5 * (abs(fnum(row["final_top_force_z"], 0.0)) + abs(fnum(row["final_bottom_force_z"], 0.0)))
        add("T5c", label, "DP", row["code"], row["excluded"], row["dtmin_adjustments"], "0.018", row["final_p_eff_proxy"], row["final_q_proxy"], pairwise_avg, row["final_porepress_mean"], row["final_kplastic_max"], "", "feedback off")
    for case, label in [("mcc_high_pc", "M3d high-pc MCC"), ("mcc_mild_yield", "M3d mild MCC")]:
        row = m3d[case]
        add("M3d", label, "MCC", row["code"], row["excluded"], row["dtmin_adjustments"], row["time"], row["p_proxy"], row["q_proxy"], row["pairwise_reaction_avg_compression"], row["PorePress_mean"], row["Kplastic_max"], row["MccReturnStatus_counts"], "feedback off; mild case not clean" if case == "mcc_mild_yield" else "elastic-like reference")
    for case, row in m3d3.items():
        add("M3d3", case, "MCC robustness", row["code"], row["excluded"], row["dtmin_adjustments"], "", row["final_p_proxy"], row["final_q_proxy"], row["final_pairwise_reaction_avg"], row["final_PorePress_mean"], row["final_Kplastic_max"], row["final_status_counts"], "substepping/fallback diagnostic")
    for row in m3m:
        add("M3m", row["variant"], "geometry diagnostic", row["code"], row["excluded"], row["dtmin_adjustments"], row["final_time"], "", "", "", "", "", f"-3:{row['final_status_-3']}|-1:{row['final_status_-1']}", "refined overhang/edge geometry")
    for row in m3n:
        add("M3n", row["variant"], "smooth Cartesian geometry", row["code"], row["excluded"], row["dtmin_adjustments"], row.get("final_time", ""), "", "", "", "", "", f"max -3:{row.get('max_status_-3','')} max -1:{row.get('max_status_-1','')}", "higher-resolution cut-cell")
    for row in m3o:
        add("M3o", row["case"], "fan-like geometry", "", "", "", "", "", "", "", "", "", "not run", row["solver_status"])
    return rows


def mcc_state_summary():
    rows = []
    m3d = last_by_case(read_csv(EXP / "M3d_MCCFeedbackOffRefinement" / "m3d_case_summary.csv"))
    for case, row in m3d.items():
        rows.append(
            {
                "stage": "M3d",
                "case": case,
                "pc_min": row["MccPc_min"],
                "pc_mean": row["MccPc_mean"],
                "pc_max": row["MccPc_max"],
                "void_ratio_mean": row["MccVoidRatio_mean"],
                "plastic_vol_strain_mean": row["MccPlasticVolStrain_mean"],
                "eq_plastic_strain_max": row["MccEqPlasticStrain_max"],
                "yield_fraction": row["MccYieldFlag_fraction"],
                "return_iterations_max": row["MccReturnIterations_max"],
                "yield_residual_converged_maxAbs": row["MccYieldResidual_converged_maxAbs"],
                "status_counts": row["MccReturnStatus_counts"],
            }
        )
    m3d3 = read_csv(EXP / "M3d3_MCCSubstepping" / "m3d3_case_summary.csv")
    for row in m3d3:
        rows.append(
            {
                "stage": "M3d3",
                "case": row["case"],
                "pc_min": row["final_MccPc_min"],
                "pc_mean": row["final_MccPc_mean"],
                "pc_max": row["final_MccPc_max"],
                "void_ratio_mean": row["final_MccVoidRatio_mean"],
                "plastic_vol_strain_mean": row["final_MccPlasticVolStrain_mean"],
                "eq_plastic_strain_max": row["final_MccEqPlasticStrain_max"],
                "yield_fraction": row["final_yield_fraction"],
                "return_iterations_max": row["final_return_iterations_max"],
                "yield_residual_converged_maxAbs": row["final_yield_residual_converged_maxAbs"],
                "status_counts": row["final_status_counts"],
            }
        )
    return rows


def return_status_summary():
    rows = [
        {"stage": "M3d", "case": "mild extended", "max_minus3": 8, "final_minus3": 8, "final_minus1": 0, "fallback_minus5": 0, "clean": "no", "note": "original-rate line-search failures remain"},
        {"stage": "M3d2", "case": "half-speed diagnostic", "max_minus3": "transient", "final_minus3": 0, "final_minus1": 0, "fallback_minus5": 0, "clean": "no", "note": "final clean but transient episodes remain"},
        {"stage": "M3d3", "case": "baseline", "max_minus3": 8, "final_minus3": 8, "final_minus1": 0, "fallback_minus5": 0, "clean": "no", "note": "single-step baseline"},
        {"stage": "M3d3", "case": "fixed substeps 4", "max_minus3": 18, "final_minus3": 18, "final_minus1": 8, "fallback_minus5": 0, "clean": "no", "note": "worse than baseline"},
        {"stage": "M3d3", "case": "adaptive substeps 16", "max_minus3": 10, "final_minus3": 10, "final_minus1": 8, "fallback_minus5": 0, "clean": "no", "note": "not clean"},
        {"stage": "M3d3", "case": "adaptive fallback 16", "max_minus3": 0, "final_minus3": 0, "final_minus1": 0, "fallback_minus5": 17, "clean": "no", "note": "fallback is not validation"},
        {"stage": "M3d3", "case": "half-speed adaptive", "max_minus3": "transient", "final_minus3": 0, "final_minus1": 0, "fallback_minus5": 0, "clean": "no", "note": "final clean but transient failures"},
        {"stage": "M3f", "case": "original-rate improved adaptive", "max_minus3": 28, "final_minus3": 28, "final_minus1": 19, "fallback_minus5": 0, "clean": "no", "note": "proactive substepping worsened tested threshold"},
        {"stage": "M3h", "case": "admissible line-search", "max_minus3": 8, "final_minus3": 8, "final_minus1": 0, "fallback_minus5": 0, "clean": "no", "note": "original-rate not improved"},
        {"stage": "M3m", "case": "overhang045 short", "max_minus3": 8, "final_minus3": 0, "final_minus1": 0, "fallback_minus5": 0, "clean": "no", "note": "short final clean but bad frames remain"},
        {"stage": "M3m", "case": "overhang045 extended", "max_minus3": 12, "final_minus3": 5, "final_minus1": 0, "fallback_minus5": 0, "clean": "no", "note": "extended check not clean"},
        {"stage": "M3n", "case": "Dp0075 Cartesian", "max_minus3": 16, "final_minus3": "transient", "final_minus1": 52, "fallback_minus5": 0, "clean": "no", "note": "Cartesian refinement worsened return populations"},
        {"stage": "M3o", "case": "radial-ring generator", "max_minus3": "", "final_minus3": "", "final_minus1": "", "fallback_minus5": "", "clean": "not tested", "note": "geometry only; no solver run"},
    ]
    return rows


def boundary_failure_evidence():
    return [
        {"evidence": "Failure localization", "finding": "MCC failed returns concentrate in edge/cap/platen-adjacent regions; measurement core is rarely the trigger.", "source": "M3j-B/M3k"},
        {"evidence": "First dense onset", "finding": "At t=0.001005 s, M3k captured ReturnStatus=-1:92 and ReturnStatus=-3:4.", "source": "M3k"},
        {"evidence": "First -3 location", "finding": "The first -3 particles are four symmetric top edge/corner particles.", "source": "M3k"},
        {"evidence": "Support deficit", "finding": "First -3 support/core is about 0.618; specimen-neighbor proxy is 56 versus core about 178.", "source": "M3k"},
        {"evidence": "Kinematic anomaly", "finding": "First -3 local velocity-gradient proxy is about 0.112 versus same-region nonfailed about 0.075 and core about 0.027.", "source": "M3k"},
        {"evidence": "Stress-path anomaly", "finding": "First -3 particles have p' about 73.97 Pa, q about 93.76 Pa, q/p' about 1.27, residual about 3888.", "source": "M3k"},
        {"evidence": "Geometry sensitivity", "finding": "Platen overhang changes the failure population without changing MCC return mapping.", "source": "M3l/M3m"},
        {"evidence": "Non-global behavior", "finding": "pc/e/plastic strain, pairwise reaction, p'-q, and pore pressure remain bounded.", "source": "M3d-M3m"},
    ]


def geometry_route_summary():
    rows = [
        {"stage": "M3l", "route": "gap_2dp", "effect": "removed -3 in short dense case but badly worsened -1", "max_minus3": 0, "max_minus1": 258, "support_note": "not acceptable"},
        {"stage": "M3l", "route": "platen_overhang", "effect": "reduced -3 and strongly reduced -1", "max_minus3": 8, "max_minus1": 20, "support_note": "support/core 0.828 -> 0.966 for failed subset"},
        {"stage": "M3l", "route": "edge_selector_buffer", "effect": "not enough improvement", "max_minus3": 13, "max_minus1": 174, "support_note": "not acceptable"},
        {"stage": "M3m", "route": "overhang045", "effect": "best short-frame geometry; delayed first -3 and reduced -1", "max_minus3": 8, "max_minus1": 8, "support_note": "short final clean but transient remains"},
        {"stage": "M3m", "route": "overhang045_extended", "effect": "not clean after extension", "max_minus3": 12, "max_minus1": 8, "support_note": "final -3=5"},
        {"stage": "M3n", "route": "Dp0075 Cartesian refinement", "effect": "support metrics improve but statuses worsen", "max_minus3": 16, "max_minus1": 52, "support_note": "specimen 407 -> 1035; edge support 0.808 -> 0.851"},
        {"stage": "M3o", "route": "external radial-ring generator", "effect": "geometry-only; angular regularity and edge neighbor improve", "max_minus3": "", "max_minus1": "", "support_note": "edge neighbor 113.64, angular gap CV ~0, no solver import"},
    ]
    return rows


def reaction_summary():
    rows = []
    for src, fname in [
        ("T4t", "T4t_TruePlatenReaction/t4t_reaction_vs_proxy_comparison.csv"),
        ("T5c", "T5c_DPExtendedFeedbackOff/t5c_reaction_vs_proxy_comparison.csv"),
    ]:
        for row in read_csv(EXP / fname):
            rows.append(
                {
                    "stage": src,
                    "case": row["case"],
                    "Fz_proxy": row["Fz_proxy"],
                    "pairwise_reaction_avg": row["reaction_force_avg_compression"],
                    "pairwise_over_Fz_proxy": row["reaction_over_proxy_force"],
                    "force_balance_error": row["force_balance_error"],
                    "p_proxy": row["p_eff_proxy"],
                    "q_proxy": row["q_proxy"],
                    "reaction_type": row["reaction_type"],
                }
            )
    m3d = read_csv(EXP / "M3d_MCCFeedbackOffRefinement" / "m3d_case_summary.csv")
    for row in m3d:
        rows.append(
            {
                "stage": "M3d",
                "case": row["case"],
                "Fz_proxy": row["Fz_proxy"],
                "pairwise_reaction_avg": row["pairwise_reaction_avg_compression"],
                "pairwise_over_Fz_proxy": row["pairwise_over_Fz_proxy"],
                "force_balance_error": row["force_balance_error"],
                "p_proxy": row["p_proxy"],
                "q_proxy": row["q_proxy"],
                "reaction_type": row["reaction_type"],
            }
        )
    return rows


def pore_pressure_summary():
    rows = []
    for stage, path, case_field, pore_field, ppr_field in [
        ("T5c", "T5c_DPExtendedFeedbackOff/t5c_case_summary.csv", "case", "final_porepress_mean", "final_porepressrate_maxabs"),
        ("M3d", "M3d_MCCFeedbackOffRefinement/m3d_case_summary.csv", "case", "PorePress_mean", "PorePressRate_maxAbs"),
        ("M3d3", "M3d3_MCCSubstepping/m3d3_case_summary.csv", "case", "final_PorePress_mean", "final_PorePressRate_maxAbs"),
    ]:
        for row in read_csv(EXP / path):
            rows.append(
                {
                    "stage": stage,
                    "case": row[case_field],
                    "pore_pressure_mean": row[pore_field],
                    "pore_press_rate_max_abs": row[ppr_field],
                    "interpretation": "bounded feedback-off diagnostic; not strict undrained validation",
                }
            )
    return rows


def no_go_table():
    return [
        {"gate": "clean MCC return status", "evidence": "Original-rate mild MCC retains ReturnStatus=-3; all clean-looking slower/fallback routes have transient or fallback caveats.", "decision": "not clean"},
        {"gate": "fallback-free validation", "evidence": "Adaptive fallback removes -3 only by producing -5 partial fallback.", "decision": "fallback cannot be validation"},
        {"gate": "boundary independence", "evidence": "Failures localize to edge/cap/platen-adjacent particles and respond strongly to geometry changes.", "decision": "boundary-induced path unresolved"},
        {"gate": "smooth layout solver path", "evidence": "M3o generator works, but direct arbitrary particle-cloud import is not confirmed.", "decision": "custom import deferred"},
        {"gate": "full u-pw feedback", "evidence": "Feedback instability remains outside this feedback-off route.", "decision": "deferred"},
        {"gate": "GPU MCC", "evidence": "SoilConstitutiveModel=3 still hard-errors on GPU.", "decision": "deferred"},
        {"gate": "paper-level validation", "evidence": "No full feedback, no clean return status, no true actuator reaction, no custom smooth solver layout.", "decision": "not claimed"},
    ]


def plot_axial_stress_strain():
    fig, ax = plt.subplots(figsize=(7, 4.8))
    series = [
        ("T5c DP high", EXP / "T5c_DPExtendedFeedbackOff/t5c_axial_stress_strain_metrics.csv", "dp_high_strength", "reaction_axial_stress_avg"),
        ("T5c DP mild", EXP / "T5c_DPExtendedFeedbackOff/t5c_axial_stress_strain_metrics.csv", "dp_mild_yield", "reaction_axial_stress_avg"),
        ("M3d MCC high-pc", EXP / "M3d_MCCFeedbackOffRefinement/m3d_axial_stress_strain_metrics.csv", "mcc_high_pc", "reaction_axial_stress_avg"),
        ("M3d MCC mild", EXP / "M3d_MCCFeedbackOffRefinement/m3d_axial_stress_strain_metrics.csv", "mcc_mild_yield", "reaction_axial_stress_avg"),
    ]
    for label, path, case, yfield in series:
        rows = [r for r in read_csv(path) if r["case"] == case]
        ax.plot([abs(fnum(r.get("axial_strain_proxy", r.get("specimen_axial_strain_proxy")))) for r in rows], [fnum(r[yfield]) for r in rows], label=label)
    ax.set_xlabel("axial strain proxy")
    ax.set_ylabel("reaction axial stress proxy (Pa)")
    ax.set_title("DP vs MCC reaction-based stress-strain")
    ax.legend(fontsize=8)
    save(fig, "main_01_dp_mcc_axial_stress_strain")


def plot_pq_paths():
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    series = [
        ("T5c DP high", EXP / "T5c_DPExtendedFeedbackOff/t5c_axial_stress_strain_metrics.csv", "dp_high_strength", "p_eff_proxy"),
        ("T5c DP mild", EXP / "T5c_DPExtendedFeedbackOff/t5c_axial_stress_strain_metrics.csv", "dp_mild_yield", "p_eff_proxy"),
        ("M3d MCC high-pc", EXP / "M3d_MCCFeedbackOffRefinement/m3d_axial_stress_strain_metrics.csv", "mcc_high_pc", "p_proxy"),
        ("M3d MCC mild", EXP / "M3d_MCCFeedbackOffRefinement/m3d_axial_stress_strain_metrics.csv", "mcc_mild_yield", "p_proxy"),
    ]
    for label, path, case, pfield in series:
        rows = [r for r in read_csv(path) if r["case"] == case]
        ax.plot([fnum(r[pfield]) for r in rows], [fnum(r["q_proxy"]) for r in rows], label=label)
    ax.set_xlabel("p' proxy (Pa)")
    ax.set_ylabel("q proxy (Pa)")
    ax.set_title("DP vs MCC p'-q paths")
    ax.legend(fontsize=8)
    save(fig, "main_02_dp_mcc_pq_paths")


def plot_mcc_state():
    rows = read_csv(EXP / "M3d_MCCFeedbackOffRefinement/m3d_mcc_state_metrics.csv")
    mild = [r for r in rows if r["case"] == "mcc_mild_yield"]
    high = [r for r in rows if r["case"] == "mcc_high_pc"]
    fig, ax = plt.subplots(figsize=(7, 4.8))
    for label, data in [("MCC high-pc", high), ("MCC mild", mild)]:
        ax.plot([abs(fnum(r["axial_strain_proxy"])) for r in data], [fnum(r["MccPc_mean"]) for r in data], label=label)
    ax.set_xlabel("axial strain proxy")
    ax.set_ylabel("pc mean (Pa)")
    ax.set_title("MCC preconsolidation pressure evolution")
    ax.legend()
    save(fig, "main_03_mcc_pc_evolution")

    fig, ax = plt.subplots(figsize=(7, 4.8))
    ax.plot([abs(fnum(r["axial_strain_proxy"])) for r in mild], [fnum(r["MccVoidRatio_mean"]) for r in mild], label="void ratio mean")
    ax2 = ax.twinx()
    ax2.plot([abs(fnum(r["axial_strain_proxy"])) for r in mild], [fnum(r["MccPlasticVolStrain_mean"]) for r in mild], color="#d62728", label="plastic volumetric strain mean")
    ax.set_xlabel("axial strain proxy")
    ax.set_ylabel("void ratio")
    ax2.set_ylabel("plastic volumetric strain")
    ax.set_title("MCC mild void ratio and plastic strain")
    ax.legend(loc="upper left")
    ax2.legend(loc="lower right")
    save(fig, "main_04_mcc_void_plastic_evolution")


def plot_return_status():
    rows = return_status_summary()
    labels = [f"{r['stage']}\n{r['case']}" for r in rows if r["stage"] in ("M3d", "M3d3", "M3f", "M3m", "M3n")]
    minus3 = [fnum(r["final_minus3"], 0.0) for r in rows if r["stage"] in ("M3d", "M3d3", "M3f", "M3m", "M3n")]
    minus1 = [fnum(r["final_minus1"], 0.0) for r in rows if r["stage"] in ("M3d", "M3d3", "M3f", "M3m", "M3n")]
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar([i - 0.2 for i in x], minus3, width=0.4, label="final -3")
    ax.bar([i + 0.2 for i in x], minus1, width=0.4, label="final -1")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("particle count")
    ax.set_title("MCC return-status comparison")
    ax.legend()
    save(fig, "main_05_return_status_comparison")


def plot_boundary_evidence():
    labels = ["first -3", "same region nonfailed", "core"]
    support = [0.618, 0.828, 1.0]
    grad = [0.112, 0.075, 0.027]
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.4))
    axes[0].bar(labels, support, color=["#d62728", "#ffbf00", "#2ca02c"])
    axes[0].set_ylabel("support/core proxy")
    axes[0].set_title("Failure support deficit")
    axes[1].bar(labels, grad, color=["#d62728", "#ffbf00", "#2ca02c"])
    axes[1].set_ylabel("velocity-gradient proxy")
    axes[1].set_title("Local strain-path anomaly")
    save(fig, "main_06_boundary_failure_evidence")


def plot_reaction_vs_proxy():
    rows = reaction_summary()
    selected = [r for r in rows if r["stage"] in ("T4t", "T5c", "M3d")]
    labels = [f"{r['stage']} {r['case']}" for r in selected]
    pairwise = [fnum(r["pairwise_reaction_avg"]) for r in selected]
    proxy = [fnum(r["Fz_proxy"]) for r in selected]
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar([i - 0.2 for i in x], pairwise, width=0.4, label="pairwise reaction")
    ax.bar([i + 0.2 for i in x], proxy, width=0.4, label="Fz_proxy")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("force (N)")
    ax.set_title("Pairwise reaction vs Fz_proxy")
    ax.legend()
    save(fig, "main_07_pairwise_reaction_vs_fz_proxy")


def plot_pore_pressure():
    fig, ax = plt.subplots(figsize=(7, 4.8))
    series = [
        ("T5c DP high", EXP / "T5c_DPExtendedFeedbackOff/t5c_pore_pressure_strain_metrics.csv", "dp_high_strength"),
        ("T5c DP mild", EXP / "T5c_DPExtendedFeedbackOff/t5c_pore_pressure_strain_metrics.csv", "dp_mild_yield"),
        ("M3d MCC high-pc", EXP / "M3d_MCCFeedbackOffRefinement/m3d_pore_pressure_metrics.csv", "mcc_high_pc"),
        ("M3d MCC mild", EXP / "M3d_MCCFeedbackOffRefinement/m3d_pore_pressure_metrics.csv", "mcc_mild_yield"),
    ]
    for label, path, case in series:
        rows = [r for r in read_csv(path) if r["case"] == case]
        strain_field = "axial_strain_proxy" if "axial_strain_proxy" in rows[0] else "specimen_axial_strain_proxy"
        if "PorePress_mean" in rows[0]:
            pore_field = "PorePress_mean"
        elif "pore_pressure_mean" in rows[0]:
            pore_field = "pore_pressure_mean"
        else:
            pore_field = "porepress_mean"
        ax.plot([abs(fnum(r[strain_field])) for r in rows], [fnum(r[pore_field]) for r in rows], label=label)
    ax.set_xlabel("axial strain proxy")
    ax.set_ylabel("mean PorePress (Pa)")
    ax.set_title("Feedback-off pore pressure vs axial strain")
    ax.legend(fontsize=8)
    save(fig, "main_08_pore_pressure_vs_strain")


def plot_geometry_routes():
    rows = geometry_route_summary()
    labels = [f"{r['stage']}\n{r['route']}" for r in rows]
    m3 = [fnum(r["max_minus3"], 0.0) for r in rows]
    m1 = [fnum(r["max_minus1"], 0.0) for r in rows]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = range(len(labels))
    ax.bar([i - 0.2 for i in x], m3, width=0.4, label="max -3")
    ax.bar([i + 0.2 for i in x], m1, width=0.4, label="max -1")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("particle count")
    ax.set_title("Geometry route return-status outcomes")
    ax.legend()
    save(fig, "supp_01_geometry_route_status")

    m3o = read_csv(EXP / "M3o_SmoothFanLayoutPrototype/m3o_layout_comparison.csv")
    labels = [r["case"].replace("_", "\n") for r in m3o]
    edge_support = [fnum(r["edge_support_core_ratio"]) for r in m3o]
    edge_neighbor = [fnum(r["edge_neighbor_mean"]) for r in m3o]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
    x = range(len(labels))
    axes[0].bar(x, edge_support)
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    axes[0].set_ylabel("edge support/core")
    axes[0].set_title("Edge support")
    axes[1].bar(x, edge_neighbor)
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    axes[1].set_ylabel("edge neighbor proxy")
    axes[1].set_title("Edge neighbor proxy")
    save(fig, "supp_02_support_neighbor_geometry")


def plot_supplementary_stability():
    rows = read_csv(EXP / "M3d_MCCFeedbackOffRefinement/m3d_stability_metrics.csv")
    fig, ax = plt.subplots(figsize=(7, 4.8))
    for case in sorted({r["case"] for r in rows}):
        data = [r for r in rows if r["case"] == case]
        ax.plot([fnum(r["time"]) for r in data], [fnum(r["velocity_max"]) for r in data], label=case)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("velocity max (m/s)")
    ax.set_title("M3d velocity boundedness")
    ax.legend(fontsize=8)
    save(fig, "supp_03_velocity_max")

    fig, ax = plt.subplots(figsize=(7, 4.8))
    for case in sorted({r["case"] for r in rows}):
        data = [r for r in rows if r["case"] == case]
        ax.plot([fnum(r["time"]) for r in data], [fnum(r["PorePressRate_maxAbs"]) for r in data], label=case)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("PorePressRate maxAbs")
    ax.set_title("M3d PorePressRate boundedness")
    ax.legend(fontsize=8)
    save(fig, "supp_04_porepressrate")


def main():
    write_csv(ROOT / "m3i_case_inventory.csv", case_inventory())
    write_csv(ROOT / "m3i_summary_metrics.csv", summary_metrics())
    write_csv(ROOT / "m3i_mcc_state_summary.csv", mcc_state_summary())
    write_csv(ROOT / "m3i_return_status_summary.csv", return_status_summary())
    write_csv(ROOT / "m3i_boundary_failure_evidence.csv", boundary_failure_evidence())
    write_csv(ROOT / "m3i_geometry_route_summary.csv", geometry_route_summary())
    write_csv(ROOT / "m3i_reaction_stress_path_summary.csv", reaction_summary())
    write_csv(ROOT / "m3i_pore_pressure_summary.csv", pore_pressure_summary())
    write_csv(ROOT / "m3i_no_go_decision_table.csv", no_go_table())

    plot_axial_stress_strain()
    plot_pq_paths()
    plot_mcc_state()
    plot_return_status()
    plot_boundary_evidence()
    plot_reaction_vs_proxy()
    plot_pore_pressure()
    plot_geometry_routes()
    plot_supplementary_stability()
    print("M3i caveated reduced package generated")


if __name__ == "__main__":
    main()
