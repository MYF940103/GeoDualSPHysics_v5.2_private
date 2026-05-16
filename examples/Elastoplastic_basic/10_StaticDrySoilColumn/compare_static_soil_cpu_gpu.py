from __future__ import annotations

import csv
import math
import pathlib
from collections import defaultdict

import matplotlib.pyplot as plt


ROOT = pathlib.Path(__file__).resolve().parent
FIG_DIR = ROOT / "figure"
FIG_DIR.mkdir(exist_ok=True)

CASE = "CaseStaticDrySoilColumn2D_Feng2021_dp002"
CPU_LABEL = "CPU"
GPU_LABEL = "GPU"
RHO0 = 2100.0
GRAVITY = 9.81
HEIGHT = 1.0
DP = 0.02
FINAL_PART = 50


def final_csv(device: str) -> pathlib.Path:
    return ROOT / f"{CASE}_{device}_out" / "particles" / f"PartFluidCsv_{FINAL_PART:04d}.csv"


def read_particle_csv(path: pathlib.Path) -> dict[int, dict[str, float]]:
    lines = path.read_text().splitlines()
    header = [v for v in lines[3].split(";") if v]
    rows = {}
    for line in lines[4:]:
        if not line.strip():
            continue
        values = [v.strip() for v in line.split(";")]
        if values and values[-1] == "":
            values = values[:-1]
        if len(values) < len(header):
            continue
        item = dict(zip(header, values))
        idp = int(float(item["Idp"]))
        vx = float(item["Vel.x [m/s]"])
        vy = float(item["Vel.y [m/s]"])
        vz = float(item["Vel.z [m/s]"])
        z = float(item["Pos.z [m]"])
        szz = float(item["Sigma_kk.z"])
        sigma_norm = -szz / (RHO0 * GRAVITY * HEIGHT)
        ana = max(0.0, (HEIGHT - z) / HEIGHT)
        rows[idp] = {
            "idp": idp,
            "x": float(item["Pos.x [m]"]),
            "z": z,
            "vx": vx,
            "vy": vy,
            "vz": vz,
            "velm": math.sqrt(vx * vx + vy * vy + vz * vz),
            "rhop": float(item["Rhop [kg/m^3]"]),
            "szz": szz,
            "sigma_norm": sigma_norm,
            "sigma_ana_norm": ana,
            "error_norm": sigma_norm - ana,
            "depth_norm": max(0.0, (HEIGHT - z) / HEIGHT),
        }
    return rows


def profile(rows: dict[int, dict[str, float]], label: str) -> list[dict[str, float | str]]:
    grouped = defaultdict(list)
    for row in rows.values():
        idx = round((row["z"] - DP / 2.0) / DP)
        grouped[idx].append(row)
    out = []
    for idx in sorted(grouped):
        group = grouped[idx]
        z_mean = sum(r["z"] for r in group) / len(group)
        sig_mean = sum(r["sigma_norm"] for r in group) / len(group)
        ana = max(0.0, (HEIGHT - z_mean) / HEIGHT)
        out.append({
            "device": label,
            "z_mean": z_mean,
            "depth_norm": max(0.0, (HEIGHT - z_mean) / HEIGHT),
            "sigma_norm": sig_mean,
            "sigma_ana_norm": ana,
            "error_norm": sig_mean - ana,
            "n": len(group),
        })
    return out


def metrics(rows: dict[int, dict[str, float]], label: str) -> dict[str, float | str]:
    errors = [r["error_norm"] for r in rows.values()]
    ana = [r["sigma_ana_norm"] for r in rows.values()]
    return {
        "device": label,
        "particles": len(rows),
        "l2_norm_vs_analytical": math.sqrt(sum(e * e for e in errors) / sum(a * a for a in ana)),
        "rmse_norm_vs_analytical": math.sqrt(sum(e * e for e in errors) / len(errors)),
        "max_abs_error_norm_vs_analytical": max(abs(e) for e in errors),
        "max_velocity": max(r["velm"] for r in rows.values()),
        "z_min": min(r["z"] for r in rows.values()),
        "z_max": max(r["z"] for r in rows.values()),
    }


def save_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def plot_profiles(cpu_profile: list[dict], gpu_profile: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 5.2), dpi=160)
    depth = [i / 100 for i in range(101)]
    ax.plot(depth, depth, "k--", lw=1.5, label="Analytical")
    for label, prof in [(CPU_LABEL, cpu_profile), (GPU_LABEL, gpu_profile)]:
        ax.plot([p["sigma_norm"] for p in prof], [p["depth_norm"] for p in prof], marker="o", ms=3, lw=1.4, label=label)
    ax.set_xlabel(r"$-\sigma_{zz}/(\rho g H)$")
    ax.set_ylabel("Normalised depth below surface")
    ax.set_title("Static soil column dp=0.02: CPU vs GPU")
    ax.set_xlim(left=0)
    ax.set_ylim(1.05, -0.05)
    ax.grid(True, alpha=0.28)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "static_soil_dp002_cpu_gpu_profile.png")
    plt.close(fig)


