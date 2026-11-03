"""Pure interrupted-prefix review/plots; never runs a solver, decoder or build."""
import ast, csv, hashlib, importlib.util, json, re, struct
from pathlib import Path
from types import SimpleNamespace
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG, N, PREFIX, DT, LAST = "upl_damp_mid_partial_review_r2", 1673, 1469, 2. ** -19, 3604480
EVENT, END, ORIGINAL_END = 5243 * DT, LAST * DT, 4798782 * DT
PROFILE_TIMES = (.5, 1.84375, 3.6875, 5.5, 6.875)
PINS = {
    "support/upl_damp_mid_plot_r1.py": "38089d6e136b70a9cb26f1ca4e6f69f9b59235685a6d3f95ebaf8d81ba7135f9",
    "notes/upl_damp_mid_plot_r1.json": "eb86a04b96c680c358f969bbdda39ab9f0c84fbbae58efe9b006c2faf731f5b6",
    "support/upl_damp_mid_partial_r1.cpp": "81e7b2c95d68244d01be3849696274f4fdfdffa4aa6c8f88640d186435de20a0",
    "notes/upl_damp_mid_partial_r1.json": "7c2f09a0c488f28502be1cf12c10a957fa44b266679f7968a89570b4718ac971",
}
CAPTIONS = {
    "One CPU8 coarse trajectory: fallback accepted dt, nominal finite-Kw Tv~0.25":
        "Interrupted CPU8 trajectory: retained through 6.875 s / nominal finite-Kw Tv~0.1877",
    "Complete 1746/1469 typed prefix required; NOT a new 9.15 s half/CPU-GPU/theory acceptance.":
        "Preserved 1673 frames / exact 1469-frame prefix; original 1746-frame plan unfinished.\nIndependent half evidence only through .5 s.",
    "Five exact saved material profiles; both unfitted H conventions shown":
        "Interrupted trajectory: five retained material profiles; both unfitted H conventions shown",
    "Same initial z0 for actual/ideal; no pressure/stress load fitting or exact dynamic-ramp/band-load claim.":
        "Same initial z0/q0, no fit; source solver exit unknown and original 9.15 s plan unfinished. No physical acceptance.",
}


def functions():
    """Definitions only: no retained or new dataset/main is invoked here."""
    raw = {}
    for rel, sha in PINS.items():
        raw[rel] = (T / rel).read_bytes()
        if hashlib.sha256(raw[rel]).hexdigest() != sha: raise ValueError("Pinned source/note changed: " + rel)
    rel = "support/upl_damp_mid_plot_r1.py"
    p = importlib.util.module_from_spec(importlib.util.spec_from_file_location("partial_frozen_plot", T / rel))
    exec(compile(raw[rel], str(T / rel), "exec"), p.__dict__)
    h, summary = p.dependencies()  # Imports pinned comparer/old-loader DEFINITIONS and extracts unmodified summarize.
    for rel, sha in PINS.items(): h.need(h.adopt(T / rel)["sha256"] == sha, "Pinned identity differs")
    steps = h.STEPS[:N].copy()
    h.need(len(h.STEPS) == 1746 and h.STEPS[-1] == 4798782 and steps[-1] == LAST, "Original/preserved schedule differs")
    scope = dict(np=np, csv=csv, Path=Path, SimpleNamespace=SimpleNamespace, N=N, EVENT=EVENT,
                 PROFILE_TIMES=PROFILE_TIMES, CONVENTIONS=p.CONVENTIONS, ideal=p.ideal, CV=p.CV)
    tree = ast.parse(raw["support/upl_damp_mid_plot_r1.py"])
    selected = [v for v in tree.body if isinstance(v, ast.FunctionDef) and v.name in {"reduce", "draw"}]
    class PresentationOnly(ast.NodeTransformer):
        def __init__(self): self.count, self.labels = 0, 0
        def visit_Constant(self, node):
            if type(node.value) is int and node.value == 1542:
                self.count += 1; return ast.copy_location(ast.Constant(value=int(np.count_nonzero(steps > 5243))), node)
            if isinstance(node.value, str):
                value = node.value
                for old, new in CAPTIONS.items():
                    if old in value: value = value.replace(old, new); self.labels += 1
                return ast.copy_location(ast.Constant(value=value), node)
            return node
    edit = PresentationOnly()
    body = edit.visit(ast.Module(body=selected, type_ignores=[])); ast.fix_missing_locations(body)
    h.need(len(selected) == 2 and edit.count == 1 and edit.labels == 4, "Only one coverage count/four captions may change")
    exec(compile(body, str(T / "support/upl_damp_mid_plot_r1.py"), "exec"), scope)
    return h, p, summary, scope["reduce"], scope["draw"], steps


