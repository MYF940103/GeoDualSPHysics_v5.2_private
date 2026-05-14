#!/usr/bin/env python3
"""Analyze M3n smooth-layout dense diagnostics."""

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
    ("CaseM3n_Overhang045Reference", "overhang045_ref", 0.01),
    ("CaseM3n_Dp0075Overhang045", "dp0075_overhang045", 0.0075),
]

R = 0.03
HGT = 0.10
HDP = 1.8
EDGE_R = 0.020
CAP_Z = 0.015
CORE_R = 0.010
CORE_Z0 = 0.025
CORE_Z1 = 0.075
AREA = math.pi * R * R


def rows_csv(path: Path):
    with path.open(newline="") as f:
        reader = csv.reader(f, delimiter=";")
        headers = [h.strip() for h in next(reader) if h.strip()]
        out = []
        for raw in reader:
            if len(raw) < len(headers):
                continue
            row = {}
            for k, v in zip(headers, raw):
                if k in {"Idp", "Type"}:
                    row[k] = int(float(v))
                else:
                    try:
                        row[k] = float(v)
                    except ValueError:
                        row[k] = math.nan
            out.append(row)
        return out


def write_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)


def fmean(vals):
    vals = [float(v) for v in vals if v is not None and math.isfinite(float(v))]
    return sum(vals) / len(vals) if vals else math.nan


def fstd(vals):
    vals = [float(v) for v in vals if v is not None and math.isfinite(float(v))]
    return float(np.std(vals)) if vals else math.nan


def fmaxabs(vals):
    vals = [abs(float(v)) for v in vals if v is not None and math.isfinite(float(v))]
    return max(vals, default=math.nan)


def part_idx(path: Path):
    return int(path.stem.split("_")[-1])


def parse_times(out: Path):
    times = {0: 0.0}
    rx = re.compile(r"Part_(\d+)\s+([0-9]+\.[0-9Ee+\-.]*)")
    text = (out / "Run.out").read_text(errors="ignore")
    for line in text.splitlines():
        m = rx.search(line)
        if m:
            times[int(m.group(1))] = float(m.group(2))
    return times


def parse_status(out: Path):
    text = (out / "Run.out").read_text(errors="ignore")
    def grab(rx):
        m = re.search(rx, text)
        return int(m.group(1)) if m else -1
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
    data = []
    for line in (out / "Run.out").read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if m:
            d = {k: float(v.rstrip(".")) for k, v in m.groupdict().items() if k != "step"}
            data.append({"step": int(m.group("step")), **d})
    return data


def parse_conf(out: Path):
    rx = re.compile(r"FlexibleConfiningStress extended diagnostics: step=(?P<step>\d+).*?lateral_fi_selected=(?P<lat>\d+).*?cap_abs_axial_accel_max=(?P<cap>[0-9Ee+\-.]+)")
    data = []
    for line in (out / "Run.out").read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if m:
            data.append({"time": 0.0, "lateral_active_targets": int(m.group("lat")), "cap_leakage_proxy": float(m.group("cap").rstrip("."))})
    return data


def nearest(t, rows):
    return min(rows, key=lambda r: abs(r["time"] - t)) if rows else None


def pos(row):
    return np.array([row["Pos.x [m]"], row["Pos.y [m]"], row["Pos.z [m]"]], dtype=float)


def vel(row):
    return np.array([row["Vel.x [m/s]"], row["Vel.y [m/s]"], row["Vel.z [m/s]"]], dtype=float)


def region(x, y, z):
    rr = math.hypot(x, y)
    cap_b = z <= CAP_Z
    cap_t = z >= HGT - CAP_Z
    lat = rr >= EDGE_R
    core = rr <= CORE_R and CORE_Z0 <= z <= CORE_Z1
    if lat and (cap_b or cap_t):
        return "edge_ring", rr
    if cap_b:
        return "bottom_cap_zone", rr
    if cap_t:
        return "top_cap_zone", rr
    if lat:
        return "lateral_surface", rr
    if core:
        return "measurement_core", rr
    return "interior", rr


