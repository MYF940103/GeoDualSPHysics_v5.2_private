"""Native endpoint diagnosis of the rejected k1e-5 run; no solver or formal edits."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import k5_guard_probe as probe
from formal_release_sequence import CASE, TESTS, STEM, utc
from mdbc_gpu_vector_run import read, bound, verify


def main():
    check = TESTS/"logs/k5_failure_review_r1.check.json"
    assert not check.exists()
    state_path = TESTS/"logs/formal_release_k5_r1.status.json"
    state = read(state_path)
    assert state["status"] == "formal_k5_rejected_or_interrupted" and state["children"][0]["stopped_by_monitor"]
    verify(state["inputs"])
    evidence = state["inputs"]+[bound(state_path), bound(TESTS/"logs/formal_release_k5_r1.queue_attempt.json"), bound(__file__)]
    baseline = CASE/(STEM+"k1em5_release_GPU_out")
    evidence += [bound(p) for p in baseline.rglob("*") if p.is_file()]
    cases = [("GPU original", baseline, .01, 1, "#555555", "-"),
        ("CPU same dt", TESTS/"outputs/k5_cpu_short_r1", .01, None, "#a06baf", ":"),
        ("GPU half dt", TESTS/"outputs/k5_dt_half_r1", .01, None, "#bd8a12", "--"),
        ("GPU dp=.005", TESTS/"outputs/k5_dp_half_r1", .005, None, "#cb7137", "-"),
        ("GPU dp=.003125 / half dt", TESTS/"outputs/k5_grid320_r1", .003125, None, "#256da3", "-")]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.4))
    rows, fields = [], {}
    for label, folder, dp, index, color, style in cases:
        if index is None:
            receipt = TESTS/"logs"/(folder.name+".check.json")
            result = read(receipt); verify(result["evidence"])
            evidence += result["evidence"]+[bound(receipt)]
            index = len(list((folder/"data").glob("Part_*.bi4")))-1
        a, initial = probe.native(folder, index), probe.native(folder, 0)
        m = probe.metrics(a, initial, dp)
        assert abs(m["time_s"]-.10001) < 1e-10
        nx, nz = round(.1/dp), round(1/dp)
        z0 = initial.z.to_numpy().reshape(nx, nz).mean(0)
        p = a.pressure.to_numpy().reshape(nx, nz).mean(0)
        s = (a.sigma_zz-a.pressure).to_numpy().reshape(nx, nz).mean(0)
        axes[0].plot(p/10000, z0, color=color, ls=style, marker=".", ms=3, label=label)
        axes[1].plot(s+10000, z0, color=color, ls=style, marker=".", ms=3)
        rows.append(dict(label=label, dp_m=dp, **m)); fields[label] = a
    labels = ["GPU\noriginal", "CPU\nsame dt", "GPU\nhalf dt", "GPU\ndp=.005", "GPU\ndp=.003125"]
    axes[2].bar(np.arange(len(rows)), [r["top_gap_pa"] for r in rows], color=[c[4] for c in cases])
    axes[2].set(xticks=np.arange(len(rows)), xticklabels=labels, ylabel="Top adjacent-layer total-stress gap (Pa)", ylim=(0, 300))
    axes[2].axhline(100, color="black", ls="--", label="Original 100-Pa limit"); axes[2].legend(fontsize=9)
    axes[0].set(xlabel="Pore pressure / q0", ylabel="Initial material height z0/H", ylim=(.90, 1)); axes[0].legend(fontsize=8)
    axes[1].set(xlabel="Total stress + q0 (Pa)", ylabel="Initial material height z0/H", ylim=(.90, 1))
    axes[1].axvline(0, color="black", lw=.8); axes[1].axvline(-100, color=".4", ls="--", lw=.8); axes[1].axvline(100, color=".4", ls="--", lw=.8)
    for ax in axes: ax.grid(alpha=.2)
    fig.suptitle("k=1e-5: native t=0.10001 s endpoint diagnosis, NOT 2Tv acceptance")
    fig.tight_layout()
    png, csv = TESTS/"figures/k5_failure_review_r1.png", TESTS/"figures/k5_failure_review_r1.csv"
    assert not png.exists() and not csv.exists()
    with png.open("xb") as stream: fig.savefig(stream, dpi=170)
    plt.close(fig); pd.DataFrame(rows).to_csv(csv, index=False, mode="x")
    reference = fields["GPU original"]
    differences = {label: dict(pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-reference.pressure)**2))),
        max_stress_component_difference_pa=float(np.max(abs(a[["sigma_xx", "sigma_yy", "sigma_zz", "sigma_xy", "sigma_yz", "sigma_xz"]].to_numpy()-reference[["sigma_xx", "sigma_yy", "sigma_zz", "sigma_xy", "sigma_yz", "sigma_xz"]].to_numpy()))))
        for label, a in fields.items() if len(a) == len(reference)}
    evidence += [bound(png), bound(csv)]
    result = dict(reviewed_utc=utc(), audit_passed=True, original_formal_run_completed=False, last_complete_native_time_s=.2,
        original_failure=state["reason"], actual_in_memory_stop_time_unknown=True, endpoint_rows=rows, same_geometry_endpoint_differences=differences,
        conclusion="CPU reproduces GPU; half dt alone does not remove the early residual. Finer space plus a revalidated smaller dt passes the single endpoint, not long admission.",
        limitations=["No revised formal inputs, 2Tv, full half-step or theory acceptance.",
            "Different grids have different top material heights; their short settlement values are not an equal-material precision ranking.",
            "Geometric exterior-corner cleanup and smaller stable dt were required for the finer tests. Failed tags and their logs remain retained."], evidence=evidence)
    with check.open("x", encoding="utf8") as stream: json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(audit_passed=True, rows=rows, same_geometry_endpoint_differences=differences), indent=2))


if __name__ == "__main__": main()
