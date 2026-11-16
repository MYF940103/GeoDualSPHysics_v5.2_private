"""One independently root-admitted fresh C04 CPU A/B/C 128-update job.

Only owns/seals the physical solver. Native decoding, comparison and every
later scheme/job require separate root admission; none follows automatically.
"""
from __future__ import annotations
import argparse
import csv
import ctypes
from ctypes import wintypes as wt
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True
import upl_tpi_cryer_cpu_build_r1 as b  # Pure stat/identity helpers; never calls build/main.

T, L = b.T, b.L
NOTE = T / "notes/upl_tpi_cryer_cpu_run_r1.md"
PREFIX = T / "outputs/upl_cryer_freebody_short_r1_seed/upl_cryer_freebody_short_r1"
OLD_CALL = L / "upl_cryer_freebody_smoke128_CPU_r1.call.json"
OLD_NATIVE_CALL = L / "upl_cryer_freebody_smoke128_CPU_r1.native.call.json"
OLD_CLOCK = T / "configs/upl_cryer_freebody_short_r1_smoke128.clock.csv"
OLD_OUT = T / "outputs/upl_cryer_freebody_smoke128_CPU_r1"
OLD_DONE = T / "outputs/upl_cryer_freebody_smoke128_CPU_r1_native/completion.json"
DT = 2.**-20
HEADER = ["part", "time_s", "completed_step", "saved_step", "dt_s"]


def bits(x):
    return struct.pack("<d", x)


class Admission:
    def __init__(self, path):
        self.entry, self.data = b.stat(path), b.read(path)
        b.need(self.data.get("stage") == "upl_tpi_cryer_cpu_run_r1.run_admission" and
               self.data.get("passed") is True and self.data.get("one_job_only") is True,
               "One independently reviewed C04 CPU job admission required")
        self.frozen = {b.key(x["path"]): x for x in self.data["inputs"]}; self.consumed = {}
        b.need(len(self.frozen) == len(self.data["inputs"]), "Duplicate frozen input")

    def pin(self, path):
        k = b.key(path); b.need(k in self.frozen, "Consumed input absent from root admission: " + str(path))
        self.consumed[k] = b.same(self.frozen[k]); return self.consumed[k]

    def finish(self):
        for x in self.consumed.values(): b.same(x)
        b.same(self.entry); return list(self.consumed.values())


