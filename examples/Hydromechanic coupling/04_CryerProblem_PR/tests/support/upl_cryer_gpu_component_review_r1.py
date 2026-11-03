"""Pure offline GPU component/metadata/CSV/memcheck review; never run a producer or decoder."""
import argparse, csv, hashlib, json, math, re, types
from pathlib import Path

T = Path(__file__).resolve().parents[1]
STAGE = "upl_cryer_gpu_component_review_r1"
PINS = {
    "support/upl_cryer_cpu_component_review_r1.py": (17112, "ebb4d4f55cece72deb948d718b39300a057a23d92a6fa5900276b3f225ab815b"),
    "notes/upl_cryer_cpu_component_review_r1.json": (3885, "94f28b4d9336b1f4194ca9256ca7ad916d2c3bb568db85f47cfb6f9a4ac9ca58"),
}
LEAVES = {"CfgInit_Domain.vtk", "CfgInit_MapCells.vtk", "Run.out", "completion.json", "summary.csv", "samples.csv", "data/Part_Head.ibi4", "data/PartOut_000.obi4"}

def definitions():
    rel = "support/upl_cryer_cpu_component_review_r1.py"; path = T / rel; raw = path.read_bytes()
    if (len(raw), hashlib.sha256(raw).hexdigest()) != PINS[rel]: raise ValueError("Pinned metadata/CSV definitions changed")
    base = types.ModuleType("frozen_cpu_component_review_definitions"); base.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), base.__dict__)  # Definitions/imports only: __name__ is NOT __main__.
    for name, (size, sha) in PINS.items(): base.bind(dict(path=str(T/name), bytes=size, sha256=sha))
    return base

def textlog(path):
    raw = Path(path).read_bytes()
    return raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig", errors="strict")

def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames): raise ValueError("Duplicate/missing CSV header")
        return list(reader)

