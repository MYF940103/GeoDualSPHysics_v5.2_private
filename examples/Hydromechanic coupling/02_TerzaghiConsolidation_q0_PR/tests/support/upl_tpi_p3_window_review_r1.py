"""Offline P3 bounded2s adapter; immutable original budgets, no solver/native/old-ledger reread."""
from __future__ import annotations
import argparse,csv,json,os,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
import upl_tpi_p2_window_review_r1 as p2
import upl_tpi_p3_native_r1 as native
staged,causal,prior=p2.staged,p2.causal,p2.prior
T=causal.T;TAG="upl_tpi_p3_window_review_r1";JOB="upl_tpi_p3_B10us_window2s_GPU_r1";P2JOB="upl_tpi_p2_B10us_window2s_GPU_r1"
NOTE=T/"notes"/(TAG+".md");CHECK=T/"logs"/(TAG+".check.json")
N,STEPS,POST,DT,END=p2.N,p2.STEPS,p2.POST,p2.DT,p2.END
TARGETS=p2.TARGETS;need,stat,write_json,write_csv,save_png=causal.need,causal.stat,causal.write_json,causal.write_csv,causal.save_png
typed=p2.typed
LABELS={"A":"A: finite Kw, 6.25 us","B10":"B10: P1, 10 us","BP2":"P2: original clock, 10 us","BP3":"P3: original clock, 10 us"}
COLORS={"A":"tab:blue","B10":"tab:orange","BP2":"tab:green","BP3":"tab:red"}
Y_LABELS=p2.Y_LABELS;DIFFERENCE_LABELS=p2.DIFFERENCE_LABELS
PRODUCTS={n:T/"figures"/(TAG+"."+n)for n in("history.csv","layers.csv","profiles.csv","targets.csv","differences.csv","B10_scalar_differences.csv","events.csv","metrics.json","history.png","startup.png","late.png","profiles.png","modes.png","differences.png")}
class Admission(causal.Admission):
 def __init__(self,path):
  self.entry=stat(path);self.data=json.loads(Path(path).read_text(encoding="utf-8-sig"));self.used={}
  need(self.data.get("stage")==TAG+".admission"and self.data.get("passed")is True and self.data.get("offline_only")is True and self.data.get("job",{}).get("tag")==JOB,"One root-read offline-only actual P3 admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};need(len(self.frozen)==len(self.data["inputs"]),"Duplicate scientific input")
  for q in(Path(__file__),NOTE,Path(p2.__file__),p2.NOTE,Path(staged.__file__),staged.NOTE,Path(causal.__file__),causal.NOTE,Path(prior.__file__),Path(native.__file__),native.NOTE,Path(native.runmod.__file__),native.runmod.NOTE,Path(native.m0.__file__),Path(p2.native.__file__),p2.native.NOTE,causal.BASE_XML,causal.PLAN_NOTE):self.pin(q)

def stat_bits(x):return struct.pack("<d",float(x))

def load_new(ad,np,result):
 tag=JOB;runpath=T/"logs"/(tag+".run.json");readpath=T/"logs"/(tag+".native_p3_r1.json");reviewpath=T/"logs"/(tag+".native_review_p3_r1.json");directory=T/"outputs"/(tag+"_native_p3_r1")
 review,decoded,run=ad.read(reviewpath),ad.read(readpath),ad.read(runpath)
 need(review.get("stage")==native.TAG+".review"and review.get("passed")is True and review.get("all22_original_guards_not_relaxed")is True and decoded.get("stage")==native.TAG+".read"and decoded.get("passed")is True and decoded.get("reader_invocations")==1 and Path(decoded["native_output"]).resolve()==directory.resolve()and run.get("stage")==native.runmod.STAGE+".run"and run.get("passed")is True,"Actual P3 run/unique read/native review must pass first")
 for job in(review["job"],decoded["job"]):
  need(job["tag"]==tag and Path(job["native_output"]).resolve()==directory.resolve()and Path(job["output_directory"]).resolve()==Path(run["output_directory"]).resolve()and job["run_receipt"]==stat(runpath)and job["plan"]==run["plan"],"Actual reviewed P3 run/native/output binding differs")
 need((run["tag"],run["mode"],run["configuration"],run["scheme"],run["event_divisor"])==(tag,"window2s","Release","B",1000)and run["clock"]["completed_updates"]==STEPS and run["clock"]["native_frames"]==N and run["clock"]["post_open_frames"]==POST,"Actual P3 two-second profile differs")
 intervals,pressure,hg=review["method_intervals"],review["pressure_three_rounds"],review["HG_original_guards"]
 need(intervals["saved_interval_rows"]==N and intervals["noninitial_signed_bit_checks"]==N-1 and intervals["actual_force_phases"]==5 and intervals["added_ULP_tolerance"]==0 and pressure["actual_records"]==3*1000*N and pressure["triplet_saved_IDs"]==1000*N and pressure["endpoint_rounds"]==3 and pressure["actual_q2_is_validated_p1"]is True and pressure["actual_q3_is_validated_p2"]is True and pressure["last_native_rate_is_R3_at_actual_p2_not_R_at_p3_or_dpdt"]is True and pressure["added_ULP_or_Pa_tolerance"]==0,"Genuine five-phase/all-three-round review required")
 need(hg["forcecalls"]==2*STEPS and hg["predictorupdates"]==hg["correctorupdates"]==STEPS,"Original HG physical counters differ")
 done=ad.read(directory/"completion.json")
 for k,v in dict(passed=True,samples=N,native_count=1000,fixed_count=40,total_native_count=1040,native_total_arrays=22,physical_columns=26,physical_schema="case02_common26_col21_ExcessPorePress_NOT_wave26",no_exclusions=True,all_exported_physical_fields_finite=True).items():need(done.get(k)==v,"Native declaration differs: "+k)
 need(ad.table(directory/"columns.csv")==[dict(column=str(i),name=name)for i,name in enumerate(causal.FIELDS)],"Original common26 schema differs")
 ids=ad.table(directory/"native_ids.csv");need(len(ids)==1000 and[int(r["row"])for r in ids]==list(range(1000))and[int(r["id"])for r in ids]==list(range(40,1040)),"Original material IDs/order differ")
 x0=np.array([[float(r[k])for k in("x0","y0","z0")]for r in ids]);layer=np.rint(x0[:,2]/.01-.5).astype(int);column=np.rint(x0[:,0]/.01-.5).astype(int)
 need(np.array_equal(np.sort(10*layer+column),np.arange(1000))and np.all(x0[:,1]==0),"Original100x10 lattice differs");order=np.argsort(10*layer+column)
 p=causal.binary(ad,directory/"physical.bin",(1000,26,N),np.dtype([("t","<f8"),("q","<f8",(1000,26))]),np)
 n=causal.binary(ad,directory/"soil_n.bin",(1000,1,N),np.dtype([("t","<f8"),("n","<f8",(1000,))]),np)
 clock=causal.binary(ad,directory/"clock.bin",(N,28),np.dtype([("t","<f8"),("step","<u4"),("dt","<f8"),("signed","<f8")]),np)
 plan=ad.table(run["plan"]["path"]);history=ad.table(directory/"history.csv");steps=np.array([int(r["completed_steps"])for r in plan],dtype=np.int64);times=np.array([float(r["time_s"])for r in plan],dtype="<f8")
 need(len(plan)==len(history)==N and steps[-1]==STEPS and times[-1]==END and np.all(np.diff(times)>0)and times.tobytes()==p["t"].tobytes()==n["t"].tobytes()==clock["t"].tobytes(),"Actual P3 native clocks differ")
 need(np.array_equal(clock["step"],np.maximum(steps-1,0))and np.all(clock["dt"]==DT)and np.isfinite(clock["signed"]).all()and np.all(clock["signed"][1:]<=1e-14)and np.all(clock["signed"][1:]!=-np.finfo(float).max),"Original Step/dt/nonempty signed gate differs")
 need(np.sum(steps>1000)==POST and 1000 in steps and 1001 in steps,"Preopen1000/post1001 coverage differs")
 for i,(r,h)in enumerate(zip(plan,history)):need(int(r["part"])==int(h["part"])==i and float(h["time_s"])==times[i]and int(h["completed_step"])==steps[i],"Native history association differs")
 need(np.isfinite(p["q"]).all()and np.isfinite(n["n"]).all(),"Nonfinite native fields");rho=np.empty((N,1000))
 with ad.pin(directory/"ledger.csv").open(encoding="utf-8-sig",newline="")as f:
  reader=csv.DictReader(f)
  for count in range(N*1000):
   r=next(reader,None);need(r is not None,"Truncated native rho ledger");part,slot=divmod(count,1000)
   need(int(r["part"])==part and int(r["id"])==slot+40 and float(r["time_s"])==times[part]and float(r["J"])==p["q"][part,slot,8]and float(r["n_native"])==n["n"][part,slot],"Actual ledger ID/clock/J/n differs");rho[part,slot]=float(r["rho_native_kg_m3"])
  need(next(reader,None)is None,"Extra native ledger rows")
 need(np.isfinite(rho).all()and np.all(rho>0),"Native density invalid")
 spec=dict(label=LABELS["BP3"],native=directory,declared=N,n=N,steps=STEPS,dt=DT,end=END,event=1000,post=POST)
 result["sources"]["BP3"]=dict(review=stat(reviewpath),read=stat(readpath),run=stat(runpath),native_frames=N,completed_bounded_2s=True,full2Tv_completed=False)
 return dict(key="BP3",p=p,n=n,clock=clock,steps=steps,x0=x0,order=order,z0=x0[order,2].reshape(100,10).mean(axis=1),rho=rho,history=history,spec=spec,review=review,run=run)

def load_context(ad,new,np,result):
 check,metrics=ad.read(p2.CHECK),ad.read(p2.PRODUCTS["metrics.json"])
 need(check["stage"]==p2.TAG and check["passed"]is True and check["analysis_complete"]is True and metrics["stage"]==p2.TAG and metrics["analysis_complete"]is True and metrics["physical_acceptance"]is False,"Completed genuine P2 science required; its failed budget stays failed")
 retained=[typed(r)for r in ad.table(p2.PRODUCTS["history.csv"])];rows={k:[r for r in retained if r["series"]==k]for k in("A","B10","BP2")}
 need([len(rows[k])for k in("A","B10","BP2")]==[1292,N,N],"Retained lightweight histories differ")
 directory=T/"outputs"/(P2JOB+"_native_p2_r1");rp=T/"logs"/(P2JOB+".run.json");rr=T/"logs"/(P2JOB+".native_review_p2_r1.json");rd=T/"logs"/(P2JOB+".native_p2_r1.json")
 review,decoded,run=ad.read(rr),ad.read(rd),ad.read(rp)
 need(review["stage"]==p2.native.TAG+".review"and review["passed"]is True and review["all22_original_guards_not_relaxed"]is True and decoded["stage"]==p2.native.TAG+".read"and decoded["passed"]is True and decoded["reader_invocations"]==1 and Path(decoded["native_output"]).resolve()==directory.resolve()and run["stage"]==p2.native.runmod.STAGE+".run"and run["passed"]is True,"Actual P2 native context required, not a renamed P3 source")
 for job in(review["job"],decoded["job"]):need(job["tag"]==P2JOB and job["run_receipt"]==stat(rp)and Path(job["native_output"]).resolve()==directory.resolve(),"Retained P2 run/native binding differs")
 need(run["clock"]["completed_updates"]==STEPS and run["clock"]["native_frames"]==N and run["plan"]==new["run"]["plan"],"P2 and P3 must use the same immutable scalar plan")
 done=ad.read(directory/"completion.json")
 for k,v in dict(passed=True,samples=N,native_count=1000,fixed_count=40,total_native_count=1040,native_total_arrays=22,physical_columns=26,physical_schema="case02_common26_col21_ExcessPorePress_NOT_wave26",no_exclusions=True,all_exported_physical_fields_finite=True).items():need(done.get(k)==v,"Retained P2 native declaration differs: "+k)
 need(ad.table(directory/"columns.csv")==[dict(column=str(i),name=name)for i,name in enumerate(causal.FIELDS)],"Retained P2 common26 schema differs")
 ids=ad.table(directory/"native_ids.csv");need(len(ids)==1000 and[int(r["row"])for r in ids]==list(range(1000))and[int(r["id"])for r in ids]==list(range(40,1040)),"Retained P2 material IDs differ")
 x0=np.array([[float(r[k])for k in("x0","y0","z0")]for r in ids]);need(x0.tobytes()==new["x0"].tobytes(),"P2/P3 original material positions differ")
 p=causal.binary(ad,directory/"physical.bin",(1000,26,N),np.dtype([("t","<f8"),("q","<f8",(1000,26))]),np)
 clock=causal.binary(ad,directory/"clock.bin",(N,28),np.dtype([("t","<f8"),("step","<u4"),("dt","<f8"),("signed","<f8")]),np)
 need(p["t"].tobytes()==clock["t"].tobytes()==new["clock"]["t"].tobytes()and all(clock[k].tobytes()==new["clock"][k].tobytes()for k in("step","dt"))and np.isfinite(p["q"]).all()and np.isfinite(clock["signed"]).all()and np.all(clock["signed"][1:]<=1e-14)and np.all(clock["signed"][1:]!=-np.finfo(float).max),"Retained P2 actual data/clock/signed differs")
 for key in("B10","BP2"):need(all(r["part"]==i and r["completed_steps"]==int(new["steps"][i])and stat_bits(r["time_s"])==stat_bits(float(clock["t"][i]))and stat_bits(r["actual_dt_s"])==stat_bits(DT)for i,r in enumerate(rows[key])),"Actual lightweight context clock differs: "+key)
 old=dict(key="BP2",p=p,clock=clock,steps=new["steps"],x0=x0,order=new["order"],z0=new["z0"],rows=rows["BP2"],spec=dict(dt=DT,event=1000),review=review)
 result["sources"]["retained_context"]=dict(science_check=stat(p2.CHECK),metrics=stat(p2.PRODUCTS["metrics.json"]),P2_native_review=stat(rr),P2_native_read=stat(rd),P2_run=stat(rp),old_A_B10_ledger_or_binary_reloaded=False,P2_ledger_or_soil_n_reloaded=False)
 return old,rows,metrics

def targets(new,old,contexts,constants,retained_targets,retained_profiles,np):
 # Literal original staged.targets inequalities; only context loading and names differ.
 budgets,profiles,selections=[],[],{}
 for tv in TARGETS:
  target=prior.EVENT+tv/constants["Cv_M0_m2_s"];part=int(np.argmin(abs(new["clock"]["t"]-target)));r=new["rows"][part];p2row=old["rows"][part];b10=contexts["B10"][part]
  stored=[x for x in retained_targets if x["series"]=="BP2"and x["requested_legacy_Tv"]==tv];need(len(stored)==1,"Retained P2 target missing");a=stored[0]
  need(a["actual_part"]==part and stat_bits(a["actual_time_s"])==stat_bits(r["time_s"]),"P2/P3 target actual sampling differs")
  ep,es,eb=r["P_layer_mean_profile_RMS_error_Pa"],abs(r["top_settlement_signed_error_mm"]),abs(r["bottom_settlement_signed_error_mm"])
  pp,sp,bp=ep<=a["A_P_layer_RMS_error_Pa"]+10.,es<=a["A_top_abs_error_mm"]+.001*constants["S_infinity_continuum_surface_mm"],eb<=.005 and eb<=a["A_bottom_abs_error_mm"]+.002
  need(a["P_increment_limit_Pa"]==10. and a["top_increment_limit_mm"]==.001*constants["S_infinity_continuum_surface_mm"]and a["bottom_abs_limit_mm"]==.005 and a["bottom_increment_limit_mm"]==.002,"Original numerical budgets changed")
  apart=int(a["A_actual_part"]);arow=contexts["A"][apart];need(arow["part"]==apart and stat_bits(arow["time_s"])==stat_bits(a["A_actual_time_s"]),"Retained A actual target differs")
  need(arow["P_layer_mean_profile_RMS_error_Pa"]==a["A_P_layer_RMS_error_Pa"]and abs(arow["top_settlement_signed_error_mm"])==a["A_top_abs_error_mm"]and abs(arow["bottom_settlement_signed_error_mm"])==a["A_bottom_abs_error_mm"],"Retained A target errors differ from original budget record")
  budgets.append(dict(series="BP3",requested_legacy_Tv=tv,target_time_s=target,actual_part=part,actual_time_s=r["time_s"],signed_target_gap_s=r["time_s"]-target,A_actual_part=apart,A_actual_time_s=a["A_actual_time_s"],signed_own_minus_A_time_gap_s=r["time_s"]-a["A_actual_time_s"],A_reference="retained_finite_Kw_at_A_actual_time",B_reference="unfitted_M0_at_own_actual_time",A_P_layer_RMS_error_Pa=a["A_P_layer_RMS_error_Pa"],B_P_layer_RMS_error_Pa=ep,P_error_increment_vs_A_Pa=ep-a["A_P_layer_RMS_error_Pa"],P_increment_limit_Pa=10.,P_noninferiority_passed=pp,A_top_abs_error_mm=a["A_top_abs_error_mm"],B_top_abs_error_mm=es,top_abs_error_increment_vs_A_mm=es-a["A_top_abs_error_mm"],top_increment_limit_mm=.001*constants["S_infinity_continuum_surface_mm"],top_noninferiority_passed=sp,A_bottom_abs_error_mm=a["A_bottom_abs_error_mm"],B_bottom_abs_error_mm=eb,bottom_abs_limit_mm=.005,bottom_increment_limit_mm=.002,bottom_absolute_and_noninferiority_passed=bp,P2_P_RMS_error_Pa=p2row["P_layer_mean_profile_RMS_error_Pa"],P2_top_abs_error_mm=abs(p2row["top_settlement_signed_error_mm"]),P2_bottom_abs_error_mm=abs(p2row["bottom_settlement_signed_error_mm"]),P2_all_original_target_budgets_passed=a["all_original_target_budgets_passed"],own_minus_P2_P_RMS_error_Pa=ep-p2row["P_layer_mean_profile_RMS_error_Pa"],own_minus_P2_top_abs_error_mm=es-abs(p2row["top_settlement_signed_error_mm"]),own_minus_P2_bottom_abs_error_mm=eb-abs(p2row["bottom_settlement_signed_error_mm"]),original_B10_P_RMS_error_Pa=b10["P_layer_mean_profile_RMS_error_Pa"],original_B10_top_abs_error_mm=abs(b10["top_settlement_signed_error_mm"]),original_B10_bottom_abs_error_mm=abs(b10["bottom_settlement_signed_error_mm"]),original_B10_all_target_budgets_passed=a["original_B10_all_target_budgets_passed"],all_original_target_budgets_passed=pp and sp and bp,new_budget_added=False,interpolation=False))
  selections[tv]=dict(BP3=part,BP2=part,B10=part,A=apart)
  for key in("A","B10","BP2"):
   selected=[x for x in retained_profiles if x["series"]==key and x["requested_legacy_Tv"]==tv];need(len(selected)==100 and all(x["actual_part"]==selections[tv][key]and stat_bits(x["actual_time_s"])==stat_bits(contexts[key][selections[tv][key]]["time_s"])for x in selected),"Retained100-layer target association differs: "+key);profiles.extend(selected)
  for layer in range(100):profiles.append(dict(series="BP3",requested_legacy_Tv=tv,target_time_s=target,actual_part=part,actual_time_s=r["time_s"],signed_target_gap_s=r["time_s"]-target,actual_legacy_Tv=r["legacy_Tv_since_drain"],applicable_reference_Tv=r["legacy_Tv_since_drain"],initial_layer=layer,z0_m=float(new["z0"][layer]),pressure_mean_Pa=float(new["arrays"]["P"][part,layer].mean()),material_settlement_mean_mm=float(new["arrays"]["settle"][part,layer].mean()),companion="M0",companion_pressure_Pa=float(new["ref"]["P"][part,layer]),companion_material_settlement_mm=float(new["ref"]["settle"][part,layer]),interpolation=False))
 return budgets,profiles,selections

def differences(new,old,layers,np):
 # Reuse staged.differences' true physical/XYZ arithmetic, without its old-n/rho ledger-dependent tail.
 rows=[];oorder=old["order"]
 for i,r in enumerate(new["rows"]):
  o=old["rows"][i];a,z=new["p"]["q"][i],old["p"]["q"][i];delta=a[:,:3]-z[:,:3];delta[:,0]-=.1*np.floor(delta[:,0]/.1+.5)
  row=dict(part=i,actual_time_s=r["time_s"],completed_steps=r["completed_steps"],clock_bits_equal=True,same_material_IDs=True,native_pressure_RMS_difference_Pa=float(np.sqrt(np.mean((a[:,6]-z[:,6])**2))),native_pressure_abs_max_difference_Pa=float(np.max(abs(a[:,6]-z[:,6]))),material_XYZ_max_difference_mm=float(1000*np.max(np.linalg.norm(delta,axis=1))),comparison="BP3_minus_BP2",interpolation=False,half_or_5Pa_equivalence_gate=False)
  for field in("pressure_mean_Pa","top10_settlement_mm","bottom10_settlement_mm","Q_total_zz_second_difference_RMS_Pa","max_layer_total_error_Pa","top_pair_total_gap_Pa","J_mean","n_mean","rho_native_mean_kg_m3","A_pi_Uz_abs_max_mm","native_top_minus_bottom_settlement_mm","diagnostic_span_from_total_stress_mm","diagnostic_span_from_pressure_mm","diagnostic_span_from_J_minus1_mm","diagnostic_native_minus_stress_span_mm"):row["new_minus_old_"+field]=r[field]-o[field]
  for field in("P_layer_mean_profile_RMS_error_Pa","top_settlement_signed_error_mm","bottom_settlement_signed_error_mm"):
   row["new_minus_old_"+field]=r[field]-o[field]if r[field]is not None else None;row["new_minus_old_abs_"+field]=abs(r[field])-abs(o[field])if r[field]is not None else None
  rows.append(row);oj=z[oorder,8].reshape(100,10)
  for k in range(100):
   layer=layers[i*100+k]
   for name,value in(("P_mean_Pa",old["arrays"]["P"][i,k].mean()),("material_settlement_mean_mm",old["arrays"]["settle"][i,k].mean()),("J_mean",oj[k].mean()),("A_pi_Uz_signed_mm",old["arrays"]["aUz"][i,k])):layer["P2_"+name]=float(value);layer["new_minus_P2_"+name]=layer[name]-float(value)
   for j,name in enumerate(causal.COMPONENTS):
    value=float(old["arrays"]["total"][i,k,:,j].mean());layer["P2_total_sigma_"+name+"_mean_Pa"]=value;layer["new_minus_P2_total_sigma_"+name+"_mean_Pa"]=layer["total_sigma_"+name+"_mean_Pa"]-value
 return rows

def figures(data,profiles,pairs,b10pairs,np):
 import matplotlib
 matplotlib.use("Agg")
 import matplotlib.pyplot as plt
 def decorate(fig,axes,title,companions=False,budget=False):
  # Reserve a real figure band; legends and reference explanations never occupy an axis.
  fig.subplots_adjust(left=.09,right=.98,bottom=.07,top=.83,hspace=.42,wspace=.35)
  handles,labels=axes.flat[0].get_legend_handles_labels()
  fig.legend(handles,labels,loc="upper center",bbox_to_anchor=(.5,.955),ncol=2,frameon=False,fontsize=8)
  fig.suptitle(title,y=.99,fontsize=13)
  explanation=[]
  if companions:explanation.append("Dashed: unfitted companion at each actual time")
  if budget:explanation.append("Dotted: 100 Pa stress limit after 0.1 s")
  if explanation:fig.text(.5,.885," | ".join(explanation),ha="center",fontsize=8)
 def draw(ax,field,low=None,high=None,reference=None):
  for key,d in data.items():
   rows=[r for r in d["rows"]if(low is None or r["time_s"]>=low)and(high is None or r["time_s"]<=high)]
   ax.plot([r["time_s"]for r in rows],[r[field]for r in rows],color=COLORS[key],lw=1.,label=LABELS[key])
   if reference:ax.plot([r["time_s"]for r in rows],[r[reference]for r in rows],color=COLORS[key],ls="--",lw=.7)
  ax.set(xlabel="Actual saved time (s)",ylabel=Y_LABELS[field]);ax.grid(True,alpha=.3)
 for name,fields,low,high in(("history",("pressure_mean_Pa","top10_settlement_mm","bottom10_settlement_mm","P_layer_mean_profile_RMS_error_Pa","top_settlement_signed_error_mm","max_layer_total_error_Pa"),None,None),("startup",("pressure_mean_Pa","J_mean","top10_settlement_mm","speed_XYZ_RMS_m_s","n_mean","max_layer_total_error_Pa"),None,.15),("late",("P_layer_mean_profile_RMS_error_Pa","top_settlement_signed_error_mm","Q_total_zz_second_difference_RMS_Pa","A_pi_Uz_abs_max_mm","J_mean","rho_native_mean_kg_m3"),1.5,None)):
  fig,axes=plt.subplots(3,2,figsize=(15,11))
  for ax,field in zip(axes.flat,fields):
   ref="companion_mean_pressure_Pa"if name=="history"and field=="pressure_mean_Pa"else("companion_top_settlement_mm"if name=="history"and field=="top10_settlement_mm"else None)
   draw(ax,field,low,high,ref)
   if name=="startup":ax.axvline(prior.EVENT,color="k",ls=":",lw=.8);ax.set_xlim(0,.15)
   if name=="late":ax.set_xlim(1.5,max(d["rows"][-1]["time_s"]for d in data.values()))
   if field=="max_layer_total_error_Pa":ax.plot([.1,END if high is None else high],[100.,100.],"k:",lw=.8,label="100 Pa limit after 0.1 s")
  decorate(fig,axes,"P3 bounded 2 s | "+name+" | original budgets retained",companions=name=="history",budget=name in("history","startup"))
  save_png(fig,PRODUCTS[name+".png"]);plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(13,10))
 for j,tv in enumerate(TARGETS):
  for i,(field,ref,label)in enumerate((("pressure_mean_Pa","companion_pressure_Pa","Pressure (Pa)"),("material_settlement_mean_mm","companion_material_settlement_mm","Material settlement (mm)"))):
   ax=axes[i,j]
   for key in data:
    rows=[r for r in profiles if r["series"]==key and r["requested_legacy_Tv"]==tv];ax.plot([r[field]for r in rows],[r["z0_m"]for r in rows],color=COLORS[key],label=LABELS[key],lw=1.,marker="x"if key=="BP3"else"o",markevery=8,ms=3,fillstyle="none");ax.plot([r[ref]for r in rows],[r["z0_m"]for r in rows],color=COLORS[key],ls="--",lw=.7)
   ax.set(xlabel=label,ylabel="Initial material z0 (m)",title="Legacy Tv=%g; actual target gaps in CSV"%tv);ax.grid(True,alpha=.3)
 decorate(fig,axes,"Actual target profiles | A finite Kw / B M0",companions=True);save_png(fig,PRODUCTS["profiles.png"]);plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(15,10),constrained_layout=True)
 for i,(field,comp,label)in enumerate((("aUz",None,"Signed alternating-X Uz (mm)"),("aT",5,"Signed alternating total sigma zz (Pa)"))):
  vals={k:data[k]["arrays"][field]if comp is None else data[k]["arrays"][field][:,:,comp]for k in("BP2","BP3")};span=max(float(np.max(abs(v)))for v in vals.values())or 1.
  for j,k in enumerate(("BP2","BP3")):
   d=data[k];mesh=axes[i,j].pcolormesh(d["clock"]["t"],d["z0"],vals[k].T,shading="nearest",cmap="coolwarm",vmin=-span,vmax=span);fig.colorbar(mesh,ax=axes[i,j],label=label);axes[i,j].set(xlabel="Actual saved time (s)",ylabel="Initial material z0 (m)",title=LABELS[k])
 fig.suptitle("Every1263 save /100 layers; no smoothing/clipping; B10 context has lightweight scalar data only");save_png(fig,PRODUCTS["modes.png"]);plt.close(fig)
 fig,axes=plt.subplots(3,2,figsize=(15,11))
 for ax,field in zip(axes.flat,("new_minus_old_top10_settlement_mm","new_minus_old_abs_top_settlement_signed_error_mm","native_pressure_RMS_difference_Pa","material_XYZ_max_difference_mm","new_minus_old_Q_total_zz_second_difference_RMS_Pa","new_minus_old_J_mean")):
  for rows,label in((pairs,"P3 minus P2"),(b10pairs,"P3 minus B10 (scalar)")):
   if field in rows[0]:ax.plot([r["actual_time_s"]for r in rows],[r[field]for r in rows],lw=1.,label=label)
  ax.set(xlabel="Shared saved time (s)",ylabel=DIFFERENCE_LABELS[field]);ax.grid(True,alpha=.3)
 decorate(fig,axes,"P3 descriptive differences | no interpolation or cross-method gate");save_png(fig,PRODUCTS["differences.png"]);plt.close(fig)

