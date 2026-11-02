"""Pure descriptive .5s CPU c/h figures after both exact-prefix and full half gates."""
import ast, csv, hashlib, importlib.util, json
from pathlib import Path
from types import SimpleNamespace
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = "upl_damp_long_plot_r1"
EVENT = 5243 * 2. ** -19
TIMES = (EVENT, .125, .25, .5)
WINDOWS = (("early_post", EVENT, .015625), ("ringdown", .015625, .125),
           ("early_consolidation", .125, .25), ("late_saved", .25, .5))
SERIES = (("CPU_c", "coarse", "#2166ac", "-", "CPU eta=.02 coarse"),
          ("CPU_h", "half", "#b35806", "--", "CPU eta=.02 half"))
PINS = {"support/upl_damp_long_compare_r1.py": "c838ed61d940c078339ac5b630718649e625731bd05f25304d80b16f659bd601",
        "notes/upl_damp_long_compare_r1.json": "3155d8dd579ed5d94ee7f5ef4102f710d5d628876d0d671ed798d99dc91a8780",
        "support/upl_damp_plot_r1.py": "2002ba3fda7cbc63338fa05b9dbf0dbaab11eb9fc9194583586ec434cbc96b9b",
        "notes/upl_damp_plot_r1.json": "b64e4e9fc6d506811ede7a2f02b669612c0c723bd6b850a8a3b22c8207ad7a08",
        "support/upl_column_ringdown_plot_r1.py": "b46583a96ea8c7f3dc9b345979983440f8f86b22de50d195458b9417f357577d",
        "notes/upl_column_ringdown_plot_r1.json": "8130d3278f347e44ac5b27dcb8af92f7483a7c24b6b2d39bbd906a291a81e070"}
HALF_GATES = {"pressure_RMS_all_times_le_5Pa", "material_XYZ_difference_all_times_le_0_005mm", "actual_time_difference_le_1e_minus14_s"}
PREFIX_GATES = {"all5_binary_payload_prefix_exact", "all3_identity_files_exact", "all3_text_prefix_exact", "same_build_program"}

def dependencies():
    sources = {rel: (T / rel).read_bytes() for rel in PINS}
    for rel, raw in sources.items():
        if hashlib.sha256(raw).hexdigest() != PINS[rel]: raise ValueError("Pinned offline dependency changed: " + rel)
    rel = "support/upl_damp_long_compare_r1.py"
    h = importlib.util.module_from_spec(importlib.util.spec_from_file_location("frozen_damp_long_exports", T / rel))
    exec(compile(sources[rel], str(T / rel), "exec"), h.__dict__)  # Guarded comparator main is never called.
    rel = "support/upl_column_ringdown_plot_r1.py"; tree = ast.parse(sources[rel], filename=str(T / rel))
    scope = {"np": np, "csv": csv, "Path": Path}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {"PROFILE_STEPS", "PROFILE_LABELS", "RHO_FIELDS"}:
            scope[node.targets[0].id] = ast.literal_eval(node.value)
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "summarize"]
    h.need(len(fn) == 1 and all(k in scope for k in ("PROFILE_STEPS", "PROFILE_LABELS", "RHO_FIELDS")), "Pinned summary closure differs")
    exec(compile(ast.Module(body=fn, type_ignores=[]), str(T / rel), "exec"), scope)
    return h, scope["summarize"]

def proof(h, case):
    e = h.adopt(T / "logs" / ("upl_damp_long_" + case + "_r1.check.json")); p = h.readjson(h.bind(e))
    wanted = HALF_GATES if case == "half" else PREFIX_GATES
    h.need(p["passed"] is True and p["physical_acceptance"] is False and p["stage"] == "upl_damp_long_compare_r1" and p["case"] == case and set(p["gates"]) == wanted and all(v is True for v in p["gates"].values()), "Required full-half/exact-prefix check rejected: " + case)
    for item in p["inputs"] + p["files"]: h.bind(item)
    return e, p

