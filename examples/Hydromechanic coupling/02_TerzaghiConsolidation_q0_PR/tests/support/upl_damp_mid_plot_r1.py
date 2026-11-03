"""One descriptive CPU coarse mid-window view, only after its complete1746/1469 prefix proof."""
import ast, csv, hashlib, importlib.util, json
from pathlib import Path
from types import SimpleNamespace
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG, N = "upl_damp_mid_plot_r1", 1746
EVENT = 5243 * 2. ** -19
PROFILE_TIMES = (.5, 1.84375, 3.6875, 7.34375, 4798782 * 2. ** -19)
M = 1666666.75 + 4. * 769230.8125 / 3.
BULK = 2e8 / float(np.float32(.3))
B = BULK / (M + BULK)
CV = B * M * float(np.float32(1e-4)) / (1000. * 9.80665)
Q0 = 10000.
CONVENTIONS = (("H1", 1., "#555555", "--"), ("H0995", .995, "#9b6b30", ":"))
PINS = {"support/upl_damp_mid_compare_r1.py": "ba556201f6a0d702fbdc13a06cfb902fccc0270f6453be74f6f6fca3f7398013",
        "notes/upl_damp_mid_compare_r1.json": "d85bbd78c026f3975c990e25a7af1a8446e0e4b342786e1bb834a4807fba50ed",
        "support/upl_column_ringdown_plot_r1.py": "b46583a96ea8c7f3dc9b345979983440f8f86b22de50d195458b9417f357577d",
        "notes/upl_column_ringdown_plot_r1.json": "8130d3278f347e44ac5b27dcb8af92f7483a7c24b6b2d39bbd906a291a81e070"}
GATES = {"all5_binary_payload_prefix_exact", "all3_identity_files_exact", "all3_text_prefix_exact", "same_build_program"}

def dependencies():
    sources = {rel: (T / rel).read_bytes() for rel in PINS}
    for rel, raw in sources.items():
        if hashlib.sha256(raw).hexdigest() != PINS[rel]: raise ValueError("Pinned source/note changed: " + rel)
    rel = "support/upl_damp_mid_compare_r1.py"
    h = importlib.util.module_from_spec(importlib.util.spec_from_file_location("frozen_mid_exports", T / rel))
    exec(compile(sources[rel], str(T / rel), "exec"), h.__dict__)  # New dataset() only; never any main or retained dataset.
    for rel, raw in sources.items():
        e = dict(path=str((T / rel).resolve()), bytes=len(raw), sha256=PINS[rel]); key = e["path"].casefold()
        if key in h.BOUND: h.need(all(h.BOUND[key][k] == e[k] for k in ("bytes", "sha256")), "Conflicting pinned identity")
        else: h.BOUND[key] = e
    rel = "support/upl_column_ringdown_plot_r1.py"; tree = ast.parse(sources[rel]); literal = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {"PROFILE_STEPS", "PROFILE_LABELS", "RHO_FIELDS"}:
            literal[node.targets[0].id] = ast.literal_eval(node.value)
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "summarize"]
    h.need(len(fn) == 1 and len(literal) == 3, "Pinned pure summary/literal closure differs")
    scope = dict(np=np, csv=csv, Path=Path, **literal)
    exec(compile(ast.Module(body=fn, type_ignores=[]), str(T / rel), "exec"), scope)  # Function body and old5243 drain declaration UNMODIFIED.
    return h, scope["summarize"]

def ideal(z0, times, height):
    """100 odd modes, uniform traction/instantaneous step drain; unfitted initial material coordinates."""
    lam = (2. * np.arange(100) + 1.) * np.pi / 2.; sign = (-1.) ** np.arange(100)
    decay = np.exp(-CV * np.outer(times - EVENT, lam ** 2) / height ** 2)
    phase = np.outer(z0, lam) / height
    pressure = 2. * B * Q0 * ((decay * (sign / lam)) @ np.cos(phase).T)
    integral = 2. * B * Q0 * height * ((decay * (sign / lam ** 2)) @ np.sin(phase).T)
    return pressure, 1000. * (Q0 * z0[None, :] - integral) / M

