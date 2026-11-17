"""Independent P2 read/review: reuse real M0 reader, not its one-round reviewer."""
from __future__ import annotations
import argparse,csv,math,re,struct
from contextlib import ExitStack
from fractions import Fraction
from pathlib import Path
import upl_tpi_p2_run_r1 as runmod
import upl_tpi_m0_dt_native_r1 as m0
import upl_tpi_p1_loadclock_native_r1 as binding
c,T,L=runmod.c,runmod.T,runmod.L
TAG="upl_tpi_p2_native_r1";SCRIPT=Path(__file__).resolve();NOTE=T/"notes"/(TAG+".md")
bits,finite,f32,pressure_f32_ftz=m0.bits,m0.finite,m0.f32,m0.pressure_f32_ftz
MAX=float.fromhex("0x1.fffffffffffffp+1023")
CPU_COLUMNS=runmod.CPU_PRESSURE_HEADER
GPU_COLUMNS=runmod.GPU_PRESSURE_HEADER
INTERVAL_COLUMNS=runmod.DT_HEADER
class Admission:
 def __init__(self,action,path):
  self.entry,self.data=c.stat(path),c.read(path);self.consumed={}
  c.need(self.data.get("stage")==TAG+"."+action+"_admission"and self.data.get("passed")is True and self.data.get("action_only")is True,"One independent P2 action admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};c.need(len(self.frozen)==len(self.data["inputs"]),"Duplicate input")
  for p in(SCRIPT,NOTE,Path(runmod.__file__),runmod.NOTE,Path(m0.__file__),m0.CPP,m0.NOTE,Path(m0.b.__file__),Path(m0.original.__file__),m0.NEUTRAL,Path(binding.__file__),binding.NOTE,Path(c.__file__)):self.pin(p)
 def pin(self,path):
  key=str(Path(path).resolve());c.need(key in self.frozen,"Unadmitted input: "+key);self.consumed[key]=c.same(self.frozen[key]);return self.consumed[key]
 def finish(self):
  for e in self.consumed.values():c.same(e)
  c.same(self.entry);return list(self.consumed.values())
def pin_reader(ad):return binding.pin_reader(ad)

def get_job(ad):
 tag=ad.data["job"]["tag"];c.need(re.fullmatch(r"upl_tpi_p2_[A-Za-z0-9_]+_r[1-9][0-9]*",tag),"Exact new P2 tag required")
 rp=L/(tag+".run.json");ad.pin(rp);run=c.read(rp);mode=run["mode"]
 c.need(mode in runmod.REFERENCES,"Unsupported existing reader profile")
 cfg,scheme,reference,steps,frames=runmod.REFERENCES[mode]
 c.need(run["stage"]==runmod.STAGE+".run" and run["passed"]is True and run["solver_invocations"]==1 and
  (run["configuration"],run["scheme"],run["window"])==(cfg,scheme,mode) and run["PART_restart"]is False and run["pressure_history_cold_start"]is True,
  "Actual completed unique new P2 run required")
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
 if scheme=="B":expected.update(UPL_TPI_M0_DT_R1="EQ40_RH1",UPL_TPI_P2_ROWS_R1="2")
 c.need(set(env)==set((*runmod.ENV_KEYS,"OMP_NUM_THREADS","OMP_DYNAMIC")) and all(env[k]==v for k,v in expected.items()) and
  env==start["actual_environment"]==call["actual_environment"],"Actual complete selector environment differs")
 if cfg=="DebugCPU":c.need(env["OMP_NUM_THREADS"]=="1" and env["OMP_DYNAMIC"]=="FALSE","Actual CPU thread selectors differ")
 ctx=dict(run,paths={"log":L/(tag+".log"),"memcheck":L/(tag+".memcheck.log")})
 ad.pin(ctx["paths"]["log"])
 if cfg=="Debug":ad.pin(ctx["paths"]["memcheck"])
 output=Path(run["output_directory"])
 for p in (output/"Run.out",output/"Run.csv"):ad.pin(p)
 if scheme!="A":
  for base in ("UplTpiP2DtR1",("UplTpiP2CpuR1"if cfg=="DebugCPU"else"UplTpiP2GpuR1")):
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
  plan=run["plan"],dt=dt,drain_step=1600 if scheme=="A"else 1000,profile=p,clock=clock,rows=rows,native_output=str(T/"outputs"/(tag+"_native_p2_r1")))

