"""Fresh descriptive CPU step-candidate figures; requires its completed own1341 half proof."""
import ast, csv, hashlib, importlib.util, json
from pathlib import Path
from types import SimpleNamespace
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG, N = "upl_damp_step_plot_r1", 1341
EVENT = 2621 * 2. ** -18
TIMES = (EVENT, .125, .25, .5)
SERIES = (("CPU_c", "coarse", "#2166ac", "-", "CPU eta=.02 coarse"),
          ("CPU_h", "half", "#b35806", "--", "CPU eta=.02 half"))
PINS = {"support/upl_damp_step_compare_r1.py": "c80cfdf362fca8ed3534319a7ae2dbc7151382bfc1331a3a61536f29885c34ff",
        "notes/upl_damp_step_compare_r1.json": "19ffe7d58d1f4dda1673dec31ae634b660a994845516d0f0726c17b367a89eda",
        "support/upl_damp_long_plot_r1.py": "09ce1447e940f809ec73a9891b2a3adfeaf795bd0d01e83298fe9bbf66085e68",
        "notes/upl_damp_long_plot_r1.json": "fcc57b23a7c1b7efebd4835530923d38e8bae715b3b4fc413459156a6d6b2632",
        "support/upl_column_ringdown_plot_r1.py": "b46583a96ea8c7f3dc9b345979983440f8f86b22de50d195458b9417f357577d",
        "notes/upl_column_ringdown_plot_r1.json": "8130d3278f347e44ac5b27dcb8af92f7483a7c24b6b2d39bbd906a291a81e070"}
GATES = {"pressure_RMS_all_times_le_5Pa", "material_XYZ_difference_all_times_le_0_005mm", "actual_time_difference_le_1e_minus14_s"}

def capture(source, filename, name, parameters, event_declaration=False):
    tree = ast.parse(source, filename=filename); found = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(found) != 1: raise ValueError("Pinned pure function missing: " + name)
    fn = found[0]
    if event_declaration:
        class Event(ast.NodeTransformer):
            count = 0
            def visit_Constant(self, node):
                if type(node.value) is int and node.value == 5243:
                    self.count += 1
                    return ast.copy_location(ast.Name(id="DRAIN_STEP", ctx=ast.Load()), node)
                return node
        change = Event(); fn = change.visit(fn)
        if change.count != 2: raise ValueError("Exactly two old event declarations must adapt; no other AST edit")
    args = ast.arguments(posonlyargs=[], args=[ast.arg(arg=k) for k in parameters], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
    factory = ast.FunctionDef(name="_capture", args=args, body=[fn, ast.Return(value=ast.Name(id=name, ctx=ast.Load()))], decorator_list=[], returns=None, type_comment=None)
    scope = {"np": np, "csv": csv, "Path": Path}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[factory], type_ignores=[])), filename, "exec"), scope)
    return scope["_capture"](*parameters.values())  # Explicit immutable closure; no old module globals patched.

def dependencies():
    sources = {rel: (T / rel).read_bytes() for rel in PINS}
    for rel, raw in sources.items():
        if hashlib.sha256(raw).hexdigest() != PINS[rel]: raise ValueError("Pinned source/note changed: " + rel)
    rel = "support/upl_damp_step_compare_r1.py"
    h = importlib.util.module_from_spec(importlib.util.spec_from_file_location("frozen_step_exports", T / rel))
    exec(compile(sources[rel], str(T / rel), "exec"), h.__dict__)  # Only new-step dataset will be called, never any main/old dataset.
    for rel, raw in sources.items():
        e = dict(path=str((T / rel).resolve()), bytes=len(raw), sha256=PINS[rel]); key = e["path"].casefold()
        if key in h.BOUND: h.need(all(h.BOUND[key][k] == e[k] for k in ("bytes", "sha256")), "Conflicting pinned source")
        else: h.BOUND[key] = e  # Register only identities actually read/verified above; no cache reset/shared old globals.
    rel = "support/upl_column_ringdown_plot_r1.py"; tree = ast.parse(sources[rel]); literals = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {"PROFILE_LABELS", "RHO_FIELDS"}:
            literals[node.targets[0].id] = ast.literal_eval(node.value)
    h.need(set(literals) == {"PROFILE_LABELS", "RHO_FIELDS"}, "Pinned summary literal closure differs")
    parameters = dict(DRAIN_STEP=2621, PROFILE_STEPS=(2621, 2622, 4096, 16384, 32768), **literals)
    summary = capture(sources[rel], str(T / rel), "summarize", parameters, True)
    rel = "support/upl_damp_long_plot_r1.py"
    reference = capture(sources[rel], str(T / rel), "ideal_reference", dict(EVENT=EVENT))
    return h, summary, reference

