"""Stream matched case-02 material histories, original safety and half-step limits."""
import argparse
from itertools import islice
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mdbc_gpu_vector_run import TESTS, bound, read, verify

SOIL = np.arange(40, 1040)
TOP, BOTTOM = np.arange(99, 1000, 100), np.arange(0, 1000, 100)
STRESS = ["sigma_xx", "sigma_yy", "sigma_zz", "sigma_xy", "sigma_yz", "sigma_xz"]


def records(name):
    path = TESTS / "logs" / (name + ".run.json")
    run = read(path)
    if "settings" in run:
        assert run["passed"] and run["owned_process_exited"] and run["exit_code"] == 0
        s = run["settings"]
        assert s["spr"] == s["event_grid"] == 1 and s["damping_text"] == "0.04" and s["xi"] == .1
    else:
        check_path = TESTS / "logs" / (name + ".check.json")
        # The CPU 15-s continuation uses the exact-event checker suffix.
        if not check_path.exists():
            check_path = TESTS / "logs" / (name.replace("_spr15_c", "_15_c_check").replace("_spr15_h", "_15_h_check") + ".check.json")
        check = read(check_path)
        assert check["passed"]
        if "candidate_evidence" in check:
            verify([check["candidate_evidence"]["run"]])
        s = run
        assert run["spr"] == run["event_grid"] == 1 and run["damping_text"] == "0.04" and run["xi"] == .1
    assert s["dt"] in (1e-5, 5e-6)
    output = TESTS / "outputs" / name
    state = output / "state.csv"
    selected = [entry for entry in run["outputs"] if Path(entry["path"]).resolve() in
                {state.resolve(), (output / "hourglass.csv").resolve(), (output / "complete.json").resolve(),
                 (output / "hourglass_final.csv").resolve()}]
    assert any(Path(e["path"]).resolve() == state.resolve() for e in selected)
    verify(selected)
    return run, s, state, [bound(path)] + selected


def frames(path, settings):
    for i, a in enumerate(pd.read_csv(path, chunksize=1000, float_precision="round_trip")):
        assert len(a) == 1000 and np.array_equal(a.id, SOIL) and a.stage.eq("full_step").all()
        assert a.time_s.nunique() == a.step.nunique() == 1
        assert int(a.step.iloc[0]) == min(i * settings["stride"], settings["steps"])
        assert abs(a.time_s.iloc[0] - a.step.iloc[0] * settings["dt"]) < 1e-7
        assert np.isfinite(a.select_dtypes(include="number").to_numpy()).all()
        assert a.rho.gt(0).all() and a.kplastic.eq(0).all()
        yield a


