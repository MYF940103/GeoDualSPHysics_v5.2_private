"""Check every stored time, pressure-history owner and C08 GPU stage against CPU."""
import csv
import json
from pathlib import Path
import numpy as np
from c08_m0_beta_compare import DT,TESTS,native,describe,require,equal

from c08_m0_gpu_coupled_r1 import TAG,CPU_TAG

def gpu_phases(log,steps):
    phases={}
    rounds={}
    for line in log.read_text(encoding="utf-8",errors="replace").splitlines():
        v=line.split()
        if not v:continue
        if v[0]=="C08M0Dt":
            step,final=map(int,v[1:3])
            dt,bound,force,wave,pore,kgrad=map(float,v[3:])
            require(dt==DT and dt<=bound and bound==min(force,wave,pore) and kgrad>=0 and np.isfinite([dt,bound,force,wave,pore,kgrad]).all(),"GPU phase timestep")
            phases.setdefault(step,[]).append((final,bound))
        if v[0]=="C08GpuRound":
            step,r,f=map(int,v[1:])
            require((step,r) not in rounds and f==int(r==3 and step%40==0),"GPU endpoint/filter cadence")
            rounds[step,r]=f
    require(set(phases)==set(range(1,steps+1)) and all([x[0] for x in p]==[0,1,0,0,0] for p in phases.values()),"Missing dynamic phases")
    require(set(rounds)=={(s,r) for s in range(1,steps+1) for r in (1,2,3)},"Missing pressure round")
    return min(b for a in phases.values() for _,b in a)

def main():
    rows=[]
    paths={}
    for label in ("b0","b004"):
        paths[label]=[(TESTS/"outputs"/(tag+"_"+label)/"data") for tag in (CPU_TAG,TAG)]
        for path in paths[label]:
            require(len(list(path.glob("Part_*.bi4")))==43,"Missing or extra frames")
    floors={k:gpu_phases(v[1].parent/"Run.out",42) for k,v in paths.items()}
    clocks=[0.]
    for _ in range(42):clocks.append(clocks[-1]+DT)
    last={}
    initial={}
    for i,t in enumerate(clocks):
        off=None
        for label,beta in (("b0",0.),("b004",.04)):
            frames=[]
            for backend,path in zip(("cpu","gpu"),paths[label]):
                key=(label,backend)
                f,history,all_ids=native(path,i,t,clocks[max(0,i-1)],beta)
                if i==0:initial[key]=f
                else:require(equal(history,last[key]),"Previous pressure writeback by native ID")
                last[key]=f["PorePress"]
                state=describe(f,initial[key])
                if i:require(state["positive_surface"]==0,"Completed free-surface pressure")
                if backend=="gpu":
                    if beta==0:off=all_ids
                    else:require(all(equal(v,off[k]) for k,v in all_ids.items()),"Unexpected beta effect before any negative pressure")
                require(state["negative_total"]==0,"Short PRE ceased to be a beta-inactive window")
                frames.append(f)
            a,b=frames
            p=b["PorePress"].astype(float)-a["PorePress"]
            d=b["Posd"]-a["Posd"]
            v=b["Vel"].astype(float)-a["Vel"]
            metrics=dict(beta=beta,step=i,time_s=t,pressure_rms_Pa=float(np.sqrt(np.mean(p*p))),pressure_max_Pa=float(np.abs(p).max()),
                displacement_max_mm=float(1000*np.max(np.linalg.norm(d,axis=1))),velocity_max_m_s=float(np.linalg.norm(v,axis=1).max()),
                J_max=float(np.abs(a["PoroVolumeRatio"]-b["PoroVolumeRatio"]).max()),kappa_max=float(np.abs(a["Kplastic"]-b["Kplastic"]).max()),
                FS_class_differences=int(np.count_nonzero(a["FSType"]!=b["FSType"])))
            for field in a:
                if ("Sigma" in field or "Stress" in field) and np.issubdtype(a[field].dtype,np.number):
                    metrics[field+"_max_Pa"]=float(np.abs(a[field].astype(float)-b[field]).max())
            rows.append(metrics)
    target=TESTS/"figures"/(TAG+"_cross.csv")
    with target.open("x",newline="") as file:
        out=csv.DictWriter(file,fieldnames=list(rows[0]));out.writeheader();out.writerows(rows)
    worst={k:max(r[k] for r in rows) for k in rows[0] if k not in ("beta","step","time_s")}
    passed=worst["pressure_rms_Pa"]<=5 and worst["displacement_max_mm"]<=.005
    result=dict(passed=passed,frames_per_pair=43,ids_per_frame=7060,soil=5000,arrays=22,
        per_run_phase_checks=210,pressure_rounds=126,step40_filter_count=1,minimum_bounds_s=floors,maxima=worst,
        thresholds=dict(pressure_rms_Pa=5,displacement_max_mm=.005),scope="Closed 210 us gravity startup; beta never activated.")
    with (TESTS/"logs"/(TAG+"_cross.json")).open("x") as out:json.dump(result,out,indent=2)
    print(json.dumps(result,indent=2))
    require(passed,"CPU/GPU short pressure or displacement comparison")

if __name__=="__main__":main()

