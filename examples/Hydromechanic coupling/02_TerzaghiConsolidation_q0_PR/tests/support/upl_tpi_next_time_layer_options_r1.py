"""Author-only finite-h one/two/converged endpoint-defect maps; no physical solver/reference."""
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path
import numpy as np

T=Path(__file__).resolve().parents[1];TAG="upl_tpi_next_time_layer_options_r1"
NOTE=T/"notes"/(TAG+".md");OUT=T/"outputs"/TAG;CHECK=T/"logs"/(TAG+".check.json")
OLD=T/"outputs/upl_tpi_case02_step_spectrum_r2"
SUMMARY=OLD/"summary.json";MODES=OLD/"nominal_modes.csv"
OLD_CHECK=T/"logs/upl_tpi_case02_step_spectrum_r2.check.json"
EPS,TINY=np.finfo(float).eps,float(np.nextafter(0.,1.))


def need(q,text):
 if not bool(q):raise ValueError(text)
def stat(path):
 p=Path(path).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(path):return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def write_json(path,value):
 with path.open("x",encoding="utf8",newline="\n")as f:json.dump(value,f,indent=2,allow_nan=False);f.write("\n")
def write_csv(path,rows):
 with path.open("x",encoding="utf8",newline="")as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def parameters_and_modes():
 old=read(SUMMARY);check=read(OLD_CHECK)
 need(check.get("passed")is True and old.get("algebra_completed")is True and
  old.get("actual_SPH_full_spectrum_proven")is False and old.get("nominal_modes")==120,
  "Actual retained nominal algebra required; never relabel it as SPH spectrum")
 p=old["parameters"]
 c=dict(M=p["Mc_loaded_double_Pa"],rho=p["rho_kg_m3"],water=p["rhow_kg_m3"],
  k=p["k_loaded_float_m_s"],gamma=p["gamma_dynamic_Pa_m"],dp=p["dp_m"])
 c["tau"]=c["k"]*(c["rho"]-c["water"])/c["gamma"]
 steps=[("old6p25us",p["dt_original_s"]),("actual10us",p["dt_candidate_1_s"]),("context20us",p["dt_candidate_2_s"])]
 with MODES.open(encoding="utf-8-sig",newline="")as f:original=list(csv.DictReader(f))
 need(len(original)==120 and [int(x["mode"])for x in original]==list(range(120)),"Retained120-mode ordering differs")
 modes=[]
 for x in original:
  need(x["actual_C02_boundary_or_full_Rgamma_symbol"]=="False","Original nominal disclaimer differs")
  modes.append(dict(scope="retained_nominal_positive_LP",mode=int(x["mode"]),family=x["family"],
   q=float(x["q_P1_common_symbol_m_inv"]),mu=float(x["mu_normalized_neighbor_symbol"])))
 for i,(q,mu)in enumerate((q,mu)for q in(math.pi/2,math.pi/c["dp"])for mu in(.2,.8)):
  modes.append(dict(scope="previous_illustrative_common_symbol",mode=i,family="previous_finite_h_fixtures",q=q,mu=mu))
 need(all(x["q"]>0 and -1<x["mu"]<1 for x in modes),"Only existing nonzero-q fixed-point examples admitted")
 return c,steps,modes


def fixed_point(y,c,q):
 r=c["water"]/c["rho"];iq=1j*q
 return -r/(1-r)*y[0]-c["gamma"]*iq/(c["k"]*q*q*(1-r))*y[1]


def step(y,c,q,mu,h,iterations):
 """Original P1 mechanics/alpha.5; endpoint y is frozen through every pressure row."""
 sigma,velocity,pn,previous=y;iq=1j*q
 an=iq*(sigma-pn)/c["rho"]
 vh=velocity+.5*h*an;sh=sigma+.5*h*c["M"]*iq*velocity
 guess=pn+.5*(pn-previous)
 ah=iq*(sh-guess)/c["rho"]
 sf=sigma+h*c["M"]*iq*vh;vf=velocity+h*ah
 if iterations is None:
  pf=fixed_point((sf,vf),c,q) # Assumed converged algebra only; no actual global solve.
 else:
  S=c["k"]*q*q/(1-mu);pf=guess
  for _ in range(iterations):
   ae=iq*(sf-pf)/c["rho"] # Refresh complete pressure->acceleration feedback each round.
   source=-c["gamma"]*iq*vf+c["water"]*c["k"]*iq*ae
   pf=(source+S*mu*pf)/S
 return np.array((sf,vf,pf,pn),dtype=complex)


