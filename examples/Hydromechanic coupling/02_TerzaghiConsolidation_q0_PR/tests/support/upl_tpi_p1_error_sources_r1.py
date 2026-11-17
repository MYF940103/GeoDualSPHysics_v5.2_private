"""One small-table-only error decomposition; no solver/native, fit, plot or large-table rewrite."""
from __future__ import annotations
import argparse,csv,json,math,struct
from pathlib import Path
T=Path(__file__).resolve().parents[1];TAG="upl_tpi_p1_error_sources_r1"
NOTE=T/"notes"/(TAG+".md");REPORT=T/"notes"/(TAG+"_result.md");CHECK=T/"logs"/(TAG+".check.json")
NEW="upl_tpi_p1_loadclock_window_review_r1";OLD="upl_tpi_m0_dt_causal_r1"
FILES={"history":T/"figures"/(NEW+".history.csv"),"profiles":T/"figures"/(NEW+".profiles.csv"),"targets":T/"figures"/(NEW+".targets.csv"),"old_history":T/"figures"/(OLD+".history.csv"),"old_targets":T/"figures"/(OLD+".targets.csv"),"old_metrics":T/"figures"/(OLD+".metrics.json"),"new_check":T/"logs"/(NEW+".check.json"),"old_check":T/"logs"/(OLD+".check.json")}
SERIES=("A","B10","Bstaged");TARGETS=(.005,.05);ARITHMETIC_MM=5e-12

def need(q,message):
 if not q:raise RuntimeError(message)
def stat(path):
 p=Path(path).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def same(e):need(stat(e["path"])=={k:e[k]for k in("path","bytes","mtime_ns")},"Input stat changed: "+e["path"])
def dump_new(path,data):
 with path.open("x",encoding="utf8",newline="\n")as f:json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
def typed(row):
 d={}
 for k,v in row.items():
  if v=="":d[k]=None
  elif v in("True","False"):d[k]=v=="True"
  else:
   try:d[k]=float(v)
   except ValueError:d[k]=v
 return d
class Admission:
 def __init__(self,path):
  self.entry=stat(path);self.data=json.loads(Path(path).read_text(encoding="utf-8-sig"));self.used={}
  need(self.data.get("stage")==TAG+".admission"and self.data.get("passed")is True and self.data.get("small_tables_only")is True,"One root-read small-table-only arithmetic admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")
  for p in(Path(__file__),NOTE,*FILES.values()):self.pin(p)
 def pin(self,path):
  k=str(Path(path).resolve());need(k in self.frozen,"Unadmitted input: "+k);same(self.frozen[k]);self.used[k]=self.frozen[k];return Path(k)
 def read(self,path):return json.loads(self.pin(path).read_text(encoding="utf-8-sig"))
 def table(self,path):
  with self.pin(path).open(encoding="utf-8-sig",newline="")as f:return[typed(r)for r in csv.DictReader(f)]
 def finish(self):
  for e in self.used.values():same(e)
  same(self.entry)

def companion(time,z,capacity,c,closed):
 q0,M,H=c["q0_Pa"],c["Mc_reference_Pa"],c["H_m"]
 if closed:return [capacity*q0 for _ in z],[1000*q0/M*(1-capacity)*x for x in z]
 tau=time-c["drain_time_s"];need(tau>=0.,"Drained companion requested before opening")
 P,S=[],[]
 for x in z:
  pp,ss=[],[]
  for j in range(c["series_modes"]):
   lam=(j+.5)*math.pi;coef=2.*(-1. if j%2 else 1.)/lam;decay=math.exp(-capacity*c["Cv_M0_m2_s"]*lam*lam*tau/H**2)
   pp.append(decay*coef*math.cos(lam*x/H));ss.append(decay*coef/lam*math.sin(lam*x/H))
  P.append(capacity*q0*math.fsum(pp));S.append(1000*q0/M*(x-H*capacity*math.fsum(ss)))
 return P,S

