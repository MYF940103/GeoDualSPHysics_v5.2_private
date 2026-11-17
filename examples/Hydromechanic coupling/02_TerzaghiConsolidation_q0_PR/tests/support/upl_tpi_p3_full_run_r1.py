"""One honest fresh P3 full2Tv GPU owner; never launch a reader or following solve."""
from __future__ import annotations
import argparse,csv,os,re,subprocess
from pathlib import Path
import upl_tpi_p3_run_r1 as p3
import upl_tpi_p3_full_plan_r1 as planmod
c,gpu=p3.c,p3.gpu;T,L,S=p3.T,p3.L,p3.S
STAGE="upl_tpi_p3_full_run_r1";NOTE=T/"notes"/(STAGE+".md");ROOT_THREAD=p3.ROOT_THREAD
TAG="upl_tpi_p3_B10us_full2tv_GPU_r1";PREP=L/"upl_tpi_p3_full_plan_r1.prepare.json"
REFERENCE=L/"upl_tpi_p3_B10us_window2s_GPU_r1.run.json"
PROTECTION=L/"upl_tpi_p3_B10us_window2s_GPU_r1.run_admission.json"
PROOFS={"build_root":("upl_tpi_p3_full_build_root_r1.review.json","upl_tpi_p3_full_build_root_r1"),"plan_root":("upl_tpi_p3_full_plan_root_r1.review.json","upl_tpi_p3_full_plan_root_r1"),"short":("upl_tpi_p3_full_short_r1.check.json","upl_tpi_p3_full_short_r1.summary"),"reader_root":("upl_tpi_m0_full10us_native_root_r1.review.json","upl_tpi_m0_full10us_native_root_r1"),"window_science":("upl_tpi_p3_window_review_r1.check.json","upl_tpi_p3_window_review_r1")}
class Admission(c.Admission):
 def __init__(self,path):
  self.entry,self.data=c.stat(path),c.read(path);self.consumed={}
  c.need(self.data.get("stage")==STAGE+".run_admission"and self.data.get("passed")is True and self.data.get("one_job_only")is True and self.data.get("notification_required")is True,"One root-reviewed full-only owner admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};c.need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")

def passed_proofs(ad):
 for p in(Path(__file__),NOTE,Path(p3.__file__),p3.NOTE,Path(p3.old.__file__),Path(gpu.__file__),Path(c.__file__),Path(planmod.__file__),planmod.NOTE):ad.pin(p)
 declared={str(Path(e["path"]).resolve()):e for e in ad.data["required_passed_checks"]};proof={}
 for role,(name,stage)in PROOFS.items():
  path=L/name;c.need(str(path.resolve())in declared,"Missing required full admission proof: "+role);entry=ad.pin(path);c.same(declared[str(path.resolve())]);value=c.read(path)
  c.need(value.get("stage")==stage and value.get("passed")is True,"Required real root proof failed: "+role);proof[role]=dict(entry=entry,value=value)
 s=proof["window_science"]["value"];c.need(s.get("analysis_complete")is True and s.get("planned_budgets_passed")is True and s.get("all_original_target_budgets_passed")is True and s.get("all_new_post01_100Pa_guards_passed")is True,"Original P3 2s physical budgets must pass without exemptions")
 return proof

