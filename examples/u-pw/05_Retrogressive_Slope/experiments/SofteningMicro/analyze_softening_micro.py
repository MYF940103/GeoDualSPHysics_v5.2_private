#!/usr/bin/env python3
"""Summarize a softening micro smoke run."""

from __future__ import annotations

import argparse
import csv
import math
import xml.etree.ElementTree as ET
from pathlib import Path


def val(row: dict[str, str], key: str, default: float = math.nan) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="") as f:
        return [r for r in csv.DictReader(f, delimiter=";") if r.get("Idp")]


def soil_value(root: ET.Element, name: str, default: float = 0.0) -> float:
    elem = root.find(f".//soils/{name}")
    if elem is None:
        return default
    try:
        return float(elem.attrib.get("value", default))
    except ValueError:
        return default


def finite(values: list[float]) -> list[float]:
    return [v for v in values if math.isfinite(v)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("xml", type=Path)
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    root = ET.parse(args.xml).getroot()
    cp = soil_value(root, "coh")
    cr = soil_value(root, "coh_r", cp)
    nc = soil_value(root, "n_coh")
    pp = soil_value(root, "phi")
    pr = soil_value(root, "phi_r", pp)
    np = soil_value(root, "n_phi")
    softening = int(soil_value(root, "Softening"))

    files = sorted(args.data_dir.glob("PartCsv_*.csv"))
    if len(files) < 2:
        raise SystemExit("Need at least two PartCsv frames")
    rows = read_rows(files[-1])
    k = [val(r, "Kplastic") for r in rows]
    v = [
        math.sqrt(
            val(r, "Vel.x [m/s]") ** 2
            + val(r, "Vel.y [m/s]") ** 2
            + val(r, "Vel.z [m/s]") ** 2
        )
        for r in rows
    ]
    pore = [val(r, "PorePress") for r in rows]
    excess = [val(r, "ExcessPorePress") for r in rows]

    kf = finite(k)
    vf = finite(v)
    pf = finite(pore)
    ef = finite(excess)
    softened_c = [cr + (cp - cr) * math.exp(-nc * kk) for kk in kf]
    softened_phi = [pr + (pp - pr) * math.exp(-np * kk) for kk in kf]

    out = {
        "case": args.xml.stem.replace("_Def", ""),
        "frames": len(files),
        "rows": len(rows),
        "softening": softening,
        "kplastic_min": min(kf) if kf else math.nan,
        "kplastic_max": max(kf) if kf else math.nan,
        "cohesion_peak": cp,
        "cohesion_residual": cr,
        "cohesion_min_est": min(softened_c) if softened_c else math.nan,
        "phi_peak_deg": pp,
        "phi_residual_deg": pr,
        "phi_min_est_deg": min(softened_phi) if softened_phi else math.nan,
        "velocity_max": max(vf) if vf else math.nan,
        "velocity_mean": sum(vf) / len(vf) if vf else math.nan,
        "porepress_min": min(pf) if pf else math.nan,
        "porepress_max": max(pf) if pf else math.nan,
        "excess_min": min(ef) if ef else math.nan,
        "excess_max": max(ef) if ef else math.nan,
    }
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out.keys()))
        writer.writeheader()
        writer.writerow(out)
    print(
        "case={case} softening={softening} kplastic_max={kplastic_max:.6g} "
        "cohesion_min_est={cohesion_min_est:.6g} velocity_max={velocity_max:.6g}".format(**out)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
