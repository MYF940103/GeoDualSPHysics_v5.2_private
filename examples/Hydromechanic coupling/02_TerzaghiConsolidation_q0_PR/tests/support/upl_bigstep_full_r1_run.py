"""Own one root-admitted larger-step full2Tv run; no decoder or next action."""
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
NAME, TAG = "upl_bigstep_full_r1_run", "upl_bigstep_2tv_CPU1_r1"
STEPS, N, DT, END, POST = 11661219, 1682, float("6.2501430511474609e-6"), 72.88428689946836, 1564
OUT, RECORD = T / "outputs" / TAG, T / "logs" / (TAG + ".run.json")
COUNTERS = dict(forcecalls=23322438, ratecalls=23322438, predictorupdates=11661219,
                correctorupdates=11661219, ratecalculations=11661220, ratecachehits=11661218)
PINS = {
    "support/upl_bigstep_full_r1_prepare.py": (14548, "0223aa1782b1391c53a47ae77da02c448b90730d0e044897dfa40e87b7f3a305"),
    "notes/upl_bigstep_full_r1_prepare.json": (4935, "7c691ce7e5629e18b200209a3efbe07839ce8c6264ac9874f556d6279110e134"),
}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def definitions():
    sys.dont_write_bytecode = True
    path = T / "support/upl_bigstep_full_r1_prepare.py"
    data = path.read_bytes()
    need((len(data), hashlib.sha256(data).hexdigest()) == PINS["support/upl_bigstep_full_r1_prepare.py"], "Frozen full input definitions changed")
    spec = importlib.util.spec_from_file_location("bigstep_full_frozen_prepare_definitions", path)
    f = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(f)  # Only definitions/proofs/scalar replay; never preparation/main or an old run/context.
    u, p = f.definitions()
    for name, (size, sha) in PINS.items():
        u.bind(dict(path=str(T / name), bytes=size, sha256=sha))
    for path in (__file__, T / "notes" / (NAME + ".json"), sys.executable):
        u.adopt(path)
    return u, f, p


