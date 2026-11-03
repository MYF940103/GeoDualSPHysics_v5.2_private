"""One fresh requested CPU1 full2Tv run; root admission, no decoder or next job."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
NAME, TAG = "upl_spr_av_2tv_run_r1", "upl_spr_av_2tv_CPU1_r1"
STEPS, N, DT = 38212357, 858, 2.0 ** -19
OUT = T / "outputs" / TAG
COUNTERS = dict(forcecalls=2 * STEPS, ratecalls=2 * STEPS, predictorupdates=STEPS,
                correctorupdates=STEPS, ratecalculations=STEPS + 1, ratecachehits=STEPS - 1)
PINS = {"support/upl_spr_av_run_r1.py": (15888, "574c3a4da7ade2c1fda97d93a95c1544d6dc05e6896a5f08594053992d2fb757"),
        "notes/upl_spr_av_run_r1.json": (3340, "42ceee38a1ba1230cb2475eda1d827c30d3c05fe4c7842a0a60b058d7cbadd59"),
        "support/upl_spr_av_full_prepare_r1.py": (13008, "b750d1099e36f015b61d6a94e61684d95396d24a3cd4e79494636c389c5d13c8"),
        "notes/upl_spr_av_full_prepare_r1.json": (4844, "358f1270df5e057a2e771a25c31c48123ccd15c76db8d09836491a3a6075a98d"),
        "logs/upl_spr_av_full_r1.inputs.json": (440609, "f8a96de0c6c1a0990603238acb979e23770270a088553619b291445fa8e20dcb")}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def definitions():
    sys.dont_write_bytecode = True
    path = T / "support/upl_spr_av_run_r1.py"
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    need((path.stat().st_size, digest) == PINS["support/upl_spr_av_run_r1.py"], "Frozen generic short utilities changed")
    spec = importlib.util.spec_from_file_location("spr_av_full_generic_bindings", path)
    u = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(u)  # Only file/exit utilities; never short context/run/check_output/main.
    for name, (size, sha) in PINS.items():
        u.bind(dict(path=str(T / name), bytes=size, sha256=sha))
    for path in (__file__, T / "notes" / (NAME + ".json"), sys.executable):
        u.adopt(path)
    return u


def context(u, admission_path):
    size, sha = PINS["logs/upl_spr_av_full_r1.inputs.json"]
    manifest = dict(path=str(T / "logs/upl_spr_av_full_r1.inputs.json"), bytes=size, sha256=sha)
    m = u.read(manifest)
    need(m.get("stage") == "upl_spr_av_full_prepare_r1" and m.get("passed") is True and m.get("prepared") is True and
         m.get("bindings_unchanged") is True and m.get("independent_final_rehash_performed") is True and
         m.get("physical_acceptance") is False and len(m["jobs"]) == 1, "Actual passed full preparation required")
    job = m["jobs"][0]
    argv = ["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip", job["input_prefix"], str(OUT),
            "-dirdataout", "data", "-svres", "-nsteps:38212357"]
    need(job["tag"] == TAG and job["window"] == "full2Tv" and job["arguments"] == argv and job["threads"] == 1 and
         job["steps"] == STEPS and job["expected_samples"] == N and job["dt_s"] == DT and job["end_s"] == STEPS * DT and
         Path(job["output_directory"]).resolve() == OUT.resolve() and Path(job["working_directory"]).resolve() == u.SRC.resolve() and
         (job["master"], job["SPR"], job["Visco"], job["eta"], job["HG"], job["SlipMode"]) == (1, 1, .1, .04, .1, 3) and
         job["expected_HG_counters"] == COUNTERS and job["expected_native_total_arrays"] == 22 and
         job["expected_total_native_count"] == 1040 and job["post_open_frames"] == 654 and
         job["post_open_drained_particle_checks_expected"] == 6540, "Exact full requested CPU1 job differs")
    table = job["saved_clock_table"]
    steps = [r["completed_steps"] for r in table]
    need(len(table) == N and steps[:458] == u.SAVE and steps[458] == 108638 and steps[-2:] == [38124716, STEPS] and
         all(type(s) is int for s in steps) and all(a < b for a, b in zip(steps, steps[1:])) and
         all((r["part"], r["saved_step"], r["time_s"], r["dt_s"]) == (i, steps[i] - 1 if i else 0, steps[i] * DT, DT)
             for i, r in enumerate(table)) and sum(s > 5243 for s in steps) == 654, "Frozen858 integer/physical clock table differs")
    need(u.same(m["program"], job["program"]) and u.same(m["source_build"], job["source_build"]), "Full own program/build differs")
    build = u.read(m["source_build"])
    need(build.get("stage") == "upl_spr_av_build_r1" and build.get("passed") is True and
         u.same(build["program"], m["program"]) and build["object_count"] == 86 and build["non_main_object_count"] == 85,
         "Genuine new isolated ReleaseCPU project-main build required")
    patch = next(p["snapshot"] for p in build["source_snapshot"] if Path(p["snapshot"]["path"]).name == "JSphCpu.cpp")
    need((patch["bytes"], patch["sha256"]) == (267740, "6de7e04477e92ea141224b9df38e0860ae07efdc7b5d512ed30c318e7260236e"), "Reviewed patch archive differs")
    for e in [m["program"], patch, *m["files"], *(p["copy"] for p in build["runtime"])]:
        u.bind(e)
    xml = ET.parse(u.bind(job["runtime"])).getroot()
    for key, value in (("DtIni", DT), ("DtFixed", DT), ("TimeMax", STEPS * DT), ("TimeOut", .18218571428571428),
                       ("SoilHourglassXi", .1), ("SoilBoundaryDerivativeSPR", 1), ("Visco", .1), ("SoilDampingCoef", .04), ("SlipMode", 3)):
        nodes = xml.findall("./execution/parameters/parameter[@key='" + key + "']")
        need(len(nodes) == 1 and float(nodes[0].get("value")) == value, "Actual full XML differs: " + key)
    masters = list(xml.iter("HydroMechDynamicSeepage"))
    need(len(masters) == 1 and masters[0].get("value") == "1", "Actual full public master differs")
    admission = u.adopt(admission_path)
    a = u.read(admission)
    need(a.get("stage") == "upl_spr_av_full_admission_r1" and a.get("passed") is True and a.get("allowed_jobs") == [TAG] and
         a.get("physical_acceptance") is False and a.get("inputs"), "Separate root full launch admission required")
    for e in (manifest, m["program"], m["source_build"]):
        need(any(u.same(e, v) for v in a["inputs"]), "Root admission missing actual manifest/program/build")
    for e in a["inputs"]:
        u.bind(e)  # Root owns completed short/native/equivalence interpretation, without another half staircase.
    return dict(manifest=manifest, job=job, program=m["program"], source_build=m["source_build"], admission=admission, patch_archive=patch)


def check_output(job):
    text = (OUT / "Run.out").read_text(encoding="utf-8-sig")
    need("Finished execution (code=0)." in text and 'RunMode="Stable - Pos-Double - Single core"' in text and
         re.search(r"Steps of simulation[.]+:\s*38212357(?:\s|$)", text) and
         re.search(r"Excluded particles[.]+:\s*0(?:\s|$)", text), "Full actual finish/step/no-loss guards failed")
    need(re.search(r"SoilHourglassXi: 0\.1\s", text) and 'SoilBoundaryDerivativeSPR="MirroredWallDerivatives"' in text and
         'SoilDamping="BuiFukagawa2013"' in text, "Full requested HG/SPR/damping flags differ")
    for key, value in (("Visco", .1), ("ViscoBoundFactor", 1.), ("SoilDampingCoef", .04)):
        r = re.search(r"(?m)^\s*" + key + r"=([-+0-9.eE]+)\s*$", text)
        need(r and float(r[1]) == value, "Full printed coefficient differs: " + key)
    f = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    r = re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
    need(f and r and tuple(map(int, f.groups())) == (2 * STEPS, STEPS, STEPS, 2 * STEPS) and
         tuple(map(int, r.groups())) == (STEPS + 1, STEPS - 1), "Original full HG logical/actual cache counts differ")
    d = re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)", text)
    need(d, "Actual full reference-history/current-mi diagnostics missing")
    net, actual, tau, spin = map(float, d.groups())
    need(all(math.isfinite(v) and v >= 0 for v in (net, actual, tau, spin)) and tau <= .2 and spin < .01,
         "Original finite/stiffness/small-spin guards failed")
    need(sorted(p.name for p in (OUT / "data").glob("Part_*.bi4")) == ["Part_%04d.bi4" % i for i in range(N)], "858 actual PART filenames required")
    result = dict(steps=STEPS, native_frames=N, native_frame_presence_only=True, HG=dict(counters=COUNTERS,
        max_reference_history_net_force=net, max_actual_float_add_net_force=actual, max_dt_over_tau=tau, spinbound=spin,
        reference_history_is_Q_over_M0=True, actual_inertia_is_current_mi=True))
    for key, label in (("simulation_runtime_seconds_reported", "Simulation Runtime"), ("total_runtime_seconds_reported", "Total Runtime")):
        r = re.search(re.escape(label) + r"[.]+:\s*([0-9.eE+-]+) sec\.", text)
        need(r and math.isfinite(float(r[1])) and float(r[1]) >= 0, "Full actual reported runtime missing")
        result[key] = float(r[1])
    return result


def run(u, ctx, result):
    import psutil
    u.adopt(psutil.__file__)
    start, receipt, log = (T / "logs" / (TAG + suffix) for suffix in (".start.json", ".call.json", ".log"))
    u.fresh(OUT, start, receipt, log)
    active = [p.info for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"])
              if (p.info["name"] or "").lower().startswith("dualsphysics") and "cpu" in (p.info["name"] or "").lower()]
    need(not active, "Another actual CPU solver is active")
    me = psutil.Process()
    result.update(job=ctx["job"], source_input_manifest=ctx["manifest"], source_build=ctx["source_build"], program=ctx["program"],
                  admission=ctx["admission"], current_patch_archive=ctx["patch_archive"], CPU_processes_before=active)
    u.final_bindings()
    child = None
    code = failure = None
    stopped = False
    started, wall = u.utc(), time.perf_counter()
    try:
        with log.open("xb") as stream:
            child = subprocess.Popen([ctx["program"]["path"], *ctx["job"]["arguments"]], cwd=u.SRC, stdout=stream,
                stderr=subprocess.STDOUT, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            actual = psutil.Process(child.pid)
            solver = dict(pid=actual.pid, created_epoch=actual.create_time(), exe=actual.exe(), command=actual.cmdline(), parent_pid=actual.ppid())
            need(Path(solver["exe"]).resolve() == Path(ctx["program"]["path"]).resolve() and solver["parent_pid"] == me.pid and
                 solver["command"][1:] == ctx["job"]["arguments"], "Actual owned solver executable/parent/argv differs")
            u.seal(start, dict(stage=TAG + ".start", utc=u.utc(), owner_pid=me.pid, owner_created_epoch=me.create_time(),
                owner_executable=me.exe(), owner_command=me.cmdline(), working_directory=str(u.SRC), owner_script=u.entry(__file__),
                solver=solver, solver_pid=solver["pid"], solver_created_epoch=solver["created_epoch"], solver_executable=solver["exe"],
                solver_command=solver["command"], solver_parent_pid=solver["parent_pid"], actual_solver_identity_verified=True,
                job=ctx["job"], source_input_manifest=ctx["manifest"], source_build=ctx["source_build"], program=ctx["program"],
                admission=ctx["admission"], inputs=list(u.BOUND.values()), direct_owner_no_scheduler=True, physical_acceptance=False))
            result["start_record"] = u.adopt(start)  # Actual child creation identity is sealed before the long wait.
            result["solver"] = solver
            code = child.wait()  # First operation when native wait returns: capture original integer returncode.
    except Exception as exc:
        failure = str(exc)
        if child is not None:
            if child.poll() is None:
                child.terminate()  # Only this owned child, on owner bookkeeping failure; never leave an unrecorded long run.
                stopped = True
            code = child.wait()
    u.seal(receipt, dict(stage=TAG + ".run_call", program=ctx["program"], target_program=ctx["program"],
        arguments=ctx["job"]["arguments"], target_arguments=ctx["job"]["arguments"], working_directory=str(u.SRC),
        start_record=result.get("start_record"), solver=result.get("solver"), started_utc=started, ended_utc=u.utc(),
        direct_native_call=True, actual_solver_call=True, public_project_main=True, fixture_or_Run_override=False, shell=False,
        typed_returncode_captured_immediately=type(code) is int, owned_call_exited=type(code) is int, exit_code=code,
        invocation_failure=failure, owner_exception_terminated_owned_child=stopped, invocation_wall_seconds=time.perf_counter() - wall,
        log=u.entry(log) if log.exists() else None, physical_acceptance=False))
    result["call"] = u.adopt(receipt)
    c = u.owned(result["call"], TAG + ".run_call")  # Exit is sealed before output reads/hashes, including intentional stop/nonzero.
    result.update(check_output(ctx["job"]), invocation_wall_seconds=c["invocation_wall_seconds"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Explicit authorization of this one root-admitted full job required")
    record = T / "logs" / (TAG + ".run.json")
    need(all(not p.exists() for p in [OUT, record, *(T / "logs" / (TAG + s) for s in (".start.json", ".call.json", ".log"))]), "Retained full job protected")
    u = None
    result = dict(stage=TAG + ".run", tag=TAG, passed=False, backend="CPU", configuration="ReleaseCPU", window="full2Tv", threads=1,
        failure=None, public_project_main=True, fixture_or_Run_override=False, native_decoder_invoked=False,
        automatic_follow_up=False, direct_owner_no_scheduler=True, all22_native_fields_review_pending=True,
        actual_native_clocks_review_pending=True, measured458_prefix_review_pending=True, physical_acceptance=False,
        other_full_half_or_mid_admitted=False, historical_mutable_source_or_canonical_revalidated=False)
    try:
        u = definitions()
        run(u, context(u, args.admission), result)
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        need(u is not None, "Pinned generic utilities not initialized")
        result["inputs"] = u.final_bindings()
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = True
    except Exception as exc:
        result["inputs"] = list(u.BOUND.values()) if u else []
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = result["passed"] = False
        result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
    try:
        result["files"] = [u.entry(p) for p in sorted(OUT.rglob("*")) if p.is_file()] if OUT.exists() else []
        result["run_out"] = next((e for e in result["files"] if Path(e["path"]).name == "Run.out"), None)
    except Exception as exc:
        result["passed"] = False
        result["payload_inventory_failure"] = str(exc)
    result.update(payload_hash_scope="One terminal inventory after actual exit; prerequisite rehash excludes historical mutable originals",
                  source_project_formal_or_canonical_files_written=False, following_action_launched=False, watcher_or_queue_invoked=False)
    with record.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], job=TAG, receipt=str(record), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
