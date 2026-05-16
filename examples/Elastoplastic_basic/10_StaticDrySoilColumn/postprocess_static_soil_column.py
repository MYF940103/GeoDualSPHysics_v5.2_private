from __future__ import annotations

import csv
import math
import pathlib
import subprocess
from collections import defaultdict

import matplotlib.pyplot as plt


ROOT = pathlib.Path(__file__).resolve().parent
FIG_DIR = ROOT / "figure"
FIG_DIR.mkdir(exist_ok=True)

RHO0 = 2100.0
GRAVITY = 9.81
HEIGHT = 1.0
FINAL_PART = 50

CASES = [
    {"name": "CaseStaticDrySoilColumn2D_Feng2021_dp010_xi002_ddt2", "dp": 0.10, "xi": 0.02, "ddt": 2, "group": "resolution"},
    {"name": "CaseStaticDrySoilColumn2D_Feng2021_dp005_xi002_ddt2", "dp": 0.05, "xi": 0.02, "ddt": 2, "group": "resolution"},
    {"name": "CaseStaticDrySoilColumn2D_Feng2021_dp002", "dp": 0.02, "xi": 0.02, "ddt": 2, "group": "resolution"},
    {"name": "CaseStaticDrySoilColumn2D_Feng2021_dp002_xi000_ddt2", "dp": 0.02, "xi": 0.00, "ddt": 2, "group": "damping"},
    {"name": "CaseStaticDrySoilColumn2D_Feng2021_dp002_xi001_ddt2", "dp": 0.02, "xi": 0.01, "ddt": 2, "group": "damping"},
    {"name": "CaseStaticDrySoilColumn2D_Feng2021_dp002", "dp": 0.02, "xi": 0.02, "ddt": 2, "group": "damping"},
    {"name": "CaseStaticDrySoilColumn2D_Feng2021_dp002_xi005_ddt2", "dp": 0.02, "xi": 0.05, "ddt": 2, "group": "damping"},
    {"name": "CaseStaticDrySoilColumn2D_Feng2021_dp002_xi002_ddt0", "dp": 0.02, "xi": 0.02, "ddt": 0, "group": "ddt"},
    {"name": "CaseStaticDrySoilColumn2D_Feng2021_dp002_xi002_ddt1", "dp": 0.02, "xi": 0.02, "ddt": 1, "group": "ddt"},
    {"name": "CaseStaticDrySoilColumn2D_Feng2021_dp002", "dp": 0.02, "xi": 0.02, "ddt": 2, "group": "ddt"},
    {"name": "CaseStaticDrySoilColumn2D_Feng2021_dp002_xi002_ddt3", "dp": 0.02, "xi": 0.02, "ddt": 3, "group": "ddt"},
]


def case_out(name: str) -> pathlib.Path:
    return ROOT / f"{name}_CPU_out"


def final_csv(name: str) -> pathlib.Path:
    return case_out(name) / "particles" / f"PartFluidCsv_{FINAL_PART:04d}.csv"


def ensure_final_csv(name: str) -> None:
    csv_path = final_csv(name)
    if csv_path.exists():
        return
    data_dir = case_out(name) / "data"
    if not data_dir.exists():
        raise FileNotFoundError(f"Missing data directory for {name}: {data_dir}")
    particles_dir = case_out(name) / "particles"
    particles_dir.mkdir(exist_ok=True)
    partvtk = ROOT.parents[2] / "bin" / "windows" / "PartVTK_win64.exe"
    cmd = (
        f'"{partvtk}" -dirin "{data_dir}" -files:{FINAL_PART} '
        f'-savecsv "{particles_dir / "PartFluidCsv"}" '
        f'-onlytype:-all,fluid '
        f'-vars:+idp,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic'
    )
    subprocess.run(cmd, shell=True, check=True, cwd=ROOT)


