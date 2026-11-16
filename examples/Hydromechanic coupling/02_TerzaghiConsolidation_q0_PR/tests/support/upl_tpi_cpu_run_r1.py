"""Own exactly one root-admitted P1 CPU short solver; seal, never decode or chain."""
from __future__ import annotations
import argparse
import csv
import ctypes
from ctypes import wintypes as wt
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
R = T.parents[3]
S = R / "src"
L = T / "logs"
NOTE = T / "notes/upl_tpi_cpu_run_r1.md"
PREP = L / "upl_tpi_cpu_r1.prepare.json"
ORIGINAL_RUN = L / "upl_bigstep_2tv_CPU1_r1.run.json"
PREFIX = T / "outputs/upl_bigstep_full_r1_seed/upl_bigstep_2tv_CPU1_r1"
SEED_XML = PREFIX.with_suffix(".xml")
SEED_BI4 = PREFIX.with_suffix(".bi4")
SEED_NORMALS = Path(str(PREFIX) + "_Normals.nbi4")
DT = float("6.2501430511474609e-6")
EVENT_STEP = 1600
HEADER = ["part", "completed_steps", "saved_step", "time_s", "dt_s",
          "post_open_by_completed_step", "target_time_s", "forced_final"]
WINDOWS = {
    "debug2ms": dict(steps=320, frames=18, end=.002000045776367195,
                     post=0, shared_A=17, tmax_text=".002", nominal=.002),
    "startup015": dict(steps=24000, frames=344, end=.1500034332275618,
                       post=226, shared_A=343, tmax_text="0.14999999", nominal=.15),
}


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def stat(path):
    p = Path(path).resolve()
    s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def same(entry):
    actual = stat(entry["path"])
    need(actual == {k: entry[k] for k in ("path", "bytes", "mtime_ns")},
         "Root-frozen stat changed: " + entry["path"])
    return actual


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(path, data):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def bits(value):
    return struct.pack("<d", value)


class Admission:
    def __init__(self, path):
        self.entry = stat(path)
        self.data = read(path)
        need(self.data.get("stage") == "upl_tpi_cpu_run_r1.run_admission"
             and self.data.get("passed") is True and self.data.get("one_job_only") is True,
             "One independently reviewed root run admission required")
        self.frozen = {str(Path(e["path"]).resolve()): e for e in self.data["inputs"]}
        self.consumed = {}

    def pin(self, path):
        p = str(Path(path).resolve())
        need(p in self.frozen, "Consumed input absent from root admission: " + p)
        self.consumed[p] = same(self.frozen[p])
        return self.consumed[p]

    def finish(self):
        same(self.entry)
        for entry in self.consumed.values():
            same(entry)
        return list(self.consumed.values())


def next_time(value, segments):
    # Exact operation order of frozen JDsOutputTime::GetNextTime. Products here
    # form output targets; actual simulation clocks below use scalar +=DT only.
    base = 0
    while base + 1 < len(segments) and value >= segments[base + 1][0]:
        base += 1
    anchor, interval = segments[base]
    next_anchor = segments[base + 1][0] if base + 1 < len(segments) else sys.float_info.max
    if value < anchor:
        return anchor
    count = int((value - anchor) / interval)
    target = anchor + interval * count
    while target <= value:
        target = anchor + interval * count
        count += 1
    return min(target, next_anchor)


