#!/usr/bin/env python3
"""Compare M3l platen/specimen smoothing variants."""

from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

CASES = [
    ("CaseM3l_BaselineDense", "baseline", "M3k-equivalent dense reference"),
    ("CaseM3l_Gap2Dp", "gap_2dp", "generated platen/specimen center gap increased from 1Dp to 2Dp"),
    ("CaseM3l_PlatenOverhang", "platen_overhang", "platen radius increased to 0.04 m"),
    ("CaseM3l_EdgeSelectorBuffer", "edge_selector_buffer", "cap/edge lateral selector exclusion set to 0.025 m"),
]

RADIUS = 0.03
HEIGHT = 0.10
H = 0.018
SUPPORT = 2.0 * H
EDGE_R = 0.020
CAP_Z = 0.015
CORE_R = 0.010
CORE_Z0 = 0.025
CORE_Z1 = 0.075
PLATEN_AREA = math.pi * RADIUS * RADIUS


def safe_mean(vals):
    vals = [float(v) for v in vals if v is not None and math.isfinite(float(v))]
    return sum(vals) / len(vals) if vals else math.nan


def safe_std(vals):
    vals = [float(v) for v in vals if v is not None and math.isfinite(float(v))]
    if len(vals) < 2:
        return 0.0 if vals else math.nan
    mu = safe_mean(vals)
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))


def write_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def part_index(path: Path) -> int:
    return int(path.stem.split("_")[-1])


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
                        row[key] = math.nan
            rows.append(row)
        return rows


def parse_times(out: Path):
    times = {0: 0.0}
    rx = re.compile(r"Part_(\d+)\s+([0-9]+\.[0-9Ee+\-.]*)")
    run = out / "Run.out"
    if not run.exists():
        return times
    for line in run.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if m:
            times[int(m.group(1))] = float(m.group(2))
    return times


def parse_run_status(out: Path):
    text = (out / "Run.out").read_text(errors="ignore")
    def grab(rx, default=-1):
        m = re.search(rx, text)
        return int(m.group(1)) if m else default
    return {
        "code": 0 if "Finished execution (code=0)" in text else -1,
        "excluded": grab(r"Excluded particles\.+:\s+(\d+)"),
        "dtmin_adjustments": grab(r"DTs adjusted to DtMin\.+:\s+(\d+)"),
        "steps": grab(r"Steps of simulation\.+:\s+(\d+)"),
        "part_files": grab(r"PART files\.+:\s+(\d+)"),
    }


def parse_reactions(out: Path):
    rx = re.compile(
        r"PlatenReaction diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[0-9Ee+\-.]+).*?"
        r"top_force=\((?P<tfx>[0-9Ee+\-.]+),(?P<tfy>[0-9Ee+\-.]+),(?P<tfz>[0-9Ee+\-.]+)\).*?"
        r"bottom_force=\((?P<bfx>[0-9Ee+\-.]+),(?P<bfy>[0-9Ee+\-.]+),(?P<bfz>[0-9Ee+\-.]+)\).*?"
        r"force_balance_error=(?P<balance>[0-9Ee+\-.]+)"
    )
    run = out / "Run.out"
    rows = []
    if not run.exists():
        return rows
    for line in run.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if not m:
            continue
        vals = {k: float(v.rstrip(".")) for k, v in m.groupdict().items() if k != "step"}
        rows.append({"step": int(m.group("step")), **vals})
    return rows


def nearest_reaction(time, rows):
    if not rows:
        return None
    return min(rows, key=lambda r: abs(r["time"] - time))


def pos(row):
    return np.array([row["Pos.x [m]"], row["Pos.y [m]"], row["Pos.z [m]"]], dtype=float)


def vel(row):
    return np.array([row["Vel.x [m/s]"], row["Vel.y [m/s]"], row["Vel.z [m/s]"]], dtype=float)


def specimen(row) -> bool:
    return int(row.get("Type", -1)) == 3


