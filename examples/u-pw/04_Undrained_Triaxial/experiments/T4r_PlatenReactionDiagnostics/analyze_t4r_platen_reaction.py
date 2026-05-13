#!/usr/bin/env python3
"""Postprocess T4r platen reaction proxy and specimen-only stress diagnostics."""

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
    "platen_no_confinement": "CaseT4r_PlatenAxial_NoConfinement",
    "platen_lateral_confinement": "CaseT4r_PlatenAxial_LateralConfinement",
}

RADIUS = 0.03
HEIGHT = 0.10
AREA0 = math.pi * RADIUS * RADIUS
REGIONS = {
    "core_small": {"rmax": 0.012, "zmin": 0.035, "zmax": 0.065},
    "core_medium": {"rmax": 0.018, "zmin": 0.025, "zmax": 0.075},
    "specimen_minus_edges": {"rmax": 0.020, "zmin": 0.015, "zmax": 0.085},
}


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


def safe_std(values: Iterable[float]) -> float:
    vals = list(values)
    if len(vals) < 2:
        return 0.0 if vals else float("nan")
    mu = safe_mean(vals)
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))


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


def parse_summary(case_key: str, case: str) -> dict[str, float | int | str]:
    run = ROOT / f"{case}_out" / "Run.out"
    txt = run.read_text(errors="ignore") if run.exists() else ""
    out: dict[str, float | int | str] = {
        "case": case_key,
        "case_name": case,
        "code": 0 if "Finished execution (code=0)" in txt else -1,
        "excluded": 0,
        "dtmin_adjustments": 0,
        "fixed_count": 0,
        "moving_count": 0,
        "fluid_count": 0,
        "true_reaction_available": 0,
        "reaction_type": "specimen_stress_proxy",
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


def classify(row: dict[str, float | int]) -> str:
    typ = int(row.get("Type", -1))
    if typ == 0:
        return "bottom_platen_fixed"
    if typ == 1:
        return "top_platen_moving"
    if typ == 3:
        return "specimen"
    return "unknown"


def is_specimen(row: dict[str, float | int]) -> bool:
    return classify(row) == "specimen"


def in_region(row: dict[str, float | int], name: str) -> bool:
    if not is_specimen(row):
        return False
    cfg = REGIONS[name]
    x = float(row["Pos.x [m]"])
    y = float(row["Pos.y [m]"])
    z = float(row["Pos.z [m]"])
    return math.hypot(x, y) <= cfg["rmax"] and cfg["zmin"] <= z <= cfg["zmax"]


def stress_components(row: dict[str, float | int]) -> tuple[float, float, float, float, float, float]:
    return (
        float(row.get("Sigma_kk.x", 0.0)),
        float(row.get("Sigma_kk.y", 0.0)),
        float(row.get("Sigma_kk.z", 0.0)),
        float(row.get("Sigma_ij.x", 0.0)),
        float(row.get("Sigma_ij.y", 0.0)),
        float(row.get("Sigma_ij.z", 0.0)),
    )


def stress_metrics_for(rows: list[dict[str, float | int]]) -> dict[str, float]:
    if not rows:
        return {
            "sigma_xx_mean": float("nan"),
            "sigma_yy_mean": float("nan"),
            "sigma_zz_mean": float("nan"),
            "sigma_a_proxy": float("nan"),
            "reaction_force_proxy": float("nan"),
            "p_eff_proxy": float("nan"),
            "q_proxy": float("nan"),
        }
    sxx = [stress_components(r)[0] for r in rows]
    syy = [stress_components(r)[1] for r in rows]
    szz = [stress_components(r)[2] for r in rows]
    sxy = [stress_components(r)[3] for r in rows]
    sxz = [stress_components(r)[4] for r in rows]
    syz = [stress_components(r)[5] for r in rows]
    sxxm, syym, szzm = safe_mean(sxx), safe_mean(syy), safe_mean(szz)
    sxym, sxzm, syzm = safe_mean(sxy), safe_mean(sxz), safe_mean(syz)
    p_eff = -(sxxm + syym + szzm) / 3.0
    q = math.sqrt(
        max(
            0.0,
            0.5 * ((sxxm - syym) ** 2 + (syym - szzm) ** 2 + (szzm - sxxm) ** 2)
            + 3.0 * (sxym * sxym + sxzm * sxzm + syzm * syzm),
        )
    )
    sigma_a = -szzm
    return {
        "sigma_xx_mean": sxxm,
        "sigma_yy_mean": syym,
        "sigma_zz_mean": szzm,
        "sigma_a_proxy": sigma_a,
        "reaction_force_proxy": sigma_a * AREA0,
        "p_eff_proxy": p_eff,
        "q_proxy": q,
    }


def velocity_mag(row: dict[str, float | int]) -> float:
    return math.sqrt(
        float(row.get("Vel.x [m/s]", 0.0)) ** 2
        + float(row.get("Vel.y [m/s]", 0.0)) ** 2
        + float(row.get("Vel.z [m/s]", 0.0)) ** 2
    )


def frame_metrics(case_key: str, case: str) -> tuple[list[dict[str, float | int | str]], list[dict[str, float | int | str]]]:
    files = part_files(case)
    if not files:
        return [], []
    times = parse_times(case)
    initial = read_rows(files[0])
    init_top = [r for r in initial if classify(r) == "top_platen_moving"]
    init_bottom = [r for r in initial if classify(r) == "bottom_platen_fixed"]
    init_spec = [r for r in initial if is_specimen(r)]
    z_top0 = safe_mean(float(r["Pos.z [m]"]) for r in init_top)
    z_bot0 = safe_mean(float(r["Pos.z [m]"]) for r in init_bottom)
    zmin0 = min(float(r["Pos.z [m]"]) for r in init_spec)
    zmax0 = max(float(r["Pos.z [m]"]) for r in init_spec)
    rmean0 = safe_mean(math.hypot(float(r["Pos.x [m]"]), float(r["Pos.y [m]"])) for r in init_spec)
    h0 = zmax0 - zmin0

    frames: list[dict[str, float | int | str]] = []
    region_rows: list[dict[str, float | int | str]] = []
    for pf in files:
        rows = read_rows(pf)
        part = part_index(pf)
        time = times.get(part, float("nan"))
        spec = [r for r in rows if is_specimen(r)]
        top = [r for r in rows if classify(r) == "top_platen_moving"]
        bottom = [r for r in rows if classify(r) == "bottom_platen_fixed"]
        zmin = min(float(r["Pos.z [m]"]) for r in spec)
        zmax = max(float(r["Pos.z [m]"]) for r in spec)
        h = zmax - zmin
        rmean = safe_mean(math.hypot(float(r["Pos.x [m]"]), float(r["Pos.y [m]"])) for r in spec)
        axial_strain = (h - h0) / h0 if h0 else float("nan")
        radial_strain = (rmean - rmean0) / rmean0 if rmean0 else float("nan")
        full_stress = stress_metrics_for(spec)
        frame = {
            "case": case_key,
            "part": part,
            "time": time,
            "total_count": len(rows),
            "specimen_count": len(spec),
            "top_platen_count": len(top),
            "bottom_platen_count": len(bottom),
            "measurement_core_small_count": sum(1 for r in rows if in_region(r, "core_small")),
            "platen_contamination_core_small": sum(1 for r in rows if not is_specimen(r) and in_region(r, "core_small")),
            "top_platen_displacement": safe_mean(float(r["Pos.z [m]"]) for r in top) - z_top0 if top else float("nan"),
            "top_platen_vz_mean": safe_mean(float(r.get("Vel.z [m/s]", 0.0)) for r in top),
            "bottom_platen_displacement": safe_mean(float(r["Pos.z [m]"]) for r in bottom) - z_bot0 if bottom else float("nan"),
            "bottom_platen_vmag_max": max([velocity_mag(r) for r in bottom] or [0.0]),
            "specimen_axial_strain_proxy": axial_strain,
            "specimen_radial_strain_proxy": radial_strain,
            "velocity_max": max([velocity_mag(r) for r in rows] or [0.0]),
            "specimen_velocity_max": max([velocity_mag(r) for r in spec] or [0.0]),
            "porepress_mean": safe_mean(float(r.get("PorePress", 0.0)) for r in spec),
            "porepress_std": safe_std(float(r.get("PorePress", 0.0)) for r in spec),
            "porepressrate_maxabs": max([abs(float(r.get("PorePressRate", 0.0))) for r in spec] or [0.0]),
            "divvel_maxabs": max([abs(float(r.get("DivVel", 0.0))) for r in spec] or [0.0]),
            "kplastic_max": max([float(r.get("Kplastic", 0.0)) for r in spec] or [0.0]),
            "true_reaction_available": 0,
            "reaction_type": "specimen_stress_proxy",
            **full_stress,
        }
        frames.append(frame)
        for region in REGIONS:
            rrows = [r for r in rows if in_region(r, region)]
            sm = stress_metrics_for(rrows)
            region_rows.append(
                {
                    "case": case_key,
                    "part": part,
                    "time": time,
                    "region": region,
                    "particle_count": len(rrows),
                    "platen_contamination": sum(1 for r in rows if not is_specimen(r) and in_region(r, region)),
                    "porepress_mean": safe_mean(float(r.get("PorePress", 0.0)) for r in rrows),
                    "porepress_std": safe_std(float(r.get("PorePress", 0.0)) for r in rrows),
                    "porepressrate_maxabs": max([abs(float(r.get("PorePressRate", 0.0))) for r in rrows] or [0.0]),
                    "divvel_mean": safe_mean(float(r.get("DivVel", 0.0)) for r in rrows),
                    "divvel_maxabs": max([abs(float(r.get("DivVel", 0.0))) for r in rrows] or [0.0]),
                    "kplastic_max": max([float(r.get("Kplastic", 0.0)) for r in rrows] or [0.0]),
                    **sm,
                }
            )
    return frames, region_rows


def parse_confinement_diag(case_key: str, case: str) -> list[dict[str, float | int | str]]:
    run = ROOT / f"{case}_out" / "Run.out"
    if not run.exists():
        return []
    by_step: dict[int, dict[str, float | int | str]] = {}
    text = run.read_text(errors="ignore").splitlines()
    rx = re.compile(
        r"FlexibleConfiningStress CPU diagnostics: step=(\d+), TimeStep=([0-9Ee+\-.]+), "
        r"p0_eff=([0-9Ee+\-.]+) Pa, targets=(\d+), legacy_targets=(\d+), "
        r"net_force=\(([0-9Ee+\-.]+),([0-9Ee+\-.]+),([0-9Ee+\-.]+)\) N, "
        r"total_abs_force=([0-9Ee+\-.]+) N, max_accel=([0-9Ee+\-.]+) m/s2, "
        r"com_accel=([0-9Ee+\-.]+) m/s2, symmetry_residual=([0-9Ee+\-.]+), "
        r"lateral_selector_active=(\d+)"
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
    for line in text:
        m = rx.search(line)
        if not m:
            continue
        step = int(m.group(1))
        by_step[step] = {
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
    for line in text:
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
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def plot_series(rows: list[dict[str, float | int | str]], ykey: str, filename: str, ylabel: str, xkey: str = "time") -> None:
    plt.figure(figsize=(7.0, 4.2))
    for case_key in CASES:
        data = [r for r in rows if r["case"] == case_key]
        if not data:
            continue
        plt.plot([float(r[xkey]) for r in data], [float(r[ykey]) for r in data], marker="o", label=case_key)
    plt.xlabel("time [s]" if xkey == "time" else xkey)
    plt.ylabel(ylabel)
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIGDIR / f"{filename}.{ext}", dpi=180)
    plt.close()


def plot_pq(rows: list[dict[str, float | int | str]]) -> None:
    plt.figure(figsize=(5.2, 4.6))
    for case_key in CASES:
        data = [r for r in rows if r["case"] == case_key]
        if not data:
            continue
        plt.plot([float(r["p_eff_proxy"]) for r in data], [float(r["q_proxy"]) for r in data], marker="o", label=case_key)
    plt.xlabel("p' proxy [Pa]")
    plt.ylabel("q proxy [Pa]")
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIGDIR / f"t4r_pq_proxy.{ext}", dpi=180)
    plt.close()


def plot_measurement_sensitivity(region_rows: list[dict[str, float | int | str]]) -> None:
    final_parts: dict[str, int] = {}
    for case_key in CASES:
        parts = [int(r["part"]) for r in region_rows if r["case"] == case_key]
        if parts:
            final_parts[case_key] = max(parts)
    plt.figure(figsize=(7.0, 4.2))
    for case_key, pfinal in final_parts.items():
        data = [r for r in region_rows if r["case"] == case_key and int(r["part"]) == pfinal]
        labels = [str(r["region"]) for r in data]
        vals = [float(r["q_proxy"]) for r in data]
        plt.plot(labels, vals, marker="o", label=case_key)
    plt.ylabel("final q proxy [Pa]")
    plt.xticks(rotation=20, ha="right")
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("svg", "png"):
        plt.savefig(FIGDIR / f"t4r_measurement_region_sensitivity.{ext}", dpi=180)
    plt.close()


def main() -> None:
    all_frames: list[dict[str, float | int | str]] = []
    all_regions: list[dict[str, float | int | str]] = []
    all_confinement: list[dict[str, float | int | str]] = []
    summaries: list[dict[str, float | int | str]] = []
    group_counts: list[dict[str, float | int | str]] = []

    for case_key, case in CASES.items():
        frames, regions = frame_metrics(case_key, case)
        all_frames.extend(frames)
        all_regions.extend(regions)
        all_confinement.extend(parse_confinement_diag(case_key, case))
        summary = parse_summary(case_key, case)
        if frames:
            final = frames[-1]
            summary.update({f"final_{k}": v for k, v in final.items() if k not in {"case", "part", "time"}})
            first = read_rows(part_files(case)[0])
            counts = Counter(classify(r) for r in first)
            group_counts.append({"case": case_key, **counts})
        summaries.append(summary)

    write_csv(ROOT / "t4r_case_summary.csv", summaries)
    write_csv(ROOT / "t4r_group_counts.csv", group_counts)
    write_csv(ROOT / "t4r_platen_motion_metrics.csv", all_frames)
    write_csv(ROOT / "t4r_reaction_metrics.csv", all_frames)
    write_csv(ROOT / "t4r_specimen_stress_path_proxy.csv", all_frames)
    write_csv(ROOT / "t4r_measurement_region_metrics.csv", all_regions)
    write_csv(ROOT / "t4r_confinement_diagnostics.csv", all_confinement)

    if all_frames:
        plot_series(all_frames, "top_platen_displacement", "t4r_top_platen_displacement", "top platen displacement [m]")
        plot_series(all_frames, "specimen_axial_strain_proxy", "t4r_axial_strain_proxy", "specimen axial strain proxy")
        plot_series(all_frames, "reaction_force_proxy", "t4r_reaction_force_proxy", "reaction force proxy [N]")
        plot_series(all_frames, "sigma_a_proxy", "t4r_axial_stress_proxy", "axial stress proxy [Pa]")
        plot_pq(all_frames)
        plot_series(all_frames, "q_proxy", "t4r_q_vs_time", "q proxy [Pa]")
        plot_series(all_frames, "porepress_mean", "t4r_pore_pressure_time", "specimen PorePress mean [Pa]")
        plot_series(all_frames, "porepress_mean", "t4r_pore_pressure_strain", "specimen PorePress mean [Pa]", xkey="specimen_axial_strain_proxy")
        plot_series(all_frames, "kplastic_max", "t4r_kplastic_max", "Kplastic max")
        plot_series(all_frames, "velocity_max", "t4r_velocity_max", "velocity max [m/s]")
        plot_series(all_frames, "porepressrate_maxabs", "t4r_porepressrate_maxabs", "PorePressRate maxAbs [Pa/s]")
    if all_regions:
        plot_measurement_sensitivity(all_regions)
    if all_confinement:
        plot_series(all_confinement, "lateral_inward_radial_accel_mean", "t4r_lateral_confinement_accel", "lateral inward accel mean [m/s2]")


if __name__ == "__main__":
    main()

