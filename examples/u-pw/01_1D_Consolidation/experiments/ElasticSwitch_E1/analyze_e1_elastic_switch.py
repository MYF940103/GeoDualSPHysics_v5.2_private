#!/usr/bin/env python3
"""Summarize E1 constitutive-model switch smoke runs."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path


CASES = [
    ("elastic_cpu", "CaseElasticSwitch_E1_Elastic_cpu_out", "CaseElasticSwitch_E1_Elastic_Def.xml"),
    ("dp_cpu", "CaseElasticSwitch_E1_DP_cpu_out", "CaseElasticSwitch_E1_DP_Def.xml"),
    ("softening_legacy_cpu", "CaseElasticSwitch_E1_SofteningLegacy_cpu_out", "CaseElasticSwitch_E1_SofteningLegacy_Def.xml"),
    ("elastic_gpu", "CaseElasticSwitch_E1_Elastic_gpu_out", "CaseElasticSwitch_E1_Elastic_Def.xml"),
]

SUMMARY = Path("e1_elastic_switch_summary.csv")


def read_xml_model(path: Path) -> dict[str, str]:
    info = {
        "xml_model": "default_dp",
        "xml_softening": "0",
        "inferred_model": "1",
    }
    if not path.exists():
        return info
    text = path.read_text(errors="ignore")
    m = re.search(r"<SoilConstitutiveModel[^>]*value=\"([^\"]+)\"", text)
    if m:
        info["xml_model"] = m.group(1)
        info["inferred_model"] = m.group(1)
    m = re.search(r"<Softening[^>]*value=\"([^\"]+)\"", text)
    if m:
        info["xml_softening"] = m.group(1)
    if info["xml_model"] == "default_dp" and info["xml_softening"] == "1":
        info["inferred_model"] = "2"
    return info


def read_run_out(outdir: Path) -> dict[str, str]:
    info = {
        "code": "missing",
        "excluded": "missing",
        "runtime_s": "missing",
        "steps": "missing",
        "frames": "missing",
        "model_log": "missing",
        "softening_log": "missing",
    }
    runout = outdir / "Run.out"
    if not runout.exists():
        return info
    text = runout.read_text(errors="ignore")
    info["code"] = "0" if "Finished execution (code=0)" in text else "unknown"
    patterns = {
        "excluded": r"Excluded particles\.+:\s+(\d+)",
        "runtime_s": r"Total Runtime\.+:\s+([0-9.Ee+-]+)",
        "steps": r"Steps of simulation\.+:\s+(\d+)",
        "frames": r"PART files\.+:\s+(\d+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            info[key] = m.group(1)
    m = re.search(r"SoilConstitutiveModel\.+:\s+(.+)", text)
    if m:
        info["model_log"] = m.group(1).strip()
    m = re.search(r"Strength Softening:\s+(.+)", text)
    if m:
        info["softening_log"] = m.group(1).strip()
    return info


def parse_float(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def scan_csv(outdir: Path) -> dict[str, float | str]:
    data = outdir / "data"
    files = sorted(data.glob("PartCsv_*.csv"))
    metrics: dict[str, float | str] = {
        "partcsv_frames": len(files),
        "max_abs_porepress": 0.0,
        "max_abs_excess": 0.0,
        "max_abs_porepress_rate": 0.0,
        "max_abs_kplastic": 0.0,
        "has_kplastic": "0",
        "has_porepress": "0",
        "has_excess": "0",
    }
    for path in files:
        with path.open(newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            keys = [k.strip() for k in (reader.fieldnames or []) if k]
            metrics["has_kplastic"] = "1" if "Kplastic" in keys else metrics["has_kplastic"]
            metrics["has_porepress"] = "1" if "PorePress" in keys else metrics["has_porepress"]
            metrics["has_excess"] = "1" if "ExcessPorePress" in keys else metrics["has_excess"]
            for raw in reader:
                row = {k.strip(): v for k, v in raw.items() if k}
                metrics["max_abs_porepress"] = max(float(metrics["max_abs_porepress"]), abs(parse_float(row.get("PorePress", "0"))))
                metrics["max_abs_excess"] = max(float(metrics["max_abs_excess"]), abs(parse_float(row.get("ExcessPorePress", "0"))))
                metrics["max_abs_porepress_rate"] = max(float(metrics["max_abs_porepress_rate"]), abs(parse_float(row.get("PorePressRate", "0"))))
                metrics["max_abs_kplastic"] = max(float(metrics["max_abs_kplastic"]), abs(parse_float(row.get("Kplastic", "0"))))
    return metrics


def main() -> None:
    rows = []
    for label, outdir_name, xml_name in CASES:
        outdir = Path(outdir_name)
        row: dict[str, str | float | int] = {"case": label, "outdir": outdir_name}
        row.update(read_xml_model(Path(xml_name)))
        row.update(read_run_out(outdir))
        row.update(scan_csv(outdir))
        if label.startswith("elastic"):
            row["plastic_zero_check"] = "pass" if float(row["max_abs_kplastic"]) == 0.0 else "fail"
        else:
            row["plastic_zero_check"] = "not_required"
        rows.append(row)
    fieldnames = [
        "case", "outdir", "code", "excluded", "runtime_s", "steps", "frames",
        "partcsv_frames", "xml_model", "xml_softening", "inferred_model",
        "model_log", "softening_log", "has_porepress", "has_excess",
        "has_kplastic", "max_abs_porepress", "max_abs_excess",
        "max_abs_porepress_rate", "max_abs_kplastic", "plastic_zero_check",
    ]
    with SUMMARY.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
