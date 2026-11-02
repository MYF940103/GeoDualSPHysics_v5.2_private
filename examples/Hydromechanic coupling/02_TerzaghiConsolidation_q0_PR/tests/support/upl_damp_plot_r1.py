"""Descriptive .125 s damping review; requires CPU half and current GPU coarse bridge first."""
import ast, csv, hashlib, importlib.util, json
from pathlib import Path
from types import SimpleNamespace
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = "upl_damp_plot_r1"
EVENT = 5243 * 2. ** -19
TIMES = (.015625, .0625, .125)
WINDOWS = (("early_post", EVENT, .015625), ("middle", .015625, .0625), ("late", .0625, .125))
SERIES = (("CPU_damped_c", "coarse", "#2166ac", "-", "CPU eta=.02 coarse"),
          ("CPU_damped_h", "half", "#67a9cf", "--", "CPU eta=.02 half"),
          ("GPU_damped_c", "coarse", "#1b7837", "-.", "GPU eta=.02 coarse"),
          ("GPU_noaux_c", "coarse", "#b35806", ":", "retained GPU noaux ON coarse"))
PINS = {"support/upl_damp_compare_r3.py": "34b2cfe642505df3b5a537631d88acf5c353b816f6f0665c5d1a34ba40c99e73",
        "notes/upl_damp_compare_r3.json": "d3ab86391a3434d8b7680282c8887461f3a4a930004a9eee08360c3dd362965f",
        "notes/upl_damp_cross_initial_r1.json": "2c9b5bd0895442f7cb85efd469598d13a366035a688fede9fa5ee7b843da9120",
        "support/upl_column_ringdown_plot_r1.py": "b46583a96ea8c7f3dc9b345979983440f8f86b22de50d195458b9417f357577d",
        "notes/upl_column_ringdown_plot_r1.json": "8130d3278f347e44ac5b27dcb8af92f7483a7c24b6b2d39bbd906a291a81e070",
        "support/upl_column_ringdown_on_off_r1.py": "b761afe9c291db1c441cc88a8b6f5d2c511f4295ae88238b08074ddde7d0f30b",
        "support/upl_column_ringdown_profile_readability_r2.py": "fa4663d13157ad8fccfd29a7ab99d2466503c90c7396a3a062561bdef923fbc0"}
GATES = {"pressure_RMS_all_times_le_5Pa", "material_XYZ_difference_all_times_le_0_005mm", "actual_time_difference_le_1e_minus14_s"}

def dependencies():
    sources = {rel: (T / rel).read_bytes() for rel in PINS}
    for rel, raw in sources.items():
        if hashlib.sha256(raw).hexdigest() != PINS[rel]: raise ValueError("Pinned review dependency changed: " + rel)
    rel = "support/upl_damp_compare_r3.py"
    h = importlib.util.module_from_spec(importlib.util.spec_from_file_location("frozen_damping_exports", T / rel))
    exec(compile(sources[rel], str(T / rel), "exec"), h.__dict__)  # Guarded comparator main never called.
    # Extract ONLY the already-reviewed summarize function and its three literal constants.
    # Do not execute the old plot module/imports/main or call its old dataset/current-source checks.
    rel = "support/upl_column_ringdown_plot_r1.py"; tree = ast.parse(sources[rel], filename=str(T / rel))
    scope = {"np": np, "csv": csv, "Path": Path}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {"PROFILE_STEPS", "PROFILE_LABELS", "RHO_FIELDS"}:
            scope[node.targets[0].id] = ast.literal_eval(node.value)
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "summarize"]
    h.need(len(fn) == 1 and all(k in scope for k in ("PROFILE_STEPS", "PROFILE_LABELS", "RHO_FIELDS")), "Frozen summary closure differs")
    exec(compile(ast.Module(body=fn, type_ignores=[]), str(T / rel), "exec"), scope)
    return h, scope["summarize"]

def proof(h, path, stage, case=None):
    e = h.adopt(T / path); p = h.readjson(e["path"])
    h.need(p["passed"] is True and p["physical_acceptance"] is False and p["stage"] == stage and p["samples"] == 1277 and p["native_count"] == 1000 and set(p["gates"]) == GATES and all(v is True for v in p["gates"].values()), "Original complete paired gates not passed: " + path)
    if case is not None: h.need(p["case"] == case, "Wrong paired review case")
    for item in p["files"]: h.bind(item)
    return e, p

