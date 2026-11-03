"""One CPU1 short HG diagnostic: separately owned run, native and compare actions."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import sys
import time

T = Path(__file__).resolve().parents[1]
CASE, SRC = T.parent, T.parents[3] / "src"
TAG = "upl_hg_cpu1_short_r1"
CONTROL = "upl_hg_column_ReleaseCPU_short_c_r1"
OUT, NATIVE = T / "outputs" / TAG, T / "outputs" / (TAG + "_native")
N, DT, STEPS, EVENT = 458, 2.0 ** -19, 13120, 5243
SAVE = sorted(set(range(0, STEPS + 1, 64)) | set(range(5120, 5377)))
COUNTERS = dict(forcecalls=26240, ratecalls=26240, predictorupdates=13120,
                correctorupdates=13120, ratecalculations=13121, ratecachehits=13119)
PINS = {
    "support/upl_hg_column_short_review_r1.py": (31041, "39067679271b7b56413710f0c94643692451d17b96eba0cf497a91b192351dc9"),
    "notes/upl_hg_column_short_review_r1.json": (5645, "b97f028987e14aa6c04ebeb22071cc8d088184609691d997a83e26f57a26c8e1"),
    "support/upl_hg_column_run_r2.ps1": (15481, "63bb27bc3f7b3ebcf31f1063a2847835f185e253a5808d6eacb185660ec6fa2f"),
    "support/upl_hg_column_native_run_r2.ps1": (29808, "0c7f52246fe8627c862e01fa2d453b53d4c1375c1b73337715f68f5ae010ca19"),
    "logs/upl_hg_column_ReleaseCPU_r1.build.json": (455112, "f01ccdaf1c86ec036c598eba888a57d4d9b69d80839d76ccf7b4dc731cc19975"),
    "logs/upl_hg_column_r1.inputs.json": (628141, "c1d9ec4018fff42dd444caf4bca757e5e3d27ad546ca49a68596225abf68e187"),
    "logs/upl_hg_column_short_native_ReleaseCPU_r1.helper.json": (415996, "0951eec35e85f4df82e3cb9abddd456f3b9701bcac7244833cd98c33fa9debad"),
    "logs/upl_hg_column_ReleaseCPU_short_c_r1.run.json": (755521, "ada9a5316c50bc6928d0e7cad732ddb4bb524dd1c10997a88e54da3d9d92ee11"),
    "logs/upl_hg_column_ReleaseCPU_short_c_r1.native_r2.json": (941762, "4e8d5832b5f2b0f147bd516e7629f21971c9aef838cf312190c93d64b597b811"),
    "logs/upl_hg_column_full_review_r1_pair.check.json": (59862, "4f577bcfc5090e93505c8df20112dbc84694396e9078eff7185dcfe78644d2b0"),
    "notes/upl_hg_column_pair_decision_r1.json": (2511, "67ce9825da77992ed36a1f77796a1fde5abcb33d743e1eb37fa854495ad0dd50"),
}
base = np = None
SOURCE_MEMBERSHIP = None


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def utc():
    return datetime.now(timezone.utc).isoformat()


def entry(path):
    path = Path(path).resolve(strict=True)
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=h.hexdigest())


def fresh(*paths):
    need(all(not Path(p).exists() for p in paths), "Retained output/call/receipt path protected")


def seal(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def bind(e):
    return base.bind(e)


def adopt(path):
    e = entry(path)
    bind(e)
    return e


def read(e):
    return json.loads(bind(e).read_text(encoding="utf-8-sig"))


def pin(name):
    size, digest = PINS[name]
    e = dict(path=str((T / name).resolve()), bytes=size, sha256=digest)
    bind(e)
    return e


def reverify():
    for e in list(base.BOUND.values()):
        need(entry(e["path"]) == e, "Consumed artifact changed: " + e["path"])
    if SOURCE_MEMBERSHIP is not None:
        current = {str(p.resolve()) for p in (SRC / "source").iterdir()
                   if p.is_file() and p.suffix.lower() in (".cpp", ".h", ".cu", ".cuh")}
        need(current == SOURCE_MEMBERSHIP, "Current265 source/header membership changed")


def inventory(directory):
    return [entry(p) for p in sorted(Path(directory).rglob("*")) if p.is_file()]


def owned(e, stage):
    c = read(e)
    need(c.get("stage") == stage and c.get("direct_native_call") and c.get("owned_call_exited") and
         c.get("typed_returncode_captured_immediately") and type(c.get("exit_code")) is int and
         c["exit_code"] == 0 and not c.get("invocation_failure"), "Own immediate subprocess exit0 required")
    bind(c["program"])
    bind(c["log"])
    need(c["program"] == c["target_program"] and c["arguments"] == c["target_arguments"],
         "Own direct native target differs")
    return c


def call(program, arguments, cwd, receipt, log, stage):
    fresh(receipt, log)
    started, wall = utc(), time.perf_counter()
    code, failure = None, None
    try:
        with log.open("xb") as stream:
            completed = subprocess.run([program["path"], *arguments], cwd=cwd, stdout=stream,
                                       stderr=subprocess.STDOUT, shell=False,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            code = completed.returncode  # First operation after the direct call returns.
    except Exception as exc:
        failure = str(exc)
    elapsed = time.perf_counter() - wall
    seal(receipt, dict(stage=stage, program=program, target_program=program, arguments=arguments,
                      target_arguments=arguments, working_directory=str(cwd), started_utc=started,
                      ended_utc=utc(), direct_native_call=True, shell=False,
                      typed_returncode_captured_immediately=type(code) is int,
                      owned_call_exited=type(code) is int, exit_code=code, invocation_failure=failure,
                      log=entry(log) if log.exists() else None, invocation_wall_seconds=elapsed,
                      physical_acceptance=False))
    return adopt(receipt)


def initialize():
    global base, np
    # Import only the pinned pure definitions; never its main or a patched dataset.
    path = T / "support/upl_hg_column_short_review_r1.py"
    size, digest = PINS["support/upl_hg_column_short_review_r1.py"]
    e = entry(path)
    need((e["bytes"], e["sha256"]) == (size, digest), "Pinned schema source changed")
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("retained_hg_short_schema", path)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    np = base.np
    for name in PINS:
        pin(name)
    adopt(__file__)
    adopt(T / "notes" / (TAG + ".json"))
    adopt(sys.executable)
    adopt(np.__file__)


def context(current_closure=False):
    global SOURCE_MEMBERSHIP
    manifest_e = pin("logs/upl_hg_column_r1.inputs.json")
    m = read(manifest_e)
    need(m.get("stage") == "upl_hg_column_prepare_r1" and m.get("passed") and m.get("prepared") and
         m.get("input_sources_unchanged") and m.get("integer_steps_times_locked_binary_dt_are_clock_truth") and
         len(m["variants"]) == 3 and len(m["jobs"]) == 6 and len(m["files"]) == 12 and
         not m.get("solver_reader_or_build_invoked") and m.get("physical_acceptance") is False,
         "Genuine retained CPU8 input preparation required")
    jobs = [j for j in m["jobs"] if j["tag"] == CONTROL]
    need(len(jobs) == 1, "Unique retained CPU8 short source job required")
    source = jobs[0]
    variants = [v for v in m["variants"] if v["window"] == "coarse"]
    need(len(variants) == 1, "Unique unchanged coarse input variant required")
    v = variants[0]
    need(source["configuration"] == "ReleaseCPU" and source["window"] == "short_c" and
         source["threads"] == 8 and source["input_variant"] == "coarse" and
         source["steps"] == STEPS and source["expected_samples"] == N and source["dt_s"] == DT and
         source["end_s"] == STEPS * DT and source["event_completed_step"] == EVENT and
         source["post_open_frames"] == 254 and source["expected_native_total_arrays"] == 22 and
         source["expected_total_native_count"] == 1040 and source["expected_HG_counters"] == COUNTERS and
         v["inverse_runtime_bytes_exact"] and v["original_initial_particle_fields_unchanged"] and
         v["changed_runtime_value_only"] == "SoilHourglassXi:0->0.1" and
         source["input_prefix"] == v["input_prefix"] and len(SAVE) == N and SAVE[-1] == STEPS and
         sum(s > EVENT for s in SAVE) == 254, "Frozen CPU8 source settings differ")
    table = [dict(part=i, completed_steps=s, saved_step=s - 1 if s else 0, time_s=s * DT)
             for i, s in enumerate(SAVE)]
    need(len(source["saved_clock_table"]) == N and all(
        tuple(row[k] for k in ("part", "completed_steps", "saved_step")) ==
        tuple(want[k] for k in ("part", "completed_steps", "saved_step"))
        for row, want in zip(source["saved_clock_table"], table)), "Independent integer schedule differs")
    old_args = ["-cpu", "-ompthreads:8", "-stable", "-mdbc_freeslip", v["input_prefix"],
                source["output_directory"], "-dirdataout", "data", "-svres", "-nsteps:13120"]
    need(source["arguments"] == old_args and Path(source["output_directory"]).resolve() ==
         (T / "outputs" / CONTROL).resolve(), "Frozen CPU8 argv/output differs")
    argv = old_args.copy()
    argv[1], argv[5] = "-ompthreads:1", str(OUT)
    job = dict(tag=TAG, backend="CPU", configuration="ReleaseCPU", window="short_c", threads=1,
               input_variant="coarse", input_prefix=v["input_prefix"], output_directory=str(OUT),
               arguments=argv, steps=STEPS, dt_s=DT, end_s=STEPS * DT, expected_samples=N,
               event_completed_step=EVENT, post_open_frames=254, expected_native_total_arrays=22,
               expected_total_native_count=1040, expected_HG_counters=COUNTERS, saved_clock_table=table,
               source_job_tag=CONTROL, source_job_was_CPU8=True, CPU1_was_in_source_manifest=False)
    for k in ("runtime", "initial_BI4", "normals"):
        bind(v[k])
    build_e = pin("logs/upl_hg_column_ReleaseCPU_r1.build.json")
    b = read(build_e)
    need(b.get("stage") == "upl_hg_column_build_r1" and b.get("passed") and b["configuration"] == "ReleaseCPU" and
         b["platform"] == "x64" and b.get("source_bindings_unchanged") and b.get("canonical_programs_unchanged") and
         b.get("runtime_unchanged") and b.get("exact_object_basename_closure") and b.get("objects_include_project_main") and
         b["object_count"] == len(b["objects"]) == 86 and b["non_main_object_count"] == 85 and
         len(b["source_snapshot"]) == 265 and len(b["runtime"]) == 4 and len(b["canonical_programs_before"]) == 7 and
         not b.get("old_objects_reused") and not b.get("canonical_program_installed") and
         (b["program"]["bytes"], b["program"]["sha256"]) ==
         (5115392, "b5a44073b7303b7df917d01105d3cb0a20a0ca1a90a9a963ccb35be9b2b3530c"),
         "Frozen authoritative current CPU86 project-main build required")
    bind(b["program"])
    pair_e = pin("logs/upl_hg_column_full_review_r1_pair.check.json")
    pair, decision = read(pair_e), read(pin("notes/upl_hg_column_pair_decision_r1.json"))
    need(pair.get("stage") == "upl_hg_column_full_review_r1" and pair.get("phase") == "pair" and
         pair.get("passed") and pair.get("independent_half_performed") and
         len(pair["independent_half_gates"]) == 3 and all(x is True for x in pair["independent_half_gates"].values()) and
         pair.get("physical_acceptance") is False and pair["source_builds"][:2] == [build_e, build_e] and
         decision.get("stage") == "upl_hg_column_pair_decision_r1" and decision.get("physical_acceptance") is False and
         not decision.get("later_mid_or_formal_jobs_admitted") and decision["review"]["passed"] and
         (decision["review"]["bytes"], decision["review"]["sha256"]) == (pair_e["bytes"], pair_e["sha256"]) and
         (CASE / decision["review"]["path"]).resolve() == Path(pair_e["path"]), "Inspected full-pair prerequisite differs")
    if current_closure:
        project = base.owned(b["project_call"])
        need(project["program"]["sha256"] == b["build_tool"]["sha256"] and project["arguments"] == b["arguments"],
             "Actual authoritative project build call differs")
        for group in (m["inputs"], m["files"], b["inputs"], b["tools"], b["libraries"], b["objects"],
                      b["compile_sources"], b["canonical_programs_before"], b["runtime_before"]):
            for e in group:
                bind(e)
        for k in ("build_tool", "log", "binlog"):
            bind(b[k])
        for p in b["source_snapshot"] + [b["documentation_snapshot"], b["case_readme_snapshot"]]:
            need((p["original"]["bytes"], p["original"]["sha256"]) ==
                 (p["snapshot"]["bytes"], p["snapshot"]["sha256"]), "Current source/archive pair differs")
            bind(p["original"])
            bind(p["snapshot"])
        current = {str(p.resolve()) for p in (SRC / "source").iterdir()
                   if p.is_file() and p.suffix.lower() in (".cpp", ".h", ".cu", ".cuh")}
        need(current == {str(Path(p["original"]["path"]).resolve()) for p in b["source_snapshot"]},
             "Current265 source/header membership changed")
        SOURCE_MEMBERSHIP = current
        for p in b["runtime"]:
            bind(p["original"])
            bind(p["copy"])
        for p in b["compiler_linker_command_tlogs"]:
            bind(p["original"])
            bind(p["snapshot"])
    return dict(job=job, variant=v, build=b, source_build=build_e, source_input_manifest=manifest_e,
                source_job=source, pair_review=pair_e, pair_decision=pin("notes/upl_hg_column_pair_decision_r1.json"))


def raw_closure(run):
    directory = Path(run["job"]["output_directory"])
    need({str(p.resolve()) for p in directory.rglob("*") if p.is_file()} ==
         {str(Path(e["path"]).resolve()) for e in run["files"]}, "Owned raw output membership changed")
    for e in run["files"]:
        bind(e)
    parts = sorted(p.name for p in (directory / "data").glob("Part_*.bi4"))
    need(parts == ["Part_%04d.bi4" % i for i in range(N)], "Actual458 PART/piece sequence differs")


def load_run(ctx):
    e = adopt(T / "logs" / (TAG + ".run.json"))
    r = read(e)
    need(r.get("stage") == TAG + ".run" and r.get("passed") and r.get("bindings_unchanged") and
         r.get("physical_acceptance") is False and r["job"] == ctx["job"] and
         r["source_build"] == ctx["source_build"] and r["program"] == ctx["build"]["program"] and
         r["source_input_manifest"] == ctx["source_input_manifest"] and r["HG"]["counters"] == COUNTERS,
         "Own CPU1 run/build/derived plan differs")
    c = owned(r["call"], TAG + ".run_call")
    need(c["program"] == r["program"] and c["arguments"] == ctx["job"]["arguments"], "Own CPU1 target/argv differs")
    bind(r["run_out"])
    return e, r


def run_action(result):
    fresh(OUT, T / "logs" / (TAG + ".start.json"), T / "logs" / (TAG + ".call.json"), T / "logs" / (TAG + ".log"))
    ctx = context(True)
    import psutil
    adopt(psutil.__file__)
    active = []
    for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"]):
        name = (p.info["name"] or "").lower()
        if name.startswith("dualsphysics") and "cpu" in name and name.endswith(".exe"):
            active.append(p.info)
    need(not active, "Another actual CPU solver is active")
    me = psutil.Process()
    start = T / "logs" / (TAG + ".start.json")
    result.update(ctx, program=ctx["build"]["program"], CPU_processes_before=active)
    result.pop("build")
    seal(start, dict(stage=TAG + ".start", utc=utc(), owner_pid=me.pid, owner_created_epoch=me.create_time(),
                     owner_executable=me.exe(), owner_command=me.cmdline(), working_directory=str(SRC),
                     owner_script=entry(__file__), job=ctx["job"], source_input_manifest=ctx["source_input_manifest"],
                     source_job_tag=CONTROL, source_build=ctx["source_build"], program=ctx["build"]["program"],
                     pair_review=ctx["pair_review"], pair_decision=ctx["pair_decision"], physical_acceptance=False))
    result["start_record"] = adopt(start)
    reverify()
    result["call"] = call(ctx["build"]["program"], ctx["job"]["arguments"], SRC,
                          T / "logs" / (TAG + ".call.json"), T / "logs" / (TAG + ".log"), TAG + ".run_call")
    c = owned(result["call"], TAG + ".run_call")
    result["run_out"] = adopt(OUT / "Run.out")
    text = Path(result["run_out"]["path"]).read_text(encoding="utf-8-sig")
    need("Finished execution (code=0)." in text and 'RunMode="Stable - Pos-Double - Single core"' in text and
         re.search(r"Steps of simulation[.]+:\s*13120(?:\s|$)", text) and
         re.search(r"Excluded particles[.]+:\s*0(?:\s|$)", text), "Actual CPU1 finish/steps/no exclusions differ")
    need(re.search(r"SoilHourglassXi: 0\.1\s", text) and 'SoilDamping="BuiFukagawa2013"' in text and
         re.search(r"SoilDampingCoef=0\.02(?:\s|$)", text) and 'SoilBoundaryDerivativeSPR="None"' in text,
         "Original xi/eta/SPR settings differ")
    f = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    r = re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
    need(f and r and tuple(map(int, f.groups())) == (26240, 13120, 13120, 26240) and
         tuple(map(int, r.groups())) == (13121, 13119), "Actual HG stage/cache counters differ")
    d = re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)", text)
    need(d, "Actual single-J force/inertia diagnostics missing")
    net, actual, tau, spin = map(float, d.groups())
    need(all(math.isfinite(x) and x >= 0 for x in (net, actual, tau, spin)) and tau <= .2 and spin < .01,
         "Original finite HG stiffness/spin guards failed")
    result["HG"] = dict(counters=COUNTERS, max_reference_history_net_force=net,
                        max_actual_float_add_net_force=actual, max_dt_over_tau=tau, spinbound=spin,
                        reference_history_is_Q_over_M0=True, actual_inertia_is_current_mi=True)
    for key, label in (("simulation_runtime_seconds_reported", "Simulation Runtime"),
                       ("total_runtime_seconds_reported", "Total Runtime")):
        match = re.search(re.escape(label) + r"[.]+:\s*([0-9.eE+-]+) sec\.", text)
        need(match and math.isfinite(float(match[1])) and float(match[1]) >= 0, "Actual runtime missing")
        result[key] = float(match[1])
    result.update(invocation_wall_seconds=c["invocation_wall_seconds"], files=inventory(OUT),
                  steps=STEPS, native_frames=N, public_project_main=True, fixture_or_Run_override=False)
    raw_closure(result)


def helper(ctx):
    h_e = pin("logs/upl_hg_column_short_native_ReleaseCPU_r1.helper.json")
    h = read(h_e)
    need(h.get("passed") and h["stage"] == "upl_hg_column_short_native_build_r1" and h["configuration"] == "ReleaseCPU" and
         h["source_build"] == ctx["source_build"] and h.get("frozen_inputs_unchanged") and
         h.get("actual_project_classes_no_stubs") and h["object_count"] == len(h["project_objects"]) == 85 and
         len(h["runtime"]) == 4 and not h.get("solver_run") and not h.get("program_run") and
         not h.get("canonical_program_installed") and h.get("physical_acceptance") is False and
         (h["program"]["bytes"], h["program"]["sha256"]) ==
         (514560, "6646e8fbaa17cef04202efdea0d2d23d49862aad8c74d5abc1856956d75410fa"), "Frozen short-reader authority differs")
    control = read(pin("logs/" + CONTROL + ".native_r2.json"))
    need(control.get("passed") and control["stage"] == "upl_hg_column_native_run_r2" and
         control["reader_helper"] == h_e and control.get("bindings_unchanged"), "Original reader provenance rejected")
    def identity(e):
        return (str(Path(e["path"]).resolve()), e["bytes"], e["sha256"])
    archives = {identity(p["historical_original"]): p["bound_archive"]
                for p in control["historical_reader_original_to_archive_bindings"]}
    for e in h["inputs"] + h["project_objects"] + h["actual_includes"] + [h["helper_object"], h["compiler_dependency_record"], h["program"]]:
        bind(archives.get(identity(e), e))
    for p in h["runtime"]:
        bind(archives.get(identity(p["original"]), p["original"]))
        bind(p["copy"])
    compile_call, link_call = base.owned(h["compile_call"]), base.owned(h["link_call"])
    objects = [str(Path(a.strip('"')).resolve()) for a in link_call["arguments"] if Path(a.strip('"')).suffix.lower() == ".obj"]
    wanted = [str(Path(e["path"]).resolve()) for e in h["project_objects"] + [h["helper_object"]]]
    need(len(objects) == len(set(objects)) == 86 and set(objects) == set(wanted) and
         all(Path(p).name.lower() != "main.obj" for p in objects), "Actual reader CPU85+1 link closure differs")
    cpp = [a for a in compile_call["arguments"] if Path(a.strip('"')).suffix.lower() == ".cpp"]
    need(len(cpp) == 1 and Path(cpp[0].strip('"')).name == "upl_hg_column_short_native_r1.cpp", "Actual reader compile source differs")
    return h_e, h


def exports(native_dir, files, completion):
    leaves = {Path(e["path"]).name: e for e in files}
    expected_leaves = {"original15.bin", "physical.bin", "clock.bin", "common_j_theta.bin", "soil_n.bin", "native_ids.csv",
                       "fixed_ids.csv", "history.csv", "ledger.csv", "fixed_samples.csv", "last_poro.csv", "columns.csv", "completion.json"}
    need(len(files) == len(leaves) == 13 and set(leaves) == expected_leaves and leaves["completion.json"] == completion and
         all(Path(e["path"]).resolve().parent == native_dir.resolve() for e in files) and
         {p.name for p in native_dir.iterdir()} == expected_leaves, "Exactly13 own native output leaves required")
    d = read(completion)
    exact = dict(stage="upl_hg_column_short_native_r1", backend="CPU_public", window="dyadic_short458", preset="coarse",
                 grid="c", model="constant", conductivity_model=0, conductivity_Ck=0, native_count=1000, fixed_count=40,
                 total_native_count=1040, samples=N, physical_columns=26, physical_schema=base.SCHEMA,
                 original_typed_arrays=15, native_dynamic_double_arrays=6, native_total_arrays=22, dt_s=DT,
                 actual_end_s=STEPS * DT, planned_end_s=STEPS * DT, planned_completed_steps=STEPS,
                 declared_ramp_and_drain_event_s=EVENT * DT, noninitial_signed_dterror_intervals=457,
                 soil_ledger_checks=458000, fixed_public_zero_marker_checks=18320, all_native_J_theta_rows=476320,
                 soil_native_n_rows=458000, post_open_completed_step_threshold=EVENT, post_open_frames=254,
                 post_open_drained_particle_checks=2540, max_activeDrainCount=10)
    need(d.get("passed") is True and all(d.get(k) == v for k, v in exact.items()), "Original typed schema/count/clock coverage differs")
    required = ("public_schema", "public_master_on", "PART_typed_public_metadata_verified", "native_PosDiv_present", "native_PosDiv_is_float",
                "native_V_rho_k_present", "no_exclusions", "initial_rest_and_decimal_lattice_verified", "double_stress_and_float_display_verified",
                "all_exported_physical_fields_finite", "declared_saved_completed_steps_exact", "actual_time_step_locked_dt_exact",
                "initial_dterror_excluded_from_noninitial_summary", "fixed_J_theta_original15_not_zeroed_or_masked",
                "common26_column21_is_actual_ExcessPorePress", "pre_open_event_pressure_not_forced_zero", "density_and_J_not_frozen_on_drained_receivers",
                "event_is_declared_preset_not_BI4_metadata", "descriptive_saved_field_summaries", "declared_first458_full_schedule_only",
                "post_open_native_receiver_coverage_verified")
    forbidden = ("GPU_private_fixed_n_mirror_to_public_zero_is_schema_change", "PosDiv_fabricated_or_derived", "full_half_second_complete",
                 "full_window_prefix_data_compared", "new_scientific_acceptance_gate", "same_force_stage_load_budget_verified",
                 "force_stage_guard_independently_observed", "historical_private_comparison_performed_by_reader", "live_final_compared_by_reader",
                 "independent_half_performed", "physical_acceptance")
    need(all(d.get(k) is True for k in required) and all(d.get(k) is False for k in forbidden) and
         d["initial_empty_dterror_intervals"] in (0, 1) and math.isfinite(d["max_noninitial_signed_dterror_s"]) and
         d["max_noninitial_signed_dterror_s"] <= 1e-14 and math.isfinite(d["max_ledger_relative_error"]) and
         0 <= d["max_ledger_relative_error"] <= 5e-13, "Original signed/ledger/finite/unmasked native guards rejected")
    headers = []
    for name, header, record in (("original15.bin", (1040, 15, N), 166408), ("physical.bin", (1000, 26, N), 208008),
                                 ("clock.bin", (N, 28), 28), ("common_j_theta.bin", (1040, 2, N), 16648), ("soil_n.bin", (1000, 1, N), 8008)):
        p = bind(leaves[name])
        with p.open("rb") as stream:
            need(struct.unpack("<" + "I" * len(header), stream.read(4 * len(header))) == header, "Binary header differs: " + name)
        need(p.stat().st_size == 4 * len(header) + N * record, "Binary length differs: " + name)
        headers.append(dict(file=leaves[name], header=header, record_bytes=record, length_verified=True))
    p = base.mapped(leaves["physical.bin"], (1000, 26, N), [("time", "<f8"), ("q", "<f8", (1000, 26))], N)
    clock = base.mapped(leaves["clock.bin"], (N, 28), [("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")], N)
    jt = base.mapped(leaves["common_j_theta.bin"], (1040, 2, N), [("time", "<f8"), ("q", "<f8", (1040, 2))], N)
    n = base.mapped(leaves["soil_n.bin"], (1000, 1, N), [("time", "<f8"), ("q", "<f8", (1000,))], N)
    times = np.asarray(SAVE) * DT
    need(all(base.bits(a["time"], times) for a in (p, clock, jt, n)) and base.bits(clock["dt"], np.full(N, DT)) and
         np.array_equal(clock["step"], np.where(np.asarray(SAVE) > 0, np.asarray(SAVE) - 1, 0)) and
         np.isfinite(clock["error"]).all() and np.all(clock["error"][1:] <= 1e-14) and
         np.all(clock["error"][1:] != -np.finfo(float).max), "Actual exact binary clocks/signed noninitial intervals differ")
    positions = {}
    for kind, count, first in (("native", 1000, 40), ("fixed", 40, 0)):
        rows = base.csv_rows(leaves[kind + "_ids.csv"])
        need(len(rows) == count and all((int(row["row"]), int(row["id"])) == (i, first + i) for i, row in enumerate(rows)), "All1040 original IDs differ")
        positions[kind] = np.asarray([[float(row[k]) for k in ("x0", "y0", "z0")] for row in rows])
        need(np.isfinite(positions[kind]).all(), "Nonfinite original coordinates")
    need(base.bits(p["q"][0, :, :3], positions["native"]), "Initial native material coordinates differ")
    cols = base.csv_rows(leaves["columns.csv"])
    need([row["name"] for row in cols] == base.FIELDS and [int(row["column"]) for row in cols] == list(range(26)), "Unmasked common26 semantics differ")
    history = base.csv_rows(leaves["history.csv"])
    need(len(history) == N, "Native458 history rows required")
    for i, row in enumerate(history):
        post = SAVE[i] > EVENT
        need((int(row["part"]), int(row["completed_step"]), int(row["saved_step"]), int(row["post_open_by_completed_step"]), int(row["activeDrainCount"])) ==
             (i, SAVE[i], SAVE[i] - 1 if i else 0, int(post), 10 if post else 0) and
             base.bits(float(row["time_s"]), times[i]) and base.bits(float(row["dt_s"]), DT) and
             base.bits(float(row["signed_dterror_s"]), clock["error"][i]) and
             0 <= float(row["max_ledger_relative_error"]) <= 5e-13, "Per-frame clock/drain/ledger differs")
        error = float(row["signed_dterror_s"])
        need(math.isfinite(error) and int(row["dterror_used_in_noninitial_summary"]) == int(i > 0) and
             ((int(row["dterror_interval_empty"]) == 0 and error <= 1e-14) if i else
              (int(row["dterror_interval_empty"]) == 1 or error <= 1e-14)), "Original signed interval/sentinel semantics differ")
    final = base.csv_rows(leaves["last_poro.csv"])
    need(len(final) == 1000 and all(int(row["id"]) == i + 40 and all(math.isfinite(float(row[k])) for k in ("J", "n", "theta"))
                                  for i, row in enumerate(final)), "Final1000 J/n/theta export differs")
    return dict(p=p, clock=clock, jt=jt, n=n, x0=positions["native"], fixed_x0=positions["fixed"],
                headers=headers, leaves=leaves, completion=d)


def native_action(result):
    fresh(NATIVE, T / "logs" / (TAG + "_reader.call.json"), T / "logs" / (TAG + "_reader.log"))
    ctx = context(True)
    run_e, r = load_run(ctx)
    for e in r["inputs"]:
        bind(e)
    raw_closure(r)
    h_e, h = helper(ctx)
    reverify()
    result.update(job=ctx["job"], source_run=run_e, source_build=ctx["source_build"], source_input_manifest=ctx["source_input_manifest"],
                  reader_helper=h_e, reader_source_build=h["source_build"], paths=dict(solver_dir=str(OUT), native_dir=str(NATIVE)))
    result["reader_call"] = call(h["program"], ["--read", "CPU", str(OUT / "data"), "coarse", str(NATIVE)], CASE,
                                 T / "logs" / (TAG + "_reader.call.json"), T / "logs" / (TAG + "_reader.log"), TAG + ".reader_call")
    owned(result["reader_call"], TAG + ".reader_call")  # Sealed before completion/export inspection.
    result.update(completion=adopt(NATIVE / "completion.json"), files=inventory(NATIVE))
    data = exports(NATIVE, result["files"], result["completion"])
    result.update(binary_header_length_checks=data["headers"], original_native_guards_passed=True,
                  typed_native_total_arrays=22, typed_native_total_ID_count=1040, typed_soil_ledger_checks=458000,
                  typed_fixed_zero_marker_checks=18320, ledger_CSV_rows_reparsed=0, post_open_frames_verified=254,
                  drainage_nonempty_per_frame_verified=True, saved_step_plan_verified=True, reader_rebuilt=False,
                  historical_reader_originals_asserted_current=False, solver_or_build_invoked=False)
    raw_closure(r)


def compare_action(result):
    table_path = T / "logs" / (TAG + ".compare.csv")
    fresh(table_path)
    ctx = context()
    run_e, run = load_run(ctx)
    native_e = adopt(T / "logs" / (TAG + ".native.json"))
    native = read(native_e)
    need(native.get("stage") == TAG + ".native" and native.get("passed") and native.get("bindings_unchanged") and
         native.get("original_native_guards_passed") and native.get("drainage_nonempty_per_frame_verified") and
         native["source_run"] == run_e and native["source_build"] == ctx["source_build"] and native["job"] == ctx["job"] and
         native.get("physical_acceptance") is False and native["reader_helper"] == pin("logs/upl_hg_column_short_native_ReleaseCPU_r1.helper.json"),
         "Own independent CPU1 native safety required")
    reader = owned(native["reader_call"], TAG + ".reader_call")
    h = read(native["reader_helper"])
    need(reader["program"] == h["program"] and reader["arguments"] ==
         ["--read", "CPU", str(OUT / "data"), "coarse", str(NATIVE)], "Own CPU1 decoder target/argv differs")
    a = exports(NATIVE, native["files"], native["completion"])
    control = base.dataset("coarse", True)  # Unchanged real CPU8 dataset/stage guards.
    b = exports(Path(control["native"]["paths"]["native_dir"]), control["native"]["files"], control["native"]["completion"])
    need(control["run"]["program"] == run["program"] and control["run"]["source_build"] == run["source_build"] and
         control["material"] == ctx["variant"] and base.bits(a["x0"], b["x0"]) and base.bits(a["fixed_x0"], b["fixed_x0"]) and
         base.bits(a["p"]["q"][0], b["p"]["q"][0]), "Same current build/input/all initial26 fields/material coordinates required")
    rows, rms_max, abs_max = [], np.zeros(26), np.zeros(26)
    for i in range(N):
        av, bv = np.asarray(a["p"]["q"][i]), np.asarray(b["p"]["q"][i])
        need(np.isfinite(av).all() and np.isfinite(bv).all(), "Nonfinite thread-comparison field")
        delta = av - bv
        rms, maximum = np.sqrt(np.mean(delta * delta, axis=0)), np.max(np.abs(delta), axis=0)
        du = (av[:, :3] - a["x0"]) - (bv[:, :3] - b["x0"])
        row = dict(part=i, completed_step=SAVE[i], CPU1_actual_time_s=float(a["clock"]["time"][i]),
                   CPU8_actual_time_s=float(b["clock"]["time"][i]), pressure_RMS_Pa=float(rms[6]),
                   material_XYZ_displacement_difference_max_mm=float(1000 * np.linalg.norm(du, axis=1).max()),
                   velocity_XYZ_RMS_m_s=float(np.sqrt(np.mean(np.sum(delta[:, 3:6] ** 2, axis=1)))),
                   stored_stress6_RMS_Pa=float(np.sqrt(np.mean(np.sum(delta[:, 10:16] ** 2, axis=1)))),
                   CPU1_signed_dterror_s=float(a["clock"]["error"][i]), CPU8_signed_dterror_s=float(b["clock"]["error"][i]))
        row.update({name + "_RMS_difference": float(x) for name, x in zip(base.FIELDS, rms)})
        row.update({name + "_max_abs_difference": float(x) for name, x in zip(base.FIELDS, maximum)})
        need(all(math.isfinite(x) for x in row.values()), "Nonfinite thread-comparison reduction")
        rows.append(row)
        rms_max, abs_max = np.maximum(rms_max, rms), np.maximum(abs_max, maximum)
    with table_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    pmax = max(row["pressure_RMS_Pa"] for row in rows)
    umax = max(row["material_XYZ_displacement_difference_max_mm"] for row in rows)
    tmax = float(np.max(np.abs(a["clock"]["time"] - b["clock"]["time"])))
    gates = dict(pressure_RMS_all458_le_5Pa=pmax <= 5., material_XYZ_all458_le_0_005mm=umax <= .005,
                 actual_time_all458_le_1e_minus14_s=tmax <= 1e-14)
    binary_equal = {name: a["leaves"][name]["sha256"] == b["leaves"][name]["sha256"] and
                    a["leaves"][name]["bytes"] == b["leaves"][name]["bytes"] for name in
                    ("original15.bin", "physical.bin", "clock.bin", "common_j_theta.bin", "soil_n.bin")}
    control_text = bind(control["run"]["run_out"]).read_text(encoding="utf-8-sig")
    control_runtime = re.search(r"Simulation Runtime[.]+:\s*([0-9.eE+-]+) sec\.", control_text)
    need(control_runtime and math.isfinite(float(control_runtime[1])) and float(control_runtime[1]) > 0,
         "Retained actual CPU8 loop runtime missing")
    result.update(source_runs=[run_e, control["run_entry"]], native_checks=[native_e, control["check"]], samples=N,
                  thread_compatibility_gates=gates, max_pressure_RMS_Pa=pmax, max_material_XYZ_difference_mm=umax,
                  max_actual_time_difference_s=tmax, all26_max_RMS=dict(zip(base.FIELDS, map(float, rms_max))),
                  all26_max_abs=dict(zip(base.FIELDS, map(float, abs_max))), five_binary_exports_exact_descriptive=binary_equal,
                  max_all1040_J_theta_abs_descriptive=float(np.max(np.abs(a["jt"]["q"] - b["jt"]["q"]))),
                  max_soil_n_abs_descriptive=float(np.max(np.abs(a["n"]["q"] - b["n"]["q"]))),
                  CPU1_simulation_runtime_seconds=run["simulation_runtime_seconds_reported"],
                  CPU8_retained_simulation_runtime_seconds=float(control_runtime[1]), controlled_speedup_claimed=False,
                  no_interpolation_smoothing_time_snap_or_periodic_unwrap=True, temporal_half_study=False,
                  raw_PART_files_rehashed=False, solver_reader_or_build_invoked=False, files=[adopt(table_path)])
    need(all(gates.values()), "Original same-dt thread compatibility thresholds failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("run", "native", "compare"), required=True)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Root full-read and explicit authorization of this one action are required")
    record = T / "logs" / (TAG + "." + args.action + ".json")
    fresh(record)
    result = dict(stage=TAG + "." + args.action, tag=TAG, action=args.action, passed=False,
                  backend="CPU", configuration="ReleaseCPU", window="short_c", threads=1,
                  physical_acceptance=False, later_mid_or_formal_jobs_admitted=False, failure=None)
    try:
        initialize()
        {"run": run_action, "native": native_action, "compare": compare_action}[args.action](result)
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        if base is not None:
            reverify()
            result["bindings_unchanged"] = True
        else:
            result["bindings_unchanged"] = False
    except Exception as exc:
        result["bindings_unchanged"] = False
        result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
        result["passed"] = False
    # Preserve partial outputs and original call receipts; never retry or chain actions.
    if args.action in ("run", "native"):
        directory = OUT if args.action == "run" else NATIVE
        if directory.exists() and "files" not in result:
            result["files"] = inventory(directory)
    result["inputs"] = list(base.BOUND.values()) if base is not None else []
    result.update(saved_final_J_weighted_load_is_descriptive_only=True, same_force_stage_load_budget_verified=False,
                  force_stage_guard_independently_observed=False, acceptance_gates_relaxed=False,
                  source_project_formal_or_canonical_files_written_by_this_action=False, following_action_launched=False)
    seal(record, result)
    print(json.dumps(dict(passed=result["passed"], action=args.action, receipt=str(record), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
