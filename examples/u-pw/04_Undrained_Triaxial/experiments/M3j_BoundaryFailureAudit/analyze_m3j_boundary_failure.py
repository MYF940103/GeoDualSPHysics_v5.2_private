#!/usr/bin/env python3
"""Aggregate M3d2/M3f/M3h MCC return failures by boundary location."""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
EXP = ROOT.parent
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

RADIUS = 0.03
HEIGHT = 0.10
CAP_Z = 0.015
EDGE_R = 0.020
CORE_R = 0.010
CORE_Z0 = 0.025
CORE_Z1 = 0.075

INPUTS = [
    ("M3d2", EXP / "M3d2_MCCReturnRobustness" / "m3d2_failed_return_particles.csv"),
    ("M3f", EXP / "M3f_MCCReturnStagingRefinement" / "m3f_transient_failed_particles.csv"),
    ("M3h", EXP / "M3h_MCCAdmissibleReturn" / "m3h_failed_return_state.csv"),
]


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def f(row, *names, default=0.0):
    for name in names:
        if name in row and row[name] not in ("", "nan", "NaN"):
            try:
                return float(row[name])
            except ValueError:
                pass
    return default


def s(row, *names, default=""):
    for name in names:
        if name in row and row[name] != "":
            return row[name]
    return default


def write_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def boundary_class(x: float, y: float, z: float):
    r = math.hypot(x, y)
    near_bottom = z <= CAP_Z
    near_top = z >= HEIGHT - CAP_Z
    near_lateral = r >= EDGE_R
    in_core = r <= CORE_R and CORE_Z0 <= z <= CORE_Z1
    if near_lateral and (near_bottom or near_top):
        region = "edge_corner"
    elif near_bottom:
        region = "bottom_cap_zone"
    elif near_top:
        region = "top_cap_zone"
    elif near_lateral:
        region = "lateral_surface"
    elif in_core:
        region = "measurement_core"
    elif near_bottom or near_top:
        region = "interior_cap_ring"
    else:
        region = "interior_ring"
    dist_bottom = z
    dist_top = HEIGHT - z
    dist_lateral = RADIUS - r
    dist_edge = min(math.hypot(dist_lateral, dist_bottom), math.hypot(dist_lateral, dist_top))
    platen = "bottom_fixed" if near_bottom else ("top_prescribed" if near_top else "none")
    return {
        "r": r,
        "r_over_R": r / RADIUS,
        "z_over_H": z / HEIGHT,
        "distance_to_bottom_platen": dist_bottom,
        "distance_to_top_platen": dist_top,
        "distance_to_lateral_boundary": dist_lateral,
        "distance_to_edge_corner": dist_edge,
        "near_bottom_platen": int(near_bottom),
        "near_top_platen": int(near_top),
        "near_lateral_surface": int(near_lateral),
        "in_measurement_core": int(in_core),
        "boundary_class": region,
        "nearest_platen_role": platen,
    }


