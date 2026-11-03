"""Sealed CSV-only descriptive u-pl/u-pw comparison; never a solver, decoder or new gate."""
import csv, hashlib, json, math, struct
import xml.etree.ElementTree as ET
from pathlib import Path

T = Path(__file__).resolve().parents[1]
C = T.parent
TAG, N, DT, END_STEP = "upl_damp_mid_baseline_r1", 1746, 2. ** -19, 4798782
EVENT, END, OLD_EVENT, OLD_CV = 5243 * DT, END_STEP * DT, .01, .027444522857366895
GATES = {"all5_binary_payload_prefix_exact", "all3_identity_files_exact", "all3_text_prefix_exact", "same_build_program"}
PINS = {
    "tests/support/upl_damp_mid_plot_r1.py": "38089d6e136b70a9cb26f1ca4e6f69f9b59235685a6d3f95ebaf8d81ba7135f9",
    "tests/notes/upl_damp_mid_plot_r1.json": "eb86a04b96c680c358f969bbdda39ab9f0c84fbbae58efe9b006c2faf731f5b6",
    "tests/support/upl_damp_mid_compare_r1.py": "ba556201f6a0d702fbdc13a06cfb902fccc0270f6453be74f6f6fca3f7398013",
    "tests/notes/upl_damp_mid_compare_r1.json": "d85bbd78c026f3975c990e25a7af1a8446e0e4b342786e1bb834a4807fba50ed",
    "figures/full_validation_three.check.json": "83aea715a92c1d7e2b9cbb0aa06cb4bae8c1e3411ce239d62263022853fe7542",
    "figures/full_validation_three_history_data.csv": "d85dec85bf4b4f9735f68843e74015e57cf47c7a1cf8d862468e5b6282c5cdb3",
    "figures/full_validation_three_profiles_data.csv": "8c6223f7d34495dc0358c236a7a9e9a1a8ae213a9c253c3c8bd4c361e11236c4",
    "figures/full_validation_three_metadata.csv": "e83c2651cdcbb718b914e25b7c2795ece93c6dff5798a0bf153e5249f8cf3dd3",
    "figures/full_validation_three_targets.csv": "a40c8843e58edd7317108c8309917483aadd3e83feab0da11730733edd3689af",
    "support/publish_three_permeabilities.py": "4a31a76eb119165eb91301869030977ea90ec4e7db4e1dd6627e7b94dd372421",
    "support/release_case.py": "229f6e6bd781a47d96c64df5a144e5b3d6a777ab4dde39e4cd012350f5d51746",
    "support/compare_precision_q0.py": "c5840f2f8e9cb39acc8458789b3c2e01b60e48fdfa3c464b647c418e72e3268f",
    "CaseTerzaghiConsolidation_q0_PR_full_k1em4_release_GPU_out/published_case.xml": "699c4216d27b4c740bf9922da68963deb7490fbf75bf2651530f15e7c4281259",
}
BOUND = {}
FIELDS = ("kind", "series", "source_csv", "source_row", "native_part", "actual_time_s", "drainage_event_s", "tau_s", "actual_Tv", "Tv_definition", "initial_layer", "initial_z_m", "mean_pressure_Pa", "top_settlement_mm", "bottom_settlement_mm", "layer_pressure_Pa", "classical_mean_pressure_Pa", "classical_top_mm", "classical_bottom_mm", "classical_layer_pressure_Pa", "H1_finite_mean_pressure_Pa", "H1_finite_top_mm", "H1_finite_layer_pressure_Pa", "H0995_finite_mean_pressure_Pa", "H0995_finite_top_mm", "H0995_finite_layer_pressure_Pa")

def need(ok, why):
    if not ok: raise ValueError(why)
def entry(path):
    p = Path(path).resolve(); digest = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): digest.update(block)
    return dict(path=str(p), bytes=p.stat().st_size, sha256=digest.hexdigest())
def bind(e):
    key = str(Path(e["path"]).resolve()).casefold()
    if key not in BOUND: BOUND[key] = entry(e["path"])
    a = BOUND[key]; need(a["sha256"] == e["sha256"].lower() and ("bytes" not in e or a["bytes"] == e["bytes"]), "Changed/conflicting consumed file: " + a["path"])
    return Path(a["path"])
