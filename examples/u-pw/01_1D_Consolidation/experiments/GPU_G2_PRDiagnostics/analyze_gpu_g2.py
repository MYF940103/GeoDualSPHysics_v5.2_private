from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = [
    ("gpu_hydrostatic", ROOT / "Case1DConsolidation_PR_GPU_G2_Hydro_out"),
    ("gpu_analytical_excess", ROOT / "Case1DConsolidation_PR_GPU_G2_Analytical_out"),
    ("cpu_hydrostatic_reference", ROOT / "Case1DConsolidation_PR_GPU_G2_Hydro_cpu_out"),
    ("cpu_analytical_excess_reference", ROOT / "Case1DConsolidation_PR_GPU_G2_Analytical_cpu_out"),
]
FIELDS = [
    "PorePress",
    "ExcessPorePress",
    "PorePressRate",
    "DivVel",
    "LapPorePress",
    "LapZ",
]
WATER_DENSITY = 1000.0
G_H = 9.810000419616699


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
    if not values:
        return (math.nan, math.nan, math.nan, math.nan)
    return (min(values), max(values), sum(values) / len(values), max(abs(v) for v in values))


def main() -> None:
    out_rows = []
    for label, out_dir in CASES:
        run = parse_run(out_dir / "Run.out")
        parts = sorted((out_dir / "data").glob("PartCsv_*.csv"))
        if not parts:
            out_rows.append({"case": label, **run, "frame": "", "particles": "0", "material": "0"})
            continue
        part = parts[-1]
        header, rows = read_part(part)
        material = [r for r in rows if int(r.get("Type", -1)) == 3]
        result = {"case": label, **run, "frame": part.stem, "particles": str(len(rows)), "material": str(len(material))}
        for field in FIELDS:
            values = [r[field] for r in material if field in r and math.isfinite(r[field])]
            mn, mx, mean, maxabs = stats(values)
            result[f"{field}_min"] = f"{mn:.12g}"
            result[f"{field}_max"] = f"{mx:.12g}"
            result[f"{field}_mean"] = f"{mean:.12g}"
            result[f"{field}_maxAbs"] = f"{maxabs:.12g}"
        if "LapPorePress" in header and "LapZ" in header:
            residual = [
                r["LapPorePress"] / (WATER_DENSITY * G_H) + r["LapZ"]
                for r in material
                if math.isfinite(r.get("LapPorePress", math.nan)) and math.isfinite(r.get("LapZ", math.nan))
            ]
            mn, mx, mean, maxabs = stats(residual)
            result["HeadResidual_min"] = f"{mn:.12g}"
            result["HeadResidual_max"] = f"{mx:.12g}"
            result["HeadResidual_mean"] = f"{mean:.12g}"
            result["HeadResidual_maxAbs"] = f"{maxabs:.12g}"
        out_rows.append(result)

    fieldnames = sorted({k for row in out_rows for k in row.keys()})
    preferred = ["case", "code", "excluded", "steps", "runtime_s", "frame", "particles", "material"]
    fieldnames = preferred + [k for k in fieldnames if k not in preferred]
    with (ROOT / "gpu_g2_smoke_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)


if __name__ == "__main__":
    main()
