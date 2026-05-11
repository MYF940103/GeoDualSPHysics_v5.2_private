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
A2 = EXP / "Analytical_Audit_A2_InitialState"
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

TIMES = [0.1, 0.5, 1.0, 2.0, 3.6]
CV_SCALE_EFF = 1.1175
CV_SCALE_EARLY_1 = 1.1550
CV_SCALE_EARLY_2 = 1.1975

E = 2.0e6
NU = 0.3
KW = 2.0e8
POROSITY = 0.3
KPERM = 1.0e-3
RHO_SOIL = 2100.0
RHO_W = 1000.0
G = 9.81
DRAIN_START = 0.002
NTERMS = 600


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", errors="ignore") as fp:
        sample = fp.read(4096)
        fp.seek(0)
        delim = ";" if sample.count(";") > sample.count(",") else ","
        return [{str(k).strip(): str(v).strip() for k, v in row.items() if k is not None and str(k).strip()} for row in csv.DictReader(fp, delimiter=delim)]


def write_rows(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, object], key: str, default: float = math.nan) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


g9b_rows = read_rows(G9B / "gpu_g9b_frame_metrics.csv")
b5_rows = read_rows(B5 / "gpu_b5_boundary_operator_frame_metrics.csv")
profile_rows = read_rows(B5 / "gpu_b5_boundary_vs_analytical_profile_timeseries.csv")
a2_cv_rows = read_rows(A2 / "cv_fit_sensitivity.csv")

if not g9b_rows:
    raise RuntimeError("Missing G9b frame metrics")

ZMIN = f(g9b_rows[0], "zmin")
ZMAX = f(g9b_rows[0], "zmax")
H = ZMAX - ZMIN
K_BULK = E / (3.0 * (1.0 - 2.0 * NU))
G_SHEAR = E / (2.0 * (1.0 + NU))
M_1D = K_BULK + 4.0 * G_SHEAR / 3.0
CV_NOM = KPERM * M_1D / (RHO_W * G)
P0_SLOPE = (KW / POROSITY) * RHO_SOIL * G / (M_1D + KW / POROSITY)


def lambda_n(n: int) -> float:
    return (2 * n + 1) * math.pi / (2 * H)


def coeff_n(n: int) -> float:
    lam = lambda_n(n)
    return 2.0 * P0_SLOPE / (H * lam * lam)


LAM = np.array([lambda_n(i) for i in range(NTERMS)])
COEFF = np.array([coeff_n(i) for i in range(NTERMS)])


def hydrostatic_y(y: np.ndarray | float) -> np.ndarray | float:
    return RHO_W * G * np.maximum(H - y, 0.0)


def excess_series(y: np.ndarray, t: float, cv_scale: float = 1.0) -> np.ndarray:
    tau = max(t - DRAIN_START, 0.0)
    cv = CV_NOM * cv_scale
    return np.cos(np.outer(y, LAM)) @ (COEFF * np.exp(-(LAM ** 2) * cv * tau))


def bottom_excess(t: float, cv_scale: float = 1.0) -> float:
    return float(excess_series(np.array([0.0]), t, cv_scale)[0])


def bottom_line(rows: list[dict[str, str]], key: str = "bottom_Excess_mean") -> tuple[np.ndarray, np.ndarray]:
    times = np.array([f(r, "time") for r in rows], dtype=float)
    vals = np.array([f(r, key) for r in rows], dtype=float)
    order = np.argsort(times)
    return times[order], vals[order]


def envelope_line(rows: list[dict[str, str]]) -> tuple[np.ndarray, np.ndarray]:
    times = np.array([f(r, "time") for r in rows], dtype=float)
    vals = np.array([f(r, "Excess_maxAbs") for r in rows], dtype=float)
    order = np.argsort(times)
    return times[order], vals[order]


def metric(values: np.ndarray, refs: np.ndarray, times: np.ndarray | None = None, min_time: float = 1.0e-12) -> dict[str, float]:
    mask = np.isfinite(values) & np.isfinite(refs)
    if times is not None:
        mask &= times > min_time
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


