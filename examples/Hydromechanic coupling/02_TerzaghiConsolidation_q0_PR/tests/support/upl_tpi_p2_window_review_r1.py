"""Offline P2 two-second adapter; preserve original budgets, no solver/reader or loadclock requirement."""
from __future__ import annotations
import argparse,csv,json,os,re,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
import upl_tpi_p1_loadclock_window_review_r1 as staged
import upl_tpi_p2_native_r1 as native
causal,prior=staged.causal,staged.prior
T=causal.T;TAG="upl_tpi_p2_window_review_r1";NOTE=T/"notes"/(TAG+".md");CHECK=T/"logs"/(TAG+".check.json")
N,STEPS,POST,DT,END=staged.N,staged.STEPS,staged.POST,staged.DT,staged.END
TARGETS=staged.TARGETS;need,stat,write_json,write_csv,save_png=causal.need,causal.stat,causal.write_json,causal.write_csv,causal.save_png
typed=staged.typed
LABELS={"A":"A: finite Kw, 6.25 us","B10":"B10: P1, 10 us","Bstaged":"Staged P1, 10 us","BP2":"P2: original clock, 10 us"}
COLORS={"A":"tab:blue","B10":"tab:orange","Bstaged":"tab:green","BP2":"tab:red"}
Y_LABELS={"pressure_mean_Pa":"Mean pore pressure (Pa)","top10_settlement_mm":"Top settlement (mm)","bottom10_settlement_mm":"Bottom settlement (mm)","P_layer_mean_profile_RMS_error_Pa":"Pressure-profile RMS error (Pa)","top_settlement_signed_error_mm":"Top signed error (mm)","max_layer_total_error_Pa":"Max layer stress error (Pa)","J_mean":"Mean volume ratio J (-)","speed_XYZ_RMS_m_s":"Speed RMS (m/s)","n_mean":"Mean porosity (-)","Q_total_zz_second_difference_RMS_Pa":"Stress curvature Q (Pa)","A_pi_Uz_abs_max_mm":"Max alternating Uz (mm)","rho_native_mean_kg_m3":"Mean density (kg/m^3)"}
DIFFERENCE_LABELS={"new_minus_old_top10_settlement_mm":"Top settlement change (mm)","new_minus_old_abs_top_settlement_signed_error_mm":"Top absolute-error change (mm)","native_pressure_RMS_difference_Pa":"Pressure RMS difference (Pa)","material_XYZ_max_difference_mm":"Max displacement difference (mm)","new_minus_old_Q_total_zz_second_difference_RMS_Pa":"Stress curvature Q change (Pa)","new_minus_old_J_mean":"Mean J change (-)"}
PRODUCTS={n:T/"figures"/(TAG+"."+n)for n in("history.csv","layers.csv","profiles.csv","targets.csv","differences.csv","staged_differences.csv","events.csv","metrics.json","history.png","startup.png","late.png","profiles.png","modes.png","differences.png")}
class Admission(causal.Admission):
 def __init__(self,path):
  self.entry=stat(path);self.data=json.loads(Path(path).read_text(encoding="utf-8-sig"));self.used={}
  need(self.data.get("stage")==TAG+".admission"and self.data.get("passed")is True and self.data.get("offline_only")is True,"One root-read offline-only P2 admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};need(len(self.frozen)==len(self.data["inputs"]),"Duplicate scientific input")
  self.job=self.data["job"]["tag"];need(re.fullmatch(r"upl_tpi_p2_[A-Za-z0-9_]+_r[1-9][0-9]*",self.job),"Exact fresh P2 job tag required")
  for p in(Path(__file__),NOTE,Path(staged.__file__),staged.NOTE,Path(causal.__file__),causal.NOTE,Path(prior.__file__),Path(native.__file__),native.NOTE,Path(native.runmod.__file__),native.runmod.NOTE,Path(native.m0.__file__),causal.BASE_XML,causal.PLAN_NOTE):self.pin(p)

def load_new(ad,np,result):
 tag=ad.job;runpath=T/"logs"/(tag+".run.json");readpath=T/"logs"/(tag+".native_p2_r1.json");reviewpath=T/"logs"/(tag+".native_review_p2_r1.json");directory=T/"outputs"/(tag+"_native_p2_r1")
 review,decoded,run=ad.read(reviewpath),ad.read(readpath),ad.read(runpath)
 need(review.get("stage")==native.TAG+".review"and review.get("passed")is True and review.get("all22_original_guards_not_relaxed")is True and decoded.get("stage")==native.TAG+".read"and decoded.get("passed")is True and decoded.get("reader_invocations")==1 and Path(decoded["native_output"]).resolve()==directory.resolve()and run.get("stage")==native.runmod.STAGE+".run"and run.get("passed")is True,"Actual P2 run/unique read/native review must pass first")
 for job in(review["job"],decoded["job"]):
  need(job["tag"]==tag and Path(job["native_output"]).resolve()==directory.resolve()and Path(job["output_directory"]).resolve()==Path(run["output_directory"]).resolve()and job["run_receipt"]==stat(runpath)and job["plan"]==run["plan"],"Actual reviewed P2 run/native/output binding differs")
 need((run["tag"],run["mode"],run["configuration"],run["scheme"],run["event_divisor"])==(tag,"window2s","Release","B",1000)and run["clock"]["completed_updates"]==STEPS and run["clock"]["native_frames"]==N and run["clock"]["post_open_frames"]==POST,"Actual P2 two-second profile differs")
 intervals,pressure,hg=review["method_intervals"],review["pressure_two_rounds"],review["HG_original_guards"]
 need(intervals["saved_interval_rows"]==N and intervals["noninitial_signed_bit_checks"]==N-1 and intervals["actual_force_phases"]==4 and intervals["added_ULP_tolerance"]==0 and pressure["actual_records"]==2*1000*N and pressure["paired_saved_IDs"]==1000*N and pressure["endpoint_rounds"]==2 and pressure["actual_q2_is_validated_p1"]is True and pressure["added_ULP_or_Pa_tolerance"]==0,"Genuine four-phase/both-round review required")
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
 need(len(plan)==len(history)==N and steps[-1]==STEPS and times[-1]==END and np.all(np.diff(times)>0)and times.tobytes()==p["t"].tobytes()==n["t"].tobytes()==clock["t"].tobytes(),"Actual P2 native clocks differ")
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
 spec=dict(label=LABELS["BP2"],native=directory,declared=N,n=N,steps=STEPS,dt=DT,end=END,event=1000,post=POST)
 result["sources"]["BP2"]=dict(review=stat(reviewpath),read=stat(readpath),run=stat(runpath),native_frames=N,completed_bounded_2s=True,full2Tv_completed=False)
 return dict(key="BP2",p=p,n=n,clock=clock,steps=steps,x0=x0,order=order,z0=x0[order,2].reshape(100,10).mean(axis=1),rho=rho,history=history,spec=spec,review=review)

def same_clock(a,b,np):
 need(a["x0"].tobytes()==b["x0"].tobytes()and a["steps"].tobytes()==b["steps"].tobytes()and all(a["clock"][k].tobytes()==b["clock"][k].tobytes()for k in("t","step","dt")),"All actual1263 material/clock/Step/dt states must match; no nearest/interpolation")

def staged_context(ad,new):
 check,metrics=ad.read(staged.CHECK),ad.read(staged.PRODUCTS["metrics.json"])
 need(check["stage"]==staged.TAG and check["passed"]is True and check["analysis_complete"]is True and metrics["stage"]==staged.TAG and metrics["analysis_complete"]is True and metrics["physical_acceptance"]is False,"Completed staged-load descriptive analysis required, irrespective of failed budgets")
 rows=[typed(r)for r in ad.table(staged.PRODUCTS["history.csv"])if r["series"]=="Bstaged"]
 need(len(rows)==N and all(r["part"]==i and r["completed_steps"]==int(new["steps"][i])and stat_bits(r["time_s"])==stat_bits(float(new["clock"]["t"][i]))and stat_bits(r["actual_dt_s"])==stat_bits(DT)for i,r in enumerate(rows)),"Staged lightweight actual clocks differ")
 return rows,metrics

def stat_bits(x):return struct.pack("<d",float(x))

def targets(new,old,constants,a_rows,oldtargets,oldprofiles,stagedtargets,stagedprofiles,np):
 # The original function owns all three original inequalities; only candidate labels and descriptive columns are adapted.
 rows,profiles,selections=staged.targets(new,old,constants,a_rows,oldtargets,oldprofiles,np)
 for r in rows:
  r["series"]="BP2";context=[x for x in stagedtargets if x["series"]=="Bstaged"and x["requested_legacy_Tv"]==r["requested_legacy_Tv"]];need(len(context)==1,"Preserved staged target missing");s=context[0]
  need(s["actual_part"]==r["actual_part"]and stat_bits(s["actual_time_s"])==stat_bits(r["actual_time_s"]),"Staged target actual clock differs")
  for source,target in(("B_P_layer_RMS_error_Pa","staged_P_RMS_error_Pa"),("B_top_abs_error_mm","staged_top_abs_error_mm"),("B_bottom_abs_error_mm","staged_bottom_abs_error_mm")):
   r[target]=s[source];r["own_minus_"+target]=r[source]-s[source]
  r["staged_all_target_budgets_passed"]=s["all_original_target_budgets_passed"]
 for selected in selections.values():selected["BP2"]=selected.pop("Bstaged")
 profiles.extend(r for r in stagedprofiles if r["series"]=="Bstaged")
 need(len(profiles)==800,"Original four-series/two-target/100-layer profiles required")
 return rows,profiles,selections

def scalar_staged_differences(new,context):
 fields=("pressure_mean_Pa","top10_settlement_mm","bottom10_settlement_mm","Q_total_zz_second_difference_RMS_Pa","max_layer_total_error_Pa","top_pair_total_gap_Pa","J_mean","n_mean","rho_native_mean_kg_m3","A_pi_Uz_abs_max_mm","native_top_minus_bottom_settlement_mm","diagnostic_span_from_pressure_mm","diagnostic_span_from_J_minus1_mm","diagnostic_native_minus_stress_span_mm")
 rows=[]
 for a,b in zip(new["rows"],context):
  r=dict(part=a["part"],actual_time_s=a["time_s"],completed_steps=a["completed_steps"],clock_bits_equal=True,comparison="BP2_minus_Bstaged",lightweight_scalar_only=True,per_ID_XYZ_or_pressure_difference_claimed=False,interpolation=False,half_or_5Pa_equivalence_gate=False)
  for f in fields:r["new_minus_old_"+f]=a[f]-b[f]
  for f in("P_layer_mean_profile_RMS_error_Pa","top_settlement_signed_error_mm","bottom_settlement_signed_error_mm"):
   r["new_minus_old_"+f]=a[f]-b[f]if a[f]is not None else None;r["new_minus_old_abs_"+f]=abs(a[f])-abs(b[f])if a[f]is not None else None
  rows.append(r)
 return rows

def figures(data,profiles,pairs,stagedpairs,np):
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
  decorate(fig,axes,"P2 bounded 2 s | "+name+" | original budgets retained",companions=name=="history",budget=name in("history","startup"))
  save_png(fig,PRODUCTS[name+".png"]);plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(13,10))
 for j,tv in enumerate(TARGETS):
  for i,(field,ref,label)in enumerate((("pressure_mean_Pa","companion_pressure_Pa","Pressure (Pa)"),("material_settlement_mean_mm","companion_material_settlement_mm","Material settlement (mm)"))):
   ax=axes[i,j]
   for key in data:
    rows=[r for r in profiles if r["series"]==key and r["requested_legacy_Tv"]==tv];ax.plot([r[field]for r in rows],[r["z0_m"]for r in rows],color=COLORS[key],label=LABELS[key],lw=1.,marker="x"if key=="BP2"else"o",markevery=8,ms=3,fillstyle="none");ax.plot([r[ref]for r in rows],[r["z0_m"]for r in rows],color=COLORS[key],ls="--",lw=.7)
   ax.set(xlabel=label,ylabel="Initial material z0 (m)",title="Legacy Tv=%g; actual target gaps in CSV"%tv);ax.grid(True,alpha=.3)
 decorate(fig,axes,"Actual target profiles | A finite Kw / B M0",companions=True);save_png(fig,PRODUCTS["profiles.png"]);plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(15,10),constrained_layout=True)
 for i,(field,comp,label)in enumerate((("aUz",None,"Signed alternating-X Uz (mm)"),("aT",5,"Signed alternating total sigma zz (Pa)"))):
  vals={k:data[k]["arrays"][field]if comp is None else data[k]["arrays"][field][:,:,comp]for k in("B10","BP2")};span=max(float(np.max(abs(v)))for v in vals.values())or 1.
  for j,k in enumerate(("B10","BP2")):
   d=data[k];mesh=axes[i,j].pcolormesh(d["clock"]["t"],d["z0"],vals[k].T,shading="nearest",cmap="coolwarm",vmin=-span,vmax=span);fig.colorbar(mesh,ax=axes[i,j],label=label);axes[i,j].set(xlabel="Actual saved time (s)",ylabel="Initial material z0 (m)",title=LABELS[k])
 fig.suptitle("Every1263 save /100 layers; no smoothing/clipping; staged context has lightweight scalar data only");save_png(fig,PRODUCTS["modes.png"]);plt.close(fig)
 fig,axes=plt.subplots(3,2,figsize=(15,11))
 for ax,field in zip(axes.flat,("new_minus_old_top10_settlement_mm","new_minus_old_abs_top_settlement_signed_error_mm","native_pressure_RMS_difference_Pa","material_XYZ_max_difference_mm","new_minus_old_Q_total_zz_second_difference_RMS_Pa","new_minus_old_J_mean")):
  for rows,label in((pairs,"P2 minus B10"),(stagedpairs,"P2 minus staged P1 (scalar)")):
   if field in rows[0]:ax.plot([r["actual_time_s"]for r in rows],[r[field]for r in rows],lw=1.,label=label)
  ax.set(xlabel="Shared saved time (s)",ylabel=DIFFERENCE_LABELS[field]);ax.grid(True,alpha=.3)
 decorate(fig,axes,"P2 descriptive differences | no interpolation or cross-method gate");save_png(fig,PRODUCTS["differences.png"]);plt.close(fig)