def intervals(ad,job):
 paths=[Path(job["output_directory"])/("UplTpiP2DtR1"+s)for s in(".policy.json",".csv",".summary.json")]
 if job["scheme"]=="A":c.need(not any(p.exists()for p in paths),"A entered P2 dt branch");return dict(expected_absent=True)
 for p in paths:ad.pin(p)
 policy,summary=c.read(paths[0]),c.read(paths[2]);w=job["profile"]
 for d in(policy,summary):c.need(d["stage"]=="upl_tpi_p2_dt_r1"and d["endpoint_defect_rounds"]==2 and d["force_phases_per_update"]==4 and d["dt_policy"]=="M0_Eq40_Rh1"and d["R_h"]==1 and d["HG_limit_reference_available"]is False and d["source_clock_policy"]=="original_TimeStep_all_four_phases"and d["signed_dterror_is_method_specific"]and d["initial_dterror_not_rewritten"]and d["physical_acceptance"]is False,"Actual four-phase method policy differs")
 c.need(bits(policy["fixed_dt_s"])==bits(job["dt"])and summary["completed"]and all(summary[k]==w["steps"]for k in("updates","pre","cor","endpoint1","endpoint2"))and summary["saved_intervals_including_initial"]==w["frames"],"Actual four-phase lifecycle differs")
 path=Path(job["native_output"])/"clock.bin";ad.pin(path)
 with path.open("rb")as f:
  c.need(struct.unpack("<II",f.read(8))==(w["frames"],28),"Native clock declaration differs");native=[struct.unpack("<dIdd",f.read(28))for _ in range(w["frames"])];c.need(f.read(1)==b"","Extra native clocks")
 mins={k:MAX for k in INTERVAL_COLUMNS[14:20]};maximum=-MAX;previous=count=0
 with paths[1].open(encoding="utf-8-sig",newline="")as f:
  reader=csv.DictReader(f);c.need(reader.fieldnames==INTERVAL_COLUMNS,"Exact21-column four-phase schema required")
  for i,row in enumerate(reader):
   c.need(i<w["frames"],"Extra interval row");v={k:finite(x)for k,x in row.items()};raw=native[i];n=int(job["rows"][i]["completed_steps"]);delta=n-previous;previous=n
   c.need(v["part"]==i and bits(v["actual_save_time_s"])==bits(raw[0])and v["saved_step"]==raw[1]and v["completed_updates"]==n and bits(v["dt_s"])==bits(raw[2])==bits(job["dt"]),"Actual interval clock/Step/dt differs")
   c.need(all(v[k]==delta for k in INTERVAL_COLUMNS[5:9])and all(v[k]==n for k in INTERVAL_COLUMNS[9:13])and v["min_HG_limit_reference_s"]==MAX,"Actual four-force counts/HG unavailable marker differ")
   if not i:c.need(v["interval_empty"]==1 and all(v[k]==MAX for k in INTERVAL_COLUMNS[14:20])and v["max_dt_minus_bound_s"]==-MAX,"Initial sentinels were masked or rewritten")
   else:
    bound=min(v["min_force_CFL_s"],v["min_skeleton_wave_AV_CFL_s"],v["min_Rh_hydro_s"]);error=job["dt"]-bound
    c.need(v["interval_empty"]==0 and delta>0 and bits(bound)==bits(v["min_selected_bound_s"])and bits(error)==bits(v["max_dt_minus_bound_s"])==bits(raw[3])and error<=1e-14,"Signed interval differs from original necessary-bound arithmetic")
    for k in mins:mins[k]=min(mins[k],v[k])
    maximum=max(maximum,error)
   count+=1
 c.need(count==w["frames"]and bits(summary["actual_end_s"])==bits(w["end"])and bits(summary["max_dt_minus_bound_s"])==bits(maximum),"Four-phase total count/end/max differs")
 for k,v in mins.items():c.need(bits(summary[k])==bits(v),"Total interval minimum differs: "+k)
 return dict(saved_interval_rows=count,noninitial_signed_bit_checks=count-1,actual_force_phases=4,initial_native_signed_and_sentinels_preserved=True,HG_reference_unavailable=True,added_ULP_tolerance=0)

