#!/usr/bin/env python3
"""Generate analytical center-pressure curves for Cryer's problem.

This script implements the center-pressure series transcribed from the u-pw
paper Eq. (46)-(47). It is an analytical/reference utility only; it does not run
GenCase, DualSPHysics, PartVTK, CPU, or GPU.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Iterable


DEFAULT_NU = [0.1, 0.2, 0.3, 0.45]
DEFAULT_CONVERGENCE_ROOTS = [20, 50, 100, 200]
DIGITIZED_FILES = {
    0.1: "digitized_Fig7B_nu01.csv",
    0.2: "digitized_Fig7B_nu02.csv",
    0.3: "digitized_Fig7B_nu03.csv",
    0.45: "digitized_Fig7B_nu045.csv",
}


def eta_from_nu(nu: float) -> float:
    if not (0.0 <= nu < 0.5):
        raise ValueError(f"nu must be in [0, 0.5); got {nu}")
    return (1.0 - nu) / (1.0 - 2.0 * nu)


def root_function(xi: float, eta: float) -> float:
    return (1.0 - eta * xi * xi / 2.0) * math.tan(xi) - xi


def scaled_root_residual(xi: float, eta: float) -> float:
    term = (1.0 - eta * xi * xi / 2.0) * math.tan(xi)
    residual = term - xi
    return abs(residual) / max(1.0, abs(term), abs(xi))


def bisect_root(eta: float, index: int, tol: float = 1e-14, max_iter: int = 200) -> float:
    """Find root index j in ((j-1/2)pi, j*pi)."""

    eps = 1e-12
    lo = (index - 0.5) * math.pi + eps
    hi = index * math.pi - eps
    flo = root_function(lo, eta)
    fhi = root_function(hi, eta)
    if flo * fhi > 0.0:
        raise RuntimeError(
            f"Root bracket failed for index={index}, eta={eta}, f(lo)={flo}, f(hi)={fhi}"
        )
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        fmid = root_function(mid, eta)
        if abs(fmid) < tol or (hi - lo) < tol:
            return mid
        if flo * fmid <= 0.0:
            hi = mid
            fhi = fmid
        else:
            lo = mid
            flo = fmid
    return 0.5 * (lo + hi)


def compute_roots(eta: float, count: int) -> list[float]:
    return [bisect_root(eta, j) for j in range(1, count + 1)]


def center_pressure_ratio(tv: float, eta: float, roots: Iterable[float]) -> float:
    total = 0.0
    for xi in roots:
        denominator = eta * xi * math.cos(xi) / 2.0 + (eta - 1.0) * math.sin(xi)
        coefficient = (math.sin(xi) - xi) / denominator
        total += coefficient * math.exp(-xi * xi * tv)
    return eta * total


def make_tv_grid(tv_min: float, tv_max: float, num: int) -> list[float]:
    if tv_min <= 0 or tv_max <= tv_min:
        raise ValueError("Expected 0 < tv_min < tv_max")
    if num < 2:
        raise ValueError("num-tv must be at least 2")
    log_min = math.log10(tv_min)
    log_max = math.log10(tv_max)
    return [10.0 ** (log_min + i * (log_max - log_min) / (num - 1)) for i in range(num)]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_digitized(path: Path) -> list[tuple[float, float]]:
    data: list[tuple[float, float]] = []
    with path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "Tv" not in row or "normalized_center_pressure" not in row:
                raise ValueError(f"{path} must have Tv,normalized_center_pressure columns")
            data.append((float(row["Tv"]), float(row["normalized_center_pressure"])))
    return data


def interpolate_logx(x: float, xs: list[float], ys: list[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lx = math.log(x)
    logs = [math.log(v) for v in xs]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if logs[mid] <= lx:
            lo = mid
        else:
            hi = mid
    t = (lx - logs[lo]) / (logs[hi] - logs[lo])
    return ys[lo] * (1.0 - t) + ys[hi] * t


def save_figures(output_dir: Path, curve_rows: list[dict[str, object]], peak_rows: list[dict[str, object]],
                 convergence_rows: list[dict[str, object]], nu_values: list[float]) -> None:
    import matplotlib.pyplot as plt

    fig_dir = output_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    grouped: dict[float, list[dict[str, object]]] = {nu: [] for nu in nu_values}
    for row in curve_rows:
        grouped[float(row["nu"])].append(row)

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    for nu in nu_values:
        rows = grouped[nu]
        ax.semilogx(
            [float(r["Tv"]) for r in rows],
            [float(r["normalized_center_pressure"]) for r in rows],
            label=f"nu={nu:g}",
        )
    ax.set_xlabel("Dimensionless time, Tv")
    ax.set_ylabel("Center pore pressure, pw(0,t)/p0")
    ax.set_title("Cryer analytical center-pressure reference")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    for ext in ["svg", "png", "pdf"]:
        fig.savefig(fig_dir / f"cryer_reference_center_pressure_curves.{ext}", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    for nu in nu_values:
        rows = [r for r in convergence_rows if float(r["nu"]) == nu]
        ax.loglog(
            [int(r["root_count"]) for r in rows],
            [float(r["max_abs_diff_vs_reference"]) for r in rows],
            marker="o",
            label=f"nu={nu:g}",
        )
    ax.set_xlabel("Root truncation count")
    ax.set_ylabel("Max abs difference vs reference truncation")
    ax.set_title("Cryer series root-truncation convergence")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    for ext in ["svg", "png", "pdf"]:
        fig.savefig(fig_dir / f"cryer_reference_root_convergence.{ext}", bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.2))
    axes[0].plot([float(r["nu"]) for r in peak_rows], [float(r["peak_pressure"]) for r in peak_rows], marker="o")
    axes[0].set_xlabel("Poisson ratio, nu")
    axes[0].set_ylabel("Peak pw(0,t)/p0")
    axes[0].set_title("Peak pressure")
    axes[0].grid(True, alpha=0.3)
    axes[1].plot([float(r["nu"]) for r in peak_rows], [float(r["peak_Tv"]) for r in peak_rows], marker="o")
    axes[1].set_xlabel("Poisson ratio, nu")
    axes[1].set_ylabel("Peak Tv")
    axes[1].set_title("Peak time")
    axes[1].grid(True, alpha=0.3)
    for ext in ["svg", "png", "pdf"]:
        fig.savefig(fig_dir / f"cryer_reference_peak_vs_nu.{ext}", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    for nu in nu_values:
        rows = grouped[nu]
        ax.loglog(
            [float(r["Tv"]) for r in rows],
            [max(abs(float(r["normalized_center_pressure"])), 1e-16) for r in rows],
            label=f"nu={nu:g}",
        )
    ax.set_xlabel("Dimensionless time, Tv")
    ax.set_ylabel("|pw(0,t)/p0|")
    ax.set_title("Cryer analytical long-time decay")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    for ext in ["svg", "png", "pdf"]:
        fig.savefig(fig_dir / f"cryer_reference_long_time_decay.{ext}", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nu", nargs="+", type=float, default=DEFAULT_NU)
    parser.add_argument("--tv-min", type=float, default=1e-4)
    parser.add_argument("--tv-max", type=float, default=10.0)
    parser.add_argument("--num-tv", type=int, default=600)
    parser.add_argument("--num-roots", type=int, default=200)
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--make-plot", action="store_true")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tv_grid = make_tv_grid(args.tv_min, args.tv_max, args.num_tv)
    reference_root_count = max(args.num_roots, max(DEFAULT_CONVERGENCE_ROOTS))

    all_roots: dict[float, list[float]] = {}
    curve_rows: list[dict[str, object]] = []
    root_rows: list[dict[str, object]] = []
    peak_rows: list[dict[str, object]] = []
    convergence_rows: list[dict[str, object]] = []
    fig7b_rows: list[dict[str, object]] = []
    digitized_available = False

    max_root_residual = 0.0
    max_scaled_root_residual = 0.0
    for nu in args.nu:
        eta = eta_from_nu(nu)
        roots = compute_roots(eta, reference_root_count)
        all_roots[nu] = roots
        for i, root in enumerate(roots[: args.num_roots], start=1):
            residual = root_function(root, eta)
            scaled_residual = scaled_root_residual(root, eta)
            max_root_residual = max(max_root_residual, abs(residual))
            max_scaled_root_residual = max(max_scaled_root_residual, scaled_residual)
            root_rows.append(
                {
                    "nu": nu,
                    "eta": eta,
                    "root_index": i,
                    "xi": f"{root:.16e}",
                    "residual": f"{residual:.16e}",
                    "scaled_residual": f"{scaled_residual:.16e}",
                }
            )

        values = [center_pressure_ratio(tv, eta, roots[: args.num_roots]) for tv in tv_grid]
        for tv, value in zip(tv_grid, values):
            curve_rows.append(
                {
                    "nu": nu,
                    "eta": eta,
                    "Tv": f"{tv:.16e}",
                    "normalized_center_pressure": f"{value:.16e}",
                    "root_count": args.num_roots,
                    "formula": "paper_eq_46_47",
                }
            )
        peak_index = max(range(len(values)), key=lambda i: values[i])
        peak_rows.append(
            {
                "nu": nu,
                "eta": eta,
                "peak_pressure": f"{values[peak_index]:.16e}",
                "peak_Tv": f"{tv_grid[peak_index]:.16e}",
                "initial_grid_pressure": f"{values[0]:.16e}",
                "final_grid_pressure": f"{values[-1]:.16e}",
                "root_count": args.num_roots,
            }
        )

        ref_values = [center_pressure_ratio(tv, eta, roots[:reference_root_count]) for tv in tv_grid]
        for count in DEFAULT_CONVERGENCE_ROOTS:
            vals = [center_pressure_ratio(tv, eta, roots[:count]) for tv in tv_grid]
            max_abs = max(abs(a - b) for a, b in zip(vals, ref_values))
            convergence_rows.append(
                {
                    "nu": nu,
                    "root_count": count,
                    "reference_root_count": reference_root_count,
                    "max_abs_diff_vs_reference": f"{max_abs:.16e}",
                }
            )

        digitized_path = output_dir / DIGITIZED_FILES.get(nu, "")
        if digitized_path.exists():
            digitized_available = True
            ref_x = tv_grid
            ref_y = values
            samples = read_digitized(digitized_path)
            errors = []
            for tv, measured in samples:
                pred = interpolate_logx(tv, ref_x, ref_y)
                errors.append(pred - measured)
                fig7b_rows.append(
                    {
                        "nu": nu,
                        "Tv": tv,
                        "digitized": measured,
                        "reference": pred,
                        "error": pred - measured,
                    }
                )
            if errors:
                rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
                max_abs = max(abs(e) for e in errors)
                print(f"Fig7B digitized check nu={nu:g}: samples={len(errors)} RMSE={rmse:.6g} maxAbs={max_abs:.6g}")

    output_csv = args.output_csv or (output_dir / "cryer_reference_curves.csv")
    write_csv(
        output_csv,
        curve_rows,
        ["nu", "eta", "Tv", "normalized_center_pressure", "root_count", "formula"],
    )
    write_csv(output_dir / "cryer_reference_roots.csv", root_rows, ["nu", "eta", "root_index", "xi", "residual", "scaled_residual"])
    write_csv(
        output_dir / "cryer_reference_convergence.csv",
        convergence_rows,
        ["nu", "root_count", "reference_root_count", "max_abs_diff_vs_reference"],
    )
    write_csv(
        output_dir / "cryer_reference_peak_metrics.csv",
        peak_rows,
        ["nu", "eta", "peak_pressure", "peak_Tv", "initial_grid_pressure", "final_grid_pressure", "root_count"],
    )
    if fig7b_rows:
        write_csv(output_dir / "cryer_reference_fig7b_validation.csv", fig7b_rows, ["nu", "Tv", "digitized", "reference", "error"])

    peaks = {float(r["nu"]): float(r["peak_pressure"]) for r in peak_rows}
    ordered_nu = sorted(args.nu)
    overshoot_order_pass = all(peaks[ordered_nu[i]] >= peaks[ordered_nu[i + 1]] for i in range(len(ordered_nu) - 1))
    nonmonotonic_pass = all(float(r["peak_pressure"]) > max(1.0, float(r["initial_grid_pressure"])) for r in peak_rows)
    final_decay_pass = all(abs(float(r["final_grid_pressure"])) < 1e-8 for r in peak_rows)
    max_conv_100 = max(
        float(r["max_abs_diff_vs_reference"])
        for r in convergence_rows
        if int(r["root_count"]) == 100
    )
    max_conv_50 = max(
        float(r["max_abs_diff_vs_reference"])
        for r in convergence_rows
        if int(r["root_count"]) == 50
    )
    selfcheck = {
        "formula": "u-pw paper Eq. (46)-(47), PDF-checked transcription",
        "settings": {
            "nu": args.nu,
            "tv_min": args.tv_min,
            "tv_max": args.tv_max,
            "num_tv": args.num_tv,
            "num_roots": args.num_roots,
            "reference_root_count": reference_root_count,
        },
        "max_root_residual_abs": max_root_residual,
        "max_scaled_root_residual": max_scaled_root_residual,
        "max_convergence_diff_50_vs_reference": max_conv_50,
        "max_convergence_diff_100_vs_reference": max_conv_100,
        "overshoot_order_pass": overshoot_order_pass,
        "nonmonotonic_peak_pass": nonmonotonic_pass,
        "long_time_decay_pass": final_decay_pass,
        "fig7b_digitized_data_available": digitized_available,
        "peaks": peak_rows,
        "notes": [
            "Curves are implemented analytical reference candidates.",
            "They are not fully verified against digitized Figure 7B unless digitized data files are supplied.",
        ],
    }
    with (output_dir / "cryer_reference_selfcheck.json").open("w") as f:
        json.dump(selfcheck, f, indent=2)

    if args.make_plot:
        save_figures(output_dir, curve_rows, peak_rows, convergence_rows, args.nu)

    print(
        "Wrote Cryer reference curves: "
        f"nu={args.nu}, roots={args.num_roots}, Tv=[{args.tv_min},{args.tv_max}], "
        f"max_root_residual={max_root_residual:.3e}, "
        f"max_scaled_root_residual={max_scaled_root_residual:.3e}, "
        f"max_conv_100={max_conv_100:.3e}, "
        f"digitized_fig7b={digitized_available}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
