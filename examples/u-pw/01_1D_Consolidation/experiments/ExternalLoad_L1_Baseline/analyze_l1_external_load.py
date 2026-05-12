#!/usr/bin/env python3
"""Lightweight analysis for the L1 external-load 1D consolidation baseline."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


CASE = "Case1DConsolidation_PR_ExternalLoad_L1"
OUTDIR = Path(f"{CASE}_gpu_out")
DATADIR = OUTDIR / "data"
METRICS = Path("l1_external_load_frame_metrics.csv")
SUMMARY = Path("l1_external_load_case_summary.csv")
FIGDIR = Path("figures")

H = 0.018
RHO_W = 1000.0
G_H = 9.81
K = 1.0e-3


def clean_key(key: str) -> str:
    return key.strip()


def read_partcsv(path: Path):
    rows = []
    with path.open(newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for raw in reader:
            if not raw.get("Idp"):
                continue
            row = {clean_key(k): v for k, v in raw.items() if k is not None and clean_key(k)}
            try:
                row["Idp"] = int(row["Idp"])
                row["Type"] = int(float(row["Type"]))
            except Exception:
                continue
            for key in (
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
                "PorePressureAccelDiff.x",
                "PorePressureAccelDiff.y",
                "PorePressureAccelDiff.z",
            ):
                row[key] = float(row.get(key, "0") or 0)
            rows.append(row)
    return rows


def frame_time(path: Path) -> float:
    m = re.search(r"PartCsv_(\d+)\.csv$", path.name)
    idx = int(m.group(1)) if m else 0
    return 0.005 * idx


def maxabs(values):
    return max((abs(v) for v in values), default=0.0)


def mean(values):
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def load_run_info():
    info = {
        "code": "unknown",
        "excluded": "unknown",
        "runtime_s": "unknown",
        "steps": "unknown",
        "frames": "unknown",
    }
    runout = OUTDIR / "Run.out"
    if runout.exists():
        text = runout.read_text(errors="ignore")
        if "Finished execution (code=0)" in text:
            info["code"] = "0"
        m = re.search(r"Excluded particles\.+:\s+(\d+)", text)
        if m:
            info["excluded"] = m.group(1)
        m = re.search(r"Total Runtime\.+:\s+([0-9.Ee+-]+)", text)
        if m:
            info["runtime_s"] = m.group(1)
        m = re.search(r"Steps of simulation\.+:\s+(\d+)", text)
        if m:
            info["steps"] = m.group(1)
        m = re.search(r"PART files\.+:\s+(\d+)", text)
        if m:
            info["frames"] = m.group(1)
    return info


def write_csv(path: Path, rows, fieldnames):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    FIGDIR.mkdir(exist_ok=True)
    files = sorted(DATADIR.glob("PartCsv_*.csv"))
    if not files:
        raise SystemExit(f"No PartCsv files found under {DATADIR}")

    initial = [r for r in read_partcsv(files[0]) if r["Type"] == 3]
    z0_by_id = {r["Idp"]: r["Pos.z [m]"] for r in initial}

    frame_rows = []
    profiles = {}
    for path in files:
        t = frame_time(path)
        fluid = [r for r in read_partcsv(path) if r["Type"] == 3]
        if not fluid:
            continue
        zvals = [r["Pos.z [m]"] for r in fluid]
        zmin, zmax = min(zvals), max(zvals)
        top = [r for r in fluid if r["Pos.z [m]"] >= zmax - H]
        bottom = [r for r in fluid if r["Pos.z [m]"] <= zmin + H]
        ref = [r for r in fluid if zmin + H < r["Pos.z [m]"] <= zmin + 2 * H]
        velmag = [
            math.sqrt(r["Vel.x [m/s]"] ** 2 + r["Vel.y [m/s]"] ** 2 + r["Vel.z [m/s]"] ** 2)
            for r in fluid
        ]
        accdiff = [
            math.sqrt(
                r["PorePressureAccelDiff.x"] ** 2
                + r["PorePressureAccelDiff.y"] ** 2
                + r["PorePressureAccelDiff.z"] ** 2
            )
            for r in fluid
        ]
        hydro_contrib = [
            K / (RHO_W * G_H) * r["LapPorePress"] + K * r["LapZ"] for r in fluid
        ]
        settlement = mean(r["Pos.z [m]"] - z0_by_id.get(r["Idp"], r["Pos.z [m]"]) for r in fluid)
        bottom_excess = mean(r["ExcessPorePress"] for r in bottom)
        ref_excess = mean(r["ExcessPorePress"] for r in ref)
        row = {
            "time_s": f"{t:.6g}",
            "nfluid": len(fluid),
            "vel_max": f"{max(velmag):.9g}",
            "vel_mean": f"{mean(velmag):.9g}",
            "mean_settlement_m": f"{settlement:.9g}",
            "PorePress_max": f"{max(r['PorePress'] for r in fluid):.9g}",
            "PorePress_mean": f"{mean(r['PorePress'] for r in fluid):.9g}",
            "ExcessPorePress_maxAbs": f"{maxabs(r['ExcessPorePress'] for r in fluid):.9g}",
            "ExcessPorePress_mean": f"{mean(r['ExcessPorePress'] for r in fluid):.9g}",
            "bottom_excess_mean": f"{bottom_excess:.9g}",
            "top_drained_excess_maxAbs": f"{maxabs(r['ExcessPorePress'] for r in top):.9g}",
            "bottom_no_flux_proxy": f"{bottom_excess - ref_excess:.9g}",
            "PorePressRate_maxAbs": f"{maxabs(r['PorePressRate'] for r in fluid):.9g}",
            "DivVel_contribution_maxAbs": f"{maxabs(-r['DivVel'] for r in fluid):.9g}",
            "hydraulic_contribution_maxAbs": f"{maxabs(hydro_contrib):.9g}",
            "PorePressureAccelDiff_maxAbs": f"{max(accdiff):.9g}",
        }
        frame_rows.append(row)
        if min(abs(t - x) for x in (0.0, 0.05, 0.1, 0.2)) < 0.0026:
            profiles[round(t, 3)] = sorted(fluid, key=lambda r: r["Pos.z [m]"])

    fields = list(frame_rows[0].keys())
    write_csv(METRICS, frame_rows, fields)

    run_info = load_run_info()
    final = frame_rows[-1]
    peak_excess = max(float(r["ExcessPorePress_maxAbs"]) for r in frame_rows)
    summary = {
        **run_info,
        "physical_time_s": frame_rows[-1]["time_s"],
        "peak_excess_maxAbs_Pa": f"{peak_excess:.9g}",
        "final_excess_maxAbs_Pa": final["ExcessPorePress_maxAbs"],
        "final_bottom_excess_mean_Pa": final["bottom_excess_mean"],
        "final_top_drained_excess_maxAbs_Pa": final["top_drained_excess_maxAbs"],
        "final_bottom_no_flux_proxy_Pa": final["bottom_no_flux_proxy"],
        "final_velocity_max_mps": final["vel_max"],
        "final_mean_settlement_m": final["mean_settlement_m"],
        "load_route": "native AccInput on mkfluid=1 top layer",
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))

    times = [float(r["time_s"]) for r in frame_rows]
    def series(name):
        return [float(r[name]) for r in frame_rows]

    plots = [
        ("l1_bottom_excess_time", "Bottom excess pressure [Pa]", series("bottom_excess_mean")),
        ("l1_excess_max_mean_time", "Excess pore pressure [Pa]", series("ExcessPorePress_maxAbs")),
        ("l1_settlement_time", "Mean z displacement [m]", series("mean_settlement_m")),
        ("l1_velocity_max_time", "Velocity max [m/s]", series("vel_max")),
        ("l1_boundary_checks", "Boundary residual [Pa]", series("top_drained_excess_maxAbs")),
    ]
    for stem, ylabel, vals in plots:
        fig, ax = plt.subplots(figsize=(6.2, 4.0))
        ax.plot(times, vals, marker="o", markersize=2)
        if stem == "l1_boundary_checks":
            ax.plot(times, series("bottom_no_flux_proxy"), marker="s", markersize=2, label="bottom no-flux proxy")
            ax.lines[0].set_label("top drained maxAbs")
            ax.legend()
        ax.axvline(0.05, color="0.5", linestyle="--", linewidth=1, label="drain activation")
        ax.set_xlabel("Time [s]")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        fig.savefig(FIGDIR / f"{stem}.svg")
        fig.savefig(FIGDIR / f"{stem}.png", dpi=180)
        plt.close(fig)

    for stem, field, xlabel in [
        ("l1_excess_profiles", "ExcessPorePress", "Excess pore pressure [Pa]"),
        ("l1_porepress_profiles", "PorePress", "Total pore pressure [Pa]"),
    ]:
        fig, ax = plt.subplots(figsize=(6.0, 5.0))
        for t, rows in sorted(profiles.items()):
            ax.plot([r[field] for r in rows], [r["Pos.z [m]"] for r in rows], label=f"t={t:g}s")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("z [m]")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(FIGDIR / f"{stem}.svg")
        fig.savefig(FIGDIR / f"{stem}.png", dpi=180)
        plt.close(fig)


if __name__ == "__main__":
    main()
