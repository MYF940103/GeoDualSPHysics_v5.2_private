from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = {
    "T0p05": {
        "name": "CaseSelfWeightConsolidation_PR_GPU_G8_T0p05",
        "timeout": 0.005,
    },
    "T0p2": {
        "name": "CaseSelfWeightConsolidation_PR_GPU_G8_T0p2",
        "timeout": 0.02,
    },
}
KERNEL_H = 0.018
HYDRAULIC_CONDUCTIVITY = 1.0e-3
WATER_DENSITY = 1000.0
HYDRAULIC_GMAG = 9.81


def parse_run(run_path: Path) -> dict[str, str]:
    text = run_path.read_text(errors="replace") if run_path.exists() else ""
    patterns = {
        "code": r"Finished execution \(code=(\d+)\)",
        "excluded": r"Excluded particles\.+:\s*(\d+)",
        "steps": r"Steps of simulation\.+:\s*(\d+)",
        "runtime_s": r"Total Runtime\.+:\s*([0-9.Ee+-]+)",
    }
    return {key: (m.group(1) if (m := re.search(pat, text)) else "") for key, pat in patterns.items()}


def read_part(path: Path) -> tuple[list[str], list[dict[str, float]]]:
    with path.open(newline="") as f:
        reader = csv.reader(f, delimiter=";")
        header = [h.strip().split()[0] for h in next(reader) if h.strip()]
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


def frame_metrics(case_id: str, part: Path, frame_index: int, timeout: float, initial: dict[int, dict[str, float]]) -> dict[str, str]:
    header, rows = material_rows(part)
    zvals = [r.get("Pos.z", math.nan) for r in rows if math.isfinite(r.get("Pos.z", math.nan))]
    zmin, zmax = (min(zvals), max(zvals)) if zvals else (math.nan, math.nan)
    top = [r for r in rows if r.get("Pos.z", -1e99) >= zmax - KERNEL_H]
    bottom = [r for r in rows if r.get("Pos.z", 1e99) <= zmin + KERNEL_H]
    ref = [r for r in rows if zmin + KERNEL_H < r.get("Pos.z", math.nan) <= zmin + 2 * KERNEL_H]
    _, _, ref_mean_ex, _ = stats([r.get("ExcessPorePress", math.nan) for r in ref])
    bottom_proxy = []
    for row in bottom:
        ex = row.get("ExcessPorePress", math.nan)
        if math.isfinite(ex) and math.isfinite(ref_mean_ex):
            bottom_proxy.append(ex - ref_mean_ex)

    dz_min, dz_max, dz_mean, dz_maxabs = settlement(rows, initial)
    p_min, p_max, p_mean, p_maxabs = stats([r.get("PorePress", math.nan) for r in rows])
    ex_min, ex_max, ex_mean, ex_maxabs = stats([r.get("ExcessPorePress", math.nan) for r in rows])
    bottom_ex_min, bottom_ex_max, bottom_ex_mean, bottom_ex_maxabs = stats([r.get("ExcessPorePress", math.nan) for r in bottom])
    _, _, _, top_ex_maxabs = stats([r.get("ExcessPorePress", math.nan) for r in top])
    _, _, _, bottom_proxy_maxabs = stats(bottom_proxy)
    _, _, vel_mean, vel_maxabs = stats([vecmag(r, "Vel") for r in rows])
    _, _, _, ace_maxabs = stats([vecmag(r, "PorePressureAccelDiff") for r in rows])
    _, _, _, rate_maxabs = stats([r.get("PorePressRate", math.nan) for r in rows])
    _, _, _, divvel_maxabs = stats([r.get("DivVel", math.nan) for r in rows])
    hydraulic = []
    for row in rows:
        lap_p = row.get("LapPorePress", math.nan)
        lap_z = row.get("LapZ", math.nan)
        if math.isfinite(lap_p) and math.isfinite(lap_z):
            hydraulic.append(HYDRAULIC_CONDUCTIVITY / (WATER_DENSITY * HYDRAULIC_GMAG) * lap_p + HYDRAULIC_CONDUCTIVITY * lap_z)
    _, _, _, hydraulic_maxabs = stats(hydraulic)

    return {
        "case": case_id,
        "frame": part.stem,
        "frame_index": str(frame_index),
        "time_s": f"{frame_index * timeout:.12g}",
        "particles": str(len(rows)),
        "has_PorePress": str("PorePress" in header),
        "has_ExcessPorePress": str("ExcessPorePress" in header),
        "has_PorePressureAccelDiff": str(all(f"PorePressureAccelDiff.{c}" in header for c in "xyz")),
        "PorePress_min": f"{p_min:.12g}",
        "PorePress_max": f"{p_max:.12g}",
        "PorePress_mean": f"{p_mean:.12g}",
        "PorePress_maxAbs": f"{p_maxabs:.12g}",
        "ExcessPorePress_min": f"{ex_min:.12g}",
        "ExcessPorePress_max": f"{ex_max:.12g}",
        "ExcessPorePress_mean": f"{ex_mean:.12g}",
        "ExcessPorePress_maxAbs": f"{ex_maxabs:.12g}",
        "bottom_ExcessPorePress_min": f"{bottom_ex_min:.12g}",
        "bottom_ExcessPorePress_max": f"{bottom_ex_max:.12g}",
        "bottom_ExcessPorePress_mean": f"{bottom_ex_mean:.12g}",
        "bottom_ExcessPorePress_maxAbs": f"{bottom_ex_maxabs:.12g}",
        "top_excess_maxAbs": f"{top_ex_maxabs:.12g}",
        "bottom_no_flux_proxy_maxAbs": f"{bottom_proxy_maxabs:.12g}",
        "Vel_mag_mean": f"{vel_mean:.12g}",
        "Vel_mag_maxAbs": f"{vel_maxabs:.12g}",
        "settlement_dz_min": f"{dz_min:.12g}",
        "settlement_dz_max": f"{dz_max:.12g}",
        "settlement_dz_mean": f"{dz_mean:.12g}",
        "settlement_dz_maxAbs": f"{dz_maxabs:.12g}",
        "PorePressRate_maxAbs": f"{rate_maxabs:.12g}",
        "DivVel_maxAbs": f"{divvel_maxabs:.12g}",
        "hydraulic_contribution_maxAbs": f"{hydraulic_maxabs:.12g}",
        "PorePressureAccelDiff_mag_maxAbs": f"{ace_maxabs:.12g}",
    }


