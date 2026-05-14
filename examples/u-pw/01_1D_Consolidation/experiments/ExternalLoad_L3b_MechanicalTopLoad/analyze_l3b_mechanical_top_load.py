#!/usr/bin/env python3
"""Postprocess the L3b mechanical top-load 1D consolidation prototype."""

from __future__ import annotations

import csv
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


CASE = "Case1DConsolidation_PR_MechanicalTopLoad_L3b"
XML = Path(f"{CASE}_Def.xml")
OUTDIR = Path(f"{CASE}_cpu_out")
FIGDIR = Path("figures")

E = 2.0e6
NU = 0.3
KW = 2.0e8
POROSITY = 0.3
KPERM = 1.0e-3
RHO_W = 1000.0
G = 9.81
Q0_EXCESS = 10000.0
NTERMS = 250


def xml_value(key: str, default: float) -> float:
    if not XML.exists():
        return default
    root = ET.parse(XML).getroot()
    for par in root.findall(".//parameter"):
        if par.attrib.get("key") == key:
            try:
                return float(par.attrib.get("value", default))
            except ValueError:
                return default
    return default


TIME_OUT = xml_value("TimeOut", 0.001)
TIME_MAX = xml_value("TimeMax", 0.02)
DRAIN_START = xml_value("PorePressureTopDrainedStartTime", 0.005)
LOAD_Q0 = xml_value("MechanicalTopLoadQ0", -10000.0)
LOAD_AREA = xml_value("MechanicalTopLoadArea", 0.1)
LOAD_RAMP_START = xml_value("MechanicalTopLoadRampStart", 0.0)
LOAD_RAMP_END = xml_value("MechanicalTopLoadRampEnd", 0.005)


def constrained_modulus() -> float:
    k_bulk = E / (3.0 * (1.0 - 2.0 * NU))
    g_shear = E / (2.0 * (1.0 + NU))
    return k_bulk + 4.0 * g_shear / 3.0


STORAGE_MOD = (constrained_modulus() * (KW / POROSITY)) / (constrained_modulus() + (KW / POROSITY))
CV = KPERM * STORAGE_MOD / (RHO_W * G)


def terzaghi_ratio(depth_from_top: float, t: float, h: float) -> float:
    if h <= 0.0:
        return 0.0
    y = max(0.0, min(h, depth_from_top))
    tau = max(t - DRAIN_START, 0.0)
    tv = CV * tau / (h * h)
    total = 0.0
    for n in range(NTERMS):
        m = (2 * n + 1) * math.pi / 2.0
        total += (2.0 / m) * math.sin(m * y / h) * math.exp(-(m * m) * tv)
    return total


def terzaghi_excess(depth_from_top: float, t: float, h: float, amp: float = Q0_EXCESS) -> float:
    return amp * terzaghi_ratio(depth_from_top, t, h)


def hydrostatic_pressure(z: float, z_top: float) -> float:
    return RHO_W * G * max(z_top - z, 0.0)


def mean(vals) -> float:
    vals = [v for v in vals if math.isfinite(v)]
    return sum(vals) / len(vals) if vals else 0.0


def std(vals) -> float:
    vals = [v for v in vals if math.isfinite(v)]
    if not vals:
        return 0.0
    m = mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))


def maxabs(vals) -> float:
    vals = [abs(v) for v in vals if math.isfinite(v)]
    return max(vals) if vals else 0.0


def read_partcsv(path: Path) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    with path.open(newline="", errors="ignore") as fp:
        reader = csv.DictReader(fp, delimiter=";")
        for raw in reader:
            if not raw.get("Idp"):
                continue
            try:
                row: dict[str, float | int] = {
                    "Idp": int(float(raw.get("Idp", "nan"))),
                    "Type": int(float(raw.get("Type", "nan"))),
                }
            except ValueError:
                continue
            for key in (
                "Mk",
                "Pos.x [m]",
                "Pos.z [m]",
                "Vel.x [m/s]",
                "Vel.z [m/s]",
                "PorePress",
                "ExcessPorePress",
                "PorePressRate",
                "DivVel",
            ):
                try:
                    row[key] = float(raw.get(key, "0") or 0)
                except ValueError:
                    row[key] = 0.0
            rows.append(row)
    return rows


