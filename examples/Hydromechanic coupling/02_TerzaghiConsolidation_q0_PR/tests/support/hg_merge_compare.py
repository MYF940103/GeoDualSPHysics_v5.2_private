"""Read-only full-cycle review, not automatic physical acceptance.

--short-test reads the completed 0.1 s production fixture and writes nothing.
The default full review waits for hg_merge_2tv and its upstream 15 s gate.
No solver launch, interpolation, extrapolation, overwrite or gate relaxation.
"""
import argparse
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

import traction_gate as gate
import hourglass_check as hg
import hg_merge_check as merge
import hg_merge_sequence as sequence
from hourglass_compare import LABELS, COLORS, STYLES, RENAME, OLD
from traction_mid_compare import measure
from settlement_audit import previous, theoretical_settlement

TESTS = Path(__file__).resolve().parents[1]
CASE = TESTS.parent
TARGETS = (.1, .2, .4, .5, .7, 1., 1.5, 2.)
LIMITS = dict(geometry_mm_exclusive=.5, post_0_1s_stress_and_top_gap_pa=100,
              dt_over_tau=.2, integrated_spin_rad_exclusive=.01,
              sampled_load_resultant_error_N_m_exclusive=.001)


def metric(key, frame, initial, model, time):
    """Only native material coordinates define layers, settlement and theory."""
    a = frame.set_index("id") if "id" in frame else frame
    a = a.sort_index()
    gate.require(np.array_equal(a.index, gate.SOIL), key+": missing/duplicate soil IDs")
    gate.finite(a, key)
    gate.require(a.rho.gt(0).all(), key+": nonpositive density")
    if "kplastic" in a:
        gate.require(a.kplastic.eq(0).all(), key+": plasticity outside elastic scope")
    r, layer = measure(a, initial, model, .1, time)
    eta = model["n"]*model["M"]/model["Kw"]
    tv = r["tv"]
    p = previous.reference.pressure_theory(layer.z0.to_numpy(), tv, model)
    pf = previous.reference.pressure_theory(layer.z0.to_numpy(), tv/(1+eta), model)/(1+eta)
    classical = float(theoretical_settlement([initial.loc[139, "z"]], time, model)[0])
    if time <= model["tD"]:
        p[:] = pf[:] = np.nan  # Fourier references do not resolve the load ramp.
        classical = np.nan
    r.update(series=key, classical_top_mm=classical,
        profile_rmse_pa=float(np.sqrt(np.mean((layer.pressure-p)**2))),
        profile_finite_kw_rmse_pa=float(np.sqrt(np.mean((layer.pressure-pf)**2))),
        classical_mean_pa=float(p.mean()), finite_kw_mean_pa=float(pf.mean()),
        max_layer_total_error_pa=float((layer.total_zz_pa+model["q0"]).abs().max()),
        total_stress_zigzag_rms_pa=hg.spatial(a)["total_sigma_zz_layer_second_difference_pa"]["rms"])
    r["mean_minus_classical_pa"] = r["mean_p_pa"]-r["classical_mean_pa"]
    r["mean_minus_finite_kw_pa"] = r["mean_p_pa"]-r["finite_kw_mean_pa"]
    r["settlement_minus_classical_mm"] = r["top_settlement_mm"]-classical
    r["transverse_compliance_rms"] = float(np.sqrt(np.mean(
        ((a.sigma_xx-model["nu"]*(a.sigma_yy+a.sigma_zz))/model["E"])**2)))
    layer["classical_pressure_pa"], layer["finite_kw_pressure_pa"] = p, pf
    layer["series"], layer["time_s"], layer["tv"] = key, time, tv
    return r, layer