def schedule(xml_root, window):
    w = WINDOWS[window]
    nodes = xml_root.findall(".//timeout")
    need(len(nodes) == 1 and nodes[0].get("active") == "true", "Original special cadence required")
    segments = [(float(n.get("time")), float(n.get("timeout"))) for n in nodes[0].findall("tout")]
    need(segments == [(0., .0001220703125), (.009765625, 2. ** -19),
                      (.01025390625, .0001220703125), (.0250244140625, .001953125),
                      (2.0000457763671875, .18218571428571428)], "Original special cadence changed")
    cap = f32(float(w["tmax_text"]))
    table = [dict(zip(HEADER, (0, 0, 0, 0., DT, 0, 0., 0)))]
    actual, target = 0., next_time(0., segments)
    for completed in range(1, w["steps"] + 1):
        actual += DT
        ordinary_output = actual >= target
        need(not (actual >= cap and completed < w["steps"]), "CLI TimeMax would stop before the admitted update cap")
        if ordinary_output or actual >= cap or completed == w["steps"]:
            table.append(dict(zip(HEADER, (len(table), completed, completed - 1, actual, DT,
                int(completed > EVENT_STEP), target, int(completed == w["steps"] and not ordinary_output)))))
            target = next_time(actual, segments)
    need(len(table) == w["frames"] and bits(actual) == bits(w["end"])
         and sum(x["post_open_by_completed_step"] for x in table) == w["post"]
         and table[-1]["forced_final"] == 1, "Independent short scalar clock/count declaration differs")
    if window == "startup015":
        need(table[117]["completed_steps"] == EVENT_STEP and not table[117]["post_open_by_completed_step"]
             and table[118]["completed_steps"] == EVENT_STEP + 1
             and table[-2]["completed_steps"] == 23691, "Original event and shared-prefix boundary differ")
    else:
        need(table[-2]["completed_steps"] == 313 and not any(x["post_open_by_completed_step"] for x in table),
             "Debug pre-open prefix differs")
    return table, dict(method="binary64 scalar +=dt and unchanged output-target arithmetic",
        actual_scalar_end_s=actual, nominal_window_s=w["nominal"], actual_fixed_dt_s=DT,
        CLI_TimeMax_text=w["tmax_text"], CLI_TimeMax_binary32_promoted_to_double_s=cap,
        completed_updates=w["steps"], event_completed_step=EVENT_STEP,
        event_step_is_preopen=True, first_post_open_completed_step=EVENT_STEP + 1,
        post_open_frames=w["post"], expected_true_drained_receivers=10 * w["post"],
        forced_final_definition="terminal save before next ordinary output target; stopped by TimeMax/nsteps",
        planned_A_shared_prefix_states=w["shared_A"], native_actual_clock_review_pending=True)


def xml_value(root, key):
    nodes = [n for n in root.iter("parameter") if n.get("key") == key]
    need(len(nodes) == 1, "Unique original XML parameter absent: " + key)
    return float(nodes[0].get("value"))