def is_material(row: dict[str, float | int]) -> bool:
    """Direct -sv:csv output labels all particles as Type=0 here; classify the specimen geometrically."""
    x = float(row["Pos.x [m]"])
    z = float(row["Pos.z [m]"])
    return -1.0e-9 <= x <= 0.100000001 and -1.0e-9 <= z <= 1.000000001


def frame_index(path: Path) -> int:
    m = re.search(r"PartCsv_(\d+)\.csv$", path.name)
    return int(m.group(1)) if m else 0


def frame_time(path: Path) -> float:
    return frame_index(path) * TIME_OUT


def run_info(outdir: Path) -> dict[str, str]:
    text = (outdir / "Run.out").read_text(errors="ignore") if (outdir / "Run.out").exists() else ""
    info = {"run": "cpu", "code": "missing", "excluded": "missing", "dtmin_adjustments": "missing", "steps": "", "runtime_s": ""}
    m = re.search(r"Finished execution \(code=([0-9-]+)\)", text)
    if m:
        info["code"] = m.group(1)
    m = re.search(r"Excluded particles\.+:\s+(\d+)", text)
    if m:
        info["excluded"] = m.group(1)
    m = re.search(r"DTs adjusted to DtMin\.+:\s+(\d+)", text)
    if m:
        info["dtmin_adjustments"] = m.group(1)
    m = re.search(r"Steps of simulation\.+:\s+(\d+)", text)
    if m:
        info["steps"] = m.group(1)
    m = re.search(r"Total Runtime\.+:\s+([0-9.Ee+-]+)", text)
    if m:
        info["runtime_s"] = m.group(1)
    return info


