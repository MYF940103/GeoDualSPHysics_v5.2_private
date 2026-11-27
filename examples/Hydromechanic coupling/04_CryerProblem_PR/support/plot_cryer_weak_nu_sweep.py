"""Compare reviewed weak Cryer nu sweeps without reading native particle files.

Use each model's own analytical reference. Numerical samples remain discrete;
exact-time tail pairs are never obtained by rounding or interpolation. This
script writes a new aggregate directory and does not change per-case results.
"""
import argparse
import os
from pathlib import Path

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_name] = "1"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from plot_cryer_formal_four_nu_r1 import Reference
from plot_cryer_weak_full import binding, need, read_csv, read_json, write_json

CASE = Path(__file__).resolve().parents[1]
FORMAL = CASE / "figures/formal_validation"
GROUPS = {"010": .1, "020": .2, "030": .3, "045": .45}
COLORS = {"010": "#b45f27", "020": "#4d842c", "030": "#147c9b", "045": "#965394"}
R, Q = .05, 10000.
PEAK_START_TV, PEAK_END_TV = .005, .12


def surface_theory(ref, tau):
    tau = np.asarray(tau, dtype=float)
    result = np.full(tau.shape, np.nan)
    positive = tau > 0
    mean = Q * ((ref.mean * ref.amplitude) @ np.exp(-ref.decay[:, None] * tau[positive]))
    result[positive] = 1000 * R * (Q - mean) / (3 * ref.K)
    result[tau == 0] = 0.
    return result


def continuous_peak(ref):
    # Optimise in Tv, then convert to the actual seconds used by this reference.
    result = minimize_scalar(
        lambda tv: -float(ref.pressure(tv * R**2 / ref.legacy_cv)[0]),
        bounds=(PEAK_START_TV, PEAK_END_TV), method="bounded", options={"xatol": 1e-14})
    need(result.success and PEAK_START_TV < result.x < PEAK_END_TV,
         "Analytical peak is not inside the scoring window")
    return dict(Pa=-float(result.fun), tau_s=float(result.x * R**2 / ref.legacy_cv),
                Tv=float(result.x))


def error_stats(values):
    values = np.asarray(values, dtype=float)
    if not len(values):
        return dict(samples=0, rms_Pa=None, max_abs_Pa=None, endpoint_error_Pa=None)
    return dict(samples=len(values), rms_Pa=float(np.sqrt(np.mean(values**2))),
                max_abs_Pa=float(np.max(np.abs(values))), endpoint_error_Pa=float(values[-1]))


def peak_score(frame, ref):
    peak = continuous_peak(ref)
    valid = frame[(frame.Tv >= PEAK_START_TV) & (frame.Tv <= PEAK_END_TV)].sort_values("tau_s")
    need(len(valid) >= 3 and valid.tau_s.is_unique, "At least three unique peak samples are needed")
    row = valid.iloc[int(np.argmax(valid.center_Pa.to_numpy()))]
    gap = float(np.diff(valid.tau_s).max())
    amplitude = 100 * (float(row.center_Pa) / peak["Pa"] - 1)
    phase = 100 * (float(row.tau_s) / peak["tau_s"] - 1)
    covered = float(valid.tau_s.iloc[0]) < peak["tau_s"] < float(valid.tau_s.iloc[-1])
    gates = dict(analytical_peak_bracketed=covered,
                 sampled_peak_interior=int(row.name) not in (int(valid.index[0]), int(valid.index[-1])),
                 dense_sampling=gap <= .01 * peak["tau_s"],
                 amplitude_within_1pct=abs(amplitude) <= 1.,
                 timing_within_2pct=abs(phase) <= 2.)
    result = dict(first_Tv=float(valid.Tv.iloc[0]), last_Tv=float(valid.Tv.iloc[-1]),
                  theoretical_peak_Pa=peak["Pa"], theoretical_peak_tau_s=peak["tau_s"],
                  theoretical_peak_Tv=peak["Tv"], sampled_peak_Pa=float(row.center_Pa),
                  sampled_peak_time_s=float(row.time_s), sampled_peak_tau_s=float(row.tau_s),
                  sampled_peak_Tv=float(row.Tv), amplitude_error_pct=amplitude,
                  timing_error_pct=phase, max_sample_gap_s=gap, sampling_limit_s=.01 * peak["tau_s"],
                  gates=gates, peak_gates_pass=all(gates.values()))
    result.update(error_stats(valid.error_Pa))
    return result