def read_particle_csv(path: pathlib.Path) -> list[dict[str, float]]:
    lines = path.read_text().splitlines()
    header = [v for v in lines[3].split(";") if v]
    rows = []
    for line in lines[4:]:
        if not line.strip():
            continue
        values = [v.strip() for v in line.split(";")]
        if values and values[-1] == "":
            values = values[:-1]
        if len(values) < len(header):
            continue
        item = dict(zip(header, values))
        rows.append({
            "x": float(item["Pos.x [m]"]),
            "z": float(item["Pos.z [m]"]),
            "idp": float(item["Idp"]),
            "velm": math.sqrt(float(item["Vel.x [m/s]"]) ** 2 + float(item["Vel.y [m/s]"]) ** 2 + float(item["Vel.z [m/s]"]) ** 2),
            "rhop": float(item["Rhop [kg/m^3]"]),
            "szz": float(item["Sigma_kk.z"]),
        })
    return rows


def analyse_case(meta: dict) -> tuple[dict, list[dict]]:
    name = meta["name"]
    ensure_final_csv(name)
    rows = read_particle_csv(final_csv(name))
    if not rows:
        raise RuntimeError(f"No particles read for {name}")
    denom = RHO0 * GRAVITY * HEIGHT
    errors = []
    ana_values = []
    for row in rows:
        z = row["z"]
        numerical = -row["szz"] / denom
        analytical = max(0.0, (HEIGHT - z) / HEIGHT)
        row["sigma_norm"] = numerical
        row["sigma_ana_norm"] = analytical
        row["error_norm"] = numerical - analytical
        row["depth_norm"] = max(0.0, (HEIGHT - z) / HEIGHT)
        errors.append(row["error_norm"])
        ana_values.append(analytical)

    l2 = math.sqrt(sum(e * e for e in errors) / sum(a * a for a in ana_values))
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    max_abs = max(abs(e) for e in errors)
    max_vel = max(row["velm"] for row in rows)

    grouped = defaultdict(list)
    dp = meta["dp"]
    for row in rows:
        idx = round((row["z"] - dp / 2.0) / dp)
        grouped[idx].append(row)

    profile = []
    for idx in sorted(grouped):
        group = grouped[idx]
        z_mean = sum(r["z"] for r in group) / len(group)
        sig_mean = sum(r["sigma_norm"] for r in group) / len(group)
        ana = max(0.0, (HEIGHT - z_mean) / HEIGHT)
        profile.append({
            **meta,
            "z_mean": z_mean,
            "depth_norm": max(0.0, (HEIGHT - z_mean) / HEIGHT),
            "sigma_norm": sig_mean,
            "sigma_ana_norm": ana,
            "error_norm": sig_mean - ana,
            "n": len(group),
        })

    metrics = {
        **meta,
        "particles": len(rows),
        "l2_norm": l2,
        "rmse_norm": rmse,
        "max_abs_error_norm": max_abs,
        "max_velocity": max_vel,
        "z_min": min(r["z"] for r in rows),
        "z_max": max(r["z"] for r in rows),
    }
    return metrics, profile


def label(meta: dict) -> str:
    return f"dp={meta['dp']:.2g}, xi={meta['xi']:.2g}, DDT={meta['ddt']}"


