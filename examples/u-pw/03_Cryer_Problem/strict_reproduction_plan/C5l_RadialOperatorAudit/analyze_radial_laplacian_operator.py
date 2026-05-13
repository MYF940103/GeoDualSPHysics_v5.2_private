#!/usr/bin/env python3
"""C5l radial Laplacian and shell-exchange audit for strict Cryer.

Postprocessing only: no source edits, no solver run, no GPU. The script
reconstructs static material sphere clouds from committed geometry metrics,
evaluates manufactured radial fields with the CPU material-material
LapPorePress formula, and audits retained pressure-only diffusion CSVs with a
radial shell finite-volume balance.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
STRICT = HERE.parent
FIG = HERE / "figures"
FIG.mkdir(parents=True, exist_ok=True)

C5I = STRICT / "C5i_SphericalDiffusionFluxCalibration"
C5J = STRICT / "C5j_MLSBoundaryFlux"
C5K = STRICT / "C5k_RadialShellFluxBoundary"
C5H = STRICT / "C5h_HigherResolutionSphere"

RADIUS = 0.05
DOMAIN_HALF = 0.16
HDP = 1.8
SHELL_BINS = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0])
AUDIT_BINS = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0, 1.12])


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def f(row: dict[str, str], key: str, default: float = float("nan")) -> float:
    try:
        val = row.get(key, "")
        return float(val) if val not in ("", None) else default
    except ValueError:
        return default


def b(row: dict[str, str], key: str) -> bool:
    return str(row.get(key, "")).strip().lower() == "true"


def write_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                keys.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as fcsv:
        wr = csv.DictWriter(fcsv, fieldnames=keys)
        wr.writeheader()
        wr.writerows(rows)


def read_cv() -> float:
    rows = read_rows(C5I / "c5i_reference_config.csv")
    return f(rows[0], "cv")


CV = read_cv()


@dataclass
class CloudSpec:
    label: str
    dp: float
    material_count: int
    surface_count_r085: int
    max_radius: float
    surface_roughness_std: float
    mean_surface_radius_error: float
    max_surface_radius_abs_error: float
    selected_boundary_particle_count: float
    material_boundary_pair_count: float


def load_cloud_specs() -> list[CloudSpec]:
    geom = read_rows(C5I / "c5i_geometry_flux_error_metrics.csv")
    sphere = read_rows(C5H / "c5h_sphere_quality_metrics.csv")
    wanted = [
        ("mode4_normalized_dp010", "coarse_diffusion", "dp=0.010"),
        ("mode4_normalized_dp008", "finer_diffusion", "dp=0.008"),
        ("mode4_normalized_dp0065", "higher_diffusion", "dp=0.0065"),
    ]
    out: list[CloudSpec] = []
    for case, sphere_case, label in wanted:
        row = next(r for r in geom if r["case_label"] == case)
        srow = next(r for r in sphere if r["case"] == sphere_case)
        out.append(
            CloudSpec(
                label=label,
                dp=f(row, "configured_dp"),
                material_count=int(f(row, "material_particle_count")),
                surface_count_r085=int(f(srow, "surface_count_r085")),
                max_radius=f(srow, "max_radius"),
                surface_roughness_std=f(row, "surface_roughness_std"),
                mean_surface_radius_error=f(row, "mean_surface_radius_error"),
                max_surface_radius_abs_error=f(row, "max_surface_radius_abs_error"),
                selected_boundary_particle_count=f(row, "selected_boundary_particle_count"),
                material_boundary_pair_count=f(row, "material_boundary_pair_count"),
            )
        )
    return out


def lattice_points(dp: float, offset_factor: float) -> np.ndarray:
    xs = np.arange(-DOMAIN_HALF + offset_factor * dp, DOMAIN_HALF + 1.0e-12, dp)
    return np.array([(x, y, z) for x in xs for y in xs for z in xs], dtype=float)


def cloud_score(r: np.ndarray, spec: CloudSpec) -> float:
    surf = r > 0.85 * RADIUS
    if not np.any(surf):
        return 1.0e99
    return (
        abs(float(np.max(r)) - spec.max_radius)
        + abs(int(np.sum(surf)) - spec.surface_count_r085) / 1000.0
        + abs(float(np.std(r[surf] - RADIUS)) - spec.surface_roughness_std)
        + abs(float(np.mean(r[surf] - RADIUS)) - spec.mean_surface_radius_error)
        + abs(float(np.max(np.abs(r[surf] - RADIUS))) - spec.max_surface_radius_abs_error)
    )


def reconstruct_cloud(spec: CloudSpec) -> tuple[np.ndarray, float]:
    best_score = 1.0e99
    best_pts: np.ndarray | None = None
    best_offset = 0.0
    for off in np.linspace(-0.5, 0.5, 81):
        pts = lattice_points(spec.dp, float(off))
        r = np.linalg.norm(pts, axis=1)
        idx = np.argsort(r)[: spec.material_count]
        cand = pts[idx]
        score = cloud_score(np.linalg.norm(cand, axis=1), spec)
        if score < best_score:
            best_score = score
            best_pts = cand
            best_offset = float(off)
    if best_pts is None:
        raise RuntimeError(f"Could not reconstruct cloud for {spec.label}")
    return best_pts, best_offset


def wendland_fac(rr2: np.ndarray, h: float) -> np.ndarray:
    rad = np.sqrt(rr2)
    qq = rad / h
    wqq1 = 1.0 - 0.5 * qq
    bwen = -2.08891 / (h**4)
    return bwen * qq * (wqq1**3) / rad


def sph_laplacian_material(pts: np.ndarray, u: np.ndarray, dp: float) -> np.ndarray:
    h = HDP * dp
    kernel_size2 = (2.0 * h) ** 2
    vol = dp**3
    out = np.zeros(len(pts), dtype=float)
    for i in range(len(pts)):
        d = pts[i] - pts
        rr2 = np.einsum("ij,ij->i", d, d)
        mask = (rr2 <= kernel_size2) & (rr2 > 1.0e-20)
        if not np.any(mask):
            continue
        fac = wendland_fac(rr2[mask], h)
        dotrgrad = rr2[mask] * fac
        out[i] = np.sum(2.0 * vol * (u[i] - u[mask]) * dotrgrad / (rr2[mask] + 1.0e-18))
    return out


def manufactured_fields(r: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    safe_r = np.maximum(r, 1.0e-12)
    x = r / RADIUS
    return {
        "constant": (np.ones_like(r), np.zeros_like(r), np.ones_like(r, dtype=bool)),
        "quadratic_r2": (r * r, np.full_like(r, 6.0), np.ones_like(r, dtype=bool)),
        "linear_gap": (RADIUS - r, -2.0 / safe_r, r >= 0.10 * RADIUS),
        "smooth_quartic": ((1.0 - x * x) ** 2, -12.0 / (RADIUS**2) + 20.0 * (r * r) / (RADIUS**4), np.ones_like(r, dtype=bool)),
    }


def audit_manufactured() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    particle_rows: list[dict] = []
    shell_rows: list[dict] = []
    summary_rows: list[dict] = []
    cloud_rows: list[dict] = []
    for spec in load_cloud_specs():
        pts, offset = reconstruct_cloud(spec)
        r = np.linalg.norm(pts, axis=1)
        surf = r > 0.85 * RADIUS
        cloud_rows.append(
            {
                "label": spec.label,
                "dp": spec.dp,
                "material_particle_count": spec.material_count,
                "reconstruction_offset_factor": offset,
                "max_radius": float(np.max(r)),
                "surface_count_r085": int(np.sum(surf)),
                "surface_roughness_std": float(np.std(r[surf] - RADIUS)),
                "mean_surface_radius_error": float(np.mean(r[surf] - RADIUS)),
                "max_surface_radius_abs_error": float(np.max(np.abs(r[surf] - RADIUS))),
                "selected_boundary_particle_count": spec.selected_boundary_particle_count,
                "material_boundary_pair_count": spec.material_boundary_pair_count,
            }
        )
        for field, (u, exact, valid) in manufactured_fields(r).items():
            lap = sph_laplacian_material(pts, u, spec.dp)
            err = lap - exact
            for a, bb in zip(AUDIT_BINS[:-1], AUDIT_BINS[1:]):
                mask = (r >= a * RADIUS) & (r < bb * RADIUS) & valid
                if not np.any(mask):
                    continue
                shell_rows.append(
                    {
                        "label": spec.label,
                        "dp": spec.dp,
                        "field": field,
                        "r_over_R_min": a,
                        "r_over_R_max": bb,
                        "count": int(np.sum(mask)),
                        "lap_mean": float(np.mean(lap[mask])),
                        "exact_mean": float(np.mean(exact[mask])),
                        "bias": float(np.mean(err[mask])),
                        "rmse": float(np.sqrt(np.mean(err[mask] ** 2))),
                        "p95_abs_error": float(np.percentile(np.abs(err[mask]), 95)),
                        "max_abs_error": float(np.max(np.abs(err[mask]))),
                    }
                )
            for name, mask in {
                "global": valid,
                "interior_r_lt_080R": (r < 0.80 * RADIUS) & valid,
                "near_boundary_r_ge_095R": (r >= 0.95 * RADIUS) & valid,
            }.items():
                if not np.any(mask):
                    continue
                summary_rows.append(
                    {
                        "label": spec.label,
                        "dp": spec.dp,
                        "field": field,
                        "region": name,
                        "rmse": float(np.sqrt(np.mean(err[mask] ** 2))),
                        "bias": float(np.mean(err[mask])),
                        "p95_abs_error": float(np.percentile(np.abs(err[mask]), 95)),
                        "max_abs_error": float(np.max(np.abs(err[mask]))),
                    }
                )
            order = np.argsort(r)
            step = max(1, len(order) // 400)
            for idx in order[::step]:
                particle_rows.append(
                    {
                        "label": spec.label,
                        "dp": spec.dp,
                        "field": field,
                        "r_over_R": float(r[idx] / RADIUS),
                        "lap": float(lap[idx]),
                        "exact": float(exact[idx]),
                        "error": float(err[idx]),
                        "valid": bool(valid[idx]),
                    }
                )
    return particle_rows, shell_rows, summary_rows, cloud_rows


def load_radial_profiles() -> list[dict]:
    rows: list[dict] = []
    for row in read_rows(C5I / "c5i_radial_bin_profiles.csv"):
        if row["case_label"] not in {"mode4_normalized_dp010", "mode4_normalized_dp008", "mode4_normalized_dp0065"}:
            continue
        rows.append(
            {
                "case": row["case_label"],
                "source": "C5i/C5h mode4 normalized",
                "dp": f(row, "configured_dp"),
                "time": f(row, "time"),
                "r_over_R_min": f(row, "r_over_R_min"),
                "r_over_R_max": f(row, "r_over_R_max"),
                "r_over_R_mid": f(row, "r_over_R_mid"),
                "count": f(row, "sph_count"),
                "mean_pressure": f(row, "sph_mean_pressure"),
                "fv_mean_pressure": f(row, "fv_mean_pressure"),
            }
        )
    for path, source in [(C5J / "c5j_radial_bin_profiles.csv", "C5j mode5 MLS"), (C5K / "c5k_radial_bin_profiles.csv", "C5k mode6 shell")]:
        for row in read_rows(path):
            case = row["case"]
            rows.append(
                {
                    "case": case,
                    "source": source,
                    "dp": 0.008 if "dp008" in case else 0.010,
                    "time": f(row, "time"),
                    "r_over_R_min": f(row, "r_over_R_min"),
                    "r_over_R_max": f(row, "r_over_R_max"),
                    "r_over_R_mid": f(row, "r_over_R_mid"),
                    "count": f(row, "excess_count"),
                    "mean_pressure": f(row, "excess_mean"),
                    "fv_mean_pressure": float("nan"),
                }
            )
    return [r for r in rows if r["r_over_R_min"] >= 0.0 and r["r_over_R_max"] <= 1.0]


def fv_reference_by_shell() -> list[dict]:
    grouped: dict[float, list[dict]] = defaultdict(list)
    for row in read_rows(C5I / "c5i_fv_reference_profiles.csv"):
        grouped[f(row, "time")].append(row)
    out: list[dict] = []
    for time, rows in grouped.items():
        rr = np.array([f(r, "r") for r in rows])
        uu = np.array([f(r, "pressure") for r in rows])
        for a, bb in zip(SHELL_BINS[:-1], SHELL_BINS[1:]):
            mask = (rr >= a * RADIUS) & (rr <= bb * RADIUS)
            if np.sum(mask) < 2:
                continue
            out.append(
                {
                    "time": time,
                    "r_over_R_min": a,
                    "r_over_R_max": bb,
                    "r_over_R_mid": 0.5 * (a + bb),
                    "fv_shell_mean": float(np.average(uu[mask], weights=rr[mask] ** 2)),
                }
            )
    return out


def groupby(rows: list[dict], key: str) -> dict:
    out: dict = defaultdict(list)
    for row in rows:
        out[row[key]].append(row)
    return out


def compute_shell_balance(radial: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    storage_rows: list[dict] = []
    flux_rows: list[dict] = []
    metric_rows: list[dict] = []
    for case, crows in groupby(radial, "case").items():
        crows = sorted(crows, key=lambda r: (r["time"], r["r_over_R_min"]))
        dp = float(crows[0]["dp"])
        source = str(crows[0]["source"])
        by_time = groupby(crows, "time")
        times = sorted(by_time.keys())
        if len(times) < 2:
            continue
        shell0 = sorted(by_time[times[0]], key=lambda r: r["r_over_R_min"])
        mids = np.array([r["r_over_R_mid"] * RADIUS for r in shell0], dtype=float)
        rmins = np.array([r["r_over_R_min"] for r in shell0], dtype=float)
        rmaxs = np.array([r["r_over_R_max"] for r in shell0], dtype=float)
        volumes = np.array([r["count"] * (dp**3) for r in shell0], dtype=float)
        for i in range(len(times) - 1):
            t0, t1 = times[i], times[i + 1]
            dt = t1 - t0
            if dt <= 0:
                continue
            g0 = sorted(by_time[t0], key=lambda r: r["r_over_R_min"])
            g1 = sorted(by_time[t1], key=lambda r: r["r_over_R_min"])
            if len(g0) != len(shell0) or len(g1) != len(shell0):
                continue
            u0 = np.array([r["mean_pressure"] for r in g0], dtype=float)
            u1 = np.array([r["mean_pressure"] for r in g1], dtype=float)
            u = 0.5 * (u0 + u1)
            dSdt = (u1 * volumes - u0 * volumes) / dt
            q = [0.0]
            for k in range(len(u) - 1):
                dr = mids[k + 1] - mids[k]
                area = 4.0 * math.pi * ((rmaxs[k] * RADIUS) ** 2)
                q.append(CV * area * (u[k] - u[k + 1]) / max(dr, 1.0e-12))
            gap = max(RADIUS - mids[-1], 0.5 * dp)
            q.append(CV * 4.0 * math.pi * RADIUS * RADIUS * u[-1] / gap)
            tm = 0.5 * (t0 + t1)
            for iface, val in enumerate(q):
                flux_rows.append(
                    {
                        "case": case,
                        "source": source,
                        "dp": dp,
                        "time_mid": tm,
                        "interface_index": iface,
                        "interface_r_over_R": 0.0 if iface == 0 else (1.0 if iface == len(q) - 1 else rmaxs[iface - 1]),
                        "fv_gradient_flux": float(val),
                    }
                )
            for k in range(len(u)):
                residual = dSdt[k] + q[k + 1] - q[k]
                storage_rows.append(
                    {
                        "case": case,
                        "source": source,
                        "dp": dp,
                        "time_mid": tm,
                        "shell_index": k,
                        "r_over_R_min": rmins[k],
                        "r_over_R_max": rmaxs[k],
                        "shell_volume": float(volumes[k]),
                        "pressure_mean_mid": float(u[k]),
                        "storage_derivative": float(dSdt[k]),
                        "flux_in": float(q[k]),
                        "flux_out": float(q[k + 1]),
                        "residual": float(residual),
                        "abs_residual": float(abs(residual)),
                    }
                )
        sdf = [r for r in storage_rows if r["case"] == case]
        fdf = [r for r in flux_rows if r["case"] == case]
        absres = np.array([r["abs_residual"] for r in sdf], dtype=float)
        outer = np.array([r["abs_residual"] for r in sdf if r["r_over_R_min"] >= 0.95], dtype=float)
        middle = np.array([r["abs_residual"] for r in sdf if r["r_over_R_min"] >= 0.4 and r["r_over_R_max"] <= 0.9], dtype=float)
        bflux = np.array([abs(r["fv_gradient_flux"]) for r in fdf if r["interface_r_over_R"] == 1.0], dtype=float)
        scale = float(np.median(bflux)) if len(bflux) else 1.0
        if scale <= 1.0e-12:
            scale = 1.0
        metric_rows.append(
            {
                "case": case,
                "source": source,
                "dp": dp,
                "shell_residual_rmse": float(np.sqrt(np.mean(absres**2))),
                "shell_residual_p95_abs": float(np.percentile(absres, 95)),
                "outer_shell_residual_p95_abs": float(np.percentile(outer, 95)) if len(outer) else float("nan"),
                "middle_shell_residual_p95_abs": float(np.percentile(middle, 95)) if len(middle) else float("nan"),
                "median_boundary_flux_abs": scale,
                "normalized_residual_p95": float(np.percentile(absres, 95) / scale),
            }
        )
    return storage_rows, flux_rows, metric_rows


def lookup_summary(summary: list[dict], label: str, field: str, region: str, metric: str) -> float:
    for row in summary:
        if row["label"] == label and row["field"] == field and row["region"] == region:
            return float(row[metric])
    return float("nan")


def boundary_diagnosis() -> tuple[list[dict], str]:
    rows: list[dict] = []
    for row in read_rows(C5I / "c5i_sph_pressure_only_summary.csv"):
        if "mode4_normalized" not in row["case_label"]:
            continue
        rows.append(
            {
                "case": row["case_label"],
                "mode": "4 normalized",
                "dp": f(row, "configured_dp"),
                "median_flux_ratio": f(row, "median_flux_ratio"),
                "final_flux_ratio": f(row, "final_flux_ratio"),
                "surface_shell_rmse": f(row, "surface_shell_pressure_rmse"),
                "center_rmse": f(row, "center_pressure_rmse"),
                "flux_reversal": b(row, "flux_reversal"),
                "diagnosis": "over-strong nonuniform Robin-like boundary; dp=0.0065 adds flux reversal",
            }
        )
    for row in read_rows(C5J / "c5j_gate_metrics.csv"):
        rows.append(
            {
                "case": row["case"],
                "mode": "5 MLS",
                "dp": f(row, "configured_dp"),
                "median_flux_ratio": f(row, "median_flux_ratio"),
                "final_flux_ratio": f(row, "final_flux_ratio"),
                "surface_shell_rmse": f(row, "surface_shell_pressure_rmse"),
                "center_rmse": f(row, "center_pressure_rmse"),
                "flux_reversal": b(row, "flux_reversal"),
                "diagnosis": "local MLS/shell flux improves some center-volume metrics but leaves surface shell high",
            }
        )
    for row in read_rows(C5K / "c5k_gate_metrics.csv"):
        rows.append(
            {
                "case": row["case"],
                "mode": "6 radial shell",
                "dp": f(row, "configured_dp"),
                "median_flux_ratio": f(row, "median_flux_ratio"),
                "final_flux_ratio": f(row, "final_flux_ratio"),
                "surface_shell_rmse": f(row, "surface_shell_pressure_rmse"),
                "center_rmse": f(row, "center_pressure_rmse"),
                "flux_reversal": b(row, "flux_reversal"),
                "diagnosis": "integrated boundary sink can match global flux locally, but shell redistribution is inconsistent",
            }
        )
    md = """# C5l Boundary Type Diagnosis

