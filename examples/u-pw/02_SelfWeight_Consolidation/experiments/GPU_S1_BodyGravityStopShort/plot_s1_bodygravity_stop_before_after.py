from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)
STOP_TIME = 0.002


def read_rows(name: str) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    path = ROOT / name
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            converted: dict[str, float | str] = {}
            for key, value in row.items():
                try:
                    converted[key] = float(value)
                except (TypeError, ValueError):
                    converted[key] = value
            rows.append(converted)
    return rows


def select_run(rows: list[dict[str, float | str]], run: str) -> list[dict[str, float | str]]:
    return [row for row in rows if row.get("run") == run]


def plot_metric(name: str, ykey: str, ylabel: str) -> None:
    cpu = select_run(read_rows("s1_bodygravity_stop_frame_metrics_cpu.csv"), "CPU")
    gpu_before = select_run(read_rows("s1_bodygravity_stop_frame_metrics_gpu_before_patch.csv"), "GPU")
    gpu_after = select_run(read_rows("s1_bodygravity_stop_frame_metrics_gpu_after_patch.csv"), "GPU")
    plt.figure(figsize=(6.5, 4.0))
    for rows, label, marker in [
        (cpu, "CPU", "o"),
        (gpu_before, "GPU before patch", "s"),
        (gpu_after, "GPU after patch", "^"),
    ]:
        if rows:
            plt.plot([row["time"] for row in rows], [row.get(ykey, float("nan")) for row in rows], marker=marker, label=label)
    plt.axvline(STOP_TIME, color="k", linestyle="--", linewidth=1, label="switch")
    plt.xlabel("time [s]")
    plt.ylabel(ylabel)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGDIR / f"{name}.svg")
    plt.savefig(FIGDIR / f"{name}.png", dpi=180)
    plt.close()


def plot_parity() -> None:
    before = read_rows("s1_bodygravity_stop_parity_metrics_before_patch.csv")
    after = read_rows("s1_bodygravity_stop_parity_metrics_after_patch.csv")
    plt.figure(figsize=(6.5, 4.0))
    for rows, label, marker in [
        (before, "before patch", "s"),
        (after, "after patch", "^"),
    ]:
        if rows:
            plt.plot([row["gpu_time"] for row in rows], [row["PorePress_diff_maxAbs"] for row in rows], marker=marker, label=f"PorePress {label}")
            plt.plot([row["gpu_time"] for row in rows], [row["ExcessPorePress_diff_maxAbs"] for row in rows], marker=marker, linestyle="--", label=f"Excess {label}")
    plt.axvline(STOP_TIME, color="k", linestyle="--", linewidth=1)
    plt.xlabel("time [s]")
    plt.ylabel("CPU/GPU max abs difference [Pa]")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGDIR / "s1_before_after_porepress_parity_error.svg")
    plt.savefig(FIGDIR / "s1_before_after_porepress_parity_error.png", dpi=180)
    plt.close()


def main() -> None:
    plot_metric("s1_before_after_bottom_excess_vs_time", "bottom_excess_mean", "bottom excess pressure [Pa]")
    plot_metric("s1_before_after_excess_maxabs_vs_time", "ExcessPorePress_maxAbs", "|excess pore pressure| max [Pa]")
    plot_metric("s1_before_after_velocity_max_vs_time", "Vel_mag_max", "max velocity [m/s]")
    plot_metric("s1_before_after_top_drained_excess_vs_time", "top_excess_maxAbs", "top layer |excess| max [Pa]")
    plot_metric("s1_before_after_bottom_noflux_proxy_vs_time", "bottom_no_flux_proxy", "bottom no-flux proxy [Pa]")
    plot_parity()


if __name__ == "__main__":
    main()