def csv_one(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    b.need(len(rows) == 1, "One genuine Run.csv summary required"); return rows[0]


def context(ad):
    import psutil
    for p in (Path(__file__), NOTE, Path(b.__file__), sys.executable, psutil.__file__, OLD_CALL,
              OLD_NATIVE_CALL, OLD_CLOCK, OLD_DONE, OLD_OUT / "Run.out", OLD_OUT / "Run.csv",
              PREFIX.with_suffix(".xml"), PREFIX.with_suffix(".bi4")): ad.pin(p)
    job = ad.data["job"]; scheme, tag = job["scheme"], job["tag"]
    b.need(scheme in ("A", "B", "C") and job["configuration"] == "DebugCPU" and
           job["window"] == "startup128" and
           re.fullmatch("upl_tpi_cryer_cpu_DebugCPU_" + scheme + r"_startup128_r[1-9][0-9]*", tag),
           "Only one fresh DebugCPU A/B/C startup128 job is admitted")
    old, oldnative, done = b.read(OLD_CALL), b.read(OLD_NATIVE_CALL), b.read(OLD_DONE)
    expected_args = ["-cpu", "-ompthreads:8", "-stable", str(PREFIX), str(OLD_OUT), "-dirdataout", "data", "-svres", "-nsteps:128"]
    b.need(old.get("exit_code") == 0 and old.get("direct_exit") is True and old.get("backend") == "CPU"
           and old.get("configuration") == "DebugCPU" and old["arguments"] == expected_args
           and oldnative.get("exit_code") == 0 and done.get("passed") is True
           and done["samples"] == 2 and done["completed_steps"] == 128 and done["actual_end_s"] == 2.**-13,
           "Original actual CPU128 provenance/profile differs; absent old run/start files are not fabricated")
    ad.pin(old["program"]["path"]); b.same(old["program"])
    review_entry = ad.pin(job["source_build_review"]["path"]); b.same(job["source_build_review"])
    review = b.read(review_entry["path"])
    b.need(review.get("stage") == "upl_tpi_cryer_cpu_build_review_r2" and review.get("passed") is True
           and review.get("adopted_completed_build") is True and review.get("original_build_passed") is False
           and review.get("configuration") == "DebugCPU" and review.get("object_count") == 86
           and review.get("program_copied") is True and review.get("program_copy_byte_equal") is True
           and review.get("program_relinked") is False
           and review.get("actual_direct_tool_Popen_and_Win32_exits_all_zero") is True
           and review.get("consumed_stats_unchanged") is True,
           "Explicit independent adoption of the genuinely completed full86 build required")
    failed_entry = ad.pin(review["original_failed_build"]["path"]); b.same(review["original_failed_build"])
    failed = b.read(failed_entry["path"])
    b.need(failed.get("passed") is False and failed.get("failure") == "Actual CL source or dependency argument malformed",
           "The original post-build parser failure must remain failed and exact")
    b.need(len(review["actual_tool_call_receipts"]) == 2, "Actual original environment and MSBuild call pair required")
    for callentry in review["actual_tool_call_receipts"]:
        ad.pin(callentry["path"]); b.same(callentry); call = b.read(callentry["path"])
        b.need(call.get("passed") is True and call.get("actual_Popen_wait_exit") == call.get("actual_Win32_exit") == 0,
               "Actual original environment/MSBuild process exits must be genuine zero")
    program = ad.pin(review["program"]["path"]); b.same(review["program"])
    ad.pin(review["source_program"]["path"]); b.same(review["source_program"])
    b.need(Path(program["path"]).name == "DualSPHysics5.2CPU_win64_debug.exe" and
           b.key(program["path"]) != b.key(review["source_program"]["path"]) and
           Path(program["path"]).resolve().is_relative_to(T / "outputs"),
           "Run the separately reviewed byte-copy package, not an invented new link or canonical executable")
    prep_entry = ad.pin(review["prepared"]["path"]); b.same(review["prepared"]); prep = b.read(prep_entry["path"])
    b.need(prep.get("passed") is True and prep.get("requires_full_DebugCPU_86_TU_compile") is True
           and prep.get("native_count") == 37181 and prep.get("soil_count") == 37173
           and prep.get("fixed_count") == 8 and prep.get("fixed_dt") == DT,
           "Actual complete XYZ C04 source/overlay differs")
    ad.pin(prep["source_diff"]["path"]); b.same(prep["source_diff"])
    runtime = []
    for pair in review["runtime"]:
        ad.pin(pair["source"]["path"]); b.same(pair["source"])
        runtime.append(ad.pin(pair["destination"]["path"])); b.same(pair["destination"])
    package = Path(program["path"]).parent
    b.need(len(runtime) == 5 and {Path(x["path"]).name.casefold() for x in runtime} ==
           {"dsphconfig.xml", "chronoengine.dll", "dsphchrono.dll", "vcomp140.dll", "vcomp140d.dll"}
           and all(Path(x["path"]).parent == package for x in runtime),
           "The adopted executable/config/five runtimes must share their real private program directory")
    xml = ET.parse(PREFIX.with_suffix(".xml")).getroot()
    def val(name):
        rows = [x for x in xml.iter("parameter") if x.get("key") == name]
        b.need(len(rows) == 1, "Unique original seed parameter required: " + name); return float(rows[0].get("value"))
    b.need(val("DtFixed") == val("DtIni") == DT and val("TimeOut") == 2.**-13
           and val("TimeMax") == .00830078125 and val("SoilHourglassXi") == val("SoilBoundaryDerivativeSPR") == 0,
           "Original dt/cadence/TimeMax/HG0/SPR0 seed changed")
    clock = [0.]
    for _ in range(128): clock.append(clock[-1] + DT)
    b.need(bits(clock[-1]) == bits(2.**-13) and clock[-2] < 2.**-13, "Original first ordinary save target crossing differs")
    rows = [dict(zip(HEADER, (0, 0., 0, 0, DT))), dict(zip(HEADER, (1, clock[-1], 128, 127, DT)))]
    with OLD_CLOCK.open(encoding="utf-8-sig", newline="") as f:
        oldrows = list(csv.DictReader(f))
    b.need(len(oldrows) == 2 and list(oldrows[0]) == HEADER and all(
        int(x["part"]) == y["part"] and int(x["completed_step"]) == y["completed_step"]
        and int(x["saved_step"]) == y["saved_step"] and bits(float(x["time_s"])) == bits(y["time_s"])
        and bits(float(x["dt_s"])) == bits(DT) for x, y in zip(oldrows, rows)), "Real retained two-state plan differs")
    oldsummary = csv_one(OLD_OUT / "Run.csv")
    b.need(oldsummary["Hardware"] == "CPU" and int(oldsummary["Steps"]) == 128 and
           int(oldsummary["PartFiles"]) == 2 and int(oldsummary["PartsOut"]) == 0, "Actual old CPU summary differs")
    paths = {name: L / (tag + suffix) for name, suffix in (("start", ".start.json"), ("call", ".call.json"),
        ("run", ".run.json"), ("status", ".status.json"), ("log", ".log"), ("plan", ".clock.csv"))}
    output = T / "outputs" / tag
    b.need(not output.exists() and all(not p.exists() for p in paths.values()), "Existing output/partial/owner record is protected")
    with paths["plan"].open("x", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=HEADER); wr.writeheader(); wr.writerows(rows)
    return dict(tag=tag, scheme=scheme, configuration="DebugCPU", window="startup128", program=program,
        source_build_review=review_entry, original_failed_build=failed_entry, prepared=prep_entry,
        runtime=runtime, input_prefix=str(PREFIX), output_directory=str(output), data=str(output / "data"),
        arguments=["-cpu", "-ompthreads:8", "-stable", str(PREFIX), str(output), "-dirdataout", "data", "-svres", "-nsteps:128"],
        cwd=str(package), paths=paths, plan=b.stat(paths["plan"]), actual_scalar_end=clock[-1],
        original_seed=[ad.pin(PREFIX.with_suffix(x)) for x in (".xml", ".bi4")],
        expected_RunMode_csv=oldsummary["RunMode"], planned_saved_states=rows,
        final_save_is_original_ordinary_target=True, source_zero_cold_start=True, PART_restart=False)


def run_owned(ad, ctx, result):
    env = os.environ.copy(); env["UPL_TPI_CPU_R1"] = ctx["scheme"]; env.pop("UPL_TPI_GPU_R1", None)
    actual_env = {"UPL_TPI_CPU_R1": env["UPL_TPI_CPU_R1"], "UPL_TPI_GPU_R1": None}
    kernel = ctypes.WinDLL("kernel32", use_last_error=True); kernel.GetCurrentProcess.restype = wt.HANDLE
    kernel.DuplicateHandle.argtypes = [wt.HANDLE, wt.HANDLE, wt.HANDLE, ctypes.POINTER(wt.HANDLE), wt.DWORD, wt.BOOL, wt.DWORD]
    kernel.GetProcessTimes.argtypes = [wt.HANDLE, ctypes.POINTER(wt.FILETIME), ctypes.POINTER(wt.FILETIME), ctypes.POINTER(wt.FILETIME), ctypes.POINTER(wt.FILETIME)]
    kernel.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]; kernel.CloseHandle.argtypes = [wt.HANDLE]
    owner = b.identity(os.getpid()); handle = wt.HANDLE(); proc = None
    call = dict(stage=ctx["tag"] + ".call", owner=owner, program=ctx["program"], arguments=ctx["arguments"],
        cwd=ctx["cwd"], actual_environment=actual_env, started_utc=b.now(), passed=False,
        actual_Popen_wait_exit=None, actual_Win32_exit=None, failure=None)
    try:
        ad.finish()
        with ctx["paths"]["log"].open("xb") as stream:
            proc = subprocess.Popen([ctx["program"]["path"], *ctx["arguments"]], cwd=ctx["cwd"], env=env,
                stdout=stream, stderr=subprocess.STDOUT, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            current = kernel.GetCurrentProcess()
            b.need(kernel.DuplicateHandle(current, wt.HANDLE(int(proc._handle)), current, ctypes.byref(handle), 0, False, 2), "Original solver handle duplication failed")
            child = b.identity(proc.pid); times = [wt.FILETIME() for _ in range(4)]
            b.need(kernel.GetProcessTimes(handle, *[ctypes.byref(x) for x in times]), "Actual solver creation time missing")
            ticks = (int(times[0].dwHighDateTime) << 32) | int(times[0].dwLowDateTime)
            b.need(child["parent"] == owner["pid"] and b.key(child["exe"]) == b.key(ctx["program"]["path"])
                   and child["argv"][1:] == ctx["arguments"] and abs((ticks - 116444736000000000) / 1e7 - child["created"]) <= 1e-6,
                   "Actual original solver parent/exe/argv/creation differs")
            call.update(child=child, creation_FILETIME_ticks=ticks)
            b.write_new(ctx["paths"]["start"], dict(stage=ctx["tag"] + ".start", owner=owner, child=child,
                program=ctx["program"], arguments=ctx["arguments"], actual_environment=actual_env,
                input_prefix=ctx["input_prefix"], output_directory=ctx["output_directory"], plan=ctx["plan"],
                source_build_review=ctx["source_build_review"], root_admission=ad.entry, physical_acceptance=False))
            call["actual_Popen_wait_exit"] = proc.wait()
    except Exception as exc:
        call["failure"] = str(exc)
        if proc is not None: call["actual_Popen_wait_exit"] = proc.wait()
    finally:
        if handle:
            value = wt.DWORD()
            if kernel.GetExitCodeProcess(handle, ctypes.byref(value)): call["actual_Win32_exit"] = int(value.value)
            else: call["failure"] = call["failure"] or "Original Win32 solver exit unavailable"
            kernel.CloseHandle(handle)
        call["passed"] = call["failure"] is None and call["actual_Popen_wait_exit"] == call["actual_Win32_exit"] == 0
        call["ended_utc"] = b.now()
        if ctx["paths"]["log"].exists(): call["log"] = b.stat(ctx["paths"]["log"])
        b.write_new(ctx["paths"]["call"], call)
        result.update(call=b.stat(ctx["paths"]["call"]), actual_environment=actual_env,
            actual_Popen_wait_exit=call["actual_Popen_wait_exit"], actual_Win32_exit=call["actual_Win32_exit"],
            child=call.get("child"), solver_invocations=int(proc is not None))
    b.need(call["passed"], call["failure"] or "Actual owned solver failed; preserve partials")


def postcheck(ctx):
    output = Path(ctx["output_directory"]); text = (output / "Run.out").read_text(encoding="utf-8-sig")
    b.need(text.count("Finished execution (code=0).") == 1 and
           re.search(r"Steps of simulation[.]+:\s*128(?:\s|$)", text) and
           re.search(r"Excluded particles[.]+:\s*0(?:\s|$)", text), "Actual CPU completion/steps/exclusion summary differs")
    row = csv_one(output / "Run.csv")
    b.need(row["Hardware"] == "CPU" and row["RunMode"] == ctx["expected_RunMode_csv"] and
           int(row["Np"]) == 37181 and int(row["Nbound"]) == int(row["Nfixed"]) == 8 and
           int(row["Steps"]) == 128 and int(row["PartFiles"]) == 2 and int(row["PartsOut"]) == 0,
           "Actual CPU/threads/full native set/frame/zero-exclusion metadata differs")
    b.need(sorted(p.name for p in (output / "data").glob("Part_*.bi4")) == ["Part_0000.bi4", "Part_0001.bi4"], "Genuine expected two native files missing/extra; decoding stays pending")
    summary = output / "UplTpiCpuR1.summary.json"
    if ctx["scheme"] == "A":
        b.need(not any((output / ("UplTpiCpuR1" + suffix)).exists() for suffix in (".policy.json", ".csv", ".summary.json")), "Default A unexpectedly entered the private history branch")
    else:
        document = b.read(summary)
        b.need(document.get("completed") is True and
               document.get("scheme") == ("B_TPI_alpha_0p5_beta0" if ctx["scheme"] == "B" else "C_PPE_t_alpha0_beta0")
               and document.get("alpha") == (.5 if ctx["scheme"] == "B" else 0.) and document.get("beta") == 0
               and document.get("commits") == document.get("endpoint_calls") == 128
               and document.get("core_field_bit_checks") == 7 * 37173 * 128 and document.get("HG_readonly_snapshot_checks") == 0
               and bits(float(document["actual_end"])) == bits(ctx["actual_scalar_end"]), "Actual pressure lifecycle counts/end/HG0 summary differs")
    return dict(solver_summary_completed=True, native_presence_only=True, native_review_pending=True,
                reported_steps=128, reported_frames=2, actual_RunMode=row["RunMode"], observed_loop_time_s=float(row["TSimul"]),
                no_half_equivalence_or_physical_acceptance=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true"); parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args(); b.need(args.execution_authorized, "One independent physical-job root admission required")
    ad = ctx = None
    result = dict(stage="upl_tpi_cryer_cpu_run_r1.run", passed=False, failure=None, solver_invocations=0,
        build_invocations=0, native_invocations=0, GenCase_invocations=0, VTK_invocations=0, SHA_scans=0,
        automatic_follow_up=False, original_processes_touched=False, physical_acceptance=False,
        all22_ID_clock_finite_elastic_noout_ledger_and_necessary_limits_review_pending=True)
    try:
        ad = Admission(args.admission); ctx = context(ad); result.update({k: v for k, v in ctx.items() if k != "paths"})
        result["root_admission"] = ad.entry; run_owned(ad, ctx, result); result.update(postcheck(ctx)); result["passed"] = True
    except Exception as exc: result["failure"] = str(exc)
    finally:
        if ctx is not None:
            for name, path in (("console", ctx["paths"]["log"]), ("Run_out", Path(ctx["output_directory"]) / "Run.out")):
                if path.exists():
                    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
                    result["last_raw_" + name + "_PART_line"] = next((x for x in reversed(lines) if re.match(r"^Part_\d+\s", x)), None)
                    result["first_raw_" + name + "_error"] = next((x for x in lines if "*** Exception" in x or re.search(r"\berror\b", x, re.I)), None)
            try: result["consumed"] = ad.finish(); result["consumed_stats_unchanged"] = True
            except Exception as exc: result["passed"] = False; result["failure"] = (result["failure"] or "") + "; " + str(exc)
            output = Path(ctx["output_directory"])
            result["output_stats_only"] = [b.stat(p) for p in output.rglob("*") if p.is_file()] if output.exists() else []
            b.write_new(ctx["paths"]["run"], result)
            b.write_new(ctx["paths"]["status"], dict(stage=ctx["tag"] + ".status", run=b.stat(ctx["paths"]["run"]),
                passed=result["passed"], state="pending_unique_native_review" if result["passed"] else "failed_preserved", next_job_launched=False))
        print(b.json.dumps(dict(passed=result["passed"], tag=result.get("tag"), failure=result["failure"]), ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__": raise SystemExit(main())