def reduce(h, summary, d):
    ctx = SimpleNamespace(readjson=h.readjson, bind=h.bind, need=h.need, N=N, STEPS=h.STEPS, base=SimpleNamespace(F=h.FIELDS))
    rows, _, rho_gap = summary(ctx, "coarse", d)
    sn = h.mapped(d["files"]["soil_n.bin"], (1000, 1, N), [("time", "<f8"), ("q", "<f8", (1000,))], N)
    h.need(h.bits(sn["time"], d["clock"]["time"]).all(), "Native n clock differs")
    times = np.asarray(d["clock"]["time"]); post_parts = np.flatnonzero(times > EVENT); z0 = d["x0"][:, 2]
    layers = np.rint(z0 / .01 - .5).astype(int); top = layers == 99
    references = {}
    for label, height, _, _ in CONVENTIONS:
        pressure, settlement = ideal(z0, times[post_parts], height)
        h.need(np.isfinite(pressure).all() and np.isfinite(settlement).all(), "Nonfinite ideal diagnostic")
        references[label] = dict(p=pressure, s=settlement)
    for part, row in enumerate(rows):
        q = np.asarray(d["p"]["q"][part]); hist = d["history"][part]; n = np.asarray(sn["q"][part]); le = float(hist["max_ledger_relative_error"])
        ux = 1000. * (q[:, 0] - d["x0"][:, 0]); total = q[:, 6] - q[:, 15]
        h.need(np.isfinite(n).all() and np.all((n > 0) & (n < 1)) and np.isfinite(le) and 0 <= le <= 5e-13, "Original native n/ledger guard rejected")
        row.update(native_n_min=float(n.min()), native_n_mean=float(n.mean()), native_n_max=float(n.max()), native_ledger_max_relative_error=le,
                   native_current_volume_total_m2=float(hist["native_current_volume_total_m2"]), native_rho_V_mass_kg_per_m=float(hist["native_rho_V_mass_kg_per_m"]),
                   saved_step=int(d["clock"]["step"][part]), locked_dt_s=float(d["clock"]["dt"][part]), signed_dterror_s=float(d["clock"]["error"][part]),
                   material_ux_mean_mm=float(ux.mean()), material_ux_RMS_mm=float(np.sqrt(np.mean(ux ** 2))), material_ux_abs_max_mm=float(np.abs(ux).max()),
                   stored_sigma_xz_RMS_Pa=float(np.sqrt(np.mean(q[:, 12] ** 2))), total_compression_zz_STD_Pa=float(total.std()),
                   saved_rhoV_LoadAce_z_N_per_m=float(hist["final_J_weighted_retained_load_z_N_per_m"]), nominal_finite_Kw_H1_Tv=(row["actual_time_s"] - EVENT) * CV if row["actual_time_s"] > EVENT else None)
        for label, *_ in CONVENTIONS:
            for field in ("pressure_mean_Pa", "top_material_settlement_mm", "pressure_RMS_error_Pa", "top_material_settlement_error_mm", "all_material_settlement_RMS_error_mm"): row[label + "_ideal_" + field] = None
    for index, part in enumerate(post_parts):
        q = np.asarray(d["p"]["q"][part]); observed = -1000. * (q[:, 2] - z0)
        for label, *_ in CONVENTIONS:
            rp, rs = references[label]["p"][index], references[label]["s"][index]
            rows[part].update({label + "_ideal_pressure_mean_Pa": float(rp.mean()), label + "_ideal_top_material_settlement_mm": float(rs[top].mean()),
                              label + "_ideal_pressure_RMS_error_Pa": float(np.sqrt(np.mean((q[:, 6] - rp) ** 2))),
                              label + "_ideal_top_material_settlement_error_mm": float((observed[top] - rs[top]).mean()),
                              label + "_ideal_all_material_settlement_RMS_error_mm": float(np.sqrt(np.mean((observed - rs) ** 2)))})
    profiles = []
    for time in PROFILE_TIMES:
        found = np.flatnonzero(times == time); h.need(len(found) == 1, "Declared exact actual profile time absent"); part = int(found[0]); index = int(np.flatnonzero(post_parts == part)[0]); q = np.asarray(d["p"]["q"][part])
        for layer in range(100):
            take = layers == layer; ux = 1000. * (q[take, 0] - d["x0"][take, 0]); total = q[take, 6] - q[take, 15]
            row = dict(part=part, actual_time_s=time, nominal_finite_Kw_H1_Tv=(time - EVENT) * CV, initial_material_layer=layer, initial_z_m=float(z0[take].mean()),
                       pressure_mean_Pa=float(q[take, 6].mean()), settlement_mean_mm=float(-1000. * (q[take, 2] - z0[take]).mean()), total_compression_zz_mean_Pa=float(total.mean()), total_compression_zz_STD_Pa=float(total.std()),
                       material_ux_mean_mm=float(ux.mean()), material_ux_RMS_mm=float(np.sqrt(np.mean(ux ** 2))), material_ux_abs_max_mm=float(np.abs(ux).max()), stored_sigma_xz_RMS_Pa=float(np.sqrt(np.mean(q[take, 12] ** 2))))
            for label, *_ in CONVENTIONS:
                row[label + "_ideal_pressure_mean_Pa"] = float(references[label]["p"][index, take].mean())
                row[label + "_ideal_settlement_mean_mm"] = float(references[label]["s"][index, take].mean())
            profiles.append(row)
    h.need(len(rows) == N and len(profiles) == 500 and len(post_parts) == 1542, "Actual1746/500profile/1542post coverage differs")
    return rows, profiles, rho_gap