def observed(frame, nu, method, pressure, td, source, ref):
    time = frame.time_s.to_numpy(float)
    need(len(time) and np.isfinite(time).all() and np.all(np.diff(time) > 0), "Nonmonotone source clocks")
    tau = time - td
    p = frame[pressure].to_numpy(float)
    need(np.isfinite(p).all(), "Nonfinite observed centre pressure")
    reference = ref.pressure(tau)
    result = pd.DataFrame(dict(nu=nu, method=method, time_s=time, tau_s=tau,
        Tv=tau * ref.legacy_cv / R**2, center_Pa=p, reference_Pa=reference, error_Pa=p-reference))
    result["source"] = str(source.relative_to(CASE))
    return result


def load_profile(tag, output):
    nu = GROUPS[tag]
    hist_path, report_path = output / "review/actual_vs_theory.csv", output / "review/review.json"
    report, hist = read_json(report_path), read_csv(hist_path)
    need(report["full_cycle_measured"] and report["native_materials"] == 37173 and
         report["drained_materials"] == 5153, "A full native-material review is required")
    sources = [hist_path, report_path]
    legacy = tag == "030" and "nu" not in report
    if legacy:
        # This adapter refers only to the already reviewed, retained original .30 run.
        need(output.name == "CaseCryerWeakFull_nu030_1Tv_GPU_out" and report["steps"] == 481685 and
             report["frames"] == 269, "Unrecognised retained nu=.30 profile")
        dt, td = 2.**-19, 2.**-7
        dense_paths = [CASE / ("support/weak_full_r1/inputs/" + kind + "_history.csv")
                       for kind in ("open", "peak")]
        dense = pd.concat([read_csv(dense_paths[0]), read_csv(dense_paths[1]).iloc[1:]], ignore_index=True)
        dense = dense.rename(columns={"center_Pa": "center18_Pa", "min_Pa": "p_min_Pa",
                                      "max_Pa": "p_max_Pa"})
        sources += dense_paths
    else:
        need(float(report["nu"]) == nu, "Nu differs from the requested profile")
        dt, td = float(report["dt_s"]), float(report["drainage_time_s"])
        dense_path = output / "review/peak_history.csv"
        dense = read_csv(dense_path)
        sources.append(dense_path)
    need(dt > 0 and td >= 0, "Invalid declared clock")
    need(hist.step.is_unique and dense.step.is_unique, "Repeated completed steps")
    need(np.isfinite(dense[["center18_Pa", "surface_inward_mm", "p_min_Pa", "p_max_Pa",
                           "max_speed_m_s"]].to_numpy(float)).all(), "Nonfinite dense scalar fields")
    # Match the actual reviewed short-time series: original .30 used 360 modes;
    # the new profiles use 720 to resolve the first drainage step. Peak and tail
    # scoring use this same per-run M0 reference without changing tolerances.
    modes = 360 if legacy else 720
    ref = Reference(nu, modes=modes, finite=False)
    full = observed(hist, nu, "weak_full", "center18_Pa", td, hist_path, ref)
    peak = observed(dense, nu, "weak_dense", "center18_Pa", td, sources[-1], ref)
    need(legacy or peak.Tv.iloc[-1] >= PEAK_END_TV-2e-12, "New dense history must cover 0.12 Tv")
    for name, measured in (("tau_s", full.tau_s), ("legacy_Tv", full.Tv)):
        need(np.allclose(hist[name], measured, rtol=0, atol=2e-12), "Review clock mismatch: " + name)
    need(1-2e-12 <= full.Tv.iloc[-1] <= 1 + dt*ref.legacy_cv/R**2 + 2e-12,
         "The actual full endpoint is not the first attained 1 Tv")
    positive = full.tau_s >= 0
    theory_delta = float(np.max(np.abs(hist.loc[positive, "M0_center18_Pa"] -
                                      full.loc[positive, "reference_Pa"])))
    need(theory_delta < 1e-6, "Review pressure reference is not the declared M0 model")
    true_surface = surface_theory(ref, full.tau_s)
    surface_delta = float(np.nanmax(np.abs(hist.M0_surface_inward_mm - true_surface)))
    need(surface_delta < 1e-10, "Review surface reference is not the true nominal surface")
    joint = full.merge(peak, on="time_s", suffixes=("_full", "_dense"), validate="one_to_one")
    mean_delta = float(np.max(np.abs(joint.center_Pa_full-joint.center_Pa_dense))) if len(joint) else None
    # C++ scalar sums and NumPy means can differ only in the binary64 last bits.
    need(len(joint) and mean_delta <= 1e-8,
         "Dense scalar history disagrees with shared full-state clocks")
    return dict(tag=tag, nu=nu, output=output, report=report, hist=hist, dense=dense,
                full=full, peak=peak, ref=ref, reference_modes=modes, dt=dt, td=td, sources=sources,
                reference_max_delta_Pa=theory_delta, surface_reference_max_delta_mm=surface_delta,
                shared_full_dense_frames=len(joint), shared_center_max_delta_Pa=mean_delta)