def review(h, configuration):
    need, bind, adopt, readjson = h.need, h.bind, h.adopt, h.readjson
    debug = configuration == "Debug"; tag = "upl_cryer_gpu_component_" + configuration + "_probe_r1"
    source = adopt(T/"logs"/(tag+".run.json")); r = readjson(bind(source))
    need(r["stage"] == "upl_cryer_gpu_component_run_r1" and r["configuration"] == configuration and r["kind"] == "non_advancing_private_GPU3D_component" and r["passed"] is True and r["typed_owned_tool_exit0"] is True and r["basic_completion_verified"] is True and r["deep_component_review_completed"] is False and r["frozen_build_program_inputs_runtime_unchanged"] is True and r["component_call_failure"] is None and r["basic_analysis_failure"] is None and r["post_binding_failure"] is None, "Only a completed own successful basic call seal is accepted")
    need(r["physical_acceptance"] is False and r["public_3D_admitted"] is False and r["solver_trajectory_started"] is False and r["live_production_sources_frozen_by_this_run"] is False and r["canonical_programs_rechecked"] is False and r["component_target_exit_independently_captured"] is (not debug), "Run scope/target-exit attribution differs")
    for e in r["inputs"] + r["files"]: bind(e)
    call = h.owned(r["call"]); helper_e = r["helper"]; helper = readjson(bind(helper_e))
    need(helper["stage"] == "upl_cryer_gpu_component_build_r1" and helper["passed"] is True and helper["status"] == "frozen_cryer_GPU_component_linked_not_run" and helper["configuration"] == configuration and helper["kind"] == "component" and helper["actual_headers_archived_not_live"] is True and helper["frozen_build_program_inputs_runtime_unchanged"] is True and helper["exact_link_closure_verified"] is True and helper["GPU_non_main_objects"] == 110 and helper["link_object_count"] == 111 and len(helper["objects"]) == 110 and len(helper["retained_build_objects111"]) == 111 and len(helper["source_snapshots265"]) == 265 and len(helper["libraries"]) == 18 and len(helper["runtime"]) == 4, "Sealed GPU110+1/265/library18/runtime4 helper required")
    for key in ("inputs", "author_files", "source_snapshots265", "actual_project_headers", "objects", "retained_build_objects111", "libraries", "tools"):
        for e in helper[key]: bind(e)
    for key in ("program", "source_build", "compiler_dependency_record", "helper_object", "documentation_snapshot", "case_readme_snapshot", "neutral_include", "retained_compiler_recipe"): bind(helper[key])
    need(r["source_build"] == helper["source_build"] and r["program"] == helper["program"] == call["target_program"], "Run/target/helper/build attribution differs")
    build = readjson(bind(helper["source_build"])); snapshots = [v["snapshot"] for v in build["source_snapshot"]]
    need(build["stage"] == "upl_damp_build_r2" and build["passed"] is True and build["configuration"] == configuration and len(build["objects"]) == 111 and build["objects"] == helper["retained_build_objects111"] and snapshots == helper["source_snapshots265"] and len(snapshots) == 265 and build["documentation_snapshot"]["snapshot"] == helper["documentation_snapshot"] and build["case_readme_snapshot"]["snapshot"] == helper["case_readme_snapshot"], "Actual selected archived source/build closure differs")
    for pair in build["source_snapshot"] + [build["documentation_snapshot"], build["case_readme_snapshot"]]:
        need(all(pair["original"][k] == pair["snapshot"][k] for k in ("bytes", "sha256")), "Recorded as-of-build archive identity differs")  # Never hash historical live originals.
    project = readjson(bind(build["project_call"]))
    need(project["direct_native_call"] is True and project["owned_call_exited"] is True and project["typed_LASTEXITCODE_captured_immediately"] is True and type(project["exit_code"]) is int and project["exit_code"] == 0 and project.get("invocation_failure") is None and project["program"] == build["build_tool"], "Original selected project build was not owned typed0")
    for e in (build["build_tool"], build["program"], build["log"], build["binlog"]): bind(e)
    expected = [e for e in build["objects"] if Path(e["path"]).name.lower() != "main.obj"]
    need(expected == helper["objects"] and len(expected) == 110 and len({Path(e["path"]).name.lower() for e in expected}) == 110, "Exact non-main object membership differs")
    cc, lc = h.owned(helper["compile_call"]), h.owned(helper["link_call"])
    linked = [str(Path(a).resolve()).casefold() for a in lc["arguments"] if a.lower().endswith(".obj")]
    need(len(linked) == len(set(linked)) == 111 and set(linked) == {str(Path(e["path"]).resolve()).casefold() for e in expected + [helper["helper_object"]]}, "Actual linker110+1 membership differs")
    need([str(Path(a).resolve()).casefold() for a in lc["arguments"] if a.lower().endswith(".lib")] == [str(Path(e["path"]).resolve()).casefold() for e in helper["libraries"]], "Actual ordered18 library arguments differ")
    dep = readjson(bind(helper["compiler_dependency_record"]))["Data"]; archive = Path(helper["archived_header_include_root"]).resolve(); includes = {str(Path(v).resolve()).casefold() for v in dep["Includes"]}; neutral = helper["neutral_include"]
    headers = {str(Path(v).resolve()).casefold() for v in dep["Includes"] if Path(v).resolve().parent == archive}
    need(Path(dep["Source"]).resolve() == (T/"support/upl_cryer_gpu_component_r1.cpp").resolve() and neutral["sha256"] == "9f6668bfe3d1bbcca7c45c58809f7062c21fcb46baae76f0a2a1b0ef3ca56d38" and str(Path(neutral["path"]).resolve()).casefold() in includes and headers == {str(Path(e["path"]).resolve()).casefold() for e in helper["actual_project_headers"]} and all(e in snapshots for e in helper["actual_project_headers"]), "Actual source/single neutral/archived-header dependencies differ")
    support_roots = ((T/"support").resolve(), (T.parent.parent/"02_TerzaghiConsolidation_q0_PR/tests/support").resolve())
    authored = [v for v in dep["Includes"] if Path(v).resolve().parent in support_roots]
    need(len(authored) == 1 and Path(authored[0]).resolve() == Path(neutral["path"]).resolve(), "Extra authored dependency beyond the single neutral include")
    for pair in helper["runtime"]:
        need(pair["original"] in [v["copy"] for v in build["runtime"]] and all(pair["original"][k] == pair["copy"][k] for k in ("bytes", "sha256")), "Runtime must derive from selected frozen build copy")
        bind(pair["original"]); bind(pair["copy"])
    note_e = next(e for e in helper["author_files"] if Path(e["path"]).name == "upl_cryer_gpu_component_r1.json")
    declaration = readjson(bind(note_e))["retained_input_provenance"]; xml, seed = (T.parent/declaration[k] for k in ("runtime", "seed"))
    for path, name in ((xml, "runtime"), (seed, "seed")): bind(dict(path=str(path), bytes=declaration[name+"_bytes"], sha256=declaration[name+"_sha256"]))
    out = T/"outputs"/tag; target = ["--input", str(xml), "--out", str(out)]
    need(call["target_arguments"] == target and call["component_call"] is True and call["actual_solver_call"] is False and call["requested_OpenMP_threads"] == 1 and call["target_exit_independently_captured"] is (not debug) and call["sanitizer_used"] is debug and Path(call["working_directory"]).resolve() == Path(helper["program"]["path"]).resolve().parent and r["arguments"] == call["arguments"], "Exact actual component invocation differs")
    errors = leaks = None; mem_e = None; prior = None
    if debug:
        need(r["debug_review"] is None and Path(call["program"]["path"]).resolve() == Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe").resolve(), "Actual Debug CUDA11.7 sanitizer required")
        mem_e = r["memcheck_log"]; mempath = bind(mem_e)
        need(mempath.resolve() == (T/"logs"/(tag+".memcheck.log")).resolve() and call["arguments"] == ["--tool", "memcheck", "--leak-check", "full", "--error-exitcode", "99", "--log-file", str(mempath), helper["program"]["path"]] + target, "Actual full memcheck/error99/target argv differs")
        log = textlog(mempath); er = re.findall(r"ERROR SUMMARY:\s*(\d+)\s+errors\b", log); le = re.findall(r"LEAK SUMMARY:\s*(\d+)\s+bytes leaked in\s+(\d+)\s+allocations\b", log)
        need(er and le and all(int(v) == 0 for v in er) and all(int(a) == int(b) == 0 for a,b in le), "Actual memlog must report zero errors AND zero bytes/allocations leaked")
        errors, leaks = 0, 0
    else:
        need(call["program"] == helper["program"] and call["arguments"] == target and r["memcheck_log"] is None, "Release must directly own the target, no substituted memtool")
        prior_e = r["debug_review"]; prior = readjson(bind(prior_e))
        need(Path(prior_e["path"]).resolve() == (T/"logs/upl_cryer_gpu_component_Debug_probe_r1_review_r1.check.json").resolve() and prior["stage"] == STAGE and prior["configuration"] == "Debug" and prior["passed"] is True and prior["typed_owned_tool_exit0"] is True and prior["target_exit_independently_captured"] is False and prior["memcheck_errors"] == 0 and prior["memcheck_leaks"] == 0 and prior["initialization_metadata_only"] is True and prior["component_completion_verified"] is True and prior["physical_acceptance"] is False, "Actual Debug offline metadata/CSV/memcheck pass required")
        for e in prior["inputs"] + prior["files"] + [prior[k] for k in ("source_run", "source_call", "helper", "completion")]: bind(e)
    files = [adopt(path) for path in sorted(out.rglob("*")) if path.is_file()]
    need(len(files) == len(r["files"]) == 8 and {Path(e["path"]).resolve().relative_to(out.resolve()).as_posix() for e in files} == LEAVES and {str(Path(e["path"]).resolve()).casefold() for e in files} == {str(Path(e["path"]).resolve()).casefold() for e in r["files"]}, "Whole8-file output membership differs; no unrecorded PART trajectory allowed")
    parsed = [h.metadata(out/"data/Part_Head.ibi4", "JPartDataHead"), h.metadata(out/"data/PartOut_000.obi4", "JPartOutBi4")]
    done_e = adopt(out/"completion.json"); need(done_e == r["completion"], "Own completion binding differs"); done = readjson(bind(done_e))
    values = dict(stage="upl_cryer_gpu_component_r1", passed=True, native_count=37173, fixed_dummy_count=8, total_native_count=37181, actual_force_calls=6, complete_rate_calls_from_force=6, explicit_complete_rate_calls=0, soil_reference_checks=223038, sample_rows=48, summary_rows=6, actual_physical_steps=0, actual_time_s=0, manual_J_pool_added8B=4, manual_validity_pool_added4B=2, observer_Init_guard_bypassed_by_fixture=True, feedback_Init_guard_bypassed_by_fixture=True, observer_initialization_validated=False, feedback_initialization_validated=False, legacy_GPU_initialization_validated=True, manual_J1_theta0_installed=True, packed_and_double_support_intervals_unambiguous=True, reference_conditioned_on_observed_C_and_Ace=True, conditional_C_moment_uses_GPU_geometry_fastmath_budget=True, CUDA11p7_published_not_guaranteed_math_envelope_assumed=True, neighbor_search_independently_reimplemented=False, declared_input_bytes_restored=True, whole_object_restored=False, no_Run_ComputeStep_SaveData_restart=True, raw_LoadAce_gate_accounted=True, CPU_GPU_0ULP_compared=False, matched_formal_stabilization=False, physical_acceptance=False, public_3D_admitted=False)
    need(all(done.get(k) == v for k,v in values.items()) and math.isfinite(done["minimum_dummy_soil_distance_m"]) and done["minimum_dummy_soil_distance_m"] > .009, "Original zero-step/manual-init/conditional-math completion differs")
    maximum = h.csv_check(out)  # Same original finite/count/identity and8-channel sample budgets; GPU extra numeric columns retained.
    summary, samples = csv_rows(out/"summary.csv"), csv_rows(out/"samples.csv")
    for row in summary:
        probe = int(row["probe"]); need(float(row["C_moment_abs_residual_max"]) >= 0 and float(row["packed_double_displacement_difference_max_m"]) >= 0, "Invalid GPU geometry diagnostic")
        if probe < 4: need(float(row["Ace_norm_max_m_s2"]) == float(row["load_norm_max_m_s2"]) == 0, "Original zero-total-stress momentum/source gate differs")
        if probe == 0: need(float(row["pdot_abs_max_Pa_s"]) == 0, "Original strict constant-pressure zero gate differs")
        if probe >= 4: need(int(row["raw_LoadAce_store_gate_open"]) + int(row["raw_LoadAce_store_gate_closed"]) == 37173, "Conditional raw-load gate count differs")
        if probe == 4: need(float(row["Ace_norm_max_m_s2"]) > 0 and float(row["load_norm_max_m_s2"]) > 0, "Original confinement-only source did not activate")
    for row in samples:
        need(int(row["packed_neighbors"]) > 0 and int(row["double_neighbors"]) > 0 and 0 <= int(row["poscell_w_UINT_BITS"]) < 2**32 and float(row["C_residual"]) >= 0 and float(row["packed_double_dr_difference_m"]) >= 0, "GPU packed/reference diagnostics differ")
    producer_names = {"JSph.cpp", "JPartDataHead.cpp", "JPartOutBi4Save.cpp", "JBinaryData.cpp", "JBinaryData.h"}; producers = [e for e in snapshots if Path(e["path"]).name in producer_names]
    need(len(producers) == 5, "Archived metadata producer definitions missing")
    return dict(configuration=configuration, source_run=source, source_call=r["call"], helper=helper_e, source_build=helper["source_build"], program=helper["program"], owned_tool_program=call["program"], completion=done_e, files=files, original_owner_passed=True, original_owner_modified=False, typed_owned_tool_exit0=True, target_exit_independently_captured=not debug, direct_target_owned_exit0=not debug, memcheck_executed=debug, memcheck_errors=errors, memcheck_leaks=leaks, memcheck_log=mem_e, memcheck_zero_errors_and_leaks=debug, prior_Debug_review=r["debug_review"], component_completion_verified=True, summary_rows=6, sample_rows=48, max_checked_ratio=maximum, initialization_metadata_only=True, metadata=parsed, metadata_producer_sources=producers, no_particle_snapshots_or_exclusions=True, particle_payload_bytes=0, excluded_particle_payload_count=0, observer_initialization_validated=False, feedback_initialization_validated=False, whole_object_restored=False, conditional_fastmath_envelope_assumed=True, caller_reconstructed_neighbor_or_device_proof=False, CPU_GPU_or_Debug_Release_0ULP_compared=False, solver_trajectory_started=False, public_3D_admitted=False, physical_acceptance=False, programs_executed_by_reviewer=0)

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--configuration", choices=("Debug", "Release"), default="Debug"); configuration = ap.parse_args().configuration
    target = T/"logs"/("upl_cryer_gpu_component_"+configuration+"_probe_r1_review_r1.check.json")
    if target.exists(): raise ValueError("Fresh-only review output; preserve prior checks")
    h = None; result = dict(stage=STAGE, passed=False, configuration=configuration, physical_acceptance=False, public_3D_admitted=False, programs_executed_by_reviewer=0)
    try:
        h = definitions(); h.adopt(__file__); h.adopt(T/"notes/upl_cryer_gpu_component_review_r1.json"); result.update(review(h, configuration))
        for e in list(h.BOUND.values()): h.need(h.entry(e["path"]) == e, "Consumed file changed during independent final rehash")
        result.update(passed=True, independent_final_rehash_performed=True, failure=None)
    except Exception as exc: result["failure"] = str(exc)
    result["inputs"] = list(h.BOUND.values()) if h else []
    result["limits"] = "Conditional non-advancing arithmetic/metadata/memcheck only. Published CUDA11.7 fast-math envelope is assumed, not a universal guaranteed bound; producer reuses actual cell table/C/Ace. Outer CSV checks are not independent all-soil device/neighbor proof. Gated raw LoadAce resultant is descriptive, not a measured unbalanced force. No public3D/init/integration/trajectory/physical or CPU-GPU0ULP acceptance. Debug owns the sanitizer exit, not a separately captured target exit."
    with target.open("x", encoding="utf-8", newline="\n") as f: json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    if not result["passed"]: raise ValueError("Offline review failed; retain " + str(target) + ": " + str(result["failure"]))
    print(target)

if __name__ == "__main__": main()
