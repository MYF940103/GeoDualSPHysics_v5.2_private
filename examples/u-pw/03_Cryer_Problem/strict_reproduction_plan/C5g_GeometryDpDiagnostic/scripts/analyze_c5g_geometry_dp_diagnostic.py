#!/usr/bin/env python3
"""Analyze C5g modest sphere geometry / dp diagnostics."""

from __future__ import annotations

import csv
import math
import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RADIUS = 0.05
POROSITY = 0.3
HYDRAULIC_CONDUCTIVITY = 1.0e-5
WATER_BULK_MODULUS = 2.0e6
WATER_DENSITY = 1000.0
HYDRAULIC_G = 9.81
DIFF_RATE_COEF = (WATER_BULK_MODULUS / POROSITY) * (HYDRAULIC_CONDUCTIVITY / (WATER_DENSITY * HYDRAULIC_G))
CENTER_RADIUS_FACTORS = [0.10, 0.15, 0.20, 0.30, 0.40]
CENTER_RADII = [RADIUS * f for f in CENTER_RADIUS_FACTORS]
PRIMARY_CENTER_RADIUS = 0.02
SURFACE_THRESHOLDS = [0.85, 0.90, 0.95]
RADIAL_BINS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 0.95), (0.95, 1.0)]

CASES = [
    {"label": "coarse_compression", "case_name": "CaseCryer_PR_StrictSphere_C5g_CoarseCompressionNormalized", "kind": "compression", "resolution": "coarse", "dp": 0.010, "mode": 4, "weighting": 1, "p0": 50.0},
    {"label": "finer_compression", "case_name": "CaseCryer_PR_StrictSphere_C5g_FinerCompressionNormalized", "kind": "compression", "resolution": "finer", "dp": 0.008, "mode": 4, "weighting": 1, "p0": 50.0},
    {"label": "coarse_diffusion", "case_name": "CaseCryer_PR_StrictSphere_C5g_CoarseDiffusionNormalized", "kind": "diffusion", "resolution": "coarse", "dp": 0.010, "mode": 4, "weighting": 1, "p0": 0.0},
    {"label": "finer_diffusion", "case_name": "CaseCryer_PR_StrictSphere_C5g_FinerDiffusionNormalized", "kind": "diffusion", "resolution": "finer", "dp": 0.008, "mode": 4, "weighting": 1, "p0": 0.0},
]

CURVED_RE = re.compile(
    r"CPU curved drained pore-pressure boundary: active=(?P<active>\w+), "
    r"center=\((?P<cx>[-+0-9.eE]+),(?P<cy>[-+0-9.eE]+),(?P<cz>[-+0-9.eE]+)\), "
    r"radius=(?P<radius>[-+0-9.eE]+), shell_thickness=(?P<thick>[-+0-9.eE]+), "
    r"target_mk=(?P<target>[-+0-9]+), value=(?P<value>[-+0-9.eE]+) Pa, "
    r"value_type=(?P<vtype>\w+), affected=(?P<affected>\d+), skipped=(?P<skipped>\d+), "
    r"radius_range=\[(?P<rmin>[-+0-9.eE]+),(?P<rmax>[-+0-9.eE]+)\], "
    r"boundary_residual_max=(?P<resid>[-+0-9.eE]+) Pa"
)

CONF_RE = re.compile(
    r"FlexibleConfiningStress CPU diagnostics: step=(?P<step>[-+0-9.eE]+), "
    r"TimeStep=(?P<time>[-+0-9.eE]+), p0_eff=(?P<p0>[-+0-9.eE]+) Pa, "
    r"targets=(?P<targets>\d+), net_force=\((?P<fx>[-+0-9.eE]+),(?P<fy>[-+0-9.eE]+),(?P<fz>[-+0-9.eE]+)\) N, "
    r"total_abs_force=(?P<fabs>[-+0-9.eE]+) N, max_accel=(?P<amax>[-+0-9.eE]+) m/s2, "
    r"com_accel=(?P<acom>[-+0-9.eE]+) m/s2, symmetry_residual=(?P<sym>[-+0-9.eE]+)"
)

CLAMP_RE = re.compile(
    r"Curved drained diagnostic clamp: stage=(?P<stage>[^,]+), TimeStep=(?P<time>[-+0-9.eE]+), "
    r"mode=2, affected=(?P<affected>\d+), skipped=(?P<skipped>\d+), "
    r"radius_range=\[(?P<rmin>[-+0-9.eE]+),(?P<rmax>[-+0-9.eE]+)\], "
    r"value=(?P<value>[-+0-9.eE]+) Pa, value_type=(?P<vtype>\w+), "
    r"before=\[(?P<beforemin>[-+0-9.eE]+),(?P<beforemax>[-+0-9.eE]+)\] Pa, "
    r"after=\[(?P<aftermin>[-+0-9.eE]+),(?P<aftermax>[-+0-9.eE]+)\] Pa"
)

