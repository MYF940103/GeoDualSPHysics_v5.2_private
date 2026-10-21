"""Publish accepted k1e-3/k1e-4 figures and real-frame data at target DeltaTv=.01.

Read-only with respect to solver outputs, frozen release reviews and inputs.
No interpolation of SPH states; target/actual time and native PART are retained.
"""
import hashlib
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from release_case import CASE, REPO, native, inspect, model, settlement, pressure_theory
from postprocess_terzaghi_q0 import degree_theory

FIG = CASE/"figures"
PREFIX = "full_validation_latest"
TARGETS = (.005, .05, .1, .25, .4, .5, .7, 1., 1.5, 2.)
READER = REPO/"bin/windows/ReadHydroMechPart_win64.exe"


def bound(path):
    path=Path(path).resolve()
    with path.open("rb") as stream:digest=hashlib.file_digest(stream,"sha256").hexdigest()
    return dict(path=str(path),sha256=digest)


def degree(tv):
    return 0. if tv<=0 else degree_theory(tv)


def load(key):
    label="full_validation_release_"+key+"_GPU"
    check_path=FIG/(label+".check.json")
    check=json.loads(check_path.read_text(encoding="utf8"))
    assert check["passed"] and check["numerical_safety_passed"] and check["final"]["tv"]>=2-1e-6
    hashes={str(Path(e["path"]).resolve()):e["sha256"].lower() for e in check["evidence"]}
    evidence=[bound(check_path)]
    def verified(path):
        b=bound(path);assert b["sha256"]==hashes[b["path"]],"Changed retained source: "+str(path)
        evidence.append(b)
    source=FIG/(label+"_history.csv");verified(source)
    source_profiles=FIG/(label+"_profiles.csv");verified(source_profiles)
    verified(READER)
    h=pd.read_csv(source,float_precision="round_trip")
    assert h.time_s.is_monotonic_increasing and len(h)==check["frames"]
    folder=Path(check["output"])
    xml=next(Path(p) for p in hashes if Path(p).parent==folder and Path(p).suffix==".xml")
    verified(xml);m=model(xml)
    assert all(m[k]==check["model"][k] for k in m)
    verified(folder/"data/Part_0000.bi4");initial=native(READER,folder,0)
    z0=initial.z.to_numpy().reshape(10,100).mean(0)
    def frame(i):
        verified(folder/"data"/f"Part_{i:04d}.bi4")
        a=native(READER,folder,i);r=inspect(a,initial,m)
        for k in ("time_s","mean_pressure_pa","top_settlement_mm","bottom_settlement_mm","max_layer_total_error_pa","top_gap_pa","Q_pa"):
            assert np.isclose(r[k],h.iloc[i][k],rtol=1e-12,atol=1e-11),k
        return a
    selected=[]
    for target in np.arange(201)/100:
        wanted=m["tD"]+target*m["H"]**2/m["cv"]
        i=int(abs(h.time_s-wanted).idxmin())
        r=h.iloc[i].to_dict()
        r.update(k_m_s=m["k"],case=key,native_part=i,native_file=f"Part_{i:04d}.bi4",target_tv=float(target),target_time_s=float(wanted))
        r["actual_tv"]=r.pop("tv")
        r["u_num"]=1-r["mean_pressure_pa"]/m["q0"]
        r["u_theory"]=degree(r["actual_tv"])
        r["mean_excess_kpa"]=r["mean_pressure_pa"]/1000
        r["mean_theory_pa"]=m["q0"]*(1-r["u_theory"])
        if target==0:
            r["classical_top_mm"]=0.;r["classical_bottom_mm"]=0.
        r["top_theory_error_mm"]=r["top_settlement_mm"]-r["classical_top_mm"]
        r["bottom_theory_error_mm"]=r["bottom_settlement_mm"]-r["classical_bottom_mm"]
        selected.append(r)
    sampled=pd.DataFrame(selected)
    assert sampled.native_part.is_unique and len(sampled)==201
    assert abs(sampled.actual_tv-sampled.target_tv).max()<=m["cv"]*float(h.time_s.diff().max())/2+1e-6
    frame(int(sampled.iloc[0].native_part));frame(int(sampled.iloc[-1].native_part))
    profiles=[];targets=[];states={}
    for target in TARGETS:
        i=int(abs(h.time_s-(m["tD"]+target*m["H"]**2/m["cv"])).idxmin())
        a=frame(i);tv=float(h.iloc[i].tv)
        p=a.pressure.to_numpy().reshape(10,100).mean(0)
        truth=pressure_theory(z0,tv,m)
        states[target]=(p,truth,tv,float(a.time_s.iloc[0]))
        for j in range(100):profiles.append(dict(case=key,k_m_s=m["k"],target_tv=target,actual_tv=tv,
            time_s=float(a.time_s.iloc[0]),native_part=i,layer=j,z0_H=float(z0[j]/m["H"]),pressure_pa=float(p[j]),classical_pa=float(truth[j])))
        targets.append(dict(case=key,k_m_s=m["k"],target_tv=target,actual_tv=tv,time_s=float(a.time_s.iloc[0]),native_part=i,
            profile_rmse_pa=float(np.sqrt(np.mean((p-truth)**2)))))
    final=sampled.iloc[-1]
    summary=dict(case=key,k_m_s=m["k"],native_frames=len(h),published_history_rows=201,actual_time_s=float(final.time_s),
        actual_tv=float(final.actual_tv),mean_pressure_pa=float(final.mean_pressure_pa),top_settlement_mm=float(final.top_settlement_mm),
        classical_top_mm=float(final.classical_top_mm),top_settlement_error_pct=float(100*(final.top_settlement_mm/final.classical_top_mm-1)),
        final_profile_rmse_pa=targets[-1]["profile_rmse_pa"],Q_pa=float(final.Q_pa),
        max_abs_target_tv_offset=float(abs(sampled.actual_tv-sampled.target_tv).max()))
    cadence=dict(case=key,k_m_s=m["k"],solver_dt_s=m["dt"],native_interval_s=float(h.time_s.diff().median()),
        native_delta_tv=float(h.tv.diff().median()),published_target_delta_tv=.01,
        future_timeout_s_for_delta_tv_point01=.01*m["H"]**2/m["cv"])
    return dict(key=key,model=m,history=sampled,profiles=pd.DataFrame(profiles),targets=targets,
        states=states,z0=z0,summary=summary,cadence=cadence,evidence=evidence)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair-layout",action="store_true")
    args=parser.parse_args()
    check_path=FIG/(PREFIX+".check.json")
    previous=[]
    if check_path.exists():
        prior=json.loads(check_path.read_text(encoding="utf8"))
        assert args.repair_layout and prior["visual_review_pending"]
        assert not (FIG/(PREFIX+".visual.json")).exists(),"Preserve visually approved publication"
        for item in prior["outputs"]:assert bound(item["path"])["sha256"]==item["sha256"]
        snapshot=CASE/"tests/outputs/latest_figures_layout_r1"
        assert (snapshot/check_path.name).is_file()
        previous=[bound(p) for p in snapshot.iterdir() if p.is_file()]
    accepted_path=CASE/"tests/logs/formal_release_k34_r1.review.json"
    accepted=json.loads(accepted_path.read_text(encoding="utf8"));assert accepted["passed"]
    runs=[load(key) for key in ("k1em3","k1em4")]
    evidence=[bound(p) for p in (Path(__file__),Path(__file__).with_name("release_case.py"),
        Path(__file__).with_name("compare_precision_q0.py"),Path(__file__).with_name("postprocess_terzaghi_q0.py"),accepted_path)]
    outputs=[]
    def csv(name,data):
        path=FIG/(PREFIX+name+".csv");assert args.repair_layout or not path.exists()
        pd.DataFrame(data).to_csv(path,index=False,mode="w" if args.repair_layout else "x");outputs.append(path)
    csv("_history_data",pd.concat([r["history"] for r in runs],ignore_index=True))
    csv("_profiles_data",pd.concat([r["profiles"] for r in runs],ignore_index=True))
    csv("_targets",[row for r in runs for row in r["targets"]])
    csv("_summary",[r["summary"] for r in runs])
    csv("_output_cadence",[r["cadence"] for r in runs])
    plt.rcParams.update({"font.size":11,"axes.spines.top":False,"axes.spines.right":False})
    colors=("#256da3","#c47725");styles=("-","--")
    def finish(fig,suffix,note,top=.94):
        fig.text(.5,.012,note,ha="center",fontsize=9)
        fig.tight_layout(rect=(0,.045,1,top));path=FIG/(PREFIX+suffix+".png");assert args.repair_layout or not path.exists()
        with path.open("wb" if args.repair_layout else "xb") as stream:fig.savefig(stream,dpi=180)
        plt.close(fig);outputs.append(path)
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for r,color,style in zip(runs,colors,styles):
        h=r["history"];label=f"k={r['model']['k']:g} m/s"
        axes[0,0].plot(h.actual_tv,h.mean_excess_kpa,color=color,ls=style,label=label)
        late=h[h.actual_tv>=1-1e-3]
        axes[0,1].plot(late.actual_tv,late.mean_excess_kpa,color=color,ls=style,label=label)
        axes[1,0].plot(h.actual_tv,h.u_num,color=color,ls=style,label=label)
        axes[1,1].plot(h.actual_tv,h.top_settlement_mm,color=color,ls=style,label=label)
    grid=np.linspace(0,2,1001);u=np.array([degree(v) for v in grid]);m=runs[0]["model"]
    axes[0,0].plot(grid,m["q0"]*(1-u)/1000,":",color=".2",label="Classical reference")
    late=grid>=1;axes[0,1].plot(grid[late],m["q0"]*(1-u[late])/1000,":",color=".2")
    axes[1,0].plot(grid,u,":",color=".2")
    axes[1,1].plot(grid,[0 if v==0 else settlement(runs[0]["z0"][-1],m["tD"]+v/m["cv"],m) for v in grid],":",color=".2",label="Classical, same material point")
    for ax,title,ylabel in zip(axes.flat,("Mean excess pore pressure","Late dissipation: Tv >= 1","Consolidation degree","Top material settlement"),
        ("Mean excess pressure (kPa)","Mean excess pressure (kPa)","U = 1 - mean(p) / q0","Settlement (mm)")):
        ax.set(title=title,xlabel="Actual Tv = Cv (t - tD) / H squared",ylabel=ylabel,xlim=(0,2));ax.grid(alpha=.22)
        ax.set_xticks(np.arange(0,2.01,.5))
    axes[0,0].set_ylim(0,10.5);axes[0,1].set(xlim=(1,2),ylim=(0,.75),xticks=np.arange(1,2.01,.25))
    axes[1,0].set_ylim(0,1.03);axes[1,1].set_ylim(0,4)
    axes[0,0].legend(fontsize=9);axes[1,1].legend(fontsize=9)
    fig.suptitle("Accepted 2Tv runs: pore-pressure dissipation and material settlement")
    finish(fig,"_history","Publication target spacing DeltaTv=.01; nearest real native frames, no SPH interpolation. k=1e-5 is not included.")
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for r,color,style in zip(runs,colors,styles):
        h=r["history"];post=h[h.time_s>=.1-1e-7];label=f"k={r['model']['k']:g} m/s"
        for ax,key in zip(axes.flat,("max_layer_total_error_pa","top_gap_pa","Q_pa","bottom_theory_error_mm")):
            v=post if key!="bottom_theory_error_mm" else h
            ax.plot(v.actual_tv,v[key],color=color,ls=style,label=label)
    for ax,ylabel in zip(axes.flat,("Max layer total-stress error (Pa)","Top adjacent-layer stress gap (Pa)","Q: RMS second layer difference (Pa)","Bottom material theory bias (mm)")):
        ax.set(xlabel="Actual Tv",ylabel=ylabel,xlim=(0,2),xticks=np.arange(0,2.01,.5));ax.grid(alpha=.22)
    for ax in axes[0]:ax.axhline(100,ls=":",color=".25");ax.set_ylim(0,105)
    axes[0,0].legend(fontsize=9);fig.suptitle("Residual stress shape and bottom-material bias (not eliminated)")
    finish(fig,"_diagnostics","Stress/Q panels start at physical t >= .1 s. Publication samples are not the full-history safety audit.")
    palette=plt.cm.viridis(np.linspace(.05,.85,len(TARGETS)))
    for r in runs:
        fig,axes=plt.subplots(1,2,figsize=(12,6));wide={"z0_H":r["z0"]/r["model"]["H"]};theory_rows=[]
        for color,target in zip(palette,TARGETS):
            p,truth,tv,t=r["states"][target];z=np.linspace(0,1,201)
            analytic=pressure_theory(z*r["model"]["H"],tv,r["model"])/r["model"]["q0"]
            for ax in ([axes[0],axes[1]] if target>=1 else [axes[0]]):
                ax.plot(analytic,z,color=color,lw=1.3,label=f"Tv ~ {target:g}")
                ax.plot(p/r["model"]["q0"],r["z0"]/r["model"]["H"],"o",color=color,mfc="none",ms=3)
            wide[f"p_num_pa_Tv{target:g}"]=p;wide[f"p_classical_pa_Tv{target:g}"]=truth
            theory_rows.extend(dict(target_tv=target,actual_tv=tv,time_s=t,z_H=float(x),classical_p_over_q0=float(y)) for x,y in zip(z,analytic))
        for ax in axes:
            ax.set(xlabel="Pore pressure / q0",ylabel="Initial material height z0/H",ylim=(0,1));ax.grid(alpha=.22)
        axes[0].set(xlim=(-.01,1.05),title="Full pressure scale");axes[1].set(xlim=(-.001,.12),title="Late-time horizontal-scale zoom")
        handles,labels=axes[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc="upper center",bbox_to_anchor=(.5,.93),ncol=5,fontsize=9,frameon=False)
        axes[1].legend(fontsize=9)
        fig.suptitle(f"k={r['model']['k']:g} m/s: 2Tv native pressure profiles")
        finish(fig,"_profiles_"+r["key"],"Solid lines: classical theory at actual saved Tv; hollow circles: native SPH. Finite Kw / ramp / moving particles differ from ideal theory.",top=.83)
        csv("_profiles_wide_"+r["key"],wide);csv("_theory_curves_"+r["key"],theory_rows)
        evidence+=r["evidence"]
    check=dict(generated_utc=pd.Timestamp.now(tz="UTC").isoformat(),publication_verified=True,visual_review_pending=True,
        solver_rerun=False,production_or_inputs_modified=False,history_target_delta_tv=.01,
        history_selection="201 nearest real saved frames per k, Tv=0 chooses tD rather than unloaded t=0; no SPH interpolation",
        accepted_source_review=bound(accepted_path),sources_verified_by_hash=True,native_profile_checks_per_case=10,
        cases=[r["summary"] for r in runs],cadence=[r["cadence"] for r in runs],outputs=[bound(p) for p in outputs],
        evidence=list({b["path"]:b for b in evidence}.values()),previous_layout_snapshot=previous,
        limitations=["No k1e-5 full-cycle result is present.","Elastic fixed-plane fresh HG scope, no full-cycle half-step or exact-HG-restart claim.",
            "Original dense native histories and original frozen figures/checks remain unchanged.","Formal XML TimeOut and the running k5 input have not been changed by this publication."])
    with check_path.open("w" if args.repair_layout else "x",encoding="utf8") as stream:json.dump(check,stream,indent=2,allow_nan=False)
    print(json.dumps({k:check[k] for k in ("publication_verified","solver_rerun","cases","cadence")},indent=2))


if __name__=="__main__":main()
