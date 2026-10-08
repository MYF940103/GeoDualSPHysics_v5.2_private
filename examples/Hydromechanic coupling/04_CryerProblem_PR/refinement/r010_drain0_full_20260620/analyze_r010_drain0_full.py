from pathlib import Path
import csv
import json
import math
import os
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SUPPORT = ROOT / "support"
FIGURES = ROOT / "figures"
sys.path.insert(0, str(SUPPORT))

import postprocess_cryer as cryer


def env_path(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing environment variable {name}")
    return Path(value)


def env_float(name, default):
    value = os.environ.get(name)
    return float(value) if value is not None else default


PARTICLES = env_path("CRYER_PARTICLES")
RUNOUT = env_path("CRYER_RUNOUT")
FIGDIR = env_path("CRYER_FIGDIR")
SUMMARY_JSON = env_path("CRYER_SUMMARY_JSON")
OUTTAG = os.environ.get("CRYER_OUTTAG", "r010_drain0_full")

Q0 = env_float("CRYER_Q0", 10000.0)
RADIUS = env_float("CRYER_RADIUS", 0.05)
RAMP = env_float("CRYER_RAMP", 0.01)


def read_part_times(runout):
    times = {}
    pattern = re.compile(r"^Part_(\d+)\s+([0-9.Ee+-]+)\s+\d+")
    for line in runout.read_text(errors="ignore").splitlines():
        match = pattern.match(line.strip())
        if match:
            times[int(match.group(1))] = float(match.group(2))
    if 0 not in times:
        times[0] = 0.0
    if not times:
        raise RuntimeError(f"No Part_ timing lines found in {runout}")
    return times


def mean(values):
    return sum(values) / len(values) if values else 0.0


def std(values):
    if not values:
        return 0.0
    mu = mean(values)
    return math.sqrt(sum((v - mu) ** 2 for v in values) / len(values))


def global_stats(rows):
    pore = [row["pore"] / Q0 for row in rows]
    return {
        "all_mean": mean(pore),
        "all_std": std(pore),
        "all_min": min(pore),
        "all_max": max(pore),
    }


def tv_from_time(time):
    return cryer.CV * max(0.0, time - RAMP) / (RADIUS * RADIUS)


def load_series():
    times = read_part_times(RUNOUT)
    series = []
    for path in sorted(PARTICLES.glob("PartFluid_*.vtk")):
        idx = cryer.part_index(path)
        if idx not in times:
            continue
        rows = cryer.read_part_vtk(path)
        cstat = cryer.center_stats(rows)
        gstat = global_stats(rows)
        time = times[idx]
        tv = tv_from_time(time)
        theory = cryer.cryer_center_pressure(tv)
        num = cstat["pore"] / Q0
        series.append({
            "part": idx,
            "time": time,
            "time_after_ramp": max(0.0, time - RAMP),
            "tv": tv,
            "center_pore_over_q0": num,
            "theory_pore_over_q0": theory,
            "signed_error": num - theory,
            "abs_error": abs(num - theory),
            "center_pore_pa": cstat["pore"],
            "center_excess_pa": cstat["excess"],
            "sample_count": cstat["count"],
            "free_surface_count": cstat["free_surface_count"],
            "max_speed": cstat["max_speed"],
            **gstat,
        })
    if not series:
        raise RuntimeError(f"No usable VTK files found in {PARTICLES}")
    return series


def write_csv(series):
    path = FIGDIR / f"{OUTTAG}_history.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(series[0].keys()))
        writer.writeheader()
        writer.writerows(series)
    return path


def summarize(series):
    post = [row for row in series if row["time"] + 1e-12 >= RAMP]
    peak = max(post, key=lambda row: row["center_pore_over_q0"])
    max_abs = max(post, key=lambda row: row["abs_error"])
    final = post[-1]
    rmse = math.sqrt(mean([row["signed_error"] ** 2 for row in post]))
    mae = mean([row["abs_error"] for row in post])
    return {
        "ramp": RAMP,
        "q0": Q0,
        "cv": cryer.CV,
        "snapshots": len(series),
        "post_ramp_snapshots": len(post),
        "peak_center": peak["center_pore_over_q0"],
        "peak_time": peak["time"],
        "peak_tv": peak["tv"],
        "theory_at_peak": peak["theory_pore_over_q0"],
        "peak_abs_error": peak["abs_error"],
        "final_center": final["center_pore_over_q0"],
        "final_time": final["time"],
        "final_tv": final["tv"],
        "final_theory": final["theory_pore_over_q0"],
        "final_abs_error": final["abs_error"],
        "max_abs_error": max_abs["abs_error"],
        "max_abs_error_time": max_abs["time"],
        "max_abs_error_tv": max_abs["tv"],
        "rmse": rmse,
        "mae": mae,
        "max_speed": max(row["max_speed"] for row in post),
        "final_max_speed": final["max_speed"],
        "max_global_std": max(row["all_std"] for row in post),
        "final_global_std": final["all_std"],
        "min_pore": min(row["all_min"] for row in post),
        "max_pore": max(row["all_max"] for row in post),
    }


def plot(series, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGURES.mkdir(parents=True, exist_ok=True)
    tv = [row["tv"] for row in series]
    num = [row["center_pore_over_q0"] for row in series]
    err = [row["signed_error"] for row in series]
    speed = [row["max_speed"] for row in series]
    global_std = [row["all_std"] for row in series]

    tvmax = max(tv)
    tv_grid = [tvmax * i / 800.0 for i in range(801)]
    theory = [cryer.cryer_center_pressure(x) for x in tv_grid]

    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    axes[0].plot(tv, num, "o-", ms=3, lw=1.0, label="SPH r010 drain@0 full")
    axes[0].plot(tv_grid, theory, "k-", lw=1.5, label="Cryer analytical, t=0 at ramp end")
    axes[0].axhline(1.0, color="0.5", ls=":", lw=1)
    axes[0].set_ylabel("p_center / q0")
    axes[0].grid(True, alpha=0.28)
    axes[0].legend(loc="best")

    axes[1].plot(tv, err, "C3o-", ms=3, lw=1.0)
    axes[1].axhline(0.0, color="0.35", ls=":", lw=1)
    axes[1].set_ylabel("SPH - analytical")
    axes[1].grid(True, alpha=0.28)

    axes[2].plot(tv, speed, "C2-", lw=1.0, label="max speed")
    axes[2].plot(tv, global_std, "C1-", lw=1.0, label="global std(PorePress/q0)")
    axes[2].set_xlabel("Tv = cv (t - ramp_end) / R^2")
    axes[2].set_ylabel("stability indicators")
    axes[2].grid(True, alpha=0.28)
    axes[2].legend(loc="best")

    fig.suptitle(
        f"r010 drain@0 full: RMSE={summary['rmse']:.4g}, peak={summary['peak_center']:.4g}, final={summary['final_center']:.4g}",
        y=0.995,
    )
    fig.tight_layout()
    local_path = FIGDIR / f"{OUTTAG}_center_pressure.png"
    figure_path = FIGURES / f"cryer_{OUTTAG}_center_pressure.png"
    fig.savefig(local_path, dpi=180)
    fig.savefig(figure_path, dpi=180)
    plt.close(fig)
    return local_path, figure_path


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True)
    series = load_series()
    csv_path = write_csv(series)
    summary = summarize(series)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2))
    local_plot, figure_plot = plot(series, summary)
    print(f"Loaded snapshots: {len(series)}")
    print(f"Peak p/q0={summary['peak_center']:.6g} at t={summary['peak_time']:.6g}, Tv={summary['peak_tv']:.6g}")
    print(f"Final p/q0={summary['final_center']:.6g}; theory={summary['final_theory']:.6g}; abs error={summary['final_abs_error']:.6g}")
    print(f"RMSE={summary['rmse']:.6g}; MAE={summary['mae']:.6g}")
    print(f"Saved {csv_path}")
    print(f"Saved {SUMMARY_JSON}")
    print(f"Saved {local_plot}")
    print(f"Saved {figure_plot}")


if __name__ == "__main__":
    main()