def pq(row):
    sx, sy, sz = row.get("Sigma_kk.x", 0.0), row.get("Sigma_kk.y", 0.0), row.get("Sigma_kk.z", 0.0)
    sxy, syz, sxz = row.get("Sigma_ij.x", 0.0), row.get("Sigma_ij.y", 0.0), row.get("Sigma_ij.z", 0.0)
    p = -(sx + sy + sz) / 3.0
    m = (sx + sy + sz) / 3.0
    dxx, dyy, dzz = sx - m, sy - m, sz - m
    j2 = 0.5 * (dxx*dxx + dyy*dyy + dzz*dzz + 2.0*(sxy*sxy + syz*syz + sxz*sxz))
    return p, math.sqrt(max(0.0, 3.0 * j2))


def weight(dist, h):
    q = dist / h
    if q >= 2.0:
        return 0.0
    return (1 - 0.5*q) ** 4 * (2*q + 1)


def grad_metric(i, xyz, vv, neigh):
    if len(neigh) < 4:
        return {}
    dx = xyz[neigh] - xyz[i]
    dv = vv[neigh] - vv[i]
    try:
        g, *_ = np.linalg.lstsq(dx, dv, rcond=None)
    except np.linalg.LinAlgError:
        return {}
    g = g.T
    sym = 0.5 * (g + g.T)
    return {"velocity_gradient_norm": float(np.linalg.norm(g)), "shear_rate_proxy": math.sqrt(max(0.0, 2.0 * float(np.sum(sym * sym))))}


def frame(case, variant, dp, part, time, rows, reaction, conf):
    h = HDP * dp
    support = 2.0 * h
    all_xyz = np.array([pos(r) for r in rows])
    spec = [r for r in rows if int(r.get("Type", -1)) == 3]
    xyz = np.array([pos(r) for r in spec])
    vv = np.array([vel(r) for r in spec])
    cache, core_support = [], []
    for i, row in enumerate(spec):
        d_all = np.linalg.norm(all_xyz - xyz[i], axis=1)
        d_spec = np.linalg.norm(xyz - xyz[i], axis=1)
        mask_all = (d_all > 1e-12) & (d_all <= support)
        mask_spec = (d_spec > 1e-12) & (d_spec <= support)
        wsum = sum(weight(float(d), h) for d in d_all[mask_all])
        reg, _ = region(*xyz[i])
        if reg == "measurement_core":
            core_support.append(wsum)
        cache.append({"all": int(mask_all.sum()), "spec": int(mask_spec.sum()), "neigh": np.where(mask_spec)[0], "w": wsum, "nearest": float(np.min(d_spec[d_spec > 1e-12]))})
    core = fmean(core_support)
    pair = 0.5 * (reaction["tfz"] + abs(reaction["bfz"])) if reaction else math.nan
    bal = reaction["balance"] if reaction else math.nan
    lat = conf["lateral_active_targets"] if conf else math.nan
    cap = conf["cap_leakage_proxy"] if conf else math.nan
    out = []
    for i, row in enumerate(spec):
        x, y, z = xyz[i]
        reg, rr = region(x, y, z)
        p, q = pq(row)
        st = int(round(row.get("MccReturnStatus", 0.0)))
        gm = grad_metric(i, xyz, vv, cache[i]["neigh"])
        out.append({
            "case": case, "variant": variant, "part": part, "time": time, "dp": dp,
            "idp": int(row.get("Idp", -1)), "return_status": st, "failed": int(st < 0),
            "x": x, "y": y, "z": z, "r": rr, "r_over_R": rr / R, "z_over_H": z / HGT, "region": reg,
            "neighbor_count_all": cache[i]["all"], "neighbor_count_specimen": cache[i]["spec"],
            "nearest_neighbor_distance": cache[i]["nearest"], "kernel_support_sum": cache[i]["w"],
            "kernel_support_ratio_to_core": cache[i]["w"] / core if core else math.nan,
            "velocity": float(np.linalg.norm(vv[i])), "DivVel": row.get("DivVel", 0.0),
            "PorePressRate": row.get("PorePressRate", 0.0), "PorePress": row.get("PorePress", 0.0),
            "sigma_zz": row.get("Sigma_kk.z", 0.0), "p_eff": p, "q": q, "q_over_p": q / p if abs(p) > 1e-12 else math.nan,
            "pc": row.get("MccPc", 0.0), "void_ratio": row.get("MccVoidRatio", 0.0),
            "plastic_vol_strain": row.get("MccPlasticVolStrain", 0.0), "eq_plastic_strain": row.get("MccEqPlasticStrain", 0.0),
            "plastic_multiplier": row.get("MccPlasticMultiplier", 0.0), "return_iterations": row.get("MccReturnIterations", 0.0),
            "yield_residual": row.get("MccYieldResidual", 0.0), "Kplastic": row.get("Kplastic", 0.0),
            "pairwise_reaction_avg": pair, "axial_stress_reaction": pair / AREA if math.isfinite(pair) else math.nan,
            "force_balance_error": bal, "lateral_active_targets": lat, "cap_leakage_proxy": cap,
            "velocity_gradient_norm": gm.get("velocity_gradient_norm", math.nan), "shear_rate_proxy": gm.get("shear_rate_proxy", math.nan),
        })
    return out


