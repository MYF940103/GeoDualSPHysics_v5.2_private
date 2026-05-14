#!/usr/bin/env python3
"""Postprocess L5 feedback-on 1D consolidation gate outputs."""

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
    ("low_cpu", "Case1DConsolidation_PR_FeedbackOn_L5_LowAmp", "cpu"),
    ("target_cpu", "Case1DConsolidation_PR_FeedbackOn_L5_TargetAmp", "cpu"),
    ("target_gpu", "Case1DConsolidation_PR_FeedbackOn_L5_TargetAmp", "gpu"),
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


def run_info(outdir: Path) -> dict[str, str]:
    text = (outdir / "Run.out").read_text(errors="ignore") if (outdir / "Run.out").exists() else ""
    def find(pattern: str, default: str = "") -> str:
        m = re.search(pattern, text)
        return m.group(1) if m else default
    return {
        "code": find(r"Finished execution \(code=([0-9-]+)\)", "missing"),
        "excluded": find(r"Excluded particles\.+:\s+(\d+)", "missing"),
        "dtmin_adjustments": find(r"DTs adjusted to DtMin\.+:\s+(\d+)", ""),
        "runtime_s": find(r"Total Runtime\.+:\s+([0-9.Ee+-]+)", ""),
        "steps": find(r"Steps of simulation\.+:\s+(\d+)", ""),
    }


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="") as fp:
        wr = csv.DictWriter(fp, fieldnames=fields)
        wr.writeheader()
        for row in rows:
            wr.writerow({field: row.get(field, "") for field in fields})


