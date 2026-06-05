from pathlib import Path
import csv
import importlib.util
import math

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
FIGDIR = ROOT / "figures"
POSTPROCESS = Path(__file__).resolve().parent / "postprocess_terzaghi_q0.py"

spec = importlib.util.spec_from_file_location("terzaghi_q0", POSTPROCESS)
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

CASES = [
    ("4e-5", "xi4e5"),
    ("0.01", "xi0p01"),
    ("0.02", "xi0p02"),
    ("0.04", "xi0p04"),
    ("0.05", "xi0p05"),
]


def mean(rows, key):
    vals = [row[key] for row in rows if key in row]
    return sum(vals) / len(vals) if vals else 0.0


def max_value(rows, key):
    vals = [row[key] for row in rows if key in row]
    return max(vals) if vals else 0.0


def top_rows(rows):
    zmax = max(row["z"] for row in rows)
    return [row for row in rows if row["z"] >= zmax - 0.55 * pp.DP]


def bottom_rows(rows):
    zmin = min(row["z"] for row in rows)
    return [row for row in rows if row["z"] <= zmin + 0.55 * pp.DP]


def degree_num(item):
    if item["time"] < pp.TL:
        return 0.0
    return 1.0 - mean(item["rows"], "excess") / pp.Q0


def top_settlement(item, z0_top):
    return z0_top - pp.top_layer_z(item["rows"])


def summarize_case(xi, tag):
    folder = ROOT / f"CaseTerzaghiConsolidation_q0_PR_{tag}_out" / "particles"
    series = pp.load_series(folder)
    z0_top = pp.top_layer_z(series[0]["rows"])
    at_010 = pp.nearest_snapshot(series, 0.0100)
    at_0125 = pp.nearest_snapshot(series, 0.0125)
    final = pp.nearest_snapshot(series, 0.1100)

    post = [item for item in series if item["time"] >= pp.TL]
    u_rmse = math.sqrt(sum((degree_num(item) - pp.degree_theory(pp.tv_from_time(item["time"]))) ** 2 for item in post) / len(post))
    mean_rmse = math.sqrt(sum((mean(item["rows"], "excess") - pp.Q0 * (1.0 - pp.degree_theory(pp.tv_from_time(item["time"])))) ** 2 for item in post) / len(post))
    max_speed = max(max_value(item["rows"], "speed") for item in series)
    max_speed_post = max(max_value(item["rows"], "speed") for item in post)

    return {
        "xi": xi,
        "tag": tag,
        "t010_mean_kpa": mean(at_010["rows"], "excess") / 1000.0,
        "t010_top_kpa": mean(top_rows(at_010["rows"]), "excess") / 1000.0,
        "t010_bottom_kpa": mean(bottom_rows(at_010["rows"]), "excess") / 1000.0,
        "t0125_top_kpa": mean(top_rows(at_0125["rows"]), "excess") / 1000.0,
        "t0125_mean_kpa": mean(at_0125["rows"], "excess") / 1000.0,
        "final_tv": pp.tv_from_time(final["time"]),
        "final_mean_kpa": mean(final["rows"], "excess") / 1000.0,
        "final_u_num": degree_num(final),
        "final_u_theory": pp.degree_theory(pp.tv_from_time(final["time"])),
        "u_rmse_post": u_rmse,
        "mean_excess_rmse_kpa": mean_rmse / 1000.0,
        "settlement_mm": top_settlement(final, z0_top) * 1000.0,
        "settlement_theory_mm": pp.H * pp.Q0 * pp.MV * pp.degree_theory(pp.tv_from_time(final["time"])) * 1000.0,
        "max_speed": max_speed,
        "max_speed_post": max_speed_post,
        "series": series,
        "z0_top": z0_top,
    }


def write_csv(rows):
    path = FIGDIR / "damping_sweep_q0_summary.csv"
    keys = [
        "xi",
        "t010_mean_kpa",
        "t010_top_kpa",
        "t010_bottom_kpa",
        "t0125_top_kpa",
        "t0125_mean_kpa",
        "final_tv",
        "final_mean_kpa",
        "final_u_num",
        "final_u_theory",
        "u_rmse_post",
        "mean_excess_rmse_kpa",
        "settlement_mm",
        "settlement_theory_mm",
        "max_speed",
        "max_speed_post",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in keys})
    return path


def plot_histories(rows):
    fig, axes = plt.subplots(3, 1, figsize=(9.5, 9.5), sharex=True)
    for row in rows:
        series = row["series"]
        times = [item["time"] for item in series]
        mean_excess = [mean(item["rows"], "excess") / 1000.0 for item in series]
        u_num = [degree_num(item) for item in series]
        settlement = [top_settlement(item, row["z0_top"]) * 1000.0 for item in series]
        axes[0].plot(times, mean_excess, label=f"xi={row['xi']}")
        axes[1].plot(times, u_num, label=f"xi={row['xi']}")
        axes[2].plot(times, settlement, label=f"xi={row['xi']}")

    times = [item["time"] for item in rows[0]["series"]]
    axes[0].plot(times, [pp.load_q(t) / 1000.0 for t in times], "k--", label="q(t)")
    axes[1].plot(times, [pp.degree_theory(pp.tv_from_time(t)) if t >= pp.TL else 0.0 for t in times], "k--", label="Terzaghi")
    axes[2].plot(times, [pp.H * pp.Q0 * pp.MV * (pp.degree_theory(pp.tv_from_time(t)) if t >= pp.TL else 0.0) * 1000.0 for t in times], "k--", label="Terzaghi")

    axes[0].set_ylabel("Mean excess p (kPa)")
    axes[1].set_ylabel("Degree U")
    axes[2].set_ylabel("Settlement (mm)")
    axes[2].set_xlabel("Time (s)")
    for ax in axes:
        ax.axvline(pp.TL, color="0.4", lw=1, ls=":")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    path = FIGDIR / "damping_sweep_q0_history.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True)
    rows = [summarize_case(xi, tag) for xi, tag in CASES]
    csv_path = write_csv(rows)
    png_path = plot_histories(rows)
    print("Damping sweep summary")
    print("xi       t010_mean  t010_top  t0125_top  U_final  U_RMSE    sett_mm  max_speed")
    for row in rows:
        print(
            f"{row['xi']:<8} "
            f"{row['t010_mean_kpa']:>9.3f} "
            f"{row['t010_top_kpa']:>9.3f} "
            f"{row['t0125_top_kpa']:>10.3f} "
            f"{row['final_u_num']:>8.5f} "
            f"{row['u_rmse_post']:>8.5f} "
            f"{row['settlement_mm']:>8.4f} "
            f"{row['max_speed']:>9.3e}"
        )
    print(f"Saved {csv_path}")
    print(f"Saved {png_path}")


if __name__ == "__main__":
    main()