def reduce(h, summary, key, grid, d):
    ctx = SimpleNamespace(readjson=h.readjson, bind=h.bind, need=h.need, N=1469, STEPS=h.STEPS, base=SimpleNamespace(F=h.FIELDS))
    rows, _, rho_gap = summary(ctx, grid, d)  # Exact pinned function and literal closure; old selected profiles ignored.
    sn = h.mapped(d["files"]["soil_n.bin"], (1000, 1, 1469), [("time", "<f8"), ("q", "<f8", (1000,))], 1469)
    h.need(h.base.bits(sn["time"], d["clock"]["time"]).all(), "Native n actual times differ")
    layers = np.rint(d["x0"][:, 2] / .01 - .5).astype(int); hist = d["history"]
    profiles = []; layer_pressure = []
    h.need(len(rows) == len(hist) == 1469, "Incomplete long summary/history")
    for part, row in enumerate(rows):
        q = np.asarray(d["p"]["q"][part]); n = np.asarray(sn["q"][part]); le = float(hist[part]["max_ledger_relative_error"])
        h.need(np.isfinite(n).all() and np.all((n > 0) & (n < 1)) and np.isfinite(le) and 0 <= le <= 5e-13, "Native n/ledger summary differs")
        row.update(series=key, native_n_min=float(n.min()), native_n_mean=float(n.mean()), native_n_max=float(n.max()), native_ledger_max_relative_error=le)
        layer_pressure.append(np.bincount(layers, weights=q[:, 6], minlength=100) / 10.)
        if row["actual_time_s"] in TIMES:
            for layer in range(100):
                take = layers == layer
                profiles.append([key, grid, part, row["actual_time_s"], layer, float(d["x0"][take, 2].mean()), float(q[take, 6].mean()), float(-1000 * (q[take, 2] - d["x0"][take, 2]).mean()), float((q[take, 6] - q[take, 15]).mean()), float(np.sqrt(np.mean(np.sum(q[take, 3:6] ** 2, axis=1))))])
    h.need(len(profiles) == 400, "Four actual saved100-layer profiles missing")
    time = np.array([r["actual_time_s"] for r in rows]); lp = np.asarray(layer_pressure); windows = []
    for label, lo, hi in WINDOWS:
        take = (time >= lo) & (time <= hi); selected = [r for r, keep in zip(rows, take) if keep]; h.need(len(selected) >= 3, "Declared sampled phase missing")
        for field in ("pressure_mean_Pa", "top10_pressure_mean_Pa", "bottom10_pressure_mean_Pa", "interior10_pressure_mean_Pa"):
            v = np.array([r[field] for r in selected]); net = float(v[-1] - v[0]); variation = float(np.abs(np.diff(v)).sum())
            windows.append([key, label, field, lo, hi, len(selected), float(time[take][0]), float(time[take][-1]), float(v.min()), float(v.max()), float(np.ptp(v)), float(v.std()), net, variation, .5 * (variation - abs(net)), float(np.ptp(lp[take], axis=0).max()), max(r["velocity_XYZ_RMS_m_s"] for r in selected)])
    return rows, profiles, windows, rho_gap

