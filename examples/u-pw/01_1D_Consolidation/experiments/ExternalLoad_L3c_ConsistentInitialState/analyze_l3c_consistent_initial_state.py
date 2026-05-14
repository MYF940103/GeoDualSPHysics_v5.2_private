#!/usr/bin/env python3
"""Postprocess the L3c consistent initial-state 1D consolidation gate."""

from __future__ import annotations

import csv
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


CASE = "Case1DConsolidation_PR_ConsistentInitialState_L3c"
XML = Path(f"{CASE}_Def.xml")
FIGDIR = Path("figures")

E = 2.0e6
NU = 0.3
KW = 2.0e8
POROSITY = 0.3
KPERM = 1.0e-3
RHO0 = 2100.0
RHO_W = 1000.0
G = 9.81
DP = 0.01
Q0_EXCESS = 10000.0
NTERMS = 250

RUNS = [
    ("cpu", Path(f"{CASE}_cpu_out")),
    ("gpu", Path(f"{CASE}_gpu_out")),
]

SUMMARY_CSV = Path("l3c_case_summary.csv")
INITIAL_STATE_CSV = Path("l3c_initial_state_metrics.csv")
ANALYTICAL_PROFILES_CSV = Path("l3c_analytical_profiles.csv")
PROFILE_METRICS_CSV = Path("l3c_analytical_profile_metrics.csv")
BOTTOM_METRICS_CSV = Path("l3c_bottom_pressure_metrics.csv")
BOUNDARY_METRICS_CSV = Path("l3c_boundary_metrics.csv")
STRESS_STATE_CSV = Path("l3c_stress_state_metrics.csv")
COMPARISON_CSV = Path("l3c_l3a_l3b_comparison.csv")


def read_xml_value(key: str, default: float) -> float:
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


TIME_OUT = read_xml_value("TimeOut", 0.001)
DRAIN_START = read_xml_value("PorePressureTopDrainedStartTime", 0.0)
TIME_MAX = read_xml_value("TimeMax", 0.02)


def read_partcsv(path: Path) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    with path.open(newline="", errors="ignore") as fp:
        reader = csv.DictReader(fp, delimiter=";")
        for raw in reader:
            if not raw.get("Idp"):
                continue
            row: dict[str, float | int] = {}
            try:
                row["Idp"] = int(float(raw.get("Idp", "nan")))
                row["Type"] = int(float(raw.get("Type", "nan")))
            except ValueError:
                continue
            for key in (
                "Mk",
                "Pos.x [m]",
                "Pos.y [m]",
                "Pos.z [m]",
                "Vel.x [m/s]",
                "Vel.y [m/s]",
                "Vel.z [m/s]",
                "Rhop [kg/m^3]",
                "PorePress",
                "ExcessPorePress",
                "PorePressRate",
                "DivVel",
                "LapPorePress",
                "LapZ",
                "PorePressureAccelDiff.x",
                "PorePressureAccelDiff.y",
                "PorePressureAccelDiff.z",
                "Sigma_kk.x",
                "Sigma_kk.y",
                "Sigma_kk.z",
                "Sigma_ij.x",
                "Sigma_ij.y",
                "Sigma_ij.z",
            ):
                try:
                    row[key] = float(raw.get(key, "0") or 0)
                except ValueError:
                    row[key] = 0.0
            rows.append(row)
    return rows


def is_material(row: dict[str, float | int]) -> bool:
    """Classify the 1D specimen geometrically if Type is not reliable in direct CSV."""
    if int(row.get("Type", -1)) == 3:
        return True
    x = float(row.get("Pos.x [m]", 0.0))
    z = float(row.get("Pos.z [m]", 0.0))
    return -1.0e-9 <= x <= 0.100000001 and -1.0e-9 <= z <= 1.000000001


def frame_index(path: Path) -> int:
    match = re.search(r"PartCsv_(\d+)\.csv$", path.name)
    return int(match.group(1)) if match else 0


