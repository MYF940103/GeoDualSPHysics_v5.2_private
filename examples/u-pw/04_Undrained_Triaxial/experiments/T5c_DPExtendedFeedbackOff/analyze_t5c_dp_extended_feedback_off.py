#!/usr/bin/env python3
"""Postprocess T5c extended DP feedback-off platen response cases."""

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
    "dp_high_strength": "CaseT5c_DPHighStrength_ExtendedFeedbackOff",
    "dp_mild_yield": "CaseT5c_DPMildYield_ExtendedFeedbackOff",
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
        kplastic_values = [float(r.get("Kplastic", 0.0)) for r in spec]
        kplastic_nonzero = sum(1 for v in kplastic_values if abs(v) > 1e-12)
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
            "kplastic_max": max(kplastic_values or [0.0]),
            "kplastic_mean": safe_mean(kplastic_values),
            "kplastic_nonzero_count": kplastic_nonzero,
            "kplastic_fraction": kplastic_nonzero / len(spec) if spec else 0.0,
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
                    "kplastic_mean": safe_mean(float(r.get("Kplastic", 0.0)) for r in rrows),
                    "kplastic_nonzero_count": sum(1 for r in rrows if abs(float(r.get("Kplastic", 0.0))) > 1e-12),
                    "kplastic_fraction": (
                        sum(1 for r in rrows if abs(float(r.get("Kplastic", 0.0))) > 1e-12) / len(rrows)
                        if rrows
                        else 0.0
                    ),
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


def parse_platen_reaction_diag(case_key: str, case: str) -> list[dict[str, float | int | str]]:
    run = ROOT / f"{case}_out" / "Run.out"
    if not run.exists():
        return []
    rx = re.compile(
        r"PlatenReaction diagnostics: step=(\d+), TimeStep=([0-9Ee+\-.]+), mode=(\d+), "
        r"top_mkbound=(-?\d+), bottom_mkbound=(-?\d+), top_count=(\d+), bottom_count=(\d+), "
        r"top_pairs=(\d+), bottom_pairs=(\d+), "
        r"top_force=\(([0-9Ee+\-.]+),([0-9Ee+\-.]+),([0-9Ee+\-.]+)\) N, "
        r"bottom_force=\(([0-9Ee+\-.]+),([0-9Ee+\-.]+),([0-9Ee+\-.]+)\) N, "
        r"top_axial_stress=([0-9Ee+\-.]+) Pa, bottom_axial_stress=([0-9Ee+\-.]+) Pa, "
        r"force_balance_error=([0-9Ee+\-.]+)"
    )
    rows: list[dict[str, float | int | str]] = []
    for line in run.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if not m:
            continue
        rows.append(
            {
                "case": case_key,
                "step": int(m.group(1)),
                "time": float(m.group(2)),
                "mode": int(m.group(3)),
                "top_mkbound": int(m.group(4)),
                "bottom_mkbound": int(m.group(5)),
                "top_count": int(m.group(6)),
                "bottom_count": int(m.group(7)),
                "top_pairs": int(m.group(8)),
                "bottom_pairs": int(m.group(9)),
                "top_force_x": float(m.group(10)),
                "top_force_y": float(m.group(11)),
                "top_force_z": float(m.group(12)),
                "bottom_force_x": float(m.group(13)),
                "bottom_force_y": float(m.group(14)),
                "bottom_force_z": float(m.group(15)),
                "top_axial_stress": float(m.group(16)),
                "bottom_axial_stress": float(m.group(17)),
                "force_balance_error": float(m.group(18).rstrip(".")),
                "reaction_type": "pairwise_fluid_bound_accumulator",
                "true_reaction_available": 1,
            }
        )
    return rows


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
        plt.savefig(FIGDIR / f"t5c_pq_proxy.{ext}", dpi=180)
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
        plt.savefig(FIGDIR / f"t5c_measurement_region_sensitivity.{ext}", dpi=180)
    plt.close()


