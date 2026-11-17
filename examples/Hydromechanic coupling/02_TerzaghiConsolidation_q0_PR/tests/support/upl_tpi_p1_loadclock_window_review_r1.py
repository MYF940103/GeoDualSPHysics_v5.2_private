"""Offline staged-load B10us window review; no solver, decoder, A-table rebuild or fitted reference."""
from __future__ import annotations
import argparse,csv,json,math,os,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
import upl_tpi_m0_dt_causal_r1 as causal
import upl_tpi_p1_loadclock_native_r1 as native
prior=causal.prior
T=causal.T;TAG="upl_tpi_p1_loadclock_window_review_r1";JOB="upl_tpi_p1_loadclock_B10us_window2s_GPU_r1"
NOTE=T/"notes"/(TAG+".md");CHECK=T/"logs"/(TAG+".check.json")
RUN=T/"logs"/(JOB+".run.json");READ=T/"logs"/(JOB+".native_loadclock_r1.json");REVIEW=T/"logs"/(JOB+".native_review_loadclock_r1.json")
NATIVE=T/"outputs"/(JOB+"_native_loadclock_r1");OLD_METRICS=causal.PRODUCTS["metrics.json"]
N,STEPS,POST,DT,END=prior.N,prior.STEPS,prior.POST,prior.DT,prior.END
TARGETS=causal.TARGETS;need,stat,write_json,write_csv,save_png=causal.need,causal.stat,causal.write_json,causal.write_csv,causal.save_png
LABELS={"A":"Retained A finite-Kw /6.25us context","B10":"Original-source-clock B /10us","Bstaged":"Staged-load-clock B /10us"}
COLORS={"A":"tab:blue","B10":"tab:orange","Bstaged":"tab:green"}
PRODUCTS={n:T/"figures"/(TAG+"."+n)for n in ("history.csv","layers.csv","profiles.csv","targets.csv","differences.csv","events.csv","loadclock.csv","metrics.json","history.png","startup.png","late.png","profiles.png","modes.png","differences.png")}
class Admission(causal.Admission):
 def __init__(self,path):
  self.entry=stat(path);self.data=json.loads(Path(path).read_text(encoding="utf-8-sig"));self.used={}
  need(self.data.get("stage")==TAG+".admission" and self.data.get("passed")is True and self.data.get("offline_only")is True,"One root-read offline-only admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};need(len(self.frozen)==len(self.data["inputs"]),"Duplicate scientific input")
  for p in (Path(__file__),NOTE,Path(causal.__file__),causal.NOTE,Path(prior.__file__),Path(native.__file__),native.NOTE,Path(native.runmod.__file__),native.runmod.NOTE,Path(native.m0.__file__),causal.BASE_XML,causal.PLAN_NOTE):self.pin(p)

def typed(row):
 result={}
 for k,v in row.items():
  if v=="":result[k]=None
  elif v in ("True","False"):result[k]=v=="True"
  else:
   try:result[k]=float(v)
   except ValueError:result[k]=v
 return result

def load_new(ad,np,result):
 review,decoded,run=ad.read(REVIEW),ad.read(READ),ad.read(RUN)
 need(review.get("stage")==native.TAG+".review" and review.get("passed")is True and review.get("all22_original_guards_not_relaxed")is True and
  decoded.get("stage")==native.TAG+".read" and decoded.get("passed")is True and decoded.get("reader_invocations")==1 and
  Path(decoded["native_output"]).resolve()==NATIVE.resolve() and run.get("stage")==native.runmod.STAGE+".run" and run.get("passed")is True,
  "Actual unique staged-load native/read/run must pass first")
 for job in [review["job"]]+([decoded["job"]]if"job"in decoded else[]):
  need(job.get("tag")==JOB and Path(job["native_output"]).resolve()==NATIVE.resolve() and
   Path(job["output_directory"]).resolve()==Path(run["output_directory"]).resolve(),"Actual reviewed native/output job binding differs")
 need((run["tag"],run["mode"],run["configuration"],run["scheme"],run["event_divisor"])==(JOB,"window2s","Release","B",1000) and
  run["clock"]["completed_updates"]==STEPS and run["clock"]["native_frames"]==N and run["clock"]["post_open_frames"]==POST,
  "Actual staged-load1263/199996 profile differs")
 need(review["staged_load_clock"]["rows"]==N and review["staged_load_clock"]["columns"]==44 and review["staged_load_clock"]["all_double_load_time_and_ramp_bits_equal"]is True and
  review["method_intervals"]["saved_interval_rows"]==N and review["method_intervals"]["noninitial_native_signed_bit_checks"]==N-1,
  "Genuine complete staged-load/signed review required")
 need(review["HG_original_guards"]["forcecalls"]==2*STEPS and review["HG_original_guards"]["predictorupdates"]==STEPS and review["HG_original_guards"]["correctorupdates"]==STEPS,
  "Original HG counters differ")
 done=ad.read(NATIVE/"completion.json")
 for k,v in dict(passed=True,samples=N,native_count=1000,fixed_count=40,total_native_count=1040,native_total_arrays=22,physical_columns=26,
  physical_schema="case02_common26_col21_ExcessPorePress_NOT_wave26",no_exclusions=True,all_exported_physical_fields_finite=True).items():need(done.get(k)==v,"Native declaration differs: "+k)
 need(ad.table(NATIVE/"columns.csv")==[dict(column=str(i),name=name)for i,name in enumerate(causal.FIELDS)],"Original26 schema differs")
 ids=ad.table(NATIVE/"native_ids.csv");need(len(ids)==1000 and [int(r["row"])for r in ids]==list(range(1000))and[int(r["id"])for r in ids]==list(range(40,1040)),"Original material ID/order differs")
 x0=np.array([[float(r[k])for k in ("x0","y0","z0")]for r in ids]);layer=np.rint(x0[:,2]/.01-.5).astype(int);column=np.rint(x0[:,0]/.01-.5).astype(int)
 need(np.array_equal(np.sort(10*layer+column),np.arange(1000)) and np.all(x0[:,1]==0),"Original100x10 lattice differs");order=np.argsort(10*layer+column)
 p=causal.binary(ad,NATIVE/"physical.bin",(1000,26,N),np.dtype([("t","<f8"),("q","<f8",(1000,26))]),np)
 n=causal.binary(ad,NATIVE/"soil_n.bin",(1000,1,N),np.dtype([("t","<f8"),("n","<f8",(1000,))]),np)
 clock=causal.binary(ad,NATIVE/"clock.bin",(N,28),np.dtype([("t","<f8"),("step","<u4"),("dt","<f8"),("signed","<f8")]),np)
 plan=ad.table(run["plan"]["path"]);history=ad.table(NATIVE/"history.csv");steps=np.array([int(r["completed_steps"])for r in plan],dtype=np.int64);times=np.array([float(r["time_s"])for r in plan],dtype="<f8")
 need(len(plan)==len(history)==N and steps[-1]==STEPS and times[-1]==END and np.all(np.diff(times)>0) and times.tobytes()==p["t"].tobytes()==n["t"].tobytes()==clock["t"].tobytes(),"Actual native clocks differ")
 need(np.array_equal(clock["step"],np.maximum(steps-1,0)) and np.all(clock["dt"]==DT) and np.isfinite(clock["signed"]).all() and np.all(clock["signed"][1:]<=1e-14) and np.all(clock["signed"][1:]!=-np.finfo(float).max),"Original Step/dt/nonempty signed gate differs")
 need(np.sum(steps>1000)==POST and 1000 in steps and 1001 in steps,"Preopen1000/post1001 coverage differs")
 for i,(r,h)in enumerate(zip(plan,history)):need(int(r["part"])==int(h["part"])==i and float(h["time_s"])==times[i] and int(h["completed_step"])==steps[i],"Native history association differs")
 need(np.isfinite(p["q"]).all() and np.isfinite(n["n"]).all(),"Nonfinite native fields")
 rho=np.empty((N,1000))
 with ad.pin(NATIVE/"ledger.csv").open(encoding="utf-8-sig",newline="")as f:
  reader=csv.DictReader(f)
  for count in range(N*1000):
   r=next(reader,None);need(r is not None,"Truncated native rho ledger");part,slot=divmod(count,1000)
   need(int(r["part"])==part and int(r["id"])==slot+40 and float(r["time_s"])==times[part] and float(r["J"])==p["q"][part,slot,8] and float(r["n_native"])==n["n"][part,slot],"Actual ledger ID/clock/J/n differs")
   rho[part,slot]=float(r["rho_native_kg_m3"])
  need(next(reader,None)is None,"Extra native ledger rows")
 need(np.isfinite(rho).all()and np.all(rho>0),"Native density invalid")
 spec=dict(label=LABELS["Bstaged"],native=NATIVE,declared=N,n=N,steps=STEPS,dt=DT,end=END,event=1000,post=POST)
 result["sources"]["Bstaged"]=dict(review=stat(REVIEW),read=stat(READ),run=stat(RUN),native_frames=N,completed_bounded_2s=True,full2Tv_completed=False)
 return dict(key="Bstaged",p=p,n=n,clock=clock,steps=steps,x0=x0,order=order,z0=x0[order,2].reshape(100,10).mean(axis=1),rho=rho,history=history,spec=spec,review=review)

def old_arrays(d,np):
 q=d["p"]["q"][:,d["order"]];P=q[:,:,6].reshape(N,100,10);settle=-1000*(q[:,:,:3][:,:,2]-d["x0"][d["order"],2]).reshape(N,100,10)
 effective=q[:,:,10:16].reshape(N,100,10,6);total=effective.copy();total[:,:,:,[0,3,5]]-=P[:,:,:,None]
 sign=np.where(np.arange(10)%2,-1.,1.);aUz=((-settle+settle.mean(axis=2,keepdims=True))*sign).mean(axis=2)
 aT=((total-total.mean(axis=2,keepdims=True))*sign[None,None,:,None]).mean(axis=2)
 d["arrays"]=dict(P=P,settle=settle,effective=effective,total=total,aUz=aUz,aT=aT)

def targets(new,old,constants,a_history,old_targets,old_profiles,np):
 rows,profiles,selections=[],[],{}
 for tv in TARGETS:
  target=prior.EVENT+tv/constants["Cv_M0_m2_s"];part=int(np.argmin(abs(new["clock"]["t"]-target)));r=new["rows"][part];o=old["rows"][part]
  original=[x for x in old_targets if x["series"]=="B10"and x["requested_legacy_Tv"]==tv];need(len(original)==1,"Preserved B10 target missing");a=original[0]
  need(int(a["actual_part"])==part and a["actual_time_s"]==r["time_s"],"Same-clock target association changed")
  ep,es,eb=r["P_layer_mean_profile_RMS_error_Pa"],abs(r["top_settlement_signed_error_mm"]),abs(r["bottom_settlement_signed_error_mm"])
  pp,sp,bp=ep<=a["A_P_layer_RMS_error_Pa"]+10.,es<=a["A_top_abs_error_mm"]+.001*constants["S_infinity_continuum_surface_mm"],eb<=.005 and eb<=a["A_bottom_abs_error_mm"]+.002
  rows.append(dict(series="Bstaged",requested_legacy_Tv=tv,target_time_s=target,actual_part=part,actual_time_s=r["time_s"],signed_target_gap_s=r["time_s"]-target,
   A_actual_part=a["A_actual_part"],A_actual_time_s=a["A_actual_time_s"],signed_own_minus_A_time_gap_s=r["time_s"]-a["A_actual_time_s"],A_reference="preserved finite_Kw at A actual time",B_reference="unfitted M0 at own actual time",
   A_P_layer_RMS_error_Pa=a["A_P_layer_RMS_error_Pa"],B_P_layer_RMS_error_Pa=ep,P_error_increment_vs_A_Pa=ep-a["A_P_layer_RMS_error_Pa"],P_increment_limit_Pa=10.,P_noninferiority_passed=pp,
   A_top_abs_error_mm=a["A_top_abs_error_mm"],B_top_abs_error_mm=es,top_abs_error_increment_vs_A_mm=es-a["A_top_abs_error_mm"],top_increment_limit_mm=.001*constants["S_infinity_continuum_surface_mm"],top_noninferiority_passed=sp,
   A_bottom_abs_error_mm=a["A_bottom_abs_error_mm"],B_bottom_abs_error_mm=eb,bottom_abs_limit_mm=.005,bottom_increment_limit_mm=.002,bottom_absolute_and_noninferiority_passed=bp,
   original_B10_P_RMS_error_Pa=o["P_layer_mean_profile_RMS_error_Pa"],original_B10_top_abs_error_mm=abs(o["top_settlement_signed_error_mm"]),original_B10_bottom_abs_error_mm=abs(o["bottom_settlement_signed_error_mm"]),
   own_minus_original_B10_P_RMS_error_Pa=ep-o["P_layer_mean_profile_RMS_error_Pa"],own_minus_original_B10_top_abs_error_mm=es-abs(o["top_settlement_signed_error_mm"]),own_minus_original_B10_bottom_abs_error_mm=eb-abs(o["bottom_settlement_signed_error_mm"]),
   original_B10_all_target_budgets_passed=a["all_original_target_budgets_passed"],all_original_target_budgets_passed=pp and sp and bp,new_budget_added=False,interpolation=False))
  selections[tv]=dict(B10=part,Bstaged=part,A=int(a["A_actual_part"]))
  for d in (old,new):
   for layer in range(100):profiles.append(dict(series=d["key"],requested_legacy_Tv=tv,target_time_s=target,actual_part=part,actual_time_s=r["time_s"],signed_target_gap_s=r["time_s"]-target,actual_legacy_Tv=r["legacy_Tv_since_drain"],applicable_reference_Tv=r["legacy_Tv_since_drain"],initial_layer=layer,z0_m=float(d["z0"][layer]),pressure_mean_Pa=float(d["arrays"]["P"][part,layer].mean()),material_settlement_mean_mm=float(d["arrays"]["settle"][part,layer].mean()),companion="M0",companion_pressure_Pa=float(d["ref"]["P"][part,layer]),companion_material_settlement_mm=float(d["ref"]["settle"][part,layer]),interpolation=False))
  aa=[x for x in old_profiles if x["series"]=="A"and x["requested_legacy_Tv"]==tv];need(len(aa)==100,"Preserved A target100-layer profile missing");profiles+=aa
 return rows,profiles,selections

def differences(new,old,layers,np):
 rows=[];oorder=old["order"]
 for i,r in enumerate(new["rows"]):
  o=old["rows"][i];a,z=new["p"]["q"][i],old["p"]["q"][i];delta=a[:,:3]-z[:,:3];delta[:,0]-=.1*np.floor(delta[:,0]/.1+.5)
  row=dict(part=i,actual_time_s=r["time_s"],completed_steps=r["completed_steps"],clock_bits_equal=True,same_material_IDs=True,native_pressure_RMS_difference_Pa=float(np.sqrt(np.mean((a[:,6]-z[:,6])**2))),native_pressure_abs_max_difference_Pa=float(np.max(abs(a[:,6]-z[:,6]))),material_XYZ_max_difference_mm=float(1000*np.max(np.linalg.norm(delta,axis=1))),interpolation=False,half_or_5Pa_equivalence_gate=False)
  for field in ("pressure_mean_Pa","top10_settlement_mm","bottom10_settlement_mm","Q_total_zz_second_difference_RMS_Pa","max_layer_total_error_Pa","top_pair_total_gap_Pa","J_mean","n_mean","rho_native_mean_kg_m3","A_pi_Uz_abs_max_mm","native_top_minus_bottom_settlement_mm","diagnostic_span_from_total_stress_mm","diagnostic_span_from_pressure_mm","diagnostic_span_from_J_minus1_mm","diagnostic_native_minus_stress_span_mm"):
   row["new_minus_old_"+field]=r[field]-o[field]
  for field in ("P_layer_mean_profile_RMS_error_Pa","top_settlement_signed_error_mm","bottom_settlement_signed_error_mm"):
   row["new_minus_old_"+field]=r[field]-o[field]if r[field]is not None else None
   row["new_minus_old_abs_"+field]=abs(r[field])-abs(o[field])if r[field]is not None else None
  rows.append(row)
  oj=z[oorder,8].reshape(100,10);on=old["n"]["n"][i,oorder].reshape(100,10);orho=old["rho"][i,oorder].reshape(100,10)
  for k in range(100):
   layer=layers[i*100+k]
   for name,value in (("P_mean_Pa",old["arrays"]["P"][i,k].mean()),("material_settlement_mean_mm",old["arrays"]["settle"][i,k].mean()),("J_mean",oj[k].mean()),("n_native_mean",on[k].mean()),("rho_native_mean_kg_m3",orho[k].mean()),("A_pi_Uz_signed_mm",old["arrays"]["aUz"][i,k])):
    layer["original_B10_"+name]=float(value);layer["new_minus_original_B10_"+name]=layer[name]-float(value)
   for j,name in enumerate(causal.COMPONENTS):
    value=float(old["arrays"]["total"][i,k,:,j].mean());layer["original_B10_total_sigma_"+name+"_mean_Pa"]=value;layer["new_minus_original_B10_total_sigma_"+name+"_mean_Pa"]=layer["total_sigma_"+name+"_mean_Pa"]-value
 return rows

def load_effect(ad,new):
 out=Path(new["review"]["job"]["output_directory"]);actual=ad.table(out/(native.runmod.SIDE+".csv"));need(len(actual)==N,"Actual saved loadclock rows missing")
 rows=[]
 for i,row in enumerate(actual):
  r=typed(row);need(int(r["part"])==i and r["actual_save_time_s"]==float(new["clock"]["t"][i]),"Real saved loadclock association differs")
  t=r["last_source_time_s"];old=10000.*max(0.,t)/prior.EVENT if t<prior.EVENT else 10000.
  r.update(original_P1_each_stage_expected_q_Pa=old,new_half_minus_original_q_Pa=r["last_half_q_double_Pa"]-old,new_endpoint_minus_original_q_Pa=r["last_endpoint_q_double_Pa"]-old,load_pressure_time_quadrature_is_not_actual_force_impulse=True);rows.append(r)
 t=0.;old_sum=0.;sums=[0.,0.,0.]
 for _ in range(STEPS):
  old=10000.*max(0.,t)/prior.EVENT if t<prior.EVENT else 10000.;old_sum+=old*DT
  for k,e in enumerate((t,t+.5*DT,t+DT)):sums[k]+=(10000.*max(0.,e)/prior.EVENT if e<prior.EVENT else 10000.)*DT
  t+=DT
 need(struct.pack("<d",t)==struct.pack("<d",END),"Diagnostic scalar source clock differs")
 return rows,dict(old_each_stage_sum_q_dt_Pa_s=old_sum,new_stage_sum_q_dt_Pa_s=sums,new_minus_old_stage_sum_q_dt_Pa_s=[s-old_sum for s in sums],not_force_impulse_or_energy_or_fluid_mass=True)

def figures(data,profiles,pairs,load,np):
 import matplotlib
 matplotlib.use("Agg")
 import matplotlib.pyplot as plt
 def draw(ax,field,low=None,high=None,reference=None):
  for key,d in data.items():
   rows=[r for r in d["rows"]if(low is None or r["time_s"]>=low)and(high is None or r["time_s"]<=high)]
   ax.plot([r["time_s"]for r in rows],[r[field]for r in rows],color=COLORS[key],lw=1.,label=LABELS[key])
   if reference:ax.plot([r["time_s"]for r in rows],[r[reference]for r in rows],color=COLORS[key],ls="--",lw=.7)
  ax.set(xlabel="Own actual saved time (s)",ylabel=field);ax.grid(True,alpha=.3)
 fig,axes=plt.subplots(3,2,figsize=(15,11),constrained_layout=True)
 for ax,field,ref in zip(axes.flat,("pressure_mean_Pa","top10_settlement_mm","bottom10_settlement_mm","P_layer_mean_profile_RMS_error_Pa","top_settlement_signed_error_mm","max_layer_total_error_Pa"),("companion_mean_pressure_Pa","companion_top_settlement_mm",None,None,None,None)):
  draw(ax,field,reference=ref)
  if field=="max_layer_total_error_Pa":ax.plot([.1,END],[100.,100.],"k--",lw=.8,label="Original post-.1s100Pa limit")
 axes[0,0].legend(fontsize=7);fig.suptitle("Bounded2s staged-load diagnostic; retained finite-Kw A failures preserved")
 save_png(fig,PRODUCTS["history.png"]);plt.close(fig)
 fig,axes=plt.subplots(3,2,figsize=(15,11),constrained_layout=True)
 for i,field in enumerate(("pressure_mean_Pa","J_mean")):
  for j,end in enumerate((.012,.15)):draw(axes[i,j],field,high=end);axes[i,j].axvline(prior.EVENT,color="k",ls=":",lw=.8);axes[i,j].set_xlim(0,end)
 for name,style in (("last_old_q_double_Pa","-"),("last_half_q_double_Pa","--"),("last_endpoint_q_double_Pa",":")):
  r=[x for x in load if x["actual_save_time_s"]<=.012];axes[2,0].plot([x["actual_save_time_s"]for x in r],[x[name]for x in r],style,label=name,lw=1.)
 axes[2,0].set(xlabel="Actual saved time (s)",ylabel="Last actual phase q (Pa)");axes[2,0].legend(fontsize=6);axes[2,0].grid(True,alpha=.3)
 draw(axes[2,1],"top10_settlement_mm",high=.15);axes[0,0].legend(fontsize=7);fig.suptitle("Unfiltered startup: source/half/endpoint load clock only; global drain unchanged")
 save_png(fig,PRODUCTS["startup.png"]);plt.close(fig)
 fig,axes=plt.subplots(3,2,figsize=(15,11),constrained_layout=True)
 for ax,field in zip(axes.flat,("P_layer_mean_profile_RMS_error_Pa","top_settlement_signed_error_mm","Q_total_zz_second_difference_RMS_Pa","A_pi_Uz_abs_max_mm","J_mean","rho_native_mean_kg_m3")):draw(ax,field,low=1.5);ax.set_xlim(1.5,END)
 axes[0,0].legend(fontsize=7);fig.suptitle("Actual1.5-2s: every material layer; no half/equivalence claim")
 save_png(fig,PRODUCTS["late.png"]);plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(13,10),constrained_layout=True)
 for j,tv in enumerate(TARGETS):
  for i,(field,ref,label)in enumerate((("pressure_mean_Pa","companion_pressure_Pa","Pressure (Pa)"),("material_settlement_mean_mm","companion_material_settlement_mm","Material settlement (mm)"))):
   ax=axes[i,j]
   for key in data:
    rows=[r for r in profiles if r["series"]==key and r["requested_legacy_Tv"]==tv];ax.plot([r[field]for r in rows],[r["z0_m"]for r in rows],color=COLORS[key],label=LABELS[key],lw=1.,marker="x"if key=="Bstaged"else"o",markevery=8,ms=3,fillstyle="none");ax.plot([r[ref]for r in rows],[r["z0_m"]for r in rows],color=COLORS[key],ls="--",lw=.7)
   ax.set(xlabel=label,ylabel="Initial material z0 (m)",title="Target legacy Tv=%g; actual clocks in CSV"%tv);ax.grid(True,alpha=.3)
 axes[0,0].legend(fontsize=7);fig.suptitle("Unfitted references: A finite-Kw, B M0; no radius/time/load fitting")
 save_png(fig,PRODUCTS["profiles.png"]);plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(15,10),constrained_layout=True)
 for i,(field,comp,label)in enumerate((("aUz",None,"Signed alternating-X Uz (mm)"),("aT",5,"Signed alternating total sigma zz (Pa)"))):
  vals={k:data[k]["arrays"][field]if comp is None else data[k]["arrays"][field][:,:,comp]for k in("B10","Bstaged")};span=max(float(np.max(abs(v)))for v in vals.values())or 1.
  for j,k in enumerate(("B10","Bstaged")):
   d=data[k];mesh=axes[i,j].pcolormesh(d["clock"]["t"],d["z0"],vals[k].T,shading="nearest",cmap="coolwarm",vmin=-span,vmax=span);fig.colorbar(mesh,ax=axes[i,j],label=label);axes[i,j].set(xlabel="Actual saved time (s)",ylabel="Initial z0 (m)",title=LABELS[k])
 fig.suptitle("All1263 actual saves /100 layers; shared range, no smoothing or clipping")
 save_png(fig,PRODUCTS["modes.png"]);plt.close(fig)
 fig,axes=plt.subplots(3,2,figsize=(15,11),constrained_layout=True);time=[r["actual_time_s"]for r in pairs]
 for ax,field in zip(axes.flat,("new_minus_old_top10_settlement_mm","new_minus_old_abs_top_settlement_signed_error_mm","native_pressure_RMS_difference_Pa","material_XYZ_max_difference_mm","new_minus_old_Q_total_zz_second_difference_RMS_Pa","new_minus_old_J_mean")):
  ax.plot(time,[r[field]for r in pairs],lw=1.);ax.set(xlabel="Exactly shared actual time (s)",ylabel=field);ax.grid(True,alpha=.3)
 fig.suptitle("Staged-load minus original-source-clock B: same dt/IDs/clocks, descriptive differences")
 save_png(fig,PRODUCTS["differences.png"]);plt.close(fig)

