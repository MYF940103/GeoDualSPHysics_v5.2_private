from pathlib import Path
import argparse
import csv
import math

import matplotlib.pyplot as plt


def read_csv(path):
    rows = []
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            out = {}
            for k, v in row.items():
                if v is None:
                    out[k] = v
                    continue
                try:
                    out[k] = float(v)
                except ValueError:
                    out[k] = v
            rows.append(out)
    return rows


def nearest(rows, key, value):
    return min(rows, key=lambda row: abs(float(row[key]) - value))


def finite(values):
    return [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]


def write_csv(path, fieldnames, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_comparison(outdir, case_name, cpu_summary, gpu_bottom, paired, target_pairs, current_label):
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8), constrained_layout=True)
    ax_curve, ax_diff = axes

    cpu_sorted = sorted(cpu_summary, key=lambda row: float(row["Tv"]))
    gpu_sorted = sorted(gpu_bottom, key=lambda row: float(row["Tv"]))
    ax_curve.plot(
        [row["Tv"] for row in cpu_sorted],
        [row["bottom_excess_sph_kPa"] for row in cpu_sorted],
        color="#2c5aa0",
        linewidth=1.8,
        label="old CPU baseline",
    )
    ax_curve.plot(
        [row["Tv"] for row in gpu_sorted],
        [row["bottom_excess_sph_kPa"] for row in gpu_sorted],
        color="#d55e00",
        linewidth=1.6,
        linestyle="-",
        label=current_label,
    )
    ax_curve.plot(
        [row["Tv"] for row in gpu_sorted],
        [row["bottom_excess_theory_kPa"] for row in gpu_sorted],
        color="#333333",
        linewidth=1.2,
        linestyle="--",
        label="Terzaghi theory",
    )
    ax_curve.set_xlabel("Time factor Tv")
    ax_curve.set_ylabel("Bottom excess pore pressure [kPa]")
    ax_curve.set_title("Bottom dissipation")
    ax_curve.grid(True, alpha=0.25)
    ax_curve.legend(fontsize=8)

    if target_pairs:
        xs = [row["target_Tv"] for row in target_pairs]
        ys = [row["diff_bottom_excess_kPa"] for row in target_pairs]
        ax_diff.axhline(0, color="#333333", linewidth=1.0)
        ax_diff.plot(xs, ys, "o-", color="#7b3294", linewidth=1.4, markersize=4)
        ax_diff.set_xlabel("Target Tv")
        ax_diff.set_ylabel(f"{current_label} - old CPU [kPa]")
        ax_diff.set_title("Target bottom-pressure difference")
        ax_diff.grid(True, alpha=0.25)
    else:
        ax_diff.text(0.5, 0.5, "No target pairs", ha="center", va="center")
        ax_diff.set_axis_off()

    fig.suptitle(case_name)
    figpath = Path(outdir) / "mode3_current_vs_old_cpu_bottom_compare.png"
    fig.savefig(figpath, dpi=220)
    plt.close(fig)
    return figpath

def load_bottom_table(figdir):
    figdir = Path(figdir)
    old = figdir / "self_weight_consolidation_summary.csv"
    current = figdir / "scenario2_bottom_dissipation.csv"
    if old.exists():
        rows = read_csv(old)
        for row in rows:
            if "time_s" not in row and "time" in row:
                row["time_s"] = row["time"]
        return rows
    if current.exists():
        return read_csv(current)
    raise RuntimeError(f"No supported bottom-dissipation CSV found in {figdir}")