def nearest_reaction(case_key: str, time: float, reactions: list[dict[str, float | int | str]]) -> dict[str, float | int | str] | None:
    data = [r for r in reactions if r["case"] == case_key]
    if not data:
        return None
    return min(data, key=lambda r: abs(float(r["time"]) - time))


def reaction_proxy_comparison(
    frames: list[dict[str, float | int | str]],
    reactions: list[dict[str, float | int | str]],
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for case_key in CASES:
        frows = [r for r in frames if r["case"] == case_key]
        if not frows:
            continue
        final = frows[-1]
        react = nearest_reaction(case_key, float(final["time"]), reactions)
        row: dict[str, float | int | str] = {
            "case": case_key,
            "time": final["time"],
            "Fz_proxy": final["reaction_force_proxy"],
            "axial_stress_proxy": final["sigma_a_proxy"],
            "p_eff_proxy": final["p_eff_proxy"],
            "q_proxy": final["q_proxy"],
        }
        if react:
            top_fz = float(react["top_force_z"])
            bot_fz = float(react["bottom_force_z"])
            top_stress = float(react["top_axial_stress"])
            bot_stress = float(react["bottom_axial_stress"])
            avg_stress = 0.5 * (top_stress + bot_stress)
            avg_force = 0.5 * (top_fz - bot_fz)
            row.update(
                {
                    "reaction_time": react["time"],
                    "top_reaction_fz": top_fz,
                    "bottom_reaction_fz": bot_fz,
                    "top_axial_stress": top_stress,
                    "bottom_axial_stress": bot_stress,
                    "reaction_axial_stress_avg": avg_stress,
                    "reaction_force_avg_compression": avg_force,
                    "force_balance_error": react["force_balance_error"],
                    "top_pairs": react["top_pairs"],
                    "bottom_pairs": react["bottom_pairs"],
                    "true_reaction_available": 1,
                    "reaction_type": react["reaction_type"],
                    "reaction_minus_proxy_force": avg_force - float(final["reaction_force_proxy"]),
                    "reaction_over_proxy_force": avg_force / float(final["reaction_force_proxy"]) if float(final["reaction_force_proxy"]) else float("nan"),
                }
            )
        else:
            row.update({"true_reaction_available": 0, "reaction_type": "missing"})
        rows.append(row)
    return rows


def reaction_strain_series(
    frames: list[dict[str, float | int | str]],
    reactions: list[dict[str, float | int | str]],
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for frame in frames:
        case_key = str(frame["case"])
        react = nearest_reaction(case_key, float(frame["time"]), reactions)
        if not react:
            continue
        top_fz = float(react["top_force_z"])
        bot_fz = float(react["bottom_force_z"])
        top_stress = float(react["top_axial_stress"])
        bot_stress = float(react["bottom_axial_stress"])
        avg_force = 0.5 * (top_fz - bot_fz)
        avg_stress = 0.5 * (top_stress + bot_stress)
        fz_proxy = float(frame["reaction_force_proxy"])
        rows.append(
            {
                "case": case_key,
                "time": frame["time"],
                "part": frame["part"],
                "specimen_axial_strain_proxy": frame["specimen_axial_strain_proxy"],
                "top_reaction_fz": top_fz,
                "bottom_reaction_fz": bot_fz,
                "reaction_force_avg_compression": avg_force,
                "top_axial_stress": top_stress,
                "bottom_axial_stress": bot_stress,
                "reaction_axial_stress_avg": avg_stress,
                "Fz_proxy": fz_proxy,
                "axial_stress_proxy": frame["sigma_a_proxy"],
                "reaction_over_proxy_force": avg_force / fz_proxy if fz_proxy else float("nan"),
                "force_balance_error": react["force_balance_error"],
                "p_eff_proxy": frame["p_eff_proxy"],
                "q_proxy": frame["q_proxy"],
                "kplastic_max": frame["kplastic_max"],
                "kplastic_nonzero_count": frame["kplastic_nonzero_count"],
            }
        )
    return rows


def stability_series(frames: list[dict[str, float | int | str]]) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for case_key in CASES:
        data = sorted([r for r in frames if r["case"] == case_key], key=lambda r: float(r["time"]))
        last_time: float | None = None
        last_kp: float | None = None
        for row in data:
            time = float(row["time"])
            kp = float(row["kplastic_max"])
            growth = 0.0
            if last_time is not None and last_kp is not None and time > last_time:
                growth = (kp - last_kp) / (time - last_time)
            rows.append(
                {
                    "case": case_key,
                    "part": row["part"],
                    "time": time,
                    "velocity_max": row["velocity_max"],
                    "specimen_velocity_max": row["specimen_velocity_max"],
                    "porepressrate_maxabs": row["porepressrate_maxabs"],
                    "divvel_maxabs": row["divvel_maxabs"],
                    "porepress_mean": row["porepress_mean"],
                    "porepress_std": row["porepress_std"],
                    "kplastic_max": row["kplastic_max"],
                    "kplastic_mean": row["kplastic_mean"],
                    "kplastic_nonzero_count": row["kplastic_nonzero_count"],
                    "kplastic_fraction": row["kplastic_fraction"],
                    "kplastic_growth_rate": growth,
                    "reaction_force_proxy": row["reaction_force_proxy"],
                    "p_eff_proxy": row["p_eff_proxy"],
                    "q_proxy": row["q_proxy"],
                }
            )
            last_time = time
            last_kp = kp
    return rows


def main() -> None:
    all_frames: list[dict[str, float | int | str]] = []
    all_regions: list[dict[str, float | int | str]] = []
    all_confinement: list[dict[str, float | int | str]] = []
    all_reactions: list[dict[str, float | int | str]] = []
    summaries: list[dict[str, float | int | str]] = []
    group_counts: list[dict[str, float | int | str]] = []

    for case_key, case in CASES.items():
        frames, regions = frame_metrics(case_key, case)
        all_frames.extend(frames)
        all_regions.extend(regions)
        all_confinement.extend(parse_confinement_diag(case_key, case))
        reactions = parse_platen_reaction_diag(case_key, case)
        all_reactions.extend(reactions)
        summary = parse_summary(case_key, case)
        if frames:
            final = frames[-1]
            summary.update({f"final_{k}": v for k, v in final.items() if k not in {"case", "part", "time"}})
            first = read_rows(part_files(case)[0])
            counts = Counter(classify(r) for r in first)
            group_counts.append({"case": case_key, **counts})
        if reactions:
            final_reaction = reactions[-1]
            summary.update({f"final_{k}": v for k, v in final_reaction.items() if k not in {"case", "step", "time"}})
            summary["true_reaction_available"] = 1
            summary["reaction_type"] = final_reaction["reaction_type"]
        summaries.append(summary)

    comparison = reaction_proxy_comparison(all_frames, all_reactions)
    reaction_strain = reaction_strain_series(all_frames, all_reactions)
    stability = stability_series(all_frames)
    write_csv(ROOT / "t5c_case_summary.csv", summaries)
    write_csv(ROOT / "t5c_platen_motion_metrics.csv", all_frames)
    write_csv(ROOT / "t5c_dp_plasticity_metrics.csv", all_frames)
    write_csv(ROOT / "t5c_stress_path_metrics.csv", all_frames)
    write_csv(ROOT / "t5c_axial_stress_strain_metrics.csv", reaction_strain)
    write_csv(ROOT / "t5c_pore_pressure_strain_metrics.csv", all_frames)
    write_csv(ROOT / "t5c_pore_pressure_metrics.csv", all_frames)
    write_csv(ROOT / "t5c_stability_metrics.csv", stability)
    write_csv(ROOT / "t5c_measurement_region_metrics.csv", all_regions)
    write_csv(ROOT / "t5c_confinement_diagnostics.csv", all_confinement)
    write_csv(ROOT / "t5c_true_reaction_metrics.csv", all_reactions)
    write_csv(ROOT / "t5c_platen_reaction_metrics.csv", all_reactions)
    write_csv(ROOT / "t5c_reaction_vs_proxy_comparison.csv", comparison)
    write_csv(ROOT / "t5c_axial_stress_metrics.csv", comparison)
    write_csv(ROOT / "t5c_group_counts.csv", group_counts)

    if all_frames:
        plot_series(all_frames, "top_platen_displacement", "t5c_top_platen_displacement", "top platen displacement [m]")
        plot_series(all_frames, "specimen_axial_strain_proxy", "t5c_axial_strain_proxy", "specimen axial strain proxy")
        plot_series(all_frames, "reaction_force_proxy", "t5c_reaction_force_proxy", "reaction force proxy [N]")
        plot_series(all_frames, "sigma_a_proxy", "t5c_axial_stress_proxy", "axial stress proxy [Pa]")
        plot_pq(all_frames)
        plot_series(all_frames, "q_proxy", "t5c_q_vs_time", "q proxy [Pa]")
        plot_series(all_frames, "q_proxy", "t5c_q_vs_axial_strain", "q proxy [Pa]", xkey="specimen_axial_strain_proxy")
        plot_series(all_frames, "p_eff_proxy", "t5c_p_eff_vs_axial_strain", "p' proxy [Pa]", xkey="specimen_axial_strain_proxy")
        plot_series(all_frames, "porepress_mean", "t5c_pore_pressure_time", "specimen PorePress mean [Pa]")
        plot_series(all_frames, "porepress_mean", "t5c_pore_pressure_strain", "specimen PorePress mean [Pa]", xkey="specimen_axial_strain_proxy")
        plot_series(all_frames, "divvel_maxabs", "t5c_divvel_maxabs", "DivVel maxAbs [1/s]")
        plot_series(all_frames, "kplastic_max", "t5c_kplastic_max", "Kplastic max")
        plot_series(all_frames, "kplastic_mean", "t5c_kplastic_mean", "Kplastic mean")
        plot_series(all_frames, "kplastic_nonzero_count", "t5c_kplastic_nonzero_count", "Kplastic nonzero particle count")
        plot_series(all_frames, "kplastic_fraction", "t5c_kplastic_fraction", "plastic fraction")
        plot_series(all_frames, "velocity_max", "t5c_velocity_max", "velocity max [m/s]")
        plot_series(all_frames, "porepressrate_maxabs", "t5c_porepressrate_maxabs", "PorePressRate maxAbs [Pa/s]")
    if all_regions:
        plot_measurement_sensitivity(all_regions)
    if all_confinement:
        plot_series(all_confinement, "lateral_inward_radial_accel_mean", "t5c_lateral_confinement_accel", "lateral inward accel mean [m/s2]")
    if all_reactions:
        plot_series(all_reactions, "top_force_z", "t5c_top_reaction_fz", "top reaction Fz [N]")
        plot_series(all_reactions, "bottom_force_z", "t5c_bottom_reaction_fz", "bottom reaction Fz [N]")
        plot_series(all_reactions, "top_axial_stress", "t5c_top_reaction_axial_stress", "top reaction axial stress [Pa]")
        plot_series(all_reactions, "bottom_axial_stress", "t5c_bottom_reaction_axial_stress", "bottom reaction axial stress [Pa]")
        plot_series(all_reactions, "force_balance_error", "t5c_force_balance_error", "force balance error")
    if reaction_strain:
        plot_series(reaction_strain, "reaction_force_avg_compression", "t5c_pairwise_reaction_vs_strain", "pairwise reaction avg [N]", xkey="specimen_axial_strain_proxy")
        plot_series(reaction_strain, "reaction_axial_stress_avg", "t5c_reaction_axial_stress_vs_strain", "reaction axial stress avg [Pa]", xkey="specimen_axial_strain_proxy")
        plot_series(reaction_strain, "reaction_over_proxy_force", "t5c_reaction_proxy_ratio", "pairwise reaction / Fz_proxy")
    if stability:
        plot_series(stability, "kplastic_growth_rate", "t5c_kplastic_growth_rate", "Kplastic max growth rate")


if __name__ == "__main__":
    main()