def save_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def plot_profile(path: pathlib.Path, profiles: list[list[dict]], title: str) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 5.2), dpi=160)
    depth = [i / 100 for i in range(101)]
    ax.plot(depth, depth, "k--", lw=1.5, label="Analytical")
    for prof in profiles:
        if not prof:
            continue
        meta = prof[0]
        ax.plot([p["sigma_norm"] for p in prof], [p["depth_norm"] for p in prof], marker="o", ms=3, lw=1.4, label=label(meta))
    ax.set_xlabel(r"$-\sigma_{zz}/(\rho g H)$")
    ax.set_ylabel("Normalised depth below surface")
    ax.set_title(title)
    ax.set_xlim(left=0)
    ax.set_ylim(1.05, -0.05)
    ax.grid(True, alpha=0.28)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_error(path: pathlib.Path, profiles: list[list[dict]], title: str) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 5.2), dpi=160)
    ax.axvline(0, color="k", lw=1)
    for prof in profiles:
        if not prof:
            continue
        meta = prof[0]
        ax.plot([p["error_norm"] for p in prof], [p["depth_norm"] for p in prof], marker="o", ms=3, lw=1.4, label=label(meta))
    ax.set_xlabel("Normalised stress error")
    ax.set_ylabel("Normalised depth below surface")
    ax.set_title(title)
    ax.set_ylim(1.05, -0.05)
    ax.grid(True, alpha=0.28)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_l2_bars(path: pathlib.Path, metrics: list[dict], title: str, key: str) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=160)
    labels = [str(m[key]) for m in metrics]
    values = [m["l2_norm"] for m in metrics]
    ax.bar(labels, values, color="#377eb8")
    ax.set_xlabel(key)
    ax.set_ylabel("Normalised L2 error")
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.28)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    metrics_by_identity = {}
    profiles_by_identity = {}
    grouped_profiles = defaultdict(list)
    grouped_metrics = defaultdict(list)

    for meta in CASES:
        metrics, profile = analyse_case(meta)
        identity = (meta["name"], meta["dp"], meta["xi"], meta["ddt"])
        metrics_by_identity[identity] = metrics
        profiles_by_identity[identity] = profile
        grouped_profiles[meta["group"]].append(profile)
        grouped_metrics[meta["group"]].append(metrics)

    metrics_rows = list(metrics_by_identity.values())
    profile_rows = [row for profile in profiles_by_identity.values() for row in profile]
    save_csv(FIG_DIR / "static_soil_column_metrics.csv", metrics_rows)
    save_csv(FIG_DIR / "static_soil_column_profiles.csv", profile_rows)

    base_profile = profiles_by_identity[("CaseStaticDrySoilColumn2D_Feng2021_dp002", 0.02, 0.02, 2)]
    plot_profile(FIG_DIR / "static_soil_base_profile_vs_analytical.png", [base_profile], "Feng 2021 static soil column: final stress profile")
    plot_error(FIG_DIR / "static_soil_base_error_profile.png", [base_profile], "Feng 2021 static soil column: final stress error")

    plot_profile(FIG_DIR / "static_soil_resolution_profiles.png", grouped_profiles["resolution"], "Resolution comparison at xi=0.02, DDT=2")
    plot_error(FIG_DIR / "static_soil_resolution_error_profiles.png", grouped_profiles["resolution"], "Resolution stress-error profiles")
    plot_l2_bars(FIG_DIR / "static_soil_resolution_l2.png", sorted(grouped_metrics["resolution"], key=lambda x: x["dp"]), "Normalised L2 error vs resolution", "dp")

    plot_profile(FIG_DIR / "static_soil_damping_profiles.png", grouped_profiles["damping"], "Damping sensitivity at dp=0.02, DDT=2")
    plot_error(FIG_DIR / "static_soil_damping_error_profiles.png", grouped_profiles["damping"], "Damping stress-error profiles")
    plot_l2_bars(FIG_DIR / "static_soil_damping_l2.png", sorted(grouped_metrics["damping"], key=lambda x: x["xi"]), "Normalised L2 error vs damping coefficient", "xi")

    plot_profile(FIG_DIR / "static_soil_ddt_profiles.png", grouped_profiles["ddt"], "Stress diffusion sensitivity at dp=0.02, xi=0.02")
    plot_error(FIG_DIR / "static_soil_ddt_error_profiles.png", grouped_profiles["ddt"], "Stress diffusion stress-error profiles")
    plot_l2_bars(FIG_DIR / "static_soil_ddt_l2.png", sorted(grouped_metrics["ddt"], key=lambda x: x["ddt"]), "Normalised L2 error vs stress diffusion option", "ddt")

    print("Wrote:")
    for path in sorted(FIG_DIR.glob("static_soil_*")):
        print(f"  {path}")


if __name__ == "__main__":
    main()
