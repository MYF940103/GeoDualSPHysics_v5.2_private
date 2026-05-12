#!/usr/bin/env python3
"""Analyze C5d curved drained boundary coupling tests."""

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
CENTER_RADII = [0.01, 0.02]
PRIMARY_CENTER_RADIUS = 0.02
SURFACE_THRESHOLDS = [0.85, 0.90, 0.95]
RADIAL_BINS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 0.95), (0.95, 1.0)]

CASES = [
    {"label": "old_ghost", "case_name": "CaseCryer_PR_StrictSphere_C5d_OldGhost", "kind": "compression", "mode": 0, "p0": 50.0},
    {"label": "strong_ghost", "case_name": "CaseCryer_PR_StrictSphere_C5d_StrongGhost", "kind": "compression", "mode": 1, "p0": 50.0},
    {"label": "quadrature", "case_name": "CaseCryer_PR_StrictSphere_C5d_Quadrature", "kind": "compression", "mode": 3, "p0": 50.0},
    {"label": "surface_clamp", "case_name": "CaseCryer_PR_StrictSphere_C5d_SurfaceClamp", "kind": "compression", "mode": 2, "p0": 50.0},
    {"label": "diffusion_old", "case_name": "CaseCryer_PR_StrictSphere_C5d_DiffusionOld", "kind": "diffusion", "mode": 0, "p0": 0.0},
    {"label": "diffusion_strong", "case_name": "CaseCryer_PR_StrictSphere_C5d_DiffusionStrong", "kind": "diffusion", "mode": 1, "p0": 0.0},
    {"label": "diffusion_quadrature", "case_name": "CaseCryer_PR_StrictSphere_C5d_DiffusionQuadrature", "kind": "diffusion", "mode": 3, "p0": 0.0},
    {"label": "diffusion_clamp", "case_name": "CaseCryer_PR_StrictSphere_C5d_DiffusionClamp", "kind": "diffusion", "mode": 2, "p0": 0.0},
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


def read_runout(case_name: str) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], dict[int, float]]:
    runout = ROOT / f"{case_name}_cpu_out" / "Run.out"
    meta: dict[str, object] = {"runout_exists": runout.exists(), "code": "unknown", "excluded": "unknown"}
    curved: list[dict[str, object]] = []
    conf: list[dict[str, object]] = []
    clamps: list[dict[str, object]] = []
    quads: list[dict[str, object]] = []
    times: dict[int, float] = {0: 0.0}
    if not runout.exists():
        return meta, curved, conf, clamps, quads, times
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
    return meta, curved, conf, clamps, quads, times


