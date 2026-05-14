#!/usr/bin/env python3
"""Postprocess M3m refined platen/edge geometry diagnostics."""

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
    ("CaseM3m_OverhangReference", "overhang_ref", "M3l platen overhang reference"),
    ("CaseM3m_Overhang045", "overhang045", "platen radius increased to 0.045 m"),
    ("CaseM3m_TrimmedEdge", "trimmed_edge", "overhang plus trimmed cap edge"),
    ("CaseM3m_SteppedCap", "stepped_cap", "overhang plus stepped cap transition"),
    ("CaseM3m_Overhang045Extended", "overhang045_extended", "short extended check for 0.045 m overhang"),
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


def safe_vals(vals):
    out = []
    for val in vals:
        try:
            f = float(val)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f):
            out.append(f)
    return out


def safe_mean(vals):
    vals = safe_vals(vals)
    return sum(vals) / len(vals) if vals else math.nan


def safe_max_abs(vals):
    vals = safe_vals(vals)
    return max((abs(v) for v in vals), default=math.nan)


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
    rows = []
    run = out / "Run.out"
    if not run.exists():
        return rows
    for line in run.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if not m:
            continue
        vals = {k: float(v.rstrip(".")) for k, v in m.groupdict().items() if k != "step"}
        rows.append({"step": int(m.group("step")), **vals})
    return rows


def parse_confinement(out: Path):
    rx = re.compile(
        r"FlexibleConfiningStress extended diagnostics: step=(?P<step>\d+).*?"
        r"lateral_fi_selected=(?P<lateral>\d+).*?cap_fi_selected=(?P<cap>\d+).*?"
        r"cap_abs_axial_accel_max=(?P<capacc>[0-9Ee+\-.]+)"
    )
    rows = []
    run = out / "Run.out"
    if not run.exists():
        return rows
    for line in run.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if m:
            rows.append({
                "step": int(m.group("step")),
                "time": 0.0,
                "lateral_active_targets": int(m.group("lateral")),
                "cap_fi_selected": int(m.group("cap")),
                "cap_leakage_proxy": float(m.group("capacc").rstrip(".")),
            })
    return rows


def nearest(time, rows):
    if not rows:
        return None
    return min(rows, key=lambda r: abs(r["time"] - time))


def pos(row):
    return np.array([row["Pos.x [m]"], row["Pos.y [m]"], row["Pos.z [m]"]], dtype=float)


def vel(row):
    return np.array([row["Vel.x [m/s]"], row["Vel.y [m/s]"], row["Vel.z [m/s]"]], dtype=float)


def is_specimen(row) -> bool:
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


def local_gradient(i, spec_positions, spec_velocities, neigh_idx):
    if len(neigh_idx) < 4:
        return {}
    dx = spec_positions[neigh_idx] - spec_positions[i]
    dv = spec_velocities[neigh_idx] - spec_velocities[i]
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


def frame_metrics(case, variant, part, time, rows, reaction, confinement):
    all_positions = np.array([pos(r) for r in rows])
    spec_rows = [r for r in rows if is_specimen(r)]
    spec_positions = np.array([pos(r) for r in spec_rows])
    spec_velocities = np.array([vel(r) for r in spec_rows])
    cache = []
    core_support = []
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

    pairwise = math.nan
    balance = math.nan
    if reaction:
        pairwise = 0.5 * (reaction["tfz"] + abs(reaction["bfz"]))
        balance = reaction["balance"]
    lateral = confinement["lateral_active_targets"] if confinement else math.nan
    cap_leak = confinement["cap_leakage_proxy"] if confinement else math.nan

    metrics = []
    for i, row in enumerate(spec_rows):
        x, y, z = map(float, spec_positions[i])
        reg, r = region_from_xyz(x, y, z)
        p, q = stress_invariants(row)
        status = int(round(row.get("MccReturnStatus", 0.0)))
        grad = local_gradient(i, spec_positions, spec_velocities, cache[i]["spec_idx"])
        support_ratio = cache[i]["weight"] / core_support_mean if core_support_mean and math.isfinite(core_support_mean) else math.nan
        metrics.append({
            "case": case,
            "variant": variant,
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
            "region": reg,
            "distance_to_top_platen": HEIGHT - z,
            "distance_to_bottom_platen": z,
            "distance_to_lateral_boundary": RADIUS - r,
            "distance_to_edge_corner": min(math.hypot(RADIUS - r, z), math.hypot(RADIUS - r, HEIGHT - z)),
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
            "lateral_active_targets": lateral,
            "cap_leakage_proxy": cap_leak,
            "axial_strain_rate_proxy": grad.get("axial_strain_rate_proxy", math.nan),
            "radial_strain_rate_proxy": grad.get("radial_strain_rate_proxy", math.nan),
            "shear_rate_proxy": grad.get("shear_rate_proxy", math.nan),
            "velocity_gradient_norm": grad.get("velocity_gradient_norm", math.nan),
        })
    return metrics


