"""One root-admitted 2000-update Nsight probe; no source change, decoder, notification or next action."""
from __future__ import annotations
import argparse,csv,ctypes,os,re,shutil,subprocess,time
from pathlib import Path
import upl_tpi_p3_run_r1 as base
c,gpu,T,L,S=base.c,base.gpu,base.T,base.L,base.S
TAG="upl_tpi_p3_cost_probe_r1";JOB="upl_tpi_p3_cost_probe_GPU_r1";SOURCE="upl_tpi_p3_B10us_window2s_GPU_r1"
NOTE=T/"notes"/(TAG+".md");NSYS=Path(r"C:/Program Files/NVIDIA Corporation/Nsight Systems 2023.3.3/target-windows-x64/nsys.exe")
OUT=T/"outputs"/JOB;REPORTDIR=T/"outputs"/(JOB+"_nsys");REPORT=REPORTDIR/"trace"
PLAN=L/(JOB+".clock.csv");PATHS={k:L/(JOB+s)for k,s in(("start",".start.json"),("tool_start",".tool.start.json"),("call",".call.json"),("run",".run.json"),("status",".status.json"),("log",".log"))}
FLAGS=["profile","--trace=cuda","--sample=none","--cpuctxsw=none","--system-wide=false","--kill=false","--wait=all","--stop-on-exit=true","--force-overwrite=false","--stats=true","--show-output=true"]
class Admission(c.Admission):
 def __init__(self,path):
  self.entry,self.data=c.stat(path),c.read(path);self.consumed={}
  c.need(self.data.get("stage")==TAG+".run_admission"and self.data.get("passed")is True and self.data.get("one_probe_only")is True,"One root-reviewed performance-only admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};c.need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")

def planned(ref):
 dt=ref["clock"]["actual_fixed_dt_s"];clocks=[0.]
 for _ in range(2000):clocks.append(clocks[-1]+dt)
 with Path(ref["plan"]["path"]).open(encoding="utf-8-sig",newline="")as f:
  r=csv.DictReader(f);old=list(r);c.need(r.fieldnames==c.HEADER and len(old)==1263,"Original full plan must remain1263 rows/eight columns")
 rows=[dict(r)for r in old if int(r["completed_steps"])<=2000]
 c.need(len(rows)==209 and int(rows[-1]["completed_steps"])==1990,"Real shared209-state prefix differs")
 for i,row in enumerate(rows):
  n=int(row["completed_steps"]);c.need(int(row["part"])==i and int(row["saved_step"])==(n-1 if n else 0)and c.bits(float(row["time_s"]))==c.bits(clocks[n])and c.bits(float(row["dt_s"]))==c.bits(dt)and int(row["forced_final"])==0,"Original shared scalar state differs")
 if int(rows[-1]["completed_steps"])!=2000:
  pending=next(r for r in old if int(r["completed_steps"])>2000)
  rows.append(dict(part=len(rows),completed_steps=2000,saved_step=1999,time_s=clocks[-1],dt_s=dt,post_open_by_completed_step=1,target_time_s=pending["target_time_s"],forced_final=1))
 c.need(len(rows)==210 and c.bits(clocks[-1])==c.bits(.02000045776367273),"Genuine forced2000 endpoint differs")
 return rows,dict(method="binary64 scalar +=dt;209 original states plus one genuine forced final",actual_fixed_dt_s=dt,actual_scalar_end_s=clocks[-1],completed_updates=2000,native_frames=len(rows),runtime_TimeMax_s=2.,nsteps_upper_cap=2000,event_completed_step=1000,event_step_is_preopen=True,first_post_open_completed_step=1001,post_open_frames=sum(int(r["completed_steps"])>1000 for r in rows),shared_original_states=209,new_forced_final_not_shared=True,n_times_dt_clock_used=False,physical_or_native_acceptance=False)