def science(ad,result):
 for k in("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):os.environ[k]="1"
 import numpy as np
 baseline=ad.read(causal.PRODUCTS["metrics.json"]);oldcheck=ad.read(causal.CHECK)
 need(oldcheck["analysis_complete"]is True and baseline["analysis_complete"]is True and baseline["physical_acceptance"]is False,"Completed preserved causal analysis required regardless of budget failures")
 old=causal.load(ad,"B10",np,result);new=load_new(ad,np,result);same_clock(old,new,np)
 constants=causal.references(ad,{"B10":old,"BP2":new},np);need(constants==baseline["constants"],"Original unfitted companion constants changed")
 retained=[typed(r)for r in ad.table(causal.PRODUCTS["history.csv"])];old["rows"]=[r for r in retained if r["series"]=="B10"];a_rows=[r for r in retained if r["series"]=="A"]
 need(len(old["rows"])==N and len(a_rows)==1292 and all(r["time_s"]==float(old["clock"]["t"][i])for i,r in enumerate(old["rows"])),"Preserved lightweight history association differs")
 context,stagedmetrics=staged_context(ad,new);staged.old_arrays(old,np);history,layers,failures=causal.describe(new,constants,np)
 oldtargets=[typed(r)for r in ad.table(causal.PRODUCTS["targets.csv"])];oldprofiles=[typed(r)for r in ad.table(causal.PRODUCTS["profiles.csv"])];stagedtargets=[typed(r)for r in ad.table(staged.PRODUCTS["targets.csv"])];stagedprofiles=[typed(r)for r in ad.table(staged.PRODUCTS["profiles.csv"])]
 budgets,profiles,selections=targets(new,old,constants,a_rows,oldtargets,oldprofiles,stagedtargets,stagedprofiles,np)
 pairs=staged.differences(new,old,layers,np);contextpairs=scalar_staged_differences(new,context)
 events=[typed(r)for r in ad.table(staged.PRODUCTS["events.csv"])if r["series"]in("A","B10","Bstaged")]+causal.events({"BP2":new},np)
 need(len(events)==24,"Six real events per four compared series required")
 guard_pass=not failures;target_pass=all(r["all_original_target_budgets_passed"]for r in budgets)
 metrics=dict(stage=TAG,analysis_complete=True,source_full_completed=False,partial2s_only=True,physical_acceptance=False,constants=constants,reference_limits=baseline["reference_limits"],decomposition_limits=baseline["decomposition_limits"],total_stress_definition=baseline["total_stress_definition"],original_target_budgets=budgets,all_original_target_budgets_passed=target_pass,all_new_post01_100Pa_guards_passed=guard_pass,new_original_100Pa_failures=failures,preserved_old_100Pa_failures=baseline["original_post01_100Pa_failures"],original_B10_failure_preserved=True,staged_failure_preserved=stagedmetrics["original_target_budgets"],old_A_failure_does_not_exempt_P2=True,exactly_shared_B_states=N,all_actual_time_step_dt_bits_equal=True,signed_intervals_independently_guarded_not_required_equal=True,half_or_5Pa_equivalence_gate=False,interpolation_or_clock_rewrite=False,source_HG_and_four_force_evidence=dict(HG=new["review"]["HG_original_guards"],M0_intervals=new["review"]["method_intervals"],P2_pressure=new["review"]["pressure_two_rounds"]),PorePressRate_is_second_round_scaled_residual_not_dpdt=True,staged_loadclock_sidecar_consumed=False,staged_native_binary_reloaded=False,schemes={},solver_invocations=0,native_invocations=0,raw_BI4_read=False,SHA_scans=0)
 for key,rows in(("A",a_rows),("B10",old["rows"]),("Bstaged",context),("BP2",history)):
  post=[r for r in rows if r["original_post_01_guard_applies"]];late=[r for r in rows if r["time_s"]>=1.5]
  metrics["schemes"][key]=dict(actual_saved_states=len(rows),actual_end_s=rows[-1]["time_s"],final=rows[-1],post01_max_layer_total_error_Pa=max(r["max_layer_total_error_Pa"]for r in post),post01_max_top_pair_gap_Pa=max(r["top_pair_total_gap_Pa"]for r in post),late_saved_states=len(late),late_max_P_layer_RMS_error_Pa=max(r["P_layer_mean_profile_RMS_error_Pa"]for r in late),late_max_top_abs_error_mm=max(abs(r["top_settlement_signed_error_mm"])for r in late),max_alternating_Uz_mm=max(r["A_pi_Uz_abs_max_mm"]for r in rows))
 metrics["difference_extrema_vs_original_B10"]=dict(pressure_RMS_max_Pa=max(r["native_pressure_RMS_difference_Pa"]for r in pairs),material_XYZ_max_mm=max(r["material_XYZ_max_difference_mm"]for r in pairs),top_difference_absmax_mm=max(abs(r["new_minus_old_top10_settlement_mm"])for r in pairs))
 result["sources"]["Bstaged"]=dict(check=stat(staged.CHECK),metrics=stat(staged.PRODUCTS["metrics.json"]),lightweight_tables_only=True,original_physical_acceptance=False)
 ad.finish()
 for name,rows in(("history.csv",a_rows+old["rows"]+context+history),("layers.csv",layers),("profiles.csv",profiles),("targets.csv",budgets),("differences.csv",pairs),("staged_differences.csv",contextpairs),("events.csv",events)):write_csv(PRODUCTS[name],rows)
 write_json(PRODUCTS["metrics.json"],metrics);figures({"A":dict(rows=a_rows),"B10":old,"Bstaged":dict(rows=context),"BP2":new},profiles,pairs,contextpairs,np);ad.finish()
 result.update(passed=True,analysis_complete=True,all_original_target_budgets_passed=target_pass,all_new_post01_100Pa_guards_passed=guard_pass,planned_budgets_passed=target_pass and guard_pass,source_full_completed=False,partial2s_only=True,rows=dict(history=len(a_rows)+3*N,new_all100_layers=len(layers),profiles=len(profiles),targets=len(budgets),same_clock_native_pairs=len(pairs),staged_scalar_pairs=len(contextpairs),events=len(events)),files=[stat(p)for p in PRODUCTS.values()],physical_acceptance=False)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");args=ap.parse_args()
 need(args.execution_authorized,"Root full-read one offline-only admission required");need(not CHECK.exists()and not any(p.exists()for p in PRODUCTS.values()),"Existing/partial P2 science products protected")
 ad=Admission(args.admission);result=dict(stage=TAG,passed=False,analysis_complete=False,sources={},solver_invocations=0,native_invocations=0,build_invocations=0,SHA_scans=0,physical_acceptance=False,automatic_follow_up=False)
 try:science(ad,result)
 except Exception as exc:result.update(first_error=str(exc),partials_preserved=True);raise
 finally:result["consumed"]=list(ad.used.values());write_json(CHECK,result)
 print(str(CHECK));return 0 if result["passed"]else 1
if __name__=="__main__":raise SystemExit(main())