def geometry_and_startup(profile):
    hist, dense, full = profile["hist"], profile["dense"], profile["full"]
    required = ["min_Pa", "max_Pa", "max_surface_abs_Pa", "max_speed_m_s", "min_J", "max_J",
                "min_det_F", "max_det_F", "max_displacement_m", "max_radius_m", "max_abs_stress_Pa"]
    finite = bool(np.isfinite(hist[required].to_numpy(float)).all())
    open_hist = hist[full.tau_s > 0]
    flags = dict(finite_saved_fields=finite,
                 saturated_nodal_J=bool(hist.min_J.min() > 1-float(np.float32(.3))),
                 positive_tet_volume=bool(hist.min_det_F.min() > 0),
                 drained_surface_exact_zero=bool(open_hist.max_surface_abs_Pa.eq(0).all()),
                 radius_within_existing_review_bound=bool(hist.max_radius_m.max() < .0525))
    t = dense.time_s - profile["td"]
    tv = t * profile["ref"].legacy_cv / R**2
    start = dense[(t > 0) & (tv < PEAK_START_TV)]
    need(len(start), "Startup scalar samples are required separately from the Mandel peak")
    top = start.loc[start.center18_Pa.idxmax()]
    closed = hist[full.tau_s <= 0].iloc[-1]
    startup_surface_error = start.surface_inward_mm.to_numpy() - surface_theory(
        profile["ref"], start.time_s.to_numpy()-profile["td"])
    return dict(gates=flags, saved_geometry_gates_pass=all(flags.values()),
        min_J=float(hist.min_J.min()), max_J=float(hist.max_J.max()),
        min_tet_det_F=float(hist.min_det_F.min()), max_tet_det_F=float(hist.max_det_F.max()),
        maximum_surface_abs_Pa=float(open_hist.max_surface_abs_Pa.max()),
        closed_actual_time_s=float(closed.time_s), closed_center_minus_q_Pa=float(closed.center18_Pa-Q),
        startup_samples=len(start), startup_center_max_Pa=float(top.center18_Pa),
        startup_center_max_time_s=float(top.time_s), startup_center_max_tau_s=float(top.time_s-profile["td"]),
        startup_field_min_Pa=float(start.p_min_Pa.min()), startup_field_max_Pa=float(start.p_max_Pa.max()),
        startup_max_speed_m_s=float(start.max_speed_m_s.max()),
        startup_surface_max_abs_error_mm=float(np.max(np.abs(startup_surface_error))),
        startup_center_exceeds_quasistatic_peak=bool(top.center18_Pa > continuous_peak(profile["ref"])["Pa"]),
        startup_assessment="Reported separately; passing Mandel-window tests does not accept the rapid opening transient.")