QUAD_RE = re.compile(
    r"CPU curved drained quadrature: material_targets=(?P<targets>\d+), "
    r"boundary_samples=(?P<samples>\d+), average_samples=(?P<avg>[-+0-9.eE]+), "
    r"quadrature_volume_scale=(?P<scale>[-+0-9.eE]+)"
)

BNDPART_RE = re.compile(
    r"CPU curved drained boundary-particle Dirichlet: selected_boundary_particles=(?P<selected>\d+), "
    r"material_targets=(?P<targets>\d+), material_boundary_pairs=(?P<pairs>\d+), "
    r"average_pairs=(?P<avg>[-+0-9.eE]+), target_mkbound=(?P<mkbound>[-+0-9]+), "
    r"selection_tolerance=(?P<tol>[-+0-9.eE]+), prescribed_value=(?P<value>[-+0-9.eE]+) Pa, "
    r"value_type=(?P<vtype>\w+), AdamiDiagnostic=(?P<adami>\w+), "
    r"Adami_samples=(?P<adami_samples>\d+), Adami_fallback=(?P<adami_fallback>\d+), "
    r"Adami_mean_abs_excess=(?P<adami_mean_abs_excess>[-+0-9.eE]+) Pa, "
    r"Adami_max_abs_excess=(?P<adami_max_abs_excess>[-+0-9.eE]+) Pa"
)

BNDWEIGHT_RE = re.compile(
    r"CPU curved drained boundary-particle weighting: mode=(?P<weighting>[-+0-9]+), "
    r"weighted_targets=(?P<targets>\d+), mean_Sm=(?P<mean_sm>[-+0-9.eE]+), "
    r"max_Sm=(?P<max_sm>[-+0-9.eE]+), mean_Sb=(?P<mean_sb>[-+0-9.eE]+), "
    r"max_Sb=(?P<max_sb>[-+0-9.eE]+), mean_boundary_fraction=(?P<mean_boundary_fraction>[-+0-9.eE]+), "
    r"max_boundary_fraction=(?P<max_boundary_fraction>[-+0-9.eE]+), mean_scale=(?P<mean_scale>[-+0-9.eE]+), "
    r"min_scale=(?P<min_scale>[-+0-9.eE]+), max_scale=(?P<max_scale>[-+0-9.eE]+)"
)


def fnum(value: object, default: float = math.nan) -> float:
    try:
        return float(str(value).strip().rstrip("."))
    except Exception:
        return default


def percentile(values: list[float], pct: float) -> float:
    data = sorted(v for v in values if math.isfinite(v))
    if not data:
        return math.nan
    if len(data) == 1:
        return data[0]
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
        "p90_abs": percentile(absv, 90.0),
        "p95_abs": percentile(absv, 95.0),
        "p99_abs": percentile(absv, 99.0),
        "max": max(vals) if vals else math.nan,
        "maxAbs": max(absv) if absv else math.nan,
    }


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


def read_runout(case_name: str) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], dict[int, float]]:
    runout = ROOT / f"{case_name}_cpu_out" / "Run.out"
    meta: dict[str, object] = {"runout_exists": runout.exists(), "code": "unknown", "excluded": "unknown"}
    curved: list[dict[str, object]] = []
    conf: list[dict[str, object]] = []
    clamps: list[dict[str, object]] = []
    quads: list[dict[str, object]] = []
    bndparts: list[dict[str, object]] = []
    weights: list[dict[str, object]] = []
    times: dict[int, float] = {0: 0.0}
    if not runout.exists():
        return meta, curved, conf, clamps, quads, bndparts, weights, times
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
    for i, match in enumerate(CURVED_RE.finditer(text)):
        row = {k: fnum(v) for k, v in match.groupdict().items() if k not in ("active", "vtype")}
        row["active"] = match.group("active")
        row["value_type"] = match.group("vtype")
        row["diag_index"] = i
        curved.append(row)
    for match in CONF_RE.finditer(text):
        row = {k: fnum(v) for k, v in match.groupdict().items() if k != "targets"}
        row["targets"] = int(match.group("targets"))
        conf.append(row)
    for match in CLAMP_RE.finditer(text):
        row = {k: fnum(v) for k, v in match.groupdict().items() if k not in ("stage", "vtype")}
        row["stage"] = match.group("stage")
        row["value_type"] = match.group("vtype")
        clamps.append(row)
    for match in QUAD_RE.finditer(text):
        row = {k: fnum(v) for k, v in match.groupdict().items()}
        quads.append(row)
    for match in BNDPART_RE.finditer(text):
        row = {k: fnum(v) for k, v in match.groupdict().items() if k not in ("vtype", "adami")}
        row["value_type"] = match.group("vtype")
        row["adami"] = match.group("adami")
        bndparts.append(row)
    for match in BNDWEIGHT_RE.finditer(text):
        weights.append({k: fnum(v) for k, v in match.groupdict().items()})
    return meta, curved, conf, clamps, quads, bndparts, weights, times