def profile(line: str, quantity: str, t: float) -> tuple[np.ndarray, np.ndarray]:
    rows = [
        r
        for r in profile_rows
        if r.get("line") == line and r.get("quantity") == quantity and abs(f(r, "time") - t) < 1e-9
    ]
    rows.sort(key=lambda r: f(r, "z_norm"))
    return np.array([f(r, "z_norm") for r in rows]), np.array([f(r, "value") for r in rows])


def analytical_profile(quantity: str, t: float, cv_scale: float) -> tuple[np.ndarray, np.ndarray]:
    z_norm = np.linspace(0.0, 1.0, 200)
    y = z_norm * H
    excess = excess_series(y, t, cv_scale)
    if quantity == "ExcessPorePress":
        return z_norm, excess
    return z_norm, excess + hydrostatic_y(y)


def interp_to(x_src: np.ndarray, y_src: np.ndarray, x_dst: np.ndarray) -> np.ndarray:
    order = np.argsort(x_src)
    return np.interp(x_dst, x_src[order], y_src[order])


def savefig(name: str) -> None:
    for ext in ("svg", "png", "pdf"):
        plt.savefig(FIGDIR / f"{name}.{ext}", bbox_inches="tight", dpi=220)
    plt.close()


def make_bottom_figure() -> None:
    t0, g0 = bottom_line(g9b_rows)
    t1, g1 = bottom_line(b5_rows)
    ref_nom = np.array([bottom_excess(t, 1.0) for t in t0])
    ref_eff = np.array([bottom_excess(t, CV_SCALE_EFF) for t in t0])
    plt.figure(figsize=(6.6, 4.2))
    plt.plot(t0, g0 / 1000, "o-", ms=3, lw=1.4, label="GPU mode=0, xi=0.05")
    plt.plot(t1, g1 / 1000, "-", lw=1.0, color="tab:gray", label="GPU mode=1, xi=0.05 (experimental)")
    plt.plot(t0, ref_nom / 1000, "k--", lw=1.8, label="Nominal analytical")
    plt.plot(t0, ref_eff / 1000, color="tab:red", lw=2.0, label=r"Effective reference, $c_v\times1.1175$")
    plt.xlabel("Time, s")
    plt.ylabel("Bottom excess pore pressure, kPa")
    plt.title("Self-weight Scenario 2 bottom excess dissipation")
    plt.legend(fontsize=8)
    plt.grid(True, alpha=0.3)
    savefig("figure1_bottom_excess_time")


def make_profile_figure(quantity: str, name: str, ylabel: str, title: str) -> None:
    fig, axes = plt.subplots(1, len(TIMES), figsize=(15.5, 3.5), sharey=True)
    for ax, t in zip(axes, TIMES):
        z0, v0 = profile("gpu_mode0_xi005_approx", quantity, t)
        z1, v1 = profile("gpu_mode1_xi005_b5", quantity, t)
        za, nom = analytical_profile(quantity, t, 1.0)
        _, eff = analytical_profile(quantity, t, CV_SCALE_EFF)
        if len(z0):
            ax.plot(v0 / 1000, z0, "o", ms=3, color="tab:blue", label="GPU mode=0")
        if len(z1):
            ax.plot(v1 / 1000, z1, "-", lw=1.0, color="0.55", label="GPU mode=1")
        ax.plot(nom / 1000, za, "k--", lw=1.6, label="Nominal")
        ax.plot(eff / 1000, za, color="tab:red", lw=1.8, label=r"$c_v\times1.1175$")
        if quantity == "PorePress":
            y = np.linspace(0.0, H, 200)
            ax.plot(hydrostatic_y(y) / 1000, y / H, ":", color="tab:green", lw=1.3, label="Hydrostatic")
        ax.set_title(f"t={t:g}s")
        ax.grid(True, alpha=0.25)
        ax.set_xlabel(ylabel)
    axes[0].set_ylabel("Normalized height z/H")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=5, fontsize=8, frameon=False)
    fig.suptitle(title, y=1.08)
    savefig(name)