def summarize_case(case_id: str, metrics: list[dict[str, str]], run_info: dict[str, str]) -> dict[str, str]:
    final = metrics[-1] if metrics else {}
    initial_ex = float(metrics[0]["ExcessPorePress_maxAbs"]) if metrics else math.nan
    final_ex = float(final.get("ExcessPorePress_maxAbs", "nan"))
    peak_ex = max(float(m["ExcessPorePress_maxAbs"]) for m in metrics) if metrics else math.nan
    return {
        "case": case_id,
        **run_info,
        "frames": str(len(metrics)),
        "final_time_s": final.get("time_s", ""),
        "initial_excess_maxAbs": f"{initial_ex:.12g}",
        "peak_excess_maxAbs": f"{peak_ex:.12g}",
        "final_excess_maxAbs": f"{final_ex:.12g}",
        "final_bottom_excess_mean": final.get("bottom_ExcessPorePress_mean", ""),
        "final_top_excess_maxAbs": final.get("top_excess_maxAbs", ""),
        "final_bottom_no_flux_proxy_maxAbs": final.get("bottom_no_flux_proxy_maxAbs", ""),
        "final_velocity_maxAbs": final.get("Vel_mag_maxAbs", ""),
        "final_velocity_mean": final.get("Vel_mag_mean", ""),
        "final_settlement_mean": final.get("settlement_dz_mean", ""),
        "final_porepress_max": final.get("PorePress_max", ""),
        "final_porepress_mean": final.get("PorePress_mean", ""),
        "final_porepressrate_maxAbs": final.get("PorePressRate_maxAbs", ""),
        "final_divvel_maxAbs": final.get("DivVel_maxAbs", ""),
        "final_hydraulic_contribution_maxAbs": final.get("hydraulic_contribution_maxAbs", ""),
        "final_acceldiff_maxAbs": final.get("PorePressureAccelDiff_mag_maxAbs", ""),
        "excess_envelope_drop_from_peak": f"{(peak_ex - final_ex):.12g}",
    }


def main() -> None:
    frame_rows: list[dict[str, str]] = []
    summary_rows: list[dict[str, str]] = []
    for case_id, info in CASES.items():
        out_dir = ROOT / f"{info['name']}_gpu_out"
        parts = sorted((out_dir / "data").glob("PartCsv_*.csv"))
        if not parts:
            summary_rows.append({"case": case_id, **parse_run(out_dir / "Run.out"), "frames": "0"})
            continue
        _, initial_rows = material_rows(parts[0])
        initial = by_id(initial_rows)
        case_metrics = []
        for idx, part in enumerate(parts):
            row = frame_metrics(case_id, part, idx, float(info["timeout"]), initial)
            case_metrics.append(row)
            frame_rows.append(row)
        summary_rows.append(summarize_case(case_id, case_metrics, parse_run(out_dir / "Run.out")))

    frame_fields = sorted({k for row in frame_rows for k in row.keys()})
    preferred_frame = [
        "case", "frame", "frame_index", "time_s", "particles",
        "PorePress_max", "PorePress_mean", "ExcessPorePress_maxAbs",
        "bottom_ExcessPorePress_mean", "top_excess_maxAbs",
        "bottom_no_flux_proxy_maxAbs", "Vel_mag_maxAbs", "Vel_mag_mean",
        "settlement_dz_mean", "PorePressRate_maxAbs", "DivVel_maxAbs",
        "hydraulic_contribution_maxAbs", "PorePressureAccelDiff_mag_maxAbs",
    ]
    frame_fields = preferred_frame + [f for f in frame_fields if f not in preferred_frame]
    with (ROOT / "gpu_g8_frame_metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=frame_fields)
        writer.writeheader()
        writer.writerows(frame_rows)

    summary_fields = sorted({k for row in summary_rows for k in row.keys()})
    preferred_summary = [
        "case", "code", "excluded", "steps", "runtime_s", "frames",
        "final_time_s", "peak_excess_maxAbs", "final_excess_maxAbs",
        "excess_envelope_drop_from_peak", "final_bottom_excess_mean",
        "final_top_excess_maxAbs", "final_bottom_no_flux_proxy_maxAbs",
        "final_velocity_maxAbs", "final_velocity_mean", "final_settlement_mean",
        "final_porepress_max", "final_porepress_mean",
        "final_porepressrate_maxAbs", "final_divvel_maxAbs",
        "final_hydraulic_contribution_maxAbs", "final_acceldiff_maxAbs",
    ]
    summary_fields = preferred_summary + [f for f in summary_fields if f not in preferred_summary]
    with (ROOT / "gpu_g8_case_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)


if __name__ == "__main__":
    main()