def frame_time(path: Path) -> float:
    return frame_index(path) * TIME_OUT


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


def q_from_stress(sxx: float, syy: float, szz: float, sxy: float, sxz: float, syz: float) -> float:
    mean_s = (sxx + syy + szz) / 3.0
    dxx, dyy, dzz = sxx - mean_s, syy - mean_s, szz - mean_s
    j2 = 0.5 * (dxx * dxx + dyy * dyy + dzz * dzz) + sxy * sxy + sxz * sxz + syz * syz
    return math.sqrt(max(3.0 * j2, 0.0))


def constrained_modulus() -> float:
    k_bulk = E / (3.0 * (1.0 - 2.0 * NU))
    g_shear = E / (2.0 * (1.0 + NU))
    return k_bulk + 4.0 * g_shear / 3.0


M_1D = constrained_modulus()
STORAGE_MOD = (M_1D * (KW / POROSITY)) / (M_1D + (KW / POROSITY))
CV = KPERM * STORAGE_MOD / (RHO_W * G)


def terzaghi_ratio(depth_from_top: float, t: float, h: float) -> float:
    if h <= 0:
        return 0.0
    y = max(0.0, min(h, depth_from_top))
    tau = max(t - DRAIN_START, 0.0)
    tv = CV * tau / (h * h)
    total = 0.0
    for n in range(NTERMS):
        m = (2 * n + 1) * math.pi / 2.0
        total += (2.0 / m) * math.sin(m * y / h) * math.exp(-(m * m) * tv)
    return total


def terzaghi_excess(depth_from_top: float, t: float, h: float, amp: float) -> float:
    return amp * terzaghi_ratio(depth_from_top, t, h)


def hydrostatic_pressure(z: float, z_top: float) -> float:
    return RHO_W * G * max(z_top - z, 0.0)


def run_info(outdir: Path) -> dict[str, str]:
    info = {
        "code": "missing",
        "excluded": "missing",
        "runtime_s": "",
        "steps": "",
        "frames": "",
        "dtmin_adjustments": "",
    }
    runout = outdir / "Run.out"
    if not runout.exists():
        return info
    text = runout.read_text(errors="ignore")
    if "Finished execution (code=0)" in text:
        info["code"] = "0"
    else:
        m = re.search(r"Finished execution \(code=([0-9-]+)\)", text)
        info["code"] = m.group(1) if m else "unknown"
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
    m = re.search(r"DTs adjusted to DtMin\.+:\s+(\d+)", text)
    info["dtmin_adjustments"] = m.group(1) if m else "0"
    return info


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = sorted({k for row in rows for k in row})
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_run(label: str, outdir: Path):
    datadir = outdir / "data"
    files = sorted(datadir.glob("PartCsv_*.csv"), key=frame_index)
    if not files:
        return None
    frames = []
    for path in files:
        rows = [r for r in read_partcsv(path) if is_material(r)]
        if rows:
            frames.append((frame_time(path), rows))
    return frames if frames else None


def select_profile_times(times: list[float]) -> list[float]:
    targets = [0.0, DRAIN_START, min(TIME_MAX, DRAIN_START + 0.005), min(TIME_MAX, DRAIN_START + 0.01), TIME_MAX]
    selected = []
    for target in targets:
        nearest = min(times, key=lambda t: abs(t - target))
        if nearest not in selected:
            selected.append(nearest)
    return selected