def adopt(path):
    e = entry(path); bind(e); return e
def readjson(e): return json.loads(bind(e).read_text(encoding="utf-8-sig"))
def table(e):
    with bind(e).open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f); need(r.fieldnames and len(set(r.fieldnames)) == len(r.fieldnames), "Duplicate/missing CSV header"); return list(r)
def number(v):
    if v is None or v == "": return None
    x = float(v); need(math.isfinite(x), "Nonfinite plotted value"); return x
def owned(e, parent_log=None):
    c = readjson(e); need(c["direct_native_call"] and c["owned_call_exited"] and c["typed_LASTEXITCODE_captured_immediately"] and type(c["exit_code"]) is int and c["exit_code"] == 0 and not c.get("invocation_failure"), "Sealed typed native exit0 required")
    bind(c["program"]); bind(c["log"] if "log" in c else parent_log); return c

def completed_mid():
    # Read completion receipts BEFORE opening any trajectory CSV; never load a dependency module/dataset.
    pe = adopt(T / "logs/upl_damp_mid_plot_r1.check.json"); p = readjson(pe)
    need(p["stage"] == "upl_damp_mid_plot_r1" and p["passed"] is True and p["physical_acceptance"] is False and not p["additional_scientific_gate"] and not p["solver_decoder_build_or_subprocess_invoked"] and (p["samples"], p["history_rows"], p["profile_rows"]) == (N, N, 500), "Completed own mid plot required, never active/partial data")
    pr = readjson(p["prefix_check"]); need(pr["stage"] == "upl_damp_mid_compare_r1" and pr["case"] == "coarse_prefix" and pr["passed"] is True and pr["physical_acceptance"] is False and pr["mid_samples"] == N and pr["compared_prefix_samples"] == 1469 and set(pr["gates"]) == GATES and all(v is True for v in pr["gates"].values()), "Complete original prefix proof required")
    ce = p["native_check"]; n = readjson(ce); need(n["stage"] == "upl_damp_mid_native_run_r1" and n["passed"] is True and (n["backend"], n["window"], n["history_rows"]) == ("CPU", "coarse", N) and n["original_native_guards_passed"] and n["drainage_nonempty_per_frame_verified"] and n["frozen_build_program_inputs_runtime_unchanged"] and n["physical_acceptance"] is False, "Own native safety closure required")
    need(pr["mid_native_check"] == ce and p["source_run"] == n["source_run"] and all(e == p["source_build"] for e in pr["source_builds"]) and all(e == p["program"] for e in pr["programs"]), "Plot/prefix/native lineage differs")
    r = readjson(p["source_run"]); need(r["stage"] == "upl_damp_mid_run_r1" and r["passed"] is True and (r["backend"], r["threads"], r["configuration"], r["native_frames"], r["planned_completed_steps"], r["planned_end_s"]) == ("CPU", 8, "ReleaseCPU", N, END_STEP, END) and r["public_project_main"] and not r["fixture_or_Run_override"] and r["frozen_build_program_inputs_runtime_unchanged"] and not r["live_production_sources_frozen_by_this_run"] and r["source_build"] == n["source_build"] == p["source_build"] and r["program"] == p["program"], "Own completed frozen project-main run required")
    sc, rc = owned(r["call"]), owned(n["reader_call"]); need(sc["program"] == sc["target_program"] == p["program"] and sc["direct_target_call"] and rc["pure_native_reader"] and not rc["solver_or_build_invoked"], "Actual solver/reader ownership differs")
    b = readjson(p["source_build"]); need(b["stage"] == "upl_damp_build_r2" and b["passed"] is True and b["program"] == p["program"] and b["configuration"] == "ReleaseCPU", "Own frozen build/program differs"); owned(b["project_call"], b["log"])
    q = readjson(n["completion"]); need(q["passed"] and q["stage"] == "upl_damp_mid_native_r1" and (q["samples"], q["native_count"], q["fixed_count"], q["actual_end_s"]) == (N, 1000, 40, END) and q["physical_schema"] == "case02_common26_col21_ExcessPorePress_NOT_wave26", "Own sealed native completion differs")
    files = {Path(e["path"]).name: e for e in p["files"]}; history_e, profiles_e = files["upl_damp_mid_plot_r1_history.csv"], files["upl_damp_mid_plot_r1_profiles.csv"]
    need(all(Path(e["path"]).resolve().parent == (T / "figures").resolve() for e in (history_e, profiles_e)), "Escaped plot CSV")
    native = {Path(e["path"]).name: e for e in n["files"]}; ids = table(native["native_ids.csv"])
    need(len(ids) == 1000 and [int(v["id"]) for v in ids] == list(range(40, 1040)) and [int(v["row"]) for v in ids] == list(range(1000)), "Original soil IDs/order differ")
    need([int(v["id"]) for v in ids if round(number(v["z0"]) / .01 - .5) == 99] == list(range(139, 1040, 100)), "Top material IDs differ")
    x = ET.parse(bind(r["job"]["runtime"])); value = lambda k: float(x.find("./execution/parameters/parameter[@key='" + k + "']").get("value"))
    need((value("Visco"), value("SoilHourglassXi"), value("SoilBoundaryDerivativeSPR"), value("SoilDamping"), value("SoilDampingCoef")) == (0., 0., 0., 1., .02), "New auxiliary settings differ from figure declaration")
    return p, history_e, profiles_e, table(history_e), table(profiles_e), ids