def stress_invariants(row):
    sx = row.get("Sigma_kk.x", 0.0)
    sy = row.get("Sigma_kk.y", 0.0)
    sz = row.get("Sigma_kk.z", 0.0)
    sxy = row.get("Sigma_ij.x", 0.0)
    syz = row.get("Sigma_ij.y", 0.0)
    sxz = row.get("Sigma_ij.z", 0.0)
    p = -(sx + sy + sz) / 3.0
    mean = (sx + sy + sz) / 3.0
    dxx, dyy, dzz = sx - mean, sy - mean, sz - mean
    j2 = 0.5 * (dxx * dxx + dyy * dyy + dzz * dzz + 2.0 * (sxy * sxy + syz * syz + sxz * sxz))
    q = math.sqrt(max(0.0, 3.0 * j2))
    return p, q


def region_from_xyz(x, y, z):
    r = math.hypot(x, y)
    near_bottom = z <= CAP_Z
    near_top = z >= HEIGHT - CAP_Z
    near_lateral = r >= EDGE_R
    in_core = r <= CORE_R and CORE_Z0 <= z <= CORE_Z1
    if near_lateral and (near_bottom or near_top):
        region = "edge_ring"
    elif near_bottom:
        region = "bottom_cap_zone"
    elif near_top:
        region = "top_cap_zone"
    elif near_lateral:
        region = "lateral_surface"
    elif in_core:
        region = "measurement_core"
    else:
        region = "interior"
    return region, r


def wendland_weight(dist):
    q = dist / H
    if q >= 2.0:
        return 0.0
    return (1.0 - 0.5 * q) ** 4 * (2.0 * q + 1.0)


def local_gradient(i, spec_positions, spec_velocities, neighbour_idx):
    if len(neighbour_idx) < 4:
        return {}
    dx = spec_positions[neighbour_idx] - spec_positions[i]
    dv = spec_velocities[neighbour_idx] - spec_velocities[i]
    try:
        grad, *_ = np.linalg.lstsq(dx, dv, rcond=None)
    except np.linalg.LinAlgError:
        return {}
    g = grad.T
    sym = 0.5 * (g + g.T)
    shear = math.sqrt(max(0.0, 2.0 * float(np.sum(sym * sym))))
    return {
        "axial_strain_rate_proxy": g[2, 2],
        "radial_strain_rate_proxy": 0.5 * (g[0, 0] + g[1, 1]),
        "shear_rate_proxy": shear,
        "velocity_gradient_norm": float(np.linalg.norm(g)),
    }