def analyze_run(label: str, outdir: Path):
    frames = load_run(label, outdir)
    if frames is None:
        return None

    all_z = [float(r["Pos.z [m]"]) for _, rows in frames for r in rows]
    zmin = min(all_z)
    zmax = max(all_z)
    h_eff = zmax - zmin
    layer = max(0.018, 1.8 * DP)

    def split_regions(rows):
        top = [r for r in rows if float(r["Pos.z [m]"]) >= zmax - layer]
        bottom = [r for r in rows if float(r["Pos.z [m]"]) <= zmin + layer]
        bottom_ref = [
            r for r in rows
            if zmin + layer < float(r["Pos.z [m]"]) <= zmin + 2.0 * layer
        ]
        return top, bottom, bottom_ref

    # Fit the analytical amplitude as a diagnostic only. For this L3c gate the
    # prescribed amplitude is already the intended q0 excess, so fitted and q0
    # curves should be close unless boundary initialization strongly modifies it.
    fit_amp = Q0_EXCESS
    for t, rows in frames:
        if t + 1e-12 >= DRAIN_START:
            _, bottom, _ = split_regions(rows)
            bottom_mean = mean(float(r["ExcessPorePress"]) for r in bottom)
            ratio = terzaghi_ratio(h_eff, t, h_eff)
            if abs(ratio) > 1e-12:
                fit_amp = bottom_mean / ratio
            break

    frame_rows = []
    profile_rows = []
    profile_metric_rows = []
    bottom_rows = []
    boundary_rows = []
    stress_rows = []
    profile_times = select_profile_times([t for t, _ in frames])

    for t, rows in frames:
        top, bottom, bottom_ref = split_regions(rows)
        velmag = [
            math.sqrt(float(r["Vel.x [m/s]"]) ** 2 + float(r["Vel.y [m/s]"]) ** 2 + float(r["Vel.z [m/s]"]) ** 2)
            for r in rows
        ]
        top_resid = maxabs(float(r["ExcessPorePress"]) for r in top)
        bottom_excess = mean(float(r["ExcessPorePress"]) for r in bottom)
        bottom_porepress = mean(float(r["PorePress"]) for r in bottom)
        ref_excess = mean(float(r["ExcessPorePress"]) for r in bottom_ref)
        bottom_depth = h_eff
        bottom_hydro = hydrostatic_pressure(zmin, zmax)
        analytical_q0_bottom = terzaghi_excess(bottom_depth, t, h_eff, Q0_EXCESS)
        analytical_fit_bottom = terzaghi_excess(bottom_depth, t, h_eff, fit_amp)
        porepressrate = [float(r["PorePressRate"]) for r in rows]
        divvel = [float(r["DivVel"]) for r in rows]
        sxx = [float(r["Sigma_kk.x"]) for r in rows]
        syy = [float(r["Sigma_kk.y"]) for r in rows]
        szz = [float(r["Sigma_kk.z"]) for r in rows]
        sxy = [float(r["Sigma_ij.x"]) for r in rows]
        sxz = [float(r["Sigma_ij.y"]) for r in rows]
        syz = [float(r["Sigma_ij.z"]) for r in rows]
        sxx_m, syy_m, szz_m = mean(sxx), mean(syy), mean(szz)
        sxy_m, sxz_m, syz_m = mean(sxy), mean(sxz), mean(syz)
        p_eff = -(sxx_m + syy_m + szz_m) / 3.0
        q_eff = q_from_stress(sxx_m, syy_m, szz_m, sxy_m, sxz_m, syz_m)

        frame_rows.append({
            "run": label,
            "time_s": t,
            "nfluid": len(rows),
            "zmin": zmin,
            "zmax": zmax,
            "H_effective_m": h_eff,
            "vel_max": max(velmag) if velmag else 0.0,
            "ExcessPorePress_maxAbs": maxabs(float(r["ExcessPorePress"]) for r in rows),
            "ExcessPorePress_mean": mean(float(r["ExcessPorePress"]) for r in rows),
            "PorePress_mean": mean(float(r["PorePress"]) for r in rows),
            "PorePress_std": std(float(r["PorePress"]) for r in rows),
            "bottom_excess_mean": bottom_excess,
            "top_drained_excess_maxAbs": top_resid,
            "bottom_no_flux_proxy": bottom_excess - ref_excess,
            "PorePressRate_maxAbs": maxabs(porepressrate),
            "PorePressRate_mean": mean(porepressrate),
            "DivVel_maxAbs": maxabs(divvel),
            "DivVel_mean": mean(divvel),
            "Sigma_xx_mean": sxx_m,
            "Sigma_yy_mean": syy_m,
            "Sigma_zz_mean": szz_m,
            "p_eff_proxy_Pa": p_eff,
            "q_eff_proxy_Pa": q_eff,
        })
        stress_rows.append({
            "run": label,
            "time_s": t,
            "Sigma_xx_mean": sxx_m,
            "Sigma_yy_mean": syy_m,
            "Sigma_zz_mean": szz_m,
            "Sigma_xy_mean": sxy_m,
            "Sigma_xz_mean": sxz_m,
            "Sigma_yz_mean": syz_m,
            "Sigma_xx_min": min(sxx) if sxx else 0.0,
            "Sigma_xx_max": max(sxx) if sxx else 0.0,
            "Sigma_zz_min": min(szz) if szz else 0.0,
            "Sigma_zz_max": max(szz) if szz else 0.0,
            "p_eff_proxy_Pa": p_eff,
            "q_eff_proxy_Pa": q_eff,
            "initial_effective_stress_mode": read_xml_value("InitialStressMode", 0.0),
            "initial_effective_stress_iso_Pa": read_xml_value("InitialEffectiveStressIso", 0.0),
        })
        bottom_rows.append({
            "run": label,
            "time_s": t,
            "Tv": CV * max(t - DRAIN_START, 0.0) / (h_eff * h_eff) if h_eff > 0 else 0.0,
            "bottom_porepress_mean": bottom_porepress,
            "bottom_hydrostatic_reference": bottom_hydro,
            "bottom_excess_mean": bottom_excess,
            "analytical_q0_bottom": analytical_q0_bottom,
            "analytical_fit_bottom": analytical_fit_bottom,
            "analytical_q0_total_bottom": bottom_hydro + analytical_q0_bottom,
            "analytical_fit_total_bottom": bottom_hydro + analytical_fit_bottom,
            "error_q0": bottom_excess - analytical_q0_bottom,
            "error_fit": bottom_excess - analytical_fit_bottom,
            "relative_error_q0": (bottom_excess - analytical_q0_bottom) / Q0_EXCESS,
            "relative_error_fit": (bottom_excess - analytical_fit_bottom) / fit_amp if abs(fit_amp) > 1e-12 else 0.0,
        })
        boundary_rows.append({
            "run": label,
            "time_s": t,
            "top_drained_excess_maxAbs": top_resid,
            "bottom_no_flux_proxy": bottom_excess - ref_excess,
            "bottom_excess_mean": bottom_excess,
            "bottom_reference_excess_mean": ref_excess,
            "velocity_max": max(velmag) if velmag else 0.0,
            "PorePressRate_maxAbs": maxabs(porepressrate),
            "DivVel_maxAbs": maxabs(divvel),
        })

        if t in profile_times:
            rows_sorted = sorted(rows, key=lambda r: float(r["Pos.z [m]"]))
            errs_q0 = []
            errs_fit = []
            refs_q0 = []
            refs_fit = []
            for r in rows_sorted:
                z = float(r["Pos.z [m]"])
                depth = zmax - z
                sim_excess = float(r["ExcessPorePress"])
                aq0 = terzaghi_excess(depth, t, h_eff, Q0_EXCESS)
                afit = terzaghi_excess(depth, t, h_eff, fit_amp)
                hydro = hydrostatic_pressure(z, zmax)
                profile_rows.append({
                    "run": label,
                    "time_s": t,
                    "z_m": z,
                    "depth_from_top_m": depth,
                    "eta_depth": depth / h_eff if h_eff else 0.0,
                    "sim_porepress": float(r["PorePress"]),
                    "sim_excess": sim_excess,
                    "analytical_excess_q0": aq0,
                    "analytical_excess_fit": afit,
                    "analytical_total_q0": hydro + aq0,
                    "analytical_total_fit": hydro + afit,
                })
                errs_q0.append(sim_excess - aq0)
                errs_fit.append(sim_excess - afit)
                refs_q0.append(aq0)
                refs_fit.append(afit)
            rmse_q0 = math.sqrt(mean(e * e for e in errs_q0))
            rmse_fit = math.sqrt(mean(e * e for e in errs_fit))
            denom_q0 = math.sqrt(mean(r * r for r in refs_q0))
            denom_fit = math.sqrt(mean(r * r for r in refs_fit))
            profile_metric_rows.append({
                "run": label,
                "time_s": t,
                "n": len(rows_sorted),
                "rmse_q0": rmse_q0,
                "relative_rmse_q0": rmse_q0 / denom_q0 if denom_q0 else 0.0,
                "rmse_fit": rmse_fit,
                "relative_rmse_fit": rmse_fit / denom_fit if denom_fit else 0.0,
                "mean_sim_excess": mean(float(r["ExcessPorePress"]) for r in rows_sorted),
                "fit_amplitude_Pa": fit_amp,
            })

    info = run_info(outdir)
    final = frame_rows[-1]
    bottom_rmse_q0 = math.sqrt(mean(float(r["error_q0"]) ** 2 for r in bottom_rows))
    bottom_rmse_fit = math.sqrt(mean(float(r["error_fit"]) ** 2 for r in bottom_rows))
    summary = {
        "run": label,
        **info,
        "TimeMax_s": TIME_MAX,
        "TimeOut_s": TIME_OUT,
        "drain_start_s": DRAIN_START,
        "H_effective_m": h_eff,
        "cv_m2_s": CV,
        "q0_target_Pa": Q0_EXCESS,
        "AccInput_az_m_s2": 0.0,
        "fit_amplitude_Pa": fit_amp,
        "peak_excess_maxAbs_Pa": max(float(r["ExcessPorePress_maxAbs"]) for r in frame_rows),
        "final_excess_maxAbs_Pa": final["ExcessPorePress_maxAbs"],
        "final_bottom_excess_mean_Pa": final["bottom_excess_mean"],
        "final_top_drained_excess_maxAbs_Pa": final["top_drained_excess_maxAbs"],
        "final_bottom_no_flux_proxy_Pa": final["bottom_no_flux_proxy"],
        "final_velocity_max_mps": final["vel_max"],
        "final_p_eff_proxy_Pa": final["p_eff_proxy_Pa"],
        "final_q_eff_proxy_Pa": final["q_eff_proxy_Pa"],
        "bottom_rmse_q0_Pa": bottom_rmse_q0,
        "bottom_rmse_fit_Pa": bottom_rmse_fit,
        "profile_rmse_q0_Pa": profile_metric_rows[-1]["rmse_q0"] if profile_metric_rows else "",
        "profile_rmse_fit_Pa": profile_metric_rows[-1]["rmse_fit"] if profile_metric_rows else "",
        "initial_stress_route": "zero effective-stress increment; InitialStressMode=0",
        "load_route": "PorePressureInit=3 uniform initial excess; no AccInput; no MechanicalTopLoad",
    }
    return {
        "summary": summary,
        "frames": frame_rows,
        "profiles": profile_rows,
        "profile_metrics": profile_metric_rows,
        "bottom": bottom_rows,
        "boundary": boundary_rows,
        "stress": stress_rows,
    }