def parse_top_load_diagnostics() -> list[dict[str, float | int | str]]:
    runout = OUTDIR / "Run.out"
    if not runout.exists():
        return []
    rows = []
    pat = re.compile(
        r"MechanicalTopLoad diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[0-9.Ee+-]+), mode=(?P<mode>\d+), "
        r"factor=(?P<factor>[0-9.Ee+-]+), target_mk=(?P<mk>-?\d+), targets=(?P<count>\d+), target_mass=(?P<mass>[0-9.Ee+-]+), "
        r"surface_z=(?P<surface>[0-9.Ee+-]+), thickness=(?P<thick>[0-9.Ee+-]+), q0=(?P<q0>[0-9.Ee+-]+) Pa, area=(?P<area>[0-9.Ee+-]+) m2, "
        r"total_force_z=(?P<force>[0-9.Ee+-]+) N, accel_z=(?P<accel>[0-9.Ee+-]+) m/s2, mean_vel_z=(?P<vel>[0-9.Ee+-]+) m/s, mean_disp_z=(?P<disp>[0-9.Ee+-]+) m"
    )
    for line in runout.read_text(errors="ignore").splitlines():
        m = pat.search(line)
        if not m:
            continue
        rows.append({
            "step": int(m.group("step")),
            "time_s": float(m.group("time")),
            "mode": int(m.group("mode")),
            "factor": float(m.group("factor")),
            "target_mk": int(m.group("mk")),
            "target_count": int(m.group("count")),
            "target_mass": float(m.group("mass")),
            "surface_z_m": float(m.group("surface")),
            "thickness_m": float(m.group("thick")),
            "q0_Pa": float(m.group("q0")),
            "area_m2": float(m.group("area")),
            "total_force_z_N": float(m.group("force")),
            "accel_z_m_s2": float(m.group("accel")),
            "mean_vel_z_m_s": float(m.group("vel")),
            "mean_disp_z_m": float(m.group("disp")),
        })
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def analyse_case() -> dict[str, list[dict] | dict]:
    part_files = sorted((OUTDIR / "data").glob("PartCsv_*.csv"), key=frame_index)
    frames: list[dict] = []
    profiles: list[dict] = []
    profile_metrics: list[dict] = []
    bottom: list[dict] = []
    boundary: list[dict] = []
    if not part_files:
        return {"summary": run_info(OUTDIR), "frames": frames, "profiles": profiles, "profile_metrics": profile_metrics, "bottom": bottom, "boundary": boundary}

    first = [r for r in read_partcsv(part_files[0]) if is_material(r)]
    zmin = min(float(r["Pos.z [m]"]) for r in first)
    zmax = max(float(r["Pos.z [m]"]) for r in first)
    h_eff = zmax - zmin
    top_thick = 0.018
    bottom_thick = 0.018

    selected_indices = {0, 1, 2, 5, 10, 20}
    for pf in part_files:
        t = frame_time(pf)
        rows = [r for r in read_partcsv(pf) if is_material(r)]
        if not rows:
            continue
        top = [r for r in rows if float(r["Pos.z [m]"]) >= zmax - top_thick]
        bottom_rows = [r for r in rows if float(r["Pos.z [m]"]) <= zmin + bottom_thick]
        ref_bottom = [r for r in rows if zmin + bottom_thick <= float(r["Pos.z [m]"]) <= zmin + 2.0 * bottom_thick]
        bottom_excess = mean(float(r["ExcessPorePress"]) for r in bottom_rows)
        ref_excess = mean(float(r["ExcessPorePress"]) for r in ref_bottom)
        bottom_depth = h_eff
        analytical_bottom = terzaghi_excess(bottom_depth, t, h_eff)
        analytical_bottom_total = hydrostatic_pressure(zmin, zmax) + analytical_bottom
        frame = {
            "run": "cpu",
            "time_s": t,
            "particle_count": len(rows),
            "PorePress_mean": mean(float(r["PorePress"]) for r in rows),
            "PorePress_std": std(float(r["PorePress"]) for r in rows),
            "ExcessPorePress_mean": mean(float(r["ExcessPorePress"]) for r in rows),
            "ExcessPorePress_maxAbs": maxabs(float(r["ExcessPorePress"]) for r in rows),
            "PorePressRate_maxAbs": maxabs(float(r["PorePressRate"]) for r in rows),
            "DivVel_maxAbs": maxabs(float(r["DivVel"]) for r in rows),
            "vel_max": max(math.hypot(float(r["Vel.x [m/s]"]), float(r["Vel.z [m/s]"])) for r in rows),
            "bottom_excess_mean": bottom_excess,
            "top_drained_excess_maxAbs": maxabs(float(r["ExcessPorePress"]) for r in top),
            "bottom_no_flux_proxy": bottom_excess - ref_excess,
        }
        frames.append(frame)
        bottom.append({
            "run": "cpu",
            "time_s": t,
            "bottom_excess_mean": bottom_excess,
            "bottom_porepress_mean": mean(float(r["PorePress"]) for r in bottom_rows),
            "analytical_q0_bottom": analytical_bottom,
            "analytical_q0_total_bottom": analytical_bottom_total,
            "error_q0": bottom_excess - analytical_bottom,
            "relative_error_q0": (bottom_excess - analytical_bottom) / analytical_bottom if analytical_bottom else 0.0,
        })
        boundary.append({
            "run": "cpu",
            "time_s": t,
            "top_drained_excess_maxAbs": frame["top_drained_excess_maxAbs"],
            "bottom_no_flux_proxy": frame["bottom_no_flux_proxy"],
        })
        if frame_index(pf) in selected_indices:
            ordered = sorted(rows, key=lambda r: float(r["Pos.z [m]"]))
            errs = []
            refs = []
            for r in ordered:
                z = float(r["Pos.z [m]"])
                depth = zmax - z
                sim_excess = float(r["ExcessPorePress"])
                analytical = terzaghi_excess(depth, t, h_eff)
                profiles.append({
                    "run": "cpu",
                    "time_s": t,
                    "z_m": z,
                    "depth_from_top_m": depth,
                    "sim_porepress": float(r["PorePress"]),
                    "sim_excess": sim_excess,
                    "analytical_excess_q0": analytical,
                    "analytical_total_q0": hydrostatic_pressure(z, zmax) + analytical,
                })
                errs.append(sim_excess - analytical)
                refs.append(analytical)
            rmse = math.sqrt(mean(e * e for e in errs))
            denom = math.sqrt(mean(r * r for r in refs))
            profile_metrics.append({
                "run": "cpu",
                "time_s": t,
                "n": len(ordered),
                "rmse_q0": rmse,
                "relative_rmse_q0": rmse / denom if denom else 0.0,
                "mean_sim_excess": mean(float(r["ExcessPorePress"]) for r in ordered),
            })

    info = run_info(OUTDIR)
    final = frames[-1]
    bottom_rmse = math.sqrt(mean(float(r["error_q0"]) ** 2 for r in bottom))
    profile_final_rmse = profile_metrics[-1]["rmse_q0"] if profile_metrics else ""
    load_diag = parse_top_load_diagnostics()
    max_force = maxabs(float(r["total_force_z_N"]) for r in load_diag) if load_diag else 0.0
    max_accel = maxabs(float(r["accel_z_m_s2"]) for r in load_diag) if load_diag else 0.0
    summary = {
        **info,
        "TimeMax_s": TIME_MAX,
        "TimeOut_s": TIME_OUT,
        "drain_start_s": DRAIN_START,
        "cv_m2_s": CV,
        "q0_target_abs_Pa": Q0_EXCESS,
        "MechanicalTopLoadQ0_Pa": LOAD_Q0,
        "MechanicalTopLoadArea_m2": LOAD_AREA,
        "MechanicalTopLoadRampEnd_s": LOAD_RAMP_END,
        "MechanicalTopLoadMaxForceAbs_N": max_force,
        "MechanicalTopLoadMaxAccelAbs_m_s2": max_accel,
        "peak_excess_maxAbs_Pa": max(float(r["ExcessPorePress_maxAbs"]) for r in frames),
        "final_excess_maxAbs_Pa": final["ExcessPorePress_maxAbs"],
        "final_bottom_excess_mean_Pa": final["bottom_excess_mean"],
        "final_top_drained_excess_maxAbs_Pa": final["top_drained_excess_maxAbs"],
        "final_bottom_no_flux_proxy_Pa": final["bottom_no_flux_proxy"],
        "final_velocity_max_mps": final["vel_max"],
        "bottom_rmse_q0_Pa": bottom_rmse,
        "profile_rmse_q0_Pa": profile_final_rmse,
        "load_route": "MechanicalTopLoad=1 CPU top material surface traction; no AccInput",
    }
    return {
        "summary": summary,
        "frames": frames,
        "profiles": profiles,
        "profile_metrics": profile_metrics,
        "bottom": bottom,
        "boundary": boundary,
        "topload": load_diag,
    }