def load_target_table(figdir):
    figdir = Path(figdir)
    old = figdir / "self_weight_consolidation_targets.csv"
    current = figdir / "scenario2_target_summary.csv"
    if old.exists():
        rows = read_csv(old)
        for row in rows:
            if "time_s" not in row and "time" in row:
                row["time_s"] = row["time"]
            if "max_speed_m_per_s" not in row and "max_speed" in row:
                row["max_speed_m_per_s"] = row["max_speed"]
        return rows
    if current.exists():
        return read_csv(current)
    raise RuntimeError(f"No supported target summary CSV found in {figdir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu-figdir", required=True, type=Path)
    parser.add_argument("--gpu-figdir", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--note", required=True, type=Path)
    parser.add_argument("--case", default="CaseSWScenario2_Mode3_GPU")
    parser.add_argument("--current-label", default="current run")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    cpu_summary = load_bottom_table(args.cpu_figdir)
    cpu_targets = load_target_table(args.cpu_figdir)
    gpu_bottom = load_bottom_table(args.gpu_figdir)
    gpu_targets = load_target_table(args.gpu_figdir)

    if not cpu_summary or not gpu_bottom:
        raise RuntimeError("Missing CPU or GPU bottom-dissipation rows.")

    paired = []
    for grow in gpu_bottom:
        tv = float(grow["Tv"])
        crow = nearest(cpu_summary, "Tv", tv)
        paired.append({
            "gpu_Tv": tv,
            "cpu_Tv": crow["Tv"],
            "gpu_time_s": grow["time_s"],
            "cpu_time_s": crow.get("time_s", crow.get("time", "")),
            "gpu_bottom_excess_kPa": grow["bottom_excess_sph_kPa"],
            "cpu_bottom_excess_kPa": crow["bottom_excess_sph_kPa"],
            "diff_bottom_excess_kPa": grow["bottom_excess_sph_kPa"] - crow["bottom_excess_sph_kPa"],
            "gpu_bottom_theory_kPa": grow["bottom_excess_theory_kPa"],
            "cpu_bottom_theory_kPa": crow["bottom_excess_theory_kPa"],
            "gpu_bottom_z_m": grow.get("bottom_z_m", ""),
            "cpu_bottom_z_m": crow.get("bottom_z_m", ""),
        })

    target_pairs = []
    for grow in gpu_targets:
        target = float(grow["target_Tv"])
        if cpu_targets:
            crow = nearest(cpu_targets, "target_Tv", target)
            # Avoid comparing the GPU initial target against the old CPU table's
            # first non-zero target. Use the bottom table for unmatched targets.
            if abs(float(crow["target_Tv"]) - target) > 1.0e-8:
                crow = nearest(cpu_summary, "Tv", float(grow["actual_Tv"]))
                crow = {
                    "target_Tv": target,
                    "actual_Tv": crow["Tv"],
                    "part": "",
                    "bottom_excess_sph_kPa": crow["bottom_excess_sph_kPa"],
                    "rms_excess_pa": float("nan"),
                    "max_speed_m_per_s": float("nan"),
                }
        else:
            continue
        cpu_speed = crow.get("max_speed_m_per_s", crow.get("max_speed", ""))
        gpu_speed = grow.get("max_speed_m_per_s", grow.get("max_speed", ""))
        target_pairs.append({
            "target_Tv": target,
            "gpu_actual_Tv": grow["actual_Tv"],
            "cpu_actual_Tv": crow["actual_Tv"],
            "gpu_part": grow["part"],
            "cpu_part": crow["part"],
            "gpu_bottom_excess_kPa": grow["bottom_excess_sph_kPa"],
            "cpu_bottom_excess_kPa": crow["bottom_excess_sph_kPa"],
            "diff_bottom_excess_kPa": grow["bottom_excess_sph_kPa"] - crow["bottom_excess_sph_kPa"],
            "gpu_rms_excess_pa": grow["rms_excess_pa"],
            "cpu_rms_excess_pa": crow["rms_excess_pa"],
            "diff_rms_excess_pa": grow["rms_excess_pa"] - crow["rms_excess_pa"],
            "gpu_max_speed_m_per_s": gpu_speed,
            "cpu_max_speed_m_per_s": cpu_speed,
            "diff_max_speed_m_per_s": (gpu_speed - cpu_speed) if isinstance(gpu_speed, float) and isinstance(cpu_speed, float) else "",
        })

    write_csv(args.outdir / "mode3_gpu_vs_cpu_bottom_dissipation_compare.csv", list(paired[0].keys()), paired)
    write_csv(args.outdir / "mode3_gpu_vs_cpu_target_compare.csv", list(target_pairs[0].keys()), target_pairs)
    plot_path = plot_comparison(args.outdir, args.case, cpu_summary, gpu_bottom, paired, target_pairs, args.current_label)

    diffs = finite([row["diff_bottom_excess_kPa"] for row in paired])
    target_diffs = finite([row["diff_bottom_excess_kPa"] for row in target_pairs])
    rms_diffs = finite([row["diff_rms_excess_pa"] for row in target_pairs])
    speed_diffs = finite([row["diff_max_speed_m_per_s"] for row in target_pairs])

    max_abs_bottom = max(abs(v) for v in diffs)
    rms_bottom = math.sqrt(sum(v * v for v in diffs) / len(diffs))
    max_abs_target = max(abs(v) for v in target_diffs)
    max_abs_rms_pa = max(abs(v) for v in rms_diffs)
    max_abs_speed = max(abs(v) for v in speed_diffs) if speed_diffs else float("nan")

    # Tolerances are intentionally engineering-level, not bitwise. The goal is
    # to decide whether the old CPU reference and current GPU path follow the
    # same physical/numerical trajectory.
    bottom_ok = max_abs_bottom <= 0.10 and rms_bottom <= 0.03
    targets_ok = max_abs_target <= 0.10 and max_abs_rms_pa <= 150.0
    status = "MATCH" if bottom_ok and targets_ok else "DIFFERENT"

    summary_rows = [{
        "status": status,
        "bottom_max_abs_diff_kPa": max_abs_bottom,
        "bottom_rms_diff_kPa": rms_bottom,
        "target_max_abs_bottom_diff_kPa": max_abs_target,
        "target_max_abs_rms_diff_pa": max_abs_rms_pa,
        "target_max_abs_speed_diff_m_per_s": max_abs_speed,
        "gpu_rows": len(gpu_bottom),
        "cpu_rows": len(cpu_summary),
    }]
    write_csv(args.outdir / "mode3_gpu_vs_cpu_summary.csv", list(summary_rows[0].keys()), summary_rows)

    decision = (
        "The current Mode 3 run and the previous CPU Mode 3 reference are close enough to treat "
        "as the same numerical path. Proceed with the two-stage Mode 3 workflow: "
        "Stage 1 analytical-init undrained relaxation, then Stage 2 restart drainage."
        if status == "MATCH"
        else
        "The current Mode 3 run differs from the previous CPU Mode 3 reference beyond the current "
        "engineering tolerance. Do not start the two-stage Mode 3 workflow yet; first "
        "check CPU/GPU path differences or code changes affecting HydroMechInitMode=3."
    )

    args.note.parent.mkdir(parents=True, exist_ok=True)
    with args.note.open("w", encoding="utf-8") as f:
        f.write("# Mode 3 current-run versus old CPU control comparison\n\n")
        f.write(f"Case: `{args.case}`\n\n")
        f.write("## Result\n\n")
        f.write(f"- Status: `{status}`\n")
        f.write(f"- Bottom dissipation max abs difference: `{max_abs_bottom:.6g} kPa`\n")
        f.write(f"- Bottom dissipation RMS difference: `{rms_bottom:.6g} kPa`\n")
        f.write(f"- Target-point max abs bottom difference: `{max_abs_target:.6g} kPa`\n")
        f.write(f"- Target-point max abs RMS-profile difference: `{max_abs_rms_pa:.6g} Pa`\n")
        if math.isfinite(max_abs_speed):
            f.write(f"- Target-point max abs speed difference: `{max_abs_speed:.6g} m/s`\n")
        f.write("\n## Decision\n\n")
        f.write(decision + "\n\n")
        f.write("## Files\n\n")
        f.write(f"- `{args.outdir / 'mode3_gpu_vs_cpu_bottom_dissipation_compare.csv'}`\n")
        f.write(f"- `{args.outdir / 'mode3_gpu_vs_cpu_target_compare.csv'}`\n")
        f.write(f"- `{args.outdir / 'mode3_gpu_vs_cpu_summary.csv'}`\n")
        f.write(f"- `{plot_path}`\n")

    print(f"Status: {status}")
    print(f"Summary: {args.outdir / 'mode3_gpu_vs_cpu_summary.csv'}")
    print(f"Figure: {plot_path}")
    print(f"Decision note: {args.note}")


if __name__ == "__main__":
    main()
