"""Review the sealed C04 3D fixed-reference component failure without loading the GPU library."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TESTS=Path(__file__).resolve().parents[1]
TAG="cryer_pair_open_failure_r1"


def require(value,message):
    if not value:raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main(output=None):
    r1=TESTS/"outputs/cryer_pair_open_r1";r2=TESTS/"outputs/cryer_pair_open_r2"
    build=TESTS/"outputs/cryer_pair_window_build_r2"
    pre=read_json(r1/"interrupted.json");fault=read_json(r2/"interrupted.json")
    require(pre=={"reason":"Noncontiguous buffer for setGeometry","last_read_step":None} and
            not (r1/"history.csv").exists(),"Unexpected first-attempt history")
    require(fault=={"reason":"First invalid update 38, phase 1 (1 predictor, 2 corrector, 3/4/5 pressure), slot 35295, native ID 35303",
                    "last_read_step":32} and not (r2/"completed.json").exists(),"Unexpected physical-component status")
    dll=read_json(build/"build.json");fixture=read_json(r2/"fixture.json")
    require(dll["passed"] and dll["exit"]==0 and "-arch=sm_86" in dll["options"] and
            Path(dll["source"]).name=="cryer_pair_window.cu","Unbound component build")
    require(set(fixture)=={"viscosity","pressure","total_with_damping","pressure_round_closed_Pa","pressure_round_open_Pa"}
            and max(fixture.values())<1e-8,"Fixture changed")
    probe=read_json(build/"abi_probe.json")
    require(probe["synthetic"] and not probe["physical_case"] and probe["restored_next_update_all_six_identical"],
            "Synthetic ABI evidence changed")
    with np.load(TESTS/"outputs/cryer_tet_reference_r1.npz") as geom:
        ids=geom["native_ids"];shells=geom["material_shell"]
        require(np.array_equal(ids,np.arange(8,37181)) and ids[35295]==35303,"Actual material ownership")
        slot_shell=int(shells[35295])
        counts=np.bincount(shells)[1:]
    h=pd.read_csv(r2/"history.csv",float_precision="round_trip")
    b=pd.read_csv(r2/"shells.csv",float_precision="round_trip")
    dt=2.**-19
    require(h.step.tolist()==[0,1,2,4,8,16,32] and len(b)==140 and
            np.array_equal(h.time_s,h.step*dt) and np.array_equal(b.time_s,b.step*dt) and
            np.isfinite(h.to_numpy()).all() and np.isfinite(b.to_numpy()).all(),"Clock or finite history")
    require(np.array_equal(h.q_at_source_Pa,10000.*np.maximum(h.step-1,0)/2048),"Actual source ramp")
    results=[];shell_rows=[]
    for i in h.itertuples():
        s=b[b.step==i.step].sort_values("material_shell");w=s["count"].to_numpy()/len(ids)
        require(np.array_equal(s.material_shell,np.arange(1,21)) and np.array_equal(s["count"],counts),
                "Native layer populations")
        avg=float(w@s.p_mean_Pa);stats=s.p_std_Pa.to_numpy()
        require(abs(avg-i.mean_Pa)<1e-7 and abs(s.p_mean_Pa.iloc[0]-i.center_Pa)<1e-7 and
                s.speed_max_m_s.max()==i.max_speed_m_s,"Material/global aggregation")
        intra=float(w@(stats**2));inter=float(w@((s.p_mean_Pa-avg)**2))
        total=intra+inter;variance_direct=i.rms_p_to_10000_Pa**2-(avg-10000)**2
        require(abs(total-variance_direct)<max(5e-5,1e-10*total),"ANOVA variance vs stored RMS")
        shell_rows.extend(dict(step=int(i.step),time_us=i.time_s*1e6,shell=int(j.material_shell),
                native_count=int(j.count),pressure_mean_Pa=j.p_mean_Pa,pressure_within_std_Pa=j.p_std_Pa,
                speed_max_m_s=j.speed_max_m_s) for j in s.itertuples())
        results.append(dict(step=i.step,time_us=i.time_s*1e6,load_Pa=i.q_at_source_Pa,
             min_Pa=i.min_Pa,max_Pa=i.max_Pa,center_Pa=i.center_Pa,mean_Pa=avg,
             global_std_Pa=np.sqrt(total),within_shell_std_rms_Pa=np.sqrt(intra),
             between_shell_mean_std_Pa=np.sqrt(inter),within_shell_variance_share=intra/total if total else None,
             largest_scatter_shell=int(s.iloc[np.argmax(stats)].material_shell) if total else None,
             largest_shell_std_Pa=float(max(stats)),max_speed_m_s=i.max_speed_m_s,rms_speed_m_s=i.rms_speed_m_s,
             face_traction_rms_Pa=i.face_traction_rms_Pa,kinetic_J=i.kinetic_J,Jmin=i.min_J,Jmax=i.max_J))
    seq=pd.DataFrame(results)
    if output is not None:
        output.mkdir(parents=True,exist_ok=True)
    prefix=output or TESTS/"figures"
    dest=prefix/(TAG+"_steps.csv");profiles=prefix/(TAG+"_shells.csv");fig=prefix/(TAG+".png")
    check=(output or TESTS/"logs")/(TAG+".check.json")
    require(not any(p.exists() for p in [dest,profiles,fig,check]),"Use a fresh review directory")
    seq.to_csv(dest,index=False);sf=pd.DataFrame(shell_rows);sf.to_csv(profiles,index=False)
    f,axes=plt.subplots(1,2,figsize=(10.4,4.1),layout="constrained")
    active=seq[seq.step>=2]
    ax=axes[0]
    for col,lab,m in [("max_Pa","Maximum pressure","o"),("min_Pa","Absolute minimum pressure","v"),
                       ("load_Pa","Applied compression","s")]:
        ax.semilogy(active.step,abs(active[col]),marker=m,label=lab)
    ax.set(xlabel="Last completed sampled update",ylabel="Magnitude (Pa)",title="Closed load ramp")
    ax=axes[1]
    for step,marker in [(8,"s"),(16,"v"),(32,"o")]:
        s=sf[sf.step==step]
        ax.semilogy(s.shell,s.pressure_within_std_Pa,marker=marker,ms=3,label=f"Step {step}")
    ax.set(xlabel="Initial material shell (1 = center)",ylabel="Within-shell pressure SD (Pa)",title="Angular scatter by material shell",
           xticks=[1,5,10,15,20])
    for ax in axes:ax.grid(alpha=.22);ax.legend(fontsize=8)
    f.savefig(fig,dpi=160);plt.close(f)
    paths=[r1/"interrupted.json",r2/"interrupted.json",r2/"fixture.json",r2/"history.csv",r2/"shells.csv",
           build/"build.json",build/"abi_probe.json",build/"cryer_pair_window.dll",
           TESTS/"support/cryer_pair_window.py",TESTS/"support/cryer_pair_window.cu"]
    bindings=[dict(path=str(p.relative_to(TESTS)),size_bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns) for p in paths]
    result={"audit_pass":True,"candidate_pass":False,"first_attempt":pre,"actual_fault":fault,"fault_slot_shell":slot_shell,
        "retained_topology_material_ids":len(ids),"saved_step_count":len(h),"rows_by_shell":len(b),
        "last_read_time_s":float(h.time_s.iloc[-1]),"last_complete_source_load_Pa":float(h.q_at_source_Pa.iloc[-1]),
        "reported_fault_phase":"Mechanical predictor, before corrector and three endpoint pressure rounds of update 38",
        "predicate_components":"OR of velocity, position/radius, J/porosity and finite stress; individual bit unavailable",
        "first_fault_material_is_not_unique_worst":True,"fault_slot_saved_state_unavailable":True,
        "abi_probe_synthetic":True,"small_cpu_gpu_fixtures":fixture,"pressure_closed_all_saved":True,
        "measured_variance_identity":"population variance = weighted average of within-shell variances + variance of shell means",
        "last_summaries":results[-2:],"updated_formal_source":False,"GPU_calls_made_by_review":0,"bindings":bindings}
    check.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps({k:result[k] for k in ("actual_fault","fault_slot_shell","last_summaries")},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,help="New directory for an independent offline reproduction")
    main(parser.parse_args().out)
