from pathlib import Path
import argparse
import csv
import importlib.util
import math

import matplotlib.pyplot as plt


TESTS = Path(__file__).resolve().parents[1]
CASE_ROOT = TESTS.parent
PP_PATH = CASE_ROOT / "support" / "postprocess_terzaghi_q0.py"

spec = importlib.util.spec_from_file_location("terzaghi_q0", PP_PATH)
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

K_HYD = 1.0e-2
CV = K_HYD * pp.M_CONSTRAINED / (pp.RHO_W * pp.G_REF)
TV1_TIME = pp.H * pp.H / CV
TARGET_TV = [0.0, 0.005, 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0]


def load_series(folder, time_out):
    series = []
    for path in sorted(folder.glob("PartFluid_*.vtk")):
        idx = pp.part_index(path)
        series.append({
            "name": path.name,
            "index": idx,
            "time": idx * time_out,
            "tv": idx * time_out / TV1_TIME,
            "rows": pp.read_part_vtk(path),
        })
    if not series:
        raise RuntimeError(f"No PartFluid VTK files found in {folder}")
    return series


def mean(rows, key):
    vals = [row[key] for row in rows if key in row]
    return sum(vals) / len(vals) if vals else 0.0


def max_value(rows, key):
    vals = [row[key] for row in rows if key in row]
    return max(vals) if vals else 0.0


def top_rows(rows):
    zmax = max(row["z"] for row in rows)
    return [row for row in rows if row["z"] >= zmax - 0.55 * pp.DP]


def terzaghi_excess(z, tv, nterms=240):
    value = 0.0
    for n in range(nterms):
        m = (2 * n + 1) * math.pi / 2.0
        lam = m / pp.H
        an = 2.0 * pp.Q0 * math.sin(lam * pp.H) / (pp.H * lam)
        value += an * math.cos(lam * z) * math.exp(-m * m * tv)
    return value


def profile_rms(rows, tv):
    prof = pp.layer_average(rows, "excess")
    sq = [(p - terzaghi_excess(z, tv)) ** 2 for z, p in prof]
    return math.sqrt(sum(sq) / len(sq)) if sq else 0.0


def degree_num(item):
    return 1.0 - mean(item["rows"], "excess") / pp.Q0


def nearest_snapshot(series, tv):
    return min(series, key=lambda item: abs(item["tv"] - tv))


def write_history(path, series):
    fields = [
        "snapshot",
        "time_s",
        "tv",
        "u_num",
        "u_theory",
        "mean_excess_kpa",
        "top_excess_kpa",
        "profile_rms_kpa",
        "max_speed_m_per_s",
        "particle_count",
    ]
    rows = []
    for item in series:
        rows.append({
            "snapshot": item["name"],
            "time_s": item["time"],
            "tv": item["tv"],
            "u_num": degree_num(item),
            "u_theory": pp.degree_theory(item["tv"]),
            "mean_excess_kpa": mean(item["rows"], "excess") / 1000.0,
            "top_excess_kpa": mean(top_rows(item["rows"]), "excess") / 1000.0,
            "profile_rms_kpa": profile_rms(item["rows"], item["tv"]) / 1000.0,
            "max_speed_m_per_s": max_value(item["rows"], "speed"),
            "particle_count": len(item["rows"]),
        })
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_targets(path, series):
    fields = [
        "target_tv",
        "snapshot",
        "time_s",
        "actual_tv",
        "u_num",
        "u_theory",
        "profile_rms_kpa",
        "mean_excess_kpa",
        "top_excess_kpa",
        "bottom_excess_kpa",
        "max_speed_m_per_s",
    ]
    rows = []
    for tv in TARGET_TV:
        item = nearest_snapshot(series, tv)
        prof = pp.layer_average(item["rows"], "excess")
        rows.append({
            "target_tv": tv,
            "snapshot": item["name"],
            "time_s": item["time"],
            "actual_tv": item["tv"],
            "u_num": degree_num(item),
            "u_theory": pp.degree_theory(item["tv"]),
            "profile_rms_kpa": profile_rms(item["rows"], item["tv"]) / 1000.0,
            "mean_excess_kpa": mean(item["rows"], "excess") / 1000.0,
            "top_excess_kpa": mean(top_rows(item["rows"]), "excess") / 1000.0,
            "bottom_excess_kpa": prof[0][1] / 1000.0 if prof else 0.0,
            "max_speed_m_per_s": max_value(item["rows"], "speed"),
        })
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def plot_history(figdir, case, history):
    tv = [row["tv"] for row in history]
    u_num = [row["u_num"] for row in history]
    u_theory = [row["u_theory"] for row in history]
    rms = [row["profile_rms_kpa"] for row in history]
    speed = [row["max_speed_m_per_s"] for row in history]

    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.0))
    axes[0].plot(tv, u_num, lw=1.6, label="SPH")
    axes[0].plot(tv, u_theory, "k--", lw=1.2, label="Terzaghi")
    axes[0].set_xlabel("Tv")
    axes[0].set_ylabel("degree of consolidation U")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend()

    axes[1].plot(tv, rms, lw=1.5)
    axes[1].set_xlabel("Tv")
    axes[1].set_ylabel("profile RMS [kPa]")
    axes[1].grid(True, alpha=0.25)

    axes[2].semilogy(tv, [max(v, 1e-12) for v in speed], lw=1.5)
    axes[2].set_xlabel("Tv")
    axes[2].set_ylabel("max speed [m/s]")
    axes[2].grid(True, alpha=0.25)

    fig.suptitle(case)
    fig.tight_layout()
    fig.savefig(figdir / f"{case}_stage2_history.png", dpi=180)
    plt.close(fig)