def retained(h):
    pe, p = proof(h, "logs/upl_column_ringdown_half_r1.check.json", "upl_column_ringdown_half_r1")
    ce = h.adopt(T / "logs/upl_column_ringdown_GPU_coarse_r1.native.json"); c = h.readjson(ce["path"])
    h.need(p["native_checks"][0] == ce and c["passed"] and c["backend"] == "GPU" and c["window"] == "coarse" and c["physical_acceptance"] is False, "Retained noaux GPU control differs")
    q = h.readjson(h.bind(c["completion"])); r = h.readjson(h.bind(c["source_run"])); call = h.base.owned(r["call"]); h.base.owned(c["reader_call"])
    h.need(q["passed"] and q["samples"] == 1277 and q["native_count"] == 1000 and q["fixed_count"] == 40 and q["native_total_arrays"] == 22 and q["PART_typed_public_metadata_verified"] and q["public_master_on"] and q["no_exclusions"] and q["all_exported_physical_fields_finite"] and q["max_ledger_relative_error"] <= 5e-13 and q["dt_s"] == 2. ** -19 and q["actual_end_s"] == .125 and q["physical_schema"] == h.SCHEMA, "Retained native schema/safety differs")
    h.need(r["passed"] and r["backend"] == "GPU" and r["window"] == "coarse" and r["public_project_main"] and not r["fixture_or_Run_override"] and r["source_inputs_objects_runtime_canonical_unchanged"] and call["program"] == r["program"], "Retained true GPU Run rejected")
    b = h.readjson(h.bind(r["source_build"])); h.need(b["passed"] and b["isolated_GPU_program"] == r["program"], "Retained actual GPU build identity differs")
    files = {Path(v["path"]).name: v for v in c["files"]}; h.need(set(files) == set(h.EXPORTS) | {"completion.json"}, "Retained13 export scope differs")
    data = dict(check=ce, run=c["source_run"], build=r["source_build"], program=r["program"], files=files, n=1277)
    data["p"] = h.mapped(files["physical.bin"], (1000, 26, 1277), [("time", "<f8"), ("q", "<f8", (1000, 26))], 1277)
    data["clock"] = h.mapped(files["clock.bin"], (1277, 28), [("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")], 1277)
    ids = np.genfromtxt(h.bind(files["native_ids.csv"]), delimiter=",", names=True, encoding="utf-8")
    h.need(np.array_equal(ids["row"], np.arange(1000)) and np.array_equal(ids["id"], np.arange(40, 1040)), "Retained soil material IDs differ")
    data["x0"] = np.column_stack([ids[k] for k in ("x0", "y0", "z0")]).astype("<f8")
    with h.bind(files["columns.csv"]).open(encoding="utf-8-sig", newline="") as f: cols = list(csv.DictReader(f))
    h.need([v["name"] for v in cols] == h.base.FIELDS and [int(v["column"]) for v in cols] == list(range(26)), "Retained common26 columns differ")
    clock = data["clock"]; times = h.DYADIC * 2. ** -19
    h.need(np.array_equal(np.where(np.arange(1277) == 0, 0, clock["step"].astype(np.int64) + 1), h.DYADIC) and np.all(clock["dt"] == 2. ** -19) and h.base.bits(clock["time"], times).all() and h.base.bits(data["p"]["time"], times).all() and h.base.bits(data["p"]["q"][0, :, :3], data["x0"]).all(), "Retained actual clock/initial coordinates differ")
    h.need(np.isfinite(clock["error"]).all() and np.all(clock["error"][1:] <= 1e-14) and np.all(clock["error"][1:] != -np.finfo(float).max), "Retained signed step guard differs")
    return data, pe, p

