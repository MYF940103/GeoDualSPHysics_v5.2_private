"""Descriptive case02 flux short-window plots; requires sealed original QC, never runs a decoder."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

TESTS = Path(__file__).resolve().parents[1]
LOCKS = {
    "support/upl_case02_qc_r1.py": "0ed07dd825c4209bb580bef6af821a415112bc6d63c7502cf0ea4e50fa401c96",
    "notes/upl_case02_qc_r1.json": "15b116e91c74dcde2d6eeefbb7492fad5b9efb3377690289d0abe1db67fee810",
    "support/upl_case02_flux_qc_r1.py": "460ee3f17fb806c4e4ae48528de4025ea6fae13e3374b3e59a1df9d315c228da",
    "notes/upl_case02_flux_qc_r1.json": "532ce8b31cd5787728696401249fea7b02d724056f5728aceb476144dcd88146",
}
for leaf, sha in LOCKS.items():
    if hashlib.sha256((TESTS/leaf).read_bytes()).hexdigest() != sha:
        raise RuntimeError("Immutable analysis dependency changed: "+leaf)
from upl_case02_qc_r1 import load_job, drain, saved_steps, identity, bind, VERIFIED, need, FIELDS, table

TAG = "upl_case02_flux_short_physical_r1"
EVENT = .01
STRESS = ("sigma_xx", "sigma_xy", "sigma_xz", "sigma_yy", "sigma_yz", "sigma_zz")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def prerequisite(leaf, mode):
    path = bind(identity(TESTS/"logs"/leaf))
    q = read_json(path)
    need(q["passed"] is True and q["stage"] == "upl_case02_flux_qc_r1" and q["mode"] == mode
         and q["physical_acceptance"] is False and q["bindings_unchanged_after_QC"] is True,
         "Complete passed flux QC required before descriptive plotting: "+leaf)
    for entry in q["inputs"]:
        bind(entry)
    return q


def provenance(job, qc):
    check = job["check"]
    expected = {str(Path(e["path"]).resolve()).casefold(): e for e in qc["inputs"]}
    for entry in (identity(TESTS/"logs"/("upl_case02_"+check["job"]+"_r1.native.check.json")),
                  check["sealed_solver"]):
        need(expected.get(str(Path(entry["path"]).resolve()).casefold()) == entry,
             "QC does not bind this native/solver pair")
    run = read_json(bind(check["sealed_solver"]))
    call = read_json(bind(run["owned_exit_record"]))
    need(call["direct_native_call"] is True and call["typed_LASTEXITCODE_captured_immediately"] is True
         and call["owned_call_exited"] is True and type(call["exit_code"]) is int and call["exit_code"] == 0
         and call["program"] == run["program"] and call["arguments"] == run["arguments"],
         "Actual owned solver call/exit/program attribution differs")
    helper = read_json(bind(run["build"]))
    build = read_json(bind(helper["source_build"]))
    need(helper["passed"] is True and helper["kind"] == "actual" and helper["configuration"] == "ReleaseCPU"
         and helper["program"] == run["program"] and build["passed"] is True,
         "Current flux solver helper/build attribution differs")
    for entry in run["bindings"]:
        bind(entry)
    for entry in run["files"]:
        bind(entry)
    need(len(helper["source_snapshot"]) == 265, "Not the declared source265 closure")
    cpu = []
    for pair in helper["source_snapshot"]:
        bind(pair["original"])
        bind(pair["snapshot"])
        if Path(pair["original"]["path"]).name == "JSphCpu.cpp":
            cpu.append(pair)
    need(len(cpu) == 1 and cpu[0]["original"]["sha256"] == cpu[0]["snapshot"]["sha256"],
         "Actual candidate CPU source/snapshot attribution")
    for entry in helper["canonical_programs_before"]:
        bind(entry)
    for runtime in helper["runtime"]:
        bind(runtime["original"])
        bind(runtime["copy"])
    return dict(native_check=identity(TESTS/"logs"/("upl_case02_"+check["job"]+"_r1.native.check.json")),
                solver_run=check["sealed_solver"], solver_call=run["owned_exit_record"],
                program=run["program"], helper=run["build"], source_build=helper["source_build"],
                source_stage=build["stage"], CPU_source=cpu[0],
                source265_original_and_snapshot_rehashed=True,
                inputs=[e for e in run["bindings"] if Path(e["path"]).suffix.lower() in (".xml", ".bi4")])


def reductions(prefix, values, series):
    series[prefix+"_mean"] = np.mean(values, axis=1)
    series[prefix+"_min"] = np.min(values, axis=1)
    series[prefix+"_max"] = np.max(values, axis=1)
    series[prefix+"_RMS"] = np.sqrt(np.mean(values*values, axis=1))


def summarize(job, factor):
    x, clock, x0 = job["x"], job["clock"], job["x0"]
    need(job["done"]["window"] == "short" and job["done"]["grid"] == ("c" if factor == 1 else "h"),
         "Only the declared complete coarse/half window is supported")
    d = drain(job, factor)
    completed = factor*saved_steps().astype(np.uint64)
    ids = np.array([int(r["id"]) for r in table(job["files"]["native_ids.csv"])])
    levels = np.unique(x0[:, 2])
    need(len(levels) == 100, "Expected original100 material layers")
    group_indices = dict(bottom=0, interior=49, top=99)
    groups = {name: np.flatnonzero(x0[:, 2] == levels[layer]) for name, layer in group_indices.items()}
    need(all(len(index) == 10 for index in groups.values()), "Expected10 native material IDs per selected layer")
    u = 1000.*(x[:, :, :3]-x0)
    s = dict(time_s=clock["time"], saved_step=clock["step"], completed_step=completed,
             post_open_by_completed_step=completed > 4000*factor)
    reductions("p_Pa", x[:, :, 6], s)
    s["p0_max_abs_Pa"] = np.max(abs(x[:, :, 7]), axis=1)
    s["settlement_mean_mm"] = -np.mean(u[:, :, 2], axis=1)  # Positive downward, material displacement.
    s["u_fullXYZ_RMS_mm"] = np.sqrt(np.mean(np.sum(u*u, axis=2), axis=1))
    s["u_fullXYZ_max_mm"] = np.max(np.linalg.norm(u, axis=2), axis=1)
    s["v_fullXYZ_RMS_m_s"] = np.sqrt(np.mean(np.sum(x[:, :, 3:6]**2, axis=2), axis=1))
    for axis, index in zip("xyz", range(3)):
        reductions("u"+axis+"_mm", u[:, :, index], s)
        reductions("v"+axis+"_m_s", x[:, :, index+3], s)
    reductions("J", x[:, :, 8], s)
    reductions("theta_last_stage_s_inv", x[:, :, 9], s)
    for name in STRESS:
        reductions(name+"_Pa", x[:, :, FIELDS.index(name)], s)
    active = np.isin(x[:, :, 17], (2, 3)) & s["post_open_by_completed_step"][:, None]
    s["active_drained_native_count"] = active.sum(axis=1)
    s["post_open_drained_max_abs_p_Pa"] = np.max(np.where(active, abs(x[:, :, 6]), 0.), axis=1)
    s["post_open_drained_p_zero_checks"] = active.sum(axis=1)
    for name, index in groups.items():
        for field, values in (("p_Pa", x[:, index, 6]), ("J", x[:, index, 8]),
                              ("theta_last_stage_s_inv", x[:, index, 9]),
                              ("sigma_zz_Pa", x[:, index, 15]), ("settlement_mm", -u[:, index, 2])):
            reductions(name+"_"+field, values, s)
    need(all(np.isfinite(value).all() for value in s.values()), "Nonfinite descriptive reduction")
    fits = []
    # Descriptive envelopes only: loaded pressure growth is not itself a numerical-instability test.
    for first, last in ((.0005, .001375), (.005, .009975)):
        for key in ("p_Pa_RMS", "v_fullXYZ_RMS_m_s"):
            mask = (s["time_s"] >= first) & (s["time_s"] <= last) & (s[key] > 0)
            row = dict(series=key, requested_actual_time_window_s=[first, last], positive_samples=int(mask.sum()))
            if mask.sum() >= 3:
                t, y = s["time_s"][mask], np.log(s[key][mask])
                tc, yc = t-t.mean(), y-y.mean()
                slope = float(np.dot(tc, yc)/np.dot(tc, tc))
                residue = yc-slope*tc
                row.update(actual_first_last_s=[float(t[0]), float(t[-1])], log_envelope_slope_s_inv=slope,
                           log_fit_R2=(1.-float(np.dot(residue, residue)/np.dot(yc, yc))) if np.dot(yc, yc) > 0 else None)
            fits.append(row)
    report = dict(samples=519, native_material_IDs=1000, fixed_IDs_checked_by_loader=40,
                  actual_first_last_s=[float(clock["time"][0]), float(clock["time"][-1])],
                  completed_steps=int(completed[-1]), dt_s=float(clock["dt"][0]), drainage=d,
                  material_groups={name: dict(layer_index=group_indices[name], initial_z_m=float(levels[group_indices[name]]),
                                             native_ids=ids[index].tolist()) for name, index in groups.items()},
                  global_series_min_max={key: [float(value.min()), float(value.max())] for key, value in s.items()},
                  descriptive_log_envelope_fits=fits)
    return s, report


def save_figure(fig, path):
    fig.tight_layout(rect=(0, 0, 1, .94))
    with path.open("xb") as stream:
        fig.savefig(stream, format="png", dpi=170)
    plt.close(fig)


def plots(data, global_path, layer_path):
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .25})
    panels = (("p_Pa_RMS", "p_Pa_min", "p_Pa_max"), ("settlement_mean_mm", "u_fullXYZ_RMS_mm"),
              ("sigma_zz_Pa_min", "sigma_zz_Pa_max"), ("vx_m_s_RMS", "vy_m_s_RMS", "vz_m_s_RMS"),
              ("J_min", "J_max"), ("theta_last_stage_s_inv_min", "theta_last_stage_s_inv_max"))
    titles = ("Soil pressure [Pa]", "Material settlement / XYZ displacement [mm]", "Effective sigma_zz [Pa]",
              "Native XYZ velocity RMS [m/s]", "Native volume ratio J", "Saved last-stage theta [1/s]")
    fig, axes = plt.subplots(3, 2, figsize=(12, 10))
    for ax, keys, title in zip(axes.flat, panels, titles):
        for name, s in data.items():
            for n, key in enumerate(keys):
                ax.plot(s["time_s"]*1000., s[key], color="C"+str(n), ls="-" if name == "coarse" else "--",
                        lw=1.1, label=name+" "+key)
        ax.axvline(EVENT*1000., color="black", lw=.8, ls=":")
        ax.set(title=title, xlabel="Actual native time [ms]")
        ax.legend(fontsize=6)
    fig.suptitle("Private case02 flux candidate: complete short c/h; descriptive, not physical validation\n"
                 "Vertical line: declared drainage event. No measured force-stage resultant or native pdot.", fontsize=10)
    save_figure(fig, global_path)
    fig, axes = plt.subplots(3, 2, figsize=(12, 10))
    fields = ("p_Pa_mean", "settlement_mm_mean", "sigma_zz_Pa_mean", "J_mean", "theta_last_stage_s_inv_RMS")
    labels = ("Layer mean pressure [Pa]", "Layer mean settlement [mm]", "Layer mean effective sigma_zz [Pa]",
              "Layer mean J", "Layer saved last-stage theta RMS [1/s]")
    for ax, key, label in zip(list(axes.flat)[:5], fields, labels):
        for name, s in data.items():
            for n, group in enumerate(("bottom", "interior", "top")):
                ax.plot(s["time_s"]*1000., s[group+"_"+key], color="C"+str(n),
                        ls="-" if name == "coarse" else "--", lw=1.1, label=name+" "+group)
        ax.axvline(EVENT*1000., color="black", lw=.8, ls=":")
        ax.set(title=label, xlabel="Actual native time [ms]")
        ax.legend(fontsize=7)
    ax = axes.flat[5]
    for name, s in data.items():
        ax.plot(s["time_s"]*1000., s["top_p_Pa_mean"], ls="-" if name == "coarse" else "--", label=name+" top mean p")
    ax.axvline(EVENT*1000., color="black", lw=.8, ls=":")
    ax.set(xlim=(9.97, 10.03), title="Dense native samples around opening [Pa]", xlabel="Actual native time [ms]")
    ax.legend(fontsize=7)
    fig.suptitle("Fixed initial-material layers: bottom0 / interior49 / top99 (10 IDs each)\n"
                 "Pressure-zero drainage checks use actual FSType2/3 after declared completed-step boundary; no pdot claim.", fontsize=10)
    save_figure(fig, layer_path)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()  # Deliberately no arbitrary input or failed-run mode.
    target = TESTS/"logs"/(TAG+".check.json")
    paths = {"history": TESTS/"figures"/(TAG+"_history.csv"), "global": TESTS/"figures"/(TAG+"_global.png"),
             "layers": TESTS/"figures"/(TAG+"_layers.png")}
    need(not target.exists() and not any(p.exists() for p in paths.values()), "Existing review output protected")
    result = dict(stage=TAG, passed=False, physical_acceptance=False, solver_reader_build_or_Git_started=False,
                  additional_physical_acceptance_gate_applied=False, partial_or_failed_run_supported=False,
                  decoder_reused_without_monkeypatch=True, native_pdot_available=False, force_stage_resultant_measured=False,
                  endpoint_force_recomputed=False, theta_is_saved_last_stage_not_endpoint_recompute=True)
    try:
        for leaf in (*LOCKS, "support/flux_short_physical_review_r1.py", "notes/flux_short_physical_review_r1.json"):
            bind(identity(TESTS/leaf))
        qc_c = prerequisite("upl_case02_flux_short_coarse_r1.qc.json", "coarse")
        qc_h = prerequisite("upl_case02_flux_short_r1.half.json", "half")
        a, b = load_job("flux_short_coarse", 519, 2.5e-6, True), load_job("flux_short_half", 519, 1.25e-6, True)
        for leaf in ("native_ids.csv", "fixed_ids.csv"):
            need(a["files"][leaf].read_bytes() == b["files"][leaf].read_bytes(), "Material ID/initial-coordinate mismatch")
        need(np.array_equal(a["x"][0].view("<u8"), b["x"][0].view("<u8")), "Initial all26 bits differ")
        provenance_a, provenance_b = provenance(a, qc_c), provenance(b, qc_h)
        need(provenance_a["program"] == provenance_b["program"] and provenance_a["CPU_source"] == provenance_b["CPU_source"],
             "The two candidate solver programs/sources differ")
        sc, rc = summarize(a, 1)
        sh, rh = summarize(b, 2)
        need(np.max(abs(sc["time_s"]-sh["time_s"])) <= 1e-14, "Original matched native-time budget failed")
        # Same quantities/units as the already-passed original QC; no new physical threshold.
        half_p = np.sqrt(np.mean((a["x"][:, :, 6]-b["x"][:, :, 6])**2, axis=1))
        du = (a["x"][:, :, :3]-a["x0"])-(b["x"][:, :, :3]-b["x0"])
        half_u = 1000.*np.max(np.linalg.norm(du, axis=2), axis=1)
        for s in (sc, sh):
            s["half_pressure_RMS_Pa"] = half_p
            s["half_max_XYZ_material_displacement_difference_mm"] = half_u
        paths["history"].parent.mkdir(parents=True, exist_ok=True)
        keys = list(sc)
        need(keys == list(sh), "Reduction column schema mismatch")
        with paths["history"].open("x", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["grid", "part"]+keys)
            for name, s in (("coarse", sc), ("half", sh)):
                for part in range(519):
                    writer.writerow([name, part]+[value[part].item() for value in s.values()])
        plots(dict(coarse=sc, half=sh), paths["global"], paths["layers"])
        result.update(passed=True, grids=dict(coarse=rc, half=rh), provenance=dict(coarse=provenance_a, half=provenance_b),
                      same_material_initial26_bits=True, actual_time_max_difference_s=float(np.max(abs(sc["time_s"]-sh["time_s"]))),
                      original_half_QC=dict(max_pressure_RMS_Pa=qc_h["max_pressure_RMS_Pa"], pressure_limit_Pa=5,
                                           max_material_displacement_difference_mm=qc_h["max_material_displacement_difference_mm"], displacement_limit_mm=.005),
                      independently_reduced_half=dict(max_pressure_RMS_Pa=float(half_p.max()),
                          max_material_displacement_difference_mm=float(half_u.max()),
                          max_difference_from_original_QC_pressure_series_Pa=float(np.max(abs(half_p-np.asarray(qc_h["pressure_RMS_Pa_all519"])))),
                          max_difference_from_original_QC_displacement_series_mm=float(np.max(abs(half_u-np.asarray(qc_h["material_displacement_difference_mm_all519"]))))),
                      output_history_rows=1038, files=[identity(p) for p in paths.values()])
        for entry in VERIFIED.values():
            need(identity(entry["path"]) == entry, "Consumed binding changed during descriptive review")
        result["bindings_unchanged_after_review"] = True
    except Exception as error:
        result.update(passed=False, failure=str(error), files=[identity(p) for p in paths.values() if p.is_file()])
    result["inputs"] = list(VERIFIED.values())
    result["limitations"] = ["Typed26 export analysis, not a second BI4 decoder or a C++ Jacobian.",
        "Native last-stage theta is not an independently recomputed endpoint or all-stage observation.",
        "PorePress0 is checked native zero; pressure rate is absent from physical26 and is neither inferred nor plotted.",
        "LoadAce columns are not a force-stage resultant/budget; no resultant or boundary flux is measured here.",
        "Increasing loaded-field envelopes or fitted log-slopes alone neither prove instability nor its absence.",
        "Complete .0125s single/half QC is not long-time, theory, formal, public or physical validation."]
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(str(target)+" passed="+str(result["passed"]))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