def plot_error(cpu_profile: list[dict], gpu_profile: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 5.2), dpi=160)
    ax.axvline(0, color="k", lw=1)
    for label, prof in [(CPU_LABEL, cpu_profile), (GPU_LABEL, gpu_profile)]:
        ax.plot([p["error_norm"] for p in prof], [p["depth_norm"] for p in prof], marker="o", ms=3, lw=1.4, label=label)
    ax.set_xlabel("Normalised stress error vs analytical")
    ax.set_ylabel("Normalised depth below surface")
    ax.set_title("Static soil column dp=0.02: CPU/GPU analytical error")
    ax.set_ylim(1.05, -0.05)
    ax.grid(True, alpha=0.28)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "static_soil_dp002_cpu_gpu_error.png")
    plt.close(fig)


def plot_delta(pointwise: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 5.2), dpi=160)
    ax.axvline(0, color="k", lw=1)
    ax.plot([p["delta_sigma_norm_gpu_minus_cpu"] for p in pointwise], [p["depth_norm_cpu"] for p in pointwise], marker="o", ms=2.5, lw=1.2)
    ax.set_xlabel("GPU - CPU normalised vertical stress")
    ax.set_ylabel("Normalised depth below surface")
    ax.set_title("Static soil column dp=0.02: pointwise CPU/GPU difference")
    ax.set_ylim(1.05, -0.05)
    ax.grid(True, alpha=0.28)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "static_soil_dp002_cpu_gpu_delta.png")
    plt.close(fig)


def main() -> None:
    cpu = read_particle_csv(final_csv(CPU_LABEL))
    gpu = read_particle_csv(final_csv(GPU_LABEL))
    common = sorted(set(cpu) & set(gpu))
    if len(common) != len(cpu) or len(common) != len(gpu):
        raise RuntimeError(f"Particle id mismatch: common={len(common)} cpu={len(cpu)} gpu={len(gpu)}")

    pointwise = []
    for idp in common:
        c = cpu[idp]
        g = gpu[idp]
        pointwise.append({
            "idp": idp,
            "z_cpu": c["z"],
            "z_gpu": g["z"],
            "depth_norm_cpu": c["depth_norm"],
            "sigma_norm_cpu": c["sigma_norm"],
            "sigma_norm_gpu": g["sigma_norm"],
            "sigma_ana_norm": c["sigma_ana_norm"],
            "delta_sigma_norm_gpu_minus_cpu": g["sigma_norm"] - c["sigma_norm"],
            "delta_szz_pa_gpu_minus_cpu": g["szz"] - c["szz"],
            "error_norm_cpu": c["error_norm"],
            "error_norm_gpu": g["error_norm"],
            "velm_cpu": c["velm"],
            "velm_gpu": g["velm"],
            "delta_velm_gpu_minus_cpu": g["velm"] - c["velm"],
            "delta_pos_z_gpu_minus_cpu": g["z"] - c["z"],
        })

    diffs = [p["delta_sigma_norm_gpu_minus_cpu"] for p in pointwise]
    szz_diffs = [p["delta_szz_pa_gpu_minus_cpu"] for p in pointwise]
    vel_diffs = [p["delta_velm_gpu_minus_cpu"] for p in pointwise]
    pos_diffs = [p["delta_pos_z_gpu_minus_cpu"] for p in pointwise]
    cpu_sig = [p["sigma_norm_cpu"] for p in pointwise]

    rows_metrics = [
        metrics(cpu, CPU_LABEL),
        metrics(gpu, GPU_LABEL),
        {
            "device": "GPU-CPU",
            "particles": len(pointwise),
            "l2_norm_vs_cpu": math.sqrt(sum(d * d for d in diffs) / sum(s * s for s in cpu_sig)),
            "rmse_norm_vs_cpu": math.sqrt(sum(d * d for d in diffs) / len(diffs)),
            "max_abs_sigma_norm_diff_vs_cpu": max(abs(d) for d in diffs),
            "max_abs_velm_diff": max(abs(d) for d in vel_diffs),
            "min_delta_z": min(pos_diffs),
            "max_delta_z": max(pos_diffs),
            "max_abs_szz_pa_diff": max(abs(d) for d in szz_diffs),
        },
    ]

    cpu_profile = profile(cpu, CPU_LABEL)
    gpu_profile = profile(gpu, GPU_LABEL)
    save_csv(FIG_DIR / "static_soil_dp002_cpu_gpu_metrics.csv", rows_metrics)
    save_csv(FIG_DIR / "static_soil_dp002_cpu_gpu_profiles.csv", cpu_profile + gpu_profile)
    save_csv(FIG_DIR / "static_soil_dp002_cpu_gpu_pointwise.csv", pointwise)
    plot_profiles(cpu_profile, gpu_profile)
    plot_error(cpu_profile, gpu_profile)
    plot_delta(pointwise)

    print("CPU/GPU metrics:")
    for row in rows_metrics:
        print(row)


if __name__ == "__main__":
    main()
