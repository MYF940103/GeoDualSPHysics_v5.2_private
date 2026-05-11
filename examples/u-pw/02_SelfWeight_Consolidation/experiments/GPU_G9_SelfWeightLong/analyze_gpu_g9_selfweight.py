from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASE = "CaseSelfWeightConsolidation_PR_Scenario2_GPU_T3p6_Xi010"
OUT = ROOT / f"{CASE}_gpu_out"
CPU_SW3H = ROOT.parents[2] / "01_1D_Consolidation" / "SW3h_scenario2_T3p6_xi010"
KERNEL_H = 0.018
TIME_OUT = 0.1
WATER_LEVEL = 1.0
KPERM = 1.0e-3
RHOW = 1000.0
G = 9.81


def parse_run(run_path: Path) -> dict[str, str]:
    text = run_path.read_text(errors="replace") if run_path.exists() else ""
    patterns = {
        "code": r"Finished execution \(code=(\d+)\)",
        "excluded": r"Excluded particles\.+:\s*(\d+)",
        "steps": r"Steps of simulation\.+:\s*(\d+)",
        "runtime_s": r"Total Runtime\.+:\s*([0-9.Ee+-]+)",
    }
    return {key: (m.group(1) if (m := re.search(pat, text)) else "") for key, pat in patterns.items()}


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", errors="ignore") as f:
        sample = f.read(4096)
        f.seek(0)
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        return list(csv.DictReader(f, delimiter=delim))


def clean_header(header: list[str]) -> list[str]:
    return [h.strip().split()[0] for h in header if h.strip()]


def read_part(path: Path) -> tuple[list[str], list[dict[str, float]]]:
    with path.open(newline="", errors="ignore") as f:
        reader = csv.reader(f, delimiter=";")
        header = clean_header(next(reader))
        rows: list[dict[str, float]] = []
        for raw in reader:
            vals = [v.strip() for v in raw if v.strip()]
            if len(vals) != len(header):
                continue
            row = {}
            for key, val in zip(header, vals):
                try:
                    row[key] = float(val)
                except ValueError:
                    row[key] = math.nan
            rows.append(row)
    return header, rows


def material_rows(part: Path) -> tuple[list[str], list[dict[str, float]]]:
    header, rows = read_part(part)
    return header, [r for r in rows if int(r.get("Type", -1)) == 3]


def stats(values: list[float]) -> tuple[float, float, float, float]:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return math.nan, math.nan, math.nan, math.nan
    return min(vals), max(vals), sum(vals) / len(vals), max(abs(v) for v in vals)


def vecmag(row: dict[str, float], field: str) -> float:
    x = row.get(f"{field}.x", math.nan)
    y = row.get(f"{field}.y", math.nan)
    z = row.get(f"{field}.z", math.nan)
    if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
        return math.nan
    return math.sqrt(x * x + y * y + z * z)


def hydrostatic(z: float) -> float:
    return RHOW * G * max(WATER_LEVEL - z, 0.0)


def by_id(rows: list[dict[str, float]]) -> dict[int, dict[str, float]]:
    return {int(r["Idp"]): r for r in rows if math.isfinite(r.get("Idp", math.nan))}


def settlement(rows: list[dict[str, float]], initial: dict[int, dict[str, float]]) -> tuple[float, float, float, float]:
    dz = []
    for row in rows:
        other = initial.get(int(row.get("Idp", -1)))
        if other:
            val = row.get("Pos.z", math.nan) - other.get("Pos.z", math.nan)
            if math.isfinite(val):
                dz.append(val)
    return stats(dz)


