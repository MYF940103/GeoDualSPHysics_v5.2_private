#!/usr/bin/env python3
"""Generate a standalone smooth/fan-like triaxial layout prototype.

This script is intentionally isolated from GenCase and the solver.  It creates a
radial-ring specimen with a lightly rounded cap edge, ring-based top/bottom
platens, and geometry/support diagnostics that can be compared with the previous
Cartesian/cut-cell layouts.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


PARAMS = {
    "layout": "radial_ring_smooth_edge_prototype",
    "R": 0.03,
    "H": 0.10,
    "target_spacing": 0.01,
    "radial_spacing": 0.01,
    "angular_spacing": 0.0075,
    "edge_smoothing_radius": 0.010,
    "max_edge_radius_reduction": 0.00375,
    "platen_radius": 0.045,
    "platen_thickness": 0.015,
    "platen_gap": 0.005,
    "support_h_factor": 1.8,
}


BASELINE_COMPARISON = [
    {
        "case": "M3m_overhang045_cartesian_dp001",
        "layout": "Cartesian cut-cell with platen overhang",
        "specimen_count": 407,
        "edge_support_core_ratio": 0.828,
        "edge_neighbor_mean": 96.25,
        "cap_support_core_ratio": "",
        "cap_neighbor_mean": "",
        "max_return_status_minus3": 8,
        "max_return_status_minus1": 20,
        "solver_status": "CPU diagnostic already run",
    },
    {
        "case": "M3n_dp0075_cartesian_overhang045",
        "layout": "Higher-resolution Cartesian cut-cell",
        "specimen_count": 1035,
        "edge_support_core_ratio": 0.851,
        "edge_neighbor_mean": 87.5,
        "cap_support_core_ratio": 0.894,
        "cap_neighbor_mean": "",
        "max_return_status_minus3": 16,
        "max_return_status_minus1": 52,
        "solver_status": "CPU diagnostic already run",
    },
]


def ring_points(radius: float, spacing: float, angular_spacing: float, phase: float):
    if radius <= 1.0e-12:
        yield 0.0, 0.0, 0.0
        return
    ntheta = max(8, int(round(2.0 * math.pi * radius / angular_spacing)))
    for i in range(ntheta):
        theta = 2.0 * math.pi * (i / ntheta) + phase
        yield radius * math.cos(theta), radius * math.sin(theta), theta


def theta_count(radius: float) -> int:
    if radius <= 1.0e-12:
        return 1
    return max(8, int(round(2.0 * math.pi * radius / PARAMS["angular_spacing"])))


def ring_particle_volume(radius: float, radius_limit: float, z_spacing: float, ntheta: int) -> float:
    dr = PARAMS["radial_spacing"]
    if radius <= 1.0e-12:
        area = math.pi * (0.5 * dr) ** 2
        return area * z_spacing
    inner = max(0.0, radius - 0.5 * dr)
    outer = min(radius_limit, radius + 0.5 * dr)
    area = math.pi * max(0.0, outer * outer - inner * inner)
    return area * z_spacing / max(1, ntheta)


def specimen_radius_limit(z: float) -> float:
    r = PARAMS["R"]
    edge_radius = PARAMS["edge_smoothing_radius"]
    max_reduction = PARAMS["max_edge_radius_reduction"]
    cap_dist = min(z, PARAMS["H"] - z)
    if cap_dist >= edge_radius:
        return r
    t = 1.0 - cap_dist / edge_radius
    return r - max_reduction * t * t


def radial_rings(radius_limit: float):
    rings = [0.0]
    r = PARAMS["radial_spacing"]
    while r < radius_limit - 1.0e-9:
        rings.append(round(r, 8))
        r += PARAMS["radial_spacing"]
    if radius_limit > 1.0e-9 and abs(rings[-1] - radius_limit) > 1.0e-5:
        rings.append(radius_limit)
    return rings


def classify_specimen(r: float, z: float) -> str:
    r_norm = r / PARAMS["R"] if PARAMS["R"] else 0.0
    z_norm = z / PARAMS["H"] if PARAMS["H"] else 0.0
    cap_zone = z <= 0.015 or z >= PARAMS["H"] - 0.015
    edge = r_norm >= 0.82
    lateral = r_norm >= 0.82
    if r_norm <= 0.45 and 0.25 <= z_norm <= 0.75:
        return "measurement_core"
    if cap_zone and edge:
        return "edge_corner"
    if z <= 0.015:
        return "bottom_cap_zone"
    if z >= PARAMS["H"] - 0.015:
        return "top_cap_zone"
    if lateral:
        return "lateral_surface"
    return "interior"


def generate_layout():
    particles = []
    pid = 1
    dz = PARAMS["target_spacing"]
    nz = int(round(PARAMS["H"] / dz))
    for iz in range(nz + 1):
        z = min(PARAMS["H"], iz * dz)
        rlim = specimen_radius_limit(z)
        for ir, radius in enumerate(radial_rings(rlim)):
            phase = (0.37 * iz + 0.19 * ir) * PARAMS["angular_spacing"] / max(radius, PARAMS["angular_spacing"])
            ntheta = theta_count(radius)
            volume_weight = ring_particle_volume(radius, rlim, dz, ntheta)
            for x, y, theta in ring_points(radius, PARAMS["target_spacing"], PARAMS["angular_spacing"], phase):
                r = math.hypot(x, y)
                particles.append(
                    {
                        "id": pid,
                        "kind": "specimen",
                        "mk": 0,
                        "x": x,
                        "y": y,
                        "z": z,
                        "r": r,
                        "theta": math.atan2(y, x),
                        "z_over_H": z / PARAMS["H"],
                        "region": classify_specimen(r, z),
                        "volume_weight": volume_weight,
                    }
                )
                pid += 1

    platen_layers = [
        ("bottom_platen", 2, -PARAMS["platen_gap"] - PARAMS["platen_thickness"], -PARAMS["platen_gap"]),
        ("top_platen", 1, PARAMS["H"] + PARAMS["platen_gap"], PARAMS["H"] + PARAMS["platen_gap"] + PARAMS["platen_thickness"]),
    ]
    for kind, mk, z0, z1 in platen_layers:
        layer_count = max(2, int(round((z1 - z0) / PARAMS["target_spacing"])) + 1)
        for iz in range(layer_count):
            denom = max(1, layer_count - 1)
            z = z0 + (z1 - z0) * iz / denom
            for ir, radius in enumerate(radial_rings(PARAMS["platen_radius"])):
                phase = 0.13 * iz + 0.07 * ir
                ntheta = theta_count(radius)
                volume_weight = ring_particle_volume(radius, PARAMS["platen_radius"], PARAMS["target_spacing"], ntheta)
                for x, y, theta in ring_points(radius, PARAMS["target_spacing"], PARAMS["angular_spacing"], phase):
                    particles.append(
                        {
                            "id": pid,
                            "kind": kind,
                            "mk": mk,
                            "x": x,
                            "y": y,
                            "z": z,
                            "r": math.hypot(x, y),
                            "theta": math.atan2(y, x),
                            "z_over_H": "",
                            "region": kind,
                            "volume_weight": volume_weight,
                        }
                    )
                    pid += 1
    return particles


def wendland_weight(distance: float, h: float) -> float:
    q = distance / h
    if q >= 2.0:
        return 0.0
    return (1.0 - 0.5 * q) ** 4 * (2.0 * q + 1.0)


def compute_support_metrics(particles):
    specimen = [p for p in particles if p["kind"] == "specimen"]
    h = PARAMS["support_h_factor"] * PARAMS["target_spacing"]
    radius = 2.0 * h
    radius2 = radius * radius
    metrics = []
    for p in specimen:
        support = 0.0
        weighted_support = 0.0
        all_neighbors = 0
        specimen_neighbors = 0
        nearest = float("inf")
        for q in particles:
            if p["id"] == q["id"]:
                continue
            dx = p["x"] - q["x"]
            dy = p["y"] - q["y"]
            dz = p["z"] - q["z"]
            d2 = dx * dx + dy * dy + dz * dz
            if d2 < nearest:
                nearest = d2
            if d2 <= radius2:
                d = math.sqrt(d2)
                w = wendland_weight(d, h)
                support += w
                weighted_support += q["volume_weight"] * w
                all_neighbors += 1
                if q["kind"] == "specimen":
                    specimen_neighbors += 1
        metrics.append(
            {
                "id": p["id"],
                "region": p["region"],
                "r_over_R": p["r"] / PARAMS["R"],
                "z_over_H": p["z"] / PARAMS["H"],
                "support_proxy": support,
                "volume_weighted_support_proxy": weighted_support,
                "neighbor_count_all": all_neighbors,
                "neighbor_count_specimen": specimen_neighbors,
                "nearest_neighbor_distance": math.sqrt(nearest) if nearest < float("inf") else "",
            }
        )
    return metrics


def mean(values):
    values = [v for v in values if v != ""]
    return sum(values) / len(values) if values else 0.0


def stdev(values):
    values = [v for v in values if v != ""]
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def summarize_geometry(particles, support_metrics):
    by_region = defaultdict(list)
    for m in support_metrics:
        by_region[m["region"]].append(m)
    core = by_region["measurement_core"]
    cap = by_region["top_cap_zone"] + by_region["bottom_cap_zone"] + by_region["edge_corner"]
    edge = by_region["edge_corner"] + by_region["lateral_surface"]
    core_support = mean([m["support_proxy"] for m in core])
    core_weighted_support = mean([m["volume_weighted_support_proxy"] for m in core])
    core_neighbors = mean([m["neighbor_count_specimen"] for m in core])

    quality = [
        {"metric": "specimen_count", "value": sum(1 for p in particles if p["kind"] == "specimen"), "units": "particles"},
        {"metric": "top_platen_count", "value": sum(1 for p in particles if p["kind"] == "top_platen"), "units": "particles"},
        {"metric": "bottom_platen_count", "value": sum(1 for p in particles if p["kind"] == "bottom_platen"), "units": "particles"},
        {"metric": "measurement_core_count", "value": len(core), "units": "particles"},
        {"metric": "edge_corner_count", "value": len(by_region["edge_corner"]), "units": "particles"},
        {"metric": "core_support_mean", "value": core_support, "units": "proxy"},
        {"metric": "edge_support_mean", "value": mean([m["support_proxy"] for m in edge]), "units": "proxy"},
        {"metric": "cap_support_mean", "value": mean([m["support_proxy"] for m in cap]), "units": "proxy"},
        {"metric": "core_volume_weighted_support_mean", "value": core_weighted_support, "units": "weighted_proxy"},
        {"metric": "edge_volume_weighted_support_mean", "value": mean([m["volume_weighted_support_proxy"] for m in edge]), "units": "weighted_proxy"},
        {"metric": "cap_volume_weighted_support_mean", "value": mean([m["volume_weighted_support_proxy"] for m in cap]), "units": "weighted_proxy"},
        {
            "metric": "edge_support_core_ratio",
            "value": mean([m["support_proxy"] for m in edge]) / core_support if core_support else "",
            "units": "ratio",
        },
        {
            "metric": "cap_support_core_ratio",
            "value": mean([m["support_proxy"] for m in cap]) / core_support if core_support else "",
            "units": "ratio",
        },
        {
            "metric": "edge_volume_weighted_support_core_ratio",
            "value": mean([m["volume_weighted_support_proxy"] for m in edge]) / core_weighted_support
            if core_weighted_support
            else "",
            "units": "ratio",
        },
        {
            "metric": "cap_volume_weighted_support_core_ratio",
            "value": mean([m["volume_weighted_support_proxy"] for m in cap]) / core_weighted_support
            if core_weighted_support
            else "",
            "units": "ratio",
        },
        {"metric": "core_specimen_neighbor_mean", "value": core_neighbors, "units": "particles"},
        {"metric": "edge_specimen_neighbor_mean", "value": mean([m["neighbor_count_specimen"] for m in edge]), "units": "particles"},
        {"metric": "cap_specimen_neighbor_mean", "value": mean([m["neighbor_count_specimen"] for m in cap]), "units": "particles"},
        {
            "metric": "nearest_neighbor_cv",
            "value": stdev([m["nearest_neighbor_distance"] for m in support_metrics])
            / mean([m["nearest_neighbor_distance"] for m in support_metrics]),
            "units": "ratio",
        },
        {"metric": "outer_ring_angular_gap_cv", "value": outer_ring_gap_cv(particles), "units": "ratio"},
        {"metric": "platen_contamination_in_core", "value": 0, "units": "particles"},
    ]
    return quality


def outer_ring_gap_cv(particles):
    specimen = [p for p in particles if p["kind"] == "specimen"]
    by_z = defaultdict(list)
    for p in specimen:
        by_z[round(p["z"], 5)].append(p)
    cvs = []
    for pts in by_z.values():
        max_r = max(p["r"] for p in pts)
        outer = [p for p in pts if p["r"] >= max_r - 0.001]
        if len(outer) < 4:
            continue
        angles = sorted((p["theta"] + 2.0 * math.pi) % (2.0 * math.pi) for p in outer)
        gaps = []
        for i, angle in enumerate(angles):
            nxt = angles[(i + 1) % len(angles)]
            if i == len(angles) - 1:
                nxt += 2.0 * math.pi
            gaps.append(nxt - angle)
        cvs.append(stdev(gaps) / mean(gaps))
    return mean(cvs)


def write_csv(path: Path, rows, fieldnames=None):
    rows = list(rows)
    if not rows:
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_layout_comparison(quality):
    qmap = {row["metric"]: row["value"] for row in quality}
    generated = {
        "case": "M3o_radial_ring_smooth_edge_prototype",
        "layout": "External radial-ring fan-like specimen, geometry only",
        "specimen_count": qmap["specimen_count"],
        "edge_support_core_ratio": qmap["edge_support_core_ratio"],
        "edge_neighbor_mean": qmap["edge_specimen_neighbor_mean"],
        "cap_support_core_ratio": qmap["cap_support_core_ratio"],
        "cap_neighbor_mean": qmap["cap_specimen_neighbor_mean"],
        "max_return_status_minus3": "",
        "max_return_status_minus1": "",
        "solver_status": "not run; no direct point-cloud import path confirmed",
    }
    return BASELINE_COMPARISON + [generated]


def plot_layout_rz(particles):
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = {"specimen": "#2f80ed", "top_platen": "#666666", "bottom_platen": "#666666"}
    for kind in ["specimen", "top_platen", "bottom_platen"]:
        pts = [p for p in particles if p["kind"] == kind]
        ax.scatter([p["r"] for p in pts], [p["z"] for p in pts], s=8, alpha=0.8, label=kind, c=colors[kind])
        if kind == "specimen":
            ax.scatter([-p["r"] for p in pts], [p["z"] for p in pts], s=8, alpha=0.8, c=colors[kind])
    ax.set_xlabel("signed radial coordinate (m)")
    ax.set_ylabel("z (m)")
    ax.set_title("M3o radial-ring smooth-edge layout, r-z view")
    ax.legend(loc="upper right")
    ax.set_aspect("equal", adjustable="box")
    save_figure(fig, "m3o_layout_preview_rz")


def plot_layout_xy(particles):
    specimen = [p for p in particles if p["kind"] == "specimen" and abs(p["z"] - PARAMS["H"] / 2.0) < 0.006]
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.scatter([p["x"] for p in specimen], [p["y"] for p in specimen], s=14, c="#2f80ed", alpha=0.85)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("M3o fan-like specimen mid-height x-y view")
    ax.set_aspect("equal", adjustable="box")
    save_figure(fig, "m3o_layout_preview_xy")


def plot_support_hist(support_metrics):
    regions = ["measurement_core", "edge_corner", "lateral_surface", "top_cap_zone", "bottom_cap_zone"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for region in regions:
        vals = [m["support_proxy"] for m in support_metrics if m["region"] == region]
        if vals:
            ax.hist(vals, bins=16, alpha=0.45, label=region)
    ax.set_xlabel("support proxy")
    ax.set_ylabel("particle count")
    ax.set_title("Support proxy distribution by region")
    ax.legend(fontsize=8)
    save_figure(fig, "m3o_support_proxy_distribution")


def plot_neighbor_hist(support_metrics):
    regions = ["measurement_core", "edge_corner", "lateral_surface", "top_cap_zone", "bottom_cap_zone"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for region in regions:
        vals = [m["neighbor_count_specimen"] for m in support_metrics if m["region"] == region]
        if vals:
            ax.hist(vals, bins=16, alpha=0.45, label=region)
    ax.set_xlabel("specimen neighbor count proxy")
    ax.set_ylabel("particle count")
    ax.set_title("Specimen neighbor count by region")
    ax.legend(fontsize=8)
    save_figure(fig, "m3o_neighbor_count_distribution")


def plot_comparison(comparison):
    labels = [row["case"].replace("_", "\n") for row in comparison]
    edge_support = [float(row["edge_support_core_ratio"]) for row in comparison]
    edge_neighbor = [float(row["edge_neighbor_mean"]) for row in comparison]
    x = list(range(len(labels)))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    axes[0].bar(x, edge_support, color=["#999999", "#999999", "#2f80ed"])
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    axes[0].set_ylabel("edge support / core support")
    axes[0].set_title("Edge support comparison")
    axes[1].bar(x, edge_neighbor, color=["#999999", "#999999", "#2f80ed"])
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    axes[1].set_ylabel("edge specimen-neighbor mean")
    axes[1].set_title("Edge neighbor comparison")
    fig.tight_layout()
    save_figure(fig, "m3o_edge_cap_support_comparison")


def plot_cartesian_comparison(comparison):
    labels = [row["case"].replace("_", "\n") for row in comparison]
    specimen_count = [float(row["specimen_count"]) for row in comparison]
    max_minus3 = [float(row["max_return_status_minus3"] or 0) for row in comparison]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    x = list(range(len(labels)))
    axes[0].bar(x, specimen_count, color=["#999999", "#999999", "#2f80ed"])
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    axes[0].set_ylabel("specimen particles")
    axes[0].set_title("Particle count")
    axes[1].bar(x, max_minus3, color=["#999999", "#999999", "#2f80ed"])
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    axes[1].set_ylabel("max ReturnStatus=-3")
    axes[1].set_title("Solver status comparison\n(M3o geometry only)")
    fig.tight_layout()
    save_figure(fig, "m3o_cartesian_comparison")


def save_figure(fig, stem: str):
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{stem}.svg")
    fig.savefig(FIG_DIR / f"{stem}.png", dpi=180)
    plt.close(fig)


def main():
    particles = generate_layout()
    support_metrics = compute_support_metrics(particles)
    quality = summarize_geometry(particles, support_metrics)
    comparison = build_layout_comparison(quality)

    write_csv(ROOT / "m3o_smooth_fan_layout_particles.csv", particles)
    write_csv(ROOT / "m3o_support_neighbor_metrics.csv", support_metrics)
    write_csv(ROOT / "m3o_geometry_quality_metrics.csv", quality)
    write_csv(ROOT / "m3o_layout_comparison.csv", comparison)
    (ROOT / "m3o_smooth_fan_layout_params.json").write_text(json.dumps(PARAMS, indent=2), encoding="utf-8")

    plot_layout_rz(particles)
    plot_layout_xy(particles)
    plot_support_hist(support_metrics)
    plot_neighbor_hist(support_metrics)
    plot_comparison(comparison)
    plot_cartesian_comparison(comparison)

    qmap = {row["metric"]: row["value"] for row in quality}
    print("Generated M3o radial-ring smooth-edge prototype")
    print(f"  specimen_count={qmap['specimen_count']}")
    print(f"  top_platen_count={qmap['top_platen_count']}")
    print(f"  bottom_platen_count={qmap['bottom_platen_count']}")
    print(f"  edge_support_core_ratio={qmap['edge_support_core_ratio']:.6f}")
    print(f"  cap_support_core_ratio={qmap['cap_support_core_ratio']:.6f}")
    print(f"  edge_specimen_neighbor_mean={qmap['edge_specimen_neighbor_mean']:.3f}")
    print("  solver_run=not_run")


if __name__ == "__main__":
    main()
