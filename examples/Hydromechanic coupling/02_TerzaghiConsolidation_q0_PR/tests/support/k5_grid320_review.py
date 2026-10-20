"""Offline native review of the completed refined-grid short pairs; no solver."""
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import k5_guard_probe as probe
from k5_grid320_sequence import TAG, FIELDS
from formal_release_sequence import TESTS, utc
from mdbc_gpu_vector_run import read, bound, verify


def main():
    out = TESTS/"logs/k5_grid320_review_r1.check.json"
    assert not out.exists()
    status_path = TESTS/"logs"/(TAG+".status.json")
    queue_path = TESTS/"logs"/(TAG+".queue_attempt.json")
    state, queue = read(status_path), read(queue_path)
    assert state["status"] == queue["terminal"]["status"] == "grid320_1s_pairs_passed_pending_review"
    assert state["queue_status"] == "queued" and len(state["runs"]) == 4
    evidence = state["inputs"]+[bound(p) for p in (Path(__file__), status_path, queue_path)]
    for item in state["runs"]:
        assert item["exit_code"] == 0 and item["owned_process_exited"] and item["completed"]
        assert not item.get("stopped_by_monitor", False)
        evidence += item["outputs"]
    unique = {p["path"]: p for p in evidence}
    verify(unique.values())
    print("Verified recorded hashes:", len(unique), flush=True)
    histories, profiles, prefixes, run_summaries = {}, {}, {}, []
    for item in state["runs"]:
        suffix = item["label"].removeprefix(TAG+"_")
        folder = TESTS/"outputs"/item["label"]
        files = sorted((folder/"data").glob("Part_*.bi4"))
        assert len(files) == item["frames"]
        initial = probe.native(folder, 0)
        assert np.array_equal(initial.id.to_numpy(), np.arange(128, 10368))
        rows, prefix, snapshots = [], [], {}
        for i in range(len(files)):
            a = probe.native(folder, i)
            m = probe.metrics(a, initial, .003125)
            assert m["stress_guard_passed"]
            assert int(a.step.iloc[0]) == i*round(.005/item["dt_s"])
            rows.append(m)
            if i <= 30:
                prefix.append(a[FIELDS].to_numpy(dtype="<f8").tobytes())
            if i in (20, 30, 100, 200):
                snapshots[i] = a
        history = pd.DataFrame(rows)
        expected = round(item["duration_s"]/item["dt_s"])
        assert rows[-1]["step"] == expected and abs(rows[-1]["time_s"]-item["duration_s"]) < 1e-7
        for key, value in item["final"].items():
            assert rows[-1][key] == value, key
        text = (folder/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
        assert "Finished execution (code=0)." in text
        calls = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
        limits = re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)", text)
        assert calls and list(map(int, calls.groups())) == [2*expected, expected, expected, 2*expected]
        assert limits and float(limits[1]) <= .2 and float(limits[2]) < .01
        run_csv = pd.read_csv(folder/"Run.csv", sep=";")
        assert int(run_csv.Np.iloc[0]) == 10368 and int(run_csv.Nfixed.iloc[0]) == 128
        assert int(run_csv.PartsOut.iloc[0]) == 0 and int(run_csv.Steps.iloc[0]) == expected
        csv = TESTS/"figures"/(item["label"]+"_review.csv")
        history.to_csv(csv, index=False, mode="x"); evidence.append(bound(csv))
        post = history[history.stress_guard_applicable]
        run_summaries.append(dict(label=item["label"], samples=len(rows), final=rows[-1],
            post_point1s_max_stress_pa=float(post.max_layer_total_error_pa.max()),
            post_point1s_max_top_gap_pa=float(post.top_gap_pa.max()),
            loop_seconds=float(run_csv.TSimul.iloc[0]), hg_max_dt_tau=float(limits[1]), hg_spin_bound=float(limits[2]),
            csv=str(csv)))
        histories[suffix], profiles[suffix], prefixes[suffix] = history, (initial, snapshots), prefix
        print("Reviewed", suffix, len(rows), "native frames", flush=True)
    for c, h in (("015c", "1c"), ("015h", "1h")):
        assert prefixes[c] == prefixes[h]
    # Independently revisit every 1-s paired native field, with actual times and IDs.
    pair_rows = []
    for i in range(201):
        a = probe.native(TESTS/"outputs"/(TAG+"_1c"), i)
        b = probe.native(TESTS/"outputs"/(TAG+"_1h"), i)
        assert np.array_equal(a.id, b.id)
        assert abs(a.time_s.iloc[0]-b.time_s.iloc[0]) < 1e-8
        assert int(b.step.iloc[0]) == 2*int(a.step.iloc[0])
        top = profiles["1c"][0].z > .996
        pair_rows.append(dict(time_s=float(a.time_s.iloc[0]),
            pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))),
            top_settlement_difference_mm=abs(float((a.z[top]-b.z[top]).mean()*1000))))
    pair = pd.DataFrame(pair_rows)
    assert pair.pressure_rms_pa.max() <= 5 and pair.top_settlement_difference_mm.max() <= .005
    for end, count in (("015", 31), ("1", 201)):
        old = next(p for p in state["comparisons"] if p["left"] == end+"c" and p["right"] == end+"h")
        assert float(pair.pressure_rms_pa.iloc[:count].max()) == old["max_pressure_rms_pa"]
        assert float(pair.top_settlement_difference_mm.iloc[:count].max()) == old["max_top_settlement_difference_mm"]
    pair_csv = TESTS/"figures/k5_grid320_review_r1_half.csv"
    pair.to_csv(pair_csv, index=False, mode="x"); evidence.append(bound(pair_csv))
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    colors, styles = {"1c": "#256da3", "1h": "#c47725"}, {"1c": "-", "1h": "--"}
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    panels = [("mean_pressure_pa", "Mean pore pressure (Pa)"), ("top_settlement_mm", "Top native-material settlement (mm)"),
              ("max_layer_total_error_pa", "Max layer total-stress error (Pa)"), ("top_gap_pa", "Top adjacent-layer stress gap (Pa)"),
              ("Q_pa", "Q: RMS second layer difference (Pa)")]
    for ax, (key, ylabel) in zip(axes.flat, panels):
        for suffix, label in (("1c", "dt = 5 microseconds"), ("1h", "dt = 2.5 microseconds")):
            h = histories[suffix]
            ax.plot(h.time_s, h[key], color=colors[suffix], ls=styles[suffix], lw=1.5, label=label)
        ax.set(xlabel="Actual physical time (s)", ylabel=ylabel, xlim=(0, 1))
        if key in ("max_layer_total_error_pa", "top_gap_pa"):
            ax.set_xlim(.1, 1); ax.set_ylim(0, 105); ax.axhline(100, color=".25", ls=":", lw=1)
            ax.set_xlabel("Actual time (s); guard applies from 0.1 s")
        ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=9)
    ax = axes[1, 2]
    ax.plot(pair.time_s, pair.pressure_rms_pa, color="#256da3", lw=1.5, label="Pressure RMS difference")
    ax.axhline(5, color=".25", ls=":", label="Original 5-Pa half-step limit")
    ax.set(xlabel="Actual physical time (s)", ylabel="Coarse / half pressure difference (Pa)", xlim=(0, 1), ylim=(0, 5.3))
    ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.suptitle("k=1e-5, dp=1/320 m, full width=0.1 m: short-window native histories")
    fig.text(.5, .008, "10240 native soil particles; eta=.04, xi=.1. Half-step agreement is not 2Tv or theory acceptance.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .03, 1, .95))
    history_png = TESTS/"figures/k5_grid320_review_r1_history.png"
    with history_png.open("xb") as stream: fig.savefig(stream, dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for row, index in enumerate((30, 200)):
        for suffix, label in (("1c", "dt = 5 microseconds"), ("1h", "dt = 2.5 microseconds")):
            initial, snapshots = profiles[suffix]; a = snapshots[index]
            z0 = initial.z.to_numpy().reshape(32, 320).mean(0)
            p = a.pressure.to_numpy().reshape(32, 320).mean(0)
            total = (a.sigma_zz-a.pressure).to_numpy().reshape(32, 320).mean(0)
            axes[row, 0].plot(p/10000, z0, color=colors[suffix], ls=styles[suffix], lw=1.4, label=label)
            axes[row, 1].plot(total+10000, z0, color=colors[suffix], ls=styles[suffix], lw=1.4)
        t = histories["1c"].time_s.iloc[index]
        axes[row, 0].set(xlabel="Pore pressure / q0", ylabel="Initial material height z0/H", ylim=(.85, 1), title=f"Actual t = {t:.6g} s")
        axes[row, 1].set(xlabel="Layer total stress + q0 (Pa)", ylabel="Initial material height z0/H", ylim=(.85, 1), xlim=(-105, 105), title=f"Actual t = {t:.6g} s")
        for v in (-100, 100): axes[row, 1].axvline(v, color=".4", ls=":", lw=1)
        axes[row, 1].axvline(0, color=".4", lw=.7)
    axes[0, 0].legend(fontsize=9)
    for ax in axes.flat: ax.grid(alpha=.2)
    fig.suptitle("Near-drainage-surface native profiles: coarse / half, same initial materials")
    fig.text(.5, .008, "Upper 15% of specimen shown. This is numerical sensitivity, not an instantaneous-load theory comparison.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .03, 1, .95))
    profile_png = TESTS/"figures/k5_grid320_review_r1_profiles.png"
    with profile_png.open("xb") as stream: fig.savefig(stream, dpi=160)
    plt.close(fig)
    evidence += [bound(history_png), bound(profile_png)]
    result = dict(reviewed_utc=utc(), audit_passed=True, verified_recorded_hashes=len(unique), runs=run_summaries,
        half_samples=201, max_pressure_rms_pa=float(pair.pressure_rms_pa.max()),
        max_top_settlement_difference_mm=float(pair.top_settlement_difference_mm.max()),
        same_dt_native_prefix_0_ulp=True, full_cycle_admitted=False, figures=[str(history_png), str(profile_png)],
        limitations=["Only 1-s / 0.15-s short pairs, not 15-s or 2Tv.",
                     "No theory acceptance, exact HG restart, plastic or complex-boundary validation.",
                     "HG runtime counters and bounds verified; full per-step internal HG states not stored."], evidence=evidence)
    with out.open("x", encoding="utf8") as stream: json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k != "evidence"}, indent=2), flush=True)


if __name__ == "__main__": main()