def context(ad):
 for p in(Path(__file__),NOTE,Path(base.__file__),base.NOTE,Path(base.old.__file__),Path(gpu.__file__),Path(c.__file__)):ad.pin(p)
 rp=L/(SOURCE+".run.json");ad.pin(rp);ref=c.read(rp)
 c.need(ref.get("stage")==base.STAGE+".run"and ref.get("passed")is True and ref["tag"]==SOURCE and(ref["configuration"],ref["scheme"],ref["mode"])==("Release","B","window2s")and ref["clock"]["completed_updates"]==199996 and ref["clock"]["native_frames"]==1263 and ref["clock"]["runtime_TimeMax_s"]==2.,"Actual completed P3 Release source required")
 build,prep,program,runtime=base.source_build(ad,{"build":ref["source_build"]},"Release")
 c.need((build,prep,program,runtime)==(ref["source_build"],ref["source_prepare"],ref["program"],ref["runtime"]),"Original P3 source/program/runtime binding changed")
 ad.pin(ref["root_admission"]["path"]);c.same(ref["root_admission"])
 for e in(ref["plan"],*ref["seed"]):ad.pin(e["path"]);c.same(e)
 for path,stage in((L/(SOURCE+".native_review_p3_r1.json"),"upl_tpi_p3_native_r1.review"),(L/"upl_tpi_p3_window_review_r1.check.json","upl_tpi_p3_window_review_r1")):
  ad.pin(path);d=c.read(path);c.need(d.get("stage")==stage and d.get("passed")is True,"Actual native/scientific prerequisite failed")
  if stage.endswith(".review"):c.need(d["job"]["tag"]==SOURCE and d["job"]["run_receipt"]==c.stat(rp),"Actual source native qualification differs")
  else:c.need(d.get("analysis_complete")is True and d.get("planned_budgets_passed")is True,"Original P3 accuracy gate must pass before a cost probe")
 nsys=ad.pin(NSYS)
 for which,args in(("version",["--version"]),("help",["profile","--help"])):
  path=L/("upl_tpi_p3_nsys_"+which+"_r1.call.json");ad.pin(path);d=c.read(path)
  c.need(d["stage"]=="upl_tpi_p3_nsys_"+which+"_r1"and d["passed"]is True and d["actual_Popen_wait_exit"]==d["actual_Win32_exit"]==0 and d["program"]==nsys and d["arguments"]==args,"Actual Nsight version/help tool evidence differs")
  ad.pin(d["log"]["path"]);c.same(d["log"])
 rows,clock=planned(ref);argv=list(ref["arguments"])
 c.need(argv.count(ref["output_directory"])==1 and argv.count("-nsteps:200000")==1 and not any(x.lower().startswith("-tmax")for x in argv),"Original argv has an unexpected override")
 argv[argv.index(ref["output_directory"])]=str(OUT);argv[argv.index("-nsteps:200000")]='-nsteps:2000'
 expected={k:None for k in(*base.ENV_KEYS,"OMP_NUM_THREADS","OMP_DYNAMIC")};expected.update(UPL_TPI_GPU_R1="B",UPL_TPI_M0_DT_R1="EQ40_RH1",UPL_TPI_P3_ROWS_R1="3")
 c.need(ref["actual_environment"]==expected,"Original six physical selectors/OMP environment differ")
 disk=shutil.disk_usage(T.anchor);minimum=ad.data.get("minimum_free_bytes")
 if minimum is not None:c.need(isinstance(minimum,int)and minimum>0 and disk.free>=minimum,"Root disk budget failed; no automatic cleanup")
 return dict(tag=JOB,mode="performance_probe2000",window="performance_probe2000",configuration="Release",scheme="B",source_run=c.stat(rp),source_build=build,source_prepare=prep,program=program,runtime=runtime,seed=ref["seed"],source_plan=ref["plan"],input_prefix=ref["input_prefix"],output_directory=str(OUT),data=str(OUT/"data"),arguments=argv,clock=clock,rows=rows,actual_environment=expected,nsys=nsys,report_directory=str(REPORTDIR),report_prefix=str(REPORT),paths=PATHS,memcheck_program=None,disk_space_before=dict(total=disk.total,used=disk.used,free=disk.free,minimum_free_bytes=minimum),performance_only=True,source_TimeMax_unchanged=True)

