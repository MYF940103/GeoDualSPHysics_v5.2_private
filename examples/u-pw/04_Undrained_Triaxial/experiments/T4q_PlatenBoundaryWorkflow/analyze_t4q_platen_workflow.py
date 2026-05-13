#!/usr/bin/env python3
"""Postprocess T4q explicit platen boundary workflow smoke cases."""

from __future__ import annotations

import csv
import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

CASES = {
    "geometry_no_load": "CaseT4q_PlatenGeometry_NoLoad",
    "top_velocity": "CaseT4q_TopVelocity_NoConfinement",
    "top_velocity_lateral": "CaseT4q_TopVelocity_LateralConfinement",
}

RADIUS = 0.03
HEIGHT = 0.10
CENTER_R = 0.012
CENTER_Z_MIN = 0.035
CENTER_Z_MAX = 0.065


def read_rows(path: Path) -> list[dict[str, float | int]]:
    with path.open(newline="") as f:
        reader = csv.reader(f, delimiter=";")
        headers = [h.strip() for h in next(reader) if h.strip()]
        rows: list[dict[str, float | int]] = []
        for raw in reader:
            if len(raw) < len(headers):
                continue
            row: dict[str, float | int] = {}
            for key, val in zip(headers, raw):
                if key in {"Idp", "Type"}:
                    row[key] = int(float(val))
                else:
                    try:
                        row[key] = float(val)
                    except ValueError:
                        row[key] = float("nan")
            rows.append(row)
        return rows


def part_index(path: Path) -> int:
    return int(path.stem.split("_")[-1])


def part_files(case: str) -> list[Path]:
    return sorted((ROOT / f"{case}_out" / "data").glob("PartCsv_*.csv"), key=part_index)


def safe_mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else float("nan")


def parse_times(case: str) -> dict[int, float]:
    run = ROOT / f"{case}_out" / "Run.out"
    times = {0: 0.0}
    if not run.exists():
        return times
    rx = re.compile(r"Part_(\d+)\s+([0-9]+\.[0-9Ee+\-.]*)")
    for line in run.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if m:
            times[int(m.group(1))] = float(m.group(2))
    return times


def parse_summary(case: str) -> dict[str, float | int | str]:
    run = ROOT / f"{case}_out" / "Run.out"
    txt = run.read_text(errors="ignore") if run.exists() else ""
    out: dict[str, float | int | str] = {
        "case": case,
        "code": 0 if "Finished execution (code=0)" in txt else -1,
        "excluded": 0,
        "dtmin_adjustments": 0,
        "fixed_count": 0,
        "moving_count": 0,
        "fluid_count": 0,
    }
    for key, pattern in [
        ("excluded", r"Excluded particles\.+:\s+(\d+)"),
        ("dtmin_adjustments", r"DTs adjusted to DtMin\.+:\s+(\d+)"),
        ("fixed_count", r"Fixed\.+:\s+(\d+)"),
        ("moving_count", r"Moving\.+:\s+(\d+)"),
        ("fluid_count", r"Fluid\.+:\s+(\d+)"),
    ]:
        m = re.search(pattern, txt)
        if m:
            out[key] = int(m.group(1))
    return out


def stress_metrics(row: dict[str, float | int]) -> tuple[float, float]:
    sxx = float(row.get("Sigma_kk.x", 0.0))
    syy = float(row.get("Sigma_kk.y", 0.0))
    szz = float(row.get("Sigma_kk.z", 0.0))
    sxy = float(row.get("Sigma_ij.x", 0.0))
    sxz = float(row.get("Sigma_ij.y", 0.0))
    syz = float(row.get("Sigma_ij.z", 0.0))
    p_eff = -(sxx + syy + szz) / 3.0
    q = math.sqrt(
        max(
            0.0,
            0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
            + 3.0 * (sxy * sxy + sxz * sxz + syz * syz),
        )
    )
    return p_eff, q


def classify(row: dict[str, float | int]) -> str:
    typ = int(row.get("Type", -1))
    z = float(row["Pos.z [m]"])
    if typ == 0:
        return "bottom_platen_fixed"
    if typ == 1:
        return "top_platen_moving"
    if typ == 3:
        return "specimen"
    if z < 0:
        return "bottom_platen_unknown"
    if z > HEIGHT:
        return "top_platen_unknown"
    return "unknown"


def is_measurement(row: dict[str, float | int]) -> bool:
    if int(row.get("Type", -1)) != 3:
        return False
    x = float(row["Pos.x [m]"])
    y = float(row["Pos.y [m]"])
    z = float(row["Pos.z [m]"])
    return math.hypot(x, y) <= CENTER_R and CENTER_Z_MIN <= z <= CENTER_Z_MAX


