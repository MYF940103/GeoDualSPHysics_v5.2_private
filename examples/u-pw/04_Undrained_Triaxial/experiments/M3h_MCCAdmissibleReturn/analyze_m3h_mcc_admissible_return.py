#!/usr/bin/env python3
"""Postprocess M3h MCC admissible return diagnostics."""

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
    "baseline": "CaseM3h_MCCMildBaseline",
    "admissible_line": "CaseM3h_MCCMildAdmissibleLine",
    "adaptive_line": "CaseM3h_MCCMildAdaptiveLine",
    "half_speed_adaptive_line": "CaseM3h_MCCMildHalfSpeedAdaptiveLine",
    "quarter_speed_line": "CaseM3h_MCCMildQuarterSpeedLine",
}

RADIUS = 0.03
HEIGHT = 0.10
AREA0 = math.pi * RADIUS * RADIUS
EDGE_R = 0.020
CAP_Z = 0.015


def read_rows(path: Path):
    with path.open(newline="") as f:
        reader = csv.reader(f, delimiter=";")
        headers = [h.strip() for h in next(reader) if h.strip()]
        rows = []
        for raw in reader:
            if len(raw) < len(headers):
                continue
            row = {}
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


def part_files(case: str):
    return sorted((ROOT / f"{case}_out" / "data").glob("PartCsv_*.csv"), key=part_index)


def parse_times(case: str):
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


def parse_reactions(case_key: str, case: str):
    run = ROOT / f"{case}_out" / "Run.out"
    if not run.exists():
        return []
    rx = re.compile(
        r"PlatenReaction diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[0-9Ee+\-.]+).*?"
        r"top_force=\((?P<tfx>[0-9Ee+\-.]+),(?P<tfy>[0-9Ee+\-.]+),(?P<tfz>[0-9Ee+\-.]+)\).*?"
        r"bottom_force=\((?P<bfx>[0-9Ee+\-.]+),(?P<bfy>[0-9Ee+\-.]+),(?P<bfz>[0-9Ee+\-.]+)\).*?"
        r"force_balance_error=(?P<balance>[0-9Ee+\-.]+)"
    )
    rows = []
    for line in run.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if not m:
            continue
        vals = {k: float(v.rstrip(".")) for k, v in m.groupdict().items() if k != "step"}
        rows.append({"case": case_key, "step": int(m.group("step")), **vals})
    return rows


def run_summary(case_key: str, case: str):
    run = ROOT / f"{case}_out" / "Run.out"
    text = run.read_text(errors="ignore") if run.exists() else ""
    out = {"case": case_key, "case_name": case, "code": 0 if "Finished execution (code=0)" in text else -1}
    for key, pattern in [
        ("excluded", r"Excluded particles\.+:\s+(\d+)"),
        ("dtmin_adjustments", r"DTs adjusted to DtMin\.+:\s+(\d+)"),
        ("steps", r"Steps of simulation\.+:\s+(\d+)"),
    ]:
        m = re.search(pattern, text)
        out[key] = int(m.group(1)) if m else -1
    return out


def safe_mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else float("nan")


def safe_std(values: Iterable[float]) -> float:
    vals = list(values)
    if len(vals) < 2:
        return 0.0 if vals else float("nan")
    mu = safe_mean(vals)
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))


def specimen(row) -> bool:
    return int(row.get("Type", -1)) == 3


def velocity_mag(row) -> float:
    return math.sqrt(
        float(row.get("Vel.x [m/s]", 0.0)) ** 2
        + float(row.get("Vel.y [m/s]", 0.0)) ** 2
        + float(row.get("Vel.z [m/s]", 0.0)) ** 2
    )


def stress_invariants(row):
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


def axial_strain(rows):
    spec = [r for r in rows if specimen(r)]
    if not spec:
        return float("nan")
    height = max(float(r["Pos.z [m]"]) for r in spec) - min(float(r["Pos.z [m]"]) for r in spec)
    return (HEIGHT - height) / HEIGHT


def region(row, zmin, zmax):
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


def nearest_reaction(time: float, reactions):
    if not reactions:
        return None
    return min(reactions, key=lambda r: abs(float(r["time"]) - time))