def source_builds(ad,proof):
 rows=proof["build_root"]["value"]["configurations"];c.need(len(rows)==4 and {r["configuration"]for r in rows}=={"DebugCPU","ReleaseCPU","Debug","Release"},"Root must review all four genuine new full builds")
 answer={}
 for cfg in("DebugCPU","ReleaseCPU","Debug","Release"):
  rootrow=next(r for r in rows if r["configuration"]==cfg);path=L/("upl_tpi_p3_full_"+cfg+"_r1.build.json");entry=ad.pin(path);c.same(rootrow["build"]);c.need(entry==rootrow["build"],"Root build/configuration identity differs");d=c.read(path)
  backend="CPU"if cfg.endswith("CPU")else"GPU";count=86 if backend=="CPU"else 111
  c.need(d.get("stage")=="upl_tpi_p3_full_build_r1"and d.get("passed")is True and d.get("configuration")==cfg and d.get("consumed_stats_unchanged")is True and d.get("object_count")==count and d.get("replacement_object_count")==1 and d.get("retained_effective_object_count")==count-1 and d.get("compile_invocations")==d.get("link_invocations")==1 and d.get("new_CUDA_compile_invocations")==0,"Exact one-Single actual full build required")
  for e in d["calls"]:
   ad.pin(e["path"]);c.same(e);a=c.read(e["path"]);c.need(a.get("passed")is True and a.get("actual_Popen_wait_exit")==a.get("actual_Win32_exit")==0,"Actual full build tool exit failed")
  pe=d["source_prepare"];ad.pin(pe["path"]);c.same(pe);q=c.read(pe["path"]);label="upl_tpi_p3_full_"+backend+"_r1";cls="JSphCpu"if backend=="CPU"else"JSphGpu"
  c.need(Path(pe["path"]).resolve()==(L/(label+".prepare.json")).resolve()and q.get("stage")=="upl_tpi_p3_full_source_r1.prepare"and q.get("passed")is True and q.get("backend")==backend and q.get("consumed_stats_unchanged")is True and q["changed_sources"]==q["recompile_sources"]==[cls+"Single.cpp"]and q["changed_headers"]==[]and q["full_scope"]["TimeMax"]==planmod.CAP and q["full_scope"]["NstepsBreak"]==planmod.STEPS and q["full_scope"]["dt_event_divisor"]==1000 and q["full_scope"]["required_scheme"]=="B"and q["full_scope"]["required_endpoint_defect_rounds"]==3,"New full qualifier source contract differs")
  c.need(q["numerical_formula_changed"]is False and q["public_class_or_virtual_ABI_changed"]is False and q["CUDA_source_and_cuh_byte_identical"]and q["all_headers_and_helpers_byte_identical"]and q["original_short_M0_TimeMax_le_2_expression_retained"]and q["non_M0_time_arm_retained"],"New full build changed physics, shared ABI or old qualification")
  source=Path(q["source_root"]);byname={Path(e["path"]).name:e for e in q["files"]};c.need(source.resolve()==(T/"outputs"/(label+"_source")).resolve()and len(byname)==(267 if backend=="CPU"else 270),"Actual full source inventory differs")
  for name in(cls+"Single.cpp","JSph.h","upl_tpi_m0_dt_r2.h","upl_tpi_cpu_r1.h"if backend=="CPU"else"upl_tpi_gpu_r1.h"):ad.pin(byname[name]["path"]);c.same(byname[name])
  program=ad.pin(d["program"]["path"]);c.same(d["program"]);c.need(program==rootrow["program"],"Root reviewed a different full executable")
  runtime=[]
  for e in d["runtime"]:runtime.append(ad.pin(e["destination"]["path"]));c.same(e["destination"])
  answer[cfg]=dict(build=entry,prepared=pe,program=program,runtime=runtime)
 return answer

def reader_ready(ad,proof):
 path=L/"upl_tpi_m0_full10us_native_r1.build.json";entry=ad.pin(path);d=c.read(path);root=proof["reader_root"]["value"]
 c.need(d.get("stage")=="upl_tpi_m0_full10us_native_r1.build"and d.get("passed")is True and d.get("private_offline_reader")is True and d.get("reader_invocations")==d.get("solver_invocations")==0 and root["build"]==entry and root["body_predicates_bytewise_retained_from_M0"]and root["only_declared_full_profile_CLI_completion_label_changed"],"Actual exact full10us reader must be ready before full solve")
 program=ad.pin(d["program"]["path"]);c.same(d["program"]);c.need(program==root["program"]and Path(program["path"]).name=="upl_tpi_m0_full10us_native_r1.exe","Root full reader identity differs")
 for e in d["runtime"]:ad.pin(e["destination"]["path"]);c.same(e["destination"])
 for e in d["calls"]:
  ad.pin(e["path"]);c.same(e);a=c.read(e["path"]);c.need(a.get("passed")is True and a.get("actual_Popen_wait_exit")==a.get("actual_Win32_exit")==0,"Actual reader build tool failed")
 return dict(build=entry,root_review=proof["reader_root"]["entry"],program=program,reader_invocations_by_owner=0)

