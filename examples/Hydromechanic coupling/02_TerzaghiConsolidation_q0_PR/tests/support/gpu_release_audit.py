"""Deduplicated evidence audit and independently sampled final material checks."""
import csv
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mdbc_gpu_vector_run import TESTS, bound, read
from settlement_audit import previous, theoretical_settlement


def main():
    tag = "gpu_release_audit_r1"
    receipt = TESTS / "logs" / (tag + ".check.json")
    assert not receipt.exists()
    state_path = TESTS / "logs/gpu_full_2tv_r1.status.json"
    status = read(state_path)
    assert status["status"] == "cpu_gpu_2tv_completed_pending_visual_physical_review"
    assert all(c["exit_code"] == 0 and c["owned_process_exited"] for c in status["children"])
    queue = read(TESTS / "logs/gpu_full_2tv_r1.queue_attempt.json")
    assert queue["terminal"]["status"] == status["status"]
    evidence = {}
    def add(items):
        for item in items:
            key = str(Path(item["path"]).resolve()).lower()
            if key in evidence:
                assert evidence[key]["sha256"].upper() == item["sha256"].upper()
            else:
                evidence[key] = item
    add([bound(state_path), bound(TESTS / "logs/gpu_full_2tv_r1.queue_attempt.json"), bound(__file__)])
    add(status["prerequisites"])
    add([c["log_hash"] for c in status["children"]])
    names = ["gpu_full_save_gpu_r1", "gpu_full_save_cpu_r1", "gpu_full_2tv_gpu_r1", "gpu_full_2tv_cpu_r1"]
    results = {}
    for name in names:
        path = TESTS / "logs" / (name + ".run.json")
        run = read(path)
        assert run["passed"] and run["owned_process_exited"] and run["exit_code"] == 0
        add([bound(path)] + run["inputs"] + run["outputs"])
        results[name] = run
    for name in ("gpu_full_save_gpu_prefix_r1", "gpu_full_save_cpu_prefix_r1", "gpu_full_save_pair_r1",
                 "gpu_full_2tv_gpu_prefix_r1", "gpu_full_2tv_cpu_prefix_r1", "gpu_full_2tv_r1_pair", "gpu_full_2tv_r1"):
        path = TESTS / "logs" / (name + ".check.json")
        check = read(path)
        assert check["passed"]
        if "prefix" in name:
            assert check["exact_physical_fields"]
        if "_pair" in name:
            assert check["comparison"]["within_limits"] and not check["half_step_gate_applied"]
        add([bound(path)] + check["evidence"])
        add([check[k] for k in ("figure", "metrics") if k in check and isinstance(check[k], dict) and "path" in check[k]])
    # Hash each unique large file only once. No source/output rewrites or solver.
    for i, item in enumerate(evidence.values()):
        assert bound(item["path"])["sha256"] == item["sha256"].upper(), item["path"]
        if i % 100 == 0:
            print(f"Verified {i}/{len(evidence)} files", flush=True)
    final = {}
    for backend in ("cpu", "gpu"):
        name = "gpu_full_2tv_" + backend + "_r1"
        run = results[name]
        path = TESTS / "outputs" / name / "state.csv"
        initial = pd.read_csv(path, nrows=1000, float_precision="round_trip")
        # Independent final-frame read, not the analysis history/profile table.
        with path.open("rb") as stream:
            header = stream.readline().decode("utf8")
            stream.seek(max(0, path.stat().st_size - 1024 * 1024))
            lines = stream.read().decode("utf8").splitlines()[-1000:]
        a = pd.read_csv(io.StringIO(header + "\n".join(lines)), float_precision="round_trip")
        assert np.array_equal(a.id, np.arange(40, 1040)) and a.step.eq(7288429).all()
        assert a.time_s.nunique() == 1 and abs(a.time_s.iloc[0] - 72.88429) < 1e-7
        assert run["completion"]["sampled_frames"] == 7290
        xml = TESTS / "outputs" / (name + "_input") / ("CaseTCq0_" + name + ".xml")
        model = previous.model(ET.parse(xml))
        time = float(a.time_s.iloc[0])
        settlement = (initial.z.to_numpy() - a.z.to_numpy()) * 1000
        top, bottom = np.arange(99, 1000, 100), np.arange(0, 1000, 100)
        theory_bottom = float(theoretical_settlement([initial.z.iloc[0]], time, model)[0])
        final[backend] = dict(mean_pressure_pa=float(a.pressure.mean()), top_material_mm=float(settlement[top].mean()),
            bottom_material_mm=float(settlement[bottom].mean()), classical_bottom_material_mm=theory_bottom,
            bottom_material_error_mm=float(settlement[bottom].mean() - theory_bottom),
            loop_seconds=run["completion"]["elapsed_seconds"])
    full = read(TESTS / "logs/gpu_full_2tv_r1.check.json")
    for backend in final:
        metrics = full["metrics"][backend.upper()]["final"]
        assert abs(final[backend]["mean_pressure_pa"] - metrics["mean_pressure_pa"]) < 1e-10
        assert abs(final[backend]["top_material_mm"] - metrics["top_settlement_mm"]) < 1e-10
    # Historical comparisons are descriptive only: load/gradient/damping/SPR differ.
    old_path = TESTS / "figures/hg_merge_full_r1_history.csv"
    old = pd.read_csv(old_path)
    current_path = TESTS / "figures/gpu_full_2tv_r1_history.csv"
    current = pd.read_csv(current_path)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    historical = {}
    for label, a in old.groupby("series"):
        historical[label] = a.iloc[-1].to_dict()
        if label in ("float", "dt1", "dt05", "off", "hg"):
            h = a[a.time_s >= .1]
            axes[0].plot(h.tv, h.mean_p_pa, lw=1, alpha=.7, label="Historical " + label)
            axes[1].plot(h.tv, h.top_settlement_mm, lw=1, alpha=.7)
    h = current[(current.backend == "GPU") & (current.time_s >= .1)]
    axes[0].plot(h.tv, h.mean_pressure_pa, "k--", lw=1.8, label="Current GPU (CPU overlaps)")
    axes[1].plot(h.tv, h.top_settlement_mm, "k--", lw=1.8)
    axes[1].plot(h.tv, h.classical_top_mm, "k:", lw=1.3)
    axes[2].plot(h.tv, h.total_stress_Q_pa, color="#2067ac", label="Current Q")
    axes[0].set(title="Mean pore pressure (Pa)", yscale="log", xlabel="Tv at actual time", ylim=(30, 15000))
    axes[1].set(title="Native top material settlement (mm)", xlabel="Tv at actual time")
    axes[2].set(title="Current layer second-difference RMS (Pa)", xlabel="Tv at actual time")
    for ax in axes:
        ax.grid(alpha=.25)
    axes[0].legend(fontsize=7)
    fig.suptitle("Late dissipation and retained history: not a single-factor comparison")
    fig.text(.5, .015, "Old load, gradient, damping and boundary settings differ; NoHG stops at 55.8 s. Q is diagnostic, not strain or energy.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, .94))
    image = TESTS / "figures" / (tag + ".png")
    with image.open("xb") as stream:
        fig.savefig(stream, dpi=170)
    plt.close(fig)
    add([bound(old_path), bound(current_path), bound(image)])
    speed = final["cpu"]["loop_seconds"] / final["gpu"]["loop_seconds"]
    result = dict(passed=True, unique_hash_verified=len(evidence), evidence=list(evidence.values()),
        final_independent=final, historical_final=historical, cpu_gpu_loop_ratio=speed,
        gpu_loop_reduction_pct=100 * (1 - 1 / speed), figures_inspected_pending=[str(image)],
        one_dimensional_release_scope="Provisionally accepted by user Oct16; current same-physics GPU delivery passed",
        physical_acceptance_generalized=False)
    with receipt.open("x", encoding="utf8") as stream:
        json.dump(result, stream, indent=2, allow_nan=True)
    print(json.dumps(dict(passed=True, unique_hash_verified=len(evidence), final=final,
                         ratio=speed, reduction_pct=result["gpu_loop_reduction_pct"]), indent=2))


if __name__ == "__main__":
    main()