def decompose(row,z,c,selection,closed):
 key=row["series"];capacity=c["finite_Kw_capacity"]if key=="A"else 1.;P,S=companion(row["time_s"],z,capacity,c,closed)
 weights=[.005]+[.01]*98+[.005];M=c["Mc_reference_Pa"];q0=c["q0_Pa"]
 top,bottom=row["top10_settlement_mm"],row["bottom10_settlement_mm"];span=top-bottom
 total,pres,j=row["diagnostic_span_from_total_stress_mm"],row["diagnostic_span_from_pressure_mm"],row["diagnostic_span_from_J_minus1_mm"]
 ref_total=1000*q0/M*math.fsum(weights);ref_p=-1000/M*math.fsum(w*p for w,p in zip(weights,P));ref_span=S[-1]-S[0]
 bottom_error=bottom-S[0];top_error=top-S[-1];span_error=span-ref_span
 components=dict(bottom_translation_mm=bottom_error,native_minus_J_integral_mm=span-j,J_minus_stress_pressure_integral_mm=j-total-pres,total_stress_integral_bias_mm=total-ref_total,pressure_integral_bias_mm=pres-ref_p,reference_trapezoid_minus_continuum_span_mm=ref_total+ref_p-ref_span)
 residual=top_error-math.fsum(components.values())
 need(abs(span-row["native_top_minus_bottom_settlement_mm"])<=ARITHMETIC_MM and abs(total+pres-row["diagnostic_span_from_effective_stress_mm"])<=ARITHMETIC_MM and abs(span-total-pres-row["diagnostic_native_minus_stress_span_mm"])<=ARITHMETIC_MM and abs(residual)<=ARITHMETIC_MM,"Stored decomposition or arithmetic closure differs")
 if not closed:
  need(abs(top_error-row["top_settlement_signed_error_mm"])<=2e-10 and abs(bottom_error-row["bottom_settlement_signed_error_mm"])<=2e-10,"Unfitted companion no longer matches original own-clock error")
 return dict(series=key,selection=selection,actual_part=int(row["part"]),actual_time_s=row["time_s"],completed_updates=int(row["completed_steps"]),dt_s=row["actual_dt_s"],reference="ideal_uniform_undrained_endload_finiteKw"if closed and key=="A"else"ideal_uniform_undrained_endload_M0"if closed else"finiteKw_drained_companion"if key=="A"else"M0_drained_companion",preopen_reference_is_dynamic_truth=False,
  legacy_Tv_since_drain=row["legacy_Tv_since_drain"],reference_capacity=capacity,native_top_mm=top,native_bottom_mm=bottom,native_span_mm=span,reference_top_mm=S[-1],reference_bottom_mm=S[0],reference_span_mm=ref_span,top_signed_error_mm=top_error,bottom_signed_error_mm=bottom_error,span_signed_error_mm=span_error,
  actual_diagnostic_total_span_mm=total,actual_diagnostic_pressure_span_mm=pres,actual_diagnostic_stress_pressure_span_mm=total+pres,actual_diagnostic_J_span_mm=j,reference_total_trapezoid_mm=ref_total,reference_pressure_trapezoid_mm=ref_p,
  reference_point_mean_pressure_Pa=math.fsum(P)/100.,native_mean_pressure_Pa=row["pressure_mean_Pa"],native_minus_reference_point_mean_pressure_Pa=row["pressure_mean_Pa"]-math.fsum(P)/100.,native_minus_reference_pressure_integral_Pa_m=-M/1000.*(pres-ref_p),native_minus_uniform_total_compression_integral_Pa_m=M/1000.*(total-ref_total),
  original_stress_layer_error_Pa=row["max_layer_total_error_Pa"],original_top_gap_Pa=row["top_pair_total_gap_Pa"],diagnostic_sum_residual_mm=residual,**components)