def assemble(p, he, fe, history, profiles):
    oldcheck = readjson(dict(path=str(C / "figures/full_validation_three.check.json"), sha256=PINS["figures/full_validation_three.check.json"]))
    need(oldcheck["publication_verified"] is True and oldcheck["solver_rerun"] is False and oldcheck["history_rows_each"] == 400, "Accepted old publication required")
    oldfiles = {Path(e["path"]).name: e for e in oldcheck["outputs"]}
    rows = lambda leaf: [dict(v, _source_row=i) for i, v in enumerate(table(oldfiles[leaf])) if v["case"] == "k1em4"]
    oh, op, om, ot = (rows("full_validation_three_" + v + ".csv") for v in ("history_data", "profiles_data", "metadata", "targets"))
    need(len(oh) == 400 and len(op) == 1000 and len(om) == 1 and len(ot) == 10, "Old accepted CSV coverage differs")
    need((number(om[0]["k_m_s"]), number(om[0]["dp_m"]), number(om[0]["width_m"]), om[0]["backend"], number(om[0]["hg_xi"]), number(om[0]["solver_dt_s"])) == (1e-4, .01, .1, "GPU", .1, 1e-5), "Old metadata differs")
    x = ET.parse(C / "CaseTerzaghiConsolidation_q0_PR_full_k1em4_release_GPU_out/published_case.xml"); value = lambda k: float(x.find("./execution/parameters/parameter[@key='" + k + "']").get("value"))
    need((value("Visco"), value("SoilHourglassXi"), value("SoilBoundaryDerivativeSPR"), value("SoilDampingCoef")) == (.1, .1, 1., .04), "Old auxiliary settings differ")
    need(len(history) == N and len(profiles) == 500 and [int(v["part"]) for v in history] == list(range(N)), "Mid CSV coverage differs")
    times = [number(v["actual_time_s"]) for v in history]
    need(times[0] == 0. and times[-1] == END and all(a < b for a, b in zip(times, times[1:])) and p["ideal_parameters"]["event_s"] == EVENT, "Mid actual time/event differs")
    for row in history: need(struct.pack("<d", number(row["actual_time_s"])) == struct.pack("<d", int(row["completed_step"]) * DT) and number(row["locked_dt_s"]) == DT, "Mid actual CSV clock differs")
    out = []
    for series, source, data, event in (("u_pl_CPU8", he["path"], history, EVENT), ("u_pw_GPU", str(C / "figures/full_validation_three_history_data.csv"), oh, OLD_EVENT)):
        for index, v in enumerate(data):
            new = series == "u_pl_CPU8"; time = number(v["actual_time_s"] if new else v["time_s"])
            if time > END: continue  # Explicit physical-window selection, never interpolation or time shifting.
            row = dict(kind="history", series=series, source_csv=source, source_row=index if new else v["_source_row"], native_part=int(v["part"] if new else v["native_part"]), actual_time_s=time, drainage_event_s=event, tau_s=time-event, actual_Tv=number(v["nominal_finite_Kw_H1_Tv"] if new else v["actual_tv"]), Tv_definition="finite_Kw_H1" if new else "legacy_classical_H1", mean_pressure_Pa=number(v["pressure_mean_Pa"] if new else v["mean_pressure_pa"]), top_settlement_mm=number(v["top10_settlement_mean_mm"] if new else v["top_settlement_mm"]), bottom_settlement_mm=number(v["bottom10_settlement_mean_mm"] if new else v["bottom_settlement_mm"]))
            if new:
                for h in ("H1", "H0995"):
                    row[h + "_finite_mean_pressure_Pa"] = number(v[h + "_ideal_pressure_mean_Pa"]); row[h + "_finite_top_mm"] = number(v[h + "_ideal_top_material_settlement_mm"])
            else: row.update(classical_mean_pressure_Pa=number(v["mean_theory_pa"]), classical_top_mm=number(v["classical_top_mm"]), classical_bottom_mm=number(v["classical_bottom_mm"]))
            out.append(row)
    oldp = [v for v in op if number(v["target_tv"]) == .25]; newp = [v for v in profiles if number(v["actual_time_s"]) == END]; target = [v for v in ot if number(v["target_tv"]) == .25]
    need(len(oldp) == len(newp) == 100 and len(target) == 1 and all(int(v["native_part"]) == int(target[0]["native_part"]) and number(v["time_s"]) == number(target[0]["time_s"]) and number(v["actual_tv"]) == number(target[0]["actual_tv"]) for v in oldp), "Old actual .25 target/profile differs")
    for data, new in ((newp, True), (oldp, False)):
        for layer, v in enumerate(data):
            need(int(v["initial_material_layer"] if new else v["layer"]) == layer, "Profile material-layer order differs")
            z = number(v["initial_z_m"] if new else v["z0_H"]); need(abs(z-(layer+.5)*.01) <= 64*math.ulp(1.), "Original material layer coordinate differs")
            time = number(v["actual_time_s"] if new else v["time_s"]); event = EVENT if new else OLD_EVENT
            row = dict(kind="profile", series="u_pl_CPU8" if new else "u_pw_GPU", source_csv=fe["path"] if new else str(C / "figures/full_validation_three_profiles_data.csv"), source_row=(profiles.index(v) if new else v["_source_row"]), native_part=int(v["part"] if new else v["native_part"]), actual_time_s=time, drainage_event_s=event, tau_s=time-event, actual_Tv=number(v["nominal_finite_Kw_H1_Tv"] if new else v["actual_tv"]), Tv_definition="finite_Kw_H1" if new else "legacy_classical_H1", initial_layer=layer, initial_z_m=z, layer_pressure_Pa=number(v["pressure_mean_Pa"] if new else v["pressure_pa"]))
            if new:
                for h in ("H1", "H0995"): row[h + "_finite_layer_pressure_Pa"] = number(v[h + "_ideal_pressure_mean_Pa"])
            else: row["classical_layer_pressure_Pa"] = number(v["classical_pa"])
            out.append(row)
    need(sum(v["kind"] == "history" and v["series"] == "u_pl_CPU8" for v in out) == N and sum(v["kind"] == "profile" for v in out) == 200, "Matching CSV coverage differs")
    return out, om[0]

