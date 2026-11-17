"""Independently read/review honest full-scope P3 short runs; no solver or build."""
from __future__ import annotations
import argparse,csv,struct
from pathlib import Path
import upl_tpi_p3_full_short_r1 as runmod
import upl_tpi_p3_native_r1 as science

c,T,L=runmod.c,runmod.T,runmod.L
m0,binding=science.m0,science.binding
TAG="upl_tpi_p3_full_short_native_r1";NOTE=T/"notes"/(TAG+".md")

class Admission(c.Admission):
 def __init__(self,action,path):
  self.entry,self.data=c.stat(path),c.read(path);self.consumed={}
  c.need(self.data.get("stage")==TAG+"."+action+"_admission"and self.data.get("passed")is True and self.data.get("action_only")is True,"One independent new short-native action required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};c.need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")
  for p in(Path(__file__),NOTE,Path(runmod.__file__),runmod.NOTE,Path(runmod.original.__file__),runmod.original.NOTE,Path(runmod.original.old.__file__),Path(runmod.gpu.__file__),Path(c.__file__),Path(science.__file__),science.NOTE,Path(m0.__file__),m0.CPP,m0.NOTE,Path(m0.b.__file__),Path(m0.original.__file__),m0.NEUTRAL,Path(binding.__file__),binding.NOTE):self.pin(p)

def pin_reader(ad):return binding.pin_reader(ad)