def load_reference(h):
    e = h.adopt(T / "logs/upl_case02_flux_load_check_r1.run.json"); r = h.readjson(h.bind(e))
    h.need(r["passed"] is True and r["direct_native_call"] is True and r["typed_LASTEXITCODE_captured_immediately"] is True and r["owned_call_exited"] is True and type(r["exit_code"]) is int and r["exit_code"] == 0 and r["physical_acceptance"] is False, "Retained frozen-load component receipt rejected")
    c = h.readjson(h.bind(r["completion"])); helper = h.readjson(h.bind(r["helper"]))
    h.need(c["passed"] is True, "Retained frozen-load completion rejected")
    for a in helper["author_files"]: h.bind(a)  # Immutable test recipes, not historical mutable production originals.
    se = [a for a in r["files"] if Path(a["path"]).name == "summary.csv"]; h.need(len(se) == 1, "Retained load summary missing")
    with h.bind(se[0]).open(encoding="utf-8-sig", newline="") as f: rows = list(csv.DictReader(f))
    row = [a for a in rows if a["case"] == "1" and float(a["q_Pa"]) == 5000.]; h.need(len(row) == 1, "Retained J1/q5000 reference missing")
    return dict(run=e, completion=r["completion"], helper=r["helper"], summary=se[0], raw_weighted_N=float(row[0]["raw_weighted_N"]), scale=float(row[0]["scale"]), exact_float_order_equivalence_claimed=False)

def load_diagnostic(h, key, grid, d):
    mass = float(np.float32(.21)); v0 = mass / 2100.; kh = np.float32(.018); radius = np.float32(2 * kh)
    radius2 = np.float32(radius * radius); hd = float(kh); bwen = np.float32(-2.7852 / (hd * hd * hd)); hypothetical_q = 10000.
    cd = float(h.readjson(h.bind(d["run"]))["actual_damping_rate_s_inv"]); rows = []
    for time in (0., .125, .25, .5):
        found = np.flatnonzero(d["clock"]["time"] == time); h.need(len(found) == 1, "Diagnostic exact saved time missing")
        part = int(found[0]); q = np.asarray(d["p"]["q"][part]); x, z, j = q[:, 0], q[:, 2], q[:, 8]
        volume = v0 * j; rho = 1000. + 1100. / j; rho_v = rho * volume
        length = np.sqrt(np.sum(q[:, 18:21] ** 2, axis=1)); top = np.isin(q[:, 17], (2., 3.)) & (length > 0) & (q[:, 20] > .35 * length)
        band = z > float(z.max()) - float(radius); acc = np.zeros(1000, dtype=np.float32)
        for i in np.flatnonzero(band):  # Receivers and neighbors use ascending native IDs, NOT production cell order.
            delta = x[i] - x; delta -= .1 * np.rint(delta / .1)
            dx = delta.astype(np.float32); dz = (z[i] - z).astype(np.float32)
            rr2 = np.float32(np.float32(dx * dx) + np.float32(dz * dz)); take = (rr2 <= radius2) & (rr2 >= np.float32(1e-18))
            rad = np.sqrt(rr2[take]).astype(np.float32); qq = np.float32(rad / kh); w = np.float32(np.float32(1) - np.float32(.5) * qq)
            fac = np.float32(bwen * qq)
            for _ in range(3): fac = np.float32(fac * w)
            fac = np.float32(fac / rad)
            pair = np.float32(np.asarray(2. * hypothetical_q * volume[take] / rho[i], dtype=np.float32) * np.float32(fac * dz[take]))
            if len(pair): acc[i] = np.add.accumulate(np.concatenate((np.zeros(1, dtype=np.float32), pair)), dtype=np.float32)[-1]
        raw = sum(float(rho_v[i]) * float(acc[i]) for i in np.flatnonzero(band))
        target = int(top.sum()) * mass * float(np.float32(-hypothetical_q / (2100. * .01)))
        h.need(np.isfinite(raw) and raw != 0 and np.isfinite(target), "Snapshot diagnostic ratio undefined")
        scale = target / raw
        normalized = sum(float(rho_v[i]) * float(np.float32(float(acc[i]) * scale)) for i in np.flatnonzero(band))
        recorded = sum(float(rho_v[i]) * float(q[i, 24]) for i in range(1000))
        damping = cd * sum(float(rho_v[i]) * float(q[i, 5]) for i in range(1000)) / .1
        rows.append(dict(series=key, grid=grid, part=part, actual_time_s=time, hypothetical_q_Pa=hypothetical_q, actual_top_count=int(top.sum()), actual_band_count=int(band.sum()), zmax_m=float(z.max()), float_mass_kg_per_m=mass, V0_m2=v0, float_radius_m=float(radius), float_bwen=float(bwen), IDorder_raw_rhoV_load_N_per_m=raw, retained_float_target_N_per_m=target, scale_target_over_raw=scale, hypothetical_IDorder_normalized_rhoV_load_N_per_m=normalized, Qcancel_Pa=scale * hypothetical_q, recorded_snapshot_rhoV_LoadAce_N_per_m=recorded, native_mean_total_compression_Pa=float((q[:, 6] - q[:, 15]).mean()), descriptive_cd_sum_rhoV_vz_over_width_Pa=damping))
    return rows