def group(rows, keys):
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r[k] for k in keys)].append(r)
    out = []
    for key, vals in sorted(groups.items()):
        c = Counter(v["return_status"] for v in vals)
        row = {k: v for k, v in zip(keys, key)}
        row.update({
            "count": len(vals), "failed_count": sum(v["failed"] for v in vals),
            "status_-3": c[-3], "status_-1": c[-1],
            "neighbor_count_specimen_mean": fmean(v["neighbor_count_specimen"] for v in vals),
            "support_ratio_mean": fmean(v["kernel_support_ratio_to_core"] for v in vals),
            "velocity_gradient_norm_mean": fmean(v["velocity_gradient_norm"] for v in vals),
            "shear_rate_mean": fmean(v["shear_rate_proxy"] for v in vals),
            "p_eff_mean": fmean(v["p_eff"] for v in vals), "q_mean": fmean(v["q"] for v in vals),
            "q_over_p_mean": fmean(v["q_over_p"] for v in vals),
            "yield_residual_maxAbs": fmaxabs(v["yield_residual"] for v in vals),
            "pc_mean": fmean(v["pc"] for v in vals), "void_ratio_mean": fmean(v["void_ratio"] for v in vals),
            "plastic_vol_strain_mean": fmean(v["plastic_vol_strain"] for v in vals),
            "eq_plastic_strain_mean": fmean(v["eq_plastic_strain"] for v in vals),
            "pairwise_reaction_avg": fmean(v["pairwise_reaction_avg"] for v in vals),
            "force_balance_error_mean": fmean(v["force_balance_error"] for v in vals),
            "sigma_zz_mean": fmean(v["sigma_zz"] for v in vals),
            "Fz_proxy": -fmean(v["sigma_zz"] for v in vals) * AREA,
            "PorePress_mean": fmean(v["PorePress"] for v in vals),
            "PorePressRate_maxAbs": fmaxabs(v["PorePressRate"] for v in vals),
            "velocity_max": max([v["velocity"] for v in vals], default=math.nan),
            "lateral_active_targets": fmean(v["lateral_active_targets"] for v in vals),
            "cap_leakage_proxy_max": fmaxabs(v["cap_leakage_proxy"] for v in vals),
        })
        out.append(row)
    return out


def status_timeline(rows):
    by = defaultdict(Counter)
    for r in rows:
        by[(r["case"], r["variant"], r["time"])][r["return_status"]] += 1
    out = []
    for (case, variant, time), c in sorted(by.items()):
        out.append({"case": case, "variant": variant, "time": time, "status_-3": c[-3], "status_-1": c[-1], "status_0": c[0], "status_1": c[1], "negative_count": sum(v for k, v in c.items() if k < 0)})
    return out


def plot_line(rows, y, name, ylabel):
    fig, ax = plt.subplots(figsize=(7, 4))
    for _, variant, _ in CASES:
        rr = [r for r in rows if r["variant"] == variant]
        ax.plot([r["time"] for r in rr], [r[y] for r in rr], label=variant)
    ax.set_xlabel("time [s]"); ax.set_ylabel(ylabel); ax.grid(True, alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIGDIR / f"{name}.svg"); fig.savefig(FIGDIR / f"{name}.png", dpi=180); plt.close(fig)