def candidate_samples(data):
    """Reuse the online thresholds; auxiliary boundary fields are mixed-phase."""
    report = {}
    run = data["run"]
    sampler = sequence.Samples(data["name"], run["dt"], run["steps"], run["stride"], report)
    sampler.initial = data["initial"]
    raw = pd.read_csv(TESTS/f"outputs/{data['name']}/state.csv", float_precision="round_trip")
    for _, frame in raw.groupby("step", sort=True):
        sampler.frame(frame, float(frame.time_s.iloc[0]))
    h = pd.read_csv(TESTS/f"outputs/{data['name']}/hourglass.csv", float_precision="round_trip")
    gate.finite(h, "HG sampled statistics")
    gate.require(h.stage.eq("corrected_endpoint").all() and h.xi.eq(.1).all()
                 and h.dt_s.eq(run["dt"]).all() and h.step.is_unique
                 and set(h.step) == set(raw.step)-{0}, "HG sampled endpoint timeline")
    gate.require(h.dt_over_tau.between(0, .2).all()
                 and h.min_natural_dt_limit_s.ge(run["dt"]).all()
                 and h.integrated_max_skew_rad.between(0, .01, inclusive="left").all(),
                 "HG sampled time-scale/rotation guard")
    return report


def upstream(data, source):
    path = source(TESTS/"logs/hg_merge_gate.check.json")
    review = gate.load(path)
    gate.require(review["full_15s_half_dt_gate_passed"] and review["seconds"] == 15
                 and review["merge_and_requested_checks_passed"], "15 s merge/half-dt gate not passed")
    for path, digest in review["scripts"].items():
        source(path, digest)
    for name, result in review["results"].items():
        runpath = source(TESTS/f"logs/{name}.run.json", result["evidence"]["run_manifest_sha256"])
        run = gate.load(runpath)
        evidence = gate.evidence(name, run)
        if run["completion"]["mode"] == "production_symplectic":
            gate.require(evidence["exe_sha256"] == data["evidence"]["exe_sha256"]
                         and merge.xml_data(run)[1] == data["signature"]
                         and run["hourglass_xi"] == data["xi"], "Full/window binary or physics differs")
    state = gate.load(source(TESTS/"logs/hg_merge_sequence.status.json"))
    gate.require(state["status"] == "completed_2tv_pending_full_physical_review",
                 "Sequence has not completed its gated full-cycle trial")
    return dict(gate_sha256=gate.sha(TESTS/"logs/hg_merge_gate.check.json"),
                half_dt=review["half_dt"], sequence_status=state["status"],
                full_cycle_half_dt_tested=False)


