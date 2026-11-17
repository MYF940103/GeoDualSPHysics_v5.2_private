"""New staged-load bindings/review; reuse the passed M0 C++ reader and numerical checks."""
from __future__ import annotations
import argparse,csv,math,re,struct
from pathlib import Path
import upl_tpi_p1_loadclock_run_r1 as runmod
import upl_tpi_m0_dt_native_r1 as m0
c,T,L=runmod.c,runmod.T,runmod.L
TAG="upl_tpi_p1_loadclock_native_r1"
SCRIPT=Path(__file__).resolve();NOTE=T/"notes"/(TAG+".md")
IDENTITY=L/"upl_tpi_m0_dt_native_identity_root_r1.review.json"
MAX=float.fromhex("0x1.fffffffffffffp+1023")
COLUMNS="part,actual_save_time_s,saved_step,completed_updates,dt_s,last_source_time_s,last_old_eval_time_s,last_half_eval_time_s,last_endpoint_eval_time_s,last_old_q_double_Pa,last_half_q_double_Pa,last_endpoint_q_double_Pa,interval_old_forces,interval_half_forces,interval_endpoint_forces,total_old_forces,total_half_forces,total_endpoint_forces,interval_old_direct_evals,interval_old_raw_evals,interval_half_direct_evals,interval_half_raw_evals,interval_endpoint_direct_evals,interval_endpoint_raw_evals,total_old_direct_evals,total_old_raw_evals,total_half_direct_evals,total_half_raw_evals,total_endpoint_direct_evals,total_endpoint_raw_evals,interval_empty,min_old_eval_time_s,max_old_eval_time_s,min_half_eval_time_s,max_half_eval_time_s,min_endpoint_eval_time_s,max_endpoint_eval_time_s,min_old_q_double_Pa,max_old_q_double_Pa,min_half_q_double_Pa,max_half_q_double_Pa,min_endpoint_q_double_Pa,max_endpoint_q_double_Pa,cold_nonforce_eval_calls".split(",")
class Admission:
 def __init__(self,action,path):
  self.entry,self.data=c.stat(path),c.read(path);self.consumed={}
  c.need(self.data.get("stage")==TAG+"."+action+"_admission" and self.data.get("passed")is True and self.data.get("action_only")is True,"One independently reviewed action admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};c.need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")
  for p in (SCRIPT,NOTE,Path(runmod.__file__),runmod.NOTE,Path(m0.__file__),m0.CPP,m0.NOTE,Path(m0.b.__file__),Path(m0.original.__file__),m0.NEUTRAL,Path(runmod.old.__file__),Path(runmod.gpu.__file__),Path(c.__file__)):self.pin(p)
 def pin(self,path):
  key=str(Path(path).resolve());c.need(key in self.frozen,"Consumed input absent from root admission: "+key)
  self.consumed[key]=c.same(self.frozen[key]);return self.consumed[key]
 def finish(self):
  for e in self.consumed.values():c.same(e)
  c.same(self.entry);return list(self.consumed.values())

def pin_reader(ad):
 ad.pin(IDENTITY);identity=c.read(IDENTITY)
 c.need(identity.get("stage")=="upl_tpi_m0_dt_native_identity_root_r1" and identity.get("passed")is True and
  identity.get("exact_build_stage")is True and identity.get("exact_program_path")is True and identity.get("original_dependencies_stats_unchanged")is True,
  "Genuine original reader identity review required")
 built=m0.pin_reader(ad)
 c.need(built.get("stage")=="upl_tpi_m0_dt_native_r1.build" and Path(built["program"]["path"]).resolve()==m0.PROGRAM.resolve() and
  {k:built["program"][k]for k in ("path","bytes","mtime_ns")}==c.stat(m0.PROGRAM),"Exact reused native implementation/program differs")
 for key,entry in (("actual_build",c.stat(m0.BUILD)),("actual_program",c.stat(m0.PROGRAM))):
  c.need(identity[key]==entry,"Original identity receipt binding differs")
 for e in identity["actual_calls"]:ad.pin(e["path"]);c.same(e)
 return built

