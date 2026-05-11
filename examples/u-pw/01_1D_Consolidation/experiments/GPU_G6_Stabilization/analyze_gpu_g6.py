from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = [
    "Case1DConsolidation_PR_GPU_G6_DampingOff",
    "Case1DConsolidation_PR_GPU_G6_DampingOn",
    "Case1DConsolidation_PR_GPU_G6_ShepardHydro",
    "Case1DConsolidation_PR_GPU_G6_ShepardAnalytical",
    "Case1DConsolidation_PR_GPU_G6_CoupledShort",
]
SCALAR_FIELDS = [
    "PorePress",
    "ExcessPorePress",
    "PorePressRate",
    "DivVel",
    "LapPorePress",
    "LapZ",
]
VECTOR_FIELDS = ["PorePressureAccelDiff"]


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


def add_stats(result: dict[str, str], rows: list[dict[str, float]], field: str) -> None:
    mn, mx, mean, maxabs = stats([r.get(field, math.nan) for r in rows])
    result[f"{field}_min"] = f"{mn:.12g}"
    result[f"{field}_max"] = f"{mx:.12g}"
    result[f"{field}_mean"] = f"{mean:.12g}"
    result[f"{field}_maxAbs"] = f"{maxabs:.12g}"


def add_vector_stats(result: dict[str, str], rows: list[dict[str, float]], field: str) -> None:
    mags = []
    for row in rows:
        x = row.get(f"{field}.x", math.nan)
        y = row.get(f"{field}.y", math.nan)
        z = row.get(f"{field}.z", math.nan)
        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
            mags.append(math.sqrt(x * x + y * y + z * z))
    mn, mx, mean, maxabs = stats(mags)
    result[f"{field}_mag_min"] = f"{mn:.12g}"
    result[f"{field}_mag_max"] = f"{mx:.12g}"
    result[f"{field}_mag_mean"] = f"{mean:.12g}"
    result[f"{field}_mag_maxAbs"] = f"{maxabs:.12g}"


def add_velocity_stats(result: dict[str, str], rows: list[dict[str, float]]) -> None:
    mags = []
    for row in rows:
        x = row.get("Vel.x", math.nan)
        y = row.get("Vel.y", math.nan)
        z = row.get("Vel.z", math.nan)
        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
            mags.append(math.sqrt(x * x + y * y + z * z))
    mn, mx, mean, maxabs = stats(mags)
    result["Vel_mag_min"] = f"{mn:.12g}"
    result["Vel_mag_max"] = f"{mx:.12g}"
    result["Vel_mag_mean"] = f"{mean:.12g}"
    result["Vel_mag_maxAbs"] = f"{maxabs:.12g}"


def compare_by_idp(rows_a: list[dict[str, float]], rows_b: list[dict[str, float]], field: str, label: str) -> dict[str, str]:
    b_by_id = {int(r["Idp"]): r for r in rows_b if math.isfinite(r.get("Idp", math.nan))}
    diffs = []
    for row in rows_a:
        other = b_by_id.get(int(row.get("Idp", -1)))
        if not other:
            continue
        if field in VECTOR_FIELDS:
            dx = row.get(f"{field}.x", math.nan) - other.get(f"{field}.x", math.nan)
            dy = row.get(f"{field}.y", math.nan) - other.get(f"{field}.y", math.nan)
            dz = row.get(f"{field}.z", math.nan) - other.get(f"{field}.z", math.nan)
            if math.isfinite(dx) and math.isfinite(dy) and math.isfinite(dz):
                diffs.append(math.sqrt(dx * dx + dy * dy + dz * dz))
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


def main() -> None:
    rows_out: list[dict[str, str]] = []
    final_rows_by_case: dict[str, list[dict[str, float]]] = {}
    for case in CASES:
        out_dir = ROOT / f"{case}_out"
        cpu_dir = ROOT / f"{case}_cpu_out"
        header, rows, frame = material_rows(out_dir)
        _, rows0, frame0 = material_rows(out_dir, "initial")
        _, cpu_rows, cpu_frame = material_rows(cpu_dir)
        final_rows_by_case[case] = rows
        result = {
            "case": case,
            **parse_run(out_dir / "Run.out"),
            "frame": frame,
            "initial_frame": frame0,
            "particles": str(len(rows)),
            "cpu_frame": cpu_frame,
            "cpu_particles": str(len(cpu_rows)),
            "has_PorePress": str("PorePress" in header),
            "has_ExcessPorePress": str("ExcessPorePress" in header),
            "has_PorePressureAccelDiff": str(all(f"PorePressureAccelDiff.{c}" in header for c in "xyz")),
        }
        for field in SCALAR_FIELDS:
            add_stats(result, rows, field)
            if rows0:
                result.update(compare_by_idp(rows, rows0, field, "final_initial"))
            if cpu_rows:
                result.update(compare_by_idp(rows, cpu_rows, field, "gpu_cpu"))
        for field in VECTOR_FIELDS:
            add_vector_stats(result, rows, field)
            if cpu_rows:
                result.update(compare_by_idp(rows, cpu_rows, field, "gpu_cpu"))
        add_velocity_stats(result, rows)
        rows_out.append(result)

    if final_rows_by_case.get("Case1DConsolidation_PR_GPU_G6_DampingOn") and final_rows_by_case.get("Case1DConsolidation_PR_GPU_G6_DampingOff"):
        on_rows = final_rows_by_case["Case1DConsolidation_PR_GPU_G6_DampingOn"]
        off_rows = final_rows_by_case["Case1DConsolidation_PR_GPU_G6_DampingOff"]
        for result in rows_out:
            if result["case"] == "Case1DConsolidation_PR_GPU_G6_DampingOn":
                result.update(compare_by_idp(on_rows, off_rows, "PorePress", "damping_on_off"))
                result.update(compare_by_idp(on_rows, off_rows, "PorePressureAccelDiff", "damping_on_off"))

    preferred = ["case", "code", "excluded", "steps", "runtime_s", "frame", "particles", "has_PorePress", "has_ExcessPorePress", "has_PorePressureAccelDiff"]
    fieldnames = preferred + sorted({k for row in rows_out for k in row.keys()} - set(preferred))
    with (ROOT / "gpu_g6_smoke_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)


if __name__ == "__main__":
    main()