def context(u, f, p, admission_path):
    manifest = u.adopt(T / "logs/upl_bigstep_full_r1.inputs.json")
    m = u.read(manifest)
    need(m.get("stage") == "upl_bigstep_full_r1_prepare" and m.get("passed") is True and m.get("prepared") is True and
         m.get("bindings_unchanged") is True and m.get("independent_final_rehash_performed") is True and
         m.get("physical_acceptance") is False and m.get("full_run_admitted") is False and len(m["jobs"]) == 1,
         "Actual passed separate full preparation required")
    candidate, source_manifest, proofs = f.candidate_proofs(u)
    need(all(u.same(m["candidate_proofs"][key], value) for key, value in proofs.items()) and
         u.same(m["source_input_manifest"], source_manifest) and m["source_job"] == candidate["jobs"][0], "Actual candidate preparation/proof chain differs")
    job = m["jobs"][0]
    argv = ["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip", str(f.PREFIX), str(OUT),
            "-dirdataout", "data", "-svres", "-nsteps:11661219"]
    need(job["tag"] == TAG and job["window"] == "candidate_full2Tv" and job["arguments"] == argv and job["threads"] == 1 and
         job["steps"] == STEPS and job["expected_samples"] == N and job["dt_s"] == DT and job["end_s"] == END and
         job["nominal_2Tv_target_s"] == 51019 / 700 and job["runtime_TimeMax_s"] == job["nominal_end_s"] == float(f.MAX_TEXT) and
         job["event_completed_step"] == 1600 and job["event_time_s"] == p.EVENT_TIME and job["expected_HG_counters"] == COUNTERS and
         job["expected_native_total_arrays"] == 22 and job["expected_total_native_count"] == 1040 and
         job["post_open_frames"] == POST and job["post_open_drained_particle_checks_expected"] == 10 * POST and
         Path(job["working_directory"]).resolve() == u.SRC.resolve() and Path(job["output_directory"]).resolve() == OUT.resolve() and
         Path(job["input_prefix"]).resolve() == f.PREFIX.resolve() and
         (job["master"], job["SPR"], job["Visco"], job["eta"], job["HG"], job["SlipMode"]) == (1, 1, .1, .04, .1, 3), "Exact one full requested-physics CPU1 job differs")
    need(u.same(job["program"], m["program"]) and u.same(job["source_build"], m["source_build"]) and
         u.same(m["program"], candidate["program"]) and u.same(m["source_build"], candidate["source_build"]) and
         (m["program"]["bytes"], m["program"]["sha256"]) ==
         (5125120, "bee3e36348b2146b6532cc2d2edf2717c8f4ff657da75812c0bcd5bc2f6e931e"), "Frozen current full program/build differs")
    build = u.read(m["source_build"])
    need(build.get("stage") == "upl_spr_av_build_r1" and build.get("passed") is True and u.same(build["program"], m["program"]) and
         build["object_count"] == 86 and build["non_main_object_count"] == 85 and len(m["immutable_source_archives"]) == 267 and
         len(m["isolated_runtime_copies"]) == 4, "Genuine current source/object/runtime archive closure differs")
    for e in [m["program"], m["prepare_admission"], *m["files"], *m["immutable_source_archives"], *m["isolated_runtime_copies"]]:
        u.bind(e)
    patch = [e for e in m["immutable_source_archives"] if Path(e["path"]).name == "JSphCpu.cpp"]
    need(len(patch) == 1 and (patch[0]["bytes"], patch[0]["sha256"]) ==
         (267740, "6de7e04477e92ea141224b9df38e0860ae07efdc7b5d512ed30c318e7260236e"), "Reviewed SPR/current-rho AV patch archive differs")
    doc = DOM.parseString(u.bind(job["runtime"]).read_bytes())
    for key, value in (("DtIni", DT), ("DtFixed", DT), ("TimeMax", float(f.MAX_TEXT)), ("TimeOut", float(f.INTERVAL_TEXT)),
                       ("SoilHourglassXi", .1), ("SoilBoundaryDerivativeSPR", 1), ("Visco", .1), ("SoilDampingCoef", .04), ("SlipMode", 3)):
        need(float(p.element(doc, key).getAttribute("value")) == value, "Actual full XML differs: " + key)
    for key, value in (("HydroMechDynamicSeepage", 1), ("HydroMechConductivityModel", 0), ("HydroMechDrainageFixedGrid", 1),
                       ("HydroMechTopLoadRampTime", p.EVENT_TIME), ("HydroMechDrainageStartTime", p.EVENT_TIME)):
        nodes = doc.getElementsByTagName(key)
        need(len(nodes) == 1 and float(nodes[0].getAttribute("value")) == value, "Actual original event/master differs: " + key)
    table, clock = f.schedule(p, doc)
    need(table == job["saved_clock_table"] and clock == m["clock"] and u.same(job["planned_clock_CSV"], m["planned_clock_CSV"]) and
         table[:1291] == candidate["jobs"][0]["saved_clock_table"][:1291], "Independent full scalar/common-prefix table differs")
    with u.bind(m["planned_clock_CSV"]).open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        need(reader.fieldnames == p.HEADER and list(reader) == [{k: str(v) for k, v in row.items()} for row in table], "Exact full scalar CSV differs")
    gate = f.admission(u, admission_path, "upl_bigstep_full_run_admission_r1",
        [manifest, m["program"], m["source_build"], m["prepare_admission"], *proofs.values()], "allowed_jobs", [TAG])
    return dict(manifest=manifest, job=job, program=m["program"], source_build=m["source_build"], admission=gate,
                patch_archive=patch[0], clock_CSV=m["planned_clock_CSV"], clock=clock, candidate_proofs=proofs)


