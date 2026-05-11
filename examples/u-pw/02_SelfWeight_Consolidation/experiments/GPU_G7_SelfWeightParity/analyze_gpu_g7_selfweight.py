from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASE = "CaseSelfWeightConsolidation_PR_GPU_G7_Scenario2Short"
CPU_OUT = ROOT / f"{CASE}_cpu_out"
GPU_OUT = ROOT / f"{CASE}_gpu_out"
KERNEL_H = 0.018
SCALAR_FIELDS = [
    "PorePress",
    "ExcessPorePress",
    "PorePressRate",
    "DivVel",
    "LapPorePress",
    "LapZ",
]
VECTOR_FIELDS = ["PorePressureAccelDiff", "Vel"]


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


def material_rows(out_dir: Path, frame: str = "final") -> tuple[list[str], list[dict[str, float]], str]:
    parts = sorted((out_dir / "data").glob("PartCsv_*.csv"))
    if not parts:
        return [], [], ""
    part = parts[0] if frame == "initial" else parts[-1]
    header, rows = read_part(part)
    return header, [r for r in rows if int(r.get("Type", -1)) == 3], part.stem


def stats(values: list[float]) -> tuple[float, float, float, float]:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return math.nan, math.nan, math.nan, math.nan
    return min(vals), max(vals), sum(vals) / len(vals), max(abs(v) for v in vals)


def vector_mag(row: dict[str, float], field: str) -> float:
    x = row.get(f"{field}.x", math.nan)
    y = row.get(f"{field}.y", math.nan)
    z = row.get(f"{field}.z", math.nan)
    if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
        return math.nan
    return math.sqrt(x * x + y * y + z * z)


def add_stats(result: dict[str, str], rows: list[dict[str, float]], field: str) -> None:
    mn, mx, mean, maxabs = stats([r.get(field, math.nan) for r in rows])
    result[f"{field}_min"] = f"{mn:.12g}"
    result[f"{field}_max"] = f"{mx:.12g}"
    result[f"{field}_mean"] = f"{mean:.12g}"
    result[f"{field}_maxAbs"] = f"{maxabs:.12g}"


def add_vector_stats(result: dict[str, str], rows: list[dict[str, float]], field: str) -> None:
    mn, mx, mean, maxabs = stats([vector_mag(r, field) for r in rows])
    result[f"{field}_mag_min"] = f"{mn:.12g}"
    result[f"{field}_mag_max"] = f"{mx:.12g}"
    result[f"{field}_mag_mean"] = f"{mean:.12g}"
    result[f"{field}_mag_maxAbs"] = f"{maxabs:.12g}"


def compare_by_idp(rows_a: list[dict[str, float]], rows_b: list[dict[str, float]], field: str, label: str) -> dict[str, str]:
    b_by_id = {int(r["Idp"]): r for r in rows_b if math.isfinite(r.get("Idp", math.nan))}
    diffs = []
    for row in rows_a:
        other = b_by_id.get(int(row.get("Idp", -1)))
        if not other:
            continue
        if field in VECTOR_FIELDS:
            a = vector_mag(row, field)
            b = vector_mag(other, field)
            if math.isfinite(a) and math.isfinite(b):
                diffs.append(a - b)
        else:
            diff = row.get(field, math.nan) - other.get(field, math.nan)
            if math.isfinite(diff):
                diffs.append(diff)
    mn, mx, mean, maxabs = stats(diffs)
    return {
        f"{label}_{field}_diff_min": f"{mn:.12g}",
        f"{label}_{field}_diff_max": f"{mx:.12g}",
        f"{label}_{field}_diff_mean": f"{mean:.12g}",
        f"{label}_{field}_diff_maxAbs": f"{maxabs:.12g}",
    }


def settlement(rows: list[dict[str, float]], initial_rows: list[dict[str, float]]) -> tuple[float, float, float, float]:
    initial = {int(r["Idp"]): r for r in initial_rows if math.isfinite(r.get("Idp", math.nan))}
    dz = []
    for row in rows:
        other = initial.get(int(row.get("Idp", -1)))
        if other:
            diff = row.get("Pos.z", math.nan) - other.get("Pos.z", math.nan)
            if math.isfinite(diff):
                dz.append(diff)
    return stats(dz)


