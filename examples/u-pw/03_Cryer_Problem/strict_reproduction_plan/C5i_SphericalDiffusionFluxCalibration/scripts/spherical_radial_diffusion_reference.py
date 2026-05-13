#!/usr/bin/env python3
"""C5i spherical pressure-only diffusion reference and SPH comparison.

The script is post-processing only. It solves the matching 1D radial
finite-volume reference problem and compares it with committed C5e/C5f/C5h
pressure-only diffusion CSV diagnostics.
"""

from __future__ import annotations

import csv
import math
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PLAN_ROOT = ROOT.parent
FIG_DIR = ROOT / "figures"
RADIAL_BINS = [
    (0.0, 0.2),
    (0.2, 0.4),
    (0.4, 0.6),
    (0.6, 0.8),
    (0.8, 0.9),
    (0.9, 0.95),
    (0.95, 1.0),
]


@dataclass(frozen=True)
class CaseSpec:
    label: str
    display: str
    source_stage: str
    metrics_path: Path
    radial_path: Path
    metrics_case: str
    radial_case: str
    resolution: str
    dp: float
    mode: int
    weighting: str
    boundary_family: str


def f(row: dict[str, object], key: str, default: float = float("nan")) -> float:
    value = row.get(key, default)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fp:
        return list(csv.DictReader(fp))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_xml_config() -> dict[str, float]:
    xml_path = (
        PLAN_ROOT
        / "C5h_HigherResolutionSphere"
        / "CaseCryer_PR_StrictSphere_C5h_HigherResDiffusionNormalized_Def.xml"
    )
    root = ET.parse(xml_path).getroot()

    def attr_float(xpath: str, attr: str, default: float) -> float:
        node = root.find(xpath)
        return float(node.attrib.get(attr, default)) if node is not None else default

    def parameter(key: str, default: float) -> float:
        for node in root.findall(".//parameter"):
            if node.attrib.get("key") == key:
                return float(node.attrib.get("value", default))
        return default

    radius = parameter("CurvedDrainedBoundaryRadius", 0.05)
    u0 = parameter("PorePressureExcessAmp", 1000.0)
    time_max = parameter("TimeMax", 0.006)
    time_out = parameter("TimeOut", 0.001)
    porosity = attr_float(".//Porosity0", "value", 0.3)
    hydraulic_conductivity = attr_float(".//HydraulicConductivity", "value", 1.0e-5)
    water_bulk_modulus = attr_float(".//WaterBulkModulus", "value", 2.0e6)
    water_density = attr_float(".//WaterDensity", "value", 1000.0)
    gx = parameter("HydraulicGravityX", 0.0)
    gy = parameter("HydraulicGravityY", 0.0)
    gz = parameter("HydraulicGravityZ", -9.81)
    gh = math.sqrt(gx * gx + gy * gy + gz * gz)
    cv = (water_bulk_modulus / porosity) * (
        hydraulic_conductivity / (water_density * gh)
    )
    return {
        "radius": radius,
        "u0": u0,
        "time_max": time_max,
        "time_out": time_out,
        "porosity": porosity,
        "hydraulic_conductivity": hydraulic_conductivity,
        "water_bulk_modulus": water_bulk_modulus,
        "water_density": water_density,
        "hydraulic_g": gh,
        "cv": cv,
    }


