#!/usr/bin/env python3
"""Summarize reduced retrogressive-slope softening smoke output."""

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


def mean(values: list[float]) -> float:
    fv = finite(values)
    return sum(fv) / len(fv) if fv else math.nan


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
    softening = int(soil_value(root, "Softening"))

    files = sorted(args.data_dir.glob("PartCsv_*.csv"))
    if len(files) < 2:
        raise SystemExit("Need at least two PartCsv frames")
    first = {r["Idp"]: r for r in read_rows(files[0])}
    last = read_rows(files[-1])

    disp: list[float] = []
    vel: list[float] = []
    kplastic: list[float] = []
    pore: list[float] = []
    excess: list[float] = []
    pprate: list[float] = []
    for r in last:
        x, y, z = val(r, "Pos.x [m]"), val(r, "Pos.y [m]"), val(r, "Pos.z [m]")
        vx, vy, vz = val(r, "Vel.x [m/s]"), val(r, "Vel.y [m/s]"), val(r, "Vel.z [m/s]")
        vel.append(math.sqrt(vx * vx + vy * vy + vz * vz))
        kk = val(r, "Kplastic")
        kplastic.append(kk)
        pore.append(val(r, "PorePress"))
        excess.append(val(r, "ExcessPorePress"))
        pprate.append(abs(val(r, "PorePressRate")))
        r0 = first.get(r["Idp"])
        if r0:
            dx = x - val(r0, "Pos.x [m]")
            dy = y - val(r0, "Pos.y [m]")
            dz = z - val(r0, "Pos.z [m]")
            disp.append(math.sqrt(dx * dx + dy * dy + dz * dz))

    kf = finite(kplastic)
    cohesion = (
        [cr + (cp - cr) * math.exp(-nc * kk) for kk in kf]
        if softening
        else [cp for _ in kf]
    )
    out = {
        "case": args.xml.stem.replace("_Def", ""),
        "frames": len(files),
        "rows": len(last),
        "softening": softening,
        "kplastic_max": max(kf) if kf else math.nan,
        "cohesion_peak": cp,
        "cohesion_residual": cr,
        "cohesion_min_est": min(cohesion) if cohesion else math.nan,
        "max_displacement": max(finite(disp)) if finite(disp) else math.nan,
        "mean_displacement": mean(disp),
        "velocity_max": max(finite(vel)) if finite(vel) else math.nan,
        "velocity_mean": mean(vel),
        "porepress_min": min(finite(pore)) if finite(pore) else math.nan,
        "porepress_max": max(finite(pore)) if finite(pore) else math.nan,
        "excess_min": min(finite(excess)) if finite(excess) else math.nan,
        "excess_max": max(finite(excess)) if finite(excess) else math.nan,
        "porepressrate_maxabs": max(finite(pprate)) if finite(pprate) else math.nan,
    }
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out.keys()))
        writer.writeheader()
        writer.writerow(out)
    print(
        "case={case} softening={softening} kplastic_max={kplastic_max:.6g} "
        "cohesion_min_est={cohesion_min_est:.6g} max_disp={max_displacement:.6g} "
        "vel_max={velocity_max:.6g}".format(**out)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
