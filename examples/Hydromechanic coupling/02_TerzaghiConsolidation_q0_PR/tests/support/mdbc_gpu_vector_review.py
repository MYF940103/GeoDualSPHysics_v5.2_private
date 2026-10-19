"""Audit saved manufactured-field CSV limits and plot CPU/GPU comparisons."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mdbc_gpu_vector_run import TESTS, bound, read, verify


def ratios(output):
    result = np.zeros(6)
    with (output / "vector_rows.csv").open() as stream:
        for row in csv.DictReader(stream):
            if int(row["roi"]):
                result[0] = max(result[0], float(row["error"]) / float(row["tolerance"]))
    with (output / "consumer_rows.csv").open() as stream:
        for row in csv.DictReader(stream):
            j = int(row["component"])
            group = 0 if j < 6 else j - 5
            floor = (20., 2000., .02)[group]
            error = abs(float(row["mls"]) - float(row["oracle"]))
            result[group + 1] = max(result[group + 1], error / (floor + 2e-5 * abs(float(row["oracle"]))))
            if group < 2:
                bias = abs(float(row["mls"]) - float(row["analytic"]))
                result[group + 4] = max(result[group + 4], bias / (floor + 2e-5 * abs(float(row["analytic"]))))
    assert np.isfinite(result).all() and np.max(result) <= 1
    return result.tolist()


def main():
    tag = "mdbc_gpu_vector_review_r1"
    receipt, figure = TESTS / "logs" / (tag + ".check.json"), TESTS / "figures" / (tag + ".png")
    assert not receipt.exists() and not figure.exists()
    cpu_path = TESTS / "logs/mdbc_vector_review_r2.check.json"
    cpu = read(cpu_path)
    assert cpu["all_18_combinations_present"] and cpu["independent_csv_limits_passed"]
    evidence = [bound(cpu_path), bound(__file__)]
    labels = [(r["geometry"], r["slip"]) for r in cpu["results"]]
    assert len(labels) == len(set(labels)) == 18
    data = {"CPU Release (retained)": [np.asarray(r["preset_limit_ratios_velocity_scalar_S_P_R_Sanalytic_Panalytic"])[[0, 2, 3, 4, 5, 6]].tolist() for r in cpu["results"]]}
    metrics = {}
    for backend in ("rel", "dbg"):
        path = TESTS / "logs" / ("mdbc_gpu_vector_" + backend + "_r1.check.json")
        check = read(path)
        assert check["passed"] and check["inputs_unchanged"] and len(check["runs"]) == 18
        verify(check["inputs"])
        evidence.append(bound(path))
        values = {}
        for run in check["runs"]:
            assert run["completed"] and run["exit_code"] == 0 and run["owned_process_exited"]
            verify(run["outputs"])
            key = (run["variant"]["geometry"], run["variant"]["slip_mode"])
            values[key] = ratios(Path(run["output"]))
            evidence.extend(run["outputs"])
        assert set(values) == set(labels)
        title = "GPU " + ("Release" if backend == "rel" else "Debug")
        data[title] = [values[k] for k in labels]
        metrics[title] = dict(maximum_limit_ratio=float(np.max(data[title])), ratios=data[title])
    fig, axes = plt.subplots(1, 3, figsize=(19, 9), sharey=True)
    columns = ["Velocity", "S vs oracle", "P vs oracle", "R vs oracle", "S analytic", "P analytic"]
    for ax, (title, values) in zip(axes, data.items()):
        a = np.asarray(values)
        ax.imshow(a, vmin=0, vmax=1, cmap="Blues", aspect="auto")
        ax.set_title(title)
        ax.set_xticks(np.arange(6), columns, rotation=45, ha="right")
        ax.set_yticks(np.arange(18), [g + " / slip " + str(s) for g, s in labels])
        ax.tick_params(axis="both", length=0)
        for i in range(18):
            for j in range(6):
                ax.text(j, i, f"{a[i,j]:.3g}", ha="center", va="center", fontsize=8)
    fig.suptitle("Fixed-plane derivative reconstruction - error / original CPU tolerance (pass <= 1)", fontsize=14)
    fig.text(.5, .015, "18 geometries/slip combinations; genuine production S/P/R consumers. No time integration.\n"
             "Raw density analytic bias is not a gate; all-native density and fallback checks are recorded by each fixture. These are not coupled accuracy tests.", ha="center", fontsize=10)
    fig.tight_layout(rect=(0, .075, 1, .96))
    with figure.open("xb") as stream:
        fig.savefig(stream, dpi=170, facecolor="white")
    plt.close(fig)
    with receipt.open("x", encoding="utf8") as stream:
        json.dump(dict(passed=True, status="manufactured_csv_limits_passed_pending_visual_review", labels=labels,
                       metrics=metrics, figure=bound(figure), evidence=evidence, physical_acceptance=False,
                       notes="GPU raw CSV limits independently recalculated; CPU ratios adopted from retained reviewed receipt."), stream, indent=2)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
