from pathlib import Path
import argparse
import csv
import importlib.util
import math

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
POSTPROCESS = ROOT / "support" / "postprocess_terzaghi_q0.py"

spec = importlib.util.spec_from_file_location("terzaghi_q0", POSTPROCESS)
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

TARGET_TV = [0.005, 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0]


def cv_for_k(k):
    return k * pp.M_CONSTRAINED / (pp.RHO_W * pp.G_REF)


def time_from_tv(tv, cv, tl):
    return tl + tv * pp.H * pp.H / cv


def tv_from_time(time, cv, tl):
    return cv * max(0.0, time - tl) / (pp.H * pp.H)


def read_series(folder, tout):
    items = []
    for path in sorted(Path(folder).glob("PartFluid_*.vtk")):
        idx = pp.part_index(path)
        items.append({
            "idx": idx,
            "path": path,
            "time": idx * tout,
            "rows": pp.read_part_vtk(path),
        })
    if not items:
        raise RuntimeError(f"No PartFluid_*.vtk files found in {folder}")
    return items


def nearest(items, time):
    return min(items, key=lambda item: abs(item["time"] - time))


def terzaghi_excess(z, t_rel, cv, nterms=240):
    value = 0.0
    for n in range(nterms):
        lam = (2 * n + 1) * math.pi / (2.0 * pp.H)
        an = 2.0 * pp.Q0 * math.sin(lam * pp.H) / (pp.H * lam)
        value += an * math.cos(lam * z) * math.exp(-lam * lam * cv * t_rel)
    return value


def metrics(item, cv, tl):
    actual_tv = tv_from_time(item["time"], cv, tl)
    t_rel = max(0.0, item["time"] - tl)
    profile = pp.layer_average(item["rows"], "excess")
    errs = []
    vals = []
    for z, pnum in profile:
        pth = terzaghi_excess(z, t_rel, cv)
        errs.append((pnum - pth) ** 2)
        vals.append(pth ** 2)
    mean_excess = sum(row["excess"] for row in item["rows"]) / len(item["rows"])
    return {
        "actual_tv": actual_tv,
        "profile": profile,
        "profile_rms_kpa": math.sqrt(sum(errs) / len(errs)) / 1000.0,
        "normalized_l2": math.sqrt(sum(errs) / sum(vals)) if sum(vals) else float("nan"),
        "u_num": 1.0 - mean_excess / pp.Q0,
        "u_theory": pp.degree_theory(actual_tv),
        "max_speed": max(row.get("speed", 0.0) for row in item["rows"]),
    }


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_comparison(cpu_dir, gpu_dir, cv, tl, tout):
    cpu_items = read_series(cpu_dir, tout)
    gpu_items = read_series(gpu_dir, tout)
    max_tv = min(tv_from_time(cpu_items[-1]["time"], cv, tl), tv_from_time(gpu_items[-1]["time"], cv, tl))
    tv_tol = 0.51 * cv * tout / (pp.H * pp.H)
    summary = []
    profiles = []
    for tv in TARGET_TV:
        if tv > max_tv + tv_tol:
            continue
        target_time = time_from_tv(tv, cv, tl)
        cpu = nearest(cpu_items, target_time)
        gpu = nearest(gpu_items, target_time)
        cm = metrics(cpu, cv, tl)
        gm = metrics(gpu, cv, tl)
        summary.append({
            "target_tv": tv,
            "cpu_part": cpu["idx"],
            "gpu_part": gpu["idx"],
            "cpu_time_s": cpu["time"],
            "gpu_time_s": gpu["time"],
            "cpu_actual_tv": cm["actual_tv"],
            "gpu_actual_tv": gm["actual_tv"],
            "cpu_rms_kpa": cm["profile_rms_kpa"],
            "gpu_rms_kpa": gm["profile_rms_kpa"],
            "gpu_minus_cpu_rms_kpa": gm["profile_rms_kpa"] - cm["profile_rms_kpa"],
            "gpu_over_cpu_rms": gm["profile_rms_kpa"] / cm["profile_rms_kpa"] if cm["profile_rms_kpa"] else float("nan"),
            "cpu_norm_l2": cm["normalized_l2"],
            "gpu_norm_l2": gm["normalized_l2"],
            "cpu_u_num": cm["u_num"],
            "gpu_u_num": gm["u_num"],
            "u_theory": gm["u_theory"],
            "gpu_minus_cpu_u": gm["u_num"] - cm["u_num"],
            "cpu_max_speed": cm["max_speed"],
            "gpu_max_speed": gm["max_speed"],
            "cpu_file": str(cpu["path"]),
            "gpu_file": str(gpu["path"]),
        })
        cpu_prof = {round(z, 8): p for z, p in cm["profile"]}
        gpu_prof = {round(z, 8): p for z, p in gm["profile"]}
        for z in sorted(set(cpu_prof) | set(gpu_prof)):
            profiles.append({
                "target_tv": tv,
                "actual_tv": gm["actual_tv"],
                "z_m": z,
                "cpu_excess_kpa": cpu_prof.get(z, float("nan")) / 1000.0,
                "gpu_excess_kpa": gpu_prof.get(z, float("nan")) / 1000.0,
                "theory_excess_kpa": terzaghi_excess(z, max(0.0, gpu["time"] - tl), cv) / 1000.0,
            })
    return summary, profiles


