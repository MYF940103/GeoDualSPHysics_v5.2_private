#!/usr/bin/env python3
"""Postprocess T4o cap-support-preserving staged triaxial confinement cases."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

CASES = {
    "stageA_all_surface": "CaseT4o_StageA_AllSurface_FeedbackOff",
    "stageB_lateral_cap": "CaseT4o_StageB_Restart_LateralCap_FeedbackOff",
    "stageC_delayed_feedback": "CaseT4o_StageC_Restart_LateralCap_FeedbackDelayed",
}

RADIUS = 0.03
HEIGHT = 0.10
CAP_EXCL = 0.015
EDGE_EXCL = 0.015
CENTER_R = 0.012
CENTER_Z_MIN = 0.035
CENTER_Z_MAX = 0.065

T4N2_STAGE_A_FINAL_Q = 15.65
T4N2_LATERAL_ONLY_FINAL_Q = 37.89
T4N2_STAGE_C_PPR_MAXABS = 1.84e12
T4N2_STAGE_C_VEL_MAX = 28.23


def read_part(path: Path) -> list[dict[str, float]]:
    with path.open(newline="") as f:
        reader = csv.reader(f, delimiter=";")
        headers = [h.strip() for h in next(reader) if h.strip()]
        rows: list[dict[str, float]] = []
        for raw in reader:
            if len(raw) < len(headers):
                continue
            row: dict[str, float] = {}
            for key, val in zip(headers, raw):
                if not key:
                    continue
                try:
                    row[key] = int(float(val)) if key == "Idp" else float(val)
                except ValueError:
                    row[key] = float("nan")
            rows.append(row)
        return rows


def part_files(case: str) -> list[Path]:
    return sorted((ROOT / f"{case}_out" / "data").glob("PartCsv_*.csv"), key=part_index)


def part_index(path: Path) -> int:
    return int(path.stem.split("_")[-1])


def classify(row: dict[str, float]) -> str:
    x = row["Pos.x [m]"]
    y = row["Pos.y [m]"]
    z = row["Pos.z [m]"]
    r = math.hypot(x, y)
    cap_zone = z <= CAP_EXCL or z >= HEIGHT - CAP_EXCL
    radial_edge = r >= RADIUS - EDGE_EXCL
    if cap_zone and radial_edge:
        return "edge"
    if z <= CAP_EXCL:
        return "bottom_cap"
    if z >= HEIGHT - CAP_EXCL:
        return "top_cap"
    if r >= RADIUS - EDGE_EXCL:
        return "lateral"
    return "interior"


def is_center(row: dict[str, float]) -> bool:
    r = math.hypot(row["Pos.x [m]"], row["Pos.y [m]"])
    z = row["Pos.z [m]"]
    return r <= CENTER_R and CENTER_Z_MIN <= z <= CENTER_Z_MAX


def safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def stress_metrics(row: dict[str, float]) -> tuple[float, float]:
    sxx = row.get("Sigma_kk.x", 0.0)
    syy = row.get("Sigma_kk.y", 0.0)
    szz = row.get("Sigma_kk.z", 0.0)
    sxy = row.get("Sigma_ij.x", 0.0)
    sxz = row.get("Sigma_ij.y", 0.0)
    syz = row.get("Sigma_ij.z", 0.0)
    p_eff = -(sxx + syy + szz) / 3.0
    q = math.sqrt(
        max(
            0.0,
            0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
            + 3.0 * (sxy * sxy + sxz * sxz + syz * syz),
        )
    )
    return p_eff, q


def frame_metrics(case_key: str, case_name: str) -> list[dict[str, float | str]]:
    times = parse_part_times(case_name)
    records: list[dict[str, float | str]] = []
    for pf in part_files(case_name):
        rows = read_part(pf)
        if not rows:
            continue
        pqs = [stress_metrics(r) for r in rows]
        p_eff = [p for p, _ in pqs]
        qvals = [q for _, q in pqs]
        vel = [
            math.sqrt(
                r.get("Vel.x [m/s]", 0.0) ** 2
                + r.get("Vel.y [m/s]", 0.0) ** 2
                + r.get("Vel.z [m/s]", 0.0) ** 2
            )
            for r in rows
        ]
        div = [r.get("DivVel", 0.0) for r in rows]
        ppr = [r.get("PorePressRate", 0.0) for r in rows]
        pw = [r.get("PorePress", 0.0) for r in rows]
        epw = [r.get("ExcessPorePress", r.get("PorePress", 0.0)) for r in rows]
        center = [r for r in rows if is_center(r)]
        center_pw = [r.get("PorePress", 0.0) for r in center]
        center_ppr = [r.get("PorePressRate", 0.0) for r in center]
        idx = part_index(pf)
        records.append(
            {
                "case": case_key,
                "part": idx,
                "time": times.get(idx, float("nan")),
                "n": len(rows),
                "p_eff_mean": safe_mean(p_eff),
                "q_mean": safe_mean(qvals),
                "sigma_xx_mean": safe_mean([r.get("Sigma_kk.x", 0.0) for r in rows]),
                "sigma_yy_mean": safe_mean([r.get("Sigma_kk.y", 0.0) for r in rows]),
                "sigma_zz_mean": safe_mean([r.get("Sigma_kk.z", 0.0) for r in rows]),
                "porepress_mean": safe_mean(pw),
                "porepress_min": min(pw),
                "porepress_max": max(pw),
                "negative_pressure_count": sum(1 for v in pw if v < 0.0),
                "excess_porepress_mean": safe_mean(epw),
                "porepressrate_mean": safe_mean(ppr),
                "porepressrate_maxabs": max(abs(v) for v in ppr),
                "divvel_mean": safe_mean(div),
                "divvel_maxabs": max(abs(v) for v in div),
                "velocity_max": max(vel),
                "kplastic_max": max(r.get("Kplastic", 0.0) for r in rows),
                "center_particle_count": len(center),
                "center_porepress_mean": safe_mean(center_pw),
                "center_porepressrate_maxabs": max([abs(v) for v in center_ppr] or [0.0]),
            }
        )
    return records


def region_metrics(case_key: str, case_name: str, part: Path) -> list[dict[str, float | str]]:
    rows = read_part(part)
    by_class: dict[str, list[dict[str, float]]] = {}
    for row in rows:
        by_class.setdefault(classify(row), []).append(row)
    out: list[dict[str, float | str]] = []
    for cls in ["interior", "lateral", "top_cap", "bottom_cap", "edge"]:
        group = by_class.get(cls, [])
        if not group:
            continue
        pqs = [stress_metrics(r) for r in group]
        out.append(
            {
                "case": case_key,
                "part": part_index(part),
                "class": cls,
                "count": len(group),
                "p_eff_mean": safe_mean([p for p, _ in pqs]),
                "q_mean": safe_mean([q for _, q in pqs]),
                "porepress_mean": safe_mean([r.get("PorePress", 0.0) for r in group]),
                "porepress_min": min(r.get("PorePress", 0.0) for r in group),
                "porepressrate_maxabs": max(abs(r.get("PorePressRate", 0.0)) for r in group),
                "velocity_max": max(
                    math.sqrt(
                        r.get("Vel.x [m/s]", 0.0) ** 2
                        + r.get("Vel.y [m/s]", 0.0) ** 2
                        + r.get("Vel.z [m/s]", 0.0) ** 2
                    )
                    for r in group
                ),
            }
        )
    return out


def parse_part_times(case_name: str) -> dict[int, float]:
    out = ROOT / f"{case_name}_out" / "Run.out"
    times: dict[int, float] = {}
    if not out.exists():
        return times
    for line in out.read_text(errors="ignore").splitlines():
        m = re.search(r"Part_(\d+)\s+([0-9]+\.[0-9Ee+\-]+)", line)
        if m:
            times[int(m.group(1))] = float(m.group(2))
        dm = re.search(r"TimeStep=([0-9Ee+\-.]+)", line)
        pm = re.search(r"step=0", line)
        if dm and pm:
            # Restart runs store the first part before the first timed Part_N line.
            first = min((part_index(p) for p in part_files(case_name)), default=None)
            if first is not None:
                times.setdefault(first, float(dm.group(1)))
    if 0 in [part_index(p) for p in part_files(case_name)]:
        times.setdefault(0, 0.0)
    return times


def parse_run_summary(case_name: str) -> dict[str, float | str]:
    path = ROOT / f"{case_name}_out" / "Run.out"
    txt = path.read_text(errors="ignore") if path.exists() else ""
    code = 0 if "Finished execution (code=0)" in txt else (1 if "Finished execution" in txt else -1)
    excluded = 0
    dtmin = 0
    m = re.search(r"Excluded particles:\s+(\d+)", txt)
    if m:
        excluded = int(m.group(1))
    m = re.search(r"DTs adjusted to DtMin:\s+(\d+)", txt)
    if m:
        dtmin = int(m.group(1))
    return {
        "code": code,
        "excluded": excluded,
        "dtmin_adjustments": dtmin,
        "restart_soil_restored": int("Restart soil state restored" in txt),
        "restart_porepress_restored": int("Restart pore-pressure state restored" in txt),
    }


def parse_flexible_diag(case_name: str) -> list[dict[str, float | str]]:
    path = ROOT / f"{case_name}_out" / "Run.out"
    if not path.exists():
        return []
    rows: list[dict[str, float | str]] = []
    rx = re.compile(
        r"FlexibleConfiningStress CPU diagnostics: step=(\d+), TimeStep=([0-9Ee+\-.]+), "
        r"p0_eff=([0-9Ee+\-.]+) Pa, targets=(\d+), legacy_targets=(\d+), "
        r"net_force=\(([0-9Ee+\-.]+),([0-9Ee+\-.]+),([0-9Ee+\-.]+)\) N, "
        r"total_abs_force=([0-9Ee+\-.]+) N, max_accel=([0-9Ee+\-.]+) m/s2, "
        r"com_accel=([0-9Ee+\-.]+) m/s2, symmetry_residual=([0-9Ee+\-.]+), "
        r"lateral_selector_active=(\d+)"
    )
    for line in path.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if not m:
            continue
        rows.append(
            {
                "case": case_name,
                "step": int(m.group(1)),
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
    return rows


def parse_cap_diag(case_name: str) -> list[dict[str, float | str]]:
    path = ROOT / f"{case_name}_out" / "Run.out"
    if not path.exists():
        return []
    rows: list[dict[str, float | str]] = []
    rx = re.compile(
        r"CapConfiningStress CPU diagnostics: step=(\d+), TimeStep=([0-9Ee+\-.]+), "
        r"p0_eff=([0-9Ee+\-.]+) Pa, top_targets=(\d+), bottom_targets=(\d+), "
        r"edge_skipped=(\d+), top_accel_mean=([0-9Ee+\-.]+), top_accel_max=([0-9Ee+\-.]+), "
        r"bottom_accel_mean=([0-9Ee+\-.]+), bottom_accel_max=([0-9Ee+\-.]+), "
        r"net_force=\(([0-9Ee+\-.]+),([0-9Ee+\-.]+),([0-9Ee+\-.]+)\) N, "
        r"total_abs_force=([0-9Ee+\-.]+) N, com_accel=([0-9Ee+\-.]+) m/s2, "
        r"symmetry_residual=([0-9Ee+\-.]+)"
    )
    for line in path.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if not m:
            continue
        rows.append(
            {
                "case": case_name,
                "step": int(m.group(1)),
                "time": float(m.group(2)),
                "p0_eff": float(m.group(3)),
                "top_targets": int(m.group(4)),
                "bottom_targets": int(m.group(5)),
                "edge_skipped": int(m.group(6)),
                "top_accel_mean": float(m.group(7)),
                "top_accel_max": float(m.group(8)),
                "bottom_accel_mean": float(m.group(9)),
                "bottom_accel_max": float(m.group(10)),
                "net_force_x": float(m.group(11)),
                "net_force_y": float(m.group(12)),
                "net_force_z": float(m.group(13)),
                "total_abs_force": float(m.group(14)),
                "com_accel": float(m.group(15)),
                "symmetry_residual": float(m.group(16)),
            }
        )
    return rows


def parse_feedback_diag(case_name: str) -> list[dict[str, float | str]]:
    path = ROOT / f"{case_name}_out" / "Run.out"
    if not path.exists():
        return []
    rows: list[dict[str, float | str]] = []
    rx = re.compile(
        r"PorePressureFeedback diagnostics: step=(\d+), TimeStep=([0-9Ee+\-.]+), "
        r"factor=([0-9Ee+\-.]+), applied=(\d+), class_skipped=(\d+), raw_max=([0-9Ee+\-.]+), "
        r"raw_mean=([0-9Ee+\-.]+), used_max=([0-9Ee+\-.]+), used_mean=([0-9Ee+\-.]+), "
        r"pre_accel_max=([0-9Ee+\-.]+), used_to_reference_ratio_max=([0-9Ee+\-.]+), "
        r"confining_ref=([0-9Ee+\-.]+), limited=(\d+), relaxed=(\d+), cap_min=([0-9Ee+\-.]+)"
    )
    for line in path.read_text(errors="ignore").splitlines():
        m = rx.search(line)
        if not m:
            continue
        rows.append(
            {
                "case": case_name,
                "step": int(m.group(1)),
                "time": float(m.group(2)),
                "factor": float(m.group(3)),
                "applied": int(m.group(4)),
                "class_skipped": int(m.group(5)),
                "raw_max": float(m.group(6)),
                "raw_mean": float(m.group(7)),
                "used_max": float(m.group(8)),
                "used_mean": float(m.group(9)),
                "pre_accel_max": float(m.group(10)),
                "used_to_reference_ratio_max": float(m.group(11)),
                "confining_ref": float(m.group(12)),
                "limited": int(m.group(13)),
                "relaxed": int(m.group(14)),
                "cap_min": float(m.group(15)),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
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


def restart_continuity() -> list[dict[str, object]]:
    a = ROOT / f"{CASES['stageA_all_surface']}_out" / "data" / "PartCsv_0023.csv"
    b = ROOT / f"{CASES['stageB_lateral_cap']}_out" / "data" / "PartCsv_0023.csv"
    if not a.exists() or not b.exists():
        return []
    ar = {int(r["Idp"]): r for r in read_part(a)}
    br = {int(r["Idp"]): r for r in read_part(b)}
    cols = [
        "Pos.x [m]",
        "Pos.y [m]",
        "Pos.z [m]",
        "Vel.x [m/s]",
        "Vel.y [m/s]",
        "Vel.z [m/s]",
        "Rhop [kg/m^3]",
        "Sigma_kk.x",
        "Sigma_kk.y",
        "Sigma_kk.z",
        "Sigma_ij.x",
        "Sigma_ij.y",
        "Sigma_ij.z",
        "Kplastic",
        "PorePress",
    ]
    rows = []
    for col in cols:
        diffs = [abs(ar[i].get(col, 0.0) - br[i].get(col, 0.0)) for i in ar.keys() & br.keys()]
        rows.append(
            {
                "quantity": col,
                "max_abs_diff": max(diffs) if diffs else float("nan"),
                "mean_abs_diff": safe_mean(diffs),
                "particle_count": len(diffs),
            }
        )
    return rows


def make_summary(all_frames: dict[str, list[dict[str, float | str]]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for key, case in CASES.items():
        frames = all_frames.get(key, [])
        if not frames:
            continue
        final = frames[-1]
        run = parse_run_summary(case)
        rows.append(
            {
                "case": key,
                "case_name": case,
                **run,
                "final_part": final["part"],
                "final_time": final["time"],
                "final_p_eff_mean": final["p_eff_mean"],
                "final_q_mean": final["q_mean"],
                "final_porepress_mean": final["porepress_mean"],
                "final_porepress_min": final["porepress_min"],
                "final_negative_pressure_count": final["negative_pressure_count"],
                "max_porepressrate_maxabs": max(float(f["porepressrate_maxabs"]) for f in frames),
                "max_velocity": max(float(f["velocity_max"]) for f in frames),
                "max_divvel_maxabs": max(float(f["divvel_maxabs"]) for f in frames),
                "center_final_porepress_mean": final["center_porepress_mean"],
                "center_max_porepressrate_maxabs": max(float(f["center_porepressrate_maxabs"]) for f in frames),
                "kplastic_max": max(float(f["kplastic_max"]) for f in frames),
                "reversal_indicator_any_negative": int(any(float(f["negative_pressure_count"]) > 0 for f in frames)),
            }
        )
    return rows


def make_transition_metrics(summary: list[dict[str, object]]) -> list[dict[str, object]]:
    by = {str(r["case"]): r for r in summary}
    a = by.get("stageA_all_surface", {})
    b = by.get("stageB_lateral_cap", {})
    c = by.get("stageC_delayed_feedback", {})
    rows: list[dict[str, object]] = []
    if a and b:
        q_a = float(a["final_q_mean"])
        q_b = float(b["final_q_mean"])
        p_a = float(a["final_p_eff_mean"])
        p_b = float(b["final_p_eff_mean"])
        rows.append(
            {
                "metric": "stageB_vs_stageA",
                "stageA_final_q": q_a,
                "stageB_final_q": q_b,
                "q_change": q_b - q_a,
                "stageA_final_p_eff": p_a,
                "stageB_final_p_eff": p_b,
                "p_eff_change": p_b - p_a,
            }
        )
        rows.append(
            {
                "metric": "stageB_vs_T4n2_lateral_only",
                "t4n2_lateral_only_final_q": T4N2_LATERAL_ONLY_FINAL_Q,
                "stageB_final_q": q_b,
                "q_reduction": T4N2_LATERAL_ONLY_FINAL_Q - q_b,
                "q_reduction_fraction": (T4N2_LATERAL_ONLY_FINAL_Q - q_b) / T4N2_LATERAL_ONLY_FINAL_Q,
            }
        )
    if c:
        ppr_c = float(c["max_porepressrate_maxabs"])
        vel_c = float(c["max_velocity"])
        rows.append(
            {
                "metric": "stageC_vs_T4n2_feedback",
                "t4n2_stageC_porepressrate_maxabs": T4N2_STAGE_C_PPR_MAXABS,
                "stageC_porepressrate_maxabs": ppr_c,
                "porepressrate_reduction": T4N2_STAGE_C_PPR_MAXABS - ppr_c,
                "t4n2_stageC_velocity_max": T4N2_STAGE_C_VEL_MAX,
                "stageC_velocity_max": vel_c,
            }
        )
    return rows


def make_plots(frames: dict[str, list[dict[str, float | str]]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        print(f"matplotlib unavailable: {exc}")
        return

    def plot_metric(metric: str, ylabel: str, name: str, logy: bool = False) -> None:
        plt.figure(figsize=(7.2, 4.2))
        for key, recs in frames.items():
            if not recs:
                continue
            x = [float(r["time"]) if not math.isnan(float(r["time"])) else float(r["part"]) for r in recs]
            y = [float(r[metric]) for r in recs]
            plt.plot(x, y, marker="o", markersize=2.5, linewidth=1.4, label=key)
        plt.xlabel("time [s]")
        plt.ylabel(ylabel)
        if logy:
            plt.yscale("log")
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=8)
        plt.tight_layout()
        for ext in ("png", "svg"):
            plt.savefig(FIGDIR / f"{name}.{ext}", dpi=180)
        plt.close()

    plot_metric("p_eff_mean", "p' proxy [Pa]", "t4o_p_eff_vs_time")
    plot_metric("q_mean", "q proxy [Pa]", "t4o_q_vs_time")
    plot_metric("porepress_mean", "mean pore pressure [Pa]", "t4o_pore_pressure_vs_time")
    plot_metric("porepressrate_maxabs", "max |PorePressRate| [Pa/s]", "t4o_porepressrate_maxabs_vs_time", True)
    plot_metric("velocity_max", "max velocity [m/s]", "t4o_velocity_max_vs_time", True)
    plot_metric("divvel_maxabs", "max |DivVel| [1/s]", "t4o_divvel_maxabs_vs_time", True)
    plot_metric("negative_pressure_count", "negative pressure count", "t4o_negative_pressure_count_vs_time")

    # Region-wise q at final frames.
    region_rows: list[dict[str, object]] = []
    for key, case in CASES.items():
        files = part_files(case)
        if files:
            region_rows.extend(region_metrics(key, case, files[-1]))
    if region_rows:
        classes = ["interior", "lateral", "top_cap", "bottom_cap", "edge"]
        plt.figure(figsize=(7.2, 4.2))
        width = 0.25
        xs = list(range(len(classes)))
        for offset, key in enumerate(frames):
            vals = []
            for cls in classes:
                row = next((r for r in region_rows if r["case"] == key and r["class"] == cls), None)
                vals.append(float(row["q_mean"]) if row else 0.0)
            plt.bar([x + (offset - 1) * width for x in xs], vals, width=width, label=key)
        plt.xticks(xs, classes, rotation=20)
        plt.ylabel("final q proxy [Pa]")
        plt.grid(True, axis="y", alpha=0.3)
        plt.legend(fontsize=8)
        plt.tight_layout()
        for ext in ("png", "svg"):
            plt.savefig(FIGDIR / f"t4o_region_wise_q.{ext}", dpi=180)
        plt.close()

    # Cap and lateral acceleration diagnostics.
    cap_rows = []
    flex_rows = []
    feedback_rows = []
    for case in CASES.values():
        cap_rows.extend(parse_cap_diag(case))
        flex_rows.extend(parse_flexible_diag(case))
        feedback_rows.extend(parse_feedback_diag(case))
    if cap_rows:
        plt.figure(figsize=(7.2, 4.2))
        for case in CASES.values():
            rows = [r for r in cap_rows if r["case"] == case]
            if rows:
                plt.plot([float(r["time"]) for r in rows], [float(r["top_accel_mean"]) for r in rows], label=f"{case} top")
                plt.plot([float(r["time"]) for r in rows], [float(r["bottom_accel_mean"]) for r in rows], "--", label=f"{case} bottom")
        plt.xlabel("time [s]")
        plt.ylabel("cap support acceleration [m/s2]")
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=6)
        plt.tight_layout()
        for ext in ("png", "svg"):
            plt.savefig(FIGDIR / f"t4o_cap_support_acceleration.{ext}", dpi=180)
        plt.close()
    if flex_rows:
        plt.figure(figsize=(7.2, 4.2))
        for case in CASES.values():
            rows = [r for r in flex_rows if r["case"] == case]
            if rows:
                plt.plot([float(r["time"]) for r in rows], [float(r["max_accel"]) for r in rows], label=case)
        plt.xlabel("time [s]")
        plt.ylabel("lateral/flexible max acceleration [m/s2]")
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=7)
        plt.tight_layout()
        for ext in ("png", "svg"):
            plt.savefig(FIGDIR / f"t4o_lateral_acceleration.{ext}", dpi=180)
        plt.close()
    if feedback_rows:
        plt.figure(figsize=(7.2, 4.2))
        for case in CASES.values():
            rows = [r for r in feedback_rows if r["case"] == case]
            if rows:
                plt.plot([float(r["time"]) for r in rows], [float(r["used_max"]) for r in rows], label=case)
        plt.xlabel("time [s]")
        plt.ylabel("feedback used max acceleration [m/s2]")
        plt.yscale("symlog", linthresh=1.0)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=7)
        plt.tight_layout()
        for ext in ("png", "svg"):
            plt.savefig(FIGDIR / f"t4o_feedback_acceleration.{ext}", dpi=180)
        plt.close()


def main() -> None:
    frames = {key: frame_metrics(key, case) for key, case in CASES.items()}
    summary = make_summary(frames)

    write_csv(ROOT / "t4o_case_summary.csv", summary)
    write_csv(ROOT / "t4o_restart_continuity_metrics.csv", restart_continuity())
    write_csv(ROOT / "t4o_cap_support_transition_metrics.csv", make_transition_metrics(summary))
    write_csv(ROOT / "t4o_stageB_equilibrium_metrics.csv", [r for r in summary if r["case"] == "stageB_lateral_cap"])
    write_csv(ROOT / "t4o_feedback_gate_metrics.csv", [r for r in summary if r["case"] == "stageC_delayed_feedback"])
    write_csv(ROOT / "t4o_axial_smoke_metrics.csv", [{"status": "not_run", "reason": "delayed feedback gate failed"}])

    all_regions: list[dict[str, object]] = []
    for key, case in CASES.items():
        files = part_files(case)
        if files:
            all_regions.extend(region_metrics(key, case, files[-1]))
    write_csv(ROOT / "t4o_region_stress_metrics.csv", all_regions)

    cap_rows: list[dict[str, object]] = []
    flex_rows: list[dict[str, object]] = []
    feedback_rows: list[dict[str, object]] = []
    for case in CASES.values():
        cap_rows.extend(parse_cap_diag(case))
        flex_rows.extend(parse_flexible_diag(case))
        feedback_rows.extend(parse_feedback_diag(case))
    write_csv(ROOT / "t4o_cap_support_metrics.csv", cap_rows)
    write_csv(ROOT / "t4o_lateral_confinement_metrics.csv", flex_rows)
    write_csv(ROOT / "t4o_feedback_diagnostics.csv", feedback_rows)

    for key, recs in frames.items():
        write_csv(ROOT / f"t4o_{key}_frame_metrics.csv", [dict(r) for r in recs])

    make_plots(frames)

    print("Wrote T4o CSV metrics and figures.")
    for row in summary:
        print(
            f"{row['case']}: code={row['code']} excluded={row['excluded']} "
            f"q={float(row['final_q_mean']):.3f} p'={float(row['final_p_eff_mean']):.3f} "
            f"max|PPR|={float(row['max_porepressrate_maxabs']):.3e} "
            f"vmax={float(row['max_velocity']):.3e}"
        )


if __name__ == "__main__":
    main()
