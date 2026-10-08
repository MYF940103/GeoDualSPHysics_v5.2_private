from pathlib import Path
import csv
import math
import sys

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "support"))
import postprocess_terzaghi_q0 as pp  # noqa: E402


CASE_CPU = "CaseTerzaghiConsolidation_q0_PR_full_k1em4"
CASE_GPU = "CaseTerzaghiConsolidation_q0_PR_full_k1em4_gpu_diagAM_Tv1"
CPU_DIR = ROOT / f"{CASE_CPU}_out" / "particles"
GPU_DIR = ROOT / f"{CASE_GPU}_out" / "particles"
FIGDIR = ROOT / "figures"

TARGET_TV = [0.005, 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0]


def configure_k1em4():
    pp.K_HYD = 1.0e-4
    pp.CV = pp.K_HYD * pp.M_CONSTRAINED / (pp.RHO_W * pp.G_REF)
    pp.TIME_MAX = 36.4471428571428
    pp.TOUT = 0.182185714285714
    pp.DP = 0.01


def snapshot_for_tv(folder, tv):
    idx = int(round(pp.time_from_tv(tv) / pp.TOUT))
    path = folder / f"PartFluid_{idx:04d}.vtk"
    if not path.exists():
        raise FileNotFoundError(path)
    time = idx * pp.TOUT
    rows = pp.read_part_vtk(path)
    return idx, path, time, rows


def metrics(rows, time):
    tv = pp.tv_from_time(time)
    t_rel = max(0.0, time - pp.TL)
    prof = pp.layer_average(rows, "excess")
    errs = []
    vals = []
    for z, p in prof:
        th = pp.terzaghi_excess(z, t_rel)
        errs.append((p - th) ** 2)
        vals.append(th ** 2)
    mean_excess = sum(r["excess"] for r in rows) / len(rows)
    return {
        "actual_tv": tv,
        "profile_rms_kpa": math.sqrt(sum(errs) / len(errs)) / 1000.0,
        "normalized_l2": math.sqrt(sum(errs) / sum(vals)) if sum(vals) > 0 else float("nan"),
        "u_num": 1.0 - mean_excess / pp.Q0,
        "u_theory": pp.degree_theory(tv),
        "max_speed": max(r.get("speed", 0.0) for r in rows),
        "profile": prof,
    }