def before_processes(ad):
 import psutil
 ad.pin(psutil.__file__);observed=[];allowed=ad.data.get("allowed_paused_gpu_processes",[])
 c.need(len(allowed)<=1,"At most the original exact paused C08 target may remain")
 for p in psutil.process_iter(["pid","name","exe","cmdline","create_time","status"]):
  name=(p.info["name"]or"").lower()
  if name.startswith("dualsphysics"):
   observed.append(p.info);matches=[x for x in allowed if x["pid"]==p.info["pid"]and x["created"]==p.info["create_time"]and Path(x["exe"]).resolve()==Path(p.info["exe"]).resolve()and x["argv"]==p.info["cmdline"]]
   c.need(len(matches)==1 and p.info["status"]==psutil.STATUS_STOPPED,"Existing/unowned active solver; never stop or replace it")
  c.need(name!="nsys.exe","Another Nsight Systems CLI is active; do not duplicate it")
 return observed

def live_target(k,tool,ctx,call):
 import psutil
 for p in psutil.process_iter(["pid","exe","cmdline"]):
  if not p.info["exe"]or Path(p.info["exe"]).resolve()!=Path(ctx["program"]["path"]).resolve()or not p.info["cmdline"]or p.info["cmdline"][1:]!=ctx["arguments"]:continue
  h=k.OpenProcess(0x100000|0x1000,False,p.pid);c.need(h and k.GetProcessId(h)==p.pid,"Matching target native handle could not be captured")
  try:
   c.need(k.WaitForSingleObject(h,0)==258,"Target exited before its native handle was captured live")
   info=c.identity(p.pid);ticks=gpu.creation(k,h)
   call["candidate_target_observation"]=dict(identity=info,native_creation_FILETIME_ticks=ticks,captured_while_live=True,ownership_verified=False)
   c.need(Path(info["exe"]).resolve()==Path(ctx["program"]["path"]).resolve()and info["argv"][1:]==ctx["arguments"],"Re-read target executable/argv differs after native handle capture")
   c.need(abs((ticks-116444736000000000)/1e7-info["created"])<=1e-6,"Native/observed target creation differs")
   chain=[info]
   for parent in p.parents():
    chain.append(c.identity(parent.pid))
    if chain[-1]["pid"]==tool["pid"]:break
   call["candidate_ancestry"]=chain
   c.need(len(chain)>=2 and chain[-1]==tool,"Matching target ancestry cannot be proven to this exact Nsight owner")
   for child,parent in zip(chain,chain[1:]):c.need(child["parent"]==parent["pid"]and parent["created"]<=child["created"]+1e-6,"Actual multi-layer ancestry has a reused or reversed identity")
   call["candidate_target_observation"]["ownership_verified"]=True
   return info,h,ticks,chain
  except Exception:k.CloseHandle(h);raise
 return None

