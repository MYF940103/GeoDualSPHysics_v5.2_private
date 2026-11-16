"""One independently admitted P1 GPU smoke or startup job; never decode or chain."""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes as wt
import csv
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True
import upl_tpi_cpu_run_r1 as c  # Pure shared stat/clock/identity/Win32 definitions; no CPU main.

T, S, L, DT = c.T, c.S, c.L, c.DT
NOTE = T / "notes/upl_tpi_gpu_run_r3.md"
PREP = L / "upl_tpi_gpu_r1.prepare.json"
OLD_GPU = L / "upl_gpu_stabilizers_release_short_r1.run.json"
SOURCE_FIXTURE_R2 = "UplTpiGpuSourceRoleFixtureR2: source_cases=8 owner_role_cases=8 device_cases_checked=16 device_kernel_completed=true private_error_bits=0"
WINDOWS = {
    "debug2steps": dict(steps=2, frames=2, end=1.2500286102294922e-5, post=0),
    "startup015": dict(steps=24000, frames=344, end=.1500034332275618, post=226),
}


class Admission(c.Admission):
    def __init__(self, path):
        self.entry = c.stat(path)
        self.data = c.read(path)
        c.need(self.data.get("stage") == "upl_tpi_gpu_run_r3.run_admission" and self.data.get("passed") is True
               and self.data.get("one_job_only") is True, "One reviewed GPU job admission required")
        self.frozen = {str(Path(e["path"]).resolve()): e for e in self.data["inputs"]}
        self.consumed = {}


def schedule(root, window):
    if window == "startup015":
        rows, clock = c.schedule(root, window)
        return rows, dict(clock, backend="GPU", planned_A_shared_prefix_states=None,
                          old_GPU_shared_records_require_actual_time_step_join=True)
    w = WINDOWS[window]
    timeout = root.findall(".//timeout")
    c.need(len(timeout) == 1 and timeout[0].get("active") == "true", "Original special output schedule absent")
    segments = [(float(x.get("time")), float(x.get("timeout"))) for x in timeout[0].findall("tout")]
    c.need(segments[:4] == [(0., 2.**-13), (.009765625, 2.**-19), (.01025390625, 2.**-13), (.0250244140625, 2.**-9)],
           "Original startup cadence changed")
    actual, target = 0., c.next_time(0., segments)
    for _ in range(2):
        actual += DT
    c.need(actual == w["end"] and actual < target, "Two-update scalar endpoint is not genuine forced-final")
    rows = [dict(zip(c.HEADER, x)) for x in [(0,0,0,0.,DT,0,0.,0), (1,2,1,actual,DT,0,target,1)]]
    return rows, dict(method="binary64 scalar +=dt with original output targets", backend="GPU",
        actual_scalar_end_s=actual, actual_fixed_dt_s=DT, completed_updates=2,
        CLI_TimeMax_text="0.14999999", CLI_TimeMax_binary32_promoted_to_double_s=c.f32(.14999999),
        actual_stop_is_two_update_nsteps=True, event_completed_step=1600, event_sample_present=False,
        event_step_is_preopen=True, first_post_open_completed_step=1601, post_open_frames=0,
        expected_true_drained_receivers=0, native_actual_clock_review_pending=True)


