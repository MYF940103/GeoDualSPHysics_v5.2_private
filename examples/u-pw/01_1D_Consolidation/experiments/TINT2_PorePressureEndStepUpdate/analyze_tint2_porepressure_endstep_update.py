#!/usr/bin/env python3
"""Postprocess TINT2 end-step pore-pressure commit experiments."""

from __future__ import annotations

import csv
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
FIGDIR = ROOT / "figures"

DP = 0.01
E = 2.0e6
NU = 0.3
KW = 2.0e8
POROSITY = 0.3
KPERM = 1.0e-3
RHO_W = 1000.0
G = 9.81
NTERMS = 250

CASES = [
    ("l3c_op1_m0", "Case1DConsolidation_PR_TINT2_L3c_Op1_Mode0", "L3c", "feedback_off", "Symplectic"),
    ("l3c_op1_m1", "Case1DConsolidation_PR_TINT2_L3c_Op1_Mode1", "L3c", "feedback_off", "Symplectic"),
    ("l3c_op2_m0", "Case1DConsolidation_PR_TINT2_L3c_Op2_Mode0", "BND1", "feedback_off", "Symplectic"),
    ("l3c_op2_m1", "Case1DConsolidation_PR_TINT2_L3c_Op2_Mode1", "BND1", "feedback_off", "Symplectic"),
    ("l5_op1_m0", "Case1DConsolidation_PR_TINT2_L5_Op1_Mode0", "L5", "feedback_on", "Symplectic"),
    ("l5_op1_m1", "Case1DConsolidation_PR_TINT2_L5_Op1_Mode1", "L5", "feedback_on", "Symplectic"),
    ("l5_op2_m0", "Case1DConsolidation_PR_TINT2_L5_Op2_Mode0", "BND1", "feedback_on", "Symplectic"),
    ("l5_op2_m1", "Case1DConsolidation_PR_TINT2_L5_Op2_Mode1", "BND1", "feedback_on", "Symplectic"),
    ("verlet_l3c_op1_m0", "Case1DConsolidation_PR_TINT2_Verlet_L3c_Op1_Mode0", "L3c", "feedback_off", "Verlet"),
    ("verlet_l3c_op1_m1", "Case1DConsolidation_PR_TINT2_Verlet_L3c_Op1_Mode1", "L3c", "feedback_off", "Verlet"),
]


def constrained_modulus() -> float:
    k_bulk = E / (3.0 * (1.0 - 2.0 * NU))
    g_shear = E / (2.0 * (1.0 + NU))
    return k_bulk + 4.0 * g_shear / 3.0


M_1D = constrained_modulus()
STORAGE_MOD = (M_1D * (KW / POROSITY)) / (M_1D + (KW / POROSITY))
CV = KPERM * STORAGE_MOD / (RHO_W * G)


def xml_value(case: str, key: str, default: float) -> float:
    path = ROOT / f"{case}_Def.xml"
    if not path.exists():
        return default
    root = ET.parse(path).getroot()
    for par in root.findall(".//parameter"):
        if par.attrib.get("key") == key:
            try:
                return float(par.attrib.get("value", default))
            except (TypeError, ValueError):
                return default
    return default


def read_partcsv(path: Path) -> list[dict[str, float | int]]:
    keys = (
        "Mk",
        "Pos.x [m]",
        "Pos.y [m]",
        "Pos.z [m]",
        "Vel.x [m/s]",
        "Vel.y [m/s]",
        "Vel.z [m/s]",
        "PorePress",
        "ExcessPorePress",
        "PorePressRate",
        "DivVel",
        "LapPorePress",
        "LapZ",
        "DivVelCorr",
        "LapPorePressCorr",
        "LapZCorr",
        "PorePressureAccelDiff.x",
        "PorePressureAccelDiff.y",
        "PorePressureAccelDiff.z",
    )
    rows: list[dict[str, float | int]] = []
    with path.open(newline="", errors="ignore") as fp:
        reader = csv.DictReader(fp, delimiter=";")
        for raw in reader:
            try:
                row: dict[str, float | int] = {
                    "Idp": int(float(raw.get("Idp", "nan"))),
                    "Type": int(float(raw.get("Type", "nan"))),
                }
            except ValueError:
                continue
            for key in keys:
                try:
                    row[key] = float(raw.get(key, "0") or 0)
                except ValueError:
                    row[key] = 0.0
            rows.append(row)
    return rows


