"""Review the full native-checker receipts; independently sample PART and plot histories."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import numpy as np
import pandas as pd
from k5em5_hg05_window_review import plt, figure_save, reference, pressure_theory
from k5em5_hg05_full import completion
from formal_release_sequence import TESTS, save, utc
from mdbc_gpu_vector_run import bound, read, verify
import k5_guard_probe as probe

TAG = "k5em5_hg05_15s_cpu_r1"


def main():
    target = TESTS/"logs"/(TAG+".release.numeric.json")
    assert not target.exists()
    state, half, prefix = [TESTS/"logs"/(TAG+s) for s in (".status.json", "_half.check.json", ".prefix1s.check.json")]
    report, pair, prior = map(read, (state, half, prefix))
    assert report["status"] == "pair_passed_pending_physical_review" and prior["passed"] and prior["frames_each"] == 1001
    assert pair == report["half"] and pair["passed"] and pair["samples"] == 15001
    assert pair["pressure_rms_max_pa"] <= 5 and pair["top_settlement_difference_max_mm"] <= .005
    paths = [Path(__file__), state, half, prefix, TESTS/"logs"/(TAG+".queue_attempt.json"),
             TESTS/"logs"/(TAG+".analysis_retired.json")]
    assert read(paths[4])["terminal"]["runs"] == report["runs"]
    verify(prior["evidence"])
    hashes = report["inputs"]+[item for run in report["runs"] for item in run["outputs"]]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda item: verify([item]), hashes))
    print(f"Verified {len(hashes)} input/output hashes; reusing completed all-15001 native safety/half checks.", flush=True)
    data, summaries, profiles, artifacts = [], [], [], []
    samples = (0, 10, 20, 50, 100, 300, 500, 1000, 2000, 5000, 7300, 10000, 12000, 15000)
    for variant, run in zip(("c", "h"), report["runs"]):
        assert run["completed"] and run["owned_exited"] and run["exit_code"] == 0 and run["checked_frames"] == 15001
        assert run["prefix_frames_equal"] == 301
        folder = TESTS/"outputs"/(TAG+"_"+variant)
        info = completion(folder, 1500000 if variant == "c" else 3000000, 15, 15001)
        model = reference.model(folder/(TAG+"_"+variant+".xml"))
        assert model["dp"] == .01 and model["width"] == .1 and model["k"] == 5e-5
        initial = probe.native(folder, 0)
        history = TESTS/"figures"/(TAG+"_"+variant+"_runtime.csv")
        paths.append(history)
        frame = pd.read_csv(history, float_precision="round_trip")
        assert len(frame) == 15001 and np.array_equal(frame.step, np.arange(15001)*(100 if variant == "c" else 200))
        assert frame.time_s.diff().iloc[1:].gt(0).all()
        post = frame[frame.time_s >= .1-1e-7]
        assert post.max_layer_total_error_pa.le(100).all() and post.top_gap_pa.le(100).all()
        assert abs(post.load_resultant_N_m+1000).lt(.001).all()
        assert frame.max_dx_mm.lt(.5).all() and frame.max_layer_span_mm.lt(.5).all()
        # Vectorized evaluation of the unchanged 240-term reference, reconciled below.
        modes = (2*np.arange(240)+1)*np.pi/2
        z0 = initial.z.to_numpy().reshape(10,100).mean(axis=0)
        tv = model["cv"]*np.maximum(frame.time_s.to_numpy()-model["tD"], 0)/model["H"]**2
        decay = np.exp(-tv[:,None]*modes[None,:]**2)
        frame["tv"] = tv
        frame["theory_mean_pa"] = model["q0"]*(decay @ (2*(-1.)**np.arange(240)/modes*np.cos(z0[:,None]*modes/model["H"]).mean(axis=0)))
        coeff = 2*model["q0"]*model["H"]*(-1.)**np.arange(240)/modes**2*np.sin(modes*z0[-1]/model["H"])
        frame["classical_top_mm"] = (model["q0"]*z0[-1]-decay@coeff)/model["M"]*1000
        sampled = []
        for i in samples:
            a = probe.native(folder, i)
            assert np.array_equal(a.id, np.arange(40,1040)) and a.load_available.eq(1).all()
            value = reference.inspect(a, initial, model)
            for key in ("time_s", "mean_pressure_pa", "top_settlement_mm", "bottom_settlement_mm", "max_layer_total_error_pa", "top_gap_pa", "Q_pa"):
                assert abs(value[key]-frame.iloc[i][key]) < 1e-7, (variant, i, key)
            if a.time_s.iloc[0] >= model["tD"]:
                truth = pressure_theory(initial.z.to_numpy(), value["tv"], model)
                assert abs(truth.mean()-frame.theory_mean_pa.iloc[i]) < 1e-7
                assert abs(value["classical_top_mm"]-frame.classical_top_mm.iloc[i]) < 1e-7
                value["pressure_theory_rmse_pa"] = float(np.sqrt(np.mean((a.pressure-truth)**2)))
                value["mean_pressure_theory_error_pa"] = float(a.pressure.mean()-truth.mean())
            sampled.append(dict(part=i, **value))
            if i in (100,1000,5000,15000):
                numeric = a.pressure.to_numpy().reshape(10,100).mean(axis=0)
                ideal = pressure_theory(z0, value["tv"], model)
                profiles.extend(dict(variant=variant,part=i,time_s=value["time_s"],tv=value["tv"],z0_m=float(z),pressure_pa=float(p),theory_pa=float(q)) for z,p,q in zip(z0,numeric,ideal))
        final = sampled[-1]
        summaries.append(dict(variant=variant, **info, final=final,
            material_settlement_error_pct=100*(final["top_settlement_mm"]/final["classical_top_mm"]-1),
            max_post_point1_stress_pa=float(post.max_layer_total_error_pa.max()),max_post_point1_top_gap_pa=float(post.top_gap_pa.max()),
            max_force_error_N_m=float(abs(post.load_resultant_N_m+1000).max()),Q_after1_min_pa=float(post[post.time_s>=1].Q_pa.min())))
        csv = TESTS/"figures"/(TAG+"_"+variant+"_release_review.csv")
        frame.to_csv(csv,index=False,mode="x")
        artifacts.append(csv)
        csv = TESTS/"figures"/(TAG+"_"+variant+"_native_samples.csv")
        pd.DataFrame(sampled).to_csv(csv,index=False,mode="x")
        artifacts.append(csv)
        data.append(frame)
    plt.rcParams.update({"font.size":10,"axes.titlesize":11,"legend.fontsize":9})
    colors = ("#2168a6", "#d87832")
    fig, axes = plt.subplots(2,2,figsize=(11,8))
    keys=("mean_pressure_pa","top_settlement_mm","max_layer_total_error_pa","Q_pa")
    titles=("Mean pore pressure (Pa)","Top material settlement (mm)","Maximum layer stress residual (Pa)","Stress second-difference RMS Q (Pa)")
    for frame,color,label,style in zip(data,colors,("10 us","5 us"),("-","--")):
        for ax,key,title in zip(axes.flat,keys,titles):
            values=frame if key in keys[:2] else frame[frame.time_s>=.1-1e-7]
            ax.plot(values.time_s,values[key],color=color,ls=style,label=label)
            ax.set(title=title,xlabel="Actual time (s)")
            ax.grid(alpha=.2)
    loaded=data[0][data[0].time_s>=.01]
    axes[0,0].plot(loaded.time_s,loaded.theory_mean_pa,color=".25",ls=":",label="Ideal theory")
    axes[0,1].plot(loaded.time_s,loaded.classical_top_mm,color=".25",ls=":")
    axes[0,0].legend()
    axes[1,0].axhline(100,color=".25",ls=":")
    fig.suptitle("k=5e-5, dp=.01 m, xi=.05: completed 15-s CPU pair")
    png=TESTS/"figures"/(TAG+"_release_history.png")
    figure_save(fig,png,"Hash-bound full native-checker histories; 14 native frames/run independently recomputed. Ideal theory omits the .01-s ramp; not 2Tv.")
    artifacts.append(png)
    fig,axes=plt.subplots(2,2,figsize=(11,8))
    for frame,color,label,style in zip(data,colors,("10 us","5 us"),("-","--")):
        post=frame[frame.time_s>=.1-1e-7]
        axes[0,0].plot(post.time_s,post.top_gap_pa,color=color,ls=style,label=label)
        axes[0,1].plot(post.time_s,abs(post.load_resultant_N_m+1000),color=color,ls=style)
    axes[0,0].legend()
    for ax,title,limit in zip(axes[0],("Top adjacent-layer stress gap (Pa)","Applied-force error (N/m)"),(100,.001)):
        ax.set(title=title,xlabel="Actual time (s)",ylim=(0,limit*1.05))
        ax.axhline(limit,color=".25",ls=":")
        ax.grid(alpha=.2)
    for ax,value,limit,title in zip(axes[1],(pair["pressure_rms_max_pa"],pair["top_settlement_difference_max_mm"]),(5,.005),("All-15001 pressure-half maximum (Pa)","All-15001 material-half maximum (mm)")):
        ax.bar((0,1),(value,limit),color=(colors[0],".65"),width=.5)
        ax.set(title=title,xticks=(0,1),xticklabels=("Native-checker peak","Unchanged limit"),ylim=(0,limit*1.12))
        ax.text(0,value+limit*.025,f"{value:.6g}",ha="center")
    fig.suptitle("Full-window original safety and inherited all-sample half-step checks")
    png=TESTS/"figures"/(TAG+"_release_guards.png")
    figure_save(fig,png,"Half-step peaks come from the completed all-15001 native pair receipt, not a new half-run or a sampled maximum.")
    artifacts.append(png)
    profiles=pd.DataFrame(profiles)
    fig,axes=plt.subplots(2,2,figsize=(10,8))
    for ax,i in zip(axes.flat,(100,1000,5000,15000)):
        for variant,color,style in zip(("c","h"),colors,("-","--")):
            f=profiles[(profiles.part==i)&(profiles.variant==variant)]
            ax.plot(f.pressure_pa/10000,f.z0_m,color=color,ls=style,label="10 us" if variant=="c" else "5 us")
            if variant=="c":ax.plot(f.theory_pa/10000,f.z0_m,color=".25",ls=":",label="Ideal theory")
        ax.set(title=f"t={f.time_s.iloc[0]:.3f} s; Tv={f.tv.iloc[0]:.5f}",xlabel="Pore pressure / q0",ylabel="Initial material z0 (m)",xlim=(0,1.03),ylim=(0,1))
        ax.grid(alpha=.2)
    axes[0,0].legend()
    fig.suptitle("15-s pore-pressure profiles at actual native save times")
    png=TESTS/"figures"/(TAG+"_release_profiles.png")
    figure_save(fig,png,"Theory uses H=1 m; the top numerical node is z0=.995 m. Same native material IDs; instantaneous ideal load, not full-cycle acceptance.")
    artifacts.append(png)
    csv=TESTS/"figures"/(TAG+"_release_profiles.csv")
    profiles.to_csv(csv,index=False,mode="x")
    artifacts.append(csv)
    result=dict(passed=True,visual_inspected=False,utc=utc(),full_admitted=False,samples=15001,hash_verified_files=len(hashes),
        original_all_sample_safety_and_half_receipts_verified=True,independent_native_samples_each=list(samples),
        native_prefix_equal_frames_each=1001,pressure_half_max_pa=pair["pressure_rms_max_pa"],settlement_half_max_mm=pair["top_settlement_difference_max_mm"],
        variants=summaries,evidence=[bound(p) for p in paths+artifacts],
        methodology="Reuse completed full native safety/half checks with all file hashes verified; independent 14-frame/run metric/theory reconciliation and all-1001 saved prefix checks. Not a second full native rerun.",
        limits=["Q is not monotonic: about4.23 Pa minimum after1s to5.67 Pa at15s.","Only15-s half-step evidence; no2Tv/plastic/general-boundary/exact-HG-restart acceptance.","k3/k4 retain xi=.1; this third-group candidate uses xi=.05."])
    save(target,result)
    print(json.dumps({k:v for k,v in result.items() if k!='evidence'},indent=2),flush=True)


if __name__ == "__main__":
    main()