def plot_scatter(rows, y, name, ylabel):
    fig, ax = plt.subplots(figsize=(7, 4))
    for failed, marker in [(0, "o"), (1, "s")]:
        rr = [r for r in rows if int(r["failed"]) == failed]
        ax.scatter([r["variant"] for r in rr], [r[y] for r in rr], marker=marker, label="failed" if failed else "nonfailed")
    ax.set_ylabel(ylabel); ax.grid(True, axis="y", alpha=0.3); ax.legend(); fig.tight_layout()
    fig.savefig(FIGDIR / f"{name}.svg"); fig.savefig(FIGDIR / f"{name}.png", dpi=180); plt.close(fig)


def plot_path(rows, x, y, name, xlabel, ylabel):
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for _, variant, _ in CASES:
        rr = [r for r in rows if r["variant"] == variant]
        ax.plot([r[x] for r in rr], [r[y] for r in rr], label=variant)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.grid(True, alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIGDIR / f"{name}.svg"); fig.savefig(FIGDIR / f"{name}.png", dpi=180); plt.close(fig)


def main():
    metrics, summary, layout = [], [], []
    init_sets = {}
    for case, variant, dp in CASES:
        out = ROOT / f"{case}_out"
        times, react, conf = parse_times(out), parse_reactions(out), parse_conf(out)
        case_rows = []
        for p in sorted((out / "data").glob("PartCsv_*.csv"), key=part_idx):
            part = part_idx(p)
            t = times.get(part, float(part))
            case_rows.extend(frame(case, variant, dp, part, t, rows_csv(p), nearest(t, react), nearest(t, conf)))
        metrics.extend(case_rows)
        st = status_timeline(case_rows)
        run = parse_status(out)
        first = next((r for r in st if r["negative_count"] > 0), None)
        final = st[-1]
        summary.append({**{"case": case, "variant": variant, "dp": dp}, **run,
            "first_failure_time": first["time"] if first else math.nan,
            "first_failure_negative_count": first["negative_count"] if first else 0,
            "first_failure_status_-3": first["status_-3"] if first else 0,
            "first_failure_status_-1": first["status_-1"] if first else 0,
            "max_status_-3": max(r["status_-3"] for r in st),
            "max_status_-1": max(r["status_-1"] for r in st),
            "bad_frame_count": sum(1 for r in st if r["negative_count"] > 0),
            "final_time": final["time"], "final_status_-3": final["status_-3"],
            "final_status_-1": final["status_-1"], "final_negative_count": final["negative_count"]})
        init = [r for r in case_rows if r["time"] == 0.0]
        init_sets[variant] = {(round(r["x"], 5), round(r["y"], 5), round(r["z"], 5)) for r in init}
        edge = [r for r in init if r["region"] == "edge_ring"]; cap = [r for r in init if r["region"] in {"edge_ring", "top_cap_zone", "bottom_cap_zone"}]; core = [r for r in init if r["region"] == "measurement_core"]
        layout.append({"case": case, "variant": variant, "dp": dp, "specimen_particle_count": len(init),
            "edge_corner_count": len(edge), "cap_edge_count": len(cap), "measurement_core_count": len(core),
            "edge_support_mean": fmean(r["kernel_support_ratio_to_core"] for r in edge),
            "edge_neighbor_mean": fmean(r["neighbor_count_specimen"] for r in edge),
            "cap_support_mean": fmean(r["kernel_support_ratio_to_core"] for r in cap),
            "cap_neighbor_mean": fmean(r["neighbor_count_specimen"] for r in cap),
            "core_support_mean": fmean(r["kernel_support_ratio_to_core"] for r in core),
            "core_neighbor_mean": fmean(r["neighbor_count_specimen"] for r in core),
            "nearest_neighbor_mean": fmean(r["nearest_neighbor_distance"] for r in init),
            "nearest_neighbor_std": fstd(r["nearest_neighbor_distance"] for r in init),
            "max_cap_radius": max([r["r"] for r in cap], default=math.nan),
            "platen_contamination_core": 0})
    timeline = status_timeline(metrics)
    local = group(metrics, ["variant", "failed"])
    region_rows = group(metrics, ["variant", "failed", "region"])
    time_rows = group(metrics, ["variant", "time"])
    ref = init_sets.get("overhang045_ref", set())
    for row in layout:
        pts = init_sets.get(row["variant"], set())
        row["actual_particle_set_added_vs_reference"] = len(pts - ref)
        row["actual_particle_set_removed_vs_reference"] = len(ref - pts)
    failed = [r for r in metrics if r["failed"]]

    for name, rows in {
        "m3n_case_summary.csv": summary,
        "m3n_geometry_quality_comparison.csv": layout,
        "m3n_geometry_quality_metrics.csv": layout,
        "m3n_particle_layout_summary.csv": layout,
        "m3n_return_status_comparison.csv": timeline,
        "m3n_failed_particle_locations.csv": failed,
        "m3n_support_neighbor_comparison.csv": local,
        "m3n_support_neighbor_metrics.csv": local,
        "m3n_velocity_gradient_comparison.csv": local,
        "m3n_stress_path_local_comparison.csv": region_rows,
        "m3n_reaction_stress_path_comparison.csv": time_rows,
        "m3n_pore_pressure_comparison.csv": time_rows,
    }.items():
        write_csv(ROOT / name, rows)

    plot_line(timeline, "status_-3", "m3n_return_status_minus3_vs_time", "ReturnStatus=-3 count")
    plot_line(timeline, "status_-1", "m3n_return_status_minus1_vs_time", "ReturnStatus=-1 count")
    plot_line(timeline, "negative_count", "m3n_negative_return_status_vs_time", "negative return count")
    plot_scatter(local, "support_ratio_mean", "m3n_support_proxy_distribution", "support ratio to core")
    plot_scatter(local, "neighbor_count_specimen_mean", "m3n_neighbor_count_proxy", "specimen neighbor proxy")
    plot_scatter(local, "velocity_gradient_norm_mean", "m3n_velocity_gradient_proxy", "velocity-gradient proxy")
    plot_scatter(local, "q_over_p_mean", "m3n_failed_vs_nonfailed_q_over_p", "q/p'")
    plot_scatter(local, "yield_residual_maxAbs", "m3n_yield_residual_comparison", "|yield residual|")
    plot_path(time_rows, "p_eff_mean", "q_mean", "m3n_global_pq_path", "p' proxy [Pa]", "q proxy [Pa]")
    plot_path(time_rows, "time", "pairwise_reaction_avg", "m3n_pairwise_reaction_vs_time", "time [s]", "pairwise reaction [N]")
    plot_path(time_rows, "time", "PorePress_mean", "m3n_pore_pressure_vs_time", "time [s]", "PorePress mean [Pa]")
    plot_path(time_rows, "time", "velocity_max", "m3n_velocity_max_vs_time", "time [s]", "velocity max [m/s]")
    plot_path(time_rows, "time", "cap_leakage_proxy_max", "m3n_cap_leakage_proxy_vs_time", "time [s]", "cap leakage proxy")
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 4.2), sharey=True)
    for ax, (_, variant, _) in zip(axes, CASES):
        init = [r for r in metrics if r["variant"] == variant and r["time"] == 0.0]
        sc = ax.scatter([r["r_over_R"] for r in init], [r["z_over_H"] for r in init], c=[r["kernel_support_ratio_to_core"] for r in init], s=5, cmap="viridis")
        ax.set_title(variant); ax.set_xlabel("r/R"); ax.grid(True, alpha=0.2)
    axes[0].set_ylabel("z/H"); fig.colorbar(sc, ax=axes.ravel().tolist(), label="support/core")
    fig.savefig(FIGDIR / "m3n_geometry_particle_layout_comparison.svg"); fig.savefig(FIGDIR / "m3n_geometry_particle_layout_comparison.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 4.2), sharey=True)
    for ax, (_, variant, _) in zip(axes, CASES):
        init = [r for r in metrics if r["variant"] == variant and r["time"] == 0.0]
        fail = [r for r in metrics if r["variant"] == variant and r["failed"]]
        ax.scatter([r["r_over_R"] for r in init], [r["z_over_H"] for r in init], s=4, c="0.75", alpha=0.25)
        ax.scatter([r["r_over_R"] for r in fail], [r["z_over_H"] for r in fail], s=9, c="tab:red", alpha=0.55)
        ax.set_title(variant); ax.set_xlabel("r/R"); ax.grid(True, alpha=0.2)
    axes[0].set_ylabel("z/H")
    fig.savefig(FIGDIR / "m3n_failed_locations_rz.svg"); fig.savefig(FIGDIR / "m3n_failed_locations_rz.png", dpi=180); plt.close(fig)


if __name__ == "__main__":
    main()