def frame_metrics(part: Path, frame_index: int, initial: dict[int, dict[str, float]]) -> dict[str, str]:
    header, rows = material_rows(part)
    zvals = [r.get("Pos.z", math.nan) for r in rows if math.isfinite(r.get("Pos.z", math.nan))]
    zmin, zmax = (min(zvals), max(zvals)) if zvals else (math.nan, math.nan)
    top = [r for r in rows if r.get("Pos.z", -1e99) >= zmax - KERNEL_H]
    bottom = [r for r in rows if r.get("Pos.z", 1e99) <= zmin + KERNEL_H]
    ref = [r for r in rows if zmin + KERNEL_H < r.get("Pos.z", math.nan) <= zmin + 2 * KERNEL_H]

    hydro = [hydrostatic(r.get("Pos.z", math.nan)) for r in rows]
    bottom_hydro = [hydrostatic(r.get("Pos.z", math.nan)) for r in bottom]
    _, _, ref_ex_mean, _ = stats([r.get("ExcessPorePress", math.nan) for r in ref])
    bottom_proxy = []
    for row in bottom:
        ex = row.get("ExcessPorePress", math.nan)
        if math.isfinite(ex) and math.isfinite(ref_ex_mean):
            bottom_proxy.append(ex - ref_ex_mean)

    p_min, p_max, p_mean, _ = stats([r.get("PorePress", math.nan) for r in rows])
    h_min, h_max, h_mean, _ = stats(hydro)
    ex_min, ex_max, ex_mean, ex_maxabs = stats([r.get("ExcessPorePress", math.nan) for r in rows])
    _, _, bottom_p_mean, _ = stats([r.get("PorePress", math.nan) for r in bottom])
    _, _, bottom_h_mean, _ = stats(bottom_hydro)
    _, _, bottom_ex_mean, bottom_ex_maxabs = stats([r.get("ExcessPorePress", math.nan) for r in bottom])
    _, _, _, top_ex_maxabs = stats([r.get("ExcessPorePress", math.nan) for r in top])
    _, _, _, bottom_proxy_maxabs = stats(bottom_proxy)
    _, _, vel_mean, vel_maxabs = stats([vecmag(r, "Vel") for r in rows])
    dz_min, dz_max, dz_mean, dz_maxabs = settlement(rows, initial)
    _, _, _, rate_maxabs = stats([r.get("PorePressRate", math.nan) for r in rows])
    _, _, _, divvel_maxabs = stats([r.get("DivVel", math.nan) for r in rows])
    hydraulic = []
    for row in rows:
        lap_p = row.get("LapPorePress", math.nan)
        lap_z = row.get("LapZ", math.nan)
        if math.isfinite(lap_p) and math.isfinite(lap_z):
            hydraulic.append(KPERM / (RHOW * G) * lap_p + KPERM * lap_z)
    _, _, _, hydraulic_maxabs = stats(hydraulic)
    _, _, _, ace_maxabs = stats([vecmag(r, "PorePressureAccelDiff") for r in rows])

    return {
        "frame": str(frame_index),
        "time": f"{frame_index * TIME_OUT:.12g}",
        "n": str(len(rows)),
        "zmin": f"{zmin:.12g}",
        "zmax": f"{zmax:.12g}",
        "velocity_max": f"{vel_maxabs:.12g}",
        "velocity_mean": f"{vel_mean:.12g}",
        "settlement_mean_z": f"{dz_mean:.12g}",
        "PorePress_min": f"{p_min:.12g}",
        "PorePress_max": f"{p_max:.12g}",
        "PorePress_mean": f"{p_mean:.12g}",
        "hydrostatic_min": f"{h_min:.12g}",
        "hydrostatic_max": f"{h_max:.12g}",
        "hydrostatic_mean": f"{h_mean:.12g}",
        "Excess_min": f"{ex_min:.12g}",
        "Excess_max": f"{ex_max:.12g}",
        "Excess_mean": f"{ex_mean:.12g}",
        "Excess_maxAbs": f"{ex_maxabs:.12g}",
        "bottom_PorePress_mean": f"{bottom_p_mean:.12g}",
        "bottom_hydrostatic_mean": f"{bottom_h_mean:.12g}",
        "bottom_Excess_mean": f"{bottom_ex_mean:.12g}",
        "bottom_Excess_maxAbs": f"{bottom_ex_maxabs:.12g}",
        "top_Excess_maxAbs": f"{top_ex_maxabs:.12g}",
        "bottom_grad_proxy": f"{bottom_proxy_maxabs:.12g}",
        "PorePressRate_maxAbs": f"{rate_maxabs:.12g}",
        "DivVelContribution_maxAbs": f"{divvel_maxabs:.12g}",
        "HydraulicContribution_maxAbs": f"{hydraulic_maxabs:.12g}",
        "PorePressureAccelDiff_maxAbs": f"{ace_maxabs:.12g}",
        "has_PorePress": str("PorePress" in header),
        "has_ExcessPorePress": str("ExcessPorePress" in header),
        "has_PorePressureAccelDiff": str(all(f"PorePressureAccelDiff.{c}" in header for c in "xyz")),
    }


def fget(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "nan"))
    except ValueError:
        return math.nan


