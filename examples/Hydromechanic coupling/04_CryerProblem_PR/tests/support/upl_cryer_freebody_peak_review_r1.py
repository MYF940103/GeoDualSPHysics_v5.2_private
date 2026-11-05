"""Offline peak-window review from completed native CSVs; never runs a decoder/solver."""
from pathlib import Path
import json, os, struct, sys
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"): os.environ[key] = "1"
T = Path(__file__).resolve().parents[1]
C, TAG, RUN = T.parent, "upl_cryer_freebody_peak_review_r1", "upl_cryer_freebody_peak_GPU_r1"
N, TOTAL, SOIL, DT, TD, TAUMAX, R, Q = 577, 37181, 37173, 2.**-20, 2.**-7, .0625, .05, 10000.
LIMIT = ("Unfitted finite-Kw, nominal n=.3, r0/a=.05 quasistatic companion; ramp/inertia/discrete-surface effects omitted.\n"
         "Retained u-pw has a historical program-identity gap. Own saved times, no interpolation or isolated A/B/5Pa claim.")

def need(ok, why):
    if not ok: raise RuntimeError(why)
def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)
def read(path): return json.loads(path.read_text(encoding="utf-8-sig"))
def prefix(old, new, header, width, rows, oldheader, newheader):
    need(old.stat().st_size == header + oldheader[0]*width and new.stat().st_size == header + newheader[0]*width, "Binary length differs")
    with old.open("rb") as a, new.open("rb") as b:
        fmt = "<" + "I"*(header//4)
        need(struct.unpack(fmt, a.read(header)) == oldheader[1] and struct.unpack(fmt, b.read(header)) == newheader[1], "Honest binary header differs")
        remaining = rows*width
        while remaining:
            count = min(2**20, remaining); left, right = a.read(count), b.read(count)
            need(len(left) == count and left == right, "First69 binary data records differ: " + old.name); remaining -= count
    return dict(old_header=list(oldheader[1]), new_header=list(newheader[1]), compared_records=rows, compared_payload_bytes=rows*width, exact=True, headers_rewritten=False)

def main():
    import numpy as np
    import pandas as pd
    from scipy.optimize import minimize_scalar
    sys.path.insert(0, str(C / "support"))
    from plot_cryer_formal_four_nu_r1 import Reference
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    native, short = T / "outputs" / (RUN + "_native"), T / "outputs/upl_cryer_freebody_short_GPU_r1_native"
    formal = C / "figures/formal_validation"
    oldpath, oldcenter = formal / "cryer_formal_four_nu_r1_nu030_summary.csv", formal / "cryer_formal_four_nu_r1_nu030_center18.csv"
    closedpath, oldcheck = T / "logs/upl_cryer_freebody_review_r1.check.json", T / "logs/cryer_formal_four_nu_r1_nu030.native.check.json"
    runpath, callpath = T / "logs" / (RUN + ".run.json"), T / "logs" / (RUN + ".call.json")
    contractpath, referencepath = T / "notes/upl_cryer_comparison_contract_r1.json", C / "support/plot_cryer_formal_four_nu_r1.py"
    leaves = ("completion.json", "summary.csv", "center18.csv", "native_ids.csv", "columns.csv", "common26.bin", "clock.bin")
    sources = [d / leaf for d in (native, short) for leaf in leaves] + [oldpath, oldcenter, closedpath, oldcheck, runpath, callpath, contractpath, referencepath,
               T / "support/upl_cryer_public_native_r2.cpp", Path(__file__), T / "notes" / (TAG + ".json")]
    before = [stat(path) for path in sources]
    outputs = {name: T / "figures" / (TAG + "_" + name) for name in ("history.csv", "center18.csv", "reference.csv", "metrics.csv", "pressure.png", "state.png")}
    check = T / "logs" / (TAG + ".check.json")
    need(not any(path.exists() for path in [*outputs.values(), check]), "Fresh outputs only; no overwrite/retry")
    done, prior, closed, oldreceipt, run, call = [read(path) for path in (native / "completion.json", short / "completion.json", closedpath, oldcheck, runpath, callpath)]
    expected = dict(stage="upl_cryer_public_native_r2", passed=True, declared_backend="GPU", window="peak_73728", samples=N, completed_steps=73728,
                    actual_end_s=.0703125, dt_s=DT, drainage_s=TD, total_native_ids=TOTAL, soil_ids=SOIL, fixed_ids=8, center_material_ids=18,
                    native_typed_arrays=22, soil_ledger_checks=SOIL*N, fixed_marker_checks=8*N, post_open_frames=512, noninitial_signed_dterror_intervals=576)
    need(all(done[k] == value for k, value in expected.items()) and done["post_open_FS23_zero_pressure_checks"] > 0 and done["max_radius_m"] <= .0525,
         "Completed577-frame r2 native safety/schema coverage required")
    need(all(done[k] is True for k in ("common26_all_native_ids", "common26_col21_actual_ExcessPorePress", "FSNormal_finite_not_cross_backend_identity_gate", "signed_dterror_is_original_necessary_step_guard")) and done["physical_acceptance"] is False, "Native interpretation differs")
    need(prior["passed"] and prior["samples"] == 69 and prior["completed_steps"] == 8704 and closed["passed"] and closed["all_five_closed_diagnostics_passed"] and closed["bindings_metadata_unchanged"], "Sealed original69/closed-five results required")
    need([row["part"] for row in closed["closed"]] == [61, 62, 63, 64] and all(row["all_five_original_diagnostics_passed"] for row in closed["closed"]), "Original closed diagnostics not passed")
    for item in closed["sources"] + closed["files"]:
        need(stat(item["path"]) == item, "Sealed69 review metadata changed")
        if Path(item["path"]) not in sources: sources.append(Path(item["path"])); before.append(item)
    need(oldreceipt["passed"] and oldreceipt["nu"] == .3 and oldreceipt["actual_saved_frames"] == 1065, "Retained old nu.3 native receipt missing")
    need(run["passed"] and run["actual_owned_exit"] == 0 and run["source_input_program_stats_unchanged"] and int(run["Run_csv"]["Steps"]) == 73728 and int(run["Run_csv"]["PartFiles"]) == N and call["direct_exit_captured"] and call["exit_code"] == 0, "Original owned peak run/call required")
    exact = dict(common26=prefix(short / "common26.bin", native / "common26.bin", 12, 8+TOTAL*26*8, 69, (69, (TOTAL,26,69)), (N, (TOTAL,26,N))),
                 clock=prefix(short / "clock.bin", native / "clock.bin", 8, 28, 69, (69, (69,28)), (N, (N,28))))
    for leaf in ("native_ids.csv", "columns.csv"): need((short / leaf).read_bytes() == (native / leaf).read_bytes(), "Original initial-ID/column ledger differs")
    load = lambda path: pd.read_csv(path, float_precision="round_trip")
    data, centers, old, oc = load(native / "summary.csv"), load(native / "center18.csv"), load(oldpath), load(oldcenter)
    time = np.arange(N)*128*DT; ids = read(contractpath)["observation"]["fixed_initial_material_IDs"]
    need(len(data) == N and len(centers) == N*18 and len(ids) == 18 and np.isfinite(data.to_numpy(dtype=float)).all() and np.array_equal(data.part, np.arange(N)) and np.array_equal(data.time_s, time), "Complete actual peak summaries required")
    clocktype = np.dtype([("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")])
    with (native / "clock.bin").open("rb") as stream: stream.seek(8); actual = np.frombuffer(stream.read(), dtype=clocktype)
    need(np.array_equal(actual["time"], time) and np.array_equal(actual["step"], np.maximum(np.arange(N)*128-1,0)) and np.all(actual["dt"] == DT) and np.isfinite(actual["error"]).all() and np.all(actual["error"] <= 1e-14) and np.all(actual["error"][1:] != -np.finfo(float).max) and np.array_equal(actual["error"], data.signed_dterror_s), "Actual signed clock payload differs")
    need(np.array_equal(centers.part, np.repeat(np.arange(N),18)) and np.array_equal(centers.id, np.tile(ids,N)) and np.array_equal(centers.time_s, np.repeat(time,18)), "Fixed18 per-frame IDs/times differ")
    first = centers.iloc[:18]; need(np.max(abs(first.r0_m-.0025)) < 1e-15 and np.array_equal(centers[["x0","y0","z0"]], np.tile(first[["x0","y0","z0"]], (N,1))), "Initial material points changed")
    oldfirst = oc[oc.part == 0].sort_values("id"); need(oldfirst.id.tolist() == ids and np.array_equal(oldfirst[["x0","y0","z0"]], first[["x0","y0","z0"]]), "Old/new initial material observation differs")
    pressures = centers.PorePress.to_numpy().reshape(N,18); scale = max(1.,float(abs(pressures).max()))
    need(np.max(abs(pressures.mean(axis=1)-data.center_pressure_Pa)) <= 64*np.finfo(float).eps*scale, "Center mean/individual association failed")
    need(np.array_equal(data.post_open, time > TD) and data.loc[time > TD,"surface_pressure_absmax_Pa"].eq(0).all() and data.loc[time > TD,"activeDrainCount"].gt(0).all(), "Actual strict post-open drainage differs")
    # Only summary/center tables feed analysis; no read of the remaining4GB field.
    old = old[(old.time_s >= 0) & (old.time_s <= TD+TAUMAX)].copy()
    ref = Reference(.3)  # Exact retained nominal-n=.3 model, one construction.
    frames = []
    for label, source, pressure in (("current_upl_GPU", data, "center_pressure_Pa"), ("retained_upw_nu030", old, "center_pressure_pa")):
        frame = source.copy(); frame["series"] = label; frame["native_fixed18_pressure_Pa"] = frame[pressure]
        frame["tau_s"] = frame.time_s-TD; frame["legacy_Tv"] = ref.legacy_cv*frame.tau_s/R**2; frame["finite_storage_theta"] = ref.cv*frame.tau_s/R**2
        frame["finite_Kw_fixed_radius_reference_Pa"] = ref.pressure(frame.tau_s.to_numpy(), radius=.0025)
        frame["native_minus_same_time_reference_Pa"] = frame.native_fixed18_pressure_Pa-frame.finite_Kw_fixed_radius_reference_Pa
        frame["shown_on_log_axis"] = frame.tau_s > 0; frame["Mandel_metric_window"] = (frame.legacy_Tv >= .005) & (frame.tau_s <= TAUMAX)
        frames.append(frame)
    scan = np.geomspace(.005,.5,400); scan_tau = scan*R**2/ref.legacy_cv; k = int(ref.pressure(scan_tau).argmax()); need(0 < k < len(scan)-1, "Reference peak not bracketed")
    opt = minimize_scalar(lambda tau: -float(ref.pressure([tau], radius=.0025)[0]), bounds=(scan_tau[k-1],scan_tau[k+1]), method="bounded", options={"xatol":1e-14}); need(opt.success, "Reference maximum optimization failed")
    pt, pp = float(opt.x), float(-opt.fun); metrics = []
    for frame in frames:
        selected = frame[frame.Mandel_metric_window]; need(len(selected) > 1, "Declared Mandel window empty")
        p = selected.loc[selected.native_fixed18_pressure_Pa.idxmax()]; sampled = selected.loc[selected.finite_Kw_fixed_radius_reference_Pa.idxmax()]
        positive = frame[frame.tau_s > 0]; burst = positive.loc[positive.native_fixed18_pressure_Pa.idxmax()]; errors = selected.native_minus_same_time_reference_Pa.to_numpy()
        metrics.append(dict(series=frame.series.iloc[0], retained_rows=len(frame), post_open_rows=len(positive), Mandel_window_rows=len(selected), declared_tau_max_s=TAUMAX,
            actual_metric_tau_min_s=float(selected.tau_s.min()), actual_metric_tau_max_s=float(selected.tau_s.max()), native_sampled_peak_part=int(p.part), native_sampled_peak_Pa=float(p.native_fixed18_pressure_Pa), native_sampled_peak_tau_s=float(p.tau_s), native_sampled_peak_Tv=float(p.legacy_Tv),
            reference_continuous_peak_Pa=pp, reference_continuous_peak_tau_s=pt, reference_continuous_peak_within_declared_window=pt <= TAUMAX,
            native_peak_amplitude_error_percent_of_reference_peak=100*(p.native_fixed18_pressure_Pa/pp-1), native_peak_difference_over_q0_percent=100*(p.native_fixed18_pressure_Pa-pp)/Q,
            native_peak_time_error_percent=100*(p.tau_s/pt-1), reference_own_sampled_peak_part=int(sampled.part), reference_own_sampled_peak_Pa=float(sampled.finite_Kw_fixed_radius_reference_Pa), reference_own_sampled_peak_tau_s=float(sampled.tau_s),
            reference_sampling_peak_loss_Pa=pp-float(sampled.finite_Kw_fixed_radius_reference_Pa), reference_sampling_peak_loss_percent=100*(1-float(sampled.finite_Kw_fixed_radius_reference_Pa)/pp), reference_sampled_peak_tau_minus_continuous_s=float(sampled.tau_s)-pt,
            native_minus_reference_own_sampled_peak_Pa=float(p.native_fixed18_pressure_Pa-sampled.finite_Kw_fixed_radius_reference_Pa), native_peak_tau_minus_reference_sampled_peak_s=float(p.tau_s-sampled.tau_s),
            own_saved_time_window_RMS_Pa=float(np.sqrt(np.mean(errors**2))), own_saved_time_window_RMS_over_q0_percent=float(np.sqrt(np.mean(errors**2)))/Q*100, own_window_max_abs_error_Pa=float(abs(errors).max()),
            native_peak_at_metric_edge=bool(p.part in (selected.part.iloc[0],selected.part.iloc[-1])), all_positive_tau_sampled_max_Pa=float(burst.native_fixed18_pressure_Pa), all_positive_tau_sampled_max_tau_s=float(burst.tau_s)))
    history = pd.concat(frames, ignore_index=True); centers = centers.copy(); centers["finite_Kw_fixed_radius_reference_Pa"] = np.repeat(frames[0].finite_Kw_fixed_radius_reference_Pa.to_numpy(),18)
    centers["native_minus_same_time_reference_Pa"] = centers.PorePress-centers.finite_Kw_fixed_radius_reference_Pa
    low = min(float(frame.loc[frame.tau_s > 0,"legacy_Tv"].min()) for frame in frames); high = ref.legacy_cv*TAUMAX/R**2
    tv = np.geomspace(low,high,700); theory = pd.DataFrame(dict(legacy_Tv=tv,tau_s=tv*R**2/ref.legacy_cv)); theory["finite_Kw_r0_over_a_005_Pa"] = ref.pressure(theory.tau_s.to_numpy(),radius=.0025)
    for name, frame in (("history.csv",history),("center18.csv",centers),("reference.csv",theory),("metrics.csv",pd.DataFrame(metrics))):
        with outputs[name].open("x",newline="",encoding="utf-8") as stream: frame.to_csv(stream,index=False,float_format="%.17g")
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    colors, markers = ("#1764a0","#df7f21"), ("o","s")
    fig, axes = plt.subplots(1,2,figsize=(14,6.5),constrained_layout=True)
    for ax in axes:
        ax.plot(theory.legacy_Tv,theory.finite_Kw_r0_over_a_005_Pa/Q,color="black",lw=1.4,label="Finite-Kw, fixed r0/a=.05")
        for frame,color,marker in zip(frames,colors,markers):
            shown = frame[frame.shown_on_log_axis]; ax.plot(shown.legacy_Tv,shown.native_fixed18_pressure_Pa/Q,color=color,ls="none",marker=marker,markevery=8 if len(shown)>100 else 2,ms=4,mfc="none",label=frame.series.iloc[0]+" / own times")
        ax.set(xscale="log",xlabel="Own actual legacy Tv",ylabel="Fixed18 pressure / q0"); ax.grid(which="both",alpha=.22); ax.legend(fontsize=8)
    axes[0].set(xlim=(low*.95,high*1.03),title="All positive-tau samples in this peak window")
    axes[1].set(xlim=(ref.legacy_cv*.02/R**2,high*1.03),title="Near-peak view only: tau >= .02 s")
    fig.suptitle("Cryer peak diagnostic through tau=.0625 s; all startup records remain in CSV/state plot\n"+LIMIT,fontsize=10)
    with outputs["pressure.png"].open("xb") as stream: fig.savefig(stream,format="png",dpi=160)
    plt.close(fig); fig, axes = plt.subplots(4,2,figsize=(13,13),constrained_layout=True)
    u, w = frames
    for frame,color,label in zip(frames,colors,("current u-pl","retained u-pw / own times")):
        axes[0,0].plot(frame.time_s,frame.native_fixed18_pressure_Pa,color=color,label=label)
        for ax,newkey,oldkey in ((axes[0,1],"shell_inward_initial_V_mm","shell_inward_mm"),(axes[2,0],"total_mean_compression_initial_V_Pa","total_mean_compression_pa"),(axes[2,1],"speed_max_m_s","speed_max_m_s")):
            ax.plot(frame.time_s,frame[newkey if label=="current u-pl" else oldkey],color=color,label=label)
        axes[3,0].plot(frame.loc[frame.part>0,"time_s"],frame.loc[frame.part>0,"signed_dterror_s" if label=="current u-pl" else "dterror_s"],color=color,label=label)
    for ax,keys in ((axes[1,0],("J_min","J_initial_V_mean","J_max")),(axes[1,1],("n_min","n_initial_V_mean","n_max")),(axes[3,1],("FS2_count","FS3_count","activeDrainCount"))):
        for key in keys: ax.plot(u.time_s,u[key],label=key)
    axes[2,0].plot(u.time_s,u.effective_mean_compression_initial_V_Pa,ls="--",label="current effective mean")
    axes[3,0].axhline(1e-14,color="red",lw=.8,ls="--",label="Original signed ceiling")
    titles = ("Complete startup + peak fixed18 pressure (Pa)","Native initial-material shell motion (mm), no shell theory", "Native J (current u-pl)","Native porosity (current u-pl)","Native mean compression (Pa), no post-drain uniform gate", "Native maximum speed (m/s)","Noninitial signed dterror (s), not absolute error", "Actual free surface / drainage counts")
    for ax,title in zip(axes.flat,titles):
        ax.set(xlabel="Actual saved time (s)",title=title); ax.axvline(TD,color="black",ls=":",lw=.8); ax.axvline(2.**-8,color="gray",ls=":",lw=.8); ax.grid(alpha=.2); ax.legend(fontsize=7)
    fig.suptitle("Complete native startup/state; lines mark ramp end and drainage event\n"+LIMIT,fontsize=10)
    with outputs["state.png"].open("xb") as stream: fig.savefig(stream,format="png",dpi=160)
    plt.close(fig)
    need([stat(path) for path in sources] == before, "Consumed closed metadata changed")
    result = dict(stage=TAG,passed=True,offline_analysis_completed=True,sources=before,files=[stat(path) for path in outputs.values()],prefix69_payloads=exact,
        inherited_closed_five=dict(source=stat(closedpath),parts=[61,62,63,64],all_original_diagnostics_passed=True,recomputed=False),metrics=metrics,
        reference=dict(nominal_n=.3,finite_Kw=2e8,r0_m=.0025,a_m=R,modes=360,legacy_cv=ref.legacy_cv,finite_cv=ref.cv,continuous_peak_Pa=pp,continuous_peak_tau_s=pt,scan_Tv=[.005,.5]),
        old_full_RMS_compared_to_new_window=False,SPH_peak_interpolated=False,no_radius_time_load_fit=True,old_program_identity_gap_retained=True,approximate_user_one_percent_scope_not_new_gate=True,
        full_field_read_scope="Only first69 common26 data records and69 clock records for exact prefix; remaining field not scanned",bindings_metadata_unchanged=True,fresh_hashes_performed=0,
        original_closed_diagnostics_recomputed=False,solver_or_decoder_or_reference_selftest_invoked=False,force_stage_budget_claimed=False,physical_acceptance=False,automatic_next_action=False)
    with check.open("x",encoding="utf-8") as stream: json.dump(result,stream,indent=2,allow_nan=False); stream.write("\n")
    print(json.dumps(dict(offline_review_completed=True,check=str(check))))

if __name__ == "__main__": main()