def prepare_context(ad):
    ad.pin(__file__)
    ad.pin(NOTE)
    ad.pin(sys.executable)
    original_entry = ad.pin(ORIGINAL_RUN)
    original = read(ORIGINAL_RUN)
    need(original.get("passed") is True and original["job"]["input_prefix"] == str(PREFIX)
         and original["job"]["dt_s"] == DT, "Completed full-A seed provenance differs")
    for path in (SEED_XML, SEED_BI4, SEED_NORMALS):
        ad.pin(path)
    expected_seed = {Path(original["job"][k]["path"]).name: original["job"][k]
                     for k in ("runtime", "initial_BI4", "normals")}
    for path in (SEED_XML, SEED_BI4, SEED_NORMALS):
        need(Path(expected_seed[path.name]["path"]).resolve() == path.resolve()
             and expected_seed[path.name]["bytes"] == path.stat().st_size, "Original full-A seed identity/size changed")
    root = ET.parse(SEED_XML).getroot()
    need(xml_value(root, "DtFixed") == xml_value(root, "DtIni") == DT
         and xml_value(root, "SoilHourglassXi") == .1 and xml_value(root, "SoilBoundaryDerivativeSPR") == 1
         and xml_value(root, "Visco") == .1 and xml_value(root, "SoilDampingCoef") == .04
         and xml_value(root, "SlipMode") == 3 and xml_value(root, "TimeMax") == 72.88428690075874,
         "Original input physical/time configuration changed")
    job = ad.data["job"]
    window, scheme, configuration = (job[k] for k in ("window", "scheme", "configuration"))
    allowed = configuration == "DebugCPU" and scheme == "B" and window == "debug2ms"
    allowed |= configuration == "ReleaseCPU" and scheme in ("A", "B", "C") and window == "startup015"
    need(allowed, "This author runner admits only Debug B 2ms or one Release A/B/C startup015")
    tag = job["tag"]
    need(re.fullmatch("upl_tpi_cpu_" + configuration + "_" + scheme + "_" + window + r"_r[1-9][0-9]*", tag),
         "Fresh per-job tag differs from its exact configuration/scheme/window")
    build_entry = ad.pin(job["source_build"]["path"])
    need(build_entry == {k: job["source_build"][k] for k in ("path", "bytes", "mtime_ns")}, "Admitted actual build stat differs")
    build = read(build_entry["path"])
    need(build.get("passed") is True and build.get("configuration") == configuration
         and build.get("solver_invocations") == build.get("program_help_invocations") == build.get("native_invocations") == 0,
         "Actual successful isolated P1 CPU build required; failed builds cannot be adopted")
    if configuration == "DebugCPU":
        need(Path(build_entry["path"]).resolve() == (L / "upl_tpi_cpu_DebugCPU_r2.build.json").resolve()
             and build.get("original_class_header_ABI_unchanged") is True
             and build.get("consumed_stats_unchanged") is True, "Actual passed full-frozen-A Debug r2 required")
        preparation = build["prepared"]
    else:
        need(Path(build_entry["path"]).resolve() == (L / "upl_tpi_cpu_release_link_r3.build.json").resolve()
             and build.get("stage") == "upl_tpi_cpu_release_link_r3"
             and build.get("original_failed_r2_and_source_stats_unchanged") is True
             and build.get("original_object_paths_and_stats_unchanged") is True
             and build.get("compile_invocations") == 0 and build.get("link_invocations") == 1,
             "Actual passed link-only Release r3, not the failed r2, required")
        preparation = build["original_source_preparation"]
        for entry in build["successful_original_CL_calls"]:
            ad.pin(entry["path"])
            call = read(entry["path"])
            need(call.get("passed") is True and call.get("actual_Popen_wait_exit") == call.get("actual_Win32_exit") == 0,
                 "An adopted original Release TU compile did not genuinely pass")
    prepared_entry = ad.pin(PREP)
    need(Path(preparation["path"]).resolve() == PREP.resolve(), "Build does not consume the admitted private overlay")
    same(preparation)
    prepared = read(PREP)
    need(prepared.get("passed") is True and prepared.get("public_source_changed") is False
         and prepared.get("class_or_header_ABI_changed") is False, "Actual private prepare closure differs")
    source_archives = [ad.pin(e["path"]) for e in [*prepared["changed_sources"], prepared["private_header"], prepared["source_diff"]]]
    program = ad.pin(build["program"]["path"])
    need(program == {k: build["program"][k] for k in ("path", "bytes", "mtime_ns")}, "Passed build's actual program changed")
    runtime = [ad.pin(x["destination"]["path"]) for x in build["runtime"]]
    checks = []
    need(ad.data.get("required_passed_checks"), "Root must declare completed prerequisite reviews for this one job")
    for entry in ad.data["required_passed_checks"]:
        frozen = ad.pin(entry["path"])
        need(read(frozen["path"]).get("passed") is True, "One declared prior review did not pass")
        checks.append(frozen)
    table, clock = schedule(root, window)
    prefix = original["job"]["saved_clock_table"][:WINDOWS[window]["shared_A"]]
    need(table[:-1] == prefix, "Independent genuine shared original-A saved clocks differ")
    out = T / "outputs" / tag
    paths = {name: L / (tag + suffix) for name, suffix in
             (("start", ".start.json"), ("call", ".call.json"), ("run", ".run.json"),
              ("status", ".status.json"), ("log", ".log"), ("plan", ".clock.csv"))}
    need(not out.exists() and all(not p.exists() for p in paths.values()), "Retained run/output/partial evidence is protected")
    argv = ["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip", str(PREFIX), str(out),
            "-dirdataout", "data", "-svres", "-tmax:" + WINDOWS[window]["tmax_text"],
            "-nsteps:" + str(WINDOWS[window]["steps"])]
    with paths["plan"].open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(table)
    plan = stat(paths["plan"])
    return dict(tag=tag, window=window, scheme=scheme, configuration=configuration,
        program=program, source_build=build_entry, prepared=prepared_entry,
        source_archives=source_archives, runtime=runtime, prerequisite_reviews=checks,
        original_full_A_run=original_entry, original_input_prefix=str(PREFIX),
        seed=[stat(x) for x in (SEED_XML, SEED_BI4, SEED_NORMALS)], original_XML_TimeMax_s=xml_value(root, "TimeMax"),
        output_directory=str(out), data=str(out / "data"), working_directory=str(S),
        arguments=argv, plan=plan, clock=clock, paths=paths,
        expected_native_arrays=22, expected_native_count=1040, expected_fixed=40, expected_soil=1000,
        scalar_plan_written_before_physical_launch=True, actual_seed_GenCase_invocations=0,
        source_zero_cold_start=True, PART_restart=False)


def identity(pid):
    import psutil
    p = psutil.Process(pid)
    return dict(pid=pid, created=p.create_time(), exe=p.exe(), argv=p.cmdline(), parent=p.ppid(), status=p.status())


