"""One admitted completed ON short-run decode and its applicable offline identity check."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

T = Path(__file__).resolve().parents[1]
NAME = "upl_spr_av_short_review_r1"
TAGS = ("upl_spr_av_new_ON0_r1", "upl_spr_av_new_ONSPR_r1", "upl_spr_av_new_requested_ON_r1")
PINS = {
    "support/upl_hg_cpu1_short_r1.py": (38151, "9553ea64dfa2c08ef14f9fa44ba8e8dd09e63608b516083d3478ec7ec664ebbc"),
    "notes/upl_hg_cpu1_short_r1.json": (7281, "9ee70adce50bec3585e5997fbe02c6405acbafba6e5ec3aa79577224655dc905"),
    "support/upl_spr_av_run_r1.py": (15888, "574c3a4da7ade2c1fda97d93a95c1544d6dc05e6896a5f08594053992d2fb757"),
    "notes/upl_spr_av_run_r1.json": (3340, "42ceee38a1ba1230cb2475eda1d827c30d3c05fe4c7842a0a60b058d7cbadd59"),
    "logs/upl_spr_av_r1.inputs.json": (823007, "8ed0f935b0f7d602f6ee381d639fe9077ee173602b7c2878527828e12d5daa8b"),
}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def utc():
    return datetime.now(timezone.utc).isoformat()


def entry(path):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def seal(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def load(relative, name):
    path = T / relative
    value = entry(path)
    need((value["bytes"], value["sha256"]) == PINS[relative], "Pinned definition source changed: " + relative)
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # Pure definitions only; no main/run/native action is called.
    return module


def definitions():
    old = load("support/upl_hg_cpu1_short_r1.py", "retained_cpu1_short_definitions")
    old.initialize()  # Pinned schema definitions and fixed metadata, not context(True) or an action.
    owner = load("support/upl_spr_av_run_r1.py", "spr_av_short_owner_definitions")
    for name, (size, digest) in PINS.items():
        value = dict(path=str((T / name).resolve()), bytes=size, sha256=digest)
        old.bind(value)
        owner.bind(value)
    for path in (__file__, T / "notes" / (NAME + ".json"), sys.executable):
        old.adopt(path)
        owner.adopt(path)
    return owner, old


def completed(owner, old, tag):
    ctx = owner.context(tag)
    job = ctx["job"]
    need(tag in TAGS and job["master"] == 1 and job["expected_native_total_arrays"] == 22 and
         job["expected_total_native_count"] == 1040 and job["post_open_frames"] == 254 and
         job["post_open_drained_particle_checks_expected"] == 2540 and
         job["expected_post_open_receivers_per_frame"] == 10 and job["half_job"] is False,
         "Only the prepared master-on CPU1 short458 job is admitted")
    run_e = owner.adopt(T / "logs" / (tag + ".run.json"))
    run = owner.read(run_e)
    need(run.get("stage") == tag + ".run" and run.get("tag") == tag and run.get("passed") is True and
         run.get("failure") is None and run.get("backend") == "CPU" and run.get("configuration") == "ReleaseCPU" and
         run.get("threads") == 1 and run.get("steps") == 13120 and run.get("native_frames") == 458 and
         run.get("bindings_unchanged") is True and run.get("independent_final_rehash_performed") is True and
         run.get("public_project_main") is True and run.get("fixture_or_Run_override") is False and
         run.get("native_decoder_invoked") is False and run.get("automatic_follow_up") is False and
         run.get("physical_acceptance") is False and run["job"] == job and
         run["source_input_manifest"] == ctx["manifest"] and run["source_build"] == ctx["source_build"] and
         run["program"] == ctx["program"], "Completed actual selected project-main Run required")
    need(Path(run["start_record"]["path"]).resolve() == (T / "logs" / (tag + ".start.json")).resolve(),
         "Completed Run start path differs")
    start = owner.read(run["start_record"])
    need(start.get("stage") == tag + ".start" and start["job"] == job and start["program"] == run["program"] and
         start["source_build"] == ctx["source_build"] and start["source_input_manifest"] == ctx["manifest"] and
         start.get("direct_owner_no_scheduler") is True and start.get("physical_acceptance") is False and
         start["owner_script"] == owner.adopt(T / "support/upl_spr_av_run_r1.py"), "Actual start/job/script identity differs")
    call = owner.owned(run["call"], tag + ".run_call")
    need(Path(run["call"]["path"]).resolve() == (T / "logs" / (tag + ".call.json")).resolve() and
         call.get("actual_solver_call") is True and call.get("public_project_main") is True and
         call.get("fixture_or_Run_override") is False and call.get("shell") is False and
         call["program"] == call["target_program"] == run["program"] and
         call["arguments"] == call["target_arguments"] == job["arguments"] and call["start_record"] == run["start_record"],
         "Original immediate typed solver call/program/argv/start differs")
    for value in run["inputs"]:
        owner.bind(value)
    directory = Path(job["output_directory"])
    need(Path(run["run_out"]["path"]).resolve() == (directory / "Run.out").resolve(), "Own Run.out required")
    owner.bind(run["run_out"])
    paths = {Path(e["path"]).resolve() for e in run["files"]}
    need(len(paths) == len(run["files"]) and all(p.is_relative_to(directory.resolve()) for p in paths),
         "Completed solver payload path closure differs")
    old.raw_closure(run)  # Unchanged raw458 membership and actual raw file hashes, no native parsing.
    observed = owner.check_output(job, directory)
    need(observed["HG"] == run["HG"] and observed["steps"] == run["steps"] and
         observed["native_frames"] == run["native_frames"], "Original Run.out HG guards changed")
    return dict(context=ctx, run=run, run_entry=run_e)


def native_data(old, native, helper_e, helper, tag, run_e, directory):
    need(native.get("stage") == tag + ".native" and native.get("passed") is True and
         native.get("bindings_unchanged") is True and native.get("original_native_guards_passed") is True and
         native.get("drainage_nonempty_per_frame_verified") is True and native.get("physical_acceptance") is False and
         native["source_run"] == run_e and native["reader_helper"] == helper_e and
         Path(native["paths"]["native_dir"]).resolve() == directory.resolve(), "Completed own native review required")
    reader = old.owned(native["reader_call"], tag + ".reader_call")
    need(reader.get("shell") is False and reader["program"] == helper["program"] and reader["arguments"] ==
         ["--read", "CPU", str(T / "outputs" / tag / "data"), "coarse", str(directory)],
         "Original decoder program/argv differs")
    for value in native["files"]:
        old.bind(value)
    return old.exports(directory, native["files"], native["completion"])


def reference(owner, old, tag, helper_e, helper):
    if tag == TAGS[2]:
        return None
    peer = "upl_hg_cpu1_short_r1" if tag == TAGS[0] else TAGS[0]
    if tag == TAGS[0]:
        # Reuse its closed historical authority, never legacy.context(True) or old mutable inputs.
        run_e = old.adopt(T / "logs" / (peer + ".run.json"))
        run = old.read(run_e)
        build_e = old.pin("logs/upl_hg_column_ReleaseCPU_r1.build.json")
        need(run.get("stage") == peer + ".run" and run.get("passed") is True and
             run.get("bindings_unchanged") is True and run.get("physical_acceptance") is False and
             run["source_build"] == build_e and run["program"] == old.read(build_e)["program"] and
             run["job"]["threads"] == 1 and run["job"]["steps"] == 13120 and run["job"]["expected_samples"] == 458 and
             run["HG"]["counters"] == old.COUNTERS, "Retained actual CPU1 short control required")
        solver = old.owned(run["call"], peer + ".run_call")
        need(solver["program"] == run["program"] and solver["arguments"] == run["job"]["arguments"],
             "Retained CPU1 solver target/arguments differ")
        old.raw_closure(run)
    else:
        source = completed(owner, old, peer)
        run_e, run = source["run_entry"], source["run"]
    native_e = old.adopt(T / "logs" / (peer + ".native.json"))
    native = old.read(native_e)
    need(native["source_build"] == run["source_build"], "Reference native/run build identity differs")
    if peer == TAGS[0]:
        need(native.get("wrapper") == NAME and native.get("independent_final_rehash_performed") is True and
             native.get("reader_attempts") == 1 and native.get("all13_exports_byte_identical") is True and
             native.get("all22_exported_arrays_and_actual_clocks_bitwise_identical") is True,
             "ONSPR requires the passed new ON0 exact-control native review")
    directory = T / "outputs" / (peer + "_native")
    data = native_data(old, native, helper_e, helper, peer, run_e, directory)
    return dict(tag=peer, native_receipt=native_e, source_run=run_e, data=data)


def descriptive(old, data):
    history = old.base.csv_rows(data["leaves"]["history.csv"])
    names = ("pressure_RMS_Pa", "top10_settlement_mean_mm", "bottom10_settlement_mean_mm", "settlement_abs_max_mm",
             "velocity_XYZ_RMS_m_s", "saved_theta_RMS_s_inv", "stored_stress_Frobenius_RMS_Pa",
             "native_current_rho_min_kg_m3", "native_current_rho_max_kg_m3", "native_rho_V_mass_kg_per_m")
    result = {}
    for name in names:
        values = [float(row[name]) for row in history]
        need(all(math.isfinite(value) for value in values), "Nonfinite descriptive native history")
        result[name] = dict(first=values[0], final=values[-1], min=min(values), max=max(values), max_abs=max(map(abs, values)))
    return result


def action(owner, old, tag, result):
    source = completed(owner, old, tag)
    helper_e, helper = old.helper(dict(source_build=old.pin("logs/upl_hg_column_ReleaseCPU_r1.build.json")))
    peer = reference(owner, old, tag, helper_e, helper)  # Complete prerequisite review before the sole decode.
    import psutil
    owner.adopt(psutil.__file__)
    old.adopt(psutil.__file__)
    active = [p.info for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"])
              if ((p.info["name"] or "").lower().startswith("dualsphysics") and "cpu" in (p.info["name"] or "").lower()) or
              (p.info["name"] or "").lower() == Path(helper["program"]["path"]).name.lower()]
    need(not active, "An actual CPU solver or this native reader is active; no concurrent/duplicate decode")
    native_dir = T / "outputs" / (tag + "_native")
    start_path = T / "logs" / (tag + ".native.start.json")
    me = psutil.Process()
    owner.final_bindings()
    old.reverify()
    seal(start_path, dict(stage=tag + ".native.start", utc=utc(), source_run=source["run_entry"],
        source_start=source["run"]["start_record"], reader_helper=helper_e, program=helper["program"],
        owner=dict(pid=me.pid, created_epoch=me.create_time(), exe=me.exe(), command=me.cmdline(), cwd=str(Path.cwd().resolve())),
        owner_script=entry(__file__), one_reader_attempt_max=True, retry_or_rearm_allowed=False, physical_acceptance=False))
    result.update(job=source["context"]["job"], source_run=source["run_entry"], source_start=source["run"]["start_record"],
        source_solver_call=source["run"]["call"], source_build=source["run"]["source_build"], source_input_manifest=source["context"]["manifest"],
        reader_helper=helper_e, reader_source_build=helper["source_build"], native_reader_start=old.adopt(start_path),
        paths=dict(solver_dir=source["run"]["job"]["output_directory"], native_dir=str(native_dir)), reader_attempts=1)
    result["reader_call"] = old.call(helper["program"], ["--read", "CPU", str(T / "outputs" / tag / "data"), "coarse", str(native_dir)],
        T.parent, T / "logs" / (tag + "_reader.call.json"), T / "logs" / (tag + "_reader.log"), tag + ".reader_call")
    old.owned(result["reader_call"], tag + ".reader_call")  # Original immediate typed exit is sealed first.
    result.update(completion=old.adopt(native_dir / "completion.json"), files=old.inventory(native_dir))
    for value in result["files"]:
        old.bind(value)
    data = old.exports(native_dir, result["files"], result["completion"])  # Unchanged22/1040/ledger/signed-clock guards.
    result.update(binary_header_length_checks=data["headers"], original_native_guards_passed=True,
        drainage_nonempty_per_frame_verified=True, post_open_frames_verified=254, post_open_receiver_checks_verified=2540,
        all22_serialized_exports_checked=True, native_total_arrays=22, native_total_ID_count=1040,
        native_samples=458, typed_soil_ledger_checks=458000, typed_fixed_zero_marker_checks=18320,
        descriptive_history=descriptive(old, data), exact_reference_required=peer is not None,
        requested_ON_safety_and_descriptive_only=tag == TAGS[2])
    if peer is not None:
        checks = {name: dict(actual=data["leaves"][name], reference=peer["data"]["leaves"][name],
            exact=(data["leaves"][name]["bytes"], data["leaves"][name]["sha256"]) ==
                  (peer["data"]["leaves"][name]["bytes"], peer["data"]["leaves"][name]["sha256"])) for name in data["leaves"]}
        result.update(exact_reference=dict(tag=peer["tag"], native_receipt=peer["native_receipt"], source_run=peer["source_run"]),
            serialized_export_identity=checks, all13_exports_byte_identical=all(value["exact"] for value in checks.values()),
            all22_exported_arrays_and_actual_clocks_bitwise_identical=all(value["exact"] for value in checks.values()))
        need(result["all13_exports_byte_identical"], "Applicable exported22-array/actual-clock bitwise identity failed")
    old.raw_closure(source["run"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", choices=TAGS, required=True)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Root full-read and explicit authorization of this one completed-run native action required")
    tag = args.job
    record, native_dir = T / "logs" / (tag + ".native.json"), T / "outputs" / (tag + "_native")
    fresh = [record, native_dir, *(T / "logs" / (tag + suffix) for suffix in
             (".native.start.json", "_reader.call.json", "_reader.log"))]
    need(all(not path.exists() for path in fresh), "Retained native/start/call/log/output protected; never retry or rearm")
    owner = old = None
    result = dict(stage=tag + ".native", wrapper=NAME, tag=tag, passed=False, failure=None, backend="CPU", configuration="ReleaseCPU",
        window="short458", threads=1, physical_acceptance=False, reader_attempts=0, reader_rebuilt=False,
        historical_reader_originals_asserted_current=False, historical_mutable_source_or_canonical_revalidated=False,
        solver_or_build_invoked=False, following_action_launched=False, watcher_or_queue_invoked=False,
        independent_half_performed=False, full_2Tv_admitted=False, new_scientific_acceptance_gate=False)
    try:
        owner, old = definitions()
        action(owner, old, tag, result)
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        need(owner is not None and old is not None, "Pinned definitions were not completely initialized")
        result["owner_definition_inputs"] = owner.final_bindings()
        old.reverify()
        result["schema_reader_inputs"] = list(old.base.BOUND.values())
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = True
    except Exception as exc:
        result["passed"] = result["bindings_unchanged"] = result["independent_final_rehash_performed"] = False
        result["owner_definition_inputs"] = list(owner.BOUND.values()) if owner is not None else []
        result["schema_reader_inputs"] = list(old.base.BOUND.values()) if old is not None and old.base is not None else []
        result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
    if native_dir.exists() and "files" not in result:
        result["files"] = [entry(path) for path in sorted(native_dir.rglob("*")) if path.is_file()]
    seal(record, result)
    print(json.dumps(dict(passed=result["passed"], job=tag, receipt=str(record), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