def draw(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.8)); colors = {"u_pl_CPU8": "#2166ac", "u_pw_GPU": "#b35806"}; labels = {"u_pl_CPU8": "u-pl CPU8", "u_pw_GPU": "Retained u-pw GPU"}
    for series in colors:
        h = [r for r in rows if r["kind"] == "history" and r["series"] == series]; pr = [r for r in rows if r["kind"] == "profile" and r["series"] == series]; c = colors[series]; label = labels[series]
        axes[0].plot([r["actual_time_s"] for r in h], [r["mean_pressure_Pa"]/1000 for r in h], color=c, lw=1.3, label=label)
        for key, style, mark in (("top_settlement_mm", "-", "top"), ("bottom_settlement_mm", "--", "bottom")): axes[1].plot([r["actual_time_s"] for r in h], [r[key] for r in h], color=c, ls=style, lw=1.2, label=label+" "+mark)
        axes[2].plot([r["layer_pressure_Pa"]/1000 for r in pr], [r["initial_z_m"] for r in pr], color=c, lw=1.3, label=f"{label}: t={pr[0]['actual_time_s']:.7g}s\nTv={pr[0]['actual_Tv']:.7g} (own definition)")
        refs = (("H1_finite_", "Finite Kw H=1", ":", "#444444"), ("H0995_finite_", "Finite Kw H=.995", "--", "#777777")) if series == "u_pl_CPU8" else (("classical_", "Old classical H=1", "-.", "#8c6d31"),)
        for prefix, name, style, color in refs:
            have = [r for r in h if r.get(prefix+"mean_pressure_Pa") is not None]
            axes[0].plot([r["actual_time_s"] for r in have], [r[prefix+"mean_pressure_Pa"]/1000 for r in have], color=color, ls=style, lw=.8, label=name)
            axes[1].plot([r["actual_time_s"] for r in have], [r[prefix+"top_mm"] for r in have], color=color, ls=style, lw=.8, label=name+" top")
            axes[2].plot([r[prefix+"layer_pressure_Pa"]/1000 for r in pr], [r["initial_z_m"] for r in pr], color=color, ls=style, lw=.9, label=name+" at own t")
    axes[0].set(xlabel="Actual physical time (s)", ylabel="Mean pore pressure (kPa)", title="Own saved samples and references")
    axes[1].set(xlabel="Actual physical time (s)", ylabel="Same-ID settlement, down (mm)", title="Top / bottom original ten IDs")
    axes[2].set(xlabel="Layer mean pore pressure (kPa)", ylabel="Initial material height z0 (m)", title="Two actual profiles near nominal Tv .25")
    for ax in axes: ax.grid(alpha=.25); ax.legend(fontsize=6.7, loc="best"); ax.tick_params(labelsize=8)
    for ax in axes[:2]: ax.axvline(EVENT, color=colors["u_pl_CPU8"], ls=":", lw=.6); ax.axvline(OLD_EVENT, color=colors["u_pw_GPU"], ls=":", lw=.6)
    fig.suptitle("Descriptive constant-k baseline: different complete formulations and stabilization", fontsize=12, y=.97)
    fig.text(.785, .85, "Common nominal inputs\nq0=10000 Pa (unfitted), k=1e-4 m/s\nE=2 MPa, nu=.3, n0=.3, Kw=2e8 Pa\ndp=.01 m, Hnom=1 m; top z0=.995 m\n\nRetained u-pw GPU\nHG xi=.1 / SPR ON / Visco=.1\neta=.04, legacy-rho damping\ndt=10 us; ramp/drain=.01 s\nPublished history DeltaTv=.005\n\nNew u-pl CPU8\nHG OFF / SPR OFF / Visco=0\neta=.02, intrinsic-solid-rho damping\ndt=2^-19 s; event=5243*dt\nJ-derived V/rho, complete-Ace Darcy\nand closed-face BC differ together\n\nReferences differ\nOld: classical incompressible water\nNew: finite Kw, H=1 and .995\nEach at its OWN actual t and z0\n\nNo interpolation / time shift / fit\nNo isolated A/B or new accuracy gate\nSparse saved data are not a stability proof", va="top", fontsize=8, linespacing=1.4)
    fig.text(.39, .025, "Straight segments only connect saved observations. Old samples are the accepted publication subset; no startup/full-history safety claim.\nProfile times and nominal Tv differ; no matched-time error, half-step acceptance or paper-replication claim.", ha="center", fontsize=8)
    fig.subplots_adjust(left=.055, right=.755, bottom=.15, top=.86, wspace=.42)
    with path.open("xb") as f: fig.savefig(f, format="png", dpi=180)
    plt.close(fig)

