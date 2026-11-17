"""One root-admitted P3 job; reuse immutable M0 inputs, never chain readers or solvers."""
from __future__ import annotations
import argparse,csv,ctypes,math,os,re,subprocess,time
from pathlib import Path
import upl_tpi_m0_dt_run_r2 as old
c,gpu=old.c,old.gpu
T,L,S=c.T,c.L,c.S
wt=c.wt
need,identity,native_api,now,stat,write_new=c.need,c.identity,c.native_api,c.now,c.stat,c.write_new
kernel_api,creation,native_exit=gpu.kernel_api,gpu.creation,gpu.native_exit
STAGE="upl_tpi_p3_run_r1"
NOTE=T/"notes"/(STAGE+".md")
ROOT_THREAD=old.ROOT_THREAD
ENV_KEYS=("UPL_TPI_CPU_R1","UPL_TPI_GPU_R1","UPL_TPI_M0_DT_R1","UPL_TPI_P1_LOADCLOCK_R1","UPL_TPI_P2_ROWS_R1","UPL_TPI_P3_ROWS_R1")
REFERENCES={
 "cpu_debug2ms":("DebugCPU","B","upl_tpi_m0_dt_Bdebug2ms_CPU_r1",200,18),
 "debug2":("Debug","B","upl_tpi_m0_dt_Bdebug2_GPU_r1",2,2),
 "Acontrol":("Release","A","upl_tpi_m0_dt_Acontrol_GPU_r1",320,18),
 "window2s":("Release","B","upl_tpi_m0_dt_B10us_window2s_GPU_r1",199996,1263),
}
SIDE="UplTpiP3DtR1"
class Admission(c.Admission):
 def __init__(self,path):
  self.entry,self.data=c.stat(path),c.read(path)
  c.need(self.data.get("stage")==STAGE+".run_admission" and self.data.get("passed")is True and self.data.get("one_job_only")is True,"One independently admitted P3 job required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};self.consumed={}
  c.need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")

def tracked_environment(ctx):
 env=os.environ.copy()
 for k in ENV_KEYS:env.pop(k,None)
 env["UPL_TPI_CPU_R1"if ctx["configuration"]=="DebugCPU"else"UPL_TPI_GPU_R1"]=ctx["scheme"]
 if ctx["scheme"]=="B":env.update(UPL_TPI_M0_DT_R1="EQ40_RH1",UPL_TPI_P3_ROWS_R1="3")
 if ctx["configuration"]=="DebugCPU":env.update(OMP_NUM_THREADS="1",OMP_DYNAMIC="FALSE")
 return env,{k:env.get(k)for k in (*ENV_KEYS,"OMP_NUM_THREADS","OMP_DYNAMIC")}

def source_build(ad,job,cfg):
  backend="CPU"if cfg=="DebugCPU"else"GPU"
  expected=L/("upl_tpi_p3_"+cfg+"_r1.build.json")
  c.need(Path(job["build"]["path"]).resolve()==expected.resolve(),"Exact P3 build tag/configuration required")
  entry=ad.pin(expected);c.same(job["build"]);built=c.read(entry["path"])
  c.need(built.get("passed")is True and built.get("stage")=="upl_tpi_p3_build_r1" and built.get("configuration")==cfg
         and built.get("consumed_stats_unchanged")is True,"Actual new P3 build/configuration required")
  pe=built.get("source_prepare",built.get("prepared"));c.need(isinstance(pe,dict),"P3 build omitted actual source preparation")
  label="upl_tpi_p3_"+backend+"_r1"
  c.need(Path(pe["path"]).resolve()==(L/(label+".prepare.json")).resolve(),"Build is not bound to selected P3 CPU/GPU r1 source")
  ad.pin(pe["path"]);c.same(pe);prep=c.read(pe["path"])
  stage="upl_tpi_p3_source_r1.prepare"
  cls="JSphCpu"if backend=="CPU"else"JSphGpu";helper="upl_tpi_cpu_r1.h"if backend=="CPU"else"upl_tpi_gpu_r1.h"
  expected_root=T/"outputs"/(label+"_source")
  c.need(prep.get("stage")==stage and prep.get("passed")is True and prep.get("backend")==backend
         and Path(prep["source_root"]).resolve()==expected_root.resolve()
         and len(prep["files"])==(267 if backend=="CPU"else 270)
         and prep.get("changed_sources")==[cls+"Single.cpp"] and prep.get("recompile_sources")==[cls+".cpp",cls+"Single.cpp"]
         and prep.get("changed_headers")==[helper,"upl_tpi_m0_dt_r2.h"]
         and prep.get("other_base_files_byte_identical")is True and prep.get("spatial_operator_sources_byte_identical")is True
         and prep.get("five_phase_original_bound_arithmetic_retained")is True and prep.get("CUDA_source_and_cuh_byte_identical")is True
         and prep.get("public_class_or_virtual_ABI_changed")is False and prep.get("shared_device_structures_or_inline_tokens_changed")is False
         and prep.get("material_J_HG_update_order_retained")is True and prep.get("old_source_clock_retained")is True
         and prep.get("endpoint_defect_rounds")==3 and prep.get("actual_full_forces_per_update")==5
         and prep.get("consumed_stats_unchanged")is True,"Actual P3 full source closure differs; no renamed P1 source accepted")
  if backend=="GPU":c.need(prep.get("GPU_original_prefix_bytes_after_removing_host_only_block")==3850,"GPU device-visible closure proof differs")
  byname={Path(x["path"]).name:x for x in prep["files"]}
  for name in [cls+".cpp",cls+"Single.cpp",helper,"upl_tpi_m0_dt_r2.h"]:
    e=ad.pin(expected_root/name);c.same(byname[name]);c.need(e=={k:byname[name][k]for k in ("path","bytes","mtime_ns")},"P3 executed source stat differs")
  program=ad.pin(built["program"]["path"]);c.same(built["program"])
  runtime=[ad.pin(e["destination"]["path"])for e in built["runtime"]]
  return entry,c.stat(pe["path"]),program,runtime

def context(ad):
 for p in (Path(__file__),NOTE,Path(old.__file__),Path(gpu.__file__),Path(c.__file__)):ad.pin(p)
 j=ad.data["job"];mode,tag=j["mode"],j["tag"]
 c.need(mode in REFERENCES and re.fullmatch(r"upl_tpi_p3_[A-Za-z0-9_]+_r[1-9][0-9]*",tag),"Unsupported new P3 profile/tag")
 cfg,scheme,reference,steps,frames=REFERENCES[mode]
 c.need(j["configuration"]==cfg and j["scheme"]==scheme,"Exact declared profile differs")
 build,prepared,program,runtime=source_build(ad,j,cfg)
 rp=L/(reference+".run.json");ad.pin(rp);ref=c.read(rp)
 c.need(ref.get("passed")is True and ref["stage"]in("upl_tpi_m0_dt_run_r1.run","upl_tpi_m0_dt_run_r2.run") and
  (ref["mode"],ref["configuration"],ref["scheme"])==(mode,cfg,scheme) and ref["clock"]["completed_updates"]==steps and ref["clock"]["native_frames"]==frames,"Retained immutable input/clock reference differs")
 check=L/(reference+".native_review_m0_r1.json");ad.pin(check);c.need(c.read(check)["passed"],"Retained native profile qualification failed")
 for e in [ref["plan"],*ref["seed"]]:ad.pin(e["path"]);c.same(e)
 root=old.ET.fromstring(Path(ref["input_prefix"]+".xml").read_text(encoding="utf-8-sig"))
 w=ref["clock"];rows,clock=old.plan(root,w["actual_fixed_dt_s"],w["runtime_TimeMax_s"],w["nsteps_upper_cap"],w["event_completed_step"])
 c.need(clock==w,"Original scalar clock declaration changed")
 with Path(ref["plan"]["path"]).open(encoding="utf-8-sig",newline="")as f:
  reader=csv.DictReader(f);saved=list(reader);c.need(reader.fieldnames==c.HEADER and len(saved)==frames,"Original planned CSV shape differs")
 for row,expected in zip(saved,rows):
  c.need(all(c.bits(float(row[k]))==c.bits(float(expected[k]))for k in c.HEADER),"Immutable actual scalar plan differs")
 checks=[];prior_modes=set()
 for e in ad.data["required_passed_checks"]:
  checks.append(ad.pin(e["path"]));v=c.read(e["path"]);c.need(v.get("passed")is True,"Prerequisite failed")
  if v.get("stage")=="upl_tpi_p3_native_r1.review":prior_modes.add(v["job"]["mode"])
 required={"cpu_debug2ms":set(),"debug2":{"cpu_debug2ms"},"Acontrol":{"cpu_debug2ms","debug2"},"window2s":{"cpu_debug2ms","debug2","Acontrol"}}[mode]
 c.need(checks and required<=prior_modes,"Required earlier native implementation gates missing")
 paths={k:L/(tag+s)for k,s in (("start",".start.json"),("tool_start",".tool.start.json"),("call",".call.json"),("run",".run.json"),("status",".status.json"),("log",".log"),("memcheck",".memcheck.log"))}
 out=T/"outputs"/tag
 c.need(not out.exists() and all(not p.exists()for p in paths.values()) and not any((L/(tag+s)).exists()for s in (".terminal.json",".queue_attempt.json",".queue_result.json")),"Existing job/outputs protected")
 argv=list(ref["arguments"]);c.need(argv.count(ref["output_directory"])==1,"Original output argument is not unique")
 argv[argv.index(ref["output_directory"])]=str(out)
 mem=ad.pin(j["memcheck_program"]["path"])if cfg=="Debug"else None
 if mem:c.need(Path(mem["path"]).name.lower()=="compute-sanitizer.exe","Real memcheck tool required")
 return dict(tag=tag,mode=mode,window=mode,configuration=cfg,scheme=scheme,program=program,source_build=build,source_prepare=prepared,runtime=runtime,
  reference_run=c.stat(rp),reference_native_review=c.stat(check),prerequisite_reviews=checks,clock=clock,plan=ref["plan"],seed=ref["seed"],
  input_prefix=ref["input_prefix"],original_input_prefix=ref["input_prefix"],output_directory=str(out),data=str(out/"data"),arguments=argv,memcheck_program=mem,
  paths=paths,required_runtime_markers=[],GenCase_invocations=0,PART_restart=False,pressure_history_cold_start=True,event_divisor=1600 if scheme=="A"else 1000,
  policy_environment="absent"if scheme=="A"else"EQ40_RH1",load_clock_environment="absent",pressure_rows_environment="absent"if scheme=="A"else"3",source_full_completed=False)

def own_solver(ad, context, result):
    import psutil
    ad.pin(psutil.__file__)
    before = []
    for process in psutil.process_iter(["pid", "name", "exe", "create_time", "cmdline", "status"]):
        if (process.info["name"] or "").lower().startswith("dualsphysics"):
            before.append(process.info)
    need(not any("cpu" in (p["name"] or "").lower() for p in before), "Another CPU solver is present; root must review it, no process replacement")
    owner = identity(os.getpid())
    env, result["actual_environment"] = tracked_environment(context)
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
    env,actual_env=tracked_environment(ctx);result["actual_environment"]=actual_env
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

def notification(ad, path):
    if path is None:
        c.need(ad.data.get("notification_required") is not True,"Root-required direct-owner completion missing")
        return None
    e=ad.pin(path);v=c.read(path)
    c.need(v.get("stage")==STAGE+".notify_admission" and v.get("passed") is True and
           v.get("root_thread_id")==ROOT_THREAD==os.environ.get("CODEX_THREAD_ID") and
           Path(v["run_admission_path"]).resolve()==Path(ad.entry["path"]).resolve() and
           v.get("max_attempts")==1 and v.get("timeout_s")==45 and v.get("watcher") is False,
           "Exact same-root one-attempt completion admission required")
    for key in ("codex","successful_queue_attempt","successful_queue_result"):
        ad.pin(v[key]["path"]);c.same(v[key])
    a,r=c.read(v["successful_queue_attempt"]["path"]),c.read(v["successful_queue_result"]["path"])
    c.need(r.get("status")=="queued" and r.get("actual_exit")==0 and r.get("attempts")==1 and
           a["arguments"][1:5]==["queue","--thread",ROOT_THREAD,"--message"] and
           a["program"]==v["codex"],"Actual already-successful queue protocol required; no self-test")
    return dict(admission=e,**v)

def notify_once(ctx,result,profile):
    if profile is None:return
    tag=ctx["tag"];terminal,attempt,reply=[L/(tag+x) for x in (".terminal.json",".queue_attempt.json",".queue_result.json")]
    c.need(not any(x.exists() for x in (terminal,attempt,reply)),"Existing queue attempt protected; never resend")
    event="run_passed_pending_native_review" if result["passed"] else "failed_preserved_pending_diagnosis"
    c.write_new(terminal,dict(stage=STAGE+".terminal",event=event,tag=tag,owner=c.identity(os.getpid()),
        run=c.stat(ctx["paths"]["run"]),status=c.stat(ctx["paths"]["status"]),
        actual_Win32_exit=result.get("actual_Win32_exit"),target_actual_Win32_exit=result.get("target_actual_Win32_exit"),
        first_actual_error=result.get("console_first_actual_error_line"),
        last_original_console_PART_line=result.get("console_last_raw_PART_line"),physical_acceptance=False))
    msg=("Authorized same-thread C02 P3 terminal. tag="+tag+" event="+event+". "
         "Read original start/call/run/status/terminal/queue_attempt, actual owned exits and program/source/input/plan bindings first. "
         "This is one B10us2s window with 199996 updates and 1263 planned native frames. Exit0 is pending native and physical review only. "
         "Check existing/active readers before a separately root-admitted unique read. Preserve all 1040 IDs,22 typed arrays,scalar clocks,signed intervals,ledger,drainage,HG and all three P3 pressure rounds/five-phase dt guards. "
         "No automatic decoder,next solver,half,reference,full run or other case. Preserve first real failure and last raw console; invent no unsaved state. "
         "This direct owner queues once with45s timeout. Timeout may have delivered: never resend,rearm or self-test.")
    c.need(msg.isascii(),"Completion message must remain ASCII")
    argv=[profile["codex"]["path"],"queue","--thread",ROOT_THREAD,"--message",msg]
    c.write_new(attempt,dict(stage=STAGE+".queue_attempt",terminal=c.stat(terminal),program=profile["codex"],
        arguments=argv,attempt=1,max_attempts=1,timeout_s=45,timeout_may_have_delivered_no_resend=True))
    outcome=dict(stage=STAGE+".queue_result",attempt=c.stat(attempt),attempts=1,do_not_resend=True)
    try:
        c.need(os.environ.get("CODEX_THREAD_ID")==ROOT_THREAD,"Root thread changed before queue")
        c.same(profile["codex"])
        r=subprocess.run(argv,cwd=T.parent,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding="utf-8",errors="replace",timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        outcome.update(status="queued" if r.returncode==0 else "queue_failed",actual_exit=r.returncode,output=r.stdout)
    except subprocess.TimeoutExpired as exc:
        output=exc.stdout or ""
        outcome.update(status="delivery_uncertain",output=output.decode("utf-8","replace") if isinstance(output,bytes) else output,
            error=str(exc),timeout_may_have_delivered=True)
    except Exception as exc:outcome.update(status="queue_failed",error=str(exc))
    c.write_new(reply,outcome)


DT_HEADER=["part","actual_save_time_s","saved_step","completed_updates","dt_s","interval_pre","interval_cor","interval_endpoint1","interval_endpoint2","interval_endpoint3","total_pre","total_cor","total_endpoint1","total_endpoint2","total_endpoint3","interval_empty","min_force_CFL_s","min_skeleton_wave_AV_CFL_s","min_Rh_hydro_s","min_legacy_Kw_wave_CFL_reference_s","min_HG_limit_reference_s","min_selected_bound_s","max_dt_minus_bound_s"]
CPU_PRESSURE_HEADER="part,pressure_round,native_id,source_step_zero_based,completed_step,source_time_s,actual_save_time_s,dt_s,pn_Pa,previous_Pa,prediction_double_Pa,mechanical_half_actual_float_Pa,endpoint_q_actual_float_Pa,S_1_per_m_s,Rgamma_Pa_per_m_s,raw_candidate_float_Pa,actual_after_BC_float_Pa,prior_committed_finalP_stale_Pa,theta_half_for_J_1_per_s,theta_endpoint_1_per_s,Jn,Jhalf,Jfull,source_drained,endpoint_drained,provisional_or_final_commit_drained,provisional_endpoint_validation_count,commits,endpoint_calls,endpoint_writes,core_field_bit_checks,hg_snapshot_checks".split(',')
GPU_PRESSURE_HEADER="part,native_id,source_step_zero_based,completed_step,source_time_s,actual_save_time_s,dt_s,pn_Pa,previous_Pa,prediction_double_Pa,half_actual_float_Pa,endpoint_q_actual_float_Pa,S_1_per_m_s,Rgamma_Pa_per_m_s,raw_final_float_Pa,final_field_float_Pa,theta_half_for_J_1_per_s,theta_endpoint_1_per_s,Jn,Jhalf,Jfull,source_drained,endpoint_drained,commit_drained,commits,endpoint_calls,core_field_bit_checks,hg_snapshot_checks,round,has_endpoint_observation,final_field_is_previous_step,validated_BC_value_float_Pa".split(',')

def csv_header(path,expected):
  with path.open(encoding="utf-8-sig",newline="")as f:
    head=next(csv.reader(f),None)
  c.need(head==expected,"Actual P3 CSV header differs: "+str(path))

def dt_output(ctx,out):
  w=ctx["clock"];n=w["completed_updates"];frames=w["native_frames"]
  paths=[out/(SIDE+s)for s in (".policy.json",".csv",".summary.json")]
  c.need(all(p.is_file()for p in paths),"Actual P3 five-phase dt sidecars missing")
  p,s=c.read(paths[0]),c.read(paths[2])
  c.need(p["stage"]==s["stage"]=="upl_tpi_p3_dt_r1" and p["backend"]==("CPU"if ctx["configuration"]=="DebugCPU"else"GPU")
    and p["pressure_scheme"]=="B" and p["endpoint_defect_rounds"]==p["force_phases_per_update"]-2==3
    and p["dt_policy"]==s["dt_policy"]=="M0_Eq40_Rh1" and p["R_h"]==s["R_h"]==1
    and p["HG_limit_reference_available"]is False and s["HG_limit_reference_available"]is False
    and p["source_clock_policy"]==s["source_clock_policy"]=="original_TimeStep_all_five_phases"
    and s["completed"]is True and s["endpoint_defect_rounds"]==3 and s["force_phases_per_update"]==5
    and s["updates"]==s["pre"]==s["cor"]==s["endpoint1"]==s["endpoint2"]==s["endpoint3"]==n
    and s["saved_intervals_including_initial"]==frames and c.bits(p["fixed_dt_s"])==c.bits(w["actual_fixed_dt_s"])
    and c.bits(s["actual_end_s"])==c.bits(w["actual_scalar_end_s"])
    and math.isfinite(s["max_dt_minus_bound_s"]) and s["max_dt_minus_bound_s"]<=1e-14,
    "Actual five-phase P3 dt summary failed")
  with paths[1].open(encoding="utf-8-sig",newline="")as f:
    reader=csv.DictReader(f);rows=list(reader);c.need(reader.fieldnames==DT_HEADER and len(rows)==frames,"Actual five-phase dt CSV shape differs")
  with Path(ctx["plan"]["path"]).open(encoding="utf-8-sig",newline="")as f:plan=list(csv.DictReader(f))
  previous=0
  for i,(r,planned)in enumerate(zip(rows,plan)):
    complete=int(r["completed_updates"]);delta=complete-previous
    c.need(int(r["part"])==i and complete==int(planned["completed_steps"]) and int(r["saved_step"])==int(planned["saved_step"])
      and c.bits(float(r["actual_save_time_s"]))==c.bits(float(planned["time_s"])) and c.bits(float(r["dt_s"]))==c.bits(w["actual_fixed_dt_s"]),"Actual P3 dt save identity differs")
    c.need([int(r[k])for k in DT_HEADER[5:10]]==[delta]*5 and [int(r[k])for k in DT_HEADER[10:15]]==[complete]*5
      and int(r["interval_empty"])==int(delta==0),"Actual P3 interval/cumulative five-force counts differ")
    if delta:
      error=float(r["max_dt_minus_bound_s"]);bound=float(r["min_selected_bound_s"])
      c.need(math.isfinite(error) and error<=1e-14 and math.isfinite(bound) and bound>0.,"Actual P3 nonempty necessary-bound interval failed")
    previous=complete
  c.need(previous==n,"P3 dt CSV final update count differs")
  return paths

def check_output(ctx):
  out=Path(ctx["output_directory"]);w=ctx["clock"];n=w["completed_updates"];frames=w["native_frames"]
  text=(out/"Run.out").read_text(encoding="utf-8-sig")
  c.need(text.count("Finished execution (code=0).") == 1 and re.search(r"Steps of simulation[.]+:\s*"+str(n)+r"(?:\s|$)",text)
    and re.search(r"Excluded particles[.]+:\s*0(?:\s|$)",text),"Actual normal summary differs")
  cap=re.search(r"(?m)^TimeMax=([-+0-9.eE]+)\s*$",text)
  c.need(cap and float(cap[1])==float(format(w["runtime_TimeMax_s"],".16g")),"Actual rounded TimeMax formatter/immutable cap differs")
  with (out/"Run.csv").open(encoding="utf-8-sig",newline="")as f:rows=list(csv.DictReader(f,delimiter=";"))
  c.need(len(rows)==1 and int(rows[0]["Steps"])==n and int(rows[0]["PartFiles"])==frames and int(rows[0]["Np"])==1040
    and int(rows[0]["PartsOut"])==0 and int(rows[0]["Nbound"])==int(rows[0]["Nfixed"])==40,"Actual Run.csv metadata differs")
  console=ctx["paths"]["log"].read_text(encoding="utf-8-sig",errors="replace")
  fixture_count=console.count(gpu.SOURCE_FIXTURE_R2)
  if ctx["configuration"]=="DebugCPU":
    c.need('RunMode="Stable - Pos-Double - Single core"'in text,"Actual CPU mode differs")
  else:
    c.need('RunMode="Stable - Pos-Cell - Single-GPU"'in text and "gpu"in rows[0]["Hardware"].lower()
      and fixture_count==(0 if ctx["scheme"]=="A"else 1),"Actual GPU mode/hardware/once16 fixture differs")
  c.need(sorted(p.name for p in (out/"data").glob("Part_*.bi4"))==["Part_%04d.bi4"%i for i in range(frames)],"Actual native frame presence differs")
  hg=re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)",text)
  cache=re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)",text)
  c.need(hg and cache and tuple(map(int,hg.groups()))==(2*n,n,n,2*n) and tuple(map(int,cache.groups()))==(n+1,n-1),"Original physical HG lifecycle/cache differs")
  guard=re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)",text)
  c.need(guard,"Original HG safety summary absent");net,actual,tau,spin=map(float,guard.groups())
  c.need(all(math.isfinite(x) and x>=0 for x in (net,actual,tau,spin)) and tau<=.2 and spin<.01,"Original HG necessary safety failed")
  products=[]
  if ctx["scheme"]=="A":
    c.need(not any(out.glob("UplTpi*")),"Default A entered a prototype pressure/dt/loadclock output path")
  else:
    cpu=ctx["configuration"]=="DebugCPU";prefix="UplTpiP3CpuR1"if cpu else"UplTpiP3GpuR1"
    policy,summary=out/(prefix+".policy.json"),out/(prefix+".summary.json")
    files=[out/(prefix+".csv")]if cpu else[out/(prefix+".round1.csv"),out/(prefix+".round2.csv"),out/(prefix+".round3.csv")]
    c.need(policy.is_file() and summary.is_file() and all(p.is_file()for p in files),"Actual P3 pressure products missing")
    p,s=c.read(policy),c.read(summary);expected="upl_tpi_p3_cpu_r1"if cpu else"upl_tpi_p3_gpu_r1"
    c.need(p["stage"]==s["stage"]==expected and p["alpha"]==s["alpha"]==.5 and p["beta"]==s["beta"]==0
      and p["M0"]is True and p["endpoint_defects_per_step"if cpu else"endpoint_defect_rounds"]==s["endpoint_defects_per_step"if cpu else"endpoint_defect_rounds"]==3 and p["native_count"]==1040 and p["soil_count"]==1000
      and s["completed"]is True and s["commits"]==n and s["endpoint_calls"]==s["endpoint_writes"]==3*n
      and s["provisional_validations"]==s["endpoint_transitions"]==2*n and s["core_field_bit_checks"]==21000*n and s["HG_readonly_snapshot_checks"]==6000*n
      and c.bits(s["actual_end"])==c.bits(w["actual_scalar_end_s"])
      and all(p[k]is False and s[k]is False for k in ("paper_literal_LF","second_order_claimed","true_implicit_solution","physical_acceptance")),
      "Actual independent P3 pressure lifecycle/limits differ")
    if cpu:
      c.need(s["first_validations"]==s["second_validations"]==n and p["global_source_clock_unchanged"]is True and p["staged_load_clock_enabled"]is False
        and p["provisional_finalP_fields_are_prior_commit_not_p1_or_p2"]is True and p["both_provisional_BC_values_are_directly_captured"]is True
        and p["q2_is_actual_p1_and_q3_is_actual_p2"]is True and p["PorePressRate_is_R3_at_actual_p2_scaled_residual_not_R_at_p3_or_dpdt"]is True
        and s["theta_endpoint_is_not_J_integration_theta"]is True and s["PorePressRate_is_R3_at_actual_p2_scaled_residual_not_R_at_p3_or_dpdt"]is True,"Actual CPU P3 source/round metadata differs")
    else:
      c.need(s["pre_calls"]==s["cor_calls"]==s["J_calls"]==n and s["provisional_row_D2D_copies"]==2*n
        and s["initial_provisional_row_D2D_copies"]==2 and s["saved_records_per_round"]==1000*frames
        and p["endpoint_source_clock_is_original_n"]is True and p["staged_load_clock"]is False
        and p["provisional_finalP_is_stale_previous_step"]is True and p["provisional_BC_value_is_validated_rule_not_extra_native_save"]is True
        and p["second_q_is_actual_first_BC_float"]is True and p["third_q_is_actual_second_BC_float"]is True
        and s["PorePressRate_is_round3_scaled_residual_at_p2_not_dpdt_or_R_at_p3"]is True,"Actual GPU P3 source/D2D metadata differs")
    for path in files:csv_header(path,CPU_PRESSURE_HEADER if cpu else GPU_PRESSURE_HEADER)
    products=[policy,summary,*files,*dt_output(ctx,out)]
    c.need(not any(out.glob("UplTpiP1LoadClockR1*")) and not any(out.glob("UplTpiM0DtR1*")) and not any(out.glob("UplTpiP2*")),"P3 emitted stale P2/staged-load/three-phase dt schema")
  if ctx["memcheck_program"]:
    mem=ctx["paths"]["memcheck"].read_text(encoding="utf-8-sig",errors="replace")
    c.need(re.search(r"ERROR SUMMARY:\s*0 errors",mem),"Actual memcheck zero-error summary absent")
  return dict(solver_summary_completed=True,native_and_physical_review_pending=True,actual_HG_max_dt_tau=tau,actual_HG_spinbound=spin,
    actual_Hardware=rows[0]["Hardware"],actual_r2_device_fixture_count=fixture_count if ctx["configuration"]!="DebugCPU"else None,
    P3_sidecar_runtime_gate_header_and_summary_only=True,P3_pressure_and_native_content_review_pending=True,
    actual_five_phase_dt_CSV_checked=ctx["scheme"]=="B",sidecar_products=[c.stat(p)for p in products])

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--notify-admission",type=Path)
 ap.add_argument("--execution-authorized",action="store_true");args=ap.parse_args();c.need(args.execution_authorized,"Root single-job execution admission required")
 ad=ctx=profile=None
 result=dict(stage=STAGE+".run",passed=False,failure=None,solver_invocations=0,native_invocations=0,VTK_invocations=0,build_invocations=0,Git_invocations=0,SHA_scans=0,
  physical_acceptance=False,automatic_follow_up=False,old_process_stopped_resumed_or_restarted=False)
 try:
  ad=Admission(args.admission);profile=notification(ad,args.notify_admission);ctx=context(ad)
  c.need(profile is None or ctx["mode"]=="window2s","Only independent 2s owner may queue once")
  result.update({k:v for k,v in ctx.items()if k!="paths"});result["root_admission"]=ad.entry
  for e in [*ctx["seed"],ctx["plan"]]:c.same(e)
  (own_solver if ctx["configuration"]=="DebugCPU"else run_owned)(ad,ctx,result)
  result.update(check_output(ctx));result["passed"]=True
 except Exception as exc:result["failure"]=str(exc)
 finally:
  if ctx is not None:
   try:
    result.update(c.terminal_evidence(ctx))
    for e in [*ctx["seed"],ctx["plan"]]:c.same(e)
    result["reused_immutable_seed_and_plan_stats_unchanged"]=True;result["consumed"]=ad.finish()
   except Exception as exc:result.update(passed=False,terminal_audit_failure=str(exc))
   c.write_new(ctx["paths"]["run"],result);c.write_new(ctx["paths"]["status"],dict(stage=ctx["tag"]+".status",passed=result["passed"],run=c.stat(ctx["paths"]["run"]),state="pending_native_review"if result["passed"]else"failed_preserved"))
   notify_once(ctx,result,profile)
  print(c.json.dumps(dict(passed=result["passed"],tag=result.get("tag"),failure=result["failure"]),ensure_ascii=False))
 return 0 if result["passed"]else 1
if __name__=="__main__":raise SystemExit(main())
