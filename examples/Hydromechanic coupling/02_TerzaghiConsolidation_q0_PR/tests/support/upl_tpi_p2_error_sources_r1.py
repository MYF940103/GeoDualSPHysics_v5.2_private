"""P2 small-table-only error identity adapter; no new solve, native, trial, alignment or fitted budget."""
from __future__ import annotations
import argparse,json,math,struct
from pathlib import Path
import upl_tpi_p1_error_sources_r1 as identity
T=identity.T;TAG="upl_tpi_p2_error_sources_r1";NOTE=T/"notes"/(TAG+".md");REPORT=T/"notes"/(TAG+"_result.md");CHECK=T/"logs"/(TAG+".check.json")
NEW="upl_tpi_p2_window_review_r1";OLD=identity.OLD
FILES={"history":T/"figures"/(NEW+".history.csv"),"profiles":T/"figures"/(NEW+".profiles.csv"),"targets":T/"figures"/(NEW+".targets.csv"),"metrics":T/"figures"/(NEW+".metrics.json"),"check":T/"logs"/(NEW+".check.json"),"old_history":T/"figures"/(OLD+".history.csv"),"old_targets":T/"figures"/(OLD+".targets.csv"),"old_metrics":T/"figures"/(OLD+".metrics.json"),"old_check":T/"logs"/(OLD+".check.json")}
SERIES=("A","B10","BP2");TARGETS=identity.TARGETS
COMPONENTS=("bottom_translation_mm","native_minus_J_integral_mm","J_minus_stress_pressure_integral_mm","total_stress_integral_bias_mm","pressure_integral_bias_mm","reference_trapezoid_minus_continuum_span_mm")
need,stat,dump_new,companion,decompose=identity.need,identity.stat,identity.dump_new,identity.companion,identity.decompose
class Admission(identity.Admission):
 def __init__(self,path):
  self.entry=stat(path);self.data=json.loads(Path(path).read_text(encoding="utf-8-sig"));self.used={}
  need(self.data.get("stage")==TAG+".admission"and self.data.get("passed")is True and self.data.get("small_tables_only")is True,"One root-read P2 small-table-only arithmetic admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")
  for p in(Path(__file__),NOTE,Path(identity.__file__),identity.NOTE,*FILES.values()):self.pin(p)

def exact_time(a,b):return struct.pack("<d",a)==struct.pack("<d",b)

def component_difference(new,old):
 d={k:new[k]-old[k]for k in COMPONENTS};delta=new["top_signed_error_mm"]-old["top_signed_error_mm"]
 need(abs(delta-math.fsum(d.values()))<=identity.ARITHMETIC_MM,"Selected component-difference identity does not close")
 return dict(top_signed_error_mm=delta,**d)