def frame_metrics(case_key: str, case: str) -> list[dict[str, float | int | str]]:
    times = parse_times(case)
    files = part_files(case)
    if not files:
        return []
    initial = read_rows(files[0])
    init_top = [r for r in initial if classify(r) == "top_platen_moving"]
    init_bottom = [r for r in initial if classify(r) == "bottom_platen_fixed"]
    init_spec = [r for r in initial if classify(r) == "specimen"]
    z_top0 = safe_mean(float(r["Pos.z [m]"]) for r in init_top)
    z_bot0 = safe_mean(float(r["Pos.z [m]"]) for r in init_bottom)
    zmin0 = min(float(r["Pos.z [m]"]) for r in init_spec)
    zmax0 = max(float(r["Pos.z [m]"]) for r in init_spec)
    h0 = zmax0 - zmin0
    out: list[dict[str, float | int | str]] = []
    for pf in files:
        rows = read_rows(pf)
        groups: dict[str, list[dict[str, float | int]]] = {}
        for row in rows:
            groups.setdefault(classify(row), []).append(row)
        spec = groups.get("specimen", [])
        top = groups.get("top_platen_moving", [])
        bottom = groups.get("bottom_platen_fixed", [])
        measure = [r for r in rows if is_measurement(r)]
        vel = [
            math.sqrt(
                float(r.get("Vel.x [m/s]", 0.0)) ** 2
                + float(r.get("Vel.y [m/s]", 0.0)) ** 2
                + float(r.get("Vel.z [m/s]", 0.0)) ** 2
            )
            for r in rows
        ]
        spec_vel = [
            math.sqrt(
                float(r.get("Vel.x [m/s]", 0.0)) ** 2
                + float(r.get("Vel.y [m/s]", 0.0)) ** 2
                + float(r.get("Vel.z [m/s]", 0.0)) ** 2
            )
            for r in spec
        ]
        if spec:
            zmin = min(float(r["Pos.z [m]"]) for r in spec)
            zmax = max(float(r["Pos.z [m]"]) for r in spec)
            axial_strain = (zmax - zmin - h0) / h0 if h0 else float("nan")
        else:
            axial_strain = float("nan")
        pqs = [stress_metrics(r) for r in spec]
        out.append(
            {
                "case": case_key,
                "part": part_index(pf),
                "time": times.get(part_index(pf), float("nan")),
                "total_count": len(rows),
                "specimen_count": len(spec),
                "top_platen_count": len(top),
                "bottom_platen_count": len(bottom),
                "measurement_count": len(measure),
                "platen_contamination_in_measurement": sum(1 for r in rows if is_measurement(r) and int(r.get("Type", -1)) != 3),
                "top_platen_z_mean": safe_mean(float(r["Pos.z [m]"]) for r in top),
                "top_platen_displacement": safe_mean(float(r["Pos.z [m]"]) for r in top) - z_top0 if top else float("nan"),
                "top_platen_vz_mean": safe_mean(float(r.get("Vel.z [m/s]", 0.0)) for r in top),
                "bottom_platen_z_mean": safe_mean(float(r["Pos.z [m]"]) for r in bottom),
                "bottom_platen_displacement": safe_mean(float(r["Pos.z [m]"]) for r in bottom) - z_bot0 if bottom else float("nan"),
                "bottom_platen_vmag_max": max(
                    [
                        math.sqrt(
                            float(r.get("Vel.x [m/s]", 0.0)) ** 2
                            + float(r.get("Vel.y [m/s]", 0.0)) ** 2
                            + float(r.get("Vel.z [m/s]", 0.0)) ** 2
                        )
                        for r in bottom
                    ]
                    or [0.0]
                ),
                "specimen_axial_strain_proxy": axial_strain,
                "specimen_velocity_max": max(spec_vel or [0.0]),
                "velocity_max": max(vel or [0.0]),
                "p_eff_mean": safe_mean(p for p, _ in pqs),
                "q_mean": safe_mean(q for _, q in pqs),
                "porepress_mean": safe_mean(float(r.get("PorePress", 0.0)) for r in spec),
                "porepress_min": min([float(r.get("PorePress", 0.0)) for r in spec] or [0.0]),
                "porepressrate_maxabs": max([abs(float(r.get("PorePressRate", 0.0))) for r in spec] or [0.0]),
                "divvel_maxabs": max([abs(float(r.get("DivVel", 0.0))) for r in spec] or [0.0]),
                "kplastic_max": max([float(r.get("Kplastic", 0.0)) for r in spec] or [0.0]),
            }
        )
    return out