def boundary_metrics(rows: list[dict[str, float]]) -> dict[str, str]:
    zvals = [r.get("Pos.z", math.nan) for r in rows]
    zvals = [z for z in zvals if math.isfinite(z)]
    if not zvals:
        return {}
    zmin, zmax = min(zvals), max(zvals)
    top = [r for r in rows if r.get("Pos.z", -1e99) >= zmax - KERNEL_H]
    bottom = [r for r in rows if r.get("Pos.z", 1e99) <= zmin + KERNEL_H]
    ref = [r for r in rows if zmin + KERNEL_H < r.get("Pos.z", math.nan) <= zmin + 2 * KERNEL_H]
    ref_vals = [r.get("ExcessPorePress", math.nan) for r in ref]
    _, _, ref_mean, _ = stats(ref_vals)
    bottom_proxy = []
    for row in bottom:
        ex = row.get("ExcessPorePress", math.nan)
        if math.isfinite(ex) and math.isfinite(ref_mean):
            bottom_proxy.append(ex - ref_mean)
    _, _, _, top_ex_maxabs = stats([r.get("ExcessPorePress", math.nan) for r in top])
    _, _, _, bottom_proxy_maxabs = stats(bottom_proxy)
    return {
        "zmin": f"{zmin:.12g}",
        "zmax": f"{zmax:.12g}",
        "top_count": str(len(top)),
        "bottom_count": str(len(bottom)),
        "bottom_ref_count": str(len(ref)),
        "top_excess_maxAbs": f"{top_ex_maxabs:.12g}",
        "bottom_no_flux_proxy_maxAbs": f"{bottom_proxy_maxabs:.12g}",
    }


def summarize(label: str, out_dir: Path) -> tuple[dict[str, str], list[dict[str, float]]]:
    header, rows, frame = material_rows(out_dir)
    _, initial_rows, initial_frame = material_rows(out_dir, "initial")
    result = {
        "run": label,
        **parse_run(out_dir / "Run.out"),
        "frame": frame,
        "initial_frame": initial_frame,
        "particles": str(len(rows)),
        "has_PorePress": str("PorePress" in header),
        "has_ExcessPorePress": str("ExcessPorePress" in header),
        "has_PorePressureAccelDiff": str(all(f"PorePressureAccelDiff.{c}" in header for c in "xyz")),
    }
    for field in SCALAR_FIELDS:
        add_stats(result, rows, field)
    for field in VECTOR_FIELDS:
        add_vector_stats(result, rows, field)
    dz_min, dz_max, dz_mean, dz_maxabs = settlement(rows, initial_rows)
    result["settlement_dz_min"] = f"{dz_min:.12g}"
    result["settlement_dz_max"] = f"{dz_max:.12g}"
    result["settlement_dz_mean"] = f"{dz_mean:.12g}"
    result["settlement_dz_maxAbs"] = f"{dz_maxabs:.12g}"
    result.update(boundary_metrics(rows))
    return result, rows


def main() -> None:
    cpu, cpu_rows = summarize("CPU", CPU_OUT)
    gpu, gpu_rows = summarize("GPU", GPU_OUT)
    for field in SCALAR_FIELDS + VECTOR_FIELDS:
        gpu.update(compare_by_idp(gpu_rows, cpu_rows, field, "gpu_cpu"))
    preferred = [
        "run", "code", "excluded", "steps", "runtime_s", "frame", "particles",
        "has_PorePress", "has_ExcessPorePress", "has_PorePressureAccelDiff",
        "PorePress_max", "PorePress_mean", "ExcessPorePress_maxAbs",
        "PorePressRate_maxAbs", "DivVel_maxAbs", "PorePressureAccelDiff_mag_maxAbs",
        "Vel_mag_max", "Vel_mag_mean", "settlement_dz_mean",
        "top_excess_maxAbs", "bottom_no_flux_proxy_maxAbs",
    ]
    rows = [cpu, gpu]
    fieldnames = preferred + sorted({k for row in rows for k in row.keys()} - set(preferred))
    with (ROOT / "gpu_g7_selfweight_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
