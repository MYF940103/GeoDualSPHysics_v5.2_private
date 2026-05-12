#!/usr/bin/env python3
"""Analyze C5b strict-sphere Cryer refinement outputs."""

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
CV_EST = HYDRAULIC_CONDUCTIVITY * WATER_BULK_MODULUS / (POROSITY * WATER_DENSITY * HYDRAULIC_G)
CENTER_AVG_RADII = [0.005, 0.0075, 0.01, 0.02]
PRIMARY_AVG_RADIUS = 0.01
SURFACE_FRAC = 0.85
INTERIOR_FRAC = 0.50
CASES = [
    {"label": "baseline", "case_name": "CaseCryer_PR_StrictSphere_C5b_Baseline", "p0": 50.0, "ramp_end": 0.0005, "time_max": 0.006},
    {"label": "slow_ramp", "case_name": "CaseCryer_PR_StrictSphere_C5b_SlowRamp", "p0": 50.0, "ramp_end": 0.005, "time_max": 0.012},
    {"label": "lower_p0", "case_name": "CaseCryer_PR_StrictSphere_C5b_LowerP0", "p0": 10.0, "ramp_end": 0.0005, "time_max": 0.006},
    {"label": "long_slow_ramp", "case_name": "CaseCryer_PR_StrictSphere_C5b_LongSlowRamp", "p0": 50.0, "ramp_end": 0.005, "time_max": 0.05},
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


def fnum(value: object, default: float = math.nan) -> float:
    try:
        return float(str(value).strip().rstrip("."))
    except Exception:
        return default


def split_line(line: str) -> list[str]:
    sep = ";" if ";" in line else ","
    return [v.strip() for v in line.strip().split(sep)]


def find_col(headers: list[str], candidates: tuple[str, ...]) -> int | None:
    lower = [h.lower().split()[0] if h.strip() else "" for h in headers]
    for cand in candidates:
        cl = cand.lower()
        for i, header in enumerate(lower):
            if header == cl:
                return i
            if len(cl) > 1 and (header.endswith("." + cl) or header.endswith("_" + cl)):
                return i
    return None


def read_runout(case_name: str) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]], dict[int, float]]:
    runout = ROOT / f"{case_name}_cpu_out" / "Run.out"
    meta: dict[str, object] = {"runout_exists": runout.exists(), "code": "unknown", "excluded": "unknown"}
    curved: list[dict[str, object]] = []
    conf: list[dict[str, object]] = []
    times: dict[int, float] = {0: 0.0}
    if not runout.exists():
        return meta, curved, conf, times
    text = runout.read_text(errors="ignore")
    meta["code"] = 0 if ("Finished execution" in text or "Execution finished" in text) else "unknown"
    m = re.search(r"Excluded particles\.*:\s*(\d+)", text)
    if not m:
        m = re.search(r"Particles out:\s*(\d+)", text)
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
    return meta, curved, conf, times



def radius_key(radius: float) -> str:
    return f"r{radius / RADIUS:.2f}".replace(".", "p")