def partial(h, steps):
    need, bind, adopt, readjson = h.need, h.bind, h.adopt, h.readjson
    ce = adopt(T / "logs/upl_damp_mid_partial_r1.native.json"); c = readjson(bind(ce))
    need(c["stage"] == "upl_damp_mid_partial_native_r1" and c["passed"] is True and c["partial_decode_only"] is True
         and c["independent_final_rehash_performed"] is True and c["failure"] is None
         and c["source_solver_exit_code"] is None and c["source_solver_completion_verified"] is False
         and c["original_window_completed"] is False and c["physical_acceptance"] is False
         and c["solver_invoked"] is False and c["original_full_gate_adopted"] is False
         and c["independent_half_performed"] is False, "Only successful pure partial decode, never successful solver reconstruction")
    for e in c["inputs"] + c["files"]: bind(e)
    ae = c["interruption_audit"]; need(Path(ae["path"]).resolve() == (T / "logs/upl_mid_gpu_interruption_r1.check.json").resolve(), "Own interruption audit required")
    a = readjson(bind(ae)); mid = a["mid"]
    need(a["stage"] == "upl_mid_gpu_interruption_r1" and a["interruption_audited"] is True
         and a["all_observed_owned_processes_absent"] is True and a["real_exit_code"] is None
         and a["typed_exit_evidence_available"] is False and a["normal_completion_or_failure_exit_invented"] is False
         and a["old_full_gate_preserved"] is True and a["physical_acceptance"] is False
         and mid["planned_window_completed"] is False and mid["native_clock_or_safety_checked"] is False
         and (mid["planned_frames"], mid["planned_completed_steps"], mid["observed_raw_frames"],
              mid["last_console_part"], mid["last_console_time_s"], mid["last_console_completed_steps"]) == (1746, 4798782, N, N - 1, END, LAST),
         "Interruption evidence must retain original plan/unknown source exit")
    for e in a["verified_input_bindings"] + a["retained_output_files"] + a["retained_logs"]: bind(e)
    text = bind(mid["run_out"]).read_text(encoding="utf-8-sig")
    need("[Simulation finished" not in text and "OpenMP(Threads:8)" in text and re.search(r"(?m)^Part_1672\s+6\.875000\s+3604480\s", text), "Recorded CPU8 interrupted console evidence differs")
    need(len(a["observations"]) == 2 and all(not v["project_processes"] for v in a["observations"]), "Two recorded survivor-free observations required")
    b = readjson(bind(mid["source_build"])); m = readjson(bind(mid["prepared"])); gate = readjson(bind(mid["admission"]))
    need(b["stage"] == "upl_damp_build_r2" and b["passed"] and b["configuration"] == "ReleaseCPU"
         and b["objects_include_project_main"] and b["exact_object_basename_closure"] and len(b["objects"]) == 86
         and len(b["source_snapshot"]) == 265 and len(b["runtime"]) == 4, "Sealed original project-main build86/265/4 differs")
    pc = readjson(bind(b["project_call"]))
    need(pc["direct_native_call"] is True and pc["typed_LASTEXITCODE_captured_immediately"] is True
         and pc["owned_call_exited"] is True and type(pc["exit_code"]) is int and pc["exit_code"] == 0
         and pc.get("invocation_failure") is None and pc["program"] == b["build_tool"],
         "Actual original project typed0 receipt required; it has no embedded log Entry")
    bind(pc["program"]); bind(b["log"]); bind(b["binlog"])
    need(m["stage"] == "upl_damp_mid_prepare_r1" and m["passed"] and m["prepared"] and len(m["jobs"]) == 1
         and m["source_build"] == mid["source_build"] and m["source_program"] == b["program"]
         and gate["stage"] == "upl_damp_mid_admission_r1" and gate["passed"]
         and gate["allowed_jobs"] == ["upl_damp_mid_CPU_coarse_r1"] and gate["physical_acceptance"] is False,
         "Original preparation/admission, not an invented completed Run, required")
    job = m["jobs"][0]
    need((job["dt_s"], job["steps"], job["expected_samples"], job["event_completed_step"], job["event_part"]) == (DT, 4798782, 1746, 5243, 203)
         and job["backend"] == "CPU" and job["threads"] == 8 and job["damping_coef"] == .02 and not job["step_candidate_adopted"], "Original declared physics/plan differs")
    table = job["saved_clock_table"]
    need(len(table) == 1746, "Original clock table differs")
    for i, row in enumerate(table):
        n = int(h.STEPS[i]); need((row["part"], row["completed_steps"], row["saved_step"]) == (i, n, n - 1 if n else 0)
            and struct.pack("<d", row["time_s"]) == struct.pack("<d", n * DT), "Original planned integer/dyadic clock differs")
    snapshots = [v["snapshot"] for v in b["source_snapshot"]]
    for v in b["source_snapshot"] + [b["documentation_snapshot"], b["case_readme_snapshot"]]:
        need(all(v["original"][k] == v["snapshot"][k] for k in ("bytes", "sha256")), "As-of-build archive attribution differs")
    for e in snapshots + b["objects"] + [v["copy"] for v in b["runtime"]] + [b["program"]]: bind(e)
    helper = readjson(bind(c["helper"])); expected = [e for e in b["objects"] if Path(e["path"]).name.lower() != "main.obj"]
    need(helper["stage"] == "upl_damp_mid_partial_reader_build_r1" and helper["passed"] and helper["kind"] == "reader"
         and helper["configuration"] == "ReleaseCPU" and helper["source_build"] == mid["source_build"]
         and helper["actual_headers_archived_not_live"] and helper["exact_link_closure_verified"]
         and helper["frozen_build_program_inputs_runtime_unchanged"] and helper["objects"] == expected
         and helper["CPU_non_main_objects"] == 85 and len(helper["actual_project_headers"]) == 8
         and helper["link_object_count"] == 86 and len(helper["libraries"]) == 17 and len(helper["runtime"]) == 4
         and helper["source_snapshots265"] == snapshots and helper["program"] == c["program"] and not helper["program_run"],
         "Actual archived-header pure-reader85+1/17/4 closure differs")
    for key in ("inputs", "author_files", "objects", "source_snapshots265", "actual_project_headers", "libraries", "tools"):
        for e in helper[key]: bind(e)
    for key in ("program", "helper_object", "compiler_dependency_record", "neutral_include"): bind(helper[key])
    cc, lc, call = h.owned(helper["compile_call"]), h.owned(helper["link_call"]), h.owned(c["call"])
    objects = [str(Path(x).resolve()).casefold() for x in lc["arguments"] if x.lower().endswith(".obj")]
    need(len(objects) == len(set(objects)) == 86 and set(objects) == {str(Path(e["path"]).resolve()).casefold() for e in expected + [helper["helper_object"]]}, "Actual reader link object closure differs")
    need([Path(x).name.lower() for x in lc["arguments"] if x.lower().endswith(".lib")] == [Path(e["path"]).name.lower() for e in helper["libraries"]], "Actual ordered17 libraries differ")
    dep = readjson(bind(helper["compiler_dependency_record"]))["Data"]; archive = Path(helper["archived_header_include_root"]).resolve()
    includes = {str(Path(x).resolve()).casefold() for x in dep["Includes"]}
    headers = {str(Path(x).resolve()).casefold() for x in dep["Includes"] if Path(x).resolve().parent == archive}
    need(Path(dep["Source"]).resolve() == (T / "support/upl_damp_mid_partial_r1.cpp").resolve()
         and headers == {str(Path(e["path"]).resolve()).casefold() for e in helper["actual_project_headers"]}
         and all(e in snapshots for e in helper["actual_project_headers"])
         and helper["neutral_include"]["sha256"] == "9f6668bfe3d1bbcca7c45c58809f7062c21fcb46baae76f0a2a1b0ef3ca56d38"
         and str(Path(helper["neutral_include"]["path"]).resolve()).casefold() in includes, "Actual archived headers/newCPP/neutral dependency differs")
    authored = [str(Path(x).resolve()).casefold() for x in dep["Includes"] if Path(x).resolve().parent == (T / "support").resolve()]
    need(authored == [str(Path(helper["neutral_include"]["path"]).resolve()).casefold()], "Only the immutable neutral authored include is permitted")
    for pair in helper["runtime"]:
        need(pair["original"] in [v["copy"] for v in b["runtime"]] and all(pair["original"][k] == pair["copy"][k] for k in ("bytes", "sha256")), "Reader runtime copies differ")
        bind(pair["original"]); bind(pair["copy"])
    out = Path(c["outdir"]).resolve(); data = (T / "outputs/upl_damp_mid_CPU_coarse_r1/data").resolve()
    need(out == (T / "outputs/upl_damp_mid_partial_r1_native").resolve() and call["program"] == helper["program"]
         and call["arguments"] == ["--read", "CPU", str(data), "partial", str(out)] and call["pure_reader"] is True
         and call["actual_solver_call"] is False and call["source_solver_exit_code"] is None
         and call["source_solver_completion_verified"] is False, "Pure decoder invocation/source-exit meaning differs")
    raw = [e for e in a["retained_output_files"] if re.fullmatch(r"Part_\d{4}\.bi4", Path(e["path"]).name)]
    need(len(raw) == N and {Path(e["path"]).name for e in raw} == {f"Part_{i:04d}.bi4" for i in range(N)}
         and all(Path(e["path"]).resolve().parent == data for e in raw), "Actual sealed1673 raw sequence/ownership differs")
    need({x.name for x in data.glob("Part_*.bi4")} == {f"Part_{i:04d}.bi4" for i in range(N)}, "Current raw PART membership changed after sealing")
    files = {Path(e["path"]).name: e for e in c["files"]}
    need(len(files) == 13 and set(files) == set(h.retained.parent.EXPORTS) | {"completion.json"}
         and all(Path(e["path"]).resolve().parent == out for e in files.values())
         and files["completion.json"] == c["completion"]
         and {x.resolve() for x in out.rglob("*") if x.is_file()} == {Path(e["path"]).resolve() for e in files.values()}, "Exactly own13 diagnostic leaves required")
    q = readjson(bind(c["completion"]))
    exact = dict(stage="upl_damp_mid_partial_r1", backend="CPU_public", window="interrupted_partial", preset="partial", grid="c",
                 model="constant", conductivity_model=0, conductivity_Ck=0, samples=N, original_expected_samples=1746,
                 preserved_samples=N, native_count=1000, fixed_count=40, total_native_count=1040, physical_columns=26,
                 native_total_arrays=22, native_dynamic_double_arrays=6, planned_end_s=ORIGINAL_END, planned_completed_steps=4798782,
                 actual_end_s=END, actual_saved_completed_steps=LAST, soil_ledger_checks=N * 1000, fixed_public_zero_marker_checks=N * 40,
                 all_native_J_theta_rows=N * 1040, noninitial_signed_dterror_intervals=N - 1, post_open_frames=N - 204,
                 post_open_drained_particle_checks=(N - 204) * 10, max_activeDrainCount=10, post_open_completed_step_threshold=5243,
                 source_solver_tag="upl_damp_mid_CPU_coarse_r1", source_solver_exit_code=None, source_solver_exit_verified=False,
                 source_solver_normal_completion_verified=False, original_planned_window_completed=False,
                 full_consolidation_acceptance=False, full_window_gates_adopted_or_relaxed=False,
                 physical_acceptance=False, interrupted_evidence_only=True, partial_decode_safety_passed=True)
    need(all(q.get(k) == v for k, v in exact.items()) and q["passed"] is True
         and q["physical_schema"] == h.retained.parent.SCHEMA and q["dt_s"] == DT
         and q["max_ledger_relative_error"] <= 5e-13 and q["max_noninitial_signed_dterror_s"] <= 1e-14
         and all(q[k] is True for k in ("PART_typed_public_metadata_verified", "public_master_on", "public_schema", "native_PosDiv_present",
                  "native_PosDiv_is_float", "native_V_rho_k_present", "no_exclusions", "all_exported_physical_fields_finite",
                  "initial_rest_and_decimal_lattice_verified", "double_stress_and_float_display_verified",
                  "declared_saved_completed_steps_exact", "actual_time_step_locked_dt_exact")), "Original typed safety or interrupted-completion semantics differ")
    p = h.mapped(files["physical.bin"], (1000, 26, N), [("time", "<f8"), ("q", "<f8", (1000, 26))], N)
    clock = h.mapped(files["clock.bin"], (N, 28), [("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")], N)
    jt = h.mapped(files["common_j_theta.bin"], (1040, 2, N), [("time", "<f8"), ("q", "<f8", (1040, 2))], N)
    por = h.mapped(files["soil_n.bin"], (1000, 1, N), [("time", "<f8"), ("q", "<f8", (1000,))], N)
    with bind(files["original15.bin"]).open("rb") as f:
        need(struct.unpack("<III", f.read(12)) == (1040, 15, N) and files["original15.bin"]["bytes"] == 12 + N * 166408, "Original15 header/length differs")
    with bind(files["columns.csv"]).open(encoding="utf-8-sig", newline="") as f: columns = list(csv.DictReader(f))
    need([v["name"] for v in columns] == h.FIELDS and [int(v["column"]) for v in columns] == list(range(26)), "Common26 field order differs")
    ids = np.genfromtxt(bind(files["native_ids.csv"]), delimiter=",", names=True, encoding="utf-8")
    fixed = np.genfromtxt(bind(files["fixed_ids.csv"]), delimiter=",", names=True, encoding="utf-8")
    need(np.array_equal(ids["id"], np.arange(40, 1040)) and np.array_equal(ids["row"], np.arange(1000))
         and np.array_equal(fixed["id"], np.arange(40)) and np.array_equal(fixed["row"], np.arange(40)), "Native1040 identity/order differs")
    x0 = np.column_stack([ids[k] for k in ("x0", "y0", "z0")]).astype("<f8"); times = steps * DT
    need(np.array_equal(clock["step"], np.where(steps > 0, steps - 1, 0)) and h.bits(clock["time"], times).all()
         and h.bits(clock["dt"], np.full(N, DT)).all() and all(h.bits(v["time"], times).all() for v in (p, jt, por))
         and h.bits(p["q"][0, :, :3], x0).all(), "Original actual dyadic clock/zero-based Step/cross-export time differs")
    need(np.isfinite(clock["error"]).all() and np.all(clock["error"][1:] <= 1e-14)
         and np.all(clock["error"][1:] != -np.finfo(float).max), "Original signed necessary-step intervals rejected")
    with bind(files["history.csv"]).open(encoding="utf-8-sig", newline="") as f: history = list(csv.DictReader(f))
    need(len(history) == N, "Partial history count differs")
    for i, row in enumerate(history):
        need((int(row["part"]), int(row["completed_step"]), int(row["saved_step"]), int(row["activeDrainCount"])) ==
             (i, int(steps[i]), int(clock["step"][i]), 10 if steps[i] > 5243 else 0)
             and all(struct.pack("<d", float(row[k])) == struct.pack("<d", float(v)) for k, v in
                     (("time_s", times[i]), ("dt_s", DT), ("signed_dterror_s", clock["error"][i]))), "History/actual native clock/drain count differs")
    return dict(check=ce, audit=ae, build=mid["source_build"], program=b["program"], files=files,
                p=p, clock=clock, x0=x0, n=N, job=job, history=history, completion=c["completion"], reader_call=c["call"])