def is_material(row: dict[str, float | int]) -> bool:
    if int(row.get("Type", -1)) == 3:
        return True
    x = float(row.get("Pos.x [m]", 0.0))
    z = float(row.get("Pos.z [m]", 0.0))
    return -1e-9 <= x <= 0.100000001 and -1e-9 <= z <= 1.000000001


def frame_index(path: Path) -> int:
    match = re.search(r"PartCsv_(\d+)\.csv$", path.name)
    return int(match.group(1)) if match else 0


def mean(vals) -> float:
    vals = [v for v in vals if math.isfinite(v)]
    return sum(vals) / len(vals) if vals else 0.0


def maxabs(vals) -> float:
    vals = [abs(v) for v in vals if math.isfinite(v)]
    return max(vals) if vals else 0.0


def rmse(vals) -> float:
    vals = [v for v in vals if math.isfinite(v)]
    return math.sqrt(sum(v * v for v in vals) / len(vals)) if vals else 0.0


def terzaghi_excess(depth_from_top: float, time_s: float, h: float, amp: float) -> float:
    if h <= 0:
        return 0.0
    y = max(0.0, min(h, depth_from_top))
    tv = CV * time_s / (h * h)
    total = 0.0
    for n in range(NTERMS):
        m = (2 * n + 1) * math.pi / 2.0
        total += (2.0 / m) * math.sin(m * y / h) * math.exp(-(m * m) * tv)
    return amp * total


def run_text(outdir: Path) -> str:
    path = outdir / "Run.out"
    return path.read_text(errors="ignore") if path.exists() else ""


def find_run_value(text: str, pattern: str, default: str = "") -> str:
    match = re.search(pattern, text)
    return match.group(1) if match else default


def run_info(text: str) -> dict[str, object]:
    return {
        "code": find_run_value(text, r"Finished execution \(code=([0-9-]+)\)", "missing"),
        "excluded": find_run_value(text, r"Excluded particles\.+:\s+(\d+)", "missing"),
        "dtmin_adjustments": find_run_value(text, r"DTs adjusted to DtMin\.+:\s+(\d+)", "0"),
        "runtime_s": find_run_value(text, r"Total Runtime\.+:\s+([0-9.Ee+-]+)", ""),
        "steps": find_run_value(text, r"Steps of simulation\.+:\s+(\d+)", ""),
    }