def retained(source, initial):
    """NoHG is a deliberately stopped 55.8 s run, never a completed 2Tv run."""
    run = gate.load(source(TESTS/f"logs/{OLD}.run.json"))
    # Explicit, hash-identical pre-layout snapshot; the historical manifest is
    # never rewritten, and no arbitrary missing-input resolver is introduced.
    oldrunner = TESTS/"logs/layout_before/support/traction_long_run.ps1"
    inputs = []
    for entry in run["inputs"]:
        if Path(entry["path"]).resolve() == (TESTS/"support/traction_long_run.ps1").resolve():
            source(oldrunner, entry["sha256"])
            inputs.append(dict(entry, path=str(oldrunner)))
        else:
            inputs.append(entry)
    evidence = gate.evidence(OLD, dict(run, inputs=inputs))
    evidence["historical_runner_verified_at"] = str(oldrunner)
    stop = gate.load(source(TESTS/f"logs/{OLD}.user_stop.json"))
    gate.require(not stop["full_2tv_completed"] and run["variant"] == "normalized"
                 and run["grad_corr"] == 1 and not run["completion_valid"], "NoHG control identity")
    oldinit = gate.state(source(TESTS/f"outputs/{OLD}/initial_state.csv"))
    gate.require(merge.differences(initial, oldinit)["zero_ulp"], "NoHG initial material state differs")
    raw = pd.read_csv(source(TESTS/f"outputs/{OLD}/state.csv"), float_precision="round_trip")
    gate.require(raw.stage.eq("predictor").all() and not raw.duplicated(["time_s", "id"]).any(),
                 "NoHG trace duplicate IDs or wrong stage")
    frames = [(float(t), g.set_index("id").sort_index()) for t, g in raw.groupby("time_s", sort=True)]
    gate.require(abs(frames[-1][0]-stop["last_reported_time_s"]) < 1e-7, "NoHG stop/time mismatch")
    parent = gate.load(source(TESTS/"logs/traction_p548.check.json"))
    nativepath = TESTS/"outputs/traction_p548_native/state.csv"
    native = pd.read_csv(source(nativepath, parent["source_hashes"][str(nativepath.relative_to(CASE))]),
                         float_precision="round_trip").rename(columns=RENAME)
    maxerr = dict(time_s=0., x=0., z=0., pressure=0., sigma_zz=0.)
    times = np.array([t for t, _ in frames])
    for t, group in native[native.id.isin(gate.SOIL)].groupby("time_s", sort=True):
        i = int(abs(times-t).argmin()); a = frames[i][1]
        b = group.set_index("id").sort_index()
        gate.require(np.array_equal(a.index, b.index) and np.array_equal(b.index, gate.SOIL), "Native NoHG IDs")
        maxerr["time_s"] = max(maxerr["time_s"], float(abs(times[i]-t)))
        for field in ("x", "z", "pressure", "sigma_zz"):
            maxerr[field] = max(maxerr[field], float((a[field]-b[field]).abs().max()))
    gate.require(maxerr["time_s"] < 1e-7 and maxerr["pressure"] == 0
                 and max(maxerr["x"], maxerr["z"]) < 3e-8 and maxerr["sigma_zz"] < .002,
                 "NoHG retained BI4 export/trace mismatch")
    datasets = {"off": (oldinit, frames)}
    oldrecord = gate.load(source(TESTS/"logs/settlement_r1.check.json"))
    for key in ("float", "dt1", "dt05"):
        path = TESTS/f"outputs/settlement_r1_{key}/state.csv"
        a = pd.read_csv(source(path, oldrecord["source_hashes"][str(path.relative_to(CASE))]),
                        float_precision="round_trip").rename(columns=RENAME)
        a = a[a.id.isin(gate.SOIL)]
        gate.require(not a.duplicated(["time_s", "id"]).any(), "Historical native timeline duplicated")
        groups = [(float(t), g.set_index("id").sort_index()) for t, g in a.groupby("time_s", sort=True)]
        gate.require(groups[0][0] == 0 and len(groups) == 401, "Historical initial time/frame count")
        init = groups[0][1]
        gate.require(np.max(abs(init.z-initial.loc[gate.SOIL, "z"])) < 3e-8, "Historical material heights differ")
        datasets[key] = (init, groups)
    return datasets, dict(no_hg_evidence=evidence, no_hg_final_time_s=frames[-1][0],
        no_hg_completed_2tv=False, native_export_verified_to_s=float(native.time_s.max()),
        retained_model=parent["model"],
        no_hg_native_export_vs_trace=maxerr,
        no_hg_last_1s_independent_native_export_verified=False,
        historical_exports_include_kplastic=False)


