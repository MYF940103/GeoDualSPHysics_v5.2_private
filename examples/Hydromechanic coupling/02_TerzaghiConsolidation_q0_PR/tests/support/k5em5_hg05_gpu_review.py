"""Audit GPU pair, CPU/GPU material comparison, native runtime and loop timing."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from formal_release_sequence import TESTS, save, utc
from mdbc_gpu_vector_run import bound, read, verify
import k5_guard_probe as probe
from k5em5_uniform_review import layer, finish, COLORS

TAG = "k5em5_hg05_gpu_review_r1"


def main():
    out = TESTS/"logs"/(TAG+".numeric.json")
    assert not out.exists()
    state = TESTS/"logs/k5em5_hg05_gpu_r1.status.json"
    r = read(state)
    assert r["status"] == "completed_diagnostic_not_full_admission" and len(r["runs"]) == 2
    verify(r["inputs"])
    timings, evidence = [], [Path(__file__), state, TESTS/"logs/k5em5_hg05_review_r1.check.json"]
    for v, g, steps in zip(("c", "h"), r["runs"], (30000, 60000)):
        assert g["numerical_safety_passed"] and g["owned_exited"] and g["exit_code"] == 0 and g["checked_frames"] == 301
        verify(g["outputs"])
        for backend, label in (("CPU8", "k5em5_hg05_r1_"+v), ("GPU0", "k5em5_hg05_gpu_r1_"+v)):
            folder = TESTS/"outputs"/label
            text = (folder/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
            counts = re.search(r"forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
            cache = re.search(r"ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
            limits = re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)", text)
            assert counts and tuple(map(int, counts.groups())) == (2*steps, steps, steps, 2*steps)
            assert cache and tuple(map(int, cache.groups())) == (steps+1, steps-1)
            assert limits and float(limits[1]) <= .2 and float(limits[2]) < .01
            summary = pd.read_csv(folder/"Run.csv", sep=";").iloc[0]
            assert summary.Steps == steps and summary.Np == 1040 and summary.PartsOut == 0
            timings.append(dict(backend=backend, variant=v, steps=steps, loop_seconds=float(summary.TSimul), steps_per_second=steps/float(summary.TSimul)))
            evidence += [folder/"Run.out", folder/"Run.csv"]
    def compare(i):
        a, b, c, d = [probe.native(TESTS/"outputs"/label, i) for label in
                      ("k5em5_hg05_gpu_r1_c", "k5em5_hg05_gpu_r1_h", "k5em5_hg05_r1_c", "k5em5_hg05_r1_h")]
        for v in (b, c, d):
            assert np.array_equal(a.id, v.id) and abs(a.time_s.iloc[0]-v.time_s.iloc[0]) < 1e-8
        assert a.step.iloc[0] == c.step.iloc[0] and b.step.iloc[0] == d.step.iloc[0] == 2*a.step.iloc[0]
        top = (a.id-40)%100 == 99
        return dict(time_s=float(a.time_s.iloc[0]),
                    half_pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))),
                    half_settlement_mm=abs(float((a.z[top]-b.z[top]).mean())*1000),
                    cpu_gpu_pressure_rms_pa=max(float(np.sqrt(np.mean((a.pressure-c.pressure)**2))),float(np.sqrt(np.mean((b.pressure-d.pressure)**2)))),
                    cpu_gpu_settlement_mm=max(abs(float((a.z[top]-c.z[top]).mean())*1000),abs(float((b.z[top]-d.z[top]).mean())*1000)),
                    cpu_gpu_stress_pointwise_pa=max(float(abs(a.sigma_zz-c.sigma_zz).max()),float(abs(b.sigma_zz-d.sigma_zz).max())))
    with ThreadPoolExecutor(max_workers=4) as pool:
        data = pd.DataFrame(pool.map(compare, range(301)))
    maxima = {c:float(data[c].max()) for c in data.columns if c != "time_s"}
    assert maxima["half_pressure_rms_pa"] <= 5 and maxima["half_settlement_mm"] <= .005
    assert maxima["cpu_gpu_pressure_rms_pa"] <= 5 and maxima["cpu_gpu_settlement_mm"] <= .005
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    for backend, color, label in (("CPU8",COLORS[0],"k5em5_hg05_r1_c"),("GPU0",COLORS[1],"k5em5_hg05_gpu_r1_c")):
        h = pd.read_csv(TESTS/"figures"/(label+"_runtime.csv"))
        post = h[h.time_s >= .1-1e-7]
        axes[0,0].plot(post.time_s,post.top_gap_pa,color=color,label=backend)
        axes[0,1].plot(post.time_s,post.max_layer_total_error_pa,color=color)
        a = layer(probe.native(TESTS/"outputs"/label,300))
        axes[1,0].plot(a.pressure/10000,a.z0,color=color)
        axes[1,1].plot(h.time_s,h.top_settlement_mm,color=color)
    for ax in axes[0]:
        ax.axhline(100,color=".25",ls="--",lw=1)
        ax.set_xlabel("Actual time (s)")
    axes[0,0].set(title="Top adjacent-layer stress gap",ylabel="Gap (Pa)")
    axes[0,0].legend()
    axes[0,1].set(title="Maximum layer total-stress residual",ylabel="Residual (Pa)")
    axes[1,0].set(title="Pore pressure at actual t=0.3 s",xlabel="Pore pressure / q0",ylabel="Initial material z0 (m)",ylim=(.85,1))
    axes[1,1].set(title="Native top settlement",xlabel="Actual time (s)",ylabel="Settlement (mm)")
    for ax in axes.flat:
        ax.grid(alpha=.2)
    fig.suptitle("Same dp=.01 m, k=5e-5, xi=.05: CPU/GPU short comparison",fontsize=13)
    png=TESTS/"figures"/(TAG+".png")
    finish(fig,png,"Original float u-pw / Darcy. Short comparison, not 2Tv; timings include concurrent monitoring and are not isolated whole-run benchmarks.")
    csv=TESTS/"figures"/(TAG+".csv")
    data.to_csv(csv,index=False,mode="x")
    cpu=sum(x["loop_seconds"] for x in timings if x["backend"]=="CPU8")
    gpu=sum(x["loop_seconds"] for x in timings if x["backend"]=="GPU0")
    result=dict(passed=True, visual_inspected=False, utc=utc(), full_admitted=False, all_301_samples=True,
                maxima=maxima, timings=timings, gpu_seconds_over_cpu_seconds=gpu/cpu,
                selected_backend="cpu" if cpu<gpu else "gpu",
                limits=["Timings are observed same-physics loop times with monitoring, not perfectly isolated benchmarks.","Only .3-s half-step evidence; longer stability/accuracy remains pending."],
                evidence=[bound(p) for p in evidence+[png,csv]])
    save(out,result)
    print(json.dumps({k:v for k,v in result.items() if k != "evidence"},indent=2))


if __name__=="__main__":
    main()
