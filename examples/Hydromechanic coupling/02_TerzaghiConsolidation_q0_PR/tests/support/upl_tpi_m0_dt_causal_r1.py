"""Offline observed2s A/B6.25us/B10us diagnosis; never a physical acceptance."""
from __future__ import annotations
import argparse,csv,json,math,os,struct
from pathlib import Path
import xml.etree.ElementTree as ET
import upl_tpi_m0_B10us_review_r1 as prior

T=Path(__file__).resolve().parents[1];TAG="upl_tpi_m0_dt_causal_r1"
NOTE=T/"notes"/(TAG+".md");CHECK=T/"logs"/(TAG+".check.json")
BASE_XML=prior.BASE_XML;PLAN_NOTE=prior.PLAN_NOTE;FIELDS=prior.FIELDS;COMPONENTS=prior.COMPONENTS
PARTIAL_TAG="upl_tpi_gpu_partial2s_native_r1";SOURCE_TAG="upl_tpi_gpu_Release_B_full2tv_r1"
PARTIAL_REVIEW=T/"logs"/(PARTIAL_TAG+".review.json");PARTIAL_READ=T/"logs"/(PARTIAL_TAG+".read.json")
SPECS={
 "A":dict(label="Retained A finite-Kw CPU1, 6.25us",native=prior.T/"outputs/upl_bigstep_2tv_CPU1_r1_native_r1",declared=1682,n=1292,steps=320001,dt=6.250143051147461e-6,end=2.0000520265024098,event=1600,post=1174),
 "B625":dict(label="Stopped B M0 GPU, 6.25us prefix",native=T/"outputs"/(SOURCE_TAG+"_observed_partial_2s_native_r1"),declared=1292,n=1292,steps=320001,dt=6.250143051147461e-6,end=2.0000520265024098,event=1600,post=1174),
 "B10":dict(label="New B M0 GPU, 10us window",native=prior.NATIVE,declared=1263,n=1263,steps=199996,dt=prior.DT,end=prior.END,event=1000,post=1159)}
COLORS={"A":"tab:blue","B625":"tab:purple","B10":"tab:orange"};TARGETS=(.005,.05)
PRODUCTS={n:T/"figures"/(TAG+"."+n)for n in ("history.csv","layers.csv","profiles.csv","targets.csv","nearest.csv","events.csv","metrics.json","history.png","startup.png","late.png","profiles.png","modes.png","nearest.png")}
need,stat,write_json,write_csv,save_png=prior.need,prior.stat,prior.write_json,prior.write_csv,prior.save_png