def native_api():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wt.HANDLE
    kernel.DuplicateHandle.argtypes = [wt.HANDLE, wt.HANDLE, wt.HANDLE, ctypes.POINTER(wt.HANDLE), wt.DWORD, wt.BOOL, wt.DWORD]
    kernel.GetProcessId.argtypes = [wt.HANDLE]
    kernel.GetProcessId.restype = wt.DWORD
    kernel.GetProcessTimes.argtypes = [wt.HANDLE, ctypes.POINTER(wt.FILETIME), ctypes.POINTER(wt.FILETIME), ctypes.POINTER(wt.FILETIME), ctypes.POINTER(wt.FILETIME)]
    kernel.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    kernel.CloseHandle.argtypes = [wt.HANDLE]
    return kernel


def own_solver(ad, context, result):
    import psutil
    ad.pin(psutil.__file__)
    before = []
    for process in psutil.process_iter(["pid", "name", "exe", "create_time", "cmdline", "status"]):
        if (process.info["name"] or "").lower().startswith("dualsphysics"):
            before.append(process.info)
    need(not any("cpu" in (p["name"] or "").lower() for p in before), "Another CPU solver is present; root must review it, no process replacement")
    owner = identity(os.getpid())
    env = os.environ.copy()
    env["UPL_TPI_CPU_R1"] = context["scheme"]
    env["OMP_NUM_THREADS"] = "1"
    env["OMP_DYNAMIC"] = "FALSE"
    result["actual_environment"] = {k: env[k] for k in ("UPL_TPI_CPU_R1", "OMP_NUM_THREADS", "OMP_DYNAMIC")}
    result["processes_before"] = before
    kernel = native_api()
    handle, child = wt.HANDLE(), None
    started, timer = now(), time.perf_counter()
    call = dict(stage=context["tag"] + ".call", owner=owner, program=context["program"],
                arguments=context["arguments"], cwd=str(S), started_utc=started,
                actual_environment=result["actual_environment"], shell=False,
                actual_Popen_wait_exit=None, actual_Win32_exit=None, passed=False)
    first_error = None
    try:
        ad.finish()
        with context["paths"]["log"].open("xb") as stream:
            child = subprocess.Popen([context["program"]["path"], *context["arguments"]],
                cwd=S, env=env, stdout=stream, stderr=subprocess.STDOUT, shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW)
            # Duplicate the genuine CreateProcess handle before any wait; it
            # survives even if a short child exits before later observations.
            current = kernel.GetCurrentProcess()
            need(bool(kernel.DuplicateHandle(current, wt.HANDLE(int(child._handle)), current,
                ctypes.byref(handle), 0, False, 2)), "Unable to duplicate original Popen native process handle")
            need(kernel.GetProcessId(handle) == child.pid, "Original native process handle PID mismatch")
            creation, exit_time, kernel_time, user_time = (wt.FILETIME() for _ in range(4))
            need(bool(kernel.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time),
                ctypes.byref(kernel_time), ctypes.byref(user_time))), "Original native creation time unavailable")
            creation_ticks = (int(creation.dwHighDateTime) << 32) | int(creation.dwLowDateTime)
            observed = identity(child.pid)
            need(observed["parent"] == owner["pid"] and Path(observed["exe"]).resolve() == Path(context["program"]["path"]).resolve()
                 and observed["argv"][1:] == context["arguments"], "Observed direct-child owner/program/argv differs")
            need(abs((creation_ticks - 116444736000000000) / 10000000. - observed["created"]) <= 1e-6,
                 "Native/observed child creation times differ")
            call.update(child=observed, original_Win32_creation_FILETIME_ticks=creation_ticks,
                        native_handle_acquired_before_wait=True)
            start = dict(stage=context["tag"] + ".start", owner=owner, child=observed,
                utc=now(), original_Win32_creation_FILETIME_ticks=creation_ticks,
                program=context["program"], source_build=context["source_build"],
                input_prefix=context["original_input_prefix"], output_directory=context["output_directory"],
                arguments=context["arguments"], working_directory=str(S), plan=context["plan"],
                clock=context["clock"], actual_environment=result["actual_environment"],
                root_admission=ad.entry, consumed=list(ad.consumed.values()),
                actual_solver_identity_verified=True, physical_acceptance=False)
            write_new(context["paths"]["start"], start)
            result["start"] = stat(context["paths"]["start"])
            call["actual_Popen_wait_exit"] = child.wait()
    except Exception as exc:
        first_error = str(exc)
        # Never abandon or terminate a genuine owned solver on an audit error.
        # Await this already-created child and preserve its original exits.
        if child is not None:
            call["actual_Popen_wait_exit"] = child.wait()
    finally:
        if handle:
            exit_code = wt.DWORD()
            if kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                call["actual_Win32_exit"] = int(exit_code.value)
            elif first_error is None:
                first_error = "Original process-handle final exit unavailable"
            kernel.CloseHandle(handle)
        call.update(ended_utc=now(), wall_seconds=time.perf_counter() - timer,
                    failure=first_error, passed=first_error is None and call["actual_Popen_wait_exit"] == call["actual_Win32_exit"] == 0)
        if context["paths"]["log"].exists():
            call["log"] = stat(context["paths"]["log"])
        write_new(context["paths"]["call"], call)
        result["call"] = stat(context["paths"]["call"])
        result["actual_Popen_wait_exit"] = call["actual_Popen_wait_exit"]
        result["actual_Win32_exit"] = call["actual_Win32_exit"]
        result["child"] = call.get("child")
        result["solver_invocations"] = int(child is not None)
    need(call["passed"], first_error or "Actual owned solver failed; retain original exit/console/partials")