def read_partcsv(case_name: str, times: dict[int, float], p0: float) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    data_dir = ROOT / f"{case_name}_cpu_out" / "data"
    rows: list[dict[str, object]] = []
    avg_rows: list[dict[str, object]] = []
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
        idx = {
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
        vals_by_key = {key: [] for key in ("p", "ex", "rate", "lap", "lapz", "div", "kp")}
        center_ex = math.nan
        center_p = math.nan
        center_r = math.inf
        center_avg_p = {radius: [] for radius in CENTER_AVG_RADII}
        center_avg_ex = {radius: [] for radius in CENTER_AVG_RADII}
        surf_ex: list[float] = []
        interior_ex: list[float] = []
        count = 0
        for line in lines[header_idx + 1:]:
            if not line.strip() or line.startswith("#"):
                continue
            vals = split_line(line)
            count += 1
            rowvals: dict[str, float] = {}
            for key in vals_by_key:
                col = idx[key]
                value = fnum(vals[col]) if col is not None and col < len(vals) else math.nan
                rowvals[key] = value
                if math.isfinite(value):
                    vals_by_key[key].append(abs(value) if key == "kp" else value)
            if idx["x"] is not None and idx["y"] is not None and idx["z"] is not None:
                x = fnum(vals[idx["x"]]); y = fnum(vals[idx["y"]]); z = fnum(vals[idx["z"]])
                r = math.sqrt(x*x + y*y + z*z)
                ex = rowvals["ex"]
                if r < center_r:
                    center_r = r
                    center_p = rowvals["p"]
                    center_ex = ex
                for radius in CENTER_AVG_RADII:
                    if r <= radius:
                        if math.isfinite(rowvals["p"]):
                            center_avg_p[radius].append(rowvals["p"])
                        if math.isfinite(ex):
                            center_avg_ex[radius].append(ex)
                if math.isfinite(ex) and r > SURFACE_FRAC * RADIUS:
                    surf_ex.append(ex)
                if math.isfinite(ex) and r < INTERIOR_FRAC * RADIUS:
                    interior_ex.append(ex)
        time = times.get(iframe, float(iframe))
        row = {
            "frame_index": iframe,
            "time": time,
            "Tv_est": CV_EST * time / (RADIUS * RADIUS),
            "frame_file": path.name,
            "particle_count_csv": count,
            "PorePress_max": max(vals_by_key["p"]) if vals_by_key["p"] else math.nan,
            "PorePress_mean": sum(vals_by_key["p"]) / len(vals_by_key["p"]) if vals_by_key["p"] else math.nan,
            "ExcessPorePress_max": max(vals_by_key["ex"]) if vals_by_key["ex"] else math.nan,
            "ExcessPorePress_mean": sum(vals_by_key["ex"]) / len(vals_by_key["ex"]) if vals_by_key["ex"] else math.nan,
            "ExcessPorePress_maxAbs": max((abs(v) for v in vals_by_key["ex"]), default=math.nan),
            "surface_ExcessPorePress_mean": sum(surf_ex) / len(surf_ex) if surf_ex else math.nan,
            "surface_ExcessPorePress_maxAbs": max((abs(v) for v in surf_ex), default=math.nan),
            "interior_ExcessPorePress_mean": sum(interior_ex) / len(interior_ex) if interior_ex else math.nan,
            "PorePressRate_maxAbs": max((abs(v) for v in vals_by_key["rate"]), default=math.nan),
            "LapPorePress_maxAbs": max((abs(v) for v in vals_by_key["lap"]), default=math.nan),
            "LapZ_maxAbs": max((abs(v) for v in vals_by_key["lapz"]), default=math.nan),
            "DivVel_maxAbs": max((abs(v) for v in vals_by_key["div"]), default=math.nan),
            "DivVel_rate_contribution_maxAbs_est": (WATER_BULK_MODULUS / POROSITY) * max((abs(v) for v in vals_by_key["div"]), default=0.0),
            "LapPorePress_rate_contribution_maxAbs_est": (WATER_BULK_MODULUS / POROSITY) * (HYDRAULIC_CONDUCTIVITY / (WATER_DENSITY * HYDRAULIC_G)) * max((abs(v) for v in vals_by_key["lap"]), default=0.0),
            "LapZ_rate_contribution_maxAbs_est": 0.0,
            "HydraulicElevationSource": 0,
            "center_PorePress": center_p,
            "center_ExcessPorePress": center_ex,
            "center_PorePress_over_p0": center_p / p0 if math.isfinite(center_p) and p0 else math.nan,
            "center_ExcessPorePress_over_p0": center_ex / p0 if math.isfinite(center_ex) and p0 else math.nan,
            "center_radius": center_r,
            "Kplastic_maxAbs": max(vals_by_key["kp"]) if vals_by_key["kp"] else 0.0,
        }
        for radius in CENTER_AVG_RADII:
            key = radius_key(radius)
            pvals = center_avg_p[radius]
            exvals = center_avg_ex[radius]
            avg_p = sum(pvals) / len(pvals) if pvals else math.nan
            avg_ex = sum(exvals) / len(exvals) if exvals else math.nan
            row[f"center_avg_count_{key}"] = len(exvals)
            row[f"center_avg_PorePress_{key}"] = avg_p
            row[f"center_avg_ExcessPorePress_{key}"] = avg_ex
            row[f"center_avg_ExcessPorePress_over_p0_{key}"] = avg_ex / p0 if math.isfinite(avg_ex) and p0 else math.nan
            avg_rows.append({
                "frame_index": iframe,
                "time": time,
                "Tv_est": row["Tv_est"],
                "radius": radius,
                "radius_over_R": radius / RADIUS,
                "count": len(exvals),
                "center_avg_PorePress": avg_p,
                "center_avg_ExcessPorePress": avg_ex,
                "center_avg_ExcessPorePress_over_p0": avg_ex / p0 if math.isfinite(avg_ex) and p0 else math.nan,
            })
        rows.append(row)
    return rows, avg_rows

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
    initial_r = [math.sqrt(x*x + y*y + z*z) for x, y, z in initial]
    rows: list[dict[str, object]] = []
    for iframe, path in enumerate(paths):
        blob = path.read_bytes()
        points = read_vtk_vectors(blob, b"POINTS", 3)
        vel = read_vtk_vectors(blob, b"Vel", 3)
        if not points or not vel:
            continue
        vmag: list[float] = []
        surf_rv: list[float] = []
        surf_disp: list[float] = []
        for p, v, r0 in zip(points, vel, initial_r):
            x, y, z = p
            vx, vy, vz = v
            r = math.sqrt(x*x + y*y + z*z)
            vm = math.sqrt(vx*vx + vy*vy + vz*vz)
            vmag.append(vm)
            rv = (x*vx + y*vy + z*vz) / r if r > 0 else 0.0
            if r0 > SURFACE_FRAC * RADIUS:
                surf_rv.append(rv)
                surf_disp.append(r - r0)
        rows.append({
            "frame_index": iframe,
            "time": times.get(iframe, float(iframe)),
            "frame_file": path.name,
            "particle_count_vtk": len(points),
            "vel_max": max(vmag) if vmag else 0.0,
            "vel_mean": sum(vmag) / len(vmag) if vmag else 0.0,
            "surface_radial_vel_mean": sum(surf_rv) / len(surf_rv) if surf_rv else 0.0,
            "surface_radial_disp_mean": sum(surf_disp) / len(surf_disp) if surf_disp else 0.0,
        })
    return rows


def merge_rows(*rowsets: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: dict[int, dict[str, object]] = {}
    for rows in rowsets:
        for row in rows:
            item = merged.setdefault(int(row["frame_index"]), {})
            item.update(row)
    return [merged[k] for k in sorted(merged)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})



def plot(all_rows: list[dict[str, object]], residual_rows: list[dict[str, object]], avg_rows: list[dict[str, object]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig_dir = ROOT / "figures"
    fig_dir.mkdir(exist_ok=True)

    def lineplot(name: str, ykey: str, ylabel: str) -> None:
        plt.figure(figsize=(7, 4.5))
        for case in sorted({str(r["case"]) for r in all_rows}):
            sub = [r for r in all_rows if r["case"] == case and str(r.get(ykey, "")) != ""]
            if not sub:
                continue
            sub.sort(key=lambda r: float(r["time"]))
            plt.plot([float(r["time"]) for r in sub], [float(r[ykey]) for r in sub], marker="o", label=case)
        plt.xlabel("time [s]")
        plt.ylabel(ylabel)
        plt.title(name.replace("_", " "))
        plt.grid(True, alpha=0.25)
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(fig_dir / f"{name}.png", dpi=180)
        plt.savefig(fig_dir / f"{name}.svg")
        plt.close()

    pk = radius_key(PRIMARY_AVG_RADIUS)
    lineplot("c5b_center_normalized_pressure_primary_radius", f"center_avg_ExcessPorePress_over_p0_{pk}", "center excess / p0 [-]")
    lineplot("c5b_near_surface_material_excess", "surface_ExcessPorePress_maxAbs", "surface |excess| max [Pa]")
    lineplot("c5b_velocity_max", "vel_max", "max velocity [m/s]")
    lineplot("c5b_kplastic_maxabs", "Kplastic_maxAbs", "|Kplastic| max")
    lineplot("c5b_lapz_rate_contribution", "LapZ_rate_contribution_maxAbs_est", "used |Kw/n k LapZ| max [Pa/s]")
    lineplot("c5b_porepress_rate_maxabs", "PorePressRate_maxAbs", "|PorePressRate| max [Pa/s]")
    lineplot("c5b_surface_radial_velocity", "surface_radial_vel_mean", "surface radial velocity mean [m/s]")

    if avg_rows:
        plt.figure(figsize=(7, 4.5))
        for case in sorted({str(r["case"]) for r in avg_rows}):
            final = [r for r in avg_rows if r["case"] == case]
            max_time = max(float(r["time"]) for r in final)
            sub = [r for r in final if abs(float(r["time"]) - max_time) < 1e-12]
            sub.sort(key=lambda r: float(r["radius_over_R"]))
            plt.plot([float(r["radius_over_R"]) for r in sub], [float(r["center_avg_ExcessPorePress_over_p0"]) for r in sub], marker="o", label=case)
        plt.xlabel("center averaging radius / R [-]")
        plt.ylabel("final averaged center excess / p0 [-]")
        plt.title("C5b center averaging sensitivity")
        plt.grid(True, alpha=0.25)
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(fig_dir / "c5b_center_averaging_radius_sensitivity.png", dpi=180)
        plt.savefig(fig_dir / "c5b_center_averaging_radius_sensitivity.svg")
        plt.close()

    if residual_rows:
        plt.figure(figsize=(7, 4.5))
        for case in sorted({str(r["case"]) for r in residual_rows}):
            sub = [r for r in residual_rows if r["case"] == case]
            plt.plot(range(len(sub)), [float(r["boundary_residual_max"]) for r in sub], marker="o", label=case)
        plt.xlabel("operator diagnostic index")
        plt.ylabel("boundary residual max [Pa]")
        plt.title("C5b curved drained operator residual")
        plt.grid(True, alpha=0.25)
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(fig_dir / "c5b_operator_boundary_residual.png", dpi=180)
        plt.savefig(fig_dir / "c5b_operator_boundary_residual.svg")
        plt.close()


def main() -> None:
    all_rows: list[dict[str, object]] = []
    avg_rows_all: list[dict[str, object]] = []
    residual_rows: list[dict[str, object]] = []
    conf_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    avg_summary_rows: list[dict[str, object]] = []

    primary_key = radius_key(PRIMARY_AVG_RADIUS)
    for case in CASES:
        label = str(case["label"])
        case_name = str(case["case_name"])
        p0 = float(case["p0"])
        meta, curved, conf, times = read_runout(case_name)
        csv_rows, avg_rows = read_partcsv(case_name, times, p0)
        vtk_rows = read_vtk(case_name, times)
        merged = merge_rows(csv_rows, vtk_rows)
        for row in merged:
            row["case"] = label
            row["case_name"] = case_name
            row["p0"] = p0
            row["ramp_end"] = case["ramp_end"]
            row["time_max_requested"] = case["time_max"]
            all_rows.append(row)
        for row in avg_rows:
            row["case"] = label
            row["p0"] = p0
            avg_rows_all.append(row)
        for row in curved:
            row["case"] = label
            row["boundary_residual_max"] = row.get("resid", "")
            residual_rows.append(row)
        for row in conf:
            row["case"] = label
            conf_rows.append(row)

        final = merged[-1] if merged else {}
        final_curve = curved[-1] if curved else {}
        final_conf = conf[-1] if conf else {}
        center_rows = [r for r in merged if math.isfinite(fnum(r.get(f"center_avg_ExcessPorePress_{primary_key}")))]
        peak_center = max((fnum(r.get(f"center_avg_ExcessPorePress_{primary_key}")) for r in center_rows), default=math.nan)
        peak_row = max(center_rows, key=lambda r: fnum(r.get(f"center_avg_ExcessPorePress_{primary_key}")), default={})
        final_center = fnum(final.get(f"center_avg_ExcessPorePress_{primary_key}"))
        summary_rows.append({
            "case": label,
            "case_name": case_name,
            "code": meta.get("code", ""),
            "excluded": meta.get("excluded", ""),
            "steps": meta.get("steps", ""),
            "runtime_sec": meta.get("runtime_sec", ""),
            "frames": len(merged),
            "particle_count": final.get("particle_count_csv", ""),
            "p0": p0,
            "ramp_end": case["ramp_end"],
            "time_max_requested": case["time_max"],
            "final_time": final.get("time", ""),
            "curved_diag_rows": len(curved),
            "final_affected": final_curve.get("affected", ""),
            "final_boundary_residual_max": final_curve.get("resid", ""),
            "final_p0_eff": final_conf.get("p0", 0.0),
            "peak_center_avg_radius": PRIMARY_AVG_RADIUS,
            "peak_center_avg_excess": peak_center,
            "peak_center_avg_excess_over_p0": peak_center / p0 if math.isfinite(peak_center) and p0 else math.nan,
            "peak_time": peak_row.get("time", ""),
            "peak_Tv_est": peak_row.get("Tv_est", ""),
            "final_center_avg_excess": final_center,
            "final_center_avg_excess_over_p0": final_center / p0 if math.isfinite(final_center) and p0 else math.nan,
            "center_pressure_decay_ratio_final_over_peak": final_center / peak_center if math.isfinite(final_center) and math.isfinite(peak_center) and peak_center else math.nan,
            "final_vel_max": final.get("vel_max", ""),
            "final_surface_excess_maxAbs": final.get("surface_ExcessPorePress_maxAbs", ""),
            "final_porepressrate_maxAbs": final.get("PorePressRate_maxAbs", ""),
            "final_kplastic_maxAbs": final.get("Kplastic_maxAbs", ""),
        })
        for radius in CENTER_AVG_RADII:
            key = radius_key(radius)
            r_rows = [r for r in merged if math.isfinite(fnum(r.get(f"center_avg_ExcessPorePress_{key}")))]
            peak = max((fnum(r.get(f"center_avg_ExcessPorePress_{key}")) for r in r_rows), default=math.nan)
            peak_r = max(r_rows, key=lambda r: fnum(r.get(f"center_avg_ExcessPorePress_{key}")), default={})
            final_v = fnum(final.get(f"center_avg_ExcessPorePress_{key}"))
            avg_summary_rows.append({
                "case": label,
                "p0": p0,
                "radius": radius,
                "radius_over_R": radius / RADIUS,
                "peak_center_avg_excess": peak,
                "peak_center_avg_excess_over_p0": peak / p0 if math.isfinite(peak) and p0 else math.nan,
                "peak_time": peak_r.get("time", ""),
                "final_center_avg_excess": final_v,
                "final_center_avg_excess_over_p0": final_v / p0 if math.isfinite(final_v) and p0 else math.nan,
                "final_count": final.get(f"center_avg_count_{key}", ""),
            })

    common_fields = sorted({key for row in all_rows for key in row.keys()})
    avg_fields = ["case", "p0", "frame_index", "time", "Tv_est", "radius", "radius_over_R", "count", "center_avg_PorePress", "center_avg_ExcessPorePress", "center_avg_ExcessPorePress_over_p0"]
    avg_summary_fields = ["case", "p0", "radius", "radius_over_R", "peak_center_avg_excess", "peak_center_avg_excess_over_p0", "peak_time", "final_center_avg_excess", "final_center_avg_excess_over_p0", "final_count"]
    residual_fields = ["case", "diag_index", "active", "radius", "thick", "target", "value", "value_type", "affected", "skipped", "rmin", "rmax", "boundary_residual_max"]
    conf_fields = ["case", "step", "time", "p0", "targets", "fx", "fy", "fz", "fabs", "amax", "acom", "sym"]
    summary_fields = ["case", "case_name", "code", "excluded", "steps", "runtime_sec", "frames", "particle_count", "p0", "ramp_end", "time_max_requested", "final_time", "curved_diag_rows", "final_affected", "final_boundary_residual_max", "final_p0_eff", "peak_center_avg_radius", "peak_center_avg_excess", "peak_center_avg_excess_over_p0", "peak_time", "peak_Tv_est", "final_center_avg_excess", "final_center_avg_excess_over_p0", "center_pressure_decay_ratio_final_over_peak", "final_vel_max", "final_surface_excess_maxAbs", "final_porepressrate_maxAbs", "final_kplastic_maxAbs"]

    write_csv(ROOT / "c5b_case_summary.csv", summary_rows, summary_fields)
    write_csv(ROOT / "c5b_center_pressure_comparison.csv", all_rows, common_fields)
    write_csv(ROOT / "c5b_boundary_residual_comparison.csv", residual_rows, residual_fields)
    write_csv(ROOT / "c5b_loading_ramp_metrics.csv", conf_rows, conf_fields)
    write_csv(ROOT / "c5b_averaging_radius_sensitivity.csv", avg_summary_rows, avg_summary_fields)
    write_csv(ROOT / "c5b_center_pressure_by_radius.csv", avg_rows_all, avg_fields)
    write_csv(ROOT / "c5b_stability_metrics.csv", all_rows, common_fields)
    plot(all_rows, residual_rows, avg_rows_all)


if __name__ == "__main__":
    main()