def analysis(ad,result):
 check,oldcheck=ad.read(FILES["check"]),ad.read(FILES["old_check"]);metrics,oldmetrics=ad.read(FILES["metrics"]),ad.read(FILES["old_metrics"])
 need(check.get("stage")==NEW and check.get("passed")is True and check.get("analysis_complete")is True and metrics.get("stage")==NEW and metrics.get("analysis_complete")is True and metrics.get("physical_acceptance")is False and oldcheck.get("analysis_complete")is True and oldmetrics.get("analysis_complete")is True,"Completed actual P2/original analyses required; failed physical budgets remain failed")
 h,profiles,targets=ad.table(FILES["history"]),ad.table(FILES["profiles"]),ad.table(FILES["targets"]);oldh,oldtargets=ad.table(FILES["old_history"]),ad.table(FILES["old_targets"])
 c=oldmetrics["constants"];need(metrics["constants"]==c and c["series_modes"]==512 and c["H_m"]==1. and c["q0_Pa"]==10000. and c["k_m_s"]==.0001 and c["Kw_XML_Pa"]==2e8,"Original unfitted constants changed")
 bykey={key:[r for r in h if r["series"]==key]for key in SERIES};need([len(bykey[k])for k in SERIES]==[1292,1263,1263],"Original A/B10/P2 small history lengths differ")
 need(check["all_original_target_budgets_passed"]==metrics["all_original_target_budgets_passed"] and check["all_new_post01_100Pa_guards_passed"]==metrics["all_new_post01_100Pa_guards_passed"],"Completed science budget records disagree")
 old_lookup={(r["series"],int(r["part"])):r for r in oldh};rows=[];selections=[];centres={}
 for key,rr in bykey.items():
  pp=sorted([r for r in profiles if r["series"]==key and r["requested_legacy_Tv"]==.005],key=lambda r:r["initial_layer"]);need(len(pp)==100,"Original100 material centre coordinates missing")
  z=[r["z0_m"]for r in pp];need(all(z[i]<z[i+1]for i in range(99)),"Material centres unordered");centres[key]=z
  pre=[r for r in rr if r["completed_steps"]==(1600 if key=="A"else 1000)];need(len(pre)==1 and pre[0]["source_clock_closed_or_preopen"]is True,"Actual preopen state missing")
  selected=[("preopen",pre[0],True),("nearest_0p15",min(rr,key=lambda r:abs(r["time_s"]-.15)),False)]
  for tv in TARGETS:selected.append(("legacy_Tv_"+str(tv),min(rr,key=lambda r:abs(r["time_s"]-(c["drain_time_s"]+tv/c["Cv_M0_m2_s"]))),False))
  for label,row,closed in selected:
   if key!="BP2":
    old=old_lookup[(key,int(row["part"]))]
    for field in("time_s","completed_steps","top10_settlement_mm","bottom10_settlement_mm","diagnostic_span_from_total_stress_mm","diagnostic_span_from_pressure_mm","diagnostic_span_from_J_minus1_mm"):need(row[field]==old[field],"Preserved A/B10 selected history changed")
   d=decompose(row,z,c,label,closed);rows.append(d);selections.append(dict(series=key,selection=label,actual_part=d["actual_part"],actual_time_s=d["actual_time_s"],nearest_only=label=="nearest_0p15",interpolation=False))
  for tv in TARGETS:
   pp=sorted([r for r in profiles if r["series"]==key and r["requested_legacy_Tv"]==tv],key=lambda r:r["initial_layer"]);need(len(pp)==100 and[r["z0_m"]for r in pp]==z,"Actual target profile/material coordinates missing")
   d=next(x for x in rows if x["series"]==key and x["selection"]=="legacy_Tv_"+str(tv));need(all(r["actual_time_s"]==d["actual_time_s"]for r in pp),"Actual target profile time differs")
   P,S=companion(d["actual_time_s"],z,d["reference_capacity"],c,False)
   need(max(abs(r["companion_pressure_Pa"]-P[i])for i,r in enumerate(pp))<=2e-8 and max(abs(r["companion_material_settlement_mm"]-S[i])for i,r in enumerate(pp))<=2e-10,"Original own-time companion/profile reproduction differs")
   pdiag=-1000/c["Mc_reference_Pa"]*math.fsum((.005 if i in(0,99)else .01)*r["pressure_mean_Pa"]for i,r in enumerate(pp));need(abs(pdiag-d["actual_diagnostic_pressure_span_mm"])<=identity.ARITHMETIC_MM,"Stored target pressure profile/integral association differs")
 need(centres["A"]==centres["B10"]==centres["BP2"],"Original material centres differ")
 changes=[]
 for label in("preopen","nearest_0p15","legacy_Tv_0.005","legacy_Tv_0.05"):
  lookup={r["series"]:r for r in rows if r["selection"]==label};a,old,new=lookup["A"],lookup["B10"],lookup["BP2"]
  need(exact_time(old["actual_time_s"],new["actual_time_s"])and old["completed_updates"]==new["completed_updates"],"Selected B10/P2 actual states do not share time and step")
  original_extra=component_difference(old,a);remaining_extra=component_difference(new,a);removed=component_difference(old,new)
  positive_fraction=removed["top_signed_error_mm"]/original_extra["top_signed_error_mm"]if original_extra["top_signed_error_mm"]>0. and 0.<=remaining_extra["top_signed_error_mm"]<=original_extra["top_signed_error_mm"]else None
  changes.append(dict(selection=label,actual_P2_and_B10_time_s=new["actual_time_s"],actual_A_time_s=a["actual_time_s"],signed_P2_minus_A_time_gap_s=new["actual_time_s"]-a["actual_time_s"],P2_minus_B10=component_difference(new,old),B10_minus_A_at_own_times=original_extra,P2_minus_A_at_own_times=remaining_extra,B10_minus_P2_removed_signed_extra=removed,fraction_of_positive_extra_signed_top_error_removed=positive_fraction,clock_alignment_or_budget_adjustment=False,causal_attribution_proven=False))
 budgets=[];gaps=[]
 for r in targets:
  need(r["series"]=="BP2"and r["requested_legacy_Tv"]in TARGETS,"Unexpected P2 target row")
  old=[o for o in oldtargets if o["series"]=="B10"and o["requested_legacy_Tv"]==r["requested_legacy_Tv"]];need(len(old)==1,"Preserved original B10 target missing");old=old[0]
  for field in("A_actual_part","A_actual_time_s","A_top_abs_error_mm","A_P_layer_RMS_error_Pa","A_bottom_abs_error_mm","P_increment_limit_Pa","top_increment_limit_mm","bottom_abs_limit_mm","bottom_increment_limit_mm"):need(r[field]==old[field],"Original A target/budget changed")
  need(r["top_increment_limit_mm"]==.001*c["S_infinity_continuum_surface_mm"],"Original top budget constant changed")
  increment=r["B_top_abs_error_mm"]-r["A_top_abs_error_mm"];limit=r["top_increment_limit_mm"]
  budgets.append(dict(requested_legacy_Tv=r["requested_legacy_Tv"],A_original_top_abs_error_mm=r["A_top_abs_error_mm"],B10_original_top_abs_error_mm=old["B_top_abs_error_mm"],P2_top_abs_error_mm=r["B_top_abs_error_mm"],P2_minus_A_abs_error_mm=increment,original_top_increment_limit_mm=limit,remaining_top_margin_mm=limit-increment,positive_top_budget_excess_mm=max(0.,increment-limit),original_B10_all_target_budgets_passed=old["all_original_target_budgets_passed"],P2_top_noninferiority_passed=r["top_noninferiority_passed"],P2_all_target_budgets_passed=r["all_original_target_budgets_passed"],full_original_P2_target_record=r,physical_decision_recomputed_or_changed=False))
  d=next(x for x in rows if x["series"]=="BP2"and x["selection"]=="legacy_Tv_"+str(r["requested_legacy_Tv"]));a=next(x for x in rows if x["series"]=="A"and x["selection"]==d["selection"])
  need(d["actual_part"]==int(r["actual_part"])and exact_time(d["actual_time_s"],r["actual_time_s"])and a["actual_part"]==int(r["A_actual_part"])and exact_time(a["actual_time_s"],r["A_actual_time_s"]),"Preserved target selection differs")
  # Same original analytic reference at the two actual times: a descriptive gap scale, never a native alignment.
  m0own=companion(d["actual_time_s"],centres["BP2"],1.,c,False)[1][-1];m0atA=companion(a["actual_time_s"],centres["BP2"],1.,c,False)[1][-1]
  kwown=companion(d["actual_time_s"],centres["A"],c["finite_Kw_capacity"],c,False)[1][-1];kwatA=companion(a["actual_time_s"],centres["A"],c["finite_Kw_capacity"],c,False)[1][-1]
  gaps.append(dict(requested_legacy_Tv=r["requested_legacy_Tv"],actual_P2_time_s=d["actual_time_s"],actual_A_time_s=a["actual_time_s"],signed_P2_minus_A_gap_s=d["actual_time_s"]-a["actual_time_s"],M0_reference_top_change_over_actual_gap_mm=m0own-m0atA,finiteKw_reference_top_change_over_actual_gap_mm=kwown-kwatA,analytic_same_reference_only=True,native_velocity_or_error_correction_claimed=False,interpolation_or_time_fit=False,used_to_adjust_budget=False))
 need(len(rows)==12 and len(budgets)==len(gaps)==2,"Four real states /three series /two original budgets required")
 result.update(passed=True,analysis_complete=True,rows=rows,selected_actual_states=selections,component_changes=changes,original_budget_records=budgets,reference_only_actual_gap_scale=gaps,constants=c,arithmetic_closure_tolerance_mm=identity.ARITHMETIC_MM,arithmetic_tolerance_is_not_physical_budget=True,max_arithmetic_closure_residual_mm=max(abs(r["diagnostic_sum_residual_mm"])for r in rows),diagnostic_identity="toperror = bottomerror + (native_span-Jintegral) + (Jintegral-stress_pressure_integral) + total_integral_bias + pressure_integral_bias + reference_trapezoid_residual",pressure_bias_sign="Positive pressure_integral_bias_mm means integrated simulated pressure is below its own companion and adds compression in the small-strain diagnostic",original_science_planned_budgets_passed=check["planned_budgets_passed"],original_science_all_target_budgets_passed=check["all_original_target_budgets_passed"],original_science_all_post01_100Pa_passed=check["all_new_post01_100Pa_guards_passed"],original_budget_results_unchanged=True,causal_mechanism_proven=False,exact_mass_energy_or_force_closure=False,closed_preopen_companion_not_finite_ramp_dynamic_truth=True,physical_acceptance=False)
 ad.finish()
 lines=["# P2 bounded2s error-source arithmetic r1","","Existing small tables only; no solve, decode, pressure trial, interpolation or fitted reference.","All rows retain their own actual saved times. Units mm; positive top error means excess settlement.","","| Series / selection | Actual time (s) | Top error | Bottom shift | Pressure bias | Total-stress bias | Native-J | J-stress/pressure | Reference quadrature |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
 for r in rows:lines.append("| "+r["series"]+" / "+r["selection"]+" | "+format(r["actual_time_s"],".12g")+" | "+" | ".join(format(r[k],"+.10g")for k in("top_signed_error_mm","bottom_translation_mm","pressure_integral_bias_mm","total_stress_integral_bias_mm","native_minus_J_integral_mm","J_minus_stress_pressure_integral_mm","reference_trapezoid_minus_continuum_span_mm"))+" |")
 lines += ["","## Same-clock P2 correction and remaining own-clock extra error","","| Selection | B10-A top | P2-A top | Removed B10-P2 | Removed pressure bias | Remaining P2-A pressure bias | Remaining P2-A total-stress bias | Remaining P2-A bottom shift |","|---|---:|---:|---:|---:|---:|---:|---:|"]
 for r in changes:
  old,new,removed=r["B10_minus_A_at_own_times"],r["P2_minus_A_at_own_times"],r["B10_minus_P2_removed_signed_extra"]
  values=(old["top_signed_error_mm"],new["top_signed_error_mm"],removed["top_signed_error_mm"],removed["pressure_integral_bias_mm"],new["pressure_integral_bias_mm"],new["total_stress_integral_bias_mm"],new["bottom_translation_mm"]);lines.append("| "+r["selection"]+" | "+" | ".join(format(v,"+.10g")for v in values)+" |")
 lines += ["","The complete unrounded component vectors, original absolute-error budget records and exact actual clock gaps are in the matching check JSON.","The reference-only time-gap scale evaluates the same original analytic companion at both actual times. It never corrects measured error, aligns native states or changes a budget.","","Preopen uses an ideal uniform undrained end-load companion, not finite-ramp/inertial dynamic truth. Other selections use the original unfitted512-mode drained companion at each own time. Material-centre trapezoids span0.99m; J-1/Mc decomposition is a small-strain diagnostic, not exact strain, mass, energy, force closure or a proof of causal mechanism.","Existing physical budget failures remain failures. This arithmetic passed flag only means the table association and identity completed.",""]
 with REPORT.open("x",encoding="utf8",newline="\n")as f:f.write("\n".join(lines))
 result["result_note"]=stat(REPORT)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--admission",type=Path,required=True);p.add_argument("--execution-authorized",action="store_true");a=p.parse_args()
 need(a.execution_authorized,"One separately root-reviewed arithmetic action required");need(not CHECK.exists()and not REPORT.exists(),"Existing P2 result/partial protected")
 ad=Admission(a.admission);result=dict(stage=TAG,passed=False,analysis_complete=False,solver_invocations=0,native_invocations=0,build_invocations=0,large_tables_read=0,large_tables_written=0,SHA_scans=0,physical_acceptance=False)
 try:analysis(ad,result)
 except Exception as e:result.update(first_error=str(e),partials_preserved=True);raise
 finally:result["consumed"]=list(ad.used.values());dump_new(CHECK,result)
 print(str(CHECK));return 0 if result["passed"]else 1
if __name__=="__main__":raise SystemExit(main())
