#!/usr/bin/env python3
"""Postprocess BND1 generalized pore-pressure boundary-operator checks."""

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
    ("l3c_mode1", "Case1DConsolidation_PR_BND1_L3c_Mode1", "feedback_off", 1),
    ("l3c_mode2", "Case1DConsolidation_PR_BND1_L3c_Mode2", "feedback_off", 2),
    ("l5_mode1", "Case1DConsolidation_PR_BND1_L5_Mode1", "feedback_on", 1),
    ("l5_mode2", "Case1DConsolidation_PR_BND1_L5_Mode2", "feedback_on", 2),
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
            except ValueError:
                return default
    return default


def read_partcsv(path: Path) -> list[dict[str, float | int]]:
    keys = (
        "Mk",
        "Pos.x [m]",
        "Pos.z [m]",
        "Vel.x [m/s]",
        "Vel.y [m/s]",
        "Vel.z [m/s]",
        "ExcessPorePress",
        "PorePressRate",
        "DivVel",
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
    m = re.search(r"PartCsv_(\d+)\.csv$", path.name)
    return int(m.group(1)) if m else 0


def mean(vals) -> float:
    vals = [v for v in vals if math.isfinite(v)]
    return sum(vals) / len(vals) if vals else 0.0


def maxabs(vals) -> float:
    vals = [abs(v) for v in vals if math.isfinite(v)]
    return max(vals) if vals else 0.0


def rmse(vals) -> float:
    vals = [v for v in vals if math.isfinite(v)]
    return math.sqrt(sum(v * v for v in vals) / len(vals)) if vals else 0.0


def terzaghi_excess(depth: float, time_s: float, h: float, amp: float) -> float:
    if h <= 0:
        return 0.0
    y = max(0.0, min(h, depth))
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
    m = re.search(pattern, text)
    return m.group(1) if m else default


def run_info(text: str) -> dict[str, str]:
    return {
        "code": find_run_value(text, r"Finished execution \(code=([0-9-]+)\)", "missing"),
        "excluded": find_run_value(text, r"Excluded particles\.+:\s+(\d+)", "missing"),
        "dtmin_adjustments": find_run_value(text, r"DTs adjusted to DtMin\.+:\s+(\d+)", ""),
        "runtime_s": find_run_value(text, r"Total Runtime\.+:\s+([0-9.Ee+-]+)", ""),
        "steps": find_run_value(text, r"Steps of simulation\.+:\s+(\d+)", ""),
    }


def boundary_log_metrics(text: str) -> dict[str, object]:
    metrics: dict[str, object] = {"boundary_log_found": "no"}
    m = re.search(
        r"CPU hydraulic boundary-particle operator: drained_pairs=(\d+), noflux_pairs=(\d+), "
        r"bottom_noflux_pairs=(\d+), ordinary_solid_noflux_pairs=(\d+), boundary_pairs=(\d+), "
        r"inactive_boundary_neighbours=(\d+)",
        text,
    )
    if m:
        metrics.update(
            {
                "boundary_log_found": "yes",
                "drained_pairs": int(m.group(1)),
                "noflux_pairs": int(m.group(2)),
                "bottom_noflux_pairs": int(m.group(3)),
                "ordinary_solid_noflux_pairs": int(m.group(4)),
                "boundary_pairs": int(m.group(5)),
                "inactive_boundary_neighbours": int(m.group(6)),
            }
        )
    m = re.search(
        r"CPU hydraulic boundary-particle unique targets: drained=(\d+), noflux=(\d+), "
        r"bottom_noflux=(\d+), ordinary_solid_noflux=(\d+), normals_used=(\d+), "
        r"MLS_samples=(\d+), MLS_fallback=(\d+), reconstructed_excess=\[([0-9.Ee+\-]+),([0-9.Ee+\-]+)\] Pa",
        text,
    )
    if m:
        metrics.update(
            {
                "unique_drained": int(m.group(1)),
                "unique_noflux": int(m.group(2)),
                "unique_bottom_noflux": int(m.group(3)),
                "unique_ordinary_solid_noflux": int(m.group(4)),
                "normals_used": int(m.group(5)),
                "mls_samples": int(m.group(6)),
                "mls_fallback": int(m.group(7)),
                "reconstructed_excess_min": float(m.group(8)),
                "reconstructed_excess_max": float(m.group(9)),
            }
        )
    return metrics


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def analyze_case(case_id: str, case: str, route: str, operator: int) -> dict[str, object]:
    time_out = xml_value(case, "TimeOut", 0.001)
    amp = xml_value(case, "PorePressureExcessAmp", 10000.0)
    feedback = int(xml_value(case, "PorePressureFeedback", 0))
    outdir = ROOT / f"{case}_cpu_out"
    text = run_text(outdir)
    info = run_info(text)
    bndlog = boundary_log_metrics(text)
    paths = sorted((outdir / "data").glob("PartCsv_*.csv"), key=frame_index) if (outdir / "data").exists() else []
    if not paths:
        return {
            "metrics": {"case_id": case_id, "route": route, "operator": operator, "status": "missing_output", **info, **bndlog},
            "pressure": [],
            "boundary": [],
            "stability": [],
            "profiles": [],
        }

    pressure_rows: list[dict[str, object]] = []
    boundary_rows: list[dict[str, object]] = []
    stability_rows: list[dict[str, object]] = []
    profile_rows: list[dict[str, object]] = []
    bottom_errors: list[float] = []
    peak = 0.0
    min_excess = 0.0
    vel_max = div_max = rate_max = accel_max = 0.0
    final_profile_rmse = top_final = bottom_final = lateral_final = 0.0
    monotonic_violations = 0
    last_vol_mean: float | None = None
    selected = {0, max(0, len(paths) // 2), len(paths) - 1}

    for idx, path in enumerate(paths):
        time_s = frame_index(path) * time_out
        rows = [r for r in read_partcsv(path) if is_material(r)]
        z_vals = [float(r["Pos.z [m]"]) for r in rows]
        x_vals = [float(r["Pos.x [m]"]) for r in rows]
        zmin, zmax = min(z_vals), max(z_vals)
        xmin, xmax = min(x_vals), max(x_vals)
        h = max(zmax - zmin, 1e-12)
        excess = [float(r["ExcessPorePress"]) for r in rows]
        vel = [
            math.sqrt(float(r["Vel.x [m/s]"]) ** 2 + float(r["Vel.y [m/s]"]) ** 2 + float(r["Vel.z [m/s]"]) ** 2)
            for r in rows
        ]
        div = [float(r["DivVel"]) for r in rows]
        rate = [float(r["PorePressRate"]) for r in rows]
        acc = [
            math.sqrt(
                float(r["PorePressureAccelDiff.x"]) ** 2
                + float(r["PorePressureAccelDiff.y"]) ** 2
                + float(r["PorePressureAccelDiff.z"]) ** 2
            )
            for r in rows
        ]
        top_rows = [r for r in rows if float(r["Pos.z [m]"]) >= zmax - 2 * DP - 1e-12]
        bottom_rows = [r for r in rows if float(r["Pos.z [m]"]) <= zmin + 2 * DP + 1e-12]
        ref_bottom = [r for r in rows if zmin + 2 * DP < float(r["Pos.z [m]"]) <= zmin + 4 * DP + 1e-12]
        left_wall = [r for r in rows if float(r["Pos.x [m]"]) <= xmin + 2 * DP + 1e-12 and zmin + 4 * DP < float(r["Pos.z [m]"]) < zmax - 4 * DP]
        left_ref = [r for r in rows if xmin + 2 * DP < float(r["Pos.x [m]"]) <= xmin + 4 * DP + 1e-12 and zmin + 4 * DP < float(r["Pos.z [m]"]) < zmax - 4 * DP]
        right_wall = [r for r in rows if float(r["Pos.x [m]"]) >= xmax - 2 * DP - 1e-12 and zmin + 4 * DP < float(r["Pos.z [m]"]) < zmax - 4 * DP]
        right_ref = [r for r in rows if xmax - 4 * DP - 1e-12 <= float(r["Pos.x [m]"]) < xmax - 2 * DP and zmin + 4 * DP < float(r["Pos.z [m]"]) < zmax - 4 * DP]

        top_resid = maxabs(float(r["ExcessPorePress"]) for r in top_rows)
        bottom_mean = mean(float(r["ExcessPorePress"]) for r in bottom_rows)
        bottom_noflux = bottom_mean - mean(float(r["ExcessPorePress"]) for r in ref_bottom)
        lateral_noflux = 0.5 * (
            mean(float(r["ExcessPorePress"]) for r in left_wall)
            - mean(float(r["ExcessPorePress"]) for r in left_ref)
            + mean(float(r["ExcessPorePress"]) for r in right_wall)
            - mean(float(r["ExcessPorePress"]) for r in right_ref)
        )
        ana_bottom = terzaghi_excess(zmax - mean(float(r["Pos.z [m]"]) for r in bottom_rows), time_s, h, amp)
        bottom_errors.append(bottom_mean - ana_bottom)
        profile_errors = []
        for r in rows:
            z = float(r["Pos.z [m]"])
            ana = terzaghi_excess(zmax - z, time_s, h, amp)
            ex = float(r["ExcessPorePress"])
            profile_errors.append(ex - ana)
            if idx in selected:
                profile_rows.append({"case_id": case_id, "time_s": time_s, "z_m": z, "excess": ex, "analytical_excess": ana})
        profile_rmse = rmse(profile_errors)
        vol_mean = mean(excess)
        if last_vol_mean is not None and vol_mean > last_vol_mean + max(1e-8, 1e-5 * amp):
            monotonic_violations += 1
        last_vol_mean = vol_mean
        peak = max(peak, maxabs(excess))
        min_excess = min(min_excess, min(excess))
        vel_max = max(vel_max, maxabs(vel))
        div_max = max(div_max, maxabs(div))
        rate_max = max(rate_max, maxabs(rate))
        accel_max = max(accel_max, maxabs(acc))
        pressure_rows.append(
            {
                "case_id": case_id,
                "time_s": time_s,
                "Tv": CV * time_s / (h * h),
                "volume_mean_excess": vol_mean,
                "peak_abs_excess": maxabs(excess),
                "bottom_excess": bottom_mean,
                "analytical_bottom_excess": ana_bottom,
                "bottom_error": bottom_mean - ana_bottom,
                "profile_rmse": profile_rmse,
            }
        )
        boundary_rows.append(
            {
                "case_id": case_id,
                "time_s": time_s,
                "top_drained_residual": top_resid,
                "bottom_noflux_proxy": bottom_noflux,
                "lateral_noflux_proxy": lateral_noflux,
            }
        )
        stability_rows.append(
            {
                "case_id": case_id,
                "time_s": time_s,
                "velocity_max": maxabs(vel),
                "DivVel_maxAbs": maxabs(div),
                "PorePressRate_maxAbs": maxabs(rate),
                "feedback_accel_max": maxabs(acc),
                "negative_excess_min": min(excess),
            }
        )
        if idx == len(paths) - 1:
            final_profile_rmse, top_final, bottom_final, lateral_final = profile_rmse, top_resid, bottom_noflux, lateral_noflux

    metrics = {
        "case_id": case_id,
        "route": route,
        "operator": operator,
        "feedback": feedback,
        "status": "ok",
        **info,
        **bndlog,
        "frames": len(paths),
        "final_time_s": frame_index(paths[-1]) * time_out,
        "p_w0": amp,
        "peak_abs_excess": peak,
        "min_excess": min_excess,
        "bottom_rmse": rmse(bottom_errors),
        "final_profile_rmse": final_profile_rmse,
        "top_drained_residual_final": top_final,
        "bottom_noflux_proxy_final": bottom_final,
        "lateral_noflux_proxy_final": lateral_final,
        "velocity_max": vel_max,
        "DivVel_maxAbs": div_max,
        "PorePressRate_maxAbs": rate_max,
        "feedback_accel_max": accel_max,
        "monotonic_volume_mean_violations": monotonic_violations,
    }
    return {"metrics": metrics, "pressure": pressure_rows, "boundary": boundary_rows, "stability": stability_rows, "profiles": profile_rows}


def plot_series(rows: list[dict[str, object]], y: str, title: str, name: str, ylabel: str) -> None:
    if not rows:
        return
    groups: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault(str(row["case_id"]), []).append(row)
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    for group, vals in sorted(groups.items()):
        vals = sorted(vals, key=lambda r: float(r["time_s"]))
        ax.plot([float(v["time_s"]) for v in vals], [float(v[y]) for v in vals], label=group)
    ax.set_title(title)
    ax.set_xlabel("time [s]")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / f"{name}.png", dpi=180)
    fig.savefig(FIGDIR / f"{name}.svg")
    plt.close(fig)


def make_figures(results: list[dict[str, object]]) -> None:
    FIGDIR.mkdir(exist_ok=True)
    pressure = [row for res in results for row in res.get("pressure", [])]
    boundary = [row for res in results for row in res.get("boundary", [])]
    stability = [row for res in results for row in res.get("stability", [])]
    profiles = [row for res in results for row in res.get("profiles", [])]
    plot_series(pressure, "bottom_excess", "Bottom excess pressure", "bnd1_bottom_excess", "Pa")
    plot_series(pressure, "profile_rmse", "Profile RMSE", "bnd1_profile_rmse", "Pa")
    plot_series(boundary, "top_drained_residual", "Top drained residual", "bnd1_top_residual", "Pa")
    plot_series(boundary, "bottom_noflux_proxy", "Bottom no-flux proxy", "bnd1_bottom_noflux", "Pa")
    plot_series(boundary, "lateral_noflux_proxy", "Lateral wall no-flux proxy", "bnd1_lateral_noflux", "Pa")
    plot_series(stability, "velocity_max", "Velocity max", "bnd1_velocity_max", "m/s")
    plot_series(stability, "DivVel_maxAbs", "DivVel maxAbs", "bnd1_divvel", "1/s")
    plot_series(stability, "PorePressRate_maxAbs", "PorePressRate maxAbs", "bnd1_porepressrate", "Pa/s")
    summary = [res["metrics"] for res in results]
    if summary:
        labels = [str(row["case_id"]) for row in summary]
        for metric, name in [("bottom_rmse", "bnd1_bottom_rmse"), ("final_profile_rmse", "bnd1_final_profile_rmse")]:
            fig, ax = plt.subplots(figsize=(7.0, 4.0))
            ax.bar(labels, [float(row.get(metric, 0) or 0) for row in summary])
            ax.set_title(metric)
            ax.set_ylabel("Pa")
            ax.tick_params(axis="x", rotation=20)
            fig.tight_layout()
            fig.savefig(FIGDIR / f"{name}.png", dpi=180)
            fig.savefig(FIGDIR / f"{name}.svg")
            plt.close(fig)
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        ordinary = [float(row.get("ordinary_solid_noflux_pairs", 0) or 0) for row in summary]
        bottom = [float(row.get("bottom_noflux_pairs", 0) or 0) for row in summary]
        drained = [float(row.get("drained_pairs", 0) or 0) for row in summary]
        ax.bar(labels, ordinary, label="ordinary solid no-flux")
        ax.bar(labels, bottom, bottom=ordinary, label="bottom no-flux")
        ax.bar(labels, drained, bottom=[ordinary[i] + bottom[i] for i in range(len(labels))], label="drained")
        ax.set_title("Boundary contribution counts")
        ax.set_ylabel("pairs")
        ax.tick_params(axis="x", rotation=20)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(FIGDIR / "bnd1_boundary_contribution_counts.png", dpi=180)
        fig.savefig(FIGDIR / "bnd1_boundary_contribution_counts.svg")
        plt.close(fig)
    if profiles:
        fig, ax = plt.subplots(figsize=(6.5, 5.5))
        grouped: dict[tuple[str, float], list[dict[str, object]]] = {}
        for row in profiles:
            grouped.setdefault((str(row["case_id"]), float(row["time_s"])), []).append(row)
        for (case_id, time_s), vals in sorted(grouped.items()):
            vals = sorted(vals, key=lambda r: float(r["z_m"]))
            ax.plot([float(v["excess"]) for v in vals], [float(v["z_m"]) for v in vals], label=f"{case_id} {time_s:.3f}s")
        ax.set_title("BND1 excess profiles")
        ax.set_xlabel("excess pore pressure [Pa]")
        ax.set_ylabel("z [m]")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=6)
        fig.tight_layout()
        fig.savefig(FIGDIR / "bnd1_excess_profiles.png", dpi=180)
        fig.savefig(FIGDIR / "bnd1_excess_profiles.svg")
        plt.close(fig)


def main() -> None:
    results = [analyze_case(*case) for case in CASES]
    summary = [res["metrics"] for res in results]
    pressure = [row for res in results for row in res.get("pressure", [])]
    boundary = [row for res in results for row in res.get("boundary", [])]
    stability = [row for res in results for row in res.get("stability", [])]
    profiles = [row for res in results for row in res.get("profiles", [])]
    summary_fields = [
        "case_id",
        "route",
        "operator",
        "feedback",
        "status",
        "code",
        "excluded",
        "dtmin_adjustments",
        "runtime_s",
        "steps",
        "frames",
        "final_time_s",
        "p_w0",
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
        "normals_used",
        "mls_samples",
        "mls_fallback",
        "reconstructed_excess_min",
        "reconstructed_excess_max",
        "peak_abs_excess",
        "min_excess",
        "bottom_rmse",
        "final_profile_rmse",
        "top_drained_residual_final",
        "bottom_noflux_proxy_final",
        "lateral_noflux_proxy_final",
        "velocity_max",
        "DivVel_maxAbs",
        "PorePressRate_maxAbs",
        "feedback_accel_max",
        "monotonic_volume_mean_violations",
    ]
    write_csv(ROOT / "bnd1_case_summary.csv", summary, summary_fields)
    write_csv(ROOT / "bnd1_boundary_diagnostics.csv", summary, summary_fields[:29])
    write_csv(
        ROOT / "bnd1_operator_comparison_metrics.csv",
        summary,
        ["case_id", "route", "operator", "bottom_rmse", "final_profile_rmse", "top_drained_residual_final", "bottom_noflux_proxy_final", "lateral_noflux_proxy_final", "peak_abs_excess"],
    )
    write_csv(
        ROOT / "bnd1_analytical_profile_metrics.csv",
        pressure,
        ["case_id", "time_s", "Tv", "volume_mean_excess", "peak_abs_excess", "bottom_excess", "analytical_bottom_excess", "bottom_error", "profile_rmse"],
    )
    write_csv(
        ROOT / "bnd1_feedback_stability_metrics.csv",
        stability,
        ["case_id", "time_s", "velocity_max", "DivVel_maxAbs", "PorePressRate_maxAbs", "feedback_accel_max", "negative_excess_min"],
    )
    write_csv(
        ROOT / "bnd1_lateral_wall_no_flux_metrics.csv",
        boundary,
        ["case_id", "time_s", "top_drained_residual", "bottom_noflux_proxy", "lateral_noflux_proxy"],
    )
    write_csv(ROOT / "bnd1_analytical_profiles.csv", profiles, ["case_id", "time_s", "z_m", "excess", "analytical_excess"])
    make_figures(results)
    print("Wrote BND1 metrics and figures.")


if __name__ == "__main__":
    main()
