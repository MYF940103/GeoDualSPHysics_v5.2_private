from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = [
    ("gpu_hydrostatic", ROOT / "Case1DConsolidation_PR_GPU_G3_Hydro_out"),
    ("gpu_analytical_excess", ROOT / "Case1DConsolidation_PR_GPU_G3_Analytical_out"),
    ("cpu_hydrostatic_reference", ROOT / "Case1DConsolidation_PR_GPU_G3_Hydro_cpu_out"),
    ("cpu_analytical_excess_reference", ROOT / "Case1DConsolidation_PR_GPU_G3_Analytical_cpu_out"),
]
COMPARE = [
    ("hydrostatic", "gpu_hydrostatic", "cpu_hydrostatic_reference"),
    ("analytical_excess", "gpu_analytical_excess", "cpu_analytical_excess_reference"),
]
FIELDS = [
    "PorePress",
    "ExcessPorePress",
    "PorePressRate",
    "DivVel",
    "LapPorePress",
    "LapZ",
]


def parse_run(run_path: Path) -> dict[str, str]:
    text = run_path.read_text(errors="replace") if run_path.exists() else ""
    code = re.search(r"Finished execution \(code=(\d+)\)", text)
    excluded = re.search(r"Excluded particles\.+:\s*(\d+)", text)
    steps = re.search(r"Steps of simulation\.+:\s*(\d+)", text)
    runtime = re.search(r"Total Runtime\.+:\s*([0-9.Ee+-]+)", text)
    dt_pore = re.search(r"dt_pore=([0-9.Ee+-]+)", text)
    part1 = re.search(r"Part_0001\s+([0-9.Ee+-]+)", text)
    return {
        "code": code.group(1) if code else "",
        "excluded": excluded.group(1) if excluded else "",
        "steps": steps.group(1) if steps else "",
        "runtime_s": runtime.group(1) if runtime else "",
        "dt_pore": dt_pore.group(1) if dt_pore else "",
        "part1_time": part1.group(1) if part1 else "",
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


def finite(values: list[float]) -> list[float]:
    return [v for v in values if math.isfinite(v)]


def stats(values: list[float]) -> tuple[float, float, float, float]:
    values = finite(values)
    if not values:
        return (math.nan, math.nan, math.nan, math.nan)
    return (min(values), max(values), sum(values) / len(values), max(abs(v) for v in values))


def by_idp(rows: list[dict[str, float]]) -> dict[int, dict[str, float]]:
    out = {}
    for row in rows:
        if int(row.get("Type", -1)) == 3:
            out[int(row["Idp"])] = row
    return out


def summarize_case(label: str, out_dir: Path) -> tuple[dict[str, str], dict[int, float]]:
    run = parse_run(out_dir / "Run.out")
    p0 = out_dir / "data" / "PartCsv_0000.csv"
    parts = sorted((out_dir / "data").glob("PartCsv_*.csv"))
    result = {"case": label, **run}
    deltas_by_id: dict[int, float] = {}
    if not p0.exists() or len(parts) < 2:
        result.update({"frame": "", "particles": "0", "material": "0"})
        return result, deltas_by_id

    header0, rows0 = read_part(p0)
    header1, rows1 = read_part(parts[-1])
    material1 = [r for r in rows1 if int(r.get("Type", -1)) == 3]
    result.update({"frame": parts[-1].stem, "particles": str(len(rows1)), "material": str(len(material1))})
    for field in FIELDS:
        values = [r[field] for r in material1 if field in r and math.isfinite(r[field])]
        mn, mx, mean, maxabs = stats(values)
        result[f"{field}_min"] = f"{mn:.12g}"
        result[f"{field}_max"] = f"{mx:.12g}"
        result[f"{field}_mean"] = f"{mean:.12g}"
        result[f"{field}_maxAbs"] = f"{maxabs:.12g}"

    rows0_id = by_idp(rows0)
    rows1_id = by_idp(rows1)
    ids = sorted(set(rows0_id) & set(rows1_id))
    deltas = []
    pred_err = []
    dt = float(run["part1_time"]) if run["part1_time"] else math.nan
    if (not math.isfinite(dt) or dt <= 0.0) and run["dt_pore"]:
        # Run.out prints very small PartTime values with six decimals, so a
        # one-step dt_pore smoke can appear as 0.000000 in the table.
        dt = float(run["dt_pore"])
    for pid in ids:
        if "PorePress" in rows0_id[pid] and "PorePress" in rows1_id[pid]:
            dp = rows1_id[pid]["PorePress"] - rows0_id[pid]["PorePress"]
            deltas.append(dp)
            deltas_by_id[pid] = dp
            if math.isfinite(dt) and "PorePressRate" in rows1_id[pid]:
                pred_err.append(dp - rows1_id[pid]["PorePressRate"] * dt)
    for prefix, values in (("DeltaPorePress", deltas), ("DeltaMinusRateDt", pred_err)):
        mn, mx, mean, maxabs = stats(values)
        result[f"{prefix}_min"] = f"{mn:.12g}"
        result[f"{prefix}_max"] = f"{mx:.12g}"
        result[f"{prefix}_mean"] = f"{mean:.12g}"
        result[f"{prefix}_maxAbs"] = f"{maxabs:.12g}"
    return result, deltas_by_id


def main() -> None:
    rows = []
    deltas = {}
    for label, out_dir in CASES:
        row, delta = summarize_case(label, out_dir)
        rows.append(row)
        deltas[label] = delta

    for label, gpu, cpu in COMPARE:
        ids = sorted(set(deltas.get(gpu, {})) & set(deltas.get(cpu, {})))
        diff = [deltas[gpu][pid] - deltas[cpu][pid] for pid in ids]
        mn, mx, mean, maxabs = stats(diff)
        rows.append({
            "case": f"compare_{label}_gpu_minus_cpu_delta",
            "code": "",
            "excluded": "",
            "steps": "",
            "runtime_s": "",
            "dt_pore": "",
            "part1_time": "",
            "frame": "",
            "particles": str(len(ids)),
            "material": str(len(ids)),
            "DeltaDiff_min": f"{mn:.12g}",
            "DeltaDiff_max": f"{mx:.12g}",
            "DeltaDiff_mean": f"{mean:.12g}",
            "DeltaDiff_maxAbs": f"{maxabs:.12g}",
        })

    fieldnames = sorted({k for row in rows for k in row.keys()})
    preferred = ["case", "code", "excluded", "steps", "runtime_s", "dt_pore", "part1_time", "frame", "particles", "material"]
    fieldnames = preferred + [k for k in fieldnames if k not in preferred]
    with (ROOT / "gpu_g3_smoke_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