def draw(rows, profiles, paths):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import MaxNLocator
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .25}); time = np.array([r["actual_time_s"] for r in rows]); post = time > EVENT
    fig, axes = plt.subplots(3, 2, figsize=(13, 11), sharex=True)
    for ax, field, title, scale in ((axes[0, 0], "pressure_mean_Pa", "Mean native pore pressure (kPa)", .001), (axes[0, 1], "top10_settlement_mean_mm", "Top material settlement, down (mm)", 1)):
        ax.plot(time, [r[field] * scale for r in rows], color="#2166ac", lw=1.3, label="Actual CPU8 coarse"); ax.set_ylabel(title)
    for label, height, color, style in CONVENTIONS:
        legend = "Ideal H=" + str(height) + "m"
        for ax, field, scale in ((axes[0, 0], "pressure_mean_Pa", .001), (axes[0, 1], "top_material_settlement_mm", 1), (axes[1, 0], "pressure_RMS_error_Pa", 1), (axes[1, 1], "top_material_settlement_error_mm", 1)):
            ax.plot(time[post], [r[label + "_ideal_" + field] * scale for r in rows if r["actual_time_s"] > EVENT], color=color, ls=style, lw=1.1, label=legend)
    axes[1, 0].set_ylabel("Pore-pressure RMS difference from ideal (Pa)"); axes[1, 1].set_ylabel("Top material settlement minus ideal (mm)")
    for field, style, label in (("total_compression_zz_mean_Pa", "-", "Mean"), ("total_compression_zz_STD_Pa", "--", "Spatial STD")): axes[2, 0].plot(time, [r[field] for r in rows], color="#2166ac", ls=style, label=label)
    axes[2, 0].set_ylabel("Derived total compression zz (Pa)")
    for field, style, label in (("material_ux_RMS_mm", "-", "RMS"), ("material_ux_abs_max_mm", "--", "Maximum absolute")): axes[2, 1].plot(time, [r[field] for r in rows], color="#b35806", ls=style, label=label)
    axes[2, 1].set_ylabel("Native material x-x0 difference (mm)")
    for ax in axes.flat: ax.axvline(EVENT, color=".65", ls=":", lw=.6); ax.legend(fontsize=8)
    for ax in axes[-1]: ax.set_xlabel("Actual native time (s)")
    fig.suptitle("One CPU8 coarse trajectory: fallback accepted dt, nominal finite-Kw Tv~0.25", y=.995)
    fig.text(.5, .012, "Complete 1746/1469 typed prefix required; NOT a new 9.15 s half/CPU-GPU/theory acceptance. Actual eta=.02, HG/SPR/viscosity/other auxiliary damping OFF.\nIdeal 100-mode uniform traction/step drain at q0=10000 Pa and initial material z0; no fitted q/H. Late 31.25 ms samples cannot certify unsaved oscillations.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .065, 1, .96))
    with paths["history_png"].open("xb") as stream: fig.savefig(stream, format="png", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(15, 10), sharey=True); colors = ("#2166ac", "#b35806", "#1b7837", "#762a83", "#d73027"); handles = []
    for time, color in zip(PROFILE_TIMES, colors):
        rs = [r for r in profiles if r["actual_time_s"] == time]; z0 = [r["initial_z_m"] for r in rs]; tv = (time - EVENT) * CV
        handles.append(Line2D([], [], color=color, label=f"actual t={time:.8g}s / Tv~{tv:.4g}"))
        for col, (label, height, *_rest) in enumerate(CONVENTIONS):
            for row, field, ref, scale in ((0, "pressure_mean_Pa", label + "_ideal_pressure_mean_Pa", .001), (1, "settlement_mean_mm", label + "_ideal_settlement_mean_mm", 1)):
                axes[row, col].plot([r[field] * scale for r in rs], z0, color=color, lw=1.2)
                axes[row, col].plot([r[ref] * scale for r in rs], z0, color=color, ls="--", lw=.9)
            axes[0, col].set_title(f"Pressure / ideal H={height}m"); axes[0, col].set_xlabel("Pore pressure (kPa)"); axes[1, col].set_title(f"Material settlement / ideal H={height}m"); axes[1, col].set_xlabel("Settlement, down (mm)")
        for row, field in ((0, "total_compression_zz_mean_Pa"), (1, "material_ux_RMS_mm")): axes[row, 2].plot([r[field] for r in rs], z0, color=color, lw=1.2)
    axes[0, 2].set_title("Actual derived total compression"); axes[0, 2].set_xlabel("Layer mean p-sigma_zz (Pa)"); axes[1, 2].set_title("Actual horizontal material difference"); axes[1, 2].set_xlabel("Layer RMS x-x0 (mm)")
    for ax in axes.flat: ax.xaxis.set_major_locator(MaxNLocator(nbins=4, min_n_ticks=2)); ax.tick_params(axis="x", labelsize=8)
    for ax in axes[:, 0]: ax.set_ylabel("Initial material z0 (m)")
    handles += [Line2D([], [], color=".3", label="Actual", ls="-"), Line2D([], [], color=".3", label="Ideal", ls="--")]
    fig.legend(handles=handles, ncol=3, loc="upper center", bbox_to_anchor=(.5, .965), fontsize=8)
    fig.suptitle("Five exact saved material profiles; both unfitted H conventions shown", y=.995)
    fig.text(.5, .012, "Ten original IDs/layer; x difference panel shows RMS, not a signed mean hiding staggering. CSV retains full actual clocks and signed/RMS/max x, sigma_xz and total-stress STD.\nTv labels are rounded nominal H1 values, not interpolated targets. Same initial z0 for actual/ideal; no pressure/stress load fitting or exact dynamic-ramp/band-load claim.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .075, 1, .86))
    with paths["profiles_png"].open("xb") as stream: fig.savefig(stream, format="png", dpi=180)
    plt.close(fig)

def main():
    paths = {k: T / "figures" / (TAG + v) for k, v in dict(history_png="_history.png", profiles_png="_profiles.png", history_csv="_history.csv", profiles_csv="_profiles.csv").items()}; check = T / "logs" / (TAG + ".check.json")
    if check.exists() or any(p.exists() for p in paths.values()): raise ValueError("Retained plot output protected")
    h = None; result = dict(stage=TAG, passed=False, physical_acceptance=False, additional_scientific_gate=False, solver_decoder_build_or_subprocess_invoked=False, failure=None)
    try:
        h, summary = dependencies(); h.adopt(__file__); h.adopt(T / "notes" / (TAG + ".json"))
        pe = h.adopt(T / "logs/upl_damp_mid_prefix_r1.check.json"); proof = h.readjson(h.bind(pe))
        h.need(proof["passed"] is True and proof["physical_acceptance"] is False and proof["stage"] == "upl_damp_mid_compare_r1" and proof["case"] == "coarse_prefix" and proof["compared_prefix_samples"] == 1469 and proof["mid_samples"] == N and set(proof["gates"]) == GATES and all(v is True for v in proof["gates"].values()), "Own complete1746/1469 prefix proof required")
        for e in proof["inputs"] + proof["files"]: h.bind(e)
        d = h.dataset()  # Exactly one actual coarse trajectory, not a cloned/fake half or an old dataset.
        h.need(proof["mid_native_check"] == d["check"] and d["check"] in proof["native_checks"] and d["run"] in proof["source_runs"] and len(proof["source_builds"]) == len(proof["programs"]) == 2 and all(e == d["build"] for e in proof["source_builds"]) and all(e == d["program"] for e in proof["programs"]) and d["n"] == N, "Actual prefix/native/build/program identity differs")
        rows, profiles, rho_gap = reduce(h, summary, d)
        for leaf, data in (("history_csv", rows), ("profiles_csv", profiles)):
            with paths[leaf].open("x", encoding="utf-8", newline="") as f: w = csv.DictWriter(f, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
        draw(rows, profiles, paths)
        for e in list(h.BOUND.values()):
            actual = h.entry(e["path"]); h.need(actual["bytes"] == e["bytes"] and actual["sha256"] == e["sha256"], "Consumed artifact changed during independent final rehash")
        result.update(passed=True, prefix_check=pe, native_check=d["check"], source_run=d["run"], source_build=d["build"], program=d["program"], actual_trajectories=1, samples=N, soil=1000, fixed=40, history_rows=len(rows), profile_rows=len(profiles), reference_post_open_times=1542, reference_material_evaluations_each_H=1542000, actual_profile_times_s=list(PROFILE_TIMES), actual_profile_nominal_H1_Tv=[(t-EVENT)*CV for t in PROFILE_TIMES], ideal_parameters=dict(M_Pa=M,storage_Pa=BULK,B=B,Cv_m2_s=CV,q0_Pa=Q0,odd_modes=100,H_m=[1.,.995],event_s=EVENT,acceptance_gate=False), native_rho_summary_vs_J_derived_gap_descriptive=rho_gap, consumed_unique_files=len(h.BOUND), independent_final_rehash_performed=True, old_dataset_or_main_called=False, new_half_or_CPU_GPU_validation=False, visual_review_performed=False)
    except Exception as exc: result["failure"] = str(exc)
    result["limitations"] = ["One actual coarse trajectory; prefix/saved safety is not a new 9.15 s half, full/theory/general-boundary acceptance.", "100-mode ideal finite-Kw uniform traction/instant-step drain at both unfitted H conventions is diagnostic, not exact dynamic-ramp/kernel-band/current-J inertia/damping truth or direct Lian2023 reproduction. Early truncation/transient effects are not an accuracy gate.", "Actual/ideal displacement uses identical initial material z0, never an analytic surface at a different coordinate. q0 remains 10000, no Qcancel/load/H fit.", "Native x-x0 is the saved coordinate difference without invented periodic unwrapping; interpret possible wrap crossings before calling it cumulative material drift. Sigma_xz and spatial total-stress STD are descriptive, not a new guard.", "Late 31.25 ms saves cannot certify unsaved high-frequency stability. All native J/n/rho/velocity/stress/ledger remain in CSV; saved LoadAce/current-J endpoint telemetry is not a force-stage load or energy proof.", "No raw PART reread/reparse or full ledger/fixed_samples CSV parsing. Common26 column21 remains actualExcessPorePress."]
    result.update(inputs=list(h.BOUND.values()) if h else [], files=[h.entry(p) for p in paths.values() if p.exists()] if h else [])
    with check.open("x", encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps(dict(passed=result["passed"],check=str(check)))); return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