def normalize_rows():
    out = []
    for stage, path in INPUTS:
        for row in read_csv(path):
            x = f(row, "x")
            y = f(row, "y")
            z = f(row, "z")
            b = boundary_class(x, y, z)
            status = int(round(f(row, "return_status")))
            case = s(row, "case")
            p = f(row, "p_proxy", "p_eff")
            q = f(row, "q_proxy", "q")
            pc = f(row, "pc", "MccPc")
            q_over_p = q / p if abs(p) > 1e-12 else math.nan
            out.append({
                "source_stage": stage,
                "case": case,
                "part": int(round(f(row, "part"))),
                "time": f(row, "time"),
                "idp": int(round(f(row, "idp", "Idp", default=-1))),
                "return_status": status,
                "original_region": s(row, "region"),
                "x": x,
                "y": y,
                "z": z,
                **b,
                "neighbor_count_available": 0,
                "neighbor_count": math.nan,
                "local_distribution_metric_available": 0,
                "local_distribution_metric": math.nan,
                "strain_increment_proxy_available": 0,
                "strain_increment_proxy": math.nan,
                "axial_velocity_gradient_proxy_available": 0,
                "axial_velocity_gradient_proxy": math.nan,
                "radial_velocity_gradient_proxy_available": 0,
                "radial_velocity_gradient_proxy": math.nan,
                "trial_state_available": int(round(f(row, "trial_state_available", default=0.0))),
                "trial_p": f(row, "trial_p", default=math.nan),
                "trial_q": f(row, "trial_q", default=math.nan),
                "p_eff": p,
                "q": q,
                "q_over_p": q_over_p,
                "pc": pc,
                "void_ratio": f(row, "void_ratio", "MccVoidRatio"),
                "plastic_vol_strain": f(row, "plastic_vol_strain", "MccPlasticVolStrain"),
                "eq_plastic_strain": f(row, "eq_plastic_strain", "MccEqPlasticStrain"),
                "plastic_multiplier": f(row, "plastic_multiplier", "MccPlasticMultiplier"),
                "return_iterations": f(row, "return_iterations", "MccReturnIterations"),
                "yield_residual": f(row, "yield_residual", "MccYieldResidual"),
                "substep_count": f(row, "substep_count", "MccSubstepCount"),
                "line_search_backtracks": f(row, "line_search_backtracks", "MccLineSearchBacktrackCount"),
                "line_search_reject_reason": f(row, "line_search_reject_reason", "MccLineSearchRejectReason"),
                "Kplastic": f(row, "Kplastic"),
                "PorePress": f(row, "PorePress"),
                "PorePressRate": f(row, "PorePressRate"),
                "DivVel": f(row, "DivVel"),
                "velocity": f(row, "velocity"),
                "pairwise_reaction_avg": f(row, "pairwise_reaction_avg", default=math.nan),
            })
    return out


def mean(vals):
    vals = [v for v in vals if isinstance(v, (int, float)) and math.isfinite(v)]
    return sum(vals) / len(vals) if vals else math.nan


def maxabs(vals):
    vals = [abs(v) for v in vals if isinstance(v, (int, float)) and math.isfinite(v)]
    return max(vals) if vals else math.nan


def group_summary(rows, keys):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in keys)].append(row)
    out = []
    for key, vals in sorted(groups.items()):
        rec = {k: v for k, v in zip(keys, key)}
        statuses = Counter(v["return_status"] for v in vals)
        rec.update({
            "count": len(vals),
            "status_-3": statuses[-3],
            "status_-1": statuses[-1],
            "status_-5": statuses[-5],
            "mean_r_over_R": mean(v["r_over_R"] for v in vals),
            "mean_z_over_H": mean(v["z_over_H"] for v in vals),
            "mean_distance_to_bottom": mean(v["distance_to_bottom_platen"] for v in vals),
            "mean_distance_to_lateral": mean(v["distance_to_lateral_boundary"] for v in vals),
            "mean_p_eff": mean(v["p_eff"] for v in vals),
            "mean_q": mean(v["q"] for v in vals),
            "mean_q_over_p": mean(v["q_over_p"] for v in vals),
            "mean_pc": mean(v["pc"] for v in vals),
            "mean_void_ratio": mean(v["void_ratio"] for v in vals),
            "mean_plastic_vol_strain": mean(v["plastic_vol_strain"] for v in vals),
            "mean_eq_plastic_strain": mean(v["eq_plastic_strain"] for v in vals),
            "max_return_iterations": max(v["return_iterations"] for v in vals),
            "max_abs_yield_residual": maxabs(v["yield_residual"] for v in vals),
            "max_abs_DivVel": maxabs(v["DivVel"] for v in vals),
            "max_velocity": max(v["velocity"] for v in vals),
            "max_abs_PorePressRate": maxabs(v["PorePressRate"] for v in vals),
            "mean_pairwise_reaction_avg": mean(v["pairwise_reaction_avg"] for v in vals),
            "neighbor_count_available": 0,
        })
        out.append(rec)
    return out