def status_rows(metrics):
    by = defaultdict(Counter)
    for row in metrics:
        by[row["time"]][row["return_status"]] += 1
    out = []
    for time, c in sorted(by.items()):
        out.append({
            "case": metrics[0]["case"],
            "variant": metrics[0]["variant"],
            "time": time,
            "status_-3": c[-3],
            "status_-1": c[-1],
            "status_0": c[0],
            "status_1": c[1],
            "negative_count": sum(v for k, v in c.items() if k < 0),
        })
    return out


def summarize(metrics, keys):
    groups = defaultdict(list)
    for row in metrics:
        groups[tuple(row[k] for k in keys)].append(row)
    out = []
    for key, vals in sorted(groups.items()):
        cnt = Counter(v["return_status"] for v in vals)
        rec = {k: v for k, v in zip(keys, key)}
        rec.update({
            "count": len(vals),
            "failed_count": sum(v["failed"] for v in vals),
            "status_-3": cnt[-3],
            "status_-1": cnt[-1],
            "neighbor_count_all_mean": safe_mean(v["neighbor_count_all"] for v in vals),
            "neighbor_count_specimen_mean": safe_mean(v["neighbor_count_specimen"] for v in vals),
            "support_ratio_mean": safe_mean(v["kernel_support_ratio_to_core"] for v in vals),
            "velocity_gradient_norm_mean": safe_mean(v["velocity_gradient_norm"] for v in vals),
            "shear_rate_mean": safe_mean(v["shear_rate_proxy"] for v in vals),
            "p_eff_mean": safe_mean(v["p_eff"] for v in vals),
            "q_mean": safe_mean(v["q"] for v in vals),
            "q_over_p_mean": safe_mean(v["q_over_p"] for v in vals),
            "yield_residual_maxAbs": safe_max_abs(v["yield_residual"] for v in vals),
            "pc_mean": safe_mean(v["pc"] for v in vals),
            "void_ratio_mean": safe_mean(v["void_ratio"] for v in vals),
            "plastic_vol_strain_mean": safe_mean(v["plastic_vol_strain"] for v in vals),
            "eq_plastic_strain_mean": safe_mean(v["eq_plastic_strain"] for v in vals),
            "pairwise_reaction_avg": safe_mean(v["pairwise_reaction_avg"] for v in vals),
            "force_balance_error_mean": safe_mean(v["force_balance_error"] for v in vals),
            "sigma_zz_mean": safe_mean(v["sigma_zz"] for v in vals),
            "Fz_proxy": -safe_mean(v["sigma_zz"] for v in vals) * PLATEN_AREA,
            "PorePress_mean": safe_mean(v["PorePress"] for v in vals),
            "PorePressRate_maxAbs": safe_max_abs(v["PorePressRate"] for v in vals),
            "velocity_max": max(safe_vals(v["velocity"] for v in vals), default=math.nan),
            "lateral_active_targets": safe_mean(v["lateral_active_targets"] for v in vals),
            "cap_leakage_proxy_max": safe_max_abs(v["cap_leakage_proxy"] for v in vals),
        })
        out.append(rec)
    return out


def read_case(case, variant):
    out = ROOT / f"{case}_out"
    times = parse_times(out)
    reactions = parse_reactions(out)
    confinements = parse_confinement(out)
    metrics = []
    data = out / "data"
    for path in sorted(data.glob("PartCsv_*.csv"), key=part_index):
        part = part_index(path)
        time = times.get(part, float(part))
        metrics.extend(frame_metrics(case, variant, part, time, read_rows(path), nearest(time, reactions), nearest(time, confinements)))
    return metrics, parse_run_status(out)


def plot_status(rows, key, name, ylabel):
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for _, variant, _ in CASES:
        vals = [r for r in rows if r["variant"] == variant]
        ax.plot([r["time"] for r in vals], [r[key] for r in vals], label=variant)
    ax.set_xlabel("time [s]")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGDIR / f"{name}.svg")
    fig.savefig(FIGDIR / f"{name}.png", dpi=180)
    plt.close(fig)


