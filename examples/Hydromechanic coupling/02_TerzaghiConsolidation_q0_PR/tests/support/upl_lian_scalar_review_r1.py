"""Replot the retained r4 standalone responses; no compiler or solver is called."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

T = Path(__file__).resolve().parents[1]
FIELDS = ["kernel_condition", "cloud", "dp_denominator", "dp", "field", "variant",
          "analytic_Laplacian", "scalar_Lstar", "scalar_abs_error",
          "scalar_relative_error_if_nonzero", "scalar_error_ratio_previous_over_current"]
LABELS = {"receiver_C_r2": "Receiver C / r2",
          "receiver_C_Eta2": "Receiver C / (r2+Eta2)",
          "production_pair_C_Eta2": "Pair C / (r2+Eta2)",
          "pair_C_r2": "Pair C / r2"}


def entry(path):
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-prefix", default="upl_lian_scalar_kernel_r4_replot")
    args = parser.parse_args()
    if not args.output_prefix or Path(args.output_prefix).name != args.output_prefix:
        parser.error("Use a plain output label under this case's tests/figures")
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[key] = "1"
    import psutil
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    source = T / "outputs/upl_lian_scalar_kernel_r4/responses.csv"
    run = T / "logs/upl_lian_scalar_kernel_r4.run.json"
    accepted = json.loads(run.read_text(encoding="utf-8-sig"))
    observed, expected = entry(source), accepted["responses"]
    if not accepted["passed"] or (observed["bytes"], observed["sha256"]) != (expected["bytes"], expected["sha256"]):
        raise ValueError("The retained passed r4 responses are required")
    with source.open(encoding="utf-8-sig", newline="") as stream:
        all_rows = list(csv.DictReader(stream))
    rows = [r for r in all_rows if r["pressure_storage"] == "double_pressure" and r["field"].startswith("cos")]
    if len(all_rows) != 768 or len(rows) != 96:
        raise ValueError("Expected 768 original rows and 96 double smooth responses")
    table = T / "figures" / (args.output_prefix + ".csv")
    png = T / "figures" / (args.output_prefix + ".png")
    check = T / "logs" / (args.output_prefix + ".plot.json")
    if any(path.exists() for path in (table, png, check)):
        raise FileExistsError("Retained plots protected; choose a fresh output prefix")
    with table.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({key: r[key] for key in FIELDS} for r in rows)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator
    fig, axes = plt.subplots(2, 4, figsize=(15, 7), layout="constrained")
    conditions = [(k, c) for k in ("production_Wendland_h1p8", "projectCubic_h1p2")
                  for c in ("ordered", "fixed_jitter_008dp")]
    for column, (kernel, cloud) in enumerate(conditions):
        for row, field in enumerate(("cos2pi_x", "cos2pi_x_plus_z")):
            ax = axes[row, column]
            for variant, label in LABELS.items():
                selected = [r for r in rows if (r["kernel_condition"], r["cloud"], r["field"], r["variant"])
                            == (kernel, cloud, field, variant)]
                ax.plot([float(r["dp"]) for r in selected],
                        [100 * float(r["scalar_relative_error_if_nonzero"]) for r in selected],
                        "-o", ms=3, label=label)
            ax.set_xscale("log", base=2)
            ax.set_yscale("log")
            ax.invert_xaxis()
            ax.xaxis.set_major_locator(FixedLocator([1 / 16, 1 / 32, 1 / 64]))
            ax.xaxis.set_major_formatter(FixedFormatter(["1/16", "1/32", "1/64"]))
            ax.xaxis.set_minor_locator(NullLocator())
            ax.set_xlabel("dp")
            ax.grid(True, which="both", alpha=.3)
            if row == 0:
                ax.set_title(("Wendland, h/dp=1.8" if kernel.startswith("production") else "Project cubic, h/dp=1.2")
                             + "\n" + ("Ordered" if cloud == "ordered" else "Fixed jitter 0.08dp"))
            if column == 0:
                ax.set_ylabel(("Axis cosine" if row == 0 else "Oblique cosine") + "\nRelative Laplace error (%)")
    axes[0, 0].legend(fontsize=7)
    fig.suptitle("Fixed-receiver scalar consistency; spatial diagnostic only")
    fig.savefig(png, dpi=160)
    plt.close(fig)
    result = dict(stage="upl_lian_scalar_review_r1", passed=True, source=entry(source), source_run=entry(run),
                  script=entry(Path(__file__).resolve()), files=[entry(table), entry(png)],
                  rows=96, solver_or_build_invoked=False, production_or_physical_acceptance=False)
    with check.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(dict(passed=True, check=str(check))))


if __name__ == "__main__":
    main()
