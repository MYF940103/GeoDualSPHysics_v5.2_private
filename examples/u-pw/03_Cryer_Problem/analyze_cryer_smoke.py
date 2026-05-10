#!/usr/bin/env python3
"""Summarize the reduced Cryer-like PR smoke output.

This script is intentionally lightweight. It reads generated PartCsv files,
finds the material-particle cloud centroid in the first frame, and reports the
nearest-particle pore-pressure history as a center-pressure proxy. It is not a
strict Cryer analytical postprocessor.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def as_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        return [row for row in reader if row]


def finite_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for row in rows:
        p = as_float(row.get("PorePress", "nan"))
        x = as_float(row.get("Pos.x [m]", "nan"))
        z = as_float(row.get("Pos.z [m]", "nan"))
        if math.isfinite(p) and math.isfinite(x) and math.isfinite(z):
            out.append(row)
    return out


def centroid(rows: list[dict[str, str]]) -> tuple[float, float]:
    xs = [as_float(r["Pos.x [m]"]) for r in rows]
    zs = [as_float(r["Pos.z [m]"]) for r in rows]
    return sum(xs) / len(xs), sum(zs) / len(zs)


def nearest_to(rows: list[dict[str, str]], cx: float, cz: float) -> dict[str, str]:
    return min(
        rows,
        key=lambda r: (as_float(r["Pos.x [m]"]) - cx) ** 2
        + (as_float(r["Pos.z [m]"]) - cz) ** 2,
    )


def frame_time_from_name(path: Path) -> str:
    stem = path.stem
    return stem.replace("PartCsv_", "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    files = sorted(args.data_dir.glob("PartCsv_*.csv"))
    if not files:
        raise SystemExit(f"No PartCsv files found in {args.data_dir}")

    first = finite_rows(read_rows(files[0]))
    if not first:
        raise SystemExit(f"No finite pore-pressure rows in {files[0]}")
    cx, cz = centroid(first)

    records = []
    for path in files:
        rows = finite_rows(read_rows(path))
        if not rows:
            continue
        center = nearest_to(rows, cx, cz)
        pore = [as_float(r["PorePress"]) for r in rows]
        excess = [as_float(r.get("ExcessPorePress", "nan")) for r in rows]
        records.append(
            {
                "frame": frame_time_from_name(path),
                "center_x": as_float(center["Pos.x [m]"]),
                "center_z": as_float(center["Pos.z [m]"]),
                "center_porepress": as_float(center["PorePress"]),
                "center_excess": as_float(center.get("ExcessPorePress", "nan")),
                "porepress_min": min(pore),
                "porepress_max": max(pore),
                "excess_min": min(v for v in excess if math.isfinite(v)),
                "excess_max": max(v for v in excess if math.isfinite(v)),
                "particle_rows": len(rows),
            }
        )

    if args.out:
        with args.out.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)

    last = records[-1]
    print(
        "frames={frames} center_porepress={p:.6g} center_excess={e:.6g} "
        "porepress_range=[{pmin:.6g},{pmax:.6g}] excess_range=[{emin:.6g},{emax:.6g}]".format(
            frames=len(records),
            p=last["center_porepress"],
            e=last["center_excess"],
            pmin=last["porepress_min"],
            pmax=last["porepress_max"],
            emin=last["excess_min"],
            emax=last["excess_max"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
