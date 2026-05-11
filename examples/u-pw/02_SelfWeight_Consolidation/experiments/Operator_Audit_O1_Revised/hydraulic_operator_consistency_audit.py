#!/usr/bin/env python3
"""O1-revised hydraulic operator diagnostic with boundary-particle models.

This standalone script does not run GenCase or DualSPHysics and does not modify
production source.  It reproduces the current material-material PR Laplacian
and compares it with idealized boundary-particle/ghost participation models.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Constants:
    dp: float = 0.01
    width: float = 0.1
    height: float = 1.0
    hdp: float = 1.8
    zmin: float = 0.005
    zmax: float = 0.995
    waterlevel: float = 1.0
    cv_scale_full_window: float = 1.1175
    cv_scale_early_001_10: float = 1.1550
    cv_scale_early_0002_05: float = 1.1975

    @property
    def h(self) -> float:
        return self.hdp * self.dp

    @property
    def support(self) -> float:
        return 2.0 * self.h

    @property
    def area(self) -> float:
        return self.dp * self.dp

    @property
    def H(self) -> float:
        return self.zmax - self.zmin


C = Constants()
EPS = 1.0e-18


def wendland_fac_2d(rr2: np.ndarray | float, h: float = C.h) -> np.ndarray | float:
    rad = np.sqrt(rr2)
    q = rad / h
    bwen = -2.7852 / (h * h * h)
    return bwen * q * (1.0 - 0.5 * q) ** 3 / rad


def wendland_wab_2d(rr2: np.ndarray | float, h: float = C.h) -> np.ndarray | float:
    rad = np.sqrt(rr2)
    q = rad / h
    awen = 0.557 / (h * h)
    q1 = 1.0 - 0.5 * q
    return awen * (2.0 * q + 1.0) * q1**4


def material_positions() -> np.ndarray:
    xs = np.arange(C.dp / 2, C.width, C.dp)
    zs = np.arange(C.dp / 2, C.height, C.dp)
    xx, zz = np.meshgrid(xs, zs, indexing="xy")
    return np.column_stack([xx.ravel(), zz.ravel()])


MAT_POS = material_positions()
N = MAT_POS.shape[0]
Y = MAT_POS[:, 1] - C.zmin
ZLAYERS = np.arange(C.dp / 2, C.height, C.dp)
XLAYERS = np.arange(C.dp / 2, C.width, C.dp)


def masks() -> dict[str, np.ndarray]:
    x = MAT_POS[:, 0]
    z = MAT_POS[:, 1]
    return {
        "full": np.ones(N, dtype=bool),
        "interior_z_1h": (z >= C.zmin + C.h) & (z <= C.zmax - C.h),
        "interior_z_2h": (z >= C.zmin + 2 * C.h) & (z <= C.zmax - 2 * C.h),
        "interior_z_3h": (z >= C.zmin + 3 * C.h) & (z <= C.zmax - 3 * C.h),
        "interior_xz_2h": (
            (z >= C.zmin + 2 * C.h)
            & (z <= C.zmax - 2 * C.h)
            & (x >= C.dp / 2 + 2 * C.h)
            & (x <= C.width - C.dp / 2 - 2 * C.h)
        ),
        "bottom_layer": z <= C.zmin + C.h,
        "top_layer": z >= C.zmax - C.h,
    }


MASKS = masks()


def build_boundary_cloud(nlayers: int = 4) -> np.ndarray:
    xs = np.arange(C.dp / 2 - nlayers * C.dp, C.width + nlayers * C.dp, C.dp)
    zs = np.arange(C.dp / 2 - nlayers * C.dp, C.height + nlayers * C.dp, C.dp)
    xx, zz = np.meshgrid(xs, zs, indexing="xy")
    pts = np.column_stack([xx.ravel(), zz.ravel()])
    in_material_box = (
        (pts[:, 0] >= C.dp / 2 - 1.0e-12)
        & (pts[:, 0] <= C.width - C.dp / 2 + 1.0e-12)
        & (pts[:, 1] >= C.dp / 2 - 1.0e-12)
        & (pts[:, 1] <= C.height - C.dp / 2 + 1.0e-12)
    )
    near_box = (
        (pts[:, 0] >= C.dp / 2 - C.support - C.dp)
        & (pts[:, 0] <= C.width - C.dp / 2 + C.support + C.dp)
        & (pts[:, 1] >= C.dp / 2 - C.support - C.dp)
        & (pts[:, 1] <= C.height - C.dp / 2 + C.support + C.dp)
    )
    return pts[(~in_material_box) & near_box]


BOUNDARY_POS = build_boundary_cloud()


def extension_neumann_bottom_dirichlet_top(func: Callable[[np.ndarray], np.ndarray], z: np.ndarray) -> np.ndarray:
    y = z - C.zmin
    y_eff = y.copy()
    sign = np.ones_like(y_eff)
    bottom = y_eff < 0.0
    y_eff[bottom] = -y_eff[bottom]
    top = y_eff > C.H
    y_eff[top] = 2.0 * C.H - y_eff[top]
    sign[top] = -1.0
    y_eff = np.clip(y_eff, 0.0, C.H)
    return sign * func(y_eff)


def laplacian_pair(target_pos: np.ndarray, source_pos: np.ndarray, target_u: np.ndarray, source_u: np.ndarray) -> np.ndarray:
    out = np.zeros(target_pos.shape[0], dtype=float)
    support2 = C.support * C.support
    for i, posi in enumerate(target_pos):
        dx = posi[0] - source_pos[:, 0]
        dz = posi[1] - source_pos[:, 1]
        rr2 = dx * dx + dz * dz
        mask = (rr2 <= support2) & (rr2 >= EPS)
        if not np.any(mask):
            continue
        rr2m = rr2[mask]
        dotrgrad = rr2m * wendland_fac_2d(rr2m)
        out[i] = np.sum(2.0 * C.area * (target_u[i] - source_u[mask]) * dotrgrad / (rr2m + EPS))
    return out


def lap_M(u: np.ndarray) -> np.ndarray:
    return laplacian_pair(MAT_POS, MAT_POS, u, u)


def lap_MB(func: Callable[[np.ndarray], np.ndarray], target_u: np.ndarray) -> np.ndarray:
    source_pos = np.vstack([MAT_POS, BOUNDARY_POS])
    boundary_u = extension_neumann_bottom_dirichlet_top(func, BOUNDARY_POS[:, 1])
    source_u = np.concatenate([target_u, boundary_u])
    return laplacian_pair(MAT_POS, source_pos, target_u, source_u)


def lap_virtual_mode1(func: Callable[[np.ndarray], np.ndarray], target_u: np.ndarray) -> np.ndarray:
    """Mirror current production mode=1: one vertical ghost contribution near top/bottom."""

    lap = lap_M(target_u).copy()
    support2 = C.support * C.support
    gap = 0.5 * C.dp
    top_plane = C.zmax + gap
    bottom_plane = C.zmin - gap
    top_threshold = C.zmax - C.h
    bottom_threshold = C.zmin + C.h

    for i, posi in enumerate(MAT_POS):
        z = posi[1]
        if z >= top_threshold:
            zg = 2.0 * top_plane - z
            rr2 = (z - zg) ** 2
            if EPS <= rr2 <= support2:
                dotrgrad = rr2 * wendland_fac_2d(rr2)
                # Dirichlet top excess ghost.
                ug = 0.0
                lap[i] += 2.0 * C.area * (target_u[i] - ug) * dotrgrad / (rr2 + EPS)
        if z <= bottom_threshold:
            zg = 2.0 * bottom_plane - z
            rr2 = (z - zg) ** 2
            if EPS <= rr2 <= support2:
                dotrgrad = rr2 * wendland_fac_2d(rr2)
                # Neumann excess mirror; scalar excess contribution is zero.
                ug = target_u[i]
                lap[i] += 2.0 * C.area * (target_u[i] - ug) * dotrgrad / (rr2 + EPS)
    return lap


def layer_values_to_particles(layer_values: np.ndarray) -> np.ndarray:
    return np.repeat(layer_values, len(XLAYERS))


def mls_1d_second_derivative(func: Callable[[np.ndarray], np.ndarray]) -> np.ndarray:
    """Local weighted quadratic reconstruction in z only with BC extension."""

    out_layers = np.zeros_like(ZLAYERS)
    source_z = np.arange(C.zmin - 4 * C.dp, C.zmax + 4 * C.dp + 0.5 * C.dp, C.dp)
    source_y = source_z - C.zmin
    source_u = extension_neumann_bottom_dirichlet_top(func, source_z)
    for k, z0 in enumerate(ZLAYERS):
        dz = source_z - z0
        rr2 = dz * dz
        mask = (rr2 <= C.support * C.support) & (rr2 >= 0.0)
        if np.count_nonzero(mask) < 3:
            out_layers[k] = np.nan
            continue
        w = np.zeros(np.count_nonzero(mask))
        rr2m = rr2[mask]
        # Use kernel values as LS weights.
        nonzero = rr2m > EPS
        w[nonzero] = wendland_wab_2d(rr2m[nonzero])
        w[~nonzero] = wendland_wab_2d(np.array([EPS]))[0]
        a = np.column_stack([np.ones_like(dz[mask]), dz[mask], dz[mask] ** 2])
        aw = a * np.sqrt(w[:, None])
        bw = source_u[mask] * np.sqrt(w)
        try:
            coef, *_ = np.linalg.lstsq(aw, bw, rcond=None)
            out_layers[k] = 2.0 * coef[2]
        except np.linalg.LinAlgError:
            out_layers[k] = np.nan
    return layer_values_to_particles(out_layers)


MODELS = {
    "M_material_only": lambda f, u: lap_M(u),
    "M_virtual_mode1": lap_virtual_mode1,
    "MB_ideal_boundary_particles": lap_MB,
}


def field_function(name: str, mode: int | None = None) -> tuple[Callable[[np.ndarray], np.ndarray], Callable[[np.ndarray], np.ndarray], str]:
    if name == "constant":
        return lambda y: np.ones_like(y), lambda y: np.zeros_like(y), "u=1"
    if name == "linear":
        return lambda y: y, lambda y: np.zeros_like(y), "u=y"
    if name == "quadratic":
        return lambda y: y * y, lambda y: np.full_like(y, 2.0), "u=y^2"
    if name == "eigen":
        assert mode is not None
        lam = (2 * mode + 1) * math.pi / (2.0 * C.H)
        return lambda y, lam=lam: np.cos(lam * y), lambda y, lam=lam: -lam * lam * np.cos(lam * y), f"cos(lambda_{mode} y)"
    raise ValueError(name)


def fit_scale(lap: np.ndarray, u: np.ndarray, lam: float, mask: np.ndarray) -> float:
    denom = lam * lam * float(np.sum(u[mask] * u[mask]))
    if denom <= 0:
        return float("nan")
    return -float(np.sum(lap[mask] * u[mask])) / denom


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def savefig(name: str) -> None:
    for ext in ("svg", "png"):
        plt.savefig(FIG_DIR / f"{name}.{ext}", bbox_inches="tight", dpi=180)
    plt.close()


def polynomial_metrics() -> list[dict]:
    rows: list[dict] = []
    for fname in ("constant", "linear", "quadratic"):
        func, lap_exact_func, label = field_function(fname)
        u = func(Y)
        exact = lap_exact_func(Y)
        for mname, model in MODELS.items():
            lap = model(func, u)
            err = lap - exact
            for region, mask in MASKS.items():
                if not np.any(mask):
                    continue
                rows.append(
                    {
                        "field": fname,
                        "field_label": label,
                        "model": mname,
                        "region": region,
                        "count": int(np.count_nonzero(mask)),
                        "lap_mean": float(np.mean(lap[mask])),
                        "lap_absmax": float(np.max(np.abs(lap[mask]))),
                        "rmse": float(np.sqrt(np.mean(err[mask] ** 2))),
                        "max_abs_error": float(np.max(np.abs(err[mask]))),
                    }
                )
    return rows


def eigenmode_metrics() -> list[dict]:
    rows: list[dict] = []
    for n in range(4):
        func, exact_func, label = field_function("eigen", n)
        lam = (2 * n + 1) * math.pi / (2.0 * C.H)
        u = func(Y)
        exact = exact_func(Y)
        for mname, model in MODELS.items():
            lap = model(func, u)
            err = lap - exact
            for region, mask in MASKS.items():
                if not np.any(mask):
                    continue
                scale = fit_scale(lap, u, lam, mask)
                rows.append(
                    {
                        "mode": n,
                        "field_label": label,
                        "lambda": lam,
                        "model": mname,
                        "region": region,
                        "count": int(np.count_nonzero(mask)),
                        "scale_s": scale,
                        "scale_vs_cv_eff_1p1175": scale - C.cv_scale_full_window,
                        "rmse": float(np.sqrt(np.mean(err[mask] ** 2))),
                        "max_abs_error": float(np.max(np.abs(err[mask]))),
                        "mean_abs_error": float(np.mean(np.abs(err[mask]))),
                    }
                )
    return rows


def hydrostatic_cancellation_metrics() -> list[dict]:
    rows: list[dict] = []
    # Let rho*g=1, p_hydro = waterlevel - z.  Then p/(rho*g) + z is constant.
    target_p = C.waterlevel - MAT_POS[:, 1]
    target_z = MAT_POS[:, 1].copy()

    def virtual_hydro_lap(target: np.ndarray, is_pressure: bool) -> np.ndarray:
        lap = laplacian_pair(MAT_POS, MAT_POS, target, target)
        support2 = C.support * C.support
        gap = 0.5 * C.dp
        top_plane = C.zmax + gap
        bottom_plane = C.zmin - gap
        top_threshold = C.zmax - C.h
        bottom_threshold = C.zmin + C.h
        for i, posi in enumerate(MAT_POS):
            z = posi[1]
            for active, plane, threshold, side in (
                (z >= top_threshold, top_plane, top_threshold, "top"),
                (z <= bottom_threshold, bottom_plane, bottom_threshold, "bottom"),
            ):
                if not active:
                    continue
                zg = 2.0 * plane - z
                rr2 = (z - zg) ** 2
                if EPS <= rr2 <= support2:
                    dotrgrad = rr2 * wendland_fac_2d(rr2)
                    ghost_value = (C.waterlevel - zg) if is_pressure else zg
                    lap[i] += 2.0 * C.area * (target[i] - ghost_value) * dotrgrad / (rr2 + EPS)
        return lap

    source_pos_mb = np.vstack([MAT_POS, BOUNDARY_POS])
    source_p_mb = C.waterlevel - source_pos_mb[:, 1]
    source_z_mb = source_pos_mb[:, 1].copy()

    hydro_laps = {
        "M_material_only": (
            laplacian_pair(MAT_POS, MAT_POS, target_p, target_p),
            laplacian_pair(MAT_POS, MAT_POS, target_z, target_z),
        ),
        "M_virtual_mode1": (
            virtual_hydro_lap(target_p, is_pressure=True),
            virtual_hydro_lap(target_z, is_pressure=False),
        ),
        "MB_ideal_boundary_particles": (
            laplacian_pair(MAT_POS, source_pos_mb, target_p, source_p_mb),
            laplacian_pair(MAT_POS, source_pos_mb, target_z, source_z_mb),
        ),
    }

    for mname, (lapp, lapz) in hydro_laps.items():
        residual = lapp + lapz
        for region, mask in MASKS.items():
            if not np.any(mask):
                continue
            rows.append(
                {
                    "model": mname,
                    "region": region,
                    "count": int(np.count_nonzero(mask)),
                    "residual_rmse": float(np.sqrt(np.mean(residual[mask] ** 2))),
                    "residual_max_abs": float(np.max(np.abs(residual[mask]))),
                    "lapp_rmse": float(np.sqrt(np.mean(lapp[mask] ** 2))),
                    "lapz_rmse": float(np.sqrt(np.mean(lapz[mask] ** 2))),
                }
            )
    return rows


def correction_metrics(eigen_rows: list[dict]) -> list[dict]:
    rows: list[dict] = []
    s0 = next(float(r["scale_s"]) for r in eigen_rows if r["mode"] == 0 and r["model"] == "M_material_only" and r["region"] == "full")
    s_mean = np.mean(
        [
            float(r["scale_s"])
            for r in eigen_rows
            if r["model"] == "M_material_only" and r["region"] == "full"
        ]
    )
    for n in range(4):
        func, exact_func, _label = field_function("eigen", n)
        lam = (2 * n + 1) * math.pi / (2.0 * C.H)
        u = func(Y)
        exact = exact_func(Y)
        variants = {
            "M_raw": lap_M(u),
            "M_scalar_norm_by_s0": lap_M(u) / s0,
            "M_scalar_norm_by_modes_mean": lap_M(u) / s_mean,
            "MB_ideal_boundary_particles": lap_MB(func, u),
            "MLS_1d_quadratic": mls_1d_second_derivative(func),
        }
        for cname, lap in variants.items():
            valid = np.isfinite(lap)
            mask = MASKS["full"] & valid
            err = lap - exact
            rows.append(
                {
                    "mode": n,
                    "correction": cname,
                    "count": int(np.count_nonzero(mask)),
                    "scale_s": fit_scale(lap, u, lam, mask),
                    "rmse": float(np.sqrt(np.mean(err[mask] ** 2))),
                    "max_abs_error": float(np.max(np.abs(err[mask]))),
                }
            )
    rows.append({"mode": "all", "correction": "M_scalar_norm_by_s0_factor", "scale_s": s0, "count": 0, "rmse": 0, "max_abs_error": 0})
    rows.append({"mode": "all", "correction": "M_scalar_norm_by_modes_mean_factor", "scale_s": float(s_mean), "count": 0, "rmse": 0, "max_abs_error": 0})
    return rows


def lookup(rows: list[dict], **query) -> dict:
    for row in rows:
        if all(row.get(k) == v for k, v in query.items()):
            return row
    raise KeyError(query)


def make_figures(poly_rows: list[dict], eigen_rows: list[dict], hydro_rows: list[dict], corr_rows: list[dict]) -> None:
    models = list(MODELS.keys())

    # Polynomial consistency.
    plt.figure(figsize=(8.5, 4.8))
    fields = ["constant", "linear", "quadratic"]
    x = np.arange(len(fields))
    width = 0.24
    for i, model in enumerate(models):
        vals = [float(lookup(poly_rows, field=f, model=model, region="full")["rmse"]) for f in fields]
        plt.bar(x + (i - 1) * width, vals, width=width, label=model)
    plt.yscale("log")
    plt.xticks(x, fields)
    plt.ylabel("Laplacian RMSE")
    plt.title("Polynomial consistency: current M vs hypothetical MB")
    plt.grid(True, which="both", axis="y", alpha=0.3)
    plt.legend(fontsize=8)
    savefig("laplacian_consistency_constant_linear_quadratic")

    # Eigenmode scaling.
    plt.figure(figsize=(8.5, 4.8))
    for model in models:
        modes = []
        scales = []
        for n in range(4):
            row = lookup(eigen_rows, mode=n, model=model, region="full")
            modes.append(n)
            scales.append(float(row["scale_s"]))
        plt.plot(modes, scales, marker="o", label=model)
    for scale, label, style in [
        (1.0, "ideal 1.0", "--"),
        (C.cv_scale_full_window, "P1 full-window cv scale 1.1175", ":"),
        (C.cv_scale_early_001_10, "A2 early 0.01-1.0 scale 1.1550", "-."),
    ]:
        plt.axhline(scale, color="k" if scale == 1.0 else "tab:red", linestyle=style, linewidth=1.2, label=label)
    plt.xlabel("Eigenmode n")
    plt.ylabel("Fitted scale s_n")
    plt.title("Eigenmode effective scaling: M vs MB")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    savefig("eigenmode_effective_scaling_M_vs_MB")

    # Regions for M.
    plt.figure(figsize=(8.5, 4.8))
    regions = ["full", "interior_z_1h", "interior_z_2h", "interior_z_3h", "interior_xz_2h"]
    for region in regions:
        scales = [float(lookup(eigen_rows, mode=n, model="M_material_only", region=region)["scale_s"]) for n in range(4)]
        plt.plot(range(4), scales, marker="o", label=region)
    plt.axhline(C.cv_scale_full_window, color="tab:red", linestyle=":", label="P1 cv scale 1.1175")
    plt.xlabel("Eigenmode n")
    plt.ylabel("s_n")
    plt.title("Effective cv scale by mode and region")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    savefig("effective_cv_scale_vs_mode")

    # Boundary vs interior error for mode 0.
    plt.figure(figsize=(9.0, 4.8))
    regions = ["full", "bottom_layer", "top_layer", "interior_z_1h", "interior_z_2h", "interior_xz_2h"]
    x = np.arange(len(regions))
    width = 0.24
    for i, model in enumerate(models):
        vals = [float(lookup(eigen_rows, mode=0, model=model, region=r)["rmse"]) for r in regions]
        plt.bar(x + (i - 1) * width, vals, width=width, label=model)
    plt.yscale("log")
    plt.xticks(x, regions, rotation=25, ha="right")
    plt.ylabel("n=0 Laplacian RMSE")
    plt.title("Boundary vs interior operator error")
    plt.grid(True, which="both", axis="y", alpha=0.3)
    plt.legend(fontsize=8)
    savefig("boundary_vs_interior_operator_error")

    # Hydrostatic cancellation.
    plt.figure(figsize=(8.5, 4.8))
    regions = ["full", "bottom_layer", "top_layer", "interior_z_2h"]
    x = np.arange(len(regions))
    width = 0.24
    for i, model in enumerate(models):
        vals = [float(lookup(hydro_rows, model=model, region=r)["residual_max_abs"]) for r in regions]
        plt.bar(x + (i - 1) * width, vals, width=width, label=model)
    plt.yscale("log")
    plt.xticks(x, regions)
    plt.ylabel("max |LapP/(rho g)+LapZ|")
    plt.title("Hydrostatic cancellation residual")
    plt.grid(True, which="both", axis="y", alpha=0.3)
    plt.legend(fontsize=8)
    savefig("hydrostatic_cancellation_residual")

    # Hypothetical correction comparison.
    plt.figure(figsize=(8.8, 4.8))
    corrections = ["M_raw", "M_scalar_norm_by_s0", "MB_ideal_boundary_particles", "MLS_1d_quadratic"]
    for corr in corrections:
        vals = [float(lookup(corr_rows, mode=n, correction=corr)["scale_s"]) for n in range(4)]
        plt.plot(range(4), vals, marker="o", label=corr)
    plt.axhline(1.0, color="k", linestyle="--", label="ideal 1.0")
    plt.axhline(C.cv_scale_full_window, color="tab:red", linestyle=":", label="P1 cv scale 1.1175")
    plt.xlabel("Eigenmode n")
    plt.ylabel("Scale s_n")
    plt.title("Hypothetical corrections: fitted scale")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    savefig("hypothetical_correction_comparison")

    # MLS or boundary-particle effect RMSE.
    plt.figure(figsize=(8.8, 4.8))
    for corr in corrections:
        vals = [float(lookup(corr_rows, mode=n, correction=corr)["rmse"]) for n in range(4)]
        plt.plot(range(4), vals, marker="o", label=corr)
    plt.yscale("log")
    plt.xlabel("Eigenmode n")
    plt.ylabel("Full-domain RMSE")
    plt.title("MLS / boundary-particle effect if tested")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend(fontsize=8)
    savefig("MLS_or_boundary_particle_effect_if_tested")


def main() -> None:
    poly = polynomial_metrics()
    eigen = eigenmode_metrics()
    hydro = hydrostatic_cancellation_metrics()
    corr = correction_metrics(eigen)

    write_csv(ROOT / "laplacian_consistency_polynomial_metrics.csv", poly)
    write_csv(ROOT / "eigenmode_effective_scaling.csv", eigen)
    write_csv(ROOT / "hydrostatic_cancellation_metrics.csv", hydro)
    write_csv(ROOT / "hypothetical_correction_metrics.csv", corr)

    make_figures(poly, eigen, hydro, corr)

    summary = {
        "particle_count_material": int(N),
        "particle_count_boundary_idealized": int(BOUNDARY_POS.shape[0]),
        "dp": C.dp,
        "h": C.h,
        "support": C.support,
        "H": C.H,
        "target_cv_scale_full_window": C.cv_scale_full_window,
        "s0_M_full": float(lookup(eigen, mode=0, model="M_material_only", region="full")["scale_s"]),
        "s0_M_interior_z_2h": float(lookup(eigen, mode=0, model="M_material_only", region="interior_z_2h")["scale_s"]),
        "s0_M_interior_xz_2h": float(lookup(eigen, mode=0, model="M_material_only", region="interior_xz_2h")["scale_s"]),
        "s0_virtual_mode1_full": float(lookup(eigen, mode=0, model="M_virtual_mode1", region="full")["scale_s"]),
        "s0_MB_full": float(lookup(eigen, mode=0, model="MB_ideal_boundary_particles", region="full")["scale_s"]),
        "s0_MB_interior_z_2h": float(lookup(eigen, mode=0, model="MB_ideal_boundary_particles", region="interior_z_2h")["scale_s"]),
        "hydro_M_full_max_abs": float(lookup(hydro, model="M_material_only", region="full")["residual_max_abs"]),
        "hydro_MB_full_max_abs": float(lookup(hydro, model="MB_ideal_boundary_particles", region="full")["residual_max_abs"]),
        "mls_mode0_scale": float(lookup(corr, mode=0, correction="MLS_1d_quadratic")["scale_s"]),
    }
    (ROOT / "operator_audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