def get_job(ad):
 tag=ad.data["job"]["tag"];matches=[(mode,v)for mode,v in runmod.REFERENCES.items()if v[-1]==tag]
 c.need(len(matches)==1,"Only an exact new full-scope short tag is allowed");mode,(cfg,scheme,reference,steps,frames,_)=matches[0]
 rp=L/(tag+".run.json");re=ad.pin(rp);run=c.read(rp)
 c.need(run.get("stage")==runmod.STAGE+".run"and run.get("passed")is True and run.get("solver_invocations")==1 and(run["configuration"],run["scheme"],run["mode"],run["window"])==(cfg,scheme,mode,mode)and run["PART_restart"]is False and run["pressure_history_cold_start"]is True,"Actual completed unique new short run required")
 for key in("call","program","source_build","source_prepare","root_admission","plan","reference_run","reference_native_review"):ad.pin(run[key]["path"]);c.same(run[key])
 for e in[*run["runtime"],*run["seed"]]:ad.pin(e["path"]);c.same(e)
 rootad=c.read(run["root_admission"]["path"])
 c.need(rootad.get("stage")==runmod.STAGE+".run_admission"and rootad.get("passed")is True and rootad.get("action_only")is True and rootad["job"]["tag"]==tag and {k:rootad["job"]["build"][k]for k in("path","bytes","mtime_ns")}==run["source_build"],"Actual new source/build root admission differs")
 be,pe,program,runtime=runmod.source_build(ad,rootad["job"],cfg)
 c.need((be,pe,program,runtime)==(run["source_build"],run["source_prepare"],run["program"],run["runtime"]),"New full-scope source/program/runtime provenance differs")
 ref=c.read(run["reference_run"]["path"]);old_review=c.read(run["reference_native_review"]["path"])
 c.need(Path(run["reference_run"]["path"]).resolve()==(L/(reference+".run.json")).resolve()and ref.get("stage")==runmod.original.STAGE+".run"and ref.get("passed")is True and old_review.get("stage")==science.TAG+".review"and old_review.get("passed")is True and old_review["job"]["run_receipt"]==run["reference_run"],"Actual original P3 short control binding differs")
 c.need(run["plan"]==ref["plan"]and run["seed"]==ref["seed"]and run["clock"]==ref["clock"]and run["reused_immutable_seed_and_plan_stats_unchanged"]is True,"Immutable original short seed/plan/clock changed")
 argv=list(ref["arguments"]);c.need(argv.count(ref["output_directory"])==1,"Original output argv not unique");argv[argv.index(ref["output_directory"])]=run["output_directory"];c.need(argv==run["arguments"],"Original argv changed beyond fresh output")
 se=ad.pin(L/(tag+".start.json"));start=c.read(se["path"]);call=c.read(run["call"]["path"])
 c.need(call["passed"]is True and call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==run["actual_Popen_wait_exit"]==run["actual_Win32_exit"]==0 and start["owner"]==call["owner"]and start["program"]==program and start["source_build"]==be,"Genuine Popen/Win32 exits or owner/program differ")
 if cfg=="DebugCPU":
  target=call["child"];ticks=call["original_Win32_creation_FILETIME_ticks"]
  c.need(target==start["child"]==run["child"]and call["native_handle_acquired_before_wait"]and target["parent"]==call["owner"]["pid"],"Actual CPU direct-child ownership differs")
 else:
  target=call["target"];ticks=call["target_creation_FILETIME_ticks"]
  c.need(target==start["target"]==run["target"]and call["target_handle_acquired_before_wait"]and call["tool_is_solver"]==(cfg=="Release")and call["target_actual_Win32_exit"]==run["target_actual_Win32_exit"]==0 and call["child"]==start["tool"]and call["child"]["parent"]==call["owner"]["pid"],"Actual GPU tool/target handles or exits differ")
 c.need(Path(target["exe"]).resolve()==Path(program["path"]).resolve()and target["argv"][1:]==run["arguments"]==start["arguments"]and abs((ticks-116444736000000000)/1e7-target["created"])<=1e-6,"Actual target exe/argv/creation differs")
 env=run["actual_environment"];expected={k:None for k in runmod.ENV_KEYS};expected["UPL_TPI_CPU_R1"if cfg=="DebugCPU"else"UPL_TPI_GPU_R1"]=scheme
 if scheme=="B":expected.update(UPL_TPI_M0_DT_R1="EQ40_RH1",UPL_TPI_P3_ROWS_R1="3")
 c.need(set(env)==set((*runmod.ENV_KEYS,"OMP_NUM_THREADS","OMP_DYNAMIC"))and all(env[k]==v for k,v in expected.items())and env==start["actual_environment"]==call["actual_environment"],"Actual complete selectors differ")
 if cfg=="DebugCPU":c.need(env["OMP_NUM_THREADS"]=="1"and env["OMP_DYNAMIC"]=="FALSE","Actual CPU thread selectors differ")
 out=Path(run["output_directory"]);paths={"log":L/(tag+".log"),"memcheck":L/(tag+".memcheck.log")};ad.pin(paths["log"])
 if cfg=="Debug":ad.pin(paths["memcheck"])
 for p in(out/"Run.out",out/"Run.csv"):ad.pin(p)
 if scheme!="A":
  for prefix in("UplTpiP3DtR1","UplTpiP3CpuR1"if cfg=="DebugCPU"else"UplTpiP3GpuR1"):
   for suffix in(".policy.json",".summary.json"):ad.pin(out/(prefix+suffix))
 runmod.original.check_output(dict(run,paths=paths))
 dt=run["clock"]["actual_fixed_dt_s"];clock=[0.]
 for _ in range(steps):clock.append(clock[-1]+dt)
 with Path(run["plan"]["path"]).open(encoding="utf-8-sig",newline="")as f:
  reader=csv.DictReader(f);rows=list(reader);c.need(reader.fieldnames==c.HEADER and len(rows)==frames,"Actual eight-column short plan differs")
 for i,row in enumerate(rows):
  n=int(row["completed_steps"]);c.need(int(row["part"])==i and int(row["saved_step"])==(n-1 if n else 0)and c.bits(float(row["time_s"]))==c.bits(clock[n])and c.bits(float(row["dt_s"]))==c.bits(dt),"Actual scalar saved time/step/dt differs")
 p=dict(m0.WINDOWS[mode]);p["end"]=clock[-1]
 c.need(p["steps"]==steps and p["frames"]==frames and int(rows[-1]["completed_steps"])==steps and c.bits(clock[-1])==c.bits(run["clock"]["actual_scalar_end_s"])and run["clock"]["post_open_frames"]==p["post"]==0,"Exact short profile/end or post-open scope differs")
 return dict(tag=tag,mode=mode,window=mode,configuration=cfg,scheme=scheme,backend="CPU"if cfg=="DebugCPU"else"GPU",run_receipt=re,source_build=be,prepared=pe,source_root=c.read(pe["path"])["source_root"],run=run,output_directory=str(out),data=run["data"],run_out=c.stat(out/"Run.out"),plan=run["plan"],dt=dt,drain_step=1600 if scheme=="A"else 1000,profile=p,clock=clock,rows=rows,native_output=str(T/"outputs"/(tag+"_native_full_short_r1")),reference_run=run["reference_run"],reference_native_review=run["reference_native_review"])