def reaction_timeline(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["source_stage"], row["case"], row["time"])].append(row)
    out = []
    for (stage, case, time), vals in sorted(groups.items()):
        statuses = Counter(v["return_status"] for v in vals)
        out.append({
            "source_stage": stage,
            "case": case,
            "time": time,
            "failed_count": len(vals),
            "status_-3": statuses[-3],
            "status_-1": statuses[-1],
            "status_-5": statuses[-5],
            "bottom_zone_count": sum(1 for v in vals if v["near_bottom_platen"]),
            "edge_count": sum(1 for v in vals if v["near_lateral_surface"]),
            "mean_pairwise_reaction_avg": mean(v["pairwise_reaction_avg"] for v in vals),
            "max_abs_DivVel": maxabs(v["DivVel"] for v in vals),
            "max_velocity": max(v["velocity"] for v in vals),
            "max_abs_PorePressRate": maxabs(v["PorePressRate"] for v in vals),
        })
    return out


def plot_maps(rows):
    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    colors = {"M3d2": "tab:blue", "M3f": "tab:orange", "M3h": "tab:green"}
    for stage, color in colors.items():
        pts = [r for r in rows if r["source_stage"] == stage and r["return_status"] in (-3, -1, -5)]
        if not pts:
            continue
        ax.scatter([r["r_over_R"] for r in pts], [r["z_over_H"] for r in pts], s=9, alpha=0.35, label=stage, c=color)
    ax.axhline(CAP_Z / HEIGHT, color="0.4", lw=0.8, ls="--")
    ax.axhline((HEIGHT - CAP_Z) / HEIGHT, color="0.4", lw=0.8, ls="--")
    ax.axvline(EDGE_R / RADIUS, color="0.4", lw=0.8, ls="--")
    ax.set_xlabel("r/R")
    ax.set_ylabel("z/H")
    ax.set_title("Failed MCC returns by normalized boundary location")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "m3j_failed_particle_maps.svg")
    fig.savefig(ROOT / "m3j_failed_particle_maps.png", dpi=180)
    fig.savefig(FIGDIR / "m3j_failed_particle_maps.svg")
    fig.savefig(FIGDIR / "m3j_failed_particle_maps.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    pts = [r for r in rows if r["return_status"] == -3]
    ax.scatter([r["x"] for r in pts], [r["z"] for r in pts], s=10, alpha=0.4, c=[r["r_over_R"] for r in pts], cmap="viridis")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("z [m]")
    ax.set_title("Line-search failures (-3): x-z projection")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGDIR / "m3j_failed_minus3_xz.svg")
    fig.savefig(FIGDIR / "m3j_failed_minus3_xz.png", dpi=180)
    plt.close(fig)


def main():
    rows = normalize_rows()
    write_csv(ROOT / "m3j_failed_particle_boundary_locations.csv", rows)
    write_csv(ROOT / "m3j_failed_region_summary.csv", group_summary(rows, ["source_stage", "case", "return_status", "boundary_class"]))
    write_csv(ROOT / "m3j_local_strain_path_comparison.csv", group_summary(rows, ["source_stage", "case", "return_status"]))
    write_csv(ROOT / "m3j_platen_interaction_failure_timeline.csv", reaction_timeline(rows))
    write_csv(ROOT / "m3j_boundary_audit_summary.csv", group_summary(rows, ["source_stage", "boundary_class"]))
    write_csv(ROOT / "m3j_unavailable_diagnostics.csv", [{
        "diagnostic": "neighbor_count",
        "available": 0,
        "reason": "retained M3d2/M3f/M3h outputs contain failed-particle CSV only; full PartCsv neighbor clouds were cleaned",
    }, {
        "diagnostic": "local_particle_distribution_metric",
        "available": 0,
        "reason": "requires full particle cloud or a dense very-short diagnostic run",
    }, {
        "diagnostic": "trial_p_trial_q_trial_yield_function",
        "available": 0,
        "reason": "M3h persisted aggregate line-search diagnostics but not per-Newton trial-state traces",
    }, {
        "diagnostic": "nearby_nonfailed_particle_comparison",
        "available": 0,
        "reason": "requires full PartCsv at failed frames; current audit avoids new simulation",
    }])
    plot_maps(rows)


if __name__ == "__main__":
    main()