def analyze_case(case_id: str, case: str, kind: str) -> dict[str, object]:
    time_out = xml_value(case, "TimeOut", 0.001)
    amp = xml_value(case, "PorePressureExcessAmp", 10000.0)
    feedback_mode = int(xml_value(case, "PorePressureFeedbackMode", 0))
    feedback_operator = int(xml_value(case, "PorePressureFeedbackOperator", 0))
    outdir = ROOT / f"{case}_{kind}_out"
    paths = sorted((outdir / "data").glob("PartCsv_*.csv"), key=frame_index) if (outdir / "data").exists() else []
    info = run_info(outdir)
    if not paths:
        return {"case_id": case_id, "kind": kind, "status": "missing_output", **info}

    pressure_rows: list[dict[str, object]] = []
    boundary_rows: list[dict[str, object]] = []
    feedback_rows: list[dict[str, object]] = []
    stability_rows: list[dict[str, object]] = []
    profile_rows: list[dict[str, object]] = []
    bottom_errors: list[float] = []
    peak = 0.0
    min_excess = 0.0
    vel_max = div_max = rate_max = accel_max = 0.0
    final_profile_rmse = top_final = bottom_final = 0.0
    monotonic_violations = 0
    last_vol_mean: float | None = None
    selected = {0, max(0, len(paths) // 4), max(0, len(paths) // 2), len(paths) - 1}

    for idx, path in enumerate(paths):
        time_s = frame_index(path) * time_out
        rows = [r for r in read_partcsv(path) if is_material(r)]
        z_vals = [float(r["Pos.z [m]"]) for r in rows]
        zmin, zmax = min(z_vals), max(z_vals)
        h = max(zmax - zmin, 1e-12)
        excess = [float(r["ExcessPorePress"]) for r in rows]
        vel = [math.sqrt(float(r["Vel.x [m/s]"]) ** 2 + float(r["Vel.y [m/s]"]) ** 2 + float(r["Vel.z [m/s]"]) ** 2) for r in rows]
        div = [float(r["DivVel"]) for r in rows]
        rate = [float(r["PorePressRate"]) for r in rows]
        acc = [
            math.sqrt(float(r["PorePressureAccelDiff.x"]) ** 2 + float(r["PorePressureAccelDiff.y"]) ** 2 + float(r["PorePressureAccelDiff.z"]) ** 2)
            for r in rows
        ]
        top_rows = [r for r in rows if float(r["Pos.z [m]"]) >= zmax - 2 * DP - 1e-12]
        bottom_rows = [r for r in rows if float(r["Pos.z [m]"]) <= zmin + 2 * DP + 1e-12]
        ref_rows = [r for r in rows if zmin + 2 * DP < float(r["Pos.z [m]"]) <= zmin + 4 * DP + 1e-12]
        top_resid = maxabs(float(r["ExcessPorePress"]) for r in top_rows)
        bottom_mean = mean(float(r["ExcessPorePress"]) for r in bottom_rows)
        ref_mean = mean(float(r["ExcessPorePress"]) for r in ref_rows)
        bottom_noflux = bottom_mean - ref_mean
        bottom_depth = zmax - mean(float(r["Pos.z [m]"]) for r in bottom_rows)
        ana_bottom = terzaghi_excess(bottom_depth, time_s, h, amp)
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
        pressure_rows.append({"case_id": case_id, "time_s": time_s, "Tv": CV * time_s / (h * h), "volume_mean_excess": vol_mean, "peak_abs_excess": maxabs(excess), "min_excess": min(excess), "bottom_excess": bottom_mean, "analytical_bottom_excess": ana_bottom, "bottom_error": bottom_mean - ana_bottom, "profile_rmse": profile_rmse})
        boundary_rows.append({"case_id": case_id, "time_s": time_s, "top_drained_residual": top_resid, "bottom_noflux_proxy": bottom_noflux})
        feedback_rows.append({"case_id": case_id, "time_s": time_s, "feedback_accel_max": maxabs(acc), "feedback_accel_mean": mean(acc)})
        stability_rows.append({"case_id": case_id, "time_s": time_s, "velocity_max": maxabs(vel), "DivVel_maxAbs": maxabs(div), "PorePressRate_maxAbs": maxabs(rate), "negative_excess_min": min(excess)})
        if idx == len(paths) - 1:
            final_profile_rmse, top_final, bottom_final = profile_rmse, top_resid, bottom_noflux

    metrics = {
        "case_id": case_id,
        "kind": kind,
        "status": "ok",
        **info,
        "frames": len(paths),
        "final_time_s": frame_index(paths[-1]) * time_out,
        "p_w0": amp,
        "feedback_mode": feedback_mode,
        "feedback_operator": feedback_operator,
        "peak_abs_excess": peak,
        "min_excess": min_excess,
        "bottom_rmse": rmse(bottom_errors),
        "final_profile_rmse": final_profile_rmse,
        "top_drained_residual_final": top_final,
        "bottom_noflux_proxy_final": bottom_final,
        "velocity_max": vel_max,
        "DivVel_maxAbs": div_max,
        "PorePressRate_maxAbs": rate_max,
        "feedback_accel_max": accel_max,
        "monotonic_volume_mean_violations": monotonic_violations,
    }
    return {"metrics": metrics, "pressure": pressure_rows, "boundary": boundary_rows, "feedback": feedback_rows, "stability": stability_rows, "profiles": profile_rows}


def plot_series(rows: list[dict[str, object]], y: str, title: str, name: str, ylabel: str) -> None:
    if not rows:
        return
    groups: dict[str, list[dict[str, object]]] = {}
    for r in rows:
        groups.setdefault(str(r["case_id"]), []).append(r)
    fig, ax = plt.subplots(figsize=(7, 4.5))
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
    pressure = [r for res in results for r in res.get("pressure", [])]
    boundary = [r for res in results for r in res.get("boundary", [])]
    feedback = [r for res in results for r in res.get("feedback", [])]
    stability = [r for res in results for r in res.get("stability", [])]
    profiles = [r for res in results for r in res.get("profiles", []) if r.get("case_id") in ("target_cpu", "target_gpu")]
    plot_series(pressure, "bottom_excess", "Bottom excess pressure", "l5_bottom_excess", "Pa")
    plot_series(pressure, "analytical_bottom_excess", "Analytical bottom excess pressure", "l5_analytical_bottom_excess", "Pa")
    plot_series(pressure, "volume_mean_excess", "Volume mean excess pressure", "l5_volume_mean_excess", "Pa")
    plot_series(boundary, "top_drained_residual", "Top drained residual", "l5_top_residual", "Pa")
    plot_series(boundary, "bottom_noflux_proxy", "Bottom no-flux proxy", "l5_bottom_noflux", "Pa")
    plot_series(feedback, "feedback_accel_max", "Feedback acceleration max", "l5_feedback_accel", "m/s2")
    plot_series(stability, "velocity_max", "Velocity max", "l5_velocity_max", "m/s")
    plot_series(stability, "DivVel_maxAbs", "DivVel maxAbs", "l5_divvel", "1/s")
    plot_series(stability, "PorePressRate_maxAbs", "PorePressRate maxAbs", "l5_porepressrate", "Pa/s")
    if profiles:
        fig, ax = plt.subplots(figsize=(6.5, 5.5))
        grouped: dict[tuple[str, float], list[dict[str, object]]] = {}
        for r in profiles:
            grouped.setdefault((str(r["case_id"]), float(r["time_s"])), []).append(r)
        for (case_id, t), vals in sorted(grouped.items()):
            vals = sorted(vals, key=lambda r: float(r["z_m"]))
            ax.plot([float(v["excess"]) for v in vals], [float(v["z_m"]) for v in vals], label=f"{case_id} {t:.3f}s")
            ax.plot([float(v["analytical_excess"]) for v in vals], [float(v["z_m"]) for v in vals], "--", color=ax.lines[-1].get_color(), alpha=0.55)
        ax.set_title("Excess profiles: solid=L5, dashed=Terzaghi")
        ax.set_xlabel("excess pore pressure [Pa]")
        ax.set_ylabel("z [m]")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(FIGDIR / "l5_excess_profiles_vs_terzaghi.png", dpi=180)
        fig.savefig(FIGDIR / "l5_excess_profiles_vs_terzaghi.svg")
        plt.close(fig)
    summary = [r["metrics"] for r in results if r.get("metrics")]
    if summary:
        fig, ax = plt.subplots(figsize=(6.5, 4.0))
        labels = [str(r["case_id"]) for r in summary]
        peaks = [float(r["peak_abs_excess"]) for r in summary]
        ax.bar(labels, peaks)
        ax.axhline(10000, color="crimson", linestyle="--", label="10 kPa target")
        ax.set_ylabel("peak |excess| [Pa]")
        ax.set_title("L5 peak excess pressure")
        ax.legend()
        fig.tight_layout()
        fig.savefig(FIGDIR / "l5_peak_excess_comparison.png", dpi=180)
        fig.savefig(FIGDIR / "l5_peak_excess_comparison.svg")
        plt.close(fig)


def main() -> None:
    results = [analyze_case(*case) for case in CASES]
    summary = [r["metrics"] if "metrics" in r else r for r in results]
    pressure = [row for r in results for row in r.get("pressure", [])]
    boundary = [row for r in results for row in r.get("boundary", [])]
    feedback = [row for r in results for row in r.get("feedback", [])]
    stability = [row for r in results for row in r.get("stability", [])]
    profiles = [row for r in results for row in r.get("profiles", [])]
    write_csv(ROOT / "l5_case_summary.csv", summary, ["case_id", "kind", "status", "code", "excluded", "dtmin_adjustments", "runtime_s", "steps", "frames", "final_time_s", "p_w0", "feedback_mode", "feedback_operator", "peak_abs_excess", "min_excess", "bottom_rmse", "final_profile_rmse", "top_drained_residual_final", "bottom_noflux_proxy_final", "velocity_max", "DivVel_maxAbs", "PorePressRate_maxAbs", "feedback_accel_max", "monotonic_volume_mean_violations"])
    write_csv(ROOT / "l5_pressure_metrics.csv", pressure, ["case_id", "time_s", "Tv", "volume_mean_excess", "peak_abs_excess", "min_excess", "bottom_excess", "analytical_bottom_excess", "bottom_error", "profile_rmse"])
    write_csv(ROOT / "l5_boundary_metrics.csv", boundary, ["case_id", "time_s", "top_drained_residual", "bottom_noflux_proxy"])
    write_csv(ROOT / "l5_feedback_diagnostics.csv", feedback, ["case_id", "time_s", "feedback_accel_max", "feedback_accel_mean"])
    write_csv(ROOT / "l5_stability_metrics.csv", stability, ["case_id", "time_s", "velocity_max", "DivVel_maxAbs", "PorePressRate_maxAbs", "negative_excess_min"])
    write_csv(ROOT / "l5_analytical_profiles.csv", profiles, ["case_id", "time_s", "z_m", "excess", "analytical_excess"])
    by_id = {str(r["case_id"]): r for r in summary if r.get("status") == "ok"}
    parity = []
    if "target_cpu" in by_id and "target_gpu" in by_id:
        for metric in ("peak_abs_excess", "bottom_rmse", "final_profile_rmse", "top_drained_residual_final", "bottom_noflux_proxy_final", "velocity_max", "DivVel_maxAbs", "PorePressRate_maxAbs", "feedback_accel_max"):
            parity.append({"metric": metric, "cpu": by_id["target_cpu"][metric], "gpu": by_id["target_gpu"][metric], "abs_diff": float(by_id["target_gpu"][metric]) - float(by_id["target_cpu"][metric])})
    write_csv(ROOT / "l5_cpu_gpu_parity.csv", parity, ["metric", "cpu", "gpu", "abs_diff"])
    comparison = []
    l3c = ROOT.parent / "ExternalLoad_L3c_ConsistentInitialState" / "l3c_case_summary.csv"
    if l3c.exists():
        comparison.append({"note": "See L3c summary for feedback-off reference", "path": str(l3c)})
    write_csv(ROOT / "l5_l3c_comparison.csv", comparison, ["note", "path"])
    make_figures(results)
    print("Wrote L5 feedback-on metrics and figures.")


if __name__ == "__main__":
    main()