def byte_equal(ad,a,z,label):
 ae,ze=ad.pin(a),ad.pin(z);c.need(ae["bytes"]==ze["bytes"],"Old/new byte count differs: "+label)
 with Path(a).open("rb")as x,Path(z).open("rb")as y:
  while True:
   av,zv=x.read(1024*1024),y.read(1024*1024);c.need(av==zv,"Old/new actual bytes differ: "+label)
   if not av:break
 return dict(file=label,old=ae,new=ze,all_bytes_equal=True)

def compare_control(ad,job,result):
 oldreview=c.read(job["reference_native_review"]["path"]);ref=oldreview["job"];old=Path(ref["native_output"]);new=Path(job["native_output"]);frames=job["profile"]["frames"]
 c.need(ref["mode"]==job["mode"]and ref["configuration"]==job["configuration"]and ref["scheme"]==job["scheme"]and ref["plan"]==job["plan"]and ref["run_receipt"]==job["reference_run"],"Actual original native job identity differs")
 oldtag=c.read(job["reference_run"]["path"])["tag"];oe=ad.pin(L/(oldtag+".native_p3_r1.json"));od=c.read(oe["path"])
 c.need(od.get("stage")==science.TAG+".read"and od.get("passed")is True and od.get("reader_invocations")==1 and od["job"]["run_receipt"]==job["reference_run"]and od["native_output"]==str(old),"Genuine original completed read required")
 ad.pin(od["reader_call"]["path"]);c.same(od["reader_call"]);oc=c.read(od["reader_call"]["path"]);c.need(oc["passed"]and oc["actual_Popen_wait_exit"]==oc["actual_Win32_exit"]==0,"Actual old reader exits differ")
 shape={"original15.bin":((1040,15,frames),166408),"physical.bin":((1000,26,frames),208008),"common_j_theta.bin":((1040,2,frames),16648),"soil_n.bin":((1000,1,frames),8008),"clock.bin":((frames,28),28)};products=[]
 for name,(header,stride)in shape.items():
  a,z=old/name,new/name;ad.pin(a);ad.pin(z);h=struct.pack("<"+"I"*len(header),*header)
  with a.open("rb")as x,z.open("rb")as y:
   c.need(x.read(len(h))==y.read(len(h))==h,"True independent short headers differ: "+name)
   for i in range(frames):
    av,zv=x.read(stride),y.read(stride);c.need(len(av)==len(zv)==stride and av==zv,"Actual same-clock record differs: "+name+"/"+str(i))
   c.need(x.read(1)==y.read(1)==b"","Trailing actual short records: "+name)
  products.append(dict(file=name,old=ad.pin(a),new=ad.pin(z),header=list(header),actual_shared_records=frames,all_record_bytes_equal=True))
 ids=[byte_equal(ad,old/name,new/name,name)for name in("native_ids.csv","fixed_ids.csv","columns.csv")]
 c.need(result["HG_original_guards"]==oldreview["HG_original_guards"],"Actual old/new HG runtime summaries differ")
 sidecars=[]
 if job["scheme"]!="A":
  prefix="UplTpiP3CpuR1"if job["backend"]=="CPU"else"UplTpiP3GpuR1";suffixes=[".policy.json",".summary.json"]+([".csv"]if job["backend"]=="CPU"else[".round1.csv",".round2.csv",".round3.csv"])
  names=[prefix+s for s in suffixes]+["UplTpiP3DtR1"+s for s in(".policy.json",".csv",".summary.json")]
  priorout=Path(c.read(job["reference_run"]["path"])["output_directory"])
  sidecars=[byte_equal(ad,priorout/name,Path(job["output_directory"])/name,name)for name in names]
 return dict(actual_original_P3_control=job["reference_native_review"],files=products,ID_and_column_exports=ids,P3_sidecars=sidecars,all_actual_saved_states_compared=frames,actual_shared_indices=[[i,i]for i in range(frames)],signed_clock_all_bytes_included=True,forced_final_included=True,headers_rewritten=False,all22_reader_guards_independently_checked=True,all22_raw_array_bit_proof=False,hidden_HG_history_cross_run_byte_proof=False,HG_runtime_summary_exact_equal=True,interpolation_or_tolerance_added=False,ReleaseCPU_runtime_test_claimed=False,Release_B_short_bit_equivalence_claimed=False)