def get_job(ad):
 tag=ad.data["job"]["tag"];c.need(re.fullmatch(r"upl_tpi_p1_loadclock_[A-Za-z0-9_]+_r[1-9][0-9]*",tag),"Exact new staged-load tag required")
 rp=L/(tag+".run.json");ad.pin(rp);run=c.read(rp);mode=run["mode"]
 c.need(mode in runmod.REFERENCES,"Unsupported existing reader profile")
 cfg,scheme,reference,steps,frames=runmod.REFERENCES[mode]
 c.need(run["stage"]==runmod.STAGE+".run" and run["passed"]is True and run["solver_invocations"]==1 and
  (run["configuration"],run["scheme"],run["window"])==(cfg,scheme,mode) and run["PART_restart"]is False and run["pressure_history_cold_start"]is True,
  "Actual completed unique new staged-load run required")
 for key in ("call","program","source_build","source_prepare","root_admission","plan","reference_run","reference_native_review"):ad.pin(run[key]["path"]);c.same(run[key])
 for e in [*run["runtime"],*run["seed"]]:ad.pin(e["path"]);c.same(e)
 rootad=c.read(run["root_admission"]["path"]);c.need(rootad["stage"]==runmod.STAGE+".run_admission" and rootad["passed"] and rootad["job"]["tag"]==tag and
  {k:rootad["job"]["build"][k]for k in ("path","bytes","mtime_ns")}==run["source_build"],"Original root job/build binding differs")
 be,pe,program,runtime=runmod.source_build(ad,rootad["job"],cfg)
 c.need(be==run["source_build"] and pe==run["source_prepare"] and program==run["program"] and runtime==run["runtime"],"Actual new source/program/runtime provenance differs")
 ref=c.read(run["reference_run"]["path"]);c.need(Path(run["reference_run"]["path"]).resolve()==(L/(reference+".run.json")).resolve() and ref["passed"] and
  run["plan"]==ref["plan"] and run["seed"]==ref["seed"] and run["clock"]==ref["clock"],"Immutable original plan/seed reference changed")
 argv=list(ref["arguments"]);c.need(argv.count(ref["output_directory"])==1,"Original output argument not unique");argv[argv.index(ref["output_directory"])]=run["output_directory"]
 c.need(argv==run["arguments"] and run["reused_immutable_seed_and_plan_stats_unchanged"]is True,"Original argv changed beyond fresh output path")
 startpath=L/(tag+".start.json");ad.pin(startpath);start=c.read(startpath);call=c.read(run["call"]["path"])
 c.need(call["passed"] and call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==run["actual_Popen_wait_exit"]==run["actual_Win32_exit"]==0 and
  start["owner"]==call["owner"] and start["program"]==program and start["source_build"]==be,"Actual handle exits/owner/program differ")
 if cfg=="DebugCPU":
  target=call["child"];ticks=call["original_Win32_creation_FILETIME_ticks"]
  c.need(target==start["child"]==run["child"] and call["native_handle_acquired_before_wait"] and target["parent"]==call["owner"]["pid"],"Actual CPU direct-child identity differs")
 else:
  target=call["target"];ticks=call["target_creation_FILETIME_ticks"]
  c.need(target==start["target"]==run["target"] and call["target_handle_acquired_before_wait"] and call["tool_is_solver"]==(cfg=="Release") and
   call["target_actual_Win32_exit"]==run["target_actual_Win32_exit"]==0 and call["child"]==start["tool"] and call["child"]["parent"]==call["owner"]["pid"],"Actual GPU target/tool identity differs")
 c.need(Path(target["exe"]).resolve()==Path(program["path"]).resolve() and target["argv"][1:]==run["arguments"]==start["arguments"] and
  abs((ticks-116444736000000000)/1e7-target["created"])<=1e-6,"Actual executable/argv/creation differs")
 env=run["actual_environment"];expected={k:None for k in runmod.ENV_KEYS};expected["UPL_TPI_CPU_R1"if cfg=="DebugCPU"else"UPL_TPI_GPU_R1"]=scheme
 if scheme=="B":expected.update(UPL_TPI_M0_DT_R1="EQ40_RH1",UPL_TPI_P1_LOADCLOCK_R1="STAGED")
 c.need(set(env)==set((*runmod.ENV_KEYS,"OMP_NUM_THREADS","OMP_DYNAMIC")) and all(env[k]==v for k,v in expected.items()) and
  env==start["actual_environment"]==call["actual_environment"],"Actual complete selector environment differs")
 if cfg=="DebugCPU":c.need(env["OMP_NUM_THREADS"]=="1" and env["OMP_DYNAMIC"]=="FALSE","Actual CPU thread selectors differ")
 ctx=dict(run,paths={"log":L/(tag+".log"),"memcheck":L/(tag+".memcheck.log")})
 ad.pin(ctx["paths"]["log"])
 if cfg=="Debug":ad.pin(ctx["paths"]["memcheck"])
 output=Path(run["output_directory"])
 for p in (output/"Run.out",output/"Run.csv"):ad.pin(p)
 if scheme!="A":
  for base in ("UplTpiM0DtR1",runmod.SIDE):
   for suffix in (".policy.json",".summary.json"):ad.pin(output/(base+suffix))
 runmod.check_output(ctx)
 dt=run["clock"]["actual_fixed_dt_s"];clock=[0.]
 for _ in range(steps):clock.append(clock[-1]+dt)
 with Path(run["plan"]["path"]).open(encoding="utf-8-sig",newline="")as f:
  reader=csv.DictReader(f);rows=list(reader);c.need(reader.fieldnames==c.HEADER and len(rows)==frames,"Actual eight-column profile differs")
 for i,row in enumerate(rows):
  n=int(row["completed_steps"]);c.need(int(row["part"])==i and int(row["saved_step"])==(n-1 if n else 0) and
   c.bits(float(row["time_s"]))==c.bits(clock[n]) and c.bits(float(row["dt_s"]))==c.bits(dt),"Actual scalar native clock plan differs")
 p=dict(m0.WINDOWS[mode]);p["end"]=clock[-1]
 c.need(p["steps"]==steps and p["frames"]==frames and rows[-1]["completed_steps"]==str(steps) and
  c.bits(clock[-1])==c.bits(run["clock"]["actual_scalar_end_s"]) and run["clock"]["post_open_frames"]==p["post"],"Actual declared endpoint/count differs")
 return dict(tag=tag,mode=mode,window=mode,configuration=cfg,scheme=scheme,backend="CPU"if cfg=="DebugCPU"else"GPU",run_receipt=c.stat(rp),source_build=be,
  prepared=pe,source_root=c.read(pe["path"])["source_root"],run=run,output_directory=str(output),data=run["data"],run_out=c.stat(output/"Run.out"),
  plan=run["plan"],dt=dt,drain_step=1600 if scheme=="A"else 1000,profile=p,clock=clock,rows=rows,native_output=str(T/"outputs"/(tag+"_native_loadclock_r1")))

