"""Selective angular/spatial pressure audit on fixed material shells at matching real clocks."""
import argparse
import json
import mmap
from pathlib import Path
from cryer_shell_equilibrium import TESTS as T,Reference,reference_fields,write,need,np,pd
from cryer_p3_radial_check_r1 import pressure_fields
from cryer_p3_verify_r1 import CENTER
from cryer_coupled_shell_modes import DT
from scipy.spatial import cKDTree


def native(path,part,step):
    with path.open("rb") as f:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mem:
            p,fs=pressure_fields(mem,part,step)
    return p.astype(float),np.isin(fs,(2,3))


def read_private(path,step,ids):
    with np.load(path) as data:
        need(int(data["step"])==step and np.array_equal(data["ids"],ids),"Identical step and soil IDs")
        return data["p"]


def extrema(p,ids,index):
    vals=p[index]
    lo=vals.min();hi=vals.max()
    return dict(minimum_Pa=lo,minimum_first_native_id=int(ids[index[vals==lo][0]]),minimum_ties=int(sum(vals==lo)),
                maximum_Pa=hi,maximum_first_native_id=int(ids[index[vals==hi][0]]),maximum_ties=int(sum(vals==hi)))


def work(stage):
    dest=T/"figures"
    tag="cryer_weak_angular_"+stage+"_r1"
    check=T/"logs"/(tag+".check.json")
    need(not check.exists(),"Checks are immutable")
    with np.load(T/"outputs/cryer_tet_reference_r1.npz") as cache:
        ids=cache["native_ids"];shell=cache["material_shell"];x=cache["x0"]
    need(np.array_equal(ids[shell==1],CENTER) and len(ids)==37173,"All fixed soil/18 center IDs")
    radius=np.arange(1,21)*.0025
    need(np.max(abs(np.linalg.norm(x,axis=1)-radius[shell-1]))<1e-14,"Original radii; no bin refitting")
    groups=[np.flatnonzero(shell==j) for j in range(1,21)]
    # Deterministic angular graph from at most six incident near neighbours per node, symmetrized.
    pairs=[]
    for ix in groups:
        near=cKDTree(x[ix]).query(x[ix],k=7)[1][:,1:]
        ab=np.column_stack((np.repeat(ix,6),ix[near].ravel()))
        pairs.append(np.unique(np.sort(ab,axis=1),axis=0))
    local=T/"outputs/cryer_p3_gpu_drain4097_r1"
    server_tag="CaseCryer_TPI_P3_nu030_peak_r1_GPU_out"
    server=T/"outputs"/server_tag/server_tag
    oldhist=pd.read_csv(T/"figures/cryer_p3_server_peak_actual_r1/physical/native_and_theory.csv",float_precision="round_trip")
    oldlocal=pd.read_csv(T/"figures/cryer_p3_gpu_drain4097_r1.csv",float_precision="round_trip")
    hdir=T/"outputs"/("cryer_weak_open_r1" if stage=="opening" else "cryer_weak_peak_r1")
    seal=json.loads((hdir/"completed.json").read_text())
    newhist=pd.read_csv(hdir/"history.csv",float_precision="round_trip")
    steps=[4096,4097,4160] if stage=="opening" else [seal["steps"]]
    small=[];detail=[];center=[];meta=[]
    refs=[Reference(.3,modes=k,finite=False) for k in (360,720)]
    for ref in refs:
        ref.cv=ref.H*ref.kappa
        ref.decay=ref.xi**2*ref.cv/.05**2
    for step in steps:
        part=65 if step==4097 else step//64
        opath=(local if step==4097 else server)/"data"/f"Part_{part:04d}.bi4"
        npath=hdir/f"state_{step}.npz"
        tau=(step-4096)*DT
        orig,fs=native(opath,part,step)
        need(np.array_equal(fs,shell==20),"Actual FS slots")
        cand=read_private(npath,step,ids)
        row=(oldlocal if step==4097 else oldhist).loc[lambda df:df.completed_step==step].iloc[0]
        ht=newhist[newhist.step==step].iloc[0]
        theory,high=[reference_fields(ref,tau,radius)[0] for ref in refs]
        # A finite mode cutoff on the very first opening step can contribute a visible error.
        diff_early=max(abs(theory-high))
        need(abs(row.center18_Pa-orig[shell==1].mean())<1e-7 and abs(ht.center_Pa-cand[shell==1].mean())<1e-8,"Two source summaries")
        meta.append(dict(step=step,old=str(opath.relative_to(T.parent)),new=str(npath.relative_to(T.parent)),
                         theory360_vs720_absmax_Pa=float(diff_early)))
        for name,p in (("original_P3",orig),("weak_flux_3D",cand)):
            need(np.all(np.isfinite(p)) and (tau==0 or np.all(p[fs]==0)),"All physical pressures and drain")
            for slot in groups[0]:
                center.append(dict(step=step,model=name,id=int(ids[slot]),p_Pa=p[slot],M0_Pa=high[0],delta_Pa=p[slot]-high[0]))
            mean=np.array([p[a].mean() for a in groups])
            common=dict(step=step,tau_s=tau,model=name)
            for j,(ix,edge) in enumerate(zip(groups,pairs)):
                jump=abs(p[edge[:,0]]-p[edge[:,1]])
                ex=extrema(p,ids,ix)
                detail.append(dict(**common,shell=j+1,r0_over_a=(j+1)/20,n=len(ix),
                    mean_Pa=mean[j],M0_Pa=high[j],mean_minus_M0_Pa=mean[j]-high[j],angular_std_Pa=p[ix].std(),
                    p05_Pa=np.percentile(p[ix],5),p95_Pa=np.percentile(p[ix],95),**ex,
                    n_angular_edges=len(edge),tangential_jump_rms_Pa=np.sqrt(np.mean(jump**2)),
                    max_tangential_jump_Pa=jump.max()))
            all_idx=np.arange(len(p))
            # Angular scatter removes the actual shell mean. Radial comparators retain continuum curvature.
            e=mean-high
            osc=e[15:19]-e[14:18]
            row=dict(**common,**extrema(p,ids,all_idx),center18_mean_Pa=mean[0],center18_std_Pa=p[groups[0]].std(),
                shell17_minus18_Pa=mean[16]-mean[17],theory17_minus18_Pa=high[16]-high[17],
                shell17_curvature_error_Pa=e[15]-2*e[16]+e[17],shell18_curvature_error_Pa=e[16]-2*e[17]+e[18],
                max_shell15to19_error_jump_Pa=max(abs(osc)),
                all_within_shell_angular_rms_Pa=np.sqrt(np.mean((p-mean[shell-1])**2)),
                all_material_radial_mean_error_rms_Pa=np.sqrt(np.mean(e[shell-1]**2)))
            for key,ix in (("min",np.argmin(p)),("max",np.argmax(p))):
                row[key+"_shell_first"]=int(shell[ix])
            small.append(row)
    for suffix,rows in (("summary",small),("shells",detail),("center",center)):
        write(dest/(tag+"_"+suffix+".csv"),rows)
    check.write_text(json.dumps(dict(passed=True,inputs=meta,source_seal_steps=seal["steps"],native_ids=37173,
        center_ids=CENTER,coverage="Fixed source-referenced groups, original pre-open and every available selected real snapshot. Uploaded material cases have the same initial IDs and shell definitions. First step is a retained local P3 comparison.",
        pressure_reference="Original nu=.3 M0, actual gamma=9806.65 and actual tau, 720 modes compared to 360; at tau=0 use closed 10 kPa state",
        angular_graph="6 nearest original cartesian neighbors within each material shell, sorted unique undirected pairs",
        reading="Original BI4 memory-mapped only at selected steps; access Idp,PorePress,FSType. Candidate NPZ accesses ids,step,p. No native decoding, new trajectory or interpolations."),
        ensure_ascii=False,allow_nan=False,indent=2)+"\n",encoding="utf8")
    print(pd.DataFrame(small).to_string(index=False))


