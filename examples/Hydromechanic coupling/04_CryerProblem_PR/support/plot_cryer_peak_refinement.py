from pathlib import Path
import csv
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
RUNROOT = ROOT / "refinement"
FIGDIR = ROOT / "figures"
TV_LIMIT = 0.13173371

CASES = [
    ("dp=0.0100", 0.0100, RUNROOT / "dp0100_shell05" / "figures" / "dp0100_shell05.csv"),
    ("dp=0.0075", 0.0075, RUNROOT / "dp0075_shell05" / "figures" / "dp0075_shell05.csv"),
    ("dp=0.00625", 0.00625, RUNROOT / "dp00625_shell05" / "figures" / "dp00625_shell05.csv"),
    ("dp=0.0050", 0.0050, RUNROOT / "dp0050_shell05_gpu" / "figures" / "dp0050_shell05_gpu.csv"),
    ("dp=0.00375", 0.00375, RUNROOT / "dp00375_shell05_gpu_partial" / "figures_partial" / "dp00375_shell05_gpu_partial.csv"),
    ("dp=0.0030", 0.0030, RUNROOT / "dp0030_shell05_gpu_peak" / "figures" / "dp0030_shell05_gpu_peak.csv"),
    ("dp=0.0025", 0.0025, RUNROOT / "dp0025_shell05_gpu_peak" / "figures" / "dp0025_shell05_gpu_peak.csv"),
]


def read_rows(path):
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        return [
            {
                "time": float(row["time_s"]),
                "tv": float(row["tv_after_load"]),
                "num": float(row["center_pore_over_q0"]),
                "theory": float(row["theory_pore_over_q0"]),
                "sample_count": int(float(row["sample_count"])),
                "free_surface_count": int(float(row["free_surface_count"])),
            }
            for row in reader
        ]


def metrics(label, dp, rows):
    window = [row for row in rows if row["tv"] <= TV_LIMIT + 1e-9]
    if not window:
        raise RuntimeError(f"No data in peak window for {label}")
    err2 = [(row["num"] - row["theory"]) ** 2 for row in window]
    abse = [abs(row["num"] - row["theory"]) for row in window]
    peak_num = max(window, key=lambda row: row["num"])
    peak_theory = max(window, key=lambda row: row["theory"])
    return {
        "label": label,
        "dp": dp,
        "npoints": len(window),
        "rmse_tv_le_0.131734": math.sqrt(sum(err2) / len(err2)),
        "mae_tv_le_0.131734": sum(abse) / len(abse),
        "peak_num": peak_num["num"],
        "peak_num_tv": peak_num["tv"],
        "peak_num_time_s": peak_num["time"],
        "theory_at_peak_num_tv": peak_num["theory"],
        "peak_theory": peak_theory["theory"],
        "peak_theory_tv": peak_theory["tv"],
        "num_at_peak_theory_tv": peak_theory["num"],
        "final_num": window[-1]["num"],
        "final_theory": window[-1]["theory"],
        "min_sample_count": min(row["sample_count"] for row in window),
        "min_free_surface_count": min(row["free_surface_count"] for row in window),
    }


def write_summary(rows):
    FIGDIR.mkdir(exist_ok=True)
    path = FIGDIR / "cryer_refinement_peak_window_summary.csv"
    keys = [
        "label", "dp", "npoints", "rmse_tv_le_0.131734", "mae_tv_le_0.131734",
        "peak_num", "peak_num_tv", "peak_num_time_s", "theory_at_peak_num_tv",
        "peak_theory", "peak_theory_tv", "num_at_peak_theory_tv",
        "final_num", "final_theory", "min_sample_count", "min_free_surface_count",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in keys})
    return path


def plot_histories(all_rows):
    path = FIGDIR / "cryer_refinement_peak_window_comparison.png"
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    theory_done = False
    for label, dp, rows in all_rows:
        window = [row for row in rows if row["tv"] <= TV_LIMIT + 1e-9]
        ax.plot([row["tv"] for row in window], [row["num"] for row in window], marker="o", markersize=3, linewidth=1.2, label=label)
        if not theory_done:
            ax.plot([row["tv"] for row in window], [row["theory"] for row in window], "k--", linewidth=1.5, label="Cryer theory")
            theory_done = True
    ax.set_xlabel("Dimensionless time Tv")
    ax.set_ylabel("Center pore pressure / q0")
    ax.set_xlim(0.0, TV_LIMIT)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_convergence(rows):
    path = FIGDIR / "cryer_refinement_peak_window_convergence.png"
    xs = [row["dp"] for row in rows]
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.8))
    axes[0].plot(xs, [row["rmse_tv_le_0.131734"] for row in rows], "o-", label="RMSE")
    axes[0].plot(xs, [row["mae_tv_le_0.131734"] for row in rows], "s-", label="MAE")
    axes[0].invert_xaxis()
    axes[0].set_xlabel("Particle spacing dp (m)")
    axes[0].set_ylabel("Error")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")

    theory_tv = rows[-1]["peak_theory_tv"]
    axes[1].plot(xs, [row["peak_num_tv"] for row in rows], "o-", label="Numerical peak Tv")
    axes[1].axhline(theory_tv, color="k", linestyle="--", linewidth=1.2, label="Theory peak Tv")
    axes[1].invert_xaxis()
    axes[1].set_xlabel("Particle spacing dp (m)")
    axes[1].set_ylabel("Peak Tv")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def main():
    all_rows = []
    summary = []
    for label, dp, path in CASES:
        if not path.exists():
            raise FileNotFoundError(path)
        rows = read_rows(path)
        all_rows.append((label, dp, rows))
        summary.append(metrics(label, dp, rows))
    summary_path = write_summary(summary)
    histories_path = plot_histories(all_rows)
    convergence_path = plot_convergence(summary)
    print(summary_path)
    print(histories_path)
    print(convergence_path)


if __name__ == "__main__":
    main()
