from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = [
    ("gpu_static_boundary", ROOT / "Case1DConsolidation_PR_GPU_G4_StaticBoundary_out"),
    ("cpu_static_boundary_reference", ROOT / "Case1DConsolidation_PR_GPU_G4_StaticBoundary_cpu_out"),
    ("gpu_diffusion", ROOT / "Case1DConsolidation_PR_GPU_G4_Diffusion_out"),
    ("cpu_diffusion_reference", ROOT / "Case1DConsolidation_PR_GPU_G4_Diffusion_cpu_out"),
]
COMPARE = [
    ("static_boundary", "gpu_static_boundary", "cpu_static_boundary_reference"),
    ("diffusion", "gpu_diffusion", "cpu_diffusion_reference"),
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
    return {
        "code": (re.search(r"Finished execution \(code=(\d+)\)", text) or ["", ""])[1],
        "excluded": (re.search(r"Excluded particles\.+:\s*(\d+)", text) or ["", ""])[1],
        "steps": (re.search(r"Steps of simulation\.+:\s*(\d+)", text) or ["", ""])[1],
        "runtime_s": (re.search(r"Total Runtime\.+:\s*([0-9.Ee+-]+)", text) or ["", ""])[1],
        "dt_pore": (re.search(r"dt_pore=([0-9.Ee+-]+)", text) or ["", ""])[1],
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


def material_rows(rows: list[dict[str, float]]) -> list[dict[str, float]]:
    return [r for r in rows if int(r.get("Type", -1)) == 3]


def summarize_case(label: str, out_dir: Path) -> tuple[dict[str, str], dict[int, dict[str, float]]]:
    run = parse_run(out_dir / "Run.out")
    parts = sorted((out_dir / "data").glob("PartCsv_*.csv"))
    result = {"case": label, **run, "frame": "", "particles": "0", "material": "0"}
    final_by_id: dict[int, dict[str, float]] = {}
    if not parts:
        return result, final_by_id

    header, rows = read_part(parts[-1])
    mats = material_rows(rows)
    final_by_id = by_idp(rows)
    result.update({"frame": parts[-1].stem, "particles": str(len(rows)), "material": str(len(mats))})
    for field in FIELDS:
        values = [r[field] for r in mats if field in r and math.isfinite(r[field])]
        mn, mx, mean, maxabs = stats(values)
        result[f"{field}_min"] = f"{mn:.12g}"
        result[f"{field}_max"] = f"{mx:.12g}"
        result[f"{field}_mean"] = f"{mean:.12g}"
        result[f"{field}_maxAbs"] = f"{maxabs:.12g}"

    zvals = [r["Pos.z"] for r in mats if "Pos.z" in r and math.isfinite(r["Pos.z"])]
    if zvals and all("ExcessPorePress" in r for r in mats):
        zmin, zmax = min(zvals), max(zvals)
        # Mirrors the XML h=hdp*dp = 1.8*0.01 used by these smoke cases.
        thick = 0.018
        top = [r["ExcessPorePress"] for r in mats if r["Pos.z"] >= zmax - thick]
        bottom = [r["ExcessPorePress"] for r in mats if r["Pos.z"] <= zmin + thick]
        ref = [r["ExcessPorePress"] for r in mats if zmin + thick < r["Pos.z"] <= zmin + 2 * thick]
        ref_mean = sum(ref) / len(ref) if ref else math.nan
        bottom_proxy = [v - ref_mean for v in bottom] if math.isfinite(ref_mean) else []
        result["zmin"] = f"{zmin:.12g}"
        result["zmax"] = f"{zmax:.12g}"
        result["top_excess_maxAbs"] = f"{stats(top)[3]:.12g}"
        result["bottom_ref_excess_mean"] = f"{ref_mean:.12g}"
        result["bottom_minus_ref_maxAbs"] = f"{stats(bottom_proxy)[3]:.12g}"
    return result, final_by_id


def main() -> None:
    rows = []
    final = {}
    for label, out_dir in CASES:
        row, byid = summarize_case(label, out_dir)
        rows.append(row)
        final[label] = byid

    for label, gpu, cpu in COMPARE:
        ids = sorted(set(final.get(gpu, {})) & set(final.get(cpu, {})))
        for field in ("PorePress", "ExcessPorePress", "PorePressRate", "LapPorePress", "LapZ"):
            diff = [
                final[gpu][pid][field] - final[cpu][pid][field]
                for pid in ids
                if field in final[gpu][pid] and field in final[cpu][pid]
            ]
            mn, mx, mean, maxabs = stats(diff)
            rows.append({
                "case": f"compare_{label}_gpu_minus_cpu_{field}",
                "particles": str(len(diff)),
                "Delta_min": f"{mn:.12g}",
                "Delta_max": f"{mx:.12g}",
                "Delta_mean": f"{mean:.12g}",
                "Delta_maxAbs": f"{maxabs:.12g}",
            })

    fieldnames = sorted({k for row in rows for k in row})
    preferred = ["case", "code", "excluded", "steps", "runtime_s", "dt_pore", "frame", "particles", "material"]
    fieldnames = preferred + [k for k in fieldnames if k not in preferred]
    with (ROOT / "gpu_g4_smoke_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