def context(ad):
    for p in (__file__, NOTE, Path(c.__file__), sys.executable, c.ORIGINAL_RUN, c.SEED_XML, c.SEED_BI4, c.SEED_NORMALS):
        ad.pin(p)
    original = c.read(c.ORIGINAL_RUN)
    c.need(original.get("passed") is True and Path(original["job"]["input_prefix"]).resolve() == c.PREFIX.resolve(),
           "Original fresh source-zero seed provenance differs")
    root = ET.parse(c.SEED_XML).getroot()
    c.need(c.xml_value(root,"DtFixed") == c.xml_value(root,"DtIni") == DT
           and c.xml_value(root,"TimeMax") == 72.88428690075874, "Original seed dt/time configuration changed")
    job = ad.data["job"]
    cfg, scheme, window, tag = (job[x] for x in ("configuration","scheme","window","tag"))
    c.need((cfg,scheme,window)==("Debug","B","debug2steps") or (cfg=="Release" and scheme in ("A","B","C") and window=="startup015"),
           "Only one Debug-B two-update or Release-A/B/C startup job is admitted")
    c.need(re.fullmatch("upl_tpi_gpu_"+cfg+"_"+scheme+"_"+window+r"_r[1-9][0-9]*",tag), "Exact fresh GPU job tag required")
    build_entry=ad.pin(job["source_build"]["path"]);build=c.read(build_entry["path"])
    c.need(build.get("passed") is True and build.get("configuration")==cfg and build.get("object_count")==111
           and build.get("consumed_stats_unchanged") is True
           and build.get("program_help_invocations")==build.get("solver_invocations")==build.get("native_invocations")==0,
           "Actual matched passed private GPU build required")
    prepare_entry=ad.pin(job["source_prepare"]["path"]);prepared=c.read(prepare_entry["path"])
    c.need(prepared.get("passed") is True and len(prepared.get("files",[]))==269,"Actual new GPU source preparation required")
    c.need("base_prepare" in prepared,"The unpatched r1 program is not admitted for physical runs")
    base_entry=ad.pin(prepared["base_prepare"]["path"]);base=c.read(base_entry["path"])
    c.need(prepared.get("host_h_API_and_other_268_files_byte_identical") is True and base.get("passed") is True
           and base.get("class_layout_or_virtual_ABI_changed") is False and base.get("old_kernel_external_signatures_changed") is False,
           "New device-guard source must retain the reviewed physical/API base closure")
    built_prepare=build.get("source_prepare",build.get("prepared"))
    c.need(isinstance(built_prepare,dict) and Path(built_prepare["path"]).resolve()==Path(prepare_entry["path"]).resolve(),"Actual build did not consume the root-selected new source preparation")
    c.same(built_prepare)
    source_entries=[*prepared["recompile_sources"],*prepared["changed_headers"],prepared["source_diff"]]
    source_entries += [x for x in prepared["files"] if Path(x["path"]).name in ("upl_tpi_gpu_r1.h","upl_tpi_gpu_r1.cuh")]
    for e in source_entries:ad.pin(e["path"])
    program=ad.pin(build["program"]["path"]);c.same(build["program"])
    expected_name="DualSPHysics5.2_win64_debug.exe" if cfg=="Debug" else "DualSPHysics5.2_GEO_win64.exe"
    c.need(Path(program["path"]).name==expected_name and Path(program["path"]).resolve().is_relative_to((T/"outputs").resolve()),"Actual private project GPU main program required")
    runtime=[ad.pin(x["destination"]["path"]) for x in build["runtime"]]
    checks=[]
    c.need(ad.data.get("required_passed_checks"),"Root must list actual completed prerequisite reviews")
    for e in ad.data["required_passed_checks"]:
        p=ad.pin(e["path"]);c.need(c.read(p["path"]).get("passed") is True,"A declared prerequisite did not pass");checks.append(p)
    if scheme=="A":
        old=ad.pin(OLD_GPU);c.need(c.read(old["path"]).get("passed") is True,"Retained genuine GPU control run missing")
    rows,clock=schedule(root,window)
    out=T/"outputs"/tag
    paths={x:L/(tag+s) for x,s in (("start",".start.json"),("tool_start",".tool.start.json"),("call",".call.json"),
        ("run",".run.json"),("status",".status.json"),("log",".log"),("memcheck",".memcheck.log"),("plan",".clock.csv"))}
    c.need(not out.exists() and all(not p.exists() for p in paths.values()),"Retained GPU output/partial/call is protected")
    argv=["-gpu","-stable","-mdbc_freeslip",str(c.PREFIX),str(out),"-dirdataout","data","-svres",
          "-tmax:0.14999999","-nsteps:"+str(WINDOWS[window]["steps"])]
    tool=None
    if cfg=="Debug":
        tool=ad.pin(job["memcheck_program"]["path"])
        c.need(Path(tool["path"]).name.lower()=="compute-sanitizer.exe","Actual compute-sanitizer tool required")
    with paths["plan"].open("x",encoding="utf-8",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=c.HEADER);wr.writeheader();wr.writerows(rows)
    return dict(tag=tag,configuration=cfg,scheme=scheme,window=window,program=program,source_build=build_entry,
        prepared=prepare_entry,source_entries=source_entries,runtime=runtime,prerequisite_reviews=checks,
        input_prefix=str(c.PREFIX),output_directory=str(out),data=str(out/"data"),arguments=argv,
        plan=c.stat(paths["plan"]),clock=clock,paths=paths,memcheck_program=tool,
        original_seed=[ad.pin(x) for x in (c.SEED_XML,c.SEED_BI4,c.SEED_NORMALS)],
        required_runtime_markers=job.get("required_runtime_markers",[]),GenCase_invocations=0,PART_restart=False)