def normalized(row,gpu):
 v={k:finite(x)for k,x in row.items()};d={k:v[k]for k in("part","native_id","source_step_zero_based","completed_step","source_time_s","actual_save_time_s","dt_s","pn_Pa","previous_Pa","prediction_double_Pa","endpoint_q_actual_float_Pa","S_1_per_m_s","Rgamma_Pa_per_m_s","theta_half_for_J_1_per_s","theta_endpoint_1_per_s","Jn","Jhalf","Jfull","source_drained","endpoint_drained","commits","endpoint_calls","core_field_bit_checks","hg_snapshot_checks")}
 d.update(half=v["half_actual_float_Pa"if gpu else"mechanical_half_actual_float_Pa"],raw=v["raw_final_float_Pa"if gpu else"raw_candidate_float_Pa"],actualBC=v["validated_BC_value_float_Pa"if gpu else"actual_after_BC_float_Pa"],bc=v["commit_drained"if gpu else"provisional_or_final_commit_drained"],round=v["round"if gpu else"pressure_round"])
 if gpu:d.update(finalField=v["final_field_float_Pa"],has=v["has_endpoint_observation"],stale=v["final_field_is_previous_step"])
 else:d.update(prior=v["prior_committed_finalP_stale_Pa"],validated=v["first_endpoint_validated"],writes=v["endpoint_writes"])
 return d

