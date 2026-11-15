"""Offline review of one frozen four-state CPU force probe; never starts programs."""
import argparse
import csv
import datetime
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parent.parent
TAG = "c08_h18_pair6817_review_r1"
PROBE = "c08_h18_pair6817_force_r1"
PARTS = (38, 60, 83, 87)
MODES = ("baseline", "AS_off", "AV_off")


def need(value, message):
    if not value:
        raise RuntimeError(message)


def stamp(path):
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def table(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    need(args.execution_authorized, "Root review required before this offline analysis")
    folder, logs = T / "outputs" / PROBE, T / "logs"
    check = logs / (TAG + ".check.json")
    outputs = [T / "figures" / (TAG + s) for s in (".csv", ".png")]
    need(not check.exists() and not any(p.exists() for p in outputs),
         "Existing analysis or partial outputs are protected")
    source = T / "outputs/c08_h18_as03n255_full3_r1/native_r1/clocks.csv"
    inputs = [Path(__file__), folder / "completion.json", source,
              logs / (PROBE + ".build.json"), logs / (PROBE + ".check.json")]
    inputs += [folder / leaf for leaf in
               ("calls.csv", "pairs.csv", "direct_pairs.csv", "focus.csv", "soil_force.csv", "selected_clocks.csv")]
    before = [stamp(p) for p in inputs]
    try:
        done = json.loads((folder / "completion.json").read_text(encoding="utf-8"))
        run = json.loads((logs / (PROBE + ".check.json")).read_text(encoding="utf-8"))
        build = json.loads((logs / (PROBE + ".build.json")).read_text(encoding="utf-8"))
        need(done["passed"] and run["passed"] and build["passed"], "Prior probe gates failed")
        need(run["build"] == stamp(logs / (PROBE + ".build.json"))
             and run["consumed_stats_unchanged"], "Actual component build/input binding differs")
        sealed = {Path(q["path"]).resolve(): q for q in run["files"]}
        for path in inputs:
            if path.parent == folder:
                need(sealed.get(path.resolve()) == stamp(path),
                     "Component-sealed output binding differs: " + path.name)
        need(done["actual_force_calls"] == done["actual_Darcy_calls"] == 12
             and done["physical_steps"] == done["material_return_calls"] == done["filter_calls"] == 0
             and done["P38_roundtrip_scalar_checks"] == 30000
             and done["necessary_bound_checks"] == 12 and done["DtVariable_invocations"] == 0,
             "Probe coverage or zero-update contract differs")
        need(build["actual_link_objects"] == 87 and build["physical_objects_compiled"] == 0,
             "Only a new entry and original 86 physical objects are admitted")
        original_lines = source.read_bytes().splitlines(keepends=True)
        selected_lines = (folder / "selected_clocks.csv").read_bytes().splitlines(keepends=True)
        need(selected_lines == [original_lines[0]] + [original_lines[p + 1] for p in PARTS],
             "Selected signed clock rows/header differ from original bytes")
        calls, pairs, direct, focus, soil = (table(folder / name) for name in
                                           ("calls.csv", "pairs.csv", "direct_pairs.csv", "focus.csv", "soil_force.csv"))
        need(tuple(map(len, (calls, pairs, direct, focus, soil))) == (12, 12, 60, 24, 60000),
             "Output row coverage differs")
        pmap = {(int(r["part"]), r["mode"]): r for r in pairs}
        need(set(pmap) == {(p, mode) for p in PARTS for mode in MODES}, "Missing/duplicate pair response")
        for row in soil:
            need(all(math.isfinite(float(v)) for k, v in row.items() if k != "mode"), "Nonfinite soil response")
        minimum_bound = math.inf
        for row in calls:
            mode = row["mode"]
            need(mode in MODES and row["actual_preload_enabled"] == row["actual_preload_released"] == "1"
                 and int(row["actual_source_event_step"]) == 2000000
                 and int(row["actual_AS_enabled"]) == int(row["actual_AS_array_present"]) == (mode != "AS_off")
                 and float(row["actual_AV_coefficient"]) == (0 if mode == "AV_off" else float("0.10000000149011612"))
                 and row["primary_bits_unchanged"] == "1", "Actual switch/phase/state contract differs")
            bound = float(row["necessary_bound_s"])
            need(math.isfinite(bound) and bound >= 5e-6, "Original necessary step guard failed")
            minimum_bound = min(minimum_bound, bound)
        result = []
        for part in PARTS:
            baseline = pmap[part, "baseline"]
            own = {r["term"]: float(r["relative_a_radial_m_s2"]) for r in direct
                   if int(r["part"]) == part and r["mode"] == "baseline"}
            need(len(own) == 5, "Direct term set differs")
            own_total = sum(own[k] for k in
                            ("literal_total_stress_commit", "literal_AS_commit", "literal_AV_commit"))
            net = float(baseline["relative_all_neighbor_a_radial_m_s2"])
            curve = float(baseline["tangential_curvature_m_s2"])
            r = dict(part=part, time_s=float(baseline["time_s"]), tau_s=float(baseline["tau_s"]),
                     r_over_dp=float(baseline["r_m"]) / .04, rdot_m_s=float(baseline["rdot_m_s"]),
                     all_neighbor_radial_a_m_s2=net, velocity_curvature_m_s2=curve,
                     all_neighbor_rddot_m_s2=float(baseline["rddot_m_s2"]),
                     own_pair_total_stress_m_s2=own["literal_total_stress_commit"],
                     own_pair_AS_m_s2=own["literal_AS_commit"], own_pair_AV_m_s2=own["literal_AV_commit"],
                     own_pair_literal_sum_m_s2=own_total,
                     other_neighbors_and_accumulation_remainder_m_s2=net-own_total,
                     ASoff_minus_baseline_radial_a_m_s2=float(pmap[part, "AS_off"]["minus_baseline_relative_a_radial_m_s2"]),
                     AVoff_minus_baseline_radial_a_m_s2=float(pmap[part, "AV_off"]["minus_baseline_relative_a_radial_m_s2"]))
            need(abs(net + curve - r["all_neighbor_rddot_m_s2"]) <= 1e-12 * max(1, abs(net + curve)),
                 "Pair radial kinematic identity differs")
            need(all(math.isfinite(v) for v in r.values()), "Nonfinite summary")
            result.append(r)
        with outputs[0].open("x", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(result[0])); w.writeheader(); w.writerows(result)
        plt.rcParams.update({"font.size": 10})
        fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
        x = [r["tau_s"] for r in result]
        panels = [("r_over_dp", "Saved spacing / dp"),
                  ("all_neighbor_radial_a_m_s2", "Whole-neighborhood relative acceleration [m/s2]"),
                  ("own_pair_total_stress_m_s2", "Isolated source-literal pair terms [m/s2]"),
                  ("ASoff_minus_baseline_radial_a_m_s2", "Whole-force switch differences [m/s2]")]
        for ax, (_, title) in zip(axes.flat, panels):
            ax.set_title(title); ax.set_xlabel("Actual time after release [s]"); ax.grid(alpha=.25); ax.axhline(0, color=".55", lw=.7)
        axes[0, 0].plot(x, [r["r_over_dp"] for r in result], "o", label="Fixed IDs 6817 / 6866")
        for key, label, marker in [("all_neighbor_radial_a_m_s2", "All neighbors", "o"),
                                   ("own_pair_literal_sum_m_s2", "Own pair literal sum", "s"),
                                   ("other_neighbors_and_accumulation_remainder_m_s2", "Remainder incl. roundoff", "^")]:
            axes[0, 1].plot(x, [r[key] for r in result], marker, label=label)
        for key, label, marker in [("own_pair_total_stress_m_s2", "Combined total stress", "o"),
                                   ("own_pair_AS_m_s2", "AS", "s"), ("own_pair_AV_m_s2", "AV", "^")]:
            axes[1, 0].plot(x, [r[key] for r in result], marker, label=label)
        for key, label, marker in [("ASoff_minus_baseline_radial_a_m_s2", "AS off - baseline", "o"),
                                   ("AVoff_minus_baseline_radial_a_m_s2", "AV off - baseline", "s")]:
            axes[1, 1].plot(x, [r[key] for r in result], marker, label=label)
        for ax in axes.flat: ax.legend(fontsize=9)
        fig.suptitle("Original AS03 saved-state CPU audit: positive radial acceleration separates the pair\n"
                     "Four discrete states; no GPU substage replay, time update or physical acceptance")
        fig.savefig(outputs[1], dpi=160); plt.close(fig)
        need([stamp(p) for p in inputs] == before, "Consumed inputs changed")
        receipt = dict(stage=TAG, passed=True, analysis_complete=True, physical_acceptance=False,
                       actual_force_calls_reused=12, new_API_calls=0, new_solver_invocations=0,
                       new_native_invocations=0, SHA_scans=0, rows=result,
                       minimum_necessary_bound_s=minimum_bound,
                       source_clock_rows_bytes_equal=True, counterfactual_is_not_additive=True,
                       remainder_is_not_a_wall_attribution=True, historical_GPU_substage_replay=False,
                       consumed=before, consumed_stats_unchanged=True,
                       files=[stamp(p) for p in outputs], visual_QA_pending=True)
    except Exception as error:
        receipt = dict(stage=TAG, passed=False, first_failure=str(error), partial_outputs_preserved=True,
                       consumed=before, physical_acceptance=False)
        with check.open("x", encoding="utf-8") as f: json.dump(receipt, f, indent=2)
        raise
    with check.open("x", encoding="utf-8") as f: json.dump(receipt, f, indent=2)
    print(json.dumps({k: receipt[k] for k in ("stage", "passed", "rows", "minimum_necessary_bound_s")}))


if __name__ == "__main__":
    main()
