"""One honest P3 full-scope short regression, or a separate three-review summary."""
from __future__ import annotations
import argparse,csv,re
from pathlib import Path
import upl_tpi_p3_run_r1 as original

c,gpu,T,L,S=original.c,original.gpu,original.T,original.L,original.S
STAGE="upl_tpi_p3_full_short_r1";NOTE=T/"notes"/(STAGE+".md")
NATIVE_STAGE="upl_tpi_p3_full_short_native_r1.review"
ENV_KEYS=original.ENV_KEYS
REFERENCES={
 "cpu_debug2ms":("DebugCPU","B","upl_tpi_p3_cpu_debug2ms_r1",200,18,"upl_tpi_p3_full_cpu_debug2ms_r1"),
 "debug2":("Debug","B","upl_tpi_p3_gpu_debug2_r1",2,2,"upl_tpi_p3_full_gpu_debug2_r1"),
 "Acontrol":("Release","A","upl_tpi_p3_Acontrol_gpu_r1",320,18,"upl_tpi_p3_full_Acontrol_gpu_r1"),
}

class Admission(c.Admission):
 def __init__(self,path,phase):
  self.entry,self.data=c.stat(path),c.read(path);self.consumed={}
  c.need(self.data.get("stage")==STAGE+"."+phase+"_admission"and self.data.get("passed")is True and self.data.get("action_only")is True,"One separately admitted short-regression action required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};c.need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")
  for p in(Path(__file__),NOTE,Path(original.__file__),original.NOTE,Path(original.old.__file__),Path(gpu.__file__),Path(c.__file__)):self.pin(p)

def source_build(ad,job,cfg):
 backend="CPU"if cfg=="DebugCPU"else"GPU";cls="JSphCpu"if backend=="CPU"else"JSphGpu"
 bp=L/("upl_tpi_p3_full_"+cfg+"_r1.build.json");c.need(Path(job["build"]["path"]).resolve()==bp.resolve(),"Exact new full-scope configuration build required")
 be=ad.pin(bp);c.same(job["build"]);built=c.read(bp)
 c.need(built.get("stage")=="upl_tpi_p3_full_build_r1"and built.get("passed")is True and built.get("configuration")==cfg and built.get("consumed_stats_unchanged")is True and built.get("replacement_object_count")==1 and built.get("retained_effective_object_count")== (85 if backend=="CPU"else 110)and built.get("object_count")== (86 if backend=="CPU"else 111)and built.get("new_CUDA_compile_invocations")==0,"Genuine one-Single-TU full-scope build required")
 pe=built["source_prepare"];expected=L/("upl_tpi_p3_full_"+backend+"_r1.prepare.json");c.need(Path(pe["path"]).resolve()==expected.resolve(),"New build is not bound to selected full-scope source")
 ad.pin(expected);c.same(pe);prep=c.read(expected);root=T/"outputs"/("upl_tpi_p3_full_"+backend+"_r1_source")
 c.need(prep.get("stage")=="upl_tpi_p3_full_source_r1.prepare"and prep.get("passed")is True and prep.get("backend")==backend and Path(prep["source_root"]).resolve()==root.resolve()and len(prep["files"])==(267 if backend=="CPU"else 270)and prep["changed_sources"]==prep["recompile_sources"]==[cls+"Single.cpp"]and prep["changed_headers"]==[]and prep.get("consumed_stats_unchanged")is True,"Actual new full-scope source identity differs")
 for key in("other_base_files_byte_identical","all_headers_and_helpers_byte_identical","CUDA_source_and_cuh_byte_identical","original_short_M0_TimeMax_le_2_expression_retained","non_M0_time_arm_retained","only_M0_qualification_time_domain_extended"):c.need(prep.get(key)is True,"Full-scope source proof missing: "+key)
 c.need(prep.get("numerical_formula_changed")is False and prep.get("public_class_or_virtual_ABI_changed")is False and prep.get("shared_device_structures_or_inline_tokens_changed")is False,"Equations or shared ABI changed")
 fs=prep["full_scope"];c.need(fs["TimeMax"]==72.88428690075874 and fs["NstepsBreak"]==7288262 and fs["dt_event_divisor"]==1000 and fs["required_scheme"]=="B"and fs["required_endpoint_defect_rounds"]==3,"Exact M0/P3 full-scope expression differs")
 byname={Path(e["path"]).name:e for e in prep["files"]}
 for name in(cls+".cpp",cls+"Single.cpp","upl_tpi_cpu_r1.h"if backend=="CPU"else"upl_tpi_gpu_r1.h","upl_tpi_m0_dt_r2.h"):
  ad.pin(root/name);c.same(byname[name])
 for e in(prep["base_prepare"],prep["source_diff"],built["base_build"]):ad.pin(e["path"]);c.same(e)
 program=ad.pin(built["program"]["path"]);c.same(built["program"]);runtime=[]
 for e in built["runtime"]:runtime.append(ad.pin(e["destination"]["path"]));c.same(e["destination"])
 return be,c.stat(expected),program,runtime

