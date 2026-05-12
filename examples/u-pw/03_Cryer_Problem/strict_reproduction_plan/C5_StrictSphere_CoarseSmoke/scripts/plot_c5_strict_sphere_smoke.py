#!/usr/bin/env python3
"""Create radial profile diagnostics for the C5 strict-sphere smoke outputs."""

from __future__ import annotations

import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RADIUS = 0.05
CASES = [
    ("C5 0.006 s", "CaseCryer_PR_StrictSphere_C5_CoarseSmoke"),
]


def split_line(line: str) -> list[str]:
    sep = ";" if ";" in line else ","
    return [v.strip() for v in line.strip().split(sep)]


def find_col(headers: list[str], name: str) -> int:
    target = name.lower()
    for i, header in enumerate(headers):
        key = header.lower().split()[0] if header.strip() else ""
        if key == target:
            return i
    raise KeyError(name)


def fnum(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return math.nan


def read_time_map(case_name: str) -> dict[int, float]:
    runout = ROOT / f"{case_name}_cpu_out" / "Run.out"
    times = {0: 0.0}
    if not runout.exists():
        return times
    import re
    text = runout.read_text(errors="ignore")
    for match in re.finditer(r"Part_(?P<idx>\d{4})\s+(?P<time>[-+0-9.eE]*\.[-+0-9.eE]+)\s+\d+", text):
        times[int(match.group("idx"))] = fnum(match.group("time"))
    return times


def read_frame(path: Path) -> list[dict[str, float]]:
    lines = path.read_text(errors="ignore").splitlines()
    if not lines:
        return []
    headers = split_line(lines[0])
    cols = {
        "x": find_col(headers, "pos.x"),
        "y": find_col(headers, "pos.y"),
        "z": find_col(headers, "pos.z"),
        "ex": find_col(headers, "excessporepress"),
        "rate": find_col(headers, "porepressrate"),
        "lap": find_col(headers, "lapporepress"),
    }
    rows: list[dict[str, float]] = []
    for line in lines[1:]:
        if not line.strip() or line.startswith("#"):
            continue
        vals = split_line(line)
        x = fnum(vals[cols["x"]])
        y = fnum(vals[cols["y"]])
        z = fnum(vals[cols["z"]])
        r = math.sqrt(x*x + y*y + z*z)
        rows.append({
            "r": r,
            "rn": r / RADIUS if RADIUS else math.nan,
            "ex": fnum(vals[cols["ex"]]),
            "rate": fnum(vals[cols["rate"]]),
            "lap": fnum(vals[cols["lap"]]),
        })
    return rows


def bin_rows(rows: list[dict[str, float]], field: str, nbins: int = 20) -> tuple[list[float], list[float]]:
    sums = [0.0] * nbins
    counts = [0] * nbins
    for row in rows:
        rn = row["rn"]
        val = row[field]
        if not math.isfinite(rn) or not math.isfinite(val):
            continue
        idx = min(nbins - 1, max(0, int(rn * nbins)))
        sums[idx] += val
        counts[idx] += 1
    x: list[float] = []
    y: list[float] = []
    for i, count in enumerate(counts):
        if count:
            x.append((i + 0.5) / nbins)
            y.append(sums[i] / count)
    return x, y


def main() -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"matplotlib unavailable: {exc}")
        return

    fig_dir = ROOT / "figures"
    fig_dir.mkdir(exist_ok=True)
    fields = [
        ("ex", "excess pressure [Pa]", "c5_radial_excess_pressure_profiles"),
        ("rate", "PorePressRate [Pa/s]", "c5_radial_porepressrate_profiles"),
        ("lap", "LapPorePress [Pa/m2]", "c5_radial_lapporepress_profiles"),
    ]
    for field, ylabel, fname in fields:
        fig, axes_obj = plt.subplots(1, len(CASES), figsize=(5 * len(CASES), 4), sharex=True)
        axes = axes_obj if isinstance(axes_obj, (list, tuple)) else [axes_obj]
        for ax, (label, case_name) in zip(axes, CASES):
            times = read_time_map(case_name)
            data_dir = ROOT / f"{case_name}_cpu_out" / "data"
            paths = sorted(data_dir.glob("PartCsv_*.csv"))
            if len(paths) > 4:
                selected = [paths[0], paths[len(paths)//2], paths[-1]]
            else:
                selected = paths
            for path in selected:
                idx = int(path.stem.split("_")[-1])
                rows = read_frame(path)
                x, y = bin_rows(rows, field)
                if x:
                    ax.plot(x, y, marker="o", markersize=3, label=f"t={times.get(idx, idx):.4g}s")
            ax.axvline(1.0, color="k", linewidth=0.8, linestyle="--")
            ax.set_title(label)
            ax.set_xlabel("r/R")
            ax.grid(True, alpha=0.25)
            ax.legend(fontsize=8)
        axes[0].set_ylabel(ylabel)
        fig.tight_layout()
        fig.savefig(fig_dir / f"{fname}.png", dpi=180)
        fig.savefig(fig_dir / f"{fname}.svg")
        plt.close(fig)

    history = ROOT / "c5_center_pressure_history.csv"
    if history.exists():
        import csv
        rows = list(csv.DictReader(history.open()))
        if rows:
            plt.figure(figsize=(6, 4))
            for case in sorted({row["case"] for row in rows}):
                sub = [row for row in rows if row["case"] == case]
                sub.sort(key=lambda row: float(row["time"]))
                plt.plot(
                    [float(row["time"]) for row in sub],
                    [float(row["center_avg_ExcessPorePress_over_p0"]) for row in sub],
                    marker="o",
                    label=f"{case} averaged",
                )
                plt.plot(
                    [float(row["time"]) for row in sub],
                    [float(row["center_ExcessPorePress_over_p0"]) for row in sub],
                    linestyle="--",
                    alpha=0.65,
                    label=f"{case} nearest",
                )
            plt.xlabel("time [s]")
            plt.ylabel("center excess / p0 [-]")
            plt.title("C5 center pressure response")
            plt.grid(True, alpha=0.25)
            plt.legend(fontsize=8)
            plt.tight_layout()
            plt.savefig(fig_dir / "c5_center_normalized_pressure_nearest_vs_average.png", dpi=180)
            plt.savefig(fig_dir / "c5_center_normalized_pressure_nearest_vs_average.svg")
            plt.close()

            ref_path = ROOT.parent / "cryer_reference_curves.csv"
            if ref_path.exists():
                ref_rows = [
                    row for row in csv.DictReader(ref_path.open())
                    if abs(float(row["nu"]) - 0.3) < 1e-12
                ]
                plt.figure(figsize=(6, 4))
                for case in sorted({row["case"] for row in rows}):
                    sub = [row for row in rows if row["case"] == case]
                    sub.sort(key=lambda row: float(row["Tv_est"]))
                    plt.plot(
                        [float(row["Tv_est"]) for row in sub],
                        [float(row["center_avg_ExcessPorePress_over_p0"]) for row in sub],
                        marker="o",
                        label=f"{case} coarse smoke",
                    )
                if ref_rows:
                    xmax = max(float(row["Tv_est"]) for row in rows)
                    ref_sub = [row for row in ref_rows if float(row["Tv"]) <= max(xmax * 1.2, 1e-3)]
                    if ref_sub:
                        plt.plot(
                            [float(row["Tv"]) for row in ref_sub],
                            [float(row["normalized_center_pressure"]) for row in ref_sub],
                            color="black",
                            linewidth=1.5,
                            linestyle="--",
                            label="analytical nu=0.3 context",
                        )
                plt.xlabel("Tv = cv t / R^2 [-]")
                plt.ylabel("center excess / p0 [-]")
                plt.title("C5 center pressure with analytical context")
                plt.grid(True, alpha=0.25)
                plt.legend(fontsize=8)
                plt.tight_layout()
                plt.savefig(fig_dir / "c5_center_pressure_with_analytical_context.png", dpi=180)
                plt.savefig(fig_dir / "c5_center_pressure_with_analytical_context.svg")
                plt.close()


if __name__ == "__main__":
    main()