def comparison_rows(summary: dict) -> list[dict]:
    rows = [
        {
            "case": "L3b mechanical top-load",
            "bottom_rmse_q0_Pa": summary.get("bottom_rmse_q0_Pa", ""),
            "profile_rmse_q0_Pa": summary.get("profile_rmse_q0_Pa", ""),
            "peak_excess_maxAbs_Pa": summary.get("peak_excess_maxAbs_Pa", ""),
            "route": "CPU surface-force prototype",
        }
    ]
    candidates = [
        ("L2 AccInput", Path("../ExternalLoad_L2_PaperAligned/l2_case_summary.csv"), "AccInput body acceleration"),
        ("L3a initial-pressure gate", Path("../ExternalLoad_L3_InitialPressureGate/l3a_case_summary.csv"), "initial pressure diffusion gate"),
    ]
    for name, path, route in candidates:
        if not path.exists():
            continue
        with path.open(newline="") as fp:
            reader = csv.DictReader(fp)
            first = next(reader, None)
        if first:
            rows.append({
                "case": name,
                "bottom_rmse_q0_Pa": first.get("bottom_rmse_q0_Pa", ""),
                "profile_rmse_q0_Pa": first.get("profile_rmse_q0_Pa", ""),
                "peak_excess_maxAbs_Pa": first.get("peak_excess_maxAbs_Pa", ""),
                "route": route,
            })
    return rows


