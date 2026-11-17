"""One root-admitted P1 staged-load job; reuse immutable M0 inputs, never chain readers."""
from __future__ import annotations
import argparse,csv,ctypes,math,os,re,subprocess,time
from pathlib import Path
import upl_tpi_m0_dt_run_r2 as old
c,gpu=old.c,old.gpu
T,L,S=c.T,c.L,c.S
wt=c.wt
need,identity,native_api,now,stat,write_new=c.need,c.identity,c.native_api,c.now,c.stat,c.write_new
kernel_api,creation,native_exit=gpu.kernel_api,gpu.creation,gpu.native_exit
STAGE="upl_tpi_p1_loadclock_run_r1"
NOTE=T/"notes"/(STAGE+".md")
ROOT_THREAD=old.ROOT_THREAD
ENV_KEYS=("UPL_TPI_CPU_R1","UPL_TPI_GPU_R1","UPL_TPI_M0_DT_R1","UPL_TPI_P1_LOADCLOCK_R1")
REFERENCES={
 "cpu_debug2ms":("DebugCPU","B","upl_tpi_m0_dt_Bdebug2ms_CPU_r1",200,18),
 "debug2":("Debug","B","upl_tpi_m0_dt_Bdebug2_GPU_r1",2,2),
 "Acontrol":("Release","A","upl_tpi_m0_dt_Acontrol_GPU_r1",320,18),
 "window2s":("Release","B","upl_tpi_m0_dt_B10us_window2s_GPU_r1",199996,1263),
}
SIDE="UplTpiP1LoadClockR1"
class Admission(c.Admission):
 def __init__(self,path):
  self.entry,self.data=c.stat(path),c.read(path)
  c.need(self.data.get("stage")==STAGE+".run_admission" and self.data.get("passed")is True and self.data.get("one_job_only")is True,"One new staged-load job admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};self.consumed={}
  c.need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")

def tracked_environment(ctx):
 env=os.environ.copy()
 for k in ENV_KEYS:env.pop(k,None)
 env["UPL_TPI_CPU_R1"if ctx["configuration"]=="DebugCPU"else"UPL_TPI_GPU_R1"]=ctx["scheme"]
 if ctx["scheme"]=="B":env.update(UPL_TPI_M0_DT_R1="EQ40_RH1",UPL_TPI_P1_LOADCLOCK_R1="STAGED")
 if ctx["configuration"]=="DebugCPU":env.update(OMP_NUM_THREADS="1",OMP_DYNAMIC="FALSE")
 return env,{k:env.get(k)for k in (*ENV_KEYS,"OMP_NUM_THREADS","OMP_DYNAMIC")}

def source_build(ad,job,cfg):
 entry=ad.pin(job["build"]["path"]);built=c.read(entry["path"])
 c.need(built.get("passed")is True and built.get("stage")=="upl_tpi_p1_loadclock_build_r1" and built.get("configuration")==cfg,"Actual new staged-load build/configuration required")
 pe=built.get("source_prepare",built.get("prepared"));c.need(isinstance(pe,dict),"Actual source preparation missing")
 ad.pin(pe["path"]);c.same(pe);prep=c.read(pe["path"]);backend="CPU"if cfg=="DebugCPU"else"GPU"
 c.need(prep.get("stage")=="upl_tpi_p1_loadclock_r1.prepare" and prep.get("passed")is True and prep.get("backend")==backend and
  prep.get("other_base_files_byte_identical")is True and prep.get("pressure_helpers_and_schema_byte_identical")is True and
  prep.get("M0_policy_header_byte_identical")is True and prep.get("CUDA_source_and_cuh_byte_identical")is True and
  prep.get("public_class_or_virtual_ABI_changed")is False and prep.get("shared_device_structures_or_inline_tokens_changed")is False,
  "Actual host-only source closure differs")
 ad.pin(Path(prep["source_root"])/"upl_tpi_p1_loadclock_r1.h")
 program=ad.pin(built["program"]["path"]);c.same(built["program"])
 runtime=[ad.pin(e["destination"]["path"])for e in built["runtime"]]
 return entry,c.stat(pe["path"]),program,runtime

def context(ad):
 for p in (Path(__file__),NOTE,Path(old.__file__),Path(gpu.__file__),Path(c.__file__)):ad.pin(p)
 j=ad.data["job"];mode,tag=j["mode"],j["tag"]
 c.need(mode in REFERENCES and re.fullmatch(r"upl_tpi_p1_loadclock_[A-Za-z0-9_]+_r[1-9][0-9]*",tag),"Unsupported new staged-load profile/tag")
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
  if v.get("stage")=="upl_tpi_p1_loadclock_native_r1.review":prior_modes.add(v["job"]["mode"])
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
  policy_environment="absent"if scheme=="A"else"EQ40_RH1",load_clock_environment="absent"if scheme=="A"else"STAGED",source_full_completed=False)

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
    msg=("已授权同线程C02 P1 staged-load单窗终态，tag="+tag+"，event="+event+"。先审原start/call/run/status/terminal/queue_attempt、实际出口和程序/source/input/plan绑定。"
         "本次只B10us2s/1263帧；正常退出不是native/物理验收。先查已有或活动reader，只有根独立准入才能用保留M0reader唯一读取。"
         "全部1040IDs/22数组/原真实scalar clock/signed/ledger/排水/HG与新增44列loadclock审查均不放宽；旧source/fullpartial保持。"
         "不自动half/下一物理窗/新reference/full/其他case；失败保留原始首因和最后原console，不造未保存时间、不重跑。"
         "directowner只45秒queue一次，timeout可能已送达，禁止重发/rearm/selftest。")
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


def check_output(ctx):
 result=old.check_output(ctx);out=Path(ctx["output_directory"]);n=ctx["clock"]["completed_updates"]
 paths=[out/(SIDE+s)for s in (".policy.json",".csv",".summary.json")]
 if ctx["scheme"]=="A":c.need(not any(p.exists()for p in paths),"Default A entered staged-load observer")
 else:
  c.need(all(p.is_file()for p in paths),"Actual staged-load sidecars missing")
  p,s=c.read(paths[0]),c.read(paths[2])
  c.need(p["stage"]==s["stage"]=="upl_tpi_p1_loadclock_r1" and p["backend"]==("CPU"if ctx["configuration"]=="DebugCPU"else"GPU") and
   p["scheme"]=="B" and p["old_half_endpoint_load_fractions"]==[0,.5,1] and
   c.bits(p["fixed_dt_s"])==c.bits(ctx["clock"]["actual_fixed_dt_s"]) and p["global_TimeStep_or_Nstep_changed"]is False and
   p["Dirichlet_source_policy_changed"]is False and p["original_P1_pressure_HG_J_order_retained"]is True and
   s["completed"]is True and s["updates"]==n and s["old_half_endpoint_force_calls"]==[n]*3 and s["site_evaluation_counts"]==[n]*6 and
   c.bits(s["actual_end_s"])==c.bits(ctx["clock"]["actual_scalar_end_s"]) and s["physical_acceptance"]is False,
   "Actual staged-load lifecycle/metadata differs; complete CSV review remains pending")
 return result

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
