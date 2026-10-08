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


DEFAULT_TARGET_TV = [0.0, 0.005, 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0, 1.5, 2.0]


def part_index(path):
    return int(path.stem.rsplit("_", 1)[1])


def load_series(particles, tout, tmax, tv_offset=0.0):
    series = []
    time_offset = tv_offset * pp.H * pp.H / pp.CV_TERZAGHI
    for path in sorted(particles.glob("PartFluid_*.vtk")):
        idx = part_index(path)
        time_rel_s = min(tmax, idx * tout)
        time_s = time_offset + time_rel_s
        series.append({
            "name": path.name,
            "index": idx,
            "time_rel_s": time_rel_s,
            "time_s": time_s,
            "tv": tv_offset + pp.CV_TERZAGHI * time_rel_s / (pp.H * pp.H),
            "rows": pp.read_part_vtk(path),
        })
    if not series:
        raise RuntimeError(f"No PartFluid VTK files found in {particles}")
    return series


def write_profile_csv(path, selected):
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "target_Tv",
            "actual_Tv",
            "part",
            "z_m",
            "z_over_H",
            "excess_sph_kPa",
            "excess_theory_kPa",
            "hydrostatic_theory_kPa",
            "total_sph_kPa",
            "total_theory_kPa",
        ])
        for target_tv, item in selected:
            prof_e = dict(pp.layer_average(item["rows"], "excess"))
            prof_p = dict(pp.layer_average(item["rows"], "pore"))
            for z in sorted(prof_e):
                t_rel = item["time_s"]
                excess_theory = pp.terzaghi_excess(z, t_rel)
                hydrostatic_theory = pp.hydrostatic(z)
                total_theory = hydrostatic_theory + excess_theory
                writer.writerow([
                    target_tv,
                    item["tv"],
                    item["name"],
                    z,
                    z / pp.H,
                    prof_e[z] / 1000.0,
                    excess_theory / 1000.0,
                    hydrostatic_theory / 1000.0,
                    prof_p.get(z, float("nan")) / 1000.0,
                    total_theory / 1000.0,
                ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--particles", required=True, type=Path)
    parser.add_argument("--figdir", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--xml", type=Path, help="Scenario XML used to read TimeOut and TimeMax when not provided")
    parser.add_argument("--tout", type=float)
    parser.add_argument("--tmax", type=float)
    parser.add_argument("--tv-offset", type=float, default=0.0)
    parser.add_argument("--target-tv", nargs="*", type=float)
    parser.add_argument("--restart-label", default="restart from Stage 1 Part_0060")
    args = parser.parse_args()

    if args.xml:
        if args.tout is None:
            args.tout = pp.xml_parameter(args.xml, "TimeOut", 0.0182185714)
        if args.tmax is None:
            args.tmax = pp.xml_parameter(args.xml, "TimeMax", 3.85)
    if args.tout is None or args.tmax is None:
        raise RuntimeError("Provide --xml or both --tout and --tmax.")

    target_tvs = args.target_tv if args.target_tv else DEFAULT_TARGET_TV
    series = load_series(args.particles, args.tout, args.tmax, args.tv_offset)
    args.figdir.mkdir(parents=True, exist_ok=True)

    selected = []
    used = set()
    for target_tv in target_tvs:
        item = min(series, key=lambda row: abs(row["tv"] - target_tv))
        if item["index"] not in used:
            selected.append((target_tv, item))
            used.add(item["index"])

    zgrid = [i / 200.0 for i in range(201)]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), constrained_layout=True)
    ax_excess, ax_total, ax_bottom = axes

    ax_excess.plot(
        [pp.undrained_excess(z) / 1000.0 for z in zgrid],
        [z / pp.H for z in zgrid],
        "k--",
        linewidth=1.5,
        label="theory initial excess",
    )
    ax_total.plot(
        [pp.hydrostatic(z) / 1000.0 for z in zgrid],
        [z / pp.H for z in zgrid],
        "k:",
        linewidth=1.7,
        label="theory hydrostatic",
    )
    ax_total.plot(
        [pp.undrained_total(z) / 1000.0 for z in zgrid],
        [z / pp.H for z in zgrid],
        "k--",
        linewidth=1.5,
        label="theory initial total",
    )

    colors = plt.cm.viridis([i / max(1, len(selected) - 1) for i in range(len(selected))])
    target_rows = []
    for color, (target_tv, item) in zip(colors, selected):
        label = f"Tv={item['tv']:.3f}"
        prof_e = pp.layer_average(item["rows"], "excess")
        prof_p = pp.layer_average(item["rows"], "pore")
        ax_excess.plot([v / 1000.0 for _, v in prof_e], [z / pp.H for z, _ in prof_e], color=color, linewidth=1.35, label=label)
        ax_total.plot([v / 1000.0 for _, v in prof_p], [z / pp.H for z, _ in prof_p], color=color, linewidth=1.35, label=label)
        ax_excess.plot(
            [pp.terzaghi_excess(z, item["time_s"]) / 1000.0 for z in zgrid],
            [z / pp.H for z in zgrid],
            "--",
            color=color,
            linewidth=0.9,
            alpha=0.65,
        )
        ax_total.plot(
            [(pp.hydrostatic(z) + pp.terzaghi_excess(z, item["time_s"])) / 1000.0 for z in zgrid],
            [z / pp.H for z in zgrid],
            "--",
            color=color,
            linewidth=0.9,
            alpha=0.65,
        )
        bnum, bz = pp.bottom_average(item["rows"], "excess")
        btheory = pp.terzaghi_excess(bz, item["time_s"])
        target_rows.append([
            target_tv,
            item["tv"],
            item["name"],
            item["time_s"],
            bnum / 1000.0,
            btheory / 1000.0,
            pp.rms_error(item["rows"], "excess", lambda z, t=item["time_s"]: pp.terzaghi_excess(z, t)),
            pp.max_value(item["rows"], "speed"),
        ])

    bottom_rows = []
    for item in series:
        bnum, bz = pp.bottom_average(item["rows"], "excess")
        btheory = pp.terzaghi_excess(bz, item["time_s"])
        bottom_rows.append([
            item["time_s"],
            item["tv"],
            bnum / 1000.0,
            btheory / 1000.0,
            bz,
        ])

    min_tv = min(row[1] for row in bottom_rows)
    max_tv = max(row[1] for row in bottom_rows)
    tv_grid = [min_tv + i / 250.0 * (max_tv - min_tv) for i in range(251)]
    z_bottom = pp.DP / 2.0
    ax_bottom.plot(
        tv_grid,
        [pp.terzaghi_excess(z_bottom, tv / pp.CV_TERZAGHI) / 1000.0 for tv in tv_grid],
        "k--",
        label="theory bottom excess",
    )
    ax_bottom.plot([row[1] for row in bottom_rows], [row[2] for row in bottom_rows], "o-", markersize=2.2, label="SPH bottom excess")

    ax_excess.set_xlabel("Excess pore pressure [kPa]")
    ax_excess.set_ylabel("z/H")
    ax_excess.set_title("Excess pore pressure")
    ax_excess.grid(True, alpha=0.25)
    ax_excess.legend(fontsize=8)

    ax_total.set_xlabel("Total pore pressure [kPa]")
    ax_total.set_ylabel("z/H")
    ax_total.set_title("Total pore pressure")
    ax_total.grid(True, alpha=0.25)
    ax_total.legend(fontsize=8)

    ax_bottom.set_xlabel("Tv")
    ax_bottom.set_ylabel("Bottom excess pore pressure [kPa]")
    ax_bottom.set_title("Bottom dissipation")
    ax_bottom.grid(True, alpha=0.25)
    ax_bottom.legend(fontsize=8)

    fig.suptitle(f"{args.case}: {args.restart_label}")
    figpath = args.figdir / "scenario2_pore_pressure_profiles.png"
    fig.savefig(figpath, dpi=220)

    bottom_csv = args.figdir / "scenario2_bottom_dissipation.csv"
    with bottom_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "Tv", "bottom_excess_sph_kPa", "bottom_excess_theory_kPa", "bottom_z_m"])
        writer.writerows(bottom_rows)

    target_csv = args.figdir / "scenario2_target_summary.csv"
    with target_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "target_Tv",
            "actual_Tv",
            "part",
            "time_s",
            "bottom_excess_sph_kPa",
            "bottom_excess_theory_kPa",
            "rms_excess_pa",
            "max_speed_m_per_s",
        ])
        writer.writerows(target_rows)

    profile_csv = args.figdir / "scenario2_profiles_by_tv.csv"
    write_profile_csv(profile_csv, selected)

    print(f"Saved figure: {figpath}")
    print(f"Saved bottom dissipation: {bottom_csv}")
    print(f"Saved target summary: {target_csv}")
    print(f"Saved profile table: {profile_csv}")
    print(f"cv={pp.CV_TERZAGHI:.12g} m^2/s, tout={args.tout:.12g} s, DeltaTv={pp.CV_TERZAGHI * args.tout / (pp.H * pp.H):.12g}")
    if target_rows:
        print("Target Tv comparisons:")
        for row in target_rows:
            print(
                f"  target Tv={row[0]:.3g}, actual Tv={row[1]:.6g}, {row[2]}, "
                f"bottom SPH={row[4]:.6g} kPa, theory={row[5]:.6g} kPa, "
                f"RMS={row[6]:.6g} Pa, max speed={row[7]:.6g} m/s"
            )


if __name__ == "__main__":
    main()