def make_envelope_figure() -> None:
    t0, env0 = envelope_line(g9b_rows)
    t1, env1 = envelope_line(b5_rows)
    ref_nom = np.array([bottom_excess(t, 1.0) for t in t0])
    ref_eff = np.array([bottom_excess(t, CV_SCALE_EFF) for t in t0])
    plt.figure(figsize=(6.6, 4.2))
    plt.plot(t0, env0 / 1000, "o-", ms=3, lw=1.4, label="GPU mode=0 envelope")
    plt.plot(t1, env1 / 1000, "-", lw=1.0, color="0.55", label="GPU mode=1 envelope")
    plt.plot(t0, ref_nom / 1000, "k--", lw=1.8, label="Nominal bottom reference")
    plt.plot(t0, ref_eff / 1000, color="tab:red", lw=2.0, label=r"Effective reference, $c_v\times1.1175$")
    plt.xlabel("Time, s")
    plt.ylabel("Excess pore-pressure envelope, kPa")
    plt.title("Excess envelope decay")
    plt.legend(fontsize=8)
    plt.grid(True, alpha=0.3)
    savefig("figure4_excess_envelope_decay")


def make_error_figure() -> None:
    t0, g0 = bottom_line(g9b_rows)
    ref_nom = np.array([bottom_excess(t, 1.0) for t in t0])
    ref_eff = np.array([bottom_excess(t, CV_SCALE_EFF) for t in t0])
    mask = t0 > 0
    rel_nom = np.abs((g0[mask] - ref_nom[mask]) / ref_nom[mask])
    rel_eff = np.abs((g0[mask] - ref_eff[mask]) / ref_eff[mask])
    plt.figure(figsize=(6.6, 4.2))
    plt.plot(t0[mask], rel_nom * 100, "o-", ms=3, label="GPU vs nominal")
    plt.plot(t0[mask], rel_eff * 100, "o-", ms=3, color="tab:red", label=r"GPU vs $c_v\times1.1175$")
    plt.xlabel("Time, s")
    plt.ylabel("Absolute relative bottom-excess error, %")
    plt.title("Bottom excess relative error")
    plt.legend()
    plt.grid(True, alpha=0.3)
    savefig("figure5_relative_error_time")


def make_cv_sensitivity() -> None:
    rows = [
        r
        for r in a2_cv_rows
        if r.get("reference") == "eq4"
        and r.get("line") == "gpu_mode0_xi005_g9b"
        and abs(f(r, "window_start") - 0.002) < 1e-12
        and abs(f(r, "window_end") - 3.6) < 1e-12
    ]
    rows.sort(key=lambda r: f(r, "scale"))
    x = np.array([f(r, "scale") for r in rows])
    y = np.array([f(r, "relative_rmse") for r in rows])
    plt.figure(figsize=(6.6, 4.2))
    plt.plot(x, y * 100, color="tab:blue", lw=1.8)
    for scale, label, color in [
        (1.0, "nominal", "k"),
        (CV_SCALE_EFF, "full-window best", "tab:red"),
        (CV_SCALE_EARLY_1, "0.01-1.0 s", "tab:orange"),
        (CV_SCALE_EARLY_2, "0.002-0.5 s", "tab:purple"),
    ]:
        yy = np.interp(scale, x, y) * 100
        plt.axvline(scale, color=color, ls="--", lw=1.1)
        plt.plot([scale], [yy], "o", color=color, label=f"{label}: {scale:.4g}")
    plt.xlabel("cv scale")
    plt.ylabel("Bottom excess relative RMSE, %")
    plt.title("Effective time-factor sensitivity")
    plt.legend(fontsize=8)
    plt.grid(True, alpha=0.3)
    savefig("figure6_cv_sensitivity")