def plot_profiles(figdir, case, series):
    selected = [nearest_snapshot(series, tv) for tv in TARGET_TV if tv > 0.0]
    fig, ax = plt.subplots(figsize=(5.3, 6.0))
    for item in selected:
        prof = pp.layer_average(item["rows"], "excess")
        ax.plot([p / 1000.0 for _, p in prof], [z / pp.H for z, _ in prof], lw=1.2, label=f"SPH Tv={item['tv']:.3f}")
    zvals = [z for z, _ in pp.layer_average(series[0]["rows"], "excess")]
    for tv in [0.05, 0.25, 0.5, 1.0]:
        ax.plot([terzaghi_excess(z, tv) / 1000.0 for z in zvals], [z / pp.H for z in zvals], "k--", lw=0.8, alpha=0.45)
    ax.set_xlabel("excess pore pressure [kPa]")
    ax.set_ylabel("z/H")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)
    ax.set_title(f"{case} pore-pressure profiles")
    fig.tight_layout()
    fig.savefig(figdir / f"{case}_stage2_profiles.png", dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--particles", type=Path, required=True)
    parser.add_argument("--figdir", type=Path, required=True)
    parser.add_argument("--time-out", type=float, required=True)
    args = parser.parse_args()

    args.figdir.mkdir(parents=True, exist_ok=True)
    series = load_series(args.particles, args.time_out)
    history = write_history(args.figdir / f"{args.case}_stage2_history.csv", series)
    targets = write_targets(args.figdir / f"{args.case}_stage2_targets.csv", series)
    plot_history(args.figdir, args.case, history)
    plot_profiles(args.figdir, args.case, series)

    final = history[-1]
    summary_path = args.figdir / f"{args.case}_stage2_summary.txt"
    with summary_path.open("w") as f:
        f.write(f"case={args.case}\n")
        f.write("restart_source=CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t010 Part_0138\n")
        f.write("stage1_restart_time_s=0.069\n")
        f.write(f"tv1_time_s={TV1_TIME:.15g}\n")
        f.write(f"final_snapshot={final['snapshot']}\n")
        f.write(f"final_time_s={float(final['time_s']):.9g}\n")
        f.write(f"final_tv={float(final['tv']):.9g}\n")
        f.write(f"final_u_num={float(final['u_num']):.9g}\n")
        f.write(f"final_u_theory={float(final['u_theory']):.9g}\n")
        f.write(f"final_profile_rms_kpa={float(final['profile_rms_kpa']):.9g}\n")
        f.write(f"final_mean_excess_kpa={float(final['mean_excess_kpa']):.9g}\n")
        f.write(f"final_max_speed_m_per_s={float(final['max_speed_m_per_s']):.9g}\n")
        f.write(f"particle_count={final['particle_count']}\n")
        f.write("\n[target snapshots]\n")
        for row in targets:
            f.write(
                f"Tv={float(row['target_tv']):.3g}, snapshot={row['snapshot']}, "
                f"actual_tv={float(row['actual_tv']):.6g}, U={float(row['u_num']):.6g}, "
                f"Uth={float(row['u_theory']):.6g}, RMS={float(row['profile_rms_kpa']):.6g} kPa\n"
            )

    print(summary_path)
    print(f"final Tv={final['tv']:.6g}, U={final['u_num']:.6g}, Uth={final['u_theory']:.6g}, RMS={final['profile_rms_kpa']:.6g} kPa")


if __name__ == "__main__":
    main()
