"""Publish three completed equal-dp 2Tv datasets without overwriting frozen releases."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from refresh_full_validation_q0 import degree, bound, TARGETS, READER
from release_case import CASE, model, native, inspect, settlement, pressure_theory

FIG = CASE/"figures"
TESTS = CASE/"tests"
PREFIX = "full_validation_three"


def verify(items):
    for item in items:
        assert bound(item["path"])["sha256"].lower() == item["sha256"].lower(), item["path"]


def retained(key):
    """Read old immutable model schemas; verify newly exposed geometry from XML/PART."""
    receipt=FIG/("full_validation_release_"+key+"_GPU.check.json")
    old=json.loads(receipt.read_text(encoding="utf8"))
    assert old["passed"] and old["numerical_safety_passed"]
    hashes={str(Path(x["path"]).resolve()):x for x in old["evidence"]}
    evidence=[bound(receipt)]
    def checked(path):
        item=hashes[str(Path(path).resolve())];verify([item]);evidence.append(bound(path))
    folder=Path(old["output"])
    xml=next(Path(p) for p in hashes if Path(p).parent==folder and Path(p).suffix==".xml")
    source=FIG/("full_validation_release_"+key+"_GPU_history.csv")
    for path in (xml,source,READER,folder/"data/Part_0000.bi4"):checked(path)
    m=model(xml)
    assert all(m[k]==v for k,v in old["model"].items())
    assert m["dp"]==.01 and m["width"]==.1 and m["nx"]==10 and m["nz"]==100
    h=pd.read_csv(source,float_precision="round_trip");assert len(h)==old["frames"]
    initial=native(READER,folder,0)
    z0=initial.z.to_numpy().reshape(10,100).mean(axis=0)
    selected=[]
    for target in np.arange(1,401)/200:
        i=int(abs(h.time_s-(m["tD"]+target/m["cv"])).idxmin());row=h.iloc[i].to_dict()
        row.update(case=key,k_m_s=m["k"],target_tv=float(target),target_time_s=m["tD"]+target/m["cv"],native_part=i,native_file=f"Part_{i:04d}.bi4")
        row["actual_tv"]=row.pop("tv");row["u_num"]=1-row["mean_pressure_pa"]/m["q0"];row["u_theory"]=degree(row["actual_tv"])
        row["mean_excess_kpa"]=row["mean_pressure_pa"]/1000;row["mean_theory_pa"]=m["q0"]*(1-row["u_theory"])
        row["top_theory_error_mm"]=row["top_settlement_mm"]-row["classical_top_mm"];row["bottom_theory_error_mm"]=row["bottom_settlement_mm"]-row["classical_bottom_mm"]
        selected.append(row)
    profiles=[];targets=[];states={}
    for target in TARGETS:
        i=int(abs(h.time_s-(m["tD"]+target/m["cv"])).idxmin())
        checked(folder/"data"/f"Part_{i:04d}.bi4")
        a=native(READER,folder,i);value=inspect(a,initial,m)
        for field in ("time_s","mean_pressure_pa","top_settlement_mm","bottom_settlement_mm","max_layer_total_error_pa","top_gap_pa","Q_pa"):
            assert abs(value[field]-h.iloc[i][field])<1e-7,(key,i,field)
        p=a.pressure.to_numpy().reshape(10,100).mean(axis=0);truth=pressure_theory(z0,value["tv"],m)
        states[target]=(p,truth,value["tv"],value["time_s"])
        profiles.extend(dict(case=key,k_m_s=m["k"],target_tv=target,actual_tv=value["tv"],time_s=value["time_s"],native_part=i,layer=j,z0_H=float(z0[j]),pressure_pa=float(p[j]),classical_pa=float(truth[j])) for j in range(100))
        targets.append(dict(case=key,k_m_s=m["k"],target_tv=target,actual_tv=value["tv"],time_s=value["time_s"],native_part=i,profile_rmse_pa=float(np.sqrt(np.mean((p-truth)**2)))))
    history=pd.DataFrame(selected);f=history.iloc[-1]
    summary=dict(case=key,k_m_s=m["k"],native_frames=len(h),published_history_rows=400,actual_time_s=float(f.time_s),actual_tv=float(f.actual_tv),mean_pressure_pa=float(f.mean_pressure_pa),
        top_settlement_mm=float(f.top_settlement_mm),classical_top_mm=float(f.classical_top_mm),top_settlement_error_pct=float(100*(f.top_settlement_mm/f.classical_top_mm-1)),
        final_profile_rmse_pa=targets[-1]["profile_rmse_pa"],Q_pa=float(f.Q_pa),max_abs_target_tv_offset=float(abs(history.actual_tv-history.target_tv).max()))
    return dict(key=key,model=m,history=history,profiles=pd.DataFrame(profiles),targets=targets,states=states,z0=z0,summary=summary,evidence=evidence,native_interval_s=float(h.time_s.diff().median()))


def third():
    receipt = TESTS/"logs/k5em5_hg05_full_cpu_r1.review.json"
    accepted = json.loads(receipt.read_text(encoding="utf8"))
    assert accepted["passed"] and accepted["visual_inspected"] and accepted["accepted_in_user_provisional_1d_scope"]
    verify(accepted["evidence"])
    stem = TESTS/"figures/k5em5_hg05_full_cpu_r1_review"
    h = pd.read_csv(str(stem)+"_history.csv",float_precision="round_trip")
    p = pd.read_csv(str(stem)+"_profiles.csv",float_precision="round_trip")
    m = accepted["model"]
    selected=[]
    for target in np.arange(1,401)/200:
        i=int(abs(h.tv-target).idxmin())
        row=h.iloc[i].to_dict()
        row.update(case="k5em5",k_m_s=m["k"],target_tv=float(target),target_time_s=m["tD"]+target*m["H"]**2/m["cv"],native_file=f"Part_{i:04d}.bi4")
        row["actual_tv"]=row.pop("tv")
        row["u_num"]=1-row["mean_pressure_pa"]/m["q0"]
        row["u_theory"]=degree(row["actual_tv"])
        row["mean_excess_kpa"]=row["mean_pressure_pa"]/1000
        row["mean_theory_pa"]=m["q0"]*(1-row["u_theory"])
        selected.append(row)
    history=pd.DataFrame(selected)
    assert history.native_part.is_unique and len(history)==400 and history.actual_tv.gt(0).all()
    states={}
    targets=[]
    for t in TARGETS:
        f=p[p.target_tv.eq(t)].sort_values("layer")
        assert len(f)==100
        states[t]=(f.pressure_pa.to_numpy(),f.classical_pa.to_numpy(),float(f.actual_tv.iloc[0]),float(f.time_s.iloc[0]))
        targets.append(dict(case="k5em5",k_m_s=m["k"],target_tv=t,actual_tv=float(f.actual_tv.iloc[0]),time_s=float(f.time_s.iloc[0]),native_part=int(f.native_part.iloc[0]),profile_rmse_pa=float(np.sqrt(np.mean((f.pressure_pa-f.classical_pa)**2)))))
    f=history.iloc[-1]
    summary=dict(case="k5em5",k_m_s=m["k"],native_frames=len(h),published_history_rows=400,actual_time_s=float(f.time_s),actual_tv=float(f.actual_tv),
        mean_pressure_pa=float(f.mean_pressure_pa),top_settlement_mm=float(f.top_settlement_mm),classical_top_mm=float(f.classical_top_mm),
        top_settlement_error_pct=accepted["final_top_settlement_error_pct"],final_profile_rmse_pa=targets[-1]["profile_rmse_pa"],Q_pa=float(f.Q_pa),
        bottom_theory_error_mm=float(f.bottom_theory_error_mm),max_abs_target_tv_offset=float(abs(history.actual_tv-history.target_tv).max()))
    return dict(key="k5em5",model=m,history=history,profiles=p,targets=targets,states=states,z0=p[p.target_tv.eq(TARGETS[0])].z0_H.to_numpy()*m["H"],
                summary=summary,evidence=[bound(receipt)]+[bound(Path(str(stem)+s+".csv")) for s in ("_history","_profiles","_targets")],native_interval_s=float(h.time_s.diff().median()))


def main():
    check_path=FIG/(PREFIX+".check.json")
    if check_path.exists():
        prior=json.loads(check_path.read_text(encoding="utf8"));verify(prior["outputs"]+prior["evidence"])
        print("Existing verified three-group publication preserved.");return
    accepted_path=TESTS/"logs/formal_release_k34_r1.review.json"
    assert json.loads(accepted_path.read_text(encoding="utf8"))["passed"]
    runs=[retained("k1em3"),retained("k1em4"),third()]
    evidence=[bound(p) for p in (Path(__file__),Path(__file__).with_name("refresh_full_validation_q0.py"),Path(__file__).with_name("release_case.py"),
        Path(__file__).with_name("compare_precision_q0.py"),accepted_path)]
    outputs=[]
    metadata=[]
    for run,backend,xi in zip(runs,("GPU","GPU","CPU8"),(.1,.1,.05)):
        assert run["model"]["dp"]==.01 and run["model"]["width"]==.1
        run["history"]=run["history"][run["history"].target_tv.gt(0)].copy()
        assert len(run["history"])==400 and run["history"].native_part.is_unique
        for table in (run["history"],run["profiles"]):
            table["backend"]=backend;table["hg_xi"]=xi
        run.update(backend=backend,xi=xi)
        run["summary"].update(backend=backend,hg_xi=xi,published_history_rows=400,bottom_theory_error_mm=float(run["history"].bottom_theory_error_mm.iloc[-1]))
        suffix="_release_CPU_uniform_out" if backend=="CPU8" else "_release_GPU_out"
        folder=CASE/("CaseTerzaghiConsolidation_q0_PR_full_"+run["key"]+suffix)
        if run["key"] == "k1em4":
            # This accepted dataset was explicitly adopted from a production-step companion.
            provenance_path=folder/"release_provenance.json"
            provenance=json.loads(provenance_path.read_text(encoding="utf8"))
            assert provenance["accepted_k1em4_adoption"] and provenance["formal_program_short_equivalence_passed"]
            verify([dict(path=provenance["source_receipt"],sha256=provenance["source_receipt_sha256"])])
            done=folder/"complete.json"
            verify([next(x for x in provenance["files"] if Path(x["path"])==done)])
            completed=json.loads(done.read_text(encoding="utf8"))
            assert completed["completed"] and completed["production_step_used"]
            runtime=pd.Series(dict(Steps=completed["steps"],TSimul=completed["elapsed_seconds"]))
            timing_scope="Adopted production-step companion loop; not a new formal BAT run"
            evidence += [bound(provenance_path),bound(done),bound(provenance["source_receipt"])]
        else:
            runtime=pd.read_csv(folder/"Run.csv",sep=";").iloc[0]
            timing_scope="Native formal solver TSimul"
            evidence.append(bound(folder/"Run.csv"))
        run["summary"].update(solver_steps=int(runtime.Steps),loop_seconds=float(runtime.TSimul),loop_hours=float(runtime.TSimul)/3600)
        metadata.append(dict(case=run["key"],k_m_s=run["model"]["k"],dp_m=.01,width_m=.1,backend=backend,hg_xi=xi,solver_dt_s=run["model"]["dt"],
            actual_native_interval_s=run["native_interval_s"],published_selected_interval_s=float(run["history"].time_s.diff().median()),published_target_delta_tv=.005,
            formal_timeout_s=.005/run["model"]["cv"],initial_loaded_Tv0_in_comparison=False,solver_steps=int(runtime.Steps),recorded_loop_hours=float(runtime.TSimul)/3600,timing_scope=timing_scope))
        evidence+=run["evidence"]
    def csv(suffix,data):
        path=FIG/(PREFIX+suffix+".csv")
        pd.DataFrame(data).to_csv(path,index=False,mode="x");outputs.append(path)
    csv("_history_data",pd.concat([r["history"] for r in runs],ignore_index=True))
    csv("_profiles_data",pd.concat([r["profiles"] for r in runs],ignore_index=True))
    csv("_targets",[v for r in runs for v in r["targets"]])
    csv("_summary",[r["summary"] for r in runs]);csv("_metadata",metadata)
    plt.rcParams.update({"font.size":10,"axes.titlesize":11,"legend.fontsize":9,"axes.spines.top":False,"axes.spines.right":False})
    colors=("#256da3","#c47725","#667b32");styles=("-","--","-.")
    note="Equal dp=.01 m and width=.1 m; HG xi=.1 / .1 / .05. Actual saved Tv, no SPH interpolation. Not a permeability-only controlled experiment."
    def finish(fig,suffix,extra="",top=.94):
        fig.text(.5,.012,note+("\n"+extra if extra else ""),ha="center",fontsize=8)
        fig.tight_layout(rect=(0,.06,1,top))
        path=FIG/(PREFIX+suffix+".png")
        with path.open("xb") as stream:fig.savefig(stream,dpi=180)
        plt.close(fig);outputs.append(path)
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for run,color,style in zip(runs,colors,styles):
        h=run["history"];label=f"k={run['model']['k']:g}, {run['backend']}, xi={run['xi']:g}"
        axes[0,0].plot(h.actual_tv,h.mean_excess_kpa,color=color,ls=style,label=label)
        late=h[h.actual_tv>=.999]
        axes[0,1].plot(late.actual_tv,late.mean_excess_kpa,color=color,ls=style)
        axes[1,0].plot(h.actual_tv,h.top_settlement_mm,color=color,ls=style)
        axes[1,1].plot(h.actual_tv,h.top_theory_error_mm,color=color,ls=style)
    grid=np.linspace(0,2,1001);m=runs[0]["model"];u=np.array([degree(v) for v in grid])
    axes[0,0].plot(grid,m["q0"]*(1-u)/1000,":",color=".2",label="Classical reference")
    axes[0,1].plot(grid[grid>=1],m["q0"]*(1-u[grid>=1])/1000,":",color=".2")
    axes[1,0].plot(grid,[0 if v==0 else settlement(runs[0]["z0"][-1],m["tD"]+v/m["cv"],m) for v in grid],":",color=".2")
    axes[1,1].axhline(0,color=".2",ls=":")
    for ax,title,ylabel in zip(axes.flat,("Mean excess pore pressure","Late pore-pressure dissipation","Top native material settlement","Top material minus classical reference"),("Pressure (kPa)","Pressure (kPa)","Settlement (mm)","Difference (mm)")):
        ax.set(title=title,xlabel="Actual Tv",ylabel=ylabel,xlim=(0,2));ax.grid(alpha=.22)
    axes[0,0].legend();axes[0,0].set_ylim(0,10.5);axes[0,1].set(xlim=(1,2),ylim=(0,.75))
    axes[1,0].set_ylim(0,4)
    fig.suptitle("Three completed 2Tv runs: pressure and material settlement")
    finish(fig,"_history","History targets=.005,.010,...,2; unloaded t=0 is not plotted as initial excess pressure.")
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for run,color,style in zip(runs,colors,styles):
        h=run["history"];post=h[h.time_s>=.1-1e-7]
        for ax,key in zip(axes.flat,("max_layer_total_error_pa","top_gap_pa","Q_pa","bottom_theory_error_mm")):
            ax.plot(post.actual_tv,post[key],color=color,ls=style,label=f"k={run['model']['k']:g}, xi={run['xi']:g}")
    for ax,title,ylabel in zip(axes.flat,("Layer total-stress residual","Top adjacent-layer stress gap","Stress second-difference RMS Q","Bottom material minus classical reference"),("Residual (Pa)","Gap (Pa)","Q (Pa)","Difference (mm)")):
        ax.set(title=title,xlabel="Actual Tv",ylabel=ylabel,xlim=(0,2));ax.grid(alpha=.22)
    for ax in axes[0]:ax.axhline(100,color=".3",ls=":");ax.set_ylim(0,105)
    axes[0,0].legend()
    fig.suptitle("Residual stress and boundary bias remain explicitly visible")
    finish(fig,"_diagnostics","Only physical t>=.1 s shown; publication samples do not replace full native safety checks.")
    palette=plt.cm.viridis(np.linspace(.05,.85,len(TARGETS)))
    for run in runs:
        fig,axes=plt.subplots(1,2,figsize=(12,6));wide={"z0_H":run["z0"]/run["model"]["H"]}
        for color,target in zip(palette,TARGETS):
            p,truth,tv,t=run["states"][target];z=np.linspace(0,1,201)
            smooth=pressure_theory(z*run["model"]["H"],tv,run["model"])/10000
            for ax in ([axes[0],axes[1]] if target>=1 else [axes[0]]):
                ax.plot(smooth,z,color=color,label=f"Tv ~ {target:g}")
                ax.plot(p/10000,run["z0"],"o",color=color,mfc="none",ms=3)
            wide[f"p_num_pa_Tv{target:g}"]=p;wide[f"p_classical_pa_Tv{target:g}"]=truth
        for ax in axes:ax.set(xlabel="Pore pressure / q0",ylabel="Initial material z0/H",ylim=(0,1));ax.grid(alpha=.22)
        axes[0].set(xlim=(-.01,1.05),title="All target Tv profiles");axes[1].set(xlim=(-.001,.12),title="Late horizontal-scale zoom")
        handles,labels=axes[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc="upper center",bbox_to_anchor=(.5,.93),ncol=5,frameon=False)
        axes[1].legend()
        fig.suptitle(f"k={run['model']['k']:g} m/s, xi={run['xi']:g}: native pressure profiles")
        finish(fig,"_profiles_"+run["key"],"Lines: theory at actual saved Tv. Hollow circles: native particle-layer means.",top=.82)
        csv("_profiles_wide_"+run["key"],wide)
    fig,axes=plt.subplots(3,3,figsize=(14,11),sharey=True)
    for col,target in enumerate((1.,1.5,2.)):
        upper=0
        for row,(run,color) in enumerate(zip(runs,colors)):
            ax=axes[row,col];p,truth,tv,t=run["states"][target];z=np.linspace(0,1,201)
            smooth=pressure_theory(z,tv,run["model"])
            ax.plot(smooth,z,color=".2",label="Classical theory")
            ax.plot(p,run["z0"],"o",color=color,mfc="none",ms=3,label="Native SPH")
            ax.set(title=f"k={run['model']['k']:g}, xi={run['xi']:g} | Tv~{target:g}",xlabel="Pressure (Pa)",ylim=(0,1))
            if col==0:ax.set_ylabel("Initial material z0/H")
            ax.text(.97,.96,f"Actual Tv={tv:.6f}\nt={t:.6f} s\nRMSE={np.sqrt(np.mean((p-truth)**2)):.3f} Pa",transform=ax.transAxes,ha="right",va="top",fontsize=9)
            ax.grid(alpha=.22);upper=max(upper,float(max(p.max(),smooth.max())))
        for ax in axes[:,col]:ax.set_xlim(0,upper*1.08)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc="upper center",bbox_to_anchor=(.5,.95),ncol=2,frameon=False)
    fig.suptitle("Late pressure profiles: one Tv per column, equal scales down each column")
    finish(fig,"_late_profiles",top=.91)
    result=dict(publication_verified=True,visual_review_pending=True,solver_rerun=False,generated_utc=pd.Timestamp.now(tz="UTC").isoformat(),
        history_target_delta_tv=.005,history_rows_each=400,history_selection="Targets .005 through2; nearest unique native post-drain frames. No unloaded0 or SPH interpolation.",
        cases=[r["summary"] for r in runs],metadata=metadata,outputs=[bound(p) for p in outputs],
        evidence=list({x["path"]:x for x in evidence}.values()),limitations=[note,"Recorded loop times differ in k/steps/backend/cadence; not a controlled CPU/GPU benchmark.",
            "1D elastic fixed-plane small-rotation fresh HG scope; no full-cycle half-step, plasticity, complex-boundary or exact-HG-restart claim.",
            "FiniteKw, ramp and moving particles differ from classical ideal reference. Q/bottom bias are not zero."])
    with check_path.open("x",encoding="utf8") as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps({k:result[k] for k in ("publication_verified","solver_rerun","cases","metadata")},indent=2),flush=True)


if __name__ == "__main__":main()