def plot_outputs(results: dict[str, dict]) -> None:
    FIGDIR.mkdir(exist_ok=True)

    def rows(kind: str):
        out = []
        for res in results.values():
            out.extend(res[kind])
        return out

    bottom = rows("bottom")
    boundary = rows("boundary")
    profiles = rows("profiles")
    frames = rows("frames")

    # 1-2. Profiles against analytical q0 and fitted amplitude.
    for stem, field_sim, field_a, xlabel in [
        ("l3c_excess_profiles_vs_analytical", "sim_excess", "analytical_excess_q0", "Excess pore pressure [Pa]"),
        ("l3c_pore_pressure_profiles", "sim_porepress", "analytical_total_q0", "Total pore pressure [Pa]"),
    ]:
        fig, ax = plt.subplots(figsize=(6.4, 5.0))
        primary_run = "gpu" if "gpu" in results else next(iter(results))
        run_profiles = [r for r in profiles if r["run"] == primary_run]
        times = sorted({float(r["time_s"]) for r in run_profiles})
        for t in times:
            rs = [r for r in run_profiles if float(r["time_s"]) == t]
            ax.plot([float(r[field_sim]) for r in rs], [float(r["z_m"]) for r in rs], marker="o", markersize=2, label=f"{primary_run} t={t:g}s")
            ax.plot([float(r[field_a]) for r in rs], [float(r["z_m"]) for r in rs], linestyle="--", linewidth=1, color=ax.lines[-1].get_color())
        ax.set_xlabel(xlabel)
        ax.set_ylabel("z [m]")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(FIGDIR / f"{stem}.svg")
        fig.savefig(FIGDIR / f"{stem}.png", dpi=180)
        plt.close(fig)

    # 3-4. Bottom pressure/excess time histories.
    for stem, ylabel, sim_key, a_key in [
        ("l3c_bottom_excess_vs_analytical", "Bottom excess pressure [Pa]", "bottom_excess_mean", "analytical_q0_bottom"),
        ("l3c_bottom_pore_pressure_vs_analytical", "Bottom total pore pressure [Pa]", "bottom_porepress_mean", "analytical_q0_total_bottom"),
    ]:
        fig, ax = plt.subplots(figsize=(6.4, 4.0))
        for label in sorted(results):
            rs = [r for r in bottom if r["run"] == label]
            ts = [float(r["time_s"]) for r in rs]
            vals = [float(r[sim_key]) for r in rs]
            sim_label = "simulated total" if "porepress" in sim_key else "simulated excess"
            ax.plot(ts, vals, marker="o", markersize=2, label=f"{label} {sim_label}")
            if label == sorted(results)[0]:
                ax.plot(ts, [float(r[a_key]) for r in rs], linestyle="--", label="Terzaghi q0=10 kPa")
                fit_key = "analytical_fit_total_bottom" if "total" in a_key else "analytical_fit_bottom"
                ax.plot(ts, [float(r[fit_key]) for r in rs], linestyle=":", label="Terzaghi fitted amplitude")
        ax.axvline(DRAIN_START, color="0.5", linestyle="--", linewidth=1, label="drain start")
        ax.set_xlabel("Time [s]")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(FIGDIR / f"{stem}.svg")
        fig.savefig(FIGDIR / f"{stem}.png", dpi=180)
        plt.close(fig)

    # 5. Relative bottom error.
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for label in sorted(results):
        rs = [r for r in bottom if r["run"] == label]
        ax.plot([float(r["time_s"]) for r in rs], [abs(float(r["relative_error_q0"])) for r in rs], marker="o", markersize=2, label=f"{label} vs q0")
        ax.plot([float(r["time_s"]) for r in rs], [abs(float(r["relative_error_fit"])) for r in rs], marker="s", markersize=2, linestyle="--", label=f"{label} vs fitted")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Absolute relative bottom error [-]")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3c_relative_error_time.svg")
    fig.savefig(FIGDIR / "l3c_relative_error_time.png", dpi=180)
    plt.close(fig)

    # 6. Boundary checks.
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for label in sorted(results):
        rs = [r for r in boundary if r["run"] == label]
        ts = [float(r["time_s"]) for r in rs]
        ax.plot(ts, [float(r["top_drained_excess_maxAbs"]) for r in rs], marker="o", markersize=2, label=f"{label} top drained")
        ax.plot(ts, [abs(float(r["bottom_no_flux_proxy"])) for r in rs], marker="s", markersize=2, linestyle="--", label=f"{label} bottom no-flux proxy")
    ax.axvline(DRAIN_START, color="0.5", linestyle="--", linewidth=1)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Boundary residual [Pa]")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3c_boundary_checks.svg")
    fig.savefig(FIGDIR / "l3c_boundary_checks.png", dpi=180)
    plt.close(fig)

    # 7. CPU/GPU comparison, or single-run bottom trend when only one exists.
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for label in sorted(results):
        rs = [r for r in bottom if r["run"] == label]
        ax.plot([float(r["time_s"]) for r in rs], [float(r["bottom_excess_mean"]) for r in rs], marker="o", markersize=2, label=label)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Bottom excess pressure [Pa]")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3c_cpu_gpu_comparison.svg")
    fig.savefig(FIGDIR / "l3c_cpu_gpu_comparison.png", dpi=180)
    plt.close(fig)

    # 8. L2 AccInput vs L3c consistent initial-state gate when L2 metrics are retained.
    l2 = Path("../ExternalLoad_L2_PaperAligned/l2_bottom_pressure_metrics.csv")
    if l2.exists():
        with l2.open(newline="") as fp:
            l2rows = list(csv.DictReader(fp))
        fig, ax = plt.subplots(figsize=(6.4, 4.0))
        for label in sorted({r["run"] for r in l2rows}):
            rs = [r for r in l2rows if r["run"] == label]
            ax.plot([float(r["time_s"]) for r in rs], [float(r["bottom_excess_mean"]) for r in rs], linestyle="--", label=f"L2 AccInput {label}")
        for label in sorted(results):
            rs = [r for r in bottom if r["run"] == label]
            ax.plot([float(r["time_s"]) for r in rs], [float(r["bottom_excess_mean"]) for r in rs], marker="o", markersize=2, label=f"L3c {label}")
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Bottom excess pressure [Pa]")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(FIGDIR / "l3c_l2_bottom_comparison.svg")
        fig.savefig(FIGDIR / "l3c_l2_bottom_comparison.png", dpi=180)
        plt.close(fig)

    # Velocity / rate diagnostics check that the pressure gate did not excite
    # the strong mechanical dynamics seen in the L2 AccInput route.
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for label in sorted(results):
        rs = [r for r in frames if r["run"] == label]
        ax.plot([float(r["time_s"]) for r in rs], [float(r["vel_max"]) for r in rs], marker="o", markersize=2, label=f"{label} velocity max")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Velocity max [m/s]")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3c_velocity_max_time.svg")
    fig.savefig(FIGDIR / "l3c_velocity_max_time.png", dpi=180)
    plt.close(fig)

    # 9. Initial excess-pressure profile.
    initial_profiles = [r for r in profiles if abs(float(r["time_s"])) < 1.0e-12]
    if initial_profiles:
        fig, ax = plt.subplots(figsize=(6.4, 5.0))
        for label in sorted({r["run"] for r in initial_profiles}):
            rs = [r for r in initial_profiles if r["run"] == label]
            ax.plot([float(r["sim_excess"]) for r in rs], [float(r["z_m"]) for r in rs], marker="o", markersize=2, label=f"{label} initial")
        ax.axvline(Q0_EXCESS, color="0.2", linestyle="--", linewidth=1, label="target 10 kPa")
        ax.set_xlabel("Initial excess pore pressure [Pa]")
        ax.set_ylabel("z [m]")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(FIGDIR / "l3c_initial_excess_profile.svg")
        fig.savefig(FIGDIR / "l3c_initial_excess_profile.png", dpi=180)
        plt.close(fig)