def check_output(context):
    out = Path(context["output_directory"])
    text = (out / "Run.out").read_text(encoding="utf-8-sig")
    w = WINDOWS[context["window"]]
    need(text.count("Finished execution (code=0).") == 1
         and 'RunMode="Stable - Pos-Double - Single core"' in text
         and re.search(r"Steps of simulation[.]+:\s*" + str(w["steps"]) + r"(?:\s|$)", text)
         and re.search(r"Excluded particles[.]+:\s*0(?:\s|$)", text), "Actual normal finish/update count/no-exclusion differs")
    printed_cap = re.search(r"(?m)^TimeMax=([-+0-9.eE]+)\s*$", text)
    # Frozen fun::VarStr(double) uses RealStr(double,16,true), not a
    # round-trip 17-digit/native clock representation. Match that log formatter;
    # do not weaken the separate owner-CLI and exact native-clock requirements.
    expected_printed_cap = float(format(context["clock"]["CLI_TimeMax_binary32_promoted_to_double_s"], ".16g"))
    need(printed_cap and float(printed_cap[1]) == expected_printed_cap,
         "Printed CLI TimeMax differs from the frozen 16-significant-digit formatter")
    hg = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    cache = re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
    need(hg and cache and tuple(map(int, hg.groups())) == (2*w["steps"], w["steps"], w["steps"], 2*w["steps"])
         and tuple(map(int, cache.groups())) == (w["steps"]+1, w["steps"]-1), "Original two-force/two-update HG/cache counters differ")
    guard = re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)", text)
    need(guard, "Original single-J HG summary guards absent")
    net, actual_net, tau, spin = map(float, guard.groups())
    need(all(math.isfinite(x) and x >= 0. for x in (net, actual_net, tau, spin)) and tau <= .2 and spin < .01,
         "Original HG finite/dt/spin guard failed")
    need(sorted(p.name for p in (out / "data").glob("Part_*.bi4")) == ["Part_%04d.bi4" % i for i in range(w["frames"])],
         "Planned native frame-presence sequence differs; native content remains pending")
    with (out / "Run.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    need(len(rows) == 1 and int(rows[0]["Steps"]) == w["steps"] and int(rows[0]["PartFiles"]) == w["frames"]
         and int(rows[0]["Np"]) == 1040 and int(rows[0]["PartsOut"]) == 0
         and int(rows[0]["Nbound"]) == int(rows[0]["Nfixed"]) == 40,
         "Actual Run.csv updates/frame/fixed/no-exclusion metadata differs")
    sidecars = [out / x for x in ("UplTpiCpuR1.policy.json", "UplTpiCpuR1.csv", "UplTpiCpuR1.summary.json")]
    if context["scheme"] == "A":
        need(not any(p.exists() for p in sidecars), "Default A unexpectedly allocated/wrote TPI sidecars")
    else:
        need(all(p.is_file() for p in sidecars), "Completed B/C implementation sidecar closure absent")
        summary = read(sidecars[2])
        need(summary.get("completed") is True and summary.get("commits") == summary.get("endpoint_calls") == w["steps"]
             and summary.get("core_field_bit_checks") == 7*1000*w["steps"]
             and summary.get("HG_readonly_snapshot_checks") == 2*1000*w["steps"]
             and bits(summary["actual_end"]) == bits(w["end"]), "Actual B/C stage lifecycle summary differs")
    return dict(solver_summary_completed=True, native_frame_presence_only=True,
        Run_out_TimeMax_is_rounded_16_significant_digit_text=printed_cap[1],
        reported_steps=w["steps"], reported_native_frames=w["frames"],
        HG=dict(logical_forces=2*w["steps"], updates_each=w["steps"], ratecalculations=w["steps"]+1,
                cache_hits=w["steps"]-1, max_reference_net=net, max_actual_float_net=actual_net, max_dt_tau=tau, spinbound=spin),
        Run_csv_PhysicalTime_is_rounded_not_native_clock=rows[0].get("PhysicalTime"),
        sidecars=[stat(p) for p in sidecars if p.exists()])


