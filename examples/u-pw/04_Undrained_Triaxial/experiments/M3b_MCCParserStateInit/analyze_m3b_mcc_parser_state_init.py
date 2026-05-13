from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = [
    "CaseM3b_MccPc0_Init",
    "CaseM3b_MccOCR_InitialStress",
]


def read_csv(path: Path) -> list[dict[str, float | int]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        headers = next(reader)
        rows: list[dict[str, float | int]] = []
        for raw in reader:
            if not raw or len(raw) < len(headers):
                continue
            row: dict[str, float | int] = {}
            for key, val in zip(headers, raw):
                if key in {"Idp", "Type"}:
                    row[key] = int(float(val))
                else:
                    try:
                        row[key] = float(val)
                    except ValueError:
                        row[key] = math.nan
            rows.append(row)
    return rows


def part_index(path: Path) -> int:
    return int(path.stem.split("_")[-1])


def part_files(case: str) -> list[Path]:
    return sorted((ROOT / f"{case}_out" / "data").glob("PartCsv_*.csv"), key=part_index)


def parse_summary(case: str) -> dict[str, float | int | str]:
    run = ROOT / f"{case}_out" / "Run.out"
    txt = run.read_text(errors="ignore") if run.exists() else ""
    out: dict[str, float | int | str] = {
        "case": case,
        "code": 0 if "Finished execution (code=0)" in txt else -1,
        "excluded": 0,
        "dtmin_adjustments": 0,
        "mcc_state_output": 0,
        "mcc_init_logged": 1 if "MCC CPU state initialised" in txt else 0,
        "mcc_stress_update_connected": 0 if "MCC stress update is not connected" in txt else -1,
    }
    for key, pattern in [
        ("excluded", r"Excluded particles\.+:\s+(\d+)"),
        ("dtmin_adjustments", r"DTs adjusted to DtMin\.+:\s+(\d+)"),
    ]:
        m = re.search(pattern, txt)
        if m:
            out[key] = int(m.group(1))
    return out


def safe_mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else math.nan


def write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def state_metrics(case: str, label: str, path: Path) -> dict[str, float | int | str]:
    rows = read_csv(path)
    pc = [float(r["MccPc"]) for r in rows if int(r.get("Idp", 0)) >= 148]
    e = [float(r["MccVoidRatio"]) for r in rows if int(r.get("Idp", 0)) >= 148]
    p_eff = [
        -(float(r.get("Sigma_kk.x", 0.0)) + float(r.get("Sigma_kk.y", 0.0)) + float(r.get("Sigma_kk.z", 0.0))) / 3.0
        for r in rows
        if int(r.get("Idp", 0)) >= 148
    ]
    return {
        "case": case,
        "frame": label,
        "particle_count": len(rows),
        "material_like_count": len(pc),
        "pc_min": min(pc) if pc else math.nan,
        "pc_mean": safe_mean(pc),
        "pc_max": max(pc) if pc else math.nan,
        "void_ratio_min": min(e) if e else math.nan,
        "void_ratio_mean": safe_mean(e),
        "void_ratio_max": max(e) if e else math.nan,
        "p_eff_min": min(p_eff) if p_eff else math.nan,
        "p_eff_mean": safe_mean(p_eff),
        "p_eff_max": max(p_eff) if p_eff else math.nan,
        "plastic_vol_strain_max": max(float(r.get("MccPlasticVolStrain", 0.0)) for r in rows),
        "eq_plastic_strain_max": max(float(r.get("MccEqPlasticStrain", 0.0)) for r in rows),
        "yield_flag_max": max(float(r.get("MccYieldFlag", 0.0)) for r in rows),
        "return_status_max": max(float(r.get("MccReturnStatus", 0.0)) for r in rows),
        "yield_residual_maxabs": max(abs(float(r.get("MccYieldResidual", 0.0))) for r in rows),
    }


def main() -> None:
    summaries: list[dict[str, float | int | str]] = []
    state_rows: list[dict[str, float | int | str]] = []
    for case in CASES:
        summary = parse_summary(case)
        files = part_files(case)
        rows = read_csv(files[-1]) if files else []
        summary["partcsv_count"] = len(files)
        summary["particle_count"] = len(rows)
        if rows and "MccPc" in rows[0]:
            summary["mcc_state_output"] = 1
            state_rows.append(state_metrics(case, "initial", files[0]))
            state_rows.append(state_metrics(case, "final", files[-1]))
        summaries.append(summary)
    write_csv(ROOT / "m3b_case_summary.csv", summaries)
    write_csv(ROOT / "m3b_mcc_state_initialization_metrics.csv", state_rows)


if __name__ == "__main__":
    main()