def prefix(h, old, new):
    h.need(new["build"] == old["build"] and new["program"] == old["program"] and old["n"] == PREFIX
           and h.bits(new["clock"]["time"][:PREFIX], old["clock"]["time"]).all(), "Same frozen build/program/1469 exact clocks required")
    rows = []
    for leaf, (offset, count) in h.BINARY.items():
        equal, first = h.prefix_bytes(new["files"][leaf], old["files"][leaf], offset, PREFIX * count)
        rows.append([leaf, "payload_after_independently_validated_header", PREFIX * count, PREFIX, equal, first])
    for leaf in h.IDENTITY:
        equal = all(new["files"][leaf][k] == old["files"][leaf][k] for k in ("bytes", "sha256"))
        rows.append([leaf, "whole_file", old["files"][leaf]["bytes"], None, equal, None])
    for leaf in h.TEXT:
        equal, first = h.prefix_bytes(new["files"][leaf], old["files"][leaf], 0, old["files"][leaf]["bytes"])
        rows.append([leaf, "entire_retained_file_is_new_beginning", old["files"][leaf]["bytes"], PREFIX, equal, first])
    h.need(len(rows) == 11 and all(v[4] for v in rows), "Original full1469 binary/identity/text prefix failed; do not plot")
    return rows


def main():
    paths = {k: T / "figures" / (TAG + v) for k, v in dict(history_png="_history.png", profiles_png="_profiles.png",
            history_csv="_history.csv", profiles_csv="_profiles.csv").items()}
    check, metrics = T / "logs" / (TAG + ".check.json"), T / "logs" / (TAG + "_prefix.csv")
    if check.exists() or metrics.exists() or any(p.exists() for p in paths.values()): raise ValueError("Retained diagnostic artifacts protected")
    h = None; result = dict(stage=TAG, passed=False, partial_diagnostic_only=True, physical_acceptance=False,
        original_full_gate_adopted=False, original_window_completed=False, source_solver_exit_code=None,
        source_solver_completion_verified=False, solver_decoder_build_or_subprocess_invoked=False, failure=None)
    try:
        h, original_plot, summary, reduce, draw, steps = functions()
        h.adopt(__file__); h.adopt(T / "notes" / (TAG + ".json"))
        try: old = h.retained.dataset("coarse")  # Only accepted same-dt1469 data, no old main/full-mid dataset.
        finally: h.merge_retained_cache()
        new = partial(h, steps); exact = prefix(h, old, new)
        with metrics.open("x", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["export", "comparison", "compared_bytes", "prefix_frames", "exact", "first_differing_payload_or_file_byte"]); w.writerows(exact)
        view = SimpleNamespace(readjson=h.readjson, bind=h.bind, need=h.need, mapped=h.mapped, bits=h.bits, STEPS=steps, FIELDS=h.FIELDS)
        rows, profiles, rho_gap = reduce(view, summary, new)
        h.need(len(rows) == N and len(profiles) == 500 and all(t in set(steps * DT) for t in PROFILE_TIMES), "Actual preserved history/profiles differ")
        for leaf, data in (("history_csv", rows), ("profiles_csv", profiles)):
            with paths[leaf].open("x", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
        draw(rows, profiles, paths)
        for e in list(h.BOUND.values()): h.need(h.entry(e["path"]) == e, "Consumed artifact changed during independent final rehash")
        result.update(passed=True, interruption_audit=new["audit"], native_check=new["check"], native_completion=new["completion"],
            pure_reader_call=new["reader_call"], source_build=new["build"], program=new["program"],
            accepted_old_native_check=old["check"], native_checks=[new["check"], old["check"]], programs=[new["program"], old["program"]],
            source_builds=[new["build"], old["build"]], compared_prefix_samples=PREFIX, preserved_samples=N,
            original_expected_samples=1746, original_planned_end_s=ORIGINAL_END, actual_saved_end_s=END,
            actual_saved_completed_steps=LAST, exact_prefix_rows=exact, all5_binary_payload_prefix_exact=True,
            all3_identity_files_exact=True, all3_text_prefix_exact=True, same_build_program=True,
            history_rows=len(rows), profile_rows=len(profiles), reference_post_open_times=N-204,
            actual_profile_times_s=list(PROFILE_TIMES), actual_profile_nominal_H1_Tv=[(t-EVENT)*original_plot.CV for t in PROFILE_TIMES],
            ideal_parameters=dict(M_Pa=original_plot.M,storage_Pa=original_plot.BULK,B=original_plot.B,Cv_m2_s=original_plot.CV,
                                  q0_Pa=original_plot.Q0,odd_modes=100,H_m=[1.,.995],event_s=EVENT,acceptance_gate=False),
            AST_reuse=dict(reduce_count_literals_changed=1,draw_caption_replacements=4,old_globals_modified=False,
                           ideal_and_summarize_bodies_modified=False,old_full_dataset_or_main_called=False),
            native_rho_summary_vs_J_derived_gap_descriptive=rho_gap, visual_review_performed=False,
            independent_final_rehash_performed=True, unique_consumed_files=len(h.BOUND))
    except Exception as exc: result["failure"] = str(exc)
    result["limits"] = [
        "Interrupted source solver: no actual solver exit receipt and original1746-frame/9.15s plan incomplete. This successful decode/prefix/plot check is not a successful Run or full-window/physical acceptance.",
        "Only the retained original1469-frame .5s coarse/half evidence exists; no6.875s half, CPU-GPU or complete consolidation proof.",
        "The100-mode finite-Kw uniform traction/instant step-drain references use actual material z0 and unchanged q0 with both unfitted H1/H.995. They are descriptive, not exact dynamic ramp/band/J-inertia/damping theory.",
        "31.25ms late saves cannot establish unsaved high-frequency stability, all-time force/flux/energy or the cause of the interruption. All true native fields/clock/ledger remain intact.",
        "Raw PARTs are hash-bound through the independent interruption/native owners, not parsed by Python. Source program association uses frozen build/observations, not invented completed solver evidence.",
    ]
    result.update(inputs=list(h.BOUND.values()) if h else [],
        files=([h.entry(metrics)] if metrics.exists() else []) + [h.entry(p) for p in paths.values() if p.exists()] if h else [])
    with check.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps(dict(passed=result["passed"], check=str(check)))); return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
