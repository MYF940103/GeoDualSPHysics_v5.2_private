"""Independent retained-hash audit and a late-window 15-s comparison (no solver)."""
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mdbc_gpu_vector_run import TESTS, bound, read, verify


def main():
    snapshot = read(TESTS / "logs/gpu_spr_15_verified_r2.snapshot.json")
    saved = {e["path"]: e for e in snapshot["entries"]}
    evidence, substitutions = [], []
    def retained_verify(items):
        for item in items:
            if bound(item["path"])["sha256"] == item["sha256"].upper():
                continue
            e = saved[item["path"]]
            copies = [Path(snapshot["snapshot"]) / e["relative"],
                      TESTS / "outputs/gpu_spr_15_verified" / e["relative"],
                      TESTS / "outputs/gpu_spr_short_verified" / e["relative"]]
            copy = next((bound(p) for p in copies if p.is_file() and bound(p)["sha256"] == item["sha256"].upper()), None)
            assert copy is not None, "No verified retained source for " + item["path"]
            substitutions.append(dict(original=item, retained_copy=copy))
    for suffix in ("c", "h"):
        path = TESTS / "logs" / ("gpu_spr_15_" + suffix + "_r1.run.json")
        run = read(path)
        assert run["passed"] and run["owned_process_exited"] and run["exit_code"] == 0
        assert run["completion"]["sampled_frames"] == 15001 and abs(run["completion"]["final_time"] - 15) < 1e-7
        retained_verify(run["inputs"] + run["outputs"])
        evidence.append(bound(path))
    tables = {}
    for name in ("gpu_spr_15_c_review_r1", "gpu_spr_15_h_review_r1", "gpu_spr_15_pair_review_r1"):
        path = TESTS / "logs" / (name + ".check.json")
        check = read(path)
        assert check["passed"] and check["frames"] == 15001
        retained_verify(check["evidence"] + [check["figure"], check["metrics"]])
        evidence += [bound(path), check["figure"], check["metrics"]]
        tables[name] = pd.read_csv(check["metrics"]["path"], float_precision="round_trip")
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    metrics = ("mean_pressure_pa", "top_settlement_mm", "bottom_settlement_mm",
               "max_layer_total_error_pa", "top_gap_pa", "total_stress_Q_pa")
    titles = ("Mean pressure (Pa)", "Top material settlement (mm)", "Bottom material settlement (mm)",
              "Layer total-stress residual (Pa)", "Top adjacent-layer gap (Pa)", "Layer second-difference RMS Q (Pa)")
    summary = {}
    for suffix, color in (("c", "#2067ac"), ("h", "#be681c")):
        table = tables["gpu_spr_15_" + suffix + "_review_r1"]
        late = table[table.time_s >= .1 - 1e-7]
        for ax, key, title in zip(axes.flat, metrics, titles):
            ax.plot(late.time_s, late[key + "_reference"], color=color, lw=2, label="CPU " + suffix)
            ax.plot(late.time_s, late[key], color=color, ls="--", lw=1, label="GPU " + suffix)
            ax.set(title=title, xlabel="Actual time (s)"); ax.grid(alpha=.25)
        summary[suffix] = dict(final=table.iloc[-1].to_dict(),
            maxima_post01={k: float(late[k].max()) for k in metrics[3:]},
            max_pressure_rms_difference_pa=float(table.pressure_rms_difference_pa.max()),
            max_top_settlement_difference_mm=float(table.top_settlement_difference_mm.abs().max()),
            max_bottom_settlement_difference_mm=float(table.bottom_settlement_difference_mm.abs().max()))
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Case 02: CPU/GPU matched native materials, t >= 0.1 s")
    fig.text(.5, .015, "Original safety limits unchanged. Q remains diagnostic; 15 s is not full-cycle acceptance.", ha="center")
    fig.tight_layout(rect=(0, .04, 1, .96))
    image = TESTS / "figures/gpu_spr_15_summary_r1.png"
    with image.open("xb") as stream:
        fig.savefig(stream, dpi=160)
    evidence += [bound(image), bound(__file__), bound(TESTS / "logs/gpu_spr_15_verified_r2.snapshot.json")]
    result = dict(passed=True, summary=summary, evidence=evidence, snapshot_substitutions=substitutions,
                  inspected_figures_pending=[str(image)], physical_acceptance=False)
    with (TESTS / "logs/gpu_spr_15_summary_r1.check.json").open("x", encoding="utf8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(dict(passed=True, summary=summary), indent=2))


if __name__ == "__main__":
    main()