def plot_group(summary, key, name, ylabel):
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for failed, marker in [(0, "o"), (1, "s")]:
        vals = [r for r in summary if int(r["failed"]) == failed]
        ax.scatter([r["variant"] for r in vals], [r[key] for r in vals], marker=marker, label="failed" if failed else "nonfailed")
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", alpha=0.3)
    ax.tick_params(axis="x", rotation=20)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGDIR / f"{name}.svg")
    fig.savefig(FIGDIR / f"{name}.png", dpi=180)
    plt.close(fig)


def plot_path(time_rows, xkey, ykey, name, xlabel, ylabel):
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    for _, variant, _ in CASES:
        rows = [r for r in time_rows if r["variant"] == variant]
        ax.plot([r[xkey] for r in rows], [r[ykey] for r in rows], label=variant)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGDIR / f"{name}.svg")
    fig.savefig(FIGDIR / f"{name}.png", dpi=180)
    plt.close(fig)


def plot_failed_locations(metrics, xkey, name, xlabel):
    fig, axes = plt.subplots(3, 2, figsize=(8.2, 9.5), sharey=True)
    for ax, (_, variant, _) in zip(axes.ravel(), CASES):
        rows = [r for r in metrics if r["variant"] == variant]
        first_rows = [r for r in rows if r["time"] == 0.0]
        failed = [r for r in rows if r["failed"]]
        ax.scatter([r[xkey] for r in first_rows], [r["z_over_H"] for r in first_rows], s=3, c="0.75", alpha=0.2)
        ax.scatter([r[xkey] for r in failed], [r["z_over_H"] for r in failed], s=7, c="tab:red", alpha=0.45)
        ax.axhline(CAP_Z / HEIGHT, color="0.4", lw=0.8, ls="--")
        ax.axhline((HEIGHT - CAP_Z) / HEIGHT, color="0.4", lw=0.8, ls="--")
        ax.set_title(variant)
        ax.grid(True, alpha=0.25)
    for ax in axes.ravel()[len(CASES):]:
        ax.axis("off")
    for ax in axes[:, 0]:
        ax.set_ylabel("z/H")
    for ax in axes[-1, :]:
        ax.set_xlabel(xlabel)
    fig.tight_layout()
    fig.savefig(FIGDIR / f"{name}.svg")
    fig.savefig(FIGDIR / f"{name}.png", dpi=180)
    plt.close(fig)