def build_cases() -> list[CaseSpec]:
    c5e = PLAN_ROOT / "C5e_BoundaryParticleDrained"
    c5f = PLAN_ROOT / "C5f_BoundaryParticleWeighting"
    c5h = PLAN_ROOT / "C5h_HigherResolutionSphere"
    return [
        CaseSpec(
            "mode3_shell_dp010",
            "mode 3 shell, dp=0.010",
            "C5e",
            c5e / "c5e_pressure_only_diffusion_metrics.csv",
            c5e / "c5e_radial_excess_profiles.csv",
            "diffusion_mode3_shell",
            "diffusion_mode3_shell",
            "coarse",
            0.010,
            3,
            "n/a",
            "mode3_shell",
        ),
        CaseSpec(
            "mode4_raw_dp010",
            "mode 4 raw, dp=0.010",
            "C5f",
            c5f / "c5f_pressure_only_diffusion_metrics.csv",
            c5f / "c5f_radial_excess_profiles.csv",
            "diffusion_raw",
            "diffusion_raw",
            "coarse",
            0.010,
            4,
            "raw",
            "mode4_raw",
        ),
        CaseSpec(
            "mode4_normalized_dp010",
            "mode 4 normalized, dp=0.010",
            "C5h",
            c5h / "c5h_pressure_only_diffusion_comparison.csv",
            c5h / "c5h_radial_profile_metrics.csv",
            "coarse_diffusion",
            "coarse_diffusion",
            "coarse",
            0.010,
            4,
            "normalized",
            "mode4_normalized",
        ),
        CaseSpec(
            "mode4_capped_dp010",
            "mode 4 capped diagnostic, dp=0.010",
            "C5f",
            c5f / "c5f_pressure_only_diffusion_metrics.csv",
            c5f / "c5f_radial_excess_profiles.csv",
            "diffusion_capped",
            "diffusion_capped",
            "coarse",
            0.010,
            4,
            "diagnostic_capped",
            "mode4_capped",
        ),
        CaseSpec(
            "mode4_normalized_dp008",
            "mode 4 normalized, dp=0.008",
            "C5h",
            c5h / "c5h_pressure_only_diffusion_comparison.csv",
            c5h / "c5h_radial_profile_metrics.csv",
            "finer_diffusion",
            "finer_diffusion",
            "finer",
            0.008,
            4,
            "normalized",
            "mode4_normalized",
        ),
        CaseSpec(
            "mode4_normalized_dp0065",
            "mode 4 normalized, dp=0.0065",
            "C5h",
            c5h / "c5h_pressure_only_diffusion_comparison.csv",
            c5h / "c5h_radial_profile_metrics.csv",
            "higher_diffusion",
            "higher_diffusion",
            "higher",
            0.0065,
            4,
            "normalized",
            "mode4_normalized",
        ),
    ]


def thomas(lower: np.ndarray, diag: np.ndarray, upper: np.ndarray, rhs: np.ndarray) -> np.ndarray:
    n = len(diag)
    c = upper.copy()
    d = rhs.copy()
    b = diag.copy()
    for i in range(1, n):
        m = lower[i - 1] / b[i - 1]
        b[i] -= m * c[i - 1]
        d[i] -= m * d[i - 1]
    x = np.empty(n)
    x[-1] = d[-1] / b[-1]
    for i in range(n - 2, -1, -1):
        x[i] = (d[i] - c[i] * x[i + 1]) / b[i]
    return x


def weighted_percentile(values: np.ndarray, weights: np.ndarray, percentile: float) -> float:
    order = np.argsort(values)
    v = values[order]
    w = weights[order]
    total = np.sum(w)
    if total <= 0:
        return float("nan")
    cutoff = percentile / 100.0 * total
    return float(v[np.searchsorted(np.cumsum(w), cutoff, side="left")])