def check_output():
    text = (OUT / "Run.out").read_text(encoding="utf-8-sig")
    need("Finished execution (code=0)." in text and 'RunMode="Stable - Pos-Double - Single core"' in text and
         re.search(r"Steps of simulation[.]+:\s*11661219(?:\s|$)", text) and
         re.search(r"Excluded particles[.]+:\s*0(?:\s|$)", text), "Actual full normal CPU1 finish/steps/no exclusions differ")
    need(re.search(r"SoilHourglassXi: 0\.1\s", text) and 'SoilBoundaryDerivativeSPR="MirroredWallDerivatives"' in text and
         'SoilDamping="BuiFukagawa2013"' in text, "Actual requested HG/SPR/damping flags differ")
    for key, value in (("Visco", .1), ("ViscoBoundFactor", 1.), ("SoilDampingCoef", .04)):
        r = re.search(r"(?m)^\s*" + key + r"=([-+0-9.eE]+)\s*$", text)
        need(r and float(r[1]) == value, "Actual printed coefficient differs: " + key)
    f = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    r = re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
    need(f and r and tuple(map(int, f.groups())) == (23322438, 11661219, 11661219, 23322438) and
         tuple(map(int, r.groups())) == (11661220, 11661218), "Original full HG logical/actual cache counters differ")
    d = re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)", text)
    need(d, "Actual reference-history/current-mi diagnostics missing")
    net, actual, tau, spin = map(float, d.groups())
    need(all(math.isfinite(v) and v >= 0 for v in (net, actual, tau, spin)) and tau <= .2 and spin < .01, "Original finite/stiffness/spin guards failed")
    need(sorted(p.name for p in (OUT / "data").glob("Part_*.bi4")) == ["Part_%04d.bi4" % i for i in range(N)], "Actual1682 PART sequence differs")
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
    active = [p.info for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"])
              if (p.info["name"] or "").lower().startswith("dualsphysics") and "cpu" in (p.info["name"] or "").lower()]
    need(not active, "Another actual CPU solver is active; no old fine/control liveness exception")
    me = psutil.Process()
    result.update(job=ctx["job"], source_input_manifest=ctx["manifest"], source_build=ctx["source_build"], program=ctx["program"],
        admission=ctx["admission"], candidate_proofs=ctx["candidate_proofs"], current_patch_archive=ctx["patch_archive"],
        planned_clock_CSV=ctx["clock_CSV"], clock=ctx["clock"], CPU_processes_before=active)
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
                 solver["command"][1:] == ctx["job"]["arguments"], "Actual owned full solver executable/parent/argv differs")
            u.seal(start, dict(stage=TAG + ".start", utc=u.utc(), owner_pid=me.pid, owner_created_epoch=me.create_time(),
                owner_executable=me.exe(), owner_command=me.cmdline(), working_directory=str(u.SRC), owner_script=u.entry(__file__),
                solver=solver, solver_pid=solver["pid"], solver_created_epoch=solver["created_epoch"], solver_executable=solver["exe"],
                solver_command=solver["command"], solver_parent_pid=solver["parent_pid"], actual_solver_identity_verified=True,
                job=ctx["job"], source_input_manifest=ctx["manifest"], source_build=ctx["source_build"], program=ctx["program"],
                admission=ctx["admission"], candidate_proofs=ctx["candidate_proofs"], planned_clock_CSV=ctx["clock_CSV"], clock=ctx["clock"],
                inputs=list(u.BOUND.values()), direct_owner_no_scheduler=True, physical_acceptance=False))
            result["start_record"], result["solver"] = u.adopt(start), solver
            code = child.wait()  # First operation on wait return: capture the original native integer exit.
    except Exception as exc:
        failure = str(exc)
        if child is not None:
            if child.poll() is None:
                child.terminate()  # Only this owned child on bookkeeping failure; never another process.
                stopped = True
            code = child.wait()
    u.seal(receipt, dict(stage=TAG + ".run_call", program=ctx["program"], target_program=ctx["program"],
        arguments=ctx["job"]["arguments"], target_arguments=ctx["job"]["arguments"], working_directory=str(u.SRC),
        start_record=result.get("start_record"), solver=result.get("solver"), started_utc=started, ended_utc=u.utc(),
        direct_native_call=True, actual_solver_call=True, public_project_main=True, fixture_or_Run_override=False, shell=False,
        typed_returncode_captured_immediately=type(code) is int, owned_call_exited=type(code) is int, exit_code=code,
        invocation_failure=failure, owner_exception_terminated_owned_child=stopped, invocation_wall_seconds=time.perf_counter() - wall,
        log=u.entry(log) if log.exists() else None, physical_acceptance=False))
    result["call"] = u.adopt(receipt)  # Real exit is sealed before output guards/hashes, including intentional failure.
    call = u.owned(result["call"], TAG + ".run_call")
    result.update(check_output(), invocation_wall_seconds=call["invocation_wall_seconds"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Explicit invocation of this one root-admitted full run required")
    need(all(not path.exists() for path in [OUT, RECORD, *(T / "logs" / (TAG + s) for s in (".start.json", ".call.json", ".log"))]), "Retained full run protected")
    u = None
    result = dict(stage=TAG + ".run", tag=TAG, passed=False, backend="CPU", configuration="ReleaseCPU", window="candidate_full2Tv", threads=1,
        failure=None, public_project_main=True, fixture_or_Run_override=False, native_decoder_invoked=False, physical_acceptance=False,
        all22_native_fields_review_pending=True, actual_scalar_native_clocks_review_pending=True, measured_common1291_prefix_review_pending=True,
        signed_noninitial_dterror_and_full_physical_review_pending=True, automatic_follow_up=False, direct_owner_no_scheduler=True,
        historical_mutable_source_or_canonical_revalidated=False, old_fine_or_control_liveness_required=False)
    try:
        u, f, p = definitions()
        run(u, context(u, f, p, args.admission), result)
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        need(u is not None, "Pinned pure utilities not initialized")
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
        source_project_formal_or_canonical_files_written=False, following_action_launched=False, watcher_or_queue_invoked=False)
    with RECORD.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], job=TAG, receipt=str(RECORD), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
