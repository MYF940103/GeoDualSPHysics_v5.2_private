"""Review dense short output without changing the original half/safety limits."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import k5_cell_sequence as cell
from formal_release_sequence import TESTS, utc
from mdbc_gpu_vector_run import read,bound,verify


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--family",choices=("8","5"),required=True);args=p.parse_args()
    tag="k5_dense"+args.family+"_r1";out=TESTS/"logs"/(tag+".review.json");assert not out.exists()
    state_path=TESTS/"logs"/(tag+".status.json");s=read(state_path)
    assert len(s["runs"])==2 and all(r["completed"] and r["exit_code"]==0 and r["owned_process_exited"] for r in s["runs"])
    evidence=s["inputs"]+[bound(state_path),bound(__file__)]
    for r in s["runs"]:evidence+=r["outputs"]
    unique={p["path"]:p for p in evidence};verify(unique.values())
    data,histories,summaries=[],[],[]
    for r in s["runs"]:
        folder=TESTS/"outputs"/r["label"];a=[cell.probe.native(folder,i) for i in range(151)]
        assert r["frames"]==151
        rows=[cell.metrics(x,a[0]) for x in a];assert rows[-1]==r["final"]
        assert all(abs(m["time_s"]-i*.001)<1e-8 for i,m in enumerate(rows))
        n=round(.15/r["dt_s"]);assert rows[-1]["step"]==n and np.array_equal(a[0].id,np.arange(32,2592))
        h=pd.DataFrame(rows);post=h[h.stress_guard_applicable]
        run=pd.read_csv(folder/"Run.csv",sep=";").iloc[0]
        assert run.Np==2592 and run.Nfixed==32 and run.PartsOut==0 and run.Steps==n
        assert "Finished execution (code=0)." in (folder/"Run.out").read_text(encoding="utf-8-sig",errors="replace")
        summaries.append(dict(label=r["label"],loop_seconds=float(run.TSimul),final=rows[-1],
            post_point1s_max_stress_pa=float(post.max_layer_total_error_pa.max()),post_point1s_max_top_gap_pa=float(post.top_gap_pa.max()),
            max_equivalent_force_error_N_m=float(abs(post.equivalent_full_width_resultant_N_m+1000).max())))
        csv=TESTS/"figures"/(r["label"]+"_review.csv");h.to_csv(csv,index=False,mode="x");evidence.append(bound(csv))
        data.append(a);histories.append(h)
    top=data[0][0].z>.996;rows=[]
    for a,b in zip(*data):
        assert np.array_equal(a.id,b.id) and b.step.iloc[0]==2*a.step.iloc[0] and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-8
        rows.append(dict(time_s=float(a.time_s.iloc[0]),pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))),
            top_settlement_difference_mm=abs(float((a.z[top]-b.z[top]).mean()*1000))))
    h=pd.DataFrame(rows);passed=bool((h.pressure_rms_pa<=5).all() and (h.top_settlement_difference_mm<=.005).all())
    assert passed==s["half"]["passed"]
    assert all(x["native_0_ulp"] and x["samples"]==31 for x in s["prefixes"])
    # Recheck all 31 matched old samples: denser SaveData must not change physics.
    source=read(TESTS/"logs"/(s["config"]["reference"]+".status.json"))
    for suffix,a in zip(("c","h"),data):
        reference=TESTS/"outputs"/(s["config"]["reference"]+"_015"+suffix)
        recorded=next(r for r in source["runs"] if r["label"]==reference.name)
        verify(recorded["outputs"]);evidence+=recorded["outputs"]
        for i in range(31):
            old=cell.probe.native(reference,i);new=a[i*5]
            assert np.array_equal(old.id,new.id) and old[cell.FIELDS].to_numpy(dtype="<f8").tobytes()==new[cell.FIELDS].to_numpy(dtype="<f8").tobytes()
    csv=TESTS/"figures"/(tag+"_all_half.csv");h.to_csv(csv,index=False,mode="x");evidence.append(bound(csv))
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(2,2,figsize=(11,8))
    axes[0,0].plot(h.time_s,h.pressure_rms_pa,color="#256da3",lw=1.4,label="1-ms native samples")
    axes[0,0].plot(h.time_s.iloc[::5],h.pressure_rms_pa.iloc[::5],"o",color="#c47725",ms=4,fillstyle="none",label="Old 5-ms sample locations")
    axes[0,0].axhline(5,color=".25",ls=":",label="Original 5-Pa limit")
    peak=h.loc[h.pressure_rms_pa.idxmax()];axes[0,0].set(xlabel="Actual physical time (s)",ylabel="Coarse / half pressure RMS difference (Pa)",title=f"Peak {peak.pressure_rms_pa:.6f} Pa at {peak.time_s:.6g} s");axes[0,0].legend(fontsize=8)
    axes[0,1].plot(h.time_s,h.top_settlement_difference_mm,color="#256da3");axes[0,1].set(xlabel="Actual physical time (s)",ylabel="Top material settlement difference (mm)",title="Zoomed difference; original limit .005 mm")
    labels=("Coarse dt="+s["config"]["steps"][0],"Half dt="+s["config"]["steps"][1])
    for hist,color,style,label in zip(histories,("#256da3","#c47725"),("-","--"),labels):
        post=hist[hist.stress_guard_applicable]
        axes[1,0].plot(post.time_s,post.max_layer_total_error_pa,color=color,ls=style,label=label)
        axes[1,1].plot(hist.time_s,hist.Q_pa,color=color,ls=style,label=label)
    axes[1,0].axhline(100,color=".25",ls=":");axes[1,0].set(xlabel="Actual time (s); guard from .1 s",ylabel="Max layer total-stress error (Pa)",ylim=(0,105));axes[1,0].legend(fontsize=8)
    axes[1,1].set(xlabel="Actual physical time (s)",ylabel="Q: RMS second layer difference (Pa)")
    for ax in axes.flat:ax.grid(alpha=.2)
    fig.suptitle("k=1e-5 dense short preflight: "+("PASS" if passed else "REJECTED")+" under unchanged limits")
    fig.tight_layout(rect=(0,0,1,.95));png=TESTS/"figures"/(tag+"_review.png")
    with png.open("xb") as stream:fig.savefig(stream,dpi=160)
    plt.close(fig);evidence.append(bound(png))
    bad=h[(h.pressure_rms_pa>5)|(h.top_settlement_difference_mm>.005)]
    result=dict(audit_passed=True,reviewed_utc=utc(),family=args.family,dense_pair_passed=passed,samples=151,
        max_pressure_rms_pa=float(h.pressure_rms_pa.max()),peak_pressure_time_s=float(peak.time_s),
        max_top_settlement_difference_mm=float(h.top_settlement_difference_mm.max()),first_failure=None if bad.empty else bad.iloc[0].to_dict(),
        native_sampling_only_0_ulp=True,runs=summaries,admitted_15s=False,full_cycle_admitted=False,evidence=evidence)
    with out.open("x",encoding="utf8") as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k not in ("evidence","runs")},indent=2),flush=True)


if __name__=="__main__":main()
