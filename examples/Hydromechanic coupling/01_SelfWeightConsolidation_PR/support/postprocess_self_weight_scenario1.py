from pathlib import Path
import csv
import math

import matplotlib.pyplot as plt

from postprocess_self_weight_consolidation import (
    ROOT,
    FIGDIR,
    H,
    DP,
    CV_TERZAGHI,
    read_part_vtk,
    part_index,
    layer_average,
    bottom_average,
    hydrostatic,
    max_value,
)


SCENARIO1 = ROOT / "CaseSelfWeightConsolidation_Scenario1_out" / "particles"
SCENARIO1_TOUT = 0.02
SCENARIO1_INITIAL_INDEX = 0
SCENARIO1_INITIAL_TIME = 0.0
SCENARIO1_TIME_MAX = 0.40
SCENARIO1_TARGET_TV = [0.005, 0.05, 0.1]


def load_series(folder):
    data = []
    for path in sorted(folder.glob("PartFluid_*.vtk")):
        idx = part_index(path)
        time = min(SCENARIO1_TIME_MAX, SCENARIO1_INITIAL_TIME + (idx - SCENARIO1_INITIAL_INDEX) * SCENARIO1_TOUT)
        data.append({"name": path.name, "index": idx, "time": time, "rows": read_part_vtk(path)})
    if not data:
        raise RuntimeError(f"No PartFluid VTK files found in {folder}")
    return data


def profile_integral(profile):
    return sum(value for _, value in profile) * DP


def build_cosine_solution(initial_profile, nterms=220):
    coeffs = []
    for n in range(nterms):
        lam = (2 * n + 1) * math.pi / (2.0 * H)
        integral = sum(value * math.cos(lam * z) for z, value in initial_profile) * DP
        coeffs.append((lam, 2.0 * integral / H))

    def solution(z, t_rel):
        t = max(0.0, t_rel)
        return sum(an * math.cos(lam * z) * math.exp(-lam * lam * CV_TERZAGHI * t) for lam, an in coeffs)

    return solution


def rms_profile(rows, value_key, theory):
    values = [(row[value_key] - theory(row["z"])) for row in rows if value_key in row]
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else float("nan")


def nearest_targets(series):
    selected = []
    used = set()
    for target_tv in SCENARIO1_TARGET_TV:
        data = min(
            series,
            key=lambda item: abs(CV_TERZAGHI * max(0.0, item["time"] - SCENARIO1_INITIAL_TIME) / (H * H) - target_tv),
        )
        if data["index"] not in used:
            selected.append((target_tv, data))
            used.add(data["index"])
    return selected


