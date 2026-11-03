"""Own one bounded larger-step CPU1 candidate; preserve the exact live fine control."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.dom.minidom as DOM

T = Path(__file__).resolve().parents[1]
NAME, TAG = "upl_bigstep_r1_run", "upl_bigstep_c625_r1"
STEPS, N, DT, EVENT = 320000, 1292, float("6.2501430511474609E-06"), 1600
OUT, RECORD = T / "outputs" / TAG, T / "logs" / (TAG + ".run.json")
COUNTERS = dict(forcecalls=640000, ratecalls=640000, predictorupdates=320000,
                correctorupdates=320000, ratecalculations=320001, ratecachehits=319999)
PINS = {
    "support/upl_bigstep_r1_prepare.py": (14051, "af24ab0c96a88585bcda5c26589a829d21aa317054dcc5127311faa963b1fff2"),
    "notes/upl_bigstep_r1_prepare.json": (4043, "542f42bf3ef78c0939f1f94ea0e37d0159b860c0079b1a14246cf1cc5e7679da"),
    "logs/upl_spr_av_2tv_CPU1_r1.start.json": (370640, "3df188211e1a4dca636e314900815377bfd60f42f4c30a03ac3da3f6acd8ff22"),
}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def definitions():
    sys.dont_write_bytecode = True
    path = T / "support/upl_bigstep_r1_prepare.py"
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    need((path.stat().st_size, digest) == PINS["support/upl_bigstep_r1_prepare.py"], "Frozen candidate preparation definitions changed")
    spec = importlib.util.spec_from_file_location("bigstep_frozen_preparation_definitions", path)
    p = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(p)  # Only definitions/schedule; never preparation or either old main/run/context.
    u = p.definitions()
    for name, (size, sha) in PINS.items():
        u.bind(dict(path=str(T / name), bytes=size, sha256=sha))
    for path in (__file__, T / "notes" / (NAME + ".json"), sys.executable):
        u.adopt(path)
    return u, p


def context(u, p):
    manifest = u.adopt(T / "logs/upl_bigstep_r1.inputs.json")
    m = u.read(manifest)
    need(m.get("stage") == "upl_bigstep_r1_prepare" and m.get("passed") is True and m.get("prepared") is True and
         m.get("bindings_unchanged") is True and m.get("independent_final_rehash_performed") is True and
         m.get("physical_acceptance") is False and len(m["jobs"]) == 1, "Actual passed candidate preparation required")
    job = m["jobs"][0]
    args = ["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip", str(p.PREFIX), str(OUT),
            "-dirdataout", "data", "-svres", "-nsteps:320000"]
    need(job["tag"] == TAG and job["window"] == "candidate2s" and job["arguments"] == args and job["steps"] == STEPS and
         job["dt_s"] == DT and job["expected_samples"] == N and job["end_s"] == 2.0000457763593587 and
         job["nominal_end_s"] == job["runtime_TimeMax_s"] == 2.0000457763671875 and job["event_completed_step"] == EVENT and
         job["threads"] == 1 and job["expected_HG_counters"] == COUNTERS and job["expected_native_total_arrays"] == 22 and
         job["expected_total_native_count"] == 1040 and job["post_open_frames"] == 1174 and
         job["post_open_drained_particle_checks_expected"] == 11740 and
         Path(job["working_directory"]).resolve() == u.SRC.resolve() and Path(job["output_directory"]).resolve() == OUT.resolve() and
         Path(job["input_prefix"]).resolve() == p.PREFIX.resolve() and
         (job["master"], job["SPR"], job["Visco"], job["eta"], job["HG"], job["SlipMode"]) == (1, 1, .1, .04, .1, 3),
         "Only the exact one larger-step requested-physics CPU1 plan is admitted")
    need(u.same(job["program"], m["program"]) and u.same(job["source_build"], m["source_build"]) and
         (m["program"]["bytes"], m["program"]["sha256"]) ==
         (5125120, "bee3e36348b2146b6532cc2d2edf2717c8f4ff657da75812c0bcd5bc2f6e931e"), "Frozen genuine program/build differs")
    build = u.read(m["source_build"])
    need(build.get("stage") == "upl_spr_av_build_r1" and build.get("passed") is True and
         u.same(build["program"], m["program"]) and build["object_count"] == 86 and build["non_main_object_count"] == 85 and
         len(m["immutable_source_archives"]) == 267 and len(m["isolated_runtime_copies"]) == 4, "Current isolated build/archive closure differs")
    for e in [m["source_input_manifest"], m["program"], *m["files"], *m["immutable_source_archives"], *m["isolated_runtime_copies"]]:
        u.bind(e)
    patch = [e for e in m["immutable_source_archives"] if Path(e["path"]).name == "JSphCpu.cpp"]
    need(len(patch) == 1 and (patch[0]["bytes"], patch[0]["sha256"]) ==
         (267740, "6de7e04477e92ea141224b9df38e0860ae07efdc7b5d512ed30c318e7260236e"), "Reviewed SPR/current-rho AV patch archive differs")
    doc = DOM.parseString(u.bind(job["runtime"]).read_bytes())
    for key, value in (("DtIni", DT), ("DtFixed", DT), ("TimeMax", p.END), ("TimeOut", .001953125),
                       ("SoilHourglassXi", .1), ("SoilBoundaryDerivativeSPR", 1), ("Visco", .1), ("SoilDampingCoef", .04), ("SlipMode", 3)):
        need(float(p.element(doc, key).getAttribute("value")) == value, "Actual candidate XML differs: " + key)
    for key, value in (("HydroMechDynamicSeepage", 1), ("HydroMechConductivityModel", 0), ("HydroMechDrainageFixedGrid", 1),
                       ("HydroMechTopLoadRampTime", p.EVENT_TIME), ("HydroMechDrainageStartTime", p.EVENT_TIME)):
        nodes = doc.getElementsByTagName(key)
        need(len(nodes) == 1 and float(nodes[0].getAttribute("value")) == value, "Actual original physical event/master differs: " + key)
    table, clock = p.schedule(doc)
    need(table == job["saved_clock_table"] and clock == m["clock"] and u.same(job["planned_clock_CSV"], m["planned_clock_CSV"]),
         "Independent scalar replay differs from prepared manifest")
    with u.bind(m["planned_clock_CSV"]).open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        need(reader.fieldnames == p.HEADER and list(reader) == [{k: str(v) for k, v in row.items()} for row in table], "Exact numeric scalar CSV differs")
    return dict(manifest=manifest, job=job, program=m["program"], source_build=m["source_build"], patch_archive=patch[0],
                clock_CSV=m["planned_clock_CSV"], clock=clock)


def actual_identity(psutil, expected, parent=None):
    process = psutil.Process(expected["pid"])
    got = dict(pid=process.pid, created_epoch=process.create_time(), exe=process.exe(), command=process.cmdline(), parent_pid=process.ppid())
    need(process.is_running() and got["created_epoch"] == expected["created_epoch"] and
         Path(got["exe"]).resolve() == Path(expected["exe"]).resolve() and got["command"] == expected["command"] and
         (parent is None or got["parent_pid"] == parent), "Exact retained fine-control process identity changed")
    return got


def fine_control(u, psutil, program):
    size, sha = PINS["logs/upl_spr_av_2tv_CPU1_r1.start.json"]
    receipt = dict(path=str(T / "logs/upl_spr_av_2tv_CPU1_r1.start.json"), bytes=size, sha256=sha)
    s = u.read(receipt)
    need(s.get("stage") == "upl_spr_av_2tv_CPU1_r1.start" and s.get("actual_solver_identity_verified") is True and
         s["owner_pid"] == 68848 and s["solver_pid"] == 37560 and s["solver_parent_pid"] == 68848 and
         u.same(s["program"], program), "Pinned original fine-control start differs")
    u.bind(s["owner_script"])
    owner = actual_identity(psutil, dict(pid=s["owner_pid"], created_epoch=s["owner_created_epoch"],
        exe=s["owner_executable"], command=s["owner_command"]))
    child = actual_identity(psutil, s["solver"], parent=owner["pid"])
    need(child["pid"] == s["solver_pid"] and child["created_epoch"] == s["solver_created_epoch"] and
         child["command"] == s["solver_command"] and Path(child["exe"]).resolve() == Path(s["solver_executable"]).resolve(),
         "Original sealed fine-control nested/flat solver identity differs")
    active = [p.info for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"])
              if (p.info["name"] or "").lower().startswith("dualsphysics") and "cpu" in (p.info["name"] or "").lower()]
    need([v["pid"] for v in active] == [child["pid"]], "Only the exact original fine-control CPU may coexist")
    return dict(start_record=receipt, owner=owner, solver=child, CPU_processes_before=active,
                growing_payload_read_or_hashed=False, process_action_taken=False)


def check_output():
    text = (OUT / "Run.out").read_text(encoding="utf-8-sig")
    need("Finished execution (code=0)." in text and 'RunMode="Stable - Pos-Double - Single core"' in text and
         re.search(r"Steps of simulation[.]+:\s*320000(?:\s|$)", text) and
         re.search(r"Excluded particles[.]+:\s*0(?:\s|$)", text), "Actual normal CPU1 finish/steps/no exclusions differ")
    need(re.search(r"SoilHourglassXi: 0\.1\s", text) and 'SoilBoundaryDerivativeSPR="MirroredWallDerivatives"' in text and
         'SoilDamping="BuiFukagawa2013"' in text, "Actual requested HG/SPR/damping flags differ")
    for key, value in (("Visco", .1), ("ViscoBoundFactor", 1.), ("SoilDampingCoef", .04)):
        r = re.search(r"(?m)^\s*" + key + r"=([-+0-9.eE]+)\s*$", text)
        need(r and float(r[1]) == value, "Actual printed coefficient differs: " + key)
    f = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    r = re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
    need(f and r and tuple(map(int, f.groups())) == (640000, 320000, 320000, 640000) and
         tuple(map(int, r.groups())) == (320001, 319999), "Original logical/actual HG cache counts differ")
    d = re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)", text)
    need(d, "Actual reference-history/current-mi diagnostics missing")
    net, actual, tau, spin = map(float, d.groups())
    need(all(math.isfinite(v) and v >= 0 for v in (net, actual, tau, spin)) and tau <= .2 and spin < .01,
         "Original finite/stiffness/small-spin guards failed")
    need(sorted(p.name for p in (OUT / "data").glob("Part_*.bi4")) == ["Part_%04d.bi4" % i for i in range(N)], "Actual1292 PART filename sequence differs")
    result = dict(steps=STEPS, native_frames=N, native_frame_presence_only=True, HG=dict(counters=COUNTERS,
        max_reference_history_net_force=net, max_actual_float_add_net_force=actual, max_dt_over_tau=tau, spinbound=spin,
        reference_history_is_Q_over_M0=True, actual_inertia_is_current_mi=True))
    for key, label in (("simulation_runtime_seconds_reported", "Simulation Runtime"), ("total_runtime_seconds_reported", "Total Runtime")):
        r = re.search(re.escape(label) + r"[.]+:\s*([0-9.eE+-]+) sec\.", text)
        need(r and math.isfinite(float(r[1])) and float(r[1]) >= 0, "Actual reported runtime missing")
        result[key] = float(r[1])
    return result


def run(u, ctx, result):
    import psutil
    u.adopt(psutil.__file__)
    start, receipt, log = (T / "logs" / (TAG + suffix) for suffix in (".start.json", ".call.json", ".log"))
    u.fresh(OUT, start, receipt, log)
    allowed = fine_control(u, psutil, ctx["program"])
    me = psutil.Process()
    result.update(job=ctx["job"], source_input_manifest=ctx["manifest"], source_build=ctx["source_build"], program=ctx["program"],
        current_patch_archive=ctx["patch_archive"], planned_clock_CSV=ctx["clock_CSV"], clock=ctx["clock"], fine_control=allowed)
    u.final_bindings()
    child, code, failure, stopped = None, None, None, False
    started, wall = u.utc(), time.perf_counter()
    try:
        with log.open("xb") as stream:
            child = subprocess.Popen([ctx["program"]["path"], *ctx["job"]["arguments"]], cwd=u.SRC, stdout=stream,
                stderr=subprocess.STDOUT, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            process = psutil.Process(child.pid)
            solver = dict(pid=process.pid, created_epoch=process.create_time(), exe=process.exe(), command=process.cmdline(), parent_pid=process.ppid())
            need(Path(solver["exe"]).resolve() == Path(ctx["program"]["path"]).resolve() and solver["parent_pid"] == me.pid and
                 solver["command"][1:] == ctx["job"]["arguments"], "Actual owned candidate executable/parent/argv differs")
            u.seal(start, dict(stage=TAG + ".start", utc=u.utc(), owner_pid=me.pid, owner_created_epoch=me.create_time(),
                owner_executable=me.exe(), owner_command=me.cmdline(), working_directory=str(u.SRC), owner_script=u.entry(__file__),
                solver=solver, solver_pid=solver["pid"], solver_created_epoch=solver["created_epoch"], solver_executable=solver["exe"],
                solver_command=solver["command"], solver_parent_pid=solver["parent_pid"], actual_solver_identity_verified=True,
                job=ctx["job"], source_input_manifest=ctx["manifest"], source_build=ctx["source_build"], program=ctx["program"],
                planned_clock_CSV=ctx["clock_CSV"], clock=ctx["clock"], fine_control=allowed, inputs=list(u.BOUND.values()),
                direct_owner_no_scheduler=True, physical_acceptance=False))
            result["start_record"], result["solver"] = u.adopt(start), solver
            code = child.wait()  # Immediately capture original Python integer returncode from the owned wait.
    except Exception as exc:
        failure = str(exc)
        if child is not None:
            if child.poll() is None:
                child.terminate()  # Only this candidate on owner bookkeeping failure; never the fine control or watcher.
                stopped = True
            code = child.wait()
    u.seal(receipt, dict(stage=TAG + ".run_call", program=ctx["program"], target_program=ctx["program"],
        arguments=ctx["job"]["arguments"], target_arguments=ctx["job"]["arguments"], working_directory=str(u.SRC),
        start_record=result.get("start_record"), solver=result.get("solver"), started_utc=started, ended_utc=u.utc(),
        direct_native_call=True, actual_solver_call=True, public_project_main=True, fixture_or_Run_override=False, shell=False,
        typed_returncode_captured_immediately=type(code) is int, owned_call_exited=type(code) is int, exit_code=code,
        invocation_failure=failure, owner_exception_terminated_owned_child=stopped, invocation_wall_seconds=time.perf_counter() - wall,
        log=u.entry(log) if log.exists() else None, physical_acceptance=False))
    result["call"] = u.adopt(receipt)  # Seal actual exit including failure before all output guards and inventory.
    call = u.owned(result["call"], TAG + ".run_call")
    result.update(check_output(), invocation_wall_seconds=call["invocation_wall_seconds"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Explicit invocation of this single bounded candidate required")
    need(all(not path.exists() for path in [OUT, RECORD, *(T / "logs" / (TAG + s) for s in (".start.json", ".call.json", ".log"))]), "Retained candidate protected")
    u = None
    result = dict(stage=TAG + ".run", tag=TAG, passed=False, backend="CPU", configuration="ReleaseCPU", window="candidate2s", threads=1,
        failure=None, public_project_main=True, fixture_or_Run_override=False, native_decoder_invoked=False, physical_acceptance=False,
        all22_native_fields_review_pending=True, actual_scalar_native_clocks_review_pending=True,
        signed_noninitial_dterror_and_candidate_comparison_pending=True, automatic_full_or_next_run=False,
        direct_owner_no_scheduler=True, historical_mutable_source_or_canonical_revalidated=False)
    try:
        u, p = definitions()
        run(u, context(u, p), result)
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        need(u is not None, "Pinned file utilities not initialized")
        result["inputs"] = u.final_bindings()
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = True
    except Exception as exc:
        result["inputs"] = list(u.BOUND.values()) if u else []
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = result["passed"] = False
        result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
    try:
        result["files"] = [u.entry(path) for path in sorted(OUT.rglob("*")) if path.is_file()] if OUT.exists() else []
        result["run_out"] = next((e for e in result["files"] if Path(e["path"]).name == "Run.out"), None)
    except Exception as exc:
        result["passed"], result["payload_inventory_failure"] = False, str(exc)
    result.update(payload_hash_scope="One terminal inventory after actual exit; immutable prerequisites rehashed once at end",
        active_fine_control_payload_read_or_hashed=False, fine_control_or_watcher_modified=False,
        source_project_formal_or_canonical_files_written=False, following_action_launched=False, watcher_or_queue_invoked=False)
    with RECORD.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], job=TAG, receipt=str(RECORD), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
