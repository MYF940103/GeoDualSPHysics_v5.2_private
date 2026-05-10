#!/usr/bin/env python3
"""Summarize the reduced retrogressive-slope PR smoke output."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def val(row: dict[str, str], key: str, default: float = math.nan) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="") as f:
        return [r for r in csv.DictReader(f, delimiter=";") if r.get("Idp")]


def finite(values):
    return [v for v in values if math.isfinite(v)]


def metrics(first: list[dict[str, str]], last: list[dict[str, str]]):
    first_by_id = {r["Idp"]: r for r in first}
    disp = []
    vel = []
    pore = []
    excess = []
    kplastic = []
    for r in last:
        x, y, z = val(r, "Pos.x [m]"), val(r, "Pos.y [m]"), val(r, "Pos.z [m]")
        vx, vy, vz = val(r, "Vel.x [m/s]"), val(r, "Vel.y [m/s]"), val(r, "Vel.z [m/s]")
        vel.append(math.sqrt(vx * vx + vy * vy + vz * vz))
        pore.append(val(r, "PorePress"))
        excess.append(val(r, "ExcessPorePress"))
        kplastic.append(val(r, "Kplastic"))
        r0 = first_by_id.get(r["Idp"])
        if r0:
            dx = x - val(r0, "Pos.x [m]")
            dy = y - val(r0, "Pos.y [m]")
            dz = z - val(r0, "Pos.z [m]")
            disp.append(math.sqrt(dx * dx + dy * dy + dz * dz))
    return {
        "rows": len(last),
        "max_displacement": max(finite(disp)) if finite(disp) else math.nan,
        "mean_displacement": sum(finite(disp)) / len(finite(disp)) if finite(disp) else math.nan,
        "max_velocity": max(finite(vel)) if finite(vel) else math.nan,
        "mean_velocity": sum(finite(vel)) / len(finite(vel)) if finite(vel) else math.nan,
        "porepress_min": min(finite(pore)),
        "porepress_max": max(finite(pore)),
        "excess_min": min(finite(excess)),
        "excess_max": max(finite(excess)),
        "kplastic_min": min(finite(kplastic)),
        "kplastic_max": max(finite(kplastic)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    files = sorted(args.data_dir.glob("PartCsv_*.csv"))
    if len(files) < 2:
        raise SystemExit("Need at least two PartCsv frames")
    result = metrics(read_csv(files[0]), read_csv(files[-1]))
    result["first_frame"] = files[0].stem.replace("PartCsv_", "")
    result["last_frame"] = files[-1].stem.replace("PartCsv_", "")

    if args.out:
        with args.out.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(result.keys()))
            writer.writeheader()
            writer.writerow(result)
    print(
        "rows={rows} max_disp={max_displacement:.6g} max_vel={max_velocity:.6g} "
        "pore=[{porepress_min:.6g},{porepress_max:.6g}] "
        "excess=[{excess_min:.6g},{excess_max:.6g}] "
        "kplastic=[{kplastic_min:.6g},{kplastic_max:.6g}]".format(**result)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