def compare_tail(weak, old):
    a, b = weak[weak.Tv >= .5], old[old.Tv >= .5]
    pair = a.drop(columns="nu").merge(b.drop(columns="nu"), on="tau_s",
                                     suffixes=("_weak", "_upw"), validate="one_to_one")
    # No clock rounding or interpolation: empty exact overlap is a valid reported result.
    result = dict(weak_own_grid=error_stats(a.error_Pa), old_own_grid=error_stats(b.error_Pa),
                  exact_tau_pairs=len(pair), weak_exact_pairs=error_stats(pair.error_Pa_weak),
                  old_exact_pairs=error_stats(pair.error_Pa_upw),
                  weak_rising_intervals=int(np.count_nonzero(np.diff(a.center_Pa) > 0)),
                  weak_largest_rise_Pa=float(max(0., np.max(np.diff(a.center_Pa)))))
    return result, pair


def assemble(outputs):
    old_path = FORMAL / "cryer_formal_four_nu_r1_native.csv"
    all_old = read_csv(old_path)
    profiles, centres, score_rows, pairs, state_rows = [], [], [], [], []
    sources = [old_path, Path(__file__), CASE/"support/plot_cryer_formal_four_nu_r1.py"]
    reports = {}
    for tag, output in sorted(outputs.items()):
        profile = load_profile(tag, output)
        nu, ref = profile["nu"], profile["ref"]
        old_native = all_old[np.isclose(all_old.nu, nu)].reset_index(drop=True)
        need(len(old_native) == 1065, "Retained finite-Kw native history is incomplete")
        old_ref = Reference(nu)
        td_old = float(old_native.time_s.iloc[0]-old_native.tau_s.iloc[0])
        old = observed(old_native, nu, "retained_u_pw", "center_pressure_pa", td_old, old_path, old_ref)
        finite = old.tau_s >= 0
        need(np.max(np.abs(old.loc[finite, "reference_Pa"] -
                           old_native.loc[finite, "finite_Kw_fixed18_p_pa"])) < 1e-6,
             "Old finite-Kw reference differs")
        weak_score, old_score = peak_score(profile["peak"], ref), peak_score(old, old_ref)
        tail, paired = compare_tail(profile["full"], old)
        paired.insert(0, "nu", nu)
        pairs.append(paired)
        hist = profile["hist"]
        state = hist.copy()
        state.insert(0, "nu", nu)
        state["M0_recomputed_surface_mm"] = surface_theory(ref, profile["full"].tau_s)
        state["surface_error_mm"] = state.surface_inward_mm-state.M0_recomputed_surface_mm
        state_rows.append(state)
        tail_surface = state[state.legacy_Tv >= .5]
        su = tail_surface.surface_error_mm.to_numpy()
        summary = dict(nu=nu, dt_s=profile["dt"], drainage_time_s=profile["td"],
                       M0_reference_modes=profile["reference_modes"],
                       actual_last_Tv=float(profile["full"].Tv.iloc[-1]),
                       full_frames=len(hist), dense_frames=len(profile["dense"]),
                       full_dense_exact_shared_frames=profile["shared_full_dense_frames"],
                       full_dense_max_center_delta_Pa=profile["shared_center_max_delta_Pa"],
                       weak_peak=weak_score, retained_upw_peak=old_score, tail=tail,
                       startup_geometry=geometry_and_startup(profile),
                       tail_surface=dict(samples=len(su), rms_mm=float(np.sqrt(np.mean(su*su))),
                           max_abs_mm=float(np.max(np.abs(su))), endpoint_error_mm=float(su[-1]),
                           endpoint_mm=float(hist.surface_inward_mm.iloc[-1]),
                           ultimate_M0_mm=float(1000*R*Q/(3*ref.K)),
                           decreasing_intervals=int(np.count_nonzero(np.diff(tail_surface.surface_inward_mm)<0))),
                       physical_acceptance=False)
        reports[tag] = summary
        for method, score in (("weak_dense", weak_score), ("retained_u_pw", old_score)):
            row = dict(nu=nu, method=method)
            row.update({k:v for k,v in score.items() if k != "gates"})
            row.update(score["gates"])
            score_rows.append(row)
        profile["old"] = old
        profile["scores"] = summary
        profiles.append(profile)
        centres.extend([profile["full"], profile["peak"], old])
        sources += profile["sources"]
    return profiles, pd.concat(centres, ignore_index=True), pd.DataFrame(score_rows), \
        pd.concat(pairs, ignore_index=True), pd.concat(state_rows, ignore_index=True), reports, sources