def write_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_lines(pathstem: str, rows, xkey: str, ykey: str, ylabel: str, cases=None):
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for case in (cases or CASES.keys()):
        cr = [r for r in rows if r["case"] == case and math.isfinite(float(r.get(ykey, float("nan"))))]
        if not cr:
            continue
        ax.plot([float(r[xkey]) for r in cr], [float(r[ykey]) for r in cr], label=case)
    ax.set_xlabel(xkey)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGDIR / f"{pathstem}.svg")
    fig.savefig(FIGDIR / f"{pathstem}.png", dpi=180)
    plt.close(fig)


def process_case(case_key: str, case: str):
    times = parse_times(case)
    reactions = parse_reactions(case_key, case)
    frames = []
    failed_rows = []
    region_rows = []
    ret_timeline = []
    line_rows = []
    admiss_rows = []
    substep_rows = []
    zref = None

    for path in part_files(case):
        part = part_index(path)
        rows = read_rows(path)
        spec = [r for r in rows if specimen(r)]
        if not spec:
            continue
        time = times.get(part, float(part))
        zmin = min(float(r["Pos.z [m]"]) for r in spec)
        zmax = max(float(r["Pos.z [m]"]) for r in spec)
        if zref is None:
            zref = (zmin, zmax)
        zmin0, zmax0 = zref
        pvals, qvals = zip(*(stress_invariants(r) for r in spec))
        status = Counter(int(round(float(r.get("MccReturnStatus", 0.0)))) for r in spec)
        reject = Counter(int(round(float(r.get("MccLineSearchRejectReason", 0.0)))) for r in spec)
        trigger = Counter(int(round(float(r.get("MccSubstepTriggerReason", 0.0)))) for r in spec)
        reaction = nearest_reaction(time, reactions)
        fz_proxy = -safe_mean(float(r.get("Sigma_kk.z", 0.0)) for r in spec) * AREA0
        pairwise = float("nan")
        balance = float("nan")
        if reaction:
            pairwise = 0.5 * (float(reaction["tfz"]) + abs(float(reaction["bfz"])))
            balance = float(reaction["balance"])

        frame = {
            "case": case_key,
            "case_name": case,
            "part": part,
            "time": time,
            "axial_strain": axial_strain(rows),
            "p_proxy": safe_mean(pvals),
            "q_proxy": safe_mean(qvals),
            "Fz_proxy": fz_proxy,
            "pairwise_reaction_avg": pairwise,
            "force_balance_error": balance,
            "MccPc_mean": safe_mean(float(r.get("MccPc", 0.0)) for r in spec),
            "MccPc_min": min(float(r.get("MccPc", 0.0)) for r in spec),
            "MccPc_max": max(float(r.get("MccPc", 0.0)) for r in spec),
            "MccVoidRatio_mean": safe_mean(float(r.get("MccVoidRatio", 0.0)) for r in spec),
            "MccVoidRatio_min": min(float(r.get("MccVoidRatio", 0.0)) for r in spec),
            "MccVoidRatio_max": max(float(r.get("MccVoidRatio", 0.0)) for r in spec),
            "MccPlasticVolStrain_mean": safe_mean(float(r.get("MccPlasticVolStrain", 0.0)) for r in spec),
            "MccEqPlasticStrain_mean": safe_mean(float(r.get("MccEqPlasticStrain", 0.0)) for r in spec),
            "MccYieldFlag_count": sum(1 for r in spec if float(r.get("MccYieldFlag", 0.0)) > 0.5),
            "MccPlasticMultiplier_max": max(float(r.get("MccPlasticMultiplier", 0.0)) for r in spec),
            "MccReturnIterations_max": max(float(r.get("MccReturnIterations", 0.0)) for r in spec),
            "MccReturnIterations_mean": safe_mean(float(r.get("MccReturnIterations", 0.0)) for r in spec),
            "MccYieldResidual_raw_maxAbs": max(abs(float(r.get("MccYieldResidual", 0.0))) for r in spec),
            "MccYieldResidual_converged_maxAbs": max(
                [abs(float(r.get("MccYieldResidual", 0.0))) for r in spec if int(round(float(r.get("MccReturnStatus", 0.0)))) in (1, 2)]
                or [0.0]
            ),
            "MccSubstepCount_max": max(float(r.get("MccSubstepCount", 0.0)) for r in spec),
            "MccSubstepCount_mean": safe_mean(float(r.get("MccSubstepCount", 0.0)) for r in spec),
            "MccSubstepFailureCount_sum": sum(float(r.get("MccSubstepFailureCount", 0.0)) for r in spec),
            "MccAdmissibilityFailureCount_sum": sum(float(r.get("MccAdmissibilityFailureCount", 0.0)) for r in spec),
            "MccFallbackUsed_sum": sum(float(r.get("MccFallbackUsed", 0.0)) for r in spec),
            "MccSubstepTriggerReason_max": max(float(r.get("MccSubstepTriggerReason", 0.0)) for r in spec),
            "MccLineSearchBacktrackCount_max": max(float(r.get("MccLineSearchBacktrackCount", 0.0)) for r in spec),
            "MccLineSearchBacktrackCount_mean": safe_mean(float(r.get("MccLineSearchBacktrackCount", 0.0)) for r in spec),
            "MccLineSearchRejectReason_max": max(float(r.get("MccLineSearchRejectReason", 0.0)) for r in spec),
            "MccLineSearchMinAlpha_min_positive": min(
                [float(r.get("MccLineSearchMinAlpha", 0.0)) for r in spec if float(r.get("MccLineSearchMinAlpha", 0.0)) > 0.0]
                or [0.0]
            ),
            "PorePress_mean": safe_mean(float(r.get("PorePress", 0.0)) for r in spec),
            "PorePress_std": safe_std(float(r.get("PorePress", 0.0)) for r in spec),
            "PorePressRate_maxAbs": max(abs(float(r.get("PorePressRate", 0.0))) for r in spec),
            "DivVel_maxAbs": max(abs(float(r.get("DivVel", 0.0))) for r in spec),
            "velocity_max": max(velocity_mag(r) for r in spec),
            "Kplastic_max": max(float(r.get("Kplastic", 0.0)) for r in spec),
        }
        for st in [-8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2]:
            frame[f"ReturnStatus_{st}"] = status[st]
            ret_timeline.append({"case": case_key, "time": time, "status": st, "count": status[st]})
        for rr in range(0, 10):
            frame[f"RejectReason_{rr}"] = reject[rr]
            line_rows.append({"case": case_key, "time": time, "reject_reason": rr, "count": reject[rr]})
        for tr in [0, 1, 2, 3, 4, 5]:
            frame[f"Trigger_{tr}"] = trigger[tr]
            substep_rows.append({"case": case_key, "time": time, "trigger_reason": tr, "count": trigger[tr]})
        frames.append(frame)

        region_counter = defaultdict(Counter)
        for r in spec:
            reg = region(r, zmin0, zmax0)
            st = int(round(float(r.get("MccReturnStatus", 0.0))))
            region_counter[reg][st] += 1
            if st < 0:
                pval, qval = stress_invariants(r)
                failed_rows.append({
                    "case": case_key,
                    "part": part,
                    "time": time,
                    "idp": int(r.get("Idp", -1)),
                    "return_status": st,
                    "region": reg,
                    "x": float(r.get("Pos.x [m]", 0.0)),
                    "y": float(r.get("Pos.y [m]", 0.0)),
                    "z": float(r.get("Pos.z [m]", 0.0)),
                    "trial_state_available": 0,
                    "trial_p": float("nan"),
                    "trial_q": float("nan"),
                    "trial_pc": float("nan"),
                    "trial_yield_function": float("nan"),
                    "newton_initial_residual": float("nan"),
                    "line_search_step_residual_trace_available": 0,
                    "p_proxy": pval,
                    "q_proxy": qval,
                    "pc": float(r.get("MccPc", 0.0)),
                    "void_ratio": float(r.get("MccVoidRatio", 0.0)),
                    "plastic_vol_strain": float(r.get("MccPlasticVolStrain", 0.0)),
                    "eq_plastic_strain": float(r.get("MccEqPlasticStrain", 0.0)),
                    "plastic_multiplier": float(r.get("MccPlasticMultiplier", 0.0)),
                    "return_iterations": float(r.get("MccReturnIterations", 0.0)),
                    "yield_residual": float(r.get("MccYieldResidual", 0.0)),
                    "substep_count": float(r.get("MccSubstepCount", 0.0)),
                    "substep_trigger_reason": float(r.get("MccSubstepTriggerReason", 0.0)),
                    "line_search_backtracks": float(r.get("MccLineSearchBacktrackCount", 0.0)),
                    "line_search_reject_reason": float(r.get("MccLineSearchRejectReason", 0.0)),
                    "line_search_min_alpha": float(r.get("MccLineSearchMinAlpha", 0.0)),
                    "Kplastic": float(r.get("Kplastic", 0.0)),
                    "PorePress": float(r.get("PorePress", 0.0)),
                    "PorePressRate": float(r.get("PorePressRate", 0.0)),
                    "DivVel": float(r.get("DivVel", 0.0)),
                    "velocity": velocity_mag(r),
                    "pairwise_reaction_avg": pairwise,
                })
        for reg, counter in region_counter.items():
            row = {"case": case_key, "part": part, "time": time, "region": reg}
            for st in [-8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2]:
                row[f"status_{st}"] = counter[st]
            region_rows.append(row)

        admiss_rows.append({
            "case": case_key,
            "part": part,
            "time": time,
            "admissibility_failure_sum": frame["MccAdmissibilityFailureCount_sum"],
            "reject_reason_max": frame["MccLineSearchRejectReason_max"],
            "line_search_backtrack_max": frame["MccLineSearchBacktrackCount_max"],
            "line_search_min_alpha_min_positive": frame["MccLineSearchMinAlpha_min_positive"],
        })

    summary = run_summary(case_key, case)
    if frames:
        final = frames[-1]
        summary.update({
            "final_time": final["time"],
            "final_axial_strain": final["axial_strain"],
            "final_return_status_-5": final["ReturnStatus_-5"],
            "final_return_status_-4": final["ReturnStatus_-4"],
            "final_return_status_-3": final["ReturnStatus_-3"],
            "final_return_status_-1": final["ReturnStatus_-1"],
            "max_return_status_-5": max(f["ReturnStatus_-5"] for f in frames),
            "max_return_status_-4": max(f["ReturnStatus_-4"] for f in frames),
            "max_return_status_-3": max(f["ReturnStatus_-3"] for f in frames),
            "max_return_status_-1": max(f["ReturnStatus_-1"] for f in frames),
            "frames_with_negative_status": sum(1 for f in frames if any(f[f"ReturnStatus_{st}"] for st in [-8, -7, -6, -5, -4, -3, -2, -1])),
            "final_pc_mean": final["MccPc_mean"],
            "final_void_ratio_mean": final["MccVoidRatio_mean"],
            "final_plastic_vol_strain_mean": final["MccPlasticVolStrain_mean"],
            "final_eq_plastic_strain_mean": final["MccEqPlasticStrain_mean"],
            "final_pairwise_reaction_avg": final["pairwise_reaction_avg"],
            "final_p_proxy": final["p_proxy"],
            "final_q_proxy": final["q_proxy"],
            "final_porepress_mean": final["PorePress_mean"],
            "max_porepressrate_abs": max(f["PorePressRate_maxAbs"] for f in frames),
            "max_velocity": max(f["velocity_max"] for f in frames),
            "max_line_search_backtracks": max(f["MccLineSearchBacktrackCount_max"] for f in frames),
            "max_line_search_reject_reason": max(f["MccLineSearchRejectReason_max"] for f in frames),
            "min_positive_alpha": min([f["MccLineSearchMinAlpha_min_positive"] for f in frames if f["MccLineSearchMinAlpha_min_positive"] > 0.0] or [0.0]),
            "clean_candidate": int(all(all(f[f"ReturnStatus_{st}"] == 0 for st in [-8, -7, -6, -5, -4, -3, -2, -1]) for f in frames)),
        })
    return frames, failed_rows, region_rows, ret_timeline, line_rows, admiss_rows, substep_rows, summary