class Admission:
 def __init__(self,path):
  self.entry=stat(path);self.data=json.loads(Path(path).read_text(encoding="utf-8-sig"))
  need(self.data.get("stage")==TAG+".admission"and self.data.get("passed")is True and self.data.get("offline_only")is True,"One root-read offline-only admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};self.used={}
  need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")
  for p in (Path(__file__),NOTE,Path(prior.__file__),BASE_XML,PLAN_NOTE):self.pin(p)
 def pin(self,path):
  key=str(Path(path).resolve());need(key in self.frozen,"Unadmitted scientific input: "+key)
  old={k:self.frozen[key][k]for k in ("path","bytes","mtime_ns")};need(stat(key)==old,"Frozen scientific input changed: "+key);self.used[key]=old;return Path(key)
 def read(self,p):return json.loads(self.pin(p).read_text(encoding="utf-8-sig"))
 def table(self,p):
  with self.pin(p).open(encoding="utf-8-sig",newline="")as f:return list(csv.DictReader(f))
 def finish(self):
  for e in self.used.values():need(stat(e["path"])==e,"Scientific input changed during diagnosis")
  need(stat(self.entry["path"])==self.entry,"Root admission changed")


def binary(ad,path,header,dtype,np):
 path=ad.pin(path);size=4*len(header)
 with path.open("rb")as f:need(struct.unpack("<"+"I"*len(header),f.read(size))==header,"Original declared binary header differs: "+path.name)
 count=header[-1]if len(header)==3 else header[0]
 need(path.stat().st_size==size+count*dtype.itemsize,"Original binary count/stride differs")
 return np.memmap(path,dtype=dtype,mode="r",offset=size,shape=(count,))


def load(ad,key,np,result):
 s=SPECS[key];directory=s["native"]
 if key=="A":
  review=ad.read(prior.A_REVIEW);decoded=ad.read(T/"logs/upl_bigstep_full_r1.native.json")
  need(review.get("passed")is True and review.get("stage")=="upl_bigstep_full_review_r1.review"and decoded.get("stage")=="upl_bigstep_full_review_r1.native"and decoded.get("passed")is True and decoded.get("original_native_guards_passed")is True,"Retained finite-Kw A native/descriptive qualification required")
  need(Path(decoded["directory"]).resolve()==directory.resolve(),"Retained A directory differs");planpath=decoded["clock_CSV"]["path"]
  provenance=dict(original_full_A_completed=True,original_physical_acceptance=False,review=stat(prior.A_REVIEW),native=stat(T/"logs/upl_bigstep_full_r1.native.json"))
 elif key=="B625":
  review,decoded=ad.read(PARTIAL_REVIEW),ad.read(PARTIAL_READ)
  need(review.get("passed")is True and review.get("stage")==PARTIAL_TAG+".review"and review.get("all22_original_prefix_guards_not_relaxed")is True
       and review.get("partial_observation")is True and review.get("source_full_completed")is False,"Unique stopped-prefix native review required")
  need(decoded.get("stage")==PARTIAL_TAG+".read"and decoded.get("passed")is True and decoded.get("reader_invocations")==1 and Path(decoded["native_output"]).resolve()==directory.resolve(),"Unique partial native read required")
  job=review["job"];need(job["source_full_completed"]is False and job["partial_observation"]is True and Path(job["native_output"]).resolve()==directory.resolve(),"Stopped source must remain incomplete");planpath=job["plan"]["path"]
  provenance=dict(source_full_completed=False,partial_observation=True,review=stat(PARTIAL_REVIEW),native=stat(PARTIAL_READ),stop=job["source_retirement_result"])
 else:
  review,decoded,run=ad.read(prior.REVIEW),ad.read(prior.READ),ad.read(prior.RUN)
  need(review.get("stage")=="upl_tpi_m0_dt_native_r1.review"and review.get("passed")is True and review.get("all22_original_guards_not_relaxed")is True and review.get("method_signed_interval_bit_replay")is True
       and decoded.get("stage")=="upl_tpi_m0_dt_native_r1.read"and decoded.get("passed")is True and decoded.get("reader_invocations")==1 and run.get("passed")is True,"Actual B10us native/run qualifications required")
  need(Path(decoded["native_output"]).resolve()==directory.resolve()and run["clock"]["completed_updates"]==s["steps"]and run["event_divisor"]==1000,"B10us source profile differs")
  planpath=run["plan"]["path"];oldscience=ad.read(prior.CHECK)
  need(oldscience.get("stage")==prior.TAG and oldscience.get("analysis_complete")is True,"Prior B10us scientific analysis must be preserved even when its top budget failed")
  provenance=dict(full2Tv_completed=False,completed_bounded_2s=True,review=stat(prior.REVIEW),native=stat(prior.READ),prior_science=stat(prior.CHECK),prior_science_passed=oldscience["passed"])
 done=ad.read(directory/"completion.json")
 required=dict(passed=True,samples=s["declared"],native_count=1000,fixed_count=40,total_native_count=1040,native_total_arrays=22,physical_columns=26,
               physical_schema="case02_common26_col21_ExcessPorePress_NOT_wave26",no_exclusions=True,all_exported_physical_fields_finite=True)
 for name,value in required.items():need(done.get(name)==value,"Native declaration differs: "+key+"/"+name)
 if key=="B625":need(done.get("source_full_completed")is False and done.get("partial_observation")is True and done.get("declared_window_complete")is False,"Partial native result mislabelled as full")
 need(ad.table(directory/"columns.csv")==[dict(column=str(i),name=name)for i,name in enumerate(FIELDS)],"Case02 physical schema differs")
 ids=ad.table(directory/"native_ids.csv");need(len(ids)==1000 and [int(r["row"])for r in ids]==list(range(1000))and [int(r["id"])for r in ids]==list(range(40,1040)),"Original1000 material IDs/order differ")
 x0=np.array([[float(r[c])for c in ("x0","y0","z0")]for r in ids]);layer=np.rint(x0[:,2]/.01-.5).astype(int);column=np.rint(x0[:,0]/.01-.5).astype(int)
 need(np.array_equal(np.sort(10*layer+column),np.arange(1000))and np.all((layer>=0)&(layer<100))and np.all((column>=0)&(column<10))and np.all(x0[:,1]==0),"Original100-by10 lattice differs");order=np.argsort(10*layer+column)
 declared=s["declared"];p=binary(ad,directory/"physical.bin",(1000,26,declared),np.dtype([("t","<f8"),("q","<f8",(1000,26))]),np)[:s["n"]]
 n=binary(ad,directory/"soil_n.bin",(1000,1,declared),np.dtype([("t","<f8"),("n","<f8",(1000,))]),np)[:s["n"]]
 clock=binary(ad,directory/"clock.bin",(declared,28),np.dtype([("t","<f8"),("step","<u4"),("dt","<f8"),("signed","<f8")]),np)[:s["n"]]
 plan=ad.table(planpath)[:s["n"]];history=ad.table(directory/"history.csv")[:s["n"]]
 times=np.array([float(r["time_s"])for r in plan],dtype="<f8");steps=np.array([int(r["completed_steps"])for r in plan],dtype=np.int64)
 need(len(plan)==len(history)==s["n"]and steps[-1]==s["steps"]and times[-1]==s["end"]and np.all(np.diff(times)>0)
      and times.tobytes()==p["t"].tobytes()==n["t"].tobytes()==clock["t"].tobytes(),"Each trajectory must preserve its own actual saved clocks")
 need(np.array_equal(clock["step"],np.maximum(steps-1,0))and np.all(clock["dt"]==s["dt"])and np.isfinite(clock["signed"]).all()
      and np.all(clock["signed"][1:]<=1e-14)and np.all(clock["signed"][1:]!=-np.finfo(float).max),"Original Step/dt/signed nonempty gate differs")
 need(int(np.sum(steps>s["event"]))==s["post"]and s["event"]in steps and s["event"]+1 in steps,"Original preopen/post event coverage differs")
 for i,(r,h)in enumerate(zip(plan,history)):need(int(r["part"])==int(h["part"])==i and float(h["time_s"])==times[i]and int(h["completed_step"])==steps[i],"Native history association differs")
 need(np.isfinite(p["q"]).all()and np.isfinite(n["n"]).all(),"Nonfinite selected native data")
 rho=np.empty((s["n"],1000))
 with ad.pin(directory/"ledger.csv").open(encoding="utf-8-sig",newline="")as f:
  reader=csv.DictReader(f)
  for count in range(s["n"]*1000):
   r=next(reader,None);need(r is not None,"Truncated selected native rho ledger");part,slot=divmod(count,1000)
   need(int(r["part"])==part and int(r["id"])==slot+40 and float(r["time_s"])==times[part]and float(r["J"])==p["q"][part,slot,8]and float(r["n_native"])==n["n"][part,slot],"Native ledger clock/ID/J/n differs")
   rho[part,slot]=float(r["rho_native_kg_m3"])
  if key!="A":need(next(reader,None)is None,"Extra records in complete selected native export")
 need(np.isfinite(rho).all()and np.all(rho>0),"Native rho must be finite positive")
 result["sources"][key]=dict(label=s["label"],selected_saved_states=s["n"],original_file_declared_states=declared,source=provenance,
     source_full_completed=False if key!="A"else True,comparison_is_partial2s_only=True,raw_BI4_read=False,new_native_invocations=0)
 return dict(key=key,p=p,n=n,clock=clock,steps=steps,x0=x0,order=order,z0=x0[order,2].reshape(100,10).mean(axis=1),rho=rho,history=history,spec=s)


def references(ad,data,np):
 root=ET.parse(ad.pin(BASE_XML)).getroot();v=lambda name:float(next(root.iter(name)).get("value"))
 values=[v(n)for n in ("ModulusE","PRvs","HydraulicConductivity","PoreWaterRho","PoreWaterBulkModulus","Porosity","HydroMechTopLoadQ0","HydroMechDrainageStartTime","HydroMechTopLoadRampTime")]
 need(values==[2e6,.3,1e-4,1000.,2e8,.3,10000.,prior.EVENT,prior.EVENT],"Original unfitted companion constants changed")
 E,nu,k,water,Kw,n0,q0,tD,ramp=values;H,g=1.,9.81;M=E*(1-nu)/((1+nu)*(1-2*nu));Cv=k*M/(water*g);cap=1/(1+n0*M/Kw)
 lam=(np.arange(512)+.5)*np.pi;coef=2*(-1.)**np.arange(512)/lam
 for key,d in data.items():
  capacity=cap if key=="A"else 1.;times=d["clock"]["t"];valid=times>=tD;P=np.full((len(times),100),np.nan);settle=P.copy()
  decay=np.exp(-capacity*Cv*lam[None,:]**2*(times[valid,None]-tD)/H**2);co=np.cos(lam[:,None]*d["z0"][None,:]/H);si=np.sin(lam[:,None]*d["z0"][None,:]/H)
  P[valid]=capacity*q0*((decay*coef)@co);settle[valid]=1000*q0/M*(d["z0"][None,:]-H*capacity*((decay*coef/lam)@si))
  d["ref"]=dict(P=P,settle=settle,capacity=capacity,name="finite_Kw"if key=="A"else"M0")
 return dict(E_Pa=E,nu=nu,Mc_reference_Pa=M,k_m_s=k,rhow_kg_m3=water,Kw_XML_Pa=Kw,n0=n0,q0_Pa=q0,H_m=H,
     drain_time_s=tD,ramp_time_s=ramp,reference_g_m_s2=g,Cv_M0_m2_s=Cv,Cv_finite_Kw_m2_s=cap*Cv,finite_Kw_capacity=cap,
     S_infinity_continuum_surface_mm=1000*q0*H/M,series_modes=512)


def describe(d,c,np):
 rows,layers,failures=[],[],[];sign=np.where(np.arange(10)%2,-1.,1.);arrays={k:[]for k in ("P","settle","effective","total","aUz","aT")}
 # Fixed original-material centres span .005..995: half endpoint weights,
 # full interior weights. This is trapezoidal integration over material centres.
 weights=np.full(100,.01);weights[[0,-1]]=.005
 for part,q in enumerate(d["p"]["q"]):
  order=d["order"];P=q[order,6].reshape(100,10);settle=-1000*(q[order,2]-d["x0"][order,2]).reshape(100,10)
  effective=q[order,10:16].reshape(100,10,6);total=effective.copy();total[:,:,[0,3,5]]-=P[:,:,None]
  J=q[order,8].reshape(100,10);n=d["n"]["n"][part,order].reshape(100,10);rho=d["rho"][part,order].reshape(100,10)
  aUz=((-settle+settle.mean(axis=1,keepdims=True))*sign).mean(axis=1);aT=((total-total.mean(axis=1,keepdims=True))*sign[None,:,None]).mean(axis=1)
  vertical=total[:,:,5].mean(axis=1);stress=float(max(abs(vertical+c["q0_Pa"])));gap=float(abs(vertical[-1]-vertical[-2]));time=float(d["clock"]["t"][part]);post=time>=.1-1e-7
  if post and(stress>100. or gap>100.):failures.append(dict(series=d["key"],part=part,time_s=time,max_layer_total_error_Pa=stress,top_pair_total_gap_Pa=gap,limit_Pa=100.))
  span=float(settle[-1].mean()-settle[0].mean());fromtotal=float(1000/c["Mc_reference_Pa"]*np.sum(weights*(-vertical)));fromp=float(-1000/c["Mc_reference_Pa"]*np.sum(weights*P.mean(axis=1)))
  r=dict(series=d["key"],part=part,time_s=time,completed_steps=int(d["steps"][part]),actual_dt_s=d["spec"]["dt"],source_clock_closed_or_preopen=bool(d["steps"][part]<=d["spec"]["event"]),legacy_Tv_since_drain=c["Cv_M0_m2_s"]*(time-prior.EVENT),
    pressure_mean_Pa=float(P.mean()),pressure_native_RMS_Pa=float(np.sqrt(np.mean(P**2))),pressure_min_Pa=float(P.min()),pressure_max_Pa=float(P.max()),top10_settlement_mm=float(settle[-1].mean()),bottom10_settlement_mm=float(settle[0].mean()),
    effective_compression_zz_mean_Pa=float(-effective[:,:,5].mean()),total_compression_zz_mean_Pa=float(-total[:,:,5].mean()),max_layer_total_error_Pa=stress,top_pair_total_gap_Pa=gap,Q_total_zz_second_difference_RMS_Pa=float(np.sqrt(np.mean(np.diff(vertical,n=2)**2))),
    original_post_01_guard_applies=post,original_stress_guard_passed=not post or stress<=100.,original_top_gap_guard_passed=not post or gap<=100.,A_pi_Uz_RMS_mm=float(np.sqrt(np.mean(aUz**2))),A_pi_Uz_abs_max_mm=float(max(abs(aUz))),
    J_min=float(J.min()),J_mean=float(J.mean()),J_max=float(J.max()),n_min=float(n.min()),n_mean=float(n.mean()),n_max=float(n.max()),rho_native_min_kg_m3=float(rho.min()),rho_native_mean_kg_m3=float(rho.mean()),rho_native_max_kg_m3=float(rho.max()),
    speed_XYZ_RMS_m_s=float(np.sqrt(np.mean(np.sum(q[:,3:6]**2,axis=1)))),native_top_minus_bottom_settlement_mm=span,diagnostic_span_from_total_stress_mm=fromtotal,diagnostic_span_from_pressure_mm=fromp,diagnostic_span_from_effective_stress_mm=fromtotal+fromp,
    diagnostic_span_from_J_minus1_mm=float(-1000*np.sum(weights*(J.mean(axis=1)-1))),diagnostic_native_minus_stress_span_mm=span-fromtotal-fromp,
    companion=d["ref"]["name"],companion_mean_pressure_Pa=None,companion_top_settlement_mm=None,companion_bottom_settlement_mm=None,P_layer_mean_profile_RMS_error_Pa=None,P_all_native_points_RMS_error_Pa=None,top_settlement_signed_error_mm=None,bottom_settlement_signed_error_mm=None,
    **{"effective_sigma_"+name+"_mean_Pa":float(effective[:,:,j].mean())for j,name in enumerate(COMPONENTS)},**{"total_sigma_"+name+"_mean_Pa":float(total[:,:,j].mean())for j,name in enumerate(COMPONENTS)})
  ref=d["ref"];valid=bool(np.isfinite(ref["P"][part]).all())
  if valid:r.update(companion_mean_pressure_Pa=float(ref["P"][part].mean()),companion_top_settlement_mm=float(ref["settle"][part,-1]),companion_bottom_settlement_mm=float(ref["settle"][part,0]),P_layer_mean_profile_RMS_error_Pa=float(np.sqrt(np.mean((P.mean(axis=1)-ref["P"][part])**2))),P_all_native_points_RMS_error_Pa=float(np.sqrt(np.mean((P-ref["P"][part,:,None])**2))),top_settlement_signed_error_mm=float(settle[-1].mean()-ref["settle"][part,-1]),bottom_settlement_signed_error_mm=float(settle[0].mean()-ref["settle"][part,0]))
  old=d["history"][part]
  for key,oldkey in (("pressure_mean_Pa","pressure_mean_Pa"),("top10_settlement_mm","top10_settlement_mean_mm"),("bottom10_settlement_mm","bottom10_settlement_mean_mm"),("rho_native_mean_kg_m3","native_current_rho_mean_kg_m3")):need(math.isclose(r[key],float(old[oldkey]),rel_tol=2e-12,abs_tol=2e-9),"Native summary changed: "+d["key"]+"/"+key)
  rows.append(r)
  for key,value in (("P",P),("settle",settle),("effective",effective),("total",total),("aUz",aUz),("aT",aT)):arrays[key].append(value)
  if d["key"]!="A":
   for level in range(100):layers.append(dict(series=d["key"],part=part,time_s=time,initial_layer=level,z0_m=float(d["z0"][level]),P_mean_Pa=float(P[level].mean()),P_min_Pa=float(P[level].min()),P_max_Pa=float(P[level].max()),material_settlement_mean_mm=float(settle[level].mean()),J_mean=float(J[level].mean()),n_native_mean=float(n[level].mean()),rho_native_mean_kg_m3=float(rho[level].mean()),A_pi_Uz_signed_mm=float(aUz[level]),
      **{"effective_sigma_"+name+"_mean_Pa":float(effective[level,:,j].mean())for j,name in enumerate(COMPONENTS)},**{"total_sigma_"+name+"_mean_Pa":float(total[level,:,j].mean())for j,name in enumerate(COMPONENTS)},**{"A_pi_total_sigma_"+name+"_signed_Pa":float(aT[level,j])for j,name in enumerate(COMPONENTS)}))
 d.update(rows=rows,arrays={k:np.array(v)for k,v in arrays.items()});return rows,layers,failures


def targets(data,c,np):
 budgets,profiles,selections=[],[],{}
 for tv in TARGETS:
  target=prior.EVENT+tv/c["Cv_M0_m2_s"];parts={}
  for key,d in data.items():
   times=d["clock"]["t"];need(times[0]<=target<=times[-1],"Declared Tv target outside actual observed coverage")
   part=int(np.argmin(abs(times-target)));parts[key]=part;r=d["rows"][part]
   for level in range(100):profiles.append(dict(series=key,requested_legacy_Tv=tv,target_time_s=target,actual_part=part,actual_time_s=r["time_s"],signed_target_gap_s=r["time_s"]-target,actual_legacy_Tv=r["legacy_Tv_since_drain"],applicable_reference_Tv=d["ref"]["capacity"]*r["legacy_Tv_since_drain"],initial_layer=level,z0_m=float(d["z0"][level]),pressure_mean_Pa=float(d["arrays"]["P"][part,level].mean()),material_settlement_mean_mm=float(d["arrays"]["settle"][part,level].mean()),companion=d["ref"]["name"],companion_pressure_Pa=float(d["ref"]["P"][part,level]),companion_material_settlement_mm=float(d["ref"]["settle"][part,level]),interpolation=False))
  selections[tv]=parts;a=data["A"]["rows"][parts["A"]];old=data["B625"]["rows"][parts["B625"]]
  epA=a["P_layer_mean_profile_RMS_error_Pa"];esA=abs(a["top_settlement_signed_error_mm"]);ebA=abs(a["bottom_settlement_signed_error_mm"])
  for key in ("B625","B10"):
   r=data[key]["rows"][parts[key]];ep=r["P_layer_mean_profile_RMS_error_Pa"];es=abs(r["top_settlement_signed_error_mm"]);eb=abs(r["bottom_settlement_signed_error_mm"])
   pp,sp,bp=ep<=epA+10.,es<=esA+.001*c["S_infinity_continuum_surface_mm"],eb<=.005 and eb<=ebA+.002
   budgets.append(dict(series=key,requested_legacy_Tv=tv,target_time_s=target,actual_part=parts[key],actual_time_s=r["time_s"],signed_target_gap_s=r["time_s"]-target,A_actual_part=parts["A"],A_actual_time_s=a["time_s"],signed_own_minus_A_time_gap_s=r["time_s"]-a["time_s"],A_reference="finite_Kw_at_A_actual_time",B_reference="M0_at_own_actual_time",A_P_layer_RMS_error_Pa=epA,B_P_layer_RMS_error_Pa=ep,P_error_increment_vs_A_Pa=ep-epA,P_increment_limit_Pa=10.,P_noninferiority_passed=pp,A_top_abs_error_mm=esA,B_top_abs_error_mm=es,top_abs_error_increment_vs_A_mm=es-esA,top_increment_limit_mm=.001*c["S_infinity_continuum_surface_mm"],top_noninferiority_passed=sp,A_bottom_abs_error_mm=ebA,B_bottom_abs_error_mm=eb,bottom_abs_limit_mm=.005,bottom_increment_limit_mm=.002,bottom_absolute_and_noninferiority_passed=bp,
     own_minus_oldB_P_RMS_error_Pa=ep-old["P_layer_mean_profile_RMS_error_Pa"],own_minus_oldB_top_abs_error_mm=es-abs(old["top_settlement_signed_error_mm"]),own_minus_oldB_bottom_abs_error_mm=eb-abs(old["bottom_settlement_signed_error_mm"]),all_original_target_budgets_passed=pp and sp and bp,new_increment_budget_added=False,interpolation=False))
 return budgets,profiles,selections


def nearest(data,np):
 old,new=data["B625"],data["B10"];rows=[];times=old["clock"]["t"]
 for part,r in enumerate(new["rows"]):
  oi=int(np.argmin(abs(times-r["time_s"])));o=old["rows"][oi];a=new["p"]["q"][part];z=old["p"]["q"][oi]
  delta=a[:,:3]-z[:,:3];delta[:,0]-=.1*np.floor(delta[:,0]/.1+.5)
  v=dict(new_part=part,new_actual_time_s=r["time_s"],new_completed_steps=r["completed_steps"],old_part=oi,old_actual_time_s=o["time_s"],old_completed_steps=o["completed_steps"],signed_new_minus_old_time_gap_s=r["time_s"]-o["time_s"],actual_time_bits_equal=struct.pack("<d",r["time_s"])==struct.pack("<d",o["time_s"]),native_same_ID_pressure_RMS_difference_Pa=float(np.sqrt(np.mean((a[:,6]-z[:,6])**2))),material_XYZ_max_difference_mm=float(1000*np.max(np.linalg.norm(delta,axis=1))),interpolation=False,descriptive_nearest_only=True,half_or_5Pa_equivalence_gate=False)
  for field in ("pressure_mean_Pa","top10_settlement_mm","bottom10_settlement_mm","Q_total_zz_second_difference_RMS_Pa","J_mean","n_mean","rho_native_mean_kg_m3","A_pi_Uz_abs_max_mm","native_top_minus_bottom_settlement_mm","diagnostic_span_from_total_stress_mm","diagnostic_span_from_pressure_mm","diagnostic_span_from_J_minus1_mm","diagnostic_native_minus_stress_span_mm"):
   v["new_minus_old_"+field]=r[field]-o[field]
  for field in ("P_layer_mean_profile_RMS_error_Pa","top_settlement_signed_error_mm","bottom_settlement_signed_error_mm"):
   valid=r[field]is not None and o[field]is not None
   v["new_minus_old_"+field]=r[field]-o[field]if valid else None
   v["new_minus_old_abs_"+field]=abs(r[field])-abs(o[field])if valid else None
  rows.append(v)
 return rows


def events(data,np):
 rows=[]
 for key,d in data.items():
  for name,part in (("initial",0),("event_preopen",int(np.flatnonzero(d["steps"]==d["spec"]["event"])[0])),("first_postopen",int(np.flatnonzero(d["steps"]==d["spec"]["event"]+1)[0])),("nearest_0p15",int(np.argmin(abs(d["clock"]["t"]-.15)))),("nearest_1p5",int(np.argmin(abs(d["clock"]["t"]-1.5)))),("last_observed",len(d["rows"])-1)):
   rows.append(dict(event_selection=name,**d["rows"][part]))
 return rows


def figures(data,selections,pairs,np):
 import matplotlib
 matplotlib.use("Agg")
 import matplotlib.pyplot as plt
 def draw(ax,field,keys=("A","B625","B10"),low=None,high=None,reference=None):
  for key in keys:
   rr=[r for r in data[key]["rows"]if(low is None or r["time_s"]>=low)and(high is None or r["time_s"]<=high)]
   ax.plot([r["time_s"]for r in rr],[r[field]for r in rr],color=COLORS[key],lw=1.,label=SPECS[key]["label"])
   if reference:ax.plot([r["time_s"]for r in rr],[r[reference]for r in rr],color=COLORS[key],ls="--",lw=.8,label=key+" qualified companion")
  ax.set(xlabel="Each source's actual saved time (s)",ylabel=field);ax.grid(True,alpha=.3)
 fig,axes=plt.subplots(3,2,figsize=(15,12),constrained_layout=True)
 for ax,field,reference in zip(axes.flat,("pressure_mean_Pa","top10_settlement_mm","P_layer_mean_profile_RMS_error_Pa","top_settlement_signed_error_mm","max_layer_total_error_Pa","Q_total_zz_second_difference_RMS_Pa"),("companion_mean_pressure_Pa","companion_top_settlement_mm",None,None,None,None)):
  draw(ax,field,reference=reference)
  if field=="max_layer_total_error_Pa":ax.plot([.1,2.00006],[100.,100.],"k--",lw=.8,label="Original post-.1s100Pa limit")
 axes.flat[0].legend(fontsize=7);fig.suptitle("Observed2s only: M0 pressure history/time-step diagnosis; original A finite-Kw failures retained")
 save_png(fig,PRODUCTS["history.png"]);plt.close(fig)
 fig,axes=plt.subplots(3,2,figsize=(15,11),constrained_layout=True)
 for row,field in enumerate(("pressure_mean_Pa","top10_settlement_mm","J_mean")):
  for col,high in enumerate((.15,.012)):
   draw(axes[row,col],field,high=high);axes[row,col].axvline(prior.EVENT,color="black",ls=":",lw=.8);axes[row,col].set_xlim(0,high)
 axes[0,0].legend(fontsize=7);fig.suptitle("Unfiltered startup and closed ramp/event: actual saved states, no fitted time shift")
 save_png(fig,PRODUCTS["startup.png"]);plt.close(fig)
 fig,axes=plt.subplots(3,2,figsize=(15,11),constrained_layout=True)
 for ax,field in zip(axes.flat,("P_layer_mean_profile_RMS_error_Pa","top_settlement_signed_error_mm","Q_total_zz_second_difference_RMS_Pa","A_pi_Uz_abs_max_mm","J_mean","rho_native_mean_kg_m3")):draw(ax,field,low=1.5);ax.set_xlim(1.5,2.00006)
 axes.flat[0].legend(fontsize=7);fig.suptitle("Late observed1.5-2s: all material layers and own-clock errors; not full consolidation")
 save_png(fig,PRODUCTS["late.png"]);plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(13,11),constrained_layout=True)
 for col,tv in enumerate(TARGETS):
  for row,quantity in enumerate(("P","settle")):
   ax=axes[row,col]
   for key,d in data.items():
    part=selections[tv][key];ax.plot(d["arrays"][quantity][part].mean(axis=1),d["z0"],color=COLORS[key],lw=1.,marker="x"if key=="B10"else"o",markevery=8,markersize=3,fillstyle="none",label=SPECS[key]["label"])
    ax.plot(d["ref"][quantity][part],d["z0"],color=COLORS[key],ls="--",lw=.8,label=key+" companion at actual t")
   ax.set(xlabel="Pressure (Pa)"if quantity=="P"else"Material settlement (mm)",ylabel="Initial material z0 (m)",title="Target legacy Tv=%g; each own nearest save"%tv);ax.grid(True,alpha=.3)
 axes[0,0].legend(fontsize=7);fig.suptitle("Unfitted H1 references: A finite-Kw, both B M0; actual timing is in profiles.csv")
 save_png(fig,PRODUCTS["profiles.png"]);plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(15,11),constrained_layout=True)
 for row,(field,component,label)in enumerate((("aUz",None,"Signed alternating-X Uz (mm)"),("aT",5,"Signed alternating total sigma zz (Pa)"))):
  vals={key:data[key]["arrays"][field]if component is None else data[key]["arrays"][field][:,:,component]for key in ("B625","B10")};span=max(float(np.max(abs(v)))for v in vals.values())or 1.
  for col,key in enumerate(("B625","B10")):
   d=data[key];mesh=axes[row,col].pcolormesh(d["clock"]["t"],d["z0"],vals[key].T,shading="nearest",cmap="coolwarm",vmin=-span,vmax=span);fig.colorbar(mesh,ax=axes[row,col],label=label)
   axes[row,col].set(xlabel="Own actual time (s)",ylabel="Initial material z0 (m)",title=SPECS[key]["label"]+"; shared color range")
 fig.suptitle("All100 material layers, every observed saved state; no smoothing or clipping")
 save_png(fig,PRODUCTS["modes.png"]);plt.close(fig)
 fig,axes=plt.subplots(3,2,figsize=(15,12),constrained_layout=True);times=[r["new_actual_time_s"]for r in pairs]
 for ax,field in zip(axes.flat,("new_minus_old_top10_settlement_mm","new_minus_old_abs_top_settlement_signed_error_mm","native_same_ID_pressure_RMS_difference_Pa","signed_new_minus_old_time_gap_s","new_minus_old_Q_total_zz_second_difference_RMS_Pa",None)):
  if field:ax.plot(times,[r[field]for r in pairs],lw=1.);ax.set(ylabel=field)
  else:
   for f in ("new_minus_old_native_top_minus_bottom_settlement_mm","new_minus_old_diagnostic_span_from_total_stress_mm","new_minus_old_diagnostic_span_from_pressure_mm","new_minus_old_diagnostic_native_minus_stress_span_mm"):ax.plot(times,[r[f]for r in pairs],lw=1.,label=f)
   ax.set(ylabel="Qualified small-strain span contributions (mm)");ax.legend(fontsize=6)
  ax.set(xlabel="New B actual time (s)");ax.grid(True,alpha=.3)
 fig.suptitle("B10us minus B6.25us nearest actual states: clock gaps explicit, descriptive only")
 save_png(fig,PRODUCTS["nearest.png"]);plt.close(fig)


