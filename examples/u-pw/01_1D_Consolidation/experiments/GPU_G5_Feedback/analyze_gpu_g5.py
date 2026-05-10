from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = [
    "Case1DConsolidation_PR_GPU_G5_Hydro",
    "Case1DConsolidation_PR_GPU_G5_Uniform",
    "Case1DConsolidation_PR_GPU_G5_NonUniform",
]
FIELDS = [
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
    code = re.search(r"Finished execution \(code=(\d+)\)", text)
    excluded = re.search(r"Excluded particles\.+:\s*(\d+)", text)
    steps = re.search(r"Steps of simulation\.+:\s*(\d+)", text)
    runtime = re.search(r"Total Runtime\.+:\s*([0-9.Ee+-]+)", text)
    return {
        "code": code.group(1) if code else "",
        "excluded": excluded.group(1) if excluded else "",
        "steps": steps.group(1) if steps else "",
        "runtime_s": runtime.group(1) if runtime else "",
    }


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


def stats(values: list[float]) -> tuple[float, float, float, float]:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return (math.nan, math.nan, math.nan, math.nan)
    return (min(vals), max(vals), sum(vals) / len(vals), max(abs(v) for v in vals))


def final_material_rows(out_dir: Path) -> tuple[list[str], list[dict[str, float]], str]:
    parts = sorted((out_dir / "data").glob("PartCsv_*.csv"))
    if not parts:
        return ([], [], "")
    header, rows = read_part(parts[-1])
    material = [r for r in rows if int(r.get("Type", -1)) == 3]
    return header, material, parts[-1].stem


def add_field_stats(result: dict[str, str], rows: list[dict[str, float]], field: str) -> None:
    mn, mx, mean, maxabs = stats([r.get(field, math.nan) for r in rows])
    result[f"{field}_min"] = f"{mn:.12g}"
    result[f"{field}_max"] = f"{mx:.12g}"
    result[f"{field}_mean"] = f"{mean:.12g}"
    result[f"{field}_maxAbs"] = f"{maxabs:.12g}"


def add_vector_stats(result: dict[str, str], rows: list[dict[str, float]], field: str) -> None:
    mags = []
    for r in rows:
        x = r.get(f"{field}.x", math.nan)
        y = r.get(f"{field}.y", math.nan)
        z = r.get(f"{field}.z", math.nan)
        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
            mags.append(math.sqrt(x * x + y * y + z * z))
    mn, mx, mean, maxabs = stats(mags)
    result[f"{field}_mag_min"] = f"{mn:.12g}"
    result[f"{field}_mag_max"] = f"{mx:.12g}"
    result[f"{field}_mag_mean"] = f"{mean:.12g}"
    result[f"{field}_mag_maxAbs"] = f"{maxabs:.12g}"


def compare_by_idp(gpu_rows: list[dict[str, float]], cpu_rows: list[dict[str, float]], field: str) -> dict[str, str]:
    cpu_by_id = {int(r["Idp"]): r for r in cpu_rows if math.isfinite(r.get("Idp", math.nan))}
    diffs = []
    for gr in gpu_rows:
        gid = int(gr["Idp"])
        cr = cpu_by_id.get(gid)
        if not cr:
            continue
        if field in VECTOR_FIELDS:
            dx = gr.get(f"{field}.x", math.nan) - cr.get(f"{field}.x", math.nan)
            dy = gr.get(f"{field}.y", math.nan) - cr.get(f"{field}.y", math.nan)
            dz = gr.get(f"{field}.z", math.nan) - cr.get(f"{field}.z", math.nan)
            if math.isfinite(dx) and math.isfinite(dy) and math.isfinite(dz):
                diffs.append(math.sqrt(dx * dx + dy * dy + dz * dz))
        else:
            diff = gr.get(field, math.nan) - cr.get(field, math.nan)
            if math.isfinite(diff):
                diffs.append(diff)
    mn, mx, mean, maxabs = stats(diffs)
    return {
        f"gpu_cpu_{field}_diff_min": f"{mn:.12g}",
        f"gpu_cpu_{field}_diff_max": f"{mx:.12g}",
        f"gpu_cpu_{field}_diff_mean": f"{mean:.12g}",
        f"gpu_cpu_{field}_diff_maxAbs": f"{maxabs:.12g}",
    }


def main() -> None:
    out_rows: list[dict[str, str]] = []
    for case in CASES:
        gpu_out = ROOT / f"{case}_out"
        cpu_out = ROOT / f"{case}_cpu_out"
        gpu_header, gpu_rows, gpu_frame = final_material_rows(gpu_out)
        cpu_header, cpu_rows, cpu_frame = final_material_rows(cpu_out)
        result = {
            "case": case,
            **parse_run(gpu_out / "Run.out"),
            "frame": gpu_frame,
            "particles": str(len(gpu_rows)),
            "cpu_frame": cpu_frame,
            "cpu_particles": str(len(cpu_rows)),
            "has_PorePressureAccelDiff": str(all(f"PorePressureAccelDiff.{c}" in gpu_header for c in "xyz")),
        }
        for field in FIELDS:
            add_field_stats(result, gpu_rows, field)
            if cpu_rows:
                result.update(compare_by_idp(gpu_rows, cpu_rows, field))
        for field in VECTOR_FIELDS:
            add_vector_stats(result, gpu_rows, field)
            if cpu_rows:
                result.update(compare_by_idp(gpu_rows, cpu_rows, field))
        out_rows.append(result)

    preferred = ["case", "code", "excluded", "steps", "runtime_s", "frame", "particles", "has_PorePressureAccelDiff"]
    fieldnames = preferred + sorted({k for row in out_rows for k in row.keys()} - set(preferred))
    with (ROOT / "gpu_g5_smoke_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)


if __name__ == "__main__":
    main()