def pressure(ad,job):
 out=Path(job["output_directory"]);gpu=job["backend"]=="GPU";base="UplTpiP2GpuR1"if gpu else"UplTpiP2CpuR1"
 paths=[out/(base+s)for s in((".policy.json",".summary.json",".round1.csv",".round2.csv")if gpu else(".policy.json",".summary.json",".csv"))]
 if job["scheme"]=="A":c.need(not any(p.exists()for p in paths),"A created P2 pressure sidecars");return dict(expected_absent=True)
 for p in paths:ad.pin(p)
 policy,summary=c.read(paths[0]),c.read(paths[1]);w=job["profile"];N=w["steps"]
 for d in(policy,summary):c.need(d["stage"]==("upl_tpi_p2_gpu_r1"if gpu else"upl_tpi_p2_cpu_r1")and d["alpha"]==.5 and d["beta"]==0 and d["full_restart_supported"]is False and d["paper_literal_LF"]is False and d["second_order_claimed"]is False and d["true_implicit_solution"]is False and d["physical_acceptance"]is False,"Independent P2 pressure metadata differs")
 c.need(policy["M0"]is True and policy["native_count"]==1040 and policy["soil_count"]==1000 and policy["history_ID_owned"]and policy["history_cold_start"],"P2 owner/history policy differs")
 c.need(summary["completed"]and summary["commits"]==N and summary["endpoint_calls"]==summary["endpoint_writes"]==2*N and summary["first_validations"]==N and summary["core_field_bit_checks"]==14000*N and summary["HG_readonly_snapshot_checks"]==4000*N and bits(summary["actual_end"])==bits(w["end"]),"Two-round lifecycle summary differs")
 if gpu:c.need(policy["endpoint_defect_rounds"]==2 and policy["endpoint_source_clock_is_original_n"]and policy["staged_load_clock"]is False and policy["first_commit_rotates_history"]is False and policy["first_finalP_is_stale_previous_step"]and policy["first_BC_value_is_validated_rule_not_extra_native_save"]and policy["first_lap_observed"]is False and policy["first_legacy_rate_observed"]is False and summary["first_row_D2D_copies"]==summary["second_transitions"]==N and summary["initial_first_row_D2D_copies"]==1 and summary["saved_records_per_round"]==1000*w["frames"]and summary["PorePressRate_is_last_round_scaled_residual_not_dpdt"],"GPU P2 snapshot/scope differs")
 else:c.need(policy["endpoint_defects_per_step"]==2 and policy["global_source_clock_unchanged"]and policy["staged_load_clock_enabled"]is False and policy["first_finalP_field_is_prior_commit_not_p1"]and policy["first_actual_BC_is_directly_captured"]and summary["second_starts"]==N and summary["PorePressRate_is_second_endpoint_scaled_residual_not_actual_dpdt"],"CPU P2 snapshot/scope differs")
 import numpy as np
 path=Path(job["native_output"])/"physical.bin";ad.pin(path)
 records=Jplain=Jfused=Jboth=0;rounding=0.;sum1=sum2=0.;correction_rows=0;subnormals=dict(pn=0,previous=0,q1=0,q2=0)
 with ExitStack()as stack:
  readers=[]
  for path in paths[2:]:
   r=csv.DictReader(stack.enter_context(path.open(encoding="utf-8-sig",newline="")));c.need(r.fieldnames==(GPU_COLUMNS if gpu else CPU_COLUMNS),"Exact independent32-column P2 schema required");readers.append(r)
  native=stack.enter_context((Path(job["native_output"])/"physical.bin").open("rb"));c.need(struct.unpack("<III",native.read(12))==(1000,26,w["frames"]),"Native physical header differs")
  for part,planned in enumerate(job["rows"]):
   n=int(planned["completed_steps"]);time=struct.unpack("<d",native.read(8))[0];state=np.frombuffer(native.read(1000*26*8),dtype="<f8").reshape(1000,26);c.need(bits(time)==bits(job["clock"][n]),"P2/native clock differs")
   seen=set();drains=[0]*5
   for _ in range(1000):
    a=next(readers[0],None);c.need(a is not None,"Missing first P2 row");first=normalized(a,gpu);records+=1
    if gpu:
     a=next(readers[1],None);c.need(a is not None,"Missing second P2 row");second=normalized(a,True);records+=1
    elif n:
     a=next(readers[0],None);c.need(a is not None,"Missing interleaved second P2 row");second=normalized(a,False);records+=1
    else:second=first # One real CPU round0 initial row, not a second observed endpoint.
    k=int(first["native_id"]);c.need(first["native_id"]==k and 40<=k<1040 and k not in seen and second["native_id"]==k,"P2 paired ID ownership differs");seen.add(k)
    for roundno,r in enumerate((first,second),1):
     c.need(r["part"]==part and r["completed_step"]==r["commits"]==n and r["endpoint_calls"]==2*n and r["core_field_bit_checks"]==14000*n and r["hg_snapshot_checks"]==4000*n and r["source_step_zero_based"]==(n-1 if n else 0)and bits(r["source_time_s"])==bits(job["clock"][n-1 if n else 0])and bits(r["actual_save_time_s"])==bits(time)and bits(r["dt_s"])==bits(job["dt"]),"Actual P2 clock/history/counters differ")
     if gpu:c.need(r["round"]==roundno and r["has"]==int(n!=0)and r["stale"]==int(n!=0 and roundno==1),"GPU observation/stale flags differ")
     else:c.need(r["round"]==(roundno if n else 0)and r["validated"]==int(n!=0)and r["writes"]==2*n,"CPU actual round/write/validation counters differ")
     c.need(all(r[x]in(0.,1.)for x in("source_drained","endpoint_drained","bc")),"P2 drainage mask is not boolean")
    for field in("pn_Pa","previous_Pa","prediction_double_Pa","half","Jn","Jhalf","Jfull","theta_half_for_J_1_per_s","source_drained"):c.need(bits(first[field])==bits(second[field]),"Source/half/J changed between endpoints")
    if not gpu:c.need(bits(first["prior"],"f")==bits(second["prior"],"f"),"CPU old final was replaced by provisional p1")
    c.need(bits(second["actualBC"],"f")==bits(state[k-40,6],"f")and bits(second["Jfull"])==bits(state[k-40,8]),"Accepted p2/J differs from native")
    if gpu:c.need(bits(second["actualBC"],"f")==bits(second["finalField"],"f"),"GPU final field is not p2")
    if not n:c.need(all(first[x]==0. and second[x]==0. for x in("pn_Pa","previous_Pa","prediction_double_Pa","half","endpoint_q_actual_float_Pa","S_1_per_m_s","Rgamma_Pa_per_m_s","raw","actualBC"))and first["Jn"]==first["Jhalf"]==first["Jfull"]==1.,"Cold P2 initial state differs")
    else:
     cast=pressure_f32_ftz if gpu else f32;pn,previous=(cast(first["pn_Pa"]),cast(first["previous_Pa"]))if gpu else(first["pn_Pa"],first["previous_Pa"])
     prediction=pn+.5*(pn-previous);c.need(bits(first["prediction_double_Pa"])==bits(prediction)and bits(first["half"],"f")==bits(0. if first["source_drained"]else cast(prediction),"f"),"History prediction/half BC differs")
     c.need(bits(first["endpoint_q_actual_float_Pa"],"f")==bits(0. if first["endpoint_drained"]else cast(prediction),"f")and bits(second["endpoint_q_actual_float_Pa"],"f")==bits(first["actualBC"],"f"),"q1 prediction or q2 actual p1 differs")
     for r in(first,second):
      if r["endpoint_drained"]:c.need(r["S_1_per_m_s"]==r["Rgamma_Pa_per_m_s"]==0.,"Drained row fabricated S/R");raw=0.
      else:
       c.need(r["S_1_per_m_s"]>0.,"Nonpositive S must not be removed/regularized");q=cast(r["endpoint_q_actual_float_Pa"])if gpu else r["endpoint_q_actual_float_Pa"];exact=q+r["Rgamma_Pa_per_m_s"]/r["S_1_per_m_s"];raw=cast(exact);rounding=max(rounding,abs(raw-exact))
      c.need(bits(r["raw"],"f")==bits(raw,"f")and bits(r["actualBC"],"f")==bits(0. if r["bc"]else raw,"f"),"P2 actual RN/FTZ/raw or true+0 BC differs")
     product=job["dt"]*first["Jhalf"];plain=first["Jn"]+product*first["theta_half_for_J_1_per_s"];pm=bits(first["Jfull"])==bits(plain)
     if gpu:
      fused=float(Fraction.from_float(first["Jn"])+Fraction.from_float(product)*Fraction.from_float(first["theta_half_for_J_1_per_s"]));fm=bits(first["Jfull"])==bits(fused);c.need(pm or fm,"Original single-J CUDA expression differs");Jfused+=int(fm);Jboth+=int(pm and fm)
      for label,v in(("pn",first["pn_Pa"]),("previous",first["previous_Pa"]),("q1",first["endpoint_q_actual_float_Pa"]),("q2",second["endpoint_q_actual_float_Pa"])):subnormals[label]+=int(0.<abs(f32(v))<2.**-126)
     else:c.need(pm,"CPU J advanced twice or used thetaEndpoint2")
     Jplain+=int(pm)
     if not first["endpoint_drained"]and not second["endpoint_drained"]:sum1+=(first["Rgamma_Pa_per_m_s"]/first["S_1_per_m_s"])**2;sum2+=(second["Rgamma_Pa_per_m_s"]/second["S_1_per_m_s"])**2;correction_rows+=1
    for i,v in enumerate((first["source_drained"],first["endpoint_drained"],first["bc"],second["endpoint_drained"],second["bc"])):drains[i]+=int(v)
   expected=10 if n>job["drain_step"]else 0;c.need(len(seen)==1000 and drains==[expected]*5,"All original true drained receivers differ")
  c.need(all(next(r,None)is None for r in readers)and native.read(1)==b"","Trailing sidecar/native rows")
 expected_records=2*1000*w["frames"]if gpu else 1000*(2*w["frames"]-1);c.need(records==expected_records,"P2 actual row count differs")
 return dict(actual_records=records,paired_saved_IDs=1000*w["frames"],endpoint_rounds=2,actual_q2_is_validated_p1=True,single_J_rows=1000*(w["frames"]-1),J_plain_matches=Jplain,J_fused_matches=Jfused,J_both_matches=Jboth,actual_GPU_pressure_RN_signed_FTZ=gpu,max_actual_rounding_Pa=rounding,observed_GPU_nonzero_subnormal_inputs=subnormals,first_BC_GPU_is_device_validated_rule_not_independent_native_save=gpu,first_lap_or_rate_claimed=False,last_native_rate_is_q2_residual_not_dpdt=True,unsaved_history_independently_observed=False,added_ULP_or_Pa_tolerance=0,R1_over_S1_RMS_Pa=math.sqrt(sum1/correction_rows)if correction_rows else None,R2_over_S2_RMS_Pa=math.sqrt(sum2/correction_rows)if correction_rows else None,residual_shrink_or_physical_acceptance_required=False)