def reduce(h, summary, key, grid, d):
    ctx = SimpleNamespace(readjson=h.readjson, bind=h.bind, need=h.need, N=N, STEPS=h.STEPS, base=SimpleNamespace(F=h.FIELDS))
    rows, _, rho_gap = summary(ctx, grid, d)
    sn = h.mapped(d["files"]["soil_n.bin"], (1000, 1, N), [("time", "<f8"), ("q", "<f8", (1000,))])
    h.need(h.bits(sn["time"], d["clock"]["time"]).all(), "Native n actual clock differs")
    layers = np.rint(d["x0"][:, 2] / .01 - .5).astype(int); profiles = []
    for part, row in enumerate(rows):
        n = np.asarray(sn["q"][part]); hist = d["history"][part]; le = float(hist["max_ledger_relative_error"])
        h.need(np.isfinite(n).all() and np.all((n > 0) & (n < 1)) and np.isfinite(le) and 0 <= le <= 5e-13, "Original native n/ledger guard rejected")
        row.update(series=key, native_n_min=float(n.min()), native_n_mean=float(n.mean()), native_n_max=float(n.max()), native_ledger_max_relative_error=le,
                   saved_rhoV_LoadAce_z_N_per_m=float(hist["final_J_weighted_retained_load_z_N_per_m"]))
        h.need(np.isfinite(row["saved_rhoV_LoadAce_z_N_per_m"]), "Nonfinite saved load telemetry")
        if row["actual_time_s"] in TIMES:
            q = np.asarray(d["p"]["q"][part])
            for layer in range(100):
                take = layers == layer
                profiles.append([key, grid, part, row["actual_time_s"], layer, float(d["x0"][take, 2].mean()), float(q[take, 6].mean()), float(-1000 * (q[take, 2] - d["x0"][take, 2]).mean()), float((q[take, 6] - q[take, 15]).mean()), float(np.sqrt(np.mean(np.sum(q[take, 3:6] ** 2, axis=1))))])
    h.need(len(rows) == N and len(profiles) == 400, "Complete new-step history/four100-layer profiles required")
    return rows, profiles, rho_gap

