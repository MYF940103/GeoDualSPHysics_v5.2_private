#!/usr/bin/env python3
"""Analyze C5j MLS / flux-consistent spherical drained boundary gate."""

from __future__ import annotations

import csv
import math
import re
import struct
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PLAN_ROOT = ROOT.parent
C5I_ROOT = PLAN_ROOT / "C5i_SphericalDiffusionFluxCalibration"
RADIUS = 0.05
RADIAL_BINS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 0.95), (0.95, 1.0)]
CENTER_RADII = [0.10 * RADIUS, 0.20 * RADIUS, 0.30 * RADIUS, 0.40 * RADIUS]

CASES = [
    {
        "label": "mode5_mls_dp008",
        "case_name": "CaseCryer_PR_StrictSphere_C5j_FinerDiffusionMLS",
        "resolution": "finer",
        "dp": 0.008,
        "mode": 5,
    },
    {
        "label": "mode5_mls_dp010",
        "case_name": "CaseCryer_PR_StrictSphere_C5j_CoarseDiffusionMLS",
        "resolution": "coarse",
        "dp": 0.010,
        "mode": 5,
    },
]

MLS_RE = re.compile(
    r"CPU curved drained MLS flux correction: order=(?P<order>[-+0-9]+), "
    r"targets=(?P<targets>\d+), samples=(?P<samples>\d+), average_samples=(?P<avg>[-+0-9.eE]+), "
    r"fallback=(?P<fallback>\d+), fallback_mode=(?P<fallback_mode>[-+0-9]+), support_radius=(?P<support>[-+0-9.eE]+), "
    r"condition_limit=(?P<cond_limit>[-+0-9.eE]+), cond_min=(?P<cond_min>[-+0-9.eE]+), "
    r"cond_mean=(?P<cond_mean>[-+0-9.eE]+), cond_max=(?P<cond_max>[-+0-9.eE]+)"
)

FLUX_RE = re.compile(
    r"CPU curved drained MLS flux diagnostics: TimeStep=(?P<time>[-+0-9.eE]+), "
    r"boundary_area=(?P<area>[-+0-9.eE]+), shell_volume=(?P<shell_volume>[-+0-9.eE]+), "
    r"mean_normal_gradient=(?P<grad_mean>[-+0-9.eE]+) Pa/m, max_abs_normal_gradient=(?P<grad_max>[-+0-9.eE]+) Pa/m, "
    r"max_abs_lap_correction=(?P<lap_corr_max>[-+0-9.eE]+), boundary_flux_integral=(?P<flux>[-+0-9.eE]+) Pa\*m3/s, "
    r"storage_rate_correction=(?P<storage_rate>[-+0-9.eE]+) Pa\*m3/s"
)


def fnum(value, default=math.nan):
    try:
        if value is None or value == "":
            return default
        if isinstance(value, str):
            value = value.strip().rstrip(".,")
        return float(value)
    except (TypeError, ValueError):
        return default


def split_line(line: str) -> list[str]:
    sep = ";" if ";" in line else ","
    return [v.strip() for v in line.strip().split(sep)]


def find_col(headers: list[str], candidates: tuple[str, ...]) -> int | None:
    lower = [h.lower().split()[0] if h.strip() else "" for h in headers]
    for cand in candidates:
        cl = cand.lower()
        for i, header in enumerate(lower):
            if header == cl or header.endswith("." + cl) or header.endswith("_" + cl):
                return i
    return None


def percentile(values: list[float], pct: float) -> float:
    data = sorted(v for v in values if math.isfinite(v))
    if not data:
        return math.nan
    x = (len(data) - 1) * pct / 100.0
    lo = int(math.floor(x))
    hi = int(math.ceil(x))
    if lo == hi:
        return data[lo]
    return data[lo] * (hi - x) + data[hi] * (x - lo)