def analysis(ad,result):
 check,oldcheck=ad.read(FILES["new_check"]),ad.read(FILES["old_check"]);oldmetrics=ad.read(FILES["old_metrics"])
 need(check.get("stage")==NEW and check.get("analysis_complete")is True and oldcheck.get("analysis_complete")is True and oldmetrics.get("analysis_complete")is True,"Completed actual analyses required; failed budgets stay failed")
 h,profiles,targets=ad.table(FILES["history"]),ad.table(FILES["profiles"]),ad.table(FILES["targets"])
 oldh,oldtargets=ad.table(FILES["old_history"]),ad.table(FILES["old_targets"])
 c=oldmetrics["constants"];need(c["series_modes"]==512 and c["H_m"]==1. and c["q0_Pa"]==10000. and c["k_m_s"]==.0001 and c["Kw_XML_Pa"]==2e8,"Original unfitted reference constants differ")
 bykey={key:[r for r in h if r["series"]==key]for key in SERIES};need([len(bykey[k])for k in SERIES]==[1292,1263,1263],"Expected small history lengths differ")
 old_lookup={(r["series"],int(r["part"])):r for r in oldh};rows=[];selection_rows=[]
 for key,rr in bykey.items():
  pp=sorted([r for r in profiles if r["series"]==key and r["requested_legacy_Tv"]==.005],key=lambda r:r["initial_layer"]);need(len(pp)==100,"Original100 material centre coordinates missing")
  z=[r["z0_m"]for r in pp];need(all(z[i]<z[i+1]for i in range(99)),"Material centres unordered")
  pre=[r for r in rr if r["completed_steps"]==(1600 if key=="A"else 1000)];need(len(pre)==1 and pre[0]["source_clock_closed_or_preopen"]is True,"True preopen state missing")
  selected=[("preopen",pre[0],True),("nearest_0p15",min(rr,key=lambda r:abs(r["time_s"]-.15)),False)]
  for tv in TARGETS:selected.append(("legacy_Tv_"+str(tv),min(rr,key=lambda r:abs(r["time_s"]-(c["drain_time_s"]+tv/c["Cv_M0_m2_s"]))),False))
  for label,row,closed in selected:
   if key!="Bstaged":
    old=old_lookup[(key,int(row["part"]))]
    for field in("time_s","completed_steps","top10_settlement_mm","bottom10_settlement_mm","diagnostic_span_from_total_stress_mm","diagnostic_span_from_pressure_mm","diagnostic_span_from_J_minus1_mm"):need(row[field]==old[field],"Preserved original A/B10 history changed")
   d=decompose(row,z,c,label,closed);rows.append(d);selection_rows.append(dict(series=key,selection=label,actual_part=d["actual_part"],actual_time_s=d["actual_time_s"],nearest_only=label=="nearest_0p15",interpolation=False))
  for tv in TARGETS:
   pp=sorted([r for r in profiles if r["series"]==key and r["requested_legacy_Tv"]==tv],key=lambda r:r["initial_layer"]);need(len(pp)==100 and [r["z0_m"]for r in pp]==z,"Actual target profile/material coordinates missing")
   d=next(x for x in rows if x["series"]==key and x["selection"]=="legacy_Tv_"+str(tv));need(all(r["actual_time_s"]==d["actual_time_s"]for r in pp),"Target/profile own time mismatch")
   P,S=companion(d["actual_time_s"],z,d["reference_capacity"],c,False)
   need(max(abs(r["companion_pressure_Pa"]-P[i])for i,r in enumerate(pp))<=2e-8 and max(abs(r["companion_material_settlement_mm"]-S[i])for i,r in enumerate(pp))<=2e-10,"Companion reproduction differs from original target small table")
   pdiag=-1000/c["Mc_reference_Pa"]*math.fsum((.005 if i in(0,99)else .01)*r["pressure_mean_Pa"]for i,r in enumerate(pp));need(abs(pdiag-d["actual_diagnostic_pressure_span_mm"])<=ARITHMETIC_MM,"Actual target pressure profile/integral association differs")
 # Use original small target tables only to retain their budgets and identify pre-existing bias.
 budget_pairs=[]
 for r in targets:
  old=[o for o in oldtargets if o["series"]=="B10"and o["requested_legacy_Tv"]==r["requested_legacy_Tv"]];need(len(old)==1,"Original B10 target budget missing")
  budget_pairs.append(dict(requested_legacy_Tv=r["requested_legacy_Tv"],A_original_top_abs_error_mm=r["A_top_abs_error_mm"],B10_original_top_abs_error_mm=r["original_B10_top_abs_error_mm"],Bstaged_top_abs_error_mm=r["B_top_abs_error_mm"],original_limit_mm=r["top_increment_limit_mm"],old_B10_all_target_budgets_passed=old[0]["all_original_target_budgets_passed"],new_all_target_budgets_passed=r["all_original_target_budgets_passed"]))
 changes=[]
 for label in("preopen","nearest_0p15","legacy_Tv_0.005","legacy_Tv_0.05"):
  lookup={r["series"]:r for r in rows if r["selection"]==label};old,new=lookup["B10"],lookup["Bstaged"]
  need(struct.pack("<d",old["actual_time_s"])==struct.pack("<d",new["actual_time_s"])and old["completed_updates"]==new["completed_updates"],"B10/staged selected states are not exactly same clock")
  changes.append(dict(selection=label,actual_time_s=new["actual_time_s"],**{"new_minus_old_"+k:new[k]-old[k]for k in("top_signed_error_mm","bottom_signed_error_mm","span_signed_error_mm","bottom_translation_mm","native_minus_J_integral_mm","J_minus_stress_pressure_integral_mm","total_stress_integral_bias_mm","pressure_integral_bias_mm","reference_trapezoid_minus_continuum_span_mm")}))
 result.update(passed=True,analysis_complete=True,rows=rows,selected_actual_states=selection_rows,Bstaged_minus_B10=changes,original_budget_records=budget_pairs,constants=c,
  arithmetic_closure_tolerance_mm=ARITHMETIC_MM,arithmetic_tolerance_is_not_physical_budget=True,max_arithmetic_closure_residual_mm=max(abs(r["diagnostic_sum_residual_mm"])for r in rows),
  diagnostic_identity="toperror = bottomerror + (native_span-Jintegral) + (Jintegral-stress_pressure_integral) + total_integral_bias + pressure_integral_bias + reference_trapezoid_residual",
  pressure_bias_sign="positive pressure_integral_bias_mm means integrated simulated pressure is below its companion and adds compression in this small-strain diagnostic",
  original_budget_results_unchanged=True,causal_mechanism_proven=False,exact_mass_energy_or_force_closure=False,closed_preopen_companion_not_finite_ramp_dynamic_truth=True,physical_acceptance=False)
 ad.finish()
 lines=["# P1 2s 误差来源小表诊断 r1","","仅消费已有小表；无新求解/解码/拟合。所有量均使用各自实际保存时刻。","","单位 mm；正顶部误差为模拟沉降偏大。底部项是相对同模型参考的平移误差。压力项为正表示压力积分不足在小应变诊断中增加压缩。","","| series / selection | actual t(s) | top error | bottom shift | pressure bias | total-stress bias | native-J | J-stress/pressure | reference quadrature |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
 for r in rows:lines.append("| "+r["series"]+" / "+r["selection"]+" | "+format(r["actual_time_s"],".12g")+" | "+" | ".join(format(r[k],"+.10g")for k in("top_signed_error_mm","bottom_translation_mm","pressure_integral_bias_mm","total_stress_integral_bias_mm","native_minus_J_integral_mm","J_minus_stress_pressure_integral_mm","reference_trapezoid_minus_continuum_span_mm"))+" |")
 lines += ["","上表各分项之和为顶部误差；完整未圆整数值、积分量/Pa·m、原预算及新减旧见同标签 logs check.json。", "", "preopen 使用理想均匀闭载的 finite-Kw/M0 无排水伴随，不是有限 ramp/惯性参考；其他三点使用原未拟合512模态排水伴随。原A和两个B的参考分别保留，未平移时钟或修改H/Cv/q0。", "", "材料中心梯形积分跨度.99m，不是全表面位移的精确积分；J-1和Mc分解是小应变诊断。分项关联不能单独证明离散算子的因果错误，也不是质量、能量或外力守恒证书。原预算失败保持失败；本次passed仅表示算术审查完整。", ""]
 with REPORT.open("x",encoding="utf8",newline="\n")as f:f.write("\n".join(lines))
 result["result_note"]=stat(REPORT)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--admission",type=Path,required=True);p.add_argument("--execution-authorized",action="store_true");a=p.parse_args()
 need(a.execution_authorized,"One independently reviewed arithmetic execution required");need(not CHECK.exists()and not REPORT.exists(),"Existing result/partial protected")
 ad=Admission(a.admission);result=dict(stage=TAG,passed=False,analysis_complete=False,solver_invocations=0,native_invocations=0,build_invocations=0,large_tables_written=0,SHA_scans=0,physical_acceptance=False)
 try:analysis(ad,result)
 except Exception as e:result.update(first_error=str(e),partials_preserved=True);raise
 finally:result["consumed"]=list(ad.used.values());dump_new(CHECK,result)
 print(str(CHECK));return 0 if result["passed"]else 1
if __name__=="__main__":raise SystemExit(main())
