#!/usr/bin/env python3
"""Dense-output platen/edge diagnostic for MCC return failures."""

from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
CASE = "CaseM3k_MCCMildDenseOnset"
OUT = ROOT / f"{CASE}_out"
DATA = OUT / "data"
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

RADIUS = 0.03
HEIGHT = 0.10
DP = 0.01
H = 0.018
SUPPORT = 2.0 * H
EDGE_R = 0.020
CAP_Z = 0.015
CORE_R = 0.010
CORE_Z0 = 0.025
CORE_Z1 = 0.075


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


def part_files():
    return sorted(DATA.glob("PartCsv_*.csv"), key=part_index)


def parse_times():
    run = OUT / "Run.out"
    times = {0: 0.0}
    rx = re.compile(r"Part_(\d+)\s+([0-9]+\.[0-9Ee+\-.]*)")
    if run.exists():
        for line in run.read_text(errors="ignore").splitlines():
            m = rx.search(line)
            if m:
                times[int(m.group(1))] = float(m.group(2))
    return times


def parse_reactions():
    run = OUT / "Run.out"
    rows = []
    rx = re.compile(
        r"PlatenReaction diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[0-9Ee+\-.]+).*?"
        r"top_force=\((?P<tfx>[0-9Ee+\-.]+),(?P<tfy>[0-9Ee+\-.]+),(?P<tfz>[0-9Ee+\-.]+)\).*?"
        r"bottom_force=\((?P<bfx>[0-9Ee+\-.]+),(?P<bfy>[0-9Ee+\-.]+),(?P<bfz>[0-9Ee+\-.]+)\).*?"
        r"force_balance_error=(?P<balance>[0-9Ee+\-.]+)"
    )
    if not run.exists():
        return rows
    for line in run.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if not m:
            continue
        vals = {k: float(v.rstrip(".")) for k, v in m.groupdict().items() if k != "step"}
        rows.append({"step": int(m.group("step")), **vals})
    return rows


def nearest_reaction(time, reactions):
    if not reactions:
        return None
    return min(reactions, key=lambda r: abs(r["time"] - time))


def specimen(row) -> bool:
    return int(row.get("Type", -1)) == 3


def pos(row):
    return np.array([row["Pos.x [m]"], row["Pos.y [m]"], row["Pos.z [m]"]], dtype=float)


def vel(row):
    return np.array([row["Vel.x [m/s]"], row["Vel.y [m/s]"], row["Vel.z [m/s]"]], dtype=float)


def velocity_mag(row):
    return float(np.linalg.norm(vel(row)))


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


def safe_mean(vals):
    vals = [v for v in vals if v is not None and math.isfinite(float(v))]
    return sum(vals) / len(vals) if vals else math.nan


def safe_std(vals):
    vals = [v for v in vals if v is not None and math.isfinite(float(v))]
    if len(vals) < 2:
        return 0.0 if vals else math.nan
    mu = safe_mean(vals)
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))


def write_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def local_gradient(i, spec_positions, spec_velocities, neighbour_idx):
    if len(neighbour_idx) < 4:
        return None
    dx = spec_positions[neighbour_idx] - spec_positions[i]
    dv = spec_velocities[neighbour_idx] - spec_velocities[i]
    try:
        grad, *_ = np.linalg.lstsq(dx, dv, rcond=None)
    except np.linalg.LinAlgError:
        return None
    # grad maps [dx,dy,dz] to [dvx,dvy,dvz]; component dV_j/dx_i = grad[i,j].
    g = grad.T
    sym = 0.5 * (g + g.T)
    shear = math.sqrt(max(0.0, 2.0 * float(np.sum(sym * sym))))
    return {
        "grad_vxx": g[0, 0],
        "grad_vyy": g[1, 1],
        "grad_vzz": g[2, 2],
        "axial_strain_rate_proxy": g[2, 2],
        "radial_strain_rate_proxy": 0.5 * (g[0, 0] + g[1, 1]),
        "shear_rate_proxy": shear,
        "velocity_gradient_norm": float(np.linalg.norm(g)),
    }


