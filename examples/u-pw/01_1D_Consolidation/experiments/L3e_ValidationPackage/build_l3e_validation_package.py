#!/usr/bin/env python3
"""Build the L3e 1D consolidation validation package from retained CSVs."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
EXP = ROOT.parent
FIGDIR = ROOT / "figures"

SRC = {
    "L1": EXP / "ExternalLoad_L1_Baseline",
    "L2": EXP / "ExternalLoad_L2_PaperAligned",
    "L3a": EXP / "ExternalLoad_L3_InitialPressureGate",
    "L3b": EXP / "ExternalLoad_L3b_MechanicalTopLoad",
    "L3c": EXP / "ExternalLoad_L3c_ConsistentInitialState",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.is_dir():
        return []
    with path.open(newline="", errors="ignore") as fp:
        return list(csv.DictReader(fp))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        val = row.get(key, "")
        return float(val) if val not in ("", None) else default
    except ValueError:
        return default


def s(row: dict[str, str], key: str, default: str = "") -> str:
    return str(row.get(key, default) if row.get(key, default) is not None else default)


def first(rows: list[dict[str, str]], run: str | None = None) -> dict[str, str]:
    if not rows:
        return {}
    if run is None:
        return rows[0]
    for row in rows:
        if row.get("run") == run:
            return row
    return rows[0]


CASES = [
    {
        "stage": "L1",
        "case": "L1 external-load baseline",
        "category": "B stable reduced smoke",
        "role": "early external-load smoke; not paper-aligned",
        "summary": "l1_external_load_case_summary.csv",
        "accinput": "yes",
        "mechanical_top_load": "no",
        "pore_pressure_init": "0 or baseline XML route",
        "initial_stress": "none",
        "feedback": "not strict validation route",
        "cpu_support": "yes",
        "gpu_support": "smoke reported earlier, not part of L3e strict figure",
        "validation_ready": "no",
    },
    {
        "stage": "L2",
        "case": "L2 paper-aligned AccInput",
        "category": "B stable reduced smoke",
        "role": "paper constants with AccInput body acceleration",
        "summary": "l2_case_summary.csv",
        "bottom": "l2_bottom_pressure_metrics.csv",
        "boundary": "l2_boundary_metrics.csv",
        "profile": "l2_profile_metrics.csv",
        "accinput": "yes",
        "mechanical_top_load": "no",
        "pore_pressure_init": "not load-generated initial-state gate",
        "initial_stress": "none",
        "feedback": "0",
        "cpu_support": "yes",
        "gpu_support": "yes",
        "validation_ready": "no",
    },
    {
        "stage": "L3a",
        "case": "L3a initial-pressure diffusion gate",
        "category": "A validation-ready paper-compatible gate",
        "role": "PR diffusion and boundary gate",
        "summary": "l3a_case_summary.csv",
        "bottom": "l3a_bottom_pressure_metrics.csv",
        "boundary": "l3a_boundary_metrics.csv",
        "profile": "l3a_profile_metrics.csv",
        "profiles": "l3a_analytical_profiles.csv",
        "accinput": "no",
        "mechanical_top_load": "no",
        "pore_pressure_init": "PorePressureInit=3, uniform 10 kPa",
        "initial_stress": "none",
        "feedback": "0",
        "cpu_support": "yes",
        "gpu_support": "yes",
        "validation_ready": "yes, diffusion/boundary gate only",
    },
    {
        "stage": "L3b",
        "case": "L3b mechanical top-load material force",
        "category": "B stable reduced smoke",
        "role": "CPU source-backed top material force diagnostic",
        "summary": "l3b_case_summary.csv",
        "bottom": "l3b_bottom_pressure_metrics.csv",
        "boundary": "l3b_boundary_metrics.csv",
        "profile": "l3b_analytical_profile_metrics.csv",
        "accinput": "no",
        "mechanical_top_load": "yes",
        "pore_pressure_init": "not initial-state gate",
        "initial_stress": "none",
        "feedback": "0",
        "cpu_support": "yes",
        "gpu_support": "deferred; MechanicalTopLoad is CPU-only",
        "validation_ready": "no",
    },
    {
        "stage": "L3c",
        "case": "L3c consistent initial-state gate",
        "category": "A validation-ready paper-compatible gate",
        "role": "Terzaghi p_w0=|q0| gate with zero effective-stress increment",
        "summary": "l3c_case_summary.csv",
        "bottom": "l3c_bottom_pressure_metrics.csv",
        "boundary": "l3c_boundary_metrics.csv",
        "profile": "l3c_analytical_profile_metrics.csv",
        "profiles": "l3c_analytical_profiles.csv",
        "accinput": "no",
        "mechanical_top_load": "no",
        "pore_pressure_init": "PorePressureInit=3, uniform 10 kPa",
        "initial_stress": "InitialStressMode=0",
        "feedback": "0",
        "cpu_support": "yes",
        "gpu_support": "yes",
        "validation_ready": "yes, diffusion/initial-state gate only",
    },
]


def load_stage(case: dict[str, str]) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    base = SRC[case["stage"]]
    return (
        read_csv(base / case.get("summary", "")),
        read_csv(base / case.get("bottom", "")),
        read_csv(base / case.get("boundary", "")),
        read_csv(base / case.get("profile", "")),
    )


def build_tables() -> dict[str, list[dict[str, object]]]:
    inventory = []
    summary_rows = []
    error_rows = []
    boundary_rows = []
    loading_rows = []
    cpu_gpu_rows = []

    for case in CASES:
        summaries, bottom, boundary, profile = load_stage(case)
        runs = summaries or [{}]
        inventory.append({
            "stage": case["stage"],
            "case": case["case"],
            "category": case["category"],
            "role": case["role"],
            "cpu_support": case["cpu_support"],
            "gpu_support": case["gpu_support"],
            "validation_ready": case["validation_ready"],
            "path": str(SRC[case["stage"]].relative_to(EXP)),
        })
        loading_rows.append({
            "stage": case["stage"],
            "case": case["case"],
            "category": case["category"],
            "uses_AccInput": case["accinput"],
            "uses_MechanicalTopLoad": case["mechanical_top_load"],
            "pore_pressure_init": case["pore_pressure_init"],
            "initial_stress": case["initial_stress"],
            "PorePressureFeedback": case["feedback"],
            "classification": case["validation_ready"],
            "reason": case["role"],
        })
        for row in runs:
            run = s(row, "run", "cpu" if case["stage"] in ("L1", "L3b") else "unknown")
            summary_rows.append({
                "stage": case["stage"],
                "case": case["case"],
                "run": run,
                "category": case["category"],
                "code": s(row, "code", "missing"),
                "excluded": s(row, "excluded", "missing"),
                "DtMin": s(row, "dtmin_adjustments", "0"),
                "TimeMax_s": row.get("TimeMax_s", row.get("physical_time_s", "")),
                "loading_route": s(row, "load_route", case["role"]),
                "peak_excess_maxAbs_Pa": row.get("peak_excess_maxAbs_Pa", ""),
                "bottom_rmse_q0_Pa": row.get("bottom_rmse_q0_Pa", ""),
                "profile_rmse_q0_Pa": row.get("profile_rmse_q0_Pa", ""),
                "top_drained_residual_Pa": row.get("final_top_drained_excess_maxAbs_Pa", ""),
                "bottom_no_flux_proxy_Pa": row.get("final_bottom_no_flux_proxy_Pa", ""),
                "velocity_max_mps": row.get("final_velocity_max_mps", ""),
                "validation_ready": case["validation_ready"],
            })
            error_rows.append({
                "stage": case["stage"],
                "case": case["case"],
                "run": run,
                "peak_excess_maxAbs_Pa": row.get("peak_excess_maxAbs_Pa", ""),
                "bottom_rmse_q0_Pa": row.get("bottom_rmse_q0_Pa", ""),
                "profile_rmse_q0_Pa": row.get("profile_rmse_q0_Pa", ""),
                "final_bottom_excess_mean_Pa": row.get("final_bottom_excess_mean_Pa", ""),
                "final_excess_maxAbs_Pa": row.get("final_excess_maxAbs_Pa", ""),
                "route_class": case["category"],
            })
            boundary_rows.append({
                "stage": case["stage"],
                "case": case["case"],
                "run": run,
                "top_drained_residual_Pa": row.get("final_top_drained_excess_maxAbs_Pa", ""),
                "bottom_no_flux_proxy_Pa": row.get("final_bottom_no_flux_proxy_Pa", ""),
                "velocity_max_mps": row.get("final_velocity_max_mps", ""),
                "DivVel_indicator": final_metric(boundary, run, "DivVel_maxAbs"),
                "PorePressRate_indicator": final_metric(boundary, run, "PorePressRate_maxAbs"),
            })
        if len(summaries) >= 2:
            cpu = first(summaries, "cpu")
            gpu = first(summaries, "gpu")
            cpu_gpu_rows.append({
                "stage": case["stage"],
                "case": case["case"],
                "cpu_code": cpu.get("code", ""),
                "gpu_code": gpu.get("code", ""),
                "cpu_peak_excess_Pa": cpu.get("peak_excess_maxAbs_Pa", ""),
                "gpu_peak_excess_Pa": gpu.get("peak_excess_maxAbs_Pa", ""),
                "peak_abs_diff_Pa": abs(f(cpu, "peak_excess_maxAbs_Pa") - f(gpu, "peak_excess_maxAbs_Pa")),
                "cpu_bottom_rmse_Pa": cpu.get("bottom_rmse_q0_Pa", ""),
                "gpu_bottom_rmse_Pa": gpu.get("bottom_rmse_q0_Pa", ""),
                "bottom_rmse_abs_diff_Pa": abs(f(cpu, "bottom_rmse_q0_Pa") - f(gpu, "bottom_rmse_q0_Pa")),
                "cpu_profile_rmse_Pa": cpu.get("profile_rmse_q0_Pa", ""),
                "gpu_profile_rmse_Pa": gpu.get("profile_rmse_q0_Pa", ""),
                "profile_rmse_abs_diff_Pa": abs(f(cpu, "profile_rmse_q0_Pa") - f(gpu, "profile_rmse_q0_Pa")),
            })

    return {
        "inventory": inventory,
        "summary": summary_rows,
        "errors": error_rows,
        "boundary": boundary_rows,
        "loading": loading_rows,
        "cpu_gpu": cpu_gpu_rows,
    }


def final_metric(rows: list[dict[str, str]], run: str, key: str) -> str:
    if not rows:
        return ""
    matches = [r for r in rows if r.get("run") == run]
    if not matches:
        matches = rows
    return matches[-1].get(key, "")


def bottom_rows(stage: str, run: str = "cpu") -> list[dict[str, str]]:
    case = next(c for c in CASES if c["stage"] == stage)
    rows = read_csv(SRC[stage] / case.get("bottom", ""))
    if not rows:
        return []
    matches = [r for r in rows if r.get("run", "cpu") == run]
    return matches if matches else rows


def plot_bottom_excess() -> None:
    FIGDIR.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.0, 4.3))
    for stage, label, style in [
        ("L2", "L2 AccInput CPU", "-"),
        ("L3a", "L3a initial pressure CPU", "-"),
        ("L3b", "L3b material force CPU", "-"),
        ("L3c", "L3c consistent initial state CPU", "-"),
    ]:
        rows = bottom_rows(stage, "cpu")
        if not rows:
            continue
        ax.plot([f(r, "time_s") for r in rows], [f(r, "bottom_excess_mean") for r in rows], style, marker="o", markersize=2, label=label)
    ref = bottom_rows("L3c", "cpu")
    if ref:
        ax.plot([f(r, "time_s") for r in ref], [f(r, "analytical_q0_bottom") for r in ref], "k--", linewidth=1.2, label="Terzaghi q0")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Bottom excess pressure [Pa]")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3e_bottom_excess_routes_vs_analytical.svg")
    fig.savefig(FIGDIR / "l3e_bottom_excess_routes_vs_analytical.png", dpi=180)
    plt.close(fig)


def plot_l3c_profiles() -> None:
    profiles = read_csv(SRC["L3c"] / "l3c_analytical_profiles.csv")
    if not profiles:
        return
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    rows = [r for r in profiles if r.get("run") == "cpu"]
    times = sorted({f(r, "time_s") for r in rows})
    for t in times:
        if t not in (0.0, 0.001, 0.005, 0.01, 0.02):
            continue
        rs = [r for r in rows if abs(f(r, "time_s") - t) < 1e-12]
        ax.plot([f(r, "sim_excess") for r in rs], [f(r, "z_m") for r in rs], marker="o", markersize=2, label=f"L3c t={t:g}s")
        ax.plot([f(r, "analytical_excess_q0") for r in rs], [f(r, "z_m") for r in rs], linestyle="--", color=ax.lines[-1].get_color())
    ax.set_xlabel("Excess pore pressure [Pa]")
    ax.set_ylabel("z [m]")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3e_l3c_profiles_vs_analytical.svg")
    fig.savefig(FIGDIR / "l3e_l3c_profiles_vs_analytical.png", dpi=180)
    plt.close(fig)


def plot_bar_metrics(table: list[dict[str, object]]) -> None:
    cpu = [r for r in table if str(r.get("run")) in ("cpu", "unknown") and r.get("stage") != "L1"]
    labels = [str(r["stage"]) for r in cpu]
    peak = [float(r.get("peak_excess_maxAbs_Pa") or 0.0) for r in cpu]
    bottom = [float(r.get("bottom_rmse_q0_Pa") or 0.0) for r in cpu]
    profile = [float(r.get("profile_rmse_q0_Pa") or 0.0) for r in cpu]
    x = list(range(len(cpu)))

    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    ax.bar([i - 0.25 for i in x], peak, width=0.25, label="peak excess")
    ax.bar(x, bottom, width=0.25, label="bottom RMSE")
    ax.bar([i + 0.25 for i in x], profile, width=0.25, label="profile RMSE")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Pressure [Pa]")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3e_error_peak_comparison.svg")
    fig.savefig(FIGDIR / "l3e_error_peak_comparison.png", dpi=180)
    plt.close(fig)


def plot_boundary(table: list[dict[str, object]]) -> None:
    rows = [r for r in table if str(r.get("run")) in ("cpu", "unknown")]
    labels = [str(r["stage"]) for r in rows]
    top = [abs(float(r.get("top_drained_residual_Pa") or 0.0)) for r in rows]
    bottom = [abs(float(r.get("bottom_no_flux_proxy_Pa") or 0.0)) for r in rows]
    x = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    ax.bar([i - 0.18 for i in x], top, width=0.36, label="top drained residual")
    ax.bar([i + 0.18 for i in x], bottom, width=0.36, label="bottom no-flux proxy")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Boundary residual [Pa]")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3e_boundary_residual_comparison.svg")
    fig.savefig(FIGDIR / "l3e_boundary_residual_comparison.png", dpi=180)
    plt.close(fig)


def plot_cpu_gpu(cpu_gpu: list[dict[str, object]]) -> None:
    if not cpu_gpu:
        return
    labels = [str(r["stage"]) for r in cpu_gpu]
    peak = [float(r.get("peak_abs_diff_Pa") or 0.0) for r in cpu_gpu]
    bottom = [float(r.get("bottom_rmse_abs_diff_Pa") or 0.0) for r in cpu_gpu]
    profile = [float(r.get("profile_rmse_abs_diff_Pa") or 0.0) for r in cpu_gpu]
    x = list(range(len(cpu_gpu)))
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    ax.bar([i - 0.25 for i in x], peak, width=0.25, label="peak diff")
    ax.bar(x, bottom, width=0.25, label="bottom RMSE diff")
    ax.bar([i + 0.25 for i in x], profile, width=0.25, label="profile RMSE diff")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("CPU/GPU absolute difference [Pa]")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3e_cpu_gpu_parity.svg")
    fig.savefig(FIGDIR / "l3e_cpu_gpu_parity.png", dpi=180)
    plt.close(fig)


def plot_velocity_diagnostics() -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    for stage, label in [("L2", "L2 AccInput"), ("L3a", "L3a"), ("L3b", "L3b"), ("L3c", "L3c")]:
        case = next(c for c in CASES if c["stage"] == stage)
        rows = read_csv(SRC[stage] / case.get("boundary", ""))
        rows = [r for r in rows if r.get("run", "cpu") == "cpu"] or rows
        if not rows:
            continue
        key = "velocity_max" if "velocity_max" in rows[0] else "velocity_max_mps"
        ax.plot([f(r, "time_s") for r in rows], [f(r, key) for r in rows], marker="o", markersize=2, label=label)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Velocity max [m/s]")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3e_velocity_diagnostics.svg")
    fig.savefig(FIGDIR / "l3e_velocity_diagnostics.png", dpi=180)
    plt.close(fig)


def plot_route_schematic() -> None:
    fig, ax = plt.subplots(figsize=(8.0, 3.4))
    ax.axis("off")
    boxes = [
        ("L2 AccInput", "body acceleration\non top material layer\nstable but dynamic"),
        ("L3b force on material", "F=q0*A applied to\ntop material row\nstill dynamic"),
        ("L3a/L3c initial state", "p_w0=|q0|\nno force impulse\nvalidation gate"),
        ("L3d deferred", "quasi-static plate\nor total-stress initializer"),
    ]
    for i, (title, body) in enumerate(boxes):
        x0 = 0.04 + i * 0.24
        ax.add_patch(plt.Rectangle((x0, 0.28), 0.2, 0.48, fill=False, linewidth=1.2))
        ax.text(x0 + 0.1, 0.66, title, ha="center", va="center", fontsize=10, weight="bold")
        ax.text(x0 + 0.1, 0.45, body, ha="center", va="center", fontsize=8)
        if i < len(boxes) - 1:
            ax.annotate("", xy=(x0 + 0.23, 0.52), xytext=(x0 + 0.205, 0.52), arrowprops={"arrowstyle": "->", "lw": 1.2})
    ax.text(0.5, 0.08, "L3e classification: use L3c for PR diffusion/boundary validation; defer strict mechanical load generation.", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3e_loading_route_schematic.svg")
    fig.savefig(FIGDIR / "l3e_loading_route_schematic.png", dpi=180)
    plt.close(fig)


def main() -> None:
    FIGDIR.mkdir(exist_ok=True)
    tables = build_tables()
    write_csv(ROOT / "l3e_case_inventory.csv", tables["inventory"])
    write_csv(ROOT / "l3e_summary_metrics.csv", tables["summary"])
    write_csv(ROOT / "l3e_analytical_error_comparison.csv", tables["errors"])
    write_csv(ROOT / "l3e_boundary_metrics_comparison.csv", tables["boundary"])
    write_csv(ROOT / "l3e_loading_route_comparison.csv", tables["loading"])
    write_csv(ROOT / "l3e_cpu_gpu_comparison.csv", tables["cpu_gpu"])
    plot_bottom_excess()
    plot_l3c_profiles()
    plot_bar_metrics(tables["summary"])
    plot_boundary(tables["boundary"])
    plot_cpu_gpu(tables["cpu_gpu"])
    plot_velocity_diagnostics()
    plot_route_schematic()
    print("Wrote L3e validation package CSV and figures.")


if __name__ == "__main__":
    main()