def pressure_figures(profiles, destination, peak_only=False):
    fig, axes = plt.subplots(2, 2, figsize=(11.4, 8), layout="constrained")
    for ax, profile in zip(axes.flat, profiles):
        tag, nu, ref = profile["tag"], profile["nu"], profile["ref"]
        lo, hi = (PEAK_START_TV, PEAK_END_TV) if peak_only else (1e-5, 5.)
        tv = np.geomspace(lo, hi, 600)
        tau = tv*R**2/ref.legacy_cv
        ax.plot(tv, ref.pressure(tau)/Q, "k-", lw=1.2, label="M0 analytical (weak)")
        ax.plot(tv, Reference(nu).pressure(tau)/Q, ":", color="0.45", lw=1.4,
                label="Finite-Kw analytical (old)")
        weak = profile["peak"] if peak_only else profile["full"]
        for frame, color, marker, label in ((profile["old"], "0.55", "x", "Retained u-pw"),
                                           (weak, COLORS[tag], "o", "Weak 3D")):
            a = frame[(frame.Tv >= lo) & (frame.Tv <= hi)]
            ax.plot(a.Tv, a.center_Pa/Q, linestyle="none", marker=marker, ms=3.4,
                    color=color, label=label)
        ax.set(xscale="log", xlim=(lo, hi), xlabel="Actual Tv after drainage",
               ylabel="Centre pressure / q0", title=f"nu = {nu:.2f}")
        if peak_only:
            v = np.concatenate([ref.pressure(tau)/Q, Reference(nu).pressure(tau)/Q])
            ax.set_ylim(float(v.min()-.02), float(v.max()+.02))
        ax.grid(alpha=.2, which="both")
        ax.legend(fontsize=7, loc="best")
    for ax in list(axes.flat)[len(profiles):]:
        ax.set_visible(False)
    name = "mandel_peak_log.png" if peak_only else "center_history_log.png"
    fig.savefig(destination/name, dpi=180)
    plt.close(fig)