def solve_reference(
    config: dict[str, float], output_times: np.ndarray, n_cells: int = 480
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    radius = config["radius"]
    cv = config["cv"]
    u0 = config["u0"]
    faces = np.linspace(0.0, radius, n_cells + 1)
    centers = 0.5 * (faces[:-1] + faces[1:])
    volumes = (faces[1:] ** 3 - faces[:-1] ** 3) / 3.0
    areas = faces**2

    lower = np.zeros(n_cells - 1)
    diag = np.zeros(n_cells)
    upper = np.zeros(n_cells - 1)
    for i in range(n_cells):
        if i > 0:
            coeff = cv * areas[i] / (volumes[i] * (centers[i] - centers[i - 1]))
            lower[i - 1] = coeff
            diag[i] -= coeff
        if i < n_cells - 1:
            coeff = cv * areas[i + 1] / (volumes[i] * (centers[i + 1] - centers[i]))
            upper[i] = coeff
            diag[i] -= coeff
        else:
            coeff = cv * areas[-1] / (volumes[i] * (radius - centers[i]))
            diag[i] -= coeff

    def apply_l(u: np.ndarray) -> np.ndarray:
        out = diag * u
        out[:-1] += upper * u[1:]
        out[1:] += lower * u[:-1]
        return out

    def shell_stats(u: np.ndarray, rmin_factor: float, rmax_factor: float) -> dict[str, float]:
        mask = (centers >= radius * rmin_factor) & (centers <= radius * rmax_factor)
        vals = u[mask]
        w = volumes[mask]
        if len(vals) == 0:
            return {"mean": float("nan"), "p95": float("nan"), "max": float("nan")}
        return {
            "mean": float(np.average(vals, weights=w)),
            "p95": weighted_percentile(vals, w, 95.0),
            "max": float(np.max(vals)),
        }

    all_times = np.unique(np.concatenate(([0.0], output_times)))
    all_times.sort()
    u = np.full(n_cells, u0, dtype=float)
    t_current = 0.0
    profile_rows: list[dict[str, object]] = []
    ts_rows: list[dict[str, object]] = []
    cumulative_flux = 0.0
    previous_flux = None
    previous_time = None
    max_dt = 1.0e-5

    for target_time in all_times:
        while t_current < target_time - 1.0e-14:
            dt = min(max_dt, target_time - t_current)
            rhs = u + 0.5 * dt * apply_l(u)
            u = thomas(-0.5 * dt * lower, 1.0 - 0.5 * dt * diag, -0.5 * dt * upper, rhs)
            t_current += dt

        surface_flux_density = cv * u[-1] / (radius - centers[-1])
        flux_integral = 4.0 * math.pi * radius * radius * surface_flux_density
        if previous_flux is not None and previous_time is not None:
            cumulative_flux += 0.5 * (previous_flux + flux_integral) * (target_time - previous_time)
        previous_flux = flux_integral
        previous_time = target_time

        shell_095 = shell_stats(u, 0.95, 1.0)
        shell_090 = shell_stats(u, 0.90, 1.0)
        volume_mean = float(np.average(u, weights=volumes))
        stored_integral = float(4.0 * math.pi * np.sum(u * volumes))
        ts_rows.append(
            {
                "time": float(target_time),
                "center_pressure": float(u[0]),
                "volume_mean_pressure": volume_mean,
                "surface_shell_mean_095_100": shell_095["mean"],
                "surface_shell_p95_095_100": shell_095["p95"],
                "surface_shell_max_095_100": shell_095["max"],
                "surface_shell_mean_090_100": shell_090["mean"],
                "surface_flux_density": surface_flux_density,
                "boundary_flux_integral": flux_integral,
                "cumulative_boundary_flux_integral": cumulative_flux,
                "stored_pressure_integral": stored_integral,
            }
        )
        for r, value, vol in zip(centers, u, volumes):
            profile_rows.append(
                {
                    "time": float(target_time),
                    "r": float(r),
                    "r_over_R": float(r / radius),
                    "pressure": float(value),
                    "cell_volume_no4pi": float(vol),
                }
            )
    return ts_rows, profile_rows


def enrich(row: dict[str, object], spec: CaseSpec) -> dict[str, object]:
    out = dict(row)
    out.update(
        {
            "case_label": spec.label,
            "display": spec.display,
            "source_stage": spec.source_stage,
            "resolution": spec.resolution,
            "configured_dp": spec.dp,
            "mode": spec.mode,
            "weighting": spec.weighting,
            "boundary_family": spec.boundary_family,
        }
    )
    return out


def load_case_frames(cases: list[CaseSpec]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    metrics: list[dict[str, object]] = []
    radial: list[dict[str, object]] = []
    for spec in cases:
        metric_rows = [r for r in read_csv_rows(spec.metrics_path) if r["case"] == spec.metrics_case]
        radial_rows = [r for r in read_csv_rows(spec.radial_path) if r["case"] == spec.radial_case]
        metrics.extend(enrich(r, spec) for r in metric_rows)
        radial.extend(enrich(r, spec) for r in radial_rows)
    return metrics, radial


def interp(rows: list[dict[str, object]], column: str, times: np.ndarray) -> np.ndarray:
    x = np.array([f(r, "time") for r in rows], dtype=float)
    y = np.array([f(r, column) for r in rows], dtype=float)
    order = np.argsort(x)
    return np.interp(times, x[order], y[order])


def group_by(rows: list[dict[str, object]], key: str) -> dict[object, list[dict[str, object]]]:
    groups: dict[object, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    return groups


def ref_shell_bin(
    profiles_by_time: dict[float, list[dict[str, object]]], time: float, rmin: float, rmax: float
) -> dict[str, float]:
    nearest_time = min(profiles_by_time.keys(), key=lambda t: abs(t - time))
    rows = [
        r
        for r in profiles_by_time[nearest_time]
        if rmin <= f(r, "r_over_R") <= rmax
    ]
    vals = np.array([f(r, "pressure") for r in rows], dtype=float)
    w = np.array([f(r, "cell_volume_no4pi") for r in rows], dtype=float)
    if len(vals) == 0:
        return {"mean": float("nan"), "p95": float("nan"), "max": float("nan")}
    return {
        "mean": float(np.average(vals, weights=w)),
        "p95": weighted_percentile(vals, w, 95.0),
        "max": float(np.max(vals)),
    }


def prepare_comparisons(
    metrics: list[dict[str, object]],
    radial: list[dict[str, object]],
    ref_ts: list[dict[str, object]],
    ref_profiles: list[dict[str, object]],
    config: dict[str, float],
) -> dict[str, list[dict[str, object]]]:
    radius = config["radius"]
    sphere_volume = 4.0 / 3.0 * math.pi * radius**3
    sphere_area = 4.0 * math.pi * radius**2
    profiles_by_time = group_by(ref_profiles, "time")

    radial_cmp: list[dict[str, object]] = []
    surface_decay: list[dict[str, object]] = []
    for row in radial:
        rmin = f(row, "r_over_R_min")
        rmax = f(row, "r_over_R_max")
        time = f(row, "time")
        stats = ref_shell_bin(profiles_by_time, time, rmin, rmax)
        sph_mean = f(row, "excess_mean")
        sph_p95 = f(row, "excess_p95_abs")
        out = {
            "case_label": row["case_label"],
            "display": row["display"],
            "source_stage": row["source_stage"],
            "resolution": row["resolution"],
            "configured_dp": row["configured_dp"],
            "mode": row["mode"],
            "weighting": row["weighting"],
            "boundary_family": row["boundary_family"],
            "time": time,
            "r_over_R_min": rmin,
            "r_over_R_max": rmax,
            "r_over_R_mid": 0.5 * (rmin + rmax),
            "sph_count": f(row, "excess_count"),
            "sph_mean_pressure": sph_mean,
            "sph_median_pressure": f(row, "excess_median"),
            "sph_p95_abs_pressure": sph_p95,
            "sph_max_abs_pressure": f(row, "excess_maxAbs"),
            "fv_mean_pressure": stats["mean"],
            "fv_p95_pressure": stats["p95"],
            "fv_max_pressure": stats["max"],
            "mean_error": sph_mean - stats["mean"],
            "p95_abs_error": sph_p95 - stats["p95"],
        }
        radial_cmp.append(out)
        if math.isclose(rmin, 0.95) and math.isclose(rmax, 1.0):
            surface_decay.append(out.copy())

    volume_decay: list[dict[str, object]] = []
    sph_summary: list[dict[str, object]] = []
    flux_metrics: list[dict[str, object]] = []
    boundary_type: list[dict[str, object]] = []
    surface_by_case = group_by(surface_decay, "case_label")
    for label, group in group_by(metrics, "case_label").items():
        group = sorted(group, key=lambda r: f(r, "time"))
        times = np.array([f(r, "time") for r in group], dtype=float)
        volume_mean = np.array([f(r, "excess_mean") for r in group], dtype=float)
        center_key = "center_avg_excess_r0p40" if "center_avg_excess_r0p40" in group[0] else "center_avg_excess_r0p20"
        center = np.array([f(r, center_key) for r in group], dtype=float)
        ref_mean = interp(ref_ts, "volume_mean_pressure", times)
        ref_center = interp(ref_ts, "center_pressure", times)
        ref_flux = interp(ref_ts, "boundary_flux_integral", times)
        ref_shell = interp(ref_ts, "surface_shell_mean_095_100", times)
        ref_shell_p95 = interp(ref_ts, "surface_shell_p95_095_100", times)
        dmean_dt = np.gradient(volume_mean, times) if len(times) > 1 else np.array([float("nan")])
        apparent_flux = -sphere_volume * dmean_dt
        with np.errstate(divide="ignore", invalid="ignore"):
            flux_ratio = np.divide(apparent_flux, ref_flux)
        case_surface = sorted(surface_by_case[label], key=lambda r: f(r, "time"))
        surface_times = np.array([f(r, "time") for r in case_surface], dtype=float)
        surface_mean = np.array([f(r, "sph_mean_pressure") for r in case_surface], dtype=float)
        surface_p95 = np.array([f(r, "sph_p95_abs_pressure") for r in case_surface], dtype=float)
        surface_max = np.array([f(r, "sph_max_abs_pressure") for r in case_surface], dtype=float)
        surface_interp = np.interp(times, surface_times, surface_mean)
        with np.errstate(divide="ignore", invalid="ignore"):
            h_eff = (apparent_flux / sphere_area) / surface_interp

        valid = times > 0.0
        finite_ratio = flux_ratio[(times > 0.0) & np.isfinite(flux_ratio)]
        center_rmse = float(np.sqrt(np.mean((center[valid] - ref_center[valid]) ** 2)))
        mean_rmse = float(np.sqrt(np.mean((volume_mean[valid] - ref_mean[valid]) ** 2)))
        shell_rmse = float(np.sqrt(np.mean((surface_interp[valid] - ref_shell[valid]) ** 2)))
        median_flux_ratio = float(np.nanmedian(finite_ratio))
        final_flux_ratio = float(flux_ratio[-1])
        p95_error_final = float(surface_p95[-1] - ref_shell_p95[-1])
        negative_pressure = bool(np.nanmin(volume_mean) < -1.0 or np.nanmin(surface_mean) < -1.0)
        flux_reversal = bool(np.nanmin(finite_ratio) < -0.25 or final_flux_ratio < -0.25)
        nonuniformity = float(np.nanmax(surface_max) / max(np.nanmax(np.abs(surface_mean)), 1.0e-12))
        if negative_pressure or median_flux_ratio > 1.5:
            effective_type = "over-strong Robin / overdrain"
        if flux_reversal:
            effective_type = "nonuniform / flux-reversal Robin"
        elif median_flux_ratio > 1.5 and (p95_error_final > 150.0 or shell_rmse > 300.0):
            effective_type = "over-strong nonuniform Robin"
        elif median_flux_ratio < 0.35:
            effective_type = "weak Robin"
        elif nonuniformity > 2.0 or p95_error_final > 250.0:
            effective_type = "nonuniform boundary"
        elif 0.7 <= median_flux_ratio <= 1.3 and shell_rmse < 150.0:
            effective_type = "near Dirichlet"
        else:
            effective_type = "mixed / nonuniform Robin"

        for i, row in enumerate(group):
            out = {
                "case_label": label,
                "display": row["display"],
                "source_stage": row["source_stage"],
                "resolution": row["resolution"],
                "configured_dp": row["configured_dp"],
                "mode": row["mode"],
                "weighting": row["weighting"],
                "boundary_family": row["boundary_family"],
                "time": times[i],
                "sph_center_pressure": center[i],
                "fv_center_pressure": ref_center[i],
                "center_error": center[i] - ref_center[i],
                "sph_volume_mean_pressure": volume_mean[i],
                "fv_volume_mean_pressure": ref_mean[i],
                "volume_mean_error": volume_mean[i] - ref_mean[i],
                "apparent_boundary_flux_integral": apparent_flux[i],
                "fv_boundary_flux_integral": ref_flux[i],
                "flux_ratio": flux_ratio[i],
                "effective_cv_ratio": flux_ratio[i],
                "effective_h": h_eff[i],
            }
            volume_decay.append(out)
            flux_metrics.append(
                {
                    "case_label": label,
                    "display": row["display"],
                    "time": times[i],
                    "configured_dp": row["configured_dp"],
                    "mode": row["mode"],
                    "weighting": row["weighting"],
                    "apparent_flux_integral": apparent_flux[i],
                    "reference_flux_integral": ref_flux[i],
                    "flux_ratio": flux_ratio[i],
                    "effective_cv_ratio": flux_ratio[i],
                    "effective_h": h_eff[i],
                }
            )

        summary = {
            "case_label": label,
            "display": group[0]["display"],
            "source_stage": group[0]["source_stage"],
            "resolution": group[0]["resolution"],
            "configured_dp": group[0]["configured_dp"],
            "mode": group[0]["mode"],
            "weighting": group[0]["weighting"],
            "boundary_family": group[0]["boundary_family"],
            "frames": len(group),
            "final_time": float(times[-1]),
            "final_center_pressure": float(center[-1]),
            "fv_final_center_pressure": float(ref_center[-1]),
            "final_volume_mean_pressure": float(volume_mean[-1]),
            "fv_final_volume_mean_pressure": float(ref_mean[-1]),
            "final_surface_shell_mean_095_100": float(surface_mean[-1]),
            "fv_final_surface_shell_mean_095_100": float(ref_shell[-1]),
            "final_surface_shell_p95_abs_095_100": float(surface_p95[-1]),
            "fv_final_surface_shell_p95_095_100": float(ref_shell_p95[-1]),
            "center_pressure_rmse": center_rmse,
            "volume_mean_pressure_rmse": mean_rmse,
            "surface_shell_pressure_rmse": shell_rmse,
            "near_surface_p95_final_error": p95_error_final,
            "median_flux_ratio": median_flux_ratio,
            "final_flux_ratio": final_flux_ratio,
            "min_flux_ratio": float(np.nanmin(finite_ratio)),
            "max_flux_ratio": float(np.nanmax(finite_ratio)),
            "final_effective_h": float(h_eff[-1]),
            "boundary_nonuniformity_index": nonuniformity,
            "negative_pressure": negative_pressure,
            "flux_reversal": flux_reversal,
            "effective_boundary_type": effective_type,
            "final_porepressrate_maxAbs": f(group[-1], "porepressrate_maxAbs"),
            "final_vel_max": f(group[-1], "vel_max"),
            "final_kplastic_maxAbs": f(group[-1], "kplastic_maxAbs"),
        }
        sph_summary.append(summary)
        boundary_type.append(
            {
                "case_label": label,
                "display": group[0]["display"],
                "configured_dp": group[0]["configured_dp"],
                "mode": group[0]["mode"],
                "weighting": group[0]["weighting"],
                "median_flux_ratio": median_flux_ratio,
                "final_flux_ratio": final_flux_ratio,
                "surface_shell_pressure_rmse": shell_rmse,
                "near_surface_p95_final_error": p95_error_final,
                "boundary_nonuniformity_index": nonuniformity,
                "negative_mean_or_shell_pressure": negative_pressure,
                "flux_reversal": flux_reversal,
                "effective_boundary_type": effective_type,
            }
        )

    return {
        "radial_cmp": radial_cmp,
        "surface_decay": surface_decay,
        "volume_decay": volume_decay,
        "sph_summary": sph_summary,
        "flux_metrics": flux_metrics,
        "boundary_type": boundary_type,
    }


def add_geometry_metrics(summary: list[dict[str, object]]) -> list[dict[str, object]]:
    c5h = PLAN_ROOT / "C5h_HigherResolutionSphere"
    quality_rows = [
        r for r in read_csv_rows(c5h / "c5h_sphere_quality_metrics.csv") if r["kind"] == "diffusion"
    ]
    selection_rows = [
        r for r in read_csv_rows(c5h / "c5h_boundary_selection_metrics.csv") if r["kind"] == "diffusion"
    ]
    quality = {r["resolution"]: r for r in quality_rows}
    selection = {r["resolution"]: r for r in selection_rows}
    out: list[dict[str, object]] = []
    for row in summary:
        if row["boundary_family"] != "mode4_normalized":
            continue
        res = str(row["resolution"])
        q = quality[res]
        s = selection[res]
        merged = dict(row)
        merged.update(
            {
                "material_particle_count": f(q, "material_particle_count"),
                "selected_boundary_particle_count": f(q, "selected_boundary_particle_count"),
                "material_boundary_pair_count": f(q, "material_boundary_pair_count"),
                "surface_roughness_std": f(q, "surface_roughness_std"),
                "max_surface_radius_abs_error": f(q, "max_surface_radius_abs_error"),
                "mean_surface_radius_error": f(q, "mean_surface_radius_error"),
                "selection_targets": f(s, "targets"),
                "selection_selected": f(s, "selected"),
                "selection_pairs": f(s, "pairs"),
                "selection_avg_pairs": f(s, "avg"),
            }
        )
        out.append(merged)
    return out


def savefig(name: str) -> None:
    for ext in ("png", "svg"):
        plt.savefig(FIG_DIR / f"{name}.{ext}", dpi=180, bbox_inches="tight")
    plt.close()


def rows_for(rows: list[dict[str, object]], **criteria: object) -> list[dict[str, object]]:
    out = rows
    for key, value in criteria.items():
        out = [r for r in out if r.get(key) == value]
    return out


def plot_outputs(
    ref_ts: list[dict[str, object]],
    ref_profiles: list[dict[str, object]],
    comp: dict[str, list[dict[str, object]]],
    geometry: list[dict[str, object]],
) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    ref_by_time = group_by(ref_profiles, "time")
    ref_times = sorted(ref_by_time.keys())

    plt.figure(figsize=(7.0, 4.4))
    for target in [0.0, 0.001, 0.002, 0.004, 0.006]:
        t = min(ref_times, key=lambda value: abs(value - target))
        rows = ref_by_time[t]
        plt.plot([f(r, "r_over_R") for r in rows], [f(r, "pressure") for r in rows], label=f"t={t:.4f}s")
    plt.xlabel("r/R")
    plt.ylabel("pressure (Pa)")
    plt.title("FV radial diffusion reference profiles")
    plt.legend()
    plt.grid(True, alpha=0.3)
    savefig("c5i_fv_radial_diffusion_reference_profiles")

    radial = comp["radial_cmp"]
    final_time = max(f(r, "time") for r in radial)
    ref_final = ref_by_time[min(ref_times, key=lambda value: abs(value - final_time))]
    plt.figure(figsize=(7.2, 4.4))
    plt.plot([f(r, "r_over_R") for r in ref_final], [f(r, "pressure") for r in ref_final], "k-", label="FV reference")
    for label, group in group_by(
        [
            r
            for r in radial
            if r["boundary_family"] == "mode4_normalized" and math.isclose(f(r, "time"), final_time)
        ],
        "case_label",
    ).items():
        group = sorted(group, key=lambda r: f(r, "r_over_R_mid"))
        plt.plot([f(r, "r_over_R_mid") for r in group], [f(r, "sph_mean_pressure") for r in group], marker="o", label=group[0]["display"])
    plt.xlabel("r/R")
    plt.ylabel("pressure (Pa)")
    plt.title("SPH radial profiles vs FV at final time")
    plt.legend()
    plt.grid(True, alpha=0.3)
    savefig("c5i_sph_radial_profiles_vs_fv")

    volume = comp["volume_decay"]
    ref_t = [f(r, "time") for r in ref_ts]
    plt.figure(figsize=(7.2, 4.4))
    plt.plot(ref_t, [f(r, "center_pressure") for r in ref_ts], "k-", label="FV center")
    for label, group in group_by(rows_for(volume, boundary_family="mode4_normalized"), "case_label").items():
        group = sorted(group, key=lambda r: f(r, "time"))
        plt.plot([f(r, "time") for r in group], [f(r, "sph_center_pressure") for r in group], marker="o", label=group[0]["display"])
    plt.xlabel("time (s)")
    plt.ylabel("center pressure (Pa)")
    plt.title("Center pressure decay vs reference")
    plt.legend()
    plt.grid(True, alpha=0.3)
    savefig("c5i_center_pressure_decay_vs_reference")

    plt.figure(figsize=(7.2, 4.4))
    plt.plot(ref_t, [f(r, "volume_mean_pressure") for r in ref_ts], "k-", label="FV volume mean")
    for label, group in group_by(rows_for(volume, boundary_family="mode4_normalized"), "case_label").items():
        group = sorted(group, key=lambda r: f(r, "time"))
        plt.plot([f(r, "time") for r in group], [f(r, "sph_volume_mean_pressure") for r in group], marker="o", label=group[0]["display"])
    plt.xlabel("time (s)")
    plt.ylabel("volume mean pressure (Pa)")
    plt.title("Volume-average pressure decay vs reference")
    plt.legend()
    plt.grid(True, alpha=0.3)
    savefig("c5i_volume_average_pressure_decay_vs_reference")

    surface = comp["surface_decay"]
    plt.figure(figsize=(7.2, 4.4))
    plt.plot(ref_t, [f(r, "surface_shell_mean_095_100") for r in ref_ts], "k-", label="FV shell 0.95-1.0R")
    for label, group in group_by(rows_for(surface, boundary_family="mode4_normalized"), "case_label").items():
        group = sorted(group, key=lambda r: f(r, "time"))
        plt.plot([f(r, "time") for r in group], [f(r, "sph_mean_pressure") for r in group], marker="o", label=group[0]["display"])
    plt.xlabel("time (s)")
    plt.ylabel("surface shell pressure (Pa)")
    plt.title("Surface shell decay vs reference")
    plt.legend()
    plt.grid(True, alpha=0.3)
    savefig("c5i_surface_shell_pressure_decay_vs_reference")

    flux = comp["flux_metrics"]
    plt.figure(figsize=(7.2, 4.4))
    for label, group in group_by(flux, "case_label").items():
        group = sorted(group, key=lambda r: f(r, "time"))
        plt.plot([f(r, "time") for r in group], [f(r, "flux_ratio") for r in group], marker="o", label=group[0]["display"])
    plt.axhline(1.0, color="k", linewidth=1.0, linestyle="--")
    plt.xlabel("time (s)")
    plt.ylabel("SPH apparent flux / FV flux")
    plt.title("Apparent flux ratio vs time")
    plt.ylim(-2.0, 4.0)
    plt.legend(fontsize=8)
    plt.grid(True, alpha=0.3)
    savefig("c5i_apparent_flux_ratio_vs_time")

    summary = sorted(comp["sph_summary"], key=lambda r: (f(r, "mode"), str(r["weighting"]), f(r, "configured_dp")))
    plt.figure(figsize=(7.2, 4.4))
    x = np.arange(len(summary))
    plt.bar(x, [f(r, "median_flux_ratio") for r in summary], color="#5470c6")
    plt.axhline(1.0, color="k", linewidth=1.0, linestyle="--")
    plt.xticks(x, [str(r["case_label"]) for r in summary], rotation=35, ha="right")
    plt.ylabel("median flux ratio")
    plt.title("Effective boundary type comparison")
    savefig("c5i_effective_boundary_type_comparison")

    norm = sorted(rows_for(comp["sph_summary"], boundary_family="mode4_normalized"), key=lambda r: f(r, "configured_dp"), reverse=True)
    plt.figure(figsize=(7.0, 4.4))
    plt.plot([f(r, "configured_dp") for r in norm], [f(r, "volume_mean_pressure_rmse") for r in norm], marker="o", label="volume mean RMSE")
    plt.plot([f(r, "configured_dp") for r in norm], [f(r, "surface_shell_pressure_rmse") for r in norm], marker="o", label="surface shell RMSE")
    plt.gca().invert_xaxis()
    plt.xlabel("dp (m)")
    plt.ylabel("RMSE (Pa)")
    plt.title("dp vs pressure-only diffusion error")
    plt.legend()
    plt.grid(True, alpha=0.3)
    savefig("c5i_dp_vs_error_metrics")

    plt.figure(figsize=(7.0, 4.4))
    plt.scatter([f(r, "surface_roughness_std") for r in geometry], [f(r, "surface_shell_pressure_rmse") for r in geometry], s=70, c=[f(r, "configured_dp") for r in geometry], cmap="viridis_r")
    for row in geometry:
        plt.annotate(str(row["resolution"]), (f(row, "surface_roughness_std"), f(row, "surface_shell_pressure_rmse")))
    plt.xlabel("surface roughness std (m)")
    plt.ylabel("surface shell RMSE (Pa)")
    plt.title("Sphere roughness vs diffusion error")
    plt.grid(True, alpha=0.3)
    savefig("c5i_sphere_roughness_vs_diffusion_error")

    plt.figure(figsize=(7.0, 4.4))
    plt.plot([f(r, "selected_boundary_particle_count") for r in geometry], [f(r, "surface_shell_pressure_rmse") for r in geometry], marker="o", label="selected boundary count")
    plt.plot([f(r, "material_boundary_pair_count") / 100.0 for r in geometry], [f(r, "surface_shell_pressure_rmse") for r in geometry], marker="s", label="pair count / 100")
    for row in geometry:
        plt.annotate(str(row["resolution"]), (f(row, "selected_boundary_particle_count"), f(row, "surface_shell_pressure_rmse")))
    plt.xlabel("count")
    plt.ylabel("surface shell RMSE (Pa)")
    plt.title("Boundary selection / pair count vs diffusion error")
    plt.legend()
    plt.grid(True, alpha=0.3)
    savefig("c5i_boundary_selection_count_vs_diffusion_error")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    config = read_xml_config()
    cases = build_cases()
    metrics, radial = load_case_frames(cases)
    output_times = np.unique(np.array([f(r, "time") for r in metrics], dtype=float))
    ref_ts, ref_profiles = solve_reference(config, output_times)
    comp = prepare_comparisons(metrics, radial, ref_ts, ref_profiles, config)
    geometry = add_geometry_metrics(comp["sph_summary"])

    write_csv(ROOT / "c5i_reference_config.csv", [config])
    write_csv(ROOT / "c5i_fv_reference_timeseries.csv", ref_ts)
    write_csv(ROOT / "c5i_fv_reference_profiles.csv", ref_profiles)
    write_csv(ROOT / "c5i_sph_pressure_only_summary.csv", comp["sph_summary"])
    write_csv(ROOT / "c5i_radial_bin_profiles.csv", comp["radial_cmp"])
    write_csv(ROOT / "c5i_volume_mean_decay.csv", comp["volume_decay"])
    write_csv(ROOT / "c5i_surface_shell_decay.csv", comp["surface_decay"])
    write_csv(ROOT / "c5i_effective_boundary_type.csv", comp["boundary_type"])
    write_csv(ROOT / "c5i_flux_ratio_metrics.csv", comp["flux_metrics"])
    write_csv(ROOT / "c5i_geometry_flux_error_metrics.csv", geometry)
    plot_outputs(ref_ts, ref_profiles, comp, geometry)


if __name__ == "__main__":
    main()
