#!/usr/bin/env python3
"""Summarize the reduced Sainte-Monique placeholder PR smoke output."""

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


def finite(values: list[float]) -> list[float]:
    return [v for v in values if math.isfinite(v)]


def range_or_nan(values: list[float]) -> tuple[float, float]:
    fv = finite(values)
    return (min(fv), max(fv)) if fv else (math.nan, math.nan)


def mean_or_nan(values: list[float]) -> float:
    fv = finite(values)
    return sum(fv) / len(fv) if fv else math.nan


def metrics(first: list[dict[str, str]], last: list[dict[str, str]]) -> dict[str, float | int | str]:
    first_by_id = {r["Idp"]: r for r in first}
    disp: list[float] = []
    vel: list[float] = []
    pore: list[float] = []
    excess: list[float] = []
    pprate: list[float] = []
    divvel: list[float] = []
    kplastic: list[float] = []
    for r in last:
        x, y, z = val(r, "Pos.x [m]"), val(r, "Pos.y [m]"), val(r, "Pos.z [m]")
        vx, vy, vz = val(r, "Vel.x [m/s]"), val(r, "Vel.y [m/s]"), val(r, "Vel.z [m/s]")
        vel.append(math.sqrt(vx * vx + vy * vy + vz * vz))
        pore.append(val(r, "PorePress"))
        excess.append(val(r, "ExcessPorePress"))
        pprate.append(abs(val(r, "PorePressRate")))
        divvel.append(val(r, "DivVel"))
        kplastic.append(val(r, "Kplastic"))
        r0 = first_by_id.get(r["Idp"])
        if r0:
            dx = x - val(r0, "Pos.x [m]")
            dy = y - val(r0, "Pos.y [m]")
            dz = z - val(r0, "Pos.z [m]")
            disp.append(math.sqrt(dx * dx + dy * dy + dz * dz))

    pore_min, pore_max = range_or_nan(pore)
    excess_min, excess_max = range_or_nan(excess)
    div_min, div_max = range_or_nan(divvel)
    kp_min, kp_max = range_or_nan(kplastic)
    return {
        "rows": len(last),
        "max_displacement": max(finite(disp)) if finite(disp) else math.nan,
        "mean_displacement": mean_or_nan(disp),
        "max_velocity": max(finite(vel)) if finite(vel) else math.nan,
        "mean_velocity": mean_or_nan(vel),
        "porepress_min": pore_min,
        "porepress_max": pore_max,
        "excess_min": excess_min,
        "excess_max": excess_max,
        "porepressrate_maxabs": max(finite(pprate)) if finite(pprate) else math.nan,
        "divvel_min": div_min,
        "divvel_max": div_max,
        "kplastic_min": kp_min,
        "kplastic_max": kp_max,
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
        "pprate_maxabs={porepressrate_maxabs:.6g} divvel=[{divvel_min:.6g},{divvel_max:.6g}] "
        "kplastic=[{kplastic_min:.6g},{kplastic_max:.6g}]".format(**result)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