def read_partcsv(case: dict[str, object], times: dict[int, float]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    case_name = str(case["case_name"])
    p0 = float(case["p0"])
    data_dir = ROOT / f"{case_name}_cpu_out" / "data"
    frame_rows: list[dict[str, object]] = []
    surface_rows: list[dict[str, object]] = []
    radial_rows: list[dict[str, object]] = []
    quality_rows: list[dict[str, object]] = []
    for iframe, path in enumerate(sorted(data_dir.glob("PartCsv_*.csv"))):
        lines = path.read_text(errors="ignore").splitlines()
        header_idx = None
        for i, line in enumerate(lines):
            if "PorePress" in line or "Kplastic" in line or "Pos" in line:
                header_idx = i
                break
        if header_idx is None:
            continue
        headers = split_line(lines[header_idx])
        cols = {
            "x": find_col(headers, ("Pos.x", "posx", "x")),
            "y": find_col(headers, ("Pos.y", "posy", "y")),
            "z": find_col(headers, ("Pos.z", "posz", "z")),
            "type": find_col(headers, ("Type",)),
            "p": find_col(headers, ("PorePress",)),
            "ex": find_col(headers, ("ExcessPorePress",)),
            "rate": find_col(headers, ("PorePressRate",)),
            "lap": find_col(headers, ("LapPorePress",)),
            "lapz": find_col(headers, ("LapZ",)),
            "div": find_col(headers, ("DivVel",)),
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
            x = fnum(vals[cols["x"]]); y = fnum(vals[cols["y"]]); z = fnum(vals[cols["z"]])
            row = {
                "r": math.sqrt(x*x + y*y + z*z),
                "p": fnum(vals[cols["p"]]) if cols["p"] is not None else math.nan,
                "ex": fnum(vals[cols["ex"]]) if cols["ex"] is not None else math.nan,
                "rate": fnum(vals[cols["rate"]]) if cols["rate"] is not None else math.nan,
                "lap": fnum(vals[cols["lap"]]) if cols["lap"] is not None else math.nan,
                "lapz": fnum(vals[cols["lapz"]]) if cols["lapz"] is not None else math.nan,
                "div": fnum(vals[cols["div"]]) if cols["div"] is not None else math.nan,
                "kp": fnum(vals[cols["kp"]]) if cols["kp"] is not None else 0.0,
            }
            particles.append(row)
        time = times.get(iframe, float(iframe))
        if iframe == 0 and particles:
            rvals = [p["r"] for p in particles]
            surface = [p["r"] for p in particles if p["r"] >= 0.85 * RADIUS]
            surface_err = [r - RADIUS for r in surface]
            mean_err = sum(surface_err) / len(surface_err) if surface_err else math.nan
            std_err = math.sqrt(sum((e - mean_err) ** 2 for e in surface_err) / len(surface_err)) if surface_err else math.nan
            quality_rows.append({
                "case": case["label"],
                "case_name": case_name,
                "kind": case["kind"],
                "resolution": case.get("resolution", ""),
                "configured_dp": case.get("dp", ""),
                "radius": RADIUS,
                "material_particle_count": len(particles),
                "surface_count_r085": len([r for r in rvals if r >= 0.85 * RADIUS]),
                "surface_count_r090": len([r for r in rvals if r >= 0.90 * RADIUS]),
                "surface_count_r095": len([r for r in rvals if r >= 0.95 * RADIUS]),
                "center_count_r010": len([r for r in rvals if r <= 0.10 * RADIUS]),
                "center_count_r015": len([r for r in rvals if r <= 0.15 * RADIUS]),
                "center_count_r020": len([r for r in rvals if r <= 0.20 * RADIUS]),
                "center_count_r030": len([r for r in rvals if r <= 0.30 * RADIUS]),
                "center_count_r040": len([r for r in rvals if r <= 0.40 * RADIUS]),
                "mean_radius": sum(rvals) / len(rvals),
                "max_radius": max(rvals),
                "mean_surface_radius_error": mean_err,
                "max_surface_radius_abs_error": max((abs(e) for e in surface_err), default=math.nan),
                "surface_roughness_std": std_err,
            })
        ex_vals = [p["ex"] for p in particles]
        rate_vals = [p["rate"] for p in particles]
        lap_vals = [p["lap"] for p in particles]
        lapz_vals = [p["lapz"] for p in particles]
        div_vals = [p["div"] for p in particles]
        kp_vals = [abs(p["kp"]) for p in particles]
        center = {}
        nearest = min(particles, key=lambda p: p["r"], default=None)
        if nearest:
            center["center_nearest_radius"] = nearest["r"]
            center["center_nearest_excess"] = nearest["ex"]
            center["center_nearest_excess_over_p0"] = nearest["ex"] / p0 if p0 and math.isfinite(nearest["ex"]) else math.nan
        for rad in CENTER_RADII:
            vals = [p["ex"] for p in particles if p["r"] <= rad and math.isfinite(p["ex"])]
            avg = sum(vals) / len(vals) if vals else math.nan
            key = f"r{rad/RADIUS:.2f}".replace(".", "p")
            center[f"center_avg_excess_{key}"] = avg
            center[f"center_avg_excess_over_p0_{key}"] = avg / p0 if p0 and math.isfinite(avg) else math.nan
            center[f"center_avg_count_{key}"] = len(vals)
        for thresh in SURFACE_THRESHOLDS:
            surf = [p["ex"] for p in particles if p["r"] >= thresh * RADIUS]
            s = stats(surf)
            surface_rows.append({
                "case": case["label"], "kind": case["kind"], "mode": case["mode"],
                "resolution": case.get("resolution", ""), "configured_dp": case.get("dp", ""),
                "frame_index": iframe, "time": time, "surface_threshold": thresh,
                **{f"surface_excess_{k}": v for k, v in s.items()},
            })
        for lo, hi in RADIAL_BINS:
            vals = [p["ex"] for p in particles if lo <= p["r"] / RADIUS < hi or (hi == 1.0 and lo <= p["r"] / RADIUS <= hi)]
            s = stats(vals)
            radial_rows.append({
                "case": case["label"], "kind": case["kind"], "mode": case["mode"],
                "resolution": case.get("resolution", ""), "configured_dp": case.get("dp", ""),
                "frame_index": iframe, "time": time, "r_over_R_min": lo, "r_over_R_max": hi,
                **{f"excess_{k}": v for k, v in s.items()},
            })
        surface_particles = [p for p in particles if p["r"] >= 0.85 * RADIUS]
        surface_lap = [p["lap"] for p in surface_particles]
        surface_rate = [p["rate"] for p in surface_particles]
        frame_rows.append({
            "case": case["label"],
            "case_name": case_name,
            "kind": case["kind"],
            "resolution": case.get("resolution", ""),
            "configured_dp": case.get("dp", ""),
            "mode": case["mode"],
            "frame_index": iframe,
            "time": time,
            "p0": p0,
            "particle_count": len(particles),
            "excess_mean": sum(ex_vals) / len(ex_vals) if ex_vals else math.nan,
            "excess_maxAbs": max((abs(v) for v in ex_vals), default=math.nan),
            "porepressrate_maxAbs": max((abs(v) for v in rate_vals), default=math.nan),
            "lap_maxAbs": max((abs(v) for v in lap_vals), default=math.nan),
            "lap_rate_contrib_maxAbs_est": DIFF_RATE_COEF * max((abs(v) for v in lap_vals), default=0.0),
            "surface_lap_maxAbs": max((abs(v) for v in surface_lap), default=math.nan),
            "surface_lap_rate_contrib_maxAbs_est": DIFF_RATE_COEF * max((abs(v) for v in surface_lap), default=0.0),
            "surface_porepressrate_maxAbs": max((abs(v) for v in surface_rate), default=math.nan),
            "lapz_rate_contrib_maxAbs_est": 0.0,
            "lapz_maxAbs": max((abs(v) for v in lapz_vals), default=math.nan),
            "div_rate_contrib_maxAbs_est": (WATER_BULK_MODULUS / POROSITY) * max((abs(v) for v in div_vals), default=0.0),
            "kplastic_maxAbs": max(kp_vals) if kp_vals else 0.0,
            **center,
        })
    return frame_rows, surface_rows, radial_rows, quality_rows


def read_vtk_vectors(blob: bytes, field_name: bytes, components: int) -> list[tuple[float, ...]] | None:
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
    return [tuple(values[i:i + components]) for i in range(0, nvalues, components)]


def read_vtk(case_name: str, times: dict[int, float]) -> list[dict[str, object]]:
    vtk_dir = ROOT / f"{case_name}_cpu_vtk_particles"
    paths = sorted(vtk_dir.glob("PartFluid_*.vtk"))
    if not paths:
        return []
    initial = read_vtk_vectors(paths[0].read_bytes(), b"POINTS", 3)
    if not initial:
        return []
    initial_com = tuple(sum(p[i] for p in initial) / len(initial) for i in range(3))
    rows: list[dict[str, object]] = []
    for iframe, path in enumerate(paths):
        blob = path.read_bytes()
        points = read_vtk_vectors(blob, b"POINTS", 3)
        vel = read_vtk_vectors(blob, b"Vel", 3)
        if not points or not vel:
            continue
        vmag = [math.sqrt(vx*vx + vy*vy + vz*vz) for vx, vy, vz in vel]
        com = tuple(sum(p[i] for p in points) / len(points) for i in range(3))
        drift = math.sqrt(sum((com[i] - initial_com[i]) ** 2 for i in range(3)))
        rows.append({
            "frame_index": iframe,
            "time": times.get(iframe, float(iframe)),
            "vel_max": max(vmag) if vmag else 0.0,
            "vel_mean": sum(vmag) / len(vmag) if vmag else 0.0,
            "com_drift": drift,
            "particle_count_vtk": len(points),
        })
    return rows


def merge_by_frame(a: list[dict[str, object]], b: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: dict[int, dict[str, object]] = {}
    for rows in (a, b):
        for row in rows:
            item = merged.setdefault(int(row["frame_index"]), {})
            item.update(row)
    return [merged[i] for i in sorted(merged)]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def generate_plots(frames: list[dict[str, object]], surfaces: list[dict[str, object]], radials: list[dict[str, object]], weights: list[dict[str, object]], quality: list[dict[str, object]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    figdir = ROOT / "figures"
    figdir.mkdir(exist_ok=True)

    def lines(name: str, rows: list[dict[str, object]], ykey: str, ylabel: str, case_filter=None) -> None:
        plt.figure(figsize=(7.2, 4.6))
        labels = sorted({str(r["case"]) for r in rows if case_filter is None or case_filter(r)})
        for label in labels:
            sub = [r for r in rows if str(r["case"]) == label and (case_filter is None or case_filter(r)) and math.isfinite(fnum(r.get(ykey)))]
            sub.sort(key=lambda r: fnum(r["time"]))
            if sub:
                plt.plot([fnum(r["time"]) for r in sub], [fnum(r[ykey]) for r in sub], marker="o", label=label)
        plt.xlabel("time [s]")
        plt.ylabel(ylabel)
        plt.grid(True, alpha=0.25)
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(figdir / f"{name}.png", dpi=180)
        plt.savefig(figdir / f"{name}.svg")
        plt.close()

    pk = "center_avg_excess_over_p0_r0p40"
    lines("c5g_center_normalized_pressure", frames, pk, "center excess / p0 [-]", lambda r: r["kind"] == "compression")
    lines("c5g_velocity_max", frames, "vel_max", "max velocity [m/s]")
    lines("c5g_kplastic_max", frames, "kplastic_maxAbs", "|Kplastic| max")
    lines("c5g_boundary_contribution_magnitude", frames, "surface_lap_rate_contrib_maxAbs_est", "surface LapPorePress rate contribution [Pa/s]")
    lines("c5g_pressure_only_mean_excess", frames, "excess_mean", "mean excess [Pa]", lambda r: r["kind"] == "diffusion")
    lines("c5g_surface_excess_p95_abs", surfaces, "surface_excess_p95_abs", "surface |excess| p95 [Pa]", lambda r: abs(fnum(r["surface_threshold"]) - 0.85) < 1e-9)
    lines("c5g_surface_excess_max_abs", surfaces, "surface_excess_maxAbs", "surface |excess| max [Pa]", lambda r: abs(fnum(r["surface_threshold"]) - 0.85) < 1e-9)
    lines("c5g_porepressrate_artifact_indicator", frames, "porepressrate_maxAbs", "|PorePressRate| max [Pa/s]")

    plt.figure(figsize=(7.2, 4.6))
    for label in ("coarse_compression", "finer_compression", "coarse_diffusion", "finer_diffusion"):
        suball = [r for r in radials if r["case"] == label]
        if not suball:
            continue
        tmax = max(fnum(r["time"]) for r in suball)
        sub = [r for r in suball if abs(fnum(r["time"]) - tmax) < 1e-12]
        sub.sort(key=lambda r: fnum(r["r_over_R_min"]))
        x = [(fnum(r["r_over_R_min"]) + fnum(r["r_over_R_max"])) / 2 for r in sub]
        y = [fnum(r["excess_mean"]) for r in sub]
        plt.plot(x, y, marker="o", label=label)
    plt.xlabel("r/R [-]")
    plt.ylabel("final radial-bin mean excess [Pa]")
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(figdir / "c5g_radial_pressure_profiles.png", dpi=180)
    plt.savefig(figdir / "c5g_radial_pressure_profiles.svg")
    plt.close()

    weight_rows = [r for r in weights if fnum(r.get("targets")) > 0]
    if weight_rows:
        labels = [str(r["case"]).replace("_", "\n") for r in weight_rows]
        x = list(range(len(weight_rows)))
        mean_scale = [fnum(r["mean_scale"]) for r in weight_rows]
        min_scale = [fnum(r["min_scale"]) for r in weight_rows]
        max_scale = [fnum(r["max_scale"]) for r in weight_rows]
        mean_fraction = [fnum(r["mean_boundary_fraction"]) for r in weight_rows]
        plt.figure(figsize=(8.2, 4.8))
        plt.bar(x, mean_scale, alpha=0.72, label="mean scale")
        plt.plot(x, min_scale, marker="v", linestyle="none", label="min scale")
        plt.plot(x, max_scale, marker="^", linestyle="none", label="max scale")
        plt.plot(x, mean_fraction, marker="o", linestyle="--", label="mean boundary fraction")
        plt.xticks(x, labels, fontsize=8)
        plt.ylabel("dimensionless scale / fraction")
        plt.grid(True, axis="y", alpha=0.25)
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(figdir / "c5g_normalized_boundary_scale_summary.png", dpi=180)
        plt.savefig(figdir / "c5g_normalized_boundary_scale_summary.svg")
        plt.close()

    if quality:
        labels = [str(r["case"]).replace("_", "\n") for r in quality]
        x = list(range(len(quality)))
        counts = [fnum(r["material_particle_count"]) for r in quality]
        surf_std = [fnum(r["surface_roughness_std"]) for r in quality]
        center_counts = [fnum(r["center_count_r020"]) for r in quality]
        plt.figure(figsize=(7.5, 4.6))
        plt.bar(x, counts, alpha=0.72)
        plt.xticks(x, labels, fontsize=8)
        plt.ylabel("material particle count")
        plt.grid(True, axis="y", alpha=0.25)
        plt.tight_layout()
        plt.savefig(figdir / "c5g_sphere_particle_count.png", dpi=180)
        plt.savefig(figdir / "c5g_sphere_particle_count.svg")
        plt.close()

        plt.figure(figsize=(7.5, 4.6))
        plt.plot(x, surf_std, marker="o", label="surface roughness std")
        plt.plot(x, center_counts, marker="s", label="center count r<0.2R")
        plt.xticks(x, labels, fontsize=8)
        plt.ylabel("roughness [m] / count")
        plt.grid(True, axis="y", alpha=0.25)
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(figdir / "c5g_sphere_quality_summary.png", dpi=180)
        plt.savefig(figdir / "c5g_sphere_quality_summary.svg")
        plt.close()

    plt.figure(figsize=(7.4, 4.6))
    for label in ("coarse_compression", "finer_compression"):
        sub = [r for r in frames if r["case"] == label and r["kind"] == "compression"]
        if not sub:
            continue
        peak = max(sub, key=lambda r: fnum(r.get("center_avg_excess_over_p0_r0p40")))
        x = [0.0]
        y = [fnum(peak.get("center_nearest_excess_over_p0"))]
        for rad in CENTER_RADII:
            key = f"r{rad/RADIUS:.2f}".replace(".", "p")
            x.append(rad / RADIUS)
            y.append(fnum(peak.get(f"center_avg_excess_over_p0_{key}")))
        plt.plot(x, y, marker="o", label=label)
    plt.xlabel("center averaging radius / R (0 = nearest)")
    plt.ylabel("peak-frame center excess / p0 [-]")
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(figdir / "c5g_center_averaging_sensitivity.png", dpi=180)
    plt.savefig(figdir / "c5g_center_averaging_sensitivity.svg")
    plt.close()


def write_surface_audit(surfaces: list[dict[str, object]], radials: list[dict[str, object]]) -> None:
    old_final = [r for r in surfaces if r["case"] == "coarse_compression" and abs(fnum(r["surface_threshold"]) - 0.85) < 1e-9]
    if old_final:
        tmax = max(fnum(r["time"]) for r in old_final)
        row = [r for r in old_final if abs(fnum(r["time"]) - tmax) < 1e-12][0]
        p95 = fnum(row["surface_excess_p95_abs"])
        mx = fnum(row["surface_excess_maxAbs"])
        mean = fnum(row["surface_excess_mean"])
        verdict = "systematic" if p95 > 0.5 * mx else "outlier-dominated"
    else:
        tmax = p95 = mx = mean = math.nan
        verdict = "unknown"
    text = [
        "# C5g Surface Residual Audit",
        "",
        "The detailed particle-field audit compares the coarse and one-level-finer normalized mode-4 sphere diagnostics.",
        "",
        f"For the raw mode-4 control at the final retained frame (`t={tmax:g} s`), the `r>0.85R` surface layer has mean excess `{mean:g} Pa`, p95 absolute excess `{p95:g} Pa`, and max absolute excess `{mx:g} Pa`.",
        "",
        f"Classification: `{verdict}`. The residual is not explained by the ghost residual diagnostic, because that log diagnostic samples the prescribed ghost state rather than the full material surface layer through time.",
        "",
        "The radial-bin CSV records whether residual changes are concentrated near `0.95R-1.0R` or spread through the outer shell.",
    ]
    (ROOT / "c5g_surface_residual_audit.md").write_text("\n".join(text) + "\n")


def main() -> None:
    frame_rows: list[dict[str, object]] = []
    surface_rows: list[dict[str, object]] = []
    radial_rows: list[dict[str, object]] = []
    boundary_rows: list[dict[str, object]] = []
    conf_rows: list[dict[str, object]] = []
    clamp_rows: list[dict[str, object]] = []
    quad_rows: list[dict[str, object]] = []
    bndpart_rows: list[dict[str, object]] = []
    weight_rows: list[dict[str, object]] = []
    quality_rows: list[dict[str, object]] = []
    center_sensitivity_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    primary_key = "center_avg_excess_r0p40"
    primary_norm_key = "center_avg_excess_over_p0_r0p40"
    for case in CASES:
        meta, curved, conf, clamps, quads, bndparts, weights, times = read_runout(str(case["case_name"]))
        csv_frames, csv_surfaces, csv_radials, csv_quality = read_partcsv(case, times)
        vtk_frames = read_vtk(str(case["case_name"]), times)
        frames = merge_by_frame(csv_frames, vtk_frames)
        for row in frames:
            frame_rows.append(row)
        for row in csv_surfaces:
            surface_rows.append(row)
        for row in csv_radials:
            radial_rows.append(row)
        for row in csv_quality:
            quality_rows.append(row)
        for row in curved:
            row["case"] = case["label"]
            row["kind"] = case["kind"]
            row["mode"] = case["mode"]
            boundary_rows.append(row)
        for row in conf:
            row["case"] = case["label"]
            conf_rows.append(row)
        for row in clamps:
            row["case"] = case["label"]
            clamp_rows.append(row)
        for row in quads:
            row["case"] = case["label"]
            row["kind"] = case["kind"]
            row["mode"] = case["mode"]
            quad_rows.append(row)
        for row in bndparts:
            row["case"] = case["label"]
            row["kind"] = case["kind"]
            row["mode"] = case["mode"]
            row["resolution"] = case.get("resolution", "")
            row["configured_dp"] = case.get("dp", "")
            bndpart_rows.append(row)
        for row in weights:
            row["case"] = case["label"]
            row["kind"] = case["kind"]
            row["mode"] = case["mode"]
            row["configured_weighting"] = case["weighting"]
            row["resolution"] = case.get("resolution", "")
            row["configured_dp"] = case.get("dp", "")
            weight_rows.append(row)

        center_frames = [r for r in frames if math.isfinite(fnum(r.get(primary_key)))]
        peak_row = max(center_frames, key=lambda r: fnum(r.get(primary_key)), default={})
        final = frames[-1] if frames else {}
        for row in frames:
            for rad in CENTER_RADII:
                key = f"r{rad/RADIUS:.2f}".replace(".", "p")
                center_sensitivity_rows.append({
                    "case": case["label"],
                    "case_name": case["case_name"],
                    "kind": case["kind"],
                    "resolution": case.get("resolution", ""),
                    "configured_dp": case.get("dp", ""),
                    "time": row.get("time", ""),
                    "frame_index": row.get("frame_index", ""),
                    "averaging_radius": rad,
                    "averaging_radius_over_R": rad / RADIUS,
                    "center_excess": row.get(f"center_avg_excess_{key}", ""),
                    "center_excess_over_p0": row.get(f"center_avg_excess_over_p0_{key}", ""),
                    "center_count": row.get(f"center_avg_count_{key}", ""),
                })
            center_sensitivity_rows.append({
                "case": case["label"],
                "case_name": case["case_name"],
                "kind": case["kind"],
                "resolution": case.get("resolution", ""),
                "configured_dp": case.get("dp", ""),
                "time": row.get("time", ""),
                "frame_index": row.get("frame_index", ""),
                "averaging_radius": "nearest",
                "averaging_radius_over_R": "nearest",
                "center_excess": row.get("center_nearest_excess", ""),
                "center_excess_over_p0": row.get("center_nearest_excess_over_p0", ""),
                "center_count": 1,
            })
        summary_rows.append({
            "case": case["label"],
            "case_name": case["case_name"],
            "kind": case["kind"],
            "resolution": case.get("resolution", ""),
            "configured_dp": case.get("dp", ""),
            "curved_mode": case["mode"],
            "configured_weighting": case["weighting"],
            "code": meta.get("code", ""),
            "excluded": meta.get("excluded", ""),
            "steps": meta.get("steps", ""),
            "runtime_sec": meta.get("runtime_sec", ""),
            "frames": len(frames),
            "particle_count_final": final.get("particle_count", ""),
            "p0": case["p0"],
            "peak_center_excess": peak_row.get(primary_key, ""),
            "peak_center_excess_over_p0": peak_row.get(primary_norm_key, ""),
            "peak_time": peak_row.get("time", ""),
            "final_center_excess": final.get(primary_key, ""),
            "final_center_excess_over_p0": final.get(primary_norm_key, ""),
            "final_surface_excess_maxAbs_r085": next((r["surface_excess_maxAbs"] for r in reversed(surface_rows) if r["case"] == case["label"] and abs(fnum(r["surface_threshold"]) - 0.85) < 1e-9), ""),
            "final_surface_excess_p95Abs_r085": next((r["surface_excess_p95_abs"] for r in reversed(surface_rows) if r["case"] == case["label"] and abs(fnum(r["surface_threshold"]) - 0.85) < 1e-9), ""),
            "final_velocity_max": final.get("vel_max", ""),
            "final_com_drift": final.get("com_drift", ""),
            "final_kplastic_maxAbs": final.get("kplastic_maxAbs", ""),
            "final_surface_lap_rate_contrib_maxAbs_est": final.get("surface_lap_rate_contrib_maxAbs_est", ""),
            "clamp_events": len([r for r in clamp_rows if r["case"] == case["label"]]),
            "quadrature_events": len([r for r in quad_rows if r["case"] == case["label"]]),
            "quadrature_boundary_samples": next((r["samples"] for r in reversed(quad_rows) if r["case"] == case["label"]), ""),
            "quadrature_material_targets": next((r["targets"] for r in reversed(quad_rows) if r["case"] == case["label"]), ""),
            "quadrature_average_samples": next((r["avg"] for r in reversed(quad_rows) if r["case"] == case["label"]), ""),
            "mode4_selected_boundary_particles": next((r["selected"] for r in reversed(bndpart_rows) if r["case"] == case["label"]), ""),
            "mode4_material_boundary_pairs": next((r["pairs"] for r in reversed(bndpart_rows) if r["case"] == case["label"]), ""),
            "mode4_average_pairs": next((r["avg"] for r in reversed(bndpart_rows) if r["case"] == case["label"]), ""),
            "mode4_adami_mean_abs_excess": next((r["adami_mean_abs_excess"] for r in reversed(bndpart_rows) if r["case"] == case["label"]), ""),
            "mode4_adami_max_abs_excess": next((r["adami_max_abs_excess"] for r in reversed(bndpart_rows) if r["case"] == case["label"]), ""),
            "weighting_mean_Sm": next((r["mean_sm"] for r in reversed(weight_rows) if r["case"] == case["label"]), ""),
            "weighting_max_Sm": next((r["max_sm"] for r in reversed(weight_rows) if r["case"] == case["label"]), ""),
            "weighting_mean_Sb": next((r["mean_sb"] for r in reversed(weight_rows) if r["case"] == case["label"]), ""),
            "weighting_max_Sb": next((r["max_sb"] for r in reversed(weight_rows) if r["case"] == case["label"]), ""),
            "weighting_mean_scale": next((r["mean_scale"] for r in reversed(weight_rows) if r["case"] == case["label"]), ""),
            "weighting_min_scale": next((r["min_scale"] for r in reversed(weight_rows) if r["case"] == case["label"]), ""),
            "weighting_max_scale": next((r["max_scale"] for r in reversed(weight_rows) if r["case"] == case["label"]), ""),
            "weighting_mean_boundary_fraction": next((r["mean_boundary_fraction"] for r in reversed(weight_rows) if r["case"] == case["label"]), ""),
        })

    for q in quality_rows:
        match = next((r for r in bndpart_rows if r["case"] == q["case"]), None)
        if match:
            q["selected_boundary_particle_count"] = match.get("selected", "")
            q["material_boundary_pair_count"] = match.get("pairs", "")
    write_csv(ROOT / "c5g_case_summary.csv", summary_rows)
    write_csv(ROOT / "c5g_sphere_quality_metrics.csv", quality_rows)
    write_csv(ROOT / "c5g_geometry_comparison_metrics.csv", quality_rows)
    write_csv(ROOT / "c5g_center_pressure_comparison.csv", frame_rows)
    write_csv(ROOT / "c5g_surface_residual_comparison.csv", surface_rows)
    write_csv(ROOT / "c5g_center_averaging_sensitivity.csv", center_sensitivity_rows)
    write_csv(ROOT / "c5g_radial_profile_metrics.csv", radial_rows)
    write_csv(ROOT / "c5g_boundary_selection_metrics.csv", bndpart_rows)
    write_csv(ROOT / "c5g_boundary_operator_contribution_metrics.csv", frame_rows)
    write_csv(ROOT / "c5g_weighting_diagnostics.csv", weight_rows)
    write_csv(ROOT / "c5g_pressure_only_diffusion_metrics.csv", [r for r in frame_rows if r["kind"] == "diffusion"])
    write_csv(ROOT / "c5g_pressure_rate_artifact_metrics.csv", frame_rows)
    write_csv(ROOT / "c5g_flexible_confining_stress_metrics.csv", conf_rows)
    write_csv(ROOT / "c5g_adami_diagnostic_metrics.csv", bndpart_rows)
    write_surface_audit(surface_rows, radial_rows)
    generate_plots(frame_rows, surface_rows, radial_rows, weight_rows, quality_rows)


if __name__ == "__main__":
    main()
