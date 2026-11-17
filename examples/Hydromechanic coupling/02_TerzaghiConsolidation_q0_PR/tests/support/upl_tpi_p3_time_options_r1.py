"""Pure P3 finite-h algebra only: retain old results and evaluate only three-row maps."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
import numpy as np
import upl_tpi_next_time_layer_options_r1 as old

T=old.T;TAG="upl_tpi_p3_time_options_r1";SCRIPT=Path(__file__).resolve()
NOTE=T/"notes"/(TAG+".md");OUT=T/"outputs"/TAG;CHECK=T/"logs"/(TAG+".check.json")
PRIOR_CASES=old.OUT/"cases.csv"
need,stat,read=old.need,old.stat,old.read
write_json,write_csv=old.write_json,old.write_csv
EPS,TINY=old.EPS,old.TINY


def key(row):return row["scope"],int(row["mode"]),row["dt_family"],row["method"]


def retained(c,steps,modes):
    receipt=read(old.CHECK)
    need(receipt.get("passed")is True and receipt.get("algebra_complete")is True and
         receipt.get("matrices")==1116 and receipt.get("roots")==4464 and
         receipt.get("actual_SPH_spectrum_proven")is False and
         receipt.get("actual_timestep_admission")is False and receipt["parameters"]==c,
         "Genuine retained one/two/converged algebra required")
    for entry in receipt["consumed"]:
        need(stat(entry["path"])==entry,"Original algebra input changed: "+entry["path"])
    entries=[x for x in receipt["files"]if Path(x["path"]).resolve()==PRIOR_CASES.resolve()]
    need(len(entries)==1 and stat(PRIOR_CASES)==entries[0],"Retained cases stat differs")
    with PRIOR_CASES.open(encoding="utf-8-sig",newline="")as f:rows=list(csv.DictReader(f))
    lookup={key(row):row for row in rows}
    wanted={(mode["scope"],mode["mode"],name,method)for mode in modes
            for name,_ in steps for method in("one","two","converged")}
    need(len(rows)==len(lookup)==1116 and set(lookup)==wanted,"Retained exact case grid differs")
    for mode in modes:
        for name,h in steps:
            for method in("one","two","converged"):
                row=lookup[mode["scope"],mode["mode"],name,method]
                need(float(row["q"])==mode["q"] and float(row["mu"])==mode["mu"] and
                     float(row["dt_s"])==h and row["family"]==mode["family"] and
                     row["actual_SPH_spectrum_or_timestep_admission"]=="False",
                     "Retained mode, step or disclaimer differs")
    return rows,lookup,receipt


def closed_matrix(c,q,mu,h):
    """Independent block form of the same original P1 mechanics plus three defects."""
    r=c["water"]/c["rho"];delta=(1-r)*(1-mu);m=1-delta
    mk=m*m*m;dk=delta*(1+m+m*m);iq=1j*q
    omega2=c["M"]*q*q*h*h/c["rho"]
    H=np.array(((1-.5*omega2,h*c["M"]*iq),(h*iq/c["rho"],1-.5*omega2)),complex)
    K=np.array(((.5*omega2,0.),(-1.5*h*iq/c["rho"],.5*h*iq/c["rho"])),complex)
    P=np.array((-r/(1-r),-c["gamma"]*iq/(c["k"]*q*q*(1-r))),complex)
    extrap=np.array((1.5,-.5));A=np.zeros((4,4),complex);A[:2,:2]=H;A[:2,2:]=K
    A[2,:2]=dk*(P@H);A[2,2:]=dk*(P@K)+mk*extrap;A[3,2]=1.
    # Include uncancelled terms in the arithmetic budget, not a new physical tolerance.
    scale=np.abs(A);scale[0,0]=scale[1,1]=1+.5*omega2
    scale[2,:2]=abs(dk)*(np.abs(P)@np.abs(H))
    scale[2,2:]=abs(dk)*(np.abs(P)@np.abs(K))+abs(mk)*abs(extrap)
    return A,scale,m,delta,mk,dk


def three_row_cases(c,steps,modes):
    cases=[];roots=[];trial=np.array((1+.2j,.3-.1j,-.4+.7j,.2+.5j))
    for mode in modes:
        q,mu=mode["q"],mode["mu"]
        for name,h in steps:
            A=np.column_stack([old.step(e,c,q,mu,h,3)for e in np.eye(4,dtype=complex)])
            direct=old.step(trial,c,q,mu,h,3)
            budget=4096*EPS*(abs(A)@abs(trial)+abs(direct))+4096*TINY
            need(np.all(abs(A@trial-direct)<=budget),"Three-row finite-h map is not linear")
            declared,terms,m,delta,mk,dk=closed_matrix(c,q,mu,h)
            need(np.all(abs(A-declared)<=4096*EPS*(abs(A)+terms)+4096*TINY),
                 "Three-row original-step and independent block matrix differ")
            guess=1.5*trial[2]-.5*trial[3];target=old.fixed_point(direct[:2],c,q)
            expected=dk*target+mk*guess
            budget=4096*EPS*(abs(expected)+abs(dk*target)+abs(mk*guess)+abs(direct[2]))+4096*TINY
            need(abs(direct[2]-expected)<=budget,"Three-row complete-source power differs")
            scale=np.array((c["M"],np.sqrt(c["M"]/c["rho"]),c["M"],c["M"]))
            B=A*scale[None,:]/scale[:,None];z,v=np.linalg.eig(B)
            error=np.max(abs(B@v-v*z[None,:]),axis=0)
            budget=4096*EPS*(np.linalg.norm(B,np.inf)+abs(z))*np.max(abs(v),axis=0)+4096*TINY
            need(np.all(error<=budget),"Three-row eigensystem arithmetic failed")
            radius=float(max(abs(z)))
            case=dict(**mode,dt_family=name,dt_s=h,method="three",finite_endpoint_rows=3,
                full_force_calls_if_straightforward=5,converged_operator_cost_unknown=False,
                m_original=m,m_effective=mk,delta_effective=dk,
                Omega_squared=c["M"]*q*q*h*h/c["rho"],dt_over_tau=h/c["tau"],
                low_Omega_positive_m_sufficient_h_over_tau_lt1=0<mk<1 and h/c["tau"]<1,
                leading_pressure_lag_h_PL_factor_with_minus_sign=mk/(2*dk),
                nominal_spectral_radius=radius,strict_float_radius_above_one=radius>1.,
                eigensystem_arithmetic_ratio=float(max(error/budget)),all_pressure_accelerations_refreshed=True,
                solid_endpoint_changed_between_rows=False,actual_SPH_spectrum_or_timestep_admission=False)
            cases.append(case)
            for index,value in enumerate(z):roots.append(dict(scope=mode["scope"],mode=mode["mode"],
                dt_family=name,method="three",root=index,z_real=float(value.real),
                z_imag=float(value.imag),abs_z=float(abs(value))))
    need(len(cases)==372 and len(roots)==1488,"Only new three-row matrices may be evaluated")
    return cases,roots


def reports(cases):
    result={}
    for case in cases:
        label=case["scope"]+"/"+case["dt_family"]+"/"+case["method"]
        r=result.setdefault(label,dict(cases=0,maximum_computed_radius=0.,strict_radius_above_one_count=0))
        radius=float(case["nominal_spectral_radius"]);r["cases"]+=1
        r["maximum_computed_radius"]=max(r["maximum_computed_radius"],radius)
        r["strict_radius_above_one_count"]+=int(radius>1.)
    return result


def comparisons(all_rows,steps,modes):
    lookup={key(row):row for row in all_rows};rows=[]
    for mode in modes:
        for name,h in steps:
            row=dict(**mode,dt_family=name,dt_s=h,actual_SPH_spectrum_or_timestep_admission=False)
            for method,label in(("one","P1"),("two","P2"),("three","P3"),("converged","converged")):
                case=lookup[mode["scope"],mode["mode"],name,method]
                radius=float(case["nominal_spectral_radius"])
                row[label+"_nominal_spectral_radius"]=radius
                row[label+"_strict_radius_above_one"]=radius>1.
                row[label+"_lag_factor"]=float(case["leading_pressure_lag_h_PL_factor_with_minus_sign"])
            row["only_P3_matrix_newly_evaluated"]=True;rows.append(row)
    need(len(rows)==372,"Comparison must retain all old mode/step rows")
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--execution-authorized",action="store_true")
    need(ap.parse_args().execution_authorized,"Root full-read unique pure-algebra authorization required")
    need(not OUT.exists()and not CHECK.exists(),"Existing or partial products protected")
    inputs=(SCRIPT,NOTE,Path(old.__file__),old.NOTE,old.CHECK,PRIOR_CASES,old.SUMMARY,old.MODES,old.OLD_CHECK)
    before=[stat(path)for path in inputs]
    result=dict(stage=TAG,passed=False,consumed=before,solver_invocations=0,native_invocations=0,
        old_script_invocations=0,old_matrix_recomputations=0,build_invocations=0,SHA_scans=0,
        physical_acceptance=False,actual_SPH_spectrum_proven=False,actual_timestep_admission=False,
        physical_candidate_selected=False,new_reference_trajectory=False,actual_GPU_float_kernel_replayed=False,
        intermediate_native_float_rounding_modeled=False)
    try:
        c,steps,modes=old.parameters_and_modes();prior,_,receipt=retained(c,steps,modes)
        new,roots=three_row_cases(c,steps,modes);combined=[]
        for rows,origin in((prior,"retained_existing_result"),(new,"new_three_row_algebra")):
            for row in rows:combined.append(dict(row,evidence_source=origin))
        need(len(combined)==1488,"Comparison must include every retained and new case")
        summary=reports(combined)
        for label,r in receipt["step_reports"].items():need(summary[label]==r,"Old spectral result changed: "+label)
        need(summary["retained_nominal_positive_LP/context20us/two"]["strict_radius_above_one_count"]==48 and
             summary["retained_nominal_positive_LP/context20us/converged"]["strict_radius_above_one_count"]==120,
             "Original twenty-microsecond counterexamples must stay visible")
        wide=comparisons(combined,steps,modes);OUT.mkdir()
        write_csv(OUT/"cases.csv",combined);write_csv(OUT/"comparison.csv",wide);write_csv(OUT/"new_P3_roots.csv",roots)
        need(all(stat(entry["path"])==entry for entry in before),"Frozen algebra input changed")
        result.update(passed=True,algebra_complete=True,parameters=c,retained_nominal_modes=120,
            previous_illustrative_modes=4,retained_old_matrices=1116,new_P3_matrices=372,new_P3_roots=1488,
            comparison_cases=1488,comparison_rows=372,step_reports=summary,
            reused_functions=["parameters_and_modes","step(iterations=3)","fixed_point"],
            interpretation="All nominal radii including failures retained; neither SPH stability nor physical/timestep admission follows",
            files=[stat(OUT/name)for name in("cases.csv","comparison.csv","new_P3_roots.csv")])
    except Exception as exc:result.update(first_failure=str(exc),partial_outputs_preserved=True);raise
    finally:write_json(CHECK,result)
    print(str(CHECK))


if __name__=="__main__":main()