def state_figure(profiles, destination):
    fig, axes = plt.subplots(2, 2, figsize=(11.4, 8), layout="constrained")
    for profile in profiles:
        hist, ref, color = profile["hist"], profile["ref"], COLORS[profile["tag"]]
        positive = hist.legacy_Tv > 0
        h = hist[positive]
        tv = h.legacy_Tv.to_numpy()
        label = f"nu={profile['nu']:.2f}"
        ultimate = 1000*R*Q/(3*ref.K)
        axes[0,0].plot(tv, h.surface_inward_mm/ultimate, ".", color=color, ms=3, label=label)
        axes[0,0].plot(tv, h.M0_surface_inward_mm/ultimate, "--", color=color, lw=1)
        axes[0,1].plot(tv, h.max_speed_m_s, ".", color=color, ms=3, label=label)
        axes[1,0].plot(tv, h.min_J, ".", color=color, ms=3, label=label)
        axes[1,0].plot(tv, h.max_J, "x", color=color, ms=3)
        axes[1,1].plot(tv, h.min_det_F, ".", color=color, ms=3, label=label)
        axes[1,1].plot(tv, h.max_det_F, "x", color=color, ms=3)
    axes[0,0].set(ylabel="True surface inward / ultimate M0",
                  title="Material samples; dashed = own M0")
    axes[0,1].set(ylabel="Maximum speed (m/s)", title="Saved full-state motion")
    axes[1,0].set(ylabel="Nodal J", title="Dots = minimum; crosses = maximum")
    axes[1,1].set(ylabel="Tet det F", title="Dots = minimum; crosses = maximum")
    for ax in axes.flat:
        ax.set(xscale="log", xlim=(1e-5, 5), xlabel="Actual Tv after drainage")
        ax.grid(alpha=.2, which="both")
        ax.legend(fontsize=7)
    fig.savefig(destination/"surface_and_geometry_log.png", dpi=180)
    plt.close(fig)


def publish(outputs, destination):
    profiles, centres, scores, pairs, state, report, sources = assemble(outputs)
    bindings = [binding(p) for p in sources]
    receipt_path = destination/"comparison.json"
    if receipt_path.exists():
        receipt = read_json(receipt_path)
        need(receipt["sources"] == bindings and all(binding(Path(a["path"])) == a for a in receipt["artifacts"]),
             "Existing aggregate differs; choose a new --figures directory")
        print("Existing aggregate sources and artifacts verified; nothing rewritten")
        return report
    need(not destination.exists(), "Preserve partial aggregate; choose a new --figures directory")
    destination.mkdir(parents=True)
    for name, data in (("center_history.csv", centres), ("peak_scores.csv", scores),
                       ("exact_tail_pairs.csv", pairs), ("state_history.csv", state)):
        data.to_csv(destination/name, index=False, float_format="%.17g")
    write_json(destination/"scores.json", report)
    pressure_figures(profiles, destination)
    pressure_figures(profiles, destination, peak_only=True)
    state_figure(profiles, destination)
    write_json(receipt_path, dict(sources=bindings, artifacts=[binding(p) for p in sorted(destination.iterdir())],
        groups=list(sorted(outputs)), model_references="Weak: M0 g=9.81. Retained u-pw: Kw=2e8, g=9.80665. Same fixed 18 centre materials.",
        peak_window_Tv=[PEAK_START_TV, PEAK_END_TV], peak_policy="Score only the observed window; require analytical peak bracket, <=1% peak-time sampling, <=1% amplitude and <=2% phase. No inferred dense samples.",
        tail_policy="Tv>=0.5; report own grids and exact actual tau intersections separately. No rounding or interpolation.",
        startup_policy="Rapid opening is reported separately and is not accepted by the Mandel-window gates.",
        scope="Small-strain fixed-reference weak Cryer research model. No solver, native decoder, VTK export, or efficiency inference.",
        physical_acceptance=False))
    print(destination/"comparison.json")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", action="append", metavar="nu010=OUTPUT",
                        help="Repeat for selected groups; retained nu030 is included automatically")
    parser.add_argument("--figures", type=Path, default=FORMAL/"weak_four_nu_r1")
    args = parser.parse_args()
    outputs = {tag: CASE/f"CaseCryerWeakFull_nu{tag}_1Tv_GPU_out" for tag in GROUPS}
    if args.profile:
        selected = {"030": outputs["030"]}
        for item in args.profile:
            key, value = item.split("=", 1)
            tag = key.removeprefix("nu")
            need(tag in GROUPS and bool(value), "Use nu010, nu020, nu030 or nu045=OUTPUT")
            selected[tag] = Path(value).resolve()
        outputs = selected
    publish(outputs, args.figures.resolve())


if __name__ == "__main__":
    main()