def main():
    FIGDIR.mkdir(exist_ok=True)
    series = load_series(SCENARIO1)
    initial = next((item for item in series if item["index"] == SCENARIO1_INITIAL_INDEX), series[0])
    t0 = initial["time"]

    initial_total_profile = layer_average(initial["rows"], "pore")
    initial_excess_profile = layer_average(initial["rows"], "excess")
    analytic_total = build_cosine_solution(initial_total_profile)
    initial_total_integral = profile_integral(initial_total_profile)

    zgrid = [i / 200.0 for i in range(201)]
    selected = nearest_targets(series)

    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.2), constrained_layout=True)
    ax_total, ax_excess = axes
    colors = plt.cm.viridis([i / max(1, len(selected) - 1) for i in range(len(selected))])

    target_rows = []
    for color, (target_tv, data) in zip(colors, selected):
        t_rel = max(0.0, data["time"] - t0)
        tv = CV_TERZAGHI * t_rel / (H * H)
        label = f"Tv={tv:.3f}"
        prof_total = layer_average(data["rows"], "pore")
        prof_excess = layer_average(data["rows"], "excess")
        ax_total.plot([v / 1000.0 for _, v in prof_total], [z / H for z, _ in prof_total], color=color, linewidth=1.35, label=label)
        ax_total.plot(
            [analytic_total(z, t_rel) / 1000.0 for z in zgrid],
            [z / H for z in zgrid],
            "--",
            color=color,
            linewidth=0.95,
            alpha=0.68,
        )
        ax_excess.plot([v / 1000.0 for _, v in prof_excess], [z / H for z, _ in prof_excess], color=color, linewidth=1.35, label=label)
        ax_excess.plot(
            [analytic_total(z, t_rel) / 1000.0 for z in zgrid],
            [z / H for z in zgrid],
            "--",
            color=color,
            linewidth=0.95,
            alpha=0.68,
        )
        bnum, bz = bottom_average(data["rows"], "pore")
        btheory = analytic_total(bz, t_rel)
        target_rows.append((
            target_tv,
            data["name"],
            data["time"],
            t_rel,
            tv,
            bnum / 1000.0,
            btheory / 1000.0,
            rms_profile(data["rows"], "pore", lambda z, t_rel=t_rel: analytic_total(z, t_rel)),
            max_value(data["rows"], "speed"),
        ))

    for ax in axes:
        ax.set_ylabel("z/H")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    ax_total.set_xlabel("Total pore pressure [kPa]")
    ax_total.set_title("Scenario 1 total pore pressure")
    ax_excess.set_xlabel("Excess pore pressure [kPa]")
    ax_excess.set_title("Scenario 1 excess pore pressure")
    fig.suptitle("Self-weight consolidation Scenario 1: gravity-off analytical initialization")
    profile_path = FIGDIR / "self_weight_scenario1_profiles.png"
    fig.savefig(profile_path, dpi=220)

    consolidation_rows = []
    for data in series:
        t_rel = max(0.0, data["time"] - t0)
        tv = CV_TERZAGHI * t_rel / (H * H)
        prof_total = layer_average(data["rows"], "pore")
        sph_integral = profile_integral(prof_total)
        theory_profile = [(z, analytic_total(z, t_rel)) for z, _ in initial_total_profile]
        theory_integral = profile_integral(theory_profile)
        u_sph = 1.0 - sph_integral / initial_total_integral
        u_theory = 1.0 - theory_integral / initial_total_integral
        consolidation_rows.append((
            data["time"],
            t_rel,
            tv,
            u_sph,
            u_theory,
            sph_integral,
            theory_integral,
            max_value(data["rows"], "speed"),
        ))

    fig_u, ax_u = plt.subplots(figsize=(7.0, 5.0), constrained_layout=True)
    ax_u.plot([row[2] for row in consolidation_rows], [row[3] for row in consolidation_rows], "o-", markersize=3, label="SPH")
    ax_u.plot([row[2] for row in consolidation_rows], [row[4] for row in consolidation_rows], "k--", linewidth=1.5, label="analytical")
    ax_u.set_xlabel("Tv")
    ax_u.set_ylabel("Degree of consolidation U")
    ax_u.set_title("Scenario 1 degree of consolidation")
    ax_u.set_xlim(left=0)
    ax_u.set_ylim(-0.05, 1.05)
    ax_u.grid(True, alpha=0.25)
    ax_u.legend()
    degree_path = FIGDIR / "self_weight_scenario1_degree.png"
    fig_u.savefig(degree_path, dpi=220)

    target_summary = FIGDIR / "self_weight_scenario1_targets.csv"
    with target_summary.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "target_Tv",
            "part",
            "time_s",
            "t_rel_s",
            "actual_Tv",
            "bottom_total_sph_kPa",
            "bottom_total_theory_kPa",
            "rms_total_pa",
            "max_speed",
        ])
        writer.writerows(target_rows)

    degree_summary = FIGDIR / "self_weight_scenario1_degree.csv"
    with degree_summary.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "time_s",
            "t_rel_s",
            "Tv",
            "U_sph",
            "U_theory",
            "integrated_total_sph_Pa_m",
            "integrated_total_theory_Pa_m",
            "max_speed",
        ])
        writer.writerows(consolidation_rows)

    print(f"Saved Scenario 1 pressure profiles: {profile_path}")
    print(f"Saved Scenario 1 degree plot: {degree_path}")
    print(f"Saved Scenario 1 target summary: {target_summary}")
    print(f"Saved Scenario 1 degree summary: {degree_summary}")
    print(f"cv_terzaghi={CV_TERZAGHI:.6g} m^2/s, initial={initial['name']} t={t0:.6g}s")
    if target_rows:
        print("Scenario 1 target Tv comparisons:")
        for row in target_rows:
            print(
                f"  target Tv={row[0]:.3g}, actual Tv={row[4]:.6g}, {row[1]}, "
                f"bottom SPH={row[5]:.6g} kPa, theory={row[6]:.6g} kPa, "
                f"RMS={row[7]:.6g} Pa, max speed={row[8]:.6g} m/s"
            )
    if consolidation_rows:
        last = consolidation_rows[-1]
        print(
            "Scenario 1 final consolidation: "
            f"t={last[0]:.6g}s, Tv={last[2]:.6g}, U_sph={last[3]:.6g}, U_theory={last[4]:.6g}"
        )


if __name__ == "__main__":
    main()
