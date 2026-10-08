from pathlib import Path
import argparse
import csv
from collections import defaultdict

import matplotlib.pyplot as plt


def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def as_float(row, key):
    value = row.get(key, "")
    return float(value) if value != "" else float("nan")


def read_profiles(path):
    profiles = defaultdict(list)
    for row in read_csv(path):
        target = float(row["target_Tv"])
        profiles[target].append(row)
    return profiles


def nearest_profile(profiles, target):
    key = min(profiles, key=lambda tv: abs(tv - target))
    return key, profiles[key]


def plot_bottom(baseline_rows, candidate_rows, outdir, baseline_label, candidate_label):
    fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
    if baseline_rows:
        ax.plot(
            [as_float(r, "Tv") for r in baseline_rows],
            [as_float(r, "bottom_excess_theory_kPa") for r in baseline_rows],
            "k--",
            linewidth=1.2,
            label="theory",
        )
        ax.plot(
            [as_float(r, "Tv") for r in baseline_rows],
            [as_float(r, "bottom_excess_sph_kPa") for r in baseline_rows],
            color="#1f77b4",
            linewidth=1.5,
            label=baseline_label,
        )
    if candidate_rows:
        ax.plot(
            [as_float(r, "Tv") for r in candidate_rows],
            [as_float(r, "bottom_excess_sph_kPa") for r in candidate_rows],
            color="#d62728",
            linewidth=1.5,
            label=candidate_label,
        )
    ax.set_xlabel("Tv")
    ax.set_ylabel("Bottom excess pore pressure [kPa]")
    ax.set_title("Scenario 2 bottom dissipation")
    ax.grid(True, alpha=0.25)
    ax.legend()
    path = outdir / "scenario2_bottom_dissipation_boundary_mode_compare.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_target_errors(baseline_rows, candidate_rows, outdir, baseline_label, candidate_label):
    fig, (ax_rms, ax_bottom) = plt.subplots(1, 2, figsize=(10, 4.5), constrained_layout=True)
    for rows, label, color in [
        (baseline_rows, baseline_label, "#1f77b4"),
        (candidate_rows, candidate_label, "#d62728"),
    ]:
        tv = [as_float(r, "actual_Tv") for r in rows]
        rms = [as_float(r, "rms_excess_pa") for r in rows]
        bottom_err = [
            as_float(r, "bottom_excess_sph_kPa") - as_float(r, "bottom_excess_theory_kPa")
            for r in rows
        ]
        ax_rms.plot(tv, rms, "o-", markersize=3, linewidth=1.4, color=color, label=label)
        ax_bottom.plot(tv, bottom_err, "o-", markersize=3, linewidth=1.4, color=color, label=label)
    ax_rms.set_xlabel("Tv")
    ax_rms.set_ylabel("Profile RMS excess-pressure error [Pa]")
    ax_rms.set_title("Profile RMS error")
    ax_rms.grid(True, alpha=0.25)
    ax_rms.legend()
    ax_bottom.axhline(0, color="k", linewidth=0.8)
    ax_bottom.set_xlabel("Tv")
    ax_bottom.set_ylabel("Bottom SPH - theory [kPa]")
    ax_bottom.set_title("Bottom pressure error")
    ax_bottom.grid(True, alpha=0.25)
    ax_bottom.legend()
    path = outdir / "scenario2_target_error_boundary_mode_compare.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_profiles(baseline_profiles, candidate_profiles, outdir, baseline_label, candidate_label):
    targets = [0.0, 0.1, 0.4, 1.0]
    fig, axes = plt.subplots(1, len(targets), figsize=(13, 4.8), sharey=True, constrained_layout=True)
    for ax, target in zip(axes, targets):
        base_tv, base_rows = nearest_profile(baseline_profiles, target)
        cand_tv, cand_rows = nearest_profile(candidate_profiles, target)
        ax.plot(
            [as_float(r, "excess_theory_kPa") for r in base_rows],
            [as_float(r, "z_over_H") for r in base_rows],
            "k--",
            linewidth=1.0,
            label="theory",
        )
        ax.plot(
            [as_float(r, "excess_sph_kPa") for r in base_rows],
            [as_float(r, "z_over_H") for r in base_rows],
            color="#1f77b4",
            linewidth=1.4,
            label=f"{baseline_label} Tv={base_tv:.3g}",
        )
        ax.plot(
            [as_float(r, "excess_sph_kPa") for r in cand_rows],
            [as_float(r, "z_over_H") for r in cand_rows],
            color="#d62728",
            linewidth=1.4,
            label=f"{candidate_label} Tv={cand_tv:.3g}",
        )
        ax.set_title(f"target Tv={target:g}")
        ax.set_xlabel("Excess pore pressure [kPa]")
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("z/H")
    axes[-1].legend(fontsize=7, loc="lower right")
    fig.suptitle("Scenario 2 excess-pressure profiles")
    path = outdir / "scenario2_profiles_boundary_mode_compare.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def write_merged_summary(baseline_rows, candidate_rows, outdir, baseline_label, candidate_label):
    rows_by_target = {}
    for row in baseline_rows:
        rows_by_target.setdefault(row["target_Tv"], {})["baseline"] = row
    for row in candidate_rows:
        rows_by_target.setdefault(row["target_Tv"], {})["candidate"] = row
    path = outdir / "scenario2_boundary_mode_target_summary_compare.csv"
    fields = [
        "target_Tv",
        "baseline_actual_Tv",
        "candidate_actual_Tv",
        "baseline_bottom_excess_sph_kPa",
        "candidate_bottom_excess_sph_kPa",
        "theory_bottom_excess_kPa",
        "baseline_bottom_error_kPa",
        "candidate_bottom_error_kPa",
        "baseline_rms_excess_pa",
        "candidate_rms_excess_pa",
        "baseline_label",
        "candidate_label",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for target in sorted(rows_by_target, key=float):
            base = rows_by_target[target].get("baseline", {})
            cand = rows_by_target[target].get("candidate", {})
            theory = base.get("bottom_excess_theory_kPa") or cand.get("bottom_excess_theory_kPa") or ""
            writer.writerow({
                "target_Tv": target,
                "baseline_actual_Tv": base.get("actual_Tv", ""),
                "candidate_actual_Tv": cand.get("actual_Tv", ""),
                "baseline_bottom_excess_sph_kPa": base.get("bottom_excess_sph_kPa", ""),
                "candidate_bottom_excess_sph_kPa": cand.get("bottom_excess_sph_kPa", ""),
                "theory_bottom_excess_kPa": theory,
                "baseline_bottom_error_kPa": (
                    as_float(base, "bottom_excess_sph_kPa") - as_float(base, "bottom_excess_theory_kPa")
                    if base else ""
                ),
                "candidate_bottom_error_kPa": (
                    as_float(cand, "bottom_excess_sph_kPa") - as_float(cand, "bottom_excess_theory_kPa")
                    if cand else ""
                ),
                "baseline_rms_excess_pa": base.get("rms_excess_pa", ""),
                "candidate_rms_excess_pa": cand.get("rms_excess_pa", ""),
                "baseline_label": baseline_label,
                "candidate_label": candidate_label,
            })
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-figdir", required=True, type=Path)
    parser.add_argument("--candidate-figdir", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--baseline-label", default="SlipMode=1")
    parser.add_argument("--candidate-label", default="Free slip, MDBCCorrector=0")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    baseline_bottom = read_csv(args.baseline_figdir / "scenario2_bottom_dissipation.csv")
    candidate_bottom = read_csv(args.candidate_figdir / "scenario2_bottom_dissipation.csv")
    baseline_target = read_csv(args.baseline_figdir / "scenario2_target_summary.csv")
    candidate_target = read_csv(args.candidate_figdir / "scenario2_target_summary.csv")
    baseline_profiles = read_profiles(args.baseline_figdir / "scenario2_profiles_by_tv.csv")
    candidate_profiles = read_profiles(args.candidate_figdir / "scenario2_profiles_by_tv.csv")

    written = [
        plot_bottom(baseline_bottom, candidate_bottom, args.outdir, args.baseline_label, args.candidate_label),
        plot_target_errors(baseline_target, candidate_target, args.outdir, args.baseline_label, args.candidate_label),
        plot_profiles(baseline_profiles, candidate_profiles, args.outdir, args.baseline_label, args.candidate_label),
        write_merged_summary(baseline_target, candidate_target, args.outdir, args.baseline_label, args.candidate_label),
    ]
    for path in written:
        print(f"Saved {path}")


if __name__ == "__main__":
    main()