def write_metrics() -> None:
    t0, g0 = bottom_line(g9b_rows)
    t1, g1 = bottom_line(b5_rows)
    ref_nom = np.array([bottom_excess(t, 1.0) for t in t0])
    ref_eff = np.array([bottom_excess(t, CV_SCALE_EFF) for t in t0])
    metric_rows = []
    m_nom = metric(g0, ref_nom, t0)
    m_eff = metric(g0, ref_eff, t0)
    m_mode = metric(np.interp(t0, t1, g1), g0, t0)
    metric_rows.append({"quantity": "bottom_excess", "comparison": "GPU mode0 vs nominal analytical", **m_nom})
    metric_rows.append({"quantity": "bottom_excess", "comparison": "GPU mode0 vs calibrated effective", **m_eff})
    metric_rows.append({"quantity": "bottom_excess", "comparison": "GPU mode1 vs GPU mode0", **m_mode})
    improvement = 100.0 * (m_nom["relative_rmse"] - m_eff["relative_rmse"]) / m_nom["relative_rmse"]
    metric_rows.append({"quantity": "bottom_excess", "comparison": "calibrated improvement percent", "n": m_nom["n"], "rmse": math.nan, "mae": math.nan, "max_abs": math.nan, "relative_rmse": improvement})

    for quantity in ["ExcessPorePress", "PorePress"]:
        for t in TIMES:
            z0, v0 = profile("gpu_mode0_xi005_approx", quantity, t)
            if not len(z0):
                continue
            za, nom = analytical_profile(quantity, t, 1.0)
            _, eff = analytical_profile(quantity, t, CV_SCALE_EFF)
            nom_i = interp_to(za, nom, z0)
            eff_i = interp_to(za, eff, z0)
            metric_rows.append({"quantity": f"{quantity}_profile_t{t:g}", "comparison": "GPU mode0 vs nominal analytical", **metric(v0, nom_i)})
            metric_rows.append({"quantity": f"{quantity}_profile_t{t:g}", "comparison": "GPU mode0 vs calibrated effective", **metric(v0, eff_i)})
    write_rows(ROOT / "paper_figure_metrics.csv", metric_rows)

    write_rows(
        ROOT / "calibrated_reference_metrics.csv",
        [
            {"reference": "nominal analytical", "cv_scale": 1.0, "bottom_relative_rmse": m_nom["relative_rmse"], "bottom_rmse": m_nom["rmse"]},
            {"reference": "calibrated effective analytical", "cv_scale": CV_SCALE_EFF, "bottom_relative_rmse": m_eff["relative_rmse"], "bottom_rmse": m_eff["rmse"]},
            {"reference": "improvement", "cv_scale": "", "bottom_relative_rmse": improvement, "bottom_rmse": m_nom["rmse"] - m_eff["rmse"]},
        ],
    )

    rows = [
        r
        for r in a2_cv_rows
        if r.get("reference") == "eq4"
        and r.get("line") == "gpu_mode0_xi005_g9b"
        and abs(f(r, "window_start") - 0.002) < 1e-12
        and abs(f(r, "window_end") - 3.6) < 1e-12
        and f(r, "scale") in {1.0, CV_SCALE_EFF, CV_SCALE_EARLY_1, CV_SCALE_EARLY_2}
    ]
    # Floating point exact matches may miss grid rows, so write interpolated values.
    sens_all = [
        r
        for r in a2_cv_rows
        if r.get("reference") == "eq4"
        and r.get("line") == "gpu_mode0_xi005_g9b"
        and abs(f(r, "window_start") - 0.002) < 1e-12
        and abs(f(r, "window_end") - 3.6) < 1e-12
    ]
    sx = np.array([f(r, "scale") for r in sens_all])
    sy = np.array([f(r, "relative_rmse") for r in sens_all])
    summary = []
    for scale, note in [(1.0, "nominal"), (CV_SCALE_EFF, "full-window best"), (CV_SCALE_EARLY_1, "A2 0.01-1.0 s best"), (CV_SCALE_EARLY_2, "A2 0.002-0.5 s best")]:
        summary.append({"cv_scale": scale, "relative_rmse": float(np.interp(scale, sx, sy)), "note": note})
    write_rows(ROOT / "cv_sensitivity_summary.csv", summary)