def loadclock(ad,job):
 out=Path(job["output_directory"]);paths=[out/(runmod.SIDE+s)for s in (".policy.json",".csv",".summary.json")]
 if job["scheme"]=="A":c.need(not any(p.exists()for p in paths),"A created staged-load sidecars");return dict(expected_absent=True)
 for p in paths:ad.pin(p)
 policy,summary=c.read(paths[0]),c.read(paths[2]);steps=job["profile"]["steps"];frames=job["profile"]["frames"];dt=job["dt"];event=m0.EVENT
 c.need(policy["stage"]==summary["stage"]=="upl_tpi_p1_loadclock_r1" and policy["backend"]==job["backend"] and policy["scheme"]=="B" and
  policy["old_half_endpoint_load_fractions"]==[0,.5,1] and c.bits(policy["fixed_dt_s"])==c.bits(dt) and c.bits(policy["ramp_and_drainage_time_s"])==c.bits(event) and
  policy["global_TimeStep_or_Nstep_changed"]is False and policy["Dirichlet_source_policy_changed"]is False and policy["original_P1_pressure_HG_J_order_retained"]is True and
  policy["original_pressure_schema_retained"]is True and policy["paired_load_sites_record_actual_calls"]is True and policy["sufficient_stability_or_physical_acceptance"]is False,
  "Exact staged-load source policy differs")
 cold=0 if job["backend"]=="CPU"else 1
 def stage_times(n):
  t=job["clock"][n-1];return [t,t+.5*dt,t+dt]
 def q(time):return 10000.*max(0.,time)/event if event>0. and time<event else 10000.
 with (Path(job["native_output"])/"clock.bin").open("rb")as f:
  c.need(struct.unpack("<II",f.read(8))==(frames,28),"Original native clock header differs")
  native=[struct.unpack("<dIdd",f.read(28))for _ in range(frames)];c.need(f.read(1)==b"","Extra native clock bytes")
 count=0;previous=0
 with paths[1].open(encoding="utf-8-sig",newline="")as f:
  reader=csv.DictReader(f);c.need(reader.fieldnames==COLUMNS,"Exact44-column staged-load CSV required")
  for i,row in enumerate(reader):
   c.need(i<frames,"Extra staged-load rows");v={k:m0.finite(x)for k,x in row.items()};planned=job["rows"][i];n=int(planned["completed_steps"]);delta=n-previous
   expected=dict(part=i,actual_save_time_s=job["clock"][n],saved_step=n-1 if n else 0,completed_updates=n,dt_s=dt,last_source_time_s=job["clock"][n-1]if n else 0.,interval_empty=int(n==0),cold_nonforce_eval_calls=cold)
   times=stage_times(n)if n else[0.,0.,0.]
   for phase,name in enumerate(("old","half","endpoint")):
    expected["last_"+name+"_eval_time_s"]=times[phase];expected["last_"+name+"_q_double_Pa"]=q(times[phase])if n else 0.
    expected["interval_"+name+"_forces"]=delta;expected["total_"+name+"_forces"]=n
    for site in ("direct","raw"):
     expected["interval_"+name+"_"+site+"_evals"]=delta;expected["total_"+name+"_"+site+"_evals"]=n
    low,high=(stage_times(previous+1)[phase],times[phase])if delta else(MAX,-MAX)
    expected["min_"+name+"_eval_time_s"],expected["max_"+name+"_eval_time_s"]=low,high
    expected["min_"+name+"_q_double_Pa"],expected["max_"+name+"_q_double_Pa"]=(q(low),q(high))if delta else(MAX,-MAX)
   c.need(set(expected)==set(COLUMNS) and all(c.bits(v[k])==c.bits(float(expected[k]))for k in COLUMNS),"Exact staged-load source/time/q/count replay differs at part "+str(i))
   c.need(c.bits(v["actual_save_time_s"])==c.bits(native[i][0]) and v["saved_step"]==native[i][1] and c.bits(v["dt_s"])==c.bits(native[i][2]),"Staged-load/native actual clock differs")
   previous=n;count+=1
 c.need(count==frames and previous==steps and summary["completed"]is True and summary["updates"]==steps and
  c.bits(summary["actual_end_s"])==c.bits(job["profile"]["end"]) and summary["old_half_endpoint_force_calls"]==[steps]*3 and summary["site_evaluation_counts"]==[steps]*6 and
  summary["cold_nonforce_eval_calls"]==cold and summary["global_clock_changed"]is False and summary["pressure_schema_changed"]is False and summary["physical_acceptance"]is False,
  "Genuine staged-load summary/counts differ")
 return dict(rows=count,columns=44,actual_phase_fractions=[0,.5,1],all_double_load_time_and_ramp_bits_equal=True,paired_site_evals_each=steps,
  initial_empty_interval_sentinels_preserved=True,actual_cold_nonforce_eval_calls=cold,global_clock_or_Dirichlet_changed=False,native_reader_rebuilt=False)