def measure(a, initial):
    t = float(a.time_s.iloc[0])
    total = (a.sigma_zz - a.pressure).to_numpy().reshape(10, 100).mean(axis=0)
    z = a.z.to_numpy()
    settlement = (initial.z.to_numpy() - z) * 1000
    dx = (a.x.to_numpy() - initial.x.to_numpy() + .05) % .1 - .05
    row = dict(time_s=t, mean_pressure_pa=float(a.pressure.mean()),
               top_settlement_mm=float(settlement[TOP].mean()), bottom_settlement_mm=float(settlement[BOTTOM].mean()),
               total_stress_Q_pa=float(np.sqrt(np.mean(np.diff(total, n=2) ** 2))),
               max_layer_total_error_pa=float(np.max(abs(total + 10000))),
               top_gap_pa=float(abs(total[-1] - total[-2])), load_resultant_N_m=float(.21 * a.load_az.sum()),
               max_abs_dx_mm=float(np.max(abs(dx)) * 1000), max_layer_z_span_mm=float(np.max(np.ptp(z.reshape(10, 100), axis=0)) * 1000))
    checks = dict(no_wall_crossing=bool((z > 0).all()), geometry=row["max_abs_dx_mm"] < .5 and row["max_layer_z_span_mm"] < .5)
    if t >= .1 - 1e-7:
        checks.update(post01_stress=row["max_layer_total_error_pa"] <= 100,
                      post01_top_gap=row["top_gap_pa"] <= 100,
                      post01_load=abs(row["load_resultant_N_m"] + 1000) < .001,
                      post01_drainage=(set(a.id[a.drained.eq(1)]) == set(SOIL[TOP]) and a.pressure.iloc[TOP].eq(0).all()))
    return row, checks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", required=True)
    p.add_argument("--reference", required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--half-gate", action="store_true")
    p.add_argument("--prefix", action="store_true", help="Compare actual matching samples through the shorter trajectory")
    p.add_argument("--exact-fields", action="store_true", help="Require saved physical fields bitwise equal (same backend/dt only)")
    args = p.parse_args()
    receipt, figure, csv = [TESTS / folder / (args.tag + suffix) for folder, suffix in
                            (("logs", ".check.json"), ("figures", ".png"), ("figures", ".csv"))]
    assert not any(f.exists() for f in (receipt, figure, csv))
    candidate, cs, cp, evidence = records(args.candidate)
    reference, rs, rp, re = records(args.reference)
    evidence += re + [bound(__file__)]
    if args.half_gate:
        assert {cs["dt"], rs["dt"]} == {1e-5, 5e-6}
        assert not args.prefix and not args.exact_fields
    if args.exact_fields:
        assert cs["dt"] == rs["dt"]
    limit = min(cs["steps"] * cs["dt"], rs["steps"] * rs["dt"])
    rows, safety = [], {"candidate": {}, "reference": {}}
    initial_a = initial_b = None
    refs = frames(rp, rs)
    b = next(refs)
    exact = True
    for i, a in enumerate(frames(cp, cs)):
        if args.prefix and a.time_s.iloc[0] > limit + 1e-7:
            break
        while b.time_s.iloc[0] < a.time_s.iloc[0] - 1e-7:
            b = next(refs)
        assert abs(a.time_s.iloc[0] - b.time_s.iloc[0]) < 1e-7
        fields = ["x", "y", "z", "vx", "vy", "vz", "rho", "pressure", "kplastic"] + STRESS
        exact = exact and a[fields].to_numpy(dtype="<f8").tobytes() == b[fields].to_numpy(dtype="<f8").tobytes()
        if i == 0:
            initial_a, initial_b = a.copy(), b.copy()
            assert np.array_equal(a[["x", "y", "z", "pressure"] + STRESS].to_numpy(), b[["x", "y", "z", "pressure"] + STRESS].to_numpy())
        ar, ac = measure(a, initial_a)
        br, bc = measure(b, initial_b)
        for label, checks in (("candidate", ac), ("reference", bc)):
            for key, passed in checks.items():
                safety[label][key] = safety[label].get(key, True) and bool(passed)
        delta = a.pressure.to_numpy() - b.pressure.to_numpy()
        row = {"frame": i, **ar, **{k + "_reference": v for k, v in br.items()}}
        row.update(pressure_rms_difference_pa=float(np.sqrt(np.mean(delta ** 2))), pressure_max_difference_pa=float(np.max(abs(delta))),
                   top_settlement_difference_mm=ar["top_settlement_mm"] - br["top_settlement_mm"],
                   bottom_settlement_difference_mm=ar["bottom_settlement_mm"] - br["bottom_settlement_mm"],
                   max_double_stress_difference_pa=float(np.max(abs(a[STRESS].to_numpy() - b[STRESS].to_numpy()))))
        rows.append(row)
    expected = 1 + math.ceil(cs["steps"] / cs["stride"])
    if args.prefix:
        expected = sum(min(i * cs["stride"], cs["steps"]) * cs["dt"] <= limit + 1e-10 for i in range(expected))
    assert len(rows) == expected
    if not args.prefix:
        assert cs["steps"] * cs["dt"] == rs["steps"] * rs["dt"]
        assert abs(b.time_s.iloc[0] - rs["steps"] * rs["dt"]) < 1e-7
    table = pd.DataFrame(rows)
    hg = pd.read_csv(cp.parent / "hourglass.csv", float_precision="round_trip")
    hg = hg.iloc[:len(rows) - 1]
    assert np.array_equal(hg.time_s.to_numpy(), table.time_s.to_numpy()[1:])
    assert np.isfinite(hg.select_dtypes(include="number").to_numpy()).all()
    hg_checks = dict(dt_over_tau=bool(hg.dt_over_tau.between(0, .2).all()),
                     small_rotation=bool(hg.integrated_max_skew_rad.between(0, .01, inclusive="left").all()),
                     work_identity=bool((abs(hg.rate_power + 2 * hg.rate_form) <= 1e-9 * (1 + abs(hg.rate_power) + 2 * hg.rate_form)).all()),
                     natural_dt=bool(candidate["completion"]["max_fixed_dt_minus_mechanical_limit_s"] <= 0))
    half = dict(pressure_rms_max_pa=float(table.pressure_rms_difference_pa.max()),
                top_settlement_abs_max_mm=float(table.top_settlement_difference_mm.abs().max()),
                pressure_limit_pa=5., settlement_limit_mm=.005)
    half["within_limits"] = half["pressure_rms_max_pa"] <= 5 and half["top_settlement_abs_max_mm"] <= .005
    passed = all(all(checks.values()) for checks in safety.values()) and all(hg_checks.values()) and (not args.half_gate or half["within_limits"]) and (not args.exact_fields or exact)
    metrics = ["mean_pressure_pa", "top_settlement_mm", "bottom_settlement_mm", "max_layer_total_error_pa", "top_gap_pa", "total_stress_Q_pa"]
    titles = ["Mean pore pressure (Pa)", "Top material settlement (mm)", "Bottom material settlement (mm)",
              "Largest layer total-stress residual (Pa)", "Top adjacent-layer stress gap (Pa)", "Layer second-difference RMS Q (Pa)"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    for ax, key, title in zip(axes.flat, metrics, titles):
        ax.plot(table.time_s_reference, table[key + "_reference"], color="#34805B", linewidth=1.8, label=args.reference)
        ax.plot(table.time_s, table[key], color="#2263A6", linewidth=1, linestyle="--", label=args.candidate)
        ax.set(title=title, xlabel="Actual time (s)");ax.grid(True, alpha=.3)
    axes[0, 0].legend(fontsize=7, frameon=False)
    fig.suptitle("Case 02 CPU/GPU production-step comparison" if not args.half_gate else "Case 02 GPU coarse/half-step comparison")
    fig.text(.5, .02, "Native material IDs and actual times matched; no interpolation. Safety uses original geometry, loading, drainage and post-0.1-s 100-Pa checks.\n"
             "Q is diagnostic only. Half-step 5-Pa / 0.005-mm limits are applied only when comparing the two GPU timesteps.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .075, 1, .96))
    with figure.open("xb") as stream:
        fig.savefig(stream, dpi=170, facecolor="white")
    plt.close(fig)
    table.to_csv(csv, index=False, mode="x")
    verify(evidence)
    with receipt.open("x", encoding="utf8") as stream:
        json.dump(dict(passed=passed, candidate=args.candidate, reference=args.reference, frames=len(rows),
                       actual_final_time_s=float(table.time_s.iloc[-1]), safety=safety,
                       half_step_gate_applied=args.half_gate, comparison=half, hourglass_checks=hg_checks,
                       prefix_only=args.prefix, exact_physical_fields_required=args.exact_fields, exact_physical_fields=exact,
                       maximum_double_stress_difference_pa=float(table.max_double_stress_difference_pa.max()),
                       figure=bound(figure), metrics=bound(csv), evidence=evidence, physical_acceptance=False,
                       visual_review_pending=True), stream, indent=2)
    print(json.dumps(dict(passed=passed, frames=len(rows), comparison=half, safety=safety), indent=2))
    if not passed:
        raise RuntimeError("Original safety or half-step checks failed; retain results and diagnose")


if __name__ == "__main__":
    main()
