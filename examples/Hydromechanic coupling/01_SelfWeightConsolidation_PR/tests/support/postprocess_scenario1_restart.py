from pathlib import Path
import argparse
import csv
import math
import sys

import matplotlib.pyplot as plt


CASE_ROOT = Path(__file__).resolve().parents[2]
ROOT_SUPPORT = CASE_ROOT / "support"
if str(ROOT_SUPPORT) not in sys.path:
    sys.path.insert(0, str(ROOT_SUPPORT))

import postprocess_self_weight_consolidation as pp


DEFAULT_TARGET_TV = [0.0, 0.005, 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0]


def part_index(path):
    return int(path.stem.rsplit("_", 1)[1])


def load_series(particles, tout, tmax):
    series = []
    for path in sorted(particles.glob("PartFluid_*.vtk")):
        idx = part_index(path)
        time_s = min(tmax, idx * tout)
        series.append({
            "name": path.name,
            "index": idx,
            "time_s": time_s,
            "tv": pp.CV_TERZAGHI * time_s / (pp.H * pp.H),
            "rows": pp.read_part_vtk(path),
        })
    if not series:
        raise RuntimeError(f"No PartFluid VTK files found in {particles}")
    return series


def profile_integral(profile):
    return sum(value for _, value in profile) * pp.DP


def build_cosine_solution(initial_profile, nterms=240):
    coeffs = []
    for n in range(nterms):
        lam = (2 * n + 1) * math.pi / (2.0 * pp.H)
        integral = sum(value * math.cos(lam * z) for z, value in initial_profile) * pp.DP
        coeffs.append((lam, 2.0 * integral / pp.H))

    def solution(z, time_s):
        t = max(0.0, time_s)
        return sum(an * math.cos(lam * z) * math.exp(-lam * lam * pp.CV_TERZAGHI * t) for lam, an in coeffs)

    return solution


def rms_profile(rows, value_key, theory):
    values = [(row[value_key] - theory(row["z"])) for row in rows if value_key in row]
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else float("nan")


def nearest_targets(series):
    selected = []
    used = set()
    for target_tv in DEFAULT_TARGET_TV:
        item = min(series, key=lambda row: abs(row["tv"] - target_tv))
        if item["index"] not in used:
            selected.append((target_tv, item))
            used.add(item["index"])
    return selected