def main() -> None:
    parts = sorted((OUT / "data").glob("PartCsv_*.csv"))
    frame_rows: list[dict[str, str]] = []
    if parts:
        _, initial_rows = material_rows(parts[0])
        initial = by_id(initial_rows)
        for idx, part in enumerate(parts):
            frame_rows.append(frame_metrics(part, idx, initial))

    frame_fields = list(frame_rows[0].keys()) if frame_rows else []
    with (ROOT / "gpu_g9_frame_metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=frame_fields)
        writer.writeheader()
        writer.writerows(frame_rows)

    run_info = parse_run(OUT / "Run.out")
    final = frame_rows[-1] if frame_rows else {}
    cpu_summary_rows = read_rows(CPU_SW3H / "sw3h_case_summary.csv")
    cpu_summary = cpu_summary_rows[0] if cpu_summary_rows else {}
    peak_excess = max((fget(r, "Excess_maxAbs") for r in frame_rows), default=math.nan)
    summary = {
        "code": run_info.get("code", ""),
        "excluded_particles": run_info.get("excluded", ""),
        "steps": run_info.get("steps", ""),
        "runtime_seconds": run_info.get("runtime_s", ""),
        "nframes": str(len(frame_rows)),
        "final_time": final.get("time", ""),
        "final_velocity_max": final.get("velocity_max", ""),
        "final_velocity_mean": final.get("velocity_mean", ""),
        "final_settlement_mean_z": final.get("settlement_mean_z", ""),
        "final_PorePress_max": final.get("PorePress_max", ""),
        "final_hydrostatic_max": final.get("hydrostatic_max", ""),
        "final_Excess_max": final.get("Excess_max", ""),
        "final_Excess_mean": final.get("Excess_mean", ""),
        "final_Excess_maxAbs": final.get("Excess_maxAbs", ""),
        "final_bottom_PorePress_mean": final.get("bottom_PorePress_mean", ""),
        "final_bottom_hydrostatic_mean": final.get("bottom_hydrostatic_mean", ""),
        "final_bottom_Excess_mean": final.get("bottom_Excess_mean", ""),
        "final_top_Excess_maxAbs": final.get("top_Excess_maxAbs", ""),
        "final_bottom_grad_proxy": final.get("bottom_grad_proxy", ""),
        "max_velocity_over_time": f"{max((fget(r, 'velocity_max') for r in frame_rows), default=math.nan):.12g}",
        "peak_Excess_maxAbs": f"{peak_excess:.12g}",
        "max_PorePressRate_over_time": f"{max((fget(r, 'PorePressRate_maxAbs') for r in frame_rows), default=math.nan):.12g}",
        "max_DivVelContribution_over_time": f"{max((fget(r, 'DivVelContribution_maxAbs') for r in frame_rows), default=math.nan):.12g}",
        "max_HydraulicContribution_over_time": f"{max((fget(r, 'HydraulicContribution_maxAbs') for r in frame_rows), default=math.nan):.12g}",
        "max_PorePressureAccelDiff_over_time": f"{max((fget(r, 'PorePressureAccelDiff_maxAbs') for r in frame_rows), default=math.nan):.12g}",
        "cpu_sw3h_final_Excess_max": cpu_summary.get("final_Excess_max", ""),
        "cpu_sw3h_final_Excess_mean": cpu_summary.get("final_Excess_mean", ""),
        "cpu_sw3h_final_bottom_Excess_mean": cpu_summary.get("final_bottom_Excess_mean", ""),
        "cpu_sw3h_final_PorePress_max": cpu_summary.get("final_PorePress_max", ""),
        "cpu_sw3h_final_velocity_max": cpu_summary.get("final_velocity_max", ""),
        "cpu_sw3h_runtime_seconds": cpu_summary.get("runtime_seconds", ""),
    }
    if cpu_summary:
        summary["gpu_minus_cpu_final_Excess_max"] = f"{fget(summary, 'final_Excess_max') - fget(cpu_summary, 'final_Excess_max'):.12g}"
        summary["gpu_minus_cpu_final_Excess_mean"] = f"{fget(summary, 'final_Excess_mean') - fget(cpu_summary, 'final_Excess_mean'):.12g}"
        summary["gpu_minus_cpu_final_bottom_Excess_mean"] = f"{fget(summary, 'final_bottom_Excess_mean') - fget(cpu_summary, 'final_bottom_Excess_mean'):.12g}"
        summary["gpu_minus_cpu_final_PorePress_max"] = f"{fget(summary, 'final_PorePress_max') - fget(cpu_summary, 'final_PorePress_max'):.12g}"
        summary["gpu_speedup_vs_cpu_sw3h"] = f"{fget(cpu_summary, 'runtime_seconds') / fget(summary, 'runtime_seconds'):.12g}"

    with (ROOT / "gpu_g9_case_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)


if __name__ == "__main__":
    main()
