from pathlib import Path
import argparse
import csv

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


POINTS = ("A", "B")


def read_history(case_dir):
    csv_path = case_dir / "figures" / "yao2d_ab_normalized_epwp.csv"
    if not csv_path.exists():
        raise SystemExit(f"Missing A/B CSV: {csv_path}")
    rows = []
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    if not rows:
        raise SystemExit(f"Empty A/B CSV: {csv_path}")
    t = np.array([float(row["time_s"]) for row in rows], dtype=float)
    data = {"time_s": t}
    for point in POINTS:
        data[point] = np.array([float(row[f"{point}_epwp_over_q0"]) for row in rows], dtype=float)
    return data


def parse_case_arg(text):
    if "=" not in text:
        raise argparse.ArgumentTypeError("Use label=case_output_dir.")
    label, path = text.split("=", 1)
    label = label.strip()
    if not label:
        raise argparse.ArgumentTypeError("Case label cannot be empty.")
    return label, Path(path)


def main():
    parser = argparse.ArgumentParser(description="Compare Yao 2-D A/B normalized EPWP histories.")
    parser.add_argument(
        "--case",
        dest="cases",
        type=parse_case_arg,
        action="append",
        required=True,
        help="Comparison case in the form label=case_output_dir. Repeat for multiple cases.",
    )
    parser.add_argument("--out-dir", type=Path, required=True, help="Directory for comparison plots and summary CSV.")
    parser.add_argument("--baseline", default=None, help="Optional baseline label for difference metrics.")
    args = parser.parse_args()

    cases = [(label, path.resolve()) for label, path in args.cases]
    histories = {label: read_history(path) for label, path in cases}
    args.out_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), constrained_layout=True)
    for ax, point in zip(axes, POINTS):
        for label, _ in cases:
            h = histories[label]
            ax.plot(h["time_s"], h[point], lw=1.8, label=label)
        ax.axvline(0.1, color="0.3", ls="--", lw=1.0)
        ax.set_xlabel("t (s)")
        ax.set_ylabel(f"{point}: Excess pore pressure / q0")
        ax.grid(True, alpha=0.28)
        ax.legend()
    fig.savefig(args.out_dir / "yao2d_ab_compare_normalized_epwp.png", dpi=240)
    plt.close(fig)

    baseline = args.baseline if args.baseline else cases[0][0]
    if baseline not in histories:
        raise SystemExit(f"Baseline label not found: {baseline}")

    summary_rows = []
    for label, path in cases:
        h = histories[label]
        row = {"case": label, "case_dir": str(path)}
        for point in POINTS:
            y = h[point]
            imax = int(np.nanargmax(y))
            row[f"{point}_max"] = float(y[imax])
            row[f"{point}_time_at_max_s"] = float(h["time_s"][imax])
            row[f"{point}_final"] = float(y[-1])
            row[f"{point}_mean"] = float(np.nanmean(y))
            y0 = histories[baseline][point]
            if len(y0) == len(y) and np.allclose(histories[baseline]["time_s"], h["time_s"]):
                diff = y - y0
                row[f"{point}_max_abs_diff_vs_{baseline}"] = float(np.nanmax(np.abs(diff)))
                row[f"{point}_final_diff_vs_{baseline}"] = float(y[-1] - y0[-1])
                row[f"{point}_rms_diff_vs_{baseline}"] = float(np.sqrt(np.nanmean(diff * diff)))
            else:
                row[f"{point}_max_abs_diff_vs_{baseline}"] = ""
                row[f"{point}_final_diff_vs_{baseline}"] = ""
                row[f"{point}_rms_diff_vs_{baseline}"] = ""
        summary_rows.append(row)

    csv_path = args.out_dir / "yao2d_ab_compare_summary.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(csv_path)
    print(args.out_dir / "yao2d_ab_compare_normalized_epwp.png")
    for row in summary_rows:
        print(row)


if __name__ == "__main__":
    main()