def owned_probe(ad,ctx,result):
 import psutil
 result["processes_before"]=before_processes(ad);env=os.environ.copy()
 for key,value in ctx["actual_environment"].items():
  env.pop(key,None)
  if value is not None:env[key]=value
 argv=[ctx["nsys"]["path"],*FLAGS,"--output",str(REPORT),ctx["program"]["path"],*ctx["arguments"]]
 owner=c.identity(os.getpid());k=gpu.kernel_api();tool_handle=c.wt.HANDLE();target_handle=None;p=None;first=None;wait_failures=[];start=time.perf_counter()
 call=dict(stage=TAG+".call",owner=owner,program=ctx["nsys"],target_program=ctx["program"],arguments=argv[1:],target_arguments=ctx["arguments"],cwd=str(S),actual_environment=ctx["actual_environment"],started_utc=c.now(),actual_Popen_wait_exit=None,actual_Win32_exit=None,target_actual_Win32_exit=None,passed=False,tool_is_solver=False,performance_only=True)
 try:
  ad.finish()
  with PATHS["log"].open("xb")as stream:
   p=subprocess.Popen(argv,cwd=S,env=env,stdout=stream,stderr=subprocess.STDOUT,shell=False,creationflags=subprocess.CREATE_NO_WINDOW)
   current=k.GetCurrentProcess();c.need(k.DuplicateHandle(current,c.wt.HANDLE(int(p._handle)),current,ctypes.byref(tool_handle),0,False,2),"Original Nsight handle duplication failed")
   tool=c.identity(p.pid);ticks=gpu.creation(k,tool_handle)
   c.need(tool["parent"]==owner["pid"]and tool["argv"][1:]==argv[1:]and Path(tool["exe"]).resolve()==NSYS.resolve()and abs((ticks-116444736000000000)/1e7-tool["created"])<=1e-6,"Actual Nsight tool identity/argv/native creation differs")
   call.update(child=tool,tool_creation_FILETIME_ticks=ticks,tool_handle_acquired_before_wait=True)
   c.write_new(PATHS["tool_start"],dict(stage=TAG+".tool.start",owner=owner,child=tool,program=ctx["nsys"],root_admission=ad.entry,performance_only=True))
   found=None
   while found is None:
    found=live_target(k,tool,ctx,call)
    if found is not None:break
    c.need(p.poll()is None,"Nsight exited before a genuine live target/ancestry could be captured")
    time.sleep(.01)
   target,target_handle,targetticks,chain=found
   c.need(targetticks>=ticks,"Profiled target predates this Nsight invocation")
   call.update(target=target,target_creation_FILETIME_ticks=targetticks,target_handle_acquired_while_live=True,target_ancestry=chain)
   # Ownership/handle are retained even if a later environment audit fails.
   actual=psutil.Process(target["pid"]).environ();targetenv={key:actual.get(key)for key in ctx["actual_environment"]}
   call["actual_target_environment"]=targetenv
   c.need(targetenv==ctx["actual_environment"],"Actual profiled target selector inheritance differs")
   c.write_new(PATHS["start"],dict(stage=TAG+".start",owner=owner,tool=tool,target=target,target_ancestry=chain,program=ctx["program"],source_build=ctx["source_build"],source_run=ctx["source_run"],arguments=ctx["arguments"],input_prefix=ctx["input_prefix"],output_directory=ctx["output_directory"],plan=ctx["plan"],clock=ctx["clock"],actual_environment=ctx["actual_environment"],actual_target_environment=targetenv,root_admission=ad.entry,performance_only=True))
   # Wait the proven target even if Nsight exits first. Never stop a live process.
   c.need(k.WaitForSingleObject(target_handle,0xFFFFFFFF)==0,"Actual owned target wait failed")
   call["target_actual_Win32_exit"]=gpu.native_exit(k,target_handle);call["actual_Popen_wait_exit"]=p.wait()
 except Exception as exc:first=str(exc)
 finally:
  if target_handle:
   try:
    c.need(k.WaitForSingleObject(target_handle,0xFFFFFFFF)==0,"Preserved owned target wait failed");call["target_actual_Win32_exit"]=gpu.native_exit(k,target_handle)
   except Exception as exc:wait_failures.append(str(exc))
   k.CloseHandle(target_handle)
  if p is not None:
   try:call["actual_Popen_wait_exit"]=p.wait()
   except Exception as exc:wait_failures.append(str(exc))
  if tool_handle:
   try:call["actual_Win32_exit"]=gpu.native_exit(k,tool_handle)
   except Exception as exc:wait_failures.append(str(exc))
   k.CloseHandle(tool_handle)
  call.update(ended_utc=c.now(),wall_seconds_including_profile_and_exports=time.perf_counter()-start,failure=first,wait_failures=wait_failures,passed=first is None and not wait_failures and call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==call["target_actual_Win32_exit"]==0)
  if PATHS["log"].exists():call["log"]=c.stat(PATHS["log"])
  c.write_new(PATHS["call"],call);result.update(call=c.stat(PATHS["call"]),tool_invocations=int(p is not None),solver_invocations=1 if isinstance(call.get("target"),dict)else(None if p is not None else 0),actual_Popen_wait_exit=call["actual_Popen_wait_exit"],actual_Win32_exit=call["actual_Win32_exit"],target_actual_Win32_exit=call["target_actual_Win32_exit"],tool=call.get("child"),target=call.get("target"),target_ancestry=call.get("target_ancestry"))
 c.need(call["passed"],first or"Actual Nsight/target failed; preserve outputs and independent exits")

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");a=ap.parse_args()
 c.need(a.execution_authorized,"Root must independently read and admit this one short profiling action")
 c.need(not OUT.exists()and not REPORTDIR.exists()and not PLAN.exists()and not any(q.exists()for q in PATHS.values()),"Existing job/report/partial protected; no retry")
 ad=ctx=None;result=dict(stage=TAG+".run",tag=JOB,passed=False,failure=None,performance_only=True,physical_acceptance=False,native_acceptance=False,trace_capture_verified=False,trace_review_pending=True,solver_invocations=0,tool_invocations=0,native_invocations=0,VTK_invocations=0,build_invocations=0,Git_invocations=0,SHA_scans=0,automatic_follow_up=False,old_process_stopped_resumed_or_restarted=False)
 try:
  ad=Admission(a.admission);result["root_admission"]=ad.entry;ctx=context(ad)
  with PLAN.open("x",encoding="utf-8",newline="")as f:
   w=csv.DictWriter(f,fieldnames=c.HEADER);w.writeheader();w.writerows(ctx.pop("rows"))
  ctx["plan"]=c.stat(PLAN);REPORTDIR.mkdir();result.update({k:v for k,v in ctx.items()if k!="paths"});result["root_admission"]=ad.entry
  owned_probe(ad,ctx,result);result["runtime_summary_only"]=base.check_output(ctx)
  report=REPORT.with_suffix(".nsys-rep");c.need(report.is_file()and report.stat().st_size>0,"Nsight returned without a complete report container; no automatic replay")
  result.update(passed=True,report=c.stat(report),profile_artifacts=[c.stat(q)for q in REPORTDIR.rglob("*")if q.is_file()],actual_CUDA_event_capture_or_stats_not_yet_reviewed=True,shared209_native_bytes_not_compared=True,new_forced_final_not_a_source_shared_state=True,TSimul_or_walltime_extrapolation_forbidden=True)
 except Exception as exc:result["failure"]=str(exc)
 finally:
  if ctx is not None:
   try:
    result.update(c.terminal_evidence(ctx))
    for e in(ctx["source_plan"],*ctx["seed"]):c.same(e)
    result["source_inputs_unchanged"]=True
   except Exception as exc:result.update(passed=False,terminal_audit_failure=str(exc))
  if ad is not None:
   try:result["consumed"]=ad.finish();result["consumed_stats_unchanged"]=True
   except Exception as exc:result.update(passed=False,consumed_stats_unchanged=False,terminal_stat_failure=str(exc))
  c.write_new(PATHS["run"],result);c.write_new(PATHS["status"],dict(stage=TAG+".status",passed=result["passed"],state="runtime_passed_trace_review_pending"if result["passed"]else"failed_preserved",run=c.stat(PATHS["run"]),performance_only=True))
 print(c.json.dumps(dict(passed=result["passed"],tag=JOB,failure=result["failure"],trace_review_pending=True),ensure_ascii=False));return 0 if result["passed"]else 1
if __name__=="__main__":raise SystemExit(main())