def build_frame_metrics(case, label, part, time, rows, reaction):
    all_positions = np.array([pos(r) for r in rows])
    spec_rows = [r for r in rows if specimen(r)]
    spec_positions = np.array([pos(r) for r in spec_rows])
    spec_velocities = np.array([vel(r) for r in spec_rows])
    core_support = []
    cache = []
    for i, row in enumerate(spec_rows):
        pi = spec_positions[i]
        dall = np.linalg.norm(all_positions - pi, axis=1)
        dspec = np.linalg.norm(spec_positions - pi, axis=1)
        all_mask = (dall > 1e-12) & (dall <= SUPPORT)
        spec_mask = (dspec > 1e-12) & (dspec <= SUPPORT)
        spec_idx = np.where(spec_mask)[0]
        wsum = float(sum(wendland_weight(float(d)) for d in dall[all_mask]))
        reg, _ = region_from_xyz(*map(float, pi))
        if reg == "measurement_core":
            core_support.append(wsum)
        cache.append({
            "all_count": int(np.count_nonzero(all_mask)),
            "spec_count": int(np.count_nonzero(spec_mask)),
            "nearest": float(np.min(dspec[dspec > 1e-12])) if np.any(dspec > 1e-12) else math.nan,
            "weight": wsum,
            "spec_idx": spec_idx,
        })
    core_support_mean = safe_mean(core_support)

    out = []
    pairwise = math.nan
    balance = math.nan
    if reaction:
        pairwise = 0.5 * (reaction["tfz"] + abs(reaction["bfz"]))
        balance = reaction["balance"]
    for i, row in enumerate(spec_rows):
        x, y, z = map(float, spec_positions[i])
        reg, r = region_from_xyz(x, y, z)
        p, q = stress_invariants(row)
        status = int(round(row.get("MccReturnStatus", 0.0)))
        grad = local_gradient(i, spec_positions, spec_velocities, cache[i]["spec_idx"])
        support_ratio = cache[i]["weight"] / core_support_mean if core_support_mean and math.isfinite(core_support_mean) else math.nan
        rec = {
            "case": case,
            "variant": label,
            "part": part,
            "time": time,
            "idp": int(row.get("Idp", -1)),
            "return_status": status,
            "failed": int(status < 0),
            "x": x,
            "y": y,
            "z": z,
            "r": r,
            "r_over_R": r / RADIUS,
            "z_over_H": z / HEIGHT,
            "distance_to_top_platen": HEIGHT - z,
            "distance_to_bottom_platen": z,
            "distance_to_lateral_boundary": RADIUS - r,
            "distance_to_edge_corner": min(math.hypot(RADIUS - r, z), math.hypot(RADIUS - r, HEIGHT - z)),
            "region": reg,
            "neighbor_count_all": cache[i]["all_count"],
            "neighbor_count_specimen": cache[i]["spec_count"],
            "nearest_neighbor_distance": cache[i]["nearest"],
            "kernel_support_sum": cache[i]["weight"],
            "kernel_support_ratio_to_core": support_ratio,
            "velocity": float(np.linalg.norm(spec_velocities[i])),
            "DivVel": row.get("DivVel", 0.0),
            "PorePressRate": row.get("PorePressRate", 0.0),
            "PorePress": row.get("PorePress", 0.0),
            "sigma_zz": row.get("Sigma_kk.z", 0.0),
            "p_eff": p,
            "q": q,
            "q_over_p": q / p if abs(p) > 1e-12 else math.nan,
            "pc": row.get("MccPc", 0.0),
            "void_ratio": row.get("MccVoidRatio", 0.0),
            "plastic_vol_strain": row.get("MccPlasticVolStrain", 0.0),
            "eq_plastic_strain": row.get("MccEqPlasticStrain", 0.0),
            "plastic_multiplier": row.get("MccPlasticMultiplier", 0.0),
            "return_iterations": row.get("MccReturnIterations", 0.0),
            "yield_residual": row.get("MccYieldResidual", 0.0),
            "Kplastic": row.get("Kplastic", 0.0),
            "pairwise_reaction_avg": pairwise,
            "axial_stress_reaction": pairwise / PLATEN_AREA if math.isfinite(pairwise) else math.nan,
            "force_balance_error": balance,
            "axial_strain_rate_proxy": grad.get("axial_strain_rate_proxy", math.nan),
            "radial_strain_rate_proxy": grad.get("radial_strain_rate_proxy", math.nan),
            "shear_rate_proxy": grad.get("shear_rate_proxy", math.nan),
            "velocity_gradient_norm": grad.get("velocity_gradient_norm", math.nan),
        }
        out.append(rec)
    return out


def status_counts(metrics):
    by = defaultdict(Counter)
    for r in metrics:
        by[r["time"]][r["return_status"]] += 1
    rows = []
    for time, c in sorted(by.items()):
        rows.append({
            "case": metrics[0]["case"],
            "variant": metrics[0]["variant"],
            "time": time,
            "status_-3": c[-3],
            "status_-1": c[-1],
            "status_0": c[0],
            "status_1": c[1],
            "negative_count": sum(v for k, v in c.items() if k < 0),
        })
    return rows


def summarize(metrics, keys):
    groups = defaultdict(list)
    for row in metrics:
        groups[tuple(row[k] for k in keys)].append(row)
    out = []
    for key, vals in sorted(groups.items()):
        c = Counter(v["return_status"] for v in vals)
        rec = {k: v for k, v in zip(keys, key)}
        rec.update({
            "count": len(vals),
            "failed_count": sum(v["failed"] for v in vals),
            "status_-3": c[-3],
            "status_-1": c[-1],
            "neighbor_count_all_mean": safe_mean(v["neighbor_count_all"] for v in vals),
            "neighbor_count_specimen_mean": safe_mean(v["neighbor_count_specimen"] for v in vals),
            "support_ratio_mean": safe_mean(v["kernel_support_ratio_to_core"] for v in vals),
            "velocity_gradient_norm_mean": safe_mean(v["velocity_gradient_norm"] for v in vals),
            "shear_rate_mean": safe_mean(v["shear_rate_proxy"] for v in vals),
            "DivVel_mean": safe_mean(v["DivVel"] for v in vals),
            "PorePressRate_maxAbs": max(abs(v["PorePressRate"]) for v in vals),
            "p_eff_mean": safe_mean(v["p_eff"] for v in vals),
            "q_mean": safe_mean(v["q"] for v in vals),
            "q_over_p_mean": safe_mean(v["q_over_p"] for v in vals),
            "yield_residual_maxAbs": max(abs(v["yield_residual"]) for v in vals),
            "pc_mean": safe_mean(v["pc"] for v in vals),
            "void_ratio_mean": safe_mean(v["void_ratio"] for v in vals),
            "plastic_vol_strain_mean": safe_mean(v["plastic_vol_strain"] for v in vals),
            "pairwise_reaction_avg": safe_mean(v["pairwise_reaction_avg"] for v in vals),
            "sigma_zz_mean": safe_mean(v["sigma_zz"] for v in vals),
            "Fz_proxy": -safe_mean(v["sigma_zz"] for v in vals) * PLATEN_AREA,
            "PorePress_mean": safe_mean(v["PorePress"] for v in vals),
            "PorePress_std": safe_std(v["PorePress"] for v in vals),
            "velocity_max": max(v["velocity"] for v in vals),
        })
        out.append(rec)
    return out