def stats(values: list[float]) -> dict[str, float | int]:
    vals = [v for v in values if math.isfinite(v)]
    absv = [abs(v) for v in vals]
    return {
        "count": len(vals),
        "mean": sum(vals) / len(vals) if vals else math.nan,
        "median": percentile(vals, 50.0),
        "p95_abs": percentile(absv, 95.0),
        "p99_abs": percentile(absv, 99.0),
        "max": max(vals) if vals else math.nan,
        "maxAbs": max(absv) if absv else math.nan,
    }


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as fp:
        return list(csv.DictReader(fp))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def group_by(rows: list[dict[str, object]], key: str) -> dict[object, list[dict[str, object]]]:
    out: dict[object, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        out[row[key]].append(row)
    return out


def read_runout(case: dict[str, object]) -> tuple[dict[str, object], list[dict[str, object]], dict[int, float]]:
    runout = ROOT / f"{case['case_name']}_cpu_out" / "Run.out"
    meta = {"case": case["label"], "code": "unknown", "excluded": "unknown", "runout_exists": runout.exists()}
    rows: list[dict[str, object]] = []
    times: dict[int, float] = {0: 0.0}
    if not runout.exists():
        return meta, rows, times
    text = runout.read_text(errors="ignore")
    meta["code"] = 0 if "Finished execution" in text else "unknown"
    m = re.search(r"Excluded particles\.*:\s*(\d+)", text)
    if m:
        meta["excluded"] = int(m.group(1))
    m = re.search(r"Steps of simulation\.*:\s*(\d+)", text)
    if m:
        meta["steps"] = int(m.group(1))
    m = re.search(r"Total Runtime\.*:\s*([-+0-9.eE]+)", text)
    if m:
        meta["runtime_sec"] = fnum(m.group(1))
    for match in re.finditer(r"Part_(?P<idx>\d{4})\s+(?P<time>[-+0-9.eE]*\.[-+0-9.eE]+)\s+\d+", text):
        times[int(match.group("idx"))] = fnum(match.group("time"))
    mls_matches = list(MLS_RE.finditer(text))
    flux_matches = list(FLUX_RE.finditer(text))
    for i, flux in enumerate(flux_matches):
        row = {
            "case": case["label"],
            "case_name": case["case_name"],
            "resolution": case["resolution"],
            "configured_dp": case["dp"],
            "diag_index": i,
        }
        if i < len(mls_matches):
            row.update({k: fnum(v) for k, v in mls_matches[i].groupdict().items()})
        row.update({k: fnum(v) for k, v in flux.groupdict().items()})
        rows.append(row)
    return meta, rows, times


def read_partcsv(case: dict[str, object], times: dict[int, float]):
    data_dir = ROOT / f"{case['case_name']}_cpu_out" / "data"
    frames: list[dict[str, object]] = []
    surfaces: list[dict[str, object]] = []
    radials: list[dict[str, object]] = []
    quality: list[dict[str, object]] = []
    for iframe, path in enumerate(sorted(data_dir.glob("PartCsv_*.csv"))):
        lines = path.read_text(errors="ignore").splitlines()
        header_idx = next((i for i, line in enumerate(lines) if "PorePress" in line or "Pos" in line), None)
        if header_idx is None:
            continue
        headers = split_line(lines[header_idx])
        cols = {
            "x": find_col(headers, ("Pos.x", "posx", "x")),
            "y": find_col(headers, ("Pos.y", "posy", "y")),
            "z": find_col(headers, ("Pos.z", "posz", "z")),
            "type": find_col(headers, ("Type",)),
            "ex": find_col(headers, ("ExcessPorePress",)),
            "rate": find_col(headers, ("PorePressRate",)),
            "lap": find_col(headers, ("LapPorePress",)),
            "kp": find_col(headers, ("Kplastic",)),
        }
        particles: list[dict[str, float]] = []
        for line in lines[header_idx + 1:]:
            if not line.strip() or line.startswith("#"):
                continue
            vals = split_line(line)
            if cols["x"] is None or cols["y"] is None or cols["z"] is None:
                continue
            if cols["type"] is not None and int(fnum(vals[cols["type"]], -1)) != 3:
                continue
            x = fnum(vals[cols["x"]])
            y = fnum(vals[cols["y"]])
            z = fnum(vals[cols["z"]])
            particles.append(
                {
                    "r": math.sqrt(x * x + y * y + z * z),
                    "ex": fnum(vals[cols["ex"]]) if cols["ex"] is not None else math.nan,
                    "rate": fnum(vals[cols["rate"]]) if cols["rate"] is not None else math.nan,
                    "lap": fnum(vals[cols["lap"]]) if cols["lap"] is not None else math.nan,
                    "kp": fnum(vals[cols["kp"]]) if cols["kp"] is not None else 0.0,
                }
            )
        time = times.get(iframe, float(iframe))
        ex_vals = [p["ex"] for p in particles]
        rates = [p["rate"] for p in particles]
        laps = [p["lap"] for p in particles]
        kp = [abs(p["kp"]) for p in particles]
        center: dict[str, object] = {}
        nearest = min(particles, key=lambda p: p["r"], default=None)
        if nearest:
            center["center_nearest_radius"] = nearest["r"]
            center["center_nearest_excess"] = nearest["ex"]
        for rad in CENTER_RADII:
            vals = [p["ex"] for p in particles if p["r"] <= rad and math.isfinite(p["ex"])]
            key = f"r{rad / RADIUS:.2f}".replace(".", "p")
            center[f"center_avg_excess_{key}"] = sum(vals) / len(vals) if vals else math.nan
            center[f"center_avg_count_{key}"] = len(vals)
        shell = [p["ex"] for p in particles if 0.95 * RADIUS <= p["r"] <= RADIUS * 1.10]
        shell_stats = stats(shell)
        surfaces.append(
            {
                "case": case["label"],
                "time": time,
                "frame_index": iframe,
                "shell": "0.95R-1.0R",
                **{f"surface_shell_{k}": v for k, v in shell_stats.items()},
            }
        )
        for lo, hi in RADIAL_BINS:
            vals = [p["ex"] for p in particles if lo <= p["r"] / RADIUS < hi or (hi == 1.0 and lo <= p["r"] / RADIUS <= hi)]
            s = stats(vals)
            radials.append(
                {
                    "case": case["label"],
                    "time": time,
                    "frame_index": iframe,
                    "r_over_R_min": lo,
                    "r_over_R_max": hi,
                    "r_over_R_mid": 0.5 * (lo + hi),
                    **{f"excess_{k}": v for k, v in s.items()},
                }
            )
        frames.append(
            {
                "case": case["label"],
                "case_name": case["case_name"],
                "resolution": case["resolution"],
                "configured_dp": case["dp"],
                "mode": case["mode"],
                "time": time,
                "frame_index": iframe,
                "particle_count": len(particles),
                "volume_mean_pressure": sum(ex_vals) / len(ex_vals) if ex_vals else math.nan,
                "porepressrate_maxAbs": max((abs(v) for v in rates), default=math.nan),
                "lap_maxAbs": max((abs(v) for v in laps), default=math.nan),
                "kplastic_maxAbs": max(kp) if kp else 0.0,
                **center,
            }
        )
        if iframe == 0 and particles:
            rvals = [p["r"] for p in particles]
            surf = [r for r in rvals if r >= 0.85 * RADIUS]
            err = [r - RADIUS for r in surf]
            mean_err = sum(err) / len(err) if err else math.nan
            quality.append(
                {
                    "case": case["label"],
                    "material_particle_count": len(particles),
                    "surface_count_r085": len(surf),
                    "surface_roughness_std": math.sqrt(sum((e - mean_err) ** 2 for e in err) / len(err)) if err else math.nan,
                    "max_surface_radius_abs_error": max((abs(e) for e in err), default=math.nan),
                }
            )
    return frames, surfaces, radials, quality


def read_vtk_vectors(blob: bytes, field_name: bytes, components: int):
    if field_name == b"POINTS":
        match = re.search(rb"POINTS\s+(\d+)\s+float\s*\n", blob)
    else:
        pattern = rb"\n" + re.escape(field_name) + rb"\s+" + str(components).encode() + rb"\s+(\d+)\s+float\s*\n"
        match = re.search(pattern, blob)
    if not match:
        return None
    count = int(match.group(1))
    start = match.end()
    nvalues = count * components
    nbytes = nvalues * 4
    if start + nbytes > len(blob):
        return None
    values = struct.unpack(f">{nvalues}f", blob[start:start + nbytes])
    return [tuple(values[i : i + components]) for i in range(0, nvalues, components)]


def read_vtk(case: dict[str, object], times: dict[int, float]) -> list[dict[str, object]]:
    vtk_dir = ROOT / f"{case['case_name']}_cpu_vtk_particles"
    rows: list[dict[str, object]] = []
    for iframe, path in enumerate(sorted(vtk_dir.glob("PartFluid_*.vtk"))):
        blob = path.read_bytes()
        vel = read_vtk_vectors(blob, b"Vel", 3)
        if not vel:
            continue
        vmag = [math.sqrt(vx * vx + vy * vy + vz * vz) for vx, vy, vz in vel]
        rows.append(
            {
                "case": case["label"],
                "frame_index": iframe,
                "time": times.get(iframe, float(iframe)),
                "vel_max": max(vmag) if vmag else 0.0,
                "vel_mean": sum(vmag) / len(vmag) if vmag else 0.0,
            }
        )
    return rows


def interpolate(rows: list[dict[str, str | object]], xkey: str, ykey: str, x: np.ndarray) -> np.ndarray:
    xs = np.array([fnum(r[xkey]) for r in rows], dtype=float)
    ys = np.array([fnum(r[ykey]) for r in rows], dtype=float)
    order = np.argsort(xs)
    return np.interp(x, xs[order], ys[order])


def reference_rows() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    return (
        read_csv_rows(C5I_ROOT / "c5i_fv_reference_timeseries.csv"),
        read_csv_rows(C5I_ROOT / "c5i_volume_mean_decay.csv"),
        read_csv_rows(C5I_ROOT / "c5i_surface_shell_decay.csv"),
        read_csv_rows(C5I_ROOT / "c5i_sph_pressure_only_summary.csv"),
    )


def build_comparison(frames, surfaces, mls_rows):
    ref_ts, c5i_volume, c5i_surface, c5i_summary = reference_rows()
    comparison: list[dict[str, object]] = []
    flux_rows: list[dict[str, object]] = []
    surface_by_case = group_by(surfaces, "case")
    mls_by_case = group_by(mls_rows, "case")
    sphere_volume = 4.0 / 3.0 * math.pi * RADIUS**3
    for case, group in group_by(frames, "case").items():
        group = sorted(group, key=lambda r: fnum(r["time"]))
        times = np.array([fnum(r["time"]) for r in group], dtype=float)
        mean = np.array([fnum(r["volume_mean_pressure"]) for r in group], dtype=float)
        center = np.array([fnum(r["center_avg_excess_r0p40"]) for r in group], dtype=float)
        ref_center = interpolate(ref_ts, "time", "center_pressure", times)
        ref_mean = interpolate(ref_ts, "time", "volume_mean_pressure", times)
        ref_shell = interpolate(ref_ts, "time", "surface_shell_mean_095_100", times)
        ref_flux = interpolate(ref_ts, "time", "boundary_flux_integral", times)
        surf = sorted(surface_by_case[case], key=lambda r: fnum(r["time"]))
        shell_mean = np.array([fnum(r["surface_shell_mean"]) for r in surf], dtype=float)
        shell_p95 = np.array([fnum(r["surface_shell_p95_abs"]) for r in surf], dtype=float)
        shell_max = np.array([fnum(r["surface_shell_maxAbs"]) for r in surf], dtype=float)
        dmean = np.gradient(mean, times)
        apparent_flux = -sphere_volume * dmean
        with np.errstate(divide="ignore", invalid="ignore"):
            flux_ratio = apparent_flux / ref_flux
        for i, row in enumerate(group):
            comparison.append(
                {
                    "case": case,
                    "time": times[i],
                    "center_pressure": center[i],
                    "fv_center_pressure": ref_center[i],
                    "volume_mean_pressure": mean[i],
                    "fv_volume_mean_pressure": ref_mean[i],
                    "surface_shell_mean": shell_mean[i],
                    "fv_surface_shell_mean": ref_shell[i],
                    "surface_shell_p95_abs": shell_p95[i],
                    "surface_shell_maxAbs": shell_max[i],
                    "porepressrate_maxAbs": row["porepressrate_maxAbs"],
                    "kplastic_maxAbs": row["kplastic_maxAbs"],
                    "apparent_flux_integral": apparent_flux[i],
                    "fv_boundary_flux_integral": ref_flux[i],
                    "flux_ratio": flux_ratio[i],
                }
            )
            flux_rows.append(
                {
                    "case": case,
                    "time": times[i],
                    "apparent_flux_integral": apparent_flux[i],
                    "fv_boundary_flux_integral": ref_flux[i],
                    "flux_ratio": flux_ratio[i],
                }
            )
        valid = times > 0.0
        finite_ratio = flux_ratio[valid & np.isfinite(flux_ratio)]
        mode4 = next((r for r in c5i_summary if r["boundary_family"] == "mode4_normalized" and abs(fnum(r["configured_dp"]) - fnum(group[0]["configured_dp"])) < 1e-12), None)
        for mrow in mls_by_case.get(case, []):
            rf = np.interp(fnum(mrow["time"]), [fnum(r["time"]) for r in ref_ts], [fnum(r["boundary_flux_integral"]) for r in ref_ts])
            mrow["fv_boundary_flux_integral"] = rf
            mrow["mls_flux_ratio_to_fv"] = fnum(mrow["flux"]) / rf if abs(rf) > 1e-20 else math.nan
        yield {
            "case": case,
            "case_name": group[0]["case_name"],
            "resolution": group[0]["resolution"],
            "configured_dp": group[0]["configured_dp"],
            "frames": len(group),
            "final_time": times[-1],
            "final_center_pressure": center[-1],
            "fv_final_center_pressure": ref_center[-1],
            "final_volume_mean_pressure": mean[-1],
            "fv_final_volume_mean_pressure": ref_mean[-1],
            "final_surface_shell_mean": shell_mean[-1],
            "fv_final_surface_shell_mean": ref_shell[-1],
            "final_surface_shell_p95_abs": shell_p95[-1],
            "center_pressure_rmse": float(np.sqrt(np.mean((center[valid] - ref_center[valid]) ** 2))),
            "volume_mean_pressure_rmse": float(np.sqrt(np.mean((mean[valid] - ref_mean[valid]) ** 2))),
            "surface_shell_pressure_rmse": float(np.sqrt(np.mean((shell_mean[valid] - ref_shell[valid]) ** 2))),
            "median_flux_ratio": float(np.nanmedian(finite_ratio)),
            "final_flux_ratio": float(flux_ratio[-1]),
            "flux_reversal": bool(np.nanmin(finite_ratio) < -0.25 or flux_ratio[-1] < -0.25),
            "negative_pressure": bool(np.nanmin(mean) < -1.0 or np.nanmin(shell_mean) < -1.0),
            "final_porepressrate_maxAbs": fnum(group[-1]["porepressrate_maxAbs"]),
            "final_kplastic_maxAbs": fnum(group[-1]["kplastic_maxAbs"]),
            "mode4_volume_rmse_same_dp": fnum(mode4["volume_mean_pressure_rmse"]) if mode4 else math.nan,
            "mode4_surface_rmse_same_dp": fnum(mode4["surface_shell_pressure_rmse"]) if mode4 else math.nan,
            "mode4_center_rmse_same_dp": fnum(mode4["center_pressure_rmse"]) if mode4 else math.nan,
            "mode4_median_flux_ratio_same_dp": fnum(mode4["median_flux_ratio"]) if mode4 else math.nan,
        }, comparison, flux_rows


def plot_outputs(comparison, radials, mls_rows, summary):
    figdir = ROOT / "figures"
    figdir.mkdir(exist_ok=True)
    ref_ts, c5i_volume, c5i_surface, _ = reference_rows()
    mode4_volume = [r for r in c5i_volume if r["boundary_family"] == "mode4_normalized" and fnum(r["configured_dp"]) in (0.008, 0.01)]
    mode4_surface = [r for r in c5i_surface if r["boundary_family"] == "mode4_normalized" and fnum(r["configured_dp"]) in (0.008, 0.01)]

    def save(name):
        plt.tight_layout()
        plt.savefig(figdir / f"{name}.png", dpi=180)
        plt.savefig(figdir / f"{name}.svg")
        plt.close()

    def line_compare(name, ykey, refkey, ylabel):
        plt.figure(figsize=(7.4, 4.6))
        plt.plot([fnum(r["time"]) for r in ref_ts], [fnum(r[refkey]) for r in ref_ts], "k-", label="FV")
        for case, group in group_by(comparison, "case").items():
            group = sorted(group, key=lambda r: fnum(r["time"]))
            plt.plot([fnum(r["time"]) for r in group], [fnum(r[ykey]) for r in group], marker="o", label=case)
        plt.xlabel("time [s]")
        plt.ylabel(ylabel)
        plt.grid(True, alpha=0.25)
        plt.legend(fontsize=8)
        save(name)

    line_compare("c5j_center_pressure_vs_fv", "center_pressure", "center_pressure", "center pressure [Pa]")
    line_compare("c5j_volume_mean_vs_fv", "volume_mean_pressure", "volume_mean_pressure", "volume mean pressure [Pa]")
    line_compare("c5j_surface_shell_vs_fv", "surface_shell_mean", "surface_shell_mean_095_100", "surface shell mean [Pa]")

    plt.figure(figsize=(7.4, 4.6))
    for case, group in group_by(comparison, "case").items():
        group = sorted(group, key=lambda r: fnum(r["time"]))
        plt.plot([fnum(r["time"]) for r in group], [fnum(r["flux_ratio"]) for r in group], marker="o", label=case)
    for case, group in group_by(mode4_volume, "case_label").items():
        if case in ("mode4_normalized_dp008", "mode4_normalized_dp010"):
            group = sorted(group, key=lambda r: fnum(r["time"]))
            plt.plot([fnum(r["time"]) for r in group], [fnum(r["flux_ratio"]) for r in group], linestyle="--", label=case)
    plt.axhline(1.0, color="k", linewidth=1, linestyle=":")
    plt.xlabel("time [s]")
    plt.ylabel("flux ratio [-]")
    plt.ylim(-2.5, 4.5)
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    save("c5j_flux_ratio_vs_time")

    plt.figure(figsize=(7.4, 4.6))
    for case, group in group_by(mls_rows, "case").items():
        group = sorted(group, key=lambda r: fnum(r["time"]))
        plt.plot([fnum(r["time"]) for r in group], [fnum(r["flux"]) for r in group], marker="o", label=f"{case} MLS correction")
        plt.plot([fnum(r["time"]) for r in group], [-fnum(r["storage_rate"]) for r in group], linestyle="--", label=f"{case} storage derivative")
    plt.xlabel("time [s]")
    plt.ylabel("integrated pressure flux [Pa*m3/s]")
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    save("c5j_integrated_boundary_flux_vs_storage")

    plt.figure(figsize=(7.4, 4.6))
    final_time = max(fnum(r["time"]) for r in radials)
    for case, group in group_by([r for r in radials if abs(fnum(r["time"]) - final_time) < 1e-12], "case").items():
        group = sorted(group, key=lambda r: fnum(r["r_over_R_mid"]))
        plt.plot([fnum(r["r_over_R_mid"]) for r in group], [fnum(r["excess_mean"]) for r in group], marker="o", label=case)
    plt.xlabel("r/R [-]")
    plt.ylabel("final radial-bin mean pressure [Pa]")
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    save("c5j_radial_profiles_final")

    line_compare("c5j_porepressrate_maxabs", "porepressrate_maxAbs", "surface_flux_density", "|PorePressRate| max [Pa/s]")

    plt.figure(figsize=(7.4, 4.6))
    for case, group in group_by(mls_rows, "case").items():
        group = sorted(group, key=lambda r: fnum(r["time"]))
        plt.plot([fnum(r["time"]) for r in group], [fnum(r["cond_mean"]) for r in group], marker="o", label=f"{case} cond mean")
        plt.plot([fnum(r["time"]) for r in group], [fnum(r["fallback"]) for r in group], marker="s", linestyle="--", label=f"{case} fallback")
    plt.xlabel("time [s]")
    plt.ylabel("condition / fallback count")
    plt.yscale("symlog")
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    save("c5j_mls_condition_fallback_stats")

    plt.figure(figsize=(7.4, 4.6))
    for case, group in group_by(comparison, "case").items():
        group = sorted(group, key=lambda r: fnum(r["time"]))
        plt.plot([fnum(r["time"]) for r in group], [fnum(r["surface_shell_p95_abs"]) for r in group], marker="o", label=f"{case} p95")
        plt.plot([fnum(r["time"]) for r in group], [fnum(r["surface_shell_maxAbs"]) for r in group], linestyle="--", label=f"{case} max")
    plt.xlabel("time [s]")
    plt.ylabel("surface shell |pressure| [Pa]")
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    save("c5j_surface_shell_p95_max_vs_time")


def main() -> None:
    all_frames: list[dict[str, object]] = []
    all_surfaces: list[dict[str, object]] = []
    all_radials: list[dict[str, object]] = []
    all_quality: list[dict[str, object]] = []
    all_mls: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    for case in CASES:
        meta, mls_rows, times = read_runout(case)
        frames, surfaces, radials, quality = read_partcsv(case, times)
        vtk_rows = {int(r["frame_index"]): r for r in read_vtk(case, times)}
        for row in frames:
            row.update(vtk_rows.get(int(row["frame_index"]), {}))
        all_frames.extend(frames)
        all_surfaces.extend(surfaces)
        all_radials.extend(radials)
        all_quality.extend(quality)
        all_mls.extend(mls_rows)
        summary = dict(meta)
        summary.update(case)
        summaries.append(summary)

    gate_rows: list[dict[str, object]] = []
    comparison: list[dict[str, object]] = []
    flux_rows: list[dict[str, object]] = []
    for summary, comp, flux in build_comparison(all_frames, all_surfaces, all_mls):
        gate_rows.append(summary)
        comparison = comp
        flux_rows = flux

    for row in summaries:
        gate = next((g for g in gate_rows if g["case"] == row["label"]), {})
        row.update(gate)
        row["gate_volume_improved_vs_mode4"] = fnum(gate.get("volume_mean_pressure_rmse")) < fnum(gate.get("mode4_volume_rmse_same_dp"))
        row["gate_surface_improved_vs_mode4"] = fnum(gate.get("surface_shell_pressure_rmse")) < fnum(gate.get("mode4_surface_rmse_same_dp"))
        row["gate_center_improved_vs_mode4"] = fnum(gate.get("center_pressure_rmse")) < fnum(gate.get("mode4_center_rmse_same_dp"))
        row["gate_flux_closer_to_one_vs_mode4"] = abs(fnum(gate.get("median_flux_ratio")) - 1.0) < abs(fnum(gate.get("mode4_median_flux_ratio_same_dp")) - 1.0)
        row["pressure_only_gate_pass"] = (
            row.get("code") == 0
            and row.get("excluded") == 0
            and fnum(row.get("final_kplastic_maxAbs")) == 0.0
            and row["gate_volume_improved_vs_mode4"]
            and row["gate_surface_improved_vs_mode4"]
            and row["gate_center_improved_vs_mode4"]
            and row["gate_flux_closer_to_one_vs_mode4"]
            and not bool(row.get("flux_reversal"))
            and not bool(row.get("negative_pressure"))
        )

    write_csv(ROOT / "c5j_case_summary.csv", summaries)
    write_csv(ROOT / "c5j_mls_flux_diagnostics.csv", all_mls)
    write_csv(ROOT / "c5j_pressure_only_comparison.csv", comparison)
    write_csv(ROOT / "c5j_flux_ratio_metrics.csv", flux_rows)
    write_csv(ROOT / "c5j_surface_shell_metrics.csv", all_surfaces)
    write_csv(ROOT / "c5j_radial_bin_profiles.csv", all_radials)
    write_csv(ROOT / "c5j_sphere_quality_metrics.csv", all_quality)
    write_csv(ROOT / "c5j_gate_metrics.csv", gate_rows)
    plot_outputs(comparison, all_radials, all_mls, summaries)


if __name__ == "__main__":
    main()