def paused_protection(ad):
 ad.pin(PROTECTION);old=c.read(PROTECTION);allowed=ad.data["allowed_paused_gpu_processes"]
 c.need(allowed==old["allowed_paused_gpu_processes"]and len(allowed)==1 and allowed[0]["status"]=="stopped"and "08_LianSaturatedColumnCollapse_u_pl"in allowed[0]["exe"],"Original C08 paused identity must be explicitly protected, not replaced")
 import psutil
 ad.pin(psutil.__file__);seen=[]
 for expected in allowed:
  ad.pin(expected["exe"]);p=psutil.Process(expected["pid"]);actual=c.identity(p.pid)
  c.need(actual["pid"]==expected["pid"]and actual["created"]==expected["created"]and Path(actual["exe"]).resolve()==Path(expected["exe"]).resolve()and actual["argv"]==expected["argv"]and actual["parent"]==expected["parent"]and p.status()==psutil.STATUS_STOPPED,"Protected C08 owner identity/status changed; never resume/stop/restart it")
  seen.append(actual)
 return dict(reference_admission=c.stat(PROTECTION),observed=seen,observed_stopped=True,no_process_action_performed=True)

def context(ad):
 j=ad.data["job"];c.need((j["tag"],j["mode"],j["configuration"],j["scheme"])==(TAG,"full2tv","Release","B"),"Only the one explicitly admitted fresh full P3 GPU B job is supported")
 proof=passed_proofs(ad);builds=source_builds(ad,proof);selected=builds["Release"];c.need({k:j["build"][k]for k in("path","bytes","mtime_ns")}==selected["build"],"Job selected a different full Release program build")
 reader=reader_ready(ad,proof);ad.pin(PREP);prep=c.read(PREP);pr=proof["plan_root"]["value"]
 c.need(prep.get("stage")==planmod.TAG+".prepare"and prep.get("passed")is True and prep.get("consumed_stats_unchanged")is True and prep.get("XML_only_TimeMax_value_changed")is True and prep.get("XML_comments_and_all_other_bytes_retained")is True and pr["prepare"]==c.stat(PREP)and pr["clock"]==prep["clock"]and pr["plan"]==prep["plan"]and pr["shared_plan_records"]==1262,"Actual root-reviewed full input/clock preparation required")
 for e in[prep["config"],prep["plan"],*prep["seed"]]:ad.pin(e["path"]);c.same(e)
 c.need(prep["input_prefix"]==str(planmod.PREFIX)and prep["plan"]["path"]==str(planmod.PLAN),"Unexpected full input/plan namespace")
 clock=prep["clock"];c.need(clock["completed_updates"]==7288262 and clock["native_frames"]==1653 and c.bits(clock["actual_fixed_dt_s"])==c.bits(planmod.DT)and c.bits(clock["actual_scalar_end_s"])==c.bits(planmod.END)and clock["post_open_frames"]==1549 and clock["expected_true_drained_receivers"]==15490 and clock["event_completed_step"]==1000 and clock["event_step_is_preopen"]is True and clock["n_times_dt_clock_used"]is False,"Exact scalar full2Tv profile differs")
 rows=planmod.actual_plan(planmod.SEGMENTS)
 with Path(prep["plan"]["path"]).open(encoding="utf-8-sig",newline="")as f:
  readercsv=csv.DictReader(f);saved=list(readercsv);c.need(readercsv.fieldnames==planmod.HEADER and len(saved)==1653,"Actual eight-column full plan differs")
 for a,b in zip(saved,rows):c.need(all(c.bits(float(a[k]))==c.bits(float(b[k]))for k in planmod.HEADER),"Actual full scalar target-crossing table differs")
 ad.pin(REFERENCE);ref=c.read(REFERENCE);c.need(ref["stage"]=="upl_tpi_p3_run_r1.run"and ref["passed"]and(ref["mode"],ref["scheme"],ref["configuration"])==("window2s","B","Release"),"Original real P3 short argv source differs")
 out=T/"outputs"/TAG;paths={k:L/(TAG+s)for k,s in(("start",".start.json"),("tool_start",".tool.start.json"),("call",".call.json"),("run",".run.json"),("status",".status.json"),("log",".log"),("memcheck",".memcheck.log"))}
 c.need(not out.exists()and all(not q.exists()for q in paths.values())and not any((L/(TAG+s)).exists()for s in(".terminal.json",".queue_attempt.json",".queue_result.json")),"Existing full run/failed/partial/notification outputs protected")
 argv=list(ref["arguments"])
 for original,replacement in[(ref["input_prefix"],prep["input_prefix"]),(ref["output_directory"],str(out)),("-nsteps:200000","-nsteps:7288262")]:c.need(argv.count(original)==1,"Unique old argv item required");argv[argv.index(original)]=replacement
 protected=paused_protection(ad)
 return dict(tag=TAG,mode="full2tv",window="full2tv",configuration="Release",scheme="B",program=selected["program"],source_build=selected["build"],source_prepare=selected["prepared"],runtime=selected["runtime"],all_full_builds=builds,full_plan_prepare=c.stat(PREP),reference_run=c.stat(REFERENCE),readiness_evidence={k:v["entry"]for k,v in proof.items()},reader_ready=reader,protected_paused_before=protected,clock=clock,plan=prep["plan"],seed=prep["seed"],input_prefix=prep["input_prefix"],original_input_prefix=ref["input_prefix"],output_directory=str(out),data=str(out/"data"),arguments=argv,memcheck_program=None,paths=paths,required_runtime_markers=[],GenCase_invocations=0,PART_restart=False,pressure_history_cold_start=True,event_divisor=1000,policy_environment="EQ40_RH1",load_clock_environment="absent",pressure_rows_environment="3",planned_full_diagnostic=True,physical_acceptance=False)

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
    msg=("Authorized same-thread C02 P3 full2Tv terminal. tag="+tag+" event="+event+". "
         "Read original start/call/run/status/terminal/queue_attempt, actual owned exits and program/source/input/plan bindings first. "
         "This is one fresh B10us full2Tv diagnostic with7288262updates/1653planned frames/end72.88428815806371s. Exit0 is pending native and physical review only. "
         "Check existing/active readers before a separately root-admitted unique full-profile read; only1262actual short states may share, never old forced-final.  Preserve all 1040 IDs,22 typed arrays,scalar clocks,signed intervals,ledger,drainage,HG and all three P3 pressure rounds/five-phase dt guards. "
         "No automatic decoder,next solver,half,reference,retry or other case. Preserve first real failure and last raw console; invent no unsaved state. "
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


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--notify-admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");args=ap.parse_args();c.need(args.execution_authorized,"Root-reviewed one-full-job execution flag required")
 ad=ctx=profile=None;result=dict(stage=STAGE+".run",passed=False,failure=None,solver_invocations=0,native_invocations=0,VTK_invocations=0,build_invocations=0,Git_invocations=0,SHA_scans=0,physical_acceptance=False,automatic_follow_up=False,old_process_stopped_resumed_or_restarted=False)
 try:
  ad=Admission(args.admission);profile=notification(ad,args.notify_admission);c.need(profile is not None,"The full direct owner requires one terminal completion admission");ctx=context(ad)
  result.update({k:v for k,v in ctx.items()if k!="paths"});result["root_admission"]=ad.entry;result["actual_owner_implementation"]=ad.pin(Path(p3.__file__))
  for e in[*ctx["seed"],ctx["plan"]]:c.same(e)
  p3.run_owned(ad,ctx,result);result.update(p3.check_output(ctx));result.update(passed=True,full2Tv_solver_summary_completed=True,native_and_physical_review_pending=True)
 except Exception as exc:result["failure"]=str(exc)
 finally:
  if ctx is not None:
   try:
    result.update(c.terminal_evidence(ctx));result["protected_paused_after"]=paused_protection(ad)
    for e in[*ctx["seed"],ctx["plan"]]:c.same(e)
    result["reused_immutable_seed_and_plan_stats_unchanged"]=True;result["consumed"]=ad.finish()
   except Exception as exc:result.update(passed=False,terminal_audit_failure=str(exc))
   c.write_new(ctx["paths"]["run"],result);c.write_new(ctx["paths"]["status"],dict(stage=TAG+".status",passed=result["passed"],run=c.stat(ctx["paths"]["run"]),state="pending_native_review"if result["passed"]else"failed_preserved"))
   notify_once(ctx,result,profile)
  print(c.json.dumps(dict(passed=result["passed"],tag=result.get("tag"),failure=result["failure"]),ensure_ascii=False))
 return 0 if result["passed"]else 1
if __name__=="__main__":raise SystemExit(main())