def context(ad):
 j=ad.data["job"];mode=j["mode"];c.need(mode in REFERENCES,"Only the three minimal short regression profiles are allowed")
 cfg,scheme,reference,steps,frames,tag=REFERENCES[mode]
 c.need(j["tag"]==tag and j["configuration"]==cfg and j["scheme"]==scheme,"Exact new profile/tag required")
 build,prepared,program,runtime=source_build(ad,j,cfg)
 rp=L/(reference+".run.json");re=ad.pin(rp);ref=c.read(rp)
 c.need(ref.get("stage")==original.STAGE+".run"and ref.get("passed")is True and(ref["mode"],ref["configuration"],ref["scheme"])==(mode,cfg,scheme)and ref.get("solver_invocations")==1 and ref.get("PART_restart")is False and ref["clock"]["completed_updates"]==steps and ref["clock"]["native_frames"]==frames,"Exact genuine original P3 short control required")
 nr=L/(reference+".native_review_p3_r1.json");ne=ad.pin(nr);review=c.read(nr)
 c.need(review.get("stage")=="upl_tpi_p3_native_r1.review"and review.get("passed")is True and review["job"]["run_receipt"]==re,"Exact original independent P3 native qualification required")
 for e in(ref["plan"],*ref["seed"]):ad.pin(e["path"]);c.same(e)
 root=original.old.ET.fromstring(Path(ref["input_prefix"]+".xml").read_text(encoding="utf-8-sig"));w=ref["clock"]
 rows,clock=original.old.plan(root,w["actual_fixed_dt_s"],w["runtime_TimeMax_s"],w["nsteps_upper_cap"],w["event_completed_step"])
 c.need(clock==w,"Original short scalar-clock declaration differs")
 with Path(ref["plan"]["path"]).open(encoding="utf-8-sig",newline="")as f:
  reader=csv.DictReader(f);saved=list(reader);c.need(reader.fieldnames==c.HEADER and len(saved)==frames,"Original eight-column short clock shape differs")
 for row,expected in zip(saved,rows):c.need(all(c.bits(float(row[k]))==c.bits(float(expected[k]))for k in c.HEADER),"Original actual short-clock rows differ")
 prior_modes=set();checks=[]
 for e in ad.data.get("required_passed_checks",[]):
  entry=ad.pin(e["path"]);c.same(e);v=c.read(e["path"]);c.need(v.get("stage")==NATIVE_STAGE and v.get("passed")is True,"New short native prerequisite failed or has wrong identity")
  prior_modes.add(v["job"]["mode"]);checks.append(entry)
 required={"cpu_debug2ms":set(),"debug2":{"cpu_debug2ms"},"Acontrol":{"cpu_debug2ms","debug2"}}[mode]
 c.need(required<=prior_modes,"Separately completed earlier new-short native gates missing")
 paths={k:L/(tag+s)for k,s in(("start",".start.json"),("tool_start",".tool.start.json"),("call",".call.json"),("run",".run.json"),("status",".status.json"),("log",".log"),("memcheck",".memcheck.log"))};out=T/"outputs"/tag
 c.need(not out.exists()and all(not p.exists()for p in paths.values())and not any((L/(tag+s)).exists()for s in(".terminal.json",".queue_attempt.json",".queue_result.json")),"Existing job/failure/partial protected")
 argv=list(ref["arguments"]);c.need(argv.count(ref["output_directory"])==1,"Original output argv not unique");argv[argv.index(ref["output_directory"])]=str(out)
 mem=ad.pin(j["memcheck_program"]["path"])if cfg=="Debug"else None
 if mem:c.need(Path(mem["path"]).name.lower()=="compute-sanitizer.exe","Genuine memcheck tool required")
 return dict(tag=tag,mode=mode,window=mode,configuration=cfg,scheme=scheme,program=program,source_build=build,source_prepare=prepared,runtime=runtime,reference_run=re,reference_native_review=ne,prerequisite_reviews=checks,clock=clock,plan=ref["plan"],seed=ref["seed"],input_prefix=ref["input_prefix"],original_input_prefix=ref["input_prefix"],output_directory=str(out),data=str(out/"data"),arguments=argv,memcheck_program=mem,paths=paths,required_runtime_markers=[],GenCase_invocations=0,PART_restart=False,pressure_history_cold_start=True,event_divisor=1600 if scheme=="A"else 1000,policy_environment="absent"if scheme=="A"else"EQ40_RH1",load_clock_environment="absent",pressure_rows_environment="absent"if scheme=="A"else"3",source_full_completed=False,implementation_regression_only=True,ReleaseCPU_runtime_test_claimed=False,Release_B_short_bit_equivalence_claimed=False)