def reduce(h, old_summary, key, grid, d):
    ctx = SimpleNamespace(readjson=h.readjson, bind=h.bind, need=h.need, N=1277, STEPS=h.DYADIC, base=SimpleNamespace(F=h.base.FIELDS))
    series, _, rho_gap = old_summary(ctx, grid, d)
    sn = h.mapped(d["files"]["soil_n.bin"], (1000, 1, 1277), [("time", "<f8"), ("q", "<f8", (1000,))], 1277)
    h.need(h.base.bits(sn["time"], d["clock"]["time"]).all(), "Native n actual times differ")
    with h.bind(d["files"]["history.csv"]).open(encoding="utf-8-sig", newline="") as f: hist = list(csv.DictReader(f))
    layers = np.rint(d["x0"][:, 2] / .01 - .5).astype(int); profiles = []; layer_p = []
    h.need(len(hist) == 1277, "Native ledger-history coverage differs")
    for part, row in enumerate(series):
        q = np.asarray(d["p"]["q"][part]); n = np.asarray(sn["q"][part]); le = float(hist[part]["max_ledger_relative_error"])
        h.need(np.isfinite(n).all() and np.all((n > 0) & (n < 1)) and np.isfinite(le) and 0 <= le <= 5e-13, "Native n/ledger summary rejected")
        row.update(series=key, native_n_min=float(n.min()), native_n_mean=float(n.mean()), native_n_max=float(n.max()), native_ledger_max_relative_error=le)
        layer_p.append(np.bincount(layers, weights=q[:, 6], minlength=100) / 10.)
        time = row["actual_time_s"]
        if time in TIMES:
            for layer in range(100):
                m = layers == layer
                profiles.append([key, grid, part, time, layer, float(d["x0"][m, 2].mean()), float(q[m, 6].mean()), float(-1000 * (q[m, 2] - d["x0"][m, 2]).mean()), float((q[m, 6] - q[m, 15]).mean()), float(np.sqrt(np.mean(np.sum(q[m, 3:6] ** 2, axis=1))))])
    h.need(len(profiles) == 300, "Three actual saved100-layer profiles missing")
    windows = []; time = np.array([r["actual_time_s"] for r in series]); lp = np.asarray(layer_p)
    for label, lo, hi in WINDOWS:
        take = (time >= lo) & (time <= hi); rows = [r for r, keep in zip(series, take) if keep]; h.need(len(rows) >= 3, "Predeclared sampled window missing")
        for field in ("pressure_mean_Pa", "top10_pressure_mean_Pa", "bottom10_pressure_mean_Pa", "interior10_pressure_mean_Pa"):
            v = np.array([r[field] for r in rows]); net = float(v[-1] - v[0]); tv = float(np.abs(np.diff(v)).sum())
            windows.append([key, label, field, lo, hi, len(rows), float(time[take][0]), float(time[take][-1]), float(v.min()), float(v.max()), float(np.ptp(v)), float(v.std()), net, tv, .5 * (tv - abs(net)), float(np.ptp(lp[take], axis=0).max()), max(r["velocity_XYZ_RMS_m_s"] for r in rows)])
    return series, profiles, windows, rho_gap