def terminal_evidence(context):
    result = {}
    for key, path in (("console", context["paths"]["log"]), ("Run_out", Path(context["output_directory"]) / "Run.out")):
        if path.is_file():
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
            result[key+"_last_raw_PART_line"] = next((x for x in reversed(lines) if re.match(r"^\s*Part_[0-9]+\s", x)), None)
            result[key+"_first_actual_error_line"] = next((x for x in lines if re.search(r"\*\*\* Exception|^Text:|\bERROR\b|\bError:", x)), None)
            if key == "Run_out":
                result["actual_Run_out_normal_finish"] = "Finished execution (code=0)." in lines
    result["unsaved_native_time_inferred"] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("A separately reviewed invocation of one physical job is required")
    ad, context = None, None
    result = dict(stage="upl_tpi_cpu_run_r1.run", passed=False, failure=None,
        solver_invocations=0, GenCase_invocations=0, native_invocations=0, VTK_invocations=0,
        build_invocations=0, SHA_scans=0, Git_invocations=0, automatic_follow_up=False,
        old_process_stopped_resumed_or_restarted=False, physical_acceptance=False,
        all22_native_and_actual_clock_signed_ledger_drainage_review_pending=True,
        default_A_shared_prefix_review_pending=True, source_Part_restart=False)
    try:
        ad = Admission(args.admission)
        context = prepare_context(ad)
        result.update({k: v for k, v in context.items() if k != "paths"})
        result["root_admission"] = ad.entry
        own_solver(ad, context, result)
        result.update(check_output(context))
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    finally:
        if context is not None:
            try:
                result.update(terminal_evidence(context))
            except Exception as exc:
                result["passed"] = False
                result["terminal_evidence_failure"] = str(exc)
                result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
            result["solver_completed"] = (result.get("actual_Popen_wait_exit") == result.get("actual_Win32_exit") == 0
                                           and result.get("actual_Run_out_normal_finish") is True)
            try:
                result["consumed"] = ad.finish()
                result["consumed_stats_unchanged"] = True
            except Exception as exc:
                result["passed"] = False
                result["consumed_stats_unchanged"] = False
                result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
            out = Path(context["output_directory"])
            result["outputs_stat_only"] = [stat(p) for p in sorted(out.rglob("*")) if p.is_file()] if out.exists() else []
            result["completed_utc"] = now()
            write_new(context["paths"]["run"], result)
            write_new(context["paths"]["status"], dict(stage=context["tag"] + ".status", passed=result["passed"],
                status="solver_completed_pending_native_review" if result["passed"] else "failed_or_audit_rejected_preserved",
                run=stat(context["paths"]["run"]), actual_Popen_wait_exit=result.get("actual_Popen_wait_exit"),
                actual_Win32_exit=result.get("actual_Win32_exit"), failure=result["failure"],
                physical_acceptance=False, native_invoked=False, following_action_launched=False))
        else:
            # A preflight rejection creates no physical job. Preserve one new
            # rejection receipt when a safe admitted tag is available.
            result["preflight_rejected_before_context_or_solver"] = True
            if ad is not None:
                tag = ad.data.get("job", {}).get("tag", "")
                if re.fullmatch(r"upl_tpi_cpu_(DebugCPU_B_debug2ms|ReleaseCPU_[ABC]_startup015)_r[1-9][0-9]*", tag):
                    rejection = L / (tag + ".preflight_rejection.json")
                    if not rejection.exists():
                        result["root_admission"] = ad.entry
                        result["tag"] = tag
                        result["consumed"] = list(ad.consumed.values())
                        write_new(rejection, result)
        print(json.dumps(dict(passed=result["passed"], tag=result.get("tag"), failure=result["failure"],
                              solver_invocations=result["solver_invocations"]), ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