def science(ad,result):
 for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):os.environ[name]="1"
 import numpy as np
 data={key:load(ad,key,np,result)for key in SPECS}
 need(all(d["x0"].tobytes()==data["A"]["x0"].tobytes()for d in data.values()),"Original material lattice differs between trajectories")
 constants=references(ad,data,np);history,layers,failures=[],[],[]
 for d in data.values():h,l,f=describe(d,constants,np);history+=h;layers+=l;failures+=f
 budgets,profiles,selections=targets(data,constants,np);pairs=nearest(data,np);event_rows=events(data,np)
 metrics=dict(stage=TAG,analysis_complete=True,source_full_completed=False,partial2s_only=True,physical_acceptance=False,constants=constants,
  reference_limits="Same unfitted H1/512-mode quasistatic companions as B10us_review: A finite-Kw, B M0; not exact finite-ramp/kernel-band/inertial/current-J startup truth",
  nearest_limits="Each source actual clock is retained; nearest pairs are descriptive, not interpolation, a half test, or a5Pa equivalence gate",
  total_stress_definition="Saved six-component sigma is effective stress; total=saved_sigma-pI, shears unchanged",
  decomposition_limits="Trapezoidal integration over fixed material centres z0=.005..995; constrained small-strain Mc and J-1 approximation only. Not an exact coupled-energy, mass or force closure, and no causal attribution proved by decomposition alone",
  original_target_budgets=budgets,original_post01_100Pa_failures=failures,old_A_failure_does_not_exempt_B=True,schemes={},
  original_B10us_science_failure_preserved=True,new_or_old_solver_invocations=0,new_native_invocations=0,raw_BI4_read=False,SHA_scans=0,interpolation_or_clock_rewrite=False)
 for key,d in data.items():
  rr=d["rows"];late=[r for r in rr if r["time_s"]>=1.5];post=[r for r in rr if r["original_post_01_guard_applies"]]
  metrics["schemes"][key]=dict(actual_saved_states=len(rr),actual_end_s=rr[-1]["time_s"],final=rr[-1],event_preopen=next(r for r in event_rows if r["series"]==key and r["event_selection"]=="event_preopen"),post01_max_layer_stress_error_Pa=max(r["max_layer_total_error_Pa"]for r in post),post01_max_top_gap_Pa=max(r["top_pair_total_gap_Pa"]for r in post),post01_failures=sum(r["series"]==key for r in failures),late_saved_states=len(late),late_max_top_abs_error_mm=max(abs(r["top_settlement_signed_error_mm"])for r in late),late_max_P_layer_RMS_error_Pa=max(r["P_layer_mean_profile_RMS_error_Pa"]for r in late),max_alternating_Uz_mm=max(r["A_pi_Uz_abs_max_mm"]for r in rr))
 ad.finish()
 for name,rows in (("history.csv",history),("layers.csv",layers),("profiles.csv",profiles),("targets.csv",budgets),("nearest.csv",pairs),("events.csv",event_rows)):write_csv(PRODUCTS[name],rows)
 write_json(PRODUCTS["metrics.json"],metrics);figures(data,selections,pairs,np);ad.finish()
 result.update(passed=True,analysis_complete=True,source_full_completed=False,partial2s_only=True,all_original_target_budgets_passed=all(r["all_original_target_budgets_passed"]for r in budgets),
   original_100Pa_failures=len(failures),rows=dict(history=len(history),B_all100_layers=len(layers),profiles=len(profiles),targets=len(budgets),nearest=len(pairs),events=len(event_rows)),files=[stat(p)for p in PRODUCTS.values()],physical_acceptance=False)


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--admission",type=Path,required=True);parser.add_argument("--execution-authorized",action="store_true");args=parser.parse_args()
 need(args.execution_authorized,"Root full-read one offline-only admission required");need(not CHECK.exists()and not any(p.exists()for p in PRODUCTS.values()),"Existing/partial diagnosis products protected")
 ad=Admission(args.admission);result=dict(stage=TAG,passed=False,analysis_complete=False,sources={},solver_invocations=0,native_invocations=0,build_invocations=0,SHA_scans=0,physical_acceptance=False,automatic_follow_up=False)
 try:science(ad,result)
 except Exception as exc:result.update(first_error=str(exc),partials_preserved=True);raise
 finally:result["consumed"]=list(ad.used.values());write_json(CHECK,result)
 print(str(CHECK));return 0 if result["passed"]else 1


if __name__=="__main__":raise SystemExit(main())

