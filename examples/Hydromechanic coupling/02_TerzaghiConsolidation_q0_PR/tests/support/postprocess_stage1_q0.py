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

Q0 = 10000.0


def load_series(folder, time_out, time_offset):
    series = []
    for path in sorted(folder.glob("PartFluid_*.vtk")):
        idx = pp.part_index(path)
        series.append({
            "name": path.name,
            "index": idx,
            "time": time_offset + idx * time_out,
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


def stage1_theory(z, zmax):
    return 0.0 if z >= zmax - 0.55 * pp.DP else Q0


def profile_metrics(rows):
    prof = pp.layer_average(rows, "excess")
    zmax = max(row["z"] for row in rows)
    sq_all = []
    sq_inner = []
    for z, val in prof:
        th = stage1_theory(z, zmax)
        sq_all.append((val - th) ** 2)
        if z < zmax - 1.55 * pp.DP:
            sq_inner.append((val - Q0) ** 2)
    rms_all = math.sqrt(sum(sq_all) / len(sq_all)) if sq_all else 0.0
    rms_inner = math.sqrt(sum(sq_inner) / len(sq_inner)) if sq_inner else 0.0
    return prof, rms_all, rms_inner


def write_metrics(path, series):
    fields = [
        "snapshot",
        "time_s",
        "mean_excess_kpa",
        "top_excess_kpa",
        "bottom_excess_kpa",
        "rms_profile_all_kpa",
        "rms_profile_inner_kpa",
        "max_speed_m_per_s",
        "particle_count",
    ]
    rows_out = []
    for item in series:
        rows = item["rows"]
        prof, rms_all, rms_inner = profile_metrics(rows)
        bottom_excess = prof[0][1] if prof else 0.0
        rows_out.append({
            "snapshot": item["name"],
            "time_s": item["time"],
            "mean_excess_kpa": mean(rows, "excess") / 1000.0,
            "top_excess_kpa": mean(top_rows(rows), "excess") / 1000.0,
            "bottom_excess_kpa": bottom_excess / 1000.0,
            "rms_profile_all_kpa": rms_all / 1000.0,
            "rms_profile_inner_kpa": rms_inner / 1000.0,
            "max_speed_m_per_s": max_value(rows, "speed"),
            "particle_count": len(rows),
        })
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows_out)
    return rows_out


def write_profile(path, item):
    prof, _, _ = profile_metrics(item["rows"])
    zmax = max(row["z"] for row in item["rows"])
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["z_m", "z_over_H", "excess_kpa", "stage1_theory_kpa", "error_kpa"])
        for z, val in prof:
            theory = stage1_theory(z, zmax)
            writer.writerow([z, z / pp.H, val / 1000.0, theory / 1000.0, (val - theory) / 1000.0])


def plot(figpath, case, series):
    metrics = []
    for item in series:
        prof, rms_all, rms_inner = profile_metrics(item["rows"])
        metrics.append((item, prof, rms_all, rms_inner))

    final, final_prof, _, _ = metrics[-1]
    zmax = max(row["z"] for row in final["rows"])
    times = [item["time"] for item, _, _, _ in metrics]
    rms_inner = [rms / 1000.0 for _, _, _, rms in metrics]
    max_speed = [max_value(item["rows"], "speed") for item, _, _, _ in metrics]
    mean_excess = [mean(item["rows"], "excess") / 1000.0 for item, _, _, _ in metrics]

    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.0))
    axes[0].plot(times, mean_excess, lw=1.5)
    axes[0].axhline(Q0 / 1000.0, color="k", ls="--", lw=1.0)
    axes[0].set_xlabel("time [s]")
    axes[0].set_ylabel("mean excess p [kPa]")
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(times, rms_inner, lw=1.5)
    axes[1].set_xlabel("time [s]")
    axes[1].set_ylabel("inner profile RMS [kPa]")
    axes[1].grid(True, alpha=0.25)

    axes[2].semilogy(times, [max(v, 1e-12) for v in max_speed], lw=1.5)
    axes[2].set_xlabel("time [s]")
    axes[2].set_ylabel("max speed [m/s]")
    axes[2].grid(True, alpha=0.25)
    fig.suptitle(case)
    fig.tight_layout()
    fig.savefig(figpath.with_name(figpath.stem + "_history.png"), dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(4.8, 5.0))
    ax.plot([v / 1000.0 for _, v in final_prof], [z / pp.H for z, _ in final_prof], lw=1.8, label="SPH final")
    ax.plot([stage1_theory(z, zmax) / 1000.0 for z, _ in final_prof], [z / pp.H for z, _ in final_prof], "k--", lw=1.2, label="stage1 target")
    ax.set_xlabel("excess pore pressure [kPa]")
    ax.set_ylabel("z/H")
    ax.grid(True, alpha=0.25)
    ax.legend()
    ax.set_title(f"{case} final profile")
    fig.tight_layout()
    fig.savefig(figpath.with_name(figpath.stem + "_final_profile.png"), dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--particles", type=Path, required=True)
    parser.add_argument("--figdir", type=Path, required=True)
    parser.add_argument("--time-out", type=float, required=True)
    parser.add_argument("--time-offset", type=float, default=0.0)
    args = parser.parse_args()

    args.figdir.mkdir(parents=True, exist_ok=True)
    series = load_series(args.particles, args.time_out, args.time_offset)
    metrics_path = args.figdir / f"{args.case}_stage1_metrics.csv"
    metrics = write_metrics(metrics_path, series)
    profile_path = args.figdir / f"{args.case}_final_profile.csv"
    write_profile(profile_path, series[-1])
    plot(args.figdir / f"{args.case}.png", args.case, series)

    final = metrics[-1]
    summary_path = args.figdir / f"{args.case}_summary.txt"
    with summary_path.open("w") as f:
        f.write(f"case={args.case}\n")
        f.write(f"final_snapshot={final['snapshot']}\n")
        f.write(f"final_time_s={float(final['time_s']):.9g}\n")
        f.write(f"mean_excess_kpa={float(final['mean_excess_kpa']):.9g}\n")
        f.write(f"top_excess_kpa={float(final['top_excess_kpa']):.9g}\n")
        f.write(f"bottom_excess_kpa={float(final['bottom_excess_kpa']):.9g}\n")
        f.write(f"rms_profile_all_kpa={float(final['rms_profile_all_kpa']):.9g}\n")
        f.write(f"rms_profile_inner_kpa={float(final['rms_profile_inner_kpa']):.9g}\n")
        f.write(f"max_speed_m_per_s={float(final['max_speed_m_per_s']):.9g}\n")
        f.write(f"particle_count={final['particle_count']}\n")

    print(summary_path)
    print(f"final mean excess={float(final['mean_excess_kpa']):.6g} kPa, inner RMS={float(final['rms_profile_inner_kpa']):.6g} kPa, max speed={float(final['max_speed_m_per_s']):.6g} m/s")


if __name__ == "__main__":
    main()