def comparison_rows(summary_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in summary_rows:
        rows.append({
            "case": f"L3c consistent initial state {row.get('run', '')}",
            "bottom_rmse_q0_Pa": row.get("bottom_rmse_q0_Pa", ""),
            "profile_rmse_q0_Pa": row.get("profile_rmse_q0_Pa", ""),
            "peak_excess_maxAbs_Pa": row.get("peak_excess_maxAbs_Pa", ""),
            "final_velocity_max_mps": row.get("final_velocity_max_mps", ""),
            "route": "uniform initial excess with zero effective-stress increment",
        })
    candidates = [
        ("L3a initial-pressure gate", Path("../ExternalLoad_L3_InitialPressureGate/l3a_case_summary.csv"), "initial pressure diffusion gate"),
        ("L3b mechanical top-load", Path("../ExternalLoad_L3b_MechanicalTopLoad/l3b_case_summary.csv"), "CPU top material surface force"),
        ("L2 AccInput", Path("../ExternalLoad_L2_PaperAligned/l2_case_summary.csv"), "AccInput body acceleration"),
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
                "final_velocity_max_mps": first.get("final_velocity_max_mps", ""),
                "route": route,
            })
    return rows


def plot_comparison_bars(rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    FIGDIR.mkdir(exist_ok=True)
    names = [str(r["case"]) for r in rows]
    bottom = [float(r.get("bottom_rmse_q0_Pa") or 0.0) for r in rows]
    profile = [float(r.get("profile_rmse_q0_Pa") or 0.0) for r in rows]
    peak = [float(r.get("peak_excess_maxAbs_Pa") or 0.0) for r in rows]
    x = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(8.0, 4.5))
    ax.bar([i - 0.25 for i in x], bottom, width=0.25, label="bottom RMSE")
    ax.bar(x, profile, width=0.25, label="profile RMSE")
    ax.bar([i + 0.25 for i in x], peak, width=0.25, label="peak excess")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=18, ha="right")
    ax.set_ylabel("Pressure [Pa]")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / "l3c_l3a_l3b_l2_pressure_comparison.svg")
    fig.savefig(FIGDIR / "l3c_l3a_l3b_l2_pressure_comparison.png", dpi=180)
    plt.close(fig)