def write_note() -> str:
    metrics = read_rows(ROOT / "calibrated_reference_metrics.csv")
    by_ref = {r["reference"]: r for r in metrics}
    nom_rel = f(by_ref["nominal analytical"], "bottom_relative_rmse")
    eff_rel = f(by_ref["calibrated effective analytical"], "bottom_relative_rmse")
    nom_rmse = f(by_ref["nominal analytical"], "bottom_rmse")
    eff_rmse = f(by_ref["calibrated effective analytical"], "bottom_rmse")
    improvement = 100.0 * (nom_rel - eff_rel) / nom_rel
    note = f"""# Calibrated Reference Note for Self-Weight Scenario 2

Date: 2026-05-12

## Purpose

This note documents the paper-figure reference lines used for the self-weight
Scenario 2 GPU long-run validation. The figures compare the GPU `xi=0.05`
result against both the nominal Supporting Materials one-dimensional
consolidation solution and a calibrated effective time-factor reference.

## Nominal Analytical Solution

The nominal reference uses the Supporting Materials Eq. (4) undrained
self-weight excess profile as the initial condition and the top-drained /
bottom-no-flux eigenbasis for a one-dimensional consolidation column:

```text
u(y,t) = sum A_n cos(lambda_n y) exp(-lambda_n^2 cv (t - t_drain))
lambda_n = (2n+1) pi / (2H)
```

with `t_drain=0.002 s`. Total pore pressure is reconstructed as
`p = p_hydro + u`.

This analytical reference is a quasi-static 1D consolidation reduction. It is
not the raw particle PR equation, because the PR implementation evolves:

```text
PorePressRate = Kw/n * (-DivVel + k/(rho_w*g) LapPorePress + k LapZ)
```

and the apparent storage enters through the coupled dynamic volumetric
response.

## A1/A2 Audit Summary

A1 showed that the boundary-operator mode does not control the remaining
bottom-excess discrepancy: GPU `PorePressureBoundaryOperator=0` and `1` give
nearly identical long-run bottom errors.

A2 showed that the actual generated state at `t~0.002 s` is not the Eq. (4)
profile. The generated bottom excess at the drainage activation frame is only
about `66.96%` of Eq. (4), then overshoots Eq. (4) at `0.003-0.005 s`, and
relaxes close to Eq. (4) around `0.01-0.02 s`. However, using the raw measured
early profile as the reference initial condition does not improve the long-run
comparison. The nominal Eq. (4) profile remains the most useful baseline
reference.

## Effective cv Calibration

The calibrated effective reference uses the same Eq. (4) initial profile and
the same boundary eigenbasis, but scales the consolidation coefficient:

```text
cv_eff = 1.1175 cv_nominal
```

This is not interpreted as a material permeability or material-parameter
recalibration. It is an apparent time-factor sensitivity that compactly
measures the difference between the quasi-static analytical reduction and the
dynamic coupled SPH response, including explicit volumetric storage, damping,
Shepard regularization, and particle operator effects.

## Comparison Results

For GPU `mode=0`, `xi=0.05` bottom excess pressure:

| Reference | RMSE (Pa) | Relative RMSE |
|---|---:|---:|
| nominal analytical | {nom_rmse:.2f} | {100*nom_rel:.2f}% |
| calibrated effective reference | {eff_rmse:.2f} | {100*eff_rel:.2f}% |

The calibrated effective reference reduces the relative bottom-excess RMSE by
approximately `{improvement:.1f}%`.

## Boundary and Corrected-Gradient Status

`PorePressureBoundaryOperator=1` remains an experimental strict-boundary path.
It is not promoted to the default production mode because it did not improve
the long-run analytical discrepancy.

Corrected-gradient PR operators remain deferred. The current discrepancy is
better described by effective time-factor / storage mapping than by a boundary
or corrected-gradient issue.

## Recommended Manuscript Wording

The nominal one-dimensional consolidation solution reproduces the overall
dissipation trend but slightly underestimates the apparent dissipation rate
observed in the fully coupled SPH simulation. A modest effective time-factor
adjustment, `cv_eff = 1.1175 cv`, reduces the bottom excess-pressure relative
RMSE from approximately 7.6% to 2.0%. This adjustment is not interpreted as a
material-parameter recalibration, but as a compact measure of the difference
between the quasi-static analytical reduction and the dynamic coupled SPH
response, including explicit volumetric storage, damping, Shepard
regularization, and particle-based operator effects.
"""
    return note


def main() -> None:
    make_bottom_figure()
    make_profile_figure("ExcessPorePress", "figure2_excess_profiles", "Excess pore pressure, kPa", "Excess pressure profiles")
    make_profile_figure("PorePress", "figure3_total_pore_pressure_profiles", "Total pore pressure, kPa", "Total pore pressure profiles")
    make_envelope_figure()
    make_error_figure()
    make_cv_sensitivity()
    write_metrics()
    (ROOT / "paper_selfweight_scenario2_calibrated_reference_note_local.md").write_text(write_note(), encoding="utf-8")


if __name__ == "__main__":
    main()