def plot_profiles(path, title, summary, profiles, cv, tl):
    ncols = 4
    nrows = math.ceil(len(summary) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 3.4 * nrows), sharex=True, sharey=True)
    axes = list(axes.ravel()) if hasattr(axes, "ravel") else [axes]
    zgrid = [i / 200.0 for i in range(201)]
    for ax, row in zip(axes, summary):
        tv = float(row["target_tv"])
        pdata = [p for p in profiles if abs(float(p["target_tv"]) - tv) < 1e-12]
        pdata.sort(key=lambda p: p["z_m"])
        t_rel = max(0.0, float(row["gpu_time_s"]) - tl)
        ax.plot([terzaghi_excess(z, t_rel, cv) / 1000.0 for z in zgrid], zgrid, color="#222222", lw=1.1, label="Theory")
        ax.plot([p["cpu_excess_kpa"] for p in pdata], [p["z_m"] for p in pdata], "o-", color="#1f77b4", lw=1.0, ms=2.2, fillstyle="none", label="CPU")
        ax.plot([p["gpu_excess_kpa"] for p in pdata], [p["z_m"] for p in pdata], "x-", color="#d97706", lw=1.0, ms=2.2, label="GPU")
        ax.set_title(f"Tv={row['gpu_actual_tv']:.3f}")
        ax.grid(True, color="#d9d9d9", lw=0.5)
        ax.set_xlabel("Excess pore pressure (kPa)")
        ax.set_ylabel("z (m)")
    for ax in axes[len(summary):]:
        ax.axis("off")
    axes[0].legend(loc="best", fontsize=8)
    fig.suptitle(title, y=0.995)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_metrics(path, title, summary):
    tv = [row["target_tv"] for row in summary]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(tv, [row["cpu_rms_kpa"] for row in summary], "o-", color="#1f77b4", label="CPU")
    axes[0].plot(tv, [row["gpu_rms_kpa"] for row in summary], "x-", color="#d97706", label="GPU")
    axes[0].set_xlabel("Tv")
    axes[0].set_ylabel("Profile RMS (kPa)")
    axes[0].grid(True, color="#d9d9d9", lw=0.5)
    axes[0].legend()
    axes[1].plot(tv, [row["u_theory"] for row in summary], "-", color="#222222", label="Theory")
    axes[1].plot(tv, [row["cpu_u_num"] for row in summary], "o-", color="#1f77b4", label="CPU")
    axes[1].plot(tv, [row["gpu_u_num"] for row in summary], "x-", color="#d97706", label="GPU")
    axes[1].set_xlabel("Tv")
    axes[1].set_ylabel("Degree of consolidation")
    axes[1].grid(True, color="#d9d9d9", lw=0.5)
    axes[1].legend()
    fig.suptitle(title, y=0.99)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--cpu-dir", required=True)
    parser.add_argument("--gpu-dir", required=True)
    parser.add_argument("--figures", required=True)
    parser.add_argument("--title", default="q0 Terzaghi CPU/GPU comparison")
    parser.add_argument("--k", type=float, default=1e-4)
    parser.add_argument("--tl", type=float, default=0.01)
    parser.add_argument("--tout", type=float, default=0.182185714285714)
    args = parser.parse_args()

    cv = cv_for_k(args.k)
    figures = Path(args.figures)
    figures.mkdir(parents=True, exist_ok=True)
    summary, profiles = build_comparison(args.cpu_dir, args.gpu_dir, cv, args.tl, args.tout)
    summary_path = figures / f"{args.label}_vs_cpu_summary.csv"
    profiles_path = figures / f"{args.label}_vs_cpu_profiles_data.csv"
    profiles_png = figures / f"{args.label}_vs_cpu_profiles.png"
    metrics_png = figures / f"{args.label}_vs_cpu_metrics.png"
    write_csv(summary_path, summary)
    write_csv(profiles_path, profiles)
    plot_profiles(profiles_png, args.title, summary, profiles, cv, args.tl)
    plot_metrics(metrics_png, args.title, summary)
    print(summary_path)
    print(profiles_path)
    print(profiles_png)
    print(metrics_png)
    for row in summary:
        print(
            f"Tv={row['target_tv']:.3g} CPU_RMS={row['cpu_rms_kpa']:.6g} "
            f"GPU_RMS={row['gpu_rms_kpa']:.6g} GPU/CPU={row['gpu_over_cpu_rms']:.4g} "
            f"GPU_U={row['gpu_u_num']:.6g}"
        )


if __name__ == "__main__":
    main()