def science(ad,result):
 for k in("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):os.environ[k]="1"
 import numpy as np
 new=load_new(ad,np,result);old,contexts,baseline=load_context(ad,new,np,result)
 constants=causal.references(ad,{"BP3":new},np);need(constants==baseline["constants"],"Original unfitted companion constants changed")
 staged.old_arrays(old,np);history,layers,failures=causal.describe(new,constants,np)
 retainedtargets=[typed(r)for r in ad.table(p2.PRODUCTS["targets.csv"])];retainedprofiles=[typed(r)for r in ad.table(p2.PRODUCTS["profiles.csv"])]
 budgets,profiles,selections=targets(new,old,contexts,constants,retainedtargets,retainedprofiles,np)
 pairs=differences(new,old,layers,np);b10pairs=p2.scalar_staged_differences(new,contexts["B10"])
 for r in b10pairs:r["comparison"]="BP3_minus_B10"
 events=[typed(r)for r in ad.table(p2.PRODUCTS["events.csv"])if r["series"]in("A","B10","BP2")]+causal.events({"BP3":new},np)
 need(len(events)==24 and len(profiles)==800,"Four series /six events /two100-layer targets required")
 guard_pass=not failures;target_pass=all(r["all_original_target_budgets_passed"]for r in budgets)
 metrics=dict(stage=TAG,analysis_complete=True,source_full_completed=False,partial2s_only=True,physical_acceptance=False,constants=constants,reference_limits=baseline["reference_limits"],decomposition_limits=baseline["decomposition_limits"],total_stress_definition=baseline["total_stress_definition"],original_target_budgets=budgets,all_original_target_budgets_passed=target_pass,all_new_post01_100Pa_guards_passed=guard_pass,new_original_100Pa_failures=failures,preserved_old_100Pa_failures=baseline["preserved_old_100Pa_failures"],preserved_P2_target_budgets=baseline["original_target_budgets"],preserved_P2_post01_100Pa_failures=baseline["new_original_100Pa_failures"],P2_failed_budget_not_reclassified=True,preserved_P2_all_target_budgets_passed=baseline["all_original_target_budgets_passed"],preserved_P2_all_post01_100Pa_guards_passed=baseline["all_new_post01_100Pa_guards_passed"],earlier_staged_conclusion_preserved=baseline["staged_failure_preserved"],old_A_failure_does_not_exempt_P3=True,exactly_shared_P2_P3_states=N,all_actual_time_step_dt_bits_equal=True,signed_intervals_independently_guarded_not_required_equal=True,half_or_5Pa_equivalence_gate=False,interpolation_or_clock_rewrite=False,source_HG_and_five_force_evidence=dict(HG=new["review"]["HG_original_guards"],M0_intervals=new["review"]["method_intervals"],P3_pressure=new["review"]["pressure_three_rounds"]),PorePressRate_is_R3_at_actual_p2_not_R_at_p3_or_dpdt=True,new_P3_ledger_passes=1,old_A_B10_P2_ledgers_reloaded=False,staged_dataset_reloaded=False,P2_layer_n_rho_fabricated=False,schemes={},solver_invocations=0,native_invocations=0,raw_BI4_read=False,SHA_scans=0)
 for key,rows in[(k,contexts[k])for k in("A","B10","BP2")]+[("BP3",history)]:
  post=[r for r in rows if r["original_post_01_guard_applies"]];late=[r for r in rows if r["time_s"]>=1.5]
  metrics["schemes"][key]=dict(actual_saved_states=len(rows),actual_end_s=rows[-1]["time_s"],final=rows[-1],post01_max_layer_total_error_Pa=max(r["max_layer_total_error_Pa"]for r in post),post01_max_top_pair_gap_Pa=max(r["top_pair_total_gap_Pa"]for r in post),late_saved_states=len(late),late_max_P_layer_RMS_error_Pa=max(r["P_layer_mean_profile_RMS_error_Pa"]for r in late),late_max_top_abs_error_mm=max(abs(r["top_settlement_signed_error_mm"])for r in late),max_alternating_Uz_mm=max(r["A_pi_Uz_abs_max_mm"]for r in rows))
 metrics["difference_extrema_vs_P2"]=dict(pressure_RMS_max_Pa=max(r["native_pressure_RMS_difference_Pa"]for r in pairs),material_XYZ_max_mm=max(r["material_XYZ_max_difference_mm"]for r in pairs),top_difference_absmax_mm=max(abs(r["new_minus_old_top10_settlement_mm"])for r in pairs))
 ad.finish()
 for name,rows in(("history.csv",contexts["A"]+contexts["B10"]+contexts["BP2"]+history),("layers.csv",layers),("profiles.csv",profiles),("targets.csv",budgets),("differences.csv",pairs),("B10_scalar_differences.csv",b10pairs),("events.csv",events)):write_csv(PRODUCTS[name],rows)
 write_json(PRODUCTS["metrics.json"],metrics);figures({"A":dict(rows=contexts["A"]),"B10":dict(rows=contexts["B10"]),"BP2":old,"BP3":new},profiles,pairs,b10pairs,np);ad.finish()
 result.update(passed=True,analysis_complete=True,all_original_target_budgets_passed=target_pass,all_new_post01_100Pa_guards_passed=guard_pass,planned_budgets_passed=target_pass and guard_pass,source_full_completed=False,partial2s_only=True,rows=dict(history=1292+3*N,new_all100_layers=len(layers),profiles=len(profiles),targets=len(budgets),same_clock_native_pairs=len(pairs),B10_scalar_pairs=len(b10pairs),events=len(events)),files=[stat(q)for q in PRODUCTS.values()],physical_acceptance=False)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");args=ap.parse_args()
 need(args.execution_authorized,"Root full-read one offline-only admission required");need(not CHECK.exists()and not any(q.exists()for q in PRODUCTS.values()),"Existing/partial P3 science products protected")
 ad=Admission(args.admission);result=dict(stage=TAG,passed=False,analysis_complete=False,sources={},solver_invocations=0,native_invocations=0,build_invocations=0,SHA_scans=0,physical_acceptance=False,automatic_follow_up=False)
 try:science(ad,result)
 except Exception as exc:result.update(first_error=str(exc),partials_preserved=True);raise
 finally:result["consumed"]=list(ad.used.values());write_json(CHECK,result)
 print(str(CHECK));return 0 if result["passed"]else 1
if __name__=="__main__":raise SystemExit(main())
