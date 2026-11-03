"""Offline completed HG1517 review, genuine CPU1/CPU8 prefixes, interrupted HG0 view."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
NAME, TAG = "upl_hg_mid2_review_r1", "upl_hg_mid2_CPU1_coarse_r1"
N, OLD, DT, EVENT = 1517, 1673, 2.0 ** -19, 5243
FULL_STEPS = sorted(set(range(0, 65537, 64)) | set(range(5120, 5377)) |
                    set(range(66560, 262145, 1024)) | set(range(278528, 4784129, 16384)) | {4798782})
PROFILE_STEPS = (262144, 524288, 786432, 917504, 966656, 1048576)
PINS = {
    "support/upl_hg_mid2_native_run_r1.py": (27082, "0e871abe5b7187ea698507fcbe385f71626de4c470654c494879ce2e6afce17d"),
    "notes/upl_hg_mid2_native_run_r1.json": (6841, "7dd6797bbad96a8b14edd686eab33df20df25e0f71169cb2f5e93597aed82db3"),
    "support/upl_hg_column_full_review_r1.py": (41848, "d8cd1b4c904663390792ea57b1d342dcfa77db4aa93c89e628794e1ae95a2acc"),
    "notes/upl_hg_column_full_review_r1.json": (8989, "44bc8df4d5ada973130b90219bb1ca6667f1bf9efc801228c7848f87f970442c"),
    "support/upl_hg_cpu1_short_r1.py": (38151, "9553ea64dfa2c08ef14f9fa44ba8e8dd09e63608b516083d3478ec7ec664ebbc"),
    "notes/upl_hg_cpu1_short_r1.json": (7281, "9ee70adce50bec3585e5997fbe02c6405acbafba6e5ec3aa79577224655dc905"),
    "logs/upl_hg_cpu1_short_r1.native.json": (453080, "5eea83d94206bcef9d2f002b7ce0f80aaec25065b675de332c060a89515492f9"),
    "logs/upl_hg_cpu1_short_r1.run.json": (624373, "a1b0b48a1f88573efa3fb4b48888534b6a4678b06d764bbb146b287ff263590d"),
    "logs/upl_hg_column_ReleaseCPU_coarse_r1.native_r2.json": (1464698, "e8b35ea299316a6f77b658fae1a485e3ad3dfe281c7989199a6c9dcab9b5fe55"),
    "logs/upl_hg_column_ReleaseCPU_coarse_r1.run.json": (1548582, "8effa59c9c2bb79b4b3e99fcd4f82fe5d72d7014b6d5f477125f89eb4f78f7c2"),
    "logs/upl_hg_mid2_r1.inputs.json": (1593497, "b595ea644faf20d8dadaace5e58980066128a596db1c8ffa07edde2ce015da9f"),
    "logs/upl_hg_mid2_reader_ReleaseCPU_r1.helper.json": (532547, "d3d86f3ed7647d32b457a48bd253160b197ae8d955adae097b708aac8e5dab5c"),
    "logs/upl_damp_mid_partial_review_r2.check.json": (809724, "d314900e6daff3cf02a9c782c3e5f728bdd9f7a4165ad20e7af796c0a1c8868e"),
    "logs/upl_damp_mid_partial_r1.native.json": (1312043, "927b5bd448f9ef0a77812c6c31c8d86c4bd98edfd4ca70efc72603e390e48d8e"),
    "logs/upl_mid_gpu_interruption_r1.check.json": (1200299, "15c9b4fb9e23f8e89c540db9ccf2aadb0b68ff48934109613bf63f86716c8160"),
    "outputs/upl_damp_mid_partial_r1_native/completion.json": (3009, "5d004456b7a26a44dde8950f0aab22dde181be6bb5150428453e88078537b811"),
    "logs/upl_damp_mid_partial_reader_ReleaseCPU_r1.helper.json": (392927, "842e85c9ef6f165be6c0cf6545beec898d3c993262a1d132eb922a54025914c3"),
    "notes/upl_damp_mid_partial_root_r1.json": (11202, "a6b2f200fcc115259dc8a8d04145ad3f6beb713a6a7803d6cc8426d7dd998e55"),
}
BOUND, CACHES = {}, []
full = np = None


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def entry(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest.hexdigest())


def bind(expected):
    key = str(Path(expected["path"]).resolve()).casefold()
    if key not in BOUND:
        BOUND[key] = entry(expected["path"])
    actual = BOUND[key]
    need(actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"].lower(),
         "Changed consumed artifact: " + expected["path"])
    return Path(actual["path"])


def adopt(path):
    key = str(Path(path).resolve()).casefold()
    if key not in BOUND:
        BOUND[key] = entry(path)
    return BOUND[key]


def read(expected):
    return json.loads(bind(expected).read_text(encoding="utf-8-sig"))


def pin(name):
    size, digest = PINS[name]
    expected = dict(path=str((T / name).resolve()), bytes=size, sha256=digest)
    bind(expected)
    return expected


def same(a, b):
    return (str(Path(a["path"]).resolve()).casefold(), a["bytes"], a["sha256"].lower()) == (
        str(Path(b["path"]).resolve()).casefold(), b["bytes"], b["sha256"].lower())


def module(name, relative):
    path = bind(pin(relative))
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)  # Definitions only; never an old main or a patched sample count.
    return value


def owned(expected, stage=None, python=False):
    value = read(expected)
    field = "typed_returncode_captured_immediately" if python else "typed_LASTEXITCODE_captured_immediately"
    need(value.get("direct_native_call") is True and value.get("owned_call_exited") is True and
         value.get(field) is True and type(value.get("exit_code")) is int and value["exit_code"] == 0 and
         value.get("invocation_failure") is None and (stage is None or value.get("stage") == stage),
         "Actual separately owned typed exit0 required")
    bind(value["program"])
    if value.get("log"):
        bind(value["log"])
    return value


def gathered_bindings():
    unique = {}
    for cache in [BOUND, *CACHES]:
        for expected in cache.values():
            key = str(Path(expected["path"]).resolve()).casefold()
            need(key not in unique or same(unique[key], expected), "Conflicting consumed-file claims")
            unique[key] = expected
    return list(unique.values())


def closure():
    values = gathered_bindings()
    for expected in values:
        need(entry(expected["path"]) == expected, "Consumed artifact changed during final independent rehash")
    return values


def initialize():
    global full, np
    sys.dont_write_bytecode = True
    for name in PINS:
        pin(name)
    full = module("mid2_frozen_full_schema", "support/upl_hg_column_full_review_r1.py")
    np = full.np
    CACHES.append(full.BOUND)
    adopt(__file__)
    adopt(T / "notes" / (NAME + ".json"))
    adopt(sys.executable)
    adopt(np.__file__)
    need(len(FULL_STEPS) == 1746 and FULL_STEPS[N - 1] == 1048576 and FULL_STEPS[OLD - 1] == 3604480 and
         all(step in FULL_STEPS[:N] for step in PROFILE_STEPS), "Declared original/bounded/profile integer schedule differs")


def extras(data, samples):
    leaves = data["leaves"]
    for name in full.STRIDES:
        full.binary(leaves[name], name, samples)
    jt = np.memmap(full.bind(leaves["common_j_theta.bin"]), mode="r", offset=12, shape=(samples,),
                   dtype=[("time", "<f8"), ("q", "<f8", (1040, 2))])
    n = np.memmap(full.bind(leaves["soil_n.bin"]), mode="r", offset=12, shape=(samples,),
                  dtype=[("time", "<f8"), ("q", "<f8", (1000,))])
    data.update(jt=jt, n=n)
    need(full.bits(jt["time"], data["clock"]["time"]) and full.bits(n["time"], data["clock"]["time"]) and
         np.isfinite(jt["q"]).all() and np.isfinite(n["q"]).all(), "Actual extra native J/theta/n clocks or finite fields differ")
    return data


def geometry(data):
    x0 = data["x0"]
    layers = np.rint((x0[:, 2] - .005) / .01).astype(int)
    columns = np.rint((x0[:, 0] - .005) / .01).astype(int)
    need(x0.shape == (1000, 3) and np.isfinite(x0).all() and np.all(x0[:, 1] == 0) and
         np.array_equal(np.sort(layers * 10 + columns), np.arange(1000)) and
         np.max(np.abs(x0[:, 2] - (.005 + layers * .01))) <= 1e-12 and
         np.max(np.abs(x0[:, 0] - (.005 + columns * .01))) <= 1e-12,
         "Original ten-column/100-layer material lattice differs")
    data.update(layers=layers, columns=columns)
    return data


def current():
    # This prerequisite is read before any new solver/native output is opened.
    ne = adopt(T / "logs" / (TAG + ".native.json"))
    native = read(ne)
    need(native.get("stage") == "upl_hg_mid2_native_run_r1" and native.get("passed") is True and
         all(native.get(k) is True for k in ("bindings_unchanged", "independent_final_rehash_performed",
             "original_native_guards_passed", "drainage_nonempty_per_frame_verified", "reader_executed_by_this_action")) and
         native.get("adopted_completed_reader") is False and native.get("solver_or_build_invoked") is False and
         native.get("physical_acceptance") is False, "Own completed1517 typed native safety prerequisite required")
    run = read(native["source_run"])
    need(run.get("stage") == "upl_hg_mid2_run_r1" and run.get("passed") is True and
         run.get("tag") == TAG and run.get("backend") == "CPU" and run.get("configuration") == "ReleaseCPU" and
         run.get("window") == "coarse" and run.get("threads") == 1 and run.get("steps") == 1048576 and
         run.get("native_frames") == N and run.get("bindings_unchanged") is True and
         run.get("public_project_main") is True and run.get("fixture_or_Run_override") is False and
         run.get("physical_acceptance") is False and same(native["source_start"], run["start_record"]) and
         same(native["source_call"], run["call"]) and same(native["source_build"], run["source_build"]) and
         same(native["program"], run["program"]) and
         same(native["input_manifest"], pin("logs/upl_hg_mid2_r1.inputs.json")), "Own solver/native/start/build association differs")
    manifest = read(native["input_manifest"])
    job = manifest["jobs"][0]
    need(manifest.get("stage") == "upl_hg_mid2_prepare_r1" and manifest.get("passed") and manifest.get("prepared") and
         run["job"] == job and run["program"] == manifest["source_program"] and
         run["source_build"] == manifest["source_build"] and job["steps"] == 1048576 and job["expected_samples"] == N and
         job["dt_s"] == DT and job["end_s"] == 2 and job["threads"] == 1 and job["event_completed_step"] == EVENT and
         job["expected_native_total_arrays"] == 22 and job["expected_total_native_count"] == 1040 and
         job["post_open_frames"] == 1313 and job["post_open_drained_particle_checks_expected"] == 13130 and
         run["HG"]["counters"] == job["expected_HG_counters"] and 0 <= run["HG"]["max_dt_over_tau"] <= .2 and
         0 <= run["HG"]["spinbound"] < .01 and run["HG"]["reference_history_is_Q_over_M0"] is True and
         run["HG"]["actual_inertia_is_current_mi"] is True and all(math.isfinite(run["HG"][k]) and run["HG"][k] >= 0
             for k in ("max_reference_history_net_force", "max_actual_float_add_net_force")),
         "Declared actual current HG1517/HG-safety plan differs")
    table = job["saved_clock_table"]
    need(len(table) == N and all((v["part"], v["completed_steps"], v["saved_step"]) ==
         (i, FULL_STEPS[i], FULL_STEPS[i] - 1 if i else 0) for i, v in enumerate(table)), "Prepared current integer schedule differs")
    call = owned(run["call"], "upl_hg_mid2_call_r1", True)
    expected = ["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip", job["input_prefix"], job["output_directory"],
                "-dirdataout", "data", "-svres", "-nsteps:1048576"]
    need(call["arguments"] == call["target_arguments"] == expected and call["program"] == call["target_program"] == run["program"] and
         call.get("actual_solver_call") and call.get("public_project_main") and not call.get("fixture_or_Run_override"),
         "Actual current CPU1 direct project-main target/arguments differ")
    bind(run["start_record"])
    bind(run["run_out"])
    build = read(run["source_build"])
    need(build.get("passed") and build.get("stage") == "upl_hg_column_build_r1" and build["program"] == run["program"] and
         build.get("exact_object_basename_closure") and len(build["objects"]) == 86 and build.get("non_main_object_count") == 85,
         "Current source-build/program provenance differs")
    for key in ("runtime", "initial_BI4", "normals"):
        bind(job[key])
    xml = ET.parse(bind(job["runtime"])).getroot()
    for key, value in (("SoilHourglassXi", .1), ("SoilDamping", 1.), ("SoilDampingCoef", .02), ("DtFixed", DT), ("TimeMax", 2.)):
        nodes = xml.findall("./execution/parameters/parameter[@key='" + key + "']")
        need(len(nodes) == 1 and float(nodes[0].get("value")) == value, "Current runtime parameter differs: " + key)
    helper_e = pin("logs/upl_hg_mid2_reader_ReleaseCPU_r1.helper.json")
    helper = read(helper_e)
    need(same(native["reader_helper"], helper_e) and helper.get("passed") and helper.get("stage") == "upl_hg_mid2_reader_build_r1" and
         helper["source_build"] == run["source_build"] and same(helper["prepared_inputs"], native["input_manifest"]) and
         helper.get("exact_link_closure_verified") and helper.get("actual_headers_archived_not_live") and
         helper.get("independent_final_rehash_performed") and helper.get("CPU_non_main_objects") == len(helper["objects"]) == 85 and
         helper.get("link_object_count") == 86 and len(helper["libraries"]) == 17 and len(helper["runtime"]) == 4,
         "Genuine current85+1 typed reader helper differs")
    reader = owned(native["reader_call"], "upl_hg_mid2_reader_call_r1", True)
    native_dir = (T / "outputs" / (TAG + "_native")).resolve()
    need(Path(native["paths"]["native_dir"]).resolve() == native_dir and
         Path(native["paths"]["solver_dir"]).resolve() == Path(job["output_directory"]).resolve() and
         reader["program"] == helper["program"] and reader["arguments"] ==
         ["--read", "CPU", str(Path(job["output_directory"]) / "data"), "coarse", str(native_dir)] and
         same(reader["source_run"], native["source_run"]) and same(reader["source_start"], native["source_start"]),
         "Current decoder association differs")
    validator = module("mid2_frozen_native_validator", "support/upl_hg_mid2_native_run_r1.py")
    owner, schema = validator.definitions()
    CACHES.extend([owner.BOUND, schema.BOUND])
    data = validator.exports(owner, schema, native_dir, native["files"], native["completion"])
    data.update(tag=TAG, check=ne, native=native, run_entry=native["source_run"], run=run, material=job,
                samples=N, steps=np.asarray(FULL_STEPS[:N]), native_dir=native_dir)
    return geometry(extras(data, N))


def cpu1_short():
    short = module("mid2_frozen_cpu1_short", "support/upl_hg_cpu1_short_r1.py")
    short.initialize()  # Pinned definitions/input checks only; no action/main is called.
    CACHES.append(short.base.BOUND)
    ne = pin("logs/upl_hg_cpu1_short_r1.native.json")
    native = read(ne)
    re_ = pin("logs/upl_hg_cpu1_short_r1.run.json")
    run = read(re_)
    need(native.get("stage") == "upl_hg_cpu1_short_r1.native" and native.get("passed") and native.get("bindings_unchanged") and
         native.get("original_native_guards_passed") and native.get("drainage_nonempty_per_frame_verified") and
         same(native["source_run"], re_) and run.get("stage") == "upl_hg_cpu1_short_r1.run" and run.get("passed") and
         run.get("threads") == 1 and run.get("native_frames") == 458 and run.get("physical_acceptance") is False,
         "Genuine completed CPU1 short458 prerequisite differs")
    owned(run["call"], "upl_hg_cpu1_short_r1.run_call", True)
    owned(native["reader_call"], "upl_hg_cpu1_short_r1.reader_call", True)
    data = short.exports(Path(native["paths"]["native_dir"]), native["files"], native["completion"])
    variants = [v for v in read(run["source_input_manifest"])["variants"] if v["window"] == "coarse"]
    need(len(variants) == 1, "Unique genuine CPU1 coarse source variant required")
    data.update(tag="upl_hg_cpu1_short_r1", check=ne, run_entry=re_, run=run, samples=458, material=variants[0])
    return data


def old_control():
    ne = pin("logs/upl_damp_mid_partial_r1.native.json")
    native = read(ne)
    review = read(pin("logs/upl_damp_mid_partial_review_r2.check.json"))
    root = read(pin("notes/upl_damp_mid_partial_root_r1.json"))
    audit_e = pin("logs/upl_mid_gpu_interruption_r1.check.json")
    audit = read(audit_e)
    need(native.get("stage") == "upl_damp_mid_partial_native_r1" and native.get("passed") is True and
         all(native.get(k) is True for k in ("partial_decode_only", "independent_final_rehash_performed")) and
         native.get("failure") is None and native.get("source_solver_exit_code") is None and
         all(native.get(k) is False for k in ("source_solver_completion_verified", "original_window_completed",
             "solver_invoked", "original_full_gate_adopted", "independent_half_performed", "physical_acceptance")),
         "Old source must remain a genuine interrupted partial decode")
    need(review.get("stage") == "upl_damp_mid_partial_review_r2" and review.get("passed") and
         all(review.get(k) is True for k in ("partial_diagnostic_only", "independent_final_rehash_performed",
             "all5_binary_payload_prefix_exact", "all3_identity_files_exact", "all3_text_prefix_exact")) and
         review["preserved_samples"] == OLD and review["original_expected_samples"] == 1746 and
         review["actual_saved_end_s"] == 6.875 and review["actual_saved_completed_steps"] == 3604480 and
         review["source_solver_exit_code"] is None and review["source_solver_completion_verified"] is False and
         review["original_window_completed"] is False and review["original_full_gate_adopted"] is False and review["physical_acceptance"] is False and
         same(review["native_check"], ne) and same(review["interruption_audit"], audit_e) and
         same(review["native_completion"], native["completion"]) and same(review["pure_reader_call"], native["call"]),
         "Passed old interrupted1673/prefix review association differs")
    need(root["stage"] == "upl_damp_mid_partial_root_r1" and root["source_solver_exit_code"] is None and
         root["original_window_completed"] is False and root["physical_acceptance"] is False and
         root["verified"]["partial_native_safety_and_identity"] and root["verified"]["all_1469_saved_prefix_bytes_exact"] and
         root["root_visual_review"]["performed"], "Root interrupted diagnostic remains required")
    mid = audit["mid"]
    need(audit["stage"] == "upl_mid_gpu_interruption_r1" and audit["interruption_audited"] and
         audit["all_observed_owned_processes_absent"] and audit["real_exit_code"] is None and
         audit["typed_exit_evidence_available"] is False and audit["normal_completion_or_failure_exit_invented"] is False and
         audit["old_full_gate_preserved"] is True and
         mid["planned_window_completed"] is False and
         (mid["planned_frames"], mid["planned_completed_steps"], mid["observed_raw_frames"], mid["last_console_time_s"], mid["last_console_completed_steps"]) ==
         (1746, 4798782, OLD, 6.875, 3604480) and same(native["interruption_audit"], audit_e), "Original unfinished plan/unknown exit differs")
    need(len(audit["observations"]) == 2 and all(not row["project_processes"] for row in audit["observations"]),
         "Two original recorded survivor-free observations required; no current process inference")
    need(same(review["source_build"], mid["source_build"]), "Old solver-build attribution differs")
    build = read(mid["source_build"])
    need(build.get("passed") and build.get("stage") == "upl_damp_build_r2" and build["program"] == review["program"], "Sealed old solver provenance differs")
    bind(review["program"])
    prepared = read(mid["prepared"])
    need(prepared.get("stage") == "upl_damp_mid_prepare_r1" and prepared.get("passed") and prepared.get("prepared") and
         len(prepared["jobs"]) == 1 and prepared["source_build"] == mid["source_build"] and prepared["source_program"] == build["program"],
         "Genuine old1746 input provenance differs")
    material = prepared["jobs"][0]
    for key in ("runtime", "initial_BI4", "normals"):
        bind(material[key])
    helper_e = pin("logs/upl_damp_mid_partial_reader_ReleaseCPU_r1.helper.json")
    helper = read(helper_e)
    reader = owned(native["call"])
    need(same(native["helper"], helper_e) and helper.get("passed") and helper.get("stage") == "upl_damp_mid_partial_reader_build_r1" and
         helper["source_build"] == mid["source_build"] and helper["program"] == native["program"] == reader["program"] and
         helper.get("exact_link_closure_verified") and helper.get("actual_headers_archived_not_live") and
         helper["CPU_non_main_objects"] == len(helper["objects"]) == 85 and helper["link_object_count"] == 86 and
         len(helper["libraries"]) == 17 and len(helper["runtime"]) == 4, "Actual old partial decoder differs from old solver program")
    native_dir = Path(native["outdir"]).resolve()
    need(native_dir == (T / "outputs/upl_damp_mid_partial_r1_native").resolve() and reader["arguments"] ==
         ["--read", "CPU", str((T / "outputs/upl_damp_mid_CPU_coarse_r1/data").resolve()), "partial", str(native_dir)] and
         reader.get("pure_reader") and reader.get("actual_solver_call") is False and
         reader.get("source_solver_exit_code") is None and reader.get("source_solver_completion_verified") is False,
         "Old decoder exit must never become a solver exit")
    completion_e = pin("outputs/upl_damp_mid_partial_r1_native/completion.json")
    need(same(native["completion"], completion_e), "Old native completion identity differs")
    done = read(completion_e)
    expected = dict(stage="upl_damp_mid_partial_r1", backend="CPU_public", window="interrupted_partial", preset="partial", grid="c",
                    model="constant", conductivity_model=0, conductivity_Ck=0, samples=OLD, preserved_samples=OLD,
                    original_expected_samples=1746, native_count=1000, fixed_count=40, total_native_count=1040,
                    physical_columns=26, physical_schema=full.SCHEMA, original_typed_arrays=15, native_dynamic_double_arrays=6,
                    native_total_arrays=22, dt_s=DT, planned_end_s=4798782 * DT, actual_end_s=6.875,
                    planned_completed_steps=4798782, actual_saved_completed_steps=3604480, soil_ledger_checks=1673000,
                    fixed_public_zero_marker_checks=66920, all_native_J_theta_rows=1739920, soil_native_n_rows=1673000,
                    noninitial_signed_dterror_intervals=1672, post_open_completed_step_threshold=EVENT,
                    post_open_frames=1469, post_open_drained_particle_checks=14690, max_activeDrainCount=10)
    need(done.get("passed") and all(done.get(k) == v for k, v in expected.items()) and
         done["source_solver_exit_code"] is None and all(done.get(k) is False for k in ("source_solver_exit_verified",
             "source_solver_normal_completion_verified", "original_planned_window_completed", "full_consolidation_acceptance",
             "full_window_gates_adopted_or_relaxed", "independent_half_performed", "physical_acceptance")) and
         done.get("interrupted_evidence_only") and done.get("partial_decode_safety_passed"), "Old completion must retain1673/6.875 interruption truth")
    flags = ("public_schema", "public_master_on", "PART_typed_public_metadata_verified", "native_PosDiv_present", "native_PosDiv_is_float",
             "native_V_rho_k_present", "no_exclusions", "initial_rest_and_decimal_lattice_verified", "double_stress_and_float_display_verified",
             "all_exported_physical_fields_finite", "declared_saved_completed_steps_exact", "actual_time_step_locked_dt_exact",
             "initial_dterror_excluded_from_noninitial_summary", "fixed_J_theta_original15_not_zeroed_or_masked",
             "common26_column21_is_actual_ExcessPorePress", "pre_open_event_pressure_not_forced_zero", "density_and_J_not_frozen_on_drained_receivers")
    need(all(done.get(k) is True for k in flags) and 0 <= done["max_ledger_relative_error"] <= 5e-13 and
         math.isfinite(done["max_noninitial_signed_dterror_s"]) and done["max_noninitial_signed_dterror_s"] <= 1e-14,
         "Original old native finite/ledger/signed-clock guards differ")
    forbidden = ("GPU_private_fixed_n_mirror_to_public_zero_is_schema_change", "PosDiv_fabricated_or_derived", "new_scientific_acceptance_gate",
                 "same_force_stage_load_budget_verified", "force_stage_guard_independently_observed", "historical_private_comparison_performed_by_reader",
                 "live_final_compared_by_reader")
    need(all(done.get(k) is False for k in forbidden) and done.get("initial_empty_dterror_intervals") in (0, 1),
         "Original old unmasked/sentinel/descriptive scope differs")
    leaves = {Path(e["path"]).name: e for e in native["files"]}
    need(len(native["files"]) == len(leaves) == 13 and set(leaves) == full.LEAVES and
         leaves["completion.json"] == completion_e and all(Path(e["path"]).resolve().parent == native_dir for e in leaves.values()),
         "Genuine old13-leaf ownership differs")
    binaries = {name: full.binary(leaves[name], name, OLD) for name in full.STRIDES}
    p = np.memmap(binaries["physical.bin"][0], mode="r", offset=12, shape=(OLD,),
                  dtype=[("time", "<f8"), ("q", "<f8", (1000, 26))])
    clock = np.memmap(binaries["clock.bin"][0], mode="r", offset=8, shape=(OLD,),
                      dtype=[("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")])
    ids = full.csv_rows(leaves["native_ids.csv"])
    fixed = full.csv_rows(leaves["fixed_ids.csv"])
    need(len(ids) == 1000 and all((int(r["row"]), int(r["id"])) == (i, i + 40) for i, r in enumerate(ids)) and
         len(fixed) == 40 and all((int(r["row"]), int(r["id"])) == (i, i) for i, r in enumerate(fixed)), "Old all1040 IDs differ")
    x0 = np.asarray([[float(r[k]) for k in ("x0", "y0", "z0")] for r in ids])
    columns = full.csv_rows(leaves["columns.csv"])
    need([r["name"] for r in columns] == full.FIELDS and [int(r["column"]) for r in columns] == list(range(26)), "Old common26 names differ")
    history = full.csv_rows(leaves["history.csv"])
    steps = np.asarray(FULL_STEPS[:OLD])
    times = steps * DT
    need(len(history) == OLD and full.bits(p["time"], times) and full.bits(clock["time"], times) and
         full.bits(clock["dt"], np.full(OLD, DT)) and np.array_equal(clock["step"], np.where(steps, steps - 1, 0)) and
         np.isfinite(clock["error"]).all() and np.all(clock["error"][1:] <= 1e-14) and
         np.all(clock["error"][1:] != -np.finfo(float).max) and full.bits(p["q"][0, :, :3], x0), "Old actual1673 binary clocks differ")
    for i, row in enumerate(history):
        post = steps[i] > EVENT
        need((int(row["part"]), int(row["completed_step"]), int(row["saved_step"]), int(row["post_open_by_completed_step"]), int(row["activeDrainCount"])) ==
             (i, int(steps[i]), int(clock["step"][i]), int(post), 10 if post else 0) and
             full.bits(float(row["time_s"]), times[i]) and full.bits(float(row["dt_s"]), DT) and
             full.bits(float(row["signed_dterror_s"]), clock["error"][i]) and
             int(row["dterror_used_in_noninitial_summary"]) == int(i > 0) and
             int(row["dterror_interval_empty"]) == int(clock["error"][i] == -np.finfo(float).max) and
             0 <= float(row["max_ledger_relative_error"]) <= 5e-13, "Old actual per-frame clock/drain/ledger differs")
    data = dict(tag="HG0_interrupted", check=ne, native=native, completion=done, leaves=leaves, binaries=binaries,
                p=p, clock=clock, x0=x0, fixed_x0=np.asarray([[float(r[k]) for k in ("x0", "y0", "z0")] for r in fixed]),
                history=history, material=material, samples=OLD, steps=steps, original_window_completed=False, source_solver_exit_code=None)
    return geometry(extras(data, OLD))


def binary_prefix(left, right, count, require_equal, comparison):
    rows = []
    for leaf, stride in full.STRIDES.items():
        lp, lo = full.binary(left["leaves"][leaf], leaf, left["samples"])
        rp, ro = full.binary(right["leaves"][leaf], leaf, right["samples"])
        lh, rh, equal, first = hashlib.sha256(), hashlib.sha256(), True, None
        with lp.open("rb") as a, rp.open("rb") as b:
            a.seek(lo)
            b.seek(ro)
            for part in range(count):
                av, bv = a.read(stride), b.read(stride)
                need(len(av) == len(bv) == stride, "Truncated actual prefix record")
                lh.update(av)
                rh.update(bv)
                if av != bv:
                    equal = False
                    if first is None:
                        first = part
        rows.append(dict(comparison=comparison, leaf=leaf, left_header_samples=left["samples"],
                         right_header_samples=right["samples"], compared_records=count, record_bytes=stride,
                         compared_record_bytes=count * stride, raw_record_bytes_equal=equal,
                         first_different_part=first, left_prefix_SHA256=lh.hexdigest(), right_prefix_SHA256=rh.hexdigest(),
                         equality_required=require_equal, dterror_or_other_bytes_excluded=False, headers_rewritten=False))
        need(not require_equal or equal, "Same CPU1 first458 raw prefix differs: " + leaf)
    return rows


def differences(left, right, count, role):
    need(full.bits(left["x0"], right["x0"]), "Original material coordinates differ")
    rows = []
    for i in range(count):
        a, b = np.asarray(left["p"]["q"][i]), np.asarray(right["p"]["q"][i])
        need(np.isfinite(a).all() and np.isfinite(b).all(), "Nonfinite actual paired fields")
        delta = a - b
        rms, maximum = np.sqrt(np.mean(delta * delta, axis=0)), np.max(np.abs(delta), axis=0)
        du = (a[:, :3] - left["x0"]) - (b[:, :3] - right["x0"])
        row = dict(role=role, part=i, completed_step=FULL_STEPS[i], left_actual_time_s=float(left["clock"]["time"][i]),
                   right_actual_time_s=float(right["clock"]["time"][i]),
                   time_difference_s=float(left["clock"]["time"][i] - right["clock"]["time"][i]),
                   pressure_RMS_Pa=float(rms[6]), material_XYZ_difference_max_mm=float(1000 * np.linalg.norm(du, axis=1).max()),
                   velocity_XYZ_RMS_m_s=float(np.sqrt(np.mean(np.sum(delta[:, 3:6] ** 2, axis=1)))),
                   stored_stress6_RMS_Pa=float(np.sqrt(np.mean(np.sum(delta[:, 10:16] ** 2, axis=1)))),
                   left_signed_dterror_s=float(left["clock"]["error"][i]), right_signed_dterror_s=float(right["clock"]["error"][i]))
        row.update({name + "_RMS_difference": float(v) for name, v in zip(full.FIELDS, rms)})
        row.update({name + "_max_abs_difference": float(v) for name, v in zip(full.FIELDS, maximum)})
        need(all(math.isfinite(v) for k, v in row.items() if k != "role"), "Nonfinite paired reduction")
        rows.append(row)
    maximum = dict(max_pressure_RMS_Pa=max(r["pressure_RMS_Pa"] for r in rows),
                   max_material_XYZ_difference_mm=max(r["material_XYZ_difference_max_mm"] for r in rows),
                   max_actual_time_difference_s=max(abs(r["time_difference_s"]) for r in rows))
    return rows, maximum


def native_density(data):
    # Actual exported native density; column25 is legacy_Rhop and is never substituted.
    rho = np.empty((N, 1000), dtype=np.float64)
    max_relative = 0.0
    path = bind(data["leaves"]["ledger.csv"])
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        need(reader.fieldnames == ["part", "time_s", "id", "J", "n_native", "theta_native", "V_native_m2",
             "rho_native_kg_m3", "k_native_m_s", "PosDiv_native", "V_reference_m2", "rho_reference_kg_m3", "k_reference_m_s", "legacy_Rhop"],
             "Actual native ledger column names differ")
        for part in range(N):
            rows = []
            for i in range(1000):
                row = next(reader, None)
                need(row is not None and (int(row["part"]), int(row["id"])) == (part, i + 40), "Native density ledger row identity/order differs")
                rows.append(row)
            for field, expected in (("time_s", np.full(1000, data["p"]["time"][part])), ("J", data["p"]["q"][part, :, 8]),
                                    ("n_native", data["n"]["q"][part]), ("theta_native", data["p"]["q"][part, :, 9])):
                values = np.asarray([float(row[field]) for row in rows])
                need(np.isfinite(values).all() and full.bits(values, expected), "Actual native ledger/binary association differs: " + field)
            values = np.asarray([float(row["rho_native_kg_m3"]) for row in rows])
            reference = np.asarray([float(row["rho_reference_kg_m3"]) for row in rows])
            need(np.isfinite(values).all() and np.isfinite(reference).all() and np.all(values > 0) and np.all(reference > 0), "Nonfinite/nonpositive actual native density")
            relative = float(np.max(np.abs(values - reference) / reference))
            need(relative <= 5e-13, "Original native density ledger tolerance failed")
            max_relative = max(max_relative, relative)
            rho[part] = values
        if data["samples"] == N:
            need(next(reader, None) is None, "Extra rows in current1517 soil ledger")
    data["rho"] = rho
    return dict(rows_reparsed=N * 1000, actual_native_density_not_legacy_or_reconstructed=True,
                old_trailing156_frames_not_reparsed=data["samples"] == OLD, max_relative_error=max_relative)


def summarize(key, data):
    history, modal, profiles = [], [], []
    layers, columns, x0 = data["layers"], data["columns"], data["x0"]
    order = np.argsort(layers * 10 + columns)
    signs = np.where(np.arange(10) % 2, -1., 1.)
    top, bottom = layers == 99, layers == 0
    need(top.sum() == bottom.sum() == 10, "Top/bottom must be ten original material IDs")
    for part in range(N):
        q, native_n, rho = np.asarray(data["p"]["q"][part]), np.asarray(data["n"]["q"][part]), data["rho"][part]
        need(np.isfinite(q).all() and np.isfinite(native_n).all() and np.isfinite(rho).all(), "Nonfinite unmasked saved fields")
        uz = 1000 * (q[:, 2] - x0[:, 2])
        compression = q[:, 6] - q[:, 15]
        uz_grid = uz[order].reshape(100, 10)
        residual = uz_grid - uz_grid.mean(axis=1, keepdims=True)
        api = np.mean(residual * signs, axis=1)
        grids = {"pressure": q[order, 6].reshape(100, 10), "total_compression": compression[order].reshape(100, 10),
                 "J": q[order, 8].reshape(100, 10), "n_native": native_n[order].reshape(100, 10), "rho_native": rho[order].reshape(100, 10)}
        source, actual = data["history"][part], float(data["clock"]["time"][part])
        row = dict(series=key, part=part, actual_time_s=actual, completed_step=FULL_STEPS[part],
                   pressure_mean_Pa=float(q[:, 6].mean()), pressure_RMS_Pa=float(np.sqrt(np.mean(q[:, 6] ** 2))),
                   pressure_min_Pa=float(q[:, 6].min()), pressure_max_Pa=float(q[:, 6].max()),
                   top10_settlement_mean_mm=float(-uz[top].mean()), bottom10_settlement_mean_mm=float(-uz[bottom].mean()),
                   material_settlement_mean_mm=float(-uz.mean()), total_compression_zz_mean_Pa=float(compression.mean()),
                   effective_compression_zz_mean_Pa=float(-q[:, 15].mean()),
                   J_min=float(q[:, 8].min()), J_mean=float(q[:, 8].mean()), J_max=float(q[:, 8].max()),
                   n_native_min=float(native_n.min()), n_native_mean=float(native_n.mean()), n_native_max=float(native_n.max()),
                   rho_native_min_kg_m3=float(rho.min()), rho_native_mean_kg_m3=float(rho.mean()), rho_native_max_kg_m3=float(rho.max()),
                   native_rho_mean_history_difference_descriptive_kg_m3=float(rho.mean() - float(source["native_current_rho_mean_kg_m3"])),
                   velocity_XYZ_RMS_m_s=float(np.sqrt(np.mean(np.sum(q[:, 3:6] ** 2, axis=1)))),
                   saved_theta_mean_s_inv=float(q[:, 9].mean()), saved_theta_RMS_s_inv=float(np.sqrt(np.mean(q[:, 9] ** 2))),
                   A_pi_Uz_RMS_mm=float(np.sqrt(np.mean(api ** 2))), A_pi_Uz_max_abs_mm=float(np.max(np.abs(api))),
                   within_layer_Uz_RMS_mm=float(np.sqrt(np.mean(residual ** 2))), max_within_layer_Uz_span_mm=float(np.ptp(uz_grid, axis=1).max()),
                   activeDrainCount=int(source["activeDrainCount"]), max_ledger_relative_error=float(source["max_ledger_relative_error"]))
        for axis in "xyz":
            field = "final_J_weighted_retained_load_" + axis + "_N_per_m"
            row[field + "_descriptive_only"] = float(source[field])
        need(all(math.isfinite(v) for k, v in row.items() if k != "series"), "Nonfinite history reduction")
        history.append(row)
        for level in range(100):
            layer = dict(series=key, part=part, actual_time_s=actual, initial_material_layer=level,
                         initial_z_m=.005 + .01 * level, A_pi_Uz_signed_mm=float(api[level]),
                         within_layer_Uz_RMS_mm=float(np.sqrt(np.mean(residual[level] ** 2))),
                         within_layer_Uz_span_mm=float(np.ptp(uz_grid[level])), settlement_down_mean_mm=float(-uz_grid[level].mean()))
            for name, grid in grids.items():
                for suffix, value in (("mean", grid[level].mean()), ("min", grid[level].min()), ("max", grid[level].max())):
                    layer[name + "_" + suffix] = float(value)
            modal.append(layer)
        if FULL_STEPS[part] in PROFILE_STEPS:
            for i in range(1000):
                profiles.append(dict(series=key, part=part, actual_time_s=actual, soil_ID=i + 40,
                    initial_material_layer=int(layers[i]), initial_material_column=int(columns[i]), x0_m=float(x0[i, 0]), z0_m=float(x0[i, 2]),
                    native_x_m=float(q[i, 0]), native_y_m=float(q[i, 1]), native_z_m=float(q[i, 2]), pressure_Pa=float(q[i, 6]),
                    Uz_up_mm=float(uz[i]), settlement_down_mm=float(-uz[i]), total_compression_zz_Pa=float(compression[i]),
                    effective_sigma_zz_Pa=float(q[i, 15]), J_native=float(q[i, 8]), n_native=float(native_n[i]),
                    rho_native_kg_m3=float(rho[i]), layer_A_pi_Uz_signed_mm=float(api[layers[i]])))
    need(len(history) == N and len(modal) == N * 100 and len(profiles) == 6000, "Complete1517/100-layer/six-profile coverage required")
    return history, modal, profiles


def write_csv(path, rows):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def draw(history, modal, paths):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .2})
    series = (("HG_CPU1", "#2166ac", "-", "Current HG=.1, completed2s"),
              ("HG0_interrupted_view", "#b35806", "--", "HG0 interrupted6.875s, first2s view"))
    panels = (("pressure_mean_Pa", "Mean pore pressure (Pa)"), ("top10_settlement_mean_mm", "Top10 material settlement (mm)"),
              ("bottom10_settlement_mean_mm", "Bottom10 material settlement (mm)"), ("total_compression_zz_mean_Pa", "Mean total compression p-sigma_zz (Pa)"),
              ("J_mean", "Native J: mean and material min/max"), ("n_native_mean", "Native n: mean and material min/max"),
              ("rho_native_mean_kg_m3", "Actual native density (kg/m^3)"), ("A_pi_Uz_RMS_mm", "Alternating Uz coefficient RMS (mm)"),
              ("within_layer_Uz_RMS_mm", "All within-layer Uz RMS (mm)"))
    fig, axes = plt.subplots(3, 3, figsize=(16, 12), sharex=True, constrained_layout=True)
    for key, color, style, label in series:
        rows = [r for r in history if r["series"] == key]
        times = [r["actual_time_s"] for r in rows]
        for ax, (field, title) in zip(axes.flat, panels):
            ax.plot(times, [r[field] for r in rows], color=color, ls=style, label=label)
            if field in ("J_mean", "n_native_mean", "rho_native_mean_kg_m3"):
                low, high = {"J_mean": ("J_min", "J_max"), "n_native_mean": ("n_native_min", "n_native_max"),
                             "rho_native_mean_kg_m3": ("rho_native_min_kg_m3", "rho_native_max_kg_m3")}[field]
                ax.fill_between(times, [r[low] for r in rows], [r[high] for r in rows], color=color, alpha=.10)
            ax.set_ylabel(title)
            ax.axvline(EVENT * DT, color=".5", ls=":", lw=.8)
    for ax in axes[-1]:
        ax.set_xlabel("Actual native time (s)")
    axes.flat[0].legend(fontsize=8)
    fig.suptitle("Bounded2s HG diagnosis: all1517 saved states; shaded ranges are actual material min/max\n"
                 "HG0 is a view of interrupted evidence, source solver exit unknown. No2s half/theory/physical acceptance.")
    with paths["history_png"].open("xb") as stream:
        fig.savefig(stream, format="png", dpi=170)
    plt.close(fig)
    variables = (("pressure_mean", "Pore pressure (Pa)"), ("settlement_down_mean_mm", "Settlement down (mm)"),
                 ("total_compression_mean", "Total compression zz (Pa)"), ("J_mean", "Native J"), ("n_native_mean", "Native n"),
                 ("rho_native_mean", "Actual native density (kg/m^3)"), ("A_pi_Uz_signed_mm", "Signed alternating Uz (mm)"))
    fig, axes = plt.subplots(7, 6, figsize=(24, 22), sharey=True, constrained_layout=True)
    for col, step in enumerate(PROFILE_STEPS):
        part = FULL_STEPS.index(step)
        axes[0, col].set_title("Actual t=" + format(step * DT, ".12g") + " s")
        for key, color, style, label in series:
            rows = [r for r in modal if r["series"] == key and r["part"] == part]
            need(len(rows) == 100, "All100 material layers required in every profile")
            for row, (field, title) in enumerate(variables):
                axes[row, col].plot([r[field] for r in rows], [r["initial_z_m"] for r in rows], color=color, ls=style, label=label)
                axes[row, col].set_xlabel(title)
        for row in range(7):
            axes[row, 0].set_ylabel("Initial material z0 (m)")
    axes[0, 0].legend(fontsize=7)
    fig.suptitle("Six actual saved material profiles: .5,1,1.5,1.75,1.84375,2s\n"
                 "Ten original IDs per layer; signed alternating coefficient, no time interpolation or load/H fitting.")
    with paths["profiles_png"].open("xb") as stream:
        fig.savefig(stream, format="png", dpi=170)
    plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True, constrained_layout=True)
    limit = max(max(abs(r["A_pi_Uz_signed_mm"]) for r in modal), np.finfo(float).tiny)
    for ax, (key, _, _, label) in zip(axes, series):
        rows = [r for r in modal if r["series"] == key]
        values = np.asarray([r["A_pi_Uz_signed_mm"] for r in rows]).reshape(N, 100).T
        artist = ax.pcolormesh(np.asarray(FULL_STEPS[:N]) * DT, .005 + np.arange(100) * .01, values,
                              shading="nearest", cmap="RdBu_r", vmin=-limit, vmax=limit, rasterized=True)
        ax.set_ylabel(label + "\nInitial material z0 (m)")
        ax.grid(False)
    axes[-1].set_xlabel("Actual native time (s); cells represent saved samples")
    fig.colorbar(artist, ax=list(axes), label="Signed A_pi(Uz) (mm), common actual scale")
    fig.suptitle("All100 layers at all1517 saved times: alternating X-column Uz\n"
                 "Up positive, even columns positive; no tiny-control normalization, smoothing or unsaved-stability claim.")
    with paths["heatmap_png"].open("xb") as stream:
        fig.savefig(stream, format="png", dpi=170)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Root full-read and explicit authorization required after genuine1517 native safety; no outputs created")
    suffixes = dict(history_png="_history.png", profiles_png="_profiles.png", heatmap_png="_mode_heatmap.png",
                    history_csv="_history.csv", profiles_csv="_profiles.csv", modal_csv="_modal.csv",
                    comparisons_csv="_comparisons.csv", prefix_csv="_prefixes.csv")
    paths = {key: T / "figures" / (NAME + suffix) for key, suffix in suffixes.items()}
    record = T / "logs" / (NAME + ".check.json")
    need(not record.exists() and all(not p.exists() for p in paths.values()), "Retained review output protected")
    result = dict(stage=NAME, passed=False, physical_acceptance=False, independent_2s_half_performed=False,
                  later_half_full_or_formal_admitted=False, solver_reader_build_Git_or_queue_invoked=False, failure=None)
    try:
        initialize()
        new, short, old = current(), cpu1_short(), old_control()
        cpu8 = full.dataset("coarse", True)
        cpu8["leaves"] = {Path(e["path"]).name: e for e in cpu8["native"]["files"]}
        need(new["run"]["source_build"] == short["run"]["source_build"] == cpu8["run"]["source_build"] and
             new["run"]["program"] == short["run"]["program"] == cpu8["run"]["program"], "Current same-program/source-build requirement failed")
        for other in (short, old, cpu8):
            need(full.bits(new["x0"], other["x0"]) and full.bits(new["p"]["q"][0], other["p"]["q"][0]), "Original material/initial26 field identity differs")
            for key in ("initial_BI4", "normals"):
                need(all(new["material"][key][field] == other["material"][key][field] for field in ("bytes", "sha256")),
                     "Genuine initial seed/Normals identity differs")
        prefixes = binary_prefix(new, short, 458, True, "same_CPU1_current2s_vs_short458")
        prefixes += binary_prefix(new, cpu8, 1469, False, "currentCPU1_first1469_vs_retainedCPU8_halfsecond")
        thread_rows, thread_max = differences(new, cpu8, 1469, "same_dt_thread_compatibility_only")
        thread_gates = dict(pressure_RMS_all1469_le_5Pa=thread_max["max_pressure_RMS_Pa"] <= 5.,
                            material_XYZ_all1469_le_0_005mm=thread_max["max_material_XYZ_difference_mm"] <= .005,
                            actual_time_all1469_le_1e_minus14_s=thread_max["max_actual_time_difference_s"] <= 1e-14)
        result.update(CPU8_first1469_thread_gates=thread_gates, CPU8_first1469_thread_maxima=thread_max)
        need(all(thread_gates.values()), "Original same-dt1469 thread compatibility thresholds failed")
        descriptive_rows, descriptive_max = differences(new, old, N, "HG_vs_interrupted_HG0_operator_difference_descriptive")
        density = {"HG_CPU1": native_density(new), "HG0_interrupted_view": native_density(old)}
        histories, modal, profiles = [], [], []
        for key, data in (("HG_CPU1", new), ("HG0_interrupted_view", old)):
            h, m, p = summarize(key, data)
            histories.extend(h)
            modal.extend(m)
            profiles.extend(p)
        write_csv(paths["prefix_csv"], prefixes)
        write_csv(paths["comparisons_csv"], thread_rows + descriptive_rows)
        write_csv(paths["history_csv"], histories)
        write_csv(paths["modal_csv"], modal)
        write_csv(paths["profiles_csv"], profiles)
        draw(histories, modal, paths)
        inputs = closure()
        result.update(passed=True, current_native_check=new["check"], current_source_run=new["run_entry"],
                      CPU1_short_native_check=short["check"], CPU8_halfsecond_native_check=cpu8["check"],
                      interrupted_HG0_native_check=old["check"], same_CPU1_first458_five_raw_prefixes_exact=True,
                      CPU8_first1469_thread_gates=thread_gates, CPU8_first1469_thread_maxima=thread_max,
                      CPU8_first1469_five_raw_prefix_equalities_descriptive=prefixes[5:],
                      HG_vs_interrupted_HG0_all1517_differences_descriptive=descriptive_max,
                      current_samples=N, old_genuine_header_samples=OLD, old_compared_view_samples=N,
                      old_actual_saved_end_s=6.875, old_original_planned_end_s=4798782 * DT,
                      old_source_solver_exit_code=None, old_original_window_completed=False,
                      actual_profile_times_s=[step * DT for step in PROFILE_STEPS], history_rows=len(histories),
                      modal_rows=len(modal), profile_rows=len(profiles), comparison_rows=len(thread_rows) + len(descriptive_rows),
                      actual_native_density_ledger=density, original_native_guards_preserved=True,
                      raw_BI4_files_reparsed_or_rehashed=False, old_ledger_trailing156_frames_reparsed=False,
                      all_selected_consumed_files_independently_rehashed=True, inputs=inputs,
                      no_interpolation_smoothing_time_snap_sample_deletion_or_periodic_unwrap=True,
                      saved_final_J_weighted_load_is_descriptive_only=True, same_force_stage_load_budget_verified=False,
                      force_stage_guard_independently_observed=False, theory_or_full_consolidation_acceptance=False)
    except Exception as exc:
        result["failure"] = str(exc)
    if "inputs" not in result:
        try:
            result["inputs"] = gathered_bindings()
        except Exception as exc:
            result["inputs"] = list(BOUND.values()) + [e for cache in CACHES for e in cache.values()]
            result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
            result["passed"] = False
    result["files"] = [entry(p) for p in paths.values() if p.exists()]
    result["limits"] = [
        "Only own completed1517 native safety and exactCPU1 first458/same-dtCPU8 first1469 gates can pass here; no independent2s half proof.",
        "HG0 has genuine1673/6.875s interrupted headers and unknown source solver exit; first1517 is a view, not a fabricated completed2s control.",
        "HG-versus-HG0 is descriptive operator evidence across retained builds/threads; neither it nor a small mode proves theory/full/formal acceptance or unsaved stability.",
        "Native density is the actual rho_native ledger export. Common26 column25 remains legacy_Rhop; no fitted load/H or instantaneous-step theory is used.",
        "A_pi=mean over10 initial X columns of (-1)^column times up-positive Uz after subtracting its material-layer mean; preserve all100 signed coefficients.",
    ]
    with record.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], check=str(record), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
