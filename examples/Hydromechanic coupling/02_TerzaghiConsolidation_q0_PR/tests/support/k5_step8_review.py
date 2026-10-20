"""Native field/time-step review of the bounded 8/4-us short candidate."""
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import k5_cell_sequence as cell
from k5_step8_sequence import TAG, BASE
from formal_release_sequence import TESTS, utc
from mdbc_gpu_vector_run import read, bound, verify


def main():
    check=TESTS/"logs/k5_step8_review_r1.check.json"; assert not check.exists()
    sp=TESTS/"logs"/(TAG+".status.json"); qp=TESTS/"logs"/(TAG+".queue_attempt.json")
    state=read(sp); old=read(TESTS/"logs/k5_cell_review_r1.check.json")
    assert state["status"] == read(qp)["terminal"]["status"] == "step8_1s_pairs_passed_pending_review"
    assert old["audit_passed"] and len(state["runs"]) == 4 and state["queue_status"] == "queued"
    evidence=state["inputs"]+old["evidence"]+[bound(p) for p in (Path(__file__),sp,qp)]
    for r in state["runs"]:
        assert r["completed"] and r["exit_code"] == 0 and r["owned_process_exited"] and not r.get("stopped_by_monitor",False)
        evidence+=r["outputs"]
    unique={p["path"]:p for p in evidence}; verify(unique.values()); print("Verified hashes",len(unique),flush=True)
    data,history,prefix,summaries={},{},{},[]
    for r in state["runs"]:
        suffix=r["label"].removeprefix(TAG+"_"); folder=TESTS/"outputs"/r["label"]
        files=sorted((folder/"data").glob("Part_*.bi4")); assert len(files)==r["frames"]
        frames=[cell.probe.native(folder,i) for i in range(len(files))]; initial=frames[0]
        rows=[cell.metrics(a,initial) for a in frames]
        assert rows[-1]==r["final"] and abs(rows[-1]["time_s"]-r["duration_s"])<1e-7
        assert all(m["step"]==i*round(.005/r["dt_s"]) for i,m in enumerate(rows))
        n=round(r["duration_s"]/r["dt_s"]); assert rows[-1]["step"]==n
        text=(folder/"Run.out").read_text(encoding="utf-8-sig",errors="replace")
        calls=re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)",text)
        limits=re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)",text)
        assert "Finished execution (code=0)." in text and list(map(int,calls.groups()))==[2*n,n,n,2*n]
        assert float(limits[1])<=.2 and float(limits[2])<.01
        run=pd.read_csv(folder/"Run.csv",sep=";").iloc[0]
        assert run.Np==2592 and run.Nfixed==32 and run.PartsOut==0 and run.Steps==n
        h=pd.DataFrame(rows); post=h[h.stress_guard_applicable]
        csv=TESTS/"figures"/(r["label"]+"_review.csv"); h.to_csv(csv,index=False,mode="x"); evidence.append(bound(csv))
        summaries.append(dict(label=r["label"],final=rows[-1],samples=len(rows),loop_seconds=float(run.TSimul),
            post_point1s_max_stress_pa=float(post.max_layer_total_error_pa.max()),post_point1s_max_top_gap_pa=float(post.top_gap_pa.max()),
            max_equivalent_force_error_N_m=float(abs(post.equivalent_full_width_resultant_N_m+1000).max()),hg_max_dt_tau=float(limits[1]),hg_spin_bound=float(limits[2])))
        data[suffix],history[suffix]=frames,h
        prefix[suffix]=[a[cell.FIELDS].to_numpy(dtype="<f8").tobytes() for a in frames[:31]]
        print("Native review",suffix,len(rows),flush=True)
    assert prefix["015c"]==prefix["1c"] and prefix["015h"]==prefix["1h"]
    curves,reference_profiles={},{}
    for suffix in ("1c","1h","half"):
        rows=[]
        if suffix!="half":
            folder=TESTS/"outputs"/(BASE+"_"+suffix)
            control=[cell.probe.native(folder,i) for i in range(201)]
            aa,bb=control,data[suffix]; reference_profiles[suffix]=control
        else: aa,bb=data["1c"],data["1h"]
        top=aa[0].z>.996
        for a,b in zip(aa,bb):
            assert np.array_equal(a.id,b.id) and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-8
            if suffix=="half": assert b.step.iloc[0]==2*a.step.iloc[0]
            p=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))); u=abs(float((a.z[top]-b.z[top]).mean()*1000))
            assert p<=5 and u<=.005
            rows.append(dict(time_s=float(a.time_s.iloc[0]),pressure_rms_pa=p,top_settlement_difference_mm=u,
                max_total_stress_difference_pa=float(abs((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure)).max())))
        h=pd.DataFrame(rows); curves[suffix]=h
        for length,count in (("015",31),("1",201)):
            kind="half" if suffix=="half" else "reference_step"
            right=TAG+"_"+length+("h" if suffix=="half" else suffix[-1])
            receipt=next(r for r in state["comparisons"] if r["kind"]==kind and r["right"]==right)
            for key in ("pressure_rms_pa","top_settlement_difference_mm","max_total_stress_difference_pa"):
                assert np.isclose(h[key].iloc[:count].max(),receipt[key],rtol=1e-12,atol=1e-12)
        csv=TESTS/"figures"/("k5_step8_review_r1_"+suffix+".csv"); h.to_csv(csv,index=False,mode="x"); evidence.append(bound(csv))
    timing=[]
    for suffix in ("1c","1h"):
        a=next(r for r in old["runs"] if r["label"]==BASE+"_"+suffix)["loop_seconds"]
        b=next(r for r in summaries if r["label"]==TAG+"_"+suffix)["loop_seconds"]
        timing.append(dict(suffix=suffix,old_seconds=a,new_seconds=b,observed_speedup=a/b,observed_reduction_percent=100*(1-b/a),estimated_2tv_days=b*728.75286/86400))
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    for ax,key,ylabel in zip(axes.flat,("mean_pressure_pa","top_settlement_mm","max_layer_total_error_pa","Q_pa"),
        ("Mean pore pressure (Pa)","Top material settlement (mm)","Max layer total-stress error (Pa)","Q: RMS second layer difference (Pa)")):
        for label,h,color,style in (("8 us",history["1c"],"#256da3","-"),("4 us",history["1h"],"#c47725","--")):
            q=h[h.stress_guard_applicable] if key=="max_layer_total_error_pa" else h
            ax.plot(q.time_s,q[key],color=color,ls=style,lw=1.5,label=label)
        ax.set(xlabel="Actual physical time (s)",ylabel=ylabel,xlim=(0,1)); ax.grid(alpha=.2)
        if key=="max_layer_total_error_pa": ax.set(xlim=(.1,1),ylim=(0,105)); ax.axhline(100,color=".25",ls=":")
    axes[0,0].legend(fontsize=9)
    for key,color,style,label in (("half","#256da3","-","8 / 4 us half pair"),("1c","#555555","--","5 / 8 us reference"),("1h","#c47725",":","2.5 / 4 us reference")):
        h=curves[key]; axes[1,1].plot(h.time_s,h.pressure_rms_pa,color=color,ls=style,label=label)
    axes[1,1].axhline(5,color=".25",ls=":"); axes[1,1].set(xlabel="Actual time (s); saved every 5 ms",ylabel="Pressure RMS difference (Pa)",xlim=(0,1),ylim=(0,5.4)); axes[1,1].legend(fontsize=8); axes[1,1].grid(alpha=.2)
    x=np.arange(2)
    axes[1,2].bar(x-.17,[r["old_seconds"]/60 for r in timing],.34,color="#555555",label="5 / 2.5 us baseline")
    axes[1,2].bar(x+.17,[r["new_seconds"]/60 for r in timing],.34,color="#256da3",label="8 / 4 us candidate")
    axes[1,2].set(xticks=x,xticklabels=["Coarse","Half"],ylabel="Observed 1-s GPU loop time (min)",ylim=(0,42));axes[1,2].legend(fontsize=8)
    fig.suptitle("k=1e-5, dp=1/320 m, width=.025 m: bounded time-step short comparison")
    fig.text(.5,.008,"5-ms sampling: peak half difference is close to 5 Pa; denser short output is required before a long-window decision. No 2Tv claim.",ha="center",fontsize=9)
    fig.tight_layout(rect=(0,.03,1,.95)); png=TESTS/"figures/k5_step8_review_r1_history.png"
    with png.open("xb") as stream:fig.savefig(stream,dpi=160)
    plt.close(fig); evidence.append(bound(png))
    fig,axes=plt.subplots(2,2,figsize=(11,8))
    z0=data["1c"][0].z.to_numpy().reshape(8,320).mean(0)
    for row,i in enumerate((30,200)):
        for a,color,style,label in ((data["1c"][i],"#256da3","-","8 us"),(data["1h"][i],"#c47725","--","4 us"),(reference_profiles["1c"][i],"#555555",":","5 us retained")):
            axes[row,0].plot(a.pressure.to_numpy().reshape(8,320).mean(0)/10000,z0,color=color,ls=style,label=label)
            axes[row,1].plot((a.sigma_zz-a.pressure).to_numpy().reshape(8,320).mean(0)+10000,z0,color=color,ls=style)
        for col in range(2):axes[row,col].set(ylim=(.85,1),ylabel="Initial material height z0/H",title=f"Actual t={data['1c'][i].time_s.iloc[0]:.6g} s");axes[row,col].grid(alpha=.2)
        axes[row,0].set_xlabel("Pore pressure / q0");axes[row,1].set(xlabel="Layer total stress + q0 (Pa)",xlim=(-105,105))
    axes[0,0].legend();fig.suptitle("Native near-surface profiles: time-step sensitivity, not theory truth")
    fig.tight_layout(rect=(0,0,1,.95));png=TESTS/"figures/k5_step8_review_r1_profiles.png"
    with png.open("xb") as stream:fig.savefig(stream,dpi=160)
    plt.close(fig);evidence.append(bound(png))
    result=dict(audit_passed=True,reviewed_utc=utc(),verified_recorded_hashes=len(unique),runs=summaries,timing=timing,
        comparisons=state["comparisons"],native_prefix_0_ulp=True,dense_short_required=True,admitted_15s=False,full_cycle_admitted=False,
        limitations=["Only 5-ms-sampled .15/1-s evidence; maximum half pressure difference 4.65046 Pa is close to 5 Pa.","No theory/full-cycle/plastic/complex-boundary or exact-HG-restart acceptance."],evidence=evidence)
    with check.open("x",encoding="utf8") as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k not in ("evidence","runs","comparisons")},indent=2),flush=True)


if __name__ == "__main__":main()