def default_A18(ad,job):
 tag="upl_tpi_m0_dt_Acontrol_GPU_r1";review=L/(tag+".native_review_m0_r1.json");ad.pin(review);prior=c.read(review)
 c.need(prior["passed"]is True and prior["job"]["mode"]=="Acontrol","Actual retained M0 A18 native review missing")
 old=T/"outputs"/(tag+"_native_m0_r1");new=Path(job["native_output"])
 for root in (old,new):
  p=root/"completion.json";ad.pin(p);d=c.read(p);c.need(d["passed"] and d["samples"]==18,"Separate actual18 native declarations differ")
 declarations={"original15.bin":((1040,15,18),166408),"physical.bin":((1000,26,18),208008),"common_j_theta.bin":((1040,2,18),16648),"soil_n.bin":((1000,1,18),8008),"clock.bin":((18,28),28)}
 products=[]
 for name,(shape,stride)in declarations.items():
  a,z=old/name,new/name;ad.pin(a);ad.pin(z);header=4*len(shape)
  with a.open("rb")as x,z.open("rb")as y:
   ah=x.read(header);zh=y.read(header);c.need(ah==zh==struct.pack("<"+"I"*len(shape),*shape),"Retained independent A18 headers differ")
   for i in range(18):
    av,zv=x.read(stride),y.read(stride);c.need(len(av)==len(zv)==stride and av==zv,"Default A18 exported actual record differs: "+name+"/"+str(i))
   c.need(x.read(1)==y.read(1)==b"","Extra A18 exported bytes")
  products.append(dict(file=name,old_header=shape,new_header=shape,actual_shared_records=18,all_record_bytes_equal=True))
 return dict(files=products,actual_shared_indices=[[i,i]for i in range(18)],forced_final320_compared=True,signed_clock_included=True,headers_rewritten=False,all22_raw_array_bit_proof=False)

