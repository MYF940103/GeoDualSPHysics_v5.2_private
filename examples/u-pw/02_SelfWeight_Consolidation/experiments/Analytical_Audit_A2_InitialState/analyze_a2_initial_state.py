from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Arial"

ROOT = Path(__file__).resolve().parent
EXP = ROOT.parent
G9B = EXP / "GPU_G9b_SelfWeightLong_Xi005"
B5 = EXP / "GPU_B5_BoundaryOperatorLong_Xi005"
DATA_DIR = ROOT / "CaseSW_S2_GPU_A2_InitAudit_gpu_out" / "data"
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

TARGET_PROFILE_TIMES = [0.0, 0.001, 0.002, 0.003, 0.005, 0.01, 0.02, 0.05]
LONG_PROFILE_TIMES = [0.1, 0.5, 1.0, 2.0, 3.6]
E = 2.0e6
NU = 0.3
KW = 2.0e8
POROSITY = 0.3
KPERM = 1.0e-3
RHO_SOIL = 2100.0
RHO_W = 1000.0
G = 9.81
DP = 0.01
KERNEL_H = 0.018
DRAIN_START = 0.002
NTERMS = 500
H = 0.99


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", errors="ignore") as fp:
        sample = fp.read(4096)
        fp.seek(0)
        delim = ";" if sample.count(";") > sample.count(",") else ","
        rows = list(csv.DictReader(fp, delimiter=delim))
    cleaned = []
    for row in rows:
        cleaned.append({str(k).strip(): str(v).strip() for k, v in row.items() if k is not None and str(k).strip()})
    return cleaned