def main():
    all_metrics = []
    all_status = []
    case_summary = []
    geometry = []
    initial_sets = {}
    for case, variant, desc in CASES:
        metrics, run = read_case(case, variant)
        all_metrics.extend(metrics)
        initial_sets[variant] = {
            (round(r["x"], 5), round(r["y"], 5), round(r["z"], 5))
            for r in metrics
            if r["time"] == 0.0
        }
        rows = status_rows(metrics)
        all_status.extend(rows)
        first = next((r for r in rows if r["negative_count"] > 0), None)
        final = rows[-1]
        case_summary.append({
            "case": case,
            "variant": variant,
            "description": desc,
            **run,
            "first_failure_time": first["time"] if first else math.nan,
            "first_failure_negative_count": first["negative_count"] if first else 0,
            "first_failure_status_-3": first["status_-3"] if first else 0,
            "first_failure_status_-1": first["status_-1"] if first else 0,
            "max_status_-3": max(r["status_-3"] for r in rows),
            "max_status_-1": max(r["status_-1"] for r in rows),
            "bad_frame_count": sum(1 for r in rows if r["negative_count"] > 0),
            "final_time": final["time"],
            "final_status_-3": final["status_-3"],
            "final_status_-1": final["status_-1"],
            "final_negative_count": final["negative_count"],
        })
        geometry.append({
            "case": case,
            "variant": variant,
            "description": desc,
            "platen_radius": 0.045 if variant in {"overhang045", "overhang045_extended"} else 0.04,
            "time_max": 0.004 if variant == "overhang045_extended" else 0.0025,
            "specimen_geometry": {
                "overhang_ref": "single R=0.03 cylinder",
                "overhang045": "single R=0.03 cylinder",
                "overhang045_extended": "single R=0.03 cylinder",
                "trimmed_edge": "cap R=0.025, core R=0.03",
                "stepped_cap": "cap R=0.025, transition R=0.028, core R=0.03",
            }[variant],
        })

    failed = [r for r in all_metrics if r["failed"]]
    local_summary = summarize(all_metrics, ["variant", "failed"])
    region_summary = summarize(all_metrics, ["variant", "failed", "region"])
    time_summary = summarize(all_metrics, ["variant", "time"])
    clean_rows = []
    for row in case_summary:
        clean_rows.append({
            "variant": row["variant"],
            "clean_candidate": int(row["code"] == 0 and row["excluded"] == 0 and row["dtmin_adjustments"] == 0 and row["max_status_-3"] == 0 and row["max_status_-1"] == 0),
            "code": row["code"],
            "excluded": row["excluded"],
            "dtmin_adjustments": row["dtmin_adjustments"],
            "max_status_-3": row["max_status_-3"],
            "max_status_-1": row["max_status_-1"],
            "bad_frame_count": row["bad_frame_count"],
        })
    base_set = initial_sets.get("overhang_ref", set())
    geometry_change = []
    for row in geometry:
        pts = initial_sets.get(row["variant"], set())
        cap_pts = [p for p in pts if p[2] <= CAP_Z or p[2] >= HEIGHT - CAP_Z]
        geometry_change.append({
            **row,
            "specimen_particle_count": len(pts),
            "cap_zone_particle_count": len(cap_pts),
            "actual_particle_set_added_vs_ref": len(pts - base_set),
            "actual_particle_set_removed_vs_ref": len(base_set - pts),
            "max_cap_radius": max((math.hypot(p[0], p[1]) for p in cap_pts), default=math.nan),
        })

    write_csv(ROOT / "m3m_case_summary.csv", case_summary)
    write_csv(ROOT / "m3m_geometry_variant_summary.csv", geometry)
    write_csv(ROOT / "m3m_geometry_change_summary.csv", geometry_change)
    write_csv(ROOT / "m3m_return_status_comparison.csv", all_status)
    write_csv(ROOT / "m3m_failed_particle_locations.csv", failed)
    write_csv(ROOT / "m3m_support_neighbor_comparison.csv", local_summary)
    write_csv(ROOT / "m3m_velocity_gradient_comparison.csv", local_summary)
    write_csv(ROOT / "m3m_stress_path_local_comparison.csv", region_summary)
    write_csv(ROOT / "m3m_reaction_stress_path_comparison.csv", time_summary)
    write_csv(ROOT / "m3m_pore_pressure_comparison.csv", time_summary)
    write_csv(ROOT / "m3m_clean_candidate_summary.csv", clean_rows)

    plot_status(all_status, "status_-3", "m3m_return_status_minus3_vs_time", "ReturnStatus=-3 count")
    plot_status(all_status, "status_-1", "m3m_return_status_minus1_vs_time", "ReturnStatus=-1 count")
    plot_status(all_status, "negative_count", "m3m_negative_return_status_vs_time", "negative return count")
    plot_failed_locations(all_metrics, "r_over_R", "m3m_failed_locations_rz", "r/R")
    plot_failed_locations(all_metrics, "x", "m3m_failed_locations_xz", "x [m]")
    plot_group(local_summary, "support_ratio_mean", "m3m_support_proxy_distribution", "support ratio to core")
    plot_group(local_summary, "neighbor_count_specimen_mean", "m3m_neighbor_count_proxy", "specimen neighbor proxy")
    plot_group(local_summary, "velocity_gradient_norm_mean", "m3m_velocity_gradient_proxy", "velocity-gradient proxy")
    plot_group(local_summary, "q_over_p_mean", "m3m_failed_vs_nonfailed_q_over_p", "q/p' proxy")
    plot_group(local_summary, "yield_residual_maxAbs", "m3m_yield_residual_comparison", "|yield residual|")
    plot_path(time_summary, "p_eff_mean", "q_mean", "m3m_global_pq_path", "p' proxy [Pa]", "q proxy [Pa]")
    plot_path(time_summary, "time", "pairwise_reaction_avg", "m3m_pairwise_reaction_vs_time", "time [s]", "pairwise reaction avg [N]")
    plot_path(time_summary, "time", "PorePress_mean", "m3m_pore_pressure_vs_time", "time [s]", "PorePress mean [Pa]")
    plot_path(time_summary, "time", "velocity_max", "m3m_velocity_max_vs_time", "time [s]", "velocity max [m/s]")
    plot_path(time_summary, "time", "cap_leakage_proxy_max", "m3m_cap_leakage_proxy_vs_time", "time [s]", "cap leakage proxy")


if __name__ == "__main__":
    main()