def plot_outputs(res: dict) -> None:
    FIGDIR.mkdir(exist_ok=True)
    profiles = res["profiles"]
    bottom = res["bottom"]
    boundary = res["boundary"]
    frames = res["frames"]
    topload = res["topload"]

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    if topload:
        ax.plot([r["time_s"] for r in topload], [r["total_force_z_N"] for r in topload], marker="o", markersize=2)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Applied top load Fz [N]")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3b_applied_top_load_vs_time.svg")
    fig.savefig(FIGDIR / "l3b_applied_top_load_vs_time.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    for t in sorted({r["time_s"] for r in profiles}):
        rs = [r for r in profiles if r["time_s"] == t]
        ax.plot([r["sim_excess"] for r in rs], [r["z_m"] for r in rs], marker="o", markersize=2, label=f"sim t={t:g}s")
        ax.plot([r["analytical_excess_q0"] for r in rs], [r["z_m"] for r in rs], linestyle="--", color=ax.lines[-1].get_color())
    ax.set_xlabel("Excess pore pressure [Pa]")
    ax.set_ylabel("z [m]")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3b_excess_profiles_vs_analytical.svg")
    fig.savefig(FIGDIR / "l3b_excess_profiles_vs_analytical.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot([r["time_s"] for r in bottom], [r["bottom_excess_mean"] for r in bottom], marker="o", markersize=2, label="L3b simulated")
    ax.plot([r["time_s"] for r in bottom], [r["analytical_q0_bottom"] for r in bottom], linestyle="--", label="Terzaghi q0")
    ax.axvline(DRAIN_START, color="0.5", linestyle="--", linewidth=1, label="drain start")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Bottom excess pressure [Pa]")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3b_bottom_excess_vs_analytical.svg")
    fig.savefig(FIGDIR / "l3b_bottom_excess_vs_analytical.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot([r["time_s"] for r in boundary], [r["top_drained_excess_maxAbs"] for r in boundary], label="top drained residual")
    ax.plot([r["time_s"] for r in boundary], [abs(r["bottom_no_flux_proxy"]) for r in boundary], label="bottom no-flux proxy")
    ax.axvline(DRAIN_START, color="0.5", linestyle="--", linewidth=1)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Boundary residual [Pa]")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3b_boundary_checks.svg")
    fig.savefig(FIGDIR / "l3b_boundary_checks.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot([r["time_s"] for r in frames], [r["vel_max"] for r in frames], label="velocity max")
    ax.plot([r["time_s"] for r in frames], [r["DivVel_maxAbs"] for r in frames], label="DivVel maxAbs")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Diagnostic magnitude")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3b_velocity_divvel_diagnostics.svg")
    fig.savefig(FIGDIR / "l3b_velocity_divvel_diagnostics.png", dpi=180)
    plt.close(fig)

    comp = comparison_rows(res["summary"])
    if comp:
        names = [r["case"] for r in comp]
        bottom_vals = [float(r["bottom_rmse_q0_Pa"] or 0.0) for r in comp]
        peak_vals = [float(r["peak_excess_maxAbs_Pa"] or 0.0) for r in comp]
        x = range(len(names))
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        ax.bar([i - 0.2 for i in x], bottom_vals, width=0.4, label="bottom RMSE")
        ax.bar([i + 0.2 for i in x], peak_vals, width=0.4, label="peak excess")
        ax.set_xticks(list(x))
        ax.set_xticklabels(names, rotation=15, ha="right")
        ax.set_ylabel("Pressure [Pa]")
        ax.grid(True, axis="y", alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(FIGDIR / "l3b_l2_l3a_l3b_pressure_comparison.svg")
        fig.savefig(FIGDIR / "l3b_l2_l3a_l3b_pressure_comparison.png", dpi=180)
        plt.close(fig)


def main() -> None:
    res = analyse_case()
    write_csv(Path("l3b_case_summary.csv"), [res["summary"]])
    write_csv(Path("l3b_top_load_diagnostics.csv"), res["topload"])
    write_csv(Path("l3b_analytical_profile_metrics.csv"), res["profile_metrics"])
    write_csv(Path("l3b_bottom_pressure_metrics.csv"), res["bottom"])
    write_csv(Path("l3b_boundary_metrics.csv"), res["boundary"])
    write_csv(Path("l3b_l2_l3a_l3b_comparison.csv"), comparison_rows(res["summary"]))
    plot_outputs(res)
    print("Wrote L3b postprocessing CSV and figures.")


if __name__ == "__main__":
    main()