def calculations(c,steps,modes):
 cases=[];roots=[];reports={};trial=np.array((1+.2j,.3-.1j,-.4+.7j,.2+.5j))
 methods=(("one",1,3),("two",2,4),("converged",None,None))
 for mode in modes:
  q,mu=mode["q"],mode["mu"];r=c["water"]/c["rho"];delta=(1-r)*(1-mu);m=1-delta
  for dtname,h in steps:
   for name,iters,forces in methods:
    A=np.column_stack([step(e,c,q,mu,h,iters)for e in np.eye(4,dtype=complex)])
    direct=step(trial,c,q,mu,h,iters);tol=4096*EPS*(abs(A)@abs(trial)+abs(direct))+4096*TINY
    need(np.all(abs(A@trial-direct)<=tol),"Declared finite-h map is not linear")
    ph=trial[2]+.5*(trial[2]-trial[3]);target=fixed_point(direct[:2],c,q)
    mk=0. if iters is None else m**iters
    # Stable delta formula avoids cancellation in1-m^2 for almost constant modes.
    dk=1. if iters is None else delta if iters==1 else delta*(1+m)
    expected=dk*target+mk*ph
    budget=4096*EPS*(abs(expected)+abs(dk*target)+abs(mk*ph)+abs(direct[2]))+4096*TINY
    need(abs(direct[2]-expected)<=budget,"Complete endpoint defect does not equal the declared J power")
    scale=np.array((c["M"],math.sqrt(c["M"]/c["rho"]),c["M"],c["M"]))
    B=A*scale[None,:]/scale[:,None];z,v=np.linalg.eig(B)
    err=np.max(abs(B@v-v*z[None,:]),axis=0)
    eb=4096*EPS*(np.linalg.norm(B,np.inf)+abs(z))*np.max(abs(v),axis=0)+4096*TINY
    need(np.all(err<=eb),"Finite-h small-matrix eigensystem arithmetic failed")
    radius=float(max(abs(z)));lag=0. if iters is None else mk/(2*dk)
    case=dict(**mode,dt_family=dtname,dt_s=h,method=name,finite_endpoint_rows=iters,
     full_force_calls_if_straightforward=forces,converged_operator_cost_unknown=iters is None,
     m_original=m,m_effective=mk,delta_effective=dk,Omega_squared=c["M"]*q*q*h*h/c["rho"],
     dt_over_tau=h/c["tau"],low_Omega_positive_m_sufficient_h_over_tau_lt1=h/c["tau"]<1.,
     leading_pressure_lag_h_PL_factor_with_minus_sign=lag,nominal_spectral_radius=radius,
     strict_float_radius_above_one=radius>1.,eigensystem_arithmetic_ratio=float(max(err/eb)),
     all_pressure_accelerations_refreshed=True,solid_endpoint_changed_between_rows=False,
     actual_SPH_spectrum_or_timestep_admission=False)
    cases.append(case)
    for j,value in enumerate(z):roots.append(dict(scope=mode["scope"],mode=mode["mode"],dt_family=dtname,method=name,
     root=j,z_real=float(value.real),z_imag=float(value.imag),abs_z=float(abs(value))))
    key=mode["scope"]+"/"+dtname+"/"+name
    report=reports.setdefault(key,dict(cases=0,maximum_computed_radius=0.,strict_radius_above_one_count=0))
    report["cases"]+=1;report["maximum_computed_radius"]=max(report["maximum_computed_radius"],radius)
    report["strict_radius_above_one_count"]+=int(radius>1.)
 need(len(cases)==124*3*3 and len(roots)==4*len(cases),"Only existing mode/step examples may be used")
 return cases,roots,reports


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--execution-authorized",action="store_true")
 need(p.parse_args().execution_authorized,"Root full-read unique algebra-only authorization required")
 need(not OUT.exists()and not CHECK.exists(),"Existing/partial mathematical products protected")
 before=[stat(x)for x in(Path(__file__),NOTE,SUMMARY,MODES,OLD_CHECK)]
 result=dict(stage=TAG,passed=False,consumed=before,solver_invocations=0,native_invocations=0,old_script_invocations=0,
  build_invocations=0,SHA_scans=0,physical_acceptance=False,actual_SPH_spectrum_proven=False,
  actual_timestep_admission=False,physical_candidate_selected=False,new_reference_trajectory=False,
  actual_GPU_float_kernel_replayed=False,intermediate_native_float_rounding_modeled=False)
 try:
  c,steps,modes=parameters_and_modes();cases,roots,reports=calculations(c,steps,modes);OUT.mkdir()
  write_csv(OUT/"cases.csv",cases);write_csv(OUT/"roots.csv",roots)
  need(all(stat(x["path"])==x for x in before),"Frozen mathematical input changed")
  result.update(passed=True,algebra_complete=True,parameters=c,retained_nominal_modes=120,previous_illustrative_modes=4,
   matrices=len(cases),roots=len(roots),step_reports=reports,
   interpretation="Spectral radii/failures are reported, not converted to actual SPH stability or physical acceptance",
   files=[stat(OUT/(n+".csv"))for n in("cases","roots")])
 except Exception as exc:result.update(first_failure=str(exc),partial_outputs_preserved=True);raise
 finally:write_json(CHECK,result)
 print(str(CHECK))


if __name__=="__main__":main()
