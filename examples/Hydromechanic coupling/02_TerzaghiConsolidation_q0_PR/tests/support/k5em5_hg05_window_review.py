"""Offline 1/15-s native audit and static plots. Never runs the physical solver."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import re
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from formal_release_sequence import CASE, TESTS, save, utc
from mdbc_gpu_vector_run import bound, read, verify
import k5_guard_probe as probe
sys.path.insert(0, str(CASE/"support"))
import release_case as reference
from compare_precision_q0 import pressure_theory


def figure_save(fig, path, foot):
    fig.text(.06, .018, foot, fontsize=8)
    fig.tight_layout(rect=(0, .055, 1, .95), h_pad=2, w_pad=2)
    with path.open("xb") as stream:
        fig.savefig(stream, dpi=180)
    plt.close(fig)


def main(args):
    tag = "k5em5_hg05_"+str(args.end)+"s_"+args.backend+"_r1"
    out = TESTS/"logs"/(tag+".review.numeric.json")
    assert not out.exists()
    state, half_path = [TESTS/"logs"/(tag+s) for s in (".status.json", "_half.check.json")]
    report, old_half = read(state), read(half_path)
    queue = TESTS/"logs"/(tag+".queue_attempt.json")
    assert read(queue)["terminal"]["runs"] == report["runs"]
    assert report["status"] == "pair_passed_pending_physical_review" and not report["full_admitted"]
    verify(report["inputs"])
    models, initial, histories, evidence, run_info = [], [], [], [Path(__file__), state, half_path, queue], []
    for v, r in zip(("c", "h"), report["runs"]):
        assert r["owned_exited"] and r["exit_code"] == 0 and r["completed"] and r["prefix_frames_equal"] == 301
        verify(r["outputs"])
        folder = TESTS/"outputs"/(tag+"_"+v)
        m = reference.model(folder/(tag+"_"+v+".xml"))
        assert m["dp"] == .01 and m["width"] == .1 and m["k"] == 5e-5 and m["nx"] == 10 and m["nz"] == 100
        assert m["tmax"] == args.end and m["dt"] == (1e-5 if v == "c" else 5e-6)
        text = (folder/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
        assert "Finished execution (code=0)." in text
        steps = int(args.end/m["dt"]+.5)
        counts = re.search(r"forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
        cache = re.search(r"ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
        limits = re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)", text)
        assert counts and tuple(map(int, counts.groups())) == (2*steps, steps, steps, 2*steps)
        assert cache and tuple(map(int, cache.groups())) == (steps+1, steps-1)
        assert limits and float(limits[1]) <= .2 and float(limits[2]) < .01
        summary = pd.read_csv(folder/"Run.csv", sep=";").iloc[0]
        assert summary.Steps == steps and summary.Np == 1040 and summary.Nfixed == 40 and summary.PartsOut == 0
        assert len(list((folder/"data").glob("Part_*.bi4"))) == args.end*1000+1
        models.append(m)
        initial.append(probe.native(folder, 0))
        histories.append(pd.read_csv(TESTS/"figures"/(tag+"_"+v+"_runtime.csv"), float_precision="round_trip"))
        run_info.append(dict(variant=v, steps=steps, loop_seconds=float(summary.TSimul), hg_dt_tau_max=float(limits[1]), spin_bound=float(limits[2])))
    def sample(i):
        frames = [probe.native(TESTS/"outputs"/(tag+"_"+v), i) for v in ("c", "h")]
        rows = []
        for k, (v, a, m, start) in enumerate(zip(("c", "h"), frames, models, initial)):
            assert np.array_equal(a.id, np.arange(40, 1040)) and a.load_available.eq(1).all()
            value = reference.inspect(a, start, m)
            for key in ("time_s", "mean_pressure_pa", "top_settlement_mm", "bottom_settlement_mm", "max_layer_total_error_pa", "top_gap_pa", "Q_pa"):
                assert abs(value[key]-histories[k].iloc[i][key]) < 1e-7, key
            if i <= 300:
                prior = "k5em5_hg05_"+("r1" if args.backend == "cpu" else "gpu_r1")+"_"+v
                assert a.equals(probe.native(TESTS/"outputs"/prior, i)), "Prefix mismatch"
            if value["time_s"] >= m["tD"]:
                p = pressure_theory(start.z.to_numpy(), value["tv"], m)
                value.update(theory_pressure_mean_pa=float(p.mean()), pressure_theory_rmse_pa=float(np.sqrt(np.mean((a.pressure-p)**2))))
            else:
                value.update(theory_pressure_mean_pa=np.nan, pressure_theory_rmse_pa=np.nan)
            rows.append(value)
        a, b = frames
        assert abs(a.time_s.iloc[0]-b.time_s.iloc[0]) < 1e-8 and b.step.iloc[0] == 2*a.step.iloc[0]
        pressure = float(np.sqrt(np.mean((a.pressure-b.pressure)**2)))
        top = np.arange(139, 1040, 100)
        difference = abs(float((a.set_index("id").loc[top,"z"]-b.set_index("id").loc[top,"z"]).mean())*1000)
        assert pressure <= 5 and difference <= .005
        return rows, dict(time_s=float(a.time_s.iloc[0]), pressure_rms_pa=pressure, top_difference_mm=difference)
    print("Inputs/output hashes and run/HG manifests verified; recomputing every native pair.", flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        sampled = list(pool.map(sample, range(args.end*1000+1)))
    data = [pd.DataFrame([x[0][k] for x in sampled]) for k in (0, 1)]
    pair = pd.DataFrame([x[1] for x in sampled])
    assert abs(pair.pressure_rms_pa.max()-old_half["pressure_rms_max_pa"]) < 1e-10
    assert abs(pair.top_difference_mm.max()-old_half["top_settlement_difference_max_mm"]) < 1e-10
    plt.rcParams.update({"font.size":10,"axes.titlesize":11,"axes.labelsize":10,"legend.fontsize":9})
    colors = ("#2168a6", "#d87832")
    artifacts, summaries = [], []
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for k, (v, frame, color, info) in enumerate(zip(("c", "h"), data, colors, run_info)):
        post = frame[frame.time_s >= .1-1e-7]
        axes[0,0].plot(frame.time_s,frame.mean_pressure_pa,color=color,label="dt="+("10" if v=="c" else "5")+" us",ls="-" if v=="c" else "--")
        axes[0,1].plot(frame.time_s,frame.top_settlement_mm,color=color,ls="-" if v=="c" else "--")
        axes[1,0].plot(post.time_s,post.max_layer_total_error_pa,color=color,ls="-" if v=="c" else "--")
        axes[1,1].plot(post.time_s,post.Q_pa,color=color,ls="-" if v=="c" else "--")
        final = frame.iloc[-1].to_dict()
        summaries.append(dict(**info, actual_final_time_s=float(final["time_s"]), final=final,
                              max_post_point1_stress_pa=float(post.max_layer_total_error_pa.max()), max_post_point1_top_gap_pa=float(post.top_gap_pa.max()),
                              max_force_error_N_m=float(abs(post.load_resultant_N_m+1000).max()),
                              max_post_point1_Q_pa=float(post.Q_pa.max()), material_settlement_error_pct=float(100*(final["top_settlement_mm"]/final["classical_top_mm"]-1))))
        csv = TESTS/"figures"/(tag+"_"+v+"_review.csv")
        frame.to_csv(csv,index=False,mode="x")
        artifacts.append(csv)
    loaded = data[0][data[0].time_s>=models[0]["tD"]]
    axes[0,0].plot(loaded.time_s,loaded.theory_pressure_mean_pa,color=".25",ls=":",label="Ideal theory")
    axes[0,1].plot(loaded.time_s,loaded.classical_top_mm,color=".25",ls=":")
    for ax, title, ylabel in zip(axes.flat,("Mean pore pressure","Top material settlement","Maximum layer stress residual","Stress second-difference RMS Q"),("Pressure (Pa)","Settlement (mm)","Residual (Pa)","Q (Pa)")):
        ax.set(title=title,xlabel="Actual time (s)",ylabel=ylabel)
        ax.grid(alpha=.2)
    axes[0,0].legend()
    axes[1,0].axhline(100,color=".25",ls=":",lw=1)
    fig.suptitle(f"k=5e-5, dp=.01 m, xi=.05: {args.end}-s {args.backend.upper()} pair")
    png=TESTS/"figures"/(tag+"_history.png")
    figure_save(fig,png,"Ideal instantaneous-load theory omits the .01-s ramp. Material points use native initial positions; no full-cycle acceptance.")
    artifacts.append(png)
    fig, axes=plt.subplots(2,2,figsize=(11,8))
    for v, frame, color in zip(("c","h"),data,colors):
        post=frame[frame.time_s>=.1-1e-7]
        axes[0,0].plot(post.time_s,post.top_gap_pa,color=color,ls="-" if v=="c" else "--",label="dt="+("10" if v=="c" else "5")+" us")
        axes[0,1].plot(post.time_s,abs(post.load_resultant_N_m+1000),color=color,ls="-" if v=="c" else "--")
    axes[1,0].plot(pair.time_s,pair.pressure_rms_pa,color=colors[0])
    axes[1,1].plot(pair.time_s,pair.top_difference_mm,color=colors[0])
    for ax,title,ylabel,limit in zip(axes.flat,("Top adjacent-layer stress gap","Applied-force balance","All-sample pressure half-step difference","Top material half-step difference"),("Gap (Pa)","|F+1000| (N/m)","Pressure RMS (Pa)","Settlement difference (mm)"),(100,.001,5,.005)):
        ax.axhline(limit,color=".25",ls=":",lw=1)
        ax.set(title=title,xlabel="Actual time (s)",ylabel=ylabel)
        ax.set_ylim(0,limit*1.05)
        ax.grid(alpha=.2)
    axes[0,0].legend()
    fig.suptitle(f"{args.end}-s original safety and half-step limits; all {args.end*1000+1} pairs")
    png=TESTS/"figures"/(tag+"_guards.png")
    figure_save(fig,png,"Dotted lines are unchanged admission limits. Runtime history and native PART fields independently reconciled.")
    artifacts.append(png)
    fig,axes=plt.subplots(2,2,figsize=(10,8))
    samples=(100,300,500,1000) if args.end==1 else (100,1000,5000,15000)
    profile_rows=[]
    for ax,i in zip(axes.flat,samples):
        for v,color in zip(("c","h"),colors):
            a=probe.native(TESTS/"outputs"/(tag+"_"+v),i)
            z0=initial[0].z.to_numpy().reshape(10,100).mean(0)
            numeric=a.pressure.to_numpy().reshape(10,100).mean(0)
            tv=models[0]["cv"]*max(float(a.time_s.iloc[0])-models[0]["tD"],0)
            ideal=pressure_theory(z0,tv,models[0])
            ax.plot(numeric/10000,z0,color=color,ls="-" if v=="c" else "--",label="dt="+("10" if v=="c" else "5")+" us")
            if v=="c":
                ax.plot(ideal/10000,z0,color=".25",ls=":",label="Ideal theory")
            profile_rows.extend(dict(part=i,variant=v,time_s=float(a.time_s.iloc[0]),tv=tv,z0_m=float(z),pressure_pa=float(p),theory_pa=float(q)) for z,p,q in zip(z0,numeric,ideal))
        ax.set(title=f"t={float(a.time_s.iloc[0]):.3f} s; Tv={tv:.5f}",xlabel="Pore pressure / q0",ylabel="Initial material z0 (m)",xlim=(0,1.03),ylim=(0,1))
        ax.grid(alpha=.2)
    axes[0,0].legend()
    fig.suptitle(f"{args.end}-s pore-pressure profiles at actual native save times")
    png=TESTS/"figures"/(tag+"_profiles.png")
    figure_save(fig,png,"Constant n/k, same dp=.01 m. Theoretical surface H=1 m; top numerical pressure node is z0=.995 m. Ramp omitted in ideal theory.")
    artifacts.append(png)
    csv=TESTS/"figures"/(tag+"_profiles_review.csv")
    pd.DataFrame(profile_rows).to_csv(csv,index=False,mode="x")
    artifacts.append(csv)
    csv=TESTS/"figures"/(tag+"_half_review.csv")
    pair.to_csv(csv,index=False,mode="x")
    artifacts.append(csv)
    result=dict(passed=True,visual_inspected=False,utc=utc(),full_admitted=False,physical_scope="bounded-window only",samples=args.end*1000+1,
                hash_verified_files=sum(len(x["outputs"]) for x in report["runs"])+len(report["inputs"]), native_prefix_equal_frames_each=301,
                pressure_half_max_pa=float(pair.pressure_rms_pa.max()),settlement_half_max_mm=float(pair.top_difference_mm.max()),variants=summaries,
                evidence=[bound(p) for p in evidence+artifacts],limits=["Instantaneous-load theory excludes finite ramp and initial compressibility transient.","No 2Tv, plasticity, complex boundary or exact HG restart acceptance."])
    save(out,result)
    print(json.dumps({k:v for k,v in result.items() if k!="evidence"},indent=2),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--end",type=int,choices=(1,15),required=True)
    p.add_argument("--backend",choices=("cpu","gpu"),required=True)
    main(p.parse_args())