def read_case(case, label):
    out = ROOT / f"{case}_out"
    times = parse_times(out)
    reactions = parse_reactions(out)
    metrics = []
    for path in sorted((out / "data").glob("PartCsv_*.csv"), key=part_index):
        part = part_index(path)
        time = times.get(part, float(part))
        metrics.extend(build_frame_metrics(case, label, part, time, read_rows(path), nearest_reaction(time, reactions)))
    return metrics, parse_run_status(out)


def plot_status(status_rows):
    for key, name, ylabel in [
        ("status_-3", "m3l_return_status_minus3_vs_time", "ReturnStatus=-3 count"),
        ("status_-1", "m3l_return_status_minus1_vs_time", "ReturnStatus=-1 count"),
        ("negative_count", "m3l_negative_status_vs_time", "negative return count"),
    ]:
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        for _, label, _ in CASES:
            rows = [r for r in status_rows if r["variant"] == label]
            ax.plot([r["time"] for r in rows], [r[key] for r in rows], label=label)
        ax.set_xlabel("time [s]")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(FIGDIR / f"{name}.svg")
        fig.savefig(FIGDIR / f"{name}.png", dpi=180)
        plt.close(fig)


def plot_metric(summary_rows, key, name, ylabel):
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for failed, marker in [(0, "o"), (1, "s")]:
        rows = [r for r in summary_rows if int(r["failed"]) == failed]
        labels = [r["variant"] for r in rows]
        vals = [r[key] for r in rows]
        ax.scatter(labels, vals, marker=marker, label="failed" if failed else "nonfailed")
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", alpha=0.3)
    ax.tick_params(axis="x", rotation=20)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGDIR / f"{name}.svg")
    fig.savefig(FIGDIR / f"{name}.png", dpi=180)
    plt.close(fig)


def plot_failed_locations(metrics):
    fig, axes = plt.subplots(2, 2, figsize=(8.2, 7.2), sharex=True, sharey=True)
    for ax, (_, label, _) in zip(axes.ravel(), CASES):
        rows = [r for r in metrics if r["variant"] == label]
        nf = [r for r in rows if not r["failed"] and r["time"] == 0.0]
        ff = [r for r in rows if r["failed"]]
        ax.scatter([r["r_over_R"] for r in nf], [r["z_over_H"] for r in nf], s=3, c="0.75", alpha=0.2)
        ax.scatter([r["r_over_R"] for r in ff], [r["z_over_H"] for r in ff], s=7, c="tab:red", alpha=0.45)
        ax.axhline(CAP_Z / HEIGHT, color="0.4", lw=0.8, ls="--")
        ax.axhline((HEIGHT - CAP_Z) / HEIGHT, color="0.4", lw=0.8, ls="--")
        ax.axvline(EDGE_R / RADIUS, color="0.4", lw=0.8, ls="--")
        ax.set_title(label)
        ax.grid(True, alpha=0.25)
    for ax in axes[:, 0]:
        ax.set_ylabel("z/H")
    for ax in axes[-1, :]:
        ax.set_xlabel("r/R")
    fig.tight_layout()
    fig.savefig(FIGDIR / "m3l_failed_particle_locations.png", dpi=180)
    fig.savefig(FIGDIR / "m3l_failed_particle_locations.svg")
    plt.close(fig)