def main() -> None:
    results = {}
    for label, outdir in RUNS:
        res = analyze_run(label, outdir)
        if res is not None:
            results[label] = res
    if not results:
        raise SystemExit("No CPU/GPU PartCsv outputs found for L3c.")

    summary = [res["summary"] for res in results.values()]
    initial_state = []
    stress_state = []
    profiles = [row for res in results.values() for row in res["profiles"]]
    profile_metrics = [row for res in results.values() for row in res["profile_metrics"]]
    bottom = [row for res in results.values() for row in res["bottom"]]
    boundary = [row for res in results.values() for row in res["boundary"]]
    for res in results.values():
        if res["frames"]:
            first = dict(res["frames"][0])
            first["p_w0_target_Pa"] = Q0_EXCESS
            first["initial_excess_target_error_mean_Pa"] = float(first["ExcessPorePress_mean"]) - Q0_EXCESS
            initial_state.append(first)
        stress_state.extend(res["stress"])

    write_csv(SUMMARY_CSV, summary)
    write_csv(INITIAL_STATE_CSV, initial_state)
    write_csv(ANALYTICAL_PROFILES_CSV, profiles)
    write_csv(PROFILE_METRICS_CSV, profile_metrics)
    write_csv(BOTTOM_METRICS_CSV, bottom)
    write_csv(BOUNDARY_METRICS_CSV, boundary)
    write_csv(STRESS_STATE_CSV, stress_state)
    comp = comparison_rows(summary)
    write_csv(COMPARISON_CSV, comp)
    plot_outputs(results)
    plot_comparison_bars(comp)


if __name__ == "__main__":
    main()