def review(ad,job,result):
 pin_reader(ad);rp=L/(job["tag"]+".native_full_short_r1.json");ad.pin(rp);decoded=c.read(rp)
 c.need(decoded.get("stage")==TAG+".read"and decoded.get("passed")is True and decoded.get("reader_invocations")==1 and decoded["native_output"]==job["native_output"]and decoded["job"]["run_receipt"]==job["run_receipt"],"One genuine new full-scope short read required")
 ad.pin(decoded["reader_call"]["path"]);c.same(decoded["reader_call"]);call=c.read(decoded["reader_call"]["path"]);c.need(call["passed"]and call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==0,"Actual reused reader exits differ")
 for p in Path(job["native_output"]).iterdir():
  if p.is_file():ad.pin(p)
 result["HG_original_guards"]=m0.hg_run(job)
 result["method_intervals"]=science.intervals(ad,job)
 result["pressure_three_rounds"]=science.pressure(ad,job)
 result["comparison"]=compare_control(ad,job,result)
 result.update(passed=True,reader_invocations=0,native_read_receipt=c.stat(rp),completion=decoded["completion"],implementation_regression_only=True,all22_original_guards_not_relaxed=True,raw22_all_array_bit_proof=False,cross_option_half_or_5Pa_equivalence_claimed=False,physical_theory_or_full_cycle_acceptance=False,consumed=ad.finish(),consumed_stats_unchanged=True)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("action",choices=("read","review"));ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");a=ap.parse_args();c.need(a.execution_authorized,"One root-reviewed independent native action required")
 ad=Admission(a.action,a.admission);tag=ad.data["job"]["tag"];path=L/(tag+(".native_full_short_r1.json"if a.action=="read"else".native_review_full_short_r1.json"));c.need(not path.exists(),"Existing/failed/partial native receipt protected")
 result=dict(stage=TAG+"."+a.action,passed=False,tag=tag,reader_implementation="upl_tpi_m0_dt_native_r1",solver_invocations=0,build_invocations=0,VTK_invocations=0,Git_invocations=0,SHA_scans=0,queue_invocations=0,physical_acceptance=False,automatic_follow_up=False)
 try:
  result["root_admission"]=ad.entry;job=get_job(ad);result["job"]={k:v for k,v in job.items()if k not in("run","rows","clock")};pin_reader(ad)
  if a.action=="read":m0.read_native(ad,job,result)
  else:review(ad,job,result)
 except Exception as exc:result.update(passed=False,first_error=str(exc),partials_preserved=True)
 c.write_new(path,result);print(c.json.dumps(dict(passed=result["passed"],receipt=str(path),first_error=result.get("first_error")),ensure_ascii=False));return 0 if result["passed"]else 1
if __name__=="__main__":raise SystemExit(main())