def draw(h, histories, profiles, paths):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator, ScalarFormatter
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .25})
    panels = (("pressure_mean_Pa", "Mean pressure (kPa)", .001), ("top_minus_bottom_pressure_Pa", "Top-bottom pressure (kPa)", .001),
              ("top10_settlement_mean_mm", "Top material settlement, down (mm)", 1), ("velocity_XYZ_RMS_m_s", "Soil XYZ speed RMS (m/s)", 1),
              ("J_mean", "Native J mean", 1), ("native_n_mean", "Native soil n mean", 1),
              ("saved_theta_RMS_s_inv", "Saved last-stage theta RMS (1/s)", 1), ("total_compression_zz_mean_Pa", "Derived total compression mean (kPa)", .001),
              ("stored_stress_Frobenius_RMS_Pa", "Stored effective stress tensor RMS (kPa)", .001), ("native_ledger_max_relative_error", "Native ledger relative error", 1))
    fig, axes = plt.subplots(5, 2, figsize=(13, 15), sharex=True)
    for key, _, color, style, label in SERIES:
        for ax, (field, title, scale) in zip(axes.flat, panels):
            rows = histories[key]; ax.plot([r["actual_time_s"] * 1000 for r in rows], [r[field] * scale for r in rows], color=color, ls=style, lw=1.2, label=label)
            ax.set_ylabel(title); ax.axvline(EVENT * 1000, color=".45", ls=":", lw=.7)
    for ax in axes[-1]: ax.set_xlabel("Actual native time (ms)")
    fig.suptitle("Single eta=.02 candidate: CPU half, GPU bridge, matched retained GPU noaux ON", y=.995)
    fig.legend(*axes.flat[0].get_legend_handles_labels(), ncol=2, loc="upper center", bbox_to_anchor=(.5, .97), fontsize=9)
    fig.text(.5, .012, "Saved-field comparison only; original half/cross gates precede this descriptive plot. No theory/force-stage or physical acceptance.\nRaw1277 samples; ordinary122.0703125 us cadence cannot certify all high-frequency decay. Pressure RMS is not oscillation amplitude.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .05, 1, .935)); fig.savefig(paths["history_png"], dpi=180); plt.close(fig)
    fig, axes = plt.subplots(4, 3, figsize=(13, 11), sharey=True)
    variables = ((6, "Pore pressure (Pa)"), (7, "Settlement, down (mm)"), (8, "Derived total compression p-sigma_zz (Pa)"), (9, "Layer XYZ speed RMS (m/s)"))
    for col, time in enumerate(TIMES):
        axes[0, col].set_title("Actual t = " + format(time, ".6g") + " s")
        for key, _, color, style, label in SERIES:
            a = np.asarray([r[4:] for r in profiles if r[0] == key and r[3] == time], dtype=float)
            h.need(a.shape == (100, 6) and np.isfinite(a).all() and np.array_equal(a[:, 0], np.arange(100)), "Complete100-layer profile missing")
            for row, (column, xlabel) in enumerate(variables):
                axes[row, col].plot(a[:, column - 4], a[:, 1], color=color, ls=style, lw=1.2, label=label); axes[row, col].set_xlabel(xlabel)
        for row in range(4):
            ax = axes[row, col]; ax.xaxis.set_major_locator(MaxNLocator(nbins=3, min_n_ticks=2)); formatter = ScalarFormatter(useOffset=False, useMathText=True)
            if row == 3: formatter.set_powerlimits((0, 0))
            ax.xaxis.set_major_formatter(formatter); ax.tick_params(axis="x", labelsize=8, pad=3)
    for ax in axes[:, 0]: ax.set_ylabel("Initial material z0 (m)")
    fig.suptitle("Native material profiles; new damped CPU/GPU and retained GPU noaux ON", y=.995)
    fig.legend(*axes[0, 0].get_legend_handles_labels(), ncol=2, loc="upper center", bbox_to_anchor=(.5, .97), fontsize=9)
    fig.text(.5, .012, "Each point = ten original soil IDs in one100-layer material band (speed: RMS); no smoothing/interpolation/clipping.\nOnly same-GPU matched-input comparison describes damping change; CPU half and CPU/GPU bridge are separate implementation checks.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .06, 1, .925)); fig.savefig(paths["profiles_png"], dpi=180); plt.close(fig)

def main():
    paths = {k: T / "figures" / (TAG + suffix) for k, suffix in {"history_png": "_history.png", "profiles_png": "_profiles.png", "history_csv": "_history.csv", "profiles_csv": "_profiles.csv", "windows_csv": "_windows.csv"}.items()}; check = T / "logs" / (TAG + ".check.json")
    if check.exists() or any(p.exists() for p in paths.values()): raise ValueError("Retained review output protected")
    result = dict(stage=TAG, passed=False, physical_acceptance=False, solver_decoder_build_or_Git_invoked=False, additional_scientific_gate=False, failure=None); h = None
    try:
        h, old_summary = dependencies()
        for rel in (*PINS, "support/" + TAG + ".py", "notes/" + TAG + ".json"): h.adopt(T / rel)
        h.adopt(h.PARENT)
        he, hp = proof(h, "logs/upl_damp_CPU_half_r3.check.json", "upl_damp_compare_r3", "CPU_half")
        be, bp = proof(h, "logs/upl_damp_cross_coarse_r3.check.json", "upl_damp_compare_r3", "cross_coarse")
        a, b, g = h.dataset("CPU", "coarse"), h.dataset("CPU", "half"), h.dataset("GPU", "coarse")
        h.need(hp["native_checks"] == [a["check"], b["check"]] and hp["source_runs"] == [a["run"], b["run"]] and bp["native_checks"] == [a["check"], g["check"]] and bp["source_runs"] == [a["run"], g["run"]], "Actual half/bridge refer to different datasets")
        old, oe, op = retained(h); data = [a, b, g, old]
        old_run = h.readjson(h.bind(old["run"])); old_half_run = h.readjson(h.bind(op["source_runs"][1]))
        for d, source in ((a, old_run), (b, old_half_run), (g, old_run)):
            r = h.readjson(h.bind(d["run"])); h.need(r["job"]["source_runtime"] == source["runtime_input"], "Damping candidate must derive from that exact retained noaux runtime")
        h.need(all(h.base.bits(d["x0"], old["x0"]).all() for d in data) and hp["source_builds"] == [a["build"], b["build"]] and bp["source_builds"] == [a["build"], g["build"]], "Material/source proof identity differs")
        histories = {}; profiles = []; windows = []; rho_gaps = {}
        for (key, grid, *_), d in zip(SERIES, data):
            histories[key], pp, ww, rho_gaps[key] = reduce(h, old_summary, key, grid, d); profiles.extend(pp); windows.extend(ww)
        with paths["history_csv"].open("x", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(histories[SERIES[0][0]][0])); writer.writeheader(); writer.writerows(r for key, *_ in SERIES for r in histories[key])
        for name, header, rows in (("profiles_csv", ["series", "grid", "part", "actual_time_s", "initial_material_layer", "initial_z_m", "pressure_mean_Pa", "settlement_mean_mm", "derived_total_compression_mean_Pa", "velocity_XYZ_RMS_m_s"], profiles),
                                   ("windows_csv", ["series", "window", "pressure_field", "declared_lo_s", "declared_hi_s", "saved_samples", "actual_first_s", "actual_last_s", "min_Pa", "max_Pa", "sampled_peak_to_peak_Pa", "sampled_temporal_STD_Pa", "net_change_Pa", "sampled_total_variation_Pa", "sampled_reversal_variation_Pa", "max_layer_sampled_peak_to_peak_Pa", "max_saved_XYZ_speed_RMS_m_s"], windows)):
            with paths[name].open("x", encoding="utf-8", newline="") as f: writer = csv.writer(f); writer.writerow(header); writer.writerows(rows)
        draw(h, histories, profiles, paths)
        for e in list(h.base.BOUND.values()): h.need(h.entry(e["path"]) == e, "Consumed input changed during descriptive review")
        result.update(passed=True, CPU_half_check=he, GPU_bridge_check=be, retained_GPU_half_check=oe, native_checks=[d["check"] for d in data], source_runs=[d["run"] for d in data], source_builds=[d["build"] for d in data], history_rows=5108, profile_rows=1200, window_rows=48, samples_each=1277, native_soil_each=1000, actual_profile_times_s=list(TIMES), declared_event_s=EVENT, CPU_half_metrics={k: hp[k] for k in ("max_pressure_RMS_Pa", "max_material_XYZ_displacement_difference_mm", "max_actual_time_difference_s")}, CPU_GPU_bridge_metrics={k: bp[k] for k in ("max_pressure_RMS_Pa", "max_material_XYZ_displacement_difference_mm", "max_actual_time_difference_s")}, native_rho_summary_vs_J_derived_gap_descriptive=rho_gaps, old_current_source_originals_revalidated=False, no_temporal_resampling_smoothing_or_clipping=True, visual_review_performed=False)
    except Exception as exc: result["failure"] = str(exc)
    result["limitations"] = ["Saved typed-export review,not a second BI4 parser or physical/theory/full-consolidation acceptance.", "CPU half and current CPU/GPU bridge retain original5Pa/0.005mm/1e-14; same-GPU option change has no new5Pa gate.", "Temporal p2p/STD include evolving mean/trend; sampled reversal variation=(sum(abs(diff))-abs(last-first))/2 is descriptive,not a fitted damping ratio or continuum oscillation amplitude.", "Windows include their declared endpoints; samples are unweighted,with dense event sampling explicitly retained. Ordinary122.0703125us cadence cannot certify all high-frequency behavior.", "Theta is saved last-stage,not a force/endpoint recomputation; common26 has no pdot. Native n/rho and ledger summaries are labeled separately from derived total stress.", "No actual force-stage external resultant,wall flux,energy budget,CPU/GPU speedup or isolated causal proof is measured. Retained control uses immutable export/provenance entries,not old mutable source originals."]
    result.update(inputs=list(h.base.BOUND.values()) if h else [], files=[h.entry(p) for p in paths.values() if p.exists()] if h else [])
    with check.open("x", encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps(dict(passed=result["passed"], check=str(check)))); return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