def read_partcsv(case: dict[str, object], times: dict[int, float]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    case_name = str(case["case_name"])
    p0 = float(case["p0"])
    data_dir = ROOT / f"{case_name}_cpu_out" / "data"
    frame_rows: list[dict[str, object]] = []
    surface_rows: list[dict[str, object]] = []
    radial_rows: list[dict[str, object]] = []
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
        ex_vals = [p["ex"] for p in particles]
        rate_vals = [p["rate"] for p in particles]
        lap_vals = [p["lap"] for p in particles]
        lapz_vals = [p["lapz"] for p in particles]
        div_vals = [p["div"] for p in particles]
        kp_vals = [abs(p["kp"]) for p in particles]
        center = {}
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
                "frame_index": iframe, "time": time, "surface_threshold": thresh,
                **{f"surface_excess_{k}": v for k, v in s.items()},
            })
        for lo, hi in RADIAL_BINS:
            vals = [p["ex"] for p in particles if lo <= p["r"] / RADIUS < hi or (hi == 1.0 and lo <= p["r"] / RADIUS <= hi)]
            s = stats(vals)
            radial_rows.append({
                "case": case["label"], "kind": case["kind"], "mode": case["mode"],
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
    return frame_rows, surface_rows, radial_rows


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


def generate_plots(frames: list[dict[str, object]], surfaces: list[dict[str, object]], radials: list[dict[str, object]]) -> None:
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
    lines("c5d_center_normalized_pressure_old_vs_new", frames, pk, "center excess / p0 [-]", lambda r: r["kind"] == "compression")
    lines("c5d_velocity_max", frames, "vel_max", "max velocity [m/s]")
    lines("c5d_kplastic_max", frames, "kplastic_maxAbs", "|Kplastic| max")
    lines("c5d_boundary_contribution_magnitude", frames, "surface_lap_rate_contrib_maxAbs_est", "surface LapPorePress rate contribution [Pa/s]")
    lines("c5d_pressure_only_diffusion_mean_excess", frames, "excess_mean", "mean excess [Pa]", lambda r: r["kind"] == "diffusion")
    lines("c5d_diagnostic_clamp_center_effect", frames, pk, "center excess / p0 [-]", lambda r: r["case"] in ("old_ghost", "strong_ghost", "quadrature", "surface_clamp"))
    lines("c5d_surface_excess_p95_abs", surfaces, "surface_excess_p95_abs", "surface |excess| p95 [Pa]", lambda r: abs(fnum(r["surface_threshold"]) - 0.85) < 1e-9)
    lines("c5d_surface_excess_max_abs", surfaces, "surface_excess_maxAbs", "surface |excess| max [Pa]", lambda r: abs(fnum(r["surface_threshold"]) - 0.85) < 1e-9)
    lines("c5d_porepressrate_artifact_indicator", frames, "porepressrate_maxAbs", "|PorePressRate| max [Pa/s]")

    plt.figure(figsize=(7.2, 4.6))
    for label in ("old_ghost", "strong_ghost", "quadrature", "surface_clamp"):
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
    plt.savefig(figdir / "c5d_radial_pressure_profiles_old_vs_new.png", dpi=180)
    plt.savefig(figdir / "c5d_radial_pressure_profiles_old_vs_new.svg")
    plt.close()


def write_surface_audit(surfaces: list[dict[str, object]], radials: list[dict[str, object]]) -> None:
    old_final = [r for r in surfaces if r["case"] == "old_ghost" and abs(fnum(r["surface_threshold"]) - 0.85) < 1e-9]
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
        "# C5d Surface Residual Audit",
        "",
        "The detailed particle-field audit was rerun under the C5d old-ghost case because C5b retained only frame summaries after raw-output cleanup.",
        "",
        f"For the old mode-3 ghost at the final retained frame (`t={tmax:g} s`), the `r>0.85R` surface layer has mean excess `{mean:g} Pa`, p95 absolute excess `{p95:g} Pa`, and max absolute excess `{mx:g} Pa`.",
        "",
        f"Classification: `{verdict}`. The residual is not explained by the ghost residual diagnostic, because that log diagnostic samples the prescribed ghost state rather than the full material surface layer through time.",
        "",
        "The radial-bin CSV records whether the residual is concentrated near `0.95R-1.0R` or spread through the outer shell.",
    ]
    (ROOT / "c5d_surface_residual_audit.md").write_text("\n".join(text) + "\n")


def main() -> None:
    frame_rows: list[dict[str, object]] = []
    surface_rows: list[dict[str, object]] = []
    radial_rows: list[dict[str, object]] = []
    boundary_rows: list[dict[str, object]] = []
    conf_rows: list[dict[str, object]] = []
    clamp_rows: list[dict[str, object]] = []
    quad_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    primary_key = "center_avg_excess_r0p40"
    primary_norm_key = "center_avg_excess_over_p0_r0p40"
    for case in CASES:
        meta, curved, conf, clamps, quads, times = read_runout(str(case["case_name"]))
        csv_frames, csv_surfaces, csv_radials = read_partcsv(case, times)
        vtk_frames = read_vtk(str(case["case_name"]), times)
        frames = merge_by_frame(csv_frames, vtk_frames)
        for row in frames:
            frame_rows.append(row)
        for row in csv_surfaces:
            surface_rows.append(row)
        for row in csv_radials:
            radial_rows.append(row)
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

        center_frames = [r for r in frames if math.isfinite(fnum(r.get(primary_key)))]
        peak_row = max(center_frames, key=lambda r: fnum(r.get(primary_key)), default={})
        final = frames[-1] if frames else {}
        summary_rows.append({
            "case": case["label"],
            "case_name": case["case_name"],
            "kind": case["kind"],
            "curved_mode": case["mode"],
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
        })

    write_csv(ROOT / "c5d_case_summary.csv", summary_rows)
    write_csv(ROOT / "c5d_center_pressure_comparison.csv", frame_rows)
    write_csv(ROOT / "c5d_surface_residual_comparison.csv", surface_rows)
    write_csv(ROOT / "c5d_surface_residual_audit.csv", surface_rows)
    write_csv(ROOT / "c5d_radial_excess_bins.csv", radial_rows)
    write_csv(ROOT / "c5d_radial_excess_profiles.csv", radial_rows)
    write_csv(ROOT / "c5d_boundary_contribution_metrics.csv", frame_rows)
    write_csv(ROOT / "c5d_boundary_quadrature_metrics.csv", quad_rows)
    write_csv(ROOT / "c5d_pressure_only_diffusion_metrics.csv", [r for r in frame_rows if r["kind"] == "diffusion"])
    write_csv(ROOT / "c5d_pressure_rate_artifact_metrics.csv", frame_rows)
    write_csv(ROOT / "c5d_flexible_confining_stress_metrics.csv", conf_rows)
    write_csv(ROOT / "c5d_clamp_diagnostics.csv", clamp_rows)
    write_surface_audit(surface_rows, radial_rows)
    generate_plots(frame_rows, surface_rows, radial_rows)


if __name__ == "__main__":
    main()
