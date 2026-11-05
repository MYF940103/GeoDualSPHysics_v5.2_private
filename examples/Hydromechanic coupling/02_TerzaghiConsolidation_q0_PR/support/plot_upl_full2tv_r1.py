"""Fresh root figures from sealed CSVs only; no solver, reader or theory evaluation."""
import csv
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"

CASE = Path(__file__).resolve().parents[1]
T = CASE / "tests"
FIG = CASE / "figures"
PREFIX = "full_validation_upl_CPU1_r1"
PINS = {
    "review": (T / "logs/upl_bigstep_full_r1.review.json", "5613343b5675bc6e6378ccd7c446b68f84c3fd2b72a5f548e69203259adf5bfc"),
    "overlay": (T / "logs/upl_full_upw_compare_r1.check.json", "03760c27e36b84a2a3bf629473b616ce6472cbe798033c8ef4ed2f15cc957ca4"),
    "focus": (T / "logs/upl_full_focus_r1.check.json", "6f1c43dde6bc95385cc16b2f791068613f564e393f11defd947d3a06c807e08a"),
    "root": (T / "notes/upl_bigstep_full_root_r1.json", "34a74789f5b54bd10de3200c0e0547e6835ea57b87f36b34206d15c9c2b0e8e7"),
}
NEW = "current_upl_CPU1_FreeSlip3"
OLD = "retained_upw_GPU_Vel0_1"
LABELS = {NEW: "Current u-pl CPU1 / FreeSlip3", OLD: "Retained u-pw GPU / Vel0"}
COLORS = {NEW: "#1764a0", OLD: "#df7f21"}
LIMIT = ("H1 references are unfitted ideal-drainage companions, not exact ramp / normalized top-2h-band / dynamic-inertia theory. "
         "H=.995 is an unfitted sensitivity. Old GPU/Vel0/dt=10 us and current CPU1/FreeSlip3/dt=6.250143 us differ in J/inertia and event time; not an isolated A/B.")
BOUND = {}