def review(ad,job,result):
 pin_reader(ad);rp=L/(job["tag"]+".native_p2_r1.json");ad.pin(rp);decoded=c.read(rp)
 c.need(decoded["stage"]==TAG+".read"and decoded["passed"]and decoded["reader_invocations"]==1 and decoded["native_output"]==job["native_output"],"One actual P2 read required")
 ad.pin(decoded["reader_call"]["path"]);c.same(decoded["reader_call"]);call=c.read(decoded["reader_call"]["path"]);c.need(call["passed"]and call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==0,"Actual reader exits differ")
 for p in Path(job["native_output"]).iterdir():
  if p.is_file():ad.pin(p)
 result["HG_original_guards"]=m0.hg_run(job);result["method_intervals"]=intervals(ad,job)
 if job["scheme"]!="A"and job["backend"]=="GPU"and job["configuration"]=="Release":result["actual_retained_pressure_PTX"]=m0.original.ptx_evidence(ad,job)
 result["pressure_two_rounds"]=pressure(ad,job)
 if job["scheme"]=="A":result["default_A_actual18_byte_control"]=binding.default_A18(ad,job)
 result.update(passed=True,reader_invocations=0,reader_implementation="upl_tpi_m0_dt_native_r1",completion=decoded["completion"],consumed=ad.finish(),consumed_stats_unchanged=True,all22_original_guards_not_relaxed=True,raw22_all_array_bit_proof=False,cross_option_half_or_5Pa_equivalence_claimed=False,physical_theory_or_full_cycle_acceptance=False)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("action",choices=["read","review"]);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");a=ap.parse_args()
 c.need(a.execution_authorized,"One independent P2 action admission required");ad=Admission(a.action,a.admission);tag=ad.data["job"]["tag"];path=L/(tag+(".native_p2_r1.json"if a.action=="read"else".native_review_p2_r1.json"));c.need(not path.exists(),"Existing/partial P2 receipt protected")
 result=dict(stage=TAG+"."+a.action,passed=False,tag=tag,reader_implementation="upl_tpi_m0_dt_native_r1",solver_invocations=0,build_invocations=0,VTK_invocations=0,SHA_scans=0,physical_acceptance=False,automatic_follow_up=False)
 try:
  result["root_admission"]=ad.entry;job=get_job(ad);result["job"]={k:v for k,v in job.items()if k not in("run","rows","clock")};pin_reader(ad)
  if a.action=="read":m0.read_native(ad,job,result)
  else:review(ad,job,result)
 except Exception as exc:result.update(passed=False,first_error=str(exc),partials_preserved=True)
 c.write_new(path,result);print(c.json.dumps(dict(passed=result["passed"],receipt=str(path),first_error=result.get("first_error")),ensure_ascii=False));return 0 if result["passed"]else 1
if __name__=="__main__":raise SystemExit(main())