def boundary_log_metrics(text: str) -> dict[str, object]:
    metrics: dict[str, object] = {"boundary_log_found": "no"}
    match = re.search(
        r"CPU hydraulic boundary-particle operator: drained_pairs=(\d+), noflux_pairs=(\d+), "
        r"bottom_noflux_pairs=(\d+), ordinary_solid_noflux_pairs=(\d+), boundary_pairs=(\d+), "
        r"inactive_boundary_neighbours=(\d+)",
        text,
    )
    if match:
        metrics.update(
            {
                "boundary_log_found": "yes",
                "drained_pairs": int(match.group(1)),
                "noflux_pairs": int(match.group(2)),
                "bottom_noflux_pairs": int(match.group(3)),
                "ordinary_solid_noflux_pairs": int(match.group(4)),
                "boundary_pairs": int(match.group(5)),
                "inactive_boundary_neighbours": int(match.group(6)),
            }
        )
    match = re.search(
        r"CPU hydraulic boundary-particle unique targets: drained=(\d+), noflux=(\d+), "
        r"bottom_noflux=(\d+), ordinary_solid_noflux=(\d+), normals_used=(\d+), "
        r"MLS_samples=(\d+), MLS_fallback=(\d+), reconstructed_excess=\[([0-9.Ee+\-]+),([0-9.Ee+\-]+)\] Pa",
        text,
    )
    if match:
        metrics.update(
            {
                "unique_drained": int(match.group(1)),
                "unique_noflux": int(match.group(2)),
                "unique_bottom_noflux": int(match.group(3)),
                "unique_ordinary_solid_noflux": int(match.group(4)),
                "normals_used": int(match.group(5)),
                "mls_samples": int(match.group(6)),
                "mls_fallback": int(match.group(7)),
                "reconstructed_excess_min": float(match.group(8)),
                "reconstructed_excess_max": float(match.group(9)),
            }
        )
    return metrics


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def analyze_case(case_id: str, case: str, family: str, route: str, integrator_label: str) -> dict[str, object]:
    time_out = xml_value(case, "TimeOut", 0.001)
    time_max = xml_value(case, "TimeMax", 0.005)
    amp = xml_value(case, "PorePressureExcessAmp", 10000.0)
    feedback = int(xml_value(case, "PorePressureFeedback", 0))
    boundary_operator = int(xml_value(case, "PorePressureBoundaryOperator", 0))
    tint_mode = int(xml_value(case, "PorePressureTimeIntegrationMode", 0))
    step_algorithm = int(xml_value(case, "StepAlgorithm", 2))
    integrator = "Verlet" if step_algorithm == 1 else "Symplectic"
    if integrator_label:
        integrator = integrator_label
    outdir = ROOT / f"{case}_cpu_out"
    text = run_text(outdir)
    info = run_info(text)
    blog = boundary_log_metrics(text)
    paths = sorted((outdir / "data").glob("PartCsv_*.csv"), key=frame_index) if (outdir / "data").exists() else []
    if not paths:
        return {
            "summary": {
                "case_id": case_id,
                "case": case,
                "family": family,
                "route": route,
                "integrator": integrator,
                "time_integration_mode": tint_mode,
                "boundary_operator": boundary_operator,
                "feedback": feedback,
                "status": "missing_output",
                **info,
                **blog,
            },
            "pressure": [],
            "boundary": [],
            "stability": [],
            "profiles": [],
            "delta": [],
        }

    pressure_rows: list[dict[str, object]] = []
    boundary_rows: list[dict[str, object]] = []
    stability_rows: list[dict[str, object]] = []
    profile_rows: list[dict[str, object]] = []
    delta_rows: list[dict[str, object]] = []
    bottom_errors: list[float] = []
    peak_excess = 0.0
    min_excess = 0.0
    max_velocity = 0.0
    max_div = 0.0
    max_rate = 0.0
    max_accel = 0.0
    max_lap_p = 0.0
    final_profile_rmse = 0.0
    final_top_resid = 0.0
    final_bottom_noflux = 0.0
    monotonic_violations = 0
    prev_vol_mean: float | None = None
    prev_rate_mean: float | None = None
    prev_time: float | None = None
    selected = {0, max(0, len(paths) // 2), len(paths) - 1}

    for idx, path in enumerate(paths):
        time_s = frame_index(path) * time_out
        rows = [row for row in read_partcsv(path) if is_material(row)]
        if not rows:
            continue
        z_values = [float(row["Pos.z [m]"]) for row in rows]
        zmin, zmax = min(z_values), max(z_values)
        height = max(zmax - zmin, 1e-12)
        excess = [float(row["ExcessPorePress"]) for row in rows]
        rates = [float(row["PorePressRate"]) for row in rows]
        divs = [float(row["DivVel"]) for row in rows]
        lap_p = [float(row["LapPorePress"]) for row in rows]
        velocities = [
            math.sqrt(float(row["Vel.x [m/s]"]) ** 2 + float(row["Vel.y [m/s]"]) ** 2 + float(row["Vel.z [m/s]"]) ** 2)
            for row in rows
        ]
        accels = [
            math.sqrt(
                float(row["PorePressureAccelDiff.x"]) ** 2
                + float(row["PorePressureAccelDiff.y"]) ** 2
                + float(row["PorePressureAccelDiff.z"]) ** 2
            )
            for row in rows
        ]
        top_rows = [row for row in rows if float(row["Pos.z [m]"]) >= zmax - 0.5 * DP - 1e-12]
        bottom_rows = [row for row in rows if float(row["Pos.z [m]"]) <= zmin + 2 * DP + 1e-12]
        ref_rows = [row for row in rows if zmin + 2 * DP < float(row["Pos.z [m]"]) <= zmin + 4 * DP + 1e-12]
        top_resid = maxabs(float(row["ExcessPorePress"]) for row in top_rows)
        bottom_mean = mean(float(row["ExcessPorePress"]) for row in bottom_rows)
        ref_mean = mean(float(row["ExcessPorePress"]) for row in ref_rows)
        bottom_noflux = bottom_mean - ref_mean
        bottom_depth = zmax - mean(float(row["Pos.z [m]"]) for row in bottom_rows)
        analytical_bottom = terzaghi_excess(bottom_depth, time_s, height, amp)
        bottom_errors.append(bottom_mean - analytical_bottom)
        profile_errors = []
        for row in rows:
            z = float(row["Pos.z [m]"])
            analytical = terzaghi_excess(zmax - z, time_s, height, amp)
            value = float(row["ExcessPorePress"])
            profile_errors.append(value - analytical)
            if idx in selected:
                profile_rows.append(
                    {
                        "case_id": case_id,
                        "time_s": time_s,
                        "z_m": z,
                        "excess_pa": value,
                        "analytical_excess_pa": analytical,
                    }
                )
        profile_rmse = rmse(profile_errors)
        vol_mean = mean(excess)
        rate_mean = mean(rates)
        if prev_vol_mean is not None and vol_mean > prev_vol_mean + max(1e-8, 1e-5 * amp):
            monotonic_violations += 1
        if prev_vol_mean is not None and prev_rate_mean is not None and prev_time is not None:
            dt_frame = time_s - prev_time
            delta_actual = vol_mean - prev_vol_mean
            delta_rate = prev_rate_mean * dt_frame
            delta_rows.append(
                {
                    "case_id": case_id,
                    "time_s": time_s,
                    "dt_frame_s": dt_frame,
                    "deltaP_rate_mean_proxy_pa": delta_rate,
                    "deltaP_actual_mean_pa": delta_actual,
                    "deltaP_correction_mean_proxy_pa": delta_actual - delta_rate,
                    "relative_correction_proxy": (delta_actual - delta_rate) / max(abs(delta_rate), 1e-12),
                }
            )
        prev_vol_mean = vol_mean
        prev_rate_mean = rate_mean
        prev_time = time_s

        peak_excess = max(peak_excess, maxabs(excess))
        min_excess = min(min_excess, min(excess))
        max_velocity = max(max_velocity, maxabs(velocities))
        max_div = max(max_div, maxabs(divs))
        max_rate = max(max_rate, maxabs(rates))
        max_accel = max(max_accel, maxabs(accels))
        max_lap_p = max(max_lap_p, maxabs(lap_p))
        final_profile_rmse = profile_rmse
        final_top_resid = top_resid
        final_bottom_noflux = bottom_noflux

        common = {
            "case_id": case_id,
            "time_s": time_s,
            "time_integration_mode": tint_mode,
            "boundary_operator": boundary_operator,
            "feedback": feedback,
        }
        pressure_rows.append(
            {
                **common,
                "vol_mean_excess_pa": vol_mean,
                "peak_abs_excess_pa": maxabs(excess),
                "min_excess_pa": min(excess),
                "bottom_excess_mean_pa": bottom_mean,
                "bottom_analytical_pa": analytical_bottom,
                "bottom_error_pa": bottom_mean - analytical_bottom,
                "profile_rmse_pa": profile_rmse,
            }
        )
        boundary_rows.append(
            {
                **common,
                "top_drained_residual_pa": top_resid,
                "bottom_noflux_proxy_pa": bottom_noflux,
                "bottom_mean_pa": bottom_mean,
                "bottom_reference_mean_pa": ref_mean,
            }
        )
        stability_rows.append(
            {
                **common,
                "velocity_max_mps": maxabs(velocities),
                "divvel_max_abs": maxabs(divs),
                "porepressrate_max_abs_pa_s": maxabs(rates),
                "porepressrate_mean_pa_s": rate_mean,
                "feedback_accel_max_abs_mps2": maxabs(accels),
                "lap_porepress_max_abs": maxabs(lap_p),
            }
        )

    summary = {
        "case_id": case_id,
        "case": case,
        "family": family,
        "route": route,
        "integrator": integrator,
        "step_algorithm": step_algorithm,
        "time_integration_mode": tint_mode,
        "boundary_operator": boundary_operator,
        "feedback": feedback,
        "time_max_s": time_max,
        "time_out_s": time_out,
        "status": "ok",
        **info,
        **blog,
        "peak_abs_excess_pa": peak_excess,
        "min_excess_pa": min_excess,
        "bottom_rmse_pa": rmse(bottom_errors),
        "final_profile_rmse_pa": final_profile_rmse,
        "final_top_drained_residual_pa": final_top_resid,
        "final_bottom_noflux_proxy_pa": final_bottom_noflux,
        "velocity_max_mps": max_velocity,
        "divvel_max_abs": max_div,
        "porepressrate_max_abs_pa_s": max_rate,
        "feedback_accel_max_abs_mps2": max_accel,
        "lap_porepress_max_abs": max_lap_p,
        "monotonic_violations": monotonic_violations,
    }
    return {
        "summary": summary,
        "pressure": pressure_rows,
        "boundary": boundary_rows,
        "stability": stability_rows,
        "profiles": profile_rows,
        "delta": delta_rows,
    }


def line_plot(rows: list[dict[str, object]], path: Path, title: str, ylabel: str, key: str, case_filter=None) -> None:
    FIGDIR.mkdir(exist_ok=True)
    grouped: dict[str, list[tuple[float, float]]] = {}
    for row in rows:
        if case_filter and not case_filter(row):
            continue
        grouped.setdefault(str(row["case_id"]), []).append((float(row["time_s"]), float(row.get(key, 0.0) or 0.0)))
    if not grouped:
        return
    plt.figure(figsize=(7.2, 4.3))
    for label, vals in sorted(grouped.items()):
        vals.sort()
        plt.plot([v[0] for v in vals], [v[1] for v in vals], marker="o", linewidth=1.5, label=label)
    plt.xlabel("time [s]")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(path.with_suffix(".png"), dpi=180)
    plt.savefig(path.with_suffix(".svg"))
    plt.close()


def bar_plot(summary_rows: list[dict[str, object]], path: Path, title: str, ylabel: str, key: str, case_filter=None) -> None:
    rows = [row for row in summary_rows if not case_filter or case_filter(row)]
    if not rows:
        return
    labels = [str(row["case_id"]) for row in rows]
    vals = [float(row.get(key, 0.0) or 0.0) for row in rows]
    plt.figure(figsize=(8.0, 4.2))
    plt.bar(labels, vals, color="#3f7cac")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(rotation=35, ha="right", fontsize=7)
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(path.with_suffix(".png"), dpi=180)
    plt.savefig(path.with_suffix(".svg"))
    plt.close()


def profile_plot(profile_rows: list[dict[str, object]], path: Path, title: str, case_filter=None) -> None:
    rows = [row for row in profile_rows if not case_filter or case_filter(row)]
    if not rows:
        return
    grouped: dict[tuple[str, float], list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault((str(row["case_id"]), float(row["time_s"])), []).append(row)
    plt.figure(figsize=(6.2, 4.8))
    for (case_id, time_s), vals in sorted(grouped.items()):
        vals.sort(key=lambda item: float(item["z_m"]))
        z = [float(item["z_m"]) for item in vals]
        ex = [float(item["excess_pa"]) for item in vals]
        if time_s == max(float(row["time_s"]) for row in rows if str(row["case_id"]) == case_id):
            plt.plot(ex, z, linewidth=1.8, label=f"{case_id} t={time_s:.3g}")
    analytical_groups: dict[float, list[dict[str, object]]] = {}
    for row in rows:
        analytical_groups.setdefault(float(row["time_s"]), []).append(row)
    if analytical_groups:
        time_s = max(analytical_groups)
        vals = sorted(analytical_groups[time_s], key=lambda item: float(item["z_m"]))
        plt.plot([float(item["analytical_excess_pa"]) for item in vals], [float(item["z_m"]) for item in vals], "k--", linewidth=1.4, label="analytical final")
    plt.xlabel("excess pore pressure [Pa]")
    plt.ylabel("z [m]")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(path.with_suffix(".png"), dpi=180)
    plt.savefig(path.with_suffix(".svg"))
    plt.close()


def comparison_rows(summary_rows: list[dict[str, object]], predicate) -> list[dict[str, object]]:
    rows = [row for row in summary_rows if predicate(row)]
    fields = (
        "case_id",
        "integrator",
        "time_integration_mode",
        "boundary_operator",
        "feedback",
        "code",
        "excluded",
        "dtmin_adjustments",
        "peak_abs_excess_pa",
        "bottom_rmse_pa",
        "final_profile_rmse_pa",
        "final_top_drained_residual_pa",
        "final_bottom_noflux_proxy_pa",
        "velocity_max_mps",
        "divvel_max_abs",
        "porepressrate_max_abs_pa_s",
        "feedback_accel_max_abs_mps2",
        "ordinary_solid_noflux_pairs",
        "unique_ordinary_solid_noflux",
    )
    return [{field: row.get(field, "") for field in fields} for row in rows]


def main() -> None:
    FIGDIR.mkdir(exist_ok=True)
    results = [analyze_case(*case) for case in CASES]
    summary_rows = [result["summary"] for result in results]
    pressure_rows = [row for result in results for row in result["pressure"]]
    boundary_rows = [row for result in results for row in result["boundary"]]
    stability_rows = [row for result in results for row in result["stability"]]
    profile_rows = [row for result in results for row in result["profiles"]]
    delta_rows = [row for result in results for row in result["delta"]]

    summary_fields = [
        "case_id",
        "case",
        "family",
        "route",
        "integrator",
        "step_algorithm",
        "time_integration_mode",
        "boundary_operator",
        "feedback",
        "time_max_s",
        "time_out_s",
        "code",
        "excluded",
        "dtmin_adjustments",
        "steps",
        "runtime_s",
        "peak_abs_excess_pa",
        "min_excess_pa",
        "bottom_rmse_pa",
        "final_profile_rmse_pa",
        "final_top_drained_residual_pa",
        "final_bottom_noflux_proxy_pa",
        "velocity_max_mps",
        "divvel_max_abs",
        "porepressrate_max_abs_pa_s",
        "feedback_accel_max_abs_mps2",
        "lap_porepress_max_abs",
        "monotonic_violations",
        "boundary_log_found",
        "drained_pairs",
        "noflux_pairs",
        "bottom_noflux_pairs",
        "ordinary_solid_noflux_pairs",
        "boundary_pairs",
        "inactive_boundary_neighbours",
        "unique_drained",
        "unique_noflux",
        "unique_bottom_noflux",
        "unique_ordinary_solid_noflux",
        "mls_fallback",
    ]
    write_csv(ROOT / "tint2_case_summary.csv", summary_rows, summary_fields)

    cmp_fields = [
        "case_id",
        "integrator",
        "time_integration_mode",
        "boundary_operator",
        "feedback",
        "code",
        "excluded",
        "dtmin_adjustments",
        "peak_abs_excess_pa",
        "bottom_rmse_pa",
        "final_profile_rmse_pa",
        "final_top_drained_residual_pa",
        "final_bottom_noflux_proxy_pa",
        "velocity_max_mps",
        "divvel_max_abs",
        "porepressrate_max_abs_pa_s",
        "feedback_accel_max_abs_mps2",
        "ordinary_solid_noflux_pairs",
        "unique_ordinary_solid_noflux",
    ]
    write_csv(
        ROOT / "tint2_l3c_feedbackoff_comparison.csv",
        comparison_rows(summary_rows, lambda row: row.get("family") == "L3c" and int(row.get("boundary_operator", 0)) == 1 and int(row.get("feedback", 0)) == 0),
        cmp_fields,
    )
    write_csv(
        ROOT / "tint2_l5_feedbackon_comparison.csv",
        comparison_rows(summary_rows, lambda row: row.get("family") == "L5" and int(row.get("boundary_operator", 0)) == 1 and int(row.get("feedback", 0)) == 1),
        cmp_fields,
    )
    write_csv(
        ROOT / "tint2_bnd1_mode2_comparison.csv",
        comparison_rows(summary_rows, lambda row: int(row.get("boundary_operator", 0)) == 2),
        cmp_fields,
    )
    write_csv(ROOT / "tint2_boundary_metrics.csv", boundary_rows, ["case_id", "time_s", "time_integration_mode", "boundary_operator", "feedback", "top_drained_residual_pa", "bottom_noflux_proxy_pa", "bottom_mean_pa", "bottom_reference_mean_pa"])
    write_csv(ROOT / "tint2_stability_metrics.csv", stability_rows, ["case_id", "time_s", "time_integration_mode", "boundary_operator", "feedback", "velocity_max_mps", "divvel_max_abs", "porepressrate_max_abs_pa_s", "porepressrate_mean_pa_s", "feedback_accel_max_abs_mps2", "lap_porepress_max_abs"])
    write_csv(ROOT / "tint2_deltaP_bookkeeping.csv", delta_rows, ["case_id", "time_s", "dt_frame_s", "deltaP_rate_mean_proxy_pa", "deltaP_actual_mean_pa", "deltaP_correction_mean_proxy_pa", "relative_correction_proxy"])
    write_csv(
        ROOT / "tint2_integrator_path_summary.csv",
        comparison_rows(summary_rows, lambda row: row.get("family") == "L3c" and int(row.get("boundary_operator", 0)) == 1),
        cmp_fields,
    )

    decision_rows: list[dict[str, object]] = []
    pairs = [
        ("l3c_op1", "l3c_op1_m0", "l3c_op1_m1"),
        ("l5_op1", "l5_op1_m0", "l5_op1_m1"),
        ("bnd1_op2_feedback_off", "l3c_op2_m0", "l3c_op2_m1"),
        ("bnd1_op2_feedback_on", "l5_op2_m0", "l5_op2_m1"),
        ("verlet_l3c_op1", "verlet_l3c_op1_m0", "verlet_l3c_op1_m1"),
    ]
    by_id = {str(row["case_id"]): row for row in summary_rows}
    for label, m0, m1 in pairs:
        a, b = by_id.get(m0, {}), by_id.get(m1, {})
        decision_rows.append(
            {
                "comparison": label,
                "mode0_excluded": a.get("excluded", ""),
                "mode1_excluded": b.get("excluded", ""),
                "mode0_dtmin": a.get("dtmin_adjustments", ""),
                "mode1_dtmin": b.get("dtmin_adjustments", ""),
                "mode0_bottom_rmse_pa": a.get("bottom_rmse_pa", ""),
                "mode1_bottom_rmse_pa": b.get("bottom_rmse_pa", ""),
                "mode0_profile_rmse_pa": a.get("final_profile_rmse_pa", ""),
                "mode1_profile_rmse_pa": b.get("final_profile_rmse_pa", ""),
                "mode0_rate_max_pa_s": a.get("porepressrate_max_abs_pa_s", ""),
                "mode1_rate_max_pa_s": b.get("porepressrate_max_abs_pa_s", ""),
                "decision_signal": "improved" if str(b.get("excluded", "")) <= str(a.get("excluded", "")) and float(b.get("bottom_rmse_pa", 1e99) or 1e99) <= float(a.get("bottom_rmse_pa", 1e99) or 1e99) else "mixed_or_no_improvement",
            }
        )
    write_csv(
        ROOT / "tint2_interface_decision_inputs.csv",
        decision_rows,
        [
            "comparison",
            "mode0_excluded",
            "mode1_excluded",
            "mode0_dtmin",
            "mode1_dtmin",
            "mode0_bottom_rmse_pa",
            "mode1_bottom_rmse_pa",
            "mode0_profile_rmse_pa",
            "mode1_profile_rmse_pa",
            "mode0_rate_max_pa_s",
            "mode1_rate_max_pa_s",
            "decision_signal",
        ],
    )

    profile_plot(profile_rows, FIGDIR / "tint2_l3c_mode0_mode1_profiles", "L3c profiles: mode 0 vs mode 1", lambda row: str(row["case_id"]) in {"l3c_op1_m0", "l3c_op1_m1"})
    bar_plot(summary_rows, FIGDIR / "tint2_l3c_profile_rmse", "L3c profile RMSE", "RMSE [Pa]", "final_profile_rmse_pa", lambda row: str(row["case_id"]) in {"l3c_op1_m0", "l3c_op1_m1", "verlet_l3c_op1_m0", "verlet_l3c_op1_m1"})
    line_plot(pressure_rows, FIGDIR / "tint2_l3c_bottom_excess", "L3c bottom excess", "bottom excess [Pa]", "bottom_excess_mean_pa", lambda row: str(row["case_id"]) in {"l3c_op1_m0", "l3c_op1_m1", "verlet_l3c_op1_m0", "verlet_l3c_op1_m1"})
    line_plot(stability_rows, FIGDIR / "tint2_l5_porepressrate", "L5 feedback-on PorePressRate", "max |PorePressRate| [Pa/s]", "porepressrate_max_abs_pa_s", lambda row: str(row["case_id"]) in {"l5_op1_m0", "l5_op1_m1"})
    line_plot(stability_rows, FIGDIR / "tint2_l5_divvel", "L5 feedback-on DivVel", "max |DivVel|", "divvel_max_abs", lambda row: str(row["case_id"]) in {"l5_op1_m0", "l5_op1_m1"})
    profile_plot(profile_rows, FIGDIR / "tint2_bnd1_mode2_feedbackoff_profiles", "BND1 mode2 feedback-off profiles", lambda row: str(row["case_id"]) in {"l3c_op2_m0", "l3c_op2_m1"})
    bar_plot(summary_rows, FIGDIR / "tint2_bnd1_mode2_feedbackon_excluded", "BND1 mode2 feedback-on excluded", "excluded particles", "excluded", lambda row: str(row["case_id"]) in {"l5_op2_m0", "l5_op2_m1"})
    line_plot(boundary_rows, FIGDIR / "tint2_top_residual", "Top drained residual", "max top residual [Pa]", "top_drained_residual_pa")
    line_plot(boundary_rows, FIGDIR / "tint2_bottom_noflux", "Bottom no-flux proxy", "bottom proxy [Pa]", "bottom_noflux_proxy_pa")
    line_plot(delta_rows, FIGDIR / "tint2_deltaP_rate_actual", "DeltaP rate proxy", "DeltaP [Pa/output]", "deltaP_rate_mean_proxy_pa")
    line_plot(delta_rows, FIGDIR / "tint2_deltaP_correction", "DeltaP correction proxy", "DeltaP correction [Pa/output]", "deltaP_correction_mean_proxy_pa")
    bar_plot(summary_rows, FIGDIR / "tint2_integrator_path_summary", "Verlet/Symplectic L3c summary", "final profile RMSE [Pa]", "final_profile_rmse_pa", lambda row: row.get("family") == "L3c" and int(row.get("boundary_operator", 0)) == 1)


if __name__ == "__main__":
    main()