def review(ad,job,result):
 pin_reader(ad);rp=L/(job["tag"]+".native_loadclock_r1.json");ad.pin(rp);decoded=c.read(rp)
 c.need(decoded["stage"]==TAG+".read" and decoded["passed"] and decoded["reader_invocations"]==1 and decoded["native_output"]==job["native_output"],"One genuine reused-reader decode required")
 ad.pin(decoded["reader_call"]["path"]);c.same(decoded["reader_call"]);call=c.read(decoded["reader_call"]["path"])
 c.need(call["passed"] and call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==0,"Actual original reader exits differ")
 for p in Path(job["native_output"]).iterdir():
  if p.is_file():ad.pin(p)
 result["HG_original_guards"]=m0.hg_run(job);result["method_intervals"]=m0.intervals(ad,job)
 if job["backend"]=="CPU":result["pressure_sidecar"]=m0.sidecar_cpu(ad,job,job["rows"],job["clock"])
 else:
  if job["scheme"]!="A"and job["configuration"]=="Release":result["actual_retained_pressure_PTX"]=m0.original.ptx_evidence(ad,job)
  result["pressure_sidecar"]=m0.sidecar_gpu(ad,job,job["rows"],job["clock"])
 result["staged_load_clock"]=loadclock(ad,job)
 if job["scheme"]=="A":result["default_A_actual18_byte_control"]=default_A18(ad,job)
 result.update(passed=True,reader_invocations=0,reader_implementation="upl_tpi_m0_dt_native_r1",completion=decoded["completion"],consumed=ad.finish(),
  consumed_stats_unchanged=True,all22_original_guards_not_relaxed=True,raw22_all_array_bit_proof=False,cross_dt_half_or_5Pa_equivalence_claimed=False,physical_theory_or_full_cycle_acceptance=False)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("action",choices=["read","review"]);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true")
 args=ap.parse_args();c.need(args.execution_authorized,"One separately reviewed read/review action required");ad=Admission(args.action,args.admission)
 tag=ad.data["job"]["tag"];path=L/(tag+(".native_loadclock_r1.json"if args.action=="read"else".native_review_loadclock_r1.json"));c.need(not path.exists(),"Existing successful/partial receipt protected")
 result=dict(stage=TAG+"."+args.action,passed=False,tag=tag,reader_implementation="upl_tpi_m0_dt_native_r1",solver_invocations=0,build_invocations=0,VTK_invocations=0,SHA_scans=0,automatic_follow_up=False,physical_acceptance=False)
 try:
  result["root_admission"]=ad.entry;job=get_job(ad);result["job"]={k:v for k,v in job.items()if k not in("run","rows","clock")};pin_reader(ad)
  if args.action=="read":m0.read_native(ad,job,result)
  else:review(ad,job,result)
 except Exception as exc:result.update(passed=False,first_error=str(exc),partials_preserved=True)
 c.write_new(path,result);print(c.json.dumps(dict(passed=result["passed"],receipt=str(path),first_error=result.get("first_error")),ensure_ascii=False))
 return 0 if result["passed"]else 1
if __name__=="__main__":raise SystemExit(main())