def main() -> None:
    all_frames = []
    all_failed = []
    all_region = []
    all_ret = []
    all_line = []
    all_admiss = []
    all_substep = []
    summaries = []
    for key, case in CASES.items():
        frames, failed, region_rows, ret_rows, line_rows, admiss_rows, substep_rows, summary = process_case(key, case)
        all_frames.extend(frames)
        all_failed.extend(failed)
        all_region.extend(region_rows)
        all_ret.extend(ret_rows)
        all_line.extend(line_rows)
        all_admiss.extend(admiss_rows)
        all_substep.extend(substep_rows)
        summaries.append(summary)

    write_csv(ROOT / "m3h_case_summary.csv", summaries)
    write_csv(ROOT / "m3h_return_status_timeline.csv", all_ret)
    write_csv(ROOT / "m3h_line_search_metrics.csv", [
        {
            "case": r["case"],
            "part": r["part"],
            "time": r["time"],
            "line_search_backtrack_max": r["MccLineSearchBacktrackCount_max"],
            "line_search_backtrack_mean": r["MccLineSearchBacktrackCount_mean"],
            "line_search_reject_reason_max": r["MccLineSearchRejectReason_max"],
            "line_search_min_alpha_min_positive": r["MccLineSearchMinAlpha_min_positive"],
        }
        for r in all_frames
    ])
    write_csv(ROOT / "m3h_admissibility_metrics.csv", all_admiss)
    write_csv(ROOT / "m3h_substep_metrics.csv", [
        {
            "case": r["case"],
            "part": r["part"],
            "time": r["time"],
            "substep_count_max": r["MccSubstepCount_max"],
            "substep_count_mean": r["MccSubstepCount_mean"],
            "substep_failure_sum": r["MccSubstepFailureCount_sum"],
            "substep_trigger_reason_max": r["MccSubstepTriggerReason_max"],
        }
        for r in all_frames
    ])
    write_csv(ROOT / "m3h_yield_residual_metrics.csv", [
        {
            "case": r["case"],
            "part": r["part"],
            "time": r["time"],
            "raw_max_abs": r["MccYieldResidual_raw_maxAbs"],
            "converged_max_abs": r["MccYieldResidual_converged_maxAbs"],
            "return_iterations_max": r["MccReturnIterations_max"],
            "return_iterations_mean": r["MccReturnIterations_mean"],
        }
        for r in all_frames
    ])
    write_csv(ROOT / "m3h_pc_ev_plastic_strain_metrics.csv", [
        {
            "case": r["case"],
            "part": r["part"],
            "time": r["time"],
            "axial_strain": r["axial_strain"],
            "pc_mean": r["MccPc_mean"],
            "pc_min": r["MccPc_min"],
            "pc_max": r["MccPc_max"],
            "void_ratio_mean": r["MccVoidRatio_mean"],
            "void_ratio_min": r["MccVoidRatio_min"],
            "void_ratio_max": r["MccVoidRatio_max"],
            "plastic_vol_strain_mean": r["MccPlasticVolStrain_mean"],
            "eq_plastic_strain_mean": r["MccEqPlasticStrain_mean"],
            "Kplastic_max": r["Kplastic_max"],
        }
        for r in all_frames
    ])
    write_csv(ROOT / "m3h_reaction_stress_path_metrics.csv", [
        {
            "case": r["case"],
            "part": r["part"],
            "time": r["time"],
            "axial_strain": r["axial_strain"],
            "pairwise_reaction_avg": r["pairwise_reaction_avg"],
            "Fz_proxy": r["Fz_proxy"],
            "force_balance_error": r["force_balance_error"],
            "p_proxy": r["p_proxy"],
            "q_proxy": r["q_proxy"],
        }
        for r in all_frames
    ])
    write_csv(ROOT / "m3h_pore_pressure_metrics.csv", [
        {
            "case": r["case"],
            "part": r["part"],
            "time": r["time"],
            "axial_strain": r["axial_strain"],
            "PorePress_mean": r["PorePress_mean"],
            "PorePress_std": r["PorePress_std"],
            "PorePressRate_maxAbs": r["PorePressRate_maxAbs"],
            "DivVel_maxAbs": r["DivVel_maxAbs"],
            "velocity_max": r["velocity_max"],
        }
        for r in all_frames
    ])
    write_csv(ROOT / "m3h_clean_candidate_summary.csv", summaries)
    write_csv(ROOT / "m3h_failed_return_state.csv", all_failed)
    write_csv(ROOT / "m3h_failed_return_region_summary.csv", all_region)
    write_csv(ROOT / "m3h_trial_state_diagnostics.csv", [
        {
            "case": r["case"],
            "part": r["part"],
            "time": r["time"],
            "idp": r["idp"],
            "trial_state_available": r["trial_state_available"],
            "trial_p": r["trial_p"],
            "trial_q": r["trial_q"],
            "trial_pc": r["trial_pc"],
            "trial_yield_function": r["trial_yield_function"],
            "newton_initial_residual": r["newton_initial_residual"],
            "line_search_step_residual_trace_available": r["line_search_step_residual_trace_available"],
            "line_search_backtracks": r["line_search_backtracks"],
            "line_search_reject_reason": r["line_search_reject_reason"],
            "line_search_min_alpha": r["line_search_min_alpha"],
        }
        for r in all_failed
    ])

    plot_lines("m3h_return_status_minus3", all_frames, "time", "ReturnStatus_-3", "ReturnStatus -3 count")
    plot_lines("m3h_return_status_minus5", all_frames, "time", "ReturnStatus_-5", "ReturnStatus -5 count")
    plot_lines("m3h_return_status_minus1", all_frames, "time", "ReturnStatus_-1", "ReturnStatus -1 count")
    plot_lines("m3h_line_search_backtrack_max", all_frames, "time", "MccLineSearchBacktrackCount_max", "max line-search backtracks")
    plot_lines("m3h_line_search_min_alpha", all_frames, "time", "MccLineSearchMinAlpha_min_positive", "min accepted alpha")
    plot_lines("m3h_admissibility_failures", all_frames, "time", "MccAdmissibilityFailureCount_sum", "admissibility failure count")
    plot_lines("m3h_substep_count_max", all_frames, "time", "MccSubstepCount_max", "max substep count")
    plot_lines("m3h_yield_residual_converged", all_frames, "time", "MccYieldResidual_converged_maxAbs", "converged |yield residual|")
    plot_lines("m3h_pc_mean", all_frames, "axial_strain", "MccPc_mean", "pc mean [Pa]")
    plot_lines("m3h_void_ratio_mean", all_frames, "axial_strain", "MccVoidRatio_mean", "void ratio mean")
    plot_lines("m3h_plastic_vol_strain", all_frames, "axial_strain", "MccPlasticVolStrain_mean", "plastic volumetric strain mean")
    plot_lines("m3h_eq_plastic_strain", all_frames, "axial_strain", "MccEqPlasticStrain_mean", "eq plastic strain mean")
    plot_lines("m3h_reaction_stress", all_frames, "axial_strain", "pairwise_reaction_avg", "pairwise reaction avg [N]")
    plot_lines("m3h_pore_pressure", all_frames, "axial_strain", "PorePress_mean", "mean pore pressure [Pa]")
    plot_lines("m3h_kplastic", all_frames, "time", "Kplastic_max", "Kplastic max")

    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    for case in CASES.keys():
        cr = [r for r in all_frames if r["case"] == case]
        if cr:
            ax.plot([r["p_proxy"] for r in cr], [r["q_proxy"] for r in cr], label=case)
    ax.set_xlabel("p' proxy [Pa]")
    ax.set_ylabel("q proxy [Pa]")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGDIR / "m3h_pq_path_comparison.svg")
    fig.savefig(FIGDIR / "m3h_pq_path_comparison.png", dpi=180)
    plt.close(fig)

    if all_failed:
        fig, ax = plt.subplots(figsize=(6.2, 4.8))
        colors = {
            "baseline": "tab:red",
            "admissible_line": "tab:orange",
            "adaptive_line": "tab:purple",
            "half_speed_adaptive_line": "tab:green",
            "quarter_speed_line": "tab:blue",
        }
        for case, color in colors.items():
            pts = [r for r in all_failed if r["case"] == case]
            if not pts:
                continue
            ax.scatter([r["x"] for r in pts], [r["z"] for r in pts], s=14, alpha=0.55, label=case, c=color)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("z [m]")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(FIGDIR / "m3h_failed_particle_locations.svg")
        fig.savefig(FIGDIR / "m3h_failed_particle_locations.png", dpi=180)
        plt.close(fig)


if __name__ == "__main__":
    main()