def plots(history, profiles, chosen, model, paths):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.alpha": .18})
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout="constrained")
    fields = [("mean_p_pa", "Mean excess pore pressure (Pa)"),
              ("top_settlement_mm", "Material settlement at z0=0.995 m (mm)"),
              ("mean_minus_finite_kw_pa", "Mean pressure minus ideal finite-Kw (Pa)"),
              ("top_minus_finite_kw_mm", "Settlement minus ideal finite-Kw (mm)")]
    for ax, (field, title) in zip(axes.flat, fields):
        for key in LABELS:
            a = history[(history.series == key) & (history.time_s > model["tD"])]
            ax.plot(a.tv, a[field], STYLES[key], color=COLORS[key], label=LABELS[key], lw=1.6)
        ax.set(xlabel="Tv from actual time", ylabel=title, xlim=(0, 2.01))
    h = history[(history.series == "hg") & (history.time_s > model["tD"])]
    for ax, classical, finite in ((axes[0, 0], "classical_mean_pa", "finite_kw_mean_pa"),
                                  (axes[0, 1], "classical_top_mm", "ideal_finite_kw_top_mm")):
        ax.plot(h.tv, h[classical], "k--", lw=1.1, label="Classical analytical reference")
        ax.plot(h.tv, h[finite], "k:", lw=1.4, label="Ideal finite-Kw reference")
    for ax in axes[1]: ax.axhline(0, color="black", lw=.7)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=3, fontsize=9)
    fig.suptitle("Full-cycle pressure and material settlement | NoHG stops at 55.8 s\nHistorical single-layer curves are not HG-only controls")
    fig.savefig(paths["history_png"], dpi=180);plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 7), layout="constrained")
    colors = plt.get_cmap("viridis")(np.linspace(.08, .9, len(TARGETS)))
    for target, color in zip(TARGETS, colors):
        item = chosen[(chosen.series == "hg") & chosen.target_tv.eq(target)].iloc[0]
        p = profiles[(profiles.series == "hg") & profiles.time_s.eq(item.time_s)]
        label = f"Tv {p.tv.iloc[0]:.4f} ({item.time_s:.5f} s)"
        axes[0].plot(p.pressure/model["q0"], p.z0/model["H"], color=color, label=label, lw=1.6)
        axes[0].plot(p.classical_pressure_pa/model["q0"], p.z0/model["H"], "--", color=color, lw=.9)
        axes[0].plot(p.finite_kw_pressure_pa/model["q0"], p.z0/model["H"], ":", color=color, lw=1.1)
        axes[1].plot(p.pressure-p.finite_kw_pressure_pa, p.z0/model["H"], color=color)
    axes[0].set(xlabel="Excess pore pressure / q0", ylabel="Initial material height z0/H", ylim=(0, 1))
    axes[1].set(title="Numerical minus ideal finite-Kw reference", xlabel="Pressure error (Pa)",
                ylabel="Initial material height z0/H", ylim=(0, 1))
    axes[1].axvline(0, color="black", lw=.7)
    axes[0].legend(fontsize=8, loc="upper right")
    fig.legend([Line2D([], [], color="black", linestyle=s) for s in ("-", "--", ":")],
               ["Left: numerical", "Left: classical", "Left: ideal finite Kw"],
               loc="outside lower center", ncol=3, fontsize=9)
    fig.suptitle("Production HG xi=0.1: all requested pressure profiles in one figure\nReferences evaluated at each actual saved time; no time interpolation")
    fig.savefig(paths["profiles_png"], dpi=180);plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), layout="constrained")
    fields = [("max_layer_total_error_pa", "Max layer Cauchy total-stress error (Pa)"),
        ("top_pair_total_gap_pa", "Top adjacent-layer total-stress gap (Pa)"),
        ("total_stress_zigzag_rms_pa", "Interior layer second-difference RMS (Pa)"),
        ("max_abs_dx_mm", "Max periodic lateral displacement (mm)"),
        ("max_within_layer_z_span_mm", "Max within-layer vertical span (mm)"),
        ("transverse_compliance_rms", "Transverse elastic-compliance RMS (dimensionless)")]
    for ax, (field, title) in zip(axes.flat, fields):
        for key in LABELS:
            a = history[(history.series == key) & (history.time_s >= .1-1e-7)]
            ax.plot(a.tv, a[field], STYLES[key], color=COLORS[key], label=LABELS[key])
        ax.set(xlabel="Tv from actual time", ylabel=title, xlim=(0, 2.01))
        if field in ("max_abs_dx_mm", "max_within_layer_z_span_mm"):
            ax.set_yscale("symlog", linthresh=1e-5)
            ax.set_ylim(bottom=0)
            ax.text(.03, .96, "symlog; linear below 1e-5 mm", transform=ax.transAxes,
                    va="top", fontsize=8)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=3, fontsize=9)
    fig.suptitle("Stress balance and particle staggering | Cauchy stress excludes HG force\nSecond differences include physical curvature; compliance is not accumulated strain")
    fig.savefig(paths["mechanics_png"], dpi=180);plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=merge.label, default="hg_merge_2tv")
    parser.add_argument("--tag", type=merge.label, default="hg_merge_full_r1")
    parser.add_argument("--short-test", action="store_true")
    args = parser.parse_args()
    name = "hg_merge_short_x01" if args.short_test else args.candidate
    paths = {**{n+"_png": TESTS/f"figures/{args.tag}_{n}.png" for n in ("history", "profiles", "mechanics")},
             **{n: TESTS/f"figures/{args.tag}_{n}.csv" for n in ("history", "profiles", "comparison")}}
    record = TESTS/f"logs/{args.tag}.check.json"
    if not args.short_test:
        gate.require(not any(p.exists() for p in [record, *paths.values()]), "Refusing overwrite")
    if not (TESTS/f"logs/{name}.run.json").exists():
        print(json.dumps(dict(status="pending_no_completed_run", label=name)));return 2
    sources = {}
    def source(path, expected=None):
        path = Path(path);digest = gate.sha(path)
        gate.require(expected is None or digest.lower() == expected.lower(), "Hash mismatch: "+str(path))
        sources[str(path)] = digest
        return path
    data = merge.read_run(name, .1 if args.short_test else gate.GRID_END)
    gate.require(data["native"] and data["xi"] == .1 and data["run"]["top_load_mode"] == 5,
                 "Expected production normalized top load and HG xi=0.1")
    checks = dict(candidate=merge.summary(data), sampled_guards=candidate_samples(data))
    r, layer = metric("hg", data["frames"][-1][1], data["initial"], data["model"], data["frames"][-1][0])
    if args.short_test:
        print(json.dumps(dict(status="short_read_only_self_test_passed", final_time_s=r["time_s"],
            native_ids=1000, layers=len(layer), endpoint_rate_passed=data["endpoint_rate"]["rate_check_passed"],
            full_cycle_review=False, files_written=False, solver_launched=False), indent=2));return 0
    checks["upstream"] = upstream(data, source)
    datasets, checks["retained"] = retained(source, data["initial"])
    gate.require(checks["retained"]["retained_model"] == {k: v for k, v in data["model"].items() if k != "dt"},
                 "Retained analytical material model differs")
    datasets["hg"] = (data["initial"], data["frames"])
    history_rows, all_layers = [], []
    for key, (initial, frames) in datasets.items():
        for time, frame in frames:
            r, layer = metric(key, frame, initial, data["model"], time)
            history_rows.append(r);all_layers.append(layer)
    history, profiles = pd.DataFrame(history_rows), pd.concat(all_layers, ignore_index=True)
    comparison = []
    for key in LABELS:
        h = history[history.series == key]
        for target in TARGETS:
            desired = data["model"]["tD"]+target*data["model"]["H"]**2/data["model"]["cv"]
            # Older 2Tv-tagged runs end 0.01 s earlier by their convention.
            # Permit nearest saved endpoints within half a sampling interval,
            # always expose the actual time/Tv; never extend their curves.
            if desired > h.time_s.max()+float(h.time_s.diff().median())/2: continue
            row = h.loc[(h.time_s-desired).abs().idxmin()].to_dict()
            comparison.append(dict(target_tv=target, requested_time_s=desired,
                                   saved_time_offset_s=row["time_s"]-desired, **row))
    chosen = pd.DataFrame(comparison)
    same_time = pd.merge_asof(history[history.series == "hg"].sort_values("time_s"),
        history[history.series == "off"].sort_values("time_s"), on="time_s", tolerance=1e-7,
        direction="nearest", suffixes=("_hg", "_off")).dropna(subset=["series_off"])
    fields = ("profile_rmse_pa", "profile_finite_kw_rmse_pa", "top_minus_finite_kw_mm",
              "max_layer_total_error_pa", "total_stress_zigzag_rms_pa", "max_abs_dx_mm",
              "max_within_layer_z_span_mm")
    comparisons = []
    for target in TARGETS:
        if target > same_time.tv_hg.max(): continue
        row = same_time.loc[(same_time.tv_hg-target).abs().idxmin()]
        result = dict(target_tv=target, actual_time_s=float(row.time_s), actual_tv=float(row.tv_hg))
        for field in fields:
            a, b = float(row[field+"_hg"]), float(row[field+"_off"])
            result[field] = dict(hg=a, no_hg=b, absolute_error_reduction_pct=100*(1-abs(a)/abs(b)) if b else None)
        comparisons.append(result)
    for path in (Path(__file__), Path(gate.__file__), Path(hg.__file__), Path(merge.__file__),
                 Path(sequence.__file__), Path(previous.__file__), Path(previous.reference.__file__),
                 Path(sys.modules["hourglass_compare"].__file__),
                 Path(inspect.getsourcefile(measure)), Path(inspect.getsourcefile(theoretical_settlement))):
        source(path)
    source(TESTS/f"logs/{name}.run.json")
    history.to_csv(paths["history"], index=False, mode="x")
    profiles.to_csv(paths["profiles"], index=False, mode="x")
    chosen.to_csv(paths["comparison"], index=False, mode="x")
    plots(history, profiles, chosen, data["model"], paths)
    post = history[(history.series == "hg") & history.tv.ge(1)]
    report = dict(status="full_cycle_comparison_ready_for_physical_review", checked_utc=datetime.now(timezone.utc).isoformat(),
        candidate=name, model=data["model"], checks=checks, thresholds=LIMITS, source_hashes=sources,
        comparison=json.loads(chosen.to_json(orient="records", double_precision=15)),
        hg_vs_nohg_same_actual_time=comparisons,
        late_cycle=dict(first_saved_tv=float(post.tv.iloc[0]), last_saved_tv=float(post.tv.iloc[-1]),
            first_mean_pressure_pa=float(post.mean_p_pa.iloc[0]), last_mean_pressure_pa=float(post.mean_p_pa.iloc[-1]),
            remaining_mean_pressure_ratio=float(post.mean_p_pa.iloc[-1]/post.mean_p_pa.iloc[0]),
            ideal_finite_kw_remaining_ratio=float(post.finite_kw_mean_pa.iloc[-1]/post.finite_kw_mean_pa.iloc[0]),
            max_profile_finite_kw_rmse_pa=float(post.profile_finite_kw_rmse_pa.max())),
        full_run_completion_verified=True, upstream_15s_half_dt_verified=True,
        full_2tv_half_dt_verified=False, physical_accuracy_accepted=False, all_cases_accepted=False,
        figures_visually_reviewed=False, solver_launched=False,
        limitations=["NoHG stopped at 55.8 s; no interpolation/extrapolation to 2Tv. BI4 export independently checks only through 54.8 s.",
            "Old float/double single-layer runs differ in load/gradient configuration: not HG-only controls.",
            "Historical native exports do not contain kplastic; candidate and NoHG trace elasticity are checked, historical elasticity is not independently proved here.",
            "Material settlement uses native IDs at initial z0=0.995 m, not a free-surface height or a PART index.",
            "Theory uses initial material coordinates and actual saved time; classical/finite-Kw solutions idealize loading and drainage, unlike the dynamic ramp.",
            "Analytical mean pressure is the mean at the same 100 material-layer heights, not a separate continuous-volume integral.",
            "Analytical cv retains g=9.81; the solver Darcy fallback is 9.80665, a known reference mismatch.",
            "Cauchy stress balance excludes HG force; layer second differences include physical curvature; inverse compliance is not accumulated strain.",
            "Boundary fields are last-corrector or SaveData diagnostics; sampled guards are not every-stage boundary proof.",
            "Only the 15 s interval has a half-dt test; no complete-cycle dt convergence or finite-rotation objectivity proof.",
            "Physical acceptance requires visual inspection and a quantified scientific conclusion; this script never accepts all cases."],
        artifacts={str(p): gate.sha(p) for p in paths.values()})
    with record.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False);stream.write("\n")
    print(json.dumps(dict(status=report["status"], record=str(record)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