def ideal_reference(h, datasets):
    modulus = 1666666.75 + 4. * 769230.8125 / 3.; b = 2e8 / float(np.float32(.3))
    B = b / (modulus + b); cv = B * modulus * float(np.float32(1e-4)) / (1000. * 9.80665); q0 = 10000.
    m = np.arange(100); lam = (2. * m + 1.) * np.pi / 2.; sign = (-1.) ** m
    profiles = []; metrics = []; a, bdata = datasets
    h.need(h.base.bits(a["x0"], bdata["x0"]).all(), "Reference material initial positions differ")
    for key, grid, d in (("CPU_c", "coarse", a), ("CPU_h", "half", bdata)):
        z0 = d["x0"][:, 2]; layers = np.rint(z0 / .01 - .5).astype(int); top = layers == 99
        for label, height in (("nominal_H1", 1.), ("initial_pressure_particle_plane_H0.995", .995)):
            for time in (.125, .25, .5):
                found = np.flatnonzero(d["clock"]["time"] == time); h.need(len(found) == 1, "Ideal reference exact saved time missing")
                part = int(found[0]); actual = np.asarray(d["p"]["q"][part]); decay = np.exp(-cv * lam ** 2 * (time - EVENT) / height ** 2)
                phase = z0[:, None] * lam / height
                pressure = 2. * B * q0 * np.sum(np.cos(phase) * (sign * decay / lam), axis=1)
                integral = 2. * B * q0 * height * np.sum(np.sin(phase) * (sign * decay / lam ** 2), axis=1)
                settlement = 1000. * (q0 * z0 - integral) / modulus; observed = -1000. * (actual[:, 2] - z0)
                stheory = float(settlement[top].mean()); sobserved = float(observed[top].mean())
                metrics.append(dict(series=key, grid=grid, convention=label, H_m=height, part=part, actual_time_s=time, tau_since_step_drain_s=time - EVENT, pressure_RMS_difference_Pa=float(np.sqrt(np.mean((actual[:, 6] - pressure) ** 2))), pressure_RMS_over_q0_percent=float(100 * np.sqrt(np.mean((actual[:, 6] - pressure) ** 2)) / q0), actual_top_material_settlement_mm=sobserved, ideal_top_material_settlement_mm=stheory, top_material_settlement_difference_percent=100 * (sobserved - stheory) / stheory, all_material_settlement_RMS_difference_mm=float(np.sqrt(np.mean((observed - settlement) ** 2)))))
                if key == "CPU_c":
                    for layer in range(100):
                        take = layers == layer
                        profiles.append(dict(convention=label, H_m=height, actual_time_s=time, initial_material_layer=layer, initial_z_m=float(z0[take].mean()), ideal_pressure_mean_Pa=float(pressure[take].mean()), ideal_material_settlement_mean_mm=float(settlement[take].mean())))
    return profiles, metrics, dict(M_Pa=modulus, B=B, Cv_m2_s=cv, q0_Pa=q0, odd_modes=100, conventions_H_m=[1., .995], acceptance_gate=False)

