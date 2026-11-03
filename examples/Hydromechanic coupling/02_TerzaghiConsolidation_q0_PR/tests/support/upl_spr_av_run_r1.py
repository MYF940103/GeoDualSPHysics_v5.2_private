"""One explicitly selected prepared CPU1 short job; never decode or chain work."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
SRC = T.parents[3] / "src"
NAME = "upl_spr_av_run_r1"
TAGS = ("upl_spr_av_old_OFF_r1", "upl_spr_av_new_OFF_r1", "upl_spr_av_new_ON0_r1",
        "upl_spr_av_new_ONSPR_r1", "upl_spr_av_new_requested_ON_r1")
N, DT, STEPS, EVENT = 458, 2.0 ** -19, 13120, 5243
SAVE = sorted(set(range(0, STEPS + 1, 64)) | set(range(5120, 5377)))
COUNTERS = dict(forcecalls=26240, ratecalls=26240, predictorupdates=13120,
                correctorupdates=13120, ratecalculations=13121, ratecachehits=13119)
PINS = {"logs/upl_spr_av_r1.inputs.json": (823007, "8ed0f935b0f7d602f6ee381d639fe9077ee173602b7c2878527828e12d5daa8b"),
        "logs/upl_spr_av_pair_cpu_r1.run.json": (2693, "d6f714fe283d30327769046caed0fd8eb740eb2fcfe0e21d003adaee14c70693")}
BOUND = {}


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


def same(a, b):
    return (str(Path(a["path"]).resolve()).casefold(), a["bytes"], a["sha256"].lower()) == (
        str(Path(b["path"]).resolve()).casefold(), b["bytes"], b["sha256"].lower())


def bind(expected):
    key = str(Path(expected["path"]).resolve()).casefold()
    if key not in BOUND:
        BOUND[key] = entry(expected["path"])
    need(same(BOUND[key], expected), "Changed consumed artifact: " + expected["path"])
    return Path(BOUND[key]["path"])


def adopt(path):
    value = entry(path)
    bind(value)
    return value


def read(expected):
    return json.loads(bind(expected).read_text(encoding="utf-8-sig"))


def pin(name):
    size, digest = PINS[name]
    value = dict(path=str(T / name), bytes=size, sha256=digest)
    bind(value)
    return value


def fresh(*paths):
    need(all(not Path(p).exists() for p in paths), "Retained job/output/log/call/receipt protected")


def seal(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def final_bindings():
    for value in list(BOUND.values()):
        need(same(entry(value["path"]), value), "Consumed artifact changed during this action")
    return list(BOUND.values())


def owned(expected, stage):
    c = read(expected)
    need(c.get("stage") == stage and c.get("direct_native_call") is True and c.get("owned_call_exited") is True and
         c.get("typed_returncode_captured_immediately") is True and type(c.get("exit_code")) is int and
         c["exit_code"] == 0 and c.get("invocation_failure") is None, "Original immediate Python native exit0 required")
    bind(c["program"])
    bind(c["log"])
    if "target_program" in c:
        need(same(c["program"], c["target_program"]) and c["arguments"] == c["target_arguments"], "Original native target differs")
    return c


def context(tag):
    need(tag in TAGS, "Only one of the five prepared short jobs is allowed")
    manifest = pin("logs/upl_spr_av_r1.inputs.json")
    m = read(manifest)
    need(m.get("stage") == "upl_spr_av_prepare_r1" and m.get("passed") is True and m.get("prepared") is True and
         m.get("bindings_unchanged") is True and m.get("independent_final_rehash_performed") is True and
         m.get("physical_acceptance") is False and [j["tag"] for j in m["jobs"]] == list(TAGS), "Frozen passed preparation required")
    job = next(j for j in m["jobs"] if j["tag"] == tag)
    directory = T / "outputs" / tag
    want = ["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip", job["input_prefix"], str(directory),
            "-dirdataout", "data", "-svres", "-nsteps:13120"]
    need(job["arguments"] == want and Path(job["output_directory"]).resolve() == directory.resolve() and
         Path(job["working_directory"]).resolve() == SRC.resolve() and job["steps"] == STEPS and job["dt_s"] == DT and
         job["end_s"] == STEPS * DT and job["expected_samples"] == N and job["threads"] == 1 and
         job["event_completed_step"] == EVENT and job["expected_HG_counters"] == COUNTERS and
         [(v["part"], v["completed_steps"], v["saved_step"]) for v in job["saved_clock_table"]] ==
         [(i, s, s - 1 if s else 0) for i, s in enumerate(SAVE)], "Fixed CPU1 integer short plan differs")
    role = "old" if tag == TAGS[0] else "new"
    need(same(job["program"], m["programs"][role]), "Selected prepared program differs")
    build = read(job["source_build"])
    need(build.get("passed") and same(build["program"], job["program"]) and build["object_count"] == 86 and
         build["non_main_object_count"] == 85, "Selected immutable project-main build differs")
    for value in [job["program"], job["configuration_file"], job["runtime"], job["initial_BI4"], job["normals"],
                  *m["isolated_runtime_copies"][role]]:
        bind(value)
    need(len(m["isolated_runtime_copies"][role]) == 4 and Path(job["runtime"]["path"]).resolve() ==
         Path(job["input_prefix"] + ".xml").resolve(), "Own isolated runtime/prefix required")
    new = read(m["new_source_build"])
    patches = [e for e in m["immutable_source_archives"]["new"] if Path(e["path"]).name == "JSphCpu.cpp"]
    need(len(patches) == 1 and (patches[0]["bytes"], patches[0]["sha256"]) ==
         (267740, "6de7e04477e92ea141224b9df38e0860ae07efdc7b5d512ed30c318e7260236e") and
         new.get("passed") and new.get("stage") == "upl_spr_av_build_r1", "Reviewed current patch archive required")
    bind(patches[0])  # Historical/current source identity comes from archives, never mutable live files.
    component = pin("logs/upl_spr_av_pair_cpu_r1.run.json")
    cr = read(component)
    cb = read(cr["source_build"])
    cc = owned(cr["original_call"], "upl_spr_av_pair_cpu_r1.call")
    done = read(cr["completion"])
    need(cr.get("stage") == "upl_spr_av_pair_cpu_r1.run" and cr.get("passed") is True and cb.get("passed") is True and
         same(cb["source_build"], m["new_source_build"]) and same(cb["program"], cc["program"]) and
         done == cr["component_summary"] and done.get("passed") is True and done["trials"] == 31 and
         done["actual_interaction_calls"] == 248 and done["csv_rows"] == 40 and done["exact_zero_controls"] is True and
         done["physical_acceptance"] is False, "Root-owned completed31/248/40 component prerequisite required")
    for value in cr["files"]:
        bind(value)
    xml = ET.parse(bind(job["runtime"])).getroot()
    for key, value in (("SoilBoundaryDerivativeSPR", job["SPR"]), ("Visco", job["Visco"]), ("SoilDampingCoef", job["eta"]),
                       ("SoilHourglassXi", .1), ("SlipMode", 3), ("DtIni", DT), ("DtFixed", DT), ("TimeMax", .5)):
        nodes = xml.findall("./execution/parameters/parameter[@key='" + key + "']")
        need(len(nodes) == 1 and float(nodes[0].get("value")) == value, "Actual prepared XML differs: " + key)
    masters = list(xml.iter("HydroMechDynamicSeepage"))
    need(len(masters) == 1 and int(masters[0].get("value")) == job["master"], "Actual public master differs")
    for path in (__file__, T / "notes" / (NAME + ".json"), sys.executable):
        adopt(path)
    return dict(manifest=manifest, job=job, program=job["program"], source_build=job["source_build"],
                component=component, current_patch_archive=patches[0])


def check_output(job, directory):
    directory = Path(directory)
    text = (directory / "Run.out").read_text(encoding="utf-8-sig")
    need("Finished execution (code=0)." in text and 'RunMode="Stable - Pos-Double - Single core"' in text and
         re.search(r"Steps of simulation[.]+:\s*13120(?:\s|$)", text) and
         re.search(r"Excluded particles[.]+:\s*0(?:\s|$)", text), "Actual normal CPU1 finish/steps/no exclusions differ")
    need(re.search(r"SoilHourglassXi: 0\.1\s", text) and 'SoilDamping="BuiFukagawa2013"' in text and
         ('SoilBoundaryDerivativeSPR="' + ("MirroredWallDerivatives" if job["SPR"] else "None") + '"') in text,
         "Actual HG/damping/SPR settings differ")
    for key, value in (("Visco", job["Visco"]), ("ViscoBoundFactor", 1.), ("SoilDampingCoef", job["eta"])):
        match = re.search(r"(?m)^\s*" + key + r"=([-+0-9.eE]+)\s*$", text)
        need(match and float(match[1]) == value, "Actual printed coefficient differs: " + key)
    f = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    r = re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
    need(f and r and tuple(map(int, f.groups())) == (26240, 13120, 13120, 26240) and
         tuple(map(int, r.groups())) == (13121, 13119), "Original logical/actual HG cache counts differ")
    labels = ("M0*Href", "mi*deltaAce") if job["master"] else ("m*H", "m*deltaAce")
    pattern = r"SoilHourglass: max\|sum\(" + re.escape(labels[0]) + r"\)\|=([^ ]+) max\|sum\(" + re.escape(labels[1]) + r"\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)"
    match = re.search(pattern, text)
    need(match, "Actual HG force-weight diagnostics missing")
    net, actual, tau, spin = map(float, match.groups())
    need(all(math.isfinite(v) and v >= 0 for v in (net, actual, tau, spin)) and tau <= .2 and spin < .01,
         "Original finite/stiffness/spin guards failed")
    need(sorted(p.name for p in (directory / "data").glob("Part_*.bi4")) == ["Part_%04d.bi4" % i for i in range(N)],
         "Actual458 PART filename sequence differs")
    result = dict(steps=STEPS, native_frames=N, native_frame_presence_only=True, HG=dict(counters=COUNTERS,
        max_history_net_force=net, max_actual_float_add_net_force=actual, max_dt_over_tau=tau, spinbound=spin,
        reference_history_is_Q_over_M0=bool(job["master"]), actual_inertia_is_current_mi=bool(job["master"])))
    if job["master"]:
        result["HG"]["max_reference_history_net_force"] = net
    for key, label in (("simulation_runtime_seconds_reported", "Simulation Runtime"), ("total_runtime_seconds_reported", "Total Runtime")):
        match = re.search(re.escape(label) + r"[.]+:\s*([0-9.eE+-]+) sec\.", text)
        need(match and math.isfinite(float(match[1])) and float(match[1]) >= 0, "Actual reported runtime missing")
        result[key] = float(match[1])
    return result


def run(ctx, result):
    job, program = ctx["job"], ctx["program"]
    tag, directory = job["tag"], Path(job["output_directory"])
    start, receipt, log = (T / "logs" / (tag + suffix) for suffix in (".start.json", ".call.json", ".log"))
    fresh(directory, start, receipt, log)
    import psutil
    adopt(psutil.__file__)
    active = [p.info for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"])
              if (p.info["name"] or "").lower().startswith("dualsphysics") and "cpu" in (p.info["name"] or "").lower()]
    need(not active, "Another actual CPU solver is active")
    me = psutil.Process()
    seal(start, dict(stage=tag + ".start", utc=utc(), owner_pid=me.pid, owner_created_epoch=me.create_time(),
        owner_executable=me.exe(), owner_command=me.cmdline(), working_directory=str(SRC), owner_script=entry(__file__),
        job=job, source_input_manifest=ctx["manifest"], source_build=ctx["source_build"], program=program,
        component=ctx["component"], direct_owner_no_scheduler=True, physical_acceptance=False))
    result.update(job=job, source_input_manifest=ctx["manifest"], source_build=ctx["source_build"], program=program,
                  component=ctx["component"], current_patch_archive=ctx["current_patch_archive"], start_record=adopt(start), CPU_processes_before=active)
    final_bindings()
    code = failure = None
    started, wall = utc(), time.perf_counter()
    try:
        with log.open("xb") as stream:
            completed = subprocess.run([program["path"], *job["arguments"]], cwd=SRC, stdout=stream, stderr=subprocess.STDOUT,
                                       shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            code = completed.returncode  # First operation after the owned direct call returns.
    except Exception as exc:
        failure = str(exc)
    seal(receipt, dict(stage=tag + ".run_call", program=program, target_program=program, arguments=job["arguments"],
        target_arguments=job["arguments"], working_directory=str(SRC), start_record=result["start_record"], started_utc=started,
        ended_utc=utc(), direct_native_call=True, actual_solver_call=True, public_project_main=True, fixture_or_Run_override=False,
        shell=False, typed_returncode_captured_immediately=type(code) is int, owned_call_exited=type(code) is int,
        exit_code=code, invocation_failure=failure, invocation_wall_seconds=time.perf_counter() - wall,
        log=entry(log) if log.exists() else None, physical_acceptance=False))
    result["call"] = adopt(receipt)  # Original exit is sealed before opening Run.out or enumerating payload.
    c = owned(result["call"], tag + ".run_call")
    result.update(check_output(job, directory), invocation_wall_seconds=c["invocation_wall_seconds"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", choices=TAGS, required=True)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Root full-read and explicit authorization of this one job required")
    record, directory = T / "logs" / (args.job + ".run.json"), T / "outputs" / args.job
    fresh(record, directory, *(T / "logs" / (args.job + s) for s in (".start.json", ".call.json", ".log")))
    result = dict(stage=args.job + ".run", tag=args.job, passed=False, backend="CPU", configuration="ReleaseCPU", threads=1,
        failure=None, public_project_main=True, fixture_or_Run_override=False, physical_acceptance=False,
        native_decoder_invoked=False, all_native_fields_and_clocks_review_pending=True, automatic_follow_up=False,
        direct_owner_no_scheduler=True, later_full_or_half_admitted=False, historical_mutable_source_or_canonical_revalidated=False)
    try:
        run(context(args.job), result)
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        result["inputs"] = final_bindings()
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = True
    except Exception as exc:
        result["inputs"] = list(BOUND.values())
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = result["passed"] = False
        result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
    result["files"] = [entry(p) for p in sorted(directory.rglob("*")) if p.is_file()] if directory.exists() else []
    result["run_out"] = next((e for e in result["files"] if Path(e["path"]).name == "Run.out"), None)
    result.update(payload_hashes_computed_once=True, final_rehash_scope="Consumed prerequisites only; owned payload inventoried once after exit",
                  source_project_formal_or_canonical_files_written=False, following_action_launched=False, watcher_or_queue_invoked=False)
    seal(record, result)
    print(json.dumps(dict(passed=result["passed"], job=args.job, receipt=str(record), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