def plot_path(time_rows, xkey, ykey, name, xlabel, ylabel):
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    for _, label, _ in CASES:
        rows = [r for r in time_rows if r["variant"] == label]
        ax.plot([r[xkey] for r in rows], [r[ykey] for r in rows], label=label)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGDIR / f"{name}.svg")
    fig.savefig(FIGDIR / f"{name}.png", dpi=180)
    plt.close(fig)


def main():
    all_metrics = []
    status_rows = []
    case_summary = []
    geometry_rows = []
    for case, label, desc in CASES:
        metrics, run = read_case(case, label)
        all_metrics.extend(metrics)
        sr = status_counts(metrics)
        status_rows.extend(sr)
        first = next((r for r in sr if r["negative_count"] > 0), None)
        final = sr[-1]
        case_summary.append({
            "case": case,
            "variant": label,
            "description": desc,
            **run,
            "first_failure_time": first["time"] if first else math.nan,
            "first_failure_negative_count": first["negative_count"] if first else 0,
            "first_failure_status_-3": first["status_-3"] if first else 0,
            "first_failure_status_-1": first["status_-1"] if first else 0,
            "max_status_-3": max(r["status_-3"] for r in sr),
            "max_status_-1": max(r["status_-1"] for r in sr),
            "bad_frame_count": sum(1 for r in sr if r["negative_count"] > 0),
            "final_time": final["time"],
            "final_status_-3": final["status_-3"],
            "final_status_-1": final["status_-1"],
            "final_negative_count": final["negative_count"],
        })
        geometry_rows.append({
            "case": case,
            "variant": label,
            "description": desc,
            "platen_gap": "2Dp generated center gap" if label == "gap_2dp" else "1Dp generated center gap",
            "platen_radius": 0.04 if label == "platen_overhang" else 0.03,
            "cap_exclusion_length": 0.025 if label == "edge_selector_buffer" else 0.015,
            "edge_exclusion_length": 0.025 if label == "edge_selector_buffer" else 0.015,
        })

    failed = [r for r in all_metrics if r["failed"]]
    local_summary = summarize(all_metrics, ["variant", "failed"])
    region_summary = summarize(all_metrics, ["variant", "region", "return_status"])
    time_summary = summarize(all_metrics, ["variant", "time"])
    failed_region_summary = summarize(all_metrics, ["variant", "failed", "region"])

    write_csv(ROOT / "m3l_case_summary.csv", case_summary)
    write_csv(ROOT / "m3l_return_status_comparison.csv", status_rows)
    write_csv(ROOT / "m3l_failed_particle_locations.csv", failed)
    write_csv(ROOT / "m3l_support_neighbor_comparison.csv", local_summary)
    write_csv(ROOT / "m3l_velocity_gradient_comparison.csv", local_summary)
    write_csv(ROOT / "m3l_stress_path_local_comparison.csv", failed_region_summary)
    write_csv(ROOT / "m3l_reaction_stress_path_comparison.csv", time_summary)
    write_csv(ROOT / "m3l_pore_pressure_comparison.csv", time_summary)
    write_csv(ROOT / "m3l_region_failure_statistics.csv", region_summary)
    write_csv(ROOT / "m3l_geometry_change_summary.csv", geometry_rows)

    plot_status(status_rows)
    plot_failed_locations(all_metrics)
    plot_metric(local_summary, "support_ratio_mean", "m3l_support_proxy_distribution", "support ratio to core")
    plot_metric(local_summary, "neighbor_count_specimen_mean", "m3l_neighbor_count_proxy", "specimen neighbor proxy")
    plot_metric(local_summary, "velocity_gradient_norm_mean", "m3l_velocity_gradient_proxy", "velocity-gradient proxy")
    plot_metric(local_summary, "q_over_p_mean", "m3l_failed_vs_nonfailed_q_over_p", "q/p' proxy")
    plot_path(time_summary, "p_eff_mean", "q_mean", "m3l_global_pq_path", "p' proxy [Pa]", "q proxy [Pa]")
    plot_path(time_summary, "time", "pairwise_reaction_avg", "m3l_pairwise_reaction_vs_time", "time [s]", "pairwise reaction avg [N]")
    plot_path(time_summary, "time", "PorePress_mean", "m3l_pore_pressure_vs_time", "time [s]", "PorePress mean [Pa]")


if __name__ == "__main__":
    main()