def kernel_api():
    k=c.native_api()
    k.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD];k.OpenProcess.restype=wt.HANDLE
    k.WaitForSingleObject.argtypes=[wt.HANDLE,wt.DWORD];k.WaitForSingleObject.restype=wt.DWORD
    return k


def creation(k,handle):
    values=[wt.FILETIME() for _ in range(4)]
    c.need(k.GetProcessTimes(handle,*[ctypes.byref(x) for x in values]),"Actual handle creation time missing")
    return (int(values[0].dwHighDateTime)<<32)|int(values[0].dwLowDateTime)


def native_exit(k,handle):
    value=wt.DWORD();c.need(k.GetExitCodeProcess(handle,ctypes.byref(value)),"Actual handle exit unavailable");return int(value.value)


def run_owned(ad,ctx,result):
    import psutil
    ad.pin(psutil.__file__)
    old=[]
    allowed=ad.data.get("allowed_paused_gpu_processes",[])
    for p in psutil.process_iter(["pid","name","exe","cmdline","create_time","status"]):
        if (p.info["name"] or "").lower().startswith("dualsphysics"):
            old.append(p.info)
            if "cpu" not in (p.info["name"] or "").lower():
                matches=[x for x in allowed if x["pid"]==p.info["pid"] and x["created"]==p.info["create_time"]
                         and Path(x["exe"]).resolve()==Path(p.info["exe"]).resolve() and x["argv"]==p.info["cmdline"]]
                c.need(len(matches)==1 and p.info["status"]==psutil.STATUS_STOPPED,"Another non-certified/active GPU solver is present; never replace it")
    result["processes_before"]=old
    env=os.environ.copy();env["UPL_TPI_GPU_R1"]=ctx["scheme"]
    actual_env={"UPL_TPI_GPU_R1":env["UPL_TPI_GPU_R1"]};result["actual_environment"]=actual_env
    target_argv=[ctx["program"]["path"],*ctx["arguments"]]
    argv=target_argv if ctx["memcheck_program"] is None else [ctx["memcheck_program"]["path"],"--tool","memcheck",
        "--error-exitcode","86","--leak-check","full","--target-processes","all","--log-file",str(ctx["paths"]["memcheck"]),*target_argv]
    owner=c.identity(os.getpid());k=kernel_api();handle=wt.HANDLE();target_handle=None;p=None;first=None
    call=dict(stage=ctx["tag"]+".call",owner=owner,program=c.stat(argv[0]),target_program=ctx["program"],arguments=argv[1:],
        target_arguments=ctx["arguments"],actual_environment=actual_env,started_utc=c.now(),actual_Popen_wait_exit=None,
        actual_Win32_exit=None,target_actual_Win32_exit=None,passed=False,tool_is_solver=ctx["memcheck_program"] is None)
    try:
        ad.finish()
        with ctx["paths"]["log"].open("xb") as f:
            p=subprocess.Popen(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,shell=False,creationflags=subprocess.CREATE_NO_WINDOW)
            current=k.GetCurrentProcess();c.need(k.DuplicateHandle(current,wt.HANDLE(int(p._handle)),current,ctypes.byref(handle),0,False,2),"Original tool handle duplication failed")
            tool=c.identity(p.pid);call.update(child=tool,tool_creation_FILETIME_ticks=creation(k,handle))
            c.need(tool["parent"]==owner["pid"] and tool["argv"][1:]==argv[1:] and Path(tool["exe"]).resolve()==Path(argv[0]).resolve(),"Actual tool ownership/argv differs")
            c.need(abs((call["tool_creation_FILETIME_ticks"]-116444736000000000)/1e7-tool["created"])<=1e-6,"Observed/native tool creation identity differs")
            c.write_new(ctx["paths"]["tool_start"],dict(stage=ctx["tag"]+".tool.start",owner=owner,child=tool,program=call["program"],root_admission=ad.entry))
            if ctx["memcheck_program"] is None:
                target=tool;target_handle=handle
            else:
                target=None
                while p.poll() is None and target is None:
                    for child in psutil.Process(p.pid).children(recursive=True):
                        try:
                            info=c.identity(child.pid)
                            if Path(info["exe"]).resolve()==Path(ctx["program"]["path"]).resolve() and info["argv"][1:]==ctx["arguments"]:
                                candidate=k.OpenProcess(0x100000|0x1000,False,child.pid)
                                c.need(candidate and k.GetProcessId(candidate)==child.pid,"Genuine target native handle missing")
                                target=info;target_handle=candidate;break
                        except (psutil.NoSuchProcess,psutil.AccessDenied):
                            continue
                    if target is None:time.sleep(.01)
                c.need(target is not None,"Memcheck target identity was not captured while live; preserve observed tool evidence")
            call.update(target=target,target_creation_FILETIME_ticks=creation(k,target_handle),target_handle_acquired_before_wait=True)
            c.need(abs((call["target_creation_FILETIME_ticks"]-116444736000000000)/1e7-target["created"])<=1e-6,"Observed/native target creation identity differs")
            c.write_new(ctx["paths"]["start"],dict(stage=ctx["tag"]+".start",owner=owner,tool=tool,target=target,program=ctx["program"],
                source_build=ctx["source_build"],input_prefix=ctx["input_prefix"],output_directory=ctx["output_directory"],arguments=ctx["arguments"],
                plan=ctx["plan"],clock=ctx["clock"],actual_environment=actual_env,root_admission=ad.entry,consumed=list(ad.consumed.values()),physical_acceptance=False))
            call["actual_Popen_wait_exit"]=p.wait()
            c.need(k.WaitForSingleObject(target_handle,0xFFFFFFFF)==0,"Actual target wait failed")
    except Exception as exc:
        first=str(exc)
        if p is not None:call["actual_Popen_wait_exit"]=p.wait()
    finally:
        if target_handle:
            call["target_actual_Win32_exit"]=native_exit(k,target_handle)
            if target_handle is not handle:k.CloseHandle(target_handle)
        if handle:
            call["actual_Win32_exit"]=native_exit(k,handle);k.CloseHandle(handle)
        call.update(ended_utc=c.now(),failure=first,passed=first is None and call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==call["target_actual_Win32_exit"]==0)
        if ctx["paths"]["log"].exists():call["log"]=c.stat(ctx["paths"]["log"])
        c.write_new(ctx["paths"]["call"],call);result["call"]=c.stat(ctx["paths"]["call"])
        result.update(actual_Popen_wait_exit=call["actual_Popen_wait_exit"],actual_Win32_exit=call["actual_Win32_exit"],
            target_actual_Win32_exit=call["target_actual_Win32_exit"],target=call.get("target"),tool_invocations=int(p is not None),
            solver_invocations=int(p is not None) if ctx["memcheck_program"] is None else (1 if isinstance(call.get("target"),dict) else None))
    c.need(call["passed"],first or "Actual owned GPU/tool failed; preserve partial output")