def run_one(ad):
 ctx=None;result=dict(stage=STAGE+".run",passed=False,failure=None,solver_invocations=0,native_invocations=0,VTK_invocations=0,build_invocations=0,Git_invocations=0,SHA_scans=0,queue_invocations=0,physical_acceptance=False,automatic_follow_up=False,old_process_stopped_resumed_or_restarted=False)
 try:
  ctx=context(ad);result.update({k:v for k,v in ctx.items()if k!="paths"});result["root_admission"]=ad.entry
  for e in[*ctx["seed"],ctx["plan"]]:c.same(e)
  # These functions have context-tagged owner/call/start evidence and no fixed
  # P3 source/build identity. Never call original context/source_build/main.
  (original.own_solver if ctx["configuration"]=="DebugCPU"else original.run_owned)(ad,ctx,result)
  result.update(original.check_output(ctx));result["passed"]=True
 except Exception as exc:result["failure"]=str(exc)
 finally:
  if ctx is not None:
   try:
    result.update(c.terminal_evidence(ctx))
    for e in[*ctx["seed"],ctx["plan"]]:c.same(e)
    result["reused_immutable_seed_and_plan_stats_unchanged"]=True;result["consumed"]=ad.finish()
   except Exception as exc:result.update(passed=False,terminal_audit_failure=str(exc))
   c.write_new(ctx["paths"]["run"],result);c.write_new(ctx["paths"]["status"],dict(stage=ctx["tag"]+".status",passed=result["passed"],run=c.stat(ctx["paths"]["run"]),state="pending_independent_native_and_regression_review"if result["passed"]else"failed_preserved"))
 print(c.json.dumps(dict(passed=result["passed"],tag=result.get("tag"),failure=result["failure"]),ensure_ascii=False));return 0 if result["passed"]else 1

def summarize(ad):
 path=L/(STAGE+".check.json");c.need(not path.exists(),"Existing complete/failure summary protected")
 result=dict(stage=STAGE+".summary",passed=False,root_admission=ad.entry,solver_invocations=0,native_invocations=0,build_invocations=0,queue_invocations=0,Git_invocations=0,SHA_scans=0,physical_acceptance=False,full_cycle_acceptance=False,automatic_follow_up=False,ReleaseCPU_runtime_test_claimed=False,Release_B_short_bit_equivalence_claimed=False)
 try:
  jobs=[]
  for mode,(cfg,scheme,reference,steps,frames,tag)in REFERENCES.items():
   re=ad.pin(L/(tag+".run.json"));run=c.read(re["path"])
   c.need(run.get("stage")==STAGE+".run"and run.get("passed")is True and run["solver_invocations"]==1 and(run["mode"],run["configuration"],run["scheme"])==(mode,cfg,scheme)and run["clock"]["completed_updates"]==steps and run["clock"]["native_frames"]==frames,"Actual new unique short run missing")
   ne=ad.pin(L/(tag+".native_review_full_short_r1.json"));v=c.read(ne["path"])
   c.need(v.get("stage")==NATIVE_STAGE and v.get("passed")is True and v["job"]["mode"]==mode and v["job"]["run_receipt"]==re,"Independent exact new-run native/regression review missing")
   for e in(run["source_build"],run["source_prepare"],run["program"],run["reference_run"],run["reference_native_review"],run["plan"]):ad.pin(e["path"]);c.same(e)
   jobs.append(dict(mode=mode,configuration=cfg,scheme=scheme,run=re,independent_native_review=ne,reference_run=run["reference_run"],source_build=run["source_build"],source_prepare=run["source_prepare"],completed_updates=steps,native_frames=frames,comparison=v.get("comparison"),all22_raw_byte_equality_not_inferred_from_five_exports=True))
  result.update(passed=True,implementation_regression_complete=True,jobs=jobs,scope="CPU Debug B200; GPU Debug B2 with memcheck; GPU Release default A320",no_new_physical_parameter_trial=True,no_half_or_reference_solver_chain=True,full_B_requires_separate_root_admission=True,consumed=ad.finish(),consumed_stats_unchanged=True)
 except Exception as exc:result.update(first_failure=str(exc),partials_preserved=True)
 c.write_new(path,result);print(c.json.dumps(dict(passed=result["passed"],receipt=str(path),failure=result.get("first_failure")),ensure_ascii=False));return 0 if result["passed"]else 1

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--phase",choices=("run","summary"),required=True);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");a=ap.parse_args();c.need(a.execution_authorized,"Root full-read independent action authorization required")
 ad=Admission(a.admission,a.phase);return run_one(ad)if a.phase=="run"else summarize(ad)
if __name__=="__main__":raise SystemExit(main())