def parse_confinement_diag(case_key: str, case: str) -> list[dict[str, float | int | str]]:
    run = ROOT / f"{case}_out" / "Run.out"
    if not run.exists():
        return []
    by_step: dict[int, dict[str, float | int | str]] = {}
    rx = re.compile(
        r"FlexibleConfiningStress CPU diagnostics: step=(\d+), TimeStep=([0-9Ee+\-.]+), "
        r"p0_eff=([0-9Ee+\-.]+) Pa, targets=(\d+), legacy_targets=(\d+), "
        r"net_force=\(([0-9Ee+\-.]+),([0-9Ee+\-.]+),([0-9Ee+\-.]+)\) N, "
        r"total_abs_force=([0-9Ee+\-.]+) N, max_accel=([0-9Ee+\-.]+) m/s2, "
        r"com_accel=([0-9Ee+\-.]+) m/s2, symmetry_residual=([0-9Ee+\-.]+), "
        r"lateral_selector_active=(\d+)"
    )
    for line in run.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if not m:
            continue
        step = int(m.group(1))
        by_step[step] = (
            {
                "case": case_key,
                "step": step,
                "time": float(m.group(2)),
                "p0_eff": float(m.group(3)),
                "targets": int(m.group(4)),
                "legacy_targets": int(m.group(5)),
                "net_force_x": float(m.group(6)),
                "net_force_y": float(m.group(7)),
                "net_force_z": float(m.group(8)),
                "total_abs_force": float(m.group(9)),
                "max_accel": float(m.group(10)),
                "com_accel": float(m.group(11)),
                "symmetry_residual": float(m.group(12)),
                "lateral_selector_active": int(m.group(13)),
            }
        )
    erx = re.compile(
        r"FlexibleConfiningStress extended diagnostics: step=(\d+), "
        r"fi_min=([0-9Ee+\-.]+), fi_max=([0-9Ee+\-.]+), fi_mean=([0-9Ee+\-.]+), "
        r"fi_threshold=([0-9Ee+\-.]+), fi_selected=(\d+), "
        r"class_interior=(\d+), class_lateral=(\d+), class_top=(\d+), class_bottom=(\d+), "
        r"class_edge=(\d+), class_outside=(\d+), lateral_fi_selected=(\d+), "
        r"cap_fi_selected=(\d+), lateral_inward_radial_accel_mean=([0-9Ee+\-.]+), "
        r"lateral_inward_radial_accel_max=([0-9Ee+\-.]+), "
        r"cap_abs_axial_accel_mean=([0-9Ee+\-.]+), cap_abs_axial_accel_max=([0-9Ee+\-.]+)"
    )
    for line in run.read_text(errors="ignore").splitlines():
        m = erx.search(line)
        if not m:
            continue
        step = int(m.group(1))
        row = by_step.setdefault(step, {"case": case_key, "step": step})
        row.update(
            {
                "fi_min": float(m.group(2)),
                "fi_max": float(m.group(3)),
                "fi_mean": float(m.group(4)),
                "fi_threshold": float(m.group(5)),
                "fi_selected": int(m.group(6)),
                "class_interior": int(m.group(7)),
                "class_lateral": int(m.group(8)),
                "class_top": int(m.group(9)),
                "class_bottom": int(m.group(10)),
                "class_edge": int(m.group(11)),
                "class_outside": int(m.group(12)),
                "lateral_fi_selected": int(m.group(13)),
                "cap_fi_selected": int(m.group(14)),
                "lateral_inward_radial_accel_mean": float(m.group(15)),
                "lateral_inward_radial_accel_max": float(m.group(16)),
                "cap_abs_axial_accel_mean": float(m.group(17)),
                "cap_abs_axial_accel_max": float(m.group(18)),
            }
        )
    return [by_step[k] for k in sorted(by_step)]


def write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    if not rows:
        path.write_text("")
        return
    keys: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def plot_series(frame_rows: list[dict[str, float | int | str]], ykey: str, name: str, ylabel: str) -> None:
    plt.figure(figsize=(7.0, 4.2))
    for case_key in CASES:
        rows = [r for r in frame_rows if r["case"] == case_key]
        if not rows:
            continue
        plt.plot([float(r["time"]) for r in rows], [float(r[ykey]) for r in rows], marker="o", label=case_key)
    plt.xlabel("time [s]")
    plt.ylabel(ylabel)
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIGDIR / f"{name}.{ext}", dpi=180)
    plt.close()


def plot_group_counts(group_rows: list[dict[str, float | int | str]]) -> None:
    labels = [str(r["case"]) for r in group_rows]
    bottom = [float(r["bottom_platen_fixed"]) for r in group_rows]
    top = [float(r["top_platen_moving"]) for r in group_rows]
    spec = [float(r["specimen"]) for r in group_rows]
    x = range(len(labels))
    plt.figure(figsize=(8.0, 4.2))
    plt.bar(x, bottom, label="bottom fixed")
    plt.bar(x, top, bottom=bottom, label="top moving")
    plt.bar(x, spec, bottom=[a + b for a, b in zip(bottom, top)], label="specimen")
    plt.xticks(list(x), labels, rotation=20, ha="right")
    plt.ylabel("particle count")
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIGDIR / f"t4q_group_counts.{ext}", dpi=180)
    plt.close()