def main():
    paths = dict(png=T/"figures"/(TAG+".png"), csv=T/"figures"/(TAG+".csv")); check = T/"logs"/(TAG+".check.json")
    need(not check.exists() and not any(p.exists() for p in paths.values()), "Retained outputs/check protected; no overwrite/retry")
    result = dict(stage=TAG, passed=False, physical_acceptance=False, additional_scientific_gate=False, isolated_AB_claim=False, solver_decoder_build_or_subprocess_invoked=False, failure=None)
    try:
        adopt(__file__); adopt(T/"notes"/(TAG+".json"))
        for rel, sha in PINS.items(): bind(dict(path=str(C/rel), sha256=sha))
        p, he, fe, history, profiles, ids = completed_mid(); rows, metadata = assemble(p, he, fe, history, profiles)
        with paths["csv"].open("x", encoding="utf-8", newline="") as f: w=csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
        draw(rows, paths["png"])
        for e in list(BOUND.values()): need(entry(e["path"]) == e, "Consumed file changed during final rehash")
        result.update(passed=True, mid_plot_check=BOUND[str((T/"logs/upl_damp_mid_plot_r1.check.json").resolve()).casefold()], mid_prefix_check=p["prefix_check"], mid_native_check=p["native_check"], mid_source_run=p["source_run"], mid_source_build=p["source_build"], mid_program=p["program"], old_publication_check=BOUND[str((C/"figures/full_validation_three.check.json").resolve()).casefold()], mid_history_rows=N, old_history_rows=sum(r["kind"]=="history" and r["series"]=="u_pw_GPU" for r in rows), profile_rows=200, matching_csv_rows=len(rows), plotted_columns=list(FIELDS), physical_end_s=END, events_s=dict(u_pl=EVENT,u_pw=OLD_EVENT), profile_actual_times_s={s:next(r["actual_time_s"] for r in rows if r["kind"]=="profile" and r["series"]==s) for s in ("u_pl_CPU8","u_pw_GPU")}, reference_parameters=dict(new=p["ideal_parameters"],old=dict(Cv_m2_s=OLD_CV,H_m=1.,finite_Kw=False,source="already published classical CSV, not recomputed")), old_metadata=metadata, top_material_ids=list(range(139,1040,100)), bottom_material_ids=list(range(40,1040,100)), independently_redecoded_old_IDs=False, new_IDs_verified=True, upstream_full_evidence_chain_reexecuted=False, raw_PART_or_native_binaries_reread=False, dependency_module_or_main_executed=False, all_plot_values_in_matching_csv=True, independent_final_rehash_performed=True, visual_review_performed=False)
    except Exception as exc: result["failure"] = str(exc)
    result["limitations"] = ["Different complete frameworks, stabilization, boundary treatment, time steps, reference models and sampling: descriptive comparison only, never isolated dynamic-seepage causality or a new cross-model 5 Pa/.005 mm gate.", "All1746 mid history samples are retained; old history is only the accepted400-row publication subset restricted to t<=mid end, not old7290-frame startup safety. Profiles use old actual Part912 near legacyTv .25 and new exact final profile, without interpolation/time shifting.", "Old IDs/material-layer mapping derives from pinned accepted reader/reducer and CSV provenance; only new native ID CSV is read again. Initial material z0, not moving bins or the analytic surface at1m, defines settlement/profile coordinates.", "Old production-step companion was accepted after recorded short program equivalence, not a newly rerun formal BAT or exact program/source identity with u-pl. Historical mutable source originals/BI4 are not recursively revalidated.", "All references are copied from already sealed CSVs, not newly evaluated theory; finite Kw/ramp/inertia/damping/quadrature and H1/H.995 ambiguities remain. No new mid half/physical/public3D/high-frequency-stability acceptance."]
    result.update(inputs=list(BOUND.values()), files=[entry(v) for v in paths.values() if v.exists()])
    with check.open("x", encoding="utf-8") as f: json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps(dict(passed=result["passed"],check=str(check)))); return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