def check_output(ctx):
    out=Path(ctx["output_directory"]);text=(out/"Run.out").read_text(encoding="utf-8-sig");w=WINDOWS[ctx["window"]]
    c.need(text.count("Finished execution (code=0).") == 1 and 'RunMode="Stable - Pos-Cell - Single-GPU"' in text
           and re.search(r"Steps of simulation[.]+:\s*"+str(w["steps"])+r"(?:\s|$)",text)
           and re.search(r"Excluded particles[.]+:\s*0(?:\s|$)",text),"Actual GPU normal finish/steps/no-exclusion differs")
    for marker in ctx["required_runtime_markers"]:
        c.need(isinstance(marker,str) and marker and marker in text,"Root-required actual device-fixture marker missing")
    # The fixture deliberately prints stdout; it does not call the solver Log.
    console=ctx["paths"]["log"].read_text(encoding="utf-8-sig",errors="replace")
    fixture_count=console.count(SOURCE_FIXTURE_R2)
    c.need(fixture_count==(0 if ctx["scheme"]=="A" else 1),"Actual independent r2 device fixture must run exactly once for B/C and stay untaken for A")
    cap=re.search(r"(?m)^TimeMax=([-+0-9.eE]+)\s*$",text)
    c.need(cap and float(cap[1])==float(format(c.f32(.14999999),".16g")),"Rounded TimeMax does not match the unchanged formatter/CLI cap")
    hg=re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)",text)
    cache=re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)",text)
    c.need(hg and cache and tuple(map(int,hg.groups()))==(2*w["steps"],w["steps"],w["steps"],2*w["steps"])
           and tuple(map(int,cache.groups()))==(w["steps"]+1,w["steps"]-1),"Original GPU HG stage/cache counts differ")
    guard=re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)",text)
    c.need(guard,"Original GPU HG necessary safety summary missing")
    net,actual,tau,spin=map(float,guard.groups())
    c.need(all(c.math.isfinite(x) and x>=0 for x in (net,actual,tau,spin)) and tau<=.2 and spin<.01,"Original GPU HG stiffness/small-spin safety failed")
    c.need(sorted(p.name for p in (out/"data").glob("Part_*.bi4"))==["Part_%04d.bi4"%i for i in range(w["frames"])],"Frame presence differs; native content remains pending")
    with (out/"Run.csv").open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f,delimiter=";"))
    c.need(len(rows)==1 and int(rows[0]["Steps"])==w["steps"] and int(rows[0]["PartFiles"])==w["frames"]
           and int(rows[0]["PartsOut"])==0 and int(rows[0]["Np"])==1040 and "gpu" in rows[0]["Hardware"].lower(),"Actual GPU Run.csv metadata differs")
    mem=None
    if ctx["memcheck_program"]:
        mem=ctx["paths"]["memcheck"].read_text(encoding="utf-8-sig",errors="replace")
        c.need(re.search(r"ERROR SUMMARY:\s*0 errors",mem),"Actual compute-sanitizer zero-error summary missing")
    return dict(solver_summary_completed=True,native_frame_presence_only=True,reported_steps=w["steps"],reported_native_frames=w["frames"],
        actual_device_from_Run_csv=rows[0]["Hardware"],actual_memcheck_zero_errors=mem is not None,
        actual_r2_device_fixture_marker_count=fixture_count,device_fixture_inferred_from_build=False,
        memcheck_log=c.stat(ctx["paths"]["memcheck"]) if mem is not None else None)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--execution-authorized",action="store_true");parser.add_argument("--admission",type=Path,required=True);args=parser.parse_args()
    if not args.execution_authorized:parser.error("Independent root single-job admission required")
    ad=ctx=None;result=dict(stage="upl_tpi_gpu_run_r3.run",passed=False,failure=None,solver_invocations=0,native_invocations=0,
        GenCase_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0,automatic_follow_up=False,physical_acceptance=False,
        all22_native_clock_signed_ledger_drainage_and_HG_review_pending=True,old_paused_processes_touched=False)
    try:
        ad=Admission(args.admission);ctx=context(ad);result.update({k:v for k,v in ctx.items() if k!="paths"});result["root_admission"]=ad.entry
        run_owned(ad,ctx,result);result.update(check_output(ctx));result["passed"]=True
    except Exception as exc:result["failure"]=str(exc)
    finally:
        if ctx is not None:
            try:result.update(c.terminal_evidence(ctx))
            except Exception as exc:result["terminal_evidence_failure"]=str(exc);result["passed"]=False
            try:result["consumed"]=ad.finish();result["consumed_stats_unchanged"]=True
            except Exception as exc:result["passed"]=False;result["consumed_stats_unchanged"]=False;result["failure"]=(result["failure"] or "")+"; "+str(exc)
            out=Path(ctx["output_directory"]);result["outputs_stat_only"]=[c.stat(p) for p in sorted(out.rglob("*")) if p.is_file()] if out.exists() else []
            c.write_new(ctx["paths"]["run"],result);c.write_new(ctx["paths"]["status"],dict(stage=ctx["tag"]+".status",run=c.stat(ctx["paths"]["run"]),
                passed=result["passed"],state="pending_native_review" if result["passed"] else "failed_preserved",physical_acceptance=False,following_action_launched=False))
        print(c.json.dumps(dict(passed=result["passed"],tag=result.get("tag"),failure=result["failure"]),ensure_ascii=False))
    return 0 if result["passed"] else 1

if __name__=="__main__":raise SystemExit(main())