def science(ad,result):
 for k in("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):os.environ[k]="1"
 import numpy as np
 baseline=ad.read(OLD_METRICS);oldcheck=ad.read(causal.CHECK)
 need(oldcheck["analysis_complete"]is True and baseline["analysis_complete"]is True and baseline["physical_acceptance"]is False,"Preserved causal analysis required regardless of old budget failures")
 old=causal.load(ad,"B10",np,result);new=load_new(ad,np,result)
 need(old["x0"].tobytes()==new["x0"].tobytes()and old["steps"].tobytes()==new["steps"].tobytes()and old["clock"]["t"].tobytes()==new["clock"]["t"].tobytes()and old["clock"]["step"].tobytes()==new["clock"]["step"].tobytes()and old["clock"]["dt"].tobytes()==new["clock"]["dt"].tobytes(),"New/original B must share every actual time/step/dt and material ID; no nearest/interpolation")
 constants=causal.references(ad,{"B10":old,"Bstaged":new},np);need(constants==baseline["constants"],"Unfitted companion constants changed")
 retained=[typed(r)for r in ad.table(causal.PRODUCTS["history.csv"])];old["rows"]=[r for r in retained if r["series"]=="B10"];a_rows=[r for r in retained if r["series"]=="A"]
 need(len(old["rows"])==N and len(a_rows)==1292 and all(r["time_s"]==float(old["clock"]["t"][i])for i,r in enumerate(old["rows"])),"Actual preserved lightweight history differs")
 old_arrays(old,np);history,layers,failures=causal.describe(new,constants,np)
 oldtargets=[typed(r)for r in ad.table(causal.PRODUCTS["targets.csv"])];oldprofiles=[typed(r)for r in ad.table(causal.PRODUCTS["profiles.csv"])];budgets,profiles,selections=targets(new,old,constants,a_rows,oldtargets,oldprofiles,np)
 pairs=differences(new,old,layers,np);load,quadrature=load_effect(ad,new)
 events=[typed(r)for r in ad.table(causal.PRODUCTS["events.csv"])if r["series"]in("A","B10")]
 for label,part in(("initial",0),("event_preopen",int(np.flatnonzero(new["steps"]==1000)[0])),("first_postopen",int(np.flatnonzero(new["steps"]==1001)[0])),("nearest_0p15",int(np.argmin(abs(new["clock"]["t"]-.15)))),("nearest_1p5",int(np.argmin(abs(new["clock"]["t"]-1.5)))),("last_observed",N-1)):events.append(dict(event_selection=label,**new["rows"][part]))
 guard_pass=not failures;target_pass=all(r["all_original_target_budgets_passed"]for r in budgets)
 metrics=dict(stage=TAG,analysis_complete=True,source_full_completed=False,partial2s_only=True,physical_acceptance=False,constants=constants,
  reference_limits=baseline["reference_limits"],decomposition_limits=baseline["decomposition_limits"],total_stress_definition=baseline["total_stress_definition"],
  original_target_budgets=budgets,all_original_target_budgets_passed=target_pass,all_new_post01_100Pa_guards_passed=guard_pass,new_original_100Pa_failures=failures,
  preserved_old_100Pa_failures=baseline["original_post01_100Pa_failures"],original_B10_failure_preserved=True,old_A_failure_does_not_exempt_B=True,
  exactly_shared_B_states=N,all_actual_time_step_dt_bits_equal=True,signed_intervals_independently_guarded_not_required_equal=True,half_or_5Pa_equivalence_gate=False,interpolation_or_clock_rewrite=False,
  source_HG_and_three_force_evidence=dict(HG=new["review"]["HG_original_guards"],M0_intervals=new["review"]["method_intervals"],staged_load=new["review"]["staged_load_clock"]),
  load_pressure_time_quadrature_diagnostic=quadrature,schemes={},solver_invocations=0,native_invocations=0,raw_BI4_read=False,SHA_scans=0)
 for d in(old,new):
  rows=d["rows"];post=[r for r in rows if r["original_post_01_guard_applies"]];late=[r for r in rows if r["time_s"]>=1.5]
  metrics["schemes"][d["key"]]=dict(actual_saved_states=N,actual_end_s=END,final=rows[-1],post01_max_layer_total_error_Pa=max(r["max_layer_total_error_Pa"]for r in post),post01_max_top_pair_gap_Pa=max(r["top_pair_total_gap_Pa"]for r in post),late_saved_states=len(late),late_max_P_layer_RMS_error_Pa=max(r["P_layer_mean_profile_RMS_error_Pa"]for r in late),late_max_top_abs_error_mm=max(abs(r["top_settlement_signed_error_mm"])for r in late),max_alternating_Uz_mm=max(r["A_pi_Uz_abs_max_mm"]for r in rows))
 metrics["difference_extrema"]=dict(pressure_RMS_max_Pa=max(r["native_pressure_RMS_difference_Pa"]for r in pairs),material_XYZ_max_mm=max(r["material_XYZ_max_difference_mm"]for r in pairs),top_difference_absmax_mm=max(abs(r["new_minus_old_top10_settlement_mm"])for r in pairs))
 ad.finish()
 for name,rows in(("history.csv",a_rows+old["rows"]+history),("layers.csv",layers),("profiles.csv",profiles),("targets.csv",budgets),("differences.csv",pairs),("events.csv",events),("loadclock.csv",load)):write_csv(PRODUCTS[name],rows)
 write_json(PRODUCTS["metrics.json"],metrics);figures({"A":dict(rows=a_rows),"B10":old,"Bstaged":new},profiles,pairs,load,np);ad.finish()
 result.update(passed=True,analysis_complete=True,all_original_target_budgets_passed=target_pass,all_new_post01_100Pa_guards_passed=guard_pass,planned_budgets_passed=target_pass and guard_pass,source_full_completed=False,partial2s_only=True,
  rows=dict(history=len(a_rows)+2*N,new_all100_layers=len(layers),profiles=len(profiles),targets=len(budgets),same_clock_pairs=len(pairs),events=len(events),loadclock=len(load)),files=[stat(p)for p in PRODUCTS.values()],physical_acceptance=False)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");args=ap.parse_args()
 need(args.execution_authorized,"Root full-read one offline-only admission required");need(not CHECK.exists()and not any(p.exists()for p in PRODUCTS.values()),"Existing/partial scientific products protected")
 ad=Admission(args.admission);result=dict(stage=TAG,passed=False,analysis_complete=False,sources={},solver_invocations=0,native_invocations=0,build_invocations=0,SHA_scans=0,physical_acceptance=False,automatic_follow_up=False)
 try:science(ad,result)
 except Exception as exc:result.update(first_error=str(exc),partials_preserved=True);raise
 finally:result["consumed"]=list(ad.used.values());write_json(CHECK,result)
 print(str(CHECK));return 0 if result["passed"]else 1
if __name__=="__main__":raise SystemExit(main())