def build_frame_metrics(part, time, rows, reaction):
    all_positions = np.array([pos(r) for r in rows])
    spec_rows = [r for r in rows if specimen(r)]
    spec_positions = np.array([pos(r) for r in spec_rows])
    spec_velocities = np.array([vel(r) for r in spec_rows])
    # Pairwise distances from specimen particles to all particles and specimen particles.
    out = []
    core_support = []
    neighbour_sets = []
    all_count_cache = []
    spec_count_cache = []
    weight_cache = []
    nearest_cache = []
    grad_cache = []

    for i, row in enumerate(spec_rows):
        pi = spec_positions[i]
        dall = np.linalg.norm(all_positions - pi, axis=1)
        dspec = np.linalg.norm(spec_positions - pi, axis=1)
        all_mask = (dall > 1e-12) & (dall <= SUPPORT)
        spec_mask = (dspec > 1e-12) & (dspec <= SUPPORT)
        spec_idx = np.where(spec_mask)[0]
        neighbour_sets.append(spec_idx)
        all_count = int(np.count_nonzero(all_mask))
        spec_count = int(np.count_nonzero(spec_mask))
        all_count_cache.append(all_count)
        spec_count_cache.append(spec_count)
        nearest_cache.append(float(np.min(dspec[dspec > 1e-12])) if np.any(dspec > 1e-12) else math.nan)
        wsum = float(sum(wendland_weight(float(d)) for d in dall[all_mask]))
        weight_cache.append(wsum)
        x, y, z = pi
        reg, r = region_from_xyz(float(x), float(y), float(z))
        if reg == "measurement_core":
            core_support.append(wsum)

    core_support_mean = safe_mean(core_support)
    for i, row in enumerate(spec_rows):
        grad = local_gradient(i, spec_positions, spec_velocities, neighbour_sets[i])
        grad_cache.append(grad or {})
        x, y, z = spec_positions[i]
        reg, r = region_from_xyz(float(x), float(y), float(z))
        p, q = stress_invariants(row)
        status = int(round(row.get("MccReturnStatus", 0.0)))
        support_ratio = weight_cache[i] / core_support_mean if core_support_mean and math.isfinite(core_support_mean) else math.nan
        pairwise = math.nan
        balance = math.nan
        if reaction:
            pairwise = 0.5 * (reaction["tfz"] + abs(reaction["bfz"]))
            balance = reaction["balance"]
        rec = {
            "part": part,
            "time": time,
            "idp": int(row.get("Idp", -1)),
            "return_status": status,
            "failed": int(status < 0),
            "x": float(x),
            "y": float(y),
            "z": float(z),
            "r": r,
            "r_over_R": r / RADIUS,
            "z_over_H": float(z) / HEIGHT,
            "distance_to_top_platen": HEIGHT - float(z),
            "distance_to_bottom_platen": float(z),
            "distance_to_lateral_boundary": RADIUS - r,
            "distance_to_edge_corner": min(math.hypot(RADIUS - r, float(z)), math.hypot(RADIUS - r, HEIGHT - float(z))),
            "region": reg,
            "neighbor_count_all": all_count_cache[i],
            "neighbor_count_specimen": spec_count_cache[i],
            "nearest_neighbor_distance": nearest_cache[i],
            "kernel_support_sum": weight_cache[i],
            "kernel_support_ratio_to_core": support_ratio,
            "velocity": velocity_mag(row),
            "DivVel": row.get("DivVel", 0.0),
            "PorePressRate": row.get("PorePressRate", 0.0),
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
            "PorePress": row.get("PorePress", 0.0),
            "pairwise_reaction_avg": pairwise,
            "force_balance_error": balance,
        }
        rec.update({
            "velocity_gradient_available": int(bool(grad)),
            "axial_strain_rate_proxy": (grad or {}).get("axial_strain_rate_proxy", math.nan),
            "radial_strain_rate_proxy": (grad or {}).get("radial_strain_rate_proxy", math.nan),
            "shear_rate_proxy": (grad or {}).get("shear_rate_proxy", math.nan),
            "velocity_gradient_norm": (grad or {}).get("velocity_gradient_norm", math.nan),
        })
        out.append(rec)
    return out


def summarize_groups(rows, keys):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in keys)].append(row)
    out = []
    for key, vals in sorted(groups.items()):
        status = Counter(v["return_status"] for v in vals)
        rec = {k: v for k, v in zip(keys, key)}
        rec.update({
            "count": len(vals),
            "failed_count": sum(v["failed"] for v in vals),
            "status_-3": status[-3],
            "status_-1": status[-1],
            "neighbor_count_all_mean": safe_mean(v["neighbor_count_all"] for v in vals),
            "neighbor_count_specimen_mean": safe_mean(v["neighbor_count_specimen"] for v in vals),
            "support_ratio_mean": safe_mean(v["kernel_support_ratio_to_core"] for v in vals),
            "kernel_support_ratio_to_core_mean": safe_mean(v["kernel_support_ratio_to_core"] for v in vals),
            "nearest_neighbor_mean": safe_mean(v["nearest_neighbor_distance"] for v in vals),
            "velocity_mean": safe_mean(v["velocity"] for v in vals),
            "velocity_gradient_norm_mean": safe_mean(v["velocity_gradient_norm"] for v in vals),
            "axial_strain_rate_mean": safe_mean(v["axial_strain_rate_proxy"] for v in vals),
            "radial_strain_rate_mean": safe_mean(v["radial_strain_rate_proxy"] for v in vals),
            "shear_rate_mean": safe_mean(v["shear_rate_proxy"] for v in vals),
            "DivVel_mean": safe_mean(v["DivVel"] for v in vals),
            "PorePressRate_maxAbs": max(abs(v["PorePressRate"]) for v in vals),
            "p_eff_mean": safe_mean(v["p_eff"] for v in vals),
            "q_mean": safe_mean(v["q"] for v in vals),
            "q_over_p_mean": safe_mean(v["q_over_p"] for v in vals),
            "pc_mean": safe_mean(v["pc"] for v in vals),
            "yield_residual_mean": safe_mean(v["yield_residual"] for v in vals),
            "yield_residual_maxAbs": max(abs(v["yield_residual"]) for v in vals),
            "return_iterations_max": max(v["return_iterations"] for v in vals),
            "pairwise_reaction_avg": safe_mean(v["pairwise_reaction_avg"] for v in vals),
        })
        out.append(rec)
    return out