def draw(h, histories, profiles, references, paths):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator, ScalarFormatter
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .25})
    panels = (("pressure_mean_Pa", "Mean pore pressure (kPa)", .001), ("top_minus_bottom_pressure_Pa", "Top-bottom pore pressure (kPa)", .001),
              ("top10_settlement_mean_mm", "Top material settlement, down (mm)", 1), ("velocity_XYZ_RMS_m_s", "Soil XYZ speed RMS (m/s)", 1),
              ("J_mean", "Native J mean", 1), ("native_n_mean", "Native soil n mean", 1),
              ("saved_theta_RMS_s_inv", "Saved last-stage theta RMS (1/s)", 1), ("effective_compression_zz_mean_Pa", "Stored effective compression zz (kPa)", .001),
              ("total_compression_zz_mean_Pa", "Derived total compression zz (kPa)", .001), ("native_ledger_max_relative_error", "Native ledger relative error", 1))
    fig, axes = plt.subplots(5, 2, figsize=(13, 15), sharex=True)
    for key, _, color, style, label in SERIES:
        rows = histories[key]
        for ax, (field, ylabel, scale) in zip(axes.flat, panels):
            ax.plot([r["actual_time_s"] for r in rows], [r[field] * scale for r in rows], color=color, ls=style, lw=1.2, label=label)
            ax.set_ylabel(ylabel); ax.axvline(EVENT, color=".45", ls=":", lw=.7); ax.axvline(.125, color=".6", ls=":", lw=.6); ax.axvline(.25, color=".75", ls=":", lw=.6)
    for ax in axes[-1]: ax.set_xlabel("Actual native time (s)")
    fig.suptitle("One eta=.02 constant-k candidate: actual CPU coarse / half through 0.5 s", y=.995)
    fig.legend(*axes.flat[0].get_legend_handles_labels(), ncol=2, loc="upper center", bbox_to_anchor=(.5, .969))
    fig.text(.5, .012, "Both exact1277-prefix proofs and full1469 half gates precede this descriptive view. Endpoint finite-Kw Tv~0.0134 (H=1m bookkeeping), not full theory acceptance.\nRaw1469 samples; late cadence1.953125ms cannot certify all high-frequency ringdown. Theta is saved last-stage; no force replay or pressure-rate observation.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .052, 1, .935)); fig.savefig(paths["history_png"], dpi=180); plt.close(fig)
    fig, axes = plt.subplots(4, 4, figsize=(15, 12), sharey=True)
    variables = ((6, "Pore pressure (kPa)", .001), (7, "Settlement, down (mm)", 1), (8, "Derived total compression (kPa)", .001), (9, "Layer XYZ speed RMS (m/s)", 1))
    for col, time in enumerate(TIMES):
        axes[0, col].set_title(("Event/pre-open\n" if time == EVENT else "") + "Actual t=" + format(time, ".12g") + " s")
        for key, _, color, style, label in SERIES:
            a = np.asarray([r[4:] for r in profiles if r[0] == key and r[3] == time], dtype=float)
            h.need(a.shape == (100, 6) and np.isfinite(a).all() and np.array_equal(a[:, 0], np.arange(100)), "Complete100-layer profile missing")
            for row, (column, xlabel, scale) in enumerate(variables):
                axes[row, col].plot(a[:, column - 4] * scale, a[:, 1], color=color, ls=style, lw=1.2, label=label); axes[row, col].set_xlabel(xlabel)
        for row in range(4):
            ax = axes[row, col]; ax.xaxis.set_major_locator(MaxNLocator(nbins=3, min_n_ticks=2)); fmt = ScalarFormatter(useOffset=False, useMathText=True)
            if row == 3: fmt.set_powerlimits((0, 0))
            ax.xaxis.set_major_formatter(fmt); ax.tick_params(axis="x", labelsize=8, pad=3)
        if time != EVENT:
            for label, color, style, title in (("nominal_H1", ".3", ":", "Ideal quasi-static H=1m"), ("initial_pressure_particle_plane_H0.995", ".6", "-.", "Ideal quasi-static H=.995m")):
                selected = [r for r in references if r["convention"] == label and r["actual_time_s"] == time]
                for row, field, scale in ((0, "ideal_pressure_mean_Pa", .001), (1, "ideal_material_settlement_mean_mm", 1.)):
                    axes[row, col].plot([r[field] * scale for r in selected], [r["initial_z_m"] for r in selected], color=color, ls=style, lw=1., label=title)
    for ax in axes[:, 0]: ax.set_ylabel("Initial material z0 (m)")
    fig.suptitle("Actual material profiles: event, 0.125 / 0.25 / 0.5 s; CPU coarse / half only", y=.995)
    fig.legend(*axes[0, 1].get_legend_handles_labels(), ncol=2, loc="upper center", bbox_to_anchor=(.5, .968))
    fig.text(.5, .012, "Each point averages ten original soil IDs (speed: RMS); no temporal interpolation/smoothing/clipping. Grey p/settlement: finite-Kw ideal uniform traction / step drain only.\nBoth H conventions shown at the SAME initial material z0; neither is fitted or an exact dynamic-ramp/band-load solution or acceptance gate. No event theory / invented0.5s GPU/noaux.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .06, 1, .925)); fig.savefig(paths["profiles_png"], dpi=180); plt.close(fig)

def main():
    paths = {k: T / "figures" / (TAG + suffix) for k, suffix in {"history_png": "_history.png", "profiles_png": "_profiles.png", "history_csv": "_history.csv", "profiles_csv": "_profiles.csv", "windows_csv": "_windows.csv", "qdiagnostic_csv": "_qdiagnostic.csv", "reference_profiles_csv": "_reference_profiles.csv", "reference_metrics_csv": "_reference_metrics.csv"}.items()}; check = T / "logs" / (TAG + ".check.json")
    if check.exists() or any(p.exists() for p in paths.values()): raise ValueError("Retained descriptive output protected")
    h = None; result = dict(stage=TAG, passed=False, physical_acceptance=False, additional_scientific_gate=False, solver_decoder_build_or_Git_invoked=False, failure=None)
    try:
        h, summary = dependencies()
        for rel in (*PINS, "support/" + TAG + ".py", "notes/" + TAG + ".json"): h.adopt(T / rel)
        ce, cp = proof(h, "coarse_prefix"); he, hp = proof(h, "half_prefix"); pe, pp = proof(h, "half")
        a, b = h.dataset("coarse"), h.dataset("half")
        h.need(pp["prefix_checks"] == [ce, he] and pp["native_checks"] == [a["check"], b["check"]] and pp["source_runs"] == [a["run"], b["run"]] and a["check"] in cp["native_checks"] and b["check"] in hp["native_checks"], "Paired/prefix proof actual dataset identity differs")
        h.need(pp["samples"] == a["n"] == b["n"] == 1469 and pp["native_count"] == 1000 and a["build"] == b["build"] and a["program"] == b["program"], "Complete same-build half coverage differs")
        retained_load_reference = load_reference(h)
        histories = {}; profiles = []; windows = []; rho_gaps = {}; qdiagnostic = []
        for (key, grid, *_), data in zip(SERIES, (a, b)):
            histories[key], pr, wr, rho_gaps[key] = reduce(h, summary, key, grid, data); profiles.extend(pr); windows.extend(wr)
            qdiagnostic.extend(load_diagnostic(h, key, grid, data))
        reference_profiles, reference_metrics, reference_parameters = ideal_reference(h, (a, b))
        for leaf, rows in (("qdiagnostic_csv", qdiagnostic), ("reference_profiles_csv", reference_profiles), ("reference_metrics_csv", reference_metrics)):
            with paths[leaf].open("x", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        with paths["history_csv"].open("x", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(histories["CPU_c"][0])); w.writeheader(); w.writerows(r for key, *_ in SERIES for r in histories[key])
        for leaf, header, rows in (("profiles_csv", ["series", "grid", "part", "actual_time_s", "initial_material_layer", "initial_z_m", "pressure_mean_Pa", "settlement_mean_mm", "derived_total_compression_mean_Pa", "velocity_XYZ_RMS_m_s"], profiles),
                                   ("windows_csv", ["series", "window", "pressure_field", "declared_lo_s", "declared_hi_s", "saved_samples", "actual_first_s", "actual_last_s", "min_Pa", "max_Pa", "sampled_peak_to_peak_Pa", "sampled_temporal_STD_Pa", "net_change_Pa", "sampled_total_variation_Pa", "sampled_reversal_variation_Pa", "max_layer_sampled_peak_to_peak_Pa", "max_saved_XYZ_speed_RMS_m_s"], windows)):
            with paths[leaf].open("x", encoding="utf-8", newline="") as f: w = csv.writer(f); w.writerow(header); w.writerows(rows)
        draw(h, histories, profiles, reference_profiles, paths)
        for e in list(h.base.BOUND.values()): h.need(h.entry(e["path"]) == e, "Consumed input changed during descriptive review")
        result.update(passed=True, prefix_checks=[ce, he], half_check=pe, native_checks=[a["check"], b["check"]], source_runs=[a["run"], b["run"]], source_builds=[a["build"], b["build"]], samples_each=1469, native_soil_each=1000, history_rows=2938, profile_rows=800, window_rows=32, qdiagnostic_rows=len(qdiagnostic), retained_load_reference=retained_load_reference, qdiagnostic_additional_physical_gate=False, reference_profile_rows=len(reference_profiles), reference_metric_rows=len(reference_metrics), ideal_quasistatic_reference=reference_parameters, actual_profile_times_s=list(TIMES), declared_event_s=EVENT, half_metrics={k: pp[k] for k in ("max_pressure_RMS_Pa", "max_material_XYZ_displacement_difference_mm", "max_actual_time_difference_s")}, native_rho_summary_vs_J_derived_gap_descriptive=rho_gaps, endpoint_Tv_approx_annotation=.0134, no_temporal_resampling_smoothing_or_clipping=True, visual_review_performed=False)
    except Exception as exc: result["failure"] = str(exc)
    result["limitations"] = ["Saved native-export description only; prefix and half gates are separate prerequisite evidence, not continuum validation.", "Sparse late1.953125ms output cannot certify all high-frequency behavior; phase p2p/STD include evolving trends and unweighted sampling.", "Only two actual CPU1469 trajectories. No0.5s GPU/noaux, pdot or force-stage load/flux/energy observation is fabricated.", "Snapshot q10000 load reconstruction is hypothetical (also at t0), uses endpoint geometry and native-ID float accumulation rather than actual force-stage cell order; it is not an applied-load change, 0ULP replay, or substitute q0/theory. Recorded rhoV*LoadAce and cd*sum(rhoV*vz)/width are descriptive, not force-stage or momentum-balance proof.", "Ideal finite-Kw reference is an explicit100-mode quasi-static uniform-traction/instant-step-drain model at q0=10000, NOT Qcancel. H1 and initial-pressure-particle-plane H.995 are both unfitted conventions; comparison uses each initial material z0, not analytic surface settlement versus a different native material point. No event reference, speed/theta/stress theory, exact dynamic-ramp/band-load claim or reference-error acceptance limit.", "Common26 column21 is actualExcessPorePress. Native n/rho and savedtheta are distinguished from derived total stress.", "Tv~.0134 finiteKw/H1 is an annotation, not 2Tv or direct Lian2023 reproduction; drainage plane/band forcing/J feedback/dynamic ramp remain reference limitations."]
    result.update(inputs=list(h.base.BOUND.values()) if h else [], files=[h.entry(p) for p in paths.values() if p.exists()] if h else [])
    with check.open("x", encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps(dict(passed=result["passed"], check=str(check)))); return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