def entry(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def bind(expected):
    actual = entry(expected["path"])
    if actual != expected:
        raise RuntimeError("Changed sealed input: " + str(expected["path"]))
    BOUND[actual["path"]] = actual
    return Path(actual["path"])


def main():
    if os.name == "nt":
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        if not kernel.SetPriorityClass(ctypes.c_void_p(kernel.GetCurrentProcess()), 0x4000):
            raise RuntimeError("Could not set BelowNormal priority")
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    receipts = {}
    for key, (path, sha) in PINS.items():
        current = entry(path)
        if current["sha256"] != sha:
            raise RuntimeError("Receipt pin changed: " + key)
        receipts[key] = json.loads(bind(current).read_text(encoding="utf-8"))
        if receipts[key].get("passed") is not True or receipts[key].get("physical_acceptance") is not False:
            raise RuntimeError("Expected passed diagnostic receipt: " + key)
    if receipts["review"]["stage"] != "upl_bigstep_full_review_r1.review" or receipts["review"]["bindings_unchanged"] is not True:
        raise RuntimeError("Full review is not sealed")
    if receipts["overlay"]["source_full_review"] != BOUND[str(PINS["review"][0].resolve())]:
        raise RuntimeError("Overlay belongs to another full review")
    if receipts["review"]["rows"] != {"history": 1682, "layers": 168200, "theory": 1564, "profile_times": 10, "profiles": 1000}:
        raise RuntimeError("Unexpected completed full-review row counts")
    for key in ("review", "overlay", "focus"):
        for item in receipts[key]["files"]:
            bind(item)
    bind(entry(__file__))
    bind(entry(T / "notes/upl_root_figures_author_r1.json"))

    source_names = {
        "history": "upl_bigstep_full_r1.history.csv", "layers": "upl_bigstep_full_r1.layers.csv",
        "theory": "upl_bigstep_full_r1.theory.csv", "profiles": "upl_bigstep_full_r1.profiles.csv",
        "profile_times": "upl_bigstep_full_r1.profile_times.csv",
        "comparison_history": "upl_full_upw_compare_r1.history.csv",
        "comparison_profiles": "upl_full_upw_compare_r1.profiles.csv",
        "comparison_profile_times": "upl_full_upw_compare_r1.profile_times.csv",
        "focus_history": "upl_full_focus_r1.history.csv", "final_stress": "upl_full_focus_r1.final_stress.csv",
    }
    sources = {key: T / "figures" / name for key, name in source_names.items()}
    for path in sources.values():
        if str(path.resolve()) not in BOUND:
            raise RuntimeError("CSV not recorded in passed receipts: " + str(path))
    frames = {key: pd.read_csv(path, float_precision="round_trip") for key, path in sources.items() if key != "layers"}
    h, th, p, times = (frames[key] for key in ("history", "theory", "profiles", "profile_times"))
    comparison, focus, final = (frames[key] for key in ("comparison_history", "focus_history", "final_stress"))
    targets = [.005, .05, .1, .25, .4, .5, .7, 1., 1.5, 2.]
    if list(times.requested_Tv) != targets or len(p) != 1000 or len(h) != 1682 or len(th) != 1564:
        raise RuntimeError("Missing full-cycle profiles/history")
    if set(comparison.series) != {NEW, OLD} or set(focus.series) != {NEW, OLD} or len(final) != 100:
        raise RuntimeError("Unexpected comparison series/material layers")
    if not np.array_equal(h.loc[h.time_s.isin(th.time_s), "time_s"].to_numpy(), th.time_s.to_numpy()):
        raise RuntimeError("References do not use exact recorded current times")
    for target in targets:
        selected = p[p.requested_Tv == target]
        if len(selected) != 100 or list(selected.initial_layer) != list(range(100)):
            raise RuntimeError("Profile lacks 100 ordered material layers")

    png_names = ("profiles", "history", "startup", "overview", "diagnostics", "qualified_upw_profiles")
    paths = {key: FIG / (PREFIX + "_" + key + ".csv") for key in source_names}
    paths.update({key + "_plot": FIG / (PREFIX + "_" + key + ".png") for key in png_names})
    paths.update({key: FIG / (PREFIX + "_" + key + ".csv") for key in ("summary", "profile_summary")})
    check_path = FIG / (PREFIX + ".check.json")
    if check_path.exists() or any(path.exists() for path in paths.values()):
        raise RuntimeError("Fresh outputs required; no existing publication is overwritten")
    FIG.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
                         "legend.fontsize": 8, "axes.spines.top": False, "axes.spines.right": False})

    def save(fig, key, title, caption=LIMIT):
        fig.suptitle(title + " | completed CPU diagnostic, physical acceptance not declared", fontsize=12)
        fig.text(.5, .015, caption, ha="center", va="bottom", fontsize=8, wrap=True)
        fig.tight_layout(rect=(0, .065, 1, .95))
        with paths[key + "_plot"].open("xb") as stream:
            fig.savefig(stream, format="png", dpi=160)
        plt.close(fig)

    def axis(ax, xlabel, ylabel, title):
        ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
        ax.grid(alpha=.22)

    palette = plt.colormaps["turbo"](np.linspace(.04, .94, 10))

    def profiles(ax, late=False, legend=True):
        for target, color in zip(targets, palette):
            if late and target < 1:
                continue
            row = p[p.requested_Tv == target]
            actual = times[times.requested_Tv == target].actual_Tv.iloc[0]
            ax.plot(row.H1_finite_Kw_P_at_actual_time_Pa, row.z0_m, color=color, lw=1.15)
            ax.plot(row.actual_P_mean_Pa, row.z0_m, color=color, lw=.5, marker="o", mfc="none", ms=3.2,
                    mew=.8, markevery=8, label=f"target {target:g}; actual {actual:.6g}")
        axis(ax, "Excess pressure (Pa)", "Initial material height z0 (m)", "Late profiles (own actual times)" if late else "All ten targets (own actual times)")
        if legend:
            ax.legend(ncol=2, loc="best")

    fig, axes = plt.subplots(1, 2, figsize=(13, 7))
    profiles(axes[0]); profiles(axes[1], late=True)
    axes[1].text(.02, .04, "Solid: H1 finite-Kw companion\nOpen circles: current layer means\nAll 100 layers retained in CSV", transform=axes[1].transAxes, fontsize=9)
    save(fig, "profiles", "Pressure profiles through Tv=2", "Target Tv labels identify requested times; curves use each recorded actual time/Tv, not interpolation.\n"
         + "Exact part, time and signed target gaps: " + PREFIX + "_profile_times.csv. " + LIMIT)

    quantities = (("mean_pressure_pa", "same_node_mean_P_Pa", "Mean pressure (Pa)"),
                  ("top_settlement_mm", "material_top_settlement_mm", "Top material settlement (mm)"),
                  ("bottom_settlement_mm", "material_bottom_settlement_mm", "Bottom material settlement (mm)"))

    def histories(axes, startup=False):
        for ax, (native, ref, ylabel) in zip(axes, quantities):
            for name in (NEW, OLD):
                row = comparison[comparison.series == name]
                if startup:
                    row = row[row.time_s <= .1]
                ax.plot(row.time_s, row[native], color=COLORS[name], lw=1.2, label=LABELS[name])
            for stem, style in (("H1_finite_Kw", "-"), ("H1_classical", "--")):
                row = th[th.time_s <= .1] if startup else th
                ax.plot(row.time_s, row[stem + "_" + ref], style, color="#333333" if style == "--" else "#26894b", lw=1, label=stem.replace("_", " ") + " / current times")
            axis(ax, "Recorded time (s)", ylabel, "Startup: t <= 0.1 s" if startup else "Complete saved history")
            ax.legend()

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    histories(axes[0])
    for name in (NEW, OLD):
        row = focus[(focus.series == name) & (focus.actual_Tv >= 1)]
        for ax, key in zip(axes[1], ("mean_pressure_Pa", "H1_classical_top_error_um", "H1_classical_bottom_error_um")):
            ax.plot(row.actual_Tv, row[key], color=COLORS[name], label=LABELS[name], lw=1.3)
    late = th[th.primary_H1_actual_Tv >= 1]
    axes[1, 0].plot(late.primary_H1_actual_Tv, late.H1_finite_Kw_same_node_mean_P_Pa, color="#26894b", label="H1 finite-Kw / current times")
    axes[1, 0].plot(late.primary_H1_actual_Tv, late.H1_classical_same_node_mean_P_Pa, "--", color="#333333", label="H1 classical / current times")
    for ax, native, ref in ((axes[1, 1], "native_material_top_settlement_mm", "H1_finite_Kw_material_top_settlement_mm"),
                            (axes[1, 2], "native_material_bottom_settlement_mm", "H1_finite_Kw_material_bottom_settlement_mm")):
        ax.plot(late.primary_H1_actual_Tv, 1000 * (late[native] - late[ref]), color="#26894b", label="Current minus H1 finite-Kw")
    for ax, label in zip(axes[1], ("Mean pressure (Pa)", "Top error (um)", "Bottom error (um)")):
        axis(ax, "Own actual Tv (H1)", label, "Late window: actual Tv >= 1")
        ax.legend()
    save(fig, "history", "Complete pressure and fixed-material settlement histories", "Errors: each series minus its own same-time H1 classical reference; green error is current minus H1 finite-Kw. " + LIMIT)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5))
    histories(axes, startup=True)
    save(fig, "startup", "Startup pressure and material settlements", "Startup is shown without removing oscillations. Companion curves begin after drainage opens; there is no ramp-matched exact theory here. " + LIMIT)

    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    profiles(axes[0], legend=False)
    histories(axes[1:])
    axes[0].text(.03, .03, "10 target colors; solid finite-Kw / open current\nTarget and actual times in profile_times.csv", transform=axes[0].transAxes, fontsize=8)
    save(fig, "overview", "Pressure profiles, mean pressure and top settlement")

    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    for name in (NEW, OLD):
        row = focus[(focus.series == name) & (focus.time_s >= .1 - 1e-7)]
        axes[0, 0].plot(row.time_s, row.Q_Pa, color=COLORS[name], label=LABELS[name])
        axes[0, 1].plot(row.time_s, row.max_layer_total_error_Pa, color=COLORS[name], label=LABELS[name])
        axes[0, 2].plot(row.time_s, row.H1_classical_bottom_error_um, color=COLORS[name], label=LABELS[name])
    axes[0, 1].axhline(100, color="#b32628", ls="--", lw=1, label="Retained old criterion: 100 Pa")
    axes[0, 2].plot(th.time_s, 1000 * (th.native_material_bottom_settlement_mm - th.H1_finite_Kw_material_bottom_settlement_mm), color="#26894b", label="Current minus H1 finite-Kw")
    axes[1, 0].plot(h.time_s, h.A_pi_Uz_RMS_mm, color=COLORS[NEW])
    axes[1, 1].plot(h.time_s, h.A_pi_total_sigma_components_RMS_Pa, color=COLORS[NEW])
    axes[1, 2].plot(final.signed_total_stress_residual_Pa, final.z0_m, color=COLORS[NEW])
    for value in (-100, 100):
        axes[1, 2].axvline(value, color="#b32628", ls="--", lw=.8)
    for ax, stem in zip(axes[2], ("J", "n", "rho_native")):
        for suffix, style in (("min", "--"), ("mean", "-"), ("max", ":")):
            column = stem + "_" + suffix + ("_kg_m3" if stem == "rho_native" else "")
            ax.plot(h.time_s, h[column], style, label=suffix)
        ax.legend()
    labels = (("Recorded time (s)", "Q (Pa)", "RMS second layer differences; t >= 0.1 s"),
              ("Recorded time (s)", "Max layer |sigma_zz + q0| (Pa)", "100 Pa is not a new-run acceptance gate"),
              ("Recorded time (s)", "Bottom error (um)", "Persistent fixed-material bottom bias"),
              ("Recorded time (s)", "Alternating-X Uz RMS (mm)", "Saved 10-column alternating mode"),
              ("Recorded time (s)", "Six-component stress RMS (Pa)", "Saved alternating-X stress mode"),
              ("Signed sigma_zz + q0 (Pa)", "Initial height z0 (m)", "Final total-stress residual, all 100 layers"),
              ("Recorded time (s)", "Current J", "All soil nodes: min / mean / max"),
              ("Recorded time (s)", "Porosity n", "All soil nodes: min / mean / max"),
              ("Recorded time (s)", "Actual native density (kg/m3)", "Current native rho, not legacy Rhop"))
    for ax, args in zip(axes.flat, labels):
        axis(ax, *args)
    for ax in axes[0]:
        ax.legend()
    save(fig, "diagnostics", "Stress, bottom bias, modes and current-state diagnostics", "Linear axes retain all values in each stated window. Q is a vertical-layer second-difference metric, not the alternating-X mode. " + LIMIT)

    for key, source in sources.items():
        with source.open("rb") as src, paths[key].open("xb") as dst:
            shutil.copyfileobj(src, dst)
        if entry(paths[key])["sha256"] != BOUND[str(source.resolve())]["sha256"]:
            raise RuntimeError("CSV copy changed bytes")
    old_profile_png = T / "figures/upl_full_upw_compare_r1.profiles.png"
    with old_profile_png.open("rb") as src, paths["qualified_upw_profiles_plot"].open("xb") as dst:
        shutil.copyfileobj(src, dst)
    if entry(paths["qualified_upw_profiles_plot"])["sha256"] != BOUND[str(old_profile_png.resolve())]["sha256"]:
        raise RuntimeError("Qualified comparison figure copy changed bytes")

    last = th.iloc[-1]
    current_end = comparison[comparison.series == NEW].iloc[-1]
    old_end = comparison[comparison.series == OLD].iloc[-1]
    old_focus = focus[focus.series == OLD].iloc[-1]
    summary = []
    for stem in ("H1_classical", "H1_finite_Kw", "H995_classical", "H995_finite_Kw"):
        pref = last[stem + "_same_node_mean_P_Pa"]
        top = last[stem + "_material_top_settlement_mm"]
        bottom = last[stem + "_material_bottom_settlement_mm"]
        summary.append(dict(series=NEW, reference=stem, time_s=current_end.time_s, actual_Tv=current_end.actual_Tv,
                            native_mean_P_Pa=current_end.mean_pressure_pa, reference_same_node_mean_P_Pa=pref,
                            reference_continuum_mean_P_Pa=last[stem + "_continuum_mean_P_Pa"],
                            pressure_error_Pa=current_end.mean_pressure_pa - pref,
                            top_settlement_mm=current_end.top_settlement_mm, reference_top_mm=top,
                            top_error_percent=100 * (current_end.top_settlement_mm - top) / top,
                            bottom_settlement_mm=current_end.bottom_settlement_mm, reference_bottom_mm=bottom,
                            bottom_error_um=1000 * (current_end.bottom_settlement_mm - bottom),
                            Q_Pa=current_end.Q_pa, max_layer_total_error_Pa=current_end.max_layer_total_error_pa,
                            native_node_profile_RMS_Pa=last[stem + "_same_node_P_profile_RMS_difference_Pa"]))
    old_profiles = frames["comparison_profiles"]
    old_last_profile = old_profiles[old_profiles.target_Tv == 2]
    if len(old_last_profile) != 100 or not (old_last_profile.old_actual_time_s == old_end.time_s).all():
        raise RuntimeError("Retained endpoint reference is not at its own final time")
    old_pref = old_last_profile.old_classical_at_own_time_Pa.mean()
    old_top = old_end.top_settlement_mm - old_focus.H1_classical_top_error_um / 1000
    old_bottom = old_end.bottom_settlement_mm - old_focus.H1_classical_bottom_error_um / 1000
    summary.append(dict(series=OLD, reference="H1_classical_at_old_own_time", time_s=old_end.time_s, actual_Tv=old_end.actual_Tv,
                        native_mean_P_Pa=old_end.mean_pressure_pa, reference_same_node_mean_P_Pa=old_pref,
                        reference_continuum_mean_P_Pa=None, pressure_error_Pa=old_end.mean_pressure_pa - old_pref,
                        top_settlement_mm=old_end.top_settlement_mm, reference_top_mm=old_top,
                        top_error_percent=100 * (old_end.top_settlement_mm - old_top) / old_top,
                        bottom_settlement_mm=old_end.bottom_settlement_mm, reference_bottom_mm=old_bottom,
                        bottom_error_um=old_focus.H1_classical_bottom_error_um, Q_Pa=old_end.Q_pa,
                        max_layer_total_error_Pa=old_end.max_layer_total_error_pa, native_node_profile_RMS_Pa=None))
    with paths["summary"].open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0])); writer.writeheader(); writer.writerows(summary)
    profile_summary = []
    for target in targets:
        row = p[p.requested_Tv == target]
        old_row = old_profiles[old_profiles.target_Tv == target]
        stamp = times[times.requested_Tv == target].iloc[0]
        profile_summary.append(dict(target_Tv=target, current_part=int(stamp.actual_part), current_actual_time_s=stamp.actual_time_s,
                                    current_actual_Tv=stamp.actual_Tv, current_signed_target_gap_s=stamp.signed_time_gap_s,
                                    current_layer_mean_RMS_vs_H1_finite_Kw_Pa=math.sqrt(np.mean((row.actual_P_mean_Pa - row.H1_finite_Kw_P_at_actual_time_Pa) ** 2)),
                                    old_actual_time_s=old_row.old_actual_time_s.iloc[0], old_actual_Tv=old_row.old_actual_Tv.iloc[0],
                                    old_signed_target_gap_s=old_row.old_signed_target_gap_s.iloc[0],
                                    old_layer_mean_RMS_vs_own_classical_Pa=math.sqrt(np.mean((old_row.old_pressure_Pa - old_row.old_classical_at_own_time_Pa) ** 2)),
                                    signed_current_minus_old_time_gap_s=old_row.signed_new_minus_old_time_gap_s.iloc[0],
                                    sample_definition="100 material-layer means; not 1000 native-node RMS", interpolation_used=False))
    with paths["profile_summary"].open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(profile_summary[0])); writer.writeheader(); writer.writerows(profile_summary)
    for expected in list(BOUND.values()):
        bind(expected)
    exceed = focus[(focus.series == NEW) & (focus.time_s >= .1 - 1e-7) & (focus.max_layer_total_error_Pa > 100)]
    receipt = dict(stage=PREFIX, passed=True, plotting_only=True, physical_acceptance=False,
                   solver_or_decoder_invoked=False, references_recomputed_or_fitted=False, interpolation_used=False,
                   priority="BelowNormal on Windows", BLAS_threads=1, dpi=160, inputs=list(BOUND.values()),
                   files=[entry(path) for path in paths.values()], bindings_unchanged=True,
                   source_row_counts={key: len(frame) for key, frame in frames.items()},
                   all_168200_layer_rows_copied_byte_exact=True, figures=6,
                   retained_old_100Pa_criterion_exceeding_current_post_point1_saved_frames=len(exceed),
                   criterion_is_not_a_new_run_accuracy_gate=True, limits=LIMIT,
                   copied_qualified_upw_profile_figure_source=BOUND[str(old_profile_png.resolve())],
                   error_summary=str(paths["summary"]), profile_RMS_summary=str(paths["profile_summary"]))
    with check_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({"passed": True, "plotting_only": True, "physical_acceptance": False, "receipt": str(check_path)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        raise