def nearest_nonfailed_comparison(frame_rows):
    out = []
    by_time = defaultdict(list)
    for row in frame_rows:
        by_time[row["time"]].append(row)
    for time, rows in by_time.items():
        failed = [r for r in rows if r["failed"]]
        nonfailed = [r for r in rows if not r["failed"]]
        core = [r for r in nonfailed if r["region"] == "measurement_core"]
        for fr in failed:
            nearest = None
            nd = math.inf
            for nr in nonfailed:
                d = math.sqrt((fr["x"] - nr["x"]) ** 2 + (fr["y"] - nr["y"]) ** 2 + (fr["z"] - nr["z"]) ** 2)
                if d < nd:
                    nd = d
                    nearest = nr
            same = [r for r in nonfailed if r["region"] == fr["region"]]
            rec = {
                "time": time,
                "part": fr["part"],
                "failed_idp": fr["idp"],
                "failed_status": fr["return_status"],
                "failed_region": fr["region"],
                "nearest_nonfailed_idp": nearest["idp"] if nearest else -1,
                "nearest_distance": nd if nearest else math.nan,
            }
            for key in ["neighbor_count_all", "neighbor_count_specimen", "kernel_support_ratio_to_core", "velocity_gradient_norm", "shear_rate_proxy", "DivVel", "PorePressRate", "p_eff", "q", "q_over_p", "pc", "yield_residual", "return_iterations"]:
                fv = fr[key]
                nv = nearest[key] if nearest else math.nan
                sv = safe_mean(r[key] for r in same)
                cv = safe_mean(r[key] for r in core)
                rec[f"failed_{key}"] = fv
                rec[f"nearest_nonfailed_{key}"] = nv
                rec[f"same_region_nonfailed_mean_{key}"] = sv
                rec[f"measurement_core_nonfailed_mean_{key}"] = cv
                rec[f"failed_minus_nearest_{key}"] = fv - nv if math.isfinite(fv) and math.isfinite(nv) else math.nan
            out.append(rec)
    return out


def parse_run_status():
    text = (OUT / "Run.out").read_text(errors="ignore")
    def grab(rx, default=-1):
        m = re.search(rx, text)
        return int(m.group(1)) if m else default
    return {
        "code": 0 if "Finished execution (code=0)" in text else -1,
        "excluded": grab(r"Excluded particles\.+:\s+(\d+)"),
        "dtmin_adjustments": grab(r"DTs adjusted to DtMin\.+:\s+(\d+)"),
        "steps": grab(r"Steps of simulation\.+:\s+(\d+)"),
    }


def plot_lines(name, rows, ykey, ylabel):
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for label, pred in [
        ("failed", lambda r: r["failed"]),
        ("nonfailed", lambda r: not r["failed"]),
        ("measurement_core", lambda r: r["region"] == "measurement_core"),
    ]:
        data = summarize_groups([r for r in rows if pred(r)], ["time"])
        if not data:
            continue
        key = f"{ykey}_mean" if f"{ykey}_mean" in data[0] else ykey
        ax.plot([d["time"] for d in data], [d.get(key, math.nan) for d in data], label=label)
    ax.set_xlabel("time [s]")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGDIR / f"{name}.svg")
    fig.savefig(FIGDIR / f"{name}.png", dpi=180)
    plt.close(fig)