def main() -> None:
    all_frames: list[dict[str, float | int | str]] = []
    group_rows: list[dict[str, float | int | str]] = []
    case_summary: list[dict[str, float | int | str]] = []
    confinement_rows: list[dict[str, float | int | str]] = []

    for case_key, case in CASES.items():
        frames = frame_metrics(case_key, case)
        all_frames.extend(frames)
        confinement_rows.extend(parse_confinement_diag(case_key, case))
        summary = parse_summary(case)
        summary["case"] = case_key
        if frames:
            final = frames[-1]
            summary.update(
                {
                    "final_top_platen_displacement": final["top_platen_displacement"],
                    "final_bottom_platen_displacement": final["bottom_platen_displacement"],
                    "final_specimen_axial_strain_proxy": final["specimen_axial_strain_proxy"],
                    "final_measurement_count": final["measurement_count"],
                    "final_platen_contamination_in_measurement": final["platen_contamination_in_measurement"],
                    "final_velocity_max": final["velocity_max"],
                    "final_specimen_velocity_max": final["specimen_velocity_max"],
                    "final_porepress_mean": final["porepress_mean"],
                    "final_porepressrate_maxabs": final["porepressrate_maxabs"],
                    "final_divvel_maxabs": final["divvel_maxabs"],
                    "final_kplastic_max": final["kplastic_max"],
                    "reaction_proxy_available": 0,
                }
            )
            first_rows = read_rows(part_files(case)[0])
            counts = Counter(classify(r) for r in first_rows)
            group_rows.append(
                {
                    "case": case_key,
                    "bottom_platen_fixed": counts.get("bottom_platen_fixed", 0),
                    "top_platen_moving": counts.get("top_platen_moving", 0),
                    "specimen": counts.get("specimen", 0),
                    "unknown": counts.get("unknown", 0),
                    "measurement_count_initial": frames[0]["measurement_count"],
                    "platen_contamination_initial": frames[0]["platen_contamination_in_measurement"],
                }
            )
        case_summary.append(summary)

    write_csv(ROOT / "t4q_frame_metrics.csv", all_frames)
    write_csv(ROOT / "t4q_case_summary.csv", case_summary)
    write_csv(ROOT / "t4q_group_counts.csv", group_rows)
    write_csv(ROOT / "t4q_platen_motion_metrics.csv", all_frames)
    write_csv(ROOT / "t4q_specimen_deformation_metrics.csv", all_frames)
    write_csv(ROOT / "t4q_measurement_region_metrics.csv", all_frames)
    write_csv(ROOT / "t4q_confinement_metrics.csv", confinement_rows)
    write_csv(
        ROOT / "t4q_reaction_proxy_metrics.csv",
        [{"case": key, "reaction_proxy_available": 0, "note": "No validated XML-only reaction output in T4q"} for key in CASES],
    )

    if all_frames:
        plot_series(all_frames, "top_platen_displacement", "t4q_top_platen_displacement", "top platen displacement [m]")
        plot_series(all_frames, "top_platen_vz_mean", "t4q_top_platen_velocity", "top platen vz [m/s]")
        plot_series(all_frames, "bottom_platen_displacement", "t4q_bottom_platen_displacement", "bottom platen displacement [m]")
        plot_series(all_frames, "specimen_axial_strain_proxy", "t4q_specimen_axial_strain", "specimen axial strain proxy")
        plot_series(all_frames, "porepress_mean", "t4q_pore_pressure", "specimen pore pressure mean [Pa]")
        plot_series(all_frames, "velocity_max", "t4q_velocity_max", "velocity max [m/s]")
        plot_series(all_frames, "porepressrate_maxabs", "t4q_porepressrate_maxabs", "PorePressRate maxAbs [Pa/s]")
        plot_series(all_frames, "divvel_maxabs", "t4q_divvel_maxabs", "DivVel maxAbs [1/s]")
    if group_rows:
        plot_group_counts(group_rows)
    if confinement_rows:
        plt.figure(figsize=(7.0, 4.2))
        rows = confinement_rows
        plt.plot([float(r["time"]) for r in rows], [float(r["max_accel"]) for r in rows], marker="o")
        plt.xlabel("time [s]")
        plt.ylabel("lateral confinement max acceleration [m/s2]")
        plt.tight_layout()
        for ext in ("svg", "png"):
            plt.savefig(FIGDIR / f"t4q_lateral_confinement_accel.{ext}", dpi=180)
        plt.close()


if __name__ == "__main__":
    main()