C5l separates boundary flux strength from radial operator consistency. The
static manufactured-field audit shows that the material-material
`LapPorePress` operator is consistent in the interior but has a large
near-boundary bias for curved radial fields. The pressure-only shell audit
then shows that matching a global or boundary flux ratio is not sufficient
when shell-to-shell redistribution is wrong.

## Classification

- Mode 4 normalized remains an over-strong, nonuniform Robin-like boundary.
- Mode 5 is an over-strong shell-flux boundary with poor radial profile consistency.
- Mode 6 is a radial FV boundary sink with inconsistent shell redistribution; it is not a validated true Dirichlet operator.

## Main Diagnosis

The current strict route is best described as an inconsistent near-boundary
radial Laplacian / shell-exchange problem. The boundary flux at `R` is only one
part of the failure. Surface-shell pressure remains high because the outer
shell, adjacent shell, and interior storage exchange do not reproduce the
finite-volume radial diffusion balance.
"""
    return rows, md


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIG / f"{name}.png", dpi=180)
    plt.savefig(FIG / f"{name}.svg")
    plt.close()


def plot_outputs(particles: list[dict], shell_err: list[dict], summary: list[dict], clouds: list[dict], radial: list[dict], flux: list[dict], residual: list[dict], bdiag: list[dict]) -> None:
    plt.figure(figsize=(7.2, 4.4))
    for label in sorted({r["label"] for r in particles}):
        xs = [r["r_over_R"] for r in particles if r["label"] == label and r["field"] == "constant" and r["valid"]]
        ys = [abs(r["error"]) for r in particles if r["label"] == label and r["field"] == "constant" and r["valid"]]
        plt.scatter(xs, ys, s=8, alpha=0.5, label=label)
    plt.yscale("symlog", linthresh=1.0e-14)
    plt.xlabel("r/R")
    plt.ylabel("|material-only Laplacian residual|")
    plt.title("Constant-field LapPorePress residual")
    plt.legend()
    savefig("c5l_constant_laplacian_residual_vs_radius")

    plt.figure(figsize=(7.2, 4.4))
    for label in sorted({r["label"] for r in shell_err}):
        rows = [r for r in shell_err if r["label"] == label and r["field"] == "quadratic_r2"]
        rows.sort(key=lambda r: r["r_over_R_min"])
        plt.plot([0.5 * (r["r_over_R_min"] + r["r_over_R_max"]) for r in rows], [r["bias"] for r in rows], marker="o", label=label)
    plt.axhline(0, color="k", lw=0.8)
    plt.xlabel("r/R")
    plt.ylabel("mean error in Lap(r^2), exact=6")
    plt.title("Quadratic radial Laplacian error")
    plt.legend()
    savefig("c5l_quadratic_laplacian_error_vs_radius")

    plt.figure(figsize=(8.0, 4.6))
    keep = sorted(residual, key=lambda r: r["normalized_residual_p95"], reverse=True)[:8]
    plt.barh([r["case"] for r in keep], [r["normalized_residual_p95"] for r in keep])
    plt.xlabel("p95 |shell residual| / median |boundary flux|")
    plt.title("Shell storage balance residual")
    savefig("c5l_shell_storage_balance_residual")

    plt.figure(figsize=(8.0, 4.6))
    for case in ["mode4_normalized_dp0065", "mode6_shell_dp008", "mode6_shell_dp010", "mode5_mls_dp010"]:
        rows = [r for r in flux if r["case"] == case and r["interface_r_over_R"] in (0.8, 0.9, 0.95, 1.0)]
        by_t: dict[float, float] = defaultdict(float)
        for r in rows:
            by_t[r["time_mid"]] += r["fv_gradient_flux"]
        if by_t:
            xs = sorted(by_t)
            plt.plot(xs, [by_t[x] for x in xs], marker="o", label=case)
    plt.axhline(0, color="k", lw=0.8)
    plt.xlabel("time [s]")
    plt.ylabel("sum outer-interface FV-gradient flux [Pa m3/s]")
    plt.title("Outer inter-shell flux diagnostic")
    plt.legend(fontsize=8)
    savefig("c5l_inter_shell_flux_vs_time")

    ref = fv_reference_by_shell()
    plt.figure(figsize=(7.4, 4.6))
    selected = {"mode4_normalized_dp010", "mode4_normalized_dp0065", "mode5_mls_dp010", "mode6_shell_dp010", "mode6_shell_dp008"}
    for case in selected:
        rows = [r for r in radial if r["case"] == case]
        if not rows:
            continue
        tf = max(r["time"] for r in rows)
        rows = sorted([r for r in rows if r["time"] == tf], key=lambda r: r["r_over_R_mid"])
        plt.plot([r["r_over_R_mid"] for r in rows], [r["mean_pressure"] for r in rows], marker="o", label=case)
    if ref:
        tf = max(r["time"] for r in ref)
        rr = sorted([r for r in ref if r["time"] == tf], key=lambda r: r["r_over_R_mid"])
        plt.plot([r["r_over_R_mid"] for r in rr], [r["fv_shell_mean"] for r in rr], "k--", lw=2, label="FV reference")
    plt.xlabel("r/R")
    plt.ylabel("shell mean pressure [Pa]")
    plt.title("Final shell pressure profiles vs FV")
    plt.legend(fontsize=8)
    savefig("c5l_shell_pressure_profiles_vs_fv")

    plt.figure(figsize=(7.2, 4.4))
    for field, marker in [("quadratic_r2", "o"), ("linear_gap", "s"), ("smooth_quartic", "^")]:
        rows = [r for r in summary if r["field"] == field and r["region"] == "near_boundary_r_ge_095R"]
        rows.sort(key=lambda r: r["dp"])
        plt.plot([r["dp"] for r in rows], [r["p95_abs_error"] for r in rows], marker=marker, label=field)
    plt.gca().invert_xaxis()
    plt.xlabel("dp [m]")
    plt.ylabel("near-boundary p95 |Laplacian error|")
    plt.title("Operator error vs dp")
    plt.legend()
    savefig("c5l_operator_error_vs_dp")

    rough_rows = []
    for c in clouds:
        err = lookup_summary(summary, c["label"], "quadratic_r2", "near_boundary_r_ge_095R", "p95_abs_error")
        rough_rows.append((c, err))
    plt.figure(figsize=(6.8, 4.4))
    plt.scatter([r[0]["surface_roughness_std"] for r in rough_rows], [r[1] for r in rough_rows], s=70)
    for c, err in rough_rows:
        plt.annotate(c["label"], (c["surface_roughness_std"], err))
    plt.xlabel("surface roughness std [m]")
    plt.ylabel("quadratic near-boundary p95 |error|")
    plt.title("Surface roughness vs operator error")
    savefig("c5l_surface_roughness_vs_operator_error")

    plt.figure(figsize=(6.8, 4.4))
    plt.scatter([r[0]["material_boundary_pair_count"] for r in rough_rows], [r[1] for r in rough_rows], s=70)
    for c, err in rough_rows:
        plt.annotate(c["label"], (c["material_boundary_pair_count"], err))
    plt.xlabel("mode-4 material-boundary pair count")
    plt.ylabel("quadratic near-boundary p95 |error|")
    plt.title("Boundary pair count vs operator error")
    savefig("c5l_boundary_pair_count_vs_operator_error")

    plt.figure(figsize=(8.0, 4.6))
    names = [r["case"].replace("mode4_normalized_", "m4_").replace("mode6_shell_", "m6_").replace("mode5_mls_", "m5_") for r in bdiag]
    x = np.arange(len(bdiag))
    plt.bar(x - 0.18, [r["median_flux_ratio"] for r in bdiag], width=0.36, label="median flux ratio")
    plt.bar(x + 0.18, [r["surface_shell_rmse"] / 300.0 for r in bdiag], width=0.36, label="surface RMSE / 300")
    plt.axhline(1, color="k", lw=0.8)
    plt.xticks(x, names, rotation=45, ha="right")
    plt.title("Mode 4/5/6 boundary type comparison")
    plt.legend()
    savefig("c5l_boundary_type_comparison")

    plt.figure(figsize=(7.2, 4.2))
    ax = plt.gca()
    for rr in SHELL_BINS:
        ax.add_patch(plt.Circle((0, 0), rr, fill=False, lw=1.0, color="0.45"))
    ax.annotate("Dirichlet p_b=0", xy=(1.0, 0.0), xytext=(1.25, 0.2), arrowprops=dict(arrowstyle="->"))
    ax.annotate("outer shell sink", xy=(0.975, 0.0), xytext=(0.55, -0.45), arrowprops=dict(arrowstyle="->"))
    ax.annotate("shell exchange must balance storage", xy=(0.75, 0.0), xytext=(-0.9, 0.55), arrowprops=dict(arrowstyle="->"))
    ax.set_aspect("equal")
    ax.set_xlim(-1.15, 1.55)
    ax.set_ylim(-1.15, 1.15)
    ax.axis("off")
    plt.title("C5l radial shell audit schematic")
    savefig("c5l_radial_shell_schematic")


def main() -> None:
    particles, shell_err, summary, clouds = audit_manufactured()
    radial = load_radial_profiles()
    balance, flux, residual = compute_shell_balance(radial)
    bdiag, bdiag_md = boundary_diagnosis()

    resolution_rows: list[dict] = []
    for c in clouds:
        row = dict(c)
        for field in ["constant", "quadratic_r2", "linear_gap", "smooth_quartic"]:
            row[f"{field}_interior_rmse"] = lookup_summary(summary, c["label"], field, "interior_r_lt_080R", "rmse")
            row[f"{field}_near_boundary_p95_abs_error"] = lookup_summary(summary, c["label"], field, "near_boundary_r_ge_095R", "p95_abs_error")
            row[f"{field}_near_boundary_bias"] = lookup_summary(summary, c["label"], field, "near_boundary_r_ge_095R", "bias")
        resolution_rows.append(row)

    write_rows(HERE / "c5l_manufactured_laplacian_particles_sample.csv", particles)
    write_rows(HERE / "c5l_manufactured_laplacian_by_shell.csv", shell_err)
    write_rows(HERE / "c5l_manufactured_laplacian_summary.csv", summary)
    write_rows(HERE / "c5l_reconstructed_cloud_metrics.csv", clouds)
    write_rows(HERE / "c5l_shell_storage_balance.csv", balance)
    write_rows(HERE / "c5l_inter_shell_flux.csv", flux)
    write_rows(HERE / "c5l_shell_residual_metrics.csv", residual)
    write_rows(HERE / "c5l_resolution_operator_error.csv", resolution_rows)
    write_rows(HERE / "c5l_shell_error_by_dp.csv", shell_err)
    write_rows(HERE / "c5l_boundary_type_diagnosis.csv", bdiag)
    (HERE / "c5l_boundary_type_diagnosis.md").write_text(bdiag_md, encoding="utf-8")

    plot_outputs(particles, shell_err, summary, clouds, radial, flux, residual, bdiag)
    print("C5l radial operator audit complete.")


if __name__ == "__main__":
    main()