def build_tables():
    summary = []
    profiles = []
    for tv in TARGET_TV:
        idx_cpu, path_cpu, time_cpu, rows_cpu = snapshot_for_tv(CPU_DIR, tv)
        idx_gpu, path_gpu, time_gpu, rows_gpu = snapshot_for_tv(GPU_DIR, tv)
        mc = metrics(rows_cpu, time_cpu)
        mg = metrics(rows_gpu, time_gpu)
        summary.append({
            "target_tv": tv,
            "cpu_part": idx_cpu,
            "gpu_part": idx_gpu,
            "cpu_time_s": time_cpu,
            "gpu_time_s": time_gpu,
            "cpu_actual_tv": mc["actual_tv"],
            "gpu_actual_tv": mg["actual_tv"],
            "cpu_rms_kpa": mc["profile_rms_kpa"],
            "gpu_rms_kpa": mg["profile_rms_kpa"],
            "gpu_minus_cpu_rms_kpa": mg["profile_rms_kpa"] - mc["profile_rms_kpa"],
            "gpu_over_cpu_rms": mg["profile_rms_kpa"] / mc["profile_rms_kpa"] if mc["profile_rms_kpa"] else float("nan"),
            "cpu_norm_l2": mc["normalized_l2"],
            "gpu_norm_l2": mg["normalized_l2"],
            "cpu_u_num": mc["u_num"],
            "gpu_u_num": mg["u_num"],
            "u_theory": mg["u_theory"],
            "gpu_minus_cpu_u": mg["u_num"] - mc["u_num"],
            "cpu_max_speed": mc["max_speed"],
            "gpu_max_speed": mg["max_speed"],
            "cpu_file": str(path_cpu.relative_to(ROOT)),
            "gpu_file": str(path_gpu.relative_to(ROOT)),
        })
        prof_cpu = {round(z, 8): p for z, p in mc["profile"]}
        prof_gpu = {round(z, 8): p for z, p in mg["profile"]}
        for z in sorted(set(prof_cpu) | set(prof_gpu)):
            t_rel = max(0.0, time_gpu - pp.TL)
            profiles.append({
                "target_tv": tv,
                "actual_tv": mg["actual_tv"],
                "z_m": z,
                "cpu_excess_kpa": prof_cpu.get(z, float("nan")) / 1000.0,
                "gpu_excess_kpa": prof_gpu.get(z, float("nan")) / 1000.0,
                "theory_excess_kpa": pp.terzaghi_excess(z, t_rel) / 1000.0,
            })
    return summary, profiles


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_profiles(summary, profiles):
    zgrid = [i / 200.0 for i in range(201)]
    fig, axes = plt.subplots(2, 4, figsize=(14, 7), sharex=True, sharey=True)
    axes = axes.ravel()
    for ax, row in zip(axes, summary):
        tv = float(row["target_tv"])
        pdata = [p for p in profiles if abs(float(p["target_tv"]) - tv) < 1e-12]
        pdata.sort(key=lambda p: p["z_m"])
        t_rel = max(0.0, float(row["gpu_time_s"]) - pp.TL)
        ax.plot([pp.terzaghi_excess(z, t_rel) / 1000.0 for z in zgrid], zgrid,
                color="#222222", lw=1.2, label="Theory")
        ax.plot([p["cpu_excess_kpa"] for p in pdata], [p["z_m"] for p in pdata],
                color="#1f77b4", lw=1.1, marker="o", ms=2.2, fillstyle="none", label="CPU")
        ax.plot([p["gpu_excess_kpa"] for p in pdata], [p["z_m"] for p in pdata],
                color="#d97706", lw=1.1, marker="x", ms=2.2, label="GPU")
        ax.set_title(f"Tv={row['gpu_actual_tv']:.3f}")
        ax.grid(True, color="#d9d9d9", lw=0.5)
    axes[0].legend(loc="best", fontsize=8)
    for ax in axes:
        ax.set_xlabel("Excess pore pressure (kPa)")
        ax.set_ylabel("z (m)")
    fig.suptitle("q0 Terzaghi k=1e-4: GPU diagAM Tv1 vs CPU profiles", y=0.995)
    fig.tight_layout()
    path = FIGDIR / "gpu_diagAM_Tv1_vs_cpu_profiles.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_metrics(summary):
    tv = [r["target_tv"] for r in summary]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(tv, [r["cpu_rms_kpa"] for r in summary], "o-", color="#1f77b4", label="CPU")
    axes[0].plot(tv, [r["gpu_rms_kpa"] for r in summary], "x-", color="#d97706", label="GPU")
    axes[0].set_xlabel("Tv")
    axes[0].set_ylabel("Profile RMS (kPa)")
    axes[0].set_title("Profile RMS")
    axes[0].grid(True, color="#d9d9d9", lw=0.5)
    axes[0].legend()

    axes[1].plot(tv, [r["u_theory"] for r in summary], "-", color="#222222", label="Theory")
    axes[1].plot(tv, [r["cpu_u_num"] for r in summary], "o-", color="#1f77b4", label="CPU")
    axes[1].plot(tv, [r["gpu_u_num"] for r in summary], "x-", color="#d97706", label="GPU")
    axes[1].set_xlabel("Tv")
    axes[1].set_ylabel("Degree of consolidation")
    axes[1].set_title("Consolidation degree")
    axes[1].grid(True, color="#d9d9d9", lw=0.5)
    axes[1].legend()
    fig.suptitle("q0 Terzaghi k=1e-4: GPU diagAM Tv1 vs CPU metrics", y=0.99)
    fig.tight_layout()
    path = FIGDIR / "gpu_diagAM_Tv1_vs_cpu_metrics.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def main():
    configure_k1em4()
    FIGDIR.mkdir(exist_ok=True)
    summary, profiles = build_tables()
    write_csv(FIGDIR / "gpu_diagAM_Tv1_vs_cpu_summary.csv", summary)
    write_csv(FIGDIR / "gpu_diagAM_Tv1_vs_cpu_profiles_data.csv", profiles)
    p1 = plot_profiles(summary, profiles)
    p2 = plot_metrics(summary)
    print(FIGDIR / "gpu_diagAM_Tv1_vs_cpu_summary.csv")
    print(FIGDIR / "gpu_diagAM_Tv1_vs_cpu_profiles_data.csv")
    print(p1)
    print(p2)
    for row in summary:
        print(
            f"Tv={row['target_tv']:.3g} CPU_RMS={row['cpu_rms_kpa']:.6g} "
            f"GPU_RMS={row['gpu_rms_kpa']:.6g} "
            f"GPU/CPU={row['gpu_over_cpu_rms']:.4g} "
            f"GPU_U={row['gpu_u_num']:.6g}"
        )


if __name__ == "__main__":
    main()