def write_profile_csv(path, selected, analytical):
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "target_Tv",
            "actual_Tv",
            "part",
            "z_m",
            "z_over_H",
            "pore_sph_kPa",
            "pore_theory_kPa",
        ])
        for target_tv, item in selected:
            prof = pp.layer_average(item["rows"], "pore")
            for z, pore in prof:
                writer.writerow([
                    target_tv,
                    item["tv"],
                    item["name"],
                    z,
                    z / pp.H,
                    pore / 1000.0,
                    analytical(z, item["time_s"]) / 1000.0,
                ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--particles", required=True, type=Path)
    parser.add_argument("--figdir", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--tout", required=True, type=float)
    parser.add_argument("--tmax", required=True, type=float)
    args = parser.parse_args()

    series = load_series(args.particles, args.tout, args.tmax)
    initial = series[0]
    initial_profile = pp.layer_average(initial["rows"], "pore")
    analytical = build_cosine_solution(initial_profile)
    initial_integral = profile_integral(initial_profile)

    args.figdir.mkdir(parents=True, exist_ok=True)
    selected = nearest_targets(series)
    zgrid = [i / 200.0 for i in range(201)]

    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.2), constrained_layout=True)
    ax_profile, ax_degree = axes

    colors = plt.cm.viridis([i / max(1, len(selected) - 1) for i in range(len(selected))])
    target_rows = []
    for color, (target_tv, item) in zip(colors, selected):
        label = f"Tv={item['tv']:.3f}"
        prof = pp.layer_average(item["rows"], "pore")
        ax_profile.plot([v / 1000.0 for _, v in prof], [z / pp.H for z, _ in prof], color=color, linewidth=1.35, label=label)
        ax_profile.plot(
            [analytical(z, item["time_s"]) / 1000.0 for z in zgrid],
            [z / pp.H for z in zgrid],
            "--",
            color=color,
            linewidth=0.95,
            alpha=0.68,
        )
        bnum, bz = pp.bottom_average(item["rows"], "pore")
        btheory = analytical(bz, item["time_s"])
        target_rows.append([
            target_tv,
            item["tv"],
            item["name"],
            item["time_s"],
            bnum / 1000.0,
            btheory / 1000.0,
            rms_profile(item["rows"], "pore", lambda z, t=item["time_s"]: analytical(z, t)),
            pp.max_value(item["rows"], "speed"),
        ])

    degree_rows = []
    for item in series:
        prof = pp.layer_average(item["rows"], "pore")
        sph_integral = profile_integral(prof)
        theory_integral = sum(analytical(z, item["time_s"]) for z, _ in initial_profile) * pp.DP
        u_sph = 1.0 - sph_integral / initial_integral
        u_theory = 1.0 - theory_integral / initial_integral
        degree_rows.append([
            item["time_s"],
            item["tv"],
            u_sph,
            u_theory,
            sph_integral,
            theory_integral,
            pp.max_value(item["rows"], "speed"),
        ])

    ax_degree.plot([row[1] for row in degree_rows], [row[2] for row in degree_rows], "o-", markersize=3, label="SPH")
    ax_degree.plot([row[1] for row in degree_rows], [row[3] for row in degree_rows], "k--", linewidth=1.5, label="analytical")

    ax_profile.set_xlabel("Pore pressure [kPa]")
    ax_profile.set_ylabel("z/H")
    ax_profile.set_title("Pore pressure profiles")
    ax_profile.grid(True, alpha=0.25)
    ax_profile.legend(fontsize=8)

    ax_degree.set_xlabel("Tv")
    ax_degree.set_ylabel("Degree of consolidation U")
    ax_degree.set_title("Degree of consolidation")
    ax_degree.set_xlim(left=0)
    ax_degree.set_ylim(-0.05, 1.05)
    ax_degree.grid(True, alpha=0.25)
    ax_degree.legend()

    fig.suptitle(f"{args.case}: gravity-off restart from Stage 1 Part_0060")
    figpath = args.figdir / "scenario1_pore_pressure_and_degree.png"
    fig.savefig(figpath, dpi=220)

    target_csv = args.figdir / "scenario1_target_summary.csv"
    with target_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "target_Tv",
            "actual_Tv",
            "part",
            "time_s",
            "bottom_pore_sph_kPa",
            "bottom_pore_theory_kPa",
            "rms_pore_pa",
            "max_speed_m_per_s",
        ])
        writer.writerows(target_rows)

    degree_csv = args.figdir / "scenario1_degree.csv"
    with degree_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "time_s",
            "Tv",
            "U_sph",
            "U_theory",
            "integrated_pore_sph_Pa_m",
            "integrated_pore_theory_Pa_m",
            "max_speed_m_per_s",
        ])
        writer.writerows(degree_rows)

    profile_csv = args.figdir / "scenario1_profiles_by_tv.csv"
    write_profile_csv(profile_csv, selected, analytical)

    print(f"Saved Scenario 1 figure: {figpath}")
    print(f"Saved target summary: {target_csv}")
    print(f"Saved degree summary: {degree_csv}")
    print(f"Saved profile table: {profile_csv}")
    print(f"cv={pp.CV_TERZAGHI:.12g} m^2/s, tout={args.tout:.12g} s, DeltaTv={pp.CV_TERZAGHI * args.tout / (pp.H * pp.H):.12g}")
    if target_rows:
        print("Scenario 1 target Tv comparisons:")
        for row in target_rows:
            print(
                f"  target Tv={row[0]:.3g}, actual Tv={row[1]:.6g}, {row[2]}, "
                f"bottom SPH={row[4]:.6g} kPa, theory={row[5]:.6g} kPa, "
                f"RMS={row[6]:.6g} Pa, max speed={row[7]:.6g} m/s"
            )
    if degree_rows:
        last = degree_rows[-1]
        print(f"Scenario 1 final: t={last[0]:.6g}s, Tv={last[1]:.6g}, U_sph={last[2]:.6g}, U_theory={last[3]:.6g}")


if __name__ == "__main__":
    main()