def write_rows(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def f(row: dict[str, object], key: str, default: float = math.nan) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def read_part(path: Path) -> list[dict[str, float]]:
    rows = []
    for raw in read_rows(path):
        if int(float(raw.get("Type", "-1"))) != 3:
            continue
        row = {k: f(raw, k) for k in raw}
        rows.append(row)
    return rows


def frame_time_from_index(idx: int) -> float:
    # The A2 run used TimeOut=0.001; run log differs by about 1e-6 at some frames.
    return idx * 0.001


def part_indices() -> list[int]:
    return sorted(int(p.stem.split("_")[1]) for p in DATA_DIR.glob("PartCsv_*.csv"))


def nearest_frame(target: float, indices: list[int]) -> int:
    return min(indices, key=lambda idx: abs(frame_time_from_index(idx) - target))


def frame_profile(idx: int, zmin_ref: float | None = None, zmax_ref: float | None = None) -> tuple[list[dict[str, float]], dict[str, float]]:
    rows = read_part(DATA_DIR / f"PartCsv_{idx:04d}.csv")
    if not rows:
        raise RuntimeError(f"No material rows in PartCsv_{idx:04d}.csv")
    zvals = [r["Pos.z [m]"] for r in rows]
    zmin = min(zvals) if zmin_ref is None else zmin_ref
    zmax = max(zvals) if zmax_ref is None else zmax_ref
    h = zmax - zmin
    layers: dict[int, list[dict[str, float]]] = {}
    speeds = []
    for row in rows:
        y = max(0.0, min(h, row["Pos.z [m]"] - zmin))
        hydro = RHO_W * G * max(h - y, 0.0)
        excess = row.get("ExcessPorePress", row.get("PorePress", 0.0) - hydro)
        row["y"] = y
        row["hydrostatic"] = hydro
        row["ExcessPorePress"] = excess
        lid = int(round(y / DP))
        layers.setdefault(lid, []).append(row)
        speeds.append(math.sqrt(row["Vel.x [m/s]"] ** 2 + row["Vel.y [m/s]"] ** 2 + row["Vel.z [m/s]"] ** 2))
    prof = []
    for lid, vals in sorted(layers.items()):
        def mean(key: str) -> float:
            return sum(v.get(key, math.nan) for v in vals) / len(vals)
        prof.append(
            {
                "y": mean("y"),
                "z": mean("Pos.z [m]"),
                "PorePress": mean("PorePress"),
                "hydrostatic": mean("hydrostatic"),
                "ExcessPorePress": mean("ExcessPorePress"),
                "PorePressRate": mean("PorePressRate"),
                "DivVel": mean("DivVel"),
                "LapPorePress": mean("LapPorePress"),
                "LapZ": mean("LapZ"),
            }
        )
    bottom = [r for r in rows if r["y"] <= KERNEL_H]
    top = [r for r in rows if r["y"] >= h - KERNEL_H]
    ref = [r for r in rows if KERNEL_H < r["y"] <= 2 * KERNEL_H]
    mean_ex = lambda vals: sum(r["ExcessPorePress"] for r in vals) / len(vals) if vals else math.nan
    metrics = {
        "frame": idx,
        "time": frame_time_from_index(idx),
        "n": len(rows),
        "zmin": zmin,
        "zmax": zmax,
        "H": h,
        "velocity_max": max(speeds),
        "velocity_mean": sum(speeds) / len(speeds),
        "PorePress_min": min(r["PorePress"] for r in rows),
        "PorePress_max": max(r["PorePress"] for r in rows),
        "PorePress_mean": sum(r["PorePress"] for r in rows) / len(rows),
        "Excess_min": min(r["ExcessPorePress"] for r in rows),
        "Excess_max": max(r["ExcessPorePress"] for r in rows),
        "Excess_mean": sum(r["ExcessPorePress"] for r in rows) / len(rows),
        "Excess_maxAbs": max(abs(r["ExcessPorePress"]) for r in rows),
        "bottom_Excess_mean": mean_ex(bottom),
        "bottom_Excess_maxAbs": max(abs(r["ExcessPorePress"]) for r in bottom) if bottom else math.nan,
        "top_Excess_maxAbs": max(abs(r["ExcessPorePress"]) for r in top) if top else math.nan,
        "bottom_ref_Excess_mean": mean_ex(ref),
        "bottom_grad_proxy": mean_ex(bottom) - mean_ex(ref) if bottom and ref else math.nan,
        "PorePressRate_maxAbs": max(abs(r.get("PorePressRate", 0.0)) for r in rows),
    }
    return prof, metrics


def constants(h: float) -> dict[str, float]:
    k_bulk = E / (3.0 * (1.0 - 2.0 * NU))
    g_shear = E / (2.0 * (1.0 + NU))
    m_1d = k_bulk + 4.0 * g_shear / 3.0
    storage = (m_1d * (KW / POROSITY)) / (m_1d + (KW / POROSITY))
    return {
        "M_1D": m_1d,
        "storage_mod": storage,
        "cv_nominal": KPERM * m_1d / (RHO_W * G),
        "cv_storage": KPERM * storage / (RHO_W * G),
        "p0_slope": (KW / POROSITY) * RHO_SOIL * G / (m_1d + KW / POROSITY),
    }


def eq4_initial(y: np.ndarray, h: float, p0_slope: float) -> np.ndarray:
    return p0_slope * (h - y)


def lambdas(h: float, nterms: int = NTERMS) -> np.ndarray:
    n = np.arange(nterms, dtype=float)
    return (2 * n + 1) * math.pi / (2 * h)


def project_initial(y_src: np.ndarray, u_src: np.ndarray, h: float) -> tuple[np.ndarray, np.ndarray]:
    grid = np.linspace(0.0, h, 1201)
    order = np.argsort(y_src)
    u_grid = np.interp(grid, y_src[order], u_src[order])
    u_grid[-1] = 0.0
    lam = lambdas(h)
    coeff = np.array([(2.0 / h) * np.trapezoid(u_grid * np.cos(l * grid), grid) for l in lam])
    return lam, coeff


def eval_series(y: np.ndarray, t: float, t0: float, cv: float, lam: np.ndarray, coeff: np.ndarray) -> np.ndarray:
    tau = max(t - t0, 0.0)
    return np.cos(np.outer(y, lam)) @ (coeff * np.exp(-(lam ** 2) * cv * tau))


def bottom_layer_ref(h: float, t: float, t0: float, cv: float, lam: np.ndarray, coeff: np.ndarray) -> float:
    y = np.linspace(0.0, min(KERNEL_H, h), 80)
    return float(eval_series(y, t, t0, cv, lam, coeff).mean())


def fd_reference(y_src: np.ndarray, u_src: np.ndarray, h: float, times: np.ndarray, t0: float, cv: float, ny: int = 301) -> dict[float, tuple[np.ndarray, np.ndarray]]:
    """Implicit 1D finite-volume reference for u_t=cv*u_yy, u_y(0)=0, u(H)=0."""
    y = np.linspace(0.0, h, ny)
    u = np.interp(y, y_src[np.argsort(y_src)], u_src[np.argsort(y_src)])
    u[-1] = 0.0
    dy = y[1] - y[0]

    def solve_tridiag(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> np.ndarray:
        n = len(d)
        cp = np.zeros(n)
        dp = np.zeros(n)
        cp[0] = c[0] / b[0]
        dp[0] = d[0] / b[0]
        for i in range(1, n):
            den = b[i] - a[i] * cp[i - 1]
            cp[i] = c[i] / den if i < n - 1 else 0.0
            dp[i] = (d[i] - a[i] * dp[i - 1]) / den
        x = np.zeros(n)
        x[-1] = dp[-1]
        for i in range(n - 2, -1, -1):
            x[i] = dp[i] - cp[i] * x[i + 1]
        return x

    out: dict[float, tuple[np.ndarray, np.ndarray]] = {}
    current = 0.0
    for t in sorted(float(v) for v in times):
        target = max(t - t0, 0.0)
        while current < target - 1e-14:
            dt = min(0.002, target - current)
            r = cv * dt / (dy * dy)
            a = np.zeros(ny)
            b = np.zeros(ny)
            c = np.zeros(ny)
            d = u.copy()
            b[0] = 1.0 + 2.0 * r
            c[0] = -2.0 * r
            for i in range(1, ny - 1):
                a[i] = -r
                b[i] = 1.0 + 2.0 * r
                c[i] = -r
            b[-1] = 1.0
            d[-1] = 0.0
            u = solve_tridiag(a, b, c, d)
            current += dt
        out[t] = (y.copy(), u.copy())
    return out


def metric(values: np.ndarray, refs: np.ndarray, times: np.ndarray | None = None, window: tuple[float, float] | None = None) -> dict[str, float]:
    mask = np.isfinite(values) & np.isfinite(refs)
    if times is not None and window is not None:
        mask &= (times >= window[0]) & (times <= window[1])
    err = values[mask] - refs[mask]
    ref = refs[mask]
    if len(err) == 0:
        return {"n": 0, "rmse": math.nan, "mae": math.nan, "max_abs": math.nan, "relative_rmse": math.nan}
    rmse = float(np.sqrt(np.mean(err ** 2)))
    denom = float(np.sqrt(np.mean(ref ** 2)))
    return {
        "n": int(len(err)),
        "rmse": rmse,
        "mae": float(np.mean(np.abs(err))),
        "max_abs": float(np.max(np.abs(err))),
        "relative_rmse": rmse / denom if denom else math.nan,
    }


def long_series(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = read_rows(path)
    times = np.array([f(r, "time") for r in rows], dtype=float)
    vals = np.array([f(r, "bottom_Excess_mean") for r in rows], dtype=float)
    return times, vals


def fit_scale(times: np.ndarray, vals: np.ndarray, t0: float, lam: np.ndarray, coeff: np.ndarray, cv_nom: float, window: tuple[float, float], layer: bool) -> tuple[float, list[dict[str, float]]]:
    rows = []
    best_scale = 1.0
    best_rmse = float("inf")
    for scale in np.linspace(0.75, 1.45, 281):
        cv = cv_nom * scale
        refs = np.array([bottom_layer_ref(H, t, t0, cv, lam, coeff) if layer else eval_series(np.array([0.0]), t, t0, cv, lam, coeff)[0] for t in times])
        m = metric(vals, refs, times, window)
        row = {"scale": float(scale), "window_start": window[0], "window_end": window[1], **m}
        rows.append(row)
        if m["rmse"] < best_rmse:
            best_rmse = m["rmse"]
            best_scale = float(scale)
    return best_scale, rows


def savefig(name: str) -> None:
    for ext in ("svg", "png"):
        plt.savefig(FIGDIR / f"{name}.{ext}", bbox_inches="tight", dpi=180)
    plt.close()


def main() -> None:
    indices = part_indices()
    prof0, met0 = frame_profile(indices[0])
    global H
    H = met0["H"]
    c = constants(H)
    cv_nom = c["cv_nominal"]
    p0_slope = c["p0_slope"]
    zmin = met0["zmin"]
    zmax = met0["zmax"]

    profiles: dict[int, list[dict[str, float]]] = {}
    frame_metrics = []
    for idx in indices:
        prof, met = frame_profile(idx, zmin, zmax)
        profiles[idx] = prof
        frame_metrics.append(met)
    write_rows(ROOT / "a2_frame_metrics.csv", frame_metrics)

    y_grid = np.linspace(0.0, H, 300)
    eq4_grid = eq4_initial(y_grid, H, p0_slope)
    lam_eq4, coeff_eq4 = project_initial(y_grid, eq4_grid, H)

    target_indices = sorted(set(nearest_frame(t, indices) for t in TARGET_PROFILE_TIMES))
    initial_rows = []
    initial_metrics = []
    for idx in target_indices:
        prof = profiles[idx]
        y = np.array([p["y"] for p in prof])
        actual = np.array([p["ExcessPorePress"] for p in prof])
        eq4 = eq4_initial(y, H, p0_slope)
        err = actual - eq4
        bottom_actual = np.mean([p["ExcessPorePress"] for p in prof if p["y"] <= KERNEL_H])
        bottom_eq4 = float(eq4_initial(np.array([0.0]), H, p0_slope)[0])
        corr = float(np.corrcoef(actual, eq4)[0, 1]) if np.std(actual) > 0 and np.std(eq4) > 0 else math.nan
        initial_metrics.append(
            {
                "frame": idx,
                "time": frame_time_from_index(idx),
                "rmse": float(np.sqrt(np.mean(err ** 2))),
                "mean_abs_error": float(np.mean(np.abs(err))),
                "max_abs_error": float(np.max(np.abs(err))),
                "relative_rmse": float(np.sqrt(np.mean(err ** 2)) / np.sqrt(np.mean(eq4 ** 2))),
                "bottom_actual_excess": float(bottom_actual),
                "bottom_eq4_excess": bottom_eq4,
                "bottom_actual_over_eq4": float(bottom_actual / bottom_eq4),
                "shape_correlation": corr,
            }
        )
        for p, eqv, er in zip(prof, eq4, err):
            initial_rows.append({"frame": idx, "time": frame_time_from_index(idx), "y": p["y"], "z": p["z"], "z_norm": p["y"] / H, "actual_excess": p["ExcessPorePress"], "eq4_excess": float(eqv), "error": float(er)})
    write_rows(ROOT / "initial_state_comparison.csv", initial_rows)
    write_rows(ROOT / "generated_initial_profile_metrics.csv", initial_metrics)

    def measured_ref(target: float) -> tuple[float, np.ndarray, np.ndarray]:
        idx = nearest_frame(target, indices)
        prof = profiles[idx]
        y = np.array([p["y"] for p in prof])
        u = np.array([p["ExcessPorePress"] for p in prof])
        lam, coeff = project_initial(y, u, H)
        return frame_time_from_index(idx), lam, coeff

    refs = [
        ("eq4_nominal_cv", DRAIN_START, lam_eq4, coeff_eq4, cv_nom, False),
        ("eq4_nominal_cv_bottom_layer_mean", DRAIN_START, lam_eq4, coeff_eq4, cv_nom, True),
    ]
    measured_targets = [
        (0.002, "measured_t0p002"),
        (0.003, "measured_t0p003"),
        (0.005, "measured_t0p005"),
        (0.010, "measured_t0p010"),
        (0.020, "measured_t0p020"),
    ]
    for target, label in measured_targets:
        t0, lam, coeff = measured_ref(target)
        refs.append((f"{label}_nominal_cv", t0, lam, coeff, cv_nom, False))
        refs.append((f"{label}_nominal_cv_bottom_layer_mean", t0, lam, coeff, cv_nom, True))

    g9b_t, g9b_b = long_series(G9B / "gpu_g9b_frame_metrics.csv")
    b5_t, b5_b = long_series(B5 / "gpu_b5_boundary_operator_frame_metrics.csv")
    long_lines = [("gpu_mode0_xi005_g9b", g9b_t, g9b_b), ("gpu_mode1_xi005_b5", b5_t, b5_b)]

    ref_metrics = []
    bottom_ts = []
    for ref_name, t0, lam, coeff, cv, layer in refs:
        for line, times, vals in long_lines:
            ref_vals = np.array([bottom_layer_ref(H, t, t0, cv, lam, coeff) if layer else eval_series(np.array([0.0]), t, t0, cv, lam, coeff)[0] for t in times])
            m = metric(vals, ref_vals, times, (1.0e-12, float(np.max(times))))
            ref_metrics.append({"reference": ref_name, "line": line, "cv_scale": 1.0, "t0": t0, "bottom_layer_mean_reference": layer, **m})
            for t, v, r in zip(times, vals, ref_vals):
                bottom_ts.append({"reference": ref_name, "line": line, "time": t, "gpu_bottom_excess": v, "reference_bottom_excess": r, "error": v - r})

    fit_rows = []
    sens_rows = []
    effective_rows = []
    t0_meas, lam_meas, coeff_meas = measured_ref(0.002)
    fit_refs = [
        ("eq4", DRAIN_START, lam_eq4, coeff_eq4, False),
        ("measured_t0p002", t0_meas, lam_meas, coeff_meas, False),
        ("measured_t0p002_bottom_layer_mean", t0_meas, lam_meas, coeff_meas, True),
    ]
    t0_meas_010, lam_meas_010, coeff_meas_010 = measured_ref(0.010)
    fit_refs.append(("measured_t0p010", t0_meas_010, lam_meas_010, coeff_meas_010, False))
    windows = [(0.002, 0.5), (0.01, 1.0), (0.002, 3.6)]
    for ref_name, t0, lam, coeff, layer in fit_refs:
        for line, times, vals in long_lines:
            for window in windows:
                best, rows = fit_scale(times, vals, t0, lam, coeff, cv_nom, window, layer)
                for row in rows:
                    sens_rows.append({"reference": ref_name, "line": line, "bottom_layer_mean_reference": layer, **row})
                cv = cv_nom * best
                ref_vals = np.array([bottom_layer_ref(H, t, t0, cv, lam, coeff) if layer else eval_series(np.array([0.0]), t, t0, cv, lam, coeff)[0] for t in times])
                m = metric(vals, ref_vals, times, window)
                fit_row = {"reference": ref_name, "line": line, "window_start": window[0], "window_end": window[1], "best_cv_scale": best, "best_cv": cv, "bottom_layer_mean_reference": layer, **m}
                fit_rows.append(fit_row)
                effective_rows.append(fit_row)
                if window == (0.002, 3.6):
                    ref_metrics.append({"reference": f"{ref_name}_bestfit_cv", "line": line, "cv_scale": best, "t0": t0, "bottom_layer_mean_reference": layer, **metric(vals, ref_vals, times, (1.0e-12, float(np.max(times))))})
                    for t, v, r in zip(times, vals, ref_vals):
                        bottom_ts.append({"reference": f"{ref_name}_bestfit_cv", "line": line, "time": t, "gpu_bottom_excess": v, "reference_bottom_excess": r, "error": v - r})

    write_rows(ROOT / "measured_reference_metrics.csv", ref_metrics)
    write_rows(ROOT / "analytical_vs_measured_reference_bottom_timeseries.csv", bottom_ts)
    write_rows(ROOT / "cv_fit_metrics.csv", fit_rows)
    write_rows(ROOT / "cv_fit_sensitivity.csv", sens_rows)
    write_rows(ROOT / "effective_cv_summary.csv", effective_rows)

    profile_rows = []
    best_cv = next(r for r in fit_rows if r["reference"] == "measured_t0p002" and r["line"] == "gpu_mode0_xi005_g9b" and r["window_start"] == 0.002 and r["window_end"] == 3.6)["best_cv"]
    profile_refs = [
        ("eq4_nominal_cv", DRAIN_START, lam_eq4, coeff_eq4, cv_nom),
        ("measured_t0p002_nominal_cv", t0_meas, lam_meas, coeff_meas, cv_nom),
        ("measured_t0p002_bestfit_cv", t0_meas, lam_meas, coeff_meas, best_cv),
        ("measured_t0p010_nominal_cv", t0_meas_010, lam_meas_010, coeff_meas_010, cv_nom),
    ]
    yp = np.linspace(0.0, H, 101)
    for name, t0, lam, coeff, cv in profile_refs:
        for t in LONG_PROFILE_TIMES:
            vals = eval_series(yp, t, t0, cv, lam, coeff)
            for yy, vv in zip(yp, vals):
                profile_rows.append({"reference": name, "time": t, "y": yy, "z": zmin + yy, "z_norm": yy / H, "excess": vv})
    write_rows(ROOT / "analytical_vs_measured_reference_profiles.csv", profile_rows)

    # Independent finite-volume reference check for the two most relevant initial profiles.
    fd_rows = []
    fd_ts_rows = []
    fd_sources = [
        ("eq4", DRAIN_START, y_grid, eq4_grid, lam_eq4, coeff_eq4, cv_nom),
        ("measured_t0p010", t0_meas_010, np.array([p["y"] for p in profiles[nearest_frame(0.010, indices)]]), np.array([p["ExcessPorePress"] for p in profiles[nearest_frame(0.010, indices)]]), lam_meas_010, coeff_meas_010, cv_nom),
    ]
    for name, t0, y0, u0, lam, coeff, cv in fd_sources:
        fd = fd_reference(y0, u0, H, g9b_t, t0, cv)
        fd_bottom = np.array([fd[float(t)][1][0] for t in g9b_t])
        series_bottom = np.array([eval_series(np.array([0.0]), float(t), t0, cv, lam, coeff)[0] for t in g9b_t])
        fd_m = metric(g9b_b, fd_bottom, g9b_t, (1.0e-12, float(np.max(g9b_t))))
        series_m = metric(fd_bottom, series_bottom, g9b_t, (1.0e-12, float(np.max(g9b_t))))
        fd_rows.append({"reference": name, "comparison": "gpu_vs_fd", **fd_m})
        fd_rows.append({"reference": name, "comparison": "fd_vs_series", **series_m})
        for t, gpu, fdv, ser in zip(g9b_t, g9b_b, fd_bottom, series_bottom):
            fd_ts_rows.append({"reference": name, "time": t, "gpu_bottom_excess": gpu, "fd_bottom_excess": fdv, "series_bottom_excess": ser, "gpu_minus_fd": gpu - fdv, "fd_minus_series": fdv - ser})
    write_rows(ROOT / "fd_reference_metrics.csv", fd_rows)
    write_rows(ROOT / "fd_reference_bottom_timeseries.csv", fd_ts_rows)

    # Figures
    plt.figure(figsize=(6.3, 4.5))
    plt.plot(eq4_grid / 1000, y_grid / H, "k--", lw=2, label="Eq.(4)")
    for target in [0.002, 0.003, 0.005]:
        idx = nearest_frame(target, indices)
        prof = profiles[idx]
        plt.plot([p["ExcessPorePress"] / 1000 for p in prof], [p["y"] / H for p in prof], marker="o", ms=3, lw=1.3, label=f"GPU t={frame_time_from_index(idx):.3f}s")
    plt.xlabel("Excess pore pressure, kPa")
    plt.ylabel("Normalized height z/H")
    plt.title("Generated initial excess vs Eq.(4)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    savefig("actual_initial_excess_vs_eq4_profiles")

    plt.figure(figsize=(6.3, 4.5))
    plt.plot(eq4_grid / 1000, y_grid / H, "k--", lw=2, label="Eq.(4)")
    for target in [0.0, 0.001, 0.002, 0.003, 0.005, 0.01, 0.02]:
        idx = nearest_frame(target, indices)
        prof = profiles[idx]
        plt.plot([p["ExcessPorePress"] / 1000 for p in prof], [p["y"] / H for p in prof], lw=1.1, label=f"{frame_time_from_index(idx):.3f}s")
    plt.xlabel("Excess pore pressure, kPa")
    plt.ylabel("Normalized height z/H")
    plt.title("Early generated excess profiles")
    plt.legend(ncol=2, fontsize=8)
    plt.grid(True, alpha=0.3)
    savefig("early_time_excess_profiles_0_to_0p02s")

    plt.figure(figsize=(6.4, 4.0))
    times_short = np.array([m["time"] for m in frame_metrics])
    bottom_short = np.array([m["bottom_Excess_mean"] for m in frame_metrics])
    plt.plot(times_short, bottom_short / 1000, "o-", ms=3, label="A2 GPU bottom layer")
    eq4_short = np.array([eval_series(np.array([0.0]), t, DRAIN_START, cv_nom, lam_eq4, coeff_eq4)[0] for t in times_short])
    plt.plot(times_short, eq4_short / 1000, "k--", label="Eq.(4)+nominal cv")
    plt.axvline(DRAIN_START, color="0.5", ls=":", label="drain start")
    plt.xlabel("Time, s")
    plt.ylabel("Bottom excess pore pressure, kPa")
    plt.title("Early-time bottom excess zoom")
    plt.legend()
    plt.grid(True, alpha=0.3)
    savefig("bottom_excess_early_time_zoom")

    plt.figure(figsize=(6.8, 4.2))
    plt.plot(g9b_t, g9b_b / 1000, "o-", ms=3, lw=1.2, label="GPU G9b mode=0 xi=0.05")
    for ref in ["eq4_nominal_cv", "measured_t0p002_nominal_cv", "measured_t0p010_nominal_cv", "measured_t0p002_bestfit_cv"]:
        rows = [r for r in bottom_ts if r["reference"] == ref and r["line"] == "gpu_mode0_xi005_g9b"]
        plt.plot([r["time"] for r in rows], [r["reference_bottom_excess"] / 1000 for r in rows], lw=1.5, label=ref)
    plt.xlabel("Time, s")
    plt.ylabel("Bottom excess pore pressure, kPa")
    plt.title("Measured-initial references vs long-run bottom excess")
    plt.legend(fontsize=8)
    plt.grid(True, alpha=0.3)
    savefig("measured_initial_reference_bottom_excess_time")

    plt.figure(figsize=(6.8, 4.2))
    for ref in ["eq4", "measured_t0p002", "measured_t0p002_bottom_layer_mean"]:
        rows = [r for r in sens_rows if r["reference"] == ref and r["line"] == "gpu_mode0_xi005_g9b" and r["window_start"] == 0.002 and r["window_end"] == 3.6]
        plt.plot([r["scale"] for r in rows], [r["relative_rmse"] for r in rows], label=ref)
    plt.xlabel("cv scale")
    plt.ylabel("Relative RMSE")
    plt.title("Effective cv sensitivity, G9b bottom excess")
    plt.legend()
    plt.grid(True, alpha=0.3)
    savefig("cv_fit_sensitivity")

    plt.figure(figsize=(6.8, 4.2))
    bar_refs = ["eq4_nominal_cv", "measured_t0p002_nominal_cv", "measured_t0p010_nominal_cv", "measured_t0p002_bestfit_cv", "measured_t0p002_nominal_cv_bottom_layer_mean"]
    vals = [next(r for r in ref_metrics if r["reference"] == br and r["line"] == "gpu_mode0_xi005_g9b")["relative_rmse"] for br in bar_refs]
    plt.bar(bar_refs, vals)
    plt.xticks(rotation=25, ha="right")
    plt.ylabel("Relative RMSE")
    plt.title("Residual error after initial/cv calibration")
    plt.grid(True, axis="y", alpha=0.3)
    savefig("residual_error_after_calibration")

    plt.figure(figsize=(6.8, 4.4))
    for ref, style in [("eq4_nominal_cv", "--"), ("measured_t0p002_nominal_cv", "-"), ("measured_t0p010_nominal_cv", "-."), ("measured_t0p002_bestfit_cv", ":")]:
        rows = [r for r in profile_rows if r["reference"] == ref and abs(r["time"] - 0.5) < 1e-12]
        plt.plot([r["excess"] / 1000 for r in rows], [r["z_norm"] for r in rows], style, lw=1.8, label=f"{ref}, t=0.5s")
    plt.xlabel("Excess pore pressure, kPa")
    plt.ylabel("Normalized height z/H")
    plt.title("Reference profile variants")
    plt.legend(fontsize=8)
    plt.grid(True, alpha=0.3)
    savefig("measured_initial_reference_vs_original_analytical")

    plt.figure(figsize=(6.8, 4.2))
    rows = [r for r in fit_rows if r["line"] == "gpu_mode0_xi005_g9b" and r["window_start"] == 0.002]
    plt.bar([r["reference"] + "\n" + str(r["window_end"]) + "s" for r in rows], [r["best_cv_scale"] for r in rows])
    plt.axhline(1.0, color="k", ls="--", lw=1)
    plt.ylabel("Best-fit cv scale")
    plt.title("Effective cv summary")
    plt.xticks(rotation=25, ha="right")
    plt.grid(True, axis="y", alpha=0.3)
    savefig("effective_cv_reference_comparison")

    plt.figure(figsize=(6.8, 4.2))
    plt.plot(g9b_t, g9b_b / 1000, "ko-", ms=3, lw=1.2, label="GPU G9b")
    for name in ["eq4", "measured_t0p010"]:
        rows_fd = [r for r in fd_ts_rows if r["reference"] == name]
        plt.plot([r["time"] for r in rows_fd], [r["fd_bottom_excess"] / 1000 for r in rows_fd], lw=1.5, label=f"FD {name}")
        plt.plot([r["time"] for r in rows_fd], [r["series_bottom_excess"] / 1000 for r in rows_fd], "--", lw=1.2, label=f"Series {name}")
    plt.xlabel("Time, s")
    plt.ylabel("Bottom excess pore pressure, kPa")
    plt.title("Finite-volume vs series reference variants")
    plt.legend(fontsize=8)
    plt.grid(True, alpha=0.3)
    savefig("fd_reference_variants")

    # Local report draft, copied to src/papers after inspection.
    key_t2 = min(initial_metrics, key=lambda r: abs(r["time"] - 0.002))
    get_metric = lambda ref: next(r for r in ref_metrics if r["reference"] == ref and r["line"] == "gpu_mode0_xi005_g9b")
    eq4_nom = get_metric("eq4_nominal_cv")
    meas_nom = get_metric("measured_t0p002_nominal_cv")
    meas010_nom = get_metric("measured_t0p010_nominal_cv")
    meas_best = get_metric("measured_t0p002_bestfit_cv")
    layer_nom = get_metric("measured_t0p002_nominal_cv_bottom_layer_mean")
    best_full = next(r for r in fit_rows if r["reference"] == "measured_t0p002" and r["line"] == "gpu_mode0_xi005_g9b" and r["window_start"] == 0.002 and r["window_end"] == 3.6)
    report = f"""# A2 Initial-State Calibration Audit

Date: 2026-05-12

No source code was modified. The only solver run was a GPU Release targeted
short run to `TimeMax=0.05 s` with `TimeOut=0.001 s`.

## Targeted Short-Run Result

- frames retained: {len(frame_metrics)}
- final retained time: {frame_metrics[-1]['time']:.3f} s
- material particles: {int(frame_metrics[0]['n'])}
- solver status: code=0, excluded=0

## Eq.(4) vs Generated Initial State

Closest retained frame to drainage activation:

- frame: {int(key_t2['frame'])}
- time: {key_t2['time']:.6f} s
- profile RMSE vs Eq.(4): {key_t2['rmse']:.3f} Pa
- relative profile RMSE: {key_t2['relative_rmse']:.5f}
- generated bottom / Eq.(4) bottom: {key_t2['bottom_actual_over_eq4']:.5f}
- generated bottom excess: {key_t2['bottom_actual_excess']:.3f} Pa
- Eq.(4) bottom excess: {key_t2['bottom_eq4_excess']:.3f} Pa

The generated state at drainage activation is close to the Eq.(4) shape but is
not identical. It is a dynamic solver state rather than an imposed analytical
initial condition.

## Bottom Excess Reference Metrics for G9b mode=0 xi=0.05

| Reference | RMSE (Pa) | Relative RMSE |
|---|---:|---:|
| Eq.(4) + nominal cv | {eq4_nom['rmse']:.3f} | {eq4_nom['relative_rmse']:.5f} |
| measured t≈0.002 + nominal cv | {meas_nom['rmse']:.3f} | {meas_nom['relative_rmse']:.5f} |
| measured t≈0.010 + nominal cv | {meas010_nom['rmse']:.3f} | {meas010_nom['relative_rmse']:.5f} |
| measured t≈0.002 + nominal cv + bottom-layer mean | {layer_nom['rmse']:.3f} | {layer_nom['relative_rmse']:.5f} |
| measured t≈0.002 + best-fit cv | {meas_best['rmse']:.3f} | {meas_best['relative_rmse']:.5f} |

Best-fit cv scale for measured t≈0.002 over the full retained long-run window:

```text
{best_full['best_cv_scale']:.4f}
```

## Interpretation

Using the frame exactly at t≈0.002 s is not a good physical analytical initial
state because the coupled self-weight response is still being generated. The
bottom excess undershoots Eq.(4) at t≈0.002 s, overshoots it at t≈0.003-0.005 s,
and relaxes closer to Eq.(4) by t≈0.01-0.02 s. This shows that the early dynamic
initialization is a real source of mismatch. The effective cv/time-factor signal
still remains important once a usable initial profile is selected.

Boundary mode=1 remains useful as an experimental strict-boundary path, but A2
does not justify promoting it to default. Corrected-gradient PR operators remain
deferred.
"""
    (ROOT / "a2_initial_state_calibration_report_local.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
