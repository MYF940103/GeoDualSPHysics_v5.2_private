"""Review the returned weak Cryer raw states against the unmodified package in this directory."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

N=37173
DT=2.**-19
TD=4096*DT
GATE="cryer_weak_3d_peak_r1_gates.json"

def check(condition,message):
    if not condition:raise ValueError(message)

def sha(path):
    with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def rows(path):
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def table(path,items):
    with path.open("x",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,items[0]);writer.writeheader();writer.writerows(items)

def determinants(pos,tets):
    edges=pos[tets[:,1:]]-pos[tets[:,0],None]
    return np.einsum("ij,ij->i",edges[:,0],np.cross(edges[:,1],edges[:,2]))

def residuals(values):
    x=np.asarray(values,dtype=float)
    return dict(rms=float(np.sqrt(np.mean(x*x))),max_abs=float(np.max(np.abs(x))),endpoint=float(x[-1]))

def figures(dest,hist,profiles,peak_rows,smoke):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout="constrained")
    open_rows=[r for r in hist if r["step"]>=4096]
    t=[r["legacy_Tv"] for r in open_rows]
    for ax,key,theory,label in zip(axes[:2],("center18_Pa","surface_inward_mm"),("M0_center18_Pa","M0_surface_inward_mm"),
           ("Center pressure (Pa)","Surface inward displacement (mm)")):
        ax.plot(t,[r[theory] for r in open_rows],"--",color="black",label="M0 at actual clock")
        ax.plot(t,[r[key] for r in open_rows],".",ms=3,label="Native-mass weak GPU")
        ax.set(xlabel="Legacy Tv after drainage",ylabel=label);ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax=axes[2]
    for step in sorted({r["step"] for r in profiles}):
        group=[r for r in profiles if r["step"]==step]
        ax.plot([r["r_over_a"] for r in group],[r["p_mean_Pa"] for r in group],".-",lw=1,label=f"step {step}")
    ax.set(xlabel="Reference radius / a",ylabel="Shell mean pressure (Pa)");ax.legend(fontsize=7);ax.grid(alpha=.2)
    fig.savefig(dest/"pressure_settlement_profiles.png",dpi=170);plt.close(fig)
    if not smoke:
        fig,ax=plt.subplots(figsize=(7.5,4),layout="constrained")
        post=[r for r in peak_rows if float(r["tau_s"])>=0]
        ax.plot([1000*float(r["tau_s"]) for r in post],[float(r["center_Pa"]) for r in post],label="Retained dense GPU peak")
        pts=[r for r in open_rows if r["step"]<=36864]
        ax.plot([r["tau_s"]*1000 for r in pts],[r["center18_Pa"] for r in pts],"o",ms=3,label="Replayed material fields")
        ax.plot([r["tau_s"]*1000 for r in pts],[r["M0_center18_Pa"] for r in pts],"--",color="black",label="M0")
        ax.set(xlabel="Time after drainage (ms)",ylabel="Center pressure (Pa)");ax.legend();ax.grid(alpha=.2)
        fig.savefig(dest/"peak_replay.png",dpi=170);plt.close(fig)

def review(package,run,dest,smoke):
    manifest=read_json(package/"manifest.json");seal=read_json(run/"server_run.json")
    mode="smoke" if smoke else "full"
    check(seal["mode"]==mode and (run/"complete.txt").read_text().strip()==mode,"Incorrect return mode")
    check(seal["package"].lower()==sha(package/"manifest.json"),"Server used a different package")
    for base,entries in ((package,manifest["files"]),(run,seal["files"])):
        for e in entries:
            p=base/e["name"];check(p.stat().st_size==e["bytes"] and sha(p)==e["sha256"].lower(),f"Integrity failure {p.name}")
    actual=rows(run/"actual_clock.csv");inputs=package/"inputs"
    reference={int(r["step"]):r for r in rows(inputs/"reference.csv")}
    plan=[k for k,v in reference.items() if int(v["scheduled"])]
    steps=[int(r["step"]) for r in actual]
    expected=[4097,36867] if smoke else sorted(set(plan)|{4097,4160,25984,36864})
    check(steps==expected and len(plan)==265 and plan[-1]==481685,"Incomplete timetable")
    check({p.name for p in run.glob("state_*.bin")}=={f"state_{s}.bin" for s in expected},"Unexpected raw frame set")
    check(set(q["name"] for q in seal["files"])=={f"state_{s}.bin" for s in expected}|{"complete.txt","actual_clock.csv"},"Incomplete returned file manifest")
    with np.load(inputs/"reference_mesh.npz") as z:
        ids,x,tets,shell,fs=[z[k] for k in ("native_ids","x0","tets","material_shell","native_surface")]
    center=np.flatnonzero(shell==1);radius=np.linalg.norm(x,axis=1)
    check(np.array_equal(ids,np.arange(8,37181)) and len(center)==18 and len(fs)==5153 and
          np.array_equal(fs,np.flatnonzero(shell==20)),"Native identity, center or drainage set changed")
    det0=determinants(x,tets);check(np.all(det0!=0),"Degenerate reference tet")
    dense=rows(inputs/"open_history.csv")+rows(inputs/"peak_history.csv")[1:]
    dense_by_step={int(r["step"]):r for r in dense}
    check(len(dense_by_step)==len(dense),"Repeated retained peak step")
    hist=[];profiles=[];sample={4097,25984,plan[84],plan[164],plan[-1]}
    dest.mkdir(parents=True,exist_ok=False)
    for r,step in zip(actual,steps):
        fpath=run/f"state_{step}.bin";check(fpath.stat().st_size==15*N*8,"Bad raw-state size")
        anchor=inputs/fpath.name
        if anchor.exists():check(sha(anchor)==sha(fpath),"Retained material checkpoint differs")
        data=np.fromfile(fpath,dtype="<f8");check(np.isfinite(data).all(),"Nonfinite particle values")
        p,prev,u,v,stress,J=np.split(data,np.array([1,2,5,8,14])*N)
        u=u.reshape(-1,3);v=v.reshape(-1,3);stress=stress.reshape(-1,6);pos=x+u
        radial=np.linalg.norm(pos,axis=1);jac=determinants(pos,tets)/det0
        porosity=1.-(1.-float(np.float32(.3)))/J
        check(np.all(jac>0.) and np.all((porosity>0.)&(porosity<1.)) and radial.max()<.0525,"Invalid geometry or porosity")
        if step>4096:check(np.all(p[fs]==0.) and np.all(prev[fs]==0.),"Surface drainage history changed")
        row=reference[step];tau=(step-4096)*DT;tv=tau*(2e6*(1-.3)/((1+.3)*(1-2*.3)))*1e-5/(1000*9.81*.05**2)
        check(float(r["time_s"])==step*DT==float(row["time_s"]) and float(row["tau_s"])==tau and
              abs(float(row["legacy_Tv"])-tv)<1e-14,"Physical clock mismatch")
        if row["target_Tv"]:
            check(-1e-14<=tv-float(row["target_Tv"])<DT*1.098,"Target missed by one or more dyadic steps")
        settlement=1000*(radius[fs]-radial[fs]).mean()
        if step in dense_by_step:
            old=dense_by_step[step]
            check(float(p[center].mean())==float(old["center_Pa"]) and abs(settlement-float(old["surface_inward_mm"]))<1e-13,
                  "Saved original pressure or settlement differs")
        hist.append(dict(step=step,time_s=step*DT,tau_s=tau,legacy_Tv=float(row["legacy_Tv"]),target_Tv=row["target_Tv"],
                    center18_Pa=float(p[center].mean()),M0_center18_Pa=float(row["M0_center18_Pa"]) if tau>=0 else None,
                    surface_inward_mm=float(settlement),M0_surface_inward_mm=float(row["M0_surface_inward_mm"]) if tau>=0 else None,
                    min_Pa=float(p.min()),max_Pa=float(p.max()),max_surface_abs_Pa=float(np.max(abs(p[fs]))),
                    max_speed_m_s=float(np.linalg.norm(v,axis=1).max()),max_displacement_m=float(np.linalg.norm(u,axis=1).max()),
                    max_radius_m=float(radial.max()),min_J=float(J.min()),max_J=float(J.max()),
                    min_det_F=float(jac.min()),max_det_F=float(jac.max()),max_abs_stress_Pa=float(np.max(abs(stress)))))
        if smoke or step in sample:
            for j in range(1,21):
                values=p[shell==j]
                profiles.append(dict(step=step,time_s=step*DT,legacy_Tv=tv,r_over_a=j/20,count=len(values),
                     p_mean_Pa=float(values.mean()),p_sd_Pa=float(values.std()),p_min_Pa=float(values.min()),p_max_Pa=float(values.max())))
    gate=read_json(inputs/GATE);check(gate["peak_bounds_pass"] and read_json(inputs/"open_completed.json")["closed_pass"],"Missing peak/open qualification")
    result=dict(mode=mode,full_cycle_measured=not smoke,steps=steps[-1],frames=len(steps),actual_end_s=steps[-1]*DT,
                actual_end_legacy_Tv=hist[-1]["legacy_Tv"],native_materials=N,drained_materials=len(fs),
                fixed_center_ids=ids[center].tolist(),minimum_tet_det_F=min(r["min_det_F"] for r in hist),
                maximum_tet_det_F=max(r["max_det_F"] for r in hist),peak_qualification=gate,
                method="Small-strain native-mass weak 3D research GPU; fixed X0; conditional on case and saved fields.")
    if not smoke:
        tail=[r for r in hist if r["target_Tv"] and float(r["target_Tv"])>=.5]
        check(len(tail)==101 and hist[-1]["target_Tv"]=="1.0","Incomplete tail or endpoint")
        p=np.array([r["center18_Pa"] for r in tail]);u=np.array([r["surface_inward_mm"] for r in tail])
        result.update(tail_frames=len(tail),tail_center_errors_Pa=residuals(p-[r["M0_center18_Pa"] for r in tail]),
            tail_surface_errors_mm=residuals(u-[r["M0_surface_inward_mm"] for r in tail]),
            center_rebound_intervals=int(np.sum(np.diff(p)>0)),largest_tail_pressure_rise_Pa=float(max(0.,np.diff(p).max())),
            settlement_decrease_intervals=int(np.sum(np.diff(u)<0)),actual_endpoint=hist[-1],
            ultimate_drained_surface_displacement_mm=.1,
            scope="Errors and reversals measured at the original clocks; dense peak uses archived bounds. No new pass tolerance is assigned to decay or settlement.")
    table(dest/"actual_vs_theory.csv",hist);table(dest/"shell_profiles.csv",profiles)
    figures(dest,hist,profiles,dense,smoke)
    with (dest/"review.json").open("x",encoding="utf8") as f:json.dump(result,f,indent=2,allow_nan=False)
    print(dest/"review.json")

if __name__=="__main__":
    a=argparse.ArgumentParser(description=__doc__);a.add_argument("returned",type=Path);a.add_argument("new_review_directory",type=Path)
    a.add_argument("--smoke",action="store_true");a.add_argument("--package",type=Path,default=Path(__file__).resolve().parent)
    arg=a.parse_args();review(arg.package,arg.returned,arg.new_review_directory,arg.smoke)