def draw(h, histories, profiles, reference, paths):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator, ScalarFormatter
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .25})
    panels = (("pressure_mean_Pa", "Mean pore pressure (kPa)", .001), ("top_minus_bottom_pressure_Pa", "Top-bottom pressure (kPa)", .001),
              ("top10_settlement_mean_mm", "Top material settlement, down (mm)", 1), ("velocity_XYZ_RMS_m_s", "Soil XYZ speed RMS (m/s)", 1),
              ("total_compression_zz_mean_Pa", "Derived total compression zz (kPa)", .001), ("saved_theta_RMS_s_inv", "Saved theta RMS (1/s)", 1),
              ("J_mean", "Native J mean", 1), ("native_n_mean", "Native soil n mean", 1),
              ("saved_rhoV_LoadAce_z_N_per_m", "Saved rhoV*LoadAce.z (N/m)", 1), ("native_ledger_max_relative_error", "Native ledger relative error", 1))
    fig, axes = plt.subplots(5, 2, figsize=(13, 15), sharex=True)
    for key, _, color, style, label in SERIES:
        rows = histories[key]
        for ax, (field, unit, scale) in zip(axes.flat, panels):
            ax.plot([r["actual_time_s"] for r in rows], [r[field] * scale for r in rows], color=color, ls=style, lw=1.2, label=label); ax.set_ylabel(unit)
            for time in (EVENT, .125, .25): ax.axvline(time, color=".6", ls=":", lw=.6)
    for ax in axes[-1]: ax.set_xlabel("Actual native time (s)")
    fig.suptitle("New larger-step candidate: CPU coarse / half, eta=.02, 0.5 s", y=.995)
    fig.legend(*axes.flat[0].get_legend_handles_labels(), ncol=2, loc="upper center", bbox_to_anchor=(.5, .969))
    fig.text(.5, .012, "Own1341-frame half gate required; HG/SPR/viscosity/other auxiliary damping OFF. Saved LoadAce/J weights are endpoint telemetry, NOT force-stage proof.\nNew ramp/drain at0.009998321533203125s; no old-event prefix inherited. Late1.953125ms saves cannot certify unsaved high-frequency behavior.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .052, 1, .935)); fig.savefig(paths["history_png"], dpi=180); plt.close(fig)
    fig, axes = plt.subplots(4, 4, figsize=(15, 12), sharey=True)
    for col, time in enumerate(TIMES):
        axes[0, col].set_title(("Event/pre-open\n" if time == EVENT else "") + "Actual t=" + format(time, ".12g") + " s")
        for key, _, color, style, label in SERIES:
            a = np.asarray([r[4:] for r in profiles if r[0] == key and r[3] == time], dtype=float)
            h.need(a.shape == (100, 6) and np.isfinite(a).all() and np.array_equal(a[:, 0], np.arange(100)), "Complete material profile missing")
            for row, (index, unit, scale) in enumerate(((2, "Pore pressure (kPa)", .001), (3, "Settlement, down (mm)", 1), (4, "Derived total compression (kPa)", .001), (5, "Layer XYZ speed RMS (m/s)", 1))):
                axes[row, col].plot(a[:, index] * scale, a[:, 1], color=color, ls=style, lw=1.2, label=label); axes[row, col].set_xlabel(unit)
        if time != EVENT:
            for convention, color, style, label in (("nominal_H1", ".3", ":", "Ideal quasi-static H=1m"), ("initial_pressure_particle_plane_H0.995", ".6", "-.", "Ideal quasi-static H=.995m")):
                rs = [r for r in reference if r["convention"] == convention and r["actual_time_s"] == time]
                for row, field, scale in ((0, "ideal_pressure_mean_Pa", .001), (1, "ideal_material_settlement_mean_mm", 1)):
                    axes[row, col].plot([r[field] * scale for r in rs], [r["initial_z_m"] for r in rs], color=color, ls=style, lw=1., label=label)
        for row in range(4):
            ax = axes[row, col]; ax.xaxis.set_major_locator(MaxNLocator(nbins=3, min_n_ticks=2)); fmt = ScalarFormatter(useOffset=False, useMathText=True)
            if row == 3: fmt.set_powerlimits((0, 0))
            ax.xaxis.set_major_formatter(fmt); ax.tick_params(axis="x", labelsize=8)
    for ax in axes[:, 0]: ax.set_ylabel("Initial material z0 (m)")
    fig.suptitle("Same actual material IDs: new event and 0.125 / 0.25 / 0.5 s", y=.995)
    fig.legend(*axes[0, 1].get_legend_handles_labels(), ncol=2, loc="upper center", bbox_to_anchor=(.5, .968))
    fig.text(.5, .012, "Ten-ID layer means (speed: RMS); both unfitted finite-Kw H conventions use identical initial z0 and q0=10000Pa, never Qcancel.\nIdeal uniform traction / instantaneous step drainage is NOT exact dynamic-ramp/band-load truth or a theory acceptance gate. No interpolation/smoothing/clipping.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .06, 1, .925)); fig.savefig(paths["profiles_png"], dpi=180); plt.close(fig)

def main():
    paths = {k: T / "figures" / (TAG + v) for k, v in dict(history_png="_history.png", profiles_png="_profiles.png", history_csv="_history.csv", profiles_csv="_profiles.csv", reference_profiles_csv="_reference_profiles.csv", reference_metrics_csv="_reference_metrics.csv").items()}
    check = T / "logs" / (TAG + ".check.json")
    if check.exists() or any(p.exists() for p in paths.values()): raise ValueError("Retained plot artifacts protected")
    h = None; result = dict(stage=TAG, passed=False, physical_acceptance=False, additional_scientific_gate=False, solver_decoder_build_or_subprocess_invoked=False, failure=None)
    try:
        h, summary, reference = dependencies()
        h.adopt(__file__); h.adopt(T / "notes" / (TAG + ".json"))
        pe = h.adopt(T / "logs/upl_damp_step_half_r1.check.json"); proof = h.readjson(h.bind(pe))
        h.need(proof["passed"] is True and proof["physical_acceptance"] is False and proof["stage"] == "upl_damp_step_compare_r1" and proof["case"] == "half" and proof["samples"] == N and proof["same_event_s"] == EVENT and proof["initial26_bit_exact"] is True and set(proof["gates"]) == GATES and all(v is True for v in proof["gates"].values()), "Own completed same-event1341 half proof required")
        for e in proof["inputs"] + proof["files"]: h.bind(e)
        a, b = h.dataset("coarse"), h.dataset("half")  # Exactly once each; no old dataset is called.
        h.need(proof["native_checks"] == [a["check"], b["check"]] and proof["source_runs"] == [a["run"], b["run"]] and proof["source_builds"] == [a["build"], b["build"]] and a["build"] == b["build"] and a["program"] == b["program"], "Actual pair/native/build identity differs")
        histories = {}; profiles = []; rho_gaps = {}
        for (key, grid, *_), data in zip(SERIES, (a, b)):
            histories[key], pr, rho_gaps[key] = reduce(h, summary, key, grid, data); profiles.extend(pr)
        rc = SimpleNamespace(need=h.need, base=SimpleNamespace(bits=h.bits))
        refs, metrics, parameters = reference(rc, (a, b))
        for leaf, rows in (("history_csv", histories["CPU_c"] + histories["CPU_h"]), ("reference_profiles_csv", refs), ("reference_metrics_csv", metrics)):
            with paths[leaf].open("x", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        with paths["profiles_csv"].open("x", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["series", "grid", "part", "actual_time_s", "initial_material_layer", "initial_z_m", "pressure_mean_Pa", "settlement_mean_mm", "derived_total_compression_mean_Pa", "velocity_XYZ_RMS_m_s"]); w.writerows(profiles)
        draw(h, histories, profiles, refs, paths)
        for e in list(h.BOUND.values()):
            actual = h.entry(e["path"]); h.need(actual["bytes"] == e["bytes"] and actual["sha256"] == e["sha256"], "Consumed input changed during independent final rehash")
        result.update(passed=True, half_check=pe, native_checks=[a["check"], b["check"]], source_runs=[a["run"], b["run"]], source_builds=[a["build"], b["build"]], samples_each=N, native_soil_each=1000, fixed_each=40, history_rows=2*N, profile_rows=len(profiles), reference_profile_rows=len(refs), reference_metric_rows=len(metrics), ideal_quasistatic_reference=parameters, actual_profile_times_s=list(TIMES), declared_event_s=EVENT, half_metrics={k: proof[k] for k in ("max_pressure_RMS_Pa", "max_material_XYZ_displacement_difference_mm", "max_actual_time_difference_s")}, native_rho_summary_vs_J_derived_gap_descriptive=rho_gaps, initial_hash_cache_unique_files=len(h.BOUND), independent_final_rehash_performed=True, old_dataset_or_main_called=False, old_new_event_comparison_performed=False, visual_review_performed=False)
    except Exception as exc: result["failure"] = str(exc)
    result["limitations"] = ["Own same-event half gates precede descriptive plots; no old-prefix inheritance, fitted q/reference or new acceptance threshold.", "Ideal finite-Kw uniform traction/step drainage at two explicit unfitted H conventions is not exact dynamic-ramp/band-load physics or direct Lian2023 reproduction; displacement is at the same initial material z0, not a different analytic surface.", "Only two actual CPU trajectories. No0.5s GPU/noaux, pressure-rate, force-stage load/flux/energy or unsaved high-frequency stability proof; late output is sparse. Saved LoadAce/current-J quadrature is descriptive endpoint telemetry.", "Common26 column21 remains true ExcessPorePress; J/n/rho native/derived distinctions retained. No raw PART re-read or full ledger/fixed-sample CSV parse."]
    result.update(inputs=list(h.BOUND.values()) if h else [], files=[h.entry(p) for p in paths.values() if p.exists()] if h else [])
    with check.open("x", encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps(dict(passed=result["passed"], check=str(check)))); return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