def peak_shells():
    """The solver stores all shell means/std, but particle arrays only at the endpoint."""
    hdir=T/"outputs/cryer_weak_peak_r1"
    seal=json.loads((hdir/"completed.json").read_text())
    history=pd.read_csv(hdir/"history.csv",float_precision="round_trip")
    shelltab=pd.read_csv(hdir/"shells.csv",float_precision="round_trip")
    need(history.iloc[-1].step==seal["steps"],"Closed peak output and actual endpoint")
    with np.load(T/"outputs/cryer_tet_reference_r1.npz") as z:
        bins=z["material_shell"]
    ref=Reference(.3,modes=720,finite=False)
    ref.cv=ref.H*ref.kappa
    ref.decay=ref.xi**2*ref.cv/.05**2
    allowed=history[history.tau_s*ref.legacy_cv/.05**2>=.005]
    step=int(allowed.iloc[np.argmax(allowed.center_Pa)].step)
    selected=shelltab[shelltab.step==step].sort_values("material_shell")
    need(len(selected)==20 and selected["count"].sum()==37173,"All sampled peak shells")
    server_tag="CaseCryer_TPI_P3_nu030_peak_r1_GPU_out"
    part=step//64
    raw,fs=native(T/"outputs"/server_tag/server_tag/"data"/f"Part_{part:04d}.bi4",part,step)
    ranges=[]
    high=reference_fields(ref,(step-4096)*DT,np.arange(1,21)*.0025)[0]
    for k,(_,r) in enumerate(selected.iterrows()):
        s=raw[bins==k+1]
        ranges.append(dict(step=step,tau_s=(step-4096)*DT,shell=k+1,n=int(r["count"]),
            theory_Pa=high[k],old_mean_Pa=s.mean(),weak_mean_Pa=r.p_mean_Pa,
            old_std_Pa=s.std(),weak_std_Pa=r.p_std_Pa))
    count=np.bincount(bins)[1:]
    def describe(frame):
        p=frame.p_mean_Pa.to_numpy()
        s=frame.p_std_Pa.to_numpy()
        return (p[16]-p[17],np.sqrt(np.average(s**2,weights=count)),max(s),int(np.argmax(s))+1)
    late=[]
    for end,rows in shelltab.groupby("step"):
        if end<4160:continue
        tau=(end-4096)*DT
        d,ang,upper,which=describe(rows.sort_values("material_shell"))
        late.append(dict(step=int(end),tau_s=tau,angular_rms_Pa=ang,shell17_minus18_Pa=d,
                         max_angular_shell=which,max_angular_std_Pa=upper))
    df=pd.DataFrame(late)
    # Report actual consecutive sampled times, retaining non-monotone transients.
    summary=[]
    for lo,hi in ((0,.001),(.001,.005),(.005,.02),(.02,.04),(.04,.0626)):
        f=df[(df.tau_s>=lo)&(df.tau_s<hi)]
        summary.append(dict(t_lo_s=lo,t_hi_s=hi,samples=len(f),max_sample_angular_rms_Pa=max(f.angular_rms_Pa),
           max_sample_angular_step=int(f.loc[f.angular_rms_Pa.idxmax(),"step"]),end_sample_angular_rms_Pa=f.angular_rms_Pa.iloc[-1],
           min_sample_shell17_minus18_Pa=min(f.shell17_minus18_Pa),max_sample_shell17_minus18_Pa=max(f.shell17_minus18_Pa)))
    tag="cryer_weak_angular_peak_r1"
    write(T/"figures"/(tag+"_shells.csv"),ranges)
    write(T/"figures"/(tag+"_intervals.csv"),summary)
    print(pd.DataFrame(ranges).iloc[[0,16,17]].to_string(index=False));print(pd.DataFrame(summary).to_string(index=False))


if __name__=="__main__":
    a=argparse.ArgumentParser(description=__doc__);a.add_argument("stage",choices=["opening","final","peak"])
    stage=a.parse_args().stage
    if stage=="peak":peak_shells()
    else:work(stage)