def main():
    times = parse_times()
    reactions = parse_reactions()
    all_metrics = []
    for path in part_files():
        part = part_index(path)
        time = times.get(part, float(part))
        reaction = nearest_reaction(time, reactions)
        all_metrics.extend(build_frame_metrics(part, time, read_rows(path), reaction))

    failed = [r for r in all_metrics if r["failed"]]
    first_failure_time = min((r["time"] for r in failed), default=math.nan)
    onset_window = [
        r for r in all_metrics
        if math.isfinite(first_failure_time) and first_failure_time - 0.0005 <= r["time"] <= first_failure_time + 0.0005
    ]

    write_csv(ROOT / "m3k_neighbor_support_metrics.csv", all_metrics)
    write_csv(ROOT / "m3k_velocity_gradient_proxy.csv", [
        {k: r[k] for k in ["part", "time", "idp", "return_status", "failed", "region", "velocity", "velocity_gradient_available", "axial_strain_rate_proxy", "radial_strain_rate_proxy", "shear_rate_proxy", "velocity_gradient_norm", "DivVel", "PorePressRate"]}
        for r in all_metrics
    ])
    write_csv(ROOT / "m3k_failed_particle_timeline.csv", failed)
    write_csv(ROOT / "m3k_failed_vs_nonfailed_local_metrics.csv", nearest_nonfailed_comparison(onset_window))
    write_csv(ROOT / "m3k_region_failure_statistics.csv", summarize_groups(all_metrics, ["time", "region", "return_status"]))
    write_csv(ROOT / "m3k_failure_onset_summary.csv", [{
        **parse_run_status(),
        "case": CASE,
        "first_failure_time": first_failure_time,
        "first_failure_count": sum(1 for r in all_metrics if r["time"] == first_failure_time and r["failed"]),
        "first_failure_status_-3": sum(1 for r in all_metrics if r["time"] == first_failure_time and r["return_status"] == -3),
        "first_failure_status_-1": sum(1 for r in all_metrics if r["time"] == first_failure_time and r["return_status"] == -1),
        "frames": len(set(r["time"] for r in all_metrics)),
        "saved_particles_per_frame": len([r for r in all_metrics if r["time"] == 0.0]),
    }])

    # Compact summaries for report.
    write_csv(ROOT / "m3k_failed_vs_region_summary.csv", summarize_groups(onset_window, ["failed", "region"]))
    write_csv(ROOT / "m3k_failed_vs_status_summary.csv", summarize_groups(onset_window, ["failed", "return_status"]))

    # Figures.
    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    for status, color in [(-3, "tab:red"), (-1, "tab:orange"), (0, "0.75"), (1, "tab:green")]:
        pts = [r for r in all_metrics if r["return_status"] == status]
        if not pts:
            continue
        ax.scatter([r["r_over_R"] for r in pts], [r["z_over_H"] for r in pts], s=8, alpha=0.45, label=f"status {status}", c=color)
    ax.axhline(CAP_Z / HEIGHT, color="0.4", ls="--", lw=0.8)
    ax.axhline((HEIGHT - CAP_Z) / HEIGHT, color="0.4", ls="--", lw=0.8)
    ax.axvline(EDGE_R / RADIUS, color="0.4", ls="--", lw=0.8)
    ax.set_xlabel("r/R")
    ax.set_ylabel("z/H")
    ax.set_title("M3k return status map")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGDIR / "m3k_failed_particle_maps.svg")
    fig.savefig(FIGDIR / "m3k_failed_particle_maps.png", dpi=180)
    plt.close(fig)

    for ykey, ylabel, name in [
        ("q_over_p", "q/p' proxy", "m3k_failed_vs_nonfailed_q_over_p"),
        ("p_eff", "p' [Pa]", "m3k_failed_vs_nonfailed_p_eff"),
        ("DivVel", "DivVel", "m3k_failed_vs_nonfailed_divvel"),
        ("velocity_gradient_norm", "velocity-gradient proxy", "m3k_failed_vs_nonfailed_gradv"),
        ("kernel_support_ratio_to_core", "support ratio to core", "m3k_failed_vs_nonfailed_support"),
        ("yield_residual", "yield residual", "m3k_failed_vs_nonfailed_residual"),
    ]:
        plot_lines(name, all_metrics, ykey, ylabel)

    timeline = summarize_groups(all_metrics, ["time", "region"])
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for reg in sorted(set(r["region"] for r in timeline)):
        rr = [r for r in timeline if r["region"] == reg]
        ax.plot([r["time"] for r in rr], [r["failed_count"] for r in rr], label=reg)
    ax.set_xlabel("time [s]")
    ax.set_ylabel("failed count")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGDIR / "m3k_region_failure_count_vs_time.svg")
    fig.savefig(FIGDIR / "m3k_region_failure_count_vs_time.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    failed_by_time = summarize_groups(failed, ["time"])
    ax.plot([r["time"] for r in failed_by_time], [r["pairwise_reaction_avg"] for r in failed_by_time], label="nearest reaction avg")
    ax.set_xlabel("time [s]")
    ax.set_ylabel("pairwise platen reaction avg [N]")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGDIR / "m3k_reaction_near_onset.svg")
    fig.savefig(FIGDIR / "m3k_reaction_near_onset.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
